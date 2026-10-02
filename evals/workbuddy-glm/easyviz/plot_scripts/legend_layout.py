"""Measured, bounded legend placement in physical units, without font shrinking.

Coordinates named *_mm are [left, bottom, width, height] in canvas millimeters;
anchor_mm is [x, y] in the same lower-left coordinate system. This helper uses no
EasyViz catalogs and may be vendored beside a standalone plotting recipe.
"""
from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import Affine2D, Bbox, IdentityTransform
import numpy as np

PT_PER_MM = 72 / 25.4
CIRCLE_AREA_PER_SIZE_PARAMETER = math.pi / 4
DEFAULTS = {
    "key_width_mm": 1.5, "key_height_mm": 1.5, "handletext_gap_mm": .7,
    "row_gap_mm": .6, "column_gap_mm": 2., "borderpad_mm": .2,
    "gap_mm": 2., "canvas_padding_mm": 1.,
}
# These are adjustable review prompts, never journal rules or fit conditions.
REVIEW_THRESHOLDS = {"area_fraction_of_plot": .20, "area_fraction_of_canvas": .12, "available_region_fraction": .85}


def _positive(value, name, zero=False):
    value = float(value)
    if not math.isfinite(value) or value < 0 or (value == 0 and not zero):
        raise ValueError(f"{name} must be finite and {'nonnegative' if zero else 'positive'}")
    return value


def _bbox_mm(fig, box):
    factor = 25.4 / fig.dpi
    return [float(v * factor) for v in (box.x0, box.y0, box.width, box.height)]


def _from_mm(fig, values):
    if len(values) != 4 or not np.isfinite(values).all() or values[2] <= 0 or values[3] <= 0:
        raise ValueError("bbox_mm/rect_mm must be finite [left,bottom,positive width,positive height]")
    factor = fig.dpi / 25.4
    return Bbox.from_bounds(*(float(v) * factor for v in values))


def _intersects(a, b, tolerance=.1):
    return min(a.x1, b.x1) - max(a.x0, b.x0) > tolerance and min(a.y1, b.y1) - max(a.y0, b.y0) > tolerance


def _contains(outer, inner, tolerance=.1):
    return inner.x0 >= outer.x0 - tolerance and inner.y0 >= outer.y0 - tolerance and inner.x1 <= outer.x1 + tolerance and inner.y1 <= outer.y1 + tolerance


def measure_bbox(fig, bbox, main_plot_bbox_mm, reserved_band_mm=None, *, available_region_mm=None):
    """Geometry diagnostics for any manually drawn legend, including labels/title.

    Pass an actual display-coordinate Bbox (e.g. union of legend artists). This
    function does not infer that a large ratio is scientifically inappropriate.
    An available region is free space outside the plot, not a reserved band.
    Supply reserved_band_mm only for an explicitly allocated legend region.
    """
    plot = _from_mm(fig, main_plot_bbox_mm)
    canvas = fig.bbox
    result = {
        "bbox_mm": _bbox_mm(fig, bbox), "plot_bbox_mm": list(main_plot_bbox_mm),
        "canvas_mm": [float(v * 25.4) for v in fig.get_size_inches()],
        "area_fraction_of_plot": float(bbox.width * bbox.height / (plot.width * plot.height)),
        "width_fraction_of_plot": float(bbox.width / plot.width),
        "height_fraction_of_plot": float(bbox.height / plot.height),
        "area_fraction_of_canvas": float(bbox.width * bbox.height / (canvas.width * canvas.height)),
        "reserved_band_fraction": None, "reserved_band_mm": reserved_band_mm,
        "available_region_fraction": None, "available_region_mm": available_region_mm,
    }
    if reserved_band_mm is not None and reserved_band_mm[2] > 0 and reserved_band_mm[3] > 0:
        band = _from_mm(fig, reserved_band_mm)
        result["reserved_band_fraction"] = float(bbox.width * bbox.height / (band.width * band.height))
    if available_region_mm is not None and available_region_mm[2] > 0 and available_region_mm[3] > 0:
        band = _from_mm(fig, available_region_mm)
        result["available_region_fraction"] = float(bbox.width * bbox.height / (band.width * band.height))
    return result


def _union_area(boxes):
    """Area of rectangle union, not the area of its enclosing rectangle."""
    xs = sorted({v for box in boxes for v in (box.x0, box.x1)})
    total = 0.
    for left, right in zip(xs, xs[1:]):
        spans = sorted((box.y0, box.y1) for box in boxes if box.x0 < right and box.x1 > left)
        low = high = None
        height = 0.
        for bottom, top in spans:
            if high is None or bottom > high:
                if high is not None: height += high - low
                low, high = bottom, top
            else:
                high = max(high, top)
        if high is not None: height += high - low
        total += (right - left) * height
    return float(total)


class LegendLayout:
    """Register categorical/size/color legends, then measure bounded placements."""

    def __init__(self, fig, ax, typography, config=None, main_plot_bbox_mm=None):
        self.fig, self.ax, self.typography = fig, ax, typography
        self.config = config or {}
        if not isinstance(self.config, dict):
            raise ValueError("legends must be an object")
        allowed = {"categorical", "size", "colorbar", "review_thresholds", "main_plot_bbox_mm"}
        if set(self.config) - allowed:
            raise ValueError(f"Unknown legends settings: {sorted(set(self.config) - allowed)}")
        self.override = main_plot_bbox_mm or self.config.get("main_plot_bbox_mm")
        self.thresholds = {**REVIEW_THRESHOLDS, **self.config.get("review_thresholds", {})}
        self.requests, self.entries = [], []
        self.report = {"status": "pending", "legends": [], "issues": [], "warnings": []}

    def add_categorical(self, labels, colors, shape="patch", title=None, edgecolor="none", linewidth_pt=0):
        if len(labels) != len(colors) or not labels or shape not in ("patch", "marker"):
            raise ValueError("Categorical legend needs matching labels/colors and patch or marker shape")
        self.requests.append({"kind": "categorical", "labels": list(map(str, labels)), "colors": list(colors), "shape": shape, "title": title, "edgecolor": edgecolor, "linewidth_pt": linewidth_pt})

    def add_size(self, values, areas_pt2, title=None, color="#777777", edgecolor="none", linewidth_pt=0, *, area_semantics="matplotlib_size_parameter"):
        """Register circular keys with an explicit physical-size interpretation.

        Legacy callers retain their raw Matplotlib ``s`` parameters. New callers
        can pass true circle fill areas, excluding stroke, by selecting
        ``geometric_circle_area``. Both quantities are recorded separately.
        """
        if len(values) != len(areas_pt2) or not values or not np.isfinite(areas_pt2).all() or min(areas_pt2) <= 0:
            raise ValueError("Size legend needs matching values and positive finite marker areas")
        if area_semantics not in ("matplotlib_size_parameter", "geometric_circle_area"):
            raise ValueError("Size legend area_semantics must be matplotlib_size_parameter or geometric_circle_area")
        supplied = np.asarray(areas_pt2, dtype=float)
        parameters = supplied / CIRCLE_AREA_PER_SIZE_PARAMETER if area_semantics == "geometric_circle_area" else supplied
        geometric = supplied if area_semantics == "geometric_circle_area" else supplied * CIRCLE_AREA_PER_SIZE_PARAMETER
        self.requests.append({"kind": "size", "labels": [f"{float(v):g}" for v in values], "values": list(map(float, values)), "areas_pt2": geometric.tolist(), "marker_size_parameters_pt2": parameters.tolist(), "area_semantics": area_semantics, "title": title, "color": color, "edgecolor": edgecolor, "linewidth_pt": linewidth_pt})

    def add_symbols(self, labels, markers, color="#666666", linewidth_pt=.6):
        """Decode nonquantitative data-state symbols without changing dot areas."""
        if len(labels) != len(markers) or not labels or any(m not in ("x", "+", "_", "|") for m in markers):
            raise ValueError("State symbols need matching labels and supported markers")
        self.requests.append({"kind": "categorical", "labels": list(map(str, labels)), "colors": [color] * len(labels), "shape": "symbols", "markers": list(markers), "title": None, "edgecolor": color, "linewidth_pt": linewidth_pt})

    def add_colorbar(self, mappable, label):
        self.requests.append({"kind": "colorbar", "mappable": mappable, "label": label})

    def _plot(self):
        return _from_mm(self.fig, self.override) if self.override is not None else self.ax.get_window_extent()

    def _tight_plot(self):
        return self._plot() if self.override is not None else self.ax.get_tightbbox(self.fig.canvas.get_renderer())

    def _settings(self, kind):
        supplied = self.config.get(kind, {})
        if not isinstance(supplied, dict):
            raise ValueError(f"legends.{kind} must be an object")
        shared = {"position", "gap_mm", "canvas_padding_mm", "allow_plot_overlap"}
        keys = {"ncol", "anchor_mm", "loc", "handletext_gap_mm", "row_gap_mm", "column_gap_mm", "borderpad_mm", "title"}
        if kind == "categorical": keys |= {"key_width_mm", "key_height_mm", "edgecolor", "linewidth_pt"}
        if kind == "size": keys |= {"color", "edgecolor", "linewidth_pt"}
        if kind == "colorbar": keys = {"orientation", "rect_mm", "length_mm", "thickness_mm", "ticks", "label", "label_position"}
        unknown = set(supplied) - shared - keys
        if unknown:
            raise ValueError(f"Unknown {kind} legend settings: {sorted(unknown)}")
        chosen = {**DEFAULTS, **supplied}
        for key in DEFAULTS:
            chosen[key] = _positive(chosen[key], key, zero=key not in ("key_width_mm", "key_height_mm"))
        chosen["position"] = supplied.get("position", "auto")
        if chosen["position"] not in ("auto", "right", "top", "bottom", "manual"):
            raise ValueError("Legend position must be auto, right, top, bottom, or manual")
        if "ncol" in supplied and (not isinstance(supplied["ncol"], int) or supplied["ncol"] < 1):
            raise ValueError("Legend ncol must be a positive integer")
        return chosen, supplied

    def _band(self, position, cfg):
        tight, canvas = self._tight_plot(), self.fig.bbox
        gap, pad = cfg["gap_mm"] * self.fig.dpi / 25.4, cfg["canvas_padding_mm"] * self.fig.dpi / 25.4
        if position == "right": bounds = (tight.x1 + gap, pad, canvas.x1 - pad, canvas.y1 - pad)
        elif position == "top": bounds = (pad, tight.y1 + gap, canvas.x1 - pad, canvas.y1 - pad)
        elif position == "bottom": bounds = (pad, pad, canvas.x1 - pad, tight.y0 - gap)
        else: bounds = (pad, pad, canvas.x1 - pad, canvas.y1 - pad)
        return Bbox.from_extents(*bounds)

    def _anchor(self, position, cfg):
        plot, band = self._plot(), self._band(position, cfg)
        gap = cfg["gap_mm"] * self.fig.dpi / 25.4
        if position == "manual":
            value = cfg.get("anchor_mm")
            if value is None or len(value) != 2 or not np.isfinite(value).all():
                raise ValueError("Manual categorical/size legend needs finite anchor_mm [x,y]")
            xy = np.array(value) * self.fig.dpi / 25.4
            return xy, cfg.get("loc", "upper left")
        if position == "right":
            y = plot.y1
            for entry in self.entries:
                box = self._bounds(entry)
                if box.x0 >= plot.x1:
                    y = min(y, box.y0 - gap)
            return np.array([band.x0, y]), "upper left"
        if position == "top": return np.array([(plot.x0 + plot.x1) / 2, band.y0]), "lower center"
        return np.array([(plot.x0 + plot.x1) / 2, band.y1]), "upper center"

    def _categorical_or_size(self, request, cfg, position, ncol):
        kind = request["kind"]
        font_pt = self.typography["legend"]
        font_mm = font_pt / PT_PER_MM
        if kind == "categorical":
            edge = cfg.get("edgecolor", request["edgecolor"])
            stroke = _positive(cfg.get("linewidth_pt", request["linewidth_pt"]), "linewidth_pt", zero=True)
            if request["shape"] == "patch":
                handles = [Patch(facecolor=c, edgecolor=edge, linewidth=stroke) for c in request["colors"]]
            elif request["shape"] == "symbols":
                handles = [Line2D([], [], linestyle="none", marker=m, color=c, markeredgecolor=c, markeredgewidth=request["linewidth_pt"], markersize=cfg["key_height_mm"] * PT_PER_MM) for m, c in zip(request["markers"], request["colors"])]
            else:
                handles = [Line2D([], [], linestyle="none", marker="o", markerfacecolor=c, markeredgecolor=edge, markeredgewidth=stroke, markersize=cfg["key_height_mm"] * PT_PER_MM) for c in request["colors"]]
            key_w, key_h = cfg["key_width_mm"], cfg["key_height_mm"]
            if request["shape"] in ("marker", "symbols"):
                key_h += stroke / PT_PER_MM
                key_w = max(key_w, key_h)
        else:
            # Markers have display-space paths plus a separate offset transform.
            # An explicitly set identity transform is essential: otherwise the
            # legend DrawingArea assigns its scale/translation to the path too,
            # displacing keys and changing their size at PDF/PNG export DPI.
            handles = [PathCollection([plt.matplotlib.markers.MarkerStyle("o").get_path().transformed(plt.matplotlib.markers.MarkerStyle("o").get_transform())], sizes=[parameter], transform=IdentityTransform(), facecolors=cfg.get("color", request["color"]), edgecolors=cfg.get("edgecolor", request["edgecolor"]), linewidths=cfg.get("linewidth_pt", request["linewidth_pt"])) for parameter in request["marker_size_parameters_pt2"]]
            # The largest quantitative key sets the row box. Its area is unchanged.
            diameter = math.sqrt(max(request["marker_size_parameters_pt2"])) / PT_PER_MM
            key_w = key_h = max(diameter, 1.5)
        anchor, loc = self._anchor(position, cfg)
        # Matplotlib's legend row box subtracts a font-relative descent. Undo
        # that adjustment so handleheight denotes the actual requested height.
        handle_height = (key_h / font_mm - .245) / .65
        legend = self.fig.legend(handles, request["labels"], title=cfg.get("title", request.get("title")), fontsize=font_pt, title_fontsize=font_pt, loc=loc, bbox_to_anchor=tuple(anchor / np.array([self.fig.bbox.width, self.fig.bbox.height])), bbox_transform=self.fig.transFigure, ncol=ncol, frameon=False, borderaxespad=0, borderpad=cfg["borderpad_mm"] / font_mm, handlelength=key_w / font_mm, handleheight=handle_height, handletextpad=cfg["handletext_gap_mm"] / font_mm, labelspacing=cfg["row_gap_mm"] / font_mm, columnspacing=cfg["column_gap_mm"] / font_mm, markerscale=1, scatterpoints=1, scatteryoffsets=[.5])
        chosen = {**cfg, "position": position, "ncol": ncol, "loc": loc, "anchor_mm": (anchor * 25.4 / self.fig.dpi).tolist(), "font_size_pt": font_pt, "effective_key_width_mm": key_w, "effective_key_height_mm": key_h}
        entry = {"kind": kind, "artist": legend, "request": request, "chosen_settings": chosen}
        if kind == "size":
            entry.update(marker_areas_pt2=request["areas_pt2"], marker_size_parameters_pt2=request["marker_size_parameters_pt2"], area_semantics=request["area_semantics"])
        return entry

    def _colorbar(self, request, cfg, position, length):
        plot, band = self._plot(), self._band(position, cfg)
        px = self.fig.dpi / 25.4
        orientation = cfg.get("orientation", "vertical" if position == "right" else "horizontal")
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("Colorbar orientation must be vertical or horizontal")
        thickness = _positive(cfg.get("thickness_mm", 2), "thickness_mm")
        if position == "manual":
            if "rect_mm" not in cfg:
                raise ValueError("Manual colorbar needs rect_mm [left,bottom,width,height]")
            box = _from_mm(self.fig, cfg["rect_mm"])
            orientation = cfg.get("orientation", "vertical" if box.height >= box.width else "horizontal")
        else:
            w, h = (thickness * px, length * px) if orientation == "vertical" else (length * px, thickness * px)
            if position == "right": box = Bbox.from_bounds(band.x0, plot.y1 - h, w, h)
            elif position == "top": box = Bbox.from_bounds((plot.x0 + plot.x1 - w) / 2, band.y0, w, h)
            else: box = Bbox.from_bounds((plot.x0 + plot.x1 - w) / 2, band.y1 - h, w, h)
        cax = self.fig.add_axes([box.x0 / self.fig.bbox.width, box.y0 / self.fig.bbox.height, box.width / self.fig.bbox.width, box.height / self.fig.bbox.height])
        norm = request["mappable"].norm
        default_ticks = [float(norm.vmin), float(getattr(norm, "vcenter", (norm.vmin + norm.vmax) / 2)), float(norm.vmax)]
        ticks = cfg.get("ticks", default_ticks)
        if not isinstance(ticks, (list, tuple)) or not ticks or not np.isfinite(ticks).all() or min(ticks) < norm.vmin or max(ticks) > norm.vmax:
            self.fig.delaxes(cax)
            raise ValueError("Colorbar ticks must be finite values within the full mapped range")
        cb = self.fig.colorbar(request["mappable"], cax=cax, orientation=orientation, ticks=ticks)
        if position == "top" and orientation == "horizontal":
            cax.xaxis.set_ticks_position("top"); cax.xaxis.set_label_position("top")
        if "label_position" in cfg:
            allowed = ("top", "bottom") if orientation == "horizontal" else ("left", "right")
            if cfg["label_position"] not in allowed:
                raise ValueError(f"Colorbar label_position must be one of {allowed}")
            (cax.xaxis if orientation == "horizontal" else cax.yaxis).set_label_position(cfg["label_position"])
        cb.set_label(cfg.get("label", request["label"]), fontsize=self.typography["legend"], labelpad=.8 * PT_PER_MM)
        cax.tick_params(labelsize=self.typography["legend"], length=.7 * PT_PER_MM, pad=.6 * PT_PER_MM)
        cb.outline.set_linewidth(.5)
        chosen = {**cfg, "position": position, "orientation": orientation, "rect_mm": _bbox_mm(self.fig, box), "length_mm": max(box.width, box.height) / px, "thickness_mm": min(box.width, box.height) / px, "ticks": list(map(float, ticks)), "font_size_pt": self.typography["legend"]}
        return {"kind": "colorbar", "artist": cax, "colorbar": cb, "request": request, "chosen_settings": chosen, "mapped_range": [float(norm.vmin), float(norm.vmax)]}

    def _bounds(self, entry):
        painter = self.fig.canvas.get_renderer()
        if entry["kind"] == "colorbar": return entry["artist"].get_tightbbox(painter)
        # The layout box alone misses malformed marker transforms. Include the
        # rendered key bounds, using the same path/offset transforms as drawing.
        return Bbox.union([entry["artist"].get_window_extent(painter), *self._key_bounds(entry)])

    def _key_bounds(self, entry):
        if entry["kind"] == "colorbar": return []
        painter, boxes = self.fig.canvas.get_renderer(), []
        for handle in entry["artist"].legend_handles:
            if isinstance(handle, PathCollection):
                paths, matrices = handle.get_paths(), handle.get_transforms()
                offsets = handle.get_offset_transform().transform(handle.get_offsets())
                marker_boxes = []
                for i, offset in enumerate(offsets):
                    scale = Affine2D(matrices[i % len(matrices)]) if len(matrices) else IdentityTransform()
                    marker_boxes.append(paths[i % len(paths)].get_extents(scale + handle.get_transform()).translated(*offset))
                box = Bbox.union(marker_boxes)
                stroke = max(handle.get_linewidths(), default=0) * self.fig.dpi / 72
                box = box.padded(stroke / 2)
            elif isinstance(handle, Line2D) and handle.get_linestyle() in ("None", "none", "", " "):
                # HandlerLine2D retains invisible line endpoints, but marks only
                # markevery=[1]. get_window_extent includes those unpainted ends.
                points = handle.get_path().vertices
                marked = handle.get_markevery()
                if marked is not None: points = points[marked]
                points = handle.get_transform().transform(points)
                radius = (handle.get_markersize() + handle.get_markeredgewidth()) * self.fig.dpi / 144
                box = Bbox.from_extents(*points.min(axis=0), *points.max(axis=0)).padded(radius)
            else:
                box = handle.get_window_extent(painter)
            boxes.append(box)
        return boxes

    def _texts(self, entry):
        if entry["kind"] != "colorbar":
            return [t for t in [entry["artist"].get_title(), *entry["artist"].get_texts()] if t.get_visible() and t.get_text().strip()]
        axes = entry["artist"]
        texts = [axes.xaxis.label, axes.yaxis.label, axes.xaxis.offsetText, axes.yaxis.offsetText]
        for axis in (axes.xaxis, axes.yaxis):
            low, high = sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks():
                if low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                    texts += [tick.label1, tick.label2]
        return [t for t in texts if t.get_visible() and t.get_text().strip()]

    def _inspect(self, entry):
        self.fig.canvas.draw()
        if entry["kind"] == "size":
            # A taller quantitative key changes Matplotlib's row descent. Use
            # actual label centers, rather than a fixed fraction of handleheight,
            # to align symbols optically without changing their area or row box.
            painter = self.fig.canvas.get_renderer()
            for handle, text in zip(entry["artist"].legend_handles, entry["artist"].get_texts()):
                box = text.get_window_extent(painter)
                offsets = np.array(handle.get_offsets(), dtype=float)
                offsets[:, 1] = handle.get_offset_transform().inverted().transform([(box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2])[1]
                handle.set_offsets(offsets)
            self.fig.canvas.draw()
        box, plot, painter = self._bounds(entry), self._plot(), self.fig.canvas.get_renderer()
        cfg, issues = entry["chosen_settings"], []
        band = self._band(cfg["position"], cfg)
        pad = cfg["canvas_padding_mm"] * self.fig.dpi / 25.4
        canvas = Bbox.from_extents(pad, pad, self.fig.bbox.x1 - pad, self.fig.bbox.y1 - pad)
        if not _contains(canvas, box): issues.append("legend_outside_canvas")
        if cfg["position"] != "manual" and not _contains(band, box): issues.append("legend_outside_available_region")
        if not cfg.get("allow_plot_overlap", False) and _intersects(box, self._tight_plot()): issues.append("legend_overlaps_plot_or_axis_labels")
        for other in self.entries:
            if other is not entry and _intersects(box, self._bounds(other)):
                issues.append(f"legend_overlaps_{other['kind']}")
        text_overlaps = []
        texts = self._texts(entry)
        for i, a in enumerate(texts):
            for b in texts[i + 1:]:
                if _intersects(a.get_window_extent(painter), b.get_window_extent(painter)):
                    text_overlaps.append([a.get_text(), b.get_text()])
        if text_overlaps: issues.append("legend_text_overlap")
        keys = self._key_bounds(entry)
        if any(_intersects(key, text.get_window_extent(painter)) for key in keys for text in texts):
            issues.append("legend_key_overlaps_text")
        if any(_intersects(key, other) for i, key in enumerate(keys) for other in keys[i + 1:]):
            issues.append("legend_keys_overlap")
        if entry["kind"] == "size":
            actual = [float(h.get_sizes()[0]) for h in entry["artist"].legend_handles]
            if not np.allclose(actual, entry["marker_size_parameters_pt2"], rtol=0, atol=1e-10): issues.append("quantitative_marker_area_changed")
        geometry = measure_bbox(self.fig, box, _bbox_mm(self.fig, plot), available_region_mm=_bbox_mm(self.fig, band) if band.width > 0 and band.height > 0 else None)
        messages = []
        for key, threshold in self.thresholds.items():
            if key not in REVIEW_THRESHOLDS:
                raise ValueError(f"Unknown legend review threshold: {key}")
            if threshold is not None and geometry[key] is not None and geometry[key] > _positive(threshold, key):
                messages.append(f"Review {key}={geometry[key]:.3f} above adjustable threshold {threshold}; this is not a journal limit.")
        return {"kind": entry["kind"], "chosen_settings": cfg, **geometry, "key_bboxes_mm": [_bbox_mm(self.fig, key) for key in keys], "issues": sorted(set(issues)), "warnings": messages, "text_overlaps": text_overlaps, **({"marker_areas_pt2": entry["marker_areas_pt2"], "marker_size_parameters_pt2": entry["marker_size_parameters_pt2"], "area_semantics": entry["area_semantics"], "fill_area_definition": "Ideal circle geometric fill area in pt², excluding edge stroke; Matplotlib s is squared diameter in pt²."} if entry["kind"] == "size" else {}), **({"mapped_range": entry["mapped_range"]} if entry["kind"] == "colorbar" else {})}

    def _remove(self, entry):
        if entry["kind"] == "colorbar": self.fig.delaxes(entry["artist"])
        else: entry["artist"].remove()

    def layout(self):
        self.fig.canvas.draw()
        for request in sorted(self.requests, key=lambda r: 0 if r["kind"] == "colorbar" else 1):
            kind = request["kind"]
            cfg, supplied = self._settings(kind)
            positions = [cfg["position"]] if cfg["position"] != "auto" else ["right", "top", "bottom"]
            candidates, best = [], None
            for position in positions:
                if kind == "colorbar":
                    side_mm = (self._plot().height if position == "right" else self._plot().width) * 25.4 / self.fig.dpi
                    start = max(18., min(28., .35 * side_mm))
                    variants = [cfg["length_mm"]] if "length_mm" in supplied else list(dict.fromkeys([start, 24., 28.]))
                    if position == "manual": variants = [start]
                else:
                    variants = [cfg["ncol"]] if "ncol" in supplied else list(range(1, min(len(request["labels"]), 4) + 1))
                for variant in variants:
                    entry = self._colorbar(request, cfg, position, _positive(variant, "length_mm")) if kind == "colorbar" else self._categorical_or_size(request, cfg, position, variant)
                    diagnostic = self._inspect(entry)
                    candidates.append({"position": position, "ncol": None if kind == "colorbar" else variant, "length_mm": variant if kind == "colorbar" else None, "bbox_mm": diagnostic["bbox_mm"], "issues": diagnostic["issues"]})
                    # Preserve the declared candidate order among feasible fits.
                    # Smaller guide area is not evidence of a better design:
                    # it can create a dense banner or leave unrelated whitespace.
                    score = (len(diagnostic["issues"]), positions.index(position), variants.index(variant))
                    if best is None or score < best[0]:
                        best = (score, position, variant)
                    self._remove(entry)
            _, position, variant = best
            chosen = self._colorbar(request, cfg, position, variant) if kind == "colorbar" else self._categorical_or_size(request, cfg, position, variant)
            chosen["attempts"] = candidates
            self.entries.append(chosen)
        return self.validate()

    def validate(self):
        self.fig.canvas.draw()
        diagnostics = []
        for entry in self.entries:
            diagnostic = self._inspect(entry)
            diagnostic["attempts"] = entry.get("attempts", [])
            diagnostics.append(diagnostic)
        issues = [f"{d['kind']}: {issue}" for d in diagnostics for issue in d["issues"]]
        boxes = [self._bounds(entry) for entry in self.entries]
        union_area, sum_area = _union_area(boxes), sum(box.width * box.height for box in boxes)
        factor = (25.4 / self.fig.dpi) ** 2
        combined = {"guide_count": len(boxes), "occupied_envelope_union_area_mm2": union_area * factor, "sum_envelope_area_mm2": sum_area * factor, "envelope_overlap_area_mm2": max(0., sum_area - union_area) * factor, "has_envelope_overlap": bool(sum_area - union_area > .1), "area_fraction_of_plot": union_area / (self._plot().width * self._plot().height), "area_fraction_of_canvas": union_area / (self.fig.bbox.width * self.fig.bbox.height), "enclosing_bbox_mm": _bbox_mm(self.fig, Bbox.union(boxes)) if boxes else None, "max_individual_width_mm": max((b.width for b in boxes), default=0) * 25.4 / self.fig.dpi, "max_individual_height_mm": max((b.height for b in boxes), default=0) * 25.4 / self.fig.dpi, "semantics": "Union of complete rectangular guide envelopes, not ink area. The enclosing bbox includes empty gaps and is reported separately. Available regions are not actual reserved layout bands."}
        warnings = [f"{d['kind']}: {warning}" for d in diagnostics for warning in d["warnings"]]
        for key in ("area_fraction_of_plot", "area_fraction_of_canvas"):
            threshold = self.thresholds[key]
            if threshold is not None and combined[key] > threshold:
                warnings.append(f"Combined guides: review {key}={combined[key]:.3f} above adjustable threshold {threshold}; this is not a journal limit.")
        self.report = {"status": "pass" if not issues else "needs_revision", "legends": diagnostics, "combined": combined, "issues": issues, "warnings": warnings, "review_thresholds": self.thresholds, "font_policy": "Preserve configured legend font size; never shrink the canvas or quantitative size keys.", "selection_policy": "Fit first, then declared candidate order; never minimize occupied area as an aesthetic objective. Automatic placement is provisional and needs visual judgment.", "measurement_note": "Legend bbox includes rendered keys, labels and title. Available-region occupancy describes free space outside the plot, not allocated legend space. Ratios and pass status describe technical fit, not design improvement. Check other annotation collisions visually."}
        return self.report
