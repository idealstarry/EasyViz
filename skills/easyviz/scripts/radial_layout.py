"""Pure physical layout helpers for supplied radial graphics (stdlib only).

These functions place existing graphical identities. They do not infer a tree,
change its child order, or transform branch lengths. A topology-only display and
a branch-length display have different meanings; the plotting recipe must adopt
and disclose that choice before using this module. Numeric defaults here are
coordinate conventions, never literature-derived aesthetic ratios.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys


def _number(value, name, *, minimum=None, positive=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        value = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f"{name} must be a finite number") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if positive and value <= 0 or minimum is not None and value < minimum:
        raise ValueError(f"{name} must be {'positive' if positive else f'at least {minimum}'}")
    return value


def _strings(values, name, *, unique=False):
    if not isinstance(values, (list, tuple)) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f"{name} must contain nonempty literal string IDs")
    if unique and len(set(values)) != len(values):
        raise ValueError(f"{name} must contain unique IDs")
    return list(values)


def _vector(values, length, name, *, positive=False):
    if not isinstance(values, (list, tuple)) or len(values) != length:
        raise ValueError(f"{name} must contain {length} numbers")
    return [_number(v, f"{name}[{i}]", positive=positive) for i, v in enumerate(values)]


def merge_category_runs(item_ids, categories, *, circular=False, start_angle_deg=0, sweep_angle_deg=360):
    """Merge adjacent equal classes, retaining every ordered item's exact interval.

    The caller has already adopted the item order. Each item occupies the same
    angular interval. With ``circular=True`` the sweep must be exactly one full
    turn, and the first/last equal classes merge across the arbitrary seam. Such
    a run has unwrapped angles and ordered ``index_intervals`` on both sides of
    the seam; the original linear order remains in ``item_ids`` and ``items``.
    For partial arcs and linear tracks use ``circular=False``. No item borders,
    gaps, color choices, sample sorting, or category recoloring are introduced.
    """
    ids = _strings(item_ids, "item_ids", unique=True)
    classes = _strings(categories, "categories")
    if len(ids) != len(classes):
        raise ValueError("item_ids and categories must have the same length")
    if not isinstance(circular, bool):
        raise ValueError("circular must be a boolean")
    start = _number(start_angle_deg, "start_angle_deg")
    sweep = _number(sweep_angle_deg, "sweep_angle_deg", positive=True)
    if sweep > 360 or circular and sweep != 360:
        raise ValueError("sweep must be at most 360 degrees; circular=True requires exactly 360")
    count = len(ids)
    step = sweep / count
    # Reuse one boundary vector so adjacent segments have identical endpoints.
    boundaries = [start + sweep * i / count for i in range(count + 1)]
    if any(not math.isfinite(v) for v in boundaries) or any(right <= left for left, right in zip(boundaries, boundaries[1:])):
        raise ValueError("Angular intervals must be finite and distinguishable at the supplied start/sweep")
    groups = []
    for i, category in enumerate(classes):
        if groups and groups[-1]["category"] == category:
            groups[-1]["stop"] = i + 1
        else:
            groups.append({"category": category, "start": i, "stop": i + 1})
    if circular and len(groups) > 1 and groups[0]["category"] == groups[-1]["category"]:
        seam = {"category": groups[0]["category"], "start": groups[-1]["start"],
                "stop": groups[0]["stop"] + count}
        groups = [seam] + groups[1:-1]
    runs, item_to_run = [], {}
    for group in groups:
        lo, hi = group["start"], group["stop"]
        wrapped = hi > count
        indices = list(range(lo, hi))
        run_ids = [ids[i % count] for i in indices]
        intervals = [[lo, count], [0, hi - count]] if wrapped else [[lo, hi]]
        run_index = len(runs)
        item_to_run.update((identifier, run_index) for identifier in run_ids)
        # Stop angle deliberately exceeds one turn for a seam-spanning wedge.
        angle_end = boundaries[hi] if not wrapped else boundaries[hi - count] + sweep
        runs.append({"category": group["category"], "item_ids": run_ids,
                     "index_intervals": intervals, "start_angle_deg": boundaries[lo],
                     "end_angle_deg": angle_end, "wraps_seam": wrapped})
    items = [{"id": identifier, "category": classes[i], "index": i,
              "start_angle_deg": boundaries[i], "end_angle_deg": boundaries[i + 1],
              "run_index": item_to_run[identifier]} for i, identifier in enumerate(ids)]
    return {"item_ids": ids, "circular": circular, "start_angle_deg": start,
            "sweep_angle_deg": sweep, "item_interval_deg": step, "items": items, "runs": runs}


def pack_labels_in_window(labels, *, window_deg, radius_mm, gap_mm=0, max_shift_deg=None):
    """Balance ordered label centers within an explicit open angular window.

    Each label is ``{id, angle_deg, extent_mm}`` or uses ``extent_deg`` instead.
    Extent is its *occupied arc span* at the supplied radius, measured/adopted by
    the recipe, not automatically inferred from text width or character count.
    Angles must already be in nondecreasing, unwrapped order (e.g. 350..390).
    Equal-weight least-squares isotonic packing moves crowded neighbors in both
    directions while keeping their order, footprints, and optional shift bound.

    This is open-window/sector packing: circular first/last collision and actual
    rotated text/leader intersections require the renderer's separate review.
    Infeasible geometry returns no placed centers, never a clipped/dropped label.
    """
    if not isinstance(labels, (list, tuple)) or not labels:
        raise ValueError("labels must be a nonempty list")
    window = _vector(window_deg, 2, "window_deg")
    lo, hi = window
    if not 0 < hi - lo <= 360:
        raise ValueError("window_deg must be increasing and span at most 360 degrees")
    radius = _number(radius_mm, "radius_mm", positive=True)
    gap = _number(gap_mm, "gap_mm", minimum=0)
    shift = None if max_shift_deg is None else _number(max_shift_deg, "max_shift_deg", minimum=0)
    gap_deg = _number(math.degrees(gap / radius), "derived gap_deg", minimum=0)
    ids, anchors, widths = [], [], []
    for i, label in enumerate(labels):
        if not isinstance(label, dict) or set(label) not in ({"id", "angle_deg", "extent_mm"}, {"id", "angle_deg", "extent_deg"}):
            raise ValueError("Each label needs only id, angle_deg, and exactly one of extent_mm/extent_deg")
        ids.extend(_strings([label["id"]], f"labels[{i}].id"))
        anchors.append(_number(label["angle_deg"], f"labels[{i}].angle_deg"))
        unit = "extent_mm" if "extent_mm" in label else "extent_deg"
        width = _number(label[unit], f"labels[{i}].{unit}", positive=True)
        widths.append(_number(math.degrees(width / radius) if unit == "extent_mm" else width, "derived extent_deg", positive=True))
    _strings(ids, "label IDs", unique=True)
    if anchors != sorted(anchors):
        raise ValueError("Label angles must already be in nondecreasing unwrapped order; no sorting is performed")
    try:
        required = _number(math.fsum(widths) + gap_deg * (len(ids) - 1), "derived required span", positive=True)
    except OverflowError:
        raise ValueError("Derived required span must be finite") from None
    report = {"status": "infeasible", "window_deg": window, "radius_mm": radius,
              "gap_mm": gap, "gap_deg": gap_deg, "max_shift_deg": shift,
              "required_span_deg": required, "available_span_deg": hi - lo,
              "circular_seam_checked": False, "issues": [], "max_shift_used_deg": None,
              "labels": [{"id": identifier, "anchor_angle_deg": anchor, "extent_deg": width,
                          "placed_angle_deg": None, "shift_deg": None}
                         for identifier, anchor, width in zip(ids, anchors, widths)]}
    if required > hi - lo + 1e-10:
        report["issues"].append("occupied_extents_and_gaps_exceed_window")
        return report
    offsets = [0.]
    for previous, width in zip(widths, widths[1:]):
        offsets.append(offsets[-1] + (previous + width) / 2 + gap_deg)
    # Subtract cumulative mandatory center separations; remaining centers must
    # be monotone. Individual bounds retain window and optional displacement.
    lower, upper, targets = [], [], []
    for anchor, width, offset in zip(anchors, widths, offsets):
        left, right = lo + width / 2, hi - width / 2
        if shift is not None:
            left, right = max(left, anchor - shift), min(right, anchor + shift)
        lower.append(left - offset)
        upper.append(right - offset)
        targets.append(anchor - offset)
    running = -math.inf
    for left, right in zip(lower, upper):
        running = max(running, left)
        if running > right + 1e-10:
            report["issues"].append("window_or_shift_bounds_infeasible")
            return report
    blocks = []
    for i, (target, left, right) in enumerate(zip(targets, lower, upper)):
        block = {"first": i, "last": i, "mean": target, "count": 1, "lo": left, "hi": right}
        block["value"] = min(max(target, left), right)
        blocks.append(block)
        while len(blocks) > 1 and blocks[-2]["value"] > blocks[-1]["value"]:
            b, a = blocks.pop(), blocks.pop()
            count = a["count"] + b["count"]
            merged = {"first": a["first"], "last": b["last"],
                      "mean": a["mean"] * (a["count"] / count) + b["mean"] * (b["count"] / count),
                      "count": a["count"] + b["count"], "lo": max(a["lo"], b["lo"]),
                      "hi": min(a["hi"], b["hi"])}
            if merged["lo"] > merged["hi"] + 1e-10:
                report["issues"].append("window_or_shift_bounds_infeasible")
                return report
            merged["value"] = min(max(merged["mean"], merged["lo"]), merged["hi"])
            blocks.append(merged)
    placed = [0.] * len(ids)
    for block in blocks:
        for i in range(block["first"], block["last"] + 1):
            placed[i] = block["value"] + offsets[i]
    for item, angle, anchor in zip(report["labels"], placed, anchors):
        item.update(placed_angle_deg=angle, shift_deg=angle - anchor)
    report.update(status="ready", max_shift_used_deg=max(abs(angle - anchor) for angle, anchor in zip(placed, anchors)))
    return report


def radial_geometry(tree_radius_mm, tracks, *, label_radius_mm=None, label_depth_mm=0,
                    center_mm=(0, 0), canvas_mm=None, guides=None):
    """Report explicit radial track geometry; never choose a preferred proportion.

    Tracks are ordered inner-to-outer ``{id, inner_radius_mm, width_mm}`` objects.
    Labels have an adopted outward radial depth, separate from the tangential
    extents in ``pack_labels_in_window``. Optional guides use ``{id, bbox_mm}``
    with [left,bottom,width,height]. Full-circle envelope overlap is conservative
    for sparse labels or partial arcs and is reported for visual review only.
    """
    radius = _number(tree_radius_mm, "tree_radius_mm", positive=True)
    center = _vector(center_mm, 2, "center_mm")
    if not isinstance(tracks, (list, tuple)):
        raise ValueError("tracks must be an ordered list")
    depth = _number(label_depth_mm, "label_depth_mm", minimum=0)
    if label_radius_mm is None and depth:
        raise ValueError("label_depth_mm requires label_radius_mm")
    label_radius = None if label_radius_mm is None else _number(label_radius_mm, "label_radius_mm", positive=True)
    checked, seen, issues, outer = [], set(), [], radius
    previous_inner = -math.inf
    for track in tracks:
        if not isinstance(track, dict) or set(track) != {"id", "inner_radius_mm", "width_mm"}:
            raise ValueError("Each track needs only id, inner_radius_mm, width_mm")
        identifier = _strings([track["id"]], "track ID")[0]
        if identifier in seen:
            raise ValueError("Track IDs must be unique")
        seen.add(identifier)
        inner = _number(track["inner_radius_mm"], "inner_radius_mm", minimum=0)
        width = _number(track["width_mm"], "width_mm", positive=True)
        if inner < previous_inner:
            raise ValueError("Tracks must already be in inner-to-outer order")
        gap = inner - outer
        if gap < 0:
            issues.append({"code": "radial_track_overlap", "id": identifier, "overlap_mm": -gap})
        track_outer = _number(inner + width, "derived track outer radius", positive=True)
        checked.append({"id": identifier, "inner_radius_mm": inner, "outer_radius_mm": track_outer,
                        "width_mm": width, "gap_from_previous_envelope_mm": gap})
        outer, previous_inner = max(outer, track_outer), inner
    if label_radius is not None and label_radius < outer:
        issues.append({"code": "label_anchors_inside_radial_tracks", "overlap_mm": outer - label_radius})
    envelope_radius = _number(max(outer, (label_radius or 0) + depth), "derived envelope radius", positive=True)
    envelope = _vector([center[0] - envelope_radius, center[1] - envelope_radius, 2 * envelope_radius, 2 * envelope_radius], 4, "derived radial envelope")
    canvas = None if canvas_mm is None else _vector(canvas_mm, 2, "canvas_mm", positive=True)
    if canvas is not None and (envelope[0] < 0 or envelope[1] < 0 or envelope[0] + envelope[2] > canvas[0] or envelope[1] + envelope[3] > canvas[1]):
        issues.append({"code": "radial_envelope_outside_canvas", "conservative": True})
    if guides is None:
        guides = []
    if not isinstance(guides, (list, tuple)):
        raise ValueError("guides must be a list")
    checked_guides, seen = [], set()
    for guide in guides:
        if not isinstance(guide, dict) or set(guide) != {"id", "bbox_mm"}:
            raise ValueError("Each guide needs only id and bbox_mm")
        identifier = _strings([guide["id"]], "guide ID")[0]
        if identifier in seen:
            raise ValueError("Guide IDs must be unique")
        seen.add(identifier)
        box = _vector(guide["bbox_mm"], 4, "bbox_mm")
        if min(box[2:]) <= 0:
            raise ValueError("Guide bbox width and height must be positive")
        _number(box[0] + box[2], "derived guide right edge")
        _number(box[1] + box[3], "derived guide top edge")
        closest = [min(max(center[i], box[i]), box[i] + box[i + 2]) for i in (0, 1)]
        if math.hypot(closest[0] - center[0], closest[1] - center[1]) < envelope_radius:
            issues.append({"code": "guide_intersects_radial_envelope", "id": identifier, "conservative": True})
        if canvas is not None and (box[0] < 0 or box[1] < 0 or box[0] + box[2] > canvas[0] or box[1] + box[3] > canvas[1]):
            issues.append({"code": "guide_outside_canvas", "id": identifier})
        checked_guides.append({"id": identifier, "bbox_mm": box})
    return {"status": "needs_review" if issues else "ready", "tree_radius_mm": radius,
            "center_mm": center, "tracks": checked, "label_radius_mm": label_radius,
            "label_depth_mm": depth, "label_gap_from_tracks_mm": None if label_radius is None else label_radius - outer,
            "radial_envelope_mm": envelope, "canvas_mm": canvas, "guides": checked_guides,
            "tree_area_fraction_of_outer_track_disk": (radius / outer) ** 2,
            "issues": issues, "aesthetic_threshold_applied": False}


def contract():
    return {"operations": {
        "runs": {"required": ["item_ids", "categories"], "options": ["circular", "start_angle_deg", "sweep_angle_deg"]},
        "labels": {"required": ["labels", "window_deg", "radius_mm"], "options": ["gap_mm", "max_shift_deg"]},
        "geometry": {"required": ["tree_radius_mm", "tracks"], "options": ["label_radius_mm", "label_depth_mm", "center_mm", "canvas_mm", "guides"]}},
        "limits": ["No tree inference, branch-length transformation, item sorting, text measurement, or automatic palette choice.",
                   "Labels are packed in one open unwrapped angular window; circular seam and rendered text/leader intersections require separate review.",
                   "Infeasible labels are all retained with null placed angles; geometry reports are not an aesthetic certification."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-contract", action="store_true")
    parser.add_argument("--input", help="JSON request file, or - for stdin; at most 1 MiB")
    args = parser.parse_args(argv)
    if args.describe_contract:
        print(json.dumps(contract(), indent=2))
        return 0
    if not args.input:
        parser.error("--input is required unless --describe-contract is used")
    try:
        if args.input == "-":
            source = sys.stdin.buffer.read(1024 * 1024 + 1)
        else:
            with Path(args.input).open("rb") as handle:
                source = handle.read(1024 * 1024 + 1)
        if len(source) > 1024 * 1024:
            raise ValueError("JSON request exceeds 1 MiB")
        payload = json.loads(source)
        if not isinstance(payload, dict) or "operation" not in payload:
            raise ValueError("Request must be an object with operation")
        operation = payload.pop("operation")
        functions = {"runs": merge_category_runs, "labels": pack_labels_in_window, "geometry": radial_geometry}
        if not isinstance(operation, str) or operation not in functions:
            raise ValueError("operation must be runs, labels, or geometry")
        report = functions[operation](**payload)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report.get("status", "ready") == "ready" else 1
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
