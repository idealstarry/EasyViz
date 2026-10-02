#!/usr/bin/env python3
"""Fixed-size replicate bars with raw observations and explicitly defined SD.

Use --data observations.csv --spec replicate.json --out directory. Component
values are never normalized, ratios are never derived, and no tests are run.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from statistics import mean, stdev
import warnings

_loader = importlib.util.spec_from_file_location("easyviz_replicate_core", Path(__file__).with_name("render.py"))
core = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(core)
plt, np, pd, require, SpecError = core.plt, core.np, core.pd, core.require, core.SpecError
VERSION = "0.1.0"
SPEC_KEYS = {"chart", "fields", "options", "layout", "typography", "formats", "order", "labels", "colors", "palette", "legends"}
OPTIONS = {"mode", "uncertainty", "bar_width", "marker_area_pt2", "point_color", "bar_color", "x_rotation", "y_limits", "y_ticks", "grid", "state_hatches"}
SCHEMA = {"chart": "replicate", "fields": {"condition": "condition column", "unit": "replicate identifier", "value": "supplied numeric value", "component": "required for stacked/grouped only", "state": "optional summary-only declared category"},
          "options": {"mode": "stacked|grouped|summary", "uncertainty": "sample_sd|none", "bar_width": .6, "marker_area_pt2": 7, "x_rotation": 0, "y_limits": "optional [low, high] containing all values and SD intervals", "y_ticks": "optional ordered numeric list", "state_hatches": "required complete state-to-hatch map when state is mapped"},
          "layout": {"width_mm": 130, "height_mm": 90, "font": "Arial", "font_size_pt": 8, "dpi": 300, "auto_fit": True},
          "semantics": ["Stacked segments are component means. Points and SD describe per-unit TOTALS, not shifted component observations.", "Grouped bars summarize each component independently; points retain its raw values.", "Summary bars use only the supplied values; a precomputed ratio is never replaced by a ratio of means.", "SD is sample SD (ddof=1), not SEM or a confidence interval. None draws no interval.", "Every condition-unit must have every component exactly once; missing components are rejected, never filled.", "Unit identifiers do not establish biological independence or cross-condition pairing.", "Declared states are retained and decoded using explicit hatches; state labels do not infer significance.", "No normalization, hypothesis tests, titles, or narrative annotations."]}


def _object(value, allowed, name):
    require(isinstance(value, dict), f"{name} must be an object")
    require(not set(value) - allowed, f"Unknown {name} keys: {sorted(set(value) - allowed)}")


def _number(value, name, *, positive=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), f"{name} must be a finite JSON number")
    require(not positive or value > 0, f"{name} must be positive")
    return float(value)


def validate_spec(spec):
    _object(spec, SPEC_KEYS, "spec")
    require(spec.get("chart") == "replicate", "chart must be replicate")
    fields = spec.get("fields", {})
    _object(fields, {"condition", "unit", "component", "value", "state"}, "fields")
    require({"condition", "unit", "value"} <= set(fields), "fields requires condition, unit and value")
    require(all(isinstance(v, str) and v.strip() for v in fields.values()), "fields must name nonempty source columns")
    require(len(set(fields.values())) == len(fields), "Each mapped role must name a distinct source column")
    options = spec.get("options", {})
    _object(options, OPTIONS, "options")
    mode = options.get("mode", "summary")
    require(mode in ("stacked", "grouped", "summary"), "mode must be stacked, grouped or summary")
    require(("component" in fields) == (mode != "summary"), "fields.component is required only for stacked/grouped modes")
    require("state" not in fields or mode == "summary", "fields.state is supported only for summary bars")
    require(options.get("uncertainty", "sample_sd") in ("sample_sd", "none"), "uncertainty must be sample_sd or none")
    require(isinstance(options.get("grid", False), bool), "grid must be a boolean")
    width = _number(options.get("bar_width", .6), "bar_width", positive=True)
    require(width <= .85, "bar_width must be <= 0.85 condition spacing")
    _number(options.get("marker_area_pt2", 7), "marker_area_pt2", positive=True)
    rotation = _number(options.get("x_rotation", 0), "x_rotation")
    require(0 <= rotation <= 90, "x_rotation must be between 0 and 90 degrees")
    for name in ("point_color", "bar_color"):
        if name in options:
            require(core.mcolors.is_color_like(options[name]) and core.mcolors.to_rgba(options[name])[3] > 0, f"{name} must be a visible color")
    if "y_limits" in options:
        require(isinstance(options["y_limits"], list) and len(options["y_limits"]) == 2, "y_limits must contain two numbers")
        low, high = [_number(v, "y_limits") for v in options["y_limits"]]
        require(low < high, "y_limits must be ascending")
    if "y_ticks" in options:
        ticks = options["y_ticks"]
        require(isinstance(ticks, list) and bool(ticks), "y_ticks must be a nonempty list")
        for tick in ticks:
            _number(tick, "y_ticks")
        require(all(a < b for a, b in zip(ticks, ticks[1:])), "y_ticks must be unique and ascending")
    require(("state_hatches" in options) == ("state" in fields), "state_hatches is required only when fields.state is mapped")
    if "state_hatches" in options:
        hatches = options["state_hatches"]
        require(isinstance(hatches, dict) and bool(hatches), "state_hatches must map every supplied state")
        require(all(isinstance(k, str) and k.strip() and isinstance(v, str) and set(v) <= set("/\\|-+x.oO*") for k, v in hatches.items()), "state_hatches values must use valid Matplotlib hatch symbols")
        require(len(set(hatches.values())) == len(hatches), "Each state needs a distinct hatch pattern")
    order = spec.get("order", {})
    _object(order, {"condition", "component", "state"}, "order")
    for role, values in order.items():
        require(role in fields, f"order.{role} requires fields.{role}")
        require(isinstance(values, list) and all(isinstance(v, str) and v.strip() for v in values), f"order.{role} must contain nonempty strings")
    labels = spec.get("labels", {})
    _object(labels, {"x", "y", "states"}, "labels")
    require(all(isinstance(v, str) for k, v in labels.items() if k != "states"), "Axis labels must be strings")
    if "states" in labels:
        require("state" in fields and isinstance(labels["states"], dict), "labels.states requires mapped states")
        require(all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in labels["states"].items()), "labels.states must map states to nonempty text")
    for key in ("layout", "typography", "legends"):
        require(isinstance(spec.get(key, {}), dict), f"{key} must be an object")
    try:
        core.figure_profile.validate_layout(spec.get("layout", {}))
        core.figure_profile.validate_typography(spec.get("typography", {}))
    except core.figure_profile.ConfigurationError as exc:
        raise SpecError(str(exc)) from None
    formats = spec.get("formats", ["pdf", "png"])
    require(isinstance(formats, list) and formats and all(isinstance(v, str) for v in formats) and len(set(formats)) == len(formats) and set(formats) <= {"pdf", "svg", "png", "tiff"}, "formats must list unique supported exports")


def prepare(data_path, spec):
    validate_spec(spec)
    data = pd.read_csv(data_path, dtype=object, keep_default_na=False)
    require(len(data) > 0, "Input has no observations")
    require(not any(c.startswith("_easyviz_") for c in data.columns), "Input columns starting _easyviz_ are reserved")
    fields, options = spec["fields"], spec.get("options", {})
    for role, column in fields.items():
        require(column in data.columns, f"Missing input column for {role}: {column}")
        require(not data[column].astype(str).str.strip().eq("").any(), f"Empty {column}; provide complete prepared observations")
    data["_easyviz_source_value_text"] = data[fields["value"]].astype(str)
    try:
        data[fields["value"]] = pd.to_numeric(data[fields["value"]], errors="raise")
    except (ValueError, TypeError):
        raise SpecError("value must contain finite numbers") from None
    require(np.isfinite(data[fields["value"]].to_numpy(float)).all(), "value must contain finite numbers")
    keys = [fields["condition"], fields["unit"]] + ([fields["component"]] if "component" in fields else [])
    require(not data.duplicated(keys).any(), "Duplicate condition-unit-component observations")
    conditions = core.ordered(data, fields["condition"], spec, "condition")
    if "component" in fields:
        components = core.ordered(data, fields["component"], spec, "component")
        for _, group in data.groupby([fields["condition"], fields["unit"]], sort=False):
            require(set(group[fields["component"]]) == set(components), "Every condition-unit must contain all components exactly once; missing is not zero")
        if options.get("mode") == "stacked":
            require((data[fields["value"]] >= 0).all(), "Stacked components must be nonnegative; no normalization is performed")
    if options.get("uncertainty", "sample_sd") == "sample_sd":
        require(all(data.loc[data[fields["condition"]] == c, fields["unit"]].nunique() >= 2 for c in conditions), "sample_sd needs at least 2 supplied units per condition; use uncertainty=none for one unit")
    if "state" in fields:
        states = core.ordered(data, fields["state"], spec, "state")
        require(set(options["state_hatches"]) == set(states), "state_hatches must cover every observed state exactly")
        if "states" in spec.get("labels", {}):
            require(set(spec["labels"]["states"]) == set(states), "labels.states must cover every observed state exactly")
        require(all(group[fields["state"]].nunique() == 1 for _, group in data.groupby(fields["condition"])), "All units in a condition must have the same declared state")
    data["_easyviz_source_row"] = np.arange(1, len(data) + 1)
    return data


def _groups(data, spec):
    """Summary records are numerical; they do not imply biological independence."""
    f, options = spec["fields"], spec.get("options", {})
    mode, summaries, observations = options.get("mode", "summary"), [], []
    conditions = core.ordered(data, f["condition"], spec, "condition")
    components = core.ordered(data, f["component"], spec, "component") if "component" in f else []
    for condition in conditions:
        selected = data[data[f["condition"]] == condition]
        units = sorted(selected[f["unit"]].unique())
        if mode == "stacked":
            for component in components:
                values = selected.loc[selected[f["component"]] == component, f["value"]].to_numpy(float)
                summaries.append({"condition": condition, "component": component, "n_units": len(units), "mean": float(values.mean()), "sample_sd": None, "kind": "component_mean"})
            values = []
            for unit in units:
                rows = selected[selected[f["unit"]] == unit]
                value = float(rows[f["value"]].sum())
                values.append(value)
                observations.append({"condition": condition, "unit": unit, "component": None, "value": value, "source_rows": rows["_easyviz_source_row"].tolist()})
            summaries.append({"condition": condition, "component": None, "n_units": len(units), "mean": float(np.mean(values)), "sample_sd": float(np.std(values, ddof=1)) if options.get("uncertainty", "sample_sd") == "sample_sd" else None, "kind": "total"})
        else:
            for component in components if mode == "grouped" else [None]:
                rows = selected[selected[f["component"]] == component] if component is not None else selected
                values = rows[f["value"]].to_numpy(float)
                state = str(rows[f["state"]].iloc[0]) if "state" in f else None
                summaries.append({"condition": condition, "component": component, "n_units": len(units), "mean": float(values.mean()), "sample_sd": float(values.std(ddof=1)) if options.get("uncertainty", "sample_sd") == "sample_sd" else None, "kind": mode, "state": state})
                for _, row in rows.iterrows():
                    observations.append({"condition": condition, "unit": row[f["unit"]], "component": component, "value": float(row[f["value"]]), "source_rows": [int(row["_easyviz_source_row"])]})
    return conditions, components, summaries, observations


class _StateLegend(core.legend_layout.LegendLayout):
    def _categorical_or_size(self, request, cfg, position, ncol):
        entry = super()._categorical_or_size(request, cfg, position, ncol)
        for handle, hatch in zip(entry["artist"].legend_handles, request.get("hatches", [])):
            handle.set_hatch(hatch)
        return entry


def draw(data, spec, layout, typography):
    f, options, labels = spec["fields"], spec.get("options", {}), spec.get("labels", {})
    mode = options.get("mode", "summary")
    conditions, components, summaries, observations = _groups(data, spec)
    colors = core.palette_colors(spec, components) if components else (core.palette_colors(spec, conditions) if "colors" in spec else dict.fromkeys(conditions, options.get("bar_color", "#C5C5C5")))
    require(all(core.mcolors.to_rgba(v)[3] > 0 for v in colors.values()), "Bar colors must have nonzero alpha")
    fig, ax = plt.subplots(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    fig.subplots_adjust(**layout["margins"])
    manager = _StateLegend(fig, ax, typography, spec.get("legends"))
    width = options.get("bar_width", .6)
    individual_width = width / len(components) if mode == "grouped" else width
    offsets = dict(zip(components, np.linspace(-width / 2 + individual_width / 2, width / 2 - individual_width / 2, len(components)))) if mode == "grouped" else dict.fromkeys(components, 0.)
    bases, bars, intervals, points = dict.fromkeys(conditions, 0.), [], [], []
    positions = {c: float(i) for i, c in enumerate(conditions)}
    for summary in summaries:
        condition, component = summary["condition"], summary["component"]
        x = positions[condition] + offsets.get(component, 0.)
        if summary["kind"] != "total":
            bottom = bases[condition] if mode == "stacked" else 0.
            state = summary.get("state")
            hatch = options.get("state_hatches", {}).get(state, "")
            patch = ax.bar(x, summary["mean"], bottom=bottom, width=individual_width, color=colors[component if component is not None else condition], edgecolor="#666666" if hatch else "none", linewidth=0, hatch=hatch, zorder=2)[0]
            patch.set_gid(f"easyviz-bar-{len(bars) + 1}")
            bars.append({**summary, "artist": patch, "x": x, "bottom": bottom, "width": individual_width})
            if mode == "stacked":
                bases[condition] += summary["mean"]
        if summary["sample_sd"] is not None:
            low, high = summary["mean"] - summary["sample_sd"], summary["mean"] + summary["sample_sd"]
            interval = ax.vlines(x, low, high, color="#444444", linewidth=layout["line_width_pt"], zorder=3)
            interval.set_gid(f"easyviz-sd-{len(intervals) + 1}")
            intervals.append({**summary, "artist": interval, "x": x, "lower": low, "upper": high})
    for observation in observations:
        c, component = observation["condition"], observation["component"]
        units = sorted(data.loc[data[f["condition"]] == c, f["unit"]].unique())
        spread = np.linspace(-individual_width * .25, individual_width * .25, len(units)) if len(units) > 1 else [0.]
        x = positions[c] + offsets.get(component, 0.) + float(spread[units.index(observation["unit"])])
        point = ax.scatter([x], [observation["value"]], s=core.circle_size_parameter(options.get("marker_area_pt2", 7)), marker="o", color=options.get("point_color", "#333333"), edgecolors="none", linewidths=0, zorder=4)
        point.set_gid(f"easyviz-observation-{len(points) + 1}")
        points.append({**observation, "artist": point, "x": x})
    minimum = min([0.] + [v["value"] for v in observations] + [v["lower"] for v in intervals])
    maximum = max([0.] + [v["value"] for v in observations] + [v["upper"] for v in intervals])
    span = maximum - minimum or max(1., abs(maximum))
    limits = options.get("y_limits", [minimum - span * .04, maximum + span * .09])
    require(limits[0] <= minimum and maximum <= limits[1], "y_limits would hide raw observations, bars or SD endpoints")
    ax.set_ylim(*limits)
    ax.set_xlim(-.55, len(conditions) - .45)
    if "y_ticks" in options:
        require(all(limits[0] <= tick <= limits[1] for tick in options["y_ticks"]), "y_ticks must lie within y_limits")
        ax.set_yticks(options["y_ticks"], [format(v, ".12g") for v in options["y_ticks"]])
    rotation = options.get("x_rotation", 0)
    ax.set_xticks(range(len(conditions)), conditions, rotation=rotation, ha="right" if rotation else "center", rotation_mode="anchor")
    ax.set_xlabel(labels.get("x", ""), fontsize=typography["axis"])
    ax.set_ylabel(labels.get("y", f["value"]), fontsize=typography["axis"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    if options.get("grid", False):
        ax.grid(axis="y", color="#E6E6E6", linewidth=.4, zorder=0)
    if components:
        manager.add_categorical(components, [colors[c] for c in components], shape="patch")
    if "state" in f:
        states = core.ordered(data, f["state"], spec, "state")
        manager.add_categorical([labels.get("states", {}).get(state, state) for state in states], [options.get("bar_color", "#C5C5C5")] * len(states), shape="patch", edgecolor="#666666", linewidth_pt=0)
        manager.requests[-1]["hatches"] = [options["state_hatches"][state] for state in states]
    if layout.get("auto_fit", False):
        fig._easyviz_auto_layout = core.auto_layout.fit(fig, ax, manager, core.check_tick_label_overlap)
        layout["margins"] = fig._easyviz_auto_layout["margins"]
    else:
        manager.layout()
    fig._easyviz_legend_layout = manager
    fig._easyviz_replicate_artists = {"bars": bars, "intervals": intervals, "points": points}
    fig._easyviz_replicate_summary = summaries
    return fig, colors


def audit_source_artists(data_path, spec, fig):
    """Reread CSV and compute expectations with independent Python statistics."""
    import csv
    with Path(data_path).open(newline="") as stream:
        raw = list(csv.DictReader(stream))
    f, options, issues = spec["fields"], spec.get("options", {}), []
    mode = options.get("mode", "summary")
    conditions = spec.get("order", {}).get("condition", list(dict.fromkeys(row[f["condition"]] for row in raw)))
    components = spec.get("order", {}).get("component", list(dict.fromkeys(row[f["component"]] for row in raw))) if "component" in f else []
    artists = fig._easyviz_replicate_artists
    colors = core.palette_colors(spec, components) if components else (core.palette_colors(spec, conditions) if "colors" in spec else dict.fromkeys(conditions, options.get("bar_color", "#C5C5C5")))
    expected, observations = {}, {}
    width = options.get("bar_width", .6)
    individual = width / len(components) if mode == "grouped" else width
    offsets = {component: -width / 2 + individual / 2 + i * individual for i, component in enumerate(components)} if mode == "grouped" else dict.fromkeys(components, 0.)
    for i, condition in enumerate(conditions):
        selected = [(n, row) for n, row in enumerate(raw, 1) if row[f["condition"]] == condition]
        units, bottom = sorted({row[f["unit"]] for _, row in selected}), 0.
        for component in components if components else [None]:
            values = [float(row[f["value"]]) for _, row in selected if component is None or row[f["component"]] == component]
            average = mean(values)
            expected[(condition, component)] = {"mean": average, "sd": stdev(values) if len(values) > 1 else None, "x": i + offsets.get(component, 0.), "bottom": bottom if mode == "stacked" else 0., "state": selected[0][1].get(f.get("state"))}
            bottom += average
        for unit_index, unit in enumerate(units):
            rows = [(n, row) for n, row in selected if row[f["unit"]] == unit]
            delta = -individual * .25 + individual * .5 * unit_index / (len(units) - 1) if len(units) > 1 else 0.
            if mode == "stacked":
                observations[tuple(n for n, _ in rows)] = (i + delta, sum(float(row[f["value"]]) for _, row in rows))
            else:
                for number, row in rows:
                    component = row[f["component"]] if components else None
                    observations[(number,)] = (i + offsets.get(component, 0.) + delta, float(row[f["value"]]))
        if mode == "stacked":
            totals = [sum(float(row[f["value"]]) for _, row in selected if row[f["unit"]] == unit) for unit in units]
            expected[(condition, None)] = {"mean": mean(totals), "sd": stdev(totals) if len(totals) > 1 else None, "x": i, "bottom": 0., "state": None}
    if len(artists["bars"]) != len(conditions) * (len(components) or 1):
        issues.append({"code": "bar_count_mismatch"})
    for record in artists["bars"]:
        exp, patch = expected[(record["condition"], record["component"])], record["artist"]
        values = [patch.get_x() + patch.get_width() / 2, patch.get_y(), patch.get_height(), patch.get_width()]
        if not np.allclose(values, [exp["x"], exp["bottom"], exp["mean"], individual], atol=1e-12, rtol=1e-12):
            issues.append({"code": "bar_mean_or_base_mismatch", "condition": record["condition"], "component": record["component"]})
        if patch.get_hatch() != options.get("state_hatches", {}).get(exp["state"], ""):
            issues.append({"code": "declared_state_mismatch", "condition": record["condition"]})
        expected_color = core.mcolors.to_rgba(colors[record["component"] if record["component"] is not None else record["condition"]])
        if not np.allclose(patch.get_facecolor(), expected_color):
            issues.append({"code": "bar_color_mismatch", "condition": record["condition"]})
    expected_intervals = len(conditions) * (len(components) if mode == "grouped" else 1) if options.get("uncertainty", "sample_sd") == "sample_sd" else 0
    if len(artists["intervals"]) != expected_intervals:
        issues.append({"code": "sd_interval_count_mismatch"})
    for record in artists["intervals"]:
        exp = expected[(record["condition"], record["component"])]
        segment = record["artist"].get_segments()
        wanted = [[exp["x"], exp["mean"] - exp["sd"]], [exp["x"], exp["mean"] + exp["sd"]]]
        if len(segment) != 1 or not np.allclose(segment[0], wanted, atol=1e-12, rtol=1e-12):
            issues.append({"code": "sample_sd_endpoint_mismatch", "condition": record["condition"]})
        if not np.allclose(record["artist"].get_colors(), [core.mcolors.to_rgba("#444444")]):
            issues.append({"code": "sample_sd_color_mismatch", "condition": record["condition"]})
    matched = set()
    for record in artists["points"]:
        key = tuple(record["source_rows"])
        if key not in observations or key in matched:
            issues.append({"code": "raw_observation_identity_mismatch"})
            continue
        matched.add(key)
        point = record["artist"]
        if point.get_offsets().shape != (1, 2) or not np.allclose(point.get_offsets()[0], observations[key], atol=1e-12, rtol=1e-12):
            issues.append({"code": "raw_observation_coordinate_mismatch", "source_rows": list(key)})
        if not np.allclose(point.get_sizes(), [core.circle_size_parameter(options.get("marker_area_pt2", 7))]) or len(point.get_edgecolors()) or np.any(point.get_linewidths()):
            issues.append({"code": "raw_point_geometry_mismatch", "source_rows": list(key)})
        if not np.allclose(point.get_facecolors(), [core.mcolors.to_rgba(options.get("point_color", "#333333"))]):
            issues.append({"code": "raw_point_color_mismatch", "source_rows": list(key)})
        if point.get_alpha() not in (None, 1):
            issues.append({"code": "raw_point_alpha_changed", "source_rows": list(key)})
        from matplotlib.markers import MarkerStyle
        circle = MarkerStyle("o")
        wanted = circle.get_path().transformed(circle.get_transform())
        if len(point.get_paths()) != 1 or point.get_paths()[0].vertices.shape != wanted.vertices.shape or not np.allclose(point.get_paths()[0].vertices, wanted.vertices):
            issues.append({"code": "raw_point_shape_mismatch", "source_rows": list(key)})
    if matched != set(observations):
        issues.append({"code": "raw_observation_count_mismatch"})
    if [label.get_text() for label in fig.axes[0].get_xticklabels()] != conditions:
        issues.append({"code": "condition_label_mapping_mismatch"})
    if set(fig.axes[0].patches) != {record["artist"] for record in artists["bars"]} or set(fig.axes[0].collections) != {record["artist"] for role in ("points", "intervals") for record in artists[role]}:
        issues.append({"code": "unaccounted_or_removed_data_artist"})
    return {"status": "pass" if not issues else "needs_revision", "source_rows": len(raw), "raw_points": len(artists["points"]), "component_values_normalized": False, "ratios_derived": False, "sample_size_independence_inferred": False, "issues": issues}


def _canvas_checks(fig):
    painter, clipped, marks = fig.canvas.get_renderer(), [], []
    skipped = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            low, high = sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                    skipped.update((tick.label1, tick.label2))
    for artist in fig.findobj(core.Text):
        if artist in skipped or not artist.get_visible() or not artist.get_text().strip():
            continue
        bounds = artist.get_window_extent(painter)
        if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.width + 1 or bounds.y1 > fig.bbox.height + 1:
            clipped.append(artist.get_text())
    ax = fig.axes[0]
    box = ax.get_window_extent(painter)
    for record in fig._easyviz_replicate_artists["points"]:
        point = record["artist"]
        center = point.get_offset_transform().transform(point.get_offsets())[0]
        radius = math.sqrt(point.get_sizes()[0]) * fig.dpi / 144
        if center[0] - radius < box.x0 - .1 or center[0] + radius > box.x1 + .1 or center[1] - radius < box.y0 - .1 or center[1] + radius > box.y1 + .1:
            marks.append({"code": "raw_observation_mark_clipped", "source_rows": record["source_rows"]})
    for record in fig._easyviz_replicate_artists["intervals"]:
        artist = record["artist"]
        endpoints = artist.get_transform().transform(artist.get_segments()[0])
        half = max(artist.get_linewidths()) * fig.dpi / 144
        # vlines use butt caps: linewidth expands horizontally, not beyond ends.
        if endpoints[:, 0].min() - half < box.x0 - .1 or endpoints[:, 0].max() + half > box.x1 + .1 or endpoints[:, 1].min() < box.y0 - .1 or endpoints[:, 1].max() > box.y1 + .1:
            marks.append({"code": "sample_sd_stroke_clipped", "condition": record["condition"]})
    return clipped, {"status": "pass" if not marks else "needs_revision", "issues": marks}


def render(data_path, spec, out, *, spec_path=None):
    data_path, out = Path(data_path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    core.write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False, "note": "Exports from previous runs are unverified until this run passes."})
    fig, before = None, set(plt.get_fignums())
    try:
        digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
        data = prepare(data_path, spec)
        resolved = deepcopy(spec)
        resolved.setdefault("layout", {}).setdefault("auto_fit", "margins" not in resolved.get("layout", {}))
        layout, typography, rc = core.setup(resolved)
        with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig, colors = draw(data, resolved, layout, typography)
            fig.canvas.draw()
            audit = audit_source_artists(data_path, resolved, fig)
            clipped, geometry = _canvas_checks(fig)
            overlap, oblique = core.check_tick_label_overlap(fig, fig.canvas.get_renderer())
            legends = fig._easyviz_legend_layout.validate()
            fitted = getattr(fig, "_easyviz_auto_layout", None)
            fig._easyviz_data_file = data_path.resolve()
            fig._easyviz_source_script = Path(__file__).resolve()
            fig._easyviz_spec_file = Path(spec_path).resolve() if spec_path else None
            exports = core.export(fig, out, resolved, layout)
            if hashlib.sha256(data_path.read_bytes()).hexdigest() != digest:
                audit["status"] = "needs_revision"
                audit["issues"].append({"code": "source_changed_during_render"})
            missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            passed = not clipped and not overlap and not missing and all(item["status"] == "pass" for item in (audit, geometry, legends)) and (not fitted or fitted["status"] == "pass")
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "input_rows": len(data), "input_sha256": digest, "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "clipped_text": clipped, "overlapping_tick_labels": overlap, "unchecked_oblique_tick_labels": oblique, "missing_glyphs": missing, "source_to_artist_audit": audit, "mark_geometry": geometry, "legend_layout": legends, "exports": exports, "auto_layout": fitted, "visual_review_required": True}
            settings = deepcopy(resolved)
            settings.update(layout=layout, typography=typography, resolved_colors=colors, input_file=str(data_path.resolve()), input_sha256=digest, supplied_spec=deepcopy(spec), auto_layout=fitted, legend_layout=legends, renderer={"version": VERSION, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "helper_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py", "figure_elements.py")}})
            if spec_path is not None:
                settings["spec_file_sha256"] = hashlib.sha256(Path(spec_path).read_bytes()).hexdigest()
            data.to_csv(out / "plotting-data.csv", index=False)
            core.write_json(out / "summary-data.json", fig._easyviz_replicate_summary)
            core.write_json(out / "stats.json", {"method": "descriptive_mean", "uncertainty": resolved.get("options", {}).get("uncertainty", "sample_sd"), "sd_ddof": 1 if resolved.get("options", {}).get("uncertainty", "sample_sd") == "sample_sd" else None, "stacked_point_and_interval_quantity": "per-unit component total" if resolved.get("options", {}).get("mode") == "stacked" else None, "unit_count_definition": "Number of distinct mapped unit IDs within each condition; biological independence and cross-condition pairing are not inferred.", "tests_performed": False, "ratios_derived": False, "normalization_performed": False})
            core.write_json(out / "settings.json", settings)
            core.write_json(out / "qa.json", qa)
            require(passed, "Source or fixed-canvas QA needs revision; inspect qa.json and actual panel at the requested dimensions and font.")
            return qa
    except Exception as exc:
        qa = json.loads((out / "qa.json").read_text())
        if qa.get("status") == "in_progress":
            qa.update(status="failed", error=str(exc))
            core.write_json(out / "qa.json", qa)
        raise
    finally:
        if fig is not None:
            plt.close(fig)
        for number in set(plt.get_fignums()) - before:
            plt.close(number)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--describe-spec", action="store_true")
    args = parser.parse_args()
    if args.describe_spec:
        print(json.dumps(SCHEMA, indent=2))
        return
    if not all((args.data, args.spec, args.out)):
        parser.error("--data, --spec and --out are required")
    args.out.mkdir(parents=True, exist_ok=True)
    core.write_json(args.out / "qa.json", {"status": "in_progress", "valid_outputs": False})
    try:
        spec = json.loads(args.spec.read_text())
        qa = render(args.data, spec, args.out, spec_path=args.spec)
    except (ValueError, OSError, ImportError) as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        if json.loads((args.out / "qa.json").read_text()).get("status") == "in_progress":
            core.write_json(args.out / "qa.json", {"status": "failed", "valid_outputs": False, "error": str(exc)})
        parser.exit(2, f"EasyViz replicate: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}))


if __name__ == "__main__":
    main()
