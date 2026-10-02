#!/usr/bin/env python
"""
Horizontal interval plot of prepared.csv (synthetic engineering data).

- Rows: Readout (vertical, first-occurrence order) x Preparation batch (2 groups).
- x: Prepared ratio on log scale; segments = given asymmetric 95% intervals (Lower 95 / Upper 95).
- Points hollow when the given interval contains 1, solid otherwise (reference-overlap
  state only; no significance inference). Intervals are used exactly as provided:
  no refitting, weighting, or recalculation.
- Missing readout/batch combinations are left as empty rows (kept, not dropped).
- Canvas: 140 x 100 mm, Arial 8 pt, PNG at 300 dpi. PDF/SVG are vector.
- Editable SVG text (svg.fonttype='none'), full canvas preserved.
"""

import csv
import json
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------
# Actual settings (recorded verbatim in output/settings.json)
# ----------------------------------------------------------------------------
FIG_W_MM, FIG_H_MM = 140.0, 100.0
DPI = 300
FONT_SIZE = 8
FONT_FAMILY = "Arial"
COLOR_A = "#0072B2"   # Okabe-Ito blue  -> Batch A
COLOR_B = "#D55E00"   # Okabe-Ito vermillion -> Batch B
REF_LINE = "#7F7F7F"

mpl.rcParams.update({
    "font.family": FONT_FAMILY,
    "font.size": FONT_SIZE,
    "svg.fonttype": "none",      # keep text editable in SVG
    "pdf.fonttype": 42,          # embed TrueType (editable text in PDF)
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "xtick.minor.width": 0.5,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "xtick.minor.size": 1.5,
    "ytick.major.size": 0,
})

# ----------------------------------------------------------------------------
# Data (read exactly as provided; category order = first occurrence)
# ----------------------------------------------------------------------------
with open(os.path.join(BASE, "prepared.csv"), newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))

batch_colors = {"Batch A": COLOR_A, "Batch B": COLOR_B}
batches = ["Batch A", "Batch B"]

categories = []
for r in rows:
    if r["Readout"] not in categories:
        categories.append(r["Readout"])

# all readout x batch combos; None marks a missing (not-provided) combination
cells = {(c, b): None for c in categories for b in batches}
for r in rows:
    cells[(r["Readout"], r["Preparation batch"])] = {
        "ratio": float(r["Prepared ratio"]),
        "lo": float(r["Lower 95"]),
        "hi": float(r["Upper 95"]),
        "hollow": float(r["Lower 95"]) <= 1.0 <= float(r["Upper 95"]),
    }

# ----------------------------------------------------------------------------
# Layout: 7 category blocks, 2 batch rows each
# ----------------------------------------------------------------------------
STEP = 1.45          # vertical distance between category block centers
ROW_OFF = 0.21       # offset of batch A/B rows within a block
cat_y = {c: -i * STEP for i, c in enumerate(categories)}

# wrap long category names to 2 lines for the y tick labels
def wrap(name, limit=16):
    words = name.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= limit or not cur:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return "\n".join(lines)

fig = plt.figure(figsize=(FIG_W_MM / 25.4, FIG_H_MM / 25.4))
ax = fig.add_axes([0.255, 0.115, 0.725, 0.79])

# reference line at ratio = 1
ax.axvline(1.0, color=REF_LINE, lw=0.7, ls=(0, (3, 2)), zorder=1)

y_pos, hollow_flags = [], {}
for c in categories:
    for b, off in zip(batches, (+ROW_OFF, -ROW_OFF)):
        cell = cells[(c, b)]
        y = cat_y[c] + off
        y_pos.append((c, b, y, cell))
        if cell is None:
            continue
        col = batch_colors[b]
        ax.plot([cell["lo"], cell["hi"]], [y, y],
                color=col, lw=1.1, solid_capstyle="butt", zorder=2)
        ax.plot([cell["lo"], cell["lo"]], [y - 0.055, y + 0.055],
                color=col, lw=0.8, zorder=2)
        ax.plot([cell["hi"], cell["hi"]], [y - 0.055, y + 0.055],
                color=col, lw=0.8, zorder=2)
        ax.plot(cell["ratio"], y,
                marker="o", ms=4.0,
                mfc="white" if cell["hollow"] else col,
                mec=col, mew=0.9, ls="none", zorder=3)
        hollow_flags[(c, b)] = cell["hollow"]

# axes cosmetics
ax.set_xscale("log")
ax.set_xlim(0.13, 8.0)
# first-occurrence category at top: standard orientation, y already decreases downward
ax.set_ylim(min(cat_y.values()) - STEP * 0.45, max(cat_y.values()) + STEP * 0.45)

ax.set_yticks([cat_y[c] for c in categories])
ax.set_yticklabels([wrap(c) for c in categories])
ax.tick_params(axis="y", pad=3)
ax.tick_params(axis="x", which="major", pad=2)

ax.set_xticks([0.2, 0.5, 1, 2, 5])
ax.set_xticklabels(["0.2", "0.5", "1", "2", "5"])
ax.xaxis.set_minor_locator(mpl.ticker.LogLocator(base=10, subs=(0.15, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 1.5, 3, 4, 6, 7, 8)))
ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
ax.set_xlabel("Prepared ratio (log scale)", labelpad=2)

ax.grid(axis="x", which="major", color="#D9D9D9", lw=0.5, zorder=0)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

# legend: batch colors + point-fill meaning
handles = [
    Line2D([], [], marker="o", ls="none", ms=3.8, mfc=COLOR_A, mec=COLOR_A, mew=0.9, label="Batch A"),
    Line2D([], [], marker="o", ls="none", ms=3.8, mfc=COLOR_B, mec=COLOR_B, mew=0.9, label="Batch B"),
    Line2D([], [], marker="o", ls="none", ms=3.8, mfc="white", mec="#333333", mew=0.9, label="Interval includes 1"),
    Line2D([], [], marker="o", ls="none", ms=3.8, mfc="#333333", mec="#333333", mew=0.9, label="Interval excludes 1"),
]
leg = ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 1.01),
                ncol=2, fontsize=FONT_SIZE, frameon=False, borderpad=0.0,
                columnspacing=1.4, handletextpad=0.5, handlelength=1.2)

# ----------------------------------------------------------------------------
# Export: full canvas, 300 dpi PNG + vector PDF/SVG
# ----------------------------------------------------------------------------
for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(OUT, f"panel.{ext}"), dpi=DPI if ext == "png" else None,
                format=ext)
plt.close(fig)

# ----------------------------------------------------------------------------
# Plot data + settings records
# ----------------------------------------------------------------------------
with open(os.path.join(OUT, "plot_data.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["readout", "batch", "row_order", "prepared_ratio",
                "lower_95", "upper_95", "interval_includes_1", "status"])
    for i, (c, b, y, cell) in enumerate(y_pos, 1):
        if cell is None:
            w.writerow([c, b, i, "", "", "", "", "missing combination (left empty)"])
        else:
            w.writerow([c, b, i, cell["ratio"], cell["lo"], cell["hi"],
                        cell["hollow"], "plotted"])

settings = {
    "figure_size_mm": [FIG_W_MM, FIG_H_MM],
    "figure_size_in": [FIG_W_MM / 25.4, FIG_H_MM / 25.4],
    "png_dpi": DPI,
    "font_family": FONT_FAMILY,
    "font_size_pt": FONT_SIZE,
    "colors": {"Batch A": COLOR_A, "Batch B": COLOR_B,
               "reference_line": REF_LINE, "grid": "#D9D9D9"},
    "x_scale": "log", "x_limits": [0.13, 8.0],
    "x_major_ticks": [0.2, 0.5, 1, 2, 5],
    "reference_line_x": 1.0,
    "point_fill_rule": "hollow if Lower95 <= 1 <= Upper95 (given interval contains 1), else solid",
    "category_order": categories,
    "rows_kept": len(rows),
    "missing_combinations": [f"{c} / {b}" for c in categories for b in batches
                             if cells[(c, b)] is None],
    "intervals": "used exactly as provided (no refit, no weighting, no recalculation, no tests)",
    "svg_text_editable": True,
    "pdf_fonttype": 42,
}
with open(os.path.join(OUT, "settings.json"), "w", encoding="utf-8") as fh:
    json.dump(settings, fh, indent=2)

print("category order:", categories)
print("rows plotted:", sum(1 for _, _, _, cell in y_pos if cell is not None))
print("missing:", settings["missing_combinations"])
print("hollow (interval includes 1):", [f"{c}/{b}" for (c, b), h in hollow_flags.items() if h])
print("done -> output/panel.{png,pdf,svg}")
