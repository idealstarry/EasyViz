"""Check final display-space observation envelopes without editing any artist.

Only registered ``point-group`` PathCollections with ordinary circular paths
are certified. These are the actual observation layers produced by the core
scatter, distribution and dotplot renderer. Axes clip boxes and the physical
figure boundary are checked; complex clip paths, path effects and other glyphs
are explicitly unmeasured. Bars, summary marks, state glyphs and legend keys
are outside this contract. No size, range, offset or layout is changed.
"""
from __future__ import annotations

import math

from matplotlib.collections import PathCollection
from matplotlib.markers import MarkerStyle
from matplotlib.transforms import Affine2D, IdentityTransform
import numpy as np


def _circle(path):
    marker = MarkerStyle("o")
    expected = marker.get_path().transformed(marker.get_transform())
    return (np.array_equal(path.vertices, expected.vertices)
            and np.array_equal(path.codes, expected.codes))


def _item(sequence, index, default=None):
    return sequence[index % len(sequence)] if len(sequence) else default


def _visible(colors, index):
    color = _item(colors, index)
    return color is not None and len(color) == 4 and float(color[3]) > 0


def _source(entry, index, count):
    """Keep a truthful row/key when a semantic group supplies that mapping."""
    keys = entry.get("source_keys", [])
    records = [record for key in keys if isinstance(key, dict)
               for record in key.get("records", [])]
    if len(records) == count:
        return {"record": records[index]}
    if len(keys) == count and isinstance(keys[index], dict):
        return keys[index].copy()
    return {"group_source_keys": keys}


def _excess(bounds, clip):
    # This tolerance covers floating-point arithmetic, never an aesthetic
    # padding allowance or a pixel-wide exemption for a clipped observation.
    tolerance = 64 * np.finfo(float).eps * max(1., *map(abs, bounds), *map(abs, clip))
    values = {"left": clip[0] - bounds[0], "bottom": clip[1] - bounds[1],
              "right": bounds[2] - clip[2], "top": bounds[3] - clip[3]}
    return {side: float(value) for side, value in values.items() if value > tolerance}


def measure(fig):
    """Measure after the final draw, using actual collection rendering transforms.

    Call separately at each export canvas size, including a rounded raster
    canvas. A log offset transform is handled by Matplotlib's own collection
    preparation. Visible solid circular strokes extend the path by half their
    actual linewidth; an invisible edge adds no thickness. Antialias fringes
    are not geometric marker area. Unusual geometry is an advisory, not a
    manufactured pass or an inferred scientific violation.
    """
    fig.canvas.draw()
    factor = 25.4 / float(fig.dpi)
    groups, clipped, advisory = [], [], []
    ignored = {"nonfinite_or_masked": 0, "zero_area": 0, "invisible": 0}
    checked = 0
    for entry in getattr(fig, "_easyviz_elements", []):
        if entry.get("role") != "point-group":
            continue
        identity = {"element_id": entry.get("id"), "label": entry.get("label")}
        artist = entry.get("_artist")
        if not isinstance(artist, PathCollection):
            advisory.append({**identity, "reason": "Observation artist is not a PathCollection"})
            continue
        if not artist.get_visible() or artist.axes is not None and not artist.axes.get_visible():
            continue
        # _prepare_points matches the drawing pipeline, including units,
        # masked offsets and non-affine (e.g. logarithmic) offset transforms.
        try:
            master, offset_transform, offsets, paths = artist._prepare_points()
            transforms = artist.get_transforms()
            centers = offset_transform.transform(offsets) if len(offsets) else np.empty((0, 2))
        except (AttributeError, TypeError, ValueError) as exc:
            advisory.append({**identity, "reason": "Collection transform could not be measured", "detail": str(exc)})
            continue
        count = max(len(paths), len(transforms), len(offsets)) if len(paths) else 0
        group = {**identity, "observations": count, "checked_observations": 0,
                 "clipped_observations": 0, "unmeasured_observations": 0}
        if artist.axes is not None:
            group["axes"] = {"x_limits": list(map(float, artist.axes.get_xlim())),
                             "y_limits": list(map(float, artist.axes.get_ylim())),
                             "x_scale": artist.axes.get_xscale(), "y_scale": artist.axes.get_yscale()}
        groups.append(group)
        reasons = []
        if not master.is_affine:
            reasons.append("Non-affine marker path transform")
        if artist.get_path_effects() or artist.get_sketch_params():
            reasons.append("Path effects or sketching change the drawn envelope")
        if artist.get_clip_on() and artist.get_clip_path() is not None:
            reasons.append("Nonrectangular/custom clip path")
        faces, edges = artist.get_facecolors(), artist.get_edgecolors()
        widths, styles = artist.get_linewidths(), artist.get_linestyles()
        boundaries = [("figure", np.asarray(fig.bbox.extents, dtype=float))]
        if artist.get_clip_on() and artist.get_clip_box() is not None:
            boundaries.append(("artist_clip_box", np.asarray(artist.get_clip_box().extents, dtype=float)))
        for index in range(count):
            center = _item(centers, index, np.zeros(2))
            path = _item(paths, index)
            transform = Affine2D(_item(transforms, index)) if len(transforms) else IdentityTransform()
            transform = transform + master
            if not np.isfinite(center).all() or not np.isfinite(transform.get_matrix()).all():
                ignored["nonfinite_or_masked"] += 1
                continue
            # A zero-size quantitative dot remains exactly zero, including
            # when state glyphs separately indicate the measured zero.
            if _item(artist.get_sizes(), index) == 0:
                ignored["zero_area"] += 1
                continue
            face_visible = _visible(faces, index)
            width = float(_item(widths, index, 0.))
            edge_visible = _visible(edges, index) and math.isfinite(width) and width > 0
            if not face_visible and not edge_visible:
                ignored["invisible"] += 1
                continue
            local_reasons = reasons.copy()
            if not _circle(path):
                local_reasons.append("Noncircular marker path")
            if edge_visible and _item(styles, index, (0, None))[1] is not None:
                local_reasons.append("Dashed observation stroke")
            if any(not np.isfinite(boundary).all() for _, boundary in boundaries):
                local_reasons.append("Nonfinite clipping boundary")
            if local_reasons:
                group["unmeasured_observations"] += 1
                advisory.append({**identity, "observation_index": index,
                                 "source": _source(entry, index, count), "reasons": local_reasons})
                continue
            box = path.get_extents(transform)
            half_stroke = width * float(fig.dpi) / 144 if edge_visible else 0.
            bounds = np.asarray(box.extents) + np.tile(center, 2) + np.array([-half_stroke, -half_stroke, half_stroke, half_stroke])
            violations = []
            for kind, boundary in boundaries:
                if excess := _excess(bounds, boundary):
                    violations.append({"boundary": kind,
                                       "clip_bounds_mm": (boundary * factor).tolist(),
                                       "exceeded_mm": {side: amount * factor for side, amount in excess.items()}})
            group["checked_observations"] += 1
            checked += 1
            if violations:
                group["clipped_observations"] += 1
                clipped.append({**identity, "observation_index": index,
                                "source": _source(entry, index, count),
                                "center_mm": (np.asarray(center) * factor).tolist(),
                                "outer_bounds_mm": (bounds * factor).tolist(),
                                "visible_stroke_width_pt": width if edge_visible else 0.,
                                "violations": violations})
    return {"status": "needs_revision" if clipped else "advisory" if advisory else "pass" if groups else "not_applicable",
            "checked_observations": checked, "clipped_observations": len(clipped),
            "unmeasured_observations": sum(group["unmeasured_observations"] for group in groups),
            "ignored_observations": ignored, "groups": groups,
            "clipped": clipped, "advisories": advisory,
            "canvas_mm": [float(value) * factor for value in fig.bbox.size],
            "scope": "Final transformed registered circular observation paths plus visible solid stroke against the actual rectangular artist clip and physical figure canvas. No other occlusion, aesthetics, state glyphs, bars or unregistered marks are certified; no geometry or data is edited."}


def summarize(reports):
    """Preserve every actual export measurement and fail any confirmed clipping."""
    values = list(reports.values())
    status = ("needs_revision" if any(item["status"] == "needs_revision" for item in values)
              else "advisory" if any(item["status"] == "advisory" for item in values)
              else "pass" if any(item["status"] == "pass" for item in values)
              else "not_applicable")
    return {"status": status, "by_format": reports,
            "note": "Confirmed observation clipping invalidates delivery. Locked scales, areas, linewidths and source rows are retained; explicitly revise the adopted range/layout or divide the panel. Advisory geometry still needs inspection."}
