#!/usr/bin/env python3
"""Render supplied cohort effects and asymmetric CIs without statistical recomputation.

Requires Python 3.11+, Matplotlib, NumPy, Pillow, and pypdf. Field names, cohort
count/order/colors, layout, and categories come from the input settings and CSV.
Fail explicitly on unsupported/malformed data or capacity; never drop intervals.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-transfer-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text
import numpy as np
from PIL import Image
from pypdf import PdfReader
from legend_layout import LegendLayout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_inputs(data: Path, cfg: dict) -> tuple[list[dict], list[dict], list[str]]:
    fields = cfg["fields"]
    roles = ("term_id", "term", "domain", "cohort", "estimate", "ci_lower", "ci_upper", "n", "row_order")
    require(all(role in fields for role in roles), "Every required field role must be mapped.")
    require(len(set(fields.values())) == len(fields), "Field mappings must be distinct.")
    with data.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames is not None and set(fields.values()) <= set(reader.fieldnames), "Missing mapped CSV fields.")
        raw = list(reader)
    require(bool(raw), "The input table is empty.")
    rows, seen = [], set()
    for index, original in enumerate(raw, 2):
        row = {role: original[fields[role]] for role in roles}
        require(all(value is not None and str(value).strip() for value in row.values()), f"Missing field at CSV line {index}.")
        for role in ("estimate", "ci_lower", "ci_upper", "n", "row_order"):
            try:
                row[role] = float(row[role])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Nonnumeric {role} at CSV line {index}.") from exc
            require(math.isfinite(row[role]), f"Nonfinite {role} at CSV line {index}.")
        require(row["n"] > 0 and row["n"].is_integer(), f"n must be a positive integer at line {index}.")
        row["n"] = int(row["n"])
        require(row["ci_lower"] <= row["estimate"] <= row["ci_upper"], f"Interval must bracket estimate at line {index}.")
        key = (row["term_id"], row["cohort"])
        require(key not in seen, f"Duplicate term/cohort pair: {key}.")
        seen.add(key)
        row["source_line"] = index
        rows.append(row)
    cohorts = cfg["cohort_order"]
    require(len(cohorts) >= 1 and len(set(cohorts)) == len(cohorts), "Cohort order must be a nonempty unique list.")
    require(set(cohorts) == {row["cohort"] for row in rows}, "Cohort order must match observed cohorts exactly.")
    require(set(cohorts) <= set(cfg["colors"]), "Every cohort needs an explicit color; colors never cycle.")
    terms_by_id = {}
    for row in rows:
        descriptor = {key: row[key] for key in ("term_id", "term", "domain", "row_order")}
        require(row["term_id"] not in terms_by_id or terms_by_id[row["term_id"]] == descriptor,
                f"Conflicting term metadata: {row['term_id']}.")
        terms_by_id[row["term_id"]] = descriptor
    terms = sorted(terms_by_id.values(), key=lambda row: row["row_order"])
    require(len({term["row_order"] for term in terms}) == len(terms), "Different terms must have distinct row_order values.")
    for term in terms:
        require({row["cohort"] for row in rows if row["term_id"] == term["term_id"]} == set(cohorts),
                f"Incomplete cohort coverage for {term['term_id']}.")
    # A domain may occupy one contiguous block only. Reordering it would change source order.
    blocks = [term["domain"] for i, term in enumerate(terms) if i == 0 or term["domain"] != terms[i - 1]["domain"]]
    require(len(blocks) == len(set(blocks)), "Domain groups must be contiguous in row_order; no silent reordering is allowed.")
    return rows, terms, cohorts


def font_record(requested: str, fallback: str) -> dict:
    try:
        filename = font_manager.findfont(requested, fallback_to_default=False)
        substituted = False
    except ValueError:
        filename = font_manager.findfont(fallback, fallback_to_default=False)
        substituted = True
    return {"requested": requested, "actual_family": font_manager.FontProperties(fname=filename).get_name(),
            "font_file": filename, "fallback_used": substituted}


def render(data: Path, settings: Path, out: Path) -> None:
    cfg = json.loads(settings.read_text())
    rows, terms, cohorts = read_inputs(data, cfg)
    layout, marks = cfg["layout"], cfg["marks"]
    require(set(cfg["formats"]) == {"pdf", "svg", "png"}, "This implementation exports the reviewable PDF/SVG/PNG set.")
    for name in ("width_mm", "height_mm", "font_size_pt", "dpi"):
        require(layout[name] > 0, f"layout.{name} must be positive.")
    for role in ("axis", "tick", "legend", "domain"):
        require(cfg["typography"][role] == layout["font_size_pt"], "This panel uses one agreed text size for every text role.")
    require(marks["point_edgecolor"] == "none" and marks["point_linewidth_pt"] == 0, "Filled points must be explicitly borderless.")
    font = font_record(layout["font"], layout["fallback_font"])
    plt.rcParams.update({
        "font.family": font["actual_family"], "font.size": layout["font_size_pt"],
        "axes.labelsize": cfg["typography"]["axis"], "xtick.labelsize": cfg["typography"]["tick"],
        "ytick.labelsize": cfg["typography"]["tick"], "legend.fontsize": cfg["typography"]["legend"],
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "axes.unicode_minus": True, "figure.facecolor": "white", "savefig.facecolor": "white",
        "text.color": marks.get("text_color", "black"),
        "axes.labelcolor": marks.get("text_color", "black"),
        "xtick.color": marks.get("text_color", "black"),
        "ytick.color": marks.get("text_color", "black"),
    })
    cursor, last_domain, headers, term_y = 0.0, None, [], {}
    for term in terms:
        if term["domain"] != last_domain:
            if last_domain is not None:
                cursor += layout["last_row_to_header"] - layout["row_step"]
            headers.append((term["domain"], cursor))
            cursor += layout["header_to_first_row"]
            last_domain = term["domain"]
        term_y[term["term_id"]] = cursor
        cursor += layout["row_step"]
    offsets = np.linspace(-layout["cohort_span"] / 2, layout["cohort_span"] / 2, len(cohorts)) if len(cohorts) > 1 else np.array([0.0])
    cohort_offset = dict(zip(cohorts, offsets))
    fig = plt.figure(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    ax = fig.add_axes(layout["axes_bounds"])
    xmin = min(row["ci_lower"] for row in rows)
    xmax = max(row["ci_upper"] for row in rows)
    xlimits = cfg.get("x_limits")
    if xlimits is None:
        span = max(xmax, 0) - min(xmin, 0)
        xlimits = [min(xmin, 0) - max(span * .06, .05), max(xmax, 0) + max(span * .06, .05)]
    require(len(xlimits) == 2 and xlimits[0] < 0 < xlimits[1], "The x range must contain zero.")
    require(xlimits[0] < xmin and xlimits[1] > xmax, "Axis limits would clip supplied confidence intervals.")
    ax.set_xlim(xlimits)
    ax.set_ylim(cursor - .3, -.45)
    if cfg.get("x_ticks") is not None:
        require(all(xlimits[0] <= x <= xlimits[1] for x in cfg["x_ticks"]), "An x tick lies outside the x range.")
        ax.set_xticks(cfg["x_ticks"])
    else:
        # Auto locators may propose a label beyond the view; retain only in-range ticks.
        ax.set_xticks([value for value in ax.xaxis.get_major_locator().tick_values(*xlimits)
                      if xlimits[0] <= value <= xlimits[1]])
    ax.set_yticks([term_y[term["term_id"]] for term in terms], [term["term"] for term in terms])
    ax.tick_params(axis="y", length=0, pad=8)
    ax.tick_params(axis="x", width=marks["axis_linewidth_pt"], length=3, pad=4)
    ax.set_xlabel(cfg["labels"]["x"], labelpad=6)
    ax.set_axisbelow(True)
    if marks.get("grid", True):
        ax.grid(axis="x", color=marks.get("grid_color", "#E5E5E5"), linewidth=marks["grid_linewidth_pt"], zorder=0)
    ax.axvline(0, color=marks.get("zero_color", "#666666"),
               linewidth=marks["zero_linewidth_pt"], linestyle=marks.get("zero_linestyle", "-"), zorder=1)
    for side in ("top", "left", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_linewidth(marks["axis_linewidth_pt"])
    ax.spines["bottom"].set_color(marks.get("axis_color", "#444444"))
    domain_texts = []
    for domain, y in headers:
        figure_y = fig.transFigure.inverted().transform(ax.transData.transform((0, y)))[1]
        domain_texts.append(fig.text(layout["domain_label_x_fraction"], figure_y, domain,
                                     ha="left", va="center", fontweight=marks.get("domain_fontweight", "bold"),
                                     color=marks.get("domain_color", "black"), fontsize=cfg["typography"]["domain"]))
    plotted, point_artists, interval_artists = [], {}, {}
    rows_by_key = {(row["term_id"], row["cohort"]): row for row in rows}
    for cohort in cohorts:
        selected = [rows_by_key[(term["term_id"], cohort)] for term in terms]
        y = np.array([term_y[row["term_id"]] + cohort_offset[cohort] for row in selected])
        lo = np.array([row["ci_lower"] for row in selected])
        hi = np.array([row["ci_upper"] for row in selected])
        x = np.array([row["estimate"] for row in selected])
        # Draw endpoints directly; no inferred SE, symmetric xerr, weighting, or fit.
        interval_artists[cohort] = ax.hlines(y, lo, hi, colors=cfg["colors"][cohort], linewidth=marks["interval_linewidth_pt"], zorder=2)
        if marks["interval_cap_height"] > 0:
            for endpoint in (lo, hi):
                ax.vlines(endpoint, y - marks["interval_cap_height"] / 2, y + marks["interval_cap_height"] / 2,
                          colors=cfg["colors"][cohort], linewidth=marks["interval_linewidth_pt"], zorder=2)
        point_artists[cohort] = ax.scatter(x, y, s=marks["point_area_pt2"], marker="o", c=cfg["colors"][cohort],
                                         edgecolors="none", linewidths=0, zorder=3)
        for row, value in zip(selected, y):
            plotted.append({**row, "plot_y": float(value), "color": cfg["colors"][cohort]})
    legend_labels, participant_counts = [], {}
    for cohort in cohorts:
        ns = sorted({row["n"] for row in rows if row["cohort"] == cohort})
        participant_counts[cohort] = ns
        label = f"{cohort} (n = {ns[0]})" if len(ns) == 1 else cohort
        legend_labels.append(label)
    key_mm = math.sqrt(marks["point_area_pt2"]) * 25.4 / 72
    supplied_legend = cfg.get("categorical_legend", {})
    require(isinstance(supplied_legend, dict), "categorical_legend must be an object.")
    require(not set(supplied_legend) - {"ncol", "key_width_mm", "key_height_mm", "handletext_gap_mm", "column_gap_mm", "row_gap_mm", "borderpad_mm"},
            "Unsupported categorical_legend option; placement follows the configured top-right canvas anchor.")
    legend_options = {
        "position": "manual", "anchor_mm": [.98 * layout["width_mm"], layout["legend_y_fraction"] * layout["height_mm"]],
        "loc": "upper right", "ncol": len(cohorts), "key_width_mm": key_mm, "key_height_mm": key_mm,
        "handletext_gap_mm": .7, "column_gap_mm": 2.0, **supplied_legend,
    }
    legends = LegendLayout(fig, ax, typography={"legend": cfg["typography"]["legend"]},
                           config={"categorical": legend_options})
    legends.add_categorical(legend_labels, [cfg["colors"][cohort] for cohort in cohorts],
                            shape="marker", edgecolor="none", linewidth_pt=0)
    legend_report = legends.layout()
    if legend_report["status"] != "pass":
        out.mkdir(parents=True, exist_ok=True)
        (out / "numeric-qa.json").write_text(json.dumps({"status": "needs_revision", "legend_layout": legend_report}, indent=2) + "\n")
    require(legend_report["status"] == "pass", f"Legend does not fit the fixed canvas: {legend_report['issues']}; inspect numeric-qa.json.")
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text_artists = [artist for artist in fig.findobj(Text) if artist.get_visible() and artist.get_text()]
    text_boxes = [(artist, artist.get_window_extent(renderer)) for artist in text_artists]
    escaped = [artist.get_text() for artist, box in text_boxes if box.x0 < -.5 or box.y0 < -.5 or box.x1 > fig.bbox.width + .5 or box.y1 > fig.bbox.height + .5]
    require(not escaped, f"Text leaves fixed canvas: {escaped}; adjust margins or canvas explicitly.")
    overlaps = []
    for i, (first, a) in enumerate(text_boxes):
        for second, b in text_boxes[i + 1:]:
            if a.overlaps(b):
                overlaps.append([first.get_text(), second.get_text()])
    require(not overlaps, f"Text overlaps at final size: {overlaps}; adjust layout without shrinking type.")
    point_diameter_pt = math.sqrt(marks["point_area_pt2"])
    min_separation_pt = None
    if len(cohorts) > 1:
        values = sorted(float(value) for value in offsets)
        min_delta = min(b - a for a, b in zip(values, values[1:]))
        min_separation_pt = abs(ax.transData.transform((0, min_delta))[1] - ax.transData.transform((0, 0))[1]) * 72 / layout["dpi"]
        require(min_separation_pt >= point_diameter_pt + .5,
                "Too many rows/cohorts for separate dots at this fixed canvas; increase height or adjust spacing explicitly.")
    mapping_errors = []
    for cohort in cohorts:
        expected = [rows_by_key[(term["term_id"], cohort)] for term in terms]
        actual_points = np.asarray(point_artists[cohort].get_offsets())
        actual_segments = interval_artists[cohort].get_segments()
        for row, actual, segment in zip(expected, actual_points, actual_segments):
            expected_y = term_y[row["term_id"]] + cohort_offset[cohort]
            if not np.array_equal(actual, [row["estimate"], expected_y]) or not np.array_equal(segment, [[row["ci_lower"], expected_y], [row["ci_upper"], expected_y]]):
                mapping_errors.append([row["term_id"], cohort])
    require(not mapping_errors, f"Source-to-artist numerical mismatch: {mapping_errors}")
    out.mkdir(parents=True, exist_ok=True)
    source_copy = out / "source.csv"
    if data.resolve() != source_copy.resolve():
        shutil.copyfile(data, source_copy)
    with (out / "plotting-data.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(plotted[0]))
        writer.writeheader()
        writer.writerows(plotted)
    for fmt in cfg["formats"]:
        # Never tight-crop: the canvas includes all margins, labels, and legend.
        fig.savefig(out / f"panel.{fmt}", format=fmt, dpi=layout["dpi"])
    png = Image.open(out / "panel.png")
    expected_px = [round(layout["width_mm"] / 25.4 * layout["dpi"]), round(layout["height_mm"] / 25.4 * layout["dpi"])]
    actual_px = list(png.size)
    pdf = PdfReader(out / "panel.pdf")
    pdf_mm = [float(pdf.pages[0].mediabox.width) * 25.4 / 72, float(pdf.pages[0].mediabox.height) * 25.4 / 72]
    fonts = []
    for obj in pdf.pages[0]["/Resources"]["/Font"].values():
        entry = obj.get_object()
        descendant = entry["/DescendantFonts"][0].get_object() if "/DescendantFonts" in entry else entry
        descriptor = descendant.get("/FontDescriptor")
        descriptor = descriptor.get_object() if descriptor is not None else {}
        fonts.append({"base_font": str(entry.get("/BaseFont")), "subtype": str(entry.get("/Subtype")),
                      "embedded": any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3"))})
    svg = ET.parse(out / "panel.svg").getroot()
    svg_mm = [float(svg.attrib[dimension].removesuffix("pt")) * 25.4 / 72 for dimension in ("width", "height")]
    svg_text = [element.text for element in svg.iter("{http://www.w3.org/2000/svg}text")]
    dimensions_pass = all(abs(a - b) <= .001 for pair in (pdf_mm, svg_mm) for a, b in zip(pair, [layout["width_mm"], layout["height_mm"]]))
    raster_pass = all(abs(a - b) <= 1 for a, b in zip(expected_px, actual_px))
    require(dimensions_pass and raster_pass, "Export dimensions do not match the fixed canvas.")
    require(all(item["embedded"] for item in fonts), "PDF font embedding was not verified.")
    actual = {**cfg, "source": {"input_path": str(data.resolve()), "saved_copy": "source.csv", "sha256": sha256(data)},
              "font_resolution": font, "actual_x_limits": list(ax.get_xlim()),
              "actual_term_order": [term["term_id"] for term in terms],
              "actual_domain_order": [domain for domain, _ in headers],
              "cohort_offsets": {key: float(value) for key, value in cohort_offset.items()},
              "participant_counts_by_cohort": participant_counts,
              "legend_layout": legend_report,
              "legend_helper": {"file": "legend_layout.py", "sha256": sha256(Path(__file__).with_name("legend_layout.py"))},
              "transformations": ["Sort unique terms by supplied row_order", "Insert domain-heading spacing", "Offset cohort y positions within each term"],
              "statistics_recomputed": False, "values_transformed": False,
              "software": {"python": sys.version.split()[0], "matplotlib": matplotlib.__version__, "numpy": np.__version__},
              "svg_font_note": "SVG preserves editable text and names Arial; viewing on another system requires that font or a compatible substitute. PDF embeds its fonts."}
    (out / "actual-settings.json").write_text(json.dumps(actual, indent=2) + "\n")
    qa = {
        "status": "passed", "scope": "This CSV and settings only; numeric/export QA is not a visual review",
        "source_sha256": sha256(data), "source_rows": len(rows), "displayed_points": len(plotted),
        "displayed_intervals": sum(len(artist.get_segments()) for artist in interval_artists.values()),
        "terms": len(terms), "cohorts": len(cohorts), "domains": len(headers),
        "source_to_artist_endpoint_checks": "passed", "source_to_artist_mismatches": mapping_errors,
        "asymmetric_intervals_preserved": sum(not math.isclose(row["estimate"] - row["ci_lower"], row["ci_upper"] - row["estimate"], abs_tol=1e-12) for row in rows),
        "term_order": [term["term_id"] for term in terms], "supplied_statistics_recomputed": False,
        "font": font, "text_sizes_pt": sorted({artist.get_fontsize() for artist in text_artists}),
        "text_outside_canvas": escaped, "text_overlap_pairs": overlaps,
        "minimum_within_term_point_center_separation_pt": min_separation_pt,
        "point_diameter_pt": point_diameter_pt,
        "legend_layout": legend_report,
        "pdf": {"page_count": len(pdf.pages), "dimensions_mm": pdf_mm, "fonts": fonts},
        "svg": {"dimensions_mm": svg_mm, "text_node_count": len(svg_text), "editable_text": bool(svg_text)},
        "png": {"pixels": actual_px, "expected_rounded_pixels": expected_px, "dpi_metadata": list(png.info.get("dpi", [])), "allowed_pixel_rounding_error": 1},
        "visual_review": "Not checked by the renderer; consult separately saved review evidence"
    }
    (out / "numeric-qa.json").write_text(json.dumps(qa, indent=2) + "\n")
    plt.close(fig)
    print(json.dumps({"out": str(out.resolve()), "points": len(plotted), "intervals": qa["displayed_intervals"], "numeric_qa": "passed", "font": font["actual_family"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    case_dir = Path(__file__).resolve().parent
    parser.add_argument("--data", type=Path, default=case_dir / "source.csv")
    parser.add_argument("--settings", type=Path, default=case_dir / "figure-settings.json")
    parser.add_argument("--out", type=Path, default=case_dir)
    args = parser.parse_args()
    render(args.data, args.settings, args.out)


if __name__ == "__main__":
    main()
