"""Reusable categorical frames and supplied-tree geometry for scientific panels.

All positions are final-canvas millimeters. Row 0 is at the top and column 0
at the left. This module places axes; it performs no clustering or analysis.
"""
from __future__ import annotations

import math

import numpy as np
from matplotlib.transforms import Bbox


def literal_order(values, name):
    if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f"{name} must be a nonempty list of literal nonempty string IDs")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} IDs must be unique")
    return tuple(values)


def supplied_linkage(payload, order):
    """Validate a complete ordered binary tree and return exact branch vertices.

Indices 0..n-1 refer to leaf_ids. Merge i receives index n+i. Heights are
nonnegative and each parent must be at least as high as its children; the
order of independent merges need not have ascending heights. Inversions are
rejected. No child swaps, leaf reordering, height rescaling or repair occurs.
"""
    if not isinstance(payload, dict) or set(payload) != {"leaf_ids", "linkage"}:
        raise ValueError("Supplied linkage must contain only leaf_ids and linkage")
    leaves = literal_order(payload["leaf_ids"], "leaf_ids")
    displayed = literal_order(list(order), "displayed leaf order")
    if set(leaves) != set(displayed):
        raise ValueError("Linkage leaf IDs must cover the displayed IDs exactly")
    n = len(leaves)
    rows = payload["linkage"]
    if not isinstance(rows, list) or len(rows) != n - 1:
        raise ValueError("Linkage needs exactly leaf_count - 1 merge rows")
    nodes = {i: {"leaves": [leaf], "height": 0., "position": float(displayed.index(leaf))} for i, leaf in enumerate(leaves)}
    consumed, branches = set(), []
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("Each linkage row must be [left,right,height,count]")
        left, right, height, count = row
        for name, value in (("left child", left), ("right child", right), ("leaf count", count)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Linkage {name} must be a JSON integer")
        if left == right or not (0 <= left < n + i and 0 <= right < n + i):
            raise ValueError("Linkage children must be distinct existing nodes")
        if left in consumed or right in consumed:
            raise ValueError("Every non-root linkage node may be used only once")
        if not isinstance(height, (float, int)) or isinstance(height, bool) or not math.isfinite(height) or height < 0:
            raise ValueError("Linkage heights must be finite nonnegative JSON numbers")
        a, b = nodes[left], nodes[right]
        if height < max(a["height"], b["height"]):
            raise ValueError("Linkage parent height must not be below a child height")
        descendants = a["leaves"] + b["leaves"]
        if count != len(descendants):
            raise ValueError("Linkage count must equal the recursive leaf count")
        consumed.update((left, right))
        vertices = [[a["position"], a["height"]], [a["position"], float(height)],
                    [b["position"], float(height)], [b["position"], b["height"]]]
        branches.append({"node": n + i, "leaf_ids": descendants, "vertices": vertices,
                         "height": float(height), "count": count})
        nodes[n + i] = {"leaves": descendants, "height": float(height),
                        "position": (a["position"] + b["position"]) / 2}
    root = nodes[2 * n - 2]
    if tuple(root["leaves"]) != displayed:
        raise ValueError("Linkage left-to-right leaf traversal must equal displayed order exactly")
    if consumed != set(range(2 * n - 2)):
        raise ValueError("Linkage must be one complete tree with exactly one root")
    return {"leaf_ids": list(leaves), "display_order": list(displayed), "branches": branches,
            "maximum_height": root["height"], "clustering_performed": False}


class AlignedFrame:
    """Move a matrix and arbitrary aligned right/top tracks as one geometry.

    Add tracks in nearest-to-farthest order. Each has its own value axis, while
    its categorical dimension shares the matrix's span, limits and centers.
    Custom scripts can draw any artists on returned axes and call reshape()
    during their own measured layout. Other placements can use add_aligned().
    """
    def __init__(self, fig, rows, columns, rect_mm, *, gap_mm=2):
        self.fig = fig
        self.rows = literal_order(list(rows), "rows")
        self.columns = literal_order(list(columns), "columns")
        self.gap_mm = float(gap_mm)
        if not math.isfinite(self.gap_mm) or self.gap_mm < 0:
            raise ValueError("Track gap must be finite and nonnegative")
        self.main = fig.add_axes([.1, .1, .5, .5])
        self.axes = {"matrix": self.main}
        self.tracks = []
        self.rect_mm = None
        self.reshape(rect_mm)
        self.main.set_xlim(-.5, len(self.columns) - .5)
        self.main.set_ylim(len(self.rows) - .5, -.5)

    def add_track(self, key, dimension, thickness_mm):
        """Return a track sharing columns (top) or rows (right)."""
        if key in self.axes or dimension not in ("row", "column"):
            raise ValueError("Track key must be unique and dimension row or column")
        thickness = float(thickness_mm)
        if not math.isfinite(thickness) or thickness <= 0:
            raise ValueError("Track thickness must be finite and positive")
        ax = self.fig.add_axes([.1, .1, .1, .1])
        self.axes[key] = ax
        self.tracks.append({"key": key, "dimension": dimension, "thickness_mm": thickness})
        self.reshape(self.rect_mm)
        return ax

    def add_aligned(self, key, dimension, rect_mm):
        """Place a custom track at an explicit rect with an exact shared span."""
        if key in self.axes or dimension not in ("row", "column"):
            raise ValueError("Track key must be unique and dimension row or column")
        rect = list(map(float, rect_mm))
        self._fraction(rect)  # validate before accessing dimension indices
        indices = (0, 2) if dimension == "column" else (1, 3)
        if any(abs(rect[i] - self.rect_mm[i]) > 1e-9 for i in indices):
            raise ValueError("Custom aligned track must have the exact matrix span")
        ax = self.fig.add_axes(self._fraction(rect))
        self.axes[key] = ax
        self.tracks.append({"key": key, "dimension": dimension, "rect_mm": rect})
        self._domain(ax, dimension)
        return ax

    def _fraction(self, rect):
        if len(rect) != 4 or not np.isfinite(rect).all() or min(rect[2:]) <= 0:
            raise ValueError("Matrix/track rect must be [left,bottom,positive width,positive height]")
        width, height = self.fig.get_size_inches() * 25.4
        return [rect[0] / width, rect[1] / height, rect[2] / width, rect[3] / height]

    def _domain(self, ax, dimension):
        if dimension == "column":
            ax.set_xlim(-.5, len(self.columns) - .5)
        else:
            ax.set_ylim(len(self.rows) - .5, -.5)

    def additions_mm(self):
        return {dimension: sum(t["thickness_mm"] + self.gap_mm for t in self.tracks
                               if t["dimension"] == dimension and "thickness_mm" in t)
                for dimension in ("row", "column")}

    def reshape(self, rect_mm):
        rect = list(map(float, rect_mm))
        self.main.set_position(self._fraction(rect))
        self.rect_mm = rect
        x, y, width, height = rect
        right, top = x + width, y + height
        for track in self.tracks:
            dimension = track["dimension"]
            if "rect_mm" in track:
                placed = list(track["rect_mm"])
                if dimension == "row": placed[1], placed[3] = y, height
                else: placed[0], placed[2] = x, width
            else:
                thickness = track["thickness_mm"]
                if dimension == "row":
                    placed = [right + self.gap_mm, y, thickness, height]
                    right += self.gap_mm + thickness
                else:
                    placed = [x, top + self.gap_mm, width, thickness]
                    top += self.gap_mm + thickness
            self.axes[track["key"]].set_position(self._fraction(placed))
            self._domain(self.axes[track["key"]], dimension)

    def body_bbox(self):
        return Bbox.union([ax.get_window_extent() for ax in self.axes.values()])

    def tight_bbox(self):
        renderer = self.fig.canvas.get_renderer()
        return Bbox.union([ax.get_tightbbox(renderer) for ax in self.axes.values()])

    def audit(self, tolerance_mm=.01):
        """Check rendered spans and every transformed categorical center."""
        self.fig.canvas.draw()
        matrix = self.main.get_window_extent()
        factor = 25.4 / self.fig.dpi
        issues, checked = [], []
        if not self.main.get_visible() or self.main not in self.fig.axes:
            issues.append({"code": "matrix_axes_absent_or_hidden"})
        expected_limits = [-.5, len(self.columns) - .5, len(self.rows) - .5, -.5]
        limits = list(self.main.get_xlim()) + list(self.main.get_ylim())
        if self.main.get_xscale() != "linear" or self.main.get_yscale() != "linear" or not np.allclose(limits, expected_limits, rtol=0, atol=1e-12):
            issues.append({"code": "matrix_category_domain_mismatch"})
        actual_rect = [matrix.x0 * factor, matrix.y0 * factor, matrix.width * factor, matrix.height * factor]
        if not np.allclose(actual_rect, self.rect_mm, atol=tolerance_mm, rtol=0):
            issues.append({"code": "matrix_rendered_rect_mismatch", "actual_mm": actual_rect, "requested_mm": list(self.rect_mm)})
        for track in self.tracks:
            ax, dimension = self.axes[track["key"]], track["dimension"]
            if not ax.get_visible() or ax not in self.fig.axes:
                issues.append({"code": "aligned_track_axes_absent_or_hidden", "track": track["key"]})
            box = ax.get_window_extent()
            columns = dimension == "column"
            actual_limits = list(ax.get_xlim() if columns else ax.get_ylim())
            expected_limits = [-.5, len(self.columns) - .5] if columns else [len(self.rows) - .5, -.5]
            if (ax.get_xscale() if columns else ax.get_yscale()) != "linear" or not np.allclose(actual_limits, expected_limits, rtol=0, atol=1e-12):
                issues.append({"code": "aligned_track_category_domain_mismatch", "track": track["key"]})
            span = [box.x0, box.width] if columns else [box.y0, box.height]
            expected_span = [matrix.x0, matrix.width] if columns else [matrix.y0, matrix.height]
            ids = self.columns if columns else self.rows
            positions = np.arange(len(ids), dtype=float)
            points = np.column_stack((positions, np.zeros(len(ids)))) if columns else np.column_stack((np.zeros(len(ids)), positions))
            index = 0 if columns else 1
            actual = ax.transData.transform(points)[:, index]
            expected = self.main.transData.transform(points)[:, index]
            discrepancy = max(np.max(np.abs(np.asarray(span) - expected_span)), np.max(np.abs(actual - expected))) * factor
            if discrepancy > tolerance_mm:
                issues.append({"code": "aligned_track_geometry_mismatch", "track": track["key"], "maximum_difference_mm": float(discrepancy)})
            checked.append({"track": track["key"], "dimension": dimension, "literal_ids": list(ids), "maximum_difference_mm": float(discrepancy)})
        return {"status": "pass" if not issues else "needs_revision", "issues": issues,
                "tracks": checked, "tolerance_mm": tolerance_mm,
                "coordinate_rule": "column 0 left; row 0 top; integer category centers and half-integer cell boundaries"}
