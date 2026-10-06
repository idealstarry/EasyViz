#!/usr/bin/env python3
"""Check an adopted Reproduce plan before drawing; never certify figure quality.

This standard-library checkpoint connects the exact staged image/data to
explicit visual relationships and actionable unresolved questions. It executes
no renderer and does not change a plan, input, export or review status.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

try:
    from reference_packet import PacketError, _load_json, validate_reading
except ImportError:
    loader = importlib.util.spec_from_file_location("easyviz_reference_packet", Path(__file__).with_name("reference_packet.py"))
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    PacketError, _load_json, validate_reading = module.PacketError, module._load_json, module.validate_reading


def describe_contract():
    return {
        "version": 1,
        "location": "implementation-plan.json -> adoption_contract; keeps the existing layer plan",
        "reference_sha256": "Exact staged reference hash",
        "relationship": {
            "id": "Unique relationship ID", "property": "E.g. coordinates.shared-x, geometry.data-region-aspect or guides.group-colors",
            "evidence_ids": "Nonempty IDs from the actual reading",
            "behavior": ["preserve", "adapt", "user-change"],
            "adopted_value": "Explicit relationship to retain/change; user data need not resemble reference values",
            "rationale": "Reason for adoption or adaptation",
        },
        "open_item": {
            "evidence_id": "Every inferred/unknown reading item appears exactly once",
            "question": "Specific information missing, rather than a vague request for more context",
            "affected_layer_ids": "Exact reading layer IDs affected by this uncertainty",
            "state": ["unresolved", "resolved", "not-required"],
            "blocking": ["layer", "delivery", "none"],
            "resolution": {"source": "Staged input ID or user-decision", "description": "Supported definition, explicit adopted preference, or reason this feature is not required"},
        },
        "checks": ["staged bytes still match", "reading provenance and exact layer coverage", "adopted physical layout and implementation route", "active layer data/mapping/primitive declarations", "explicit visual relationships", "unresolved questions and required omissions"],
        "limits": "Record completeness only. Source semantics, experimental independence, statistical validity, actual artist values, export fidelity and visual quality remain separate checks. No renderer or Agent turn is started.",
    }


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _positive(value):
    return type(value) in {int, float} and math.isfinite(value) and value > 0


def _list_ids(value, label):
    if not isinstance(value, list) or any(not _text(item) for item in value) or len(set(value)) != len(value):
        raise PacketError(f"{label} must be a list of unique nonempty IDs")
    return set(value)


def _contained(root, relative):
    if not _text(relative):
        raise PacketError("Packet file needs a nonempty relative path")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise PacketError(f"Path escapes the packet: {relative}")
    candidate = root / path
    if any(part.is_symlink() for part in (candidate, *candidate.parents) if part != root and root in part.parents):
        raise PacketError(f"Symlink evidence is unsupported: {relative}")
    if root not in candidate.resolve().parents or not candidate.is_file():
        raise PacketError(f"Missing regular packet file: {relative}")
    if candidate.stat().st_size > 25 * 1024 * 1024:
        raise PacketError(f"Packet evidence exceeds 25 MiB: {relative}")
    return candidate


def check(packet_dir, plan_path=None):
    """Return safe partial-plan feedback, without mutating execution/delivery state."""
    root = Path(packet_dir).resolve()
    manifest = _load_json(_contained(root, "packet.json"))
    if not isinstance(manifest, dict) or type(manifest.get("version")) is not int or manifest["version"] != 1 or manifest.get("track") != "reproduce" or manifest.get("input_mode") != "image-data":
        raise PacketError("Checkpoint requires a version 1 Reproduce image-data packet")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise PacketError("Packet artifacts must be a list")
    by_id = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not _text(artifact.get("id")) or artifact["id"] in by_id:
            raise PacketError("Packet artifact IDs must be unique")
        file = _contained(root, artifact.get("path"))
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if artifact.get("sha256") != actual or type(artifact.get("bytes")) is not int or artifact["bytes"] != file.stat().st_size:
            raise PacketError(f"Staged input changed: {artifact['id']}")
        by_id[artifact["id"]] = artifact
    if "reference" not in by_id or "reading" not in by_id:
        raise PacketError("Adoption requires an actual saved reading; staging alone is not image inspection")
    sources = {identity for identity in by_id if identity == "reference" or identity.startswith(("caption-", "methods-"))}
    reading = validate_reading(_load_json(_contained(root, by_id["reading"]["path"])), by_id["reference"]["sha256"], sources)
    if not reading["reader"]["image_viewed"] or not reading["layers"]:
        raise PacketError("Adoption requires reported image access and at least one read layer")
    relative = manifest.get("plan", "implementation-plan.json") if plan_path is None else plan_path
    plan = _load_json(_contained(root, relative))
    return check_plan(plan, reading, by_id)


def check_plan(plan, reading, artifacts):
    """Validate declarations; callers must separately verify captured file bytes."""
    errors, blocked_layers, open_questions = [], [], []
    def error(code, message):
        errors.append({"code": code, "message": message})
    if not isinstance(plan, dict) or type(plan.get("version")) is not int or plan["version"] != 1 or plan.get("track") != "reproduce":
        raise PacketError("Plan must be a version 1 Reproduce plan")
    evidence = {item["id"]: item for item in reading["evidence"]}
    source_layers = {layer["id"]: layer for layer in reading["layers"]}
    data_ids = {identity for identity in artifacts if identity.startswith("data-")}
    declared = plan.get("layers")
    if not isinstance(declared, list):
        raise PacketError("Plan layers must be a list")
    layers = {}
    for layer in declared:
        if not isinstance(layer, dict) or not _text(layer.get("source_layer_id")) or layer["source_layer_id"] in layers:
            raise PacketError("Plan layer IDs must be unique")
        layers[layer["source_layer_id"]] = layer
    if set(layers) != set(source_layers):
        error("layer-coverage", "Keep every read layer exactly once, including intentionally omitted or unresolved layers")
    active = []
    for identity, layer in layers.items():
        if identity not in source_layers:
            continue
        cited = _list_ids(layer.get("evidence_ids"), f"{identity}.evidence_ids")
        if cited != set(source_layers[identity]["evidence_ids"]):
            error("layer-evidence", f"{identity}: preserve the reading's evidence IDs")
        adoption = layer.get("adoption", {})
        if not isinstance(adoption, dict):
            raise PacketError("Layer adoption must be an object")
        status, decision, priority = layer.get("status"), adoption.get("decision"), adoption.get("priority")
        if not _text(status) or not _text(decision) or {"implemented": "preserve", "adapted": "adapt", "omitted": "omit", "unresolved": "unresolved"}.get(status) != decision:
            error("layer-decision", f"{identity}: status and explicit adoption decision must agree")
        if not _text(priority) or priority not in {"required", "preferred", "flexible"} or not _text(adoption.get("reason")):
            error("layer-priority", f"{identity}: assign a priority and reason")
        if not _text(status):
            continue
        if status in {"omitted", "unresolved"}:
            if priority == "required":
                blocked_layers.append(identity)
            continue
        if status not in {"implemented", "adapted"}:
            continue
        active.append(identity)
        used = _list_ids(layer.get("data_artifacts"), f"{identity}.data_artifacts")
        if not used <= data_ids or (source_layers[identity]["required_data_meanings"] and not used):
            error("layer-source", f"{identity}: bind data-bearing layers to staged user data")
        if not isinstance(layer.get("field_mapping"), dict) or (source_layers[identity]["required_data_meanings"] and not layer["field_mapping"]):
            error("layer-mapping", f"{identity}: declare the actual source field mapping")
        for name in ("transform", "artist", "backend"):
            if not _text(layer.get(name)):
                error("layer-implementation", f"{identity}: declare {name}, including explicit none where applicable")
    layout = plan.get("layout", {})
    if not isinstance(layout, dict) or not all(_positive(layout.get(name)) for name in ("width_mm", "height_mm")) or not _text(layout.get("font")):
        error("physical-layout", "Adopt positive canvas mm and an explicit font; pixels do not establish physical dimensions")
    typography = layout.get("typography_pt") if isinstance(layout, dict) else None
    if not isinstance(typography, dict) or not typography or any(not _text(key) or not _positive(value) for key, value in typography.items()):
        error("typography", "Adopt explicit positive point sizes for the text roles")
    implementation = plan.get("implementation", {})
    if not isinstance(implementation, dict):
        raise PacketError("implementation must be an object")
    route = implementation.get("route")
    if route == "custom-script":
        script = implementation.get("script")
        candidate = Path(script) if _text(script) else None
        if candidate is None or candidate.is_absolute() or ".." in candidate.parts or candidate.suffix != ".py":
            error("implementation-route", "Custom implementation needs a relative .py path inside the packet")
    elif not _text(route) or route not in {"core", "recipe", "focused-recipe"} or not _text(implementation.get("recipe")):
        error("implementation-route", "Choose a supported core/recipe route or a declared custom script")
    if not _text(implementation.get("selection_reason")):
        error("implementation-reason", "Explain why the implementation supports the adopted relationships")
    contract = plan.get("adoption_contract")
    if not isinstance(contract, dict):
        raise PacketError("Plan needs adoption_contract from the current packet scaffold")
    if contract.get("reference_sha256") != reading["reference"]["sha256"]:
        error("reference-identity", "Adoption relationships must identify this exact reference image")
    relationships = contract.get("relationships")
    if not isinstance(relationships, list) or not relationships:
        error("visual-relationships", "Record at least one material geometry, coordinate or guide relationship")
        relationships = []
    seen = set()
    for relationship in relationships:
        if not isinstance(relationship, dict) or not _text(relationship.get("id")) or relationship["id"] in seen:
            raise PacketError("Relationship IDs must be unique")
        seen.add(relationship["id"])
        ids = _list_ids(relationship.get("evidence_ids"), "relationship.evidence_ids")
        if not ids or not ids <= set(evidence):
            error("relationship-evidence", "Every adopted relationship cites actual read evidence")
        if not _text(relationship.get("behavior")) or relationship["behavior"] not in {"preserve", "adapt", "user-change"} or any(not _text(relationship.get(name)) for name in ("property", "adopted_value", "rationale")):
            error("relationship-decision", "Relationships need property, behavior, adopted value and rationale")
    questions = contract.get("open_items")
    if not isinstance(questions, list):
        raise PacketError("adoption_contract.open_items must be a list")
    uncertain = {identity for identity, item in evidence.items() if item["state"] != "observed"}
    seen_questions = set()
    # The reading's own unresolved statement is not new evidence resolving it.
    allowed_sources = (set(artifacts) - {"reading"}) | {"user-decision"}
    blocked_delivery = bool(blocked_layers)
    for question in questions:
        if not isinstance(question, dict) or not _text(question.get("evidence_id")) or question["evidence_id"] not in uncertain or question["evidence_id"] in seen_questions:
            raise PacketError("Each open item must uniquely name inferred/unknown reading evidence")
        identity = question["evidence_id"]
        seen_questions.add(identity)
        affected = _list_ids(question.get("affected_layer_ids"), "open-item.affected_layer_ids")
        expected = {key for key, layer in source_layers.items() if identity in layer["evidence_ids"]}
        if affected != expected:
            error("question-layer-coverage", f"{identity}: keep all affected reading layers")
        if not _text(question.get("question")) or not _text(question.get("blocking")) or question["blocking"] not in {"layer", "delivery", "none"}:
            error("question-action", f"{identity}: specify a concrete question and blocking scope")
        state = question.get("state")
        if state == "unresolved":
            if question.get("resolution") is not None:
                error("question-resolution", f"{identity}: unresolved evidence cannot contain a completed resolution")
            if question.get("blocking") == "layer":
                for layer_id in affected & set(active):
                    error("unresolved-layer", f"{identity}: {layer_id} is active despite an unresolved layer-blocking definition")
            if question.get("blocking") == "delivery":
                blocked_delivery = True
            open_questions.append({**question, "original_evidence_state": evidence[identity]["state"]})
        elif state in {"resolved", "not-required"}:
            resolution = question.get("resolution")
            if not isinstance(resolution, dict) or not _text(resolution.get("source")) or resolution["source"] not in allowed_sources or not _text(resolution.get("description")):
                error("question-resolution", f"{identity}: name staged evidence or an explicit user decision and its meaning")
            if state == "not-required" and question.get("blocking") != "none":
                error("question-resolution", f"{identity}: not-required questions must explicitly stop blocking")
        else:
            error("question-state", f"{identity}: use unresolved, resolved or not-required")
    if seen_questions != uncertain:
        error("uncertainty-coverage", "Preserve every inferred/unknown reading item with its resolution or explicit open question")
    if not active:
        error("no-active-layers", "Adopt at least one supported layer before preparing a partial rendering")
    return {
        "version": 1, "track": "reproduce",
        "status": "needs_adoption" if errors else ("partial_adoption" if blocked_delivery or open_questions else "adoption_complete"),
        "can_render_supported_layers": bool(active) and not errors,
        "active_layers": active, "required_unresolved_or_omitted_layers": blocked_layers,
        "delivery_blocked_by_adoption": bool(errors) or blocked_delivery,
        "open_questions": open_questions, "errors": errors,
        "reader_provenance": reading["reader"],
        "ready_for_delivery": False, "visual_review_passed": False,
        "limitations": ["This checks recorded adoption, not scientific or image-reading truth.", "A partial render does not satisfy omitted or unresolved required layers.", "Actual source-to-artist values, all exports and independent visual review still need verification."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-contract", action="store_true")
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--plan", help="Relative plan path inside the packet; defaults to the manifest's plan")
    parser.add_argument("--out", type=Path, help="Optional new report file; an existing report is never replaced")
    args = parser.parse_args()
    if args.describe_contract:
        print(json.dumps(describe_contract(), indent=2)); return
    if args.packet is None:
        parser.error("--packet is required")
    try:
        report = check(args.packet, args.plan)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
                stream.write("\n")
        print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    raise SystemExit(1 if report["errors"] else 0)


if __name__ == "__main__":
    main()
