#!/usr/bin/env python3
"""Independent reviewer audit of source text, Decimal summaries and SVG centers."""
import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
CASE = ROOT / "examples/create/compartment-ccl2"
loader = importlib.util.spec_from_file_location("independent_expression_source_reader", ROOT / "examples/create/thermogenic-expression/validate.py")
source_reader = importlib.util.module_from_spec(loader); loader.loader.exec_module(source_reader)
SVG = {"s": "http://www.w3.org/2000/svg"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-root", type=Path, default=CASE)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "numeric-evidence.json")
    args = parser.parse_args()
    contract = json.loads((CASE / "inputs/input-contract.json").read_text())
    workbook = CASE / "inputs" / contract["source_file"]
    assert hashlib.sha256(workbook.read_bytes()).hexdigest() == contract["source_sha256"]
    actual_source = source_reader.source_cells(workbook, "3c")
    with (CASE / "inputs/observations.csv").open(newline="") as stream: rows = list(csv.DictReader(stream))
    assert len(rows) == 88
    for row in rows:
        assert actual_source[row["source_cell"]] == row["ccl2"]
        assert Decimal(actual_source[row["source_time_cell"]]) == Decimal(row["hour"])
    groups = {}
    for row in rows: groups.setdefault((row["compartment"], row["condition"], int(row["hour"])), []).append(row)
    reports = []; maximum_summary_error = maximum_marker_y_error = maximum_mean_x_error = maximum_mean_y_error = 0
    for name in ("lung", "serum"):
        spec = json.loads((args.render_root / "panels" / name / "spec.json").read_text())
        output = args.render_root / "panels" / name / "output"
        evidence = json.loads((output / "artist-evidence.json").read_text())
        svg = ET.parse(output / "panel.svg").getroot(); by_id = {node.get("id"): node for node in svg.iter() if node.get("id")}
        width, height = spec["layout"]["width_mm"], spec["layout"]["height_mm"]
        left, bottom, x_size, y_size = spec["layout"]["axes_fraction"]
        ylow, yhigh = spec["options"]["y_limits"]; xlow, xhigh = spec["options"]["x_limits"]
        for row in evidence["raw_rows"]:
            uses = by_id[row["artist_id"]].findall(".//s:use", SVG); assert len(uses) == 1
            expected_y = (height * (1 - bottom - y_size) + (yhigh - float(row["ccl2"])) / (yhigh - ylow) * height * y_size) / 25.4 * 72
            error = abs(float(uses[0].get("y")) - expected_y); maximum_marker_y_error = max(maximum_marker_y_error, error); assert error < 1e-5
            assert abs(row["display_offset_mm"]) <= 4.45 + 1e-8
        mean_groups = {}
        for summary in evidence["summary_rows"]:
            key = (summary["compartment"], summary["condition"], summary["hour"])
            values = [Decimal(row["ccl2"]) for row in groups[key]]
            with localcontext() as context:
                context.prec = 50
                mean = sum(values) / Decimal(len(values))
                sem = (sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1) / Decimal(len(values))).sqrt()
            errors = [abs(float(mean) - summary["mean"]), abs(float(sem) - summary["sem"])]
            maximum_summary_error = max(maximum_summary_error, *errors); assert max(errors) < 1e-12
            assert summary["n"] == len(values)
            assert summary["source_cells"] == [row["source_cell"] for row in groups[key]]
            mean_marker = by_id[summary["mean_artist_id"]].findall(".//s:use", SVG); assert len(mean_marker) == 1
            expected_x = (width * left + (summary["hour"] - xlow) / (xhigh - xlow) * width * x_size) / 25.4 * 72
            error = abs(float(mean_marker[0].get("x")) - expected_x); maximum_mean_x_error = max(maximum_mean_x_error, error); assert error < 1e-5
            expected_y = (height * (1 - bottom - y_size) + (yhigh - float(mean)) / (yhigh - ylow) * height * y_size) / 25.4 * 72
            error = abs(float(mean_marker[0].get("y")) - expected_y); maximum_mean_y_error = max(maximum_mean_y_error, error); assert error < 1e-5
            if spec["options"].get("mean_marker") == "_":
                node = mean_marker[0]
                definition = by_id[node.get("{http://www.w3.org/1999/xlink}href").removeprefix("#")]
                values = list(map(float, re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[Ee][-+]?\d+)?", definition.get("d"))))
                assert len(values) == 4 and sorted(values) == [-spec["options"]["mean_marker_pt"] / 2, 0, 0, spec["options"]["mean_marker_pt"] / 2]
                style = dict(item.strip().split(":", 1) for item in node.get("style").split(";") if ":" in item)
                assert float(style["stroke-width"]) == spec["options"]["mean_edge_pt"]
                mean_groups.setdefault(summary["hour"], []).append(float(node.get("y")))
        tick_gaps = [abs(positions[0] - positions[1]) / 72 * 25.4 - spec["options"]["mean_edge_pt"] / 72 * 25.4 for positions in mean_groups.values()]
        if tick_gaps: assert min(tick_gaps) > 0, "Actual genotype mean tick stroke edges must remain separate"
        reports.append({"compartment": spec["compartment"], "raw_source_values": len(evidence["raw_rows"]), "source_group_summaries": len(evidence["summary_rows"]),
                        "minimum_actual_mean_tick_stroke_gap_mm": min(tick_gaps) if tick_gaps else None,
                        "canvas_mm": [width, height], "exports_sha256": {extension: hashlib.sha256((output / ("panel." + extension)).read_bytes()).hexdigest() for extension in ("png", "pdf", "svg")}})
    result = {"status": "pass", "literal_workbook_numeric_and_hour_cells": 88, "independent_decimal_mean_sem_groups": 16,
              "actual_svg_raw_y_centers": 88, "actual_svg_exact_mean_hour_centers": 16,
              "maximum_summary_error": maximum_summary_error, "maximum_actual_raw_svg_y_error_pt": maximum_marker_y_error,
              "maximum_actual_mean_svg_x_error_pt": maximum_mean_x_error, "maximum_actual_mean_svg_y_error_pt": maximum_mean_y_error, "panels": reports,
              "render_root": str(args.render_root.resolve()),
              "scope": "Reviewer source/summary/actual-SVG checks independently of the case plotter. Full PDF/SVG raw/SEM/font/assembly checks separately rerun through the standalone validator; image judgments are reported separately."}
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "pass", "source_cells": 88, "mean_sem_groups": 16}))


if __name__ == "__main__": main()
