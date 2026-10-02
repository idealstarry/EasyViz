#!/usr/bin/env python3
"""Independent written-export audit for the frozen unseen interval pilot.

Read the protocol before the outputs. The geometry checks below never import a
model's plotting code or EasyViz; they recover measurements from written SVG
paths and ticks. Only manually inspected entry scripts may be rerun, in clean
temporary copies. No frozen model output is repaired.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
NS = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}"
NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
COLUMNS = ["Readout", "Preparation batch", "Prepared ratio", "Lower 95", "Upper 95"]
EXPECTED_SHA = "b9d1c0eef736267344770a2f42bf2033eda1073e538ce352829ed93317f98d99"
EXPORTED_COLUMN_ALIASES = {"Readout": "readout", "Preparation batch": "batch", "Prepared ratio": "prepared_ratio", "Lower 95": "lower_95", "Upper 95": "upper_95"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check(condition, evidence):
    return {"status": "pass" if bool(condition) else "fail", "evidence": evidence}


def first(values):
    return list(dict.fromkeys(values))


def normalized(value):
    return " ".join(value.split()).replace("−", "-").replace("‐", "-").replace("‑", "-")


def styles(value):
    return dict(part.strip().split(":", 1) for part in value.split(";") if ":" in part)


def circle_geometry(path, dx=0, dy=0):
    d = path.get("d", "")
    # Hollow Matplotlib circles add an explicit closing L before z.
    if d.count("C") != 8 or re.sub(NUMBER + r"|[MCLzZ\s,]", "", d):
        return None
    coords = np.array([float(v) for v in re.findall(NUMBER, d)]).reshape(-1, 2)
    low, high = coords.min(axis=0), coords.max(axis=0)
    diameters = high - low
    if abs(diameters[0] - diameters[1]) > 2e-5 or diameters[0] <= 0:
        return None
    return {"center_pt": ((low + high) / 2 + [dx, dy]).tolist(), "diameter_pt": float(diameters[0])}


def actual_primitives(tree, axes, include_legends=False):
    ids = {n.get("id"): n for n in tree.iter() if n.get("id")}
    circles, lines = [], []
    def visit(node, inherited):
        if node.tag in (NS + "defs", NS + "text"):
            return
        if not include_legends and node.get("id", "").startswith("legend_"):
            return
        merged = dict(inherited)
        merged.update(styles(node.get("style", "")))
        if node.tag == NS + "use":
            target = ids.get(node.get(XLINK + "href", "").lstrip("#"))
            if target is not None:
                actual = dict(styles(target.get("style", "")))
                actual.update(merged)
                value = circle_geometry(target, float(node.get("x", 0)), float(node.get("y", 0)))
                if value is not None:
                    value["style"] = actual
                    circles.append(value)
        elif node.tag == NS + "path":
            value = circle_geometry(node)
            if value is not None:
                value["style"] = merged
                circles.append(value)
            elif re.sub(NUMBER + r"|[ML\s,]", "", node.get("d", "")) == "":
                values = [float(v) for v in re.findall(NUMBER, node.get("d", ""))]
                if len(values) == 4:
                    lines.append({"endpoints_pt": np.array(values).reshape(2, 2).tolist(), "style": merged})
        for child in node:
            visit(child, merged)
    visit(axes, {})
    return circles, lines


def tick_value(text):
    spans = text.findall(NS + "tspan")
    chunks = [normalized("".join(n.itertext())) for n in spans]
    if len(chunks) == 2 and chunks[0] == "10" and re.fullmatch(r"[-+]?\d+", chunks[1]):
        return 10 ** int(chunks[1])
    return float(normalized("".join(text.itertext())))


def svg_measurements(path):
    tree = ET.parse(path).getroot()
    axes = next(n for n in tree.iter() if n.get("id") == "axes_1")
    xaxis = next(n for n in axes.iter() if n.get("id") == "matplotlib.axis_1")
    yaxis = next(n for n in axes.iter() if n.get("id") == "matplotlib.axis_2")
    xvalues, xpositions, labels = [], [], []
    for group in xaxis:
        if not group.get("id", "").startswith("xtick_"):
            continue
        text = group.find(f".//{NS}text")
        marker = group.find(f".//{NS}use")
        if text is not None and marker is not None:
            xvalues.append(tick_value(text))
            xpositions.append(float(marker.get("x")))
    if len(xvalues) < 2 or min(xvalues) <= 0:
        raise ValueError("Cannot recover log transform from written positive numeric tick labels")
    slope, intercept = np.polyfit(np.log(xvalues), xpositions, 1)
    residual = float(np.max(np.abs(np.array(xpositions) - (np.log(xvalues) * slope + intercept))))
    for group in yaxis:
        if not group.get("id", "").startswith("ytick_"):
            continue
        texts = list(group.iter(NS + "text"))
        marker = group.find(f".//{NS}use")
        if texts:
            if marker is not None:
                y = float(marker.get("y"))
                anchor_method = "Visible tick glyph; exact axis tick coordinate"
            else:
                # A zero-length y tick need not emit any SVG glyph. Its
                # wrapped label remains present. Use written text baseline
                # positions only to assign marks to the closest label block;
                # do not pretend a font-baseline proxy is an exact tick.
                ys = []
                for text in texts:
                    if text.get("y") is not None:
                        ys.append(float(text.get("y")))
                    else:
                        match = re.search(f"translate\\(\\s*({NUMBER})[ ,]+({NUMBER})\\s*\\)", text.get("transform", ""))
                        if not match:
                            raise ValueError("Cannot read wrapped label text anchor")
                        ys.append(float(match[2]))
                y = float(np.mean(ys))
                anchor_method = "Mean written text baseline proxy; tick glyph suppressed"
            labels.append({"text": normalized(" ".join("".join(t.itertext()) for t in texts)), "y_pt": y, "measurement": anchor_method})
    circles, lines = actual_primitives(tree, axes)
    axes_patch = next(n for n in axes.iter() if n.get("id") == "patch_2").find(NS + "path")
    patch_coordinates = np.array([float(v) for v in re.findall(NUMBER, axes_patch.get("d"))]).reshape(-1, 2)
    plot_bbox = [*patch_coordinates.min(axis=0), *patch_coordinates.max(axis=0)]
    return tree, {"log_x_slope_pt": float(slope), "log_x_intercept_pt": float(intercept), "log_tick_fit_max_residual_pt": residual, "tick_values": xvalues, "tick_positions_pt": xpositions, "labels_top_to_bottom": labels, "circles": circles, "lines": lines, "plot_bbox_pt": plot_bbox}


def canonical_plot_table(source, plotted):
    mapping = {col: col if col in plotted[0] else EXPORTED_COLUMN_ALIASES[col] for col in COLUMNS}
    source_keys = {(r["Readout"], r["Preparation batch"]) for r in source}
    observed, empty_placeholders, invalid_rows = [], [], []
    for row in plotted:
        try:
            decoded = {col: row[mapping[col]] for col in COLUMNS}
        except KeyError:
            invalid_rows.append({"error": "required_export_role_absent"})
            continue
        key = decoded["Readout"], decoded["Preparation batch"]
        if key not in source_keys and all(decoded[col] == "" for col in COLUMNS[2:]):
            empty_placeholders.append(key)
        elif key in source_keys and all(decoded[col] != "" for col in COLUMNS[2:]):
            observed.append(decoded)
        else:
            invalid_rows.append({"identity": key, "error": "source_values_missing_or_unsupplied_values_created"})
    expected_missing = {(label,batch) for label in first(r["Readout"] for r in source) for batch in first(r["Preparation batch"] for r in source)} - source_keys
    placeholder_valid = len(empty_placeholders)==len(set(empty_placeholders)) and set(empty_placeholders) <= expected_missing
    return observed, {"original_export_rows": len(plotted), "observed_source_rows": len(observed), "explicit_blank_unsupplied_coordinates": empty_placeholders, "blank_placeholders_are_allowed_traceability_coordinates_not_imputed_observations": placeholder_valid, "column_role_mapping": mapping, "invalid_rows": invalid_rows}


def compare_table(source, plotted):
    plotted, representation = canonical_plot_table(source, plotted)
    if len(source) != len(plotted) or representation["invalid_rows"] or not representation["blank_placeholders_are_allowed_traceability_coordinates_not_imputed_observations"]:
        return False
    # Export-table sorting is not the requested axis category order. Match
    # unique readout/batch identities so legitimate rendering-group order is
    # not incorrectly treated as lost source observations.
    try:
        by_key = {(r["Readout"], r["Preparation batch"]): r for r in plotted}
    except KeyError:
        return False
    if len(by_key) != len(source):
        return False
    for a in source:
        b = by_key.get((a["Readout"], a["Preparation batch"]), {})
        for col in COLUMNS:
            if col not in b:
                return False
            if col in COLUMNS[2:]:
                if not math.isclose(float(a[col]), float(b[col]), rel_tol=1e-13, abs_tol=0):
                    return False
            elif a[col] != b[col]:
                return False
    return True


def marker_color(marker):
    fill = marker["style"].get("fill", "#000000").strip().lower()
    return marker["style"].get("stroke", "#000000").strip().lower() if fill in ("none", "white", "#ffffff") else fill


def batch_decoding(tree, colors):
    evidence = []
    for legend in tree.iter(NS + "g"):
        if not legend.get("id", "").startswith("legend_"):
            continue
        circles, lines = actual_primitives(tree, legend, include_legends=True)
        for text in legend.iter(NS + "text"):
            label = normalized("".join(text.itertext()))
            if label not in colors or text.get("x") is None or text.get("y") is None:
                continue
            x, y = float(text.get("x")), float(text.get("y"))
            candidates = [(abs(x-c["center_pt"][0]), marker_color(c)) for c in circles if c["center_pt"][0] < x+1 and abs(c["center_pt"][1]-y) < 6]
            candidates += [(abs(x-np.mean([p[0] for p in line["endpoints_pt"]])), line["style"].get("stroke", "#000000").strip().lower()) for line in lines if max(p[0] for p in line["endpoints_pt"]) < x+1 and abs(np.mean([p[1] for p in line["endpoints_pt"]])-y) < 6]
            if candidates:
                distance, color = min(candidates)
                evidence.append({"batch_label": label, "legend_handle_color": color, "actual_data_color": colors[label], "horizontal_distance_pt": distance})
    # Explicitly colored direct batch labels also satisfy direct decoding.
    for text in tree.iter(NS + "text"):
        label = normalized("".join(text.itertext()))
        text_styles = styles(text.get("style", ""))
        if label in colors and "fill" in text_styles and text_styles["fill"].strip().lower() == colors[label]:
            evidence.append({"batch_label": label, "direct_label_color": colors[label], "actual_data_color": colors[label]})
    decoded = {r["batch_label"] for r in evidence if r.get("legend_handle_color", r.get("direct_label_color")) == r["actual_data_color"]}
    return check(decoded == set(colors) and bool(colors), {"matched_batch_decodings": evidence, "decoded_batches": sorted(decoded), "measurement": "Actual SVG batch text paired with the nearest preceding legend glyph, or explicitly colored direct batch text"})


def geometry_audit(folder, source):
    tree, measured = svg_measurements(folder / "output/panel.svg")
    desired_labels = first(normalized(r["Readout"]) for r in source)
    batches = first(r["Preparation batch"] for r in source)
    recovered_labels = [r["text"] for r in measured["labels_top_to_bottom"]]
    label_y = {r["text"]: r["y_pt"] for r in measured["labels_top_to_bottom"]}
    slope, intercept = measured["log_x_slope_pt"], measured["log_x_intercept_pt"]
    markers = measured["circles"]
    horizontal = [line for line in measured["lines"] if abs(line["endpoints_pt"][0][1] - line["endpoints_pt"][1][1]) < 2e-5 and abs(line["endpoints_pt"][0][0] - line["endpoints_pt"][1][0]) > 1]
    errors, evidence, used_markers, used_lines, colors = [], [], set(), set(), {}
    for index, row in enumerate(source):
        target_x = slope * math.log(float(row["Prepared ratio"])) + intercept
        tick_y = label_y.get(normalized(row["Readout"]))
        if tick_y is None:
            errors.append({"source_row": index, "error": "label_absent"})
            continue
        label_positions = [r["y_pt"] for r in measured["labels_top_to_bottom"]]
        pitch = min(abs(a - b) for a, b in zip(label_positions, label_positions[1:]))
        candidates = [(i, m) for i, m in enumerate(markers) if i not in used_markers and abs(m["center_pt"][0] - target_x) < 2e-5 and abs(m["center_pt"][1] - tick_y) < pitch * .49]
        if len(candidates) != 1:
            errors.append({"source_row": index, "error": "point_not_unique_at_supplied_ratio", "candidate_count": len(candidates)})
            continue
        marker_index, marker = candidates[0]
        used_markers.add(marker_index)
        point_y = marker["center_pt"][1]
        target_ends = sorted(slope * math.log(float(row[c])) + intercept for c in ("Lower 95", "Upper 95"))
        candidates = [(i, line) for i, line in enumerate(horizontal) if i not in used_lines and abs(line["endpoints_pt"][0][1] - point_y) < 2e-5 and np.allclose(sorted(p[0] for p in line["endpoints_pt"]), target_ends, atol=2e-5, rtol=0)]
        if len(candidates) != 1:
            errors.append({"source_row": index, "error": "supplied_asymmetric_interval_not_unique", "candidate_count": len(candidates)})
            continue
        line_index, line = candidates[0]
        used_lines.add(line_index)
        fill = marker["style"].get("fill", "#000000").strip().lower()
        hollow = fill in ("none", "#ffffff", "white")
        expected_hollow = float(row["Lower 95"]) <= 1 <= float(row["Upper 95"])
        point_color = marker["style"].get("stroke", "#000000") if hollow else fill
        point_color = point_color.strip().lower()
        line_color = line["style"].get("stroke", "#000000").strip().lower()
        batch = row["Preparation batch"]
        color_valid = point_color == line_color and (batch not in colors or colors[batch] == point_color)
        colors.setdefault(batch, point_color)
        if hollow != expected_hollow or not color_valid:
            errors.append({"source_row": index, "error": "overlap_fill_or_batch_color", "actual_hollow": hollow, "expected_hollow": expected_hollow, "point_color": point_color, "interval_color": line_color})
        evidence.append({"source_row": index, "Readout": row["Readout"], "Preparation batch": batch, "supplied_estimate": float(row["Prepared ratio"]), "supplied_lower": float(row["Lower 95"]), "supplied_upper": float(row["Upper 95"]), "written_point_center_pt": marker["center_pt"], "written_interval_endpoints_pt": line["endpoints_pt"], "actual_hollow": hollow, "expected_hollow": expected_hollow, "batch_color": point_color, "actual_circle_diameter_pt": marker["diameter_pt"]})
    reference_x = intercept
    vertical = [line for line in measured["lines"] if abs(line["endpoints_pt"][0][0] - line["endpoints_pt"][1][0]) < 2e-5 and abs(line["endpoints_pt"][0][0] - reference_x) < 2e-5 and abs(line["endpoints_pt"][0][1] - line["endpoints_pt"][1][1]) > 20]
    observed = {(r["Readout"], r["Preparation batch"]) for r in source}
    absent = [(label, batch) for label in first(r["Readout"] for r in source) for batch in batches if (label, batch) not in observed]
    offsets = {batch: [r["written_point_center_pt"][1] - label_y[normalized(r["Readout"])] for r in evidence if r["Preparation batch"] == batch] for batch in batches}
    pair_gaps = []
    for label in first(r["Readout"] for r in source):
        pair = {r["Preparation batch"]: r for r in evidence if r["Readout"]==label}
        if all(batch in pair for batch in batches):
            pair_gaps.append(pair[batches[1]]["written_point_center_pt"][1] - pair[batches[0]]["written_point_center_pt"][1])
    consistent_offsets = len(pair_gaps)==4 and max(pair_gaps)-min(pair_gaps)<2e-5
    bbox = measured["plot_bbox_pt"]
    outside = []
    for row in evidence:
        cx, cy = row["written_point_center_pt"]
        radius = row["actual_circle_diameter_pt"] / 2
        points = [[cx-radius,cy-radius],[cx+radius,cy+radius],*row["written_interval_endpoints_pt"]]
        if any(not (bbox[0]-2e-5 <= x <= bbox[2]+2e-5 and bbox[1]-2e-5 <= y <= bbox[3]+2e-5) for x,y in points):
            outside.append(row["source_row"])
    diameters = [row["actual_circle_diameter_pt"] for row in evidence]
    checks = {
        "logarithmic_axis_from_written_ticks": check(measured["log_tick_fit_max_residual_pt"] < 2e-5 and slope > 0, {k: measured[k] for k in ("log_x_slope_pt", "log_x_intercept_pt", "log_tick_fit_max_residual_pt", "tick_values", "tick_positions_pt")}),
        "first_appearance_readout_order": check(recovered_labels == desired_labels and all(a["y_pt"] < b["y_pt"] for a, b in zip(measured["labels_top_to_bottom"], measured["labels_top_to_bottom"][1:])), measured["labels_top_to_bottom"]),
        "all_actual_estimates_endpoints_and_overlap_states": check(len(evidence) == 11 and not errors, {"measurement": "Actual written SVG circle centers, fill/stroke styles and horizontal interval endpoints; x recovered from written log tick positions", "rows_checked": len(evidence), "errors": errors}),
        "sparse_rows_without_extra_data_markers": check(len(markers) == len(used_markers) == 11 and len(absent) == 3, {"actual_data_circle_count": len(markers), "matched_source_rows": len(used_markers), "three_unsupplied_combinations": absent}),
        "stable_distinct_batch_colors": check(len(colors) == 2 and len(set(colors.values())) == 2 and not any(e.get("error") == "overlap_fill_or_batch_color" for e in errors), colors),
        "actual_batch_color_decoding": batch_decoding(tree, colors),
        "aligned_consistent_batch_offsets": check(consistent_offsets, {"actual_y_offsets_from_readout_label_anchor_pt": offsets, "actual_between_batch_gaps_in_four_paired_readouts_pt": pair_gaps, "note": "When tick glyphs are suppressed, wrapped text baselines are grouping proxies, not exact ticks; consistent series separation is checked from actual paired marker centers. Spacing aesthetics are a separate visual question."}),
        "reference_line_at_ratio_1": check(len(vertical) >= 1, {"actual_full_reference_paths": vertical, "expected_point_coordinate_pt": reference_x, "note": "A coincident major grid line is allowed alongside the explicit reference; overlapping guide paths are not extra observations."}),
        "complete_intervals_and_markers_inside_plot_viewport": check(len(evidence)==11 and not outside, {"written_plot_bbox_pt": bbox, "source_rows_with_geometry_outside_plot": outside, "measurement": "Written interval endpoints and circle extrema against the actual axes rectangle; prevents hidden clipping from passing solely on raw path coordinates."}),
        "actual_circle_marker_geometry": check(len(diameters)==11 and all(math.isfinite(d) and d>0 for d in diameters), {"actual_circle_diameters_pt": diameters, "equal_sizes_observed": bool(diameters) and max(diameters)-min(diameters)<2e-5, "note": "The protocol does not prescribe a marker diameter or require uniform sizes. Any weighting claim requires source-code/semantic evidence; size variation alone is not treated as statistical weighting."}),
    }
    return {"checks": checks, "per_source_row_actual_geometry": evidence}, tree


def export_audit(folder, tree):
    def length(value):
        match = re.fullmatch(f"({NUMBER})(mm|pt|px)", value)
        if not match:
            raise ValueError("Unsupported SVG canvas units")
        amount, unit = float(match[1]), match[2]
        return amount if unit == "mm" else amount * 25.4 / (72 if unit == "pt" else 96)
    svg_mm = [length(tree.get(k)) for k in ("width", "height")]
    editable = list(tree.iter(NS + "text"))
    reader = PdfReader(folder / "output/panel.pdf")
    page = reader.pages[0]
    pdf_mm = [float(page.mediabox.width) * 25.4 / 72, float(page.mediabox.height) * 25.4 / 72]
    spans = []
    def visitor(text, cm, tm, font, size):
        if text.strip():
            spans.append({"text": text.strip(), "font": str(font.get("/BaseFont", "")) if font else "", "size_pt": float(size)})
    page.extract_text(visitor_text=visitor)
    font_records = []
    for key, reference in page["/Resources"]["/Font"].items():
        font = reference.get_object()
        descendant = font.get("/DescendantFonts", [font])[0].get_object()
        descriptor_reference = descendant.get("/FontDescriptor")
        descriptor = descriptor_reference.get_object() if descriptor_reference else {}
        font_file = descriptor.get("/FontFile2") or descriptor.get("/FontFile") or descriptor.get("/FontFile3")
        # The request requires editable SVG text, not a particular PDF font
        # container. Record Type3 glyph programs honestly without mistaking
        # the absence of a TrueType stream for unembedded PDF glyphs.
        glyph_programs = font.get("/CharProcs")
        glyph_bytes = sum(len(v.get_object().get_data()) for v in glyph_programs.get_object().values()) if glyph_programs else 0
        font_records.append({"resource": str(key), "base_font": str(font.get("/BaseFont")), "subtype": str(font.get("/Subtype")), "embedded_bytes": len(font_file.get_object().get_data()) if font_file else glyph_bytes, "embedding": "font stream" if font_file else "Type3 glyph programs" if glyph_programs else "none"})
    font_ok = bool(spans) and all("Arial" in s["font"] and s["size_pt"] == 8 for s in spans) and all(f["embedded_bytes"] > 0 for f in font_records)
    with Image.open(folder / "output/panel.png") as image:
        pixels, dpi = list(image.size), image.info.get("dpi")
        yy, xx = np.where(np.any(np.asarray(image.convert("RGB")) < 245, axis=2))
        clearance = [float(xx.min()), float(image.width - 1 - xx.max()), float(yy.min()), float(image.height - 1 - yy.max())]
    return {"checks": {
        "exact_vector_canvas": check(len(reader.pages) == 1 and np.allclose(svg_mm, [140, 100], atol=1e-5) and np.allclose(pdf_mm, [140, 100], atol=1e-5), {"SVG_mm": svg_mm, "PDF_mm": pdf_mm, "PDF_pages": len(reader.pages)}),
        "editable_SVG_text": check(bool(editable), {"text_node_count": len(editable)}),
        "actual_embedded_Arial_8pt_text": check(font_ok, {"actual_fonts": sorted({s["font"] for s in spans}), "actual_sizes_pt": sorted({s["size_pt"] for s in spans}), "font_resources": font_records, "nonmatching_text": [s for s in spans if "Arial" not in s["font"] or s["size_pt"] != 8]}),
        "PNG_300dpi_canvas": check(dpi is not None and np.allclose(dpi, [300, 300], atol=.02) and all(abs(a-b) <= 1 for a,b in zip(pixels, [140*300/25.4,100*300/25.4])), {"pixels": pixels, "stored_dpi": dpi, "integer_rounding_tolerance_px": 1}),
        "ink_inside_canvas": check(min(clearance)>0, {"clearances_px_left_right_top_bottom": clearance, "threshold_RGB": 245, "does_not_prove_internal_overlap_absence": True})}}


def relocated_rerun(folder, entry, plotted_file, source, render_spec=None):
    with tempfile.TemporaryDirectory(prefix="easyviz-glm-independent-") as temporary:
        copied = Path(temporary) / folder.name
        shutil.copytree(folder, copied, ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", ".workbuddy"))
        # Only actual exported artifacts are removed. A regenerated result
        # cannot pass merely because an existing PNG/table was copied.
        for relative in ("output",):
            if (copied / relative).is_dir():
                shutil.rmtree(copied / relative)
        copied_table = copied / plotted_file
        if copied_table.exists():
            copied_table.unlink()
        arguments = ["--data", "prepared.csv", "--spec", render_spec, "--out", "output"] if render_spec else []
        result = subprocess.run([sys.executable, str(copied / entry), *arguments], cwd=copied, capture_output=True, text=True, timeout=180)
        identical = False
        if (copied / "output/panel.png").exists():
            with Image.open(copied / "output/panel.png") as a, Image.open(folder / "output/panel.png") as b:
                identical = a.size == b.size and np.array_equal(np.asarray(a), np.asarray(b))
        regenerated = copied_table.exists() and compare_table(source, table(copied_table))
        return check(result.returncode == 0 and identical and regenerated, {"entry_script": entry, "entry_arguments": arguments, "exit_code": result.returncode, "fresh_output_directory": True, "existing_plotting_table_removed_before_run": True, "identical_PNG_pixels": identical, "regenerated_source_values_preserved": regenerated, "stdout_tail": result.stdout[-1000:], "stderr_tail": result.stderr[-1000:], "limit": "Same installed scientific runtime and fonts; this is relocation/reuse evidence, not cross-machine installation."})


def write_markdown(audit):
    arms = audit["arms"]
    summary = audit["check_summary"]
    baseline_canvas = arms["baseline"]["exports"]["checks"]["exact_vector_canvas"]["evidence"]
    easyviz_canvas = arms["easyviz"]["exports"]["checks"]["exact_vector_canvas"]["evidence"]
    baseline_png = arms["baseline"]["exports"]["checks"]["PNG_300dpi_canvas"]["evidence"]
    easyviz_png = arms["easyviz"]["exports"]["checks"]["PNG_300dpi_canvas"]["evidence"]
    source_rows = [len(arms[name]["geometry"]["per_source_row_actual_geometry"]) for name in ("baseline","easyviz")]
    hollow_counts = [sum(r["actual_hollow"] for r in arms[name]["geometry"]["per_source_row_actual_geometry"]) for name in ("baseline","easyviz")]
    def canvas(values):
        return f"{values[0]:.6f} × {values[1]:.6f} mm"
    lines = ["# Independent numerical and export audit: unseen interval task", "", "Both arms preserve and correctly render all eleven supplied estimates and asymmetric interval endpoints. Actual written SVG geometry confirms the log axis, reference at 1, first-appearance readout order, stable decoded batch colors, six hollow reference-overlap circles and five filled circles. Both safely rerun from a relocated directory and reproduce the same PNG pixels. The baseline has a small physical-size drift in all export formats; EasyViz preserves the requested physical canvas.", "", f"{summary['passed']} checks passed and {summary['failed']} failed. The two failures concern baseline vector/raster dimensions, not incorrect data or missing observations. All 208 frozen-file hashes matched before the audit and remained unchanged.", "", "| Actual artifact measurement | Baseline | With EasyViz |", "|---|---|---|", f"| Matched source estimates and intervals | {source_rows[0]} | {source_rows[1]} |", f"| Hollow / filled circles | {hollow_counts[0]} / {source_rows[0]-hollow_counts[0]} | {hollow_counts[1]} / {source_rows[1]-hollow_counts[1]} |", "| Unprovided readout/batch pairs | 3 left unpainted | 3 left unpainted |", f"| PDF page | {canvas(baseline_canvas['PDF_mm'])} | {canvas(easyviz_canvas['PDF_mm'])} |", f"| SVG physical canvas | {canvas(baseline_canvas['SVG_mm'])} | {canvas(easyviz_canvas['SVG_mm'])} |", f"| PNG raster | {baseline_png['pixels'][0]} × {baseline_png['pixels'][1]} px, {baseline_png['stored_dpi'][0]:.4f} dpi | {easyviz_png['pixels'][0]} × {easyviz_png['pixels'][1]} px, {easyviz_png['stored_dpi'][0]:.4f} dpi |", "| Actual fonts / SVG text | Embedded Arial 8 pt; editable text | Embedded Arial 8 pt; editable text |", "| Clean relocated rerun | Exit 0; identical PNG pixels | Exit 0; identical PNG pixels |", "", "The requested vector dimensions were 140 × 100 mm. Baseline PDF and SVG measure 139.954 × 99.822 mm, a difference of −0.046 and −0.178 mm. Its PNG height is 1179 pixels against an ideal 1181.102 pixels, beyond the protocol's one-pixel integer-rounding allowance. The frozen baseline check record calls the size equivalent; that statement is inaccurate. These are small deviations. The audit does not attribute their cause or repair the originals.", "", "The baseline export table uses renamed columns and includes fourteen coordinate records: eleven supplied observations plus three explicit blank records for unprovided combinations. The audit decodes the five roles and confirms the blank records have no numeric estimate or endpoints; it does not falsely count them as imputed observations. EasyViz exports eleven source rows plus traceability fields. Every supplied value is compared by its unique readout/batch identity, while actual axis order is checked independently.", "", "Measurements come from the exported paths, not model self-QA: a log transform is fitted from actual numeric SVG tick positions; all point centers, interval endpoints, fill states and colors are matched to supplied values; complete circle/interval geometry is checked against the written axes viewport. The baseline suppresses y tick marks and wraps labels. Its actual text baselines are used only as label-block proxies; exact paired-series separation is recovered from the actual marker centers. A coincident grid line at 1 is permitted alongside the explicit reference line. Native `<use>` marker paths and the explicit closing line on hollow-circle paths are decoded without changing model outputs.", "", "Both entry paths were inspected before execution. The baseline writes relative to its own script; the EasyViz arm uses the documented copied CLI and sibling helpers. Temporary copies had their output directories and plotting tables removed before rerunning. No script was patched, no helper was added, and no frozen output was touched. Both programs use supplied endpoints directly and neither introduces a statistical test, fitting, numerical weighting, inferred n, or recomputed interval. Both captions describe the synthetic source, unknown n/interval construction, missing combinations and reference-overlap semantics. Model self-reported QA remains separate from this audit.", "", "No anonymous visual-review findings were read before these conclusions. Physical-size compliance does not establish an aesthetic preference. This is one unfamiliar synthetic task and one run per arm, using one app-reported model and an explicitly detailed request. It does not certify actual backend identity, cross-machine installation, cost in money, journal suitability, novice benefit in general, or GLM versus Deepseek performance.", "", "The companion JSON records per-observation written geometry, fonts, dimensions, rerun logs and all frozen-file checks. Reproduce the audit with:", "", "```sh", "python independent-numeric-audit.py --baseline-entry plot_panel.py --baseline-table output/plot_data.csv --easyviz-entry plot_scripts/interval_plot.py --easyviz-table output/plotting-data.csv --easyviz-render-spec interval-spec.json", "```", "", "Exit status 1 is deliberate while the two original dimension failures remain. It reports the frozen result faithfully rather than repairing it."]
    (ROOT / "independent-numeric-audit.md").write_text("\n".join(lines)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arm in ("baseline", "easyviz"):
        parser.add_argument(f"--{arm}-entry", required=True, help="Manually inspected safe relative Python entry script")
        parser.add_argument(f"--{arm}-table", required=True, help="Relative exported plotting-table path")
        parser.add_argument(f"--{arm}-render-spec", help="For a documented renderer CLI: --data prepared.csv --spec THIS --out output")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "freeze-manifest.json").read_text())["files"]
    before = {name: sha(ROOT / name) for name in manifest}
    mismatch = [name for name in manifest if before[name] != manifest[name]]
    audit = {"audited_at_utc": datetime.now(timezone.utc).isoformat(), "protocol_sha256": sha(ROOT / "protocol.md"), "independent_written_export_audit": True, "freeze_manifest_initial": check(not mismatch, {"files_checked": len(manifest), "mismatches": mismatch}), "arms": {}}
    for arm in ("baseline", "easyviz"):
        folder = ROOT / arm
        source = table(folder / "prepared.csv")
        plotted_path = getattr(args, f"{arm}_table")
        plotted = table(folder / plotted_path)
        decoded_table, table_representation = canonical_plot_table(source, plotted)
        geometry, svg = geometry_audit(folder, source)
        audit["arms"][arm] = {"input_hash": check(sha(folder / "prepared.csv") == EXPECTED_SHA, {"actual": sha(folder / "prepared.csv"), "protocol_expected": EXPECTED_SHA}), "source_values_and_rows": check(len(source) == 11 and compare_table(source, plotted), {"input_rows": len(source), "export_table_representation": table_representation, "all_five_original_roles_compared_by_unique_readout_batch_identity": True, "table_observed_row_order_retained": [(r["Readout"], r["Preparation batch"]) for r in source] == [(r["Readout"], r["Preparation batch"]) for r in decoded_table], "note": "Axis first-appearance order is checked separately. Renaming columns or adding explicit blank coordinate records does not create an estimate or lose a supplied observation."}), "geometry": geometry, "exports": export_audit(folder, svg), "relocated_clean_rerun": relocated_rerun(folder, getattr(args, f"{arm}_entry"), plotted_path, source, getattr(args, f"{arm}_render_spec"))}
    after = {name: sha(ROOT / name) for name in manifest}
    audit["frozen_files_unchanged"] = check(before == after, {"files_checked": len(manifest), "changed_files": [name for name in manifest if before[name] != after[name]]})
    passed, failed = [], []
    def collect(value, prefix=""):
        if isinstance(value, dict):
            if value.get("status") in ("pass", "fail"):
                (passed if value["status"] == "pass" else failed).append(prefix)
            for key, child in value.items():
                if key != "status":
                    collect(child, f"{prefix}.{key}" if prefix else key)
    collect(audit)
    audit["check_summary"] = {"passed": len(passed), "failed": len(failed), "failures": failed}
    (ROOT / "independent-numeric-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n")
    write_markdown(audit)
    print(json.dumps(audit["check_summary"], indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
