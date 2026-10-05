#!/usr/bin/env python3
"""Independently validate source cells, exported SVG artists and physical files.

This validator reads the original XLSX/XML without executing the plotter. It
recomputes summaries with the standard library and derives plot transforms from
the saved specification, rather than trusting the plotter's claimed pass flag.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import mean, stdev
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
import pymupdf

HERE = Path(__file__).resolve().parent
SVG = "http://www.w3.org/2000/svg"
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XL_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
XLINK = "http://www.w3.org/1999/xlink"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames))
        result = list(reader)
        assert result and all(None not in row and all(item is not None for item in row.values()) for row in result)
        return result


def workbook_cells(path):
    with zipfile.ZipFile(path) as archive:
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(item for item in book.findall(f"{{{MAIN}}}sheets/{{{MAIN}}}sheet") if item.attrib["name"] == "3c")
        relationship = sheet.attrib[f"{{{XL_REL}}}id"]
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(item.attrib["Target"] for item in relationships if item.attrib["Id"] == relationship)
        sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(item.itertext()) for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        cells = {}
        for item in ET.fromstring(archive.read(sheet_path)).findall(f".//{{{MAIN}}}c"):
            value = item.findtext(f"{{{MAIN}}}v")
            if value is not None and item.attrib.get("t") == "s":
                value = strings[int(value)]
            elif value is None and item.attrib.get("t") == "inlineStr":
                value = "".join(item.find(f"{{{MAIN}}}is").itertext())
            cells[item.attrib["r"]] = value
    return cells


def check_input():
    inputs = HERE / "inputs"
    contract = json.loads((inputs / "input-contract.json").read_text())
    workbook = inputs / contract["source_file"]
    assert digest(workbook) == contract["source_sha256"]
    cells = workbook_cells(workbook)
    expected, blanks = {}, set()
    block_columns = {("Lung", "Control"): ["B", "C", "D", "E", "F"],
                     ("Lung", "IM-DTR"): ["G", "H", "I", "J", "K", "L"],
                     ("Serum", "Control"): ["N", "O", "P", "Q", "R", "S", "T", "U"],
                     ("Serum", "IM-DTR"): ["V", "W", "X", "Y", "Z", "AA", "AB", "AC"]}
    for (compartment, condition), columns in block_columns.items():
        time_column = "A" if compartment == "Lung" else "M"
        for row_number in range(3, 7):
            hour_cell = f"{time_column}{row_number}"
            hour = cells[hour_cell]
            assert int(hour) in (0, 12, 24, 48)
            for column in columns:
                address = f"{column}{row_number}"
                value = cells.get(address)
                key = (compartment, condition, hour, address)
                if value is None or value == "":
                    blanks.add(key)
                else:
                    assert math.isfinite(float(value))
                    expected[key] = {"value": value, "time_cell": hour_cell}
    source = read_csv(inputs / "observations.csv")
    assert len(source) == len(expected) == contract["observations"] == 88
    actual = {}
    by_group = {}
    for row in source:
        key = (row["compartment"], row["condition"], row["hour"], row["source_cell"])
        assert key not in actual and key in expected
        assert row["ccl2"] == expected[key]["value"], f"Source numeric string changed at {key}"
        assert row["source_time_cell"] == expected[key]["time_cell"]
        assert row["source_sheet"] == "3c"
        assert row["unit"] == contract["unit_by_compartment"][row["compartment"]]
        actual[key] = row
        group = key[:3]
        by_group.setdefault(group, []).append(float(row["ccl2"]))
    assert actual.keys() == expected.keys()
    saved_blanks = read_csv(inputs / "blank-cells.csv")
    assert {(row["compartment"], row["condition"], row["hour"], row["source_cell"]) for row in saved_blanks} == blanks
    assert len(blanks) == contract["blank_source_cells"] == 20
    expected_summaries = {}
    for key, values in by_group.items():
        expected_summaries[key] = {"n": len(values), "mean": mean(values), "sem": stdev(values) / math.sqrt(len(values))}
    adopted = read_csv(inputs / "descriptive-summary.csv")
    assert len(adopted) == len(expected_summaries) == 16
    for row in adopted:
        key = (row["compartment"], row["condition"], row["hour"])
        wanted = expected_summaries[key]
        assert int(row["n"]) == wanted["n"]
        for statistic in ("mean", "sem"):
            assert math.isclose(float(row[statistic]), wanted[statistic], rel_tol=1e-12, abs_tol=1e-12)
    for row in contract["group_counts"]:
        assert expected_summaries[(row["compartment"], row["condition"], row["hour"])]["n"] == row["n"]
    p_values = read_csv(inputs / "author-adjusted-p.csv")
    assert len(p_values) == 8
    for row in p_values:
        assert row["source_sheet"] == "3c" and row["comparison"] == "Control vs IM-DTR"
        assert row["adjusted_p"] == cells[row["source_cell"]]
    return source, expected_summaries, {"source_rows": 88, "empty_source_cells": 20,
        "group_counts_means_sems": 16, "supplied_adjusted_p_retained_exactly": 8,
        "original_numeric_strings_and_cell_traces": True, "workbook_sha256": digest(workbook)}


def to_svg_points(spec, x, y):
    layout, options = spec["layout"], spec["options"]
    width, height = layout["width_mm"] * 72 / 25.4, layout["height_mm"] * 72 / 25.4
    left, bottom, fraction_width, fraction_height = layout["axes_fraction"]
    xmin, xmax = options["x_limits"]
    ymin, ymax = options["y_limits"]
    return [(left + (x - xmin) / (xmax - xmin) * fraction_width) * width,
            (1 - bottom - (y - ymin) / (ymax - ymin) * fraction_height) * height]


def path_vertices(path):
    commands = re.findall(r"[A-Za-z]", path)
    assert commands and set(commands) <= {"M", "L"}, "Expected the actual straight trajectory/interval path"
    numbers = list(map(float, re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[Ee][-+]?\d+)?", path)))
    assert len(numbers) % 2 == 0
    return list(zip(numbers[::2], numbers[1::2]))


def styles(node):
    return dict(piece.strip().split(":", 1) for piece in node.attrib.get("style", "").split(";") if ":" in piece)


def close_points(actual, expected):
    assert len(actual) == len(expected)
    assert all(abs(a - b) <= 2e-5 for first, second in zip(actual, expected) for a, b in zip(first, second)), (actual, expected)


def check_panel(folder, spec, source, expected_summaries):
    compartment = spec["compartment"]
    rows = [row for row in source if row["compartment"] == compartment]
    raw_by_cell = {row["source_cell"]: row for row in rows}
    manifest = json.loads((folder / "elements.json").read_text())
    qa = json.loads((folder / "qa.json").read_text())
    receipt = json.loads((folder / "handoff.json").read_text())
    evidence = json.loads((folder / "artist-evidence.json").read_text())
    assert qa["status"] == evidence["status"] == "pass"
    assert qa["export_hashes"] == {name: digest(folder / ("panel." + name)) for name in ("pdf", "svg", "png")}
    assert all(qa["exports"][name]["sha256"] == digest(folder / ("panel." + name)) for name in ("pdf", "svg", "png"))
    assert digest(folder / "source-snapshot.csv") == digest(HERE / "inputs/observations.csv")
    assert manifest["version"]["input_sha256"] == digest(HERE / "inputs/observations.csv")
    assert manifest["version"]["figure_sha256"] == digest(folder / "panel.svg")
    assert manifest["version"]["source_script_sha256"] == digest(HERE / "plot.py")
    assert digest(folder / "source-script.py") == digest(HERE / "plot.py")
    saved_spec = folder / "spec-snapshot.json"
    assert json.loads(saved_spec.read_text()) == spec
    assert manifest["input"]["supplied_spec_sha256"] == digest(saved_spec)
    original_spec = HERE / "panels" / compartment.lower() / "spec.json"
    if spec.get("explicit_overrides"):
        assert digest(folder / "adopted-spec.json") == digest(saved_spec)
        assert qa["source_bindings"]["original_spec_file"]["sha256"] == digest(original_spec)
        assert manifest["input"]["spec_file"] == str((folder / "adopted-spec.json").resolve())
    else:
        assert digest(saved_spec) == digest(original_spec)
    assert qa["continuity_before"]["status"] == qa["continuity_after"]["status"] == "pass"
    assert receipt["kind"] == "easyviz-source-handoff" and receipt["track"] == "create"
    assert receipt["consumption"]["kind"] == "captured-bytes-before-export"
    assert receipt["exports"] == {"panel." + name: digest(folder / ("panel." + name)) for name in ("pdf", "svg", "png")}
    canonical = json.dumps(spec, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    assert receipt["version"]["spec_sha256"] == manifest["version"]["spec_sha256"] == hashlib.sha256(canonical).hexdigest()
    for role, value in receipt["consumption"]["source_sha256"].items():
        assert value == qa["source_bindings"][role]["sha256"] == digest(receipt["input"][role])
    for role, binding in receipt["input"]["auxiliary_inputs"].items():
        assert binding == qa["source_bindings"][role]
        assert binding["sha256"] == receipt["consumption"]["auxiliary_sha256"][role] == digest(binding["path"])
    assert manifest["input"]["auxiliary_inputs"] == receipt["input"]["auxiliary_inputs"]
    assert manifest["version"]["auxiliary_inputs_sha256"] == receipt["version"]["auxiliary_inputs_sha256"]
    assert receipt["version"]["figure_sha256"] == manifest["version"]["figure_sha256"]
    assert digest(folder / "source-data.csv") == receipt["version"]["input_sha256"]
    assert qa["source_p_values_plotted"] is False
    root = ET.parse(folder / "panel.svg").getroot()
    ids = {node.attrib["id"]: node for node in root.iter() if "id" in node.attrib}
    assert len(ids) == len([node for node in root.iter() if "id" in node.attrib])
    text = root.findall(f".//{{{SVG}}}text")
    assert text, "SVG text was converted into paths"
    assert all("8px" in item.attrib.get("style", "") for item in text), "SVG text font size drifted"
    exported_rows = read_csv(folder / "plotting-data.csv")
    assert len(exported_rows) == len(rows)
    actual_evidence = {row["source_cell"]: row for row in evidence["raw_rows"]}
    assert actual_evidence.keys() == raw_by_cell.keys()
    raw_centers, mean_centers, max_error = [], [], 0
    for row in exported_rows:
        wanted = raw_by_cell[row["source_cell"]]
        assert all(row[key] == value for key, value in wanted.items())
        item = ids[row["artist_id"]]
        uses = item.findall(f".//{{{SVG}}}use")
        assert len(uses) == 1
        actual = [float(uses[0].attrib["x"]), float(uses[0].attrib["y"])]
        expected = to_svg_points(spec, float(row["display_hour"]), float(wanted["ccl2"]))
        close_points([actual], [expected])
        max_error = max(max_error, max(abs(a - b) for a, b in zip(actual, expected)))
        offset_mm = (actual[0] - to_svg_points(spec, float(wanted["hour"]), float(wanted["ccl2"]))[0]) / 72 * 25.4
        assert abs(offset_mm - float(row["display_offset_mm"])) < 1e-6
        assert spec["options"]["raw_min_offset_mm"] - 1e-6 <= abs(offset_mm) <= spec["options"]["raw_max_offset_mm"] + 1e-6
        assert offset_mm < 0 if wanted["condition"] == "Control" else offset_mm > 0
        style = styles(uses[0])
        assert style["fill"].strip() == "#ffffff"
        assert style["stroke"].strip().lower() == spec["colors"][wanted["condition"]].lower()
        assert float(style["stroke-width"]) == spec["options"]["raw_edge_pt"]
        path_id = uses[0].attrib[f"{{{XLINK}}}href"].removeprefix("#")
        marker = ids[path_id].attrib["d"]
        numeric = list(map(float, re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[Ee][-+]?\d+)?", marker)))
        assert max(numeric) == spec["options"]["raw_marker_pt"] / 2
        assert min(numeric) == -spec["options"]["raw_marker_pt"] / 2
        raw_centers.append({"xy": actual, "condition": wanted["condition"]})
    summary_records = evidence["summary_rows"]
    assert len(summary_records) == 8
    for row in summary_records:
        key = (compartment, row["condition"], str(row["hour"]))
        wanted = expected_summaries[key]
        assert row["n"] == wanted["n"]
        assert math.isclose(row["mean"], wanted["mean"], rel_tol=1e-12)
        assert math.isclose(row["sem"], wanted["sem"], rel_tol=1e-12)
        use = ids[row["mean_artist_id"]].findall(f".//{{{SVG}}}use")
        assert len(use) == 1
        point = [float(use[0].attrib["x"]), float(use[0].attrib["y"])]
        close_points([point], [to_svg_points(spec, row["hour"], wanted["mean"])])
        if spec["options"].get("mean_marker") == "_":
            definition = ids[use[0].attrib[f"{{{XLINK}}}href"].removeprefix("#")]
            vertices = path_vertices(definition.attrib["d"])
            close_points(vertices, [[spec["options"]["mean_marker_pt"] / 2, 0],
                                    [-spec["options"]["mean_marker_pt"] / 2, 0]])
            assert float(styles(use[0])["stroke-width"]) == spec["options"]["mean_edge_pt"]
            assert styles(use[0])["stroke"].strip().casefold() == spec["colors"][row["condition"]].casefold()
        mean_centers.append(point)
        path = ids[row["sem_artist_id"]].find(f"{{{SVG}}}path")
        close_points(path_vertices(path.attrib["d"]), [to_svg_points(spec, row["hour"], wanted["mean"] - wanted["sem"]),
                                                      to_svg_points(spec, row["hour"], wanted["mean"] + wanted["sem"])])
        assert float(styles(path)["stroke-width"]) == spec["options"]["sem_line_pt"]
    trajectories = [item for item in manifest["elements"] if item["role"] == "mean-trajectory"]
    assert len(trajectories) == 2
    for item in trajectories:
        condition = item["label"].split(" · ")[0]
        path = ids[item["id"]].find(f"{{{SVG}}}path")
        expected = [to_svg_points(spec, hour, expected_summaries[(compartment, condition, str(hour))]["mean"])
                    for hour in (0, 12, 24, 48)]
        close_points(path_vertices(path.attrib["d"]), expected)
        assert float(styles(path)["stroke-width"]) == spec["options"]["mean_line_pt"]
    radius_pt = (spec["options"]["raw_marker_pt"] + spec["options"]["raw_edge_pt"]) / 2
    gaps = []
    left, bottom, width_fraction, height_fraction = spec["layout"]["axes_fraction"]
    width_pt = spec["layout"]["width_mm"] * 72 / 25.4
    height_pt = spec["layout"]["height_mm"] * 72 / 25.4
    region = [left * width_pt, (1 - bottom - height_fraction) * height_pt,
              (left + width_fraction) * width_pt, (1 - bottom) * height_pt]
    margins = []
    for index, first in enumerate(raw_centers):
        x, y = first["xy"]
        margins.append(min(x - radius_pt - region[0], region[2] - x - radius_pt,
                           y - radius_pt - region[1], region[3] - y - radius_pt) / 72 * 25.4)
        for second in raw_centers[index + 1:]:
            delta = [a - b for a, b in zip(first["xy"], second["xy"])]
            distance = max(map(abs, delta)) if first["condition"] == second["condition"] == "IM-DTR" else math.hypot(*delta)
            gaps.append((distance - 2 * radius_pt) / 72 * 25.4)
    assert min(gaps) >= spec["options"]["raw_gap_pt"] / 72 * 25.4 - 1e-5
    assert min(margins) > 0
    # Read the actual PDF embedded fonts, 8 pt text and vector marker centers.
    mean_visibility_gaps = []
    if spec["options"].get("mean_marker") == "_":
        # At the shared true time, the mean ticks must each remain visible.
        # A circular footprint approximation misses the earlier near-coincident
        # filled-marker obstruction at serum 0 h and lung 48 h.
        for hour in (0, 12, 24, 48):
            first = to_svg_points(spec, hour, expected_summaries[(compartment, "Control", str(hour))]["mean"])
            second = to_svg_points(spec, hour, expected_summaries[(compartment, "IM-DTR", str(hour))]["mean"])
            gap = (abs(first[1] - second[1]) - spec["options"]["mean_edge_pt"]) / 72 * 25.4
            mean_visibility_gaps.append(gap)
        assert min(mean_visibility_gaps) > 0
    with pymupdf.open(folder / "panel.pdf") as document:
        page = document[0]
        drawings = page.get_drawings()
        dimensions = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
        close_points([dimensions], [[spec["layout"]["width_mm"], spec["layout"]["height_mm"]]])
        fonts = page.get_fonts()
        assert fonts and all(document.extract_font(font[0])[3] for font in fonts)
        spans = [span for block in page.get_text("dict")["blocks"] if block["type"] == 0
                 for line in block["lines"] for span in line["spans"]]
        font_prefix = spec["layout"]["font"].replace(" ", "").casefold()
        assert spans and all(math.isclose(span["size"], 8, abs_tol=.001)
                             and span["font"].replace(" ", "").casefold().startswith(font_prefix) for span in spans)
        assert all(min(span["bbox"]) >= -.01 and span["bbox"][2] <= page.rect.width + .01
                   and span["bbox"][3] <= page.rect.height + .01 for span in spans)
        pdf_markers = []
        colors = {tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)) for color in spec["colors"].values()}
        for drawing in drawings:
            if drawing["type"] not in ("f", "fs") or drawing.get("color") is None:
                continue
            if not any(all(abs(a - b) < 1e-5 for a, b in zip(drawing["color"], color)) for color in colors):
                continue
            rectangle = drawing["rect"]
            center = [rectangle.x0 + rectangle.width / 2, rectangle.y0 + rectangle.height / 2]
            if abs(rectangle.width - spec["options"]["raw_marker_pt"]) < 1e-4 and abs(rectangle.height - spec["options"]["raw_marker_pt"]) < 1e-4:
                if region[0] <= center[0] <= region[2] and region[1] <= center[1] <= region[3]:
                    pdf_markers.append(center)
        assert len(pdf_markers) == len(raw_centers), (len(pdf_markers), len(raw_centers))
        for raw in raw_centers:
            assert any(math.dist(raw["xy"], actual) < 1e-4 for actual in pdf_markers)
        # Verify summary marks in the independent PDF vector representation,
        # using values recomputed directly from XLSX rather than claimed QA.
        def matching_pdf_lines(vertices, width, condition):
            rgb = tuple(int(spec["colors"][condition][index:index + 2], 16) / 255 for index in (1, 3, 5))
            matches = []
            for drawing in drawings:
                color = drawing.get("color")
                if color is None or drawing.get("width") is None or abs(drawing["width"] - width) >= 1e-5:
                    continue
                if any(abs(a - b) >= 1e-5 for a, b in zip(color, rgb)):
                    continue
                items = drawing["items"]
                if len(items) != len(vertices) - 1 or any(item[0] != "l" for item in items):
                    continue
                actual = [tuple(items[0][1])] + [tuple(item[2]) for item in items]
                if all(math.dist(wanted, drawn) < 1e-4 for wanted, drawn in zip(vertices, actual)):
                    matches.append(drawing)
            assert len(matches) == 1, (condition, width, vertices, len(matches))
        for row in summary_records:
            wanted = expected_summaries[(compartment, row["condition"], str(row["hour"]))]
            x, y = to_svg_points(spec, row["hour"], wanted["mean"])
            half = spec["options"]["mean_marker_pt"] / 2
            matching_pdf_lines([[x + half, y], [x - half, y]], spec["options"]["mean_edge_pt"], row["condition"])
            matching_pdf_lines([to_svg_points(spec, row["hour"], wanted["mean"] - wanted["sem"]),
                                to_svg_points(spec, row["hour"], wanted["mean"] + wanted["sem"])],
                               spec["options"]["sem_line_pt"], row["condition"])
        for condition in spec["order"]["condition"]:
            matching_pdf_lines([to_svg_points(spec, hour, expected_summaries[(compartment, condition, str(hour))]["mean"])
                                for hour in (0, 12, 24, 48)], spec["options"]["mean_line_pt"], condition)
    for key, mm in zip(("width", "height"), (spec["layout"]["width_mm"], spec["layout"]["height_mm"])):
        assert abs(float(root.attrib[key].removesuffix("pt")) / 72 * 25.4 - mm) < 1e-5
    with Image.open(folder / "panel.png") as image:
        assert all(abs(dpi - 300) < .01 for dpi in image.info["dpi"])
        for actual, mm in zip(image.size, (spec["layout"]["width_mm"], spec["layout"]["height_mm"])):
            ideal = mm / 25.4 * 300
            assert actual in {math.floor(ideal), round(ideal)}
    return {"status": "pass", "compartment": compartment, "raw_source_to_svg_and_pdf_markers": len(rows),
            "source_means_and_sem_paths": 8, "exact_linear_mean_times": [0, 12, 24, 48],
            "actual_pdf_summary_marks_and_strokes": 16, "actual_pdf_mean_trajectories": 2,
            "numeric_y_values_preserved": True, "bounded_raw_display_offsets_only": True,
            "maximum_raw_svg_coordinate_error_pt": max_error, "minimum_raw_glyph_gap_mm": min(gaps),
            "minimum_raw_axis_glyph_clearance_mm": min(margins), "svg_text_editable": True,
            "minimum_between_genotype_mean_tick_gap_mm": min(mean_visibility_gaps) if mean_visibility_gaps else None,
            "pdf_fonts_embedded": True, "all_pdf_text_adopted_font_8pt": True,
            "actual_font": qa["actual_font"]["actual_name"], "explicit_overrides": spec.get("explicit_overrides", {}),
            "captured_source_handoff_current": True,
            "dimensions_mm": [spec["layout"]["width_mm"], spec["layout"]["height_mm"]],
            "exports_sha256": qa["export_hashes"]}


def check_composition(folder, panel_outputs):
    record = json.loads((folder / "composition.json").read_text())
    assert record["rescaled"] is record["data_redrawn"] is record["font_size_changed"] is False
    expected_spans = []
    for index, output in enumerate(panel_outputs):
        with pymupdf.open(output / "panel.pdf") as document:
            source = document[0]
            left = record["panels"][index]["offset_mm"] / 25.4 * 72
            assert record["panels"][index]["pdf_sha256"] == digest(output / "panel.pdf")
            for block in source.get_text("dict")["blocks"]:
                if block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            expected_spans.append((span["text"], [span["bbox"][0] + left, span["bbox"][1], span["bbox"][2] + left, span["bbox"][3]]))
    with pymupdf.open(folder / "panel.pdf") as document:
        page = document[0]
        spans = [span for block in page.get_text("dict")["blocks"] if block["type"] == 0 for line in block["lines"] for span in line["spans"]]
        assert len(spans) == len(expected_spans)
        for actual, (text, bbox) in zip(spans, expected_spans):
            assert actual["text"] == text and abs(actual["size"] - 8) < .001
            assert all(abs(a - b) < .002 for a, b in zip(actual["bbox"], bbox))
        assert abs(page.rect.width / 72 * 25.4 - 167) < 1e-5 and abs(page.rect.height / 72 * 25.4 - 65) < 1e-5
    root = ET.parse(folder / "panel.svg").getroot()
    ids = [node.attrib["id"] for node in root.iter() if "id" in node.attrib]
    assert len(ids) == len(set(ids))
    return {"status": "pass", "individual_panels_rescaled": False, "all_pdf_text_positions_preserved": True,
            "individual_font_sizes_retained": True, "svg_ids_unique": True, "dimensions_mm": [167, 65]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, default=HERE)
    parser.add_argument("--out", type=Path, default=HERE / "validation.json")
    parser.add_argument("--font", help="The explicitly requested font used for this alternate-font redraw")
    args = parser.parse_args()
    source, summaries, input_report = check_input()
    panels, outputs = [], []
    for name in ("lung", "serum"):
        spec = json.loads((HERE / "panels" / name / "spec.json").read_text())
        if args.font:
            spec["explicit_overrides"] = {"font": {"original": spec["layout"]["font"], "requested": args.font}}
            spec["layout"]["font"] = args.font
        output = args.outputs / "panels" / name / "output"
        panels.append(check_panel(output, spec, source, summaries))
        outputs.append(output)
    report = {"status": "pass", "input": input_report, "panels": panels,
              "composition": check_composition(args.outputs / "output", outputs),
              "scope": "One real source case; direct XLSX numeric strings, independent group summaries, actual SVG/PDF markers and SEM, physical glyph clearances, dimensions/fonts/text, and unscaled composition. Numerical/export success does not establish aesthetics or broad Agent efficacy."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "pass", "source_rows": 88, "panels": 2, "summary_cells": 16}))


if __name__ == "__main__":
    main()
