#!/usr/bin/env python3
"""Manuscript dot plot for `prepared.csv` (synthetic engineering test data).

Encoding
--------
* x     : Treatment arm      (input first-appearance order)
* y     : Cell type          (input first-appearance order)
* area  : Detected fraction  -> marker area is linear in the value on a shared
          0-1 scale (the radius is NOT the mapped variable)
* colour: Prepared score     -> perceptually uniform sequential colormap
* zeros : an observed Detected fraction of 0 is drawn with a dedicated
          non-quantitative cross symbol; its marker area is exactly 0 and it is
          never replaced by a small positive radius

No statistics are performed: the table holds supplied descriptive quantities
without independent replicate information, so nothing is imputed, pooled,
filtered or summarised.  All 24 rows are drawn.

Outputs (relative to this script)
---------------------------------
output/panel.pdf | panel.svg | panel.png
data/plot_data.csv
settings/figure_settings.json
checks/script_report.txt

Run:  /Users/starry/Desktop/EasyViz/.venv/bin/python make_figure.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Circle

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
IN_CSV = ROOT / "prepared.csv"
OUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
SET_DIR = ROOT / "settings"
CHK_DIR = ROOT / "checks"

# ---------------------------------------------------------------------------
# Figure settings.  Lengths are millimetres unless the name says otherwise.
# ---------------------------------------------------------------------------
MM_PER_IN = 25.4
PT_PER_IN = 72.0

FIG_W_MM = 120.0
FIG_H_MM = 90.0
FONT_PT = 8.0
DPI = 300

DOT_MAX_DIAM_MM = 5.6  # diameter of a dot whose Detected fraction == 1.0
ZERO_MARKER = "x"
ZERO_MARKER_S = 25.0  # points**2 -> 5.0 pt across, i.e. 1.76 mm
ZERO_MARKER_LW = 0.5
ZERO_COLOR = "#8c8c8c"

CMAP_NAME = "viridis"
CBAR_TICKS = [0.0, 0.5, 1.0, 1.5]
CBAR_WIDTH_MM = 3.5
CBAR_GAP_MM = 1.5

SPINE_COLOR = "#4d4d4d"
SPINE_LW = 0.5
TICK_LEN_PT = 1.8
TICK_PAD_PT = 1.5
AXIS_LABEL_PAD_PT = 2.0
DOT_EDGE_COLOR = "#3a3a3a"
DOT_EDGE_LW = 0.22

# fixed vertical layout (mm)
M_TOP = 2.2
M_BOTTOM = 1.0
XTICK_TEXT_MM = 2.9
XLABEL_PAD_MM = 1.4
XLABEL_MM = 2.8
LEGEND_GAP_MM = 2.0
LEGEND_H_MM = 10.0
LEGEND_LABEL_Y_MM = 1.6  # centre of the value labels, in mm from legend bottom
LEGEND_TEXT_HALF_MM = 1.4
LEGEND_LABEL_GAP_MM = 0.8
LEGEND_FILL = "#c8c8c8"  # neutral fill: legend circles encode size only
LEGEND_TITLE_GAP_MM = 4.0

# desired clear canvas around the ink, per side (mm)
PAD_LEFT_MM = 2.0
PAD_RIGHT_MM = 1.5
PAD_TOP_MM = 2.0
PAD_BOTTOM_MM = 2.0

MM = 1.0 / MM_PER_IN  # mm -> inch


def pt2mm(v: float) -> float:
    """Convert a length in points to millimetres."""
    return v * MM_PER_IN / PT_PER_IN


def text_width_in(fig, s: str, fontsize: float, family: str) -> float:
    """Rendered width of `s` in inches at the given font size."""
    t = fig.text(0.0, 0.0, s, fontsize=fontsize, fontfamily=family)
    renderer = fig.canvas.get_renderer()
    w = t.get_window_extent(renderer=renderer).width / fig.dpi
    t.remove()
    return w


def main() -> None:
    for d in (OUT_DIR, DATA_DIR, SET_DIR, CHK_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Input.  Read as text first so that the category order is preserved
    # exactly as it appears in the file.
    # ------------------------------------------------------------------
    raw = pd.read_csv(IN_CSV, dtype=str)
    raw.columns = [c.strip() for c in raw.columns]
    for c in ("Cell type", "Treatment arm"):
        raw[c] = raw[c].str.strip()
    raw["Detected fraction"] = raw["Detected fraction"].astype(float)
    raw["Prepared score"] = raw["Prepared score"].astype(float)

    cell_types = list(dict.fromkeys(raw["Cell type"]))
    arms = list(dict.fromkeys(raw["Treatment arm"]))
    ymap = {c: i for i, c in enumerate(cell_types)}
    xmap = {a: j for j, a in enumerate(arms)}

    df = raw.copy()
    df["x"] = df["Treatment arm"].map(xmap)
    df["y"] = df["Cell type"].map(ymap)

    # ------------------------------------------------------------------
    # Encoding: marker AREA is linear in the value.
    #
    # matplotlib's `scatter(s=...)` takes the SQUARE OF THE MARKER DIAMETER in
    # points (the default 'o' marker is a unit circle scaled by sqrt(s)), so
    #     d_pt(fraction) = sqrt(fraction) * D_MAX_PT
    #     drawn geometric area = pi/4 * d_pt^2  ->  linear in `fraction`
    # Setting s = pi * r^2 instead would inflate every dot by a factor of
    # sqrt(pi) and produce a diameter that no longer matches the declared one.
    # ------------------------------------------------------------------
    d_max_pt = DOT_MAX_DIAM_MM * PT_PER_IN / MM_PER_IN
    s_max_pt2 = float(d_max_pt**2)  # scatter size argument at fraction == 1.0

    def diameter_mm_for(fraction: float) -> float:
        return float(np.sqrt(fraction)) * DOT_MAX_DIAM_MM

    df["s_pt2"] = df["Detected fraction"] * s_max_pt2
    df["diameter_mm"] = np.sqrt(df["s_pt2"]) * MM_PER_IN / PT_PER_IN
    df["radius_mm"] = df["diameter_mm"] / 2.0
    df["is_zero"] = df["Detected fraction"] == 0.0

    score_min = float(df["Prepared score"].min())
    score_max = float(df["Prepared score"].max())
    norm = Normalize(vmin=score_min, vmax=score_max)

    # ------------------------------------------------------------------
    # Font / global style
    # ------------------------------------------------------------------
    arial_path = fm.findfont(
        fm.FontProperties(family="Arial"), fallback_to_default=False
    )
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial"],
            "font.size": FONT_PT,
            "axes.labelsize": FONT_PT,
            "axes.titlesize": FONT_PT,
            "xtick.labelsize": FONT_PT,
            "ytick.labelsize": FONT_PT,
            "legend.fontsize": FONT_PT,
            "axes.linewidth": SPINE_LW,
            "axes.edgecolor": SPINE_COLOR,
            "axes.labelcolor": "black",
            "text.color": "black",
            "xtick.color": SPINE_COLOR,
            "ytick.color": SPINE_COLOR,
            "xtick.major.width": SPINE_LW,
            "ytick.major.width": SPINE_LW,
            "xtick.major.size": TICK_LEN_PT,
            "ytick.major.size": TICK_LEN_PT,
            "xtick.major.pad": TICK_PAD_PT,
            "ytick.major.pad": TICK_PAD_PT,
            "pdf.fonttype": 42,  # TrueType -> editable text in the PDF
            "ps.fonttype": 42,
            "svg.fonttype": "none",  # keep text as text in the SVG
            "figure.dpi": DPI,
            "savefig.dpi": DPI,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    fig = plt.figure(figsize=(FIG_W_MM * MM, FIG_H_MM * MM))

    # ------------------------------------------------------------------
    # Vertical layout (independent of the horizontal fit)
    # ------------------------------------------------------------------
    main_bottom_mm = (
        M_BOTTOM
        + XLABEL_MM
        + XLABEL_PAD_MM
        + XTICK_TEXT_MM
        + pt2mm(TICK_LEN_PT)
        + pt2mm(TICK_PAD_PT)
    )
    main_h_mm = FIG_H_MM - main_bottom_mm - LEGEND_GAP_MM - LEGEND_H_MM - M_TOP
    legend_bottom_mm = main_bottom_mm + main_h_mm + LEGEND_GAP_MM

    # ------------------------------------------------------------------
    # Horizontal layout: a first estimate from measured text extents, then
    # corrected against the really rendered ink bbox (see `auto_fit` below).
    # ------------------------------------------------------------------
    longest_label = max(cell_types, key=len)
    ylab_w_mm = text_width_in(fig, longest_label, FONT_PT, "Arial") / MM
    cbar_tick_w_mm = max(
        text_width_in(fig, f"{t:g}", FONT_PT, "Arial") / MM for t in CBAR_TICKS
    )
    ylabel_text_mm = pt2mm(FONT_PT * 1.2)  # height of a rotated axis title

    left_mm = (
        PAD_LEFT_MM
        + ylabel_text_mm
        + pt2mm(AXIS_LABEL_PAD_PT)
        + ylab_w_mm
        + pt2mm(TICK_PAD_PT)
        + pt2mm(TICK_LEN_PT)
    )
    right_mm = (
        PAD_RIGHT_MM
        + ylabel_text_mm
        + pt2mm(AXIS_LABEL_PAD_PT)
        + cbar_tick_w_mm
        + pt2mm(TICK_PAD_PT)
        + pt2mm(TICK_LEN_PT)
        + CBAR_WIDTH_MM
        + CBAR_GAP_MM
    )
    plot_w_mm = FIG_W_MM - left_mm - right_mm

    ax = fig.add_axes([0.0, 0.0, 0.5, 0.5])
    cax = fig.add_axes([0.0, 0.0, 0.1, 0.1])
    ax_leg = fig.add_axes([0.0, 0.0, 0.5, 0.1])

    def apply_layout(l_mm: float, w_mm: float) -> None:
        ax.set_position(
            [l_mm / FIG_W_MM, main_bottom_mm / FIG_H_MM,
             w_mm / FIG_W_MM, main_h_mm / FIG_H_MM]
        )
        cax.set_position(
            [(l_mm + w_mm + CBAR_GAP_MM) / FIG_W_MM, main_bottom_mm / FIG_H_MM,
             CBAR_WIDTH_MM / FIG_W_MM, main_h_mm / FIG_H_MM]
        )
        ax_leg.set_position(
            [l_mm / FIG_W_MM, legend_bottom_mm / FIG_H_MM,
             w_mm / FIG_W_MM, LEGEND_H_MM / FIG_H_MM]
        )

    apply_layout(left_mm, plot_w_mm)

    # ------------------------------------------------------------------
    # Dots
    # ------------------------------------------------------------------
    nz = df[~df["is_zero"]]
    zz = df[df["is_zero"]]

    ax.scatter(
        nz["x"],
        nz["y"],
        s=nz["s_pt2"],
        c=nz["Prepared score"],
        cmap=CMAP_NAME,
        norm=norm,
        edgecolors=DOT_EDGE_COLOR,
        linewidths=DOT_EDGE_LW,
        zorder=3,
    )
    ax.scatter(
        zz["x"],
        zz["y"],
        s=ZERO_MARKER_S,
        marker=ZERO_MARKER,
        c=ZERO_COLOR,
        linewidths=ZERO_MARKER_LW,
        zorder=4,
    )

    # ------------------------------------------------------------------
    # Axes cosmetics
    # ------------------------------------------------------------------
    n_arm = len(arms)
    n_cell = len(cell_types)
    ax.set_xlim(-0.5, n_arm - 0.5)
    ax.set_ylim(n_cell - 0.5, -0.5)  # first cell type on top
    ax.set_xticks(range(n_arm))
    ax.set_xticklabels(arms)
    ax.set_yticks(range(n_cell))
    ax.set_yticklabels(cell_types)
    ax.set_xlabel("Treatment arm", labelpad=AXIS_LABEL_PAD_PT)
    ax.set_ylabel("Cell type", labelpad=AXIS_LABEL_PAD_PT)
    ax.tick_params(direction="out", top=False, right=False)
    for s in ax.spines.values():
        s.set_linewidth(SPINE_LW)
        s.set_color(SPINE_COLOR)
    ax.set_axisbelow(True)

    # ------------------------------------------------------------------
    # Colour bar (Prepared score)
    # ------------------------------------------------------------------
    sm = ScalarMappable(norm=norm, cmap=CMAP_NAME)
    cbar = fig.colorbar(sm, cax=cax, ticks=CBAR_TICKS)
    cbar.set_label("Prepared score", labelpad=AXIS_LABEL_PAD_PT)
    cbar.outline.set_linewidth(SPINE_LW)
    cbar.outline.set_edgecolor(SPINE_COLOR)
    cbar.ax.tick_params(
        direction="out", width=SPINE_LW, length=TICK_LEN_PT, pad=TICK_PAD_PT
    )

    # ------------------------------------------------------------------
    # Size legend (Detected fraction) with the zero symbol.  Drawn in mm
    # data units so that the circle radii are physically exact.
    # ------------------------------------------------------------------
    r_max_mm = DOT_MAX_DIAM_MM / 2.0
    y_centre = LEGEND_LABEL_Y_MM + LEGEND_TEXT_HALF_MM + LEGEND_LABEL_GAP_MM + r_max_mm
    legend_title = "Detected fraction"
    legend_title_w_mm = text_width_in(fig, legend_title, FONT_PT, "Arial") / MM

    def draw_size_legend(w_mm: float) -> None:
        ax_leg.clear()
        ax_leg.set_xlim(0.0, w_mm)
        ax_leg.set_ylim(0.0, LEGEND_H_MM)
        ax_leg.axis("off")
        ax_leg.text(
            0.0, y_centre, legend_title, ha="left", va="center", fontsize=FONT_PT
        )

        entries = 5  # the zero symbol plus 0.25 / 0.50 / 0.75 / 1.00
        region_x0 = legend_title_w_mm + LEGEND_TITLE_GAP_MM
        step = (w_mm - region_x0) / entries
        centres = [region_x0 + (i + 0.5) * step for i in range(entries)]

        # entry 1: observed zero -> non-quantitative symbol, marker area is 0
        ax_leg.plot(
            [centres[0]],
            [y_centre],
            marker=ZERO_MARKER,
            markersize=ZERO_MARKER_S**0.5,
            markeredgewidth=ZERO_MARKER_LW,
            color=ZERO_COLOR,
            linestyle="none",
        )
        ax_leg.text(centres[0], LEGEND_LABEL_Y_MM, "0", ha="center", va="center",
                    fontsize=FONT_PT)

        # entries 2-5: the shared 0-1 area scale
        for frac, cx in zip([0.25, 0.50, 0.75, 1.00], centres[1:]):
            r = diameter_mm_for(frac) / 2.0
            ax_leg.add_patch(
                Circle(
                    (cx, y_centre),
                    r,
                    facecolor=LEGEND_FILL,
                    edgecolor=DOT_EDGE_COLOR,
                    linewidth=DOT_EDGE_LW,
                )
            )
            ax_leg.text(cx, LEGEND_LABEL_Y_MM, f"{frac:.2f}", ha="center",
                        va="center", fontsize=FONT_PT)

    draw_size_legend(plot_w_mm)

    # ------------------------------------------------------------------
    # Auto-fit: measure the real ink bbox and shrink the plotting area so
    # that every glyph of the rotated y title stays inside the canvas.
    # The colour bar is anchored to the right edge, so only the left side
    # and the plot width change.
    # ------------------------------------------------------------------
    fit_log = []
    for _ in range(3):
        fig.canvas.draw()
        ink = fig.get_tightbbox(fig.canvas.get_renderer())
        ink_x0_mm = ink.x0 / MM
        ink_x1_mm = ink.x1 / MM
        ink_y0_mm = ink.y0 / MM
        ink_y1_mm = ink.y1 / MM
        fit_log.append(
            f"iter ink bbox mm: x {ink_x0_mm:.3f}..{ink_x1_mm:.3f} "
            f"y {ink_y0_mm:.3f}..{ink_y1_mm:.3f}"
        )
        d_left = PAD_LEFT_MM - ink_x0_mm
        d_right = ink_x1_mm - (FIG_W_MM - PAD_RIGHT_MM)
        if abs(d_left) < 0.02 and abs(d_right) < 0.02:
            break
        left_mm += d_left
        # keep the colour bar anchored to the right edge
        plot_w_mm = FIG_W_MM - right_mm - left_mm
        apply_layout(left_mm, plot_w_mm)
        draw_size_legend(plot_w_mm)

    fig.canvas.draw()
    ink = fig.get_tightbbox(fig.canvas.get_renderer())
    ink_x0_mm, ink_x1_mm = ink.x0 / MM, ink.x1 / MM
    ink_y0_mm, ink_y1_mm = ink.y0 / MM, ink.y1 / MM

    # ------------------------------------------------------------------
    # Save (bbox_inches=None -> the full 120 x 90 mm canvas is preserved)
    # ------------------------------------------------------------------
    fig.savefig(OUT_DIR / "panel.pdf", format="pdf")
    fig.savefig(OUT_DIR / "panel.svg", format="svg")
    fig.savefig(OUT_DIR / "panel.png", format="png", dpi=DPI)

    # matplotlib writes the SVG envelope in points; re-declare the identical
    # physical size in millimetres.  The viewBox is left untouched, so no
    # geometry, no text and no coordinate changes - only the unit label.
    svg_path = OUT_DIR / "panel.svg"
    svg_txt = svg_path.read_text(encoding="utf-8")
    for attr, mm_value in (("width", FIG_W_MM), ("height", FIG_H_MM)):
        svg_txt, n = re.subn(
            rf'(<svg\b[^>]*?\b{attr}=")[^"]*(")',
            lambda m, v=mm_value: f"{m.group(1)}{v:g}mm{m.group(2)}",
            svg_txt,
            count=1,
        )
        assert n == 1, f"could not set the SVG {attr} attribute"
    svg_path.write_text(svg_txt, encoding="utf-8")

    # ------------------------------------------------------------------
    # Plotting data
    # ------------------------------------------------------------------
    out = df[
        [
            "Cell type",
            "Treatment arm",
            "Detected fraction",
            "Prepared score",
            "x",
            "y",
            "is_zero",
            "s_pt2",
            "radius_mm",
            "diameter_mm",
        ]
    ].copy()
    out.to_csv(DATA_DIR / "plot_data.csv", index=False)

    # ------------------------------------------------------------------
    # Resolved settings record
    # ------------------------------------------------------------------
    settings = {
        "input": IN_CSV.name,
        "outputs": ["output/panel.pdf", "output/panel.svg", "output/panel.png"],
        "canvas": {
            "width_mm": FIG_W_MM,
            "height_mm": FIG_H_MM,
            "width_in": FIG_W_MM * MM,
            "height_in": FIG_H_MM * MM,
            "dpi": DPI,
            "png_px": [round(FIG_W_MM * MM * DPI), round(FIG_H_MM * MM * DPI)],
            "bbox_inches": None,
            "clear_canvas_mm_measured": {
                "left": ink_x0_mm,
                "right": FIG_W_MM - ink_x1_mm,
                "top": FIG_H_MM - ink_y1_mm,
                "bottom": ink_y0_mm,
            },
        },
        "fonts": {
            "family": "Arial",
            "resolved_file": str(arial_path),
            "size_pt": FONT_PT,
            "pdf_fonttype": 42,
            "svg_fonttype": "none",
        },
        "scale_mapping": {
            "variable": "Detected fraction",
            "channel": "marker area",
            "range": [0.0, 1.0],
            "shared_scale_across_all_panels_and_rows": True,
            "linear_in_area": True,
            "radius_used_as_mapping_variable": False,
            "scatter_size_argument_at_fraction_1_pt2": s_max_pt2,
            "diameter_of_fraction_1_mm": DOT_MAX_DIAM_MM,
            "formula": (
                "matplotlib scatter(s) takes the square of the marker diameter "
                "in points: s_pt2 = fraction * (D_MAX_mm * 72/25.4)^2 ; "
                "drawn diameter d_mm = sqrt(fraction) * D_MAX_mm ; "
                "drawn geometric area = pi/4 * d_mm^2, i.e. linear in fraction"
            ),
            "reference_diameters_mm": {
                f"{f:.2f}": round(diameter_mm_for(f), 4)
                for f in (0.25, 0.50, 0.75, 0.85, 1.00)
            },
            "reference_radii_mm": {
                f"{f:.2f}": round(diameter_mm_for(f) / 2.0, 4)
                for f in (0.25, 0.50, 0.75, 0.85, 1.00)
            },
        },
        "colour_mapping": {
            "variable": "Prepared score",
            "channel": "marker fill",
            "colormap": CMAP_NAME,
            "vmin": score_min,
            "vmax": score_max,
            "normalisation": "linear, data minimum to data maximum",
            "colourbar_ticks": CBAR_TICKS,
            "dot_edge_color": DOT_EDGE_COLOR,
            "dot_edge_width_pt": DOT_EDGE_LW,
        },
        "zero_marking": {
            "rule": "Detected fraction == 0 -> marker area exactly 0",
            "symbol": ZERO_MARKER,
            "size_pt2": ZERO_MARKER_S,
            "linewidth_pt": ZERO_MARKER_LW,
            "colour": ZERO_COLOR,
            "n_zero_points": int(df["is_zero"].sum()),
            "rows": df.loc[df["is_zero"], ["Cell type", "Treatment arm"]].to_dict(
                "records"
            ),
        },
        "axes": {
            "x_title": "Treatment arm",
            "y_title": "Cell type",
            "x_order": arms,
            "y_order": cell_types,
            "spine_colour": SPINE_COLOR,
            "spine_width_pt": SPINE_LW,
            "tick_length_pt": TICK_LEN_PT,
            "tick_pad_pt": TICK_PAD_PT,
            "axis_label_pad_pt": AXIS_LABEL_PAD_PT,
            "grid": False,
            "main_axes_rect_mm_lbwh": [
                round(left_mm, 3),
                round(main_bottom_mm, 3),
                round(plot_w_mm, 3),
                round(main_h_mm, 3),
            ],
            "row_pitch_mm": round(main_h_mm / n_cell, 3),
            "column_pitch_mm": round(plot_w_mm / n_arm, 3),
            "colourbar_gap_mm": CBAR_GAP_MM,
            "colourbar_width_mm": CBAR_WIDTH_MM,
            "size_legend_height_mm": LEGEND_H_MM,
        },
        "rendered_marker_extremes": {
            "smallest_nonzero": {
                "fraction": float(nz["Detected fraction"].min()),
                "diameter_mm": round(float(nz["diameter_mm"].min()), 4),
            },
            "largest": {
                "fraction": float(nz["Detected fraction"].max()),
                "diameter_mm": round(float(nz["diameter_mm"].max()), 4),
            },
        },
        "text_in_image": [
            "axis titles: Treatment arm / Cell type",
            "tick labels: the input categories",
            "size legend title: Detected fraction",
            "colour bar title: Prepared score",
        ],
        "excluded_by_request": ["figure title", "subtitle", "explanatory footnote"],
    }
    (SET_DIR / "figure_settings.json").write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Console / file report
    # ------------------------------------------------------------------
    def fp(v: float) -> str:
        return f"{v:.4f}".rstrip("0").rstrip(".")

    lines = [
        "make_figure.py - run report",
        f"input file               : {IN_CSV}",
        f"rows read                : {len(df)} (expected 24)",
        f"cell types in order      : {cell_types}",
        f"treatment arms in order  : {arms}",
        "Detected fraction min/max: "
        f"{fp(df['Detected fraction'].min())} / {fp(df['Detected fraction'].max())}",
        f"Prepared score  min/max  : {fp(score_min)} / {fp(score_max)}",
        f"observed zeros           : {int(df['is_zero'].sum())} -> "
        + "; ".join(
            f"{r['Cell type']} / {r['Treatment arm']}"
            for r in df.loc[df["is_zero"], ["Cell type", "Treatment arm"]].to_dict(
                "records"
            )
        ),
        f"smallest non-zero value  : {fp(nz['Detected fraction'].min())} "
        f"(dot diameter {fp(float(nz['diameter_mm'].min()))} mm)",
        f"largest value            : {fp(nz['Detected fraction'].max())} "
        f"(dot diameter {fp(float(nz['diameter_mm'].max()))} mm)",
        f"scatter s at fraction 1.0: {fp(s_max_pt2)} pt^2 "
        f"(marker diameter {fp(DOT_MAX_DIAM_MM)} mm)",
        f"resolved Arial file      : {arial_path}",
        f"canvas                   : {fp(FIG_W_MM)} x {fp(FIG_H_MM)} mm "
        f"({round(FIG_W_MM * MM * DPI)} x {round(FIG_H_MM * MM * DPI)} px at {DPI} dpi)",
        f"measured longest y label : '{longest_label}' {fp(ylab_w_mm)} mm",
        f"main axes (mm, l/b/w/h)  : {fp(left_mm)} / {fp(main_bottom_mm)} / "
        f"{fp(plot_w_mm)} / {fp(main_h_mm)}",
        f"row pitch (mm)           : {fp(main_h_mm / n_cell)}",
        f"column pitch (mm)        : {fp(plot_w_mm / n_arm)}",
        "",
        "auto-fit trace:",
        *[f"  {r}" for r in fit_log],
        f"  final clear canvas (mm): left {fp(ink_x0_mm)} | "
        f"right {fp(FIG_W_MM - ink_x1_mm)} | top {fp(FIG_H_MM - ink_y1_mm)} | "
        f"bottom {fp(ink_y0_mm)}",
        "",
        "written:",
        "  output/panel.pdf",
        "  output/panel.svg",
        "  output/panel.png",
        "  data/plot_data.csv",
        "  settings/figure_settings.json",
    ]
    report = "\n".join(lines) + "\n"
    (CHK_DIR / "script_report.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
