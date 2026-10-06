#!/usr/bin/env python3
"""Portable, source-bound EasyViz documents; opening a document never runs its code.

An .ev file is a bounded ZIP containing a real mapped SVG, ordinary exports and
the exact declared plotting inputs. Source bytes and adopted statistics remain
unchanged; only explicit location metadata is rebound when a copy is opened.
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
import zlib

from figure_workbench import (FigureWorkbench, WorkbenchError, read_svg, sanitized_svg, sha256,
                              MAX_FIGURE_INFO_BYTES, make_figure_info,
                              validate_figure_info, validate_figure_name)
from figure_handoff import HandoffError, normalize_inputs
from apply_figure_requests import ANALYSIS_CAPTURE_NAMES, passing_qa, verify_declared_exports, set_pointer

MAX_DOCUMENT_BYTES = 64 * 1024 * 1024
MAX_UNPACKED_BYTES = 128 * 1024 * 1024
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_MEMBERS = 256
KIND = "easyviz-editable-document"
SCHEMA_VERSION = 1
MANIFEST = "document.json"
EXPORTS = {"panel.svg", "panel.pdf", "panel.png", "panel.tiff"}
SIDECARS = {"elements.json", "handoff.json", "settings.json", "qa.json", "stats.json",
            "plotting-data.csv", "analysis-caption.md", "caption.md", "figure-caption.md", "requests.json",
            "figure-info.json"}
LOCATION_RECORDS = {"elements.json", "handoff.json", "settings.json", "qa.json"}
RUNTIME_HELPERS = {"legend_layout.py", "figure_profile.py", "auto_layout.py", "annotation_review.py",
                   "figure_elements.py", "panel_readability.py", "observation_clipping.py", "analysis_result.py"}
REQUIRED_CORE_HELPERS = RUNTIME_HELPERS - {"analysis_result.py"}
PRIMARY = {"data_file": "input_sha256", "source_script": "source_script_sha256", "spec_file": None}


class EVDocumentError(ValueError):
    """The document cannot safely preserve a selectable, source-bound figure."""


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise EVDocumentError("Document JSON contains duplicate keys")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
        pending, nodes = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            nodes += 1
            if depth > 64 or nodes > 100000 or isinstance(item, float) and not math.isfinite(item):
                raise EVDocumentError("Document JSON exceeds finite structure limits")
            if isinstance(item, dict):
                pending.extend((part, depth + 1) for part in item.values())
            elif isinstance(item, list):
                pending.extend((part, depth + 1) for part in item)
        return value
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise EVDocumentError(f"Document JSON must be finite and unambiguous: {exc}") from exc


def _encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def _member(name):
    if (not isinstance(name, str) or not name or len(name) > 300 or "\\" in name or ":" in name
            or any(ord(char) < 32 for char in name) or name.startswith("/") or any(part in {"", ".", ".."} for part in name.split("/"))
            or str(PurePosixPath(name)) != name):
        raise EVDocumentError("Document members must have regular relative paths")
    return name


def _regular(path, *, limit=MAX_MEMBER_BYTES):
    path = Path(path).expanduser().absolute()
    if path.is_symlink() or not path.is_file() or any(parent.is_symlink() for parent in path.parents):
        raise EVDocumentError(f"A regular source file is required: {path}")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise EVDocumentError("Document input exceeds the bounded file size")
    return raw


def _replace_paths(value, locations):
    if isinstance(value, dict):
        return {key: _replace_paths(item, locations) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_paths(item, locations) for item in value]
    return locations.get(value, value) if isinstance(value, str) else value


def _rebound_input(info, locations):
    info = copy.deepcopy(info)
    if not isinstance(info, dict):
        raise EVDocumentError("Source location metadata must be an object")
    for field in PRIMARY:
        if isinstance(info.get(field), str):
            info[field] = locations.get(info[field], info[field])
    for name in ("auxiliary_inputs", "aligned_layer_inputs"):
        auxiliary = info.get(name, {})
        if not isinstance(auxiliary, dict):
            raise EVDocumentError("Auxiliary source location metadata must be an object")
        for record in auxiliary.values():
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise EVDocumentError("Auxiliary source metadata requires an explicit path")
            record["path"] = locations.get(record["path"], record["path"])
    return info


def _relocate_metadata(name, value, locations, receipt=None):
    """Rebind known location records while preserving literal labels and science."""
    value = copy.deepcopy(value)
    if not isinstance(value, dict):
        raise EVDocumentError("Figure location metadata must be an object")
    if name in {"elements.json", "handoff.json"}:
        value["input"] = _rebound_input(value["input"], locations)
    elif name == "settings.json":
        if isinstance(value.get("input"), dict):
            value["input"] = _rebound_input(value["input"], locations)
        for field in ("inputs", "source_bindings"):
            records = value.get(field, {})
            if not isinstance(records, dict):
                raise EVDocumentError("Declared settings source bindings must be an object")
            for record in records.values():
                if isinstance(record, dict) and isinstance(record.get("path"), str):
                    record["path"] = locations.get(record["path"], record["path"])
        if isinstance(value.get("figure_profile"), dict):
            record = value["figure_profile"]
            record["path"] = locations.get(record.get("path"), record.get("path"))
        for key in ("input_file", "source_script", "spec_file"):
            if isinstance(value.get(key), dict) and isinstance(value[key].get("path"), str):
                value[key]["path"] = locations.get(value[key]["path"], value[key]["path"])
            elif isinstance(value.get(key), str):
                value[key] = locations.get(value[key], value[key])
        for role, evidence in (receipt or {}).get("consumption", {}).get("auxiliary_claims", {}).items():
            original = (receipt or {}).get("input", {}).get("auxiliary_inputs", {}).get(role, {}).get("path")
            if original in locations:
                set_pointer(value, evidence["path"], locations[original])
    elif name == "qa.json" and "source_continuity" in value:
        value["source_continuity"] = _replace_paths(value["source_continuity"], locations)
    return value


def _relocate_requests(raw, version, old_input, new_input):
    ledger = _json(raw)
    if not isinstance(ledger, dict) or not isinstance(ledger.get("requests"), list):
        raise EVDocumentError("Document requests must have a valid request ledger")
    for item in ledger["requests"]:
        if not isinstance(item, dict) or item.get("status") != "pending":
            continue
        if item.get("version") == version and item.get("input") == old_input:
            item["input"] = copy.deepcopy(new_input)
        elif item.get("version") == version:
            item["status"] = "stale"
            item["document_import_note"] = "Source provenance differs from this document; the request was retained without reassigning it."
    return _encode(ledger)


def _verified_tree(root):
    app = FigureWorkbench(root)
    state = app.state()
    if not state["manifest_valid"] or not state["elements"]:
        raise EVDocumentError("Re-export this figure with a current real element map before creating an .ev document")
    if not state["provenance_valid"] or state["source_current"] is not True:
        raise EVDocumentError("Re-export this figure: its declared source, data, specification or exports are stale")
    svg, _, _ = read_svg(app.read_file("panel.svg", required=True))
    identifiers = [node.attrib["id"] for node in svg.iter() if "id" in node.attrib]
    if len(identifiers) != len(set(identifiers)):
        raise EVDocumentError("SVG contains duplicate element IDs")
    safe, _, _ = read_svg(sanitized_svg(svg))
    visible_ids = {node.attrib["id"] for node in safe.iter() if "id" in node.attrib}
    if any(element["id"] not in visible_ids for element in state["elements"]):
        raise EVDocumentError("Selectable element IDs must belong to the actual safe figure preview")
    qa = passing_qa(app.read_file("qa.json"), "document")
    verify_declared_exports(qa, lambda name: _regular(Path(root) / name))
    return app, state, qa


def _input_name(field, path, *, core=False):
    if field == "spec_file":
        return "inputs/plot-spec.json"
    if field == "data_file":
        suffix = path.suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,12}", path.suffix) else ".bin"
        return "inputs/source-data" + suffix
    return _member("inputs/" + ("runtime/render.py" if core else "source/" + path.name))


def _capture(root):
    app, state, qa = _verified_tree(root)
    qa_before = app.read_file("qa.json")
    info = state["input"]
    raw_inputs = {field: _regular(info[field]) for field in PRIMARY}
    for field, version_key in PRIMARY.items():
        expected = info.get("supplied_spec_sha256") if field == "spec_file" else state["version"].get(version_key)
        if sha256(raw_inputs[field]) != expected:
            raise EVDocumentError("A declared source changed while packing the document")
    installed = Path(__file__).with_name("render.py")
    auxiliary = info.get("auxiliary_inputs", {})
    core = (sha256(raw_inputs["source_script"]) == sha256(_regular(installed))
            and {"helper:" + name for name in REQUIRED_CORE_HELPERS} <= auxiliary.keys())
    files, bindings, locations = {}, {}, {}
    for field, raw in raw_inputs.items():
        path = Path(info[field])
        name = _input_name(field, path, core=core)
        files[name], bindings[field], locations[str(path)] = raw, name, name
    bindings["auxiliary_inputs"] = {}
    for index, (role, record) in enumerate(sorted(auxiliary.items()), start=1):
        path, raw = Path(record["path"]), _regular(record["path"])
        if sha256(raw) != record["sha256"]:
            raise EVDocumentError("A declared auxiliary input changed while packing the document")
        if role in ANALYSIS_CAPTURE_NAMES:
            name = "inputs/adopted-analysis/" + ANALYSIS_CAPTURE_NAMES[role]
        elif role.startswith("helper:"):
            name = _member("inputs/" + ("runtime/" if core else "source/") + path.name)
        else:
            suffix = path.suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,12}", path.suffix) else ".bin"
            name = locations.get(str(path), f"inputs/auxiliary-{index:04d}{suffix}")
        if name in files and files[name] != raw:
            raise EVDocumentError("Declared source inputs collide at the same document path")
        files[name], locations[str(path)], bindings["auxiliary_inputs"][role] = raw, name, name
    declared = {"panel.svg"} | {"panel." + ext for ext in qa.get("exports", {})}
    receipt = _json(app.read_file("handoff.json")) if app.read_file("handoff.json") else None
    if receipt:
        declared.update(receipt["exports"])
    if not declared <= EXPORTS:
        raise EVDocumentError("Document has unsupported declared exports")
    for name in sorted(declared | SIDECARS):
        path = Path(root) / name
        if path.exists() or path.is_symlink():
            raw = _regular(path, limit=MAX_FIGURE_INFO_BYTES if name == "figure-info.json" else MAX_MEMBER_BYTES)
            files[name] = _encode(_relocate_metadata(name, _json(raw), locations, receipt)) if name in LOCATION_RECORDS else raw
    figure_name = validate_figure_name(state["figure_name"])
    figure_info = validate_figure_info(_json(files["figure-info.json"])) if "figure-info.json" in files else make_figure_info(figure_name)
    if figure_info["display_name"] != figure_name:
        raise EVDocumentError("Figure display name changed while packing the document")
    files["figure-info.json"] = _encode(figure_info)
    # Every primary/auxiliary input path in these records must be package-local,
    # including receipts generated from a previously relocated document.
    for name in ("elements.json", "handoff.json"):
        if name in files:
            record = _json(files[name])
            record["input"] = _rebound_input(info, locations)
            files[name] = _encode(record)
    if "requests.json" in files:
        files["requests.json"] = _relocate_requests(files["requests.json"], state["version"], info, _rebound_input(info, locations))
    _, after, _ = _verified_tree(root)
    if (after["version"] != state["version"] or after["figure_name"] != state["figure_name"]
            or after["source_current"] is not True or app.read_file("qa.json") != qa_before):
        raise EVDocumentError("Figure or source changed while packing the document")
    runtime = {"render.py": sha256(raw_inputs["source_script"])} if core else {}
    if core:
        for role, record in auxiliary.items():
            filename = role.removeprefix("helper:")
            if role.startswith("helper:") and filename in RUNTIME_HELPERS:
                runtime[filename] = record["sha256"]
    manifest = {"kind": KIND, "schema_version": SCHEMA_VERSION, "name": figure_name,
                "track": state.get("track", ""), "panel": state["panel"], "version": state["version"],
                "formats": sorted(name.rsplit(".", 1)[1] for name in declared), "bindings": bindings,
                "renderer": {"kind": "core" if core else "custom", "runtime": runtime},
                "members": {name: sha256(raw) for name, raw in sorted(files.items())}}
    manifest["id"] = "ev-" + sha256(_encode({"version": manifest["version"], "members": manifest["members"]}))[:24]
    return manifest, files


def _read_document(path):
    path = Path(path).expanduser().absolute()
    if path.suffix.lower() != ".ev":
        raise EVDocumentError("Open an EasyViz .ev document; ordinary image files require source-backed re-export")
    raw = _regular(path, limit=MAX_DOCUMENT_BYTES)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if not 2 <= len(entries) <= MAX_MEMBERS:
                raise EVDocumentError("Document contains too many or too few members")
            names, total, files = set(), 0, {}
            for entry in entries:
                name = _member(entry.filename)
                mode = entry.external_attr >> 16
                if (name in names or entry.is_dir() or entry.flag_bits & 1 or stat.S_ISLNK(mode)
                        or stat.S_IFMT(mode) not in {0, stat.S_IFREG}
                        or entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        or not 0 <= entry.file_size <= MAX_MEMBER_BYTES):
                    raise EVDocumentError("Document has duplicate, special, encrypted or oversized members")
                names.add(name)
                total += entry.file_size
                if total > MAX_UNPACKED_BYTES:
                    raise EVDocumentError("Document exceeds the unpacked size limit")
                with archive.open(entry) as stream:
                    content = stream.read(MAX_MEMBER_BYTES + 1)
                if len(content) != entry.file_size or len(content) > MAX_MEMBER_BYTES:
                    raise EVDocumentError("Document member size differs from its bounded declaration")
                files[name] = content
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError, zlib.error) as exc:
        raise EVDocumentError(f"Cannot read the EasyViz document: {exc}") from exc
    manifest = _json(files.pop(MANIFEST, b"{}"))
    if (not isinstance(manifest, dict) or manifest.get("kind") != KIND or manifest.get("schema_version") != SCHEMA_VERSION
            or not re.fullmatch(r"ev-[0-9a-f]{24}", str(manifest.get("id", "")))
            or not isinstance(manifest.get("members"), dict) or set(manifest["members"]) != set(files)):
        raise EVDocumentError("Unsupported or incomplete editable-document manifest")
    for name, content in files.items():
        if manifest["members"][name] != sha256(content):
            raise EVDocumentError("Document member content differs from its declared binding")
    expected_id = "ev-" + sha256(_encode({"version": manifest.get("version"), "members": manifest["members"]}))[:24]
    if manifest["id"] != expected_id:
        raise EVDocumentError("Document identity differs from its declared members")
    manifest["name"] = validate_figure_name(manifest.get("name"))
    if "figure-info.json" in files:
        if len(files["figure-info.json"]) > MAX_FIGURE_INFO_BYTES:
            raise EVDocumentError("Figure display metadata exceeds the bounded file size")
        figure_info = validate_figure_info(_json(files["figure-info.json"]))
        if figure_info["display_name"] != manifest["name"]:
            raise EVDocumentError("Document name differs from its figure display metadata")
    bindings = manifest.get("bindings")
    if not isinstance(bindings, dict) or not isinstance(bindings.get("auxiliary_inputs"), dict):
        raise EVDocumentError("Document requires complete input bindings")
    locations = [bindings.get(field) for field in PRIMARY] + list(bindings["auxiliary_inputs"].values())
    if any(not isinstance(name, str) or _member(name) not in files or not name.startswith("inputs/") for name in locations):
        raise EVDocumentError("Document input bindings must identify preserved local members")
    if not {"panel.svg", "elements.json", "qa.json"} <= files.keys() or set(files) - (EXPORTS | SIDECARS | set(locations)):
        raise EVDocumentError("Document has missing essential or undeclared members")
    renderer = manifest.get("renderer")
    if (not isinstance(renderer, dict) or renderer.get("kind") not in {"core", "custom"}
            or not isinstance(renderer.get("runtime"), dict)
            or set(renderer["runtime"]) - (RUNTIME_HELPERS | {"render.py"})):
        raise EVDocumentError("Document runtime binding is unsupported")
    expected_runtime = {"render.py"} | {role.removeprefix("helper:") for role in bindings["auxiliary_inputs"]
                                       if role.startswith("helper:") and role.removeprefix("helper:") in RUNTIME_HELPERS}
    if renderer["kind"] == "core" and (not REQUIRED_CORE_HELPERS <= expected_runtime
                                        or set(renderer["runtime"]) != expected_runtime):
        raise EVDocumentError("Core documents require their complete captured runtime closure")
    for filename, expected in renderer["runtime"].items():
        role = "source_script" if filename == "render.py" else "helper:" + filename
        name = bindings[role] if role in PRIMARY else bindings["auxiliary_inputs"].get(role)
        if name not in files or expected != sha256(files[name]):
            raise EVDocumentError("Preserved runtime source differs from its declared identity")
    for name in ("elements.json", "handoff.json"):
        if name not in files:
            continue
        record = _json(files[name])
        if not isinstance(record, dict) or not isinstance(record.get("input"), dict):
            raise EVDocumentError("Document source records require explicit input bindings")
        if any(record["input"].get(field) != bindings[field] for field in PRIMARY):
            raise EVDocumentError("Document source records disagree with its input bindings")
        auxiliary = normalize_inputs(record["input"], Path("/").absolute()).get("auxiliary_inputs", {})
        declared = record["input"].get("auxiliary_inputs", {})
        if set(auxiliary) != set(bindings["auxiliary_inputs"]) or any(declared[role].get("path") != bindings["auxiliary_inputs"][role] for role in auxiliary):
            raise EVDocumentError("Document must retain every declared auxiliary input")
    return manifest, files


def _materialize(root, manifest, files, *, trusted_runtime=False):
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    # Older .ev documents only named the manifest. Promote that label to the
    # portable display metadata instead of replacing it with the import folder.
    if "figure-info.json" not in files:
        (root / "figure-info.json").write_bytes(_encode(make_figure_info(manifest["name"])))
    bindings = manifest["bindings"]
    locations = {name: str(root / name) for name in [bindings[field] for field in PRIMARY] + list(bindings["auxiliary_inputs"].values())}
    runtime = manifest["renderer"]["runtime"]
    matched = manifest["renderer"]["kind"] == "core" and runtime.get("render.py") == sha256(files[bindings["source_script"]])
    for name, expected in runtime.items():
        installed = Path(__file__).with_name(name)
        matched = matched and installed.is_file() and sha256(_regular(installed)) == expected
    if trusted_runtime and matched:
        locations[bindings["source_script"]] = str(Path(__file__).with_name("render.py").resolve())
        for role, name in bindings["auxiliary_inputs"].items():
            filename = role.removeprefix("helper:")
            if role.startswith("helper:") and filename in runtime:
                if sha256(files[name]) != runtime[filename]:
                    raise EVDocumentError("Preserved runtime helper differs from its declared identity")
                locations[name] = str(Path(__file__).with_name(filename).resolve())
    portable_input = _json(files["elements.json"])["input"]
    receipt = _json(files["handoff.json"]) if "handoff.json" in files else None
    for name in LOCATION_RECORDS:
        if name in files:
            (root / name).write_bytes(_encode(_relocate_metadata(name, _json(files[name]), locations, receipt)))
    app, state, _ = _verified_tree(root)
    if (state["version"] != manifest.get("version") or state["panel"] != manifest.get("panel")
            or state["figure_name"] != manifest["name"]):
        raise EVDocumentError("Document metadata differs from its actual source-bound figure")
    actual_formats = sorted(name.rsplit(".", 1)[1] for name in EXPORTS & files.keys())
    if actual_formats != manifest.get("formats"):
        raise EVDocumentError("Document export formats differ from its actual members")
    if "requests.json" in files:
        (root / "requests.json").write_bytes(_relocate_requests(files["requests.json"], state["version"], portable_input, state["input"]))
    spec = _json(files[bindings["spec_file"]])
    statistics = spec.get("statistics", {}) if isinstance(spec, dict) else {}
    analysis = statistics.get("analysis") if isinstance(statistics, dict) else None
    if isinstance(analysis, dict):
        auxiliary = state["input"].get("auxiliary_inputs", {})
        if not set(ANALYSIS_CAPTURE_NAMES) <= set(auxiliary) or auxiliary["analysis_result"]["sha256"] != analysis.get("results_sha256"):
            raise EVDocumentError("Adopted statistics require their matching result and every declared companion")
        derived = copy.deepcopy(spec)
        derived["statistics"]["analysis"]["results_file"] = auxiliary["analysis_result"]["path"]
        (root / "rerender-spec.json").write_bytes(_encode(derived))
    return state, matched


def export_document(figure_dir, output_path=None):
    """Atomically create/refresh panel.ev from a verified mapped attempt."""
    try:
        root = Path(figure_dir).expanduser().resolve()
        output = Path(output_path).expanduser().absolute() if output_path is not None else root / "panel.ev"
        if (output.suffix.lower() != ".ev" or output.is_symlink() or not output.parent.is_dir()
                or any(parent.is_symlink() for parent in output.parents) or (output.exists() and not output.is_file())):
            raise EVDocumentError("Output must be a regular .ev file in an existing local directory")
        manifest, files = _capture(root)
        state = FigureWorkbench(root).state()
        source_paths = [state["input"][field] for field in PRIMARY] + [record["path"] for record in state["input"].get("auxiliary_inputs", {}).values()]
        if any(output == Path(path).absolute() for path in source_paths):
            raise EVDocumentError("Document export must not replace any declared plotting input")
        if len(files) + 1 > MAX_MEMBERS or sum(map(len, files.values())) > MAX_UNPACKED_BYTES:
            raise EVDocumentError("Declared figure inputs exceed the document size limits")
        # Recheck the exact portable document in isolation before publication.
        with tempfile.TemporaryDirectory(prefix="easyviz-ev-verify-") as temporary:
            _materialize(Path(temporary).resolve(), manifest, files)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in {MANIFEST: _encode(manifest), **files}.items():
                archive.writestr(name, raw)
        raw = buffer.getvalue()
        if len(raw) > MAX_DOCUMENT_BYTES:
            raise EVDocumentError("Compressed document exceeds its size limit")
        temporary = output.with_name(output.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(raw)
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
        return output
    except (WorkbenchError, HandoffError, OSError, KeyError, TypeError) as exc:
        raise EVDocumentError(str(exc)) from exc


def inspect_document(document_path):
    """Validate a document and return library metadata without executing sources."""
    try:
        manifest, files = _read_document(document_path)
        with tempfile.TemporaryDirectory(prefix="easyviz-ev-inspect-") as temporary:
            _, runtime_available = _materialize(Path(temporary).resolve(), manifest, files)
        return {key: copy.deepcopy(manifest[key]) for key in ("kind", "schema_version", "id", "name", "track", "panel", "version", "formats", "renderer")} | {"runtime_available": runtime_available}
    except (WorkbenchError, HandoffError, OSError, KeyError, TypeError) as exc:
        raise EVDocumentError(str(exc)) from exc


def import_document(document_path, project_dir):
    """Open a validated copy in a fresh project attempt; never run package code."""
    target = None
    created = False
    try:
        project = Path(project_dir).expanduser().absolute()
        if not project.is_dir() or project.is_symlink() or any(parent.is_symlink() for parent in project.parents):
            raise EVDocumentError("Import requires an existing regular project directory")
        manifest, files = _read_document(document_path)
        # Validate fully before adding anything to the chosen project.
        with tempfile.TemporaryDirectory(prefix="easyviz-ev-import-check-") as temporary:
            _materialize(Path(temporary).resolve(), manifest, files)
        target = project / ("ev-import-" + uuid.uuid4().hex)
        target.mkdir()
        created = True
        state, matched = _materialize(target, manifest, files, trusted_runtime=True)
        provenance = {"kind": KIND, "schema_version": SCHEMA_VERSION, "document_id": manifest["id"],
                      "name": manifest["name"], "version": state["version"], "renderer": manifest["renderer"],
                      "runtime_available": matched, "note": "Preserved figure and input bytes; source location metadata rebound without executing package code."}
        (target / "document-origin.json").write_bytes(_encode(provenance))
        return target
    except (WorkbenchError, HandoffError, OSError, KeyError, TypeError, EVDocumentError) as exc:
        if target is not None and created:
            shutil.rmtree(target, ignore_errors=True)
        raise EVDocumentError(str(exc)) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("figure_dir", type=Path)
    export.add_argument("--out", type=Path)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("document", type=Path)
    opening = commands.add_parser("import")
    opening.add_argument("document", type=Path)
    opening.add_argument("--project-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export_document(args.figure_dir, args.out) if args.command == "export" else import_document(args.document, args.project_dir) if args.command == "import" else inspect_document(args.document)
        print(json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else result)
    except EVDocumentError as exc:
        parser.exit(2, f"Cannot open EasyViz document: {exc}\n")


if __name__ == "__main__":
    main()
