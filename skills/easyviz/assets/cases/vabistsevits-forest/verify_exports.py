#!/usr/bin/env python3
"""Inspect exported PDF geometry independently of the plotting implementation.

This case audit reads source CSV, specs, and export files, without importing the
renderer or relying on its source-to-artist QA. Run after both panels are rendered.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pymupdf
from PIL import Image

BASE = Path(__file__).resolve().parent
PT_PER_MM = 72 / 25.4


def rows(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def close(a, b, tolerance=0.002):
    return abs(a - b) <= tolerance


def rgb(hex_color: str):
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def same_color(a, b):
    return a is not None and max(abs(x - y) for x, y in zip(a, b)) < 1e-5


def inspect_panel(panel: str) -> dict:
    source = rows(BASE / f"inputs/source-data-{panel}.csv")
    spec = json.loads((BASE / f"panel-{panel}-spec.json").read_text())
    output = BASE / f"output-{panel}"
    checks, findings = {}, []
    doc = pymupdf.open(output / "panel.pdf")
    assert len(doc) == 1, "Expected one full-canvas PDF page"
    page = doc[0]
    width, height = page.rect.width, page.rect.height
    checks["pdf_size_mm"] = [width / PT_PER_MM, height / PT_PER_MM]
    assert close(width, spec["layout"]["width_mm"] * PT_PER_MM)
    assert close(height, spec["layout"]["height_mm"] * PT_PER_MM)
    drawings = page.get_drawings()
    black = [d for d in drawings if same_color(d["color"], (0, 0, 0))
             and len(d["items"]) == 1 and d["items"][0][0] == "l"]
    horizontal = [d for d in black if close(d["rect"].height, 0)]
    vertical = [d for d in black if close(d["rect"].width, 0)]
    bottom = max(horizontal, key=lambda d: d["rect"].width)["rect"]
    left = max(vertical, key=lambda d: d["rect"].height)["rect"]
    assert close(bottom.x0, left.x0) and close(bottom.y0, left.y1)
    plot = [bottom.x0, left.y0, bottom.x1, bottom.y0]
    checks["plot_bounds_pdf_points_measured_from_spines"] = plot
    x_low, x_high = spec["options"]["x_limits"]

    def x_position(value):
        return plot[0] + math.log(value / x_low) / math.log(x_high / x_low) * (plot[2] - plot[0])

    labels, series = spec["order"]["label"], spec["order"]["series"]
    expected_pairs = {(label, group) for label in labels for group in series}
    assert {(r["outcome"], r["exposure"]) for r in source} == expected_pairs
    # The adopted blocks contain a header, eight rows, then 0.6 row of space.
    row_positions = {(label, group): group_index * (len(labels) + 1.6) + index + 1
                     for group_index, group in enumerate(series) for index, label in enumerate(labels)}
    y_high = max(row_positions.values()) + .5

    def y_position(value):
        return plot[1] + (value + .5) / (y_high + .5) * (plot[3] - plot[1])

    palette = {name: rgb(color) for name, color in spec["colors"].items()}
    colored = [d for d in drawings if any(same_color(d["color"] or d["fill"], color)
                                         for color in palette.values())]
    intervals = [d for d in colored if len(d["items"]) == 1
                 and d["items"][0][0] == "l" and close(d["rect"].height, 0)]
    circles = [d for d in colored if d["items"] and all(i[0] == "c" for i in d["items"])]
    assert len(intervals) == len(source) == len(circles) == 24
    maximum_error = 0.
    actual_states = {"filled": 0, "hollow": 0}
    for record in source:
        y = y_position(row_positions[(record["outcome"], record["exposure"])])
        color = palette[record["outcome"]]
        matched_lines = [d for d in intervals if same_color(d["color"], color)
                         and close(d["rect"].y0, y)]
        matched_circles = [d for d in circles if same_color(d["color"] or d["fill"], color)
                           and close((d["rect"].y0 + d["rect"].y1) / 2, y)]
        assert len(matched_lines) == len(matched_circles) == 1
        line, circle = matched_lines[0], matched_circles[0]
        bounds = line["rect"]
        center = circle["rect"]
        values = [(bounds.x0, x_position(float(record["ci_low"]))),
                  (bounds.x1, x_position(float(record["ci_high"]))),
                  ((center.x0 + center.x1) / 2, x_position(float(record["estimate"])))]
        for actual, expected in values:
            maximum_error = max(maximum_error, abs(actual - expected))
            assert close(actual, expected), (record["source_row"], actual, expected)
        state = "hollow" if circle["fill"] is None else "filled"
        assert state == record["mark_state"]
        assert (state == "hollow") == (record["effect_direction"] == "overlaps null")
        assert not record["n"], "The source does not provide per-estimate sample sizes"
        if state == "filled":
            assert circle["color"] is None, "Filled points must be borderless"
        else:
            assert same_color(circle["color"], color)
            assert close(circle["width"], spec["layout"]["line_width_pt"])
        area = math.pi / 4 * center.width * center.height
        assert close(area, spec["options"]["marker_area_pt2"], .01)
        actual_states[state] += 1
    checks.update(pdf_intervals=len(intervals), pdf_estimate_circles=len(circles),
                  source_estimates_and_asymmetric_endpoints_verified=True,
                  maximum_pdf_position_error_pt=maximum_error, actual_fill_states=actual_states,
                  actual_geometric_marker_area_pt2=spec["options"]["marker_area_pt2"],
                  per_estimate_n_unknown=True)
    spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block
             for line in block["lines"] for span in line["spans"] if span["text"].strip()]
    assert spans and all(close(s["size"], 8, .001) for s in spans)
    assert all(s["font"].startswith("Arial") for s in spans)
    checks["pdf_actual_text_sizes_pt"] = sorted({s["size"] for s in spans})
    checks["pdf_actual_text_fonts"] = sorted({s["font"] for s in spans})
    checks["pdf_font_embedding"] = [{"font": f[3], "extension": f[1],
                                      "embedded": len(doc.extract_font(f[0])[3]) > 0}
                                     for f in page.get_fonts()]
    assert all(f["embedded"] for f in checks["pdf_font_embedding"])
    with Image.open(output / "panel.png") as png:
        expected = [round(spec["layout"][key] / 25.4 * spec["layout"]["dpi"])
                    for key in ("width_mm", "height_mm")]
        assert all(abs(a - b) <= 1 for a, b in zip(png.size, expected))
        checks["png_pixels"] = list(png.size)
        checks["png_dpi_metadata"] = list(png.info["dpi"])
    svg = ET.parse(output / "panel.svg").getroot()
    assert svg.attrib["width"].endswith("pt") and svg.attrib["height"].endswith("pt")
    assert close(float(svg.attrib["width"][:-2]), width)
    assert close(float(svg.attrib["height"][:-2]), height)
    checks["svg_text_nodes"] = len(svg.findall(".//{http://www.w3.org/2000/svg}text"))
    assert checks["svg_text_nodes"] > 24
    checks["sha256"] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                          for name in ("panel.pdf", "panel.svg", "panel.png")}
    return {"status": "pass", "checks": checks, "findings": findings}


def main():
    original = {r["source_row"]: r for r in rows(BASE / "inputs/source-data.csv")}
    partition = rows(BASE / "inputs/source-data-a.csv") + rows(BASE / "inputs/source-data-b.csv")
    assert len(original) == len(partition) == len({r["source_row"] for r in partition}) == 48
    assert all(all(record[key] == original[record["source_row"]][key]
                   for key in original[record["source_row"]]) for record in partition)
    result = {"status": "pass", "scope": "Independent exported-PDF vector and physical-export audit; no renderer imported and no QA status trusted.",
              "all_original_48_records_and_numeric_strings_preserved": True,
              "panel_a": inspect_panel("a"), "panel_b": inspect_panel("b"),
              "limits": "Numerical/physical verification does not assess publication suitability, study inference, or calibrated print readability."}
    (BASE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "verified_source_rows": 48}))


if __name__ == "__main__":
    main()
