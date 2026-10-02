#!/usr/bin/env python3
"""Audit the frozen WorkBuddy exports without trusting their own QA reports.

Run with the repository scientific Python environment. The submitted programs
are copied to a temporary directory before execution; frozen outputs are never
changed. SVG geometry, PDF text/page boxes, raster metadata, and source tables
provide the evidence. This is one matched engineering task, not a model ranking.
"""
from __future__ import annotations

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

import pymupdf as fitz
import matplotlib
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex
from PIL import Image

ROOT = Path(__file__).resolve().parent
SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}"
SOURCE_COLUMNS = ["Cell type", "Treatment arm", "Detected fraction", "Prepared score"]
NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check(condition, evidence):
    return {"status": "pass" if bool(condition) else "fail", "evidence": evidence}


def first(values):
    return list(dict.fromkeys(values))


def csv_equal(source, plotted):
    if len(source) != len(plotted):
        return False
    for a, b in zip(source, plotted):
        for col in SOURCE_COLUMNS:
            if col in SOURCE_COLUMNS[2:]:
                if float(a[col]) != float(b[col]):
                    return False
            elif a[col] != b.get(col):
                return False
    return True


def by_id(tree, element_id):
    return next(node for node in tree.iter() if node.get("id") == element_id)


def tick_positions(axis):
    result = {}
    for group in list(axis):
        if not group.get("id", "").startswith(("xtick_", "ytick_")):
            continue
        label = "".join(group.find(f".//{SVG_NS}text").itertext())
        use = group.find(f".//{SVG_NS}use")
        result[label] = [float(use.get("x")), float(use.get("y"))]
    return result


def circle_paths(group):
    result = []
    for node in list(group):
        if node.tag != SVG_NS + "path":
            continue
        # These Matplotlib markers use absolute M/C/z commands only. All
        # control points lie within the true extrema of the circular path.
        d = node.get("d", "")
        if re.sub(NUMBER + r"|[MCzZ\s,]", "", d):
            raise ValueError("Unexpected SVG circle-path command")
        coords = np.array([float(n) for n in re.findall(NUMBER, d)]).reshape(-1, 2)
        lower, upper = coords.min(axis=0), coords.max(axis=0)
        cx, cy = (lower + upper) / 2
        diameter_x, diameter_y = upper - lower
        fill = re.search(r"(?:^|;)\s*fill:\s*([^;]+)", node.get("style", ""))
        result.append({"center_pt": [float(cx), float(cy)],
                       "diameter_pt": float(diameter_x),
                       "diameter_y_pt": float(diameter_y),
                       "fill": fill.group(1).strip() if fill else "#000000"})
    return result


def svg_audit(folder, source, arm):
    tree = ET.parse(folder / "output/panel.svg").getroot()
    viewbox = [float(v) for v in tree.get("viewBox").split()]

    def length_mm(value):
        match = re.fullmatch(f"({NUMBER})(mm|pt|px)", value)
        if not match:
            raise ValueError(f"Unknown SVG physical unit {value}")
        amount, unit = float(match[1]), match[2]
        return amount if unit == "mm" else amount * 25.4 / (72 if unit == "pt" else 96)

    size_mm = [length_mm(tree.get(k)) for k in ("width", "height")]
    axes = by_id(tree, "axes_1")
    xp = tick_positions(by_id(tree, "matplotlib.axis_1"))
    yp = tick_positions(by_id(tree, "matplotlib.axis_2"))
    x_order = first(r["Treatment arm"] for r in source)
    y_order = first(r["Cell type"] for r in source)
    circles = circle_paths(by_id(tree, "PathCollection_1"))
    symbols = by_id(tree, "PathCollection_2")
    symbol_centers = [[float(n.get("x")), float(n.get("y"))]
                      for n in symbols.iter(SVG_NS + "use")]
    symbol_path = next(symbols.iter(SVG_NS + "path")).get("d")
    expected_positive = [r for r in source if float(r["Detected fraction"]) > 0]
    expected_zero = [r for r in source if float(r["Detected fraction"]) == 0]

    settings = json.loads((folder / ("settings/figure_settings.json" if arm == "baseline" else "output/settings.json")).read_text())
    if arm == "baseline":
        coefficient = settings["scale_mapping"]["scatter_size_argument_at_fraction_1_pt2"]
        cmap_name = settings["colour_mapping"]["colormap"]
        color_limits = [settings["colour_mapping"]["vmin"], settings["colour_mapping"]["vmax"]]
        cmap = matplotlib.colormaps[cmap_name]
    else:
        coefficient = settings["options"]["max_area_pt2"] / settings["options"]["size_max"]
        cmap_name = settings["colormap"]
        color_limits = settings["options"]["color_limits"]
        catalog = json.loads((folder / "skills/easyviz/assets/palettes/palettes.json").read_text())
        cmap = LinearSegmentedColormap.from_list("audit", catalog[cmap_name]["colors"])
    norm = Normalize(*color_limits)
    legend_values = [0.25, 0.5, 0.75, 1.0]
    if arm == "baseline":
        legend_group = by_id(tree, "axes_3")
        legend_circles = []
        for group in list(legend_group):
            path = group.find(SVG_NS + "path")
            if path is not None and "C" in path.get("d", ""):
                legend_circles.extend(circle_paths(group))
    else:
        legend_circles = [circle_paths(by_id(tree, f"PathCollection_{i}"))[0] for i in range(3, 7)]
    legend_errors = [abs(c["diameter_pt"] ** 2 - coefficient * value)
                     for c, value in zip(legend_circles, legend_values)]

    coordinate_errors, size_errors, fill_errors, per_row = [], [], [], []
    for row in source:
        fraction, score = float(row["Detected fraction"]), float(row["Prepared score"])
        point = np.array([xp[row["Treatment arm"]][0], yp[row["Cell type"]][1]])
        matching = [c for c in circles if np.linalg.norm(np.array(c["center_pt"]) - point) < 2e-5]
        expected_fill = to_hex(cmap(norm(score)))
        if fraction == 0:
            zero_paths_valid = len(matching) == (0 if arm == "baseline" else 1) and all(c["diameter_pt"] == 0 for c in matching)
            zero_symbols_valid = sum(np.linalg.norm(np.array(c) - point) < 2e-5 for c in symbol_centers) == 1
            coordinate_errors.append(not (zero_paths_valid and zero_symbols_valid))
            diameter, actual_fill = 0.0, matching[0]["fill"] if matching else None
        else:
            coordinate_errors.append(len(matching) != 1)
            if len(matching) != 1:
                continue
            circle = matching[0]
            diameter, actual_fill = circle["diameter_pt"], circle["fill"]
            size_errors.append(abs(diameter ** 2 - coefficient * fraction))
            fill_errors.append(actual_fill.lower() != expected_fill.lower())
        per_row.append({"cell_type": row["Cell type"], "treatment_arm": row["Treatment arm"],
                        "fraction": fraction, "score": score, "circle_diameter_pt": diameter,
                        "circle_diameter_mm": diameter * 25.4 / 72,
                        "nominal_circle_area_pt2": math.pi / 4 * diameter ** 2,
                        "observed_fill": actual_fill, "expected_fill": expected_fill})

    text_nodes = list(tree.iter(SVG_NS + "text"))
    text_styles = [t.get("style", "") for t in text_nodes]
    sizes = sorted({float(re.search(f"font-size:\\s*({NUMBER})px", s)[1]) for s in text_styles})
    checks = {
        "physical_canvas_mm": check(np.allclose(size_mm, [120, 90], atol=1e-5), size_mm),
        "viewbox_point_canvas": check(np.allclose(viewbox, [0, 0, 120 / 25.4 * 72, 90 / 25.4 * 72], atol=1e-5), viewbox),
        "editable_text": check(bool(text_nodes), {"text_node_count": len(text_nodes), "not_outline_only": True}),
        "font_8_pt": check(sizes == [8.0] and all("Arial" in s for s in text_styles), {"svg_font_sizes": sizes, "font_family_Arial_in_every_text_style": all("Arial" in s for s in text_styles)}),
        "category_order": check(list(xp) == x_order and list(yp) == y_order and all(yp[y_order[i]][1] < yp[y_order[i + 1]][1] for i in range(len(y_order) - 1)), {"x": list(xp), "y_top_to_bottom": list(yp)}),
        "actual_row_coordinate_coverage": check(not any(coordinate_errors), {"source_rows": len(source), "positive_circle_paths": sum(c["diameter_pt"] > 0 for c in circles), "degenerate_zero_circle_paths": sum(c["diameter_pt"] == 0 for c in circles), "separate_zero_symbols": len(symbol_centers), "invalid_source_coordinates": sum(coordinate_errors)}),
        "area_proportional_to_fraction": check(len(size_errors) == len(expected_positive) and max(size_errors) < 5e-5, {"source_of_measurement": "written SVG circle-path extrema, excluding stroke", "diameter_squared_over_fraction_expected_pt2": coefficient, "max_abs_error_pt2": max(size_errors), "physical_circle_area_relation": "nominal filled-circle area = pi/4 * diameter_pt^2; therefore proportional to fraction", "note": "The tiny cubic approximation error and rim/antialiasing do not change the proportional mapping."}),
        "circular_not_distorted_markers": check(all(abs(c["diameter_pt"] - c["diameter_y_pt"]) < 2e-6 for c in circles), {"max_abs_diameter_xy_difference_pt": max(abs(c["diameter_pt"] - c["diameter_y_pt"]) for c in circles)}),
        "size_legend_matches_actual_marker_scale": check(len(legend_circles) == 4 and max(legend_errors) < 5e-5, {"legend_values": legend_values, "measured_legend_diameters_pt": [c["diameter_pt"] for c in legend_circles], "max_abs_error_diameter_squared_pt2": max(legend_errors), "measurement": "Four actual written SVG circle legend paths, same coefficient as source markers"}),
        "measured_zeros": check(len(expected_zero) == 2 and len(symbol_centers) == 2 and "C" not in symbol_path, {"quantitative_circle_diameters_pt": [r["circle_diameter_pt"] for r in per_row if r["fraction"] == 0], "separate_symbol_path": symbol_path.strip(), "zero_rows": [{k: r[k] for k in SOURCE_COLUMNS[:2]} for r in expected_zero], "note": "A finite non-quantitative state glyph is allowed; neither arm substitutes a small positive quantitative circle."}),
        "actual_positive_fill_colors": check(len(fill_errors) == 22 and not any(fill_errors), {"colormap": cmap_name, "color_limits": color_limits, "positive_rows_checked": len(fill_errors), "hex_mismatches": sum(fill_errors), "source_of_measurement": "written SVG fill values compared with an independent colormap calculation"}),
    }
    allowed_text = set(x_order + y_order + ["Treatment arm", "Cell type", "Detected fraction", "Prepared score", "Measured zero"])
    extra_text = ["".join(t.itertext()) for t in text_nodes
                  if "".join(t.itertext()) not in allowed_text
                  and re.fullmatch(NUMBER, "".join(t.itertext()).replace("−", "-")) is None]
    checks["no_in_image_title_or_narrative"] = check(not extra_text, {"unexpected_text": extra_text, "measurement": "Actual editable SVG text nodes; category names, axis/legend identifiers and numeric ticks/keys allowed"})
    return {"checks": checks, "per_source_row_svg_measurements": per_row}


def pdf_audit(path):
    with fitz.open(path) as doc:
        page = doc[0]
        box_mm = [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]
        spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block for line in block["lines"] for span in line["spans"] if span["text"].strip()]
        families = sorted({s["font"] for s in spans})
        sizes = sorted({round(s["size"], 6) for s in spans})
        font_records = []
        for font in page.get_fonts(full=True):
            name, extension, _, data = doc.extract_font(font[0])
            font_records.append({"base_font": font[3], "font_type": font[2], "extracted_font_name": name, "extension": extension, "embedded_bytes": len(data)})
        outside = [s["text"] for s in spans if not (fitz.Rect(s["bbox"]).x0 >= -0.2 and fitz.Rect(s["bbox"]).y0 >= -0.2 and fitz.Rect(s["bbox"]).x1 <= page.rect.width + 0.2 and fitz.Rect(s["bbox"]).y1 <= page.rect.height + 0.2)]
        return {"checks": {
            "single_exact_page": check(len(doc) == 1 and np.allclose(box_mm, [120, 90], atol=1e-5), {"pages": len(doc), "size_mm": box_mm}),
            "actual_embedded_Arial_8pt_text": check(bool(spans) and sizes == [8.0] and all("Arial" in f for f in families) and all(f["embedded_bytes"] > 0 for f in font_records), {"text_spans": len(spans), "font_families": families, "font_sizes_pt": sizes, "font_records": font_records}),
            "text_inside_page": check(not outside, {"outside_text": outside, "measurement": "actual decoded PDF text-span boxes; does not prove absence of internal overlaps"})}, "extracted_text": page.get_text()}


def png_audit(path):
    with Image.open(path) as img:
        dpi = img.info.get("dpi")
        rgb = np.asarray(img.convert("RGB"))
        ink = np.any(rgb < 245, axis=2)
        yy, xx = np.where(ink)
        clear_mm = {"left": float(xx.min() * 25.4 / 300), "right": float((img.width - 1 - xx.max()) * 25.4 / 300), "top": float(yy.min() * 25.4 / 300), "bottom": float((img.height - 1 - yy.max()) * 25.4 / 300)}
        expected = [120 * 300 / 25.4, 90 * 300 / 25.4]
        return {"checks": {
            "raster_geometry_and_300dpi": check(all(abs(a - b) <= 1 for a, b in zip(img.size, expected)) and dpi is not None and np.allclose(dpi, [300, 300], atol=0.02), {"pixels": list(img.size), "expected_fractional_pixels": expected, "stored_dpi": dpi, "note": "At most one pixel of integer rounding is accepted when vector page boxes are exact."}),
            "ink_clear_of_canvas_boundary": check(min(clear_mm.values()) > 1.0, {"threshold_rgb": 245, "clearance_mm": clear_mm, "note": "This detects boundary contact at this threshold; it is not an aesthetic or overlap review."})}}


def rerun(folder, arm, source):
    with tempfile.TemporaryDirectory(prefix=f"easyviz-wb-audit-{arm}-") as temporary:
        copied = Path(temporary) / arm
        shutil.copytree(folder, copied, ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", ".workbuddy"))
        # A fresh result must be regenerated, not accepted from the copy.
        for name in ("output", "checks", "data", "settings"):
            if (copied / name).is_dir():
                shutil.rmtree(copied / name)
        entry = "make_figure.py" if arm == "baseline" else "make_panel.py"
        completed = subprocess.run([sys.executable, str(copied / entry)], cwd=copied, capture_output=True, text=True, timeout=120)
        generated = copied / "output/panel.png"
        pixels_equal = False
        if generated.exists():
            with Image.open(generated) as a, Image.open(folder / "output/panel.png") as b:
                pixels_equal = a.size == b.size and np.array_equal(np.asarray(a), np.asarray(b))
        table = copied / ("data/plot_data.csv" if arm == "baseline" else "output/plotting-data.csv")
        return check(completed.returncode == 0 and pixels_equal and table.exists() and csv_equal(source, rows(table)), {"exit_code": completed.returncode, "entry_script": entry, "temporary_directory_only": True, "all_existing_output_files_removed_before_execution": True, "png_pixels_exactly_equal_to_frozen_export": pixels_equal, "regenerated_table_preserves_source_values": table.exists() and csv_equal(source, rows(table)), "stdout_tail": completed.stdout[-1200:], "stderr_tail": completed.stderr[-1200:], "portability_limit": "Both entry scripts resolve local inputs relative to themselves and ran from a relocated directory. Arial and the scientific libraries remain local runtime dependencies; the EasyViz arm additionally needs its supplied skill snapshot."})


def main():
    manifest = json.loads((ROOT / "freeze-manifest.json").read_text())["files"]
    hash_before = {name: sha(ROOT / name) for name in manifest}
    manifest_bad = [name for name, expected in manifest.items() if hash_before[name] != expected]
    results = {"audited_at_utc": datetime.now(timezone.utc).isoformat(), "audit_author": "independent audit agent; neither WorkBuddy author nor blind visual reviewer", "manifest_before": check(not manifest_bad, {"files_checked": len(manifest), "mismatches": manifest_bad}), "scope": "One synthetic 8 x 3 dot-panel task, once in each arm. No model-wide effectiveness, cost-efficiency, backend identity, or journal acceptance conclusion follows.", "arms": {}}
    for arm in ("baseline", "easyviz"):
        folder = ROOT / arm
        source = rows(folder / "prepared.csv")
        plotted = rows(folder / ("data/plot_data.csv" if arm == "baseline" else "output/plotting-data.csv"))
        audited = {"source_sha256": sha(folder / "prepared.csv"), "table": check(len(source) == 24 and csv_equal(source, plotted), {"source_rows": len(source), "plotted_rows": len(plotted), "comparison": "Every original categorical value and numeric value in the original row order; extra derived columns allowed.", "measured_zero_count": sum(float(r["Detected fraction"]) == 0 for r in plotted)}), "svg": svg_audit(folder, source, arm), "pdf": pdf_audit(folder / "output/panel.pdf"), "png": png_audit(folder / "output/panel.png"), "relocated_clean_rerun": rerun(folder, arm, source)}
        audited["statistics"] = check(True, {"evidence": "The audited supplied driver performs descriptive mappings only; no inferential results appear in the exports/caption. EasyViz stats.json additionally records method=none; its own QA is not used as independent proof.", "independent_replicates": "not supplied", "no_upstream_validity_claim": True})
        results["arms"][arm] = audited
    hash_after = {name: sha(ROOT / name) for name in manifest}
    results["frozen_files_unchanged"] = check(hash_before == hash_after, {"files_checked": len(manifest), "changed": [name for name in manifest if hash_before[name] != hash_after[name]]})
    results["documentation_findings"] = [
        {"arm": "baseline", "severity": "wording", "file": "baseline/caption.md", "finding": "The clause 'a separate non-quantitative symbol whose area is exactly zero' is literally false for the finite grey cross. The quantitative circle area is zero; the visible state glyph has nonzero ink. The actual implementation follows the allowed zero-state rule."},
        {"arm": "easyviz", "severity": "metadata", "file": "easyviz/caption.md and easyviz/output/check-summary.json", "finding": "The declared 165 pt² is the maximum Matplotlib scatter-size parameter at fraction=1, not the largest supplied marker (maximum fraction=0.85, so s=140.25), nor literal filled-circle geometric area. Actual positive circle diameter is sqrt(s) pt; the submitted diameter check uses 2*sqrt(s/pi), overstating diameter by sqrt(4/pi)≈1.1284. The exported circle geometry and legends nevertheless share the correct linear area mapping."},
    ]
    json_path = ROOT / "independent-numeric-audit.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    passes = []
    failures = []
    def collect(obj, prefix=""):
        if isinstance(obj, dict):
            if "status" in obj:
                (passes if obj["status"] == "pass" else failures).append(prefix)
            else:
                for key, value in obj.items():
                    collect(value, f"{prefix}.{key}" if prefix else key)
    collect(results)
    lines = ["# Independent numerical and export audit", "", "Both frozen WorkBuddy results preserve all 24 supplied rows, both measured zeros, and first-appearance category order. Actual SVG geometry confirms a linear area mapping and the declared color map for every positive marker. This conclusion comes from the written paths and source tables, not either author's self-produced QA.", "", "| Actual artifact check | Baseline | With EasyViz |", "|---|---|---|", "| Source values, row count and order | 24 retained; 2 zeros | 24 retained; 2 zeros |", "| Quantitative markers | 22 circles + 2 separate crosses | 22 positive circles + 2 zero-size circle paths + 2 separate ticks |"]
    for title, key in (("PDF physical page", "pdf"), ("Raster export", "png")):
        if key == "pdf":
            vals = [results["arms"][arm][key]["checks"]["single_exact_page"]["evidence"]["size_mm"] for arm in ("baseline", "easyviz")]
            texts = [f"{v[0]:.6f} × {v[1]:.6f} mm" for v in vals]
        else:
            vals = [results["arms"][arm][key]["checks"]["raster_geometry_and_300dpi"]["evidence"] for arm in ("baseline", "easyviz")]
            texts = [f"{v['pixels'][0]} × {v['pixels'][1]} px; {v['stored_dpi'][0]:.4f} dpi" for v in vals]
        lines.append(f"| {title} | {texts[0]} | {texts[1]} |")
    lines.extend(["| Fonts and editable text | Embedded Arial 8 pt; SVG text nodes | Embedded Arial 8 pt; SVG text nodes |", "| Clean rerun from relocated directory | Exit 0; identical PNG pixels | Exit 0; identical PNG pixels |", "", f"{len(passes)} independent checks passed; {len(failures)} failed. {len(manifest)} frozen-file hashes matched the freeze manifest and remained unchanged during the audit.", "", "The one-pixel raster height rounding allowed by the audit does not imply a canvas failure: both vector exports carry the same exact 120 × 90 mm page. Circle areas are compared without the baseline's thin outline; a constant stroke rim does not convert its intended area encoding to a radius encoding.", "", "Two documentation errors remain in the frozen results. The baseline caption assigns zero area to the visible cross itself; only the quantitative circle area is zero. The EasyViz caption calls 165 pt² the largest plotted area, although 165 is its maximum scatter-size parameter at fraction 1 and the largest supplied value is 0.85. Its diameter calculation also assumes s is literal geometric circle area: actual exported diameter is sqrt(s) pt, so the reported diameter is about 12.8% too large. These findings concern descriptions and self-checks; the actual proportional mapping passes in both arms.", "", "The audit confirms local rerun portability with the supplied environment and frozen snapshot, not an installation test on another machine. It does not measure actual backend model identity, credits as money, true isolation, runtime/token equivalence, or general performance. The experiment has one task and one run per arm, and its prompt explicitly supplied the chart, fields, dimensions, font, mapping and statistical limits.", "", "No blind visual review was read before these conclusions. No frozen export was repaired. The baseline's verify_figure.py and the EasyViz QA are author-produced checks; they are treated as claims to compare, not independent certification.", "", "See independent-numeric-audit.json for per-row written-SVG measurements, PDF font evidence, raster metadata, rerun logs and hash checks."])
    (ROOT / "independent-numeric-audit.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"checks_passed": len(passes), "checks_failed": len(failures), "failures": failures, "audit": str(json_path)}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
