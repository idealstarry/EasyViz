#!/usr/bin/env python3
"""Audit rerendered artist coordinates against frozen source values.

The author's export callback is replaced to capture the complete figure. The
scripts write scratch trace/caption files only in a temporary folder; preserved
initial/final artifacts are never overwritten. The audit also checks saved trace
fields and PDF text size. This is a fixed evaluation companion, not runtime code.
"""
from __future__ import annotations
import csv
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from collections import Counter

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/easyviz-skill-value-audit-mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.text import Text
import numpy as np
from pypdf import PdfReader


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def pairs_counter(pairs):
    return Counter(tuple(round(float(value), 10) for value in row) for row in pairs)


def matching_xy(fig, expected):
    for ax in fig.axes:
        for line in ax.lines:
            pair = np.column_stack([line.get_xdata(), line.get_ydata()]).astype(float)
            if pair.shape == expected.shape and np.allclose(pair, expected, atol=1e-10, rtol=0):
                return True
        for collection in ax.collections:
            if isinstance(collection, PathCollection):
                pairs = np.asarray(collection.get_offsets(), dtype=float)
                if pairs.shape == expected.shape and pairs_counter(pairs) == pairs_counter(expected):
                    return True
    return False


def capture_figure(script, arm, task, scratch):
    captured = []
    def capture(fig, *args, **kwargs):
        captured.append(fig)
        return {"audit_capture": True}
    module = runpy.run_path(str(script), run_name="__figure_audit__")
    if arm == "baseline":
        function = module["co2" if task == "noaa-co2" else "earthquakes"]
        function.__globals__["export"] = capture
        function(ROOT / "inputs", scratch)
    else:
        function = module["main"]
        function.__globals__["export"] = capture
        previous_argv = sys.argv
        sys.argv = [str(script), "--panel", task, "--out", str(scratch), "--inputs", str(ROOT / "inputs")]
        try:
            function()
        finally:
            sys.argv = previous_argv
    if len(captured) != 1:
        raise ValueError(f"Expected one complete figure, obtained {len(captured)} for {script}")
    return captured[0]


def inspect(fig, source, task, output):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text = [item for item in fig.findobj(Text) if item.get_visible() and item.get_text().strip()]
    clipped = []
    for item in text:
        box = item.get_window_extent(renderer)
        if box.x0 < -0.5 or box.y0 < -0.5 or box.x1 > fig.bbox.x1 + 0.5 or box.y1 > fig.bbox.y1 + 0.5:
            clipped.append(item.get_text())
    record = {"artist_font_sizes_pt": sorted(set(item.get_fontsize() for item in text)),
              "artist_font_8pt_pass": all(item.get_fontsize() == 8 for item in text),
              "text_outside_canvas": clipped, "text_canvas_bounds_pass": not clipped,
              "source_rows": len(source)}
    if task == "noaa-co2":
        means = np.array([[int(row["year"]), float(row["mean_ppm"])] for row in source])
        unc = np.array([[int(row["year"]), float(row["uncertainty_ppm"])] for row in source])
        record["all_annual_mean_coordinates_pass"] = matching_xy(fig, means)
        record["all_supporting_uncertainty_coordinates_pass"] = matching_xy(fig, unc)
        expected_segments = np.array([[[int(row["year"]), float(row["mean_ppm"]) - float(row["uncertainty_ppm"])],
                                       [int(row["year"]), float(row["mean_ppm"]) + float(row["uncertainty_ppm"])]] for row in source])
        record["all_45_supplied_uncertainty_endpoints_pass"] = any(
            np.asarray(collection.get_segments()).shape == expected_segments.shape and
            np.allclose(np.asarray(collection.get_segments()), expected_segments, atol=1e-10, rtol=0)
            for ax in fig.axes for collection in ax.collections if isinstance(collection, LineCollection))
    else:
        collections = [collection for ax in fig.axes for collection in ax.collections if isinstance(collection, PathCollection)]
        expected = np.array([[float(row["depth"]), float(row["mag"])] for row in source])
        pooled = np.concatenate([np.asarray(collection.get_offsets(), dtype=float) for collection in collections])
        record["event_mark_count"] = len(pooled)
        record["all_event_coordinates_and_multiplicities_pass"] = pairs_counter(pooled) == pairs_counter(expected)
        record["separate_type_coordinate_groups_pass"] = all(any(
            pairs_counter(collection.get_offsets()) == pairs_counter([[float(row["depth"]), float(row["mag"])] for row in source if row["magType"] == key])
            for collection in collections) for key in sorted(set(row["magType"] for row in source)))
        record["display_axes"] = [{"x_scale": ax.get_xscale(), "y_scale": ax.get_yscale(), "xlim": list(ax.get_xlim()), "ylim": list(ax.get_ylim())} for ax in fig.axes]
    trace = read_csv(output / "plotted-values.csv")
    key = "year" if task == "noaa-co2" else "id"
    expected_by_id = {row[key]: row for row in source}
    record["trace_rows"] = len(trace)
    record["trace_source_fields_identical_pass"] = len(trace) == len(source) and len(set(row[key] for row in trace)) == len(source) and all(
        row[key] in expected_by_id and all(row[field] == value for field, value in expected_by_id[row[key]].items()) for row in trace)
    if task == "noaa-co2":
        record["trace_uncertainty_bounds_pass"] = all(
            abs(float(row["uncertainty_lower_ppm"]) - (float(row["mean_ppm"]) - float(row["uncertainty_ppm"]))) < 1e-10 and
            abs(float(row["uncertainty_upper_ppm"]) - (float(row["mean_ppm"]) + float(row["uncertainty_ppm"]))) < 1e-10 for row in trace)
    pdf = next(output.glob("*.pdf"))
    sizes = []
    def visit(text, cm, tm, font, font_size):
        if text.strip():
            sizes.append(float(font_size))
    PdfReader(pdf).pages[0].extract_text(visitor_text=visit)
    record["pdf_text_font_sizes_pt"] = sorted(set(sizes))
    record["exported_pdf_font_8pt_pass"] = bool(sizes) and all(size == 8 for size in sizes)
    record["all_recorded_checks_pass"] = all(value for key, value in record.items() if key.endswith("_pass"))
    return record


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="easyviz-value-artist-audit-") as folder:
        for arm in ("baseline", "easyviz"):
            for task in ("noaa-co2", "usgs-earthquakes"):
                output = ROOT / arm / task / "final"
                script = output / "plot.py"
                source = read_csv(ROOT / "inputs" / ("noaa-co2-1980-2024.csv" if task == "noaa-co2" else "usgs-earthquakes-2024-01.csv"))
                scratch = Path(folder) / arm / task
                scratch.mkdir(parents=True)
                fig = capture_figure(script, arm, task, scratch)
                record = {"arm": arm, "task": task, "script": str(script.relative_to(ROOT)), **inspect(fig, source, task, output)}
                results.append(record)
                plt.close(fig)
    passed = all(record["all_recorded_checks_pass"] for record in results)
    report = {"method": "Independent audit of the saved final script's complete Matplotlib artists, plus saved plotted-value CSV and exported PDF text", "records": results, "pass": passed,
              "limits": "Artist-array fidelity verifies that every supplied coordinate is drawn, including overlapping events. It does not imply every overlapping event is separately visible, or that subpixel uncertainty is discernible; those are visual-reading questions. No physical print or browser SVG-font substitution test was performed."}
    (ROOT / "value-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"records": len(results), "pass": passed}))
    raise SystemExit(0 if passed else 1)

if __name__ == "__main__":
    main()
