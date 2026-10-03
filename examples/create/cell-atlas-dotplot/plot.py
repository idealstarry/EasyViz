#!/usr/bin/env python3
"""Create a single annotated myeloid composition chart from released source data."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors, font_manager
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from legend_layout import LegendLayout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--settings", type=Path,
                        help="Optional figure-settings JSON; source data remain case-specific")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    output = args.output_dir or here / "output"
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads((args.settings or here / "figure-settings.json").read_text())
    annotations = json.loads((here / "annotations.json").read_text())
    source = pd.read_csv(here / "source-data.csv")
    assert source.shape == (48, 9)
    assert not source.duplicated(["seurat_clusters", "tissue"]).any()
    assert not source[["seurat_clusters", "tissue", "n", "percent", "n_cluster"]].isna().any().any()
    assert (source.n >= 0).all() and (source.n % 1 == 0).all()
    assert set(source.tissue) == set(config["depot_order"])
    assert all(source.groupby("seurat_clusters").tissue.nunique() == 3)

    # Percentages are descriptive pooled-object compositions, never subject rates.
    totals = source.groupby("tissue").n.sum()
    source["depot_total"] = source.tissue.map(totals)
    source["within_depot_percent"] = 100.0 * source.n / source.depot_total
    np.testing.assert_allclose(source.within_depot_percent, source.percent, atol=1e-10)
    np.testing.assert_allclose(source.groupby("tissue").within_depot_percent.sum(), 100.0)
    pooled = source.groupby("seurat_clusters").n.sum()
    np.testing.assert_array_equal(source.seurat_clusters.map(pooled), source.n_cluster)
    source["pooled_subtype_n"] = source.seurat_clusters.map(pooled)
    source.to_csv(output / "plotted-data.csv", index=False)

    family = config["font_family"]
    text_pt = float(config["font_size_pt"])
    assert text_pt > 0, "font_size_pt must be positive"
    try:
        font_path = font_manager.findfont(family, fallback_to_default=False)
    except ValueError:
        family = "DejaVu Sans"
        font_path = font_manager.findfont(family, fallback_to_default=False)
    plt.rcParams.update({
        "font.family": family,
        "font.size": text_pt,
        "axes.titlesize": text_pt,
        "axes.labelsize": text_pt,
        "xtick.labelsize": text_pt,
        "ytick.labelsize": text_pt,
        "legend.fontsize": text_pt,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.bbox": None,
    })
    width, height = config["width_mm"], config["height_mm"]
    assert width > 0 and height > 0, "Canvas dimensions must be positive"
    # Layout coordinates describe the original design, independent of final mm.
    # Resizing the canvas changes relative spacing, but never scales font points.
    layout_width, layout_height = 180.0, 120.0
    fig = plt.figure(figsize=(width / 25.4, height / 25.4), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], xlim=(0, layout_width), ylim=(0, layout_height))
    ax.set_axis_off()
    ax.set_axisbelow(True)
    visual = {
        "text_color": "#2F3B43", "secondary_text_color": "#687780",
        "header_color": "#3B4952", "count_text_color": "#46555E",
        "header_rule_color": "#BDC7CD", "header_rule_width_pt": .45,
        "group_rule_color": "#E5EAED", "group_rule_width_pt": .3,
        "baseline_color": "#D3DCE1", "baseline_width_pt": .35,
        "annotation_strip_width": .75, "colorbar_outline": "none",
        "colorbar_tick_color": "#8B9AA4", "colorbar_tick_width_pt": .4,
        "header_font_weight": "normal",
        **config.get("visual_style", {}),
    }
    ink, muted = visual["text_color"], visual["secondary_text_color"]
    text_artists = []

    def label(x, y, text, **kwargs):
        defaults = dict(ha="left", va="center", fontsize=text_pt, color=ink, zorder=5)
        defaults.update(kwargs)
        artist = ax.text(x, y, text, **defaults)
        text_artists.append(artist)
        return artist

    # Manuscript title and narrative context belong in caption.md, outside the panel.
    label(6, 110, "Subtype", color=visual["header_color"], weight=visual["header_font_weight"])
    label(57, 110, "Reported marker examples", color=visual["header_color"], weight=visual["header_font_weight"])
    label(118, 114, "Within-depot composition", ha="center", color=visual["header_color"], weight=visual["header_font_weight"])
    label(160, 110, "Pooled n", ha="center", color=visual["header_color"], weight=visual["header_font_weight"])
    depots = config["depot_order"]
    x_locations = dict(zip(depots, [102, 119, 136]))
    for depot, x in x_locations.items():
        label(x, 109, config["depot_display"][depot], ha="center", color=visual["header_color"], weight=visual["header_font_weight"])
        label(x, 104.5, f"n={int(totals[depot]):,}", ha="center", color=muted)
    ax.plot([6, 175], [101, 101], lw=visual["header_rule_width_pt"],
            color=visual["header_rule_color"], zorder=1)

    # Rows are grouped by the authors' descriptive labels; no statistical clustering.
    row_positions = []
    y = 97.8
    row_pitch = float(config.get("row_pitch", 4.8))
    half_row = row_pitch / 2
    prior = None
    for annotation in annotations:
        if prior and prior != annotation["display_group"]:
            y -= 1.3
        row_positions.append(y)
        y -= row_pitch
        prior = annotation["display_group"]
    cmap = colors.LinearSegmentedColormap.from_list("easyviz_composition", config["color_stops"])
    mark_style = config.get("mark_style", {"outline": "none"})
    assert mark_style.get("outline", "none") in ("none", "uniform")
    edge_color = "none" if mark_style.get("outline", "none") == "none" else mark_style.get("edge_color", "#343B43")
    edge_width = 0.0 if edge_color == "none" else float(mark_style.get("edge_width_pt", 0.3))
    assert np.isfinite(edge_width) and edge_width >= 0
    mark_style = {"outline": mark_style.get("outline", "none"), "edge_color": edge_color, "edge_width_pt": edge_width}
    size_legend_color = config.get("size_legend_color", config["color_stops"][len(config["color_stops"]) // 2])
    norm = colors.Normalize(*config["color_range_percent"])
    max_area, size_max = config["dot_area_max_pt2"], config["dot_count_scale_max"]
    bar_start, bar_width = 149, 18
    assert int(pooled.max()) <= config["pooled_count_axis_max"]
    groups = list(dict.fromkeys(a["display_group"] for a in annotations))
    for index, group in enumerate(groups):
        positions = [pos for annotation, pos in zip(annotations, row_positions) if annotation["display_group"] == group]
        top, bottom = max(positions) + half_row, min(positions) - half_row
        if index:
            # Group boundaries carry grouping, not a table of boxed cells.
            boundary = top + .65
            ax.plot([9, 175], [boundary, boundary],
                    color=visual["group_rule_color"], lw=visual["group_rule_width_pt"], zorder=1)
        ax.add_patch(Rectangle((6, bottom), visual["annotation_strip_width"], top - bottom,
                               facecolor=config["group_colors"][group], edgecolor=edge_color, linewidth=edge_width, zorder=1))
    ax.plot([bar_start, bar_start], [min(row_positions) - half_row, 100],
            color=visual["baseline_color"], lw=visual["baseline_width_pt"], zorder=1)

    for annotation, y in zip(annotations, row_positions):
        cluster = annotation["cluster"]
        label(9, y, "myC" + (str(cluster) if cluster == 0 else f"{cluster:02d}"), color=muted)
        label(24, y, annotation["label"])
        label(57, y, annotation["marker_examples"], fontstyle="italic", color=muted)
        subset = source[source.seurat_clusters == cluster].set_index("tissue")
        for depot, x in x_locations.items():
            row = subset.loc[depot]
            ax.scatter([x], [y], s=[max_area * row.n / size_max],
                       c=[row.within_depot_percent], cmap=cmap, norm=norm,
                       linewidths=edge_width, edgecolors=edge_color, zorder=3)
        n = int(pooled[cluster])
        ax.barh(y, n / config["pooled_count_axis_max"] * bar_width,
                height=1.8, left=bar_start, color=config["group_colors"][annotation["display_group"]],
                alpha=1.0, edgecolor=edge_color, linewidth=edge_width, zorder=2)
        label(175, y, f"{n:,}", ha="right", color=visual["count_text_color"])

    # A shared physical-layout helper also serves the generic renderer and other
    # recipes. Quantitative keys retain exactly the areas of the data marks.
    body_bottom = min(row_positions) - half_row
    plot_bbox_mm = [6 * width / layout_width, body_bottom * height / layout_height,
                    169 * width / layout_width, (101 - body_bottom) * height / layout_height]
    guides = LegendLayout(fig, ax, {"legend": text_pt}, config.get("legends", {}),
                          main_plot_bbox_mm=plot_bbox_mm)
    guides.add_categorical(["M2", "Other macrophages", "Monocytes", "DC"],
                           [config["group_colors"][g] for g in groups],
                           edgecolor=edge_color, linewidth_pt=edge_width)
    legend_counts = [100, 1000, 2500]
    guides.add_size(legend_counts, [max_area * n / size_max for n in legend_counts],
                    title="Count", color=size_legend_color,
                    edgecolor=edge_color, linewidth_pt=edge_width)
    guides.add_colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), "Within-depot share (%)")
    legend_report = guides.layout()
    for entry in guides.entries:
        for text in entry["artist"].findobj(matplotlib.text.Text):
            text.set_color(ink)
        if entry["kind"] == "colorbar":
            entry["colorbar"].outline.set_visible(visual["colorbar_outline"] != "none")
            entry["artist"].tick_params(color=visual["colorbar_tick_color"],
                                       labelcolor=ink, width=visual["colorbar_tick_width_pt"])
            entry["artist"].xaxis.label.set_color(ink)
            entry["artist"].yaxis.label.set_color(ink)
    # Validate the final guide geometry after applying cosmetic guide styles.
    legend_report = guides.validate()
    assert legend_report["status"] == "pass", f"Legend layout needs revision: {legend_report['issues']}"

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    clipped = [a.get_text() for a in text_artists if not canvas.contains(*a.get_window_extent(renderer).p0)
               or not canvas.contains(*a.get_window_extent(renderer).p1)]
    assert not clipped, f"Labels outside final canvas: {clipped}"
    for extension in config["formats"]:
        fig.savefig(output / f"figure.{extension}", dpi=config["dpi"], bbox_inches=None, pad_inches=0,
                    metadata={"Creator": "EasyViz"} if extension in ["svg", "pdf"] else None)
    audit = {
        "source_rows": len(source), "cell_subtypes": len(annotations),
        "depot_totals": {k: int(v) for k, v in totals.items()}, "pooled_objects": int(source.n.sum()),
        "percent_denominator": "all myeloid objects in the same depot",
        "percent_max_abs_error": float(np.max(np.abs(source.within_depot_percent - source.percent))),
        "dot_area": f"{max_area} pt^2 * n / {size_max}",
        "color_scale_percent": config["color_range_percent"],
        "color_stops": config["color_stops"],
        "group_colors": config["group_colors"],
        "size_legend_color": size_legend_color,
        "canvas_mm": [width, height], "text_pt": text_pt,
        "layout_reference_coordinates": [layout_width, layout_height],
        "font_family": family, "font_file": font_path,
        "mark_style": mark_style,
        "visual_style": visual,
        "legend_layout": legend_report,
        "main_plot_bbox_mm": plot_bbox_mm,
        "reserved_legend_band_mm": [0, 0, width, body_bottom * height / layout_height],
        "row_pitch_reference_units": row_pitch,
        "labels_outside_canvas": clipped, "source_data_sampled": False,
        "hypothesis_tests": "none; source contains pooled object counts, not participant replicates",
    }
    (output / "validation.json").write_text(json.dumps(audit, indent=2) + "\n")
    plt.close(fig)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
