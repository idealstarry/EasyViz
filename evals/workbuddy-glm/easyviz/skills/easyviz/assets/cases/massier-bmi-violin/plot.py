#!/usr/bin/env python3
"""Render a user-requested style adaptation of the standalone BMI reconstruction.

Run from any directory: /path/to/python /path/to/plot.py
Dependencies: matplotlib, numpy, pandas, scipy, Pillow, pymupdf.
No network access or original author plotting code is used.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-massier-mpl"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "easyviz-massier-cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
import scipy
from scipy.stats import gaussian_kde
from PIL import Image
import fitz


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    settings = json.loads((BASE / "settings.json").read_text())
    source = BASE / settings["source_data"]
    # Text import preserves all original numeric strings and empty BMI cells.
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    assert list(frame.columns) == ["source_row", "source_id", "cohort", "bmi"]
    bmi = pd.to_numeric(frame["bmi"].replace("", np.nan), errors="raise")
    available = bmi.notna()
    assert np.isfinite(bmi[available]).all(), "Non-finite BMI requires explicit treatment"
    assert len(frame) == settings["expected_records"]
    assert int(available.sum()) == settings["expected_available_bmi"]
    assert int((~available).sum()) == settings["expected_missing_bmi"]
    assert frame["source_row"].is_unique
    order = settings["axis"]["y_order_top_to_bottom"]
    assert set(frame["cohort"]) == set(order)

    plotting = frame.copy()
    plotting["cohort_display"] = plotting["cohort"].map(settings["cohort_labels"])
    plotting["included_in_density"] = available
    plotting["exclusion_reason"] = np.where(available, "", "missing BMI (empty source field)")
    plotting.to_csv(BASE / "plotting-data.csv", index=False)

    requested_font = settings["font"]["requested"]
    try:
        font_path = font_manager.findfont(requested_font, fallback_to_default=False)
        actual_font = font_manager.FontProperties(fname=font_path).get_name()
    except ValueError:
        actual_font = settings["font"]["fallback"]
        font_path = font_manager.findfont(actual_font, fallback_to_default=False)
    settings["font"]["actual"] = actual_font
    settings["font"]["resolved_font_path"] = font_path
    dump(BASE / "settings.json", settings)
    plt.rcParams.update({
        "font.family": actual_font, "font.size": 8,
        "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "figure.titlesize": 8,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "axes.unicode_minus": False,
    })

    prepared = []
    cohort_stats = []
    density_rows = []
    for cohort in order:
        mask = frame["cohort"].eq(cohort)
        values = bmi[mask & available].to_numpy(dtype=float)
        assert len(values) >= 2 and np.std(values, ddof=1) > 0
        kde = gaussian_kde(values, bw_method="scott")
        grid = np.linspace(values.min(), values.max(), settings["density"]["grid_points_per_cohort"])
        raw_density = kde(grid)
        # Normalize the visible area after the explicit observed-range trim.
        visible_mass = float(np.trapezoid(raw_density, grid))
        displayed_density = raw_density / visible_mass
        prepared.append((cohort, grid, raw_density, displayed_density))
        cohort_stats.append({
            "cohort": cohort, "display_label": settings["cohort_labels"][cohort],
            "source_records": int(mask.sum()), "n_available_bmi": int(len(values)),
            "n_missing_bmi": int((mask & ~available).sum()),
            "missing_source_rows": frame.loc[mask & ~available, "source_row"].tolist(),
            "min_bmi": float(values.min()), "max_bmi": float(values.max()),
            "sample_sd_bmi": float(np.std(values, ddof=1)),
            "quartiles_bmi": np.quantile(values, [0.25, 0.5, 0.75], method="linear").tolist(),
            "scott_factor": float(kde.factor),
            "bandwidth_bmi_units": float(np.sqrt(kde.covariance[0, 0])),
            "kde_mass_inside_observed_range": visible_mass,
            "displayed_density_integral": float(np.trapezoid(displayed_density, grid)),
        })
    max_density = max(float(item[3].max()) for item in prepared)
    half_thickness = settings["layout"]["maximum_violin_thickness_rows"] / 2
    scale = half_thickness / max_density

    canvas = settings["canvas"]
    palette = settings["palette"]
    fig = plt.figure(figsize=(canvas["width_mm"] / 25.4, canvas["height_mm"] / 25.4),
                     dpi=canvas["dpi"], facecolor=palette["background"])
    ax = fig.add_axes(settings["layout"]["axes_bounds_fraction"])
    ax.set_facecolor(palette["background"])
    ax.set_axisbelow(True)
    ax.set_xlim(settings["axis"]["x_limits"])
    ax.set_xticks(settings["axis"]["x_major_ticks"])
    ax.set_xticks(settings["axis"]["x_minor_ticks"], minor=True)
    ax.grid(axis="x", which="both", color=palette["grid"],
            linewidth=settings["layout"]["grid_width_pt"], zorder=0)
    for row, (cohort, grid, raw_density, displayed_density) in enumerate(prepared):
        width = displayed_density * scale
        ax.fill_between(grid, row - width, row + width,
                        facecolor=palette["fill"], edgecolor=palette["outline"],
                        linewidth=settings["layout"]["violin_outline_width_pt"], zorder=3)
        q1, median, q3 = cohort_stats[row]["quartiles_bmi"]
        ax.plot([q1, q3], [row, row], color=palette["summary"],
                linewidth=settings["summary"]["line_width_pt"], solid_capstyle="round", zorder=4)
        ax.plot(median, row, "o", color=palette["summary"], markeredgewidth=0,
                markersize=settings["summary"]["median_diameter_pt"], zorder=5)
        for x, raw, density, half_width in zip(grid, raw_density, displayed_density, width):
            density_rows.append({"cohort": cohort, "bmi": x, "raw_kde": raw,
                                 "displayed_density": density, "half_width_rows": half_width})
    ax.set_ylim(len(order) - 0.35, -0.65)
    ax.set_yticks(range(len(order)), [settings["cohort_labels"][c] for c in order])
    ax.set_xlabel(settings["axis"]["x_label"], labelpad=6, fontsize=8)
    ax.tick_params(axis="both", which="major", color=palette["text"], labelcolor=palette["text"],
                   width=0.6, length=3, pad=4, labelsize=8)
    ax.tick_params(axis="x", which="minor", length=0)
    ax.tick_params(axis="y", length=0, pad=7)
    for side in ["right", "top", "left"]:
        ax.spines[side].set_visible(False)
    for side in ["bottom"]:
        ax.spines[side].set_linewidth(settings["layout"]["spine_width_pt"])
        ax.spines[side].set_color(palette["text"])

    # Check all text at the full fixed-size canvas before export.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas_box = fig.bbox
    text_bounds = []
    for artist in [ax.xaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()]:
        box = artist.get_window_extent(renderer)
        text_bounds.append({"text": artist.get_text(), "font_size_pt": artist.get_fontsize(),
                            "inside_canvas": bool(box.x0 >= 0 and box.y0 >= 0 and
                                                  box.x1 <= canvas_box.width and box.y1 <= canvas_box.height)})
    assert all(t["inside_canvas"] for t in text_bounds), "Text extends beyond fixed canvas"
    assert all(t["font_size_pt"] == 8 for t in text_bounds)
    assert bmi[available].between(*settings["axis"]["x_limits"]).all()
    for suffix in canvas["formats"]:
        fig.savefig(BASE / f"panel.{suffix}", dpi=canvas["dpi"], facecolor=palette["background"])
    plt.close(fig)

    pd.DataFrame(density_rows).to_csv(BASE / "density-data.csv", index=False)
    stats = {
        "method": "Gaussian kernel density estimation (KDE)",
        "implementation": "scipy.stats.gaussian_kde", "scipy_version": scipy.__version__,
        "bandwidth_rule": "Scott: sample SD (ddof=1) × n^(-1/5)",
        "parameter_provenance": "Chosen independently; original author density parameters are unknown",
        "support": settings["density"]["support"], "grid_points_per_cohort": 512,
        "normalization": settings["density"]["normalization"], "density_to_half_width_multiplier": scale,
        "boundary_correction": "none", "hypothesis_test": None,
        "summary_marks": settings["summary"],
        "unit": "participant record", "all_source_records": len(frame),
        "available_bmi": int(available.sum()), "missing_bmi": int((~available).sum()),
        "missing_value_handling": settings["density"]["missing"], "cohorts": cohort_stats,
        "source_sha256": sha256(source),
        "software_versions": {"matplotlib": matplotlib.__version__, "numpy": np.__version__,
                              "pandas": pd.__version__, "scipy": scipy.__version__},
    }
    dump(BASE / "stats.json", stats)

    with Image.open(BASE / "panel.png") as png:
        png_size = list(png.size)
        png_dpi = list(png.info.get("dpi", []))
    with fitz.open(BASE / "panel.pdf") as pdf:
        page = pdf[0]
        pdf_mm = [float(page.rect.width * 25.4 / 72), float(page.rect.height * 25.4 / 72)]
        pdf_fonts = [list(font) for font in page.get_fonts(full=True)]
        font_sizes = sorted({round(span["size"], 4)
                             for block in page.get_text("dict")["blocks"] if "lines" in block
                             for line in block["lines"] for span in line["spans"]})
        embedded_fonts = []
        for font in pdf_fonts:
            extracted = pdf.extract_font(font[0])
            embedded_fonts.append({"font_name": font[3], "embedded": len(extracted[3]) > 0})
        pdf_text = page.get_text()
    svg = ET.parse(BASE / "panel.svg").getroot()
    svg_pt = [float(svg.attrib[key].removesuffix("pt")) for key in ["width", "height"]]
    svg_mm = [value * 25.4 / 72 for value in svg_pt]
    # Agg truncates fractional canvas pixels; vector dimensions stay exact.
    expected_px = [int(canvas[key] / 25.4 * canvas["dpi"]) for key in ["width_mm", "height_mm"]]
    expected_mm = [canvas["width_mm"], canvas["height_mm"]]
    checks = {
        "all_864_source_rows_preserved": len(plotting) == 864,
        "all_858_available_bmi_used": sum(c["n_available_bmi"] for c in cohort_stats) == 858,
        "all_6_missing_bmi_reported": sum(c["n_missing_bmi"] for c in cohort_stats) == 6,
        "all_available_bmi_inside_axis": bool(bmi[available].between(*settings["axis"]["x_limits"]).all()),
        "all_8_cohort_labels_in_pdf": all(settings["cohort_labels"][c] in pdf_text for c in order),
        "all_text_8pt": font_sizes == [8.0],
        "all_text_inside_canvas": all(t["inside_canvas"] for t in text_bounds),
        "pdf_canvas_160_by_100_mm": bool(np.allclose(pdf_mm, expected_mm, atol=0.001)),
        "svg_canvas_160_by_100_mm": bool(np.allclose(svg_mm, expected_mm, atol=0.001)),
        "png_dimensions_at_300dpi": png_size == expected_px,
        "png_resolution_metadata_300dpi": bool(np.allclose(png_dpi, [300, 300], atol=0.01)),
        "pdf_fonts_embedded": all(x["embedded"] for x in embedded_fonts),
        "all_displayed_densities_integrate_to_one": all(abs(c["displayed_density_integral"] - 1) < 1e-10 for c in cohort_stats),
    }
    assert all(checks.values()), checks
    qa = {
        "status": "awaiting_visual_review", "render_pass": 2,
        "numerical_checks": {k: {"status": "passed" if value else "failed"} for k, value in checks.items()},
        "measurements": {"pdf_mm": pdf_mm, "svg_mm": svg_mm, "png_pixels": png_size,
                         "png_dpi": png_dpi, "pdf_font_sizes_pt": font_sizes,
                         "pdf_fonts": embedded_fonts, "resolved_font": actual_font},
        "text_bounds": text_bounds,
        "visual_review": {"status": "pending", "independent": False},
        "residual_uncertainties": ["Original density estimator, bandwidth, support, boundary correction and normalization are unknown.",
                                   "Blue fill and white summary marks are user-requested style adaptations.",
                                   "The 160 × 100 mm canvas adapts the reference column geometry; historical independent reviews do not assess this revision."],
        "output_sha256": {f"panel.{suffix}": sha256(BASE / f"panel.{suffix}") for suffix in canvas["formats"]},
    }
    # Preserve original visual-review results if this is an unchanged portable rerun.
    prior_qa = BASE / "qa.json"
    if prior_qa.exists():
        old = json.loads(prior_qa.read_text())
        if old.get("output_sha256", {}).get("panel.png") == qa["output_sha256"]["panel.png"]:
            qa["visual_review"] = old.get("visual_review", qa["visual_review"])
            qa["status"] = old.get("status", qa["status"])
            if "independent_data_verification" in old:
                qa["independent_data_verification"] = old["independent_data_verification"]
    dump(prior_qa, qa)
    # Immutable first rendering: later revisions must not erase the evaluation trace.
    first = BASE / "first-render"
    if not first.exists():
        first.mkdir()
        for name in ["plot.py", "settings.json", "stats.json", "qa.json", "panel.pdf", "panel.svg", "panel.png"]:
            shutil.copyfile(BASE / name, first / name)
    print(json.dumps({"output_dir": str(BASE), "checks_passed": len(checks),
                      "records": len(frame), "available_bmi": int(available.sum()),
                      "missing_bmi": int((~available).sum()), "font": actual_font,
                      "canvas_mm": expected_mm, "png_pixels": png_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
