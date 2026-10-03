#!/usr/bin/env python3
"""Data-only create showcase: one annotated inhibition matrix at final print size."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
import warnings
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap, LinearSegmentedColormap, Normalize, TwoSlopeNorm
from matplotlib.patches import Patch, Rectangle
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def color_scale(cfg, values):
    """Return an explicit invertible scale; reject any clipped source value."""
    lo, hi = cfg["color_limits"]
    values = np.asarray(values, dtype=float)
    if not np.isfinite([lo, hi]).all() or lo >= hi:
        raise ValueError("Color limits must be finite and increasing")
    if not np.isfinite(values).all() or values.min() < lo or values.max() > hi:
        raise ValueError("Color limits would clip measurements")
    method = cfg.get("color_normalization", "linear")
    if method == "two_slope":
        center = cfg["color_center"]
        if not np.isfinite(center) or not lo < center < hi:
            raise ValueError("Two-slope center must be strictly inside the color limits")
        norm = TwoSlopeNorm(vmin=lo, vcenter=center, vmax=hi)
        forward = [f"x <= {center}: 0.5 * (x - ({lo})) / ({center} - ({lo}))",
                   f"x >= {center}: 0.5 + 0.5 * (x - ({center})) / ({hi} - ({center}))"]
        inverse = [f"u <= 0.5: {lo} + 2 * u * ({center} - ({lo}))",
                   f"u >= 0.5: {center} + 2 * (u - 0.5) * ({hi} - ({center}))"]
    elif method == "linear":
        center = None
        norm = Normalize(vmin=lo, vmax=hi, clip=False)
        forward = [f"u = (x - ({lo})) / ({hi} - ({lo}))"]
        inverse = [f"x = {lo} + u * ({hi} - ({lo}))"]
    else:
        raise ValueError(f"Unsupported color normalization: {method}")
    palette = cfg.get("color_stops", cfg["colormap"])
    if "color_stops" in cfg:
        positions = np.asarray([stop[0] for stop in palette], dtype=float)
        if positions[0] != 0 or positions[-1] != 1 or not np.all(np.diff(positions) > 0):
            raise ValueError("Color-stop positions must increase from 0 to 1")
    cmap = LinearSegmentedColormap.from_list("easyviz_case", palette, N=1025) if isinstance(palette, list) else plt.get_cmap(palette)
    luminance_check = None
    if cfg.get("check_branch_luminance", False):
        if method != "two_slope":
            raise ValueError("Branch luminance check requires two-slope normalization")
        coordinates = np.linspace(0, 1, 1025)
        rgb = np.asarray(cmap(coordinates))[:, :3]
        linear_rgb = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
        luminance = linear_rgb @ np.array([.2126, .7152, .0722])
        lower, upper = np.diff(luminance[:513]), np.diff(luminance[512:])
        if not np.all(lower >= -1e-12) or not np.all(upper <= 1e-12):
            raise ValueError("Diverging branch luminance must increase toward zero and decrease away from zero")
        luminance_check = {"space": "sRGB relative luminance", "sampled_color_coordinates": len(coordinates),
                           "negative_arm_nondecreasing": True, "positive_arm_nonincreasing": True,
                           "negative_arm_minimum_increment": float(lower.min()),
                           "positive_arm_maximum_increment": float(upper.max()),
                           "zero_relative_luminance": float(luminance[512])}
    probes = np.unique(np.r_[np.linspace(lo, hi, 29), values.ravel(), center if center is not None else []])
    normalized = np.asarray(norm(probes))
    if not np.all(np.diff(normalized) > 0) or not np.allclose(norm.inverse(normalized), probes, atol=1e-10):
        raise ValueError("Color scale must be strictly ordered and invertible")
    contract = {"class": type(norm).__name__, "method": method, "vmin": lo,
                "vcenter": center, "vmax": hi, "clip": False,
                "forward_piecewise": forward, "inverse_piecewise": inverse,
                "neutral_normalized_position": float(norm(center)) if center is not None else None,
                "source_values_normalized_range": [float(norm(values.min())), float(norm(values.max()))],
                "order_and_inverse_checked_points": len(probes), "strict_order_and_inverse_pass": True,
                "color_stops": [{"normalized_position": stop[0], "raw_minutes": float(norm.inverse(stop[0])), "color": stop[1]} for stop in cfg.get("color_stops", [])],
                "branch_luminance_check": luminance_check,
                "readout_mapping": "Colorbar tick positions use norm(raw minutes); inverse(norm(x)) returns original minutes."}
    return norm, cmap, contract


def run(out, data_path=HERE / "source-data.csv", genome_path=HERE / "genome-status.csv", settings_path=HERE / "settings.json"):
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False})
    cfg = json.loads(settings_path.read_text())
    # Inspect raw column identifiers before pandas can replace empty/duplicate headers.
    with data_path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), [])
    if not header or header[0] != "sender":
        raise ValueError("Matrix CSV must start with the sender identifier column")
    if not all(identifier.strip() for identifier in header[1:]):
        raise ValueError("Matrix column IDs must be nonempty")
    if len(set(header[1:])) != len(header[1:]):
        raise ValueError("Matrix column IDs must be unique")
    full = pd.read_csv(data_path, dtype={"sender": str}, index_col="sender", keep_default_na=False)
    full.index = full.index.astype(str)
    status = pd.read_csv(genome_path, dtype={"strain": str}, index_col="strain", keep_default_na=False)["genome"]
    for role, identifiers in (("Matrix row", full.index), ("Annotation strain", status.index)):
        if not all(str(identifier).strip() for identifier in identifiers):
            raise ValueError(f"{role} IDs must be nonempty")
    n = len(full)
    assert n >= 2 and full.shape == (n, n) and full.index.is_unique and full.columns.is_unique, "Need a square matrix with unique strain IDs"
    assert np.isfinite(full.values).all() and set(full.index) == set(full.columns)
    assert status.index.is_unique and set(status.index) == set(full.index) and set(status).issubset({0, 1})
    norm, cmap, normalization = color_scale(cfg, full.values)
    lo, hi = cfg["color_limits"]
    count = cfg["selection_count"]
    assert isinstance(count, int) and 2 <= count <= n, "selection_count must be an integer in 2..number of strains"
    ranks = np.rint(np.linspace(0, len(full) - 1, count)).astype(int)
    assert len(set(ranks)) == count
    summaries, chosen = [], {}
    for role, means in (("sender", full.mean(axis=1)), ("receiver", full.mean(axis=0))):
        table = pd.DataFrame({"strain": means.index, "full_matrix_mean_gii_min": means.to_numpy()})
        table = table.sort_values(["full_matrix_mean_gii_min", "strain"], ascending=[False, True], kind="stable").reset_index(drop=True)
        table["role"] = role
        table["mean_rank"] = np.arange(len(table)) + 1
        table["genome_analyzed"] = table.strain.map(status)
        table["selected"] = table.index.isin(ranks)
        table["denominator"] = n
        summaries.append(table)
        chosen[role] = table.iloc[ranks].copy()
    summary = pd.concat(summaries, ignore_index=True)
    rows, cols = chosen["sender"].strain.tolist(), chosen["receiver"].strain.tolist()
    shown = full.loc[rows, cols]
    selected = shown.rename_axis(index="sender", columns="receiver").stack().rename("gii_min").reset_index()
    selected["sender_rank"] = selected.sender.map(chosen["sender"].set_index("strain").mean_rank)
    selected["receiver_rank"] = selected.receiver.map(chosen["receiver"].set_index("strain").mean_rank)
    assert len(selected) == count ** 2
    assert np.array_equal(selected.gii_min.to_numpy(), shown.to_numpy().ravel())
    fontpath = font_manager.findfont(font_manager.FontProperties(family=cfg["font"]), fallback_to_default=True)
    font = font_manager.FontProperties(fname=fontpath).get_name()
    width, height, dpi = cfg["width_mm"], cfg["height_mm"], cfg["dpi"]
    rc = {"font.family": font, "font.size": cfg["font_size_pt"], "axes.labelsize": cfg["font_size_pt"], "xtick.labelsize": cfg["font_size_pt"], "ytick.labelsize": cfg["font_size_pt"], "axes.linewidth": cfg["line_width_pt"], "axes.edgecolor": cfg.get("axis_color", "#252E31"), "text.color": cfg.get("text_color", "#252E31"), "axes.labelcolor": cfg.get("text_color", "#252E31"), "xtick.color": cfg.get("text_color", "#252E31"), "ytick.color": cfg.get("text_color", "#252E31"), "xtick.major.width": cfg["line_width_pt"], "ytick.major.width": cfg["line_width_pt"], "pdf.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "easyviz-annotated-inhibition"}
    with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        fig = plt.figure(figsize=(width / 25.4, height / 25.4), dpi=dpi, facecolor="white")

        def axis(key):
            x, y, w, h = cfg[key]
            return fig.add_axes([x / width, y / height, w / width, h / height])

        def text(key, label, **kwargs):
            x, y = cfg["text_positions_mm"][key]
            return fig.text(x / width, y / height, label, **kwargs)

        ax = axis("heatmap_mm")
        image = ax.imshow(shown, cmap=cmap, norm=norm, aspect="equal", interpolation="nearest")
        ax.set_xticks(range(count), cols, rotation=90, ha="center", va="top")
        ax.set_yticks(range(count), rows)
        ax.tick_params(length=0, pad=3)
        for spine in ax.spines.values():
            spine.set_visible(False)
        text("sender_axis", "Sender strain", rotation=90, ha="center", va="center")
        text("receiver_axis", "Receiver strain", ha="center", va="center")

        def mean_axis_limits(role):
            values = chosen[role].full_matrix_mean_gii_min
            if f"{role}_mean_limits" in cfg:
                limits = cfg[f"{role}_mean_limits"]
                ticks = cfg.get(f"{role}_mean_ticks", np.linspace(*limits, 3).tolist())
            else:
                low, high = min(0, values.min()), max(0, values.max())
                if low == high:
                    high = low + 1
                ticks = MaxNLocator(nbins=3).tick_values(low, high).tolist()
                limits = [ticks[0], ticks[-1]]
            assert len(limits) == 2 and limits[0] <= min(0, values.min()) <= max(0, values.max()) <= limits[1], "Mean limits would clip bars"
            return limits, ticks

        # Top bar heights and side bar lengths use all partners, not the crop.
        top = axis("receiver_mean_mm")
        top.bar(np.arange(count), chosen["receiver"].full_matrix_mean_gii_min, width=.82, color=cfg["mean_color"], linewidth=0, zorder=2)
        top.set_xlim(-.5, count - .5)
        limits, ticks = mean_axis_limits("receiver")
        top.set_ylim(*limits)
        top.set_yticks(ticks)
        top.set_xticks([])
        top.tick_params(length=1.5, pad=2, color=cfg.get("axis_color", "#252E31"))
        top.set_axisbelow(True)
        if cfg.get("mean_grid", False):
            top.grid(axis="y", color=cfg["grid_color"], linewidth=cfg.get("grid_width_pt", .35))
        top.spines[["top", "right", "bottom"]].set_visible(False)
        text("receiver_mean", "Receiver mean GII (min)", ha="left", va="bottom")

        right = axis("sender_mean_mm")
        right.barh(np.arange(count), chosen["sender"].full_matrix_mean_gii_min, height=.82, color=cfg["mean_color"], linewidth=0, zorder=2)
        right.set_ylim(count - .5, -.5)
        limits, ticks = mean_axis_limits("sender")
        right.set_xlim(*limits)
        right.set_xticks(ticks)
        right.set_yticks([])
        right.tick_params(length=1.5, pad=2, color=cfg.get("axis_color", "#252E31"))
        right.set_axisbelow(True)
        if cfg.get("mean_grid", False):
            right.grid(axis="x", color=cfg["grid_color"], linewidth=cfg.get("grid_width_pt", .35))
        right.spines[["top", "right", "left"]].set_visible(False)
        text("sender_mean", "Sender mean (min)", ha="left", va="bottom")

        binary = ListedColormap([cfg["genome_colors"][str(v)] for v in (0, 1)])
        for key, array in (("receiver_genome_mm", status.loc[cols].to_numpy()[None, :]), ("sender_genome_mm", status.loc[rows].to_numpy()[:, None])):
            strip = axis(key)
            strip.imshow(array, cmap=binary, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
            # White, unfilled binary cells need an explicit boundary at 2 mm.
            for row, column in zip(*np.where(array == 0)):
                strip.add_patch(Rectangle((column - .5, row - .5), 1, 1, facecolor="none",
                                          edgecolor=cfg["axis_color"], linewidth=cfg["line_width_pt"]))
            strip.set_axis_off()

        barax = axis("colorbar_mm")
        ticks = cfg.get("colorbar_ticks", np.linspace(lo, hi, 5).tolist())
        # A changed transfer range retains informative in-range ticks plus its endpoints/center.
        ticks = sorted(set([lo, hi] + [v for v in ticks if lo <= v <= hi] +
                           ([cfg["color_center"]] if cfg.get("color_normalization") == "two_slope" else [])))
        cb = fig.colorbar(image, cax=barax, orientation="horizontal", ticks=ticks)
        cb.outline.set_visible(False)
        cb.ax.tick_params(length=1.5, pad=2, color=cfg.get("axis_color", "#252E31"))
        text("colorbar_title", "Pairwise GII (min)", ha="center", va="bottom")
        legend_x, legend_y = cfg["text_positions_mm"]["genome_legend"]
        fig.legend(handles=[Patch(facecolor=cfg["genome_colors"]["1"], edgecolor="none", label="Genome analyzed"), Patch(facecolor=cfg["genome_colors"]["0"], edgecolor=cfg["axis_color"], linewidth=cfg["line_width_pt"], label="Not analyzed")], loc="lower left", bbox_to_anchor=(legend_x / width, legend_y / height), borderaxespad=0, frameon=False, ncol=2, handlelength=1.0, handleheight=.8, columnspacing=1.3)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        clipped = []
        for artist in fig.findobj(Text):
            if artist.get_visible() and artist.get_text().strip():
                bounds = artist.get_window_extent(renderer)
                if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.width + 1 or bounds.y1 > fig.bbox.height + 1:
                    clipped.append(artist.get_text())
        fig.savefig(out / "panel.pdf", bbox_inches=None, metadata={"CreationDate": None, "ModDate": None, "Creator": "EasyViz"})
        fig.savefig(out / "panel.svg", bbox_inches=None, metadata={"Date": None, "Creator": "EasyViz"})
        pixels = [round(width / 25.4 * dpi), round(height / 25.4 * dpi)]
        fig.set_size_inches(pixels[0] / dpi, pixels[1] / dpi)
        fig.canvas.draw()
        Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert("RGB").save(out / "panel.png", dpi=(dpi, dpi))
        plt.close(fig)
    missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
    page = PdfReader(out / "panel.pdf").pages[0]
    page_mm = [float(page.mediabox.width) / 72 * 25.4, float(page.mediabox.height) / 72 * 25.4]
    assert np.allclose(page_mm, [width, height], atol=1e-5)
    fonts = []
    for reference in page["/Resources"]["/Font"].values():
        record = reference.get_object()
        descendants = record.get("/DescendantFonts", [record])
        for item in descendants:
            child = item.get_object()
            descriptor = child.get("/FontDescriptor", {}).get_object() if "/FontDescriptor" in child else {}
            fonts.append({"font": str(child.get("/BaseFont", "")), "embedded": any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3"))})
    assert fonts and all(f["embedded"] for f in fonts)
    svg = ET.parse(out / "panel.svg").getroot()
    svg_mm = [float(svg.attrib[key].removesuffix("pt")) / 72 * 25.4 for key in ("width", "height")]
    assert np.allclose(svg_mm, [width, height], atol=1e-5)
    svg_text_count = len(svg.findall(".//{http://www.w3.org/2000/svg}text"))
    assert svg_text_count > 0
    with Image.open(out / "panel.png") as png:
        assert list(png.size) == pixels
        png_dpi = list(png.info["dpi"])
    selected.to_csv(out / "plotting-data.csv", index=False)
    summary.to_csv(out / "summary-data.csv", index=False)
    selection = pd.concat([chosen[role] for role in ("sender", "receiver")], ignore_index=True)
    selection.to_csv(out / "selection.csv", index=False)
    cfg.update(actual_font=font, source_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(), genome_sha256=hashlib.sha256(genome_path.read_bytes()).hexdigest(), script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), selected_sender_ids=rows, selected_receiver_ids=cols, selected_ranks_one_based=(ranks + 1).tolist(), source_file=data_path.name, genome_file=genome_path.name, normalization_contract=normalization, actual_colorbar_ticks=ticks, selection=f"Rounded {count} equally spaced ranks from 0 to {n - 1}, after sorting means descending then strain ID.")
    write_json(out / "render-settings.json", cfg)
    qa = {"status": "pass" if not clipped and not missing else "needs_revision", "full_matrix_shape": list(full.shape), "full_input_measurements": int(full.size), "selected_shape": list(shown.shape), "selected_measurements": len(selected), "selected_values_equal_source": bool(np.array_equal(selected.gii_min.to_numpy(), full.loc[rows, cols].to_numpy().ravel())), "negative_input_measurements_retained": int((full.values < 0).sum()), "negative_selected_measurements_retained": int((shown.values < 0).sum()), "summary_denominator": n, "summary_means_recomputed_from_all_partners": bool(np.allclose(chosen["sender"].full_matrix_mean_gii_min, full.loc[rows].mean(axis=1)) and np.allclose(chosen["receiver"].full_matrix_mean_gii_min, full.loc[:, cols].mean(axis=0))), "genome_strips_match_strain_ids": True, "pdf_mm": page_mm, "png_pixels": pixels, "png_dpi": png_dpi, "font": font, "body_font_pt": cfg["font_size_pt"], "panel_title_rendered": False, "caption_file": "caption.md", "clipped_text": clipped, "missing_glyphs": missing, "inferential_statistics": "none", "visual_review_required": True}
    qa.update(pdf_fonts=fonts, svg_mm=svg_mm, svg_editable_text_elements=svg_text_count, valid_outputs=not clipped and not missing, color_normalization=normalization, colorbar_ticks=ticks, summary_count=len(summary), all_summary_means_recomputed_from_all_partners=bool(np.allclose(summary[summary.role == "sender"].set_index("strain").full_matrix_mean_gii_min.reindex(full.index), full.mean(axis=1)) and np.allclose(summary[summary.role == "receiver"].set_index("strain").full_matrix_mean_gii_min.reindex(full.columns), full.mean(axis=0))))
    write_json(out / "qa.json", qa)
    assert qa["status"] == "pass", qa
    print(json.dumps({"status": qa["status"], "output": str(out), "measurements_shown": len(selected)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--data", type=Path, default=HERE / "source-data.csv")
    parser.add_argument("--genome", type=Path, default=HERE / "genome-status.csv")
    parser.add_argument("--settings", type=Path, default=HERE / "settings.json")
    args = parser.parse_args()
    run(args.out, args.data, args.genome, args.settings)
