#!/usr/bin/env python3
"""Two source-bound Ccl2 time panels, with trajectories, SEM and all mice.

Each time is a terminal cross-sectional group. Lines join group means only.
Raw x offsets are a bounded visibility treatment, never sampling times.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
from statistics import mean, stdev
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
import numpy as np
import pymupdf

HERE = Path(__file__).resolve().parent
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def captured_csv(path):
    captured = Path(path).read_bytes()
    rows = list(csv.DictReader(io.StringIO(captured.decode("utf-8"), newline="")))
    if not rows or any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("A nonempty rectangular source CSV is required")
    return rows, captured


def runtime_path(explicit=None):
    if explicit:
        path = Path(explicit).resolve()
        if not (path / "figure_elements.py").is_file():
            raise FileNotFoundError("Pass the EasyViz scripts folder, with sibling helpers intact")
        return path
    for parent in HERE.parents:
        for relative in ("scripts", "skills/easyviz/scripts"):
            path = parent / relative
            if (path / "figure_elements.py").is_file():
                return path
    raise FileNotFoundError("Supply --tools /path/to/easyviz/scripts")


def mapping_runtime(tools):
    loader = importlib.util.spec_from_file_location("ccl2_figure_elements", tools / "figure_elements.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def source_continuity(bindings):
    differences = []
    for role, binding in bindings.items():
        path = Path(binding["path"])
        actual = digest_bytes(path.read_bytes()) if path.is_file() else None
        if actual != binding["sha256"]:
            differences.append({"role": role, "path": str(path), "expected": binding["sha256"], "actual": actual})
    return {"status": "pass" if not differences else "needs_revision", "differences": differences}


def groups(rows):
    result = {}
    for row in rows:
        key = (row["compartment"], row["condition"], int(row["hour"]))
        result.setdefault(key, []).append(row)
    return result


def summary(rows):
    result = []
    for (compartment, condition, hour), cell in groups(rows).items():
        values = [float(row["ccl2"]) for row in cell]
        result.append({"compartment": compartment, "condition": condition, "hour": hour,
                       "n": len(values), "mean": mean(values), "sem": stdev(values) / math.sqrt(len(values)),
                       "source_cells": [row["source_cell"] for row in cell]})
    return result


def raw_positions(ax, cell, condition, spec):
    """Pack in physical x; the source concentration remains unchanged.

    Genotype slots are left/right of the true time. Avoid glyph intersections
    within a slot and retain a central corridor for the mean/SEM glyphs.
    """
    options = spec["options"]
    diameter = options["raw_marker_pt"] * 25.4 / 72
    stroke = options["raw_edge_pt"] * 25.4 / 72
    diameter += stroke
    clearance = options["raw_gap_pt"] * 25.4 / 72
    step = diameter + clearance
    sign = -1 if condition == "Control" else 1
    center = sign * options["raw_slot_mm"]
    inner = options["raw_min_offset_mm"]
    available = int(math.floor((options["raw_max_offset_mm"] - inner) / step + 1e-9)) + 1
    candidates = [sign * (inner + index * step) for index in range(available)]
    candidates.sort(key=lambda offset: abs(offset - center))
    limit = options["raw_max_offset_mm"]
    candidates = [offset for offset in candidates if abs(offset) <= limit
                  and abs(offset) >= options["raw_min_offset_mm"]]
    retained = []
    # Source-cell tie breaking is deterministic, not a biological mouse ID.
    for row in sorted(cell, key=lambda row: (float(row["ccl2"]), row["source_cell"])):
        nominal = np.asarray(ax.transData.transform((float(row["hour"]), float(row["ccl2"]))), dtype=float)
        chosen = None
        for offset in candidates:
            proposed = nominal + np.array([offset / 25.4 * ax.figure.dpi, 0])
            separation = [(proposed - actual[1]) * 25.4 / ax.figure.dpi for actual in retained]
            if all((np.max(np.abs(delta)) if options["markers"][condition] == "s" else np.linalg.norm(delta))
                   >= step - 1e-9 for delta in separation):
                chosen = (offset, proposed)
                break
        if chosen is None:
            raise ValueError(f"Raw slot is too crowded for {row['compartment']} {condition} {row['hour']} h")
        retained.append((row, chosen[1]))
    return [(row, ax.transData.inverted().transform(display)) for row, display in retained]


def draw(rows, spec, mapper):
    layout, options = spec["layout"], spec["options"]
    font = font_manager.findfont(font_manager.FontProperties(family=layout["font"]), fallback_to_default=False)
    resolved_name = font_manager.FontProperties(fname=font).get_name()
    rc = {"font.family": layout["font"], "font.size": layout["font_size_pt"],
          "axes.labelsize": layout["font_size_pt"], "xtick.labelsize": layout["font_size_pt"],
          "ytick.labelsize": layout["font_size_pt"], "legend.fontsize": layout["font_size_pt"],
          "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
          "svg.hashsalt": "easyviz-compartment-ccl2",
          "axes.linewidth": options["axis_line_pt"], "savefig.facecolor": "white"}
    with plt.rc_context(rc):
        fig = plt.figure(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
        ax = fig.add_axes(layout["axes_fraction"])
        ax.set_xlim(options["x_limits"])
        ax.set_ylim(options["y_limits"])
        ax.set_xticks(spec["order"]["hour"])
        ax.set_yticks(options["y_ticks"])
        ax.set_xlabel(spec["labels"]["x"], labelpad=3)
        ax.set_ylabel(spec["labels"]["y"], labelpad=4)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#2A2A2A")
        ax.tick_params(direction="out", length=2.6, width=options["axis_line_pt"], pad=3, colors="#222222")
        fig.canvas.draw()
        cells = groups(rows)
        summaries = summary(rows)
        source_artists = []
        summary_artists = []
        for condition in spec["order"]["condition"]:
            color = spec["colors"][condition]
            marker = options["markers"][condition]
            selected = [item for item in summaries if item["condition"] == condition]
            selected.sort(key=lambda item: item["hour"])
            # Exact linear source hours anchor the means and SEM.
            line, = ax.plot([item["hour"] for item in selected], [item["mean"] for item in selected],
                            color=color, linewidth=options["mean_line_pt"], zorder=2,
                            solid_joinstyle="round", solid_capstyle="round")
            mapper.register(fig, line, "mean-trajectory", f"{condition} · group mean trajectory",
                            key=[spec["compartment"], condition],
                            source_keys=[{"source_sheet": "3c", "source_cells": item["source_cells"],
                                          "hour": item["hour"], "summary": "mean"} for item in selected],
                            spec_paths=[mapper.pointer("colors", condition), mapper.pointer("options", "mean_line_pt")],
                            editable=["color", "linewidth"])
            for item in selected:
                interval, = ax.plot([item["hour"], item["hour"]], [item["mean"] - item["sem"], item["mean"] + item["sem"]],
                                    color=color, linewidth=options["sem_line_pt"], zorder=3, solid_capstyle="butt")
                point, = ax.plot([item["hour"]], [item["mean"]], marker=marker,
                                 markersize=options["mean_marker_pt"], linestyle="none", color=color,
                                 markeredgewidth=options["mean_edge_pt"], markeredgecolor="white", zorder=4)
                key = [spec["compartment"], condition, item["hour"]]
                trace = [{"source_sheet": "3c", "source_cells": item["source_cells"],
                          "hour": item["hour"], "condition": condition}]
                mapper.register(fig, interval, "sem-interval", f"{condition} · {item['hour']} h · SEM",
                                key=key, source_keys=trace, spec_paths=[mapper.pointer("options", "sem_line_pt")], editable=["linewidth"])
                mapper.register(fig, point, "mean-marker", f"{condition} · {item['hour']} h · mean",
                                key=key, source_keys=trace, spec_paths=[mapper.pointer("options", "mean_marker_pt")], editable=["markersize"])
                summary_artists.append({**item, "mean_artist": point, "sem_artist": interval, "trajectory": line})
                for raw, position in raw_positions(ax, cells[(spec["compartment"], condition, item["hour"])], condition, spec):
                    artist, = ax.plot([position[0]], [position[1]], marker=marker,
                                      markersize=options["raw_marker_pt"], markerfacecolor="white", markeredgecolor=color,
                                      markeredgewidth=options["raw_edge_pt"], linestyle="none", zorder=5)
                    mapper.register(fig, artist, "raw-observation", f"{condition} · {item['hour']} h · source {raw['source_cell']}",
                                    key=[spec["compartment"], raw["source_sheet"], raw["source_cell"]],
                                    source_keys=[{"source_sheet": raw["source_sheet"], "source_cell": raw["source_cell"],
                                                  "condition": condition, "nominal_hour": int(raw["hour"])}],
                                    spec_paths=[mapper.pointer("colors", condition), mapper.pointer("options", "raw_marker_pt"),
                                                mapper.pointer("options", "raw_edge_pt")], editable=["color", "markersize", "linewidth"])
                    source_artists.append({"row": raw, "artist": artist, "display_hour": float(position[0])})
        handles = [Line2D([], [], color=spec["colors"][condition], linewidth=options["mean_line_pt"],
                          marker=options["markers"][condition], markersize=options["mean_marker_pt"],
                          markeredgewidth=options["mean_edge_pt"], markeredgecolor="white")
                   for condition in spec["order"]["condition"]]
        legend = fig.legend(handles, spec["order"]["condition"], loc="upper right", bbox_to_anchor=(.965, .985),
                            borderaxespad=0, frameon=False, ncol=2, columnspacing=1.0, handlelength=1.2,
                            handletextpad=.4, borderpad=0)
        mapper.register(fig, legend, "legend", "Genotype · mean trajectory keys", key=spec["compartment"],
                        spec_paths=[mapper.pointer("order", "condition")], editable=["layout"])
        for condition, handle in zip(spec["order"]["condition"], legend.legend_handles):
            mapper.register(fig, handle, "legend-key", condition, key=[spec["compartment"], condition],
                            source_keys=[{"condition": condition}], spec_paths=[mapper.pointer("colors", condition)], editable=["color"])
        fig._ccl2_raw_artists = source_artists
        fig._ccl2_summary_artists = summary_artists
        fig._ccl2_resolved_font = {"requested": layout["font"], "actual_name": resolved_name, "file": font}
        fig._easyviz_resolved_colors = spec["colors"].copy()
        fig._easyviz_track = "create"
        mapper.attach_layout(fig, spec)
        fig.canvas.draw()
    return fig, ax


def artist_evidence(fig, ax, spec):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    mm_per_pixel = 25.4 / fig.dpi
    raw_records, summary_records = [], []
    region = ax.get_window_extent(renderer)
    clearances = []
    for record in fig._ccl2_raw_artists:
        artist, row = record["artist"], record["row"]
        x, y = float(artist.get_xdata()[0]), float(artist.get_ydata()[0])
        if not math.isclose(y, float(row["ccl2"]), rel_tol=1e-12, abs_tol=1e-10):
            raise ValueError("An actual raw artist changed the source concentration")
        center = ax.transData.transform((x, y))
        radius = (artist.get_markersize() + artist.get_markeredgewidth()) / 2 * fig.dpi / 72
        margin = min(center[0] - radius - region.x0, region.x1 - center[0] - radius,
                     center[1] - radius - region.y0, region.y1 - center[1] - radius) * mm_per_pixel
        clearances.append(margin)
        if margin < -1e-6:
            raise ValueError(f"Raw glyph clips: {row['source_cell']}")
        offset = (center[0] - ax.transData.transform((float(row["hour"]), y))[0]) * mm_per_pixel
        if abs(offset) > spec["options"]["raw_max_offset_mm"] + 1e-7:
            raise ValueError("A raw display offset exceeds the agreed bound")
        raw_records.append({**row, "display_hour": x, "display_offset_mm": float(offset),
                            "center_canvas_mm": [float(item * mm_per_pixel) for item in center],
                            "radius_with_stroke_mm": radius * mm_per_pixel, "glyph_axis_clearance_mm": margin,
                            "artist_id": artist.get_gid()})
    for record in fig._ccl2_summary_artists:
        point, interval = record["mean_artist"], record["sem_artist"]
        x, y = float(point.get_xdata()[0]), float(point.get_ydata()[0])
        assert x == record["hour"] and math.isclose(y, record["mean"], rel_tol=1e-12)
        assert np.allclose(interval.get_ydata(), [record["mean"] - record["sem"], record["mean"] + record["sem"]], rtol=1e-12)
        radius = (point.get_markersize() + point.get_markeredgewidth()) / 2 * fig.dpi / 72
        center = ax.transData.transform((x, y))
        ends = ax.transData.transform(np.column_stack((interval.get_xdata(), interval.get_ydata())))
        halfstroke = interval.get_linewidth() / 2 * fig.dpi / 72
        margin = min(center[0] - radius - region.x0, region.x1 - center[0] - radius,
                     center[1] - radius - region.y0, region.y1 - center[1] - radius,
                     np.min(ends[:, 1]) - halfstroke - region.y0, region.y1 - np.max(ends[:, 1]) - halfstroke) * mm_per_pixel
        clearances.append(margin)
        assert margin > 0, "A mean/SEM footprint reaches an axis boundary"
        summary_records.append({key: value for key, value in record.items() if key not in ("mean_artist", "sem_artist", "trajectory")}
                               | {"nominal_hour": x, "actual_mean_y": y, "actual_sem_y": list(map(float, interval.get_ydata())),
                                  "glyph_axis_clearance_mm": margin, "mean_artist_id": point.get_gid(), "sem_artist_id": interval.get_gid()})
    text_boxes = []
    width, height = spec["layout"]["width_mm"], spec["layout"]["height_mm"]
    for text in fig.findobj(matplotlib.text.Text):
        if not text.get_visible() or not text.get_text().strip():
            continue
        bounds = text.get_window_extent(renderer)
        box = [bounds.x0 * mm_per_pixel, bounds.y0 * mm_per_pixel, bounds.x1 * mm_per_pixel, bounds.y1 * mm_per_pixel]
        if min(box[:2]) < -.02 or box[2] > width + .02 or box[3] > height + .02:
            raise ValueError(f"Text clips canvas: {text.get_text()} {box}")
        assert text.get_fontsize() == spec["layout"]["font_size_pt"]
        text_boxes.append({"text": text.get_text(), "font_size_pt": text.get_fontsize(), "bbox_mm": box})
    pair_gaps = []
    for index, first in enumerate(raw_records):
        for second in raw_records[index + 1:]:
            delta = np.subtract(first["center_canvas_mm"], second["center_canvas_mm"])
            # Square footprint clearance is axis-aligned, not a circle-radius
            # approximation that could miss overlapping square corners.
            distance = (max(abs(float(value)) for value in delta)
                        if first["condition"] == second["condition"] == "IM-DTR"
                        else math.dist(first["center_canvas_mm"], second["center_canvas_mm"]))
            pair_gaps.append(distance - first["radius_with_stroke_mm"] - second["radius_with_stroke_mm"])
    if min(pair_gaps) < -1e-6:
        raise ValueError("Actual raw glyph footprints overlap")
    return {"status": "pass", "raw_rows": raw_records, "summary_rows": summary_records,
            "minimum_raw_glyph_gap_mm": min(pair_gaps), "minimum_axis_footprint_clearance_mm": min(clearances),
            "data_region_mm": [float(value * mm_per_pixel) for value in (region.x0, region.y0, region.width, region.height)],
            "text_boxes": text_boxes, "actual_font": fig._ccl2_resolved_font,
            "raw_x_interpretation": "bounded categorical display offsets; nominal source hours are retained",
            "mean_x_interpretation": "exact linear source hours; lines join group means, not individual mice"}


def render_panel(rows, source_bytes, spec, spec_bytes, spec_path, destination, mapper):
    destination.mkdir(parents=True, exist_ok=True)
    compartment = spec["compartment"]
    selected = [row for row in rows if row["compartment"] == compartment]
    source_path = HERE / "inputs/observations.csv"
    code_bytes = Path(__file__).read_bytes()
    bindings = {"data_file": {"path": str(source_path.resolve()), "sha256": digest_bytes(source_bytes)},
                "source_script": {"path": str(Path(__file__).resolve()), "sha256": digest_bytes(code_bytes)},
                "spec_file": {"path": str(spec_path.resolve()), "sha256": digest_bytes(spec_bytes)}}
    fig, ax = draw(selected, spec, mapper)
    try:
        fig._easyviz_source_script = Path(__file__).resolve()
        fig._easyviz_data_file = source_path.resolve()
        fig._easyviz_spec_file = spec_path.resolve()
        fig._easyviz_source_bindings = bindings
        evidence = artist_evidence(fig, ax, spec)
        before = source_continuity(bindings)
        if before["status"] != "pass":
            raise ValueError(f"Source changed before export: {before}")
        # Export settings must remain active during serialization, rather than
        # merely during artist construction: SVG text and PDF embedded fonts
        # are controlled by the rc values in force at savefig time.
        with plt.rc_context({"svg.fonttype": "none", "pdf.fonttype": 42,
                             "svg.hashsalt": "easyviz-compartment-ccl2"}):
            for name in ("pdf", "svg", "png"):
                metadata = ({"Creator": "EasyViz Create Ccl2 case", "CreationDate": None, "ModDate": None}
                            if name == "pdf" else {"Creator": "EasyViz Create Ccl2 case", "Date": None}
                            if name == "svg" else None)
                fig.savefig(destination / ("panel." + name), dpi=spec["layout"]["dpi"], facecolor="white", metadata=metadata)
        mapper.write(fig, destination, spec, spec["layout"])
        after = source_continuity(bindings)
        if after["status"] != "pass":
            raise ValueError(f"Source changed during export: {after}")
        (destination / "source-snapshot.csv").write_bytes(source_bytes)
        (destination / "spec-snapshot.json").write_bytes(spec_bytes)
        with (destination / "plotting-data.csv").open("w", newline="") as handle:
            fields = list(selected[0]) + ["display_hour", "display_offset_mm", "artist_id"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in evidence["raw_rows"]:
                writer.writerow({key: row[key] for key in fields})
        (destination / "artist-evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        report = {"status": "pass", "compartment": compartment, "input_rows": len(selected), "whole_input_rows": len(rows),
                  "source_sha256": digest_bytes(source_bytes), "source_bindings": bindings,
                  "continuity_before": before, "continuity_after": after,
                  "layout_mm": [spec["layout"]["width_mm"], spec["layout"]["height_mm"]],
                  "summary_definition": "mean ± SEM = sample SD / sqrt(n)", "mean_times_exact": True,
                  "source_p_values_plotted": False, "no_animal_pairs_inferred": True,
                  "exports": {name: digest_bytes((destination / ("panel." + name)).read_bytes()) for name in ("pdf", "svg", "png")},
                  "minimum_raw_glyph_gap_mm": evidence["minimum_raw_glyph_gap_mm"],
                  "minimum_axis_footprint_clearance_mm": evidence["minimum_axis_footprint_clearance_mm"]}
        (destination / "qa.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        with pymupdf.open(destination / "panel.pdf") as document:
            document[0].get_pixmap(dpi=96).save(destination / "pdf-preview-96dpi.png")
    finally:
        plt.close(fig)
    return report


def compose(outputs, destination):
    """Place independent vector panels at original size; no redraw or scaling."""
    destination.mkdir(parents=True, exist_ok=True)
    sources = [pymupdf.open(folder / "panel.pdf") for folder in outputs]
    document = pymupdf.open()
    try:
        widths = [source[0].rect.width for source in sources]
        height = max(source[0].rect.height for source in sources)
        gap = 3 / 25.4 * 72
        total = sum(widths) + gap * (len(widths) - 1)
        page = document.new_page(width=total, height=height)
        combined = ET.Element(f"{{{SVG}}}svg", {"version": "1.1", "width": f"{total}pt", "height": f"{height}pt", "viewBox": f"0 0 {total} {height}"})
        records, left = [], 0
        for index, (folder, source, width) in enumerate(zip(outputs, sources, widths)):
            page.show_pdf_page(pymupdf.Rect(left, 0, left + width, source[0].rect.height), source, 0)
            root = ET.parse(folder / "panel.svg").getroot()
            ids = {node.attrib["id"]: f"compartment-{index}-{node.attrib['id']}" for node in root.iter() if "id" in node.attrib}
            group = ET.SubElement(combined, f"{{{SVG}}}g", {"transform": f"translate({left} 0)"})
            import re
            for child in root:
                clone = deepcopy(child)
                for node in clone.iter():
                    for key, value in list(node.attrib.items()):
                        if key == "id":
                            node.attrib[key] = ids[value]
                        elif value.startswith("#") and value[1:] in ids:
                            node.attrib[key] = "#" + ids[value[1:]]
                        else:
                            node.attrib[key] = re.sub(r"url\(#([^)]*)\)", lambda match: "url(#" + ids.get(match[1], match[1]) + ")", value)
                group.append(clone)
            records.append({"source": str(folder.relative_to(destination.parent)), "offset_mm": left / 72 * 25.4,
                            "width_mm": width / 72 * 25.4, "height_mm": source[0].rect.height / 72 * 25.4,
                            "pdf_sha256": digest_bytes((folder / "panel.pdf").read_bytes())})
            left += width + gap
        document.save(destination / "panel.pdf", garbage=4, deflate=True, no_new_id=True)
        ET.ElementTree(combined).write(destination / "panel.svg", encoding="utf-8", xml_declaration=True)
        page.get_pixmap(dpi=300).save(destination / "panel.png")
        page.get_pixmap(dpi=96).save(destination / "pdf-preview-96dpi.png")
        (destination / "composition.json").write_text(json.dumps({"status": "pass", "panels": records,
            "gap_mm": 3, "rescaled": False, "data_redrawn": False, "font_size_changed": False,
            "dimensions_mm": [total / 72 * 25.4, height / 72 * 25.4]}, indent=2) + "\n")
    finally:
        document.close()
        for source in sources:
            source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    destination = args.out.resolve()
    if not args.overwrite and any((destination / "panels" / name / "output/panel.svg").exists() for name in ("lung", "serum")):
        raise FileExistsError("Exports already exist; use a new --out folder or explicit --overwrite")
    mapper = mapping_runtime(runtime_path(args.tools))
    rows, source_bytes = captured_csv(HERE / "inputs/observations.csv")
    outputs, reports = [], []
    for name in ("lung", "serum"):
        spec_path = HERE / "panels" / name / "spec.json"
        spec_bytes = spec_path.read_bytes()
        spec = json.loads(spec_bytes)
        target = destination / "panels" / name / "output"
        reports.append(render_panel(rows, source_bytes, spec, spec_bytes, spec_path, target, mapper))
        outputs.append(target)
    compose(outputs, destination / "output")
    print(json.dumps({"status": "pass", "panels": [item["compartment"] for item in reports], "source_rows": len(rows), "output": str(destination)}))


if __name__ == "__main__":
    main()
