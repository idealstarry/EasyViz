#!/usr/bin/env python3
"""Stage reference-image reproduction inputs and an unresolved implementation plan.

This standard-library tool copies and hashes files. It does not inspect image
content, infer data meanings, choose statistics, or certify independent review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


VERSION = 1
STATES = {"observed", "inferred", "unknown"}
INDEPENDENCE = {"independent", "main-agent", "not-independent", "unreported"}
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class PacketError(ValueError):
    """An input or reading cannot be represented without guessing or replacing files."""


def require(condition, message):
    if not condition:
        raise PacketError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _object(value, keys, label):
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == set(keys), f"{label} must contain exactly: {', '.join(sorted(keys))}")


def _text(value, label, *, empty=False):
    require(isinstance(value, str) and (empty or bool(value.strip())), f"{label} must be a {'string' if empty else 'nonempty string'}")


def _strings(value, label):
    require(isinstance(value, list), f"{label} must be a list")
    for item in value:
        _text(item, label)


def reading_template(reference_sha256):
    return {
        "version": VERSION,
        "reader": {"agent_id": "unreported", "independence": "unreported", "image_viewed": False, "limitations": []},
        "reference": {"sha256": reference_sha256, "region": "whole supplied image; select the intended panel before reading"},
        "evidence": [], "layers": [],
    }


def describe_reading():
    return {
        "version": VERSION,
        "reader": {"agent_id": "Nonempty reader identity; provenance is self-reported.", "independence": sorted(INDEPENDENCE), "image_viewed": "Boolean: the reader actually opened this exact image.", "limitations": "List of legibility, access, and inherited-context limitations."},
        "reference": {"sha256": "SHA-256 of supplied reference bytes, not a filename or another crop.", "region": "Selected panel/region; geometry is relative to this supplied image."},
        "evidence_item": {"id": "Unique identifier, e.g. E1.", "property": "A property such as layers.points, axes.scale, or statistics.interval.", "description": "Reader observation or explicitly uncertain interpretation.", "state": sorted(STATES), "source": "reference, caption-N, methods-N, or null only for unknown evidence.", "uncertainty": "String; inferred and unknown items require a nonempty explanation."},
        "layer_item": {"id": "Unique identifier, e.g. raw-points.", "evidence_ids": "Nonempty list of existing evidence IDs.", "description": "The visible or unresolved layer; no implementation choice.", "required_data_meanings": "List of meanings needed from real user data; do not invent column names."},
        "top_level_keys": ["version", "reader", "reference", "evidence", "layers"],
        "limits": "Schema and image hash validation do not verify image interpretation or independence. No adopted decisions are inferred from a reading.",
    }


def validate_reading(reading, reference_sha256, sources):
    """Validate identity and evidence structure, never the semantic truth of a claim."""
    _object(reading, {"version", "reader", "reference", "evidence", "layers"}, "reading")
    require(type(reading["version"]) is int and reading["version"] == VERSION, "reading.version must be 1")
    reader = reading["reader"]
    _object(reader, {"agent_id", "independence", "image_viewed", "limitations"}, "reader")
    _text(reader["agent_id"], "reader.agent_id")
    require(isinstance(reader["independence"], str) and reader["independence"] in INDEPENDENCE, "Invalid reader.independence")
    require(type(reader["image_viewed"]) is bool, "reader.image_viewed must be a boolean")
    _strings(reader["limitations"], "reader.limitations")
    require(reader["independence"] != "independent" or reader["image_viewed"], "An independent image reading must report actual image access")
    _object(reading["reference"], {"sha256", "region"}, "reference")
    require(reading["reference"]["sha256"] == reference_sha256, "Reading reference.sha256 differs from the supplied image")
    _text(reading["reference"]["region"], "reference.region")

    require(isinstance(reading["evidence"], list), "evidence must be a list")
    evidence_ids = set()
    for item in reading["evidence"]:
        _object(item, {"id", "property", "description", "state", "source", "uncertainty"}, "evidence item")
        _text(item["id"], "evidence.id")
        require(bool(IDENTIFIER.fullmatch(item["id"])) and item["id"] not in evidence_ids, "Evidence IDs must be unique identifiers")
        evidence_ids.add(item["id"])
        _text(item["property"], "evidence.property")
        _text(item["description"], "evidence.description")
        require(isinstance(item["state"], str) and item["state"] in STATES, "Invalid evidence state")
        _text(item["uncertainty"], "evidence.uncertainty", empty=item["state"] == "observed")
        source = item["source"]
        require((isinstance(source, str) and source in sources) or (source is None and item["state"] == "unknown"), "Evidence source must name a staged reference/caption/methods input; null is only allowed for unknown")
        require(not (source == "reference" and item["state"] == "observed") or reader["image_viewed"], "Observed image evidence requires a reading that reports image access")

    require(isinstance(reading["layers"], list), "layers must be a list")
    layer_ids = set()
    for layer in reading["layers"]:
        _object(layer, {"id", "evidence_ids", "description", "required_data_meanings"}, "layer")
        _text(layer["id"], "layer.id")
        require(bool(IDENTIFIER.fullmatch(layer["id"])) and layer["id"] not in layer_ids, "Layer IDs must be unique identifiers")
        layer_ids.add(layer["id"])
        _strings(layer["evidence_ids"], "layer.evidence_ids")
        require(layer["evidence_ids"] and len(layer["evidence_ids"]) == len(set(layer["evidence_ids"])) and set(layer["evidence_ids"]) <= evidence_ids, "Each layer must cite unique existing evidence IDs")
        _text(layer["description"], "layer.description")
        _strings(layer["required_data_meanings"], "layer.required_data_meanings")
    return reading


def _load_json(path):
    def invalid_constant(value):
        raise PacketError(f"Non-finite JSON value: {value}")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid_constant, object_pairs_hook=unique_keys)


def implementation_plan(reading, data_ids, custom_script):
    return {
        "version": VERSION, "track": "reproduce", "input_mode": "image-data", "status": "unresolved-scaffold",
        "execution_ready": False,
        "implementation": {"route": "custom-script" if custom_script else "unresolved", "script": custom_script, "recipe": None, "selection_reason": None},
        "user_data_artifact_ids": data_ids,
        "data_mapping": {}, "statistical_layers": [],
        "layout": {"width_mm": None, "height_mm": None, "font": None, "typography_pt": {}, "legend_layout": {}},
        "colors": {}, "panel_text": {"title": "omit unless explicitly requested", "caption_file": "caption.md"},
        "evidence_decisions": [{"evidence_id": item["id"], "evidence_state": item["state"], "adopted_requirement": None, "priority": None, "rationale": None} for item in reading["evidence"]],
        "layers": [{"source_layer_id": layer["id"], "evidence_ids": layer["evidence_ids"], "reading_description": layer["description"], "required_data_meanings": layer["required_data_meanings"], "status": "unresolved", "data_artifacts": [], "field_mapping": {}, "transform": None, "artist": None, "backend": None, "verification": [], "adoption": {"decision": None, "priority": None, "reason": None}} for layer in reading["layers"]],
        "intentional_differences": [],
        "baseline": {"script": None, "exports": [], "review": None},
        "implementation_gap_checklist": [{"item": item, "status": "unresolved", "evidence": None} for item in [
            "fresh image reading and independence provenance",
            "user field meanings, units, observation grain and missingness",
            "all visible layers mapped, intentionally adapted, or explicitly unresolved",
            "transformations, pairing, uncertainty and statistical definitions supported",
            "recipe boundaries checked; custom script used for unsupported geometry/layers",
            "agreed final canvas and typography; complete legend bounds measured",
            "source-to-artist values and counts verified without invented observations",
            "baseline compared with adaptation at the same final size",
            "PDF/SVG/PNG exported, inspected and independently reviewed where possible",
        ]],
        "limits": "Scaffold only. It is not a render.py specification, an adopted plan, or a passed review. Complete the scientific and implementation decisions explicitly.",
    }


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def build(reference, data, out, *, captions=(), methods=(), reading_path=None, custom_script=None):
    """Build a new packet with byte-identical snapshots and separate reader inputs."""
    reference, out = Path(reference).resolve(), Path(out).absolute()
    require(data, "At least one explicit user-data file is required for an image-data packet")
    require(not out.exists() and not out.is_symlink(), f"Output already exists: {out}")
    if custom_script is not None:
        require(isinstance(custom_script, str), "--custom-script must be a relative .py path inside the new packet")
        candidate = Path(custom_script)
        require(not candidate.is_absolute() and ".." not in candidate.parts and candidate.suffix == ".py", "--custom-script must be a relative .py path inside the new packet")
        require(candidate.parts and candidate.parts[0] not in {"reader-inputs", "data"}, "Custom script path cannot occupy staged input directories")

    sources = [("reference", reference, Path("reader-inputs") / f"reference{reference.suffix}")]
    for kind, paths, directory in (("caption", captions, "reader-inputs"), ("methods", methods, "reader-inputs"), ("data", data, "data")):
        for index, path in enumerate(paths, 1):
            original = Path(path).resolve()
            sources.append((f"{kind}-{index}", original, Path(directory) / f"{kind}-{index}-{original.name}"))
    if reading_path is not None:
        sources.append(("reading", Path(reading_path).resolve(), Path("reference-reading.json")))
    resolved_out = out.resolve()
    for _, source, _ in sources:
        require(source.is_file(), f"Input is not an accessible file: {source}")
        require(source != resolved_out and resolved_out not in source.parents, "Output cannot contain or replace an input")
    require(len({source for _, source, _ in sources}) == len(sources), "Supply each input file once with its correct evidence/data role")
    hashes = {identity: sha256(source) for identity, source, _ in sources}
    evidence_sources = {identity for identity, _, _ in sources if identity == "reference" or identity.startswith(("caption-", "methods-"))}
    reading = reading_template(hashes["reference"])
    if reading_path is not None:
        reading = validate_reading(_load_json(reading_path), hashes["reference"], evidence_sources)
    plan = implementation_plan(reading, [identity for identity, _, _ in sources if identity.startswith("data-")], custom_script)

    # mkdir is exclusive: existing outputs, including a raced destination, survive.
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.mkdir()
    except FileExistsError:
        raise PacketError(f"Output already exists: {out}") from None
    try:
        artifacts = []
        for identity, source, relative in sources:
            staged = out / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, staged)
            require(sha256(staged) == hashes[identity] == sha256(source), f"Input changed while staging: {source}; retry with stable files")
            artifacts.append({"id": identity, "original_path": str(source), "path": relative.as_posix(), "bytes": staged.stat().st_size, "sha256": hashes[identity]})
        _write_json(out / "reading-template.json", reading_template(hashes["reference"]))
        _write_json(out / "implementation-plan.json", plan)
        manifest = {
            "version": VERSION, "track": "reproduce", "input_mode": "image-data", "artifacts": artifacts,
            "reading": {"provided": reading_path is not None, "schema_validated": reading_path is not None, "reader_provenance": reading["reader"], "semantic_reading_verified": False, "independence_verified": False},
            "plan": "implementation-plan.json",
            "reader_input_ids": sorted(evidence_sources),
            "limitations": ["The tool stages bytes; no image semantics or statistical meanings are inspected.", "Reader separation is an input/instruction contract, not an operating-system sandbox.", "Independent reading and visual review are self-reported evidence, never certified by packet creation.", "Author code and paper Source Data are not required and are not retrieved or executed."],
        }
        _write_json(out / "packet.json", manifest)
        reader_paths = "\n".join(f"- {relative.as_posix()} ({identity})" for identity, _, relative in sources if identity in evidence_sources)
        (out / "reader-request.md").write_text(
            "# Fresh reference reading\n\nOpen the actual supplied reference image. Use only the files below and the Reference Reader instructions.\n\n"
            + reader_paths
            + "\n\nReport observed, inferred and unknown evidence in the reading-template.json structure. Record the selected panel/region and reader provenance. Do not inspect data/, neighboring project files, implementation-plan.json, prior plotting code, or author code. Do not choose a plotting recipe. The template hash identifies this exact image; it does not prove a reading occurred. If access or independence is unavailable, report it truthfully.\n", encoding="utf-8")
        return manifest
    except Exception:
        shutil.rmtree(out)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-reading", action="store_true", help="Print the structured reading contract without writing files")
    parser.add_argument("--reference", type=Path, help="Supplied reference image; this tool does not interpret its pixels")
    parser.add_argument("--data", action="append", type=Path, help="Explicit real user-data file; repeat for several files")
    parser.add_argument("--caption", action="append", default=[], type=Path, help="Supplied caption excerpt; repeat when needed")
    parser.add_argument("--methods", action="append", default=[], type=Path, help="Supplied methods excerpt; repeat when needed")
    parser.add_argument("--reading", type=Path, help="Reader-produced structured JSON matching the exact image hash")
    parser.add_argument("--custom-script", help="Planned relative .py output path for implementation beyond supported recipes; no code is run")
    parser.add_argument("--out", type=Path, help="New packet directory; never overwrite an existing directory")
    args = parser.parse_args()
    if args.describe_reading:
        print(json.dumps(describe_reading(), indent=2))
        return
    if args.reference is None or not args.data or args.out is None:
        parser.error("--reference, at least one --data and --out are required")
    try:
        manifest = build(args.reference, args.data, args.out, captions=args.caption, methods=args.methods, reading_path=args.reading, custom_script=args.custom_script)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    next_step = ("Review the supplied reading and its self-reported provenance; explicitly adopt every layer, then implement and inspect exports. Obtain another reading when evidence is missing or inadequate."
                 if manifest["reading"]["provided"] else
                 "Obtain a fresh image reading; explicitly adopt every layer, then implement and inspect exports.")
    print(json.dumps({"status": "unresolved-scaffold", "packet": str(args.out), "input_mode": manifest["input_mode"],
                      "image_reading_performed_by_tool": False,
                      "supplied_reading_schema_validated": manifest["reading"]["schema_validated"],
                      "semantic_reading_verified_by_tool": False,
                      "visual_review_passed": False, "next": next_step}))


if __name__ == "__main__":
    main()
