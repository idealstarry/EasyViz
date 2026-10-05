#!/usr/bin/env python3
"""Plot supplied numerical estimates and intervals without recalculating them.

Run with --data source.csv --spec interval.json --out output-directory. Copy this
script together with render.py and its sibling helpers for portable execution.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
from importlib.metadata import version as package_version
import json
import math
from pathlib import Path
import platform
import warnings

_loader = importlib.util.spec_from_file_location("easyviz_interval_core", Path(__file__).with_name("render.py"))
core = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(core)
plt, np, pd = core.plt, core.np, core.pd
SpecError = core.SpecError
require, write_json = core.require, core.write_json
from matplotlib.transforms import Affine2D
from matplotlib.markers import MarkerStyle

VERSION = "0.1.0"
REQUIRED = {"label", "estimate", "lower", "upper"}
FIELDS = REQUIRED | {"series", "color", "mark_state"}
OPTIONS = {"x_scale", "x_limits", "x_ticks", "reference_value", "grid", "marker_area_pt2", "series_span", "series_layout", "cap_height", "mark_fill"}
SPEC_KEYS = {"chart", "fields", "options", "layout", "typography", "formats", "order", "labels", "colors", "palette", "legends"}
_HELPER_HASHES = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                  for name in ("render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py", "figure_elements.py", "panel_readability.py", "observation_clipping.py")}
SCHEMA = {
    "chart": "interval", "fields": {"label": "label", "estimate": "estimate", "lower": "lower", "upper": "upper", "series": "optional category", "color": "optional categorical color role", "mark_state": "optional filled/hollow input"},
    "layout": {"width_mm": 88, "height_mm": 88, "font": "Arial", "font_size_pt": 8, "dpi": 300, "auto_fit": True},
    "options": {"x_scale": "linear|log", "reference_value": "optional explicit finite number", "x_limits": ["minimum", "maximum"], "x_ticks": "optional strictly ascending numeric positions, shown as plain numbers", "marker_area_pt2": 20, "series_span": .6, "series_layout": "aligned|blocks", "cap_height": 0, "grid": False, "mark_fill": "all_filled|input|reference_overlap"},
    "order": {"label": ["every label exactly once"], "series": ["every series exactly once"], "color": ["every color category exactly once, if mapped"]},
    "labels": {"x": "axis name and units", "y": "optional", "filled": "optional mark-state legend label", "hollow": "optional mark-state legend label"},
    "colors": {"series label, or row label without a series field": "color"},
    "formats": ["pdf", "svg", "png", "tiff"],
    "semantics": ["Intervals are supplied numerical endpoints, not recomputed confidence intervals.", "No weights, tests, denominators or sample sizes are inferred.", "Sparse label/series combinations remain absent.", "A reference line is drawn only when reference_value is supplied.", "reference_overlap explicitly adopts inclusive lower <= reference <= upper as hollow; it does not establish significance.", "Default estimates are equal-area filled borderless circles; marker_area_pt2 is geometric fill area and raw Matplotlib s=4/pi times that area.", "Titles and narrative are not part of this numerical plotting recipe."],
}


class _IntervalLegendLayout(core.legend_layout.LegendLayout):
    """Keep shared measurement/placement while decoding mixed marker fill states."""

    def _categorical_or_size(self, request, cfg, position, ncol):
        entry = super()._categorical_or_size(request, cfg, position, ncol)
        for handle, state in zip(entry["artist"].legend_handles, request.get("interval_mark_states", [])):
            handle.set_markeredgecolor("none" if state == "filled" else "#666666")
            handle.set_markeredgewidth(0 if state == "filled" else request["linewidth_pt"])
        return entry


def _object(value, allowed, name):
    require(isinstance(value, dict), f"{name} must be an object")
    require(all(isinstance(k, str) for k in value), f"{name} keys must be strings")
    require(not set(value) - allowed, f"Unknown {name} keys: {sorted(set(value) - allowed)}")


def _number(value, name, *, positive=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), f"{name} must be a finite JSON number")
    require(not positive or value > 0, f"{name} must be positive")
    return float(value)


def validate_spec(spec):
    _object(spec, SPEC_KEYS, "spec")
    require(spec.get("chart", "interval") == "interval", "chart must be interval")
    fields = spec.get("fields", {})
    _object(fields, FIELDS, "fields")
    require(REQUIRED <= set(fields), "fields requires label, estimate, lower and upper")
    require(all(isinstance(v, str) and v.strip() for v in fields.values()), "fields must map roles to nonempty column names")
    require(len({fields[r] for r in ("estimate", "lower", "upper")}) == 3, "Estimate and both interval endpoint fields must name distinct source columns")
    require(not ({fields[r] for r in ("estimate", "lower", "upper")} & {column for role, column in fields.items() if role not in ("estimate", "lower", "upper")}), "Numeric interval fields cannot also encode category or mark-state roles")
    options = spec.get("options", {})
    _object(options, OPTIONS, "options")
    require(options.get("x_scale", "linear") in ("linear", "log"), "x_scale must be linear or log")
    require(isinstance(options.get("grid", False), bool), "grid must be a boolean")
    _number(options.get("marker_area_pt2", 20), "marker_area_pt2", positive=True)
    span = _number(options.get("series_span", .6), "series_span", positive=True)
    require(span <= .8, "series_span must be <= 0.8 to keep series inside their label row")
    arrangement = options.get("series_layout", "aligned")
    require(arrangement in ("aligned", "blocks"), "series_layout must be aligned or blocks")
    require(arrangement != "blocks" or "series" in fields, "series_layout=blocks requires fields.series")
    require(arrangement != "blocks" or "series_span" not in options, "series_span applies only to aligned series")
    require("series" not in fields or "color" not in fields or fields["color"] == fields["series"] or arrangement == "blocks", "An independent color role with multiple series requires series_layout=blocks so series identity is directly decoded")
    cap = _number(options.get("cap_height", 0), "cap_height")
    require(0 <= cap <= .2, "cap_height must be between 0 and 0.2 label-row units")
    mode = options.get("mark_fill", "all_filled")
    require(mode in ("all_filled", "input", "reference_overlap"), "mark_fill must be all_filled, input or reference_overlap")
    require(("mark_state" in fields) == (mode == "input"), "fields.mark_state is required only when mark_fill=input; supplied styles cannot be silently ignored")
    require(mode != "reference_overlap" or "reference_value" in options, "reference_overlap requires an explicit reference_value")
    if "reference_value" in options:
        reference = _number(options["reference_value"], "reference_value")
        require(options.get("x_scale") != "log" or reference > 0, "Log reference_value must be strictly positive")
    if "x_limits" in options:
        limits = options["x_limits"]
        require(isinstance(limits, list) and len(limits) == 2, "x_limits must be two finite numbers")
        low, high = [_number(v, "x_limits") for v in limits]
        require(low < high, "x_limits must be strictly ascending")
        require(options.get("x_scale") != "log" or low > 0, "Log x_limits must be strictly positive")
        require("reference_value" not in options or low <= options["reference_value"] <= high, "x_limits would clip the supplied reference_value")
    if "x_ticks" in options:
        ticks = options["x_ticks"]
        require(isinstance(ticks, list) and ticks, "x_ticks must be a nonempty numeric list")
        for value in ticks:
            _number(value, "x_ticks", positive=options.get("x_scale") == "log")
        require(all(a < b for a, b in zip(ticks, ticks[1:])), "x_ticks must be unique and strictly ascending")
        require("x_limits" not in options or all(options["x_limits"][0] <= v <= options["x_limits"][1] for v in ticks), "x_ticks must lie within x_limits")
    order = spec.get("order", {})
    _object(order, {"label", "series", "color"}, "order")
    require("series" not in order or "series" in fields, "order.series requires fields.series")
    require("color" not in order or "color" in fields, "order.color requires fields.color")
    for role, values in order.items():
        require(isinstance(values, list) and all(isinstance(v, str) and v.strip() for v in values), f"order.{role} must be a list of nonempty category strings")
    labels = spec.get("labels", {})
    _object(labels, {"x", "y", "filled", "hollow"}, "labels")
    require(all(isinstance(v, str) for v in labels.values()), "labels must contain strings")
    require(mode != "all_filled" or not ({"filled", "hollow"} & set(labels)), "Mark-state legend labels require an explicit mark_fill semantic")
    for key in ("layout", "typography", "legends"):
        require(isinstance(spec.get(key, {}), dict), f"{key} must be an object")
    formats = spec.get("formats", ["pdf", "png"])
    require(isinstance(formats, list) and formats and all(isinstance(v, str) for v in formats) and len(formats) == len(set(formats)), "formats must be a nonempty list without duplicates")
    require(set(formats) <= {"pdf", "svg", "png", "tiff"}, "Supported formats: pdf, svg, png, tiff")
    # Validate shared layout/types without routing an interval through core chart validation.
    try:
        core.figure_profile.validate_layout(spec.get("layout", {}))
        core.figure_profile.validate_typography(spec.get("typography", {}))
    except core.figure_profile.ConfigurationError as exc:
        raise SpecError(str(exc)) from None


def prepare(data_path, spec):
    """Validate all supplied rows; preserve absent combinations and unused fields."""
    validate_spec(spec)
    data = pd.read_csv(data_path, dtype=object, keep_default_na=False)
    require(len(data) > 0, "Input has no observations")
    require(not any(c.startswith("_easyviz_") for c in data.columns), "Input columns starting _easyviz_ are reserved")
    f, options = spec["fields"], spec.get("options", {})
    for role, column in f.items():
        require(column in data.columns, f"Missing input column for {role}: {column}")
        require(not data[column].astype(str).str.strip().eq("").any(), f"Empty values in {column}; do not invent an interval for a missing row")
    for role in ("estimate", "lower", "upper"):
        try:
            data[f[role]] = pd.to_numeric(data[f[role]], errors="raise")
        except (ValueError, TypeError):
            raise SpecError(f"{f[role]} must contain only numeric values") from None
        require(np.isfinite(data[f[role]].to_numpy(float)).all(), f"Non-finite values in {f[role]}")
    lower, estimate, upper = [data[f[role]].to_numpy(float) for role in ("lower", "estimate", "upper")]
    require(np.all(lower <= estimate) and np.all(estimate <= upper), "Supplied intervals must bracket the estimate: lower <= estimate <= upper")
    if options.get("x_scale", "linear") == "log":
        require(np.all(lower > 0), "Log axes require strictly positive interval endpoints and estimates")
    keys = [f["label"]] + ([f["series"]] if "series" in f else [])
    require(not data.duplicated(keys).any(), "Duplicate label/series rows; each supplied interval needs one unique pair")
    for role in ("label", "series", "color"):
        if role in f:
            core.ordered(data, f[role], spec, role)
    if "mark_state" in f:
        require(data[f["mark_state"]].isin(["filled", "hollow"]).all(), "mark_state values must be filled or hollow")
    if "x_limits" in options:
        low, high = options["x_limits"]
        require(np.all(lower >= low) and np.all(upper <= high), "x_limits would clip supplied interval endpoints")
    data["_easyviz_source_row"] = np.arange(1, len(data) + 1)
    return data


def _states(data, spec):
    f, options = spec["fields"], spec.get("options", {})
    mode = options.get("mark_fill", "all_filled")
    if mode == "input":
        return data[f["mark_state"]].tolist()
    if mode == "reference_overlap":
        ref = options["reference_value"]
        return np.where((data[f["lower"]] <= ref) & (ref <= data[f["upper"]]), "hollow", "filled").tolist()
    return ["filled"] * len(data)


def draw(data, spec, layout, typography):
    """Draw exact source endpoints, recording artists for a separate source audit."""
    f, options, labels = spec["fields"], spec.get("options", {}), spec.get("labels", {})
    label_order = core.ordered(data, f["label"], spec, "label")
    series_order = core.ordered(data, f["series"], spec, "series") if "series" in f else []
    color_order = core.ordered(data, f["color"], spec, "color") if "color" in f else series_order or label_order
    color_field = f.get("color", f.get("series", f["label"]))
    if "color" in f or series_order or "colors" in spec:
        colors = core.palette_colors(spec, color_order)
    else:
        colors = dict.fromkeys(label_order, core.DEFAULT_COLORS[0])
    require(all(core.mcolors.to_rgba(color)[3] > 0 for color in colors.values()),
            "Mapped interval colors must have nonzero alpha; transparent estimates cannot represent supplied rows")
    offsets = dict(zip(series_order, np.linspace(-options.get("series_span", .6) / 2, options.get("series_span", .6) / 2, len(series_order)))) if len(series_order) > 1 else dict.fromkeys(series_order, 0.)
    ymap = dict(zip(label_order, range(len(label_order))))
    ticks, tick_labels, headers, pair_y = list(range(len(label_order))), list(label_order), {}, {}
    if options.get("series_layout", "aligned") == "blocks":
        ticks, tick_labels, cursor = [], [], 0.
        supplied_pairs = set(zip(data[f["label"]], data[f["series"]]))
        for series in series_order:
            ticks.append(cursor)
            tick_labels.append(series)
            headers[cursor] = series
            cursor += 1
            for label in label_order:
                if (label, series) in supplied_pairs:
                    pair_y[(label, series)] = cursor
                    ticks.append(cursor)
                    tick_labels.append(label)
                    cursor += 1
            cursor += .6
    fig, ax = plt.subplots(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    fig.subplots_adjust(**layout["margins"])
    manager = _IntervalLegendLayout(fig, ax, typography, spec.get("legends"))
    ax.set_axisbelow(True)
    if options.get("grid", False):
        ax.grid(axis="x", color="#e5e5e5", linewidth=.4, zorder=0)
    ax.set_xscale(options.get("x_scale", "linear"))
    artists, states, ys = [], _states(data, spec), []
    for row_index, (_, row) in enumerate(data.iterrows()):
        label = str(row[f["label"]])
        series = str(row[f["series"]]) if series_order else None
        y = pair_y[(label, series)] if pair_y else ymap[label] + offsets.get(series, 0.)
        color = colors[str(row[color_field])]
        low, value, high = [float(row[f[role]]) for role in ("lower", "estimate", "upper")]
        line = ax.hlines(y, low, high, colors=color, linewidth=layout["line_width_pt"], zorder=2)
        point = ax.scatter([value], [y], s=4 / math.pi * options.get("marker_area_pt2", 20), marker="o", facecolors=color if states[row_index] == "filled" else "none", edgecolors="none" if states[row_index] == "filled" else color, linewidths=0 if states[row_index] == "filled" else layout["line_width_pt"], zorder=3)
        caps = None
        if options.get("cap_height", 0):
            half = options["cap_height"] / 2
            caps = ax.vlines([low, high], y - half, y + half, colors=color, linewidth=layout["line_width_pt"], zorder=2)
        artists.append({"source_row": row_index + 1, "point": point, "interval": line, "caps": caps})
        ys.append(y)
    data["_easyviz_y"] = ys
    data["_easyviz_mark_state"] = states
    data["_easyviz_marker_area_pt2"] = options.get("marker_area_pt2", 20)
    data["_easyviz_matplotlib_s"] = 4 / math.pi * options.get("marker_area_pt2", 20)
    reference = options.get("reference_value")
    if reference is not None:
        fig._easyviz_reference_artist = ax.axvline(reference, color="#999999", linewidth=layout["line_width_pt"], linestyle="--", zorder=1)
    low, high = float(data[f["lower"]].min()), float(data[f["upper"]].max())
    if reference is not None:
        low, high = min(low, reference), max(high, reference)
    if "x_limits" in options:
        limits = options["x_limits"]
    elif options.get("x_scale", "linear") == "log":
        pad = (math.log(high) - math.log(low)) * .08 if low != high else .1
        limits = [math.exp(math.log(low) - pad), math.exp(math.log(high) + pad)]
    else:
        pad = (high - low) * .08 if low != high else max(1., abs(low) * .08)
        limits = [low - pad, high + pad]
    ax.set_xlim(*limits)
    if "x_ticks" in options:
        require(all(limits[0] <= v <= limits[1] for v in options["x_ticks"]), "x_ticks must lie within the displayed x_limits; supply explicit limits when needed")
        ax.set_xticks(options["x_ticks"], [format(v, ".12g") for v in options["x_ticks"]])
        ax.xaxis.set_minor_formatter(core.matplotlib.ticker.NullFormatter())
    ax.set_ylim(max(ticks) + .5, -.5)
    ax.set_yticks(ticks, tick_labels)
    for position, text in zip(ticks, ax.get_yticklabels()):
        if position in headers:
            text.set_color(colors[headers[position]] if color_field == f["series"] else "#444444")
            text.set_fontweight("bold")
            text.set_fontsize(typography["tick"])
    ax.set_xlabel(labels.get("x", f["estimate"]), fontsize=typography["axis"])
    ax.set_ylabel(labels.get("y", ""), fontsize=typography["axis"])
    ax.spines[["top", "right"]].set_visible(False)
    if series_order and options.get("series_layout", "aligned") != "blocks":
        manager.add_categorical(series_order, [colors[v] for v in series_order], shape="marker", edgecolor="none", linewidth_pt=0)
    elif "color" in f and color_field not in (f["label"], f.get("series")):
        manager.add_categorical(color_order, [colors[v] for v in color_order], shape="marker", edgecolor="none", linewidth_pt=0)
    if options.get("mark_fill", "all_filled") != "all_filled":
        defaults = {"filled": "filled", "hollow": "hollow"} if options["mark_fill"] == "input" else {"filled": "Excludes reference", "hollow": "Includes reference"}
        present = [state for state in ("filled", "hollow") if state in states]
        manager.add_categorical([labels.get(state, defaults[state]) for state in present], ["#666666" if state == "filled" else "none" for state in present], shape="marker", edgecolor="#666666", linewidth_pt=layout["line_width_pt"])
        manager.requests[-1]["interval_mark_states"] = present
    if layout.get("auto_fit", False):
        fig._easyviz_auto_layout = core.auto_layout.fit(fig, ax, manager, core.check_tick_label_overlap)
        layout["margins"] = fig._easyviz_auto_layout["margins"]
    else:
        manager.layout()
    fig._easyviz_legend_layout, fig._easyviz_interval_artists = manager, artists
    return fig, colors


def audit_source_artists(data_path, spec, fig):
    """Independently reread source rows and check actual artist coordinates."""
    raw = pd.read_csv(data_path, dtype=object, keep_default_na=False)
    f, options, issues, rows = spec["fields"], spec.get("options", {}), [], []
    labels = spec.get("order", {}).get("label", list(dict.fromkeys(raw[f["label"]])))
    series = spec.get("order", {}).get("series", list(dict.fromkeys(raw[f["series"]]))) if "series" in f else []
    offsets = np.linspace(-options.get("series_span", .6) / 2, options.get("series_span", .6) / 2, len(series)) if len(series) > 1 else np.zeros(len(series))
    color_field = f.get("color", f.get("series", f["label"]))
    color_categories = spec.get("order", {}).get("color", list(dict.fromkeys(raw[f["color"]]))) if "color" in f else series or labels
    expected_colors = core.palette_colors(spec, color_categories) if "color" in f or series or "colors" in spec else dict.fromkeys(labels, core.DEFAULT_COLORS[0])
    ticks, tick_labels, pairs_y = list(range(len(labels))), list(labels), {}
    if options.get("series_layout", "aligned") == "blocks":
        ticks, tick_labels, cursor = [], [], 0.
        pairs = set(zip(raw[f["label"]], raw[f["series"]]))
        for group in series:
            ticks.append(cursor)
            tick_labels.append(group)
            cursor += 1
            for label in labels:
                if (label, group) in pairs:
                    pairs_y[(label, group)] = cursor
                    ticks.append(cursor)
                    tick_labels.append(label)
                    cursor += 1
            cursor += .6
    records = getattr(fig, "_easyviz_interval_artists", [])
    if sorted(r["source_row"] for r in records) != list(range(1, len(raw) + 1)):
        issues.append({"code": "source_row_count_or_identity"})
    ax, accounted = fig.axes[0], set()
    for record in records:
        number = record["source_row"]
        if not 1 <= number <= len(raw):
            continue
        row = raw.iloc[number - 1]
        expected_y = pairs_y[(row[f["label"]], row[f["series"]])] if pairs_y else labels.index(row[f["label"]]) + (offsets[series.index(row[f["series"]])] if series else 0)
        value, low, high = [float(row[f[role]]) for role in ("estimate", "lower", "upper")]
        point, interval = record["point"], record["interval"]
        expected_segment = np.array([[low, expected_y], [high, expected_y]])
        actual = interval.get_segments()
        if len(actual) != 1 or not np.allclose(actual[0], expected_segment, atol=1e-12, rtol=1e-12):
            issues.append({"code": "interval_endpoint_mismatch", "source_row": number})
        if point.get_offsets().shape != (1, 2) or not np.allclose(point.get_offsets(), [[value, expected_y]], atol=1e-12, rtol=1e-12):
            issues.append({"code": "estimate_coordinate_mismatch", "source_row": number})
        if not np.allclose(point.get_sizes(), [4 / math.pi * options.get("marker_area_pt2", 20)], atol=1e-12, rtol=0):
            issues.append({"code": "marker_area_changed", "source_row": number})
        mode = options.get("mark_fill", "all_filled")
        state = row[f["mark_state"]] if mode == "input" else ("hollow" if mode == "reference_overlap" and low <= options["reference_value"] <= high else "filled")
        color = core.mcolors.to_rgba(expected_colors[row[color_field]])
        filled = len(point.get_facecolors()) > 0 and point.get_facecolors()[0, 3] > 0
        if filled != (state == "filled"):
            issues.append({"code": "mark_state_mismatch", "source_row": number})
        if state == "filled" and (len(point.get_edgecolors()) or np.any(point.get_linewidths() != 0)):
            issues.append({"code": "filled_mark_border_added", "source_row": number})
        if state == "filled" and (len(point.get_facecolors()) != 1 or not np.allclose(point.get_facecolors()[0], color)):
            issues.append({"code": "mark_color_mismatch", "source_row": number})
        if state == "hollow" and (len(point.get_edgecolors()) != 1 or not np.allclose(point.get_edgecolors()[0], color) or not np.allclose(point.get_linewidths(), [spec.get("layout", {}).get("line_width_pt", .6)])):
            issues.append({"code": "hollow_mark_outline_mismatch", "source_row": number})
        if len(interval.get_colors()) != 1 or not np.allclose(interval.get_colors()[0], color):
            issues.append({"code": "interval_color_mismatch", "source_row": number})
        circle = MarkerStyle("o")
        expected_path = circle.get_path().transformed(circle.get_transform())
        actual_paths = point.get_paths()
        if len(actual_paths) != 1 or actual_paths[0].vertices.shape != expected_path.vertices.shape or not np.allclose(actual_paths[0].vertices, expected_path.vertices):
            issues.append({"code": "marker_shape_changed", "source_row": number})
        if point.get_alpha() not in (None, 1):
            issues.append({"code": "marker_alpha_changed", "source_row": number})
        if record["caps"] is not None:
            half = options.get("cap_height", 0) / 2
            expected_caps = [[[x, expected_y - half], [x, expected_y + half]] for x in (low, high)]
            if not np.allclose(record["caps"].get_segments(), expected_caps, atol=1e-12, rtol=1e-12):
                issues.append({"code": "cap_endpoint_mismatch", "source_row": number})
            accounted.add(record["caps"])
        accounted.update((point, interval))
        if point not in ax.collections or interval not in ax.collections:
            issues.append({"code": "source_artist_not_on_axes", "source_row": number})
        rows.append({"source_row": number, "label": row[f["label"]], "series": row[f["series"]] if series else None, "color_category": row[color_field], "estimate": value, "lower": low, "upper": high, "y": float(expected_y), "mark_state": state})
    if set(ax.collections) != accounted:
        issues.append({"code": "unaccounted_data_artist"})
    if [t.get_text() for t in ax.get_yticklabels()] != tick_labels or len(ax.get_yticks()) != len(ticks) or not np.allclose(ax.get_yticks(), ticks):
        issues.append({"code": "row_label_mapping_changed"})
    if ax.get_xscale() != options.get("x_scale", "linear"):
        issues.append({"code": "axis_scale_changed"})
    if "x_ticks" in options and (len(ax.get_xticks()) != len(options["x_ticks"]) or not np.allclose(ax.get_xticks(), options["x_ticks"], atol=1e-12, rtol=0)):
        issues.append({"code": "explicit_tick_positions_changed"})
    left, right = ax.get_xlim()
    if any(float(row[f["lower"]]) < left or float(row[f["upper"]]) > right for _, row in raw.iterrows()):
        issues.append({"code": "axis_limits_hide_source_endpoints"})
    reference = getattr(fig, "_easyviz_reference_artist", None)
    if (reference is None) != ("reference_value" not in options) or (reference is not None and not np.allclose(reference.get_xdata(), options["reference_value"], rtol=0, atol=0)):
        issues.append({"code": "reference_line_mismatch"})
    return {"status": "pass" if not issues else "needs_revision", "source_rows": len(raw), "audited_artist_rows": len(records), "intervals_recomputed": False, "sample_size_inferred": False, "missing_combinations_imputed": False, "rows": rows, "issues": issues}


def _mark_geometry(fig):
    """Check actual final-size circle bounds and cross-row mark collisions."""
    records, shapes, issues = fig._easyviz_interval_artists, [], []
    plot = fig.axes[0].get_window_extent()
    for record in records:
        point = record["point"]
        center = point.get_offset_transform().transform(point.get_offsets())[0]
        matrix = Affine2D(point.get_transforms()[0])
        box = point.get_paths()[0].get_extents(matrix + point.get_transform()).translated(*center)
        box = box.padded(max(point.get_linewidths(), default=0) * fig.dpi / 144)
        shapes.append((record, center, box))
        if box.x0 < plot.x0 - .1 or box.x1 > plot.x1 + .1 or box.y0 < plot.y0 - .1 or box.y1 > plot.y1 + .1:
            issues.append({"code": "estimate_mark_clipped", "source_row": record["source_row"]})
        for role in ("interval", "caps"):
            collection = record[role]
            if collection is None:
                continue
            for j, segment in enumerate(collection.get_segments()):
                a, b, half, cap = _stroke_segment(collection, segment, j, fig)
                delta = b - a
                length = np.linalg.norm(delta)
                direction = delta / length if length else np.array([0., 1.])
                normal = np.array([-direction[1], direction[0]]) * half
                extension = direction * half if cap in ("projecting", "round") else np.zeros(2)
                corners = np.array([a - extension - normal, a - extension + normal,
                                    b + extension - normal, b + extension + normal])
                low, high = corners.min(axis=0), corners.max(axis=0)
                if low[0] < plot.x0 - .1 or high[0] > plot.x1 + .1 or low[1] < plot.y0 - .1 or high[1] > plot.y1 + .1:
                    issues.append({"code": "interval_stroke_clipped", "source_row": record["source_row"], "role": role})
    for i, (record, center, box) in enumerate(shapes):
        rx, ry = box.width / 2, box.height / 2
        for other_record, other_center, other_box in shapes[i + 1:]:
            dx = (center[0] - other_center[0]) / (rx + other_box.width / 2)
            dy = (center[1] - other_center[1]) / (ry + other_box.height / 2)
            if dx * dx + dy * dy < 1:
                issues.append({"code": "estimate_marks_overlap", "source_rows": [record["source_row"], other_record["source_row"]]})
        for other in records:
            if other is record:
                continue
            for collection in (other["interval"], other["caps"]):
                if collection is None:
                    continue
                for j, segment in enumerate(collection.get_segments()):
                    a, b, half, cap = _stroke_segment(collection, segment, j, fig)
                    delta = b - a
                    length = np.linalg.norm(delta)
                    if length:
                        direction = delta / length
                        along = np.dot(center - a, direction)
                        across = abs(np.dot(center - a, [-direction[1], direction[0]]))
                        extension = half if cap == "projecting" else 0
                        distance = math.hypot(max(0, -extension - along, along - length - extension), max(0, across - half))
                        if cap == "round":
                            nearest = a + np.clip(along, 0, length) * direction
                            distance = max(0, np.linalg.norm(nearest - center) - half)
                    else:
                        distance = max(0, np.linalg.norm(center - a) - half)
                    if distance < min(rx, ry):
                        issues.append({"code": "interval_overlaps_other_estimate", "source_rows": [other["source_row"], record["source_row"]]})
    return {"status": "pass" if not issues else "needs_revision", "issues": issues}


def _stroke_segment(collection, segment, index, fig):
    """Final pixel geometry, respecting butt versus extended line ends."""
    a, b = collection.get_transform().transform(segment)
    widths = collection.get_linewidths()
    half = float(widths[index % len(widths)]) * fig.dpi / 144 if len(widths) else 0.
    return a, b, half, collection.get_capstyle() or "butt"


def _clipped_text(fig):
    painter, skipped = fig.canvas.get_renderer(), set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            low, high = sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                    skipped.update((tick.label1, tick.label2))
    result = []
    for artist in fig.findobj(core.Text):
        if artist in skipped or not artist.get_visible() or not artist.get_text().strip():
            continue
        bounds = artist.get_window_extent(painter)
        if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.width + 1 or bounds.y1 > fig.bbox.height + 1:
            result.append({"text": artist.get_text(), "bounds_px": [float(v) for v in bounds.extents]})
    return result


def render(data_path, spec, out, *, spec_path=None):
    """Return QA on success; persist truthful failed QA before raising on failure."""
    data_path, out = Path(data_path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False, "note": "Until this run passes, exports may be stale or unverified."})
    fig = None
    figures_before = set(plt.get_fignums())
    try:
        input_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
        data = prepare(data_path, spec)
        write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False, "input_rows": len(data), "input_sha256": input_hash, "note": "Until this run passes, exports may be stale or unverified."})
        resolved = deepcopy(spec)
        resolved.setdefault("chart", "interval")
        resolved.setdefault("layout", {}).setdefault("auto_fit", "margins" not in resolved.get("layout", {}))
        layout, typography, rc = core.setup(resolved)
        with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig, colors = draw(data, resolved, layout, typography)
            fig.canvas.draw()
            audit = audit_source_artists(data_path, resolved, fig)
            if hashlib.sha256(data_path.read_bytes()).hexdigest() != input_hash:
                audit["status"] = "needs_revision"
                audit["issues"].append({"code": "source_changed_during_render"})
            clipped = _clipped_text(fig)
            overlap, oblique = core.check_tick_label_overlap(fig, fig.canvas.get_renderer())
            legends = fig._easyviz_legend_layout.validate()
            geometry = _mark_geometry(fig)
            fitted = getattr(fig, "_easyviz_auto_layout", None)
            fig._easyviz_data_file = data_path.resolve()
            fig._easyviz_source_script = Path(__file__).resolve()
            fig._easyviz_spec_file = Path(spec_path).resolve() if spec_path else None
            exports = core.export(fig, out, resolved, layout)
            readability = core.panel_readability.measure(fig)
            if hashlib.sha256(data_path.read_bytes()).hexdigest() != input_hash:
                audit["status"] = "needs_revision"
                if not any(item["code"] == "source_changed_during_render" for item in audit["issues"]):
                    audit["issues"].append({"code": "source_changed_during_render"})
            missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            passed = not clipped and not overlap and not missing and all(item["status"] == "pass" for item in (audit, legends, geometry)) and (not fitted or fitted["status"] == "pass")
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "input_rows": len(data), "plotted_input_rows": len(fig._easyviz_interval_artists), "input_sha256": input_hash, "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "clipped_text": clipped, "overlapping_tick_labels": overlap, "unchecked_oblique_tick_labels": oblique, "missing_glyphs": missing, "source_to_artist_audit": audit, "mark_geometry": geometry, "legend_layout": legends, "exports": exports, "visual_review_required": True}
            qa["readability"] = readability
            settings = deepcopy(resolved)
            settings.update(layout=layout, typography=typography, resolved_colors=colors, formats=resolved.get("formats", ["pdf", "png"]), input_file=str(data_path.resolve()), input_sha256=input_hash, supplied_spec=deepcopy(spec), spec_sha256=hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest())
            settings["axis"] = {"x_scale": fig.axes[0].get_xscale(), "x_limits": list(map(float, fig.axes[0].get_xlim())), "explicit_x_ticks": resolved.get("options", {}).get("x_ticks"), "reference_value": resolved.get("options", {}).get("reference_value"), "reference_drawn": "reference_value" in resolved.get("options", {})}
            area = resolved.get("options", {}).get("marker_area_pt2", 20)
            settings["mark_policy"] = {"shape": "circle", "geometric_fill_area_pt2": area, "matplotlib_s": 4 / math.pi * area, "diameter_pt": math.sqrt(4 / math.pi * area), "fill": resolved.get("options", {}).get("mark_fill", "all_filled"), "filled_outline": "none", "hollow_outline": "mapped category color", "reference_overlap_semantics": "inclusive supplied endpoint overlap; no significance inferred" if resolved.get("options", {}).get("mark_fill") == "reference_overlap" else None}
            settings["renderer"] = {"version": VERSION, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "helper_sha256": _HELPER_HASHES}
            settings["runtime"] = {"python": platform.python_version(), **{name: package_version(name) for name in ("matplotlib", "numpy", "pandas", "Pillow", "pypdf")}}
            if spec_path is not None:
                settings["spec_file"], settings["spec_file_sha256"] = str(Path(spec_path).resolve()), hashlib.sha256(Path(spec_path).read_bytes()).hexdigest()
            if fitted:
                qa["auto_layout"] = settings["auto_layout"] = fitted
            settings["legend_layout"] = legends
            data.to_csv(out / "plotting-data.csv", index=False)
            write_json(out / "settings.json", settings)
            write_json(out / "stats.json", {"method": "supplied_intervals", "intervals_recomputed": False, "weights_inferred": False, "sample_size_inferred": False, "tests_performed": False})
            write_json(out / "qa.json", qa)
            require(passed, "Canvas or source-to-artist QA needs revision; inspect qa.json and the exported panel. Preserve final dimensions and fonts or explicitly request a larger panel.")
            return qa
    except Exception as exc:
        status = json.loads((out / "qa.json").read_text())
        if status.get("status") == "in_progress":
            status.update(status="failed", error=str(exc))
            write_json(out / "qa.json", status)
        raise
    finally:
        if fig is not None:
            plt.close(fig)
        for number in set(plt.get_fignums()) - figures_before:
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
        parser.error("--data, --spec and --out are required unless --describe-spec is used")
    try:
        spec = json.loads(args.spec.read_text())
    except (ValueError, OSError) as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        write_json(args.out / "qa.json", {"status": "failed", "valid_outputs": False, "error": str(exc)})
        parser.exit(2, f"EasyViz interval: {exc}\n")
    try:
        qa = render(args.data, spec, args.out, spec_path=args.spec)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"EasyViz interval: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}))


if __name__ == "__main__":
    main()
