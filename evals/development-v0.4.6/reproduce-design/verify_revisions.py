#!/usr/bin/env python3
"""Verify actual exported geometry without importing either plotting script."""
from __future__ import annotations
import csv
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import pymupdf
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PT = 72 / 25.4


def source_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def near(actual, expected, tolerance=.003):
    assert abs(actual - expected) <= tolerance, (actual, expected)


def rgb(value):
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def color_equal(one, two):
    return one is not None and max(abs(a - b) for a, b in zip(one, two)) < .0003


def common(case, case_base=None, expected_font="Arial"):
    base = Path(case_base) if case_base else ROOT / "examples/no-author-code" / case
    revision = base / "revision-v0.4.6"
    spec = json.loads((revision / "adopted-spec.json").read_text())
    output = revision / "output"
    document = pymupdf.open(output / "panel.pdf")
    assert len(document) == 1
    page = document[0]
    width, height = (spec["layout"][key] for key in ("width_mm", "height_mm"))
    near(page.rect.width, width * PT)
    near(page.rect.height, height * PT)
    spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b for line in b["lines"] for s in line["spans"]]
    normalize_font = lambda name: name.replace(" ", "").replace("-", "").lower()
    assert spans and all(abs(s["size"] - 8) < .001 and normalize_font(s["font"]).startswith(normalize_font(expected_font)) for s in spans)
    font_records = [{"name": f[3], "embedded": bool(document.extract_font(f[0])[3])} for f in page.get_fonts()]
    assert font_records and all(f["embedded"] for f in font_records)
    svg = ET.parse(output / "panel.svg").getroot()
    for key, expected in (("width", width), ("height", height)):
        near(float(svg.attrib[key].removesuffix("pt")), expected * PT)
    svg_ids = {e.attrib["id"] for e in svg.iter() if "id" in e.attrib}
    mapping = json.loads((output / "elements.json").read_text())
    assert all(e["id"] in svg_ids for e in mapping["elements"])
    assert len(svg.findall('.//{http://www.w3.org/2000/svg}text')) > 0
    with Image.open(output / "panel.png") as image:
        image.load()
        assert list(image.size) == [round(d / 25.4 * spec["layout"]["dpi"]) for d in (width, height)]
        near(image.info["dpi"][0], spec["layout"]["dpi"], .01)
    assert (output / "source-data.csv").read_bytes() == (base / "inputs/source-data.csv").read_bytes()
    checks = {"pdf_mm": [page.rect.width / PT, page.rect.height / PT], "fonts": font_records,
        "text_size_pt": 8, "editable_svg_text": True, "element_map_svg_id_coverage": len(mapping["elements"]),
        "literal_source_snapshot_preserved": True}
    return base, spec, output, document, page, checks


def forest(case_base=None, expected_font="Arial"):
    base, spec, output, document, page, checks = common("vabistsevits-forest", case_base, expected_font)
    source = source_rows(base / "inputs/source-data.csv")
    rendered = {r["source_row"]: r for r in source_rows(output / "plotting-data.csv")}
    assert len(rendered) == len(source) == 48
    assert all(all(rendered[r["source_row"]][key] == value for key, value in r.items()) for r in source)
    drawings = page.get_drawings()
    layout = spec["layout"]
    intervals = [d for d in drawings if len(d["items"]) == 1 and d["items"][0][0] == "l"
                 and abs(d["rect"].height) < .001 and any(color_equal(d["color"], rgb(c)) for c in spec["colors"].values())]
    circles = [d for d in drawings if d["items"] and all(i[0] == "c" for i in d["items"])]
    assert len(intervals) == 48
    actual_fills = {"filled": 0, "hollow": 0}
    maximum_error = 0
    for record in source:
        panel_index = {"a": 0, "b": 1}[record["panel"]]
        left, bottom = layout["plot_left_mm"][panel_index], layout["plot_bottom_mm"]
        plot_width, plot_height = layout["plot_width_mm"], layout["plot_height_mm"]
        exposure_index = spec["exposures"].index(record["exposure"])
        outcome_index = spec["outcomes"].index(record["outcome"])
        source_y = spec["first_y_by_exposure"][exposure_index] - outcome_index
        y = page.rect.height - (bottom + plot_height * (source_y - spec["y_limits"][0]) / (spec["y_limits"][1] - spec["y_limits"][0])) * PT
        color = rgb(spec["colors"][record["outcome"]])
        expected_x = lambda value: (left + plot_width * math.log(float(value) / spec["x_limits"][0]) / math.log(spec["x_limits"][1] / spec["x_limits"][0])) * PT
        candidate_lines = [d for d in intervals if color_equal(d["color"], color) and abs(d["rect"].y0 - y) < .003
                           and d["rect"].x0 > left * PT - .003 and d["rect"].x1 < (left + plot_width) * PT + .003]
        candidate_points = [d for d in circles if color_equal(d["color"], color) or color_equal(d["fill"], color)]
        candidate_points = [d for d in candidate_points if abs((d["rect"].y0 + d["rect"].y1) / 2 - y) < .003
                            and left * PT <= (d["rect"].x0 + d["rect"].x1) / 2 <= (left + plot_width) * PT]
        assert len(candidate_lines) == len(candidate_points) == 1, record["source_row"]
        interval, point = candidate_lines[0], candidate_points[0]
        pairs = [(interval["rect"].x0, expected_x(record["ci_low"])), (interval["rect"].x1, expected_x(record["ci_high"])),
                 ((point["rect"].x0 + point["rect"].x1) / 2, expected_x(record["estimate"]))]
        for actual, expected in pairs:
            maximum_error = max(maximum_error, abs(actual - expected))
            near(actual, expected)
        near(point["rect"].width, spec["marker_diameter_pt"])
        near(point["rect"].height, spec["marker_diameter_pt"])
        near(interval["width"], spec["strokes"]["interval_pt"])
        hollow = color_equal(point["fill"], (1, 1, 1))
        assert hollow == (record["effect_direction"] == "overlaps null")
        if hollow:
            near(point["width"], spec["strokes"]["marker_outline_pt"])
        else:
            assert point["color"] is None and color_equal(point["fill"], color)
        actual_fills["hollow" if hollow else "filled"] += 1
    measured_spines = []
    for left in layout["plot_left_mm"]:
        targets = [(left * PT, (layout["height_mm"] - layout["plot_bottom_mm"] - layout["plot_height_mm"]) * PT),
                   ((left + layout["plot_width_mm"]) * PT, (layout["height_mm"] - layout["plot_bottom_mm"]) * PT)]
        frame = [d for d in drawings if color_equal(d["color"], rgb("#D9D9D9")) and len(d["items"]) == 1
                 and abs(d["rect"].width) < .003 and abs(d["rect"].height - layout["plot_height_mm"] * PT) < .003
                 and (abs(d["rect"].x0 - targets[0][0]) < .003 or abs(d["rect"].x0 - targets[1][0]) < .003)]
        assert len(frame) == 2
        measured_spines.append([layout["plot_width_mm"], frame[0]["rect"].height / PT])
    texts = [s["text"] for b in page.get_text("dict")["blocks"] if "lines" in b for line in b["lines"] for s in line["spans"]]
    assert all(sum(text == outcome for text in texts) == 1 for outcome in spec["outcomes"])
    assert all(sum(text == exposure for text in texts) == 1 for exposure in spec["exposures"])
    checks.update(verified_estimates=48, verified_asymmetric_ci_endpoints=96, maximum_pdf_position_error_pt=maximum_error,
        geometric_point_diameter_pt=spec["marker_diameter_pt"], supplied_fill_states=actual_fills,
        measured_lane_mm=measured_spines, shared_outcome_label_count=8, exposure_label_count=3,
        hypothesis_tests_recomputed=False, per_estimate_n_unknown=True)
    document.close()
    return checks


def radar(case_base=None, expected_font="Arial"):
    base, spec, output, document, page, checks = common("massier-integration-radar", case_base, expected_font)
    source = source_rows(base / "inputs/source-data.csv")
    lookup = {(r["integration_method"], r["cell_class"]): r for r in source}
    plotting = source_rows(output / "plotting-data.csv")
    assert len(plotting) == 25 and all(all(r[key] == lookup[(r["integration_method"], r["cell_class"])][key]
        for key in ("integration_method", "cell_class", "acceptance_rate")) for r in plotting)
    drawings = page.get_drawings()
    layout = spec["layout"]
    center = (layout["center_mm"][0] * PT, page.rect.height - layout["center_mm"][1] * PT)
    radius = layout["radius_mm"] * PT
    background = [d for d in drawings if d["items"] and all(i[0] == "c" for i in d["items"])
                  and abs(d["rect"].width - radius * 2) < .003 and d["fill"] is not None]
    assert len(background) == 1
    near(background[0]["rect"].height, radius * 2)
    traces = [d for d in drawings if len(d["items"]) == 5 and all(i[0] == "l" for i in d["items"])]
    assert len(traces) == 5
    maximum_error = 0
    for method in spec["methods"]:
        color = rgb(method["color"])
        trace = [d for d in traces if color_equal(d["color"], color)]
        assert len(trace) == 1
        trace = trace[0]
        near(trace["width"], layout["line_width_pt"])
        points = [d for d in drawings if d["items"] and all(i[0] == "c" for i in d["items"])
                  and color_equal(d["fill"], color) and d["rect"].y0 < (layout["height_mm"] - 20) * PT]
        assert len(points) == 5
        expected_points = []
        for index, cell in enumerate(spec["classes"]):
            rate = float(lookup[(method["source"], cell["source"])]["acceptance_rate"])
            theta = math.radians(90 - 72 * index)
            expected = (center[0] + radius * rate / spec["radial_limits"][1] * math.cos(theta),
                        center[1] - radius * rate / spec["radial_limits"][1] * math.sin(theta))
            expected_points.append(expected)
            vertex = trace["items"][index][1]
            for actual, wanted in zip(vertex, expected):
                maximum_error = max(maximum_error, abs(actual - wanted))
                near(actual, wanted)
        unused = points.copy()
        for expected in expected_points:
            point_index = next(i for i, d in enumerate(unused) if abs((d["rect"].x0 + d["rect"].x1) / 2 - expected[0]) < .003
                               and abs((d["rect"].y0 + d["rect"].y1) / 2 - expected[1]) < .003)
            point = unused.pop(point_index)
            near(point["rect"].width, layout["marker_diameter_pt"])
            near(point["rect"].height, layout["marker_diameter_pt"])
        assert not unused
        near(trace["items"][-1][2].x, expected_points[0][0])
        near(trace["items"][-1][2].y, expected_points[0][1])
    assert "depot" not in page.get_text()
    checks.update(verified_vertices=25, verified_closed_traces=5, maximum_pdf_position_error_pt=maximum_error,
        circle_diameter_mm=background[0]["rect"].width / PT, geometric_point_diameter_pt=layout["marker_diameter_pt"],
        unchanged_zero_origin_values=sum(float(r["acceptance_rate"]) == 0 for r in source), upstream_integration_recomputed=False)
    document.close()
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forest-case", type=Path, help="Copied/package case with inputs and revision-v0.4.6/output")
    parser.add_argument("--radar-case", type=Path)
    parser.add_argument("--expected-font", default="Arial")
    parser.add_argument("--out", type=Path, default=HERE / "export-verification.json")
    args = parser.parse_args()
    baseline = json.loads((HERE / "baseline-index.json").read_text())
    # Accommodate the documented index's list or named envelope without changing it.
    entries = baseline if isinstance(baseline, list) else baseline["files"]
    for entry in entries:
        saved = Path(entry["snapshot"] if "snapshot" in entry else entry["copied_path"])
        if not saved.is_absolute():
            saved = ROOT / saved
        assert hashlib.sha256(saved.read_bytes()).hexdigest() == entry["sha256"]
    result = {"status": "passed", "scope": "Actual exported PDF vector geometry, physical sizes, source strings and SVG maps; renderer not imported and QA claims not trusted.",
              "forest": forest(args.forest_case, args.expected_font), "radar": radar(args.radar_case, args.expected_font), "baseline_files_unchanged": len(entries),
              "limits": ["No calibrated print proof or publication-suitability claim.", "Visual review is a separate task; preserved numbers do not prove aesthetic improvement."]}
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "estimates": 48, "radar_vertices": 25}))


if __name__ == "__main__":
    main()
