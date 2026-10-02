#!/usr/bin/env python3
"""Reproducible driver for the cell-type dot panel.

Validates the input contract requested for this panel, renders the single
panel with the bundled EasyViz core renderer, and re-checks the quantitative
mappings and export dimensions.

Run with the scientific environment:
    /Users/starry/Desktop/EasyViz/.venv/bin/python make_panel.py

Only files inside this working directory are written.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE / "skills" / "easyviz"
RENDER = SKILL / "scripts" / "render.py"
DATA = HERE / "prepared.csv"
SPEC = HERE / "panel-spec.json"
OUT = HERE / "output"

X_COL, Y_COL, SIZE_COL, COLOR_COL = "Treatment arm", "Cell type", "Detected fraction", "Prepared score"
EXPECTED_X = ["Control", "Low dose", "High dose"]
EXPECTED_Y = [
    "Resident macrophages", "Activated monocytes", "Interferon macrophages",
    "Lipid-associated cells", "Antigen-presenting cells", "Cycling myeloid cells",
    "Inflammatory macrophages", "Tissue monocytes",
]


def first_appearance(values):
    return list(dict.fromkeys(values))


def validate_input():
    import pandas as pd

    frame = pd.read_csv(DATA)
    checks = {}
    checks["row_count"] = int(len(frame))
    assert len(frame) == 24, "Expected 24 rows"
    for column in (X_COL, Y_COL, SIZE_COL, COLOR_COL):
        assert column in frame.columns, f"Missing column {column}"
    assert not frame[[X_COL, Y_COL, SIZE_COL, COLOR_COL]].isna().any().any(), "Missing values"
    assert not frame.duplicated([X_COL, Y_COL]).any(), "Duplicate cell/treatment cells"

    # Category order must be the first-appearance order of the source.
    x_order = first_appearance(frame[X_COL].astype(str).tolist())
    y_order = first_appearance(frame[Y_COL].astype(str).tolist())
    assert x_order == EXPECTED_X, f"x order mismatch: {x_order}"
    assert y_order == EXPECTED_Y, f"y order mismatch: {y_order}"

    # Complete 8 x 3 matrix, no absent or extra coordinates.
    observed = {(x, y) for x, y in zip(frame[X_COL].astype(str), frame[Y_COL].astype(str))}
    complete = {(x, y) for y in y_order for x in x_order}
    assert observed == complete, "Matrix is not complete"
    checks["matrix"] = f"{len(y_order)} x {len(x_order)} complete, no absent coordinates"

    # Detected fraction stays inside the declared 0-1 scale; zeros are observed.
    fractions = frame[SIZE_COL].astype(float)
    assert (fractions >= 0).all() and (fractions <= 1).all(), "Fraction outside 0-1"
    zeros = frame.loc[fractions.eq(0.0), [Y_COL, X_COL]]
    assert len(zeros) == 2, f"Expected exactly 2 measured zeros, found {len(zeros)}"
    checks["measured_zeros"] = [f"{r[Y_COL]} / {r[X_COL]}" for _, r in zeros.iterrows()]
    checks["fraction_min_positive"] = float(fractions[fractions > 0].min())
    checks["fraction_max"] = float(fractions.max())

    scores = frame[COLOR_COL].astype(float)
    checks["score_range"] = [float(scores.min()), float(scores.max())]
    checks["category_order_x"] = x_order
    checks["category_order_y"] = y_order
    return checks


def render():
    subprocess.run(
        [sys.executable, str(RENDER), "--data", str(DATA), "--spec", str(SPEC), "--out", str(OUT)],
        check=True,
    )
    return json.loads((OUT / "qa.json").read_text()), json.loads((OUT / "settings.json").read_text())


def validate_outputs(settings, qa):
    import pandas as pd

    spec_options = settings["options"]
    size_max = float(spec_options["size_max"])
    max_area = float(spec_options["max_area_pt2"])
    plotted = pd.read_csv(OUT / "plotting-data.csv")
    assert len(plotted) == 24, "Plotting table lost rows"

    # Area is linear in the fraction on the fixed 0-1 scale, never a radius.
    expected_area = plotted[SIZE_COL].astype(float) / size_max * max_area
    diff = (expected_area - plotted["_easyviz_area_pt2"]).abs().max()
    assert diff < 1e-9, f"Area mapping mismatch {diff}"
    zero_area = plotted.loc[plotted[SIZE_COL].astype(float).eq(0.0), "_easyviz_area_pt2"]
    assert (zero_area == 0).all(), "Measured zero must have zero area"

    result = {
        "qa_status": qa["status"],
        "clipped_text": len(qa["clipped_text"]),
        "overlapping_tick_labels": len(qa["overlapping_tick_labels"]),
        "missing_glyphs": qa["missing_glyphs"],
        "observed_rows": settings["dot_states"]["observed_rows"],
        "zero_rows": settings["dot_states"]["zero_rows"],
        "unmeasured_rows": settings["dot_states"]["unmeasured_rows"],
        "missing_coordinates": settings["dot_states"]["missing_coordinates"],
        "state_symbols": settings["dot_states"]["symbols"],
        "area_mapping": f"area_pt2 = detected_fraction / {size_max:g} * {max_area:g}",
        "area_max_abs_error": float(diff),
        "zero_area_pt2": [float(v) for v in zero_area.tolist()],
        "max_dot_diameter_mm": round(2 * math.sqrt(float(expected_area.max()) / math.pi) / 72 * 25.4, 3),
        "min_positive_diameter_mm": round(2 * math.sqrt(float(expected_area[expected_area > 0].min()) / math.pi) / 72 * 25.4, 3),
        "font_family": settings["layout"]["font"],
        "font_size_pt": settings["layout"]["font_size_pt"],
        "dpi": settings["layout"]["dpi"],
        "canvas_mm": [settings["layout"]["width_mm"], settings["layout"]["height_mm"]],
        "colormap": settings.get("colormap"),
        "color_limits": spec_options.get("color_limits"),
        "exports": qa["exports"],
        "statistics": "none requested; synthetic descriptive quantities without independent replicates",
    }
    (OUT / "check-summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    print("input contract:")
    print(json.dumps(validate_input(), indent=2))
    qa, settings = render()
    print("output checks:")
    print(json.dumps(validate_outputs(settings, qa), indent=2))
    print(f"\nwrote {OUT}/panel.pdf, panel.svg, panel.png and the traceability files")


if __name__ == "__main__":
    main()
