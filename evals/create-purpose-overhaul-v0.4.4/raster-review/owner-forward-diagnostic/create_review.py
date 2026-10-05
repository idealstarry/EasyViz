#!/usr/bin/env python3
"""Stage and check a hash-bound, human/Agent-recorded Create visual review.

This helper does not inspect images, launch a reviewer, or certify aesthetics.
It binds a compact review attestation to the actual exports and saved evidence.
Only the standard library is used; source files are hashed, never executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zlib

SCHEMA_VERSION = 1
POLICY_VERSION = "0.4.4"
MAX_FILE_BYTES = 32 * 1024 * 1024
ARTIFACT_NAMES = ("panel.png", "panel.pdf", "panel.svg", "panel.tiff", "settings.json",
                  "render-settings.json", "elements.json", "qa.json", "stats.json", "plotting-data.csv")
DESIGN_CRITERIA = ("scientific_mapping", "reading_priority", "mark_hierarchy", "geometry",
                   "palette_and_strokes", "guides_and_text")
MEASURED_CRITERIA = ("export_dimensions", "typography", "source_provenance", "technical_qa", "caption")
CHECK_STATUSES = {"passed", "failed", "not_checked"}
READINESS = {"ready", "ready_with_notes", "needs_revision", "not_reviewed"}
LIMITATION = ("A recorded attestation establishes record completeness and current artifact bindings. "
              "It cannot prove that the reviewer opened an image, establish aesthetic superiority, "
              "or certify statistical validity or publication acceptance.")


class ReviewError(ValueError):
    """A safe, actionable packet or record error."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def load_json(raw, label):
    def unique_object(pairs):
        record = {}
        for key, value in pairs:
            if key in record:
                raise ValueError("Duplicate JSON keys")
            record[key] = value
        return record
    try:
        value = json.loads(raw, object_pairs_hook=unique_object,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ReviewError(f"{label} is not valid finite JSON") from exc
    if not isinstance(value, dict):
        raise ReviewError(f"{label} must be a JSON object")
    return value


def read_regular(path, *, required=False):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ReviewError(f"{path.name} must be a regular file, not a symlink")
    if not path.exists():
        if required:
            raise ReviewError(f"Required file is missing: {path}")
        return None
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ReviewError(f"{path.name} must be a regular file no larger than {MAX_FILE_BYTES} bytes")
    return path.read_bytes()


def object_at(record, key):
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def raster_pixels_match(pixels, canvas_mm, dpi):
    """Allow each axis's floor or nearest grid, including integer FP noise."""
    if not isinstance(pixels, list) or len(pixels) != 2 or any(type(value) is not int or value <= 0 for value in pixels):
        return False
    for actual, millimeters in zip(pixels, canvas_mm):
        ideal = millimeters / 25.4 * dpi
        if not math.isfinite(ideal):
            return False
        # Legacy Agg truncation can yield n-1 when equivalent inch/mm
        # arithmetic lands just below an integer. The pinned newer Agg adds
        # 1e-8 before truncation. Restrict compatibility to that tiny band;
        # dimensions alone cannot distinguish such a grid from a 1 px crop.
        allowed = {math.floor(ideal), round(ideal)}
        if abs(ideal - round(ideal)) <= 1e-8:
            allowed.add(round(ideal) - 1)
        if actual not in allowed:
            return False
    return True


def dpi_pair(value):
    return isinstance(value, list) and len(value) == 2 and all(positive(item) for item in value)


def text_required(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{label} needs concrete evidence")
    return value


def png_measurement(raw):
    """Read physical metadata from an actual PNG; no image appearance is inferred."""
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ReviewError("panel.png is not a PNG")
    at, size, dpi, ended = 8, None, None, False
    while at + 12 <= len(raw):
        length = struct.unpack(">I", raw[at:at + 4])[0]
        end = at + 12 + length
        if end > len(raw):
            raise ReviewError("panel.png contains a truncated chunk")
        kind, body = raw[at + 4:at + 8], raw[at + 8:at + 8 + length]
        if zlib.crc32(kind + body) & 0xffffffff != struct.unpack(">I", raw[end - 4:end])[0]:
            raise ReviewError("panel.png contains an invalid chunk checksum")
        if kind == b"IHDR" and length == 13:
            size = list(struct.unpack(">II", body[:8]))
        if kind == b"pHYs" and length == 9 and body[8] == 1:
            dpi = [value * .0254 for value in struct.unpack(">II", body[:8])]
        at = end
        if kind == b"IEND":
            ended = True
            break
    if not ended or size is None or min(size) <= 0 or at != len(raw):
        raise ReviewError("panel.png needs a complete positive-size PNG canvas")
    return {"pixels": size, "dpi": dpi}


def svg_measurement(raw):
    # Matplotlib's external SVG DOCTYPE is harmless; entity/internal subsets are not.
    if b"<!ENTITY" in raw.upper() or b"[" in raw.split(b"<!DOCTYPE", 1)[-1].split(b">", 1)[0] and b"<!DOCTYPE" in raw:
        raise ReviewError("SVG entity declarations are unsupported")
    try:
        root = ET.fromstring(raw)
        result = {}
        for key in ("width", "height"):
            value = root.attrib[key]
            scale = {"pt": 25.4 / 72, "mm": 1, "cm": 10, "in": 25.4}
            unit = next((unit for unit in scale if value.endswith(unit)), None)
            if unit is None:
                raise ValueError("missing physical unit")
            number = float(value[:-len(unit)]) * scale[unit]
            if not positive(number):
                raise ValueError("invalid physical size")
            result[key + "_mm"] = number
        return result
    except (ET.ParseError, KeyError, ValueError) as exc:
        raise ReviewError("panel.svg needs a valid physical canvas") from exc


def evidence(status, detail):
    return {"status": status, "evidence": detail}


def source_bindings(root, records):
    """Use declared paths only; relative paths are scoped to the figure directory."""
    claims = {"data_file": [], "source_script": [], "spec_file": [], "figure_profile": []}
    for origin, record in records.items():
        info, version = object_at(record, "input"), object_at(record, "version")
        profile = object_at(record, "figure_profile")
        if isinstance(profile.get("path"), str) and profile["path"].strip():
            claims["figure_profile"].append((origin + ":figure_profile.path", profile["path"], profile.get("sha256")))
        for role, hash_key in (("data_file", "input_sha256"), ("source_script", "source_script_sha256"),
                               ("spec_file", "supplied_spec_sha256")):
            location = info.get(role)
            expected = info.get(hash_key) if role == "spec_file" else version.get(hash_key, record.get(hash_key))
            if isinstance(location, str) and location.strip():
                claims[role].append((origin + ":input." + role, location, expected))
        # Focused exporters sometimes keep direct absolute source/spec paths in settings.
        for field, role, hash_key in (("input_file", "data_file", "input_sha256"),
                                     ("source_script", "source_script", "source_script_sha256"),
                                     ("spec_file", "spec_file", "spec_file_sha256")):
            location = record.get(field)
            if isinstance(location, str) and location.strip():
                # Core settings.input_file is a basename label. When the element
                # map records the actual data_file, that exact pointer wins.
                if field == "input_file" and not Path(location).is_absolute() and any(object_at(value, "input").get("data_file") for value in records.values()):
                    continue
                claims[role].append((origin + ":" + field, location, record.get(hash_key)))
    result = {}
    for role, entries in claims.items():
        checked = []
        for origin, location, expected in entries:
            path = Path(location).expanduser()
            if not path.is_absolute():
                # Do not search cwd/parents or execute paths from provenance records.
                if ".." in path.parts:
                    checked.append({"declared_by": origin, "path": location, "status": "not_checked",
                                    "reason": "Relative provenance must remain within the figure directory; save an explicit absolute path."})
                    continue
                path = root / path
            raw = read_regular(path)
            actual = digest(raw) if raw is not None else None
            status = "not_checked" if actual is None or not isinstance(expected, str) else "passed" if actual == expected else "failed"
            checked.append({"declared_by": origin, "path": str(path.absolute()), "sha256": actual,
                            "expected_sha256": expected, "status": status})
        result[role] = checked
    return result


def snapshot(figure_dir, *, caption=None, baseline_dir=None):
    root = Path(figure_dir).expanduser().resolve()
    if not root.is_dir():
        raise ReviewError("Figure directory does not exist")
    artifacts, raws, records = {}, {}, {}
    for name in ARTIFACT_NAMES:
        raw = read_regular(root / name)
        if raw is None:
            continue
        artifacts[name] = {"path": str(root / name), "sha256": digest(raw), "bytes": len(raw)}
        raws[name] = raw
        if name.endswith(".json"):
            records[name] = load_json(raw, name)
    settings = records.get("settings.json", records.get("render-settings.json", {}))
    qa, elements = records.get("qa.json", {}), records.get("elements.json", {})
    track = settings.get("track") or object_at(settings, "input").get("track") or elements.get("track")
    if track and track != "create":
        raise ReviewError("Create review cannot certify a reproduce-track output")
    layout = object_at(settings, "layout")
    panel = {key: layout.get(key, qa.get(key, object_at(elements, "panel").get(key))) for key in ("width_mm", "height_mm")}
    sources = source_bindings(root, records)
    checks = {}
    png = png_measurement(raws["panel.png"]) if "panel.png" in raws else None
    dimensions = {"adopted_canvas_mm": panel, "actual_png": png, "qa_exports": qa.get("exports")}
    dimension_status = "not_checked"
    if all(positive(panel[key]) for key in panel) and png and positive(layout.get("dpi")):
        canvas_mm = [panel[key] for key in ("width_mm", "height_mm")]
        statuses = ["passed" if raster_pixels_match(png["pixels"], canvas_mm, layout["dpi"]) and dpi_pair(png["dpi"]) and all(abs(value - layout["dpi"]) <= .1 for value in png["dpi"]) else "failed"]
        declared_formats = settings.get("formats", list(object_at(qa, "exports")))
        if not isinstance(declared_formats, list) or not declared_formats:
            statuses.append("not_checked")
        dimensions["format_bindings"] = {}
        for extension in declared_formats if isinstance(declared_formats, list) else []:
            if extension not in ("png", "pdf", "svg", "tiff") or f"panel.{extension}" not in artifacts:
                statuses.append("failed")
                continue
            recorded = object_at(object_at(qa, "exports"), extension)
            actual_hash = artifacts[f"panel.{extension}"]["sha256"]
            declared_hash = recorded.get("sha256")
            hash_status = ("not_checked" if declared_hash is None else
                           "passed" if isinstance(declared_hash, str) and declared_hash == actual_hash else "failed")
            # PNG/SVG are measured directly from the current bytes. PDF/TIFF
            # use saved actual-export measurements only when those records are
            # bound to the current file bytes; absence is honestly unchecked.
            measurement_source = "current_file" if extension in ("png", "svg") else "hash_bound_qa"
            format_statuses = []
            if extension in ("pdf", "tiff") or declared_hash is not None:
                format_statuses.append(hash_status)
            if extension == "png":
                format_statuses.append(statuses[0])
                if "pixels" in recorded and recorded["pixels"] != png["pixels"]:
                    format_statuses.append("failed")
                if "dpi" in recorded and (not dpi_pair(recorded["dpi"]) or not dpi_pair(png["dpi"]) or
                                          any(abs(value - actual) > 1e-6 for value, actual in zip(recorded["dpi"], png["dpi"]))):
                    format_statuses.append("failed")
            elif extension == "tiff":
                pixels, dpi = recorded.get("pixels"), recorded.get("dpi")
                if not isinstance(pixels, list) or not dpi_pair(dpi):
                    format_statuses.append("not_checked")
                elif not raster_pixels_match(pixels, canvas_mm, layout["dpi"]) or any(abs(value - layout["dpi"]) > .1 for value in dpi):
                    format_statuses.append("failed")
            elif extension == "pdf":
                if not all(positive(recorded.get(key)) for key in panel):
                    format_statuses.append("not_checked")
                elif any(abs(recorded[key] - panel[key]) >= .05 for key in panel):
                    format_statuses.append("failed")
            else:
                measured = svg_measurement(raws["panel.svg"])
                dimensions["actual_svg"] = measured
                if any(abs(measured[key] - panel[key]) >= .05 for key in panel):
                    format_statuses.append("failed")
                if recorded and any(positive(recorded.get(key)) and abs(recorded[key] - measured[key]) >= .05 for key in panel):
                    format_statuses.append("failed")
            format_status = "failed" if "failed" in format_statuses else "not_checked" if "not_checked" in format_statuses else "passed"
            dimensions["format_bindings"][extension] = {"status": format_status, "measurement_source": measurement_source,
                                                        "recorded_sha256": declared_hash, "actual_sha256": actual_hash}
            statuses.append(format_status)
        dimension_status = "failed" if "failed" in statuses else "not_checked" if "not_checked" in statuses else "passed"
    checks["export_dimensions"] = evidence(dimension_status, dimensions)
    typography = settings.get("typography")
    checks["typography"] = evidence("passed" if isinstance(layout.get("actual_font"), str) and layout["actual_font"].strip() and isinstance(typography, dict) and typography and all(positive(value) for value in typography.values()) else "not_checked",
                                      {"actual_font": layout.get("actual_font"), "font_substituted": layout.get("font_substituted"), "sizes_pt": typography,
                                       "scope": "Actual-font and point-size records from the exporter; font embedding is not inferred from PNG."})
    provenance_status = "passed"
    for role in ("data_file", "source_script"):
        if not sources[role] or any(item["status"] == "not_checked" for item in sources[role]):
            provenance_status = "not_checked" if provenance_status != "failed" else "failed"
        if any(item["status"] == "failed" for item in sources[role]):
            provenance_status = "failed"
    for role in ("spec_file", "figure_profile"):
        if any(item["status"] == "failed" for item in sources[role]):
            provenance_status = "failed"
        elif any(item["status"] == "not_checked" for item in sources[role]) and provenance_status != "failed":
            provenance_status = "not_checked"
    expected_data_hashes = {record.get("input_sha256") for record in records.values() if isinstance(record.get("input_sha256"), str)}
    expected_data_hashes.update(item.get("expected_sha256") for item in sources["data_file"] if item.get("expected_sha256"))
    if len(expected_data_hashes) > 1:
        provenance_status = "failed"
    declared_svg = object_at(elements, "version").get("figure_sha256")
    if declared_svg and declared_svg != artifacts.get("panel.svg", {}).get("sha256"):
        provenance_status = "failed"
    declared_script = object_at(elements, "version").get("source_script_sha256")
    recorded_renderer = object_at(settings, "renderer").get("sha256")
    if declared_script and recorded_renderer and declared_script != recorded_renderer:
        provenance_status = "failed"
    declared_colors = object_at(elements, "version").get("resolved_colors_sha256")
    if declared_colors:
        colors = settings.get("resolved_colors")
        actual_colors = digest(json.dumps(colors, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()) if isinstance(colors, dict) else None
        if actual_colors != declared_colors:
            provenance_status = "failed"
    # The saved settings are always the adopted specification; an original spec
    # file is additionally bound when its location was recorded by the exporter.
    if not settings:
        provenance_status = "not_checked" if provenance_status != "failed" else "failed"
    checks["source_provenance"] = evidence(provenance_status, {"declared_sources": sources,
                                        "saved_specification": artifacts.get("settings.json", artifacts.get("render-settings.json")),
                                        "resolved_spec_sha256": object_at(elements, "version").get("spec_sha256"),
                                        "scope": "Source/spec byte hashes establish continuity; they do not establish scientific or statistical correctness."})
    qa_status = "passed" if qa.get("status") == "pass" and qa.get("valid_outputs") is True else "not_checked" if not qa else "failed"
    for key in ("clipped_text", "overlapping_tick_labels", "missing_glyphs"):
        if qa.get(key):
            qa_status = "failed"
    for key in ("legend_layout", "cell_annotations", "auto_layout", "point_layout", "source_to_artist_audit"):
        value = object_at(qa, key)
        if value.get("status") in ("failed", "fail", "needs_revision"):
            qa_status = "failed"
    checks["technical_qa"] = evidence(qa_status, {"qa": artifacts.get("qa.json"), "status": qa.get("status"),
                                         "valid_outputs": qa.get("valid_outputs"), "input_rows": qa.get("input_rows"),
                                         "plotted_input_rows": qa.get("plotted_input_rows"),
                                         "readability_advisory": object_at(qa, "readability").get("status"),
                                         "scope": "Acknowledges saved numerical/export evidence; visual hierarchy, point/summary occlusion and statistics still need review."})
    caption_location = caption or object_at(settings, "input").get("caption_file") or settings.get("caption_file")
    caption_path = Path(caption_location).expanduser() if caption_location else root / "caption.md"
    if not caption_path.is_absolute():
        caption_path = root / caption_path
    caption_raw = read_regular(caption_path)
    if caption_raw is not None:
        artifacts["caption"] = {"path": str(caption_path.absolute()), "sha256": digest(caption_raw), "bytes": len(caption_raw)}
    checks["caption"] = evidence("passed" if caption_raw and caption_raw.strip() else "not_checked",
                                 {"artifact": artifacts.get("caption"), "scope": "Separate caption is present; its scientific wording is a review attestation."})
    baseline = None
    if baseline_dir:
        base_root = Path(baseline_dir).expanduser().resolve()
        if not base_root.is_dir():
            raise ReviewError("Baseline directory does not exist")
        raw = read_regular(base_root / "panel.png")
        if raw is not None:
            baseline = {"path": str(base_root / "panel.png"), "sha256": digest(raw), "measurement": png_measurement(raw)}
        else:
            baseline = {"path": str(base_root / "panel.png"), "sha256": None, "measurement": None}
    return {"figure_dir": str(root), "artifacts": artifacts, "source_bindings": sources, "panel": panel,
            "measured_checks": checks, "candidate_png": artifacts.get("panel.png"), "baseline_png": baseline}


def stage(figure_dir, reading_task, *, pass_number=1, out=None, caption=None, baseline_dir=None, baseline_kind=None):
    text_required(reading_task, "reading_task")
    if type(pass_number) is not int or pass_number not in (1, 2, 3):
        raise ReviewError("pass_number must be 1, 2 or 3, including the first rendering")
    if baseline_dir and baseline_kind not in ("accepted", "default_demonstration"):
        raise ReviewError("A comparison needs baseline_kind=accepted or default_demonstration")
    if not baseline_dir and baseline_kind:
        raise ReviewError("baseline_kind requires a baseline directory")
    if caption and not Path(caption).expanduser().is_absolute():
        caption = str(Path(figure_dir).expanduser().resolve() / caption)
    bound = snapshot(figure_dir, caption=caption, baseline_dir=baseline_dir)
    packet = {"schema_version": SCHEMA_VERSION, "kind": "easyviz_create_review_packet", "policy_version": POLICY_VERSION,
              "pass_number": pass_number, "reading_task": reading_task,
              "inputs": {"figure_dir": bound["figure_dir"], "caption": str(Path(caption).expanduser().absolute()) if caption else None,
                         "baseline_dir": str(Path(baseline_dir).expanduser().resolve()) if baseline_dir else None, "baseline_kind": baseline_kind},
              "snapshot": bound, "required_design_checks": list(DESIGN_CRITERIA), "required_external_checks": list(MEASURED_CRITERIA),
              "instructions": ["Open the actual candidate PNG as a complete canvas before first user-visible delivery.",
                               "Consider the recorded physical size: inspect a nominal-size view if available, or honestly record a final-proportions view and its size basis. One actual opening may cover both views.",
                               "Record brief, concrete evidence for each design criterion; inspect the caption separately.",
                               "Acknowledge the saved measured evidence without inventing measurements. Required failed/not_checked items prevent readiness.",
                               "Correct critical/major failures before delivery; record corrections and residual minor/intentional differences. A clean first pass is valid.",
                               "Keep comparative preference separate from readiness. No baseline or reference image is required for Create.",
                               "After any meaningful change, rerender affected formats and stage the current exports for another review; at most three visual passes total."],
              "limitation": LIMITATION}
    destination = Path(out).expanduser().absolute() if out else Path(bound["figure_dir"]) / "create-review" / f"pass-{pass_number:02d}"
    if destination.is_symlink():
        raise ReviewError("Review destination must not be a symlink")
    destination.mkdir(parents=True, exist_ok=True)
    packet_path, review_path = destination / "packet.json", destination / "review.json"
    serialized = json_bytes(packet)
    existing = read_regular(packet_path)
    if existing is not None and existing != serialized:
        raise ReviewError("This review directory binds a different packet. Use a fresh --out directory for the current pass.")
    if existing is None:
        if read_regular(review_path) is not None:
            raise ReviewError("Review record exists without its bound packet; use a fresh --out directory")
        packet_path.write_bytes(serialized)
    if read_regular(review_path) is None:
        review = {"schema_version": SCHEMA_VERSION, "kind": "easyviz_create_review", "policy_version": POLICY_VERSION,
                  "packet_sha256": digest(serialized), "pass_number": pass_number,
                  "reviewer": {"role": "self-review", "identity": ""}, "status": "not_reviewed",
                  "images_opened": [],
                  "design_checks": [{"criterion": criterion, "status": "not_checked", "evidence": ""} for criterion in DESIGN_CRITERIA],
                  "external_checks": [{"criterion": criterion, "status": "not_checked", "evidence": ""} for criterion in MEASURED_CRITERIA],
                  "findings": [], "corrections": [], "residual_issues": [],
                  "preference": {"choice": "not_checked" if baseline_dir else "not_applicable", "reasons": ""},
                  "limitation": LIMITATION}
        review_path.write_bytes(json_bytes(review))
    return {"packet": str(packet_path), "review": str(review_path), "packet_sha256": digest(serialized),
            "gate_status": "pending", "measured_checks": {key: value["status"] for key, value in bound["measured_checks"].items()}, "limitation": LIMITATION}


def validate_record(packet, review, packet_sha256):
    """Validate an attestation, without claiming its visual observations are true."""
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    require(type(review.get("schema_version")) is int and review.get("schema_version") == SCHEMA_VERSION and review.get("kind") == "easyviz_create_review", "Unsupported review record schema/kind")
    require(review.get("policy_version") == POLICY_VERSION, "Review policy version does not match this packet")
    require(review.get("packet_sha256") == packet_sha256, "Review record belongs to a different packet hash")
    require(review.get("pass_number") == packet["pass_number"] and type(review.get("pass_number")) is int, "Review pass number does not match the packet")
    status = review.get("status")
    require(isinstance(status, str) and status in READINESS, "Unknown readiness status")
    require(status in ("ready", "ready_with_notes"), "Review is not ready for first delivery")
    reviewer = object_at(review, "reviewer")
    require(reviewer.get("role") in ("self-review", "independent") and isinstance(reviewer.get("identity"), str) and bool(reviewer["identity"].strip()), "Record a reviewer identity and self-review/independent role")
    bound = packet["snapshot"]
    images = review.get("images_opened")
    require(isinstance(images, list), "images_opened must be a list")
    images = images if isinstance(images, list) else []
    for role, artifact in (("candidate", bound["candidate_png"]), ("baseline", bound["baseline_png"])):
        if role == "baseline" and (artifact is None or object_at(review, "preference").get("choice") in ("not_checked", "not_applicable")):
            continue
        matching = [entry for entry in images if isinstance(entry, dict) and entry.get("role") == role]
        require(len(matching) == 1, f"Record exactly one {role} image-opening attestation")
        if len(matching) != 1 or not artifact:
            require(artifact is not None, f"Actual {role} PNG is unavailable")
            continue
        opened = matching[0]
        require(opened.get("path") == artifact["path"] and opened.get("sha256") == artifact["sha256"] and bool(artifact["sha256"]), f"{role} image-opening attestation is stale or points to a different image")
        views = opened.get("views")
        require(isinstance(views, list) and len(views) == 2 and all(isinstance(value, str) for value in views) and set(views) == {"full_canvas", "final_proportions"}, f"{role} needs recorded full_canvas and final_proportions views")
        for field in ("tool", "size_basis"):
            require(isinstance(opened.get(field), str) and bool(opened[field].strip()), f"{role} opening needs {field}")
    for key, criteria in (("design_checks", DESIGN_CRITERIA), ("external_checks", MEASURED_CRITERIA)):
        checks = review.get(key)
        require(isinstance(checks, list), f"{key} must be a list")
        checks = checks if isinstance(checks, list) else []
        named = [entry.get("criterion") for entry in checks if isinstance(entry, dict)]
        require(len(checks) == len(criteria) and all(isinstance(value, str) for value in named) and set(named) == set(criteria), f"{key} must cover the required criteria exactly once")
        for item in checks:
            if not isinstance(item, dict):
                require(False, f"{key} has an invalid item")
                continue
            criterion = item.get("criterion")
            require(isinstance(item.get("status"), str) and item.get("status") in CHECK_STATUSES, f"Unknown check status for {criterion}")
            require(item.get("status") == "passed", f"Required {criterion} check has not passed")
            require(isinstance(item.get("evidence"), str) and bool(item["evidence"].strip()), f"{criterion} needs concrete evidence")
            if key == "external_checks" and criterion in MEASURED_CRITERIA:
                require(bound["measured_checks"][criterion]["status"] == "passed", f"Saved measured evidence for {criterion} is failed or not_checked; an attestation cannot upgrade it")
    findings, corrections = review.get("findings"), review.get("corrections")
    require(isinstance(findings, list) and isinstance(corrections, list), "findings and corrections must be lists")
    findings = findings if isinstance(findings, list) else []
    corrections = corrections if isinstance(corrections, list) else []
    ids, residual = set(), set()
    for finding in findings:
        if not isinstance(finding, dict):
            require(False, "Finding must be an object")
            continue
        identity, severity, state = finding.get("id"), finding.get("severity"), finding.get("state")
        require(isinstance(identity, str) and bool(identity.strip()) and identity not in ids, "Findings need unique nonempty IDs")
        if isinstance(identity, str):
            ids.add(identity)
        require(severity in ("critical", "major", "minor", "note"), f"Unknown finding severity: {identity}")
        require(state in ("open", "resolved", "accepted"), f"Unknown finding state: {identity}")
        for field in ("location", "evidence", "requirement", "action"):
            require(isinstance(finding.get(field), str) and bool(finding[field].strip()), f"Finding {identity} needs {field}")
        require(severity not in ("critical", "major") or state == "resolved", f"Unresolved {severity} finding: {identity}")
        if state == "resolved":
            matches = [item for item in corrections if isinstance(item, dict) and item.get("finding_id") == identity]
            require(len(matches) == 1, f"Resolved finding {identity} needs one recorded correction")
            if len(matches) == 1:
                correction = matches[0]
                require(bound["candidate_png"] is not None and correction.get("candidate_sha256") == bound["candidate_png"]["sha256"], f"Correction {identity} does not bind the reviewed current PNG")
                for field in ("action", "evidence"):
                    require(isinstance(correction.get(field), str) and bool(correction[field].strip()), f"Correction {identity} needs {field}")
        elif state in ("open", "accepted"):
            if isinstance(identity, str):
                residual.add(identity)
    resolved_ids = {finding["id"] for finding in findings if isinstance(finding, dict) and isinstance(finding.get("id"), str) and finding.get("state") == "resolved"}
    for correction in corrections:
        require(isinstance(correction, dict) and isinstance(correction.get("finding_id"), str) and correction["finding_id"] in resolved_ids, "Correction refers to an unknown or unresolved finding")
    residual_record = review.get("residual_issues")
    require(isinstance(residual_record, list) and len(residual_record) == len(residual) and all(isinstance(value, str) for value in residual_record) and set(residual_record) == residual, "residual_issues must list every unresolved/accepted finding ID exactly once")
    require(not residual or status == "ready_with_notes", "Residual minor/note findings require ready_with_notes")
    preference = object_at(review, "preference")
    choice = preference.get("choice")
    require(choice in ("not_applicable", "baseline", "candidate", "no_clear_preference", "not_checked"), "Unknown comparative preference")
    if choice in ("baseline", "candidate", "no_clear_preference"):
        require(bound["baseline_png"] is not None and bool(bound["baseline_png"]["sha256"]), "Comparative preference requires an available baseline image")
        require(isinstance(preference.get("reasons"), str) and bool(preference["reasons"].strip()), "Comparative preference needs concrete visible reasons")
        if bound["baseline_png"] and bound["candidate_png"]:
            require(bound["baseline_png"]["measurement"]["pixels"] == bound["measured_checks"]["export_dimensions"]["evidence"]["actual_png"]["pixels"] and bound["baseline_png"]["measurement"]["dpi"] == bound["measured_checks"]["export_dimensions"]["evidence"]["actual_png"]["dpi"], "Compare images exported at the same physical size")
    return errors


def check(packet_path, review_path=None):
    packet_path = Path(packet_path).expanduser().absolute()
    raw = read_regular(packet_path, required=True)
    packet = load_json(raw, "Review packet")
    if type(packet.get("schema_version")) is not int or packet.get("schema_version") != SCHEMA_VERSION or packet.get("kind") != "easyviz_create_review_packet" or packet.get("policy_version") != POLICY_VERSION:
        raise ReviewError("Unsupported packet schema/kind/policy version")
    if type(packet.get("pass_number")) is not int or packet["pass_number"] not in (1, 2, 3):
        raise ReviewError("Packet exceeds the three-pass policy or has an invalid pass number")
    if packet.get("required_design_checks") != list(DESIGN_CRITERIA) or packet.get("required_external_checks") != list(MEASURED_CRITERIA):
        raise ReviewError("Packet required review criteria were changed")
    text_required(packet.get("reading_task"), "Packet reading_task")
    inputs = object_at(packet, "inputs")
    if not isinstance(inputs.get("figure_dir"), str):
        raise ReviewError("Packet needs its actual figure directory")
    for field in ("caption", "baseline_dir"):
        if inputs.get(field) is not None and not isinstance(inputs[field], str):
            raise ReviewError(f"Packet {field} must be a path or null")
    if inputs.get("baseline_dir") and inputs.get("baseline_kind") not in ("accepted", "default_demonstration"):
        raise ReviewError("Packet needs a known baseline kind for a comparison")
    if not inputs.get("baseline_dir") and inputs.get("baseline_kind"):
        raise ReviewError("Packet baseline kind needs an actual comparison directory")
    current = snapshot(inputs["figure_dir"], caption=inputs.get("caption"), baseline_dir=inputs.get("baseline_dir"))
    errors = []
    if current != packet.get("snapshot"):
        errors.append("Export, source, saved specification, caption or QA evidence changed since staging. Review the current exports in a fresh packet.")
    review_path = Path(review_path).expanduser().absolute() if review_path else packet_path.with_name("review.json")
    review = load_json(read_regular(review_path, required=True), "Review record")
    # Validate attestation against independently reconstructed current data, so
    # a malformed/edited packet snapshot cannot hide required checks or crash
    # the validation path. A changed packet has already been rejected above.
    packet["snapshot"] = current
    errors.extend(validate_record(packet, review, digest(raw)))
    return {"gate_status": "recorded" if not errors else "blocked", "readiness": review.get("status"),
            "packet_sha256": digest(raw), "review": str(review_path), "errors": errors, "limitation": LIMITATION}


DESCRIPTION = {
    "schema_version": SCHEMA_VERSION, "policy_version": POLICY_VERSION, "recipe": "create_review", "track": "create",
    "commands": {"stage": "stage --figure-dir DIR --reading-task TEXT [--pass-number 1..3] [--caption PATH] [--out DIR] [--baseline-dir DIR --baseline-kind accepted|default_demonstration]",
                 "check": "check --packet PATH [--review PATH]"},
    "outputs": "Default DIR/create-review/pass-01/packet.json and review.json. Identical restaging preserves the review; changed packets require a fresh output directory.",
    "image_attestation": {"role": "candidate", "path": "Copy snapshot.candidate_png.path", "sha256": "Copy snapshot.candidate_png.sha256",
                          "views": ["full_canvas", "final_proportions"], "tool": "Actual image-opening tool or inspection method", "size_basis": "Actual nominal-size display or honest final-proportions assessment using recorded width/height; do not claim an unavailable preview."},
    "design_criteria": list(DESIGN_CRITERIA), "external_criteria": list(MEASURED_CRITERIA),
    "check_entry": {"criterion": "One required criterion", "status": "passed|failed|not_checked", "evidence": "One concrete brief observation or actual measured record acknowledged"},
    "finding": {"id": "f1", "severity": "critical|major|minor|note", "state": "open|resolved|accepted", "location": "Actual region", "evidence": "Observed conflict", "requirement": "Adopted requirement or optional improvement", "action": "Feasible correction or explicit accepted adaptation"},
    "correction": {"finding_id": "f1", "action": "Actual change", "evidence": "Visible result after rerender", "candidate_sha256": "Current PNG hash"},
    "statuses": sorted(READINESS), "gate_status": "recorded or blocked; recorded validates an attestation, not vision",
    "custom_metadata": {
        "instruction": "A custom script may save its actual measurements and provenance using this contract. These are evidence records, not values to invent merely to pass. Missing source/QA evidence remains not_checked.",
        "settings.json": {"input": {"data_file": "Actual absolute source-data path", "source_script": "Actual absolute plotting-script path",
                                     "spec_file": "Actual specification path when a separate spec exists", "supplied_spec_sha256": "SHA-256 of actual spec bytes when supplied"},
                          "version": {"input_sha256": "SHA-256 of actual source data", "source_script_sha256": "SHA-256 of actual plotting source"},
                          "layout": {"width_mm": 88, "height_mm": 66, "dpi": 300, "actual_font": "Actual selected font", "font_substituted": False},
                          "typography": {"axis": 8, "tick": 8, "legend": 8, "annotation": 8}, "formats": ["png", "pdf", "svg"]},
        "qa.json": {"status": "pass only when actual checks succeeded", "valid_outputs": "true only for actually valid outputs",
                    "input_sha256": "Actual source data hash", "input_rows": "Actual checked source-row count",
                    "exports": {"png": {"pixels": "Actual full PNG [width,height]", "dpi": "Actual PNG dpi [x,y]", "sha256": "Actual exported bytes; optional when directly measured by gate"},
                                "pdf": {"width_mm": "Measured page width", "height_mm": "Measured page height", "sha256": "Required SHA-256 of the same bytes whose page was measured"},
                                "svg": {"width_mm": "Measured physical width", "height_mm": "Measured physical height", "sha256": "Actual exported bytes; optional when directly measured by gate"},
                                "tiff": {"pixels": "Actual TIFF [width,height]", "dpi": "Actual TIFF dpi [x,y]", "sha256": "Required SHA-256 of the same bytes whose pixels/dpi were measured"}}},
        "scope": "Use only formats actually exported. PDF/TIFF saved measurements require matching export byte hashes; missing hashes remain not_checked and mismatches fail. PNG/SVG are directly measured, with optional matching saved hashes. Shared exporters may instead provide elements.json.input/version; saved settings supply the adopted spec. Separate caption location is explicit --caption or metadata caption_file. All files are read-only for this helper except its new review directory.",
    },
    "scope": "No reference image or baseline is mandatory. Source paths come from actual metadata; unresolved/custom QA remains not_checked. Optional comparison is separate from readiness.",
    "limitation": LIMITATION,
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-spec", action="store_true")
    commands = parser.add_subparsers(dest="command")
    staging = commands.add_parser("stage")
    staging.add_argument("--figure-dir", required=True)
    staging.add_argument("--reading-task", required=True)
    staging.add_argument("--pass-number", type=int, default=1)
    staging.add_argument("--out")
    staging.add_argument("--caption")
    staging.add_argument("--baseline-dir")
    staging.add_argument("--baseline-kind", choices=("accepted", "default_demonstration"))
    checking = commands.add_parser("check")
    checking.add_argument("--packet", required=True)
    checking.add_argument("--review")
    args = parser.parse_args(argv)
    try:
        if args.describe_spec:
            result = DESCRIPTION
        elif args.command == "stage":
            result = stage(args.figure_dir, args.reading_task, pass_number=args.pass_number, out=args.out,
                           caption=args.caption, baseline_dir=args.baseline_dir, baseline_kind=args.baseline_kind)
        elif args.command == "check":
            result = check(args.packet, args.review)
        else:
            parser.error("Choose stage/check or --describe-spec")
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 1 if result.get("gate_status") == "blocked" else 0
    except (ReviewError, OSError) as exc:
        print(json.dumps({"gate_status": "blocked", "error": str(exc), "limitation": LIMITATION}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
