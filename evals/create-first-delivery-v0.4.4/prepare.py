"""Prepare prospective probes after the candidate implementation is frozen.

Run with --workbook /path/to/the/official/Yen/SourceData.xlsx. No accepted image
or aesthetic feedback seeds these inputs. This script never runs a renderer.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import shutil

import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True)
    args = parser.parse_args()
    inputs = HERE / "inputs"
    inputs.mkdir(exist_ok=False)
    shutil.copy2(args.workbook, inputs / "yen-source-data.xlsx")
    runtime = sorted((ROOT / "skills/easyviz/scripts").glob("*.py"))
    runtime.append(ROOT / "skills/easyviz/assets/palettes/palettes.json")
    frozen = {str(path.relative_to(ROOT)): sha(path) for path in runtime}
    cases = []

    def save(name, rows, specification, caption, source):
        folder = inputs / name
        folder.mkdir()
        with (folder / "data.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        write_json(folder / "spec.json", specification)
        (folder / "caption.md").write_text(caption + "\n")
        cases.append({
            "id": name, "rows": len(rows), "source": source,
            "data_sha256": sha(folder / "data.csv"),
            "spec_sha256": sha(folder / "spec.json"),
            "caption_sha256": sha(folder / "caption.md"),
            "reading_task": caption.split(". ")[0],
            "style_feedback_supplied": False,
        })

    def spec(chart, fields, width, height, **kwargs):
        return {"chart": chart, "fields": fields,
                "layout": {"width_mm": width, "height_mm": height,
                           "font": "Arial", "font_size_pt": 8, "dpi": 300},
                "formats": ["png", "pdf", "svg"], **kwargs}

    workbook = openpyxl.load_workbook(args.workbook, read_only=True, data_only=True)
    sheet = workbook["Fig.1i,j"]
    rows, trace = [], []
    for column, condition in (("B", "Vehicle"), ("C", "STM2457")):
        for row in range(7, 10):
            cell = sheet[f"{column}{row}"]
            assert isinstance(cell.value, (int, float))
            unit = str(sheet[f"A{row}"].value)
            rows.append({"condition": condition, "unit": unit, "value": cell.value})
            trace.append({"condition": condition, "unit": unit,
                          "worksheet": sheet.title, "cell": cell.coordinate,
                          "numeric_value": cell.value})
    workbook.close()
    save("yen-relative-m6a", rows,
         spec("replicate", {"condition": "condition", "unit": "unit", "value": "value"}, 60, 62,
              order={"condition": ["Vehicle", "STM2457"]},
              labels={"x": "Condition", "y": "Relative m6A (%)"},
              options={"mode": "summary", "uncertainty": "sample_sd",
                       "y_limits": [0, 140], "y_ticks": [0, 50, 100],
                       "marker_area_pt2": 7}),
         "Compare relative m6A after vehicle or STM2457 treatment. All six Fig. 1i "
         "values are source-normalized relative levels, not absolute methylation "
         "percentages; no further normalization. Source: Yen, Lung, Liau et al., "
         "Nature Communications 16, 4063 (2025), DOI 10.1038/s41467-025-59117-2, "
         "CC BY 4.0. Three independent experiments per condition as stated by "
         "the source; means and sample SD are recomputed from supplied values. "
         "Experimental IDs do not establish a paired test; no test or "
         "significance annotation is drawn. New labels/design are adaptations.",
         {"kind": "real_public_source_data", "workbook": "yen-source-data.xlsx",
          "workbook_sha256": sha(args.workbook),
          "article": "https://www.nature.com/articles/s41467-025-59117-2",
          "download": "https://media.springernature.com/original/springer-static/esm/"
                      "art%3A10.1038%2Fs41467-025-59117-2/MediaObjects/"
                      "41467_2025_59117_MOESM15_ESM.xlsx",
          "license": "https://creativecommons.org/licenses/by/4.0/", "cells": trace})

    rng = np.random.default_rng(344401)
    synthetic = {"kind": "original_synthetic_stress_probe", "seed": 344401,
                 "biological_inference": False}
    groups = ["Baseline", "Early response", "Mid response", "Late response",
              "Recovery", "Persistent"]
    rows = [{"group": group, "unit": f"U{i:02d}", "value": float(value)}
            for j, group in enumerate(groups)
            for i, value in enumerate(rng.normal(15 + j, 2.5, 18 + 3 * j), 1)]
    save("six-long-label-boxes", rows,
         spec("distribution", {"group": "group", "value": "value", "unit": "unit"}, 100, 80,
              order={"group": groups}, labels={"x": "Condition", "y": "Response (a.u.)"},
              options={"kind": "box", "y_limits": [0, 30], "point_area_pt2": 9,
                       "x_rotation": 35}),
         "Compare six labeled synthetic distributions. All observations remain "
         "visible; raw-value quartiles and Tukey 1.5 IQR whiskers are descriptive. "
         "Unequal synthetic counts are not sample sizes from a study; no test.",
         synthetic)
    rows = [{"group": group, "unit": f"U{i:03d}", "value": float(value)}
            for j, (group, count) in enumerate([("Reference", 75), ("Exposed", 115), ("Recovered", 45)])
            for i, value in enumerate(rng.normal(10 + j * 2, 2.6, count), 1)]
    save("dense-unequal-violins", rows,
         spec("distribution", {"group": "group", "value": "value", "unit": "unit"}, 90, 78,
              order={"group": ["Reference", "Exposed", "Recovered"]},
              labels={"x": "Condition", "y": "Response (a.u.)"},
              options={"kind": "violin", "violin_inner": "box",
                       "y_limits": [0, 24], "point_area_pt2": 9}),
         "Read estimated shape and raw observations in three unequal synthetic "
         "distributions. Scott Gaussian KDE, 100 evaluation points, trimming to "
         "observed range and independent width normalization are adopted; inner "
         "quartiles summarize raw values. All points remain; no test or inference.",
         synthetic)
    rows = [{"row": f"Feature {i + 1}", "column": f"S{j + 1:02d}", "value": round(float(rng.uniform(0, 12)), 4)}
            for i in range(4) for j in range(13)]
    save("wide-annotated-matrix", rows,
         spec("heatmap", {"row": "row", "column": "column", "value": "value"}, 128, 78,
              order={"y": [f"Feature {i + 1}" for i in range(4)],
                     "x": [f"S{j + 1:02d}" for j in range(13)]},
              labels={"x": "Sample", "y": "Feature", "color": "Value (a.u.)"},
              options={"color_limits": [0, 12], "annotate_values": True,
                       "value_format": ".1f", "x_rotation": 90}),
         "Read a complete four-by-thirteen synthetic magnitude matrix. All 52 "
         "cells, identifiers and row order remain; one adopted linear 0–12 scale, "
         "no center or normalization. Decimal display labels do not round colors.",
         synthetic)
    rows = []
    for j, group in enumerate(["Class A", "Class B", "Class C"]):
        for i in range(45):
            x = float(rng.uniform(0, 12))
            rows.append({"group": group, "unit": f"U{i + 1:03d}", "x": x,
                         "y": float(2 + .45 * x + j * 1.2 + rng.normal(0, 1.5))})
    save("three-class-scatter", rows,
         spec("scatter", {"x": "x", "y": "y", "group": "group", "unit": "unit"}, 88, 78,
              order={"group": ["Class A", "Class B", "Class C"]},
              labels={"x": "Measurement 1 (a.u.)", "y": "Measurement 2 (a.u.)"},
              options={"x_limits": [0, 12], "y_limits": [-4, 15], "point_area_pt2": 12}),
         "Distinguish three synthetic classes in a fixed-coordinate scatter. "
         "All 135 coordinates and constant point areas remain; no regression, "
         "correlation test or jitter of measured axes.",
         synthetic)
    write_json(HERE / "input-freeze.json", {
        "implementation_hashes": frozen, "cases": cases,
        "design": "Prospective new inputs created after implementation freeze; "
                  "no aesthetic feedback precedes the first independent review. "
                  "This bounded workflow check is not a causal model comparison.",
    })


if __name__ == "__main__":
    main()
