#!/usr/bin/env python3
"""Audit recorded reproduction coverage, source fidelity and SVG bindings.

The tool does not read figure semantics, execute plotting code, establish a
statistical method, or certify visual quality. Complex plans can opt into its
small audit contract; ordinary figures need no new serialization workflow.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

try:
    from reference_packet import PacketError, _load_json, validate_reading
except ImportError:  # Importlib callers may not have the sibling directory on sys.path.
    import importlib.util
    _loader = importlib.util.spec_from_file_location("easyviz_packet", Path(__file__).with_name("reference_packet.py"))
    _packet = importlib.util.module_from_spec(_loader)
    _loader.loader.exec_module(_packet)
    PacketError, _load_json, validate_reading = _packet.PacketError, _packet._load_json, _packet.validate_reading


HASH = re.compile(r"^[0-9a-f]{64}$")
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
MAX_BYTES = 25 * 1024 * 1024
MAX_ROWS = 100_000


def describe_contract():
    return {
        "audit_version": 1,
        "layer": {
            "source_layer_id": "Exact ID from the saved reading; cover every reading layer once.",
            "status": ["implemented", "adapted", "omitted", "unresolved"],
            "adoption": {"decision": ["preserve", "adapt", "omit", "unresolved"], "priority": ["required", "preferred", "flexible"], "reason": "Nonempty reason; required omissions remain incomplete."},
            "field_mapping": {"x": {"artifact": "data-1", "field": "time", "unit": "h"}},
            "transform": "Explicit transformation/missingness policy, or 'none'; the tool does not certify it.",
            "artist": "Actual primitive, e.g. line and uncertainty band.",
            "backend": "Drawing call and coordinate space, e.g. matplotlib Axes.plot in data coordinates.",
            "verification": [{"kind": "numeric", "source_artifact": "data-1", "source_keys": ["id"], "source_fields": ["mean"], "target": "output/artist-values.csv", "target_sha256": "EXACT_HASH", "target_keys": ["id"], "target_fields": ["artist_y"], "atol": 1e-12}],
        },
        "audit": {
            "version": 1,
            "script": {"path": "implementation/panel.py", "sha256": "EXACT_HASH"},
            "outputs": [{"format": "svg", "path": "output/panel.svg", "sha256": "EXACT_HASH"}, {"format": "pdf", "path": "output/panel.pdf", "sha256": "EXACT_HASH"}, {"format": "png", "path": "output/panel.png", "sha256": "EXACT_HASH"}],
            "axes": [{"id": "main-x", "dimension": "x", "scale": "linear", "unit": "h", "domain": [0, 6], "plot_box_svg_id": "main-plot-box", "shared_with": []}],
            "joins": [{"id": "metadata", "left": {"artifact": "data-1", "keys": ["id"]}, "right": {"artifact": "data-2", "keys": ["id"]}, "cardinality": "many-to-one", "coverage": "left"}],
            "guides": [{"id": "group-color", "kind": "categorical", "svg_ids": ["group-legend"], "meaning": "Condition color", "mapping": {"Control": "#2581B9", "Treatment": "#DF9A3C"}}],
            "bindings": [{"layer": "points", "svg_ids": ["raw-points"], "axes": ["main-x"], "joins": [], "guides": ["group-color"]}],
        },
        "verification_kinds": {
            "numeric": "One-to-one keyed numeric values; identical key sets, finite values, absolute tolerance. No unrecorded aggregation.",
            "records": "One-to-one keyed literal fields; identical key sets and exact string values, preserving IDs such as 001/NA.",
            "bounds": "A hashed target CSV plus keys and fields=[lower,center,upper]; finite values and lower <= center <= upper.",
            "svg-presence": "For a nonnumeric guide/annotation, svg_ids must exist and belong to that layer's binding; this establishes presence only.",
        },
        "guide_mappings": {
            "categorical": "Nonempty category -> color/style string mapping.",
            "continuous": {"domain": [0, 1], "colors": ["#FFFFFF", "#2581B9"], "unit": "score"},
            "area": {"domain": [0, 1], "area_pt2": [0, 100], "unit": "fraction", "relation": "linear-area"},
        },
        "geometry": "For shared axes, set the axes patch gid to plot_box_svg_id. A rect or untransformed rectangular M/L SVG path is measured in final-canvas mm. Shared x compares actual left/width; shared y compares top/height. Unsupported geometry is missing evidence, never guessed.",
        "limits": "Hashes and IDs bind recorded evidence to files. Numeric checks compare source and recorded artist tables, not pixels. A mapping declaration does not prove the script used it. Reader independence, semantic/scientific correctness and visual quality remain unverified.",
    }


class Audit:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors, self.missing, self.checks = [], [], []
        self.tables = {}

    def issue(self, code, message, *, missing=False):
        (self.missing if missing else self.errors).append({"code": code, "message": message})

    def file(self, relative):
        if not isinstance(relative, str) or not relative.strip():
            raise PacketError("File paths must be nonempty relative paths inside the packet")
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise PacketError(f"Path escapes packet: {relative}")
        path = self.root / candidate
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != self.root and self.root in parent.parents):
            raise PacketError(f"Symlink evidence is unsupported: {relative}")
        resolved = path.resolve()
        if self.root not in resolved.parents or not resolved.is_file():
            raise PacketError(f"Evidence is not a regular packet file: {relative}")
        if resolved.stat().st_size > MAX_BYTES:
            raise PacketError(f"Evidence exceeds {MAX_BYTES} bytes: {relative}")
        return resolved

    def hashed(self, item, label):
        if not isinstance(item, dict) or not HASH.fullmatch(str(item.get("sha256", ""))):
            self.issue("missing-hash", f"{label} needs path and exact lowercase SHA-256", missing=True)
            return None
        path = self.file(item.get("path"))
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != item["sha256"]:
            self.issue("hash-mismatch", f"{label} differs from its recorded hash: {item['path']}")
            return None
        if "bytes" in item and (type(item["bytes"]) is not int or item["bytes"] != path.stat().st_size):
            self.issue("size-mismatch", f"{label} differs from its recorded byte count")
        self.checks.append({"kind": "hash", "file": item["path"], "sha256": actual})
        return path

    def table(self, path):
        path = Path(path)
        if path not in self.tables:
            if path.suffix.lower() not in {".csv", ".tsv"}:
                raise PacketError(f"Tabular checks support explicit UTF-8 CSV/TSV, not {path.suffix}; stage a provenance-recorded CSV for this audit")
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, delimiter="\t" if path.suffix.lower() == ".tsv" else ",")
                fields = reader.fieldnames
                if not fields or len(fields) != len(set(fields)) or any(not value for value in fields):
                    raise PacketError(f"CSV fields must be nonempty and unique: {path.name}")
                rows = []
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise PacketError(f"Ragged CSV row: {path.name}")
                    rows.append(row)
                    if len(rows) > MAX_ROWS:
                        raise PacketError(f"CSV exceeds {MAX_ROWS} parsed records: {path.name}")
                self.tables[path] = (fields, rows)
        return self.tables[path]

    def index(self, path, keys, label, *, unique=True):
        fields, rows = self.table(path)
        if not isinstance(keys, list) or not keys or not all(isinstance(key, str) and key in fields for key in keys) or len(set(keys)) != len(keys):
            raise PacketError(f"{label} keys must name unique existing CSV fields")
        indexed = {}
        for row in rows:
            identity = tuple(row[key] for key in keys)
            if any(not value.strip() or value != value.strip() for value in identity):
                raise PacketError(f"{label} has empty or padded join/record keys; resolve them explicitly")
            if unique and identity in indexed:
                raise PacketError(f"{label} has duplicate record keys: {identity}")
            indexed.setdefault(identity, []).append(row)
        return fields, rows, indexed

    def numeric(self, value, label):
        try:
            number = Decimal(value)
        except (TypeError, ValueError, InvalidOperation):
            raise PacketError(f"{label} must be numeric") from None
        if not number.is_finite():
            raise PacketError(f"{label} must be finite")
        return number

    def within_tolerance(self, left, right, tolerance):
        # Parse original numeric strings and subtract with enough precision for
        # their full exponent span; binary floats conflate integers above 2**53.
        values = (left, right, Decimal(str(tolerance)))
        precision = max(value.adjusted() for value in values) - min(value.as_tuple().exponent for value in values) + 3
        if precision > 10_000:
            raise PacketError("Numeric exponent/precision span exceeds the 10,000-digit audit bound")
        with localcontext() as context:
            context.prec = max(28, precision)
            return abs(left - right) <= values[2]


def _identified(items, key, label):
    if not isinstance(items, list):
        raise PacketError(f"{label} must be a list")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip() or item[key] in result:
            raise PacketError(f"{label} needs nonempty unique {key} values")
        result[item[key]] = item
    return result


def _list(value, label):
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value) or len(value) != len(set(value)):
        raise PacketError(f"{label} must contain unique nonempty strings")
    return value


def _choice(value, options):
    return isinstance(value, str) and value in options


def _number(value, label):
    try:
        finite = type(value) in {int, float} and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise PacketError(f"{label} must be a finite JSON number")
    return value


def _range(value, label, *, nonnegative=False, increasing=True):
    if not isinstance(value, list) or len(value) != 2:
        raise PacketError(f"{label} must be a two-number domain")
    low, high = (_number(item, label) for item in value)
    if (increasing and low >= high) or (nonnegative and low < 0):
        raise PacketError(f"{label} has invalid ordered bounds")
    return low, high


def _svg(path):
    text = path.read_text(encoding="utf-8")
    if "<!ENTITY" in text.upper():
        raise PacketError("SVG entity declarations are unsupported")
    root = ET.fromstring(text)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise PacketError("Recorded SVG output is not an SVG document")
    nodes = {}
    for node in root.iter():
        identity = node.get("id")
        if identity is not None:
            if identity in nodes:
                raise PacketError(f"SVG contains duplicate ID: {identity}")
            nodes[identity] = node
    parents = {child: parent for parent in root.iter() for child in parent}
    return root, nodes, parents


def _svg_mm(value):
    match = re.fullmatch(r"\s*(" + NUMBER + r")\s*(mm|cm|in|pt|px)\s*", value or "")
    if match is None:
        raise PacketError("SVG physical dimensions require explicit mm/cm/in/pt/px units")
    result = float(match[1]) * {"mm": 1, "cm": 10, "in": 25.4, "pt": 25.4 / 72, "px": 25.4 / 96}[match[2]]
    if not math.isfinite(result) or result <= 0:
        raise PacketError("SVG physical dimensions must be finite and positive")
    return result


def _plot_box(root, node, parents, width_mm, height_mm):
    """Measure a deliberately bound rectangular axes patch, never a generic bbox."""
    current = node
    while current is not None:
        tag = current.tag.rsplit("}", 1)[-1]
        if current.get("transform") or re.search(r"(?:^|;)\s*transform\s*:", current.get("style", ""), re.I):
            raise PacketError("Transformed SVG plot boxes need an explicit geometry verifier")
        if tag in {"defs", "symbol", "marker"} or (tag == "svg" and current is not root):
            raise PacketError("Nested SVG viewports or definition-only plot boxes need an explicit geometry verifier")
        current = parents.get(current)
    shapes = [child for child in node.iter() if child.tag.rsplit("}", 1)[-1] in {"rect", "path"}]
    if len(shapes) != 1 or shapes[0].get("transform"):
        raise PacketError("Plot box must bind exactly one untransformed rectangle/path")
    shape = shapes[0]
    # Intermediate descendant groups can transform the rectangle even when its
    # bound outer group and the rectangle itself have no transform attribute.
    current = shape
    while current is not node:
        tag = current.tag.rsplit("}", 1)[-1]
        if current.get("transform") or re.search(r"(?:^|;)\s*transform\s*:", current.get("style", ""), re.I):
            raise PacketError("Transformed SVG plot boxes need an explicit geometry verifier")
        if tag in {"svg", "defs", "symbol", "marker"}:
            raise PacketError("Nested SVG viewports or definition-only plot boxes need an explicit geometry verifier")
        current = parents.get(current)
    if any(child.tag.rsplit("}", 1)[-1] == "style" and re.search(r"\btransform\s*:", child.text or "", re.I) for child in root.iter()):
        raise PacketError("SVG stylesheet transforms need an explicit geometry verifier")
    if shape.tag.rsplit("}", 1)[-1] == "rect":
        x, y, w, h = (float(shape.get(key, "0")) for key in ("x", "y", "width", "height"))
        if w <= 0 or h <= 0:
            raise PacketError("SVG rectangle width and height must be positive")
        points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    else:
        commands = re.findall(r"([ML])\s*(" + NUMBER + r")[,\s]+(" + NUMBER + r")", shape.get("d", ""))
        residue = re.sub(r"([ML])\s*(" + NUMBER + r")[,\s]+(" + NUMBER + r")", "", shape.get("d", ""))
        if residue.strip() not in {"z", "Z"} or len(commands) not in {4, 5} or commands[0][0] != "M" or any(cmd != "L" for cmd, _, _ in commands[1:]):
            raise PacketError("Plot box path must be a closed M/L rectangle")
        points = [(float(x), float(y)) for _, x, y in commands]
        if len(points) == 5:
            if points[-1] != points[0]:
                raise PacketError("Plot box closing vertex differs")
            points.pop()
    if any(not math.isfinite(value) for point in points for value in point):
        raise PacketError("Plot box has non-finite geometry")
    xs, ys = {point[0] for point in points}, {point[1] for point in points}
    if len(xs) != 2 or len(ys) != 2 or set(points) != {(x, y) for x in xs for y in ys}:
        raise PacketError("Plot box is not an axis-aligned rectangle")
    if any(a[0] != b[0] and a[1] != b[1] for a, b in zip(points, points[1:] + points[:1])):
        raise PacketError("Plot box path crosses its rectangle")
    view = [float(value) for value in root.get("viewBox", "").replace(",", " ").split()]
    if len(view) != 4 or not all(math.isfinite(value) for value in view) or view[2] <= 0 or view[3] <= 0:
        raise PacketError("SVG requires a finite positive viewBox")
    if root.get("preserveAspectRatio", "xMidYMid meet").strip() != "none" and not math.isclose(width_mm / view[2], height_mm / view[3], rel_tol=1e-9):
        raise PacketError("Letterboxed SVG viewports need an explicit geometry verifier")
    return [(min(xs) - view[0]) * width_mm / view[2], (min(ys) - view[1]) * height_mm / view[3], (max(xs) - min(xs)) * width_mm / view[2], (max(ys) - min(ys)) * height_mm / view[3]]


def _verify(check, audit, data):
    if not isinstance(check, dict):
        raise PacketError("Layer verification entries must be objects")
    kind = check.get("kind")
    if kind == "svg-presence":
        # Checked against the actual SVG after file binding, not against a note.
        _list(check.get("svg_ids"), "verification.svg_ids")
        return
    if not _choice(kind, {"numeric", "records", "bounds"}):
        audit.issue("unexecuted-check", f"Verification kind {kind!r} is a recorded note, not an executed numeric/record/bounds check", missing=True)
        return
    target = audit.hashed({"path": check.get("target"), "sha256": check.get("target_sha256")}, "verification target")
    if target is None:
        return
    target_fields, target_rows, target_index = audit.index(target, check.get("target_keys"), "target")
    fields = check.get("target_fields")
    if not isinstance(fields, list) or not fields or not all(isinstance(field, str) and field in target_fields for field in fields) or len(set(fields)) != len(fields):
        raise PacketError("target_fields must name unique existing CSV fields")
    if kind == "bounds":
        if len(fields) != 3:
            raise PacketError("bounds target_fields must be [lower,center,upper]")
        if not target_rows:
            raise PacketError("bounds needs actual interval records")
        for row in target_rows:
            low, center, high = (audit.numeric(row[field], field) for field in fields)
            if not low <= center <= high:
                audit.issue("interval-order", f"Interval does not satisfy lower <= center <= upper at {tuple(row[key] for key in check['target_keys'])}")
        audit.checks.append({"kind": "bounds", "target": check["target"], "records": len(target_rows)})
        return
    identity = check.get("source_artifact")
    if not isinstance(identity, str) or identity not in data:
        raise PacketError(f"Verification source is not staged user data: {identity}")
    source_fields, source_rows, source_index = audit.index(data[identity], check.get("source_keys"), "source")
    selected = check.get("source_fields")
    if not isinstance(selected, list) or len(selected) != len(fields) or not all(isinstance(field, str) and field in source_fields for field in selected) or len(set(selected)) != len(selected):
        raise PacketError("source_fields must name unique existing fields and match target_fields length")
    if not source_rows or not target_rows:
        audit.issue("empty-record-evidence", f"{identity} -> {check['target']} has no records to verify", missing=True)
    if set(source_index) != set(target_index):
        audit.issue("record-set-mismatch", f"{identity} -> {check['target']} has {len(set(source_index) - set(target_index))} missing and {len(set(target_index) - set(source_index))} extra keys")
    tolerance = _number(check.get("atol", 0), "atol")
    if tolerance < 0:
        raise PacketError("atol must be nonnegative")
    mismatches = 0
    for key in set(source_index) & set(target_index):
        original, rendered = source_index[key][0], target_index[key][0]
        for left, right in zip(selected, fields):
            if kind == "numeric":
                matches = audit.within_tolerance(audit.numeric(original[left], left), audit.numeric(rendered[right], right), tolerance)
            else:
                matches = original[left] == rendered[right]
            mismatches += not matches
    if mismatches:
        audit.issue("numeric-mismatch" if kind == "numeric" else "literal-mismatch", f"{identity} -> {check['target']}: {mismatches} field values differ")
    audit.checks.append({"kind": kind, "source": identity, "target": check["target"], "source_records": len(source_rows), "target_records": len(target_rows), "compared_fields": len(fields), "absolute_tolerance": tolerance if kind == "numeric" else None})


def audit_plan(packet_dir, plan_path=None):
    audit = Audit(packet_dir)
    manifest_path = audit.file("packet.json")
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("track") != "reproduce" or type(manifest.get("version")) is not int or manifest.get("version") != 1:
        raise PacketError("Expected a version 1 reproduce packet")
    artifacts = _identified(manifest.get("artifacts"), "id", "packet artifacts")
    if "reference" not in artifacts:
        raise PacketError("Packet must identify its reference artifact")
    data = {}
    for identity, artifact in artifacts.items():
        path = audit.hashed(artifact, identity)
        if path is not None and identity.startswith("data-"):
            data[identity] = path
    if "reading" not in artifacts:
        audit.issue("missing-reading", "Packet needs a saved image reading before adoption can be checked", missing=True)
        reading = {"evidence": [], "layers": []}
    else:
        reading = _load_json(audit.file(artifacts["reading"]["path"]))
        validate_reading(reading, artifacts["reference"]["sha256"], {key for key in artifacts if key == "reference" or key.startswith(("caption-", "methods-"))})
    plan_path = Path(plan_path).resolve() if plan_path is not None else audit.file(manifest.get("plan"))
    if not plan_path.is_file() or plan_path.stat().st_size > MAX_BYTES:
        raise PacketError("Plan must be an accessible JSON file within the size limit")
    plan = _load_json(plan_path)
    if not isinstance(plan, dict) or plan.get("track") != "reproduce" or type(plan.get("version")) is not int or plan.get("version") != 1:
        raise PacketError("Expected a version 1 reproduce implementation plan")
    source_layers = _identified(reading["layers"], "id", "reading layers")
    if not source_layers:
        audit.issue("missing-layer-reading", "Saved reading contains no material layer evidence", missing=True)
    layers = _identified(plan.get("layers"), "source_layer_id", "plan layers")
    if set(source_layers) != set(layers):
        audit.issue("layer-coverage", f"Plan must preserve all reading layers: missing={sorted(set(source_layers) - set(layers))}, untraced={sorted(set(layers) - set(source_layers))}")
    active = {}
    for identity, layer in layers.items():
        if identity in source_layers and layer.get("evidence_ids") != source_layers[identity]["evidence_ids"]:
            audit.issue("layer-evidence-changed", f"{identity} must retain the saved reading's evidence IDs")
        adoption = layer.get("adoption")
        if not isinstance(adoption, dict) or not _choice(adoption.get("priority"), {"required", "preferred", "flexible"}) or not isinstance(adoption.get("reason"), str) or not adoption["reason"].strip():
            audit.issue("missing-adoption", f"{identity} needs adoption priority and reason", missing=True)
            continue
        status, decision = layer.get("status"), adoption.get("decision")
        expected = {"implemented": "preserve", "adapted": "adapt", "omitted": "omit", "unresolved": "unresolved"}
        if not isinstance(status, str) or status not in expected or decision != expected[status]:
            audit.issue("adoption-status", f"{identity} status and adoption decision must agree")
            continue
        if status == "unresolved" or (status == "omitted" and adoption["priority"] == "required"):
            audit.issue("unresolved-layer", f"{identity} is unresolved or omits a required layer", missing=True)
            continue
        if status == "omitted":
            audit.checks.append({"kind": "intentional-omission", "layer": identity, "reason": adoption["reason"]})
            continue
        active[identity] = layer
        for name in ("transform", "artist", "backend"):
            if not isinstance(layer.get(name), str) or not layer[name].strip():
                audit.issue("missing-layer-implementation", f"{identity} needs explicit {name}", missing=True)
        used = _list(layer.get("data_artifacts"), f"{identity}.data_artifacts")
        if identity in source_layers and source_layers[identity]["required_data_meanings"] and not used:
            audit.issue("missing-layer-data", f"{identity} needs real data for the reading's declared meanings", missing=True)
        if not set(used) <= set(data):
            audit.issue("unstaged-layer-data", f"{identity} cites absent or changed staged data")
        mapping = layer.get("field_mapping")
        if not isinstance(mapping, dict) or (used and not mapping):
            audit.issue("missing-field-mapping", f"{identity} needs an actual field mapping", missing=True)
            continue
        for role, field in mapping.items():
            if not isinstance(field, dict) or field.get("artifact") not in used or not isinstance(field.get("field"), str) or not isinstance(field.get("unit"), str) or not field["unit"].strip():
                audit.issue("missing-field-meaning", f"{identity}.{role} needs artifact, field and unit (use 'category'/'dimensionless' when appropriate)", missing=True)
                continue
            if field["artifact"] in data:
                try:
                    columns, _ = audit.table(data[field["artifact"]])
                except PacketError as exc:
                    audit.issue("unsupported-table-evidence", str(exc), missing=True)
                else:
                    if field["field"] not in columns:
                        audit.issue("absent-field", f"{identity}.{role} maps a nonexistent source field")
        checks = layer.get("verification")
        if not isinstance(checks, list) or not checks:
            audit.issue("missing-layer-verification", f"{identity} needs verification evidence", missing=True)
        else:
            checked_artifacts = {check.get("source_artifact") for check in checks if isinstance(check, dict) and _choice(check.get("kind"), {"numeric", "records"}) and isinstance(check.get("source_artifact"), str)}
            if set(used) - checked_artifacts:
                audit.issue("missing-source-verification", f"{identity} needs a source-bound numeric/record check for {sorted(set(used) - checked_artifacts)}; presence/bounds alone do not verify data fidelity", missing=True)
            for check in checks:
                try:
                    _verify(check, audit, data)
                except PacketError as exc:
                    audit.issue("invalid-verification", f"{identity}: {exc}")
    contract = plan.get("audit")
    if not isinstance(contract, dict) or type(contract.get("version")) is not int or contract.get("version") != 1:
        audit.issue("missing-output-bindings", "Optional complex-plan audit block is absent/unresolved", missing=True)
    else:
        _bindings(contract, plan, active, data, audit)
    return {
        "version": 1, "track": "reproduce",
        "status": "failed" if audit.errors else "incomplete" if audit.missing else "passed-recorded-checks",
        "packet_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "errors": audit.errors, "missing_evidence": audit.missing, "checks": audit.checks,
        "reader_independence_verified": False, "semantic_correctness_verified": False,
        "visual_review_passed": False,
        "limits": ["Coverage refers to the saved reading; an unread or unreported visible layer can still be missed.", "Numeric checks compare source values with a recorded artist/derived table; they do not independently decode plotted values from pixels.", "Declared mappings, units, joins, guide relationships and domains are structurally checked; their scientific meanings and actual application by the script remain the Agent's responsibility.", "Bound rectangular SVG plot boxes support actual alignment checks; other visual geometry and aesthetics need image review."]}


def _bindings(contract, plan, active, data, audit):
    script = audit.hashed(contract.get("script"), "implementation script")
    if script is not None and script.suffix != ".py":
        audit.issue("script-type", "Implementation script must be the actual Python file")
    implementation = plan.get("implementation")
    if not isinstance(implementation, dict):
        raise PacketError("Plan implementation must be an object")
    if script is not None and implementation.get("script") != contract["script"]["path"]:
        audit.issue("script-binding", "Audit script differs from the plan's adopted implementation")
    outputs = _identified(contract.get("outputs"), "format", "audit outputs")
    if not {"svg", "pdf", "png"} <= set(outputs):
        audit.issue("missing-export", "Bind SVG, PDF and PNG from the same attempt", missing=True)
    svg = None
    for kind, item in outputs.items():
        path = audit.hashed(item, f"{kind} export")
        if path is not None:
            if path.suffix.lower() != f".{kind}":
                audit.issue("export-type", f"{kind} binding has a different filename extension")
            if kind == "svg":
                svg = _svg(path)
    if svg is None:
        return
    root, nodes, parents = svg
    layout = plan.get("layout", {})
    if not isinstance(layout, dict):
        raise PacketError("Plan layout must be an object")
    width, height = (_number(layout.get(key), key) for key in ("width_mm", "height_mm"))
    if width <= 0 or height <= 0:
        raise PacketError("Canvas dimensions must be positive")
    actual_width, actual_height = _svg_mm(root.get("width")), _svg_mm(root.get("height"))
    if abs(actual_width - width) > .01 or abs(actual_height - height) > .01:
        audit.issue("canvas-mismatch", "SVG physical size differs from the adopted layout by more than 0.01 mm")
    audit.checks.append({"kind": "svg-canvas", "width_mm": actual_width, "height_mm": actual_height})
    axes = _identified(contract.get("axes", []), "id", "axes")
    guides = _identified(contract.get("guides", []), "id", "guides")
    joins = _identified(contract.get("joins", []), "id", "joins")
    bindings = _identified(contract.get("bindings"), "layer", "layer bindings")
    if set(bindings) != set(active):
        audit.issue("binding-coverage", f"Every implemented/adapted layer needs one binding: missing={sorted(set(active) - set(bindings))}, extra={sorted(set(bindings) - set(active))}")
    for identity, binding in bindings.items():
        ids = _list(binding.get("svg_ids"), f"{identity}.svg_ids")
        if not ids or not set(ids) <= set(nodes):
            audit.issue("missing-svg-artist", f"{identity} must bind existing exported SVG IDs")
        for key, available in (("axes", axes), ("guides", guides), ("joins", joins)):
            references = _list(binding.get(key, []), f"{identity}.{key}")
            if not set(references) <= set(available):
                audit.issue("absent-layer-relationship", f"{identity} cites an undefined {key} relationship")
        if identity in active:
            for check in active[identity].get("verification", []):
                if isinstance(check, dict) and check.get("kind") == "svg-presence":
                    checked_ids = _list(check.get("svg_ids"), f"{identity}.verification.svg_ids")
                    if not checked_ids or not set(checked_ids) <= set(ids) or not set(checked_ids) <= set(nodes):
                        audit.issue("missing-svg-verification", f"{identity} presence verification must cite its existing bound SVG IDs")
                    else:
                        audit.checks.append({"kind": "svg-presence", "layer": identity, "svg_ids": checked_ids})
            for axis_id in binding.get("axes", []):
                if axis_id in axes:
                    dimension = axes[axis_id].get("dimension")
                    mapping = active[identity].get("field_mapping")
                    field = mapping.get(dimension) if isinstance(mapping, dict) and _choice(dimension, {"x", "y"}) else None
                    if isinstance(field, dict) and field.get("unit") != axes[axis_id].get("unit"):
                        audit.issue("axis-field-unit", f"{identity} field unit disagrees with bound axis {axis_id}")
    measured = {}
    for identity, axis in axes.items():
        if not _choice(axis.get("dimension"), {"x", "y"}) or not _choice(axis.get("scale"), {"linear", "log", "category"}) or not isinstance(axis.get("unit"), str) or not axis["unit"].strip():
            raise PacketError(f"{identity} needs dimension, supported scale and explicit unit")
        if axis["scale"] == "category":
            domain = _list(axis.get("domain"), f"{identity}.domain")
            if not domain:
                raise PacketError(f"{identity} needs a nonempty category domain")
        else:
            domain = _range(axis.get("domain"), f"{identity}.domain")
            if axis["scale"] == "log" and domain[0] <= 0:
                raise PacketError("Log axis domains must be positive")
        sharing = _list(axis.get("shared_with", []), f"{identity}.shared_with")
        if identity in sharing or not set(sharing) <= set(axes):
            raise PacketError(f"{identity} shared_with must name other declared axes")
        box_id = axis.get("plot_box_svg_id")
        if box_id is not None:
            if not isinstance(box_id, str) or box_id not in nodes:
                audit.issue("missing-axis-box", f"{identity} plot box ID is absent from the SVG")
            else:
                try:
                    measured[identity] = _plot_box(root, nodes[box_id], parents, actual_width, actual_height)
                except (PacketError, ValueError) as exc:
                    audit.issue("unsupported-axis-geometry", f"{identity}: {exc}", missing=True)
        elif sharing or any(identity in other.get("shared_with", []) for other in axes.values()):
            audit.issue("missing-axis-geometry", f"{identity} needs a bound SVG plot box for shared-axis alignment", missing=True)
    for identity, axis in axes.items():
        for partner_id in axis.get("shared_with", []):
            partner = axes[partner_id]
            if any(axis[key] != partner[key] for key in ("dimension", "scale", "unit", "domain")):
                audit.issue("shared-axis-mapping", f"{identity}/{partner_id} differ in dimension, scale, unit or domain")
            if identity in measured and partner_id in measured:
                indexes = (0, 2) if axis["dimension"] == "x" else (1, 3)
                if any(abs(measured[identity][index] - measured[partner_id][index]) > .01 for index in indexes):
                    audit.issue("shared-axis-alignment", f"{identity}/{partner_id} SVG plot boxes are not aligned within 0.01 mm")
                else:
                    audit.checks.append({"kind": "svg-shared-axis-alignment", "axes": [identity, partner_id], "bounds_mm": [measured[identity], measured[partner_id]], "absolute_tolerance_mm": .01})
    for identity, join in joins.items():
        if not _choice(join.get("cardinality"), {"one-to-one", "many-to-one"}) or not _choice(join.get("coverage"), {"left", "both"}):
            raise PacketError(f"{identity} needs explicit join cardinality and coverage")
        indexes = []
        descriptors = [join.get(side) for side in ("left", "right")]
        if all(isinstance(item, dict) and isinstance(item.get("keys"), list) for item in descriptors) and len(descriptors[0]["keys"]) != len(descriptors[1]["keys"]):
            raise PacketError(f"{identity} left/right key lists must have equal length")
        for side in ("left", "right"):
            descriptor = join.get(side)
            if not isinstance(descriptor, dict) or not isinstance(descriptor.get("artifact"), str) or descriptor.get("artifact") not in data:
                audit.issue("invalid-join-source", f"{identity}.{side} must name unchanged staged user data")
                break
            try:
                _, _, index = audit.index(data[descriptor["artifact"]], descriptor.get("keys"), f"{identity}.{side}", unique=side == "right" or join["cardinality"] == "one-to-one")
            except PacketError as exc:
                audit.issue("join-cardinality", f"{identity}: {exc}")
                break
            indexes.append(index)
        if len(indexes) != 2:
            continue
        left, right = map(set, indexes)
        if not left or not right:
            audit.issue("empty-join-evidence", f"{identity} has no left/right records for its declared relationship", missing=True)
        if left - right or (join["coverage"] == "both" and right - left):
            audit.issue("join-coverage", f"{identity} has {len(left - right)} unmatched left and {len(right - left)} unmatched right keys")
        audit.checks.append({"kind": "join", "id": identity, "left_unique_keys": len(left), "right_unique_keys": len(right), "cardinality": join["cardinality"], "coverage": join["coverage"]})
    for identity, guide in guides.items():
        kind, mapping = guide.get("kind"), guide.get("mapping")
        if not _choice(kind, {"categorical", "continuous", "area"}) or not isinstance(guide.get("meaning"), str) or not guide["meaning"].strip() or not isinstance(mapping, dict) or not mapping:
            raise PacketError(f"{identity} needs guide kind, meaning and explicit mapping")
        ids = _list(guide.get("svg_ids"), f"{identity}.svg_ids")
        if not ids or not set(ids) <= set(nodes):
            audit.issue("missing-svg-guide", f"{identity} must bind actual exported guide IDs")
        if kind == "categorical":
            if not all(isinstance(key, str) and key and isinstance(value, str) and value.strip() for key, value in mapping.items()):
                raise PacketError("Categorical mappings need literal categories and style values")
        else:
            _range(mapping.get("domain"), f"{identity}.domain", nonnegative=kind == "area")
            if not isinstance(mapping.get("unit"), str) or not mapping["unit"].strip():
                raise PacketError(f"{identity} needs the guide's quantitative unit")
            if kind == "area":
                _range(mapping.get("area_pt2"), f"{identity}.area_pt2", nonnegative=True)
                if mapping.get("relation") != "linear-area":
                    raise PacketError("Area guides must declare linear-area, not radius/diameter")
            else:
                colors = _list(mapping.get("colors"), f"{identity}.colors")
                if len(colors) < 2:
                    raise PacketError("Continuous guides need at least two declared colors")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-contract", action="store_true")
    parser.add_argument("--packet", type=Path, help="Existing staged packet directory")
    parser.add_argument("--plan", type=Path, help="Adopted plan; defaults to the packet's plan")
    parser.add_argument("--out", type=Path, help="New JSON audit file; existing files are preserved")
    args = parser.parse_args()
    if args.describe_contract:
        print(json.dumps(describe_contract(), indent=2))
        return
    if args.packet is None:
        parser.error("--packet is required")
    try:
        result = audit_plan(args.packet, args.plan)
        rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.out is not None:
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        print(rendered, end="")
    except (PacketError, ValueError, OSError, ET.ParseError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    if result["status"] != "passed-recorded-checks":
        parser.exit(1)


if __name__ == "__main__":
    main()
