#!/usr/bin/env python3
"""Independent, portable image-data reproduction of one supplied radar chart."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-radar-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle
import numpy as np
import pandas as pd
from PIL import Image
import pymupdf

ROOT = Path(__file__).resolve().parent


def write_json(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2) + "\n")


def main():
    settings = json.loads((ROOT / "settings.json").read_text())
    layout = settings["layout"]
    source_path = ROOT / settings["input_data"]
    # The original text is retained here to avoid rounding small source values.
    source_text = pd.read_csv(source_path, dtype=str)
    data = source_text.copy()
    data["acceptance_rate"] = pd.to_numeric(data["acceptance_rate"], errors="raise")
    classes = settings["cell_classes_clockwise_from_top"]
    methods = settings["methods_in_legend_and_drawing_order"]
    class_order = [c["source"] for c in classes]
    method_order = [m["source"] for m in methods]
    required_pairs = {(m, c) for m in method_order for c in class_order}
    actual_pairs = set(zip(data.integration_method, data.cell_class))
    if len(data) != 25 or actual_pairs != required_pairs or data.duplicated(["integration_method", "cell_class"]).any():
        raise ValueError("Source must contain exactly the 25 unique required method–class pairs.")
    values = data.acceptance_rate.to_numpy()
    if not np.isfinite(values).all() or not ((values >= 0) & (values <= 1)).all():
        raise ValueError("Acceptance rates must be finite numeric values in [0, 1].")
    radial = settings["radial_scale"]
    r_min, r_max = radial["limits"]
    if radial["origin"] != 0 or r_min != 0 or values.max() > r_max:
        raise ValueError("Adopted zero-origin display must contain every supplied value.")
    try:
        font_path = font_manager.findfont(layout["font_requested"], fallback_to_default=False)
    except ValueError:
        font_path = font_manager.findfont(layout["font_fallback"], fallback_to_default=False)
    actual_font = font_manager.FontProperties(fname=font_path).get_name()
    layout["font_actual"] = actual_font
    layout["font_file"] = font_path
    write_json("settings.json", settings)
    plt.rcParams.update({
        "font.family": actual_font, "font.size": layout["font_size_pt"],
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "savefig.bbox": None, "axes.unicode_minus": False,
    })

    width_mm, height_mm = layout["width_mm"], layout["height_mm"]
    fig = plt.figure(figsize=(width_mm / 25.4, height_mm / 25.4), dpi=layout["dpi"], facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, width_mm), ylim=(0, height_mm), aspect="equal")
    ax.axis("off")
    ax.set_axisbelow(True)
    cx, cy = layout["center_mm"]
    radius = layout["radius_mm"]
    angle_deg = 90 - np.arange(5) * 72
    theta = np.deg2rad(angle_deg)
    direction = np.column_stack([np.cos(theta), np.sin(theta)])
    background = Circle((cx, cy), radius, facecolor=settings["colors"]["background"], edgecolor="none", zorder=0)
    ax.add_patch(background)
    for dx, dy in direction:
        ax.plot([cx, cx + radius * dx], [cy, cy + radius * dy], color=settings["colors"]["spokes_and_outer_ring"], linewidth=layout["grid_line_width_pt"], zorder=1)
    for value in radial["ticks"][1:]:
        color = settings["colors"]["intermediate_ring"] if value != r_max else settings["colors"]["spokes_and_outer_ring"]
        ax.add_patch(Circle((cx, cy), radius * value / r_max, fill=False, edgecolor=color, linewidth=layout["grid_line_width_pt"], linestyle=(0, (4, 3)), zorder=1))

    plotted_vertices = []
    for method_index, method in enumerate(methods):
        rows = data[data.integration_method == method["source"]].set_index("cell_class").loc[class_order]
        rates = rows.acceptance_rate.to_numpy()
        points = np.array([cx, cy]) + (radius * rates / r_max)[:, None] * direction
        closed = np.vstack([points, points[0]])
        ax.plot(closed[:, 0], closed[:, 1], color=method["color"], linewidth=layout["line_width_pt"], zorder=3 + method_index * .1)
        ax.plot(points[:, 0], points[:, 1], linestyle="none", marker="o", markersize=layout["marker_diameter_pt"], markeredgewidth=0, color=method["color"], zorder=4 + method_index * .1)
        for idx, cell in enumerate(classes):
            source_row = source_text[(source_text.integration_method == method["source"]) & (source_text.cell_class == cell["source"])].iloc[0]
            plotted_vertices.append({
                "integration_method": method["source"], "cell_class": cell["source"],
                "acceptance_rate": source_row.acceptance_rate,
                "method_label": method["display"], "cell_class_label": cell["display"],
                "angle_degrees_counterclockwise_from_right": int(angle_deg[idx]),
                "x_mm": float(points[idx, 0]), "y_mm": float(points[idx, 1]),
            })
    pd.DataFrame(plotted_vertices).to_csv(ROOT / "plotting-data.csv", index=False)

    texts = []
    def label(x, y, value, role="axis", **kwargs):
        t = ax.text(x, y, value, fontsize=settings["typography"][role], va="center", zorder=10, **kwargs)
        texts.append(t)
        return t
    label(cx, 84.5, "depot", role="title", ha="center")
    label(cx, 80.25, "all", ha="center")
    label(69.6, 60.3, "FAPs", ha="left")
    label(60.25, 29.6, "vascular", ha="left")
    label(27.75, 29.6, "immune", ha="right")
    label(18.4, 60.3, "adipocytes", ha="right")
    for value in radial["ticks"]:
        label(cx - layout["radial_label_offset_mm"], cy + radius * value / r_max, f"{value:g}", role="tick", ha="right")
    label(cx, 23.4, "kBET", ha="center")
    label(cx, 19.6, "(acceptance rate)", ha="center")

    # A readable left-to-right order across the first and then the second row.
    legend_positions = [(14, 11.8), (35.3, 11.8), (64, 11.8), (26.5, 6.4), (52, 6.4)]
    for method, (x, y) in zip(methods, legend_positions):
        ax.plot([x, x + 5.5], [y, y], color=method["color"], linewidth=layout["line_width_pt"], zorder=5)
        ax.plot([x + 2.75], [y], marker="o", linestyle="none", markersize=layout["marker_diameter_pt"], markeredgewidth=0, color=method["color"], zorder=6)
        label(x + 7.2, y, method["display"], role="legend", ha="left")

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    text_boxes = []
    for t in texts:
        box = t.get_window_extent(renderer)
        text_boxes.append({"text": t.get_text(), "bbox_px": list(box.bounds), "inside_canvas": bool(box.x0 >= 0 and box.y0 >= 0 and box.x1 <= canvas.x1 and box.y1 <= canvas.y1)})
    overlap_pairs = []
    for i, one in enumerate(texts):
        for two in texts[i + 1:]:
            if one.get_window_extent(renderer).overlaps(two.get_window_extent(renderer)):
                overlap_pairs.append([one.get_text(), two.get_text()])
    for extension in settings["formats"]:
        fig.savefig(ROOT / f"panel.{extension}", dpi=layout["dpi"], bbox_inches=None, pad_inches=0)
    plt.close(fig)

    with pymupdf.open(ROOT / "panel.pdf") as document:
        page = document[0]
        pdf_mm = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
        spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block for line in block["lines"] for span in line["spans"]]
        pdf_font_sizes = sorted({round(s["size"], 4) for s in spans})
        pdf_fonts = [{"basefont": f[3], "type": f[2], "embedded": bool(document.extract_font(f[0])[3])} for f in page.get_fonts()]
    svg = ET.parse(ROOT / "panel.svg").getroot()
    svg_pt = [float(svg.attrib[key].removesuffix("pt")) for key in ["width", "height"]]
    svg_mm = [p / 72 * 25.4 for p in svg_pt]
    with Image.open(ROOT / "panel.png") as im:
        png_size = list(im.size)
        png_dpi = list(im.info.get("dpi", ()))
    expected_pixels = [round(dim / 25.4 * layout["dpi"]) for dim in [width_mm, height_mm]]
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    stats = {
        "hypothesis_tests": [], "new_hypothesis_test_performed": False,
        "upstream_analysis_recomputed": False,
        "statistical_layer": "Only supplied kBET acceptance rates; no uncertainty or inferential layer",
        "source_rows": int(len(data)), "plotted_vertices": len(plotted_vertices), "unique_pairs": len(actual_pairs),
        "methods": len(method_order), "cell_classes": len(class_order),
        "missing_values": int(data.isna().sum().sum()), "zero_values": int((values == 0).sum()),
        "minimum": float(values.min()), "maximum": float(values.max()),
        "excluded_rows": 0, "imputed_rows": 0, "source_sha256": source_hash,
    }
    write_json("stats.json", stats)
    qa = {
        "schema_version": "1.0", "overall_status": "not_reviewed",
        "review_packet": {"reference": settings["reference_image"], "candidate": "panel.png", "specification": "adopted-spec.md", "settings": "settings.json"},
        "visual_review": {"status": "not_reviewed", "reviewer_role": "implementer", "pass_number": 0, "findings": [], "independent_review": "Pending separate reviewer"},
        "numerical_checks": {
            "data_coverage": {"status": "passed", "evidence": stats},
            "source_text_values_retained": {"status": "passed", "evidence": "plotting-data.csv retains the unchanged acceptance_rate string for each method–class pair"},
            "pdf_canvas": {"status": "passed" if np.allclose(pdf_mm, [width_mm, height_mm], atol=.001) else "failed", "measured_mm": pdf_mm},
            "svg_canvas": {"status": "passed" if np.allclose(svg_mm, [width_mm, height_mm], atol=.001) else "failed", "measured_mm": svg_mm},
            "png_canvas": {"status": "passed" if png_size == expected_pixels else "failed", "measured_px": png_size, "expected_px": expected_pixels, "dpi_metadata": png_dpi},
            "pdf_fonts": {"status": "passed" if pdf_font_sizes == [8.0] and all(f["embedded"] for f in pdf_fonts) else "failed", "text_sizes_pt": pdf_font_sizes, "fonts": pdf_fonts},
            "svg_text_editability": {"status": "passed" if len(svg.findall('.//{http://www.w3.org/2000/svg}text')) > 0 else "failed", "text_elements": len(svg.findall('.//{http://www.w3.org/2000/svg}text'))},
            "text_canvas_boundaries": {"status": "passed" if all(t["inside_canvas"] for t in text_boxes) else "failed", "measurement": "Matplotlib renderer text bounding boxes", "labels": text_boxes},
            "text_text_overlap": {"status": "passed" if not overlap_pairs else "failed", "overlap_pairs": overlap_pairs, "limitation": "Does not detect text–mark overlap; requires visual inspection"},
        },
        "residual_notes": settings["intentional_differences"],
    }
    write_json("qa.json", qa)
    print(json.dumps({"output": str(ROOT), "font": actual_font, "source_values": len(data), "zero_values": int((values == 0).sum()), "checks": {k:v["status"] for k,v in qa["numerical_checks"].items()}}, indent=2))


if __name__ == "__main__":
    main()
