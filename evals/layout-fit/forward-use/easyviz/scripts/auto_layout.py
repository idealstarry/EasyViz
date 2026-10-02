"""Measure axis text and guide footprints within a fixed physical canvas.

This is a technical fit helper, not a design-quality score. It preserves the
canvas, fonts, labels, data and quantitative marker sizes.
"""
from __future__ import annotations

from copy import deepcopy
import math


def _clear(manager):
    for entry in manager.entries:
        manager._remove(entry)
    manager.entries = []


def _fit_axis(fig, ax, reserve, padding_mm):
    px = fig.dpi / 25.4
    width, height = fig.bbox.width, fig.bbox.height
    available = [padding_mm * px, (padding_mm + reserve["bottom"]) * px,
                 (fig.get_figwidth() * 25.4 - padding_mm - reserve["right"]) * px,
                 (fig.get_figheight() * 25.4 - padding_mm - reserve["top"]) * px]
    # Re-measure after moving the axes: numeric locators can change their ticks.
    for _ in range(8):
        fig.canvas.draw()
        painter = fig.canvas.get_renderer()
        plot = ax.get_window_extent(painter)
        tight = ax.get_tightbbox(painter)
        overhang = [max(0., plot.x0 - tight.x0), max(0., plot.y0 - tight.y0),
                    max(0., tight.x1 - plot.x1), max(0., tight.y1 - plot.y1)]
        bounds = [available[0] + overhang[0], available[1] + overhang[1],
                  available[2] - overhang[2], available[3] - overhang[3]]
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            return False
        position = [bounds[0] / width, bounds[1] / height,
                    (bounds[2] - bounds[0]) / width, (bounds[3] - bounds[1]) / height]
        old = ax.get_position(original=True).bounds
        ax.set_position(position)
        if max(abs(a - b) for a, b in zip(old, position)) * max(width, height) < .25:
            break
    fig.canvas.draw()
    return True


def _reservation(fig, manager, padding_mm):
    reserved = {"right": 0., "bottom": 0., "top": 0.}
    by_side = {edge: [] for edge in reserved}
    for entry in manager.entries:
        side = entry["chosen_settings"]["position"]
        if side in by_side:
            by_side[side].append((manager._bounds(entry), entry["chosen_settings"]["gap_mm"]))
    mm = 25.4 / fig.dpi
    for side, entries in by_side.items():
        if not entries:
            continue
        if side == "right":
            # Right guides stack vertically; the widest envelope sets the band.
            reserved[side] = max(box.width * mm + gap for box, gap in entries)
        else:
            reserved[side] = sum(box.height * mm + gap for box, gap in entries)
        reserved[side] += max(0., max(entry["chosen_settings"]["canvas_padding_mm"]
                                    for entry in manager.entries
                                    if entry["chosen_settings"]["position"] == side) - padding_mm)
    # A vertical colorbar ends at the data-region top, but its endpoint tick
    # extends above that top. Reserve the measured text overhang as well.
    plot = manager._plot()
    if by_side["right"]:
        reserved["top"] += max(0., max(box.y1 for box, _ in by_side["right"]) - plot.y1) * mm
    return reserved


def _issues(fig, ax, manager, tick_check):
    painter = fig.canvas.get_renderer()
    tight = ax.get_tightbbox(painter)
    canvas = fig.bbox
    issues = []
    if tight.x0 < -1 or tight.y0 < -1 or tight.x1 > canvas.x1 + 1 or tight.y1 > canvas.y1 + 1:
        issues.append("axis_text_outside_canvas")
    overlaps, _ = tick_check(fig, painter)
    issues.extend(["tick_label_overlap"] * len(overlaps))
    issues.extend(manager.validate()["issues"])
    return issues


def fit(fig, ax, manager, tick_check, *, padding_mm=2.):
    """Return measured layout evidence; retain user guide settings when supplied.

    A single automatic guide is tried on the right, bottom and top. Multiple
    automatic guides use the helper's vertical stack on the right. Choose a
    technically feasible arrangement with the largest data region; the final
    image still requires a visual review. Explicit guide positions stay fixed.
    """
    original = deepcopy(manager.config)
    if manager.override is not None or any(original.get(kind, {}).get("position") == "manual"
                                          for kind in ("categorical", "size", "colorbar")):
        raise ValueError("layout.auto_fit cannot be combined with manual legend coordinates or main_plot_bbox_mm; use explicit margins for that layout")
    sole_auto = (len(manager.requests) == 1 and
                 original.get(manager.requests[0]["kind"], {}).get("position", "auto") == "auto")
    sides = ["right", "bottom", "top"] if sole_auto else ["right"]
    attempts, solutions = [], []
    for side in sides:
        _clear(manager)
        manager.config = deepcopy(original)
        for request in manager.requests:
            cfg = manager.config.setdefault(request["kind"], {})
            if cfg.get("position", "auto") == "auto":
                cfg["position"] = side
        reserve = {"right": 0., "bottom": 0., "top": 0.}
        possible = True
        for _ in range(3):
            _clear(manager)
            if not _fit_axis(fig, ax, reserve, padding_mm):
                possible = False
                break
            manager.layout()
            measured = _reservation(fig, manager, padding_mm)
            updated = {edge: max(reserve[edge], measured[edge]) for edge in reserve}
            if max(abs(updated[e] - reserve[e]) for e in reserve) < .05:
                break
            reserve = updated
        issues = _issues(fig, ax, manager, tick_check) if possible else ["no_positive_data_region"]
        bounds = list(ax.get_position(original=True).bounds)
        area = ax.get_window_extent().width * ax.get_window_extent().height / (fig.bbox.width * fig.bbox.height)
        record = {"automatic_guide_side": side if manager.requests else None,
                  "reserved_mm": reserve, "issues": issues,
                  "data_area_fraction": area if possible else 0.}
        attempts.append(record)
        solutions.append((len(issues), -area if possible else math.inf, len(solutions),
                          bounds, deepcopy(manager.config), record))
    best = min(solutions, key=lambda item: item[:3])
    _clear(manager)
    ax.set_position(best[3])
    manager.config = best[4]
    manager.layout()
    issues = _issues(fig, ax, manager, tick_check)
    if best[5]["issues"] == ["no_positive_data_region"]:
        issues.append("no_positive_data_region")
    position = ax.get_position(original=True)
    mm = 25.4 / fig.dpi
    box = ax.get_window_extent()
    return {"status": "pass" if not issues else "needs_revision", "issues": issues,
            "margins": {"left": position.x0, "right": position.x1,
                        "bottom": position.y0, "top": position.y1},
            "data_region_mm": [box.x0 * mm, box.y0 * mm, box.width * mm, box.height * mm],
            "data_area_fraction": box.width * box.height / (fig.bbox.width * fig.bbox.height),
            "attempts": attempts, "padding_mm": padding_mm,
            "note": "Measured technical fit at unchanged canvas and font sizes. No data or labels were removed. Largest feasible data region is a space-allocation choice, not proof of aesthetic or journal quality. If it does not fit, enlarge or split the panel explicitly."}
