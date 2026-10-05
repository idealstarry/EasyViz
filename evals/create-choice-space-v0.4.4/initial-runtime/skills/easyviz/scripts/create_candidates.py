#!/usr/bin/env python3
"""Render scene-informed, constrained candidates for a declared NEW Create draft.

This helper uses the existing renderers. A candidate is a design proposal, never
an aesthetic certification. It cannot edit an accepted panel or source file.
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


def _load(name, filename):
    loader = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


core = _load("easyviz_candidates_core", "render.py")
style = _load("easyviz_candidates_style", "create_style.py")
replicate = _load("easyviz_candidates_replicate", "replicate_plot.py")
require, SpecError = core.require, core.SpecError
VERSION = "0.2.0"
SUPPORTED = ("distribution", "heatmap", "scatter", "replicate")
CONTRACT = {
    "version": VERSION,
    "command": "create_candidates.py --data prepared.csv --spec adopted-new-draft.json --out NEW_DIRECTORY --new-draft [--count 1|2|3] [--no-render]",
    "track": "create",
    "scope": "New explicitly mapped distribution (box/violin), complete heatmap, fixed-area scatter, or focused replicate draft; existing accepted/reproduce panels use their original source and renderer.",
    "declaration": "--new-draft is required; input is an ordinary renderer spec, with explicit fields and already adopted scientific methods. For replicate, options.mode and options.uncertainty are required.",
    "preserved": ["Byte-identical input/spec/profile snapshots; every row, value, literal key, category order, axis scale/limits, normalization, statistics, KDE method and point area.", "Explicit widths/heights and profile declarations, agreed fonts and font sizes, explicit cosmetic options, margins and manual guides.", "No quantitative point movement; only distribution categorical packing uses the renderer's existing point-placement mechanism."],
    "suggested": "Only omitted new-draft dimensions/cosmetics receive chart/data suggestions. Conditional visual-role and decoding routes are limited tool implementations, not the complete design space. At most three materially distinct rendered mark/color/guide proposals; width/margin changes alone do not count. Fewer if explicit choices lock the routes.",
    "outputs": ["source.csv", "source-spec.json", "profile.json when used", "manifest.json", "candidate-NN/spec.json", "candidate-NN/panel.png and other requested exports unless --no-render", "per-candidate renderer data/settings/statistics/qa; geometry-evidence.json"],
    "review": "Technical QA and source/artist evidence are separate from pending visual review. All candidates require inspecting actual exports; no winner is selected, and failed candidates remain visibly invalid.",
}


def _json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_source(raw):
    try:
        table = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise SpecError(f"Prepared input must be a valid UTF-8 CSV: {exc}") from None
    require(len(table) > 1, "Prepared CSV requires a header and rows")
    header, rows = table[0], table[1:]
    require(all(h.strip() for h in header) and len(header) == len(set(header)), "CSV headers must be nonempty and unique")
    require(all(len(row) == len(header) for row in rows), "Ragged or empty CSV rows must be prepared explicitly; no row is dropped")
    return header, rows


def _features(data, spec):
    chart, fields, options = spec["chart"], spec["fields"], spec.get("options", {})
    result = {"chart": chart, "input_rows": len(data), "reading_task_source": "chart_family_hint_only",
              "reading_task_scope": "Not the user's adopted objective; the calling Agent must establish the actual reading task and scientific contract before invoking this limited helper.", "task": {
        "distribution": "compare raw distributions with the adopted summary",
        "heatmap": "read a complete supplied quantitative matrix",
        "scatter": "read fixed-size observations on two supplied numeric axes",
        "replicate": "read adopted component/condition means with raw replicates and supplied uncertainty semantics",
    }[chart], "category_order": {}, "label_max_characters": {}}
    roles = {"distribution": ("group",), "heatmap": ("row", "column"), "scatter": ("group",), "replicate": ("condition", "component", "state")}[chart]
    for role in roles:
        if role not in fields:
            continue
        order_role = {"row": "y", "column": "x"}.get(role, role)
        labels = core.ordered(data, fields[role], spec, order_role)
        result["category_order"][role] = labels
        result["label_max_characters"][role] = max(map(len, labels))
    if chart == "distribution":
        groups = result["category_order"]["group"]
        result.update(kind=options.get("kind", "box"), orientation=options.get("orientation", "vertical"), category_count=len(groups), inner_summary=options.get("violin_inner", "none"))
        result["group_counts"] = {g: int((data[fields["group"]].astype(str) == g).sum()) for g in groups}
        result["maximum_tie_count"] = int(data.groupby([fields["group"], fields["value"]], sort=False).size().max())
        result["dense_raw_layer"] = max(result["group_counts"].values()) > 60 or result["maximum_tie_count"] > 8
    elif chart == "heatmap":
        result.update(matrix_rows=len(result["category_order"]["row"]), matrix_columns=len(result["category_order"]["column"]))
        result["narrow_matrix"] = result["matrix_columns"] <= 4
    elif chart == "scatter":
        result["duplicate_coordinate_rows"] = int(data.duplicated([fields["x"], fields["y"]], keep=False).sum())
        result["group_count"] = len(result["category_order"].get("group", []))
    else:
        result.update(mode=options["mode"], uncertainty=options["uncertainty"], category_count=len(result["category_order"]["condition"]))
        result["component_count"] = len(result["category_order"].get("component", []))
    return result


def _draw(data_path, spec):
    """Use exactly the same source preparation, statistics and draw as export."""
    renderer = replicate if spec["chart"] == "replicate" else core
    data = renderer.prepare(data_path, spec)
    layout, typography, rc = core.setup(spec)
    with core.plt.rc_context(rc):
        if renderer is replicate:
            fig, _ = renderer.draw(data, spec, layout, typography)
        else:
            fig, _ = core.draw(data, spec, layout, typography, core.statistics(data, spec))
        fig.canvas.draw()
    return fig, data, layout, typography


def _visual_facets(fig):
    """Actual painted roles/decoding, excluding width/margin-only differences."""
    marks = []
    def rgba(value):
        if isinstance(value, str):
            value = core.mcolors.to_rgba(value)
        array = core.np.asarray(value, dtype=float)
        return core.np.round(array, 8).tolist()
    for item in getattr(fig, "_easyviz_elements", []):
        artist = item["_artist"]
        entry = {"role": item["role"], "label": item["label"]}
        for facet, methods in (("face", ("get_facecolors", "get_facecolor")), ("edge", ("get_edgecolors", "get_edgecolor")), ("stroke", ("get_color",))):
            for method in methods:
                if hasattr(artist, method):
                    entry[facet] = rgba(getattr(artist, method)())
                    break
        if len(entry) > 2:
            marks.append(entry)
    guides = [{"kind": entry["kind"], **{key: entry["chosen_settings"][key] for key in ("position", "orientation", "ncol") if key in entry["chosen_settings"]}}
              for entry in fig._easyviz_legend_layout.entries]
    ramps = [{"rgba_samples": rgba(image.cmap(core.np.linspace(0, 1, 5))),
              "norm": type(image.norm).__name__, "limits": [float(image.norm.vmin), float(image.norm.vmax)],
              "center": getattr(image.norm, "vcenter", None)} for image in fig.axes[0].images]
    return {"painted_mark_roles": marks, "continuous_decoding": ramps, "guide_organization": guides}


def _measure(fig, data, spec, typography):
    """Evidence from real artists; no sampled aesthetic quality score."""
    ax = fig.axes[0]
    box = ax.get_window_extent()
    factor = 25.4 / fig.dpi
    evidence = {"data_region_mm": [float(v * factor) for v in (box.x0, box.y0, box.width, box.height)],
                "canvas_mm": [fig.get_figwidth() * 25.4, fig.get_figheight() * 25.4],
                "numeric_limits": {"x": list(map(float, ax.get_xlim())), "y": list(map(float, ax.get_ylim()))},
                "scales": {"x": ax.get_xscale(), "y": ax.get_yscale()}, "typography": typography,
                "category_tick_labels": {}, "issues": [], "visual_facets": _visual_facets(fig),
                "guide_geometry": fig._easyviz_legend_layout.validate()}
    chart, fields, options = spec["chart"], spec["fields"], spec.get("options", {})
    elements = getattr(fig, "_easyviz_elements", [])
    if chart in ("distribution", "scatter"):
        points = [item for item in elements if item["role"] == "point-group"]
        preserved = True
        sizes_preserved = True
        observation_count = 0
        for item in points:
            artist = item["_artist"]
            actual = core.np.asarray(artist.get_offsets(), dtype=float)
            if "group" in fields:
                selected = data[data[fields["group"]].astype(str) == item["label"]]
            else:
                selected = data
            if chart == "distribution":
                numeric = 0 if options.get("orientation") == "horizontal" else 1
                expected = selected[fields["value"]].to_numpy(float)
                preserved &= actual.shape == (len(expected), 2) and core.np.array_equal(actual[:, numeric], expected)
            else:
                expected = selected[[fields["x"], fields["y"]]].to_numpy(float)
                preserved &= core.np.array_equal(actual, expected)
            sizes_preserved &= core.np.allclose(artist.get_sizes(), options.get("point_area_pt2", 9 if chart == "distribution" else 12))
            observation_count += len(actual)
        evidence["source_to_artist"] = {"status": "pass" if preserved and sizes_preserved and observation_count == len(data) else "needs_revision",
                                       "numeric_coordinates_preserved": bool(preserved), "point_area_preserved": bool(sizes_preserved), "observation_count": observation_count}
        if chart == "distribution":
            evidence["point_layout"] = deepcopy(getattr(fig, "_easyviz_point_layout", {}))
            categorical_axis = "y" if options.get("orientation") == "horizontal" else "x"
            labels = ax.get_yticklabels() if categorical_axis == "y" else ax.get_xticklabels()
            evidence["category_tick_labels"][categorical_axis] = [t.get_text() for t in labels]
            groups = core.ordered(data, fields["group"], spec, "group")
            span = abs((ax.get_ylim() if categorical_axis == "y" else ax.get_xlim())[1] - (ax.get_ylim() if categorical_axis == "y" else ax.get_xlim())[0])
            pitch = (box.height if categorical_axis == "y" else box.width) * factor / span
            evidence["category_pitch_mm"] = float(pitch)
            evidence["summary_thickness_mm"] = float(pitch * options.get("box_width", .5)) if options.get("kind", "box") == "box" else None
            # Compare real marker envelopes with the adopted summary's maximum
            # categorical envelope. A crossing is review evidence, not data loss.
            half_width = options.get("box_width", .5) / 2 if options.get("kind", "box") == "box" else options.get("violin_width", .7) / 2
            radius = math.sqrt(options.get("point_area_pt2", 9)) / 2 * 25.4 / 72
            if options.get("point_style") == "hollow":
                radius += options.get("point_edge_width_pt", .45) / 2 * 25.4 / 72
            crossings = 0
            for index, item in enumerate(points):
                axis = 1 if categorical_axis == "y" else 0
                coords = core.np.asarray(item["_artist"].get_offsets(), dtype=float)[:, axis]
                crossings += int(core.np.count_nonzero(abs(coords - index) * pitch - radius < half_width * pitch))
            evidence["raw_summary_categorical_envelope_crossings"] = crossings
            evidence["summary_raw_separation_note"] = "Envelope crossings require visual inspection, particularly opaque points over box medians; violin contour width is a conservative envelope, not a density crossing test."
            require(len(groups) == len(points), "Distribution groups/point collections disagree")
    elif chart == "heatmap":
        rows = core.ordered(data, fields["row"], spec, "y")
        cols = core.ordered(data, fields["column"], spec, "x")
        expected = data.pivot(index=fields["row"], columns=fields["column"], values=fields["value"]).loc[rows, cols].to_numpy(float)
        image = ax.images[0]
        unchanged = core.np.array_equal(core.np.asarray(image.get_array()), expected)
        evidence["source_to_artist"] = {"status": "pass" if unchanged else "needs_revision", "matrix_values_preserved": bool(unchanged), "color_limits": [float(image.norm.vmin), float(image.norm.vmax)]}
        evidence["cell_dimensions_mm"] = [float(box.width * factor / len(cols)), float(box.height * factor / len(rows))]
        evidence["cell_annotations"] = core.annotation_review.check_heatmap_annotations(fig, ax)
    else:
        evidence["source_to_artist"] = replicate.audit_source_artists(Path(data.attrs["candidate_source_path"]), spec, fig)
        clipped, marks = replicate._canvas_checks(fig)
        evidence["replicate_mark_geometry"] = marks
        if clipped:
            evidence["issues"].append("text_outside_canvas")
        if marks["status"] != "pass":
            evidence["issues"].append("replicate_mark_geometry")
    evidence["issues"].extend(core.auto_layout._issues(
        fig, ax, fig._easyviz_legend_layout, core.check_tick_label_overlap,
        annotation_check=lambda canvas, axes: core.annotation_review.check_heatmap_annotations(canvas, axes)))
    for key in ("source_to_artist", "point_layout", "cell_annotations"):
        if evidence.get(key, {}).get("status") == "needs_revision":
            evidence["issues"].append(key)
    evidence["technical_measurement_status"] = "needs_revision" if evidence["issues"] else "pass"
    return evidence


def _dimensions(features):
    chart = features["chart"]
    if chart == "distribution":
        n = features["category_count"]
        return (88, max(55, min(160, 23 + n * 11))) if features["orientation"] == "horizontal" else (max(70, min(180, 27 + n * 15)), 75)
    if chart == "heatmap":
        return max(70, min(180, 42 + features["matrix_columns"] * 7)), max(58, min(180, 23 + features["matrix_rows"] * 5))
    if chart == "replicate":
        return max(75, min(180, 30 + features["category_count"] * 18)), 75
    return 88, 78


_MISSING = object()


def _value(spec, path):
    for key in path:
        if not isinstance(spec, dict) or key not in spec:
            return _MISSING
        spec = spec[key]
    return spec


def _route_choices(base, features):
    """Bounded deterministic routes, filtered by actual adopted path locks."""
    chart, options = features["chart"], base.get("options", {})
    routes, excluded = [], []
    color_locked = any(key in base for key in ("colors", "palette", "profile"))
    def add(name, role, patches, *, requirements=(), condition=True, reason=""):
        blocked = list(reason and not condition and [reason] or [])
        for path, desired in requirements:
            adopted = _value(base, path)
            if adopted is not _MISSING and adopted != desired:
                blocked.append("Explicit /" + "/".join(path) + " retains the adopted value")
        if blocked:
            excluded.append({"route_id": name, "reasons": blocked})
        else:
            routes.append({"id": name, "visual_role": role, "patches": patches})
    if "profile" in base:
        return [{"id": "adopted-profile", "visual_role": "Adopted profile and source treatment", "patches": {}}], [{"route_id": "automatic-role-reassignment", "reasons": ["Adopted profile is authoritative"]}]
    if chart == "distribution":
        n = features["category_count"]
        kind = features["kind"]
        neutral = {("line_roles", "summary", "color"): "#333333"}
        if kind == "violin":
            neutral[("line_roles", "data", "color")] = "#555555"
        area = {**neutral, ("options", "point_color"): "#454545"}
        open_summary = {**neutral}
        if kind == "box":
            area.update({("options", "box_style"): "filled", ("options", "box_fill_alpha"): 1})
            open_summary[("options", "box_style")] = "outline"
            area_requirements = [(('options', 'box_style'), 'filled')]
            open_requirements = [(('options', 'box_style'), 'outline')]
            area_available = options.get("box_fill_alpha", 1) > 0
        else:
            has_inner = features["inner_summary"] == "box"
            area[("options", "violin_fill_alpha")] = 0 if has_inner else .24
            open_summary[("options", "violin_fill_alpha")] = 0
            open_requirements = [(('options', 'violin_fill_alpha'), 0)]
            area_requirements = []
            if has_inner:
                area[("options", "violin_inner_fill_alpha")] = 1
                open_summary[("options", "violin_inner_fill_alpha")] = 0
                open_requirements.append((('options', 'violin_inner_fill_alpha'), 0))
            area_available = options.get("violin_inner_fill_alpha" if has_inner else "violin_fill_alpha", 1) > 0
        if not color_locked:
            area[("palette",)] = "progeny-summary"
        raw = {**open_summary}
        raw_requirements = [*open_requirements, *[(path, value) for path, value in neutral.items()]]
        raw_available = "point_color" not in options and (color_locked or n <= 6)
        if not color_locked and n <= 6:
            raw[("palette",)] = "notch2-balanced" if n <= 4 else "somerville-bright"
        position = {**open_summary, ("options", "point_color"): "#454545"}
        position_requirements = [*open_requirements, *[(path, value) for path, value in neutral.items()], (("options", "point_color"), "#454545")]
        # Labels can decode numerous lanes without forcing a dark multicolor mix.
        choices = [("summary-area", "Category identity on bounded summary/density areas; uniform raw observations", area, area_requirements, area_available and (color_locked or n <= 4), "No eligible unlocked visible summary area/capacity"),
                   ("observation-color", "Category identity on raw observations; open neutral summaries/contours", raw, raw_requirements, raw_available, "Explicit raw color or categorical palette capacity locks raw reassignment"),
                   ("neutral-position", "Direct category labels/positions decode identity; open neutral marks", position, position_requirements, not color_locked, "Adopted categorical color mapping is retained on a colored layer")]
        if n > 4 and not color_locked:
            choices = [choices[2], choices[1], choices[0]]
        for name, role, changes, required, eligible, reason in choices:
            add(name, role, changes, requirements=required, condition=eligible, reason=reason)
    elif chart == "replicate":
        for treatment in ("filled", "outline"):
            patches = {("options", "bar_style"): treatment, ("options", "point_color"): "#333333"}
            if features["mode"] == "summary":
                patches[("options", "bar_color")] = "#CACACA"
            elif not color_locked and features["component_count"] <= 4:
                patches[("palette",)] = "progeny-summary"
            if treatment == "outline" and features["mode"] == "summary":
                patches.update({("options", "bar_edge_color"): "#333333", ("options", "bar_edge_width_pt"): .7})
            add("replicate-" + treatment, "Adopted means/uncertainty with " + treatment + " supplied bars and raw observations", patches,
                requirements=[(("options", "bar_style"), treatment)], condition=treatment != "outline" or ("state" not in base["fields"] and options.get("bar_edge_width_pt", .55) > 0), reason="Outline requires unmapped states and a positive adopted/default edge width")
    elif chart == "heatmap":
        ramp_locked = any(key in base for key in ("colormap", "palette", "profile")) or "color_limits" not in options
        ramps = ([None] if ramp_locked else (["scwat-blue-white-coral", "somerville-blue-coral"] if "color_center" in options else ["notch2-blue", "notch2-teal"]))
        for index, ramp in enumerate(ramps):
            add("matrix-ramp-" + str(index + 1), "Supplied matrix with the adopted normalization and an eligible quantitative ramp", {} if ramp is None else {("colormap",): ramp})
        guide = base.get("legends", {}).get("colorbar", {})
        guide_free = not _manual_layout(base) and not any(key in guide for key in ("position", "orientation", "rect_mm", "length_mm", "thickness_mm", "label_position"))
        guide_patches = {("legends", "colorbar", "position"): "bottom", ("legends", "colorbar", "orientation"): "horizontal"}
        if ramps[0] is not None:
            guide_patches[("colormap",)] = ramps[0]
        add("matrix-bottom-guide", "Same matrix/ramp with a horizontal magnitude guide below the data", guide_patches,
            condition=guide_free, reason="Explicit guide/axes geometry locks guide organization")
    else:
        n = features["group_count"]
        pairs = ("scwat-blue-pink", "scwat-blue-coral") if n <= 2 else (("notch2-balanced", "notch2-bright") if n <= 4 else (("somerville-bright", "easyviz-muted") if n <= 6 else (("okabe-ito",) if n <= 8 else (None,))))
        if color_locked or not n:
            pairs = (None,)
        for index, palette in enumerate(pairs):
            add("scatter-decoding-" + str(index + 1), "Fixed observations with capacity-matched categorical small-mark decoding", {} if palette is None else {("palette",): palette})
        hollow = {("options", "point_style"): "hollow", ("options", "point_edge_width_pt"): .45}
        if pairs[0] is not None:
            hollow[("palette",)] = pairs[0]
        add("scatter-hollow", "Fixed-coordinate observations with an open glyph treatment", hollow, requirements=[(("options", "point_style"), "hollow")])
    if not routes:
        routes.append({"id": "adopted-treatment", "visual_role": "Explicit adopted treatment; automatic role alternatives are locked", "patches": {}})
    return routes, excluded


def _cosmetics(base, features, route):
    result = deepcopy(base)
    if "profile" in base:
        return result
    if result["chart"] != "replicate":
        result = style.apply_defaults(result)
    options = result.setdefault("options", {})
    # Explicit source options survive; the defaults filled by apply_defaults
    # may vary across proposals only where the source never adopted them.
    supplied = base.get("options", {})
    def suggest(key, value):
        if key not in supplied:
            options[key] = value
    def stroke(role, key, value):
        if key == "line_width_pt" and "line_width_pt" in base.get("layout", {}):
            return
        if "profile" not in base and key not in base.get("line_roles", {}).get(role, {}):
            result.setdefault("line_roles", {}).setdefault(role, {})[key] = value
    chart = features["chart"]
    if chart == "distribution":
        suggest("point_layout", "beeswarm")
        if options["point_layout"] == "beeswarm":
            suggest("point_gap_pt", .3)
            suggest("point_max_offset_mm", 1.3 if not features["dense_raw_layer"] else 4)
        if features["kind"] == "box":
            suggest("box_width", .16)
            if not features["dense_raw_layer"]:
                suggest("point_category_offset", .29)
        else:
            suggest("violin_width", .38)
            # Adding an inner summary changes the adopted layer contract, so
            # only refine the appearance of an already requested inner box.
            if supplied.get("violin_inner") == "box":
                suggest("violin_inner_width", .12)
                stroke("data", "line_width_pt", .5)
            if not features["dense_raw_layer"]:
                suggest("point_category_offset", .35)
                if options["point_layout"] == "beeswarm":
                    suggest("point_max_offset_mm", .8)
        if features["dense_raw_layer"]:
            suggest("point_style", "hollow")
        if options.get("point_style") == "hollow":
            suggest("point_edge_width_pt", .45)
    elif chart == "heatmap":
        suggest("cell_aspect", "auto")
        suggest("cell_border_width_pt", 0)
        if options.get("cell_border_width_pt", 0):
            suggest("cell_border_color", "white")
    elif chart == "scatter":
        if not features["group_count"]:
            suggest("point_color", "#3795D3")
        if options["point_style"] == "hollow":
            suggest("point_edge_width_pt", .45)
    else:
        suggest("bar_width", .55)
        if features["mode"] == "grouped":
            suggest("component_gap", .06)
    for path, value in route["patches"].items():
        if _value(base, path) is not _MISSING or (path == ("palette",) and "colors" in base):
            continue
        target = result
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value
    return result


def _manual_layout(spec):
    return "margins" in spec.get("layout", {}) or "main_plot_bbox_mm" in spec.get("legends", {}) or any(isinstance(v, dict) and v.get("position") == "manual" for v in spec.get("legends", {}).values())


def _compact(spec, features, fitted, annotation_minimum):
    """Compact categorical/matrix geometry without changing numeric limits."""
    result = deepcopy(spec)
    if "profile" in spec or _manual_layout(spec):
        return result
    bounds = deepcopy(fitted)
    width, height = spec["layout"]["width_mm"], spec["layout"]["height_mm"]
    available_w = (bounds["right"] - bounds["left"]) * width
    available_h = (bounds["top"] - bounds["bottom"]) * height
    target_w, target_h = available_w, available_h
    if features["chart"] == "distribution":
        # Physical category pitch is explicit evidence, independent of mark
        # size. Few groups no longer occupy the entire broad data region.
        n = features["category_count"] + .2
        pitch = 12 if features["orientation"] == "horizontal" else 15
        if features["dense_raw_layer"]:
            pitch *= 1.35
        if features["orientation"] == "horizontal":
            target_h = min(available_h, n * pitch)
        else:
            target_w = min(available_w, n * pitch)
    elif features["chart"] == "heatmap":
        cell = max(5.5, *annotation_minimum)
        target_w = min(available_w, features["matrix_columns"] * cell)
        target_h = min(available_h, features["matrix_rows"] * cell)
    elif features["chart"] == "replicate":
        target_w = min(available_w, (features["category_count"] + .1) * 18)
    dx, dy = (available_w - target_w) / 2 / width, (available_h - target_h) / 2 / height
    bounds.update(left=bounds["left"] + dx, right=bounds["right"] - dx,
                  bottom=bounds["bottom"] + dy, top=bounds["top"] - dy)
    result["layout"].update(auto_fit=False, margins=bounds)
    return result


def _changes(before, after, prefix=""):
    paths = []
    for key in sorted(set(before) | set(after)):
        path = prefix + "/" + str(key).replace("~", "~0").replace("/", "~1")
        if key not in before or key not in after:
            paths.append(path)
        elif isinstance(before[key], dict) and isinstance(after[key], dict):
            paths.extend(_changes(before[key], after[key], path))
        elif before[key] != after[key]:
            paths.append(path)
    return paths


def _card_ids(features):
    # IDs express eligibility by task/data features, never by showcase filename.
    chart = features["chart"]
    if chart == "distribution":
        if features["kind"] == "violin":
            return ["violin-summary-hierarchy"] if features["inner_summary"] == "box" else []
        return ["distribution-summary-lane"] if features["category_count"] <= 4 else []
    if chart == "heatmap":
        return ["heatmap-tall-narrow"] if features["narrow_matrix"] and features["matrix_rows"] >= features["matrix_columns"] * 2 else []
    if chart == "scatter":
        return ["scatter-small-mark-color"] if features["group_count"] == 2 else []
    return ["replicate-neutral-compact"] if features["mode"] == "summary" and features["uncertainty"] == "sample_sd" and features["category_count"] <= 5 else []


def _color_evidence(source, candidate):
    """Record catalog provenance for actual suggested roles, without web claims."""
    catalog = json.loads((Path(__file__).resolve().parents[1] / "assets/palettes/palettes.json").read_text())
    record = {"origin": "adopted_profile" if "profile" in source else "new_draft_suggestion",
              "role_note": "Categorical assignment follows the unchanged declared order. Raw observations use a supplied point color when present, otherwise the category mapping; neutral role assignments and single-quantity bars are EasyViz adaptations. No numeric scale or fitted line is inferred.",
              "role_colors": {"raw": candidate.get("options", {}).get("point_color"),
                              "bar": candidate.get("options", {}).get("bar_color"),
                              "summary_stroke": candidate.get("line_roles", {}).get("summary", {}).get("color"),
                              "contour_stroke": candidate.get("line_roles", {}).get("data", {}).get("color")},
              "color_paths_changed": [p for p in _changes(source, candidate) if p in ("/palette", "/colormap", "/options/point_color", "/options/bar_color", "/options/bar_edge_color", "/line_roles/data/color", "/line_roles/summary/color")]}
    for key in ("palette", "colormap"):
        name = candidate.get(key)
        if isinstance(name, str) and name in catalog:
            entry = catalog[name]
            record[key] = {"name": name, "origin": "adopted" if key in source else "suggested",
                           **{k: entry[k] for k in ("type", "source", "source_id", "provenance", "adaptation", "note") if k in entry}}
    if "colors" in source:
        record["category_mapping"] = "Preserved explicit/profile colors"
    if source["chart"] == "distribution" and "colors" not in source and "palette" not in source and "profile" not in source and candidate.get("line_roles", {}).get("summary", {}).get("color") == "#333333" and candidate.get("options", {}).get("box_style") == "outline" and "point_color" in candidate.get("options", {}):
        record["area_role"] = "Open neutral summaries use direct category labels for identity. Catalog category colors remain an unused fallback for unfilled bodies; no multicolor mixture is drawn."
    if source["chart"] == "heatmap":
        record["continuous_semantics"] = {"bounds": deepcopy(candidate.get("options", {}).get("color_limits")),
                                          "center": candidate.get("options", {}).get("color_center"),
                                          "note": "A suggested ramp requires already adopted numeric bounds. A diverging suggestion additionally requires an already adopted center; neither is inferred from signs or the data."}
    return record


def create_candidates(data_path, spec_path, out, *, new_draft=False, count=2, render=True):
    """Create a fresh inspectable proposal directory, preserving all inputs."""
    data_path, spec_path, out = Path(data_path), Path(spec_path), Path(out)
    require(new_draft is True, "Declare new_draft=True / --new-draft; accepted panels and Reproduce specifications are outside this helper")
    require(isinstance(count, int) and not isinstance(count, bool) and 1 <= count <= 3, "count must be 1, 2 or 3")
    require(not out.exists() and not out.is_symlink(), f"Output already exists; choose a NEW directory: {out}")
    raw, spec_raw = data_path.read_bytes(), spec_path.read_bytes()
    _, rows = _read_source(raw)
    source_spec = json.loads(spec_raw)
    require(isinstance(source_spec, dict) and source_spec.get("chart") in SUPPORTED, f"Candidate charts are {SUPPORTED}; other charts retain their existing Create workflow")
    require(source_spec["chart"] != "scatter" or "size" not in source_spec.get("fields", {}), "Candidate scatter requires fixed observations; fields.size retains the quantitative-area workflow")
    if source_spec["chart"] == "replicate":
        require("profile" not in source_spec, "Focused replicate renderer does not accept figure profiles; use its explicit adopted layout/typography contract")
        require({"mode", "uncertainty"} <= set(source_spec.get("options", {})), "Replicate candidates require adopted options.mode and options.uncertainty; neither is inferred")
        resolved, profile_record = deepcopy(source_spec), None
        data = replicate.prepare(data_path, resolved)
    else:
        resolved, profile_record = core.resolve_spec(source_spec, spec_path=spec_path)
        # The resolver's adopted bytes are the authority, even if an external
        # writer changes the live profile during subsequent measured planning.
        profile_raw = Path(profile_record["path"]).read_bytes() if profile_record else None
        require(profile_raw is None or _digest(profile_raw) == profile_record["sha256"], "Figure profile changed during resolution; retry from a stable adopted profile")
        data = core.prepare(data_path, resolved)
    require(len(data) == len(rows), "CSV preparation changed the row count")
    features = _features(data, resolved)
    base = deepcopy(resolved)
    layout = base.setdefault("layout", {})
    suggested = []
    for key, value in zip(("width_mm", "height_mm"), _dimensions(features)):
        if key not in layout:
            layout[key] = value
            suggested.append(key)
    layout.setdefault("auto_fit", not _manual_layout(base))
    formats = base.setdefault("formats", ["pdf", "png"])
    if "png" not in formats:
        formats.append("png")
    # All proposals share the same default numeric bounds and measured font.
    choices, excluded = _route_choices(base, features)
    first = _cosmetics(base, features, choices[0])
    fig = None
    try:
        fig, actual_data, actual_layout, typography = _draw(data_path, first)
        if features["chart"] == "replicate":
            actual_data.attrs["candidate_source_path"] = str(data_path)
        baseline = _measure(fig, actual_data, first, typography)
        fitted = actual_layout["margins"]
        annotation_minimum = [0., 0.]
        if features["chart"] == "heatmap":
            cell_min = baseline["cell_annotations"]["minimum_sufficient_cell_dimensions_mm"]
            annotation_minimum = [cell_min["width"], cell_min["height"]]
        if features["chart"] in ("distribution", "scatter"):
            numeric_axes = ("x", "y") if features["chart"] == "scatter" else (("x",) if features["orientation"] == "horizontal" else ("y",))
            for axis in numeric_axes:
                base.setdefault("options", {}).setdefault(axis + "_limits", baseline["numeric_limits"][axis])
    finally:
        if fig is not None:
            core.plt.close(fig)
    plans, seen = [], set()
    for route in choices:
        proposed = _cosmetics(base, features, route)
        fig = None
        try:
            # Guide alternatives need their own measured fit, inside the same
            # adopted canvas. Reusing the first guide's margins would be stale.
            fig, _, proposal_layout, _ = _draw(data_path, proposed)
            fitted = proposal_layout["margins"]
            if features["chart"] == "heatmap":
                minimum = core.annotation_review.check_heatmap_annotations(fig, fig.axes[0])["minimum_sufficient_cell_dimensions_mm"]
                annotation_minimum = [minimum["width"], minimum["height"]]
        finally:
            if fig is not None:
                core.plt.close(fig)
        candidate = _compact(proposed, features, fitted, annotation_minimum)
        fig = None
        try:
            fig, _, _, _ = _draw(data_path, candidate)
            facets = _visual_facets(fig)
        finally:
            if fig is not None:
                core.plt.close(fig)
        fingerprint = json.dumps(facets, sort_keys=True, allow_nan=False)
        if fingerprint in seen:
            excluded.append({"route_id": route["id"], "reasons": ["Same actual mark/color/guide facets as an earlier candidate; width/margin differences alone do not count"]})
            continue
        seen.add(fingerprint)
        plans.append((route, candidate, facets))
        if len(plans) == count:
            break
    # Claim the fresh directory atomically only after input validation/planning.
    out.mkdir(parents=True, exist_ok=False)
    (out / "source.csv").write_bytes(raw)
    (out / "source-spec.json").write_bytes(spec_raw)
    if profile_record:
        (out / "profile.json").write_bytes(profile_raw)
    manifest = {"version": VERSION, "track": "create", "stage": "new_draft", "status": "in_progress",
                "source": {"path": str(data_path.resolve()), "sha256": _digest(raw), "snapshot": "source.csv"},
                "source_spec": {"path": str(spec_path.resolve()), "sha256": _digest(spec_raw), "snapshot": "source-spec.json"},
                "profile": profile_record, "features": features, "suggested_dimension_keys": suggested,
                "baseline_geometry": baseline, "candidates": [], "aesthetic_winner": None,
                "design_space": {"scope": "Limited conditional tool routes, not the complete set of scientifically valid figure designs or a reading-task recommendation",
                                 "eligible_routes": [route["id"] for route in choices], "excluded_routes": excluded,
                                 "requested_count": count, "returned_count": len(plans),
                                 "distinctness_basis": "Actual artist RGBA/quantitative ramp samples and measured guide position/orientation; no width/margin-only count inflation"},
                "note": "Chart/data heuristics propose inspectable designs; technical success does not certify visual quality. Inspect actual candidates and complete visual review before adoption."}
    _json(out / "manifest.json", manifest)
    for ordinal, (route, candidate, facets) in enumerate(plans, 1):
        candidate_id = f"candidate-{ordinal:02d}"
        directory = out / candidate_id
        directory.mkdir()
        runnable = deepcopy(candidate)
        if profile_record:
            runnable["profile"] = "../profile.json"
        _json(directory / "spec.json", runnable)
        record = {"id": candidate_id, "spec": f"{candidate_id}/spec.json", "eligible_design_card_ids": _card_ids(features),
                  "changed_paths": _changes(resolved, candidate),
                  "color_decisions": _color_evidence(resolved, candidate),
                  "route_id": route["id"], "visual_role": route["visual_role"], "visual_facet_evidence": facets,
                  "changed_facets_vs_candidate_01": [key for key in facets if facets[key] != plans[0][2][key]],
                  "reason": route["visual_role"] + ". Measured fit at the adopted science, canvas and fonts; explicit paths remain locked. This limited route is a proposal, not a preferred or exhaustive design.",
                  "technical_review": {"status": "not_rendered", "qa_path": None},
                  "visual_review": {"status": "pending", "review_required": True}}
        fig = None
        try:
            # Actual artist evidence is useful even in spec-only planning mode.
            fig, actual_data, _, typography = _draw(out / "source.csv", candidate)
            if features["chart"] == "replicate":
                actual_data.attrs["candidate_source_path"] = str(out / "source.csv")
            geometry = _measure(fig, actual_data, candidate, typography)
            _json(directory / "geometry-evidence.json", geometry)
            record["geometry_evidence"] = f"{candidate_id}/geometry-evidence.json"
            if geometry["technical_measurement_status"] == "needs_revision":
                record["technical_review"].update(status="needs_revision", measured_issues=geometry["issues"])
        except (ValueError, OSError, ImportError) as exc:
            record["technical_review"].update(status="failed", error=str(exc))
        finally:
            if fig is not None:
                core.plt.close(fig)
        if render and record["technical_review"]["status"] != "failed":
            record["technical_review"]["qa_path"] = f"{candidate_id}/qa.json"
            try:
                if features["chart"] == "replicate":
                    qa = replicate.render(out / "source.csv", runnable, directory, spec_path=directory / "spec.json")
                else:
                    qa = core.render(out / "source.csv", runnable, directory, spec_path=directory / "spec.json", track="create")
                record["technical_review"]["renderer_status"] = qa["status"]
                record["technical_review"]["status"] = qa["status"] if geometry["technical_measurement_status"] == "pass" else "needs_revision"
            except (ValueError, OSError, ImportError) as exc:
                qa = json.loads((directory / "qa.json").read_text()) if (directory / "qa.json").exists() else {"status": "failed"}
                record["technical_review"].update(status="failed", renderer_status=qa["status"], error=str(exc))
        manifest["candidates"].append(record)
        _json(out / "manifest.json", manifest)
    unchanged = data_path.read_bytes() == raw and spec_path.read_bytes() == spec_raw
    if profile_record:
        unchanged &= _digest(Path(profile_record["path"]).read_bytes()) == profile_record["sha256"]
    manifest["inputs_unchanged"] = bool(unchanged)
    manifest["status"] = "visual_review_pending" if unchanged and all(c["technical_review"]["status"] in ("pass", "not_rendered") for c in manifest["candidates"]) else "needs_revision"
    _json(out / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--new-draft", action="store_true", help="Explicit declaration that this is a new Create draft, never an accepted panel")
    parser.add_argument("--count", type=int, choices=(1, 2, 3), default=2, help="Maximum distinct justified candidates")
    parser.add_argument("--no-render", action="store_true", help="Write specs and artist geometry evidence only; exports and visual review remain pending")
    parser.add_argument("--describe-contract", "--describe-spec", action="store_true", help="Print the new-draft candidate contract")
    args = parser.parse_args()
    if args.describe_contract:
        print(json.dumps(CONTRACT, indent=2))
        return
    if not (args.data and args.spec and args.out and args.new_draft):
        parser.error("--data, --spec, --out and --new-draft are required")
    try:
        manifest = create_candidates(args.data, args.spec, args.out, new_draft=args.new_draft, count=args.count, render=not args.no_render)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    print(json.dumps({"status": manifest["status"], "output": str(args.out), "candidate_count": len(manifest["candidates"]), "visual_review": "pending"}))
    if manifest["status"] == "needs_revision":
        parser.exit(2)


if __name__ == "__main__":
    main()
