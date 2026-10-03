#!/usr/bin/env python3
"""Prepare verified cosmetic spec edits and record reviewed attempt history.

No author script is executed. Optional --render uses only this installed core
renderer, after its identity and hash have been checked against the element map.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_workbench import FigureWorkbench, WorkbenchError, safe_json, sha256, timestamp

MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
ELEMENT_FIELDS = ("id", "role", "label", "source_keys", "spec_paths", "editable")
SNAPSHOT_FILES = ("panel.svg", "panel.pdf", "panel.png", "panel.tiff", "elements.json", "settings.json", "qa.json", "stats.json", "plotting-data.csv")


def read_regular(path):
    path = Path(path).expanduser()
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise WorkbenchError(f"A regular, bounded absolute source file is required: {path}")
    return path.read_bytes()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def fresh_directory(path, source):
    path = Path(path).expanduser()
    if ".." in path.parts:
        raise WorkbenchError("Output path must not contain parent traversal components")
    path = path.absolute()
    source = Path(source).resolve()
    if path.exists() or path.is_symlink():
        raise WorkbenchError("Output must be a fresh attempt directory")
    if path == source or source in path.parents:
        raise WorkbenchError("Output must be outside the reviewed attempt directory")
    # Reject symlink ancestors rather than silently writing outside the named tree.
    if any(parent.is_symlink() for parent in path.parents):
        raise WorkbenchError("Output ancestors must not be symlinks")
    path.mkdir(parents=True)
    return path


def verified_attempt(figure_dir, *, require_sources=True):
    app = FigureWorkbench(figure_dir)
    state = app.state()
    if not state["manifest_valid"]:
        raise WorkbenchError("A current semantic element map is required")
    if require_sources and state["source_current"] is not True:
        raise WorkbenchError("Source, input and supplied-spec hashes must all be available and current")
    return app, state


def selected_requests(app, state, request_ids=None):
    ledger = app.ledger()
    requests = ledger["requests"]
    if request_ids:
        if len(set(request_ids)) != len(request_ids):
            raise WorkbenchError("Request IDs must be unique")
        selected = [item for item in requests if isinstance(item, dict) and item.get("id") in request_ids]
        if len(selected) != len(request_ids):
            raise WorkbenchError("A requested ID is missing")
    else:
        selected = [item for item in requests if isinstance(item, dict) and item.get("status") == "pending"]
    if not selected:
        raise WorkbenchError("No pending requests were selected")
    for item in selected:
        if item.get("status") != "pending" or item.get("version") != state["version"]:
            raise WorkbenchError("Only pending requests bound to the current figure version may be processed")
        if item.get("input", {}) != state["input"]:
            raise WorkbenchError("Request input provenance differs from the current element map")
    return ledger, selected


def pointer_parts(path):
    if not isinstance(path, str) or not path.startswith("/") or len(path) > 2000:
        raise WorkbenchError("A mapped JSON pointer is required; legacy dotted paths need an Agent")
    parts = path[1:].split("/")
    if any(not part or re.search(r"~(?![01])", part) for part in parts):
        raise WorkbenchError("Invalid JSON pointer")
    return [part.replace("~1", "/").replace("~0", "~") for part in parts]


def compatible(property_name, path):
    parts = pointer_parts(path)
    if len(parts) == 3 and parts[0] == "line_roles" and parts[1] in {"data", "summary", "reference", "axis", "grid"}:
        if property_name in {"color", "facecolor", "edgecolor"}:
            return parts[2] == "color"
        if property_name in {"linewidth", "line_width_pt"}:
            return parts[2] == "line_width_pt"
        if property_name == "linestyle":
            return parts[1] != "axis" and parts[2] == "linestyle"
        return False
    if property_name in {"color", "facecolor", "edgecolor"}:
        return ((len(parts) == 2 and parts[0] == "colors") or parts in (["options", "point_color"], ["options", "regression_color"]) or (len(parts) >= 2 and parts[0] == "style" and parts[-1] in {"color", "facecolor", "edgecolor"}))
    if property_name == "alpha":
        return parts == ["options", "alpha"] or (len(parts) >= 2 and parts[0] == "style" and parts[-1] == "alpha")
    if property_name in {"linewidth", "line_width_pt"}:
        return parts == ["layout", "line_width_pt"] or (len(parts) >= 2 and parts[0] == "style" and parts[-1] in {"linewidth", "line_width_pt"})
    if property_name == "linestyle":
        return len(parts) >= 2 and parts[0] == "style" and parts[-1] == "linestyle"
    return False


def cosmetic_value(property_name, value):
    if property_name in {"color", "facecolor", "edgecolor"}:
        # A small explicit syntax avoids CSS URLs and executable-looking strings.
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", value):
            raise WorkbenchError("Automatic color edits require #RRGGBB or #RRGGBBAA")
        return value
    if property_name in {"alpha", "linewidth", "line_width_pt"}:
        if isinstance(value, bool):
            raise WorkbenchError("Numeric cosmetic properties cannot be booleans")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise WorkbenchError("Cosmetic numeric value must be a finite number without units") from exc
        import math
        if not math.isfinite(number) or (not 0 <= number <= 1 if property_name == "alpha" else not 0 < number <= 20):
            raise WorkbenchError("Opacity must be 0 to 1; line width must be greater than 0 and at most 20 pt")
        return number
    if property_name == "linestyle" and value in ("-", "--", "-.", ":", "solid", "dashed", "dashdot", "dotted"):
        return value
    raise WorkbenchError("This property needs explicit Agent code/spec edits; data positions and quantitative areas are never automatic")


def request_elements(item, state):
    records = item.get("elements") or ([item["element"]] if isinstance(item.get("element"), dict) else [])
    ids = item.get("element_ids") if "element_ids" in item else ([item["element_id"]] if item.get("element_id") else [])
    if not ids or not isinstance(ids, list) or not all(isinstance(value, str) and value for value in ids) or len(ids) != len(set(ids)) or not isinstance(records, list) or not all(isinstance(record, dict) and isinstance(record.get("id"), str) for record in records) or {record["id"] for record in records} != set(ids):
        raise WorkbenchError("Automatic edits require real mapped element identities")
    current = {element["id"]: element for element in state["elements"]}
    for record in records:
        mapped = current.get(record.get("id"))
        if mapped is None or any(record.get(key) != mapped.get(key) for key in ELEMENT_FIELDS):
            raise WorkbenchError("Request element metadata differs from the current map")
    return records


def resolve_path(item, element):
    prop = item.get("property")
    editable = element.get("editable", [])
    if prop not in editable:
        raise WorkbenchError("Property is not editable for every selected element")
    paths = element.get("spec_paths", [])
    explicit = item.get("spec_path")
    binding = editable.get(prop) if isinstance(editable, dict) else None
    if isinstance(binding, str):
        if binding not in paths or (explicit is not None and explicit != binding):
            raise WorkbenchError("Property binding must match its mapped specification path")
        candidates = [binding]
    elif explicit is not None:
        candidates = [explicit] if explicit in paths else []
    else:
        candidates = [path for path in paths if isinstance(path, str) and path.startswith("/") and compatible(prop, path)]
    if len(candidates) != 1 or not compatible(prop, candidates[0]):
        raise WorkbenchError("Cosmetic path is unsupported or ambiguous; ask the Agent to edit code/spec explicitly")
    return candidates[0]


def set_pointer(spec, path, value):
    parts = pointer_parts(path)
    node = spec
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node or not isinstance(node[part], dict):
            raise WorkbenchError(f"Mapped cosmetic parent is absent or is not an object: {path}")
        node = node[part]
    if not isinstance(node, dict):
        raise WorkbenchError("Mapped cosmetic target must be an object property")
    node[parts[-1]] = value


def prepare_requests(figure_dir, out, request_ids=None, *, render=False):
    app, state = verified_attempt(figure_dir)
    ledger, requests = selected_requests(app, state, request_ids)
    original_ledger = copy.deepcopy(ledger)
    spec = safe_json(read_regular(state["input"]["spec_file"]))
    if not isinstance(spec, dict):
        raise WorkbenchError("Supplied specification must be an object")
    spec = copy.deepcopy(spec)
    settings = safe_json(app.read_file("settings.json") or b"{}")
    if "profile" in spec or (isinstance(settings, dict) and settings.get("figure_profile")):
        raise WorkbenchError("Shared profile edits need an Agent to preserve the profile and every dependent panel")
    patches, owners = {}, {}
    for item in requests:
        prop = item.get("property")
        value = cosmetic_value(prop, item.get("value"))
        for element in request_elements(item, state):
            path = resolve_path(item, element)
            # Core stroke roles use canonical short styles. Custom plotting
            # scripts retain the originally accepted Matplotlib alias.
            patches[path] = ({"solid": "-", "dashed": "--", "dashdot": "-.", "dotted": ":"}.get(value, value)
                             if prop == "linestyle" and pointer_parts(path)[0] == "line_roles" else value)
            owners[path] = item["id"]
    # Preserve all accepted category assignments before adding one explicit color.
    if any(pointer_parts(path)[0] == "colors" for path in patches) and "colors" not in spec:
        colors = settings.get("resolved_colors") if isinstance(settings, dict) else None
        if not isinstance(colors, dict) or not colors:
            raise WorkbenchError("A complete resolved category-color mapping is required")
        canonical_colors = json.dumps(colors, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        if state["version"].get("resolved_colors_sha256") != sha256(canonical_colors):
            raise WorkbenchError("Accepted category colors need a matching resolved-colors hash; legacy palette maps require Agent verification")
        spec["colors"] = copy.deepcopy(colors)
    for path, value in patches.items():
        if pointer_parts(path)[0] == "colors" and pointer_parts(path)[1] not in spec.get("colors", {}):
            raise WorkbenchError("Category color target is not an accepted category")
        if pointer_parts(path)[0] == "options" and "options" not in spec:
            spec["options"] = {}
        set_pointer(spec, path, value)
    renderer_path = Path(__file__).with_name("render.py").resolve()
    if render:
        source = Path(state["input"]["source_script"])
        if source.resolve() != renderer_path or state["version"].get("source_script_sha256") != sha256(read_regular(renderer_path)):
            raise WorkbenchError("--render accepts only the unchanged installed core renderer; author scripts need an Agent")
        if any(pointer_parts(path)[0] == "style" for path in patches):
            raise WorkbenchError("Custom style bindings need Agent implementation; core rerender does not consume them")
        import render as core_renderer
        resolved, _ = core_renderer.resolve_spec(safe_json(read_regular(state["input"]["spec_file"])), spec_path=Path(state["input"]["spec_file"]))
        canonical = json.dumps(resolved, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        if sha256(canonical) != state["version"].get("spec_sha256"):
            raise WorkbenchError("Resolved specification differs from the reviewed figure version")
    # Recheck provenance after planning and before making a new attempt.
    if app.state()["version"] != state["version"] or app.state()["source_current"] is not True:
        raise WorkbenchError("Figure or source changed while preparing requests")
    target = fresh_directory(out, app.root)
    spec_path = target / "plot-spec.json"
    write_json(spec_path, spec)
    affected = {path: [element["id"] for element in state["elements"] if path in element.get("spec_paths", [])] for path in patches}
    plan = {"schema_version": 1, "status": "prepared", "created_at": timestamp(), "from_attempt": str(app.root), "version": state["version"], "input": state["input"], "request_ids": [item["id"] for item in requests], "patches": [{"spec_path": path, "value": value, "request_id": owners[path], "affected_element_ids": affected[path]} for path, value in patches.items()], "spec_file": str(spec_path), "spec_sha256": sha256(spec_path.read_bytes()), "rendered": False, "note": "Only explicit cosmetic spec paths changed. Render with the plotting source and review the new exports before recording requests as applied."}
    write_json(target / "request-plan.json", plan)
    if render:
        core_renderer.render(Path(state["input"]["data_file"]), spec, target, spec_path=spec_path, track=state.get("track") or None)
        plan.update(status="rendered", rendered=True)
        write_json(target / "request-plan.json", plan)
        record_requests(app.root, target, [item["id"] for item in requests], changed_files=["plot-spec.json"], validation="Core render QA passed; final visual review remains required.", superseded_ids=[item["id"] for item in requests if item["id"] not in owners.values()])
    else:
        ledger.setdefault("history", []).append({"id": str(uuid.uuid4()), "action": "prepared", "at": timestamp(), "request_ids": plan["request_ids"], "target_attempt": str(target), "spec_sha256": plan["spec_sha256"]})
        ledger["updated_at"] = timestamp()
        if app.ledger() != original_ledger:
            raise WorkbenchError("Request queue changed while preparing; the new plan is preserved, but history was not overwritten")
        app.write_ledger(ledger)
    return plan


def record_requests(figure_dir, target_dir, request_ids, *, changed_files, validation, superseded_ids=None):
    app, state = verified_attempt(figure_dir, require_sources=False)
    target_app, target = verified_attempt(target_dir)
    ledger, requests = selected_requests(app, state, request_ids)
    original_ledger = copy.deepcopy(ledger)
    target_ledger = target_app.ledger()
    if target_app.root == app.root or app.root in target_app.root.parents:
        raise WorkbenchError("Applied results must be a separate fresh attempt")
    if state["version"].get("input_sha256") != target["version"].get("input_sha256"):
        raise WorkbenchError("Cosmetic request history requires unchanged source data")
    qa = safe_json(target_app.read_file("qa.json") or b"{}")
    if not isinstance(qa, dict) or qa.get("status") != "pass":
        raise WorkbenchError("A passing target qa.json is required before recording application")
    if not isinstance(validation, str) or not validation.strip() or len(validation) > 8000:
        raise WorkbenchError("Describe validation of the fresh target attempt")
    if not changed_files or not all(isinstance(name, str) and name and not Path(name).is_absolute() and ".." not in Path(name).parts and (target_app.root / name).is_file() and not (target_app.root / name).is_symlink() and (target_app.root / name).resolve().is_relative_to(target_app.root) for name in changed_files):
        raise WorkbenchError("Changed files must identify regular files inside the target attempt")
    superseded = set(superseded_ids or [])
    if not superseded <= {item["id"] for item in requests}:
        raise WorkbenchError("Superseded IDs must be among the processed requests")
    event = {"id": str(uuid.uuid4()), "action": "applied", "at": timestamp(), "from_version": state["version"], "target_attempt": str(target_app.root), "target_version": target["version"], "request_ids": [item["id"] for item in requests], "changed_files": changed_files, "validation": validation.strip()}
    for item in requests:
        item.update(status="superseded" if item["id"] in superseded else "applied", applied_at=event["at"], result={key: event[key] for key in ("target_attempt", "target_version", "changed_files", "validation")})
        if item["id"] in superseded:
            item["superseded_by"] = [request["id"] for request in requests if request["id"] not in superseded]
    if app.state()["version"] != state["version"] or target_app.state()["version"] != target["version"] or target_app.state()["source_current"] is not True:
        raise WorkbenchError("Figure or target source changed while recording application")
    ledger.setdefault("history", []).append(event)
    ledger.update(updated_at=timestamp(), version=state["version"])
    if app.ledger() != original_ledger or target_app.ledger() != target_ledger:
        raise WorkbenchError("Request queue changed while recording; retry without overwriting newer requests")
    merged = copy.deepcopy(ledger)
    source_ids = {item.get("id") for item in merged["requests"] if isinstance(item, dict)}
    merged["requests"].extend(copy.deepcopy(item) for item in target_ledger["requests"] if not isinstance(item, dict) or item.get("id") not in source_ids)
    history_ids = {item.get("id") for item in merged.get("history", []) if isinstance(item, dict) and item.get("id")}
    merged["history"].extend(copy.deepcopy(item) for item in target_ledger.get("history", []) if not item.get("id") or item["id"] not in history_ids)
    app.write_ledger(ledger)
    target_app.write_ledger(merged)
    return event


def accept_attempt(figure_dir, *, validation):
    app, state = verified_attempt(figure_dir)
    qa = safe_json(app.read_file("qa.json") or b"{}")
    if not isinstance(qa, dict) or qa.get("status") != "pass" or not isinstance(validation, str) or not validation.strip():
        raise WorkbenchError("Accept requires passing QA and a description of visual validation")
    spec = safe_json(read_regular(state["input"]["spec_file"]))
    settings = safe_json(app.read_file("settings.json") or b"{}")
    if not isinstance(spec, dict) or "profile" in spec or (isinstance(settings, dict) and settings.get("figure_profile")):
        raise WorkbenchError("Accepted restore supports one self-contained source/spec/data attempt; shared profiles need an Agent")
    snapshot = app.root / "accepted-snapshot"
    if snapshot.exists() or snapshot.is_symlink():
        raise WorkbenchError("This attempt already has an accepted snapshot; preserve it")
    files = {name: read_regular(app.root / name) for name in SNAPSHOT_FILES if (app.root / name).exists()}
    provenance = {}
    for field, name in (("spec_file", "plot-spec.json"), ("source_script", "plot-source.py"), ("data_file", "source-data.csv")):
        files[name] = read_regular(state["input"][field])
        provenance[field] = name
    if app.state()["version"] != state["version"] or app.state()["source_current"] is not True:
        raise WorkbenchError("Figure or source changed while accepting the attempt")
    snapshot.mkdir()
    for name, data in files.items():
        (snapshot / name).write_bytes(data)
    acceptance = {"schema_version": 1, "accepted_at": timestamp(), "version": state["version"], "input": state["input"], "provenance": provenance, "files": {name: sha256(data) for name, data in files.items()}, "validation": validation.strip()}
    write_json(snapshot / "acceptance.json", acceptance)
    ledger = app.ledger()
    ledger.setdefault("history", []).append({"id": str(uuid.uuid4()), "action": "accepted", "at": acceptance["accepted_at"], "target_attempt": str(app.root), "version": state["version"], "validation": validation.strip()})
    ledger["updated_at"] = timestamp()
    app.write_ledger(ledger)
    return acceptance


def restore_attempt(figure_dir, out):
    app = FigureWorkbench(figure_dir)
    snapshot = app.root / "accepted-snapshot"
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise WorkbenchError("A verified accepted-snapshot is required")
    acceptance = safe_json(read_regular(snapshot / "acceptance.json"))
    if not isinstance(acceptance, dict) or acceptance.get("schema_version") != 1 or not isinstance(acceptance.get("files"), dict):
        raise WorkbenchError("Unsupported acceptance snapshot")
    allowed = set(SNAPSHOT_FILES) | {"plot-spec.json", "plot-source.py", "source-data.csv"}
    files = {}
    for name, expected in acceptance["files"].items():
        if name not in allowed:
            raise WorkbenchError("Snapshot contains an unsupported or escaping path")
        data = read_regular(snapshot / name)
        if sha256(data) != expected:
            raise WorkbenchError("Accepted snapshot has changed; restoration is refused")
        files[name] = data
    if not {"panel.svg", "elements.json", "plot-spec.json", "plot-source.py", "source-data.csv"} <= files.keys():
        raise WorkbenchError("Snapshot must restore source, specification, input and exports together")
    manifest = safe_json(files["elements.json"])
    if not isinstance(manifest, dict) or not isinstance(manifest.get("version"), dict) or manifest.get("version") != acceptance.get("version") or manifest["version"].get("figure_sha256") != sha256(files["panel.svg"]):
        raise WorkbenchError("Accepted manifest/export version does not match the snapshot")
    input_info = manifest.get("input", {})
    if not isinstance(input_info, dict):
        raise WorkbenchError("Accepted provenance must be an object")
    for field, name, expected in (("data_file", "source-data.csv", manifest["version"].get("input_sha256")), ("source_script", "plot-source.py", manifest["version"].get("source_script_sha256")), ("spec_file", "plot-spec.json", input_info.get("supplied_spec_sha256"))):
        if expected != sha256(files[name]):
            raise WorkbenchError("Accepted provenance does not match the restored source bundle")
    target = fresh_directory(out, app.root)
    for name, data in files.items():
        (target / name).write_bytes(data)
    manifest["input"] = {**input_info, "data_file": str(target / "source-data.csv"), "source_script": str(target / "plot-source.py"), "spec_file": str(target / "plot-spec.json")}
    write_json(target / "elements.json", manifest)
    target_app, restored = verified_attempt(target)
    event = {"id": str(uuid.uuid4()), "action": "restored", "at": timestamp(), "accepted_attempt": str(app.root), "target_attempt": str(target), "target_version": restored["version"], "validation": acceptance.get("validation", ""), "note": "Source/spec/input and matching accepted exports were restored together. No author script was executed."}
    ledger = copy.deepcopy(app.ledger())
    for item in ledger["requests"]:
        if isinstance(item, dict) and item.get("status") == "pending":
            item.update(status="superseded", superseded_at=event["at"], superseded_by_restore=event["id"])
    ledger.setdefault("history", []).append(event)
    ledger.update(version=restored["version"], updated_at=timestamp())
    target_app.write_ledger(ledger)
    write_json(target / "restoration.json", event)
    return event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("apply", "record", "accept", "restore"):
        child = sub.add_parser(command)
        child.add_argument("--figure-dir", required=True, type=Path)
        if command in {"apply", "restore"}:
            child.add_argument("--out", required=True, type=Path)
        if command in {"apply", "record"}:
            child.add_argument("--request-id", action="append", dest="request_ids")
        if command == "apply":
            child.add_argument("--render", action="store_true", help="Rerender only with the hash-verified installed core renderer")
        if command in {"record", "accept"}:
            child.add_argument("--validation", required=True)
        if command == "record":
            child.add_argument("--target-dir", required=True, type=Path)
            child.add_argument("--changed-file", action="append", required=True, dest="changed_files")
            child.add_argument("--superseded-id", action="append", dest="superseded_ids")
    args = parser.parse_args()
    try:
        if args.command == "apply":
            result = prepare_requests(args.figure_dir, args.out, args.request_ids, render=args.render)
        elif args.command == "record":
            result = record_requests(args.figure_dir, args.target_dir, args.request_ids, changed_files=args.changed_files, validation=args.validation, superseded_ids=args.superseded_ids)
        elif args.command == "accept":
            result = accept_attempt(args.figure_dir, validation=args.validation)
        else:
            result = restore_attempt(args.figure_dir, args.out)
    except (WorkbenchError, OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Cannot process figure requests: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
