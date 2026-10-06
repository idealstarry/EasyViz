#!/usr/bin/env python3
"""Bounded, reproducible legend-layout benchmark; not universal layout certification.

Fresh synthetic data exercise semantic mappings and measured rendered geometry.
Before/after runs use identical CSV, specification, font, and canvas. The saved
baseline is a historical renderer snapshot; main code is imported by path.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-legend-eval-mpl"))
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex
from matplotlib.legend import Legend
from matplotlib.text import Text
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from marker_geometry import collection_fill_areas_pt2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "legend-transfer"
PALETTE = ["#2581B9", "#DF9A3C", "#1AA781", "#D76F3B", "#007F7F", "#A37FFF", "#29ACF3", "#E47751"]
LONG = ["Activated T cells", "Memory B cells", "Inflammatory monocytes", "Dendritic cell precursors",
        "Cytotoxic lymphocytes", "Vascular endothelial cells", "Stromal progenitor cells", "Tissue resident macrophages"]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_module(path, name):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fixture(case_id, chart, width, height, rows, spec_updates, *, intent, expected="pass"):
    base = {"chart": chart, "layout": {"width_mm": width, "height_mm": height, "font": "Arial", "font_size_pt": 8,
            "line_width_pt": .6, "dpi": 300}, "typography": {name: 8 for name in ("axis", "tick", "legend", "annotation")},
            "formats": ["svg", "png"], "seed": 23}
    base.update(spec_updates)
    folder = OUT / "cases" / case_id
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "source.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    write_json(folder / "spec.json", base)
    return {"id": case_id, "chart": chart, "width_mm": width, "height_mm": height,
            "intent": intent, "expected_after_status": expected, "source": str((folder / "source.csv").relative_to(OUT)),
            "spec": str((folder / "spec.json").relative_to(OUT)), "input_rows": len(rows)}


def categorical(case_id, count, width, height, long=False, extra=None, expected="pass"):
    groups = LONG[:count] if long else [f"G{i + 1}" for i in range(count)]
    rows = [{"unit": f"U{g:02}{i:02}", "arm": label, "score_x": round(.4 + i * .27 + g * .025, 5),
             "score_y": round(.35 + ((i * 3 + g * 2) % 9) * .17, 5)}
            for g, label in enumerate(groups) for i in range(6)]
    spec = {"fields": {"x": "score_x", "y": "score_y", "group": "arm", "unit": "unit"},
            "colors": dict(zip(groups, PALETTE)), "order": {"group": groups},
            "labels": {"x": "Score X", "y": "Score Y"},
            "options": {"point_area_pt2": 12, "alpha": 1, "grid": False}}
    if extra:
        spec.update(extra)
    return fixture(case_id, "scatter", width, height, rows, spec, expected=expected,
                   intent=f"{count} complete categorical entries with {'long' if long else 'short'} labels; preserve decoding and keep legend outside the plotting rectangle without shrinking 8 pt type.")


def generate():
    cases = [
        categorical("categorical-2-short-88", 2, 88, 72),
        categorical("categorical-4-long-132", 4, 132, 88, long=True),
        categorical("categorical-8-short-180", 8, 180, 96),
        categorical("categorical-8-long-180", 8, 180, 108, long=True),
    ]
    for case_id, width, height, nr, nc in [("colorbar-landscape-132", 132, 76, 5, 7), ("colorbar-square-88", 88, 88, 6, 6)]:
        rows = [{"feature": f"F{r + 1}", "sample": f"S{c + 1}", "value": round((r * 3 + c * 2) % 17 / 16, 4)} for r in range(nr) for c in range(nc)]
        cases.append(fixture(case_id, "heatmap", width, height, rows,
                     {"fields": {"row": "feature", "column": "sample", "value": "value"},
                      "labels": {"x": "Sample", "y": "Feature", "color": "Fraction"},
                      "colormap": ["#F5FBFE", "#2581B9"], "options": {"color_limits": [0, 1], "x_rotation": 0}},
                     intent="Readable continuous scale with stable 0–1 mapping; occupied colorbar length and reserved space are measured, not forced to a universal ratio."))
    for case_id, width, height, maximum, area in [("dot-small-88", 88, 88, 20, 36), ("dot-large-132", 132, 96, 200, 144)]:
        rows = [{"column": f"C{c + 1}", "row": f"R{r + 1}", "count": maximum * ([.1, .25, .5, 1][(r + c) % 4]),
                 "fraction": round(((r * 2 + c * 3) % 11) / 10, 2)} for r in range(5) for c in range(5)]
        cases.append(fixture(case_id, "dotplot", width, height, rows,
                     {"fields": {"x": "column", "y": "row", "size": "count", "color": "fraction"},
                      "labels": {"x": "Sample", "y": "Feature", "size": "Count", "color": "Fraction"},
                      "colormap": ["#F5FBFE", "#2581B9"],
                      "options": {"size_max": maximum, "max_area_pt2": area, "size_legend": [maximum * .1, maximum * .5, maximum], "color_limits": [0, 1], "x_rotation": 0}},
                     intent="Independent size and color keys must be readable and nonoverlapping. Quantitative legend areas must remain exactly proportional to data areas."))
    manual_layout = {"width_mm": 132, "height_mm": 96, "font": "Arial", "font_size_pt": 8, "line_width_pt": .6, "dpi": 300,
                     "margins": {"left": .19, "right": .77, "bottom": .23, "top": .72}}
    cases.append(categorical("manual-categorical-132", 4, 132, 96, extra={"layout": manual_layout,
                 "legends": {"categorical": {"position": "manual", "anchor_mm": [18, 76], "loc": "lower left", "ncol": 2}}}))
    cases[-1]["intent"] = "Honor the explicit lower-left legend anchor at (18,76) mm with two columns; preserve the same 132 × 96 mm canvas and 8 pt type. Historical renderer does not implement this override."
    cases.append(categorical("impossible-8-long-88", 8, 88, 32, long=True, expected="needs_revision"))
    cases[-1]["intent"] = "Eight long labels cannot fit this fixed footprint with adequate plot and 8 pt type. Return needs_revision; do not hide entries, shrink typography, or silently expand the canvas."
    manifest = {"kind": "synthetic evaluation", "generator": "tests/check_legend_layouts.py",
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "cases": cases,
                "comparison_control": "The before and after renderer receive identical source bytes and JSON specifications. Font, text sizes, canvas, values, and mappings are fixed within each case.",
                "acceptance": {"hard": ["No legend/plot or legend/legend intersection unless explicitly authorized", "No clipped output text", "All original source fields and rows retained", "All active text remains 8 pt", "Quantitative legend areas equal supplied size mapping", "Explicit placement honored", "Impossible footprint reports needs_revision"],
                               "diagnostic_only": ["Legend occupied area divided by plot/canvas area", "Occupied versus available margin-band area", "Colorbar length divided by plot dimension", "Before/after plotting-region size"],
                               "visual": "Inspect actual candidate images for missing decoding, excessive blank legend space, glyph crowding, and mark balance. Contact sheet is a documentation aid only."}}
    write_json(OUT / "manifest.json", manifest)
    return manifest


def box_mm(bounds, dpi):
    return [round(float(value) * 25.4 / dpi, 6) for value in (bounds.x0, bounds.y0, bounds.width, bounds.height)]


def intersection(a, b):
    return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))


def add_reserved_bands(geometry):
    """Describe geometric canvas margins; do not pretend all margin area is a key."""
    if not geometry:
        return geometry
    width, height = geometry["canvas_mm"]
    x, y, w, h = geometry["plot_bbox_mm"]
    bands = {"right": [x + w, 0, width - x - w, height], "left": [0, 0, x, height],
             "top": [0, y + h, width, height - y - h], "bottom": [0, 0, width, y]}
    geometry["canvas_margin_bands_mm"] = bands
    geometry["margin_band_note"] = "Geometric space outside the plot rectangle; bands include corners and are not summed. Axis text also occupies these margins. Actual helper reservations are recorded separately."
    for item in geometry["actual_legends"]:
        bx, by, bw, bh = item["bbox_mm"]
        side = "right" if bx >= x + w - .01 else "left" if bx + bw <= x + .01 else "top" if by >= y + h - .01 else "bottom" if by + bh <= y + .01 else "overlap"
        item["inferred_margin_side"] = side
        if side in bands:
            reserved = bands[side]
            item["inferred_available_band_mm"] = reserved
            item["occupied_fraction_of_inferred_band"] = bw * bh / (reserved[2] * reserved[3]) if reserved[2] * reserved[3] else None
    return geometry


def inspect_figure(fig, spec):
    fig.canvas.draw()
    painter, dpi = fig.canvas.get_renderer(), fig.dpi
    primary = fig.axes[0]
    plot = box_mm(primary.get_window_extent(painter), dpi)
    width, height = fig.get_size_inches() * 25.4
    legends, signal = [], {"collections": [], "images": []}
    axis_text = []
    for direction, axis in (("x", primary.xaxis), ("y", primary.yaxis)):
        if axis.label.get_visible() and axis.label.get_text().strip():
            axis_text.append({"role": f"{direction} label", "text": axis.label.get_text(), "bbox_mm": box_mm(axis.label.get_window_extent(painter), dpi)})
        low, high = sorted(axis.get_view_interval())
        for tick in axis.get_major_ticks():
            if low - 1e-9 <= tick.get_loc() <= high + 1e-9:
                for label in (tick.label1, tick.label2):
                    if label.get_visible() and label.get_text().strip():
                        axis_text.append({"role": f"{direction} tick", "text": label.get_text(), "bbox_mm": box_mm(label.get_window_extent(painter), dpi)})
    for coll in primary.collections:
        offsets = np.ma.asarray(coll.get_offsets()).filled(np.nan)
        if len(offsets):
            signal["collections"].append({"offsets": offsets.tolist(), "sizes": coll.get_sizes().tolist(),
                "values": None if coll.get_array() is None else np.ma.asarray(coll.get_array()).filled(np.nan).tolist(),
                "clim": list(coll.get_clim()), "facecolors": coll.get_facecolors().tolist()})
    for image in primary.images:
        signal["images"].append({"values": np.ma.asarray(image.get_array()).filled(np.nan).tolist(), "clim": list(image.get_clim())})
    for legend in fig.findobj(Legend):
        if not legend.get_visible():
            continue
        bbox = box_mm(legend.get_window_extent(painter), dpi)
        items = []
        for handle, text in zip(legend.legend_handles, legend.get_texts()):
            item = {"label": text.get_text(), "text_bbox_mm": box_mm(text.get_window_extent(painter), dpi)}
            if isinstance(handle, PathCollection):
                if len(handle.get_facecolors()):
                    item["fill_color"] = to_hex(handle.get_facecolors()[0])
                item["marker_size_parameters_pt2"] = handle.get_sizes().tolist()
                item["areas_pt2"] = collection_fill_areas_pt2(handle, fig).tolist()
                offsets = handle.get_offset_transform().transform(handle.get_offsets())
                symbols = []
                for center, area in zip(offsets, handle.get_sizes()):
                    diameter_px = math.sqrt(float(area)) / 72 * dpi
                    symbols.append([round((float(center[0]) - diameter_px / 2) * 25.4 / dpi, 6),
                                    round((float(center[1]) - diameter_px / 2) * 25.4 / dpi, 6),
                                    round(diameter_px * 25.4 / dpi, 6), round(diameter_px * 25.4 / dpi, 6)])
                item["symbol_bboxes_mm"] = symbols
            else:
                item["handle_type"] = type(handle).__name__
                if hasattr(handle, "get_facecolor"):
                    item["fill_color"] = to_hex(handle.get_facecolor())
                elif hasattr(handle, "get_markerfacecolor"):
                    item["fill_color"] = to_hex(handle.get_markerfacecolor())
            items.append(item)
        legends.append({"kind": "size" if spec["chart"] == "dotplot" else "categorical", "bbox_mm": bbox,
                        "labels": [text.get_text() for text in legend.get_texts()], "title": legend.get_title().get_text(), "items": items})
    for axis in fig.axes[1:]:
        if hasattr(axis, "_colorbar"):
            legends.append({"kind": "colorbar", "bbox_mm": box_mm(axis.get_tightbbox(painter), dpi),
                            "bar_bbox_mm": box_mm(axis.get_window_extent(painter), dpi),
                            "ticks": axis._colorbar.get_ticks().tolist(), "clim": list(axis._colorbar.mappable.get_clim()),
                            "label": axis.get_ylabel() or axis.get_xlabel()})
    collisions = []
    for index, item in enumerate(legends):
        area = item["bbox_mm"][2] * item["bbox_mm"][3]
        item["area_fraction_of_plot"] = area / (plot[2] * plot[3])
        item["area_fraction_of_canvas"] = area / (width * height)
        item["plot_intersection_mm2"] = intersection(item["bbox_mm"], plot)
        if item["plot_intersection_mm2"] > .01:
            collisions.append({"roles": [item["kind"], "plot"], "intersection_mm2": item["plot_intersection_mm2"]})
        for text in axis_text:
            overlap = intersection(item["bbox_mm"], text["bbox_mm"])
            if overlap > .01:
                collisions.append({"roles": [item["kind"], f"{text['role']}: {text['text']}"], "intersection_mm2": overlap})
        for other in legends[index + 1:]:
            overlap = intersection(item["bbox_mm"], other["bbox_mm"])
            if overlap > .01:
                collisions.append({"roles": [item["kind"], other["kind"]], "intersection_mm2": overlap})
        # Exact symbol boxes matter especially for large quantitative dots.
        symbols = [(row["label"], box) for row in item.get("items", []) for box in row.get("symbol_bboxes_mm", [])]
        texts = [(row["label"], row["text_bbox_mm"]) for row in item.get("items", [])]
        for label, symbol in symbols:
            for text_label, text in texts:
                overlap = intersection(symbol, text)
                if overlap > .01:
                    collisions.append({"roles": [f"{item['kind']} symbol {label}", f"legend text {text_label}"], "intersection_mm2": overlap})
    font_sizes = sorted({float(artist.get_fontsize()) for artist in fig.findobj(Text) if artist.get_visible() and artist.get_text().strip()})
    return add_reserved_bands({"canvas_mm": [float(width), float(height)], "plot_bbox_mm": plot,
            "decorated_plot_bbox_mm": box_mm(primary.get_tightbbox(painter, bbox_extra_artists=[]), dpi),
            "plot_bbox_note": "plot_bbox_mm is the data rectangle; decorated_plot_bbox_mm additionally includes axes/ticks/axis labels but excludes the legend.", "axis_text_bboxes_mm": axis_text, "actual_legends": legends,
            "measured_collisions": collisions, "text_sizes_pt": font_sizes, "data_artist_values": signal,
            "mark_geometry": getattr(fig, "_easyviz_mark_geometry", None)})


def values_preserved(source, plotted):
    if not plotted.exists():
        return None
    original = list(csv.DictReader(source.open()))
    actual = list(csv.DictReader(plotted.open()))
    if len(original) != len(actual):
        return False
    for expected, observed in zip(original, actual):
        for key, value in expected.items():
            if key not in observed:
                return False
            try:
                same = float(value) == float(observed[key])
            except ValueError:
                same = value == observed[key]
            if not same:
                return False
    return True


def inspect_size_exports(destination, geometry, spec):
    """Measure actual vector paths and raster ink, independently of get_sizes()."""
    if spec["chart"] != "dotplot":
        return None
    options = spec["options"]
    expected_areas = [float(v) / options["size_max"] * options["max_area_pt2"] for v in options["size_legend"]]
    output = {"expected_areas_pt2": expected_areas, "expected_diameters_pt": [2 * math.sqrt(v / math.pi) for v in expected_areas],
              "area_contract": "Geometric circle fill area, excluding stroke; raw Matplotlib s is 4/pi times this area."}
    svg_path = destination / "panel.svg"
    if svg_path.exists():
        root = ET.parse(svg_path).getroot()
        ns = "{http://www.w3.org/2000/svg}"
        definitions = {item.attrib["id"]: item for item in root.iter() if "id" in item.attrib}
        extents = []
        for group in root.iter(ns + "g"):
            if not group.attrib.get("id", "").startswith("legend_"):
                continue
            for collection in group.iter(ns + "g"):
                if not collection.attrib.get("id", "").startswith("PathCollection_"):
                    continue
                uses = list(collection.iter(ns + "use"))
                candidates = []
                for use in uses:
                    href = use.attrib.get("{http://www.w3.org/1999/xlink}href", use.attrib.get("href", ""))
                    candidates.append((definitions.get(href.removeprefix("#")), use))
                if not uses:
                    candidates = [(path, None) for path in collection.iter(ns + "path")]
                for path, use in candidates:
                    if path is None or path.tag != ns + "path":
                        continue
                    numbers = [float(v) for v in re.findall(r"[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?", path.attrib.get("d", ""))]
                    if len(numbers) < 8 or len(numbers) % 2:
                        continue
                    xs, ys = numbers[::2], numbers[1::2]
                    offset = [float(use.attrib.get("x", 0)), float(use.attrib.get("y", 0))] if use is not None else [0, 0]
                    extents.append({"diameter_x_pt": max(xs) - min(xs), "diameter_y_pt": max(ys) - min(ys),
                                    "center_pt": [(max(xs) + min(xs)) / 2 + offset[0], (max(ys) + min(ys)) / 2 + offset[1]],
                                    "transform": use.attrib.get("transform") if use is not None else collection.attrib.get("transform"),
                                    "definition_transform": path.attrib.get("transform")})
        expected_centers = []
        for legend in geometry.get("actual_legends", []):
            if legend["kind"] == "size":
                for item in legend["items"]:
                    for x, y, w, h in item.get("symbol_bboxes_mm", []):
                        expected_centers.append([(x + w / 2) * 72 / 25.4, (spec["layout"]["height_mm"] - y - h / 2) * 72 / 25.4])
        output["expected_svg_centers_pt"] = expected_centers
        output["svg_center_tolerance_pt"] = .25
        output["svg_diameter_tolerance_pt"] = .001
        output["svg_marker_extents"] = extents
        output["svg_pass"] = len(extents) == len(expected_areas) == len(expected_centers) and all(
            abs(item["diameter_x_pt"] - 2 * math.sqrt(area / math.pi)) < .001 and abs(item["diameter_y_pt"] - 2 * math.sqrt(area / math.pi)) < .001
            and np.allclose(item["center_pt"], center, atol=.25) and not item["transform"] and not item["definition_transform"]
            for item, area, center in zip(extents, expected_areas, expected_centers))
    else:
        output["svg_pass"] = False
    png_path = destination / "panel.png"
    raster = []
    if png_path.exists():
        image = Image.open(png_path).convert("RGB")
        px_per_mm = spec["layout"]["dpi"] / 25.4
        for legend in geometry.get("actual_legends", []):
            if legend["kind"] != "size":
                continue
            for item in legend["items"]:
                color = item.get("fill_color", "#777777")
                rgb = np.array([int(color[index:index + 2], 16) for index in (1, 3, 5)])
                for box, area in zip(item.get("symbol_bboxes_mm", []), item.get("areas_pt2", [])):
                    x, y, width, height = box
                    crop_box = (math.floor(x * px_per_mm) - 3, math.floor(image.height - (y + height) * px_per_mm) - 3,
                                math.ceil((x + width) * px_per_mm) + 3, math.ceil(image.height - y * px_per_mm) + 3)
                    pixels = np.asarray(image.crop(crop_box)).astype(int)
                    mask = (np.abs(pixels - rgb) <= 4).all(axis=2)
                    yy, xx = np.where(mask)
                    measured = [int(xx.max() - xx.min() + 1), int(yy.max() - yy.min() + 1)] if len(xx) else [0, 0]
                    expected = 2 * math.sqrt(float(area) / math.pi) / 72 * spec["layout"]["dpi"]
                    raster.append({"label": item["label"], "expected_diameter_px": expected, "same_fill_ink_extent_px": measured,
                                   "tolerance_px": 2.5, "passed": all(abs(value - expected) <= 2.5 for value in measured)})
    output["png_ink_checks"] = raster
    output["png_pass"] = len(raster) == len(expected_areas) and all(item["passed"] for item in raster)
    output["scope"] = "Circular quantitative legend keys in these Matplotlib SVG/PNG exports; SVG path diameters use point-sized viewBox units. SVG center tolerance permits subpoint text-centering differences between raster/vector backends; it does not loosen marker area checks. Raster tolerance accounts for integer positioning and antialiasing."
    return output


def run_case(module, case, stage):
    folder = OUT / "cases" / case["id"]
    source, settings = folder / "source.csv", folder / "spec.json"
    spec = json.loads(settings.read_text())
    destination = folder / stage
    measurement = {}
    original_export = module.export
    def capture(fig, out, actual_spec, layout):
        measurement.update(inspect_figure(fig, actual_spec))
        return original_export(fig, out, actual_spec, layout)
    module.export = capture
    error = None
    try:
        module.render(source, spec, destination)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        module.export = original_export
    qa_path = destination / "qa.json"
    qa = json.loads(qa_path.read_text()) if qa_path.exists() else {"status": "no_qa"}
    helper_path = Path(module.__file__).parent / "legend_layout.py"
    measured = {"renderer_path": str(Path(module.__file__).resolve()), "renderer_sha256": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
                "legend_helper_sha256": hashlib.sha256(helper_path.read_bytes()).hexdigest() if helper_path.exists() else None,
                "renderer_status": qa["status"], "error": error, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "source_values_preserved": values_preserved(source, destination / "plotting-data.csv"),
                "geometry": measurement, "reported_legend_layout": qa.get("legend_layout"),
                "clipped_text": qa.get("clipped_text"), "tick_overlaps": qa.get("overlapping_tick_labels"),
                "actual_size_export_checks": inspect_size_exports(destination, measurement, spec)}
    write_json(destination / "measured-geometry.json", measured)
    return measured


def evaluate(case, before, after):
    failures, notes = [], []
    geometry = after.get("geometry", {})
    spec = json.loads((OUT / case["spec"]).read_text())
    expected = case["expected_after_status"]
    if expected == "needs_revision":
        if after["renderer_status"] != "needs_revision":
            failures.append(f"Impossible footprint returned {after['renderer_status']}, expected needs_revision.")
        if geometry and geometry.get("text_sizes_pt") != [8.0]:
            failures.append("Impossible case silently changed typography.")
    else:
        if after["renderer_status"] not in ("pass", "passed"):
            failures.append(f"Feasible case returned {after['renderer_status']}.")
        if not geometry:
            failures.append("No actual figure geometry was captured.")
        if after["source_values_preserved"] is not True:
            failures.append("Source rows/values not verified as preserved.")
        if geometry.get("text_sizes_pt") != [8.0]:
            failures.append("Active output text differs from 8 pt.")
        failures.extend(f"Measured collision: {issue['roles']}" for issue in geometry.get("measured_collisions", []))
        if after.get("clipped_text"):
            failures.append("Output text is clipped.")
        if geometry and not np.allclose(geometry["canvas_mm"], [case["width_mm"], case["height_mm"]], atol=1e-5):
            failures.append("Canvas changed.")
        if case["chart"] == "scatter":
            legends = [legend for legend in geometry.get("actual_legends", []) if legend["kind"] == "categorical"]
            declared = spec["order"]["group"]
            if len(legends) != 1 or legends[0]["labels"] != declared:
                failures.append("Categorical legend label coverage/order differs from the declared groups.")
            else:
                for item in legends[0]["items"]:
                    if item.get("fill_color") != to_hex(spec["colors"][item["label"]]):
                        failures.append(f"Categorical key color differs for {item['label']}.")
        if case["chart"] in ("heatmap", "dotplot"):
            scales = [legend for legend in geometry.get("actual_legends", []) if legend["kind"] == "colorbar"]
            if len(scales) != 1 or not np.allclose(scales[0]["clim"], spec["options"]["color_limits"], atol=1e-10):
                failures.append("Required colorbar is absent or its range differs from the supplied mapping.")
            elif scales[0]["label"] != spec["labels"]["color"]:
                failures.append("Colorbar meaning label is absent or altered.")
        if case["chart"] == "dotplot":
            options = spec["options"]
            intended = [float(value) / options["size_max"] * options["max_area_pt2"] for value in options["size_legend"]]
            observed = [item["areas_pt2"][0] for legend in geometry.get("actual_legends", []) if legend["kind"] == "size" for item in legend["items"] if "areas_pt2" in item]
            if len(observed) != len(intended) or not np.allclose(observed, intended, rtol=1e-6, atol=1e-10):
                failures.append(f"Quantitative symbol area changed: {observed} vs {intended} pt².")
            exported = after.get("actual_size_export_checks") or {}
            if not exported.get("svg_pass"):
                failures.append("Actual SVG quantitative key paths do not match the supplied areas.")
            if not exported.get("png_pass"):
                failures.append("Actual PNG quantitative key ink does not match the expected rendered diameter/position.")
            legends = [legend for legend in geometry.get("actual_legends", []) if legend["kind"] == "size"]
            if len(legends) != 1 or legends[0]["labels"] != [f"{value:g}" for value in options["size_legend"]] or legends[0]["title"] != spec["labels"]["size"]:
                failures.append("Quantitative size key is absent or its value/meaning labels changed.")
        if case["id"] == "manual-categorical-132":
            legends = [legend for legend in geometry.get("actual_legends", []) if legend["kind"] == "categorical"]
            if not legends or not np.allclose(legends[0]["bbox_mm"][:2], [18, 76], atol=.5):
                failures.append("Manual anchor not honored within 0.5 mm border-padding tolerance.")
            notes.append("Historical renderer ignores the manual override; no baseline support is implied.")
    if before and before.get("geometry") and geometry:
        before_signal = before["geometry"]["data_artist_values"]
        after_signal = deepcopy(geometry["data_artist_values"])
        before_mode = (before["geometry"].get("mark_geometry") or {}).get("mode")
        after_mode = (geometry.get("mark_geometry") or {}).get("mode")
        if case["chart"] == "dotplot" and before_mode is None and after_mode == "mapped_circle_fill_area":
            for original, current in zip(before_signal["collections"], after_signal["collections"]):
                expected_parameters = np.asarray(original["sizes"]) * 4 / math.pi
                if np.shape(current["sizes"]) == expected_parameters.shape and np.allclose(current["sizes"], expected_parameters, rtol=1e-10, atol=1e-10):
                    current["sizes"] = original["sizes"]
            notes.append("Historical max_area_pt2 was passed as raw Matplotlib s. Current core converts desired geometric circle fill area to s=4/pi*area; the intentional physical-size correction is checked separately and unchanged circle diameter is not claimed.")
        if before_signal != after_signal:
            failures.append("Before/after data artist values, areas, or color mappings differ.")
        if before["source_sha256"] != after["source_sha256"]:
            failures.append("Before/after source bytes differ.")
    if geometry and after["source_values_preserved"] is not True and not any("Source rows/values" in value for value in failures):
        failures.append("Source rows/values not verified as preserved.")
    notes.append("Legend/plot area and reserved-space ratios are diagnostics, not universal pass thresholds.")
    compactness = {}
    for name, result in (("before", before), ("after", after)):
        measured = result.get("geometry", {}) if result else {}
        if measured:
            plot = measured["plot_bbox_mm"]
            compactness[name] = {"plot_area_mm2": plot[2] * plot[3],
                "total_occupied_legend_bbox_area_mm2": sum(item["bbox_mm"][2] * item["bbox_mm"][3] for item in measured["actual_legends"]),
                "colorbar_lengths_mm": [max(item["bar_bbox_mm"][2:]) for item in measured["actual_legends"] if item["kind"] == "colorbar"],
                "legend_bboxes_mm": [{"kind": item["kind"], "bbox_mm": item["bbox_mm"]} for item in measured["actual_legends"]]}
    return {"id": case["id"], "status": "passed" if not failures else "failed", "failures": failures, "notes": notes, "compactness_diagnostics": compactness,
            "expected_after_status": expected, "before_renderer_status": before["renderer_status"] if before else "not_run", "after_renderer_status": after["renderer_status"]}


def contact_sheet(cases):
    px_per_mm, column, padding = 3, 560, 16
    rows = [max(100, math.ceil(case["height_mm"] * px_per_mm)) + 45 for case in cases]
    sheet = Image.new("RGB", (column * 2 + padding * 3, sum(rows) + 60), "#f1f3f4")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(font_manager.findfont("Arial"), 15)
    draw.text((padding, 10), "Documentation thumbnails only; inspect originals at their recorded size.", fill="black", font=font)
    y = 42
    for case, row_height in zip(cases, rows):
        for i, stage in enumerate(("before", "after")):
            x = padding + i * (column + padding)
            qa_path = OUT / "cases" / case["id"] / stage / "qa.json"
            status = json.loads(qa_path.read_text()).get("status", "unknown") if qa_path.exists() else "not_run"
            draw.text((x, y), f"{case['id']} — {stage} [{status}]", fill="black", font=font)
            image_path = OUT / "cases" / case["id"] / stage / "panel.png"
            if image_path.exists():
                im = Image.open(image_path).convert("RGB")
                im = im.resize((round(case["width_mm"] * px_per_mm), round(case["height_mm"] * px_per_mm)), Image.Resampling.LANCZOS)
                sheet.paste(im, (x, y + 24))
            else:
                draw.text((x + 8, y + 40), "No export — see this run's QA and error record", fill="#7A2424", font=font)
        y += row_height
    sheet.save(OUT / "contact-sheet.png")


def report(manifest, results):
    summary = {"scope": f"Only the {len(results)} rendered cases listed below from the ten-case synthetic manifest; no universal legend-layout claim", "results": results,
               "passed": sum(item["status"] == "passed" for item in results), "failed": sum(item["status"] == "failed" for item in results),
               "geometry_units": "mm; [x0,y0,width,height] from lower-left canvas origin; marker area in pt²",
               "visual_review": "Actual images require inspection; independent findings are saved separately in visual-review.md. A contact sheet is not a print proof.",
               "comparison_controls": manifest["comparison_control"], "acceptance": manifest["acceptance"]}
    write_json(OUT / "results.json", summary)
    lines = ["# Legend transfer benchmark", "", summary["scope"] + ".", "", manifest["comparison_control"], "",
             "| Case | Before renderer | After renderer | Benchmark checks |", "| --- | --- | --- | --- |"]
    for result in results:
        lines.append(f"| {result['id']} | {result['before_renderer_status']} | {result['after_renderer_status']} | {result['status']} |")
    lines.extend(["", "Each run's `measured-geometry.json` records actual legend, symbol, label, colorbar, and plot boxes, including both the data rectangle and its decorated axis footprint. Renderer reports supply selected placement, available regions, occupied envelopes, candidate attempts, and warnings where available. Quantitative size keys are checked against the exact supplied point-area mapping.", "",
                  "Area/length ratios are descriptive diagnostics. A high ratio alone does not fail a panel; failures concern collisions, clipping, missing decoding, changes to values or quantitative areas, font/canvas changes, ignored explicit placement, or an impossible footprint reported as ready.", "",
                  "Inspect `visual-review.md` and original PNGs for visual findings. `contact-sheet.png` is a documentation aid rendered at a common physical scale; it does not establish 8 pt readability by itself.", ""])
    lines.extend(["| Case | Occupied legend boxes, before → after (mm²) | Plot, before → after (mm²) |", "| --- | --- | --- |"])
    for result in results:
        metrics = result["compactness_diagnostics"]
        if "before" in metrics and "after" in metrics:
            b, a = metrics["before"], metrics["after"]
            lines.append(f"| {result['id']} | {b['total_occupied_legend_bbox_area_mm2']:.1f} → {a['total_occupied_legend_bbox_area_mm2']:.1f} | {b['plot_area_mm2']:.1f} → {a['plot_area_mm2']:.1f} |")
    lines.extend(["", "These occupied boxes include decoding text; smaller is useful only when all required labels and quantitative key sizes remain readable. Manual placement and the intentionally impossible case are behavior checks, not evidence of automatic compaction.", ""])
    for result in results:
        if result["failures"]:
            lines.extend([f"## {result['id']}", "", *[f"- {failure}" for failure in result["failures"]], ""])
    (OUT / "results.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--only", nargs="*", help="Optional exact case IDs; reports include these cases only")
    parser.add_argument("--skip-before", action="store_true", help="Reuse saved before measurements rather than rerun unchanged baseline")
    parser.add_argument("--renderer", type=Path, default=ROOT / "skills/easyviz/scripts/render.py")
    parser.add_argument("--baseline", type=Path, default=OUT / "baseline/skills/easyviz/scripts/render.py")
    args = parser.parse_args()
    manifest = generate()
    if args.generate_only:
        print(json.dumps({"generated_cases": len(manifest["cases"]), "out": str(OUT)})); return
    current = load_module(args.renderer, "legend_current_renderer")
    baseline = load_module(args.baseline, "legend_baseline_renderer") if args.baseline.exists() else None
    results = []
    cases = [case for case in manifest["cases"] if not args.only or case["id"] in args.only]
    for case in cases:
        saved = OUT / "cases" / case["id"] / "before" / "measured-geometry.json"
        before = json.loads(saved.read_text()) if args.skip_before and saved.exists() else run_case(baseline, case, "before") if baseline else None
        if before:
            add_reserved_bands(before.get("geometry", {}))
            write_json(saved, before)
        after = run_case(current, case, "after")
        result = evaluate(case, before, after)
        results.append(result)
        print(json.dumps({"case": case["id"], "status": result["status"], "failures": result["failures"]}), flush=True)
    report(manifest, results)
    contact_sheet(cases)
    raise SystemExit(1 if any(result["status"] == "failed" for result in results) else 0)


if __name__ == "__main__":
    main()
