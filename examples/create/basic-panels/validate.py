#!/usr/bin/env python3
"""Check source values, public-renderer artists, and actual saved PDF/SVG/PNG.

Artist checks rebuild a figure through the same public renderer; they are
separate from saved-export font/dimension checks and independent image review.
This bounded evidence does not rank aesthetics or establish a model benchmark.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, quantiles, stdev
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image
import pymupdf

from plot import HERE, module, runtime_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(first, second):
    return math.isclose(float(first), float(second), rel_tol=1e-12, abs_tol=1e-12)


def check_artists(renderer, data_path, spec):
    prepared = renderer.prepare(data_path, spec)
    helper = renderer.core if spec["chart"] == "replicate" else renderer
    layout, typography, rc = helper.setup(deepcopy(spec))
    result = {}
    with helper.plt.rc_context(rc):
        if spec["chart"] == "replicate":
            fig, _ = renderer.draw(prepared, spec, layout, typography)
        else:
            fig, _ = renderer.draw(prepared, spec, layout, typography, result)
        try:
            fig.canvas.draw()
            source = list(csv.DictReader(data_path.open(newline="")))
            fields = spec["fields"]
            if spec["chart"] == "replicate":
                audit = renderer.audit_source_artists(data_path, spec, fig)
                assert audit["status"] == "pass", audit
                for group in fig._easyviz_replicate_summary:
                    values = [float(row[fields["value"]]) for row in source if row[fields["condition"]] == group["condition"]]
                    assert close(group["mean"], mean(values))
                    assert close(group["sample_sd"], stdev(values))
                return {"source_to_artist_audit": audit, "summary_check": "Independent Python mean and sample stdev", "readability": helper.panel_readability.measure(fig)}
            axis = fig.axes[0]
            if spec["chart"] == "scatter":
                records = []
                if "group" in fields:
                    groups = spec["order"]["group"]
                    for group, artist in zip(groups, axis.collections):
                        expected = np.asarray([[float(row[fields["x"]]), float(row[fields["y"]])] for row in source if row[fields["group"]] == group])
                        assert np.allclose(artist.get_offsets(), expected, rtol=1e-12, atol=1e-12)
                        records.extend(expected.tolist())
                else:
                    expected = np.asarray([[float(row[fields["x"]]), float(row[fields["y"]])] for row in source])
                    assert np.allclose(axis.collections[0].get_offsets(), expected, rtol=1e-12, atol=1e-12)
                    records = expected.tolist()
                assert len(records) == len(source)
                return {"raw_paired_points": len(records), "numeric_coordinates_unchanged": True, "unsupported_fit_or_test_added": False}
            if spec["chart"] == "distribution":
                from matplotlib.collections import PathCollection
                groups = spec["order"]["group"]
                point_artists = [artist for artist in axis.collections if isinstance(artist, PathCollection)]
                summaries = []
                for index, (group, artist) in enumerate(zip(groups, point_artists)):
                    values = [float(row[fields["value"]]) for row in source if row[fields["group"]] == group]
                    assert np.allclose(artist.get_offsets()[:, 1], values, rtol=1e-12, atol=1e-12)
                    q1, median, q3 = quantiles(values, n=4, method="inclusive")
                    record = {"group": group, "observations": len(values), "q1": q1, "median": median, "q3": q3}
                    if spec["options"]["kind"] == "box":
                        vertices = axis.patches[index].get_path().vertices
                        assert close(vertices[:, 1].min(), q1) and close(vertices[:, 1].max(), q3)
                        medians = [line for line in axis.lines if len(line.get_ydata()) == 2 and close(line.get_ydata()[0], median) and close(line.get_ydata()[1], median)]
                        assert medians, f"Missing median at {group}"
                    elif spec["options"].get("violin_inner") == "box":
                        actual = result["violin_inner_summaries"][index]
                        assert all(close(actual[key], record[key]) for key in ("q1", "median", "q3"))
                        rectangle = axis.patches[index]
                        assert close(rectangle.get_y(), q1) and close(rectangle.get_height(), q3 - q1)
                    summaries.append(record)
                assert sum(record["observations"] for record in summaries) == len(source)
                return {"raw_numeric_coordinates_unchanged": True, "source_observations": len(source), "independent_inclusive_quartiles": summaries}
            if spec["chart"] == "heatmap":
                matrix = axis.images[0].get_array()
                rows, columns = spec["order"]["y"], spec["order"]["x"]
                assert matrix.shape == (len(rows), len(columns))
                for row in source:
                    assert close(matrix[rows.index(row[fields["row"]]), columns.index(row[fields["column"]])], row[fields["value"]])
                assert [axis.images[0].norm.vmin, axis.images[0].norm.vmax] == spec["options"]["color_limits"]
                return {"matrix_cells": int(matrix.size), "matrix_order_and_values_unchanged": True, "global_color_limits": spec["options"]["color_limits"]}
            raise ValueError("Unsupported gallery chart")
        finally:
            helper.plt.close(fig)


def check_exports(out, spec):
    with pymupdf.open(out / "panel.pdf") as document:
        page = document[0]
        size = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
        assert all(abs(actual - expected) < 0.001 for actual, expected in zip(size, [110, 88]))
        spans = [span for block in page.get_text("dict")["blocks"] if block["type"] == 0 for line in block["lines"] for span in line["spans"]]
        fonts = sorted({span["font"] for span in spans})
        expected_font = spec["layout"]["font"].replace(" ", "").casefold()
        assert all(font.replace(" ", "").casefold().startswith(expected_font) for font in fonts), fonts
        sizes = sorted({round(span["size"], 3) for span in spans})
        assert set(sizes) <= {8.0, 5.6}, sizes
        assert all(document.extract_font(font[0])[3] for font in page.get_fonts())
    svg = ET.parse(out / "panel.svg").getroot()
    svg_size = [float(svg.attrib[key].removesuffix("pt")) / 72 * 25.4 for key in ("width", "height")]
    assert all(abs(actual - expected) < 0.001 for actual, expected in zip(svg_size, [110, 88]))
    texts = svg.findall(".//{http://www.w3.org/2000/svg}text")
    assert texts, "SVG text is not preserved"
    with Image.open(out / "panel.png") as image:
        pixels, dpi = image.size, image.info["dpi"]
        expected = [round(mm / 25.4 * 300) for mm in (110, 88)]
        assert all(abs(a - b) <= 1 for a, b in zip(pixels, expected))
        assert all(abs(value - 300) < 0.01 for value in dpi)
    return {"pdf_mm": size, "pdf_fonts": fonts, "pdf_fonts_embedded": True, "pdf_text_sizes_pt": sizes, "superscript_note": "5.6 pt is the standard 70% log-tick exponent of an 8 pt label, when present.", "svg_mm": svg_size, "svg_text_preserved": True, "png_pixels": list(pixels), "png_dpi": list(dpi), "sha256": {extension: digest(out / f"panel.{extension}") for extension in ("pdf", "svg", "png")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--font", help="Match the explicit font override used by plot.py.")
    parser.add_argument("--outputs", type=Path, help="Read saved case outputs from the plot.py --out directory.")
    parser.add_argument("--candidate-only", action="store_true", help="Validate five final panels; use when historical comparisons were not copied.")
    parser.add_argument("--out", type=Path, default=HERE / "validation.json")
    args = parser.parse_args()
    tools = runtime_path(args.tools)
    core = module(tools / "render.py", "basic_validate_core")
    replicate = module(tools / "replicate_plot.py", "basic_validate_replicate")
    records = []
    for case in json.loads((HERE / "manifest.json").read_text())["cases"]:
        folder = HERE / case["id"]
        renderer = replicate if case["renderer"] == "replicate_plot.py" else core
        baseline = json.loads((folder / "baseline-spec.json").read_text())
        candidate = json.loads((folder / "candidate-spec.json").read_text())
        assert baseline["fields"] == candidate["fields"]
        for key in ("width_mm", "height_mm", "font", "font_size_pt", "dpi"):
            assert baseline["layout"][key] == candidate["layout"][key]
        for key in ("x_limits", "y_limits", "x_scale", "y_scale", "color_limits", "color_center"):
            assert baseline["options"].get(key) == candidate["options"].get(key)
        destination = (args.outputs.resolve() / case["id"]) if args.outputs else folder
        runs = [("baseline", folder / "source-data.csv", folder / "baseline-spec.json", destination / "first-render"), ("candidate", folder / "source-data.csv", folder / "candidate-spec.json", destination / "output"), ("transfer", folder / "transfer/source-data.csv", folder / "transfer/spec.json", destination / "transfer/output")]
        if args.candidate_only:
            runs = [runs[1]]
        for role, source_path, spec_path, output in runs:
            spec = json.loads(spec_path.read_text())
            if args.font:
                spec["layout"]["font"] = args.font
            qa = json.loads((output / "qa.json").read_text())
            assert qa["status"] == "pass" and qa["input_sha256"] == digest(source_path)
            records.append({"case": case["id"], "run": role, "status": "pass", "input_rows": qa["input_rows"], "input_sha256": digest(source_path), "artist_checks": check_artists(renderer, source_path, spec), "actual_exports": check_exports(output, spec), "readability": qa.get("readability"), "visual_review_required": True})
    report = {"status": "pass", "runs": len(records), "comparison_numeric_axes_dimensions_font_preserved": True, "violin_comparison_note": "Candidate adds a declared descriptive Q1/median/Q3 layer; its source/KDE/numeric scales are unchanged. This is not a solely cosmetic comparison.", "scope": "Five known basic structures and five bounded true-source transfer probes; not a new-agent benchmark, a blind data test, or proof of CNS acceptance.", "records": records}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "runs": report["runs"], "report": str(args.out.resolve())}))


if __name__ == "__main__":
    main()
