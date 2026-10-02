#!/usr/bin/env python3
"""Independently verify written scatter exports and an engineering transfer.

The numerical audit never imports the renderer. It compares the supplied table
with actual SVG paths, SVG tick transforms, PDF page/font objects and PNG pixels.
The optional transfer command invokes the ordinary renderer as a subprocess,
then audits its exports with the same independent measurements.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
NS = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}"
NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
NUMERIC_SOURCE_COLUMNS = {"me3", "me5", "md3", "md5", "meand", "mdd", "pv", "fdr", "prob", "logq"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check(condition, evidence):
    return {"status": "pass" if bool(condition) else "fail", "evidence": evidence}


def by_id(tree, name):
    return next(n for n in tree.iter() if n.get("id") == name)


def close(a, b):
    return math.isclose(float(a), float(b), rel_tol=2e-13, abs_tol=0)


def circle(path):
    d = path.get("d", "")
    if re.sub(NUMBER + r"|[MCzZ\s,]", "", d):
        raise ValueError("Unexpected circular SVG path commands")
    coords = np.array([float(v) for v in re.findall(NUMBER, d)]).reshape(-1, 2)
    low, high = coords.min(axis=0), coords.max(axis=0)
    diameter = high - low
    fill = re.search(r"(?:^|;)\s*fill:\s*([^;]+)", path.get("style", ""))
    return {"center_pt": ((low + high) / 2).tolist(),
            "diameter_pt": float(diameter[0]),
            "diameter_y_pt": float(diameter[1]),
            "nominal_circle_fill_area_pt2": math.pi / 4 * float(diameter[0]) ** 2,
            "fill": fill[1].strip().lower() if fill else "#000000"}


def path_circles(group):
    # Matplotlib writes each variable-size marker directly for these cases.
    # Refuse an unfamiliar representation instead of silently overlooking it.
    if list(group.iter(NS + "use")):
        raise ValueError("This audit expects direct variable-size marker paths")
    return [circle(n) for n in list(group) if n.tag == NS + "path"]


def numeric_tick_transform(axis, coordinate):
    values, positions = [], []
    for group in list(axis):
        if not group.get("id", "").startswith(("xtick_", "ytick_")):
            continue
        text = group.find(f".//{NS}text")
        value = float("".join(text.itertext()).replace("−", "-"))
        marker = group.find(f".//{NS}use")
        values.append(value)
        positions.append(float(marker.get(coordinate)))
    slope, intercept = np.polyfit(values, positions, 1)
    residual = float(np.max(np.abs(np.asarray(positions) - (np.asarray(values) * slope + intercept))))
    if residual > 2e-6:
        raise ValueError("The written numeric tick positions are not a consistent linear transform")
    return {"slope_pt_per_unit": float(slope), "intercept_pt": float(intercept),
            "max_tick_fit_residual_pt": residual, "tick_values": values,
            "tick_positions_pt": positions}


def svg_length_mm(value):
    match = re.fullmatch(f"({NUMBER})(mm|pt|px)", value)
    if not match:
        raise ValueError(f"Unknown SVG unit: {value}")
    amount, unit = float(match[1]), match[2]
    return amount if unit == "mm" else amount * 25.4 / (72 if unit == "pt" else 96)


def audit_exports(folder, data_file="source-data.csv"):
    spec = json.loads((folder / "spec.json").read_text())
    source = table(folder / data_file)
    plotted = table(folder / "output/plotting-data.csv")
    fields, options = spec["fields"], spec["options"]
    numeric = NUMERIC_SOURCE_COLUMNS | {fields[k] for k in ("x", "y", "size")}
    source_mismatches = []
    if len(source) != len(plotted):
        source_mismatches.append("row_count")
    else:
        for i, (a, b) in enumerate(zip(source, plotted)):
            for col, value in a.items():
                if col not in b or not (close(value, b[col]) if col in numeric else value == b[col]):
                    source_mismatches.append({"row": i, "column": col})
    zero_count = sum(float(r[fields["size"]]) == 0 for r in source)
    checks = {"source_table_retained": check(not source_mismatches, {"source_rows": len(source), "plotted_rows": len(plotted), "all_original_columns_and_original_row_order_compared": True, "numeric_relative_tolerance": 2e-13, "numeric_absolute_tolerance": 0, "mismatches": source_mismatches, "zero_size_rows": zero_count})}

    tree = ET.parse(folder / "output/panel.svg").getroot()
    dims = [svg_length_mm(tree.get(k)) for k in ("width", "height")]
    requested_dims = [spec["layout"]["width_mm"], spec["layout"]["height_mm"]]
    checks["svg_canvas"] = check(np.allclose(dims, requested_dims, atol=1e-5), {"actual_mm": dims, "requested_mm": requested_dims})
    texts = list(tree.iter(NS + "text"))
    sizes = sorted({float(re.search(f"font-size:\\s*({NUMBER})px", n.get("style", ""))[1]) for n in texts})
    checks["editable_svg_Arial_8pt"] = check(bool(texts) and sizes == [8.0] and all("Arial" in n.get("style", "") for n in texts), {"text_node_count": len(texts), "sizes_in_point_scaled_viewbox": sizes, "Arial_in_all_text_styles": all("Arial" in n.get("style", "") for n in texts)})
    allowed_text = set(spec["order"]["group"])
    for text in spec["labels"].values():
        allowed_text.update(text.split("\n"))
    unknown_text = ["".join(n.itertext()) for n in texts if "".join(n.itertext()) not in allowed_text and re.fullmatch(NUMBER, "".join(n.itertext()).replace("−", "-")) is None]
    checks["no_title_or_narrative_inside_panel"] = check(not unknown_text, {"unexpected_text_nodes": unknown_text})
    transform = {"x": numeric_tick_transform(by_id(tree, "matplotlib.axis_1"), "x"), "y": numeric_tick_transform(by_id(tree, "matplotlib.axis_2"), "y")}
    group_report, max_position_error, max_area_error = [], 0.0, 0.0
    all_geometry_ok, total_paths, zero_paths = True, 0, 0
    for index, group in enumerate(spec["order"]["group"], start=1):
        expected = [r for r in source if r[fields["group"]] == group]
        actual = path_circles(by_id(tree, f"PathCollection_{index}"))
        total_paths += len(actual)
        zero_paths += sum(c["diameter_pt"] == 0 for c in actual)
        # Some vector backends may omit zero-area paths. All corresponding
        # rows must still survive in the traceability table, and no positive
        # substitute is allowed. Compare retained paths in source group order.
        compare_rows = expected if len(actual) == len(expected) else [r for r in expected if float(r[fields["size"]]) > 0]
        ok = len(actual) == len(compare_rows)
        position_error, area_error, color_bad, shape_bad = 0.0, 0.0, 0, 0
        for row, path in zip(compare_rows, actual):
            target = [transform[dim]["slope_pt_per_unit"] * float(row[fields[dim]]) + transform[dim]["intercept_pt"] for dim in ("x", "y")]
            error = float(np.max(np.abs(np.array(path["center_pt"]) - target)))
            position_error = max(position_error, error)
            target_area = float(row[fields["size"]]) / options["size_max"] * options["max_area_pt2"]
            area_error = max(area_error, abs(path["nominal_circle_fill_area_pt2"] - target_area))
            color_bad += path["fill"] != spec["colors"][group].lower()
            shape_bad += abs(path["diameter_pt"] - path["diameter_y_pt"]) > 2e-6
        ok &= position_error < 2e-5 and area_error < 2e-5 and color_bad == shape_bad == 0
        all_geometry_ok &= ok
        max_position_error = max(max_position_error, position_error)
        max_area_error = max(max_area_error, area_error)
        group_report.append({"group": group, "source_rows": len(expected), "source_zero_rows": sum(float(r[fields["size"]]) == 0 for r in expected), "actual_svg_paths": len(actual), "max_coordinate_error_pt": position_error, "max_geometric_area_error_pt2": area_error, "color_mismatches": color_bad, "noncircular_paths": shape_bad, "source_order_within_group_checked": True, "status": "pass" if ok else "fail"})
    checks["actual_scatter_geometry"] = check(all_geometry_ok, {"measurement": "Actual written SVG path extrema and linear transforms fitted from all numeric axis ticks; no renderer import or artist self-report", "group_order": spec["order"]["group"], "groups": group_report, "total_svg_data_paths": total_paths, "retained_zero_area_paths": zero_paths, "maximum_coordinate_error_pt": max_position_error, "maximum_geometric_area_error_pt2": max_area_error, "area_formula": f"geometric circle fill area = {fields['size']} / {options['size_max']} * {options['max_area_pt2']} pt²", "note": "Nominal circular fill area excludes stroke; the negligible fixed cubic circle approximation error does not affect relative proportionality."})

    size_legend = by_id(tree, "legend_2")
    legend_circles = [circle(path) for path in size_legend.iter(NS + "path") if "C" in path.get("d", "")]
    level_errors = [abs(c["nominal_circle_fill_area_pt2"] - float(v) / options["size_max"] * options["max_area_pt2"]) for c, v in zip(legend_circles, options["size_legend"])]
    checks["actual_size_legend_geometry"] = check(len(legend_circles) == len(options["size_legend"]) and max(level_errors) < 2e-5, {"levels": options["size_legend"], "written_svg_nominal_fill_areas_pt2": [c["nominal_circle_fill_area_pt2"] for c in legend_circles], "max_area_error_pt2": max(level_errors)})

    axes = by_id(tree, "axes_1")
    expected_lines = [(dim, float(v)) for dim, values in options["reference_lines"].items() for v in values]
    actual_lines = []
    for group in list(axes):
        path = group.find(NS + "path")
        if path is None or "stroke-dasharray" not in path.get("style", ""):
            continue
        coords = np.array([float(v) for v in re.findall(NUMBER, path.get("d"))]).reshape(-1, 2)
        dim = "x" if abs(coords[0, 0] - coords[1, 0]) < 1e-6 else "y"
        value = (coords[0, 0 if dim == "x" else 1] - transform[dim]["intercept_pt"]) / transform[dim]["slope_pt_per_unit"]
        actual_lines.append((dim, float(value)))
    line_ok = len(actual_lines) == len(expected_lines) and all(a[0] == b[0] and abs(a[1] - b[1]) < 1e-6 for a, b in zip(actual_lines, expected_lines))
    checks["actual_reference_lines"] = check(line_ok, {"expected_source_positions": expected_lines, "actual_positions_recovered_from_written_paths": actual_lines, "note": "Drawn supplied locations do not infer significance or change source classes."})

    pdf = PdfReader(folder / "output/panel.pdf")
    page = pdf.pages[0]
    pdf_mm = [float(page.mediabox.width) * 25.4 / 72, float(page.mediabox.height) * 25.4 / 72]
    spans = []
    def visitor(text, cm, tm, font, size):
        if text.strip():
            spans.append({"text": text.strip(), "font": str(font.get("/BaseFont", "")) if font else "", "font_size_pt": float(size)})
    extracted = page.extract_text(visitor_text=visitor)
    embedded = []
    for name, reference in page["/Resources"]["/Font"].items():
        font = reference.get_object()
        descendant = font.get("/DescendantFonts", [font])[0].get_object()
        descriptor = descendant.get("/FontDescriptor", {}).get_object()
        stream = descriptor.get("/FontFile2")
        embedded.append({"resource": str(name), "base_font": str(font.get("/BaseFont")), "subtype": str(font.get("/Subtype")), "embedded_TrueType_bytes": len(stream.get_object().get_data()) if stream else 0})
    checks["actual_PDF_page_and_embedded_font"] = check(len(pdf.pages) == 1 and np.allclose(pdf_mm, requested_dims, atol=1e-5) and bool(spans) and all(s["font_size_pt"] == 8 and "Arial" in s["font"] for s in spans) and all(f["embedded_TrueType_bytes"] > 0 for f in embedded), {"pages": len(pdf.pages), "actual_page_mm": pdf_mm, "selected_text_fragment_count": len(spans), "actual_text_fonts": sorted({s["font"] for s in spans}), "actual_text_sizes_pt": sorted({s["font_size_pt"] for s in spans}), "font_resources": embedded, "selectable_text_extracted": bool(extracted.strip())})
    with Image.open(folder / "output/panel.png") as image:
        dpi = image.info.get("dpi")
        pixels = list(image.size)
        expected_pixels = [v * spec["layout"]["dpi"] / 25.4 for v in requested_dims]
        ys, xs = np.where(np.any(np.asarray(image.convert("RGB")) < 245, axis=2))
        clearance = [float(xs.min()), float(image.width - 1 - xs.max()), float(ys.min()), float(image.height - 1 - ys.max())]
    checks["actual_PNG_canvas_and_dpi"] = check(all(abs(a - b) < 1 for a, b in zip(pixels, expected_pixels)) and dpi is not None and np.allclose(dpi, [300, 300], atol=.02), {"pixels": pixels, "expected_fractional_pixels": expected_pixels, "metadata_dpi": dpi})
    checks["ink_clear_of_canvas_edge"] = check(min(clearance) > 0, {"minimum_clearance_px": min(clearance), "all_clearances_px_left_right_top_bottom": clearance, "threshold": "Any RGB channel <245; internal overlap and aesthetics remain independent visual questions."})
    stats = json.loads((folder / "output/stats.json").read_text())
    checks["no_new_statistical_inference"] = check(stats.get("method") == "none" and "regression" not in stats, {"stats_json": stats, "plotting_scope": "Supplied descriptive coordinates, classes and sizes only; upstream P values are preserved inputs."})
    return {"source_sha256": sha(folder / data_file), "spec_sha256": sha(folder / "spec.json"), "output_sha256": {p.name: sha(p) for p in (folder / "output").glob("panel.*")}, "checks": checks, "actual_tick_transforms": transform}


def workbook_audit(workbook):
    provenance = json.loads((HERE / "provenance.json").read_text())
    source = table(HERE / "source-data.csv")
    if workbook is None:
        return {"status": "not_checked", "evidence": "Pass --source-workbook to compare the prepared CSV with the official workbook. The full workbook is intentionally outside this portable case."}
    with zipfile.ZipFile(workbook) as archive:
        spreadsheet = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        relns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
        idns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        sheets = ET.fromstring(archive.read("xl/workbook.xml"))
        selected = next(n for n in sheets.iter(spreadsheet + "sheet") if n.get("name") == provenance["source_sheet"])
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(n.get("Target") for n in rels.iter(relns + "Relationship") if n.get("Id") == selected.get(idns + "id"))
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = ["".join(n.itertext()) for n in strings.findall(spreadsheet + "si")]
        styles = ET.fromstring(archive.read("xl/styles.xml"))
        formats = [int(n.get("numFmtId", 0)) for n in styles.find(spreadsheet + "cellXfs")]
        workbook_properties = sheets.find(spreadsheet + "workbookPr")
        uses_1904 = workbook_properties is not None and workbook_properties.get("date1904") in ("1", "true")
        epoch = datetime(1904, 1, 1) if uses_1904 else datetime(1899, 12, 30)
        worksheet = ET.fromstring(archive.read(target))
        sheet_rows = []
        date_cells = []
        for row in worksheet.iter(spreadsheet + "row"):
            values = {}
            for cell in row.findall(spreadsheet + "c"):
                value = cell.find(spreadsheet + "v")
                if value is None:
                    continue
                raw = value.text
                if cell.get("t") == "s":
                    decoded = shared[int(raw)]
                elif 14 <= formats[int(cell.get("s", 0))] <= 22:
                    # The official sheet contains two gene-column cells with
                    # built-in Excel date formatting. Preserve their decoded
                    # dates rather than inventing an original gene symbol.
                    decoded = str(epoch + timedelta(days=float(raw)))
                    date_cells.append({"cell": cell.get("r"), "serial_value": raw, "number_format_id": formats[int(cell.get("s", 0))], "decoded_value": decoded})
                else:
                    decoded = raw
                values[re.sub(r"\d", "", cell.get("r"))] = decoded
            sheet_rows.append((int(row.get("r")), values))
    headers = sheet_rows[0][1]
    selected_rows = [(row, values) for row, values in sheet_rows[1:] if 2 <= row <= 1458]
    mismatches = []
    if len(selected_rows) != len(source):
        mismatches.append("row_count")
    for (row_index, values), prepared in zip(selected_rows, source):
        if row_index != int(prepared["source_row"]):
            mismatches.append({"row": row_index, "column": "source_row"})
        for key in provenance["selected_columns"]:
            column = next(c for c, name in headers.items() if name == key)
            valid = close(values[column], prepared[key]) if key in NUMERIC_SOURCE_COLUMNS else values[column] == prepared[key]
            if not valid:
                mismatches.append({"row": row_index, "column": key})
    return check(sha(workbook) == provenance["source_sha256"] and not mismatches, {"actual_workbook_sha256": sha(workbook), "expected_workbook_sha256": provenance["source_sha256"], "sheet": provenance["source_sheet"], "source_rows": [2, 1458], "source_row_count": len(selected_rows), "columns_compared": provenance["selected_columns"], "method": "Direct read of cached official XLSX cell XML, shared strings and built-in date formats, independent of the original extraction script and renderer", "Excel_date_cells_in_gene_column": date_cells, "source_identifier_limitation": "A968 and A1306 are already numeric Excel dates in the official gene column. The prepared CSV preserves decoded date strings; original gene names cannot be recovered from this sheet. Plot coordinates, classes and probabilities are unaffected.", "mismatches": mismatches})


def scientific_input_checks():
    source = table(HERE / "source-data.csv")
    p = json.loads((HERE / "provenance.json").read_text())
    counts = dict(Counter(r["color"] for r in source))
    alias_ok = all(r["display_class"] == p["display_aliases"][r["color"]] for r in source)
    mdd_error = max(abs(float(r["mdd"]) - float(r["md3"]) + float(r["md5"])) for r in source)
    logq_error = max(abs(float(r["logq"]) + math.log10(float(r["fdr"]))) for r in source)
    threshold_ok = all((r["color"] == "Not_sig") == (abs(float(r["mdd"])) < .2) for r in source)
    return {
        "source_CSV_hash": check(sha(HERE / "source-data.csv") == p["csv_sha256"], {"actual": sha(HERE / "source-data.csv"), "provenance_record": p["csv_sha256"]}),
        "all_source_classes_and_aliases_preserved": check(counts == {"C5up": 471, "C3up": 143, "Not_sig": 843} and alias_ok, {"source_class_counts": counts, "display_aliases": p["display_aliases"], "all_rows_checked": len(source)}),
        "coordinate_semantics_crosscheck": check(mdd_error < 1e-12 and logq_error < 1e-12, {"mdd_equals_md3_minus_md5_max_abs_error": mdd_error, "logq_equals_negative_log10_fdr_max_abs_error": logq_error, "note": "These identities check supplied column semantics; neither coordinate was regenerated for plotting."}),
        "small_effect_class_is_not_P_nonsignificance": check(threshold_ok and all(float(r["fdr"]) < .01 for r in source), {"all_1457_supplied_fdr_below_0_01": all(float(r["fdr"]) < .01 for r in source), "grey_source_class_matches_abs_mdd_below_0_2": threshold_ok, "scope": "The already selected Source Data sheet; not the full assayed gene universe."}),
    }


def generate_transfer(runtime):
    folder = HERE / "transfer"
    folder.mkdir(exist_ok=True)
    fieldnames = ["row_key", "effect_axis", "prepared_height", "measured_share", "series_label"]
    values = [(-2.5, 2.2, 0, "Batch A"), (-1.8, 7, .02, "Batch B"), (-.4, 1.2, .15, "Batch C"), (0, 4.9, .25, "Batch A"), (1, 8.3, .5, "Batch B"), (1.7, 6.1, .7, "Batch C"), (2.6, 9.5, .8, "Batch A"), (3, 11.7, .95, "Batch B"), (3.6, 10.1, 1, "Batch C")]
    with (folder / "source-data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows([[f"synthetic-{i}", *row] for i, row in enumerate(values, 1)])
    spec = {"chart": "scatter", "fields": {"x": "effect_axis", "y": "prepared_height", "size": "measured_share", "group": "series_label"}, "layout": {"width_mm": 100, "height_mm": 85, "font": "Arial", "font_size_pt": 8, "line_width_pt": .6, "dpi": 300, "auto_fit": True}, "formats": ["pdf", "svg", "png"], "colors": {"Batch C": "#346C83", "Batch A": "#A5424F", "Batch B": "#D99C32"}, "order": {"group": ["Batch C", "Batch A", "Batch B"]}, "labels": {"x": "Prepared axis X", "y": "Prepared axis Y", "size": "Prepared fraction"}, "options": {"size_max": 1, "max_area_pt2": 36, "size_legend": [.02, .5, 1], "alpha": 1, "x_limits": [-3, 4], "y_limits": [0, 14], "reference_lines": {"x": [0], "y": [5]}, "grid": False, "regression": False}, "statistics": {"method": "none"}}
    (folder / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
    (folder / "README.md").write_text("# Synthetic scatter transfer probe\n\nNine invented engineering observations with renamed fields, interleaved categories, one measured zero and one small positive value (0.02). The explicit group order differs from first appearance. There is no biological source or interpretation. The probe reuses the generic renderer with a 100 × 85 mm canvas, Arial 8 pt and measured automatic layout. Its area, colors, group order and reference locations are explicit. It tests field-name and size/layout portability; it is not reproduction of a second study.\n\nRegenerate with verify_exports.py --generate-transfer --runtime /path/to/easyviz/scripts/render.py, then inspect verification.json for an independent audit of the written exports.\n")
    completed = subprocess.run([sys.executable, str(runtime), "--data", str(folder / "source-data.csv"), "--spec", str(folder / "spec.json"), "--out", str(folder / "output")], capture_output=True, text=True, timeout=120)
    if completed.returncode:
        raise RuntimeError(f"Transfer render failed: {completed.stderr[-2000:]}")
    (folder / "render-evidence.json").write_text(json.dumps({"command_arguments": ["render.py", "--data", "source-data.csv", "--spec", "spec.json", "--out", "output"], "runtime_sha256": sha(runtime), "exit_code": completed.returncode, "stdout_tail": completed.stdout[-1000:], "stderr_tail": completed.stderr[-1000:], "engineering_transfer_only": True}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-workbook", type=Path)
    parser.add_argument("--generate-transfer", action="store_true")
    parser.add_argument("--runtime", type=Path, help="Explicit renderer path, only needed when generating the transfer")
    args = parser.parse_args()
    if args.generate_transfer:
        if args.runtime is None:
            parser.error("--generate-transfer requires --runtime")
        generate_transfer(args.runtime)
    history = HERE / "first-render"
    historical = {p.name: sha(p) for p in history.iterdir() if p.is_file()} if history.is_dir() else None
    output = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "independent_audit": True, "scope": "Numerical and export verification, not aesthetic certification or validation of upstream biological analysis", "official_workbook_to_CSV": workbook_audit(args.source_workbook), "scientific_inputs": scientific_input_checks(), "paper_scatter": audit_exports(HERE)}
    if (HERE / "transfer/output/panel.svg").exists():
        output["engineering_transfer"] = audit_exports(HERE / "transfer")
        output["engineering_transfer"]["scope"] = "Synthetic field-name, category-order, scale and automatic-layout transfer; no new study or model performance claim."
    output["first_render_history_unchanged"] = (check(historical == {p.name: sha(p) for p in history.iterdir() if p.is_file()}, {"files_checked": len(historical), "historical_export_files_were_only_hashed": True})
                                               if historical is not None else {"status": "not_checked", "evidence": "Development-only first-render history is outside the portable case."})
    passed, failed = [], []
    def collect(value, path=""):
        if isinstance(value, dict):
            if value.get("status") in ("pass", "fail"):
                (passed if value["status"] == "pass" else failed).append(path)
            for key, item in value.items():
                if key != "status":
                    collect(item, f"{path}.{key}" if path else key)
    collect(output)
    output["check_summary"] = {"passed": len(passed), "failed": len(failed), "failures": failed}
    (HERE / "verification.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output["check_summary"], indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
