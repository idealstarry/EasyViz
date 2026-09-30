#!/usr/bin/env python3
"""Independent baseline panels; uses only the frozen CSVs and general Matplotlib.

Replay example:
  /Users/starry/Desktop/EasyViz/.venv/bin/python plot_figures.py \
    --panel both --stage final --output-root /path/to/new/output
The source directory can be changed with --input-dir. Initial exports are immutable.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(HERE / ".cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
import numpy as np
from PIL import Image
from pypdf import PdfReader

INPUT_DEFAULT = Path("/Users/starry/Desktop/EasyViz/evals/skill-value/inputs")
WIDTH_MM, HEIGHT_MM, DPI, FONT_PT = 90, 70, 300, 8
FONT_PATH = font_manager.findfont(font_manager.FontProperties(family="Arial"), fallback_to_default=False)
STYLE = {
    "font.family": "Arial", "font.size": FONT_PT,
    "axes.labelsize": FONT_PT, "xtick.labelsize": FONT_PT,
    "ytick.labelsize": FONT_PT, "legend.fontsize": FONT_PT,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "xtick.major.size": 2.5,
    "ytick.major.size": 2.5, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "savefig.facecolor": "white",
    "axes.unicode_minus": True, "text.color": "#202020",
    "axes.labelcolor": "#202020", "xtick.color": "#202020",
    "ytick.color": "#202020",
}
plt.rcParams.update(STYLE)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        out = csv.DictWriter(handle, fieldnames=list(rows[0]))
        out.writeheader()
        out.writerows(rows)

def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def source_record(input_dir, key):
    records = json.loads((input_dir / "provenance.json").read_text())
    record = next(row for row in records if row["id"] == key)
    source = input_dir / Path(record["derived_file"]).name
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != record["derived_sha256"]:
        raise ValueError(f"Source hash does not match: {source}")
    return source, record, digest

def style_axes(ax):
    ax.set_axisbelow(True)
    ax.grid(True, color="#dedede", linewidth=0.45, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(pad=2.5)

def export(fig, out_dir, name, settings, trace, caption):
    # Check visible text against the complete physical canvas, not a cropped box.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    limits = fig.bbox
    text_extents = []
    outside = []
    for artist in fig.findobj(matplotlib.text.Text):
        if not artist.get_visible() or not artist.get_text():
            continue
        box = artist.get_window_extent(renderer)
        item = {"text": artist.get_text(), "font_pt": artist.get_fontsize(),
                "bounds_px": list(box.bounds)}
        text_extents.append(item)
        if box.x0 < -0.5 or box.y0 < -0.5 or box.x1 > limits.x1 + 0.5 or box.y1 > limits.y1 + 0.5:
            outside.append(item)
    for fmt in ("png", "pdf", "svg"):
        fig.savefig(out_dir / f"{name}.{fmt}", format=fmt, dpi=DPI,
                    bbox_inches=None, pad_inches=0)
    # An exact 90 x 70 mm canvas has fractional pixels at 300 dpi.
    # Use nearest integer pixel dimensions and retain 300 dpi PNG metadata.
    target_px = (round(WIDTH_MM * DPI / 25.4), round(HEIGHT_MM * DPI / 25.4))
    png = out_dir / f"{name}.png"
    with Image.open(png) as image:
        original_px = image.size
        raster = image.copy()
    if raster.size != target_px:
        raster = raster.resize(target_px, Image.Resampling.LANCZOS)
    raster.save(png, dpi=(DPI, DPI))
    with Image.open(png) as image:
        png_size = image.size
        png_dpi = image.info.get("dpi")
    page = PdfReader(out_dir / f"{name}.pdf").pages[0]
    pdf_mm = [float(page.mediabox.width) * 25.4 / 72,
              float(page.mediabox.height) * 25.4 / 72]
    if any(abs(actual - expected) > 0.001 for actual, expected in zip(pdf_mm, [90, 70])):
        raise ValueError(f"Unexpected PDF dimensions: {pdf_mm}")
    settings.update({
        "canvas_mm": [WIDTH_MM, HEIGHT_MM], "png_dpi_requested": DPI,
        "png_size_px": png_size, "png_dpi_metadata": png_dpi,
        "png_raw_renderer_size_px": original_px,
        "raster_quantization": "Nearest integer pixels; LANCZOS adjustment of <1 pixel per dimension if required. Exact physical canvas in PDF and SVG.",
        "pdf_page_mm": pdf_mm, "font_requested": "Arial", "font_actual": "Arial",
        "font_file": FONT_PATH, "all_text_font_pt": FONT_PT,
        "matplotlib_version": matplotlib.__version__, "matplotlib_settings": STYLE,
        "tight_or_cropped_bbox": False,
        "text_beyond_canvas": outside, "visible_text_bounds": text_extents,
        "script_execution_utc": utc_now(),
    })
    write_json(out_dir / "settings.json", settings)
    write_csv(out_dir / "plotted-values.csv", trace)
    (out_dir / "caption.md").write_text(caption, encoding="utf-8")
    shutil.copyfile(Path(__file__), out_dir / "plot.py")
    # A size proof for inspecting the actual export at 96 screen pixels/inch.
    # It is an inspection derivative, not the delivered 300 dpi panel.
    proof = raster.resize((round(WIDTH_MM * 96 / 25.4), round(HEIGHT_MM * 96 / 25.4)), Image.Resampling.LANCZOS)
    proof.save(out_dir / "inspection-at-96dpi.png", dpi=(96, 96))
    plt.close(fig)
    return {"panel": name, "output": str(out_dir), "text_beyond_canvas": outside,
            "png_size_px": png_size, "pdf_page_mm": pdf_mm}

def co2(input_dir, out_dir):
    source, record, digest = source_record(input_dir, "noaa-co2")
    rows = read_csv(source)
    if len(rows) != 45 or [int(row["year"]) for row in rows] != list(range(1980, 2025)):
        raise ValueError("CO2 annual rows are incomplete, duplicated, or unsorted")
    years = np.array([int(row["year"]) for row in rows])
    means = np.array([float(row["mean_ppm"]) for row in rows])
    uncertainty = np.array([float(row["uncertainty_ppm"]) for row in rows])
    if not np.isfinite(means).all() or not np.isfinite(uncertainty).all() or (uncertainty < 0).any():
        raise ValueError("Invalid CO2 mean or uncertainty")
    delta = Decimal(rows[-1]["mean_ppm"]) - Decimal(rows[0]["mean_ppm"])
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), dpi=DPI)
    ax = fig.add_axes([0.18, 0.42, 0.78, 0.53])
    unc_ax = fig.add_axes([0.18, 0.16, 0.78, 0.16], sharex=ax)
    for current in (ax, unc_ax):
        style_axes(current)
        current.set_xlim(1979.5, 2024.5)
    ax.fill_between(years, means - uncertainty, means + uncertainty,
                    color="#287b9f", alpha=0.3, zorder=2, linewidth=0)
    ax.plot(years, means, color="#1d668c", linewidth=1.1, zorder=3)
    ax.errorbar(years, means, yerr=uncertainty, fmt="none", color="#1d668c",
                linewidth=0.5, capsize=1.0, capthick=0.5, zorder=4)
    ax.scatter(years[[0, -1]], means[[0, -1]], s=9, color="#1d668c", zorder=5)
    ax.set_ylim(331, 432)
    ax.set_yticks([340, 360, 380, 400, 420])
    ax.set_ylabel("CO₂ (ppm)", labelpad=5)
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    ax.annotate(rows[0]["mean_ppm"], (years[0], means[0]), xytext=(3, 6),
                textcoords="offset points", ha="left", va="bottom", fontsize=FONT_PT)
    ax.annotate(rows[-1]["mean_ppm"], (years[-1], means[-1]), xytext=(-3, 3),
                textcoords="offset points", ha="right", va="bottom", fontsize=FONT_PT)
    ax.text(1987, 404, f"Δ {delta} ppm", fontsize=FONT_PT, ha="left", va="center")
    unc_ax.plot(years, uncertainty, color="#1d668c", linewidth=0.9,
                marker="o", markersize=1.8, markeredgewidth=0, zorder=3)
    unc_ax.set_ylim(0.08, 0.16)
    unc_ax.set_yticks([0.08, 0.12, 0.16], labels=["0.08", "0.12", "0.16"])
    unc_ax.set_xticks([1980, 1990, 2000, 2010, 2024])
    unc_ax.set_ylabel("Unc. (ppm)", labelpad=5)
    unc_ax.set_xlabel("Year", labelpad=3)
    trace = []
    for row in rows:
        trace.append({**row,
                      "uncertainty_lower_ppm": str(Decimal(row["mean_ppm"]) - Decimal(row["uncertainty_ppm"])),
                      "uncertainty_upper_ppm": str(Decimal(row["mean_ppm"]) + Decimal(row["uncertainty_ppm"])),
                      "main_x_year": row["year"], "main_y_mean_ppm": row["mean_ppm"],
                      "lower_x_year": row["year"], "lower_y_uncertainty_ppm": row["uncertainty_ppm"]})
    settings = {"source_file": str(source), "source_sha256": digest, "source_provenance": record,
                "source_rows": len(rows), "plotted_rows": len(trace), "filtering": "None; all 45 frozen annual observations retained.",
                "transformations": ["Numeric parsing solely for plotting; original decimal strings preserved in trace.",
                                    "Exact Decimal mean minus/plus supplied uncertainty defines band bounds.",
                                    "No interpolation, fitted line, weighting, averaging, significance layer, or uncertainty recomputation."],
                "statistics": {"first_year": 1980, "last_year": 2024,
                               "first_mean_ppm": rows[0]["mean_ppm"], "last_mean_ppm": rows[-1]["mean_ppm"],
                               "overall_change_ppm": str(delta), "uncertainty_min_ppm": str(min(uncertainty)),
                               "uncertainty_max_ppm": str(max(uncertainty))},
                "axes": {"main_position": [0.18, 0.42, 0.78, 0.53], "uncertainty_position": [0.18, 0.16, 0.78, 0.16],
                         "x_scale": "linear", "main_y_scale": "linear", "uncertainty_y_scale": "linear",
                         "main_y_limits": [331, 432], "uncertainty_y_limits": [0.08, 0.16]},
                "uncertainty_meaning": "Standard deviation of differences between independent NOAA/ESRL and Scripps annual means; not a confidence interval or temporal spread.",
                "grid_zorder": 0, "data_zorder": [2, 3, 4, 5]}
    caption = f"""Annual mean atmospheric CO₂ in the NOAA Global Monitoring Laboratory Mauna Loa series, 1980–2024. The upper trace connects 45 calendar-year means of dry-air mole fraction (µmol mol⁻¹, expressed as ppm). CO₂ rose from {rows[0]['mean_ppm']} ppm in 1980 to {rows[-1]['mean_ppm']} ppm in 2024, an increase of {delta} ppm. The shaded envelope and capped vertical bars show mean ± NOAA's supplied uncertainty. This uncertainty is the standard deviation of differences between annual means independently determined by NOAA/ESRL and Scripps, not a confidence interval or within-year temporal variation. Its value is 0.12 ppm in every supplied year; the lower trace makes this small quantity readable independently of the full concentration range. The envelope and bars are correspondingly narrow on the upper axis. No annual means or uncertainty values were recomputed, and no model was fitted.

The supplied series includes Maunakea observations from December 2022 through 4 July 2023 while Mauna Loa observations were paused after 29 November 2022; observations at Mauna Loa resumed in July 2023. Thus the site series includes this temporary alternate location.

Data: NOAA Global Monitoring Laboratory, Boulder, Colorado, USA; Dr. Xin Lan, NOAA/GML, and Dr. Ralph Keeling, Scripps Institution of Oceanography, [Mauna Loa annual means](https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt), retrieved 30 September 2026. The frozen input and its SHA256 are identified in settings.json. Government source material is public domain; this figure is a third-party presentation and implies no NOAA endorsement.
"""
    return export(fig, out_dir, "noaa-co2", settings, trace, caption)

def earthquakes(input_dir, out_dir):
    source, record, digest = source_record(input_dir, "usgs-earthquakes")
    rows = read_csv(source)
    identifiers = [row["id"] for row in rows]
    if len(set(identifiers)) != len(rows):
        raise ValueError("Duplicated earthquake identifiers")
    for row in rows:
        time = datetime.fromisoformat(row["time"].replace("Z", "+00:00"))
        if not (datetime(2024, 1, 1, tzinfo=timezone.utc) <= time < datetime(2024, 2, 1, tzinfo=timezone.utc)):
            raise ValueError("Event outside the supplied January sample")
        if any(row[key] != "us" for key in ["net", "locationSource", "magSource"]) or row["status"] != "reviewed":
            raise ValueError("Unexpected preferred source or review status")
        if not math.isfinite(float(row["depth"])) or float(row["depth"]) <= 0 or not math.isfinite(float(row["mag"])):
            raise ValueError("Invalid depth or magnitude for logarithmic depth display")
        if float(row["mag"]) < 5:
            raise ValueError("Magnitude below the supplied query threshold")
    counts = Counter(row["magType"] for row in rows)
    encodings = {"mb": {"marker": "o", "color": "#166b9a"},
                 "mww": {"marker": "^", "color": "#c97421"},
                 "mwb": {"marker": "s", "color": "#208360"},
                 "mwr": {"marker": "D", "color": "#8251a3"}}
    if set(counts) != set(encodings):
        raise ValueError("Unexpected magnitude type; encoding must be explicit")
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), dpi=DPI)
    ax = fig.add_axes([0.18, 0.20, 0.78, 0.66])
    style_axes(ax)
    ax.set_xscale("log")
    ax.set_xlim(3, 700)
    ax.set_ylim(4.85, 7.7)
    ax.xaxis.set_major_locator(FixedLocator([5, 10, 30, 100, 300, 600]))
    ax.xaxis.set_major_formatter(FixedFormatter(["5", "10", "30", "100", "300", "600"]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_yticks([5, 5.5, 6, 6.5, 7, 7.5], labels=["5.0", "5.5", "6.0", "6.5", "7.0", "7.5"])
    ax.set_xlabel("Hypocentral depth (km; log scale)", labelpad=4)
    ax.set_ylabel("Catalog magnitude", labelpad=5)
    handles = {}
    for zorder, key in enumerate(["mww", "mb", "mwb", "mwr"], start=3):
        current = [row for row in rows if row["magType"] == key]
        encoding = encodings[key]
        handles[key] = ax.scatter([float(row["depth"]) for row in current],
                                  [float(row["mag"]) for row in current],
                                  s=15, marker=encoding["marker"], facecolors="none",
                                  edgecolors=encoding["color"], linewidths=0.65, alpha=0.75,
                                  label=key, zorder=zorder)
    fig.legend([handles[key] for key in encodings], list(encodings),
               loc="upper center", bbox_to_anchor=(0.56, 0.985), ncol=4,
               frameon=False, columnspacing=0.9, handletextpad=0.35,
               handlelength=1.0, borderaxespad=0.0, markerscale=1)
    trace = []
    for row in rows:
        encoding = encodings[row["magType"]]
        trace.append({**row, "plotted_x_depth_km": row["depth"], "plotted_y_catalog_mag": row["mag"],
                      "x_log10_depth": format(math.log10(float(row["depth"])), ".17g"),
                      "marker": encoding["marker"], "color_hex": encoding["color"]})
    coincidence = Counter((row["depth"], row["mag"]) for row in rows)
    exact_groups = [{"depth": key[0], "mag": key[1], "event_count": count} for key, count in coincidence.items() if count > 1]
    stats = {"events": len(rows), "magnitude_type_counts": dict(counts),
             "depth_min_km": min(rows, key=lambda row: float(row["depth"]))["depth"],
             "depth_max_km": max(rows, key=lambda row: float(row["depth"]))["depth"],
             "magnitude_min": min(rows, key=lambda row: float(row["mag"]))["mag"],
             "magnitude_max": max(rows, key=lambda row: float(row["mag"]))["mag"],
             "exact_coincident_xy_groups": exact_groups,
             "events_in_coincident_xy_groups": sum(group["event_count"] for group in exact_groups)}
    settings = {"source_file": str(source), "source_sha256": digest, "source_provenance": record,
                "source_rows": len(rows), "plotted_rows": len(trace),
                "filtering": "None; January UTC, reviewed status, magnitude >=5 and preferred USGS sources are validated, not reapplied to omit rows.",
                "transformations": ["Numeric parsing for plotting; original decimal strings and identifiers preserved in trace.",
                                    "Logarithmic display of positive preferred hypocentral depth; no change to depth values.",
                                    "Magnitude type mapped to both shape and color.",
                                    "No jitter, subsampling, rounding, weighting, aggregation, regression, or significance layer."],
                "statistics": stats, "encodings": encodings,
                "axes": {"position": [0.18, 0.20, 0.78, 0.66], "x_scale": "log", "y_scale": "linear",
                         "x_limits": [3, 700], "y_limits": [4.85, 7.7]},
                "mark_area_pt2": 15, "mark_linewidth_pt": 0.65, "mark_opacity": 0.75,
                "grid_zorder": 0, "data_zorder": [3, 4, 5, 6],
                "event_uncertainty": "Unavailable in the supplied minimal input; no event error bars drawn."}
    caption = f"""Preferred hypocentral depth and catalog magnitude of {len(rows)} reviewed USGS earthquake events in the supplied global January 2024 ComCat sample. Each plotted mark represents one catalog event; depth is in kilometres on a logarithmic horizontal axis and magnitude is the preferred catalog value. Shape and colour identify the catalog magnitude type: mb (body-wave magnitude, {counts['mb']} events), mww (moment magnitude from W-phase inversion, {counts['mww']}), mwb (moment magnitude from body-wave inversion, {counts['mwb']}), and mwr (moment magnitude from regional moment-tensor inversion, {counts['mwr']}). These measurement types are retained separately; their values do not constitute uniformly measured energy or intensity. Depth ranges from {stats['depth_min_km']} to {stats['depth_max_km']} km and magnitude from {stats['magnitude_min']} to {stats['magnitude_max']}. Equal depths and magnitudes can overlap; all events are plotted at their catalog coordinates without jitter or aggregation, so visible mark counts need not equal event counts. No uncertainty fields were supplied for these events, and no error bars, fitted relationships or significance tests are shown.

The source query spans 1 January 2024 00:00:00 UTC inclusive to 1 February 2024 00:00:00 UTC exclusive, with global scope, minimum magnitude 5, earthquake event type and contributor us. The frozen table additionally requires preferred network, location source and magnitude source all equal to us; two nonmatching preferred-source rows were excluded during creation of the common input. All 131 supplied rows are retained here. This is a defined catalog sample, not all earthquakes, and supports no claim of catalog completeness or absence of events outside the query.

Data: U.S. Geological Survey, Department of the Interior/USGS, [ComCat/FDSN earthquake catalog](https://earthquake.usgs.gov/fdsnws/event/1/), retrieved 30 September 2026. The exact query, frozen-file SHA256 and retrieval provenance are recorded in settings.json. USGS-produced source material is public domain; this figure is a third-party presentation and implies no USGS endorsement.
"""
    return export(fig, out_dir, "usgs-earthquakes", settings, trace, caption)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT_DEFAULT)
    parser.add_argument("--output-root", type=Path, default=HERE)
    parser.add_argument("--stage", choices=["initial", "final"], required=True)
    parser.add_argument("--panel", choices=["noaa-co2", "usgs-earthquakes", "both"], default="both")
    args = parser.parse_args()
    started = utc_now()
    panels = ["noaa-co2", "usgs-earthquakes"] if args.panel == "both" else [args.panel]
    reports = []
    for panel in panels:
        destination = args.output_root / panel / args.stage
        if args.stage == "initial" and destination.exists() and any(destination.iterdir()):
            raise FileExistsError(f"First complete render already preserved: {destination}")
        destination.mkdir(parents=True, exist_ok=True)
        reports.append((co2 if panel == "noaa-co2" else earthquakes)(args.input_dir, destination))
    execution = {"start_utc": started, "end_utc": utc_now(), "stage": args.stage,
                 "panel_reports": reports, "python_executable": __import__("sys").executable,
                 "source_files_read": [str(args.input_dir / "provenance.json")] + [str(args.input_dir / ("noaa-co2-1980-2024.csv" if panel == "noaa-co2" else "usgs-earthquakes-2024-01.csv")) for panel in panels]}
    write_json(args.output_root / f"render-{args.stage}-log.json", execution)
    print(json.dumps(execution, indent=2))

if __name__ == "__main__":
    main()
