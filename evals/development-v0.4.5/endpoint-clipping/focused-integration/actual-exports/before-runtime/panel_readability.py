"""Measure rendered mark sizes and strokes without changing a scientific panel.

Custom Create or Reproduce scripts can call ``measure(fig)`` after final layout.
The report is advisory: a small quantitative mark can be scientifically correct.
It never changes data, artist properties, output pixels, or a panel's QA status.
"""
from __future__ import annotations

import math
import re

import numpy as np
from matplotlib import colors as mcolors
from matplotlib.collections import LineCollection, PathCollection, PolyCollection
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.patches import Patch

MM_PER_PT = 25.4 / 72
DEFAULT_THRESHOLDS = {
    "small_point_span_mm": 0.35,
    "low_contrast_ratio": 2.0,
    "thin_stroke_pt": 0.25,
    "large_legend_canvas_fraction": 0.25,
}
_SUPPORTING_ROLES = {"grid", "heatmap-grid", "separator", "metadata-strip", "matrix"}


def _range(values):
    finite = np.asarray(values, dtype=float).reshape(-1)
    finite = finite[np.isfinite(finite)]
    return [float(finite.min()), float(finite.max())] if len(finite) else None


def _rgba(color, alpha=None):
    return np.asarray(mcolors.to_rgba(color, alpha=alpha), dtype=float)


def _over(color, background):
    """The actual artist RGBA already contains its alpha; composite just once."""
    return color[:3] * color[3] + background * (1 - color[3])


def _background(fig, artist):
    canvas = _over(_rgba(fig.get_facecolor()), np.ones(3))
    ax = getattr(artist, "axes", None)
    return _over(_rgba(ax.get_facecolor()), canvas) if ax is not None else canvas


def _contrast(rgb, background):
    def luminance(color):
        linear = np.where(color <= .04045, color / 12.92, ((color + .055) / 1.055) ** 2.4)
        return linear @ np.array([.2126, .7152, .0722])
    first, second = luminance(rgb), float(luminance(background))
    return (np.maximum(first, second) + .05) / (np.minimum(first, second) + .05)


def _cycle(values, count, *, default=0):
    array = np.asarray(values)
    if len(array) == 0:
        return np.full(count, default, dtype=float)
    return array[np.arange(count) % len(array)]


def _path_point_record(artist, fig):
    offsets = np.ma.asarray(artist.get_offsets(), dtype=float)
    if offsets.ndim != 2 or not len(offsets):
        return None
    count = len(offsets)
    mask = np.ma.getmaskarray(offsets).any(axis=1)
    finite = np.isfinite(offsets.filled(np.nan)).all(axis=1) & ~mask
    sizes = _cycle(artist.get_sizes(), count)
    finite &= np.isfinite(sizes) & (sizes >= 0)
    paths = artist.get_paths()
    if not paths:
        return None
    extents = np.asarray([[path.get_extents().width, path.get_extents().height] for path in paths])
    spans = _cycle(extents, count) * np.sqrt(np.maximum(sizes, 0))[:, None] * MM_PER_PT
    faces = _cycle(artist.get_facecolors(), count, default=0)
    edges = _cycle(artist.get_edgecolors(), count, default=0)
    if faces.ndim == 1:
        faces = np.zeros((count, 4))
    if edges.ndim == 1:
        edges = np.zeros((count, 4))
    widths = _cycle(artist.get_linewidths(), count)
    face_visible = faces[:, 3] > 0
    edge_visible = (edges[:, 3] > 0) & (widths > 0)
    positive = finite & (sizes > 0)
    visible = positive & (face_visible | edge_visible)
    background = _background(fig, artist)
    # Both filled marks and outlines can carry contrast. The stronger visible
    # component is recorded, without multiplying Collection.get_alpha() again.
    face_contrast = _contrast(faces[:, :3] * faces[:, 3, None] + background * (1 - faces[:, 3, None]), background)
    edge_contrast = _contrast(edges[:, :3] * edges[:, 3, None] + background * (1 - edges[:, 3, None]), background)
    contrasts = np.maximum(np.where(face_visible, face_contrast, 1), np.where(edge_visible, edge_contrast, 1))
    outer = spans + np.where(edge_visible & positive, widths, 0)[:, None] * MM_PER_PT
    record = {
        "finite_mark_count": int(finite.sum()), "masked_or_nonfinite_count": int((~finite).sum()),
        "zero_size_parameter_count": int((finite & (sizes == 0)).sum()),
        "positive_size_parameter_count": int(positive.sum()),
        "visible_positive_count": int(visible.sum()),
        "positive_without_visible_face_or_edge_count": int((positive & ~visible).sum()),
        "size_parameter_pt2_range": _range(sizes[finite]),
        "positive_marker_bbox_width_mm_range": _range(spans[positive, 0]),
        "positive_marker_bbox_height_mm_range": _range(spans[positive, 1]),
        "positive_outer_span_mm_range": _range(outer[positive].max(axis=1)),
        "visible_component_contrast_ratio_range": _range(contrasts[visible]),
        "edge_width_pt_range": _range(widths[edge_visible & positive]),
    }
    return record, outer.max(axis=1), contrasts, visible


def _line_point_record(artist, fig):
    marker = artist.get_marker()
    if marker in (None, "", " ", "None", "none") or artist.get_markersize() <= 0:
        return None
    positions = np.ma.asarray(artist.get_xydata(), dtype=float)
    finite = np.isfinite(positions.filled(np.nan)).all(axis=1) & ~np.ma.getmaskarray(positions).any(axis=1)
    # A Line2D can deliberately mark every kth observation. Do not count
    # unpainted marker locations as observations that were lost or omitted.
    markevery = artist.get_markevery()
    if markevery is not None:
        return {"marker_measurement": "not_measured", "reason": "Line2D markevery selection requires visual review"}, None, None, None
    shape = MarkerStyle(marker)
    bbox = shape.get_path().transformed(shape.get_transform()).get_extents()
    diameter = float(artist.get_markersize())
    edge_width = float(artist.get_markeredgewidth())
    alpha = artist.get_alpha()
    face = _rgba(artist.get_markerfacecolor(), alpha)
    edge = _rgba(artist.get_markeredgecolor(), alpha)
    background = _background(fig, artist)
    face_visible, edge_visible = face[3] > 0, edge[3] > 0 and edge_width > 0
    contrast = max(float(_contrast(_over(face, background), background)) if face_visible else 1,
                   float(_contrast(_over(edge, background), background)) if edge_visible else 1)
    span = max(bbox.width, bbox.height) * diameter * MM_PER_PT + (edge_width * MM_PER_PT if edge_visible else 0)
    count = int(finite.sum())
    return {
        "finite_mark_count": count, "masked_or_nonfinite_count": int((~finite).sum()),
        "zero_size_parameter_count": 0, "positive_size_parameter_count": count,
        "visible_positive_count": count if face_visible or edge_visible else 0,
        "markersize_pt_range": [diameter, diameter],
        "positive_marker_bbox_width_mm_range": [bbox.width * diameter * MM_PER_PT] * 2,
        "positive_marker_bbox_height_mm_range": [bbox.height * diameter * MM_PER_PT] * 2,
        "positive_outer_span_mm_range": [span, span],
        "visible_component_contrast_ratio_range": [contrast, contrast] if face_visible or edge_visible else None,
        "edge_width_pt_range": [edge_width, edge_width] if edge_visible else None,
    }, np.full(count, span), np.full(count, contrast), np.full(count, face_visible or edge_visible)


def _visible(artist):
    ax = getattr(artist, "axes", None)
    return artist.get_visible() and (ax is None or ax.get_visible())


def _entries(fig):
    entries, seen = [], set()
    for index, item in enumerate(getattr(fig, "_easyviz_elements", [])):
        artist = item.get("_artist")
        if artist is None or id(artist) in seen or not _visible(artist):
            continue
        entries.append((artist, str(item.get("id", f"registered-{index}")), str(item.get("role", "registered")), str(item.get("label", "")), "registered"))
        seen.add(id(artist))
    for index, ax in enumerate(fig.axes):
        if not ax.get_visible():
            continue
        for kind, artists in (("line", ax.lines), ("collection", ax.collections)):
            for number, artist in enumerate(artists):
                if id(artist) in seen or not _visible(artist):
                    continue
                entries.append((artist, f"axes-{index}-{kind}-{number}", f"unregistered-{kind}", str(artist.get_label()), "axes-fallback"))
                seen.add(id(artist))
        for number, legend in enumerate([child for child in ax.get_children() if isinstance(child, Legend)]):
            if id(legend) not in seen and _visible(legend):
                entries.append((legend, f"axes-{index}-legend-{number}", "legend", "Legend", "axes-fallback"))
                seen.add(id(legend))
    for number, legend in enumerate(fig.legends):
        if id(legend) not in seen and _visible(legend):
            entries.append((legend, f"figure-legend-{number}", "legend", "Legend", "figure-fallback"))
            seen.add(id(legend))
    return entries


def _widths(artist, role):
    def drawn_segment(points):
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or len(points) < 2:
            return False
        finite = np.isfinite(points).all(axis=1)
        return bool((finite[:-1] & finite[1:]).any())
    if isinstance(artist, LineCollection):
        rgba = artist.get_colors()
        widths = np.asarray(artist.get_linewidths(), dtype=float)
        if not len(rgba) or not len(widths) or not len(artist.get_segments()):
            return None
        count = len(artist.get_segments())
        visible = (_cycle(rgba, count)[:, 3] > 0) & np.asarray([drawn_segment(segment) for segment in artist.get_segments()])
        return _cycle(widths, count)[visible]
    if isinstance(artist, PolyCollection) and role == "distribution":
        rgba = artist.get_edgecolors()
        widths = np.asarray(artist.get_linewidths(), dtype=float)
        count = len(artist.get_paths())
        if not count or not len(rgba) or not len(widths):
            return None
        return _cycle(widths, count)[_cycle(rgba, count)[:, 3] > 0]
    if isinstance(artist, Line2D):
        if role == "axis-tick":
            return np.asarray([artist.get_markeredgewidth()]) if artist.get_markersize() > 0 else None
        if artist.get_linestyle() not in (None, "", " ", "None", "none") and drawn_segment(artist.get_xydata()):
            return np.asarray([artist.get_linewidth()]) if _rgba(artist.get_color(), artist.get_alpha())[3] > 0 else None
    if isinstance(artist, Patch) and role in {"axis-line", "component", "distribution", "summary", "summary-box", "summary-line"}:
        return np.asarray([artist.get_linewidth()]) if artist.get_edgecolor()[3] > 0 else None
    return None


def measure(fig, *, thresholds=None, max_items=64, max_warnings=32):
    """Return bounded JSON-safe measurements of actual final-layout artists.

    Thresholds are review cues in physical units, not publication standards.
    Role metadata from ``figure_elements.register`` distinguishes supporting
    grids/separators from data strokes. Unregistered custom lines have unknown
    semantics. Zero ``PathCollection.s`` values remain explicit, never enlarged.
    Color contrast uses actual face/edge RGBA over the axes/figure background;
    images, overlaid marks and other nonuniform backgrounds are not modeled.
    """
    limits = dict(DEFAULT_THRESHOLDS)
    if thresholds is not None:
        unknown = set(thresholds) - set(limits)
        if unknown:
            raise ValueError(f"Unknown readability thresholds: {sorted(unknown)}")
        limits.update(thresholds)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0 for value in limits.values()):
        raise ValueError("Readability thresholds must be positive finite numbers")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in (max_items, max_warnings)):
        raise ValueError("Readability report limits must be positive integers")
    fig.canvas.draw()
    painter = fig.canvas.get_renderer()
    records, warnings, roles = [], [], {}
    totals = {"point_artists": 0, "stroke_artists": 0, "legend_artists": 0,
              "finite_marks": 0, "zero_size_parameters": 0, "small_visible_marks": 0,
              "low_contrast_small_marks": 0, "thin_data_stroke_artists": 0}
    canvas_area = float(fig.bbox.width * fig.bbox.height)
    for artist, identity, role, label, provenance in _entries(fig):
        item = {"id": identity, "role": role, "label": label[:160], "artist_type": type(artist).__name__, "mapping": provenance}
        point_result = (_path_point_record(artist, fig) if isinstance(artist, PathCollection)
                        else _line_point_record(artist, fig) if isinstance(artist, Line2D) and role != "axis-tick" else None)
        if point_result:
            points, spans, contrasts, visible = point_result
            item["points"] = points
            totals["point_artists"] += 1
            totals["finite_marks"] += points.get("finite_mark_count", 0)
            totals["zero_size_parameters"] += points.get("zero_size_parameter_count", 0)
            if visible is not None:
                small = visible & (spans < limits["small_point_span_mm"])
                faint = small & (contrasts < limits["low_contrast_ratio"])
                points["small_visible_count"] = int(small.sum())
                points["low_contrast_small_count"] = int(faint.sum())
                totals["small_visible_marks"] += int(small.sum())
                totals["low_contrast_small_marks"] += int(faint.sum())
                if small.any():
                    warnings.append({"id": identity, "role": role, "kind": "small_positive_marks", "count": int(small.sum()),
                                     "message": "Inspect these positive marks at final size. Preserve quantitative size mappings; consider layout or panel size before changing mark area."})
                if faint.any():
                    warnings.append({"id": identity, "role": role, "kind": "low_contrast_small_marks", "count": int(faint.sum()),
                                     "message": "Small marks have low face/edge contrast against the uniform background; inspect color and opacity at final size."})
        widths = _widths(artist, role)
        if widths is not None and len(widths):
            positive_widths = np.asarray(widths)[np.isfinite(widths) & (np.asarray(widths) > 0)]
            item["strokes"] = {"positive_width_pt_range": _range(positive_widths)}
            totals["stroke_artists"] += 1
            if len(positive_widths):
                aggregate = roles.setdefault(role, {"artist_count": 0, "width_pt_range": [float("inf"), 0]})
                aggregate["artist_count"] += 1
                aggregate["width_pt_range"][0] = min(aggregate["width_pt_range"][0], float(positive_widths.min()))
                aggregate["width_pt_range"][1] = max(aggregate["width_pt_range"][1], float(positive_widths.max()))
                # Very light cell seams and separators are purposeful. White
                # stroke layers with unknown roles are also left to visual QA.
                supporting = role in _SUPPORTING_ROLES or bool(re.search(r"(^|[-_ ])(grid|separator)([-_ ]|$)", role))
                if isinstance(artist, LineCollection) and len(artist.get_colors()):
                    supporting |= bool(np.all(artist.get_colors()[:, :3] > .97))
                thin = positive_widths.min() < limits["thin_stroke_pt"]
                if thin and not supporting:
                    totals["thin_data_stroke_artists"] += 1
                    warnings.append({"id": identity, "role": role, "kind": "thin_stroke",
                                     "message": "Inspect this stroke at final size; role and reference styling may justify a thin line."})
        if isinstance(artist, Legend):
            bounds = artist.get_window_extent(painter)
            fraction = float(bounds.width * bounds.height / canvas_area) if canvas_area else 0
            factor = 25.4 / fig.dpi
            item["legend"] = {"bbox_mm": [float(value * factor) for value in (bounds.x0, bounds.y0, bounds.width, bounds.height)],
                              "canvas_area_fraction": fraction,
                              "scope": "Bounding rectangle occupancy, not data overlap or occlusion"}
            totals["legend_artists"] += 1
            if fraction > limits["large_legend_canvas_fraction"]:
                warnings.append({"id": identity, "role": role, "kind": "large_legend_bbox",
                                 "message": "This legend occupies a large canvas fraction. Inspect its placement and information density; no overlap is inferred."})
        if any(name in item for name in ("points", "strokes", "legend")):
            records.append(item)
    evidence = {}
    for attr, key in (("_easyviz_point_layout", "point_layout"), ("_easyviz_auto_layout", "auto_layout")):
        report = getattr(fig, attr, None)
        if isinstance(report, dict):
            evidence[key] = {"status": report.get("status"), "note": "Existing layout evidence is recorded separately in core QA; readability does not rerun or replace it."}
    return {
        "schema_version": 1, "status": "review_suggested" if warnings else "no_advisory_flags",
        "advisory_only": True, "thresholds": limits, "totals": totals,
        "stroke_roles": roles, "artists": records[:max_items], "artist_count": len(records),
        "artists_omitted_from_detail": max(0, len(records) - max_items),
        "warnings": warnings[:max_warnings], "warning_count": len(warnings),
        "warnings_omitted_from_detail": max(0, len(warnings) - max_warnings),
        "layout_evidence": evidence,
        "scope": "Actual visible artist settings after draw; finite unmasked locations are counted without clipping/occlusion inference. PathCollection sizes are Matplotlib size parameters, not universal fill areas; marker path geometry supplies physical bounding spans. Zero size parameters are preserved separately. Contrast is actual face/edge RGBA composited once over a uniform axes/figure background.",
        "not_checked": ["Scientific or statistical validity", "Reference fidelity and missing layers", "Color-vision accessibility or between-category color distinction", "Nonuniform backgrounds, image contrast, mark occlusion or point/label overlap", "Heatmap value normalization, bar fill design, text readability and arbitrary patches", "Line2D markevery marker selection"],
        "policy": "Thresholds are configurable review cues. They do not change artist properties, data, quantitative marker areas, exports, or core QA pass/fail.",
    }
