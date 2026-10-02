"""Measure heatmap value labels in their own cells without changing the figure.

Register labels as ``{"text": Text, "row": int, "column": int}`` records in
``fig._easyviz_cell_annotations``, or pass the records explicitly. Measurements
use the rendered font and transformed cell corners, including inverted axes.
The adjustable padding is a readability aid, not a journal requirement.
"""
from __future__ import annotations

import math

from matplotlib.text import Text
from matplotlib.transforms import Bbox


def _bbox_mm(box, factor):
    return [float(value * factor) for value in (box.x0, box.y0, box.width, box.height)]


def _records(fig, ax, artists):
    if artists is not None:
        return list(artists)
    registered = getattr(fig, "_easyviz_cell_annotations", None)
    if registered is not None:
        return list(registered)
    # A fallback for an existing plain imshow heatmap. Other annotations must
    # not be mistaken for cell values merely because they belong to the axes.
    records = []
    for artist in ax.texts:
        if artist.get_ha() != "center" or artist.get_va() != "center" or artist.get_transform() != ax.transData:
            continue
        x, y = artist.get_position()
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            continue
        if all(math.isfinite(value) and value.is_integer() for value in (x, y)):
            records.append({"text": artist, "row": int(y), "column": int(x)})
    return records


def check_heatmap_annotations(fig, ax, artists=None, *, padding_mm=.2):
    """Return JSON-safe cell overflow and label collision measurements.

    ``row`` and ``column`` are zero-based cell coordinates, as for the default
    imshow extent. Each cell spans column +/- .5 and row +/- .5 in data space.
    Explicit records are preferred when a heatmap contains other centered text.
    A failed review never hides values, shrinks fonts, or enlarges the canvas.
    """
    padding_mm = float(padding_mm)
    if not math.isfinite(padding_mm) or padding_mm < 0:
        raise ValueError("padding_mm must be finite and nonnegative")
    fig.canvas.draw()
    painter = fig.canvas.get_renderer()
    factor = 25.4 / fig.dpi
    padding_px = padding_mm / factor
    records = _records(fig, ax, artists)
    measured, issues = [], []
    for record in records:
        artist, row, column = record["text"], record["row"], record["column"]
        if not isinstance(artist, Text) or artist.axes is not ax:
            raise ValueError("Each registered text must be a Text artist on the reviewed axes")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (row, column)):
            raise ValueError("Registered row and column must be zero-based integers")
        if not artist.get_visible() or not artist.get_text().strip():
            continue
        corners = ax.transData.transform([[column - .5, row - .5], [column + .5, row + .5]])
        left, right = sorted(float(point[0]) for point in corners)
        bottom, top = sorted(float(point[1]) for point in corners)
        cell = Bbox.from_extents(left, bottom, right, top)
        text = artist.get_window_extent(painter)
        overflow = {
            "left": max(0., left + padding_px - text.x0),
            "right": max(0., text.x1 - right + padding_px),
            "bottom": max(0., bottom + padding_px - text.y0),
            "top": max(0., text.y1 - top + padding_px),
        }
        entry = {
            "row": row, "column": column, "text": artist.get_text(),
            "text_bbox_mm": _bbox_mm(text, factor), "cell_bbox_mm": _bbox_mm(cell, factor),
            "required_cell_width_mm": float(text.width * factor + 2 * padding_mm),
            "required_cell_height_mm": float(text.height * factor + 2 * padding_mm),
        }
        measured.append((text, entry))
        if any(value > .01 for value in overflow.values()):
            issues.append({"code": "cell_annotation_outside_cell", **entry,
                           "overflow_mm": {edge: float(value * factor) for edge, value in overflow.items()}})
    # Sweep in x to avoid comparing every pair on ordinary sparse cell grids.
    ordered = sorted(measured, key=lambda item: item[0].x0)
    overlaps = []
    for i, (a, first) in enumerate(ordered):
        for j in range(i + 1, len(ordered)):
            b, second = ordered[j]
            if b.x0 >= a.x1 - .01:
                break
            width = min(a.x1, b.x1) - max(a.x0, b.x0)
            height = min(a.y1, b.y1) - max(a.y0, b.y0)
            if width > .01 and height > .01:
                overlap = {
                    "code": "cell_annotations_overlap",
                    "cells": [{key: entry[key] for key in ("row", "column", "text", "text_bbox_mm", "cell_bbox_mm")}
                              for entry in (first, second)],
                    "intersection_mm": [float(width * factor), float(height * factor)],
                }
                overlaps.append(overlap)
    issues.extend(overlaps)
    return {
        "status": "pass" if not issues else "needs_revision",
        "registered_count": len(records), "checked_count": len(measured),
        "padding_mm": padding_mm, "issues": issues,
        "overflow_count": sum(issue["code"] == "cell_annotation_outside_cell" for issue in issues),
        "overlap_pair_count": len(overlaps),
        "minimum_sufficient_cell_dimensions_mm": {
            "width": max((entry["required_cell_width_mm"] for _, entry in measured), default=0.),
            "height": max((entry["required_cell_height_mm"] for _, entry in measured), default=0.),
        },
        "cells": [entry for _, entry in measured],
        "note": "Rendered text envelopes must fit their cells with the configured padding. Cell dimensions are a measured fit requirement, not a publication standard. No figure settings or data are changed.",
    }
