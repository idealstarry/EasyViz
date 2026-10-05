"""Bind custom figure exports to their actual source files without inventing IDs.

This receipt records provenance only. It cannot certify aesthetics, statistics,
that every runtime dependency was declared, or that an Agent applied an opinion.
The workbench and request helpers never execute the recorded source scripts.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

MAX_FILE_BYTES = 32 * 1024 * 1024
EXPORT_NAMES = {"panel.svg", "panel.pdf", "panel.png", "panel.tiff"}
SOURCE_FIELDS = ("data_file", "source_script", "spec_file")


class HandoffError(ValueError):
    """A receipt or declared source file cannot establish current provenance."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      allow_nan=False, separators=(",", ":")).encode()


def regular_bytes(path):
    path = Path(path).expanduser()
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise HandoffError(f"A bounded, regular absolute source file is required: {path}")
    return path.read_bytes()


def normalize_inputs(info, root):
    """Keep every declared auxiliary input, resolving only explicit local paths."""
    if not isinstance(info, dict):
        raise HandoffError("Source input bindings must be an object")
    result = dict(info)

    def location(value):
        if not isinstance(value, str) or not value.strip():
            raise HandoffError("A source path must be a nonempty string")
        path = Path(value).expanduser()
        if not path.is_absolute():
            if ".." in path.parts:
                raise HandoffError("Relative source paths must remain inside the figure directory")
            path = Path(root) / path
        return str(path.absolute())

    for field in SOURCE_FIELDS:
        if info.get(field) is not None:
            result[field] = location(info[field])
    merged = {}
    for name in ("auxiliary_inputs", "aligned_layer_inputs"):
        if name not in info:
            continue
        entries = info[name]
        if not isinstance(entries, dict) or len(entries) > 100:
            raise HandoffError("Auxiliary source bindings must be a bounded object")
        for role, record in entries.items():
            if not isinstance(role, str) or not role.strip() or len(role) > 200 or not isinstance(record, dict):
                raise HandoffError("Auxiliary inputs require named path/hash records")
            expected = record.get("sha256")
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise HandoffError("Every declared auxiliary input requires its SHA256 binding")
            normalized = {**record, "path": location(record.get("path"))}
            if role in merged and merged[role] != normalized:
                raise HandoffError("Auxiliary source declarations disagree")
            merged[role] = normalized
    if merged or any(name in info for name in ("auxiliary_inputs", "aligned_layer_inputs")):
        result["auxiliary_inputs"] = merged
        if "aligned_layer_inputs" in info:
            result["aligned_layer_inputs"] = merged.copy()
    return result


def auxiliary_identity(info):
    """Paths can be rebound on restore; literal roles and input bytes cannot."""
    return {role: record["sha256"] for role, record in info.get("auxiliary_inputs", {}).items()}


def bound_version(version, info):
    result = dict(version)
    auxiliary = auxiliary_identity(info)
    if "auxiliary_inputs_sha256" in result and "auxiliary_inputs" not in info:
        raise HandoffError("Auxiliary-input version requires complete declared source bindings")
    if auxiliary or "auxiliary_inputs" in info:
        actual = digest(canonical(auxiliary))
        if "auxiliary_inputs_sha256" in result and result["auxiliary_inputs_sha256"] != actual:
            raise HandoffError("Auxiliary-input version differs from its declared source bindings")
        result["auxiliary_inputs_sha256"] = actual
    return result


def validate_receipt(record, *, root, svg_hash, panel):
    if not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("kind") != "easyviz-source-handoff":
        raise HandoffError("Unsupported custom source handoff receipt")
    version = record.get("version")
    if not isinstance(version, dict) or any(not isinstance(version.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", version[key]) for key in (
        "figure_sha256", "spec_sha256", "input_sha256", "source_script_sha256")):
        raise HandoffError("A custom handoff receipt requires complete source/spec/figure hashes")
    if version["figure_sha256"] != svg_hash:
        raise HandoffError("Custom handoff receipt belongs to a different SVG export")
    adopted = record.get("panel")
    if not isinstance(adopted, dict) or any(isinstance(adopted.get(key), bool) or not isinstance(adopted.get(key), (int, float)) or not math.isfinite(adopted[key]) or adopted[key] <= 0 or panel.get(key) is None or abs(adopted[key] - panel[key]) >= .05 for key in ("width_mm", "height_mm")):
        raise HandoffError("Custom handoff receipt dimensions differ from the actual SVG")
    info = normalize_inputs(record.get("input"), root)
    if any(not isinstance(info.get(field), str) for field in SOURCE_FIELDS) or not isinstance(info.get("supplied_spec_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", info["supplied_spec_sha256"]):
        raise HandoffError("Custom handoff receipt requires actual source/spec/data locations and hashes")
    exports = record.get("exports")
    if not isinstance(exports, dict) or "panel.svg" not in exports or not exports or set(exports) - EXPORT_NAMES:
        raise HandoffError("Custom handoff receipt requires fixed declared export hashes")
    for name, expected in exports.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or digest(regular_bytes(Path(root) / name)) != expected:
            raise HandoffError(f"Custom handoff export differs from actual {name} bytes")
    consumption = record.get("consumption")
    expected_sources = {"data_file": version["input_sha256"], "source_script": version["source_script_sha256"],
                        "spec_file": info["supplied_spec_sha256"]}
    if not isinstance(consumption, dict) or consumption.get("kind") not in {"captured-bytes-before-export", "legacy-recorded-evidence"} or consumption.get("source_sha256") != expected_sources or consumption.get("auxiliary_sha256") != auxiliary_identity(info):
        raise HandoffError("Custom source handoff requires complete matching declared consumption evidence")
    if consumption["kind"] == "legacy-recorded-evidence" and any(not isinstance(consumption.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", consumption[key]) for key in ("settings_sha256", "qa_sha256")):
        raise HandoffError("Legacy consumption evidence requires its original settings and QA identities")
    if consumption["kind"] == "legacy-recorded-evidence":
        claims = consumption.get("auxiliary_claims")
        if not isinstance(claims, dict) or set(claims) - set(auxiliary_identity(info)):
            raise HandoffError("Legacy auxiliary consumption evidence must bind declared source roles")
        for evidence in claims.values():
            if not isinstance(evidence, dict) or set(evidence) != {"path", "sha256"} or any(not isinstance(pointer, str) or not pointer.startswith("/") or len(pointer) > 2000 or any(not part or re.search(r"~(?![01])", part) for part in pointer[1:].split("/")) for pointer in evidence.values()):
                raise HandoffError("Legacy auxiliary consumption evidence requires valid explicit pointers")
    return {**record, "input": info, "version": bound_version(version, info)}


class CapturedInputs:
    """Actual byte payloads read before this fresh attempt has figure exports.

    Parse the returned data/spec/auxiliary bytes, rather than reopening sources.
    This records the caller's consumption declaration; it cannot certify that
    arbitrary plotting code used those bytes or discover undeclared imports.
    """
    def __init__(self, out, paths, raw, auxiliary):
        from types import MappingProxyType
        self.out = Path(out)
        self.paths = MappingProxyType(dict(paths))
        self.raw = MappingProxyType(dict(raw))
        self.auxiliary = MappingProxyType({role: (path, content) for role, (path, content) in auxiliary.items()})

    def read(self, field):
        return self.raw[field]

    def read_auxiliary(self, role):
        return self.auxiliary[role][1]


def _capture(data_file, source_script, spec_file, auxiliary_inputs):
    paths = {field: Path(path).expanduser().absolute() for field, path in (
        ("data_file", data_file), ("source_script", source_script), ("spec_file", spec_file))}
    raw = {field: regular_bytes(path) for field, path in paths.items()}
    if auxiliary_inputs is not None and not isinstance(auxiliary_inputs, dict):
        raise HandoffError("Auxiliary inputs must name their actual source paths")
    auxiliary = {role: (Path(path).expanduser().absolute(), regular_bytes(Path(path).expanduser().absolute()))
                 for role, path in (auxiliary_inputs or {}).items()}
    # Validate roles and bounded declarations before any export or receipt write.
    normalize_inputs({"auxiliary_inputs": {role: {"path": str(path), "sha256": digest(content)}
                      for role, (path, content) in auxiliary.items()}}, Path.cwd())
    return paths, raw, auxiliary


def capture_inputs(out, *, data_file, source_script, spec_file, auxiliary_inputs=None):
    """Read once before plotting; use these actual bytes in the plot/analysis."""
    out = Path(out).expanduser().resolve()
    if out.exists() and not out.is_dir():
        raise HandoffError("A fresh figure attempt directory is required")
    if any((out / name).exists() or (out / name).is_symlink() for name in (*EXPORT_NAMES, "handoff.json")):
        raise HandoffError("Capture source bytes before exports in a fresh attempt; existing exports need verified legacy migration or rerendering")
    paths, raw, auxiliary = _capture(data_file, source_script, spec_file, auxiliary_inputs)
    return CapturedInputs(out, paths, raw, auxiliary)


def _captured_hashes(capture):
    return {field: digest(raw) for field, raw in capture.raw.items()}


def _ensure_continuity(capture):
    for field, path in capture.paths.items():
        if regular_bytes(path) != capture.raw[field]:
            raise HandoffError("A primary source/spec/script changed after its bytes were captured")
    for path, content in capture.auxiliary.values():
        if regular_bytes(path) != content:
            raise HandoffError("A declared auxiliary input changed after its bytes were captured")


def _json_pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise HandoffError("Legacy evidence requires an explicit JSON pointer")
    current = value
    for part in pointer[1:].split("/"):
        if not part or re.search(r"~(?![01])", part):
            raise HandoffError("Invalid legacy evidence JSON pointer")
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise HandoffError("Declared legacy consumption evidence is missing")
        current = current[part]
    return current


def _settings_claims(settings, capture, *, auxiliary_claims=None, require_complete=False):
    """Check existing explicit consumption claims without guessing meanings."""
    if not isinstance(settings, dict):
        raise HandoffError("Consumed settings evidence must be an object")
    hashes = _captured_hashes(capture)
    aliases = {"data_file": (("version", "input_sha256"), ("input_sha256",)),
               "source_script": (("version", "source_script_sha256"), ("source_script_sha256",)),
               "spec_file": (("input", "supplied_spec_sha256"), ("supplied_spec_sha256",))}
    bindings = settings.get("source_bindings", {})
    if not isinstance(bindings, dict):
        raise HandoffError("Consumed source bindings must be an object")
    for field, locations in aliases.items():
        claims = []
        for parts in locations:
            value = settings
            for part in parts:
                if not isinstance(value, dict) or part not in value:
                    break
                value = value[part]
            else:
                claims.append(value)
        if field in bindings:
            record = bindings[field]
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise HandoffError("Consumed source bindings require actual path/hash records")
            claims.append(record.get("sha256"))
        if field == "spec_file" and isinstance(settings.get("spec_file"), dict):
            claims.append(settings["spec_file"].get("sha256"))
        if require_complete and not claims:
            raise HandoffError("Declared legacy consumption evidence is missing")
        if any(expected != hashes[field] for expected in claims):
            raise HandoffError("Existing consumed settings contradict captured primary source/spec/script bytes")
    for role, record in bindings.items():
        if role in SOURCE_FIELDS:
            continue
        if not isinstance(record, dict) or role not in capture.auxiliary or record.get("sha256") != digest(capture.auxiliary[role][1]):
            raise HandoffError("Existing consumed source bindings contradict or omit declared auxiliary inputs")
    records = settings.get("inputs", {})
    if not isinstance(records, dict):
        raise HandoffError("Declared consumed settings inputs must be an object")
    declared = {str(path): digest(raw) for path, raw in capture.auxiliary.values()}
    declared[str(capture.paths["data_file"])] = hashes["data_file"]
    for record in records.values():
        if not isinstance(record, dict) or not isinstance(record.get("path"), str) or record.get("sha256") != declared.get(record["path"]):
            raise HandoffError("Existing consumed settings contradict or omit declared auxiliary inputs")
    explicit = auxiliary_claims or {}
    if not isinstance(explicit, dict) or set(explicit) - set(capture.auxiliary):
        raise HandoffError("Legacy auxiliary evidence must bind actual declared roles")
    claimed_paths = set()
    for role, evidence in explicit.items():
        if not isinstance(evidence, dict) or set(evidence) != {"path", "sha256"}:
            raise HandoffError("Legacy auxiliary evidence requires explicit path and hash pointers")
        recorded_path = _json_pointer(settings, evidence["path"])
        expected = _json_pointer(settings, evidence["sha256"])
        if not isinstance(recorded_path, str) or expected != digest(capture.auxiliary[role][1]):
            raise HandoffError("Legacy consumed auxiliary evidence contradicts actual source bytes")
        claimed_paths.add(recorded_path)
    input_info = settings.get("input", {})
    if not isinstance(input_info, dict):
        raise HandoffError("Consumed settings input evidence must be an object")
    for field, path in input_info.items():
        if field in SOURCE_FIELDS or not field.endswith("_file"):
            continue
        if not isinstance(path, str) or (path not in declared and path not in claimed_paths):
            raise HandoffError("Every declared legacy auxiliary source needs explicit consumption evidence")
        # The paired legacy fields explicitly record a file/hash claim. This
        # naming convention supplies evidence, never a data or element meaning.
        paired_hash = settings.get("version", {}).get(field[:-5] + "_sha256")
        if path in declared and paired_hash is not None and paired_hash != declared[path]:
            raise HandoffError("Existing consumed settings contradict captured auxiliary source bytes")
    for name in ("auxiliary_inputs", "aligned_layer_inputs"):
        if name in input_info:
            normalized = normalize_inputs({name: input_info[name]}, capture.out)
            for role, record in normalized["auxiliary_inputs"].items():
                if role not in capture.auxiliary or record["path"] != str(capture.auxiliary[role][0]) or record["sha256"] != digest(capture.auxiliary[role][1]):
                    raise HandoffError("Existing consumed settings contradict or omit declared auxiliary inputs")
    if require_complete:
        for role, (path, raw) in capture.auxiliary.items():
            if role not in explicit and not any(isinstance(record, dict) and record.get("path") == str(path)
                                              and record.get("sha256") == digest(raw) for record in records.values()):
                raise HandoffError("Legacy migration requires complete consumed evidence for every auxiliary role")


def _adopted_claims(settings, qa, manifest, adopted, *, legacy_override=False):
    expected = digest(canonical(adopted))
    claims = []
    for record in (settings, qa, manifest):
        if not isinstance(record, dict):
            raise HandoffError("Existing source/export evidence must be an object")
        version = record.get("version", {})
        if isinstance(version, dict) and "spec_sha256" in version:
            claims.append(version["spec_sha256"])
        for key in ("resolved_spec_sha256", "spec_sha256"):
            if key in record:
                claims.append(record[key])
    if isinstance(settings.get("spec"), dict):
        claims.append(digest(canonical(settings["spec"])))
    if any(value != expected for value in claims):
        raise HandoffError("Existing adopted specification evidence contradicts the proposed source handoff")
    if legacy_override and not claims:
        raise HandoffError("Legacy resolved-spec migration requires original adopted specification evidence")


def write_receipt(out, *, capture, formats, resolved_spec=None, track=None):
    """Bind final exports to the declared byte capture used before plotting."""
    if not isinstance(capture, CapturedInputs) or Path(out).expanduser().resolve() != capture.out:
        raise HandoffError("A matching pre-export source-byte capture is required")
    _ensure_continuity(capture)
    proof = {"kind": "captured-bytes-before-export", "source_sha256": _captured_hashes(capture),
             "auxiliary_sha256": {role: digest(raw) for role, (_, raw) in capture.auxiliary.items()}}
    return _write_receipt(out, capture=capture, formats=formats, resolved_spec=resolved_spec,
                          track=track, consumption=proof)


def migrate_receipt(out, *, data_file, source_script, spec_file, formats,
                    auxiliary_inputs=None, auxiliary_claims=None, resolved_spec=None, track=None):
    """Explicitly validate complete legacy consumed settings and export evidence.

    This is migration of existing claims, never a new claim that old outputs
    consumed newly read inputs. Missing/ambiguous original claims require a fresh
    rerender with capture_inputs; unverified figures can still collect notes.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from figure_workbench import safe_json
    out = Path(out).expanduser().resolve()
    if not isinstance(formats, (list, tuple)) or not formats or "svg" not in formats or len(set(formats)) != len(formats) or any("panel." + str(value) not in EXPORT_NAMES for value in formats):
        raise HandoffError("Declare distinct exported svg/pdf/png/tiff formats, including svg")
    paths, raw, auxiliary = _capture(data_file, source_script, spec_file, auxiliary_inputs)
    capture = CapturedInputs(out, paths, raw, auxiliary)
    settings_bytes = regular_bytes(out / "settings.json")
    qa_bytes = regular_bytes(out / "qa.json")
    settings, qa = safe_json(settings_bytes), safe_json(qa_bytes)
    _settings_claims(settings, capture, auxiliary_claims=auxiliary_claims, require_complete=True)
    _settings_claims(qa, capture)
    manifest_path = out / "elements.json"
    manifest = safe_json(regular_bytes(manifest_path)) if manifest_path.exists() else {}
    adopted = safe_json(raw["spec_file"]) if resolved_spec is None else resolved_spec
    _adopted_claims(settings, qa, manifest, adopted, legacy_override=resolved_spec is not None)
    if not isinstance(qa, dict) or qa.get("status") != "pass" or qa.get("valid_outputs") is not True:
        raise HandoffError("Legacy migration requires passing actual export evidence")
    exports = qa.get("exports")
    if not isinstance(exports, dict):
        raise HandoffError("Legacy migration requires complete matching actual export hashes")
    for extension in formats:
        record = exports.get(extension)
        if not isinstance(record, dict) or record.get("sha256") != digest(regular_bytes(out / ("panel." + extension))):
            raise HandoffError("Legacy migration requires complete matching actual export hashes")
    proof = {"kind": "legacy-recorded-evidence", "source_sha256": _captured_hashes(capture),
             "auxiliary_sha256": {role: digest(raw) for role, (_, raw) in auxiliary.items()},
             "settings_sha256": digest(settings_bytes), "qa_sha256": digest(qa_bytes),
             "auxiliary_claims": auxiliary_claims or {}}
    _ensure_continuity(capture)
    return _write_receipt(out, capture=capture, formats=formats, resolved_spec=resolved_spec,
                          track=track, consumption=proof, auxiliary_claims=auxiliary_claims)


def _write_receipt(out, *, capture, formats, resolved_spec=None, track=None, consumption, auxiliary_claims=None):
    """Call after final exports; declare every consumed auxiliary input explicitly."""
    # Imported lazily: figure_workbench can read receipts without an import cycle.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from figure_workbench import read_svg, safe_json
    out = Path(out).expanduser().resolve()
    if not out.is_dir():
        raise HandoffError("The final figure export directory must already exist")
    if not isinstance(formats, (list, tuple)) or not formats or "svg" not in formats or len(set(formats)) != len(formats) or any("panel." + str(value) not in EXPORT_NAMES for value in formats):
        raise HandoffError("Declare distinct exported svg/pdf/png/tiff formats, including svg")
    if track not in (None, "create", "reproduce"):
        raise HandoffError("Track must be explicitly create or reproduce")
    paths, raw = capture.paths, capture.raw
    settings_path = out / "settings.json"
    if settings_path.exists() or settings_path.is_symlink():
        _settings_claims(safe_json(regular_bytes(settings_path)), capture, auxiliary_claims=auxiliary_claims)
    supplied = safe_json(raw["spec_file"])
    adopted = supplied if resolved_spec is None else resolved_spec
    if not isinstance(supplied, dict) or not isinstance(adopted, dict):
        raise HandoffError("Supplied and adopted specifications must be objects")
    existing = {}
    for name in ("settings.json", "qa.json", "elements.json"):
        path = out / name
        existing[name] = safe_json(regular_bytes(path)) if path.exists() else {}
    _settings_claims(existing["qa.json"], capture)
    _adopted_claims(existing["settings.json"], existing["qa.json"], existing["elements.json"], adopted)
    exports = {"panel." + extension: digest(regular_bytes(out / ("panel." + extension))) for extension in formats}
    _, _, panel = read_svg(regular_bytes(out / "panel.svg"))
    if any(panel.get(key) is None for key in ("width_mm", "height_mm")):
        raise HandoffError("A custom source handoff requires physical SVG dimensions")
    layout = adopted.get("layout", {})
    if isinstance(layout, dict):
        for key in ("width_mm", "height_mm"):
            if key in layout and (isinstance(layout[key], bool) or not isinstance(layout[key], (int, float))
                                  or not math.isfinite(layout[key]) or layout[key] <= 0
                                  or abs(layout[key] - panel[key]) >= .05):
                raise HandoffError("Adopted specification dimensions differ from the actual SVG export")
    info = {field: str(path) for field, path in paths.items()}
    info["supplied_spec_sha256"] = digest(raw["spec_file"])
    if capture.auxiliary:
        info["auxiliary_inputs"] = {role: {"path": str(path), "sha256": digest(content)}
                                    for role, (path, content) in capture.auxiliary.items()}
    info = normalize_inputs(info, out)
    version = bound_version({"figure_sha256": exports["panel.svg"], "spec_sha256": digest(canonical(adopted)),
                             "input_sha256": digest(raw["data_file"]), "source_script_sha256": digest(raw["source_script"])}, info)
    receipt = {"schema_version": 1, "kind": "easyviz-source-handoff", "version": version,
               "panel": panel, "input": info, "exports": exports, "track": track, "consumption": consumption,
               "scope": "Explicit source files and actual export bytes. No element identities are inferred; aesthetics and undeclared dependencies are not verified."}
    validate_receipt(receipt, root=out, svg_hash=version["figure_sha256"], panel=panel)
    target = out / "handoff.json"
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise HandoffError("A source handoff receipt must be a regular local file")
    _ensure_continuity(capture)
    # Publish one complete receipt so an open workbench cannot read a partial JSON.
    import os
    import tempfile
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".handoff-", suffix=".json", dir=out, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return receipt
