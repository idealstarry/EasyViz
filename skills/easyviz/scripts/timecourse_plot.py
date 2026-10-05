#!/usr/bin/env python3
"""Plot supplied numerical summaries as unsmoothed lines and uncertainty bands.

One y axis supports multiple series; explicit dual y axes require one series
per axis. No raw-data aggregation, curve fitting or uncertainty calculation.
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

_loader = importlib.util.spec_from_file_location("easyviz_timecourse_core", Path(__file__).with_name("render.py"))
core = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(core)
plt, np, pd = core.plt, core.np, core.pd
SpecError, require, write_json = core.SpecError, core.require, core.write_json
from matplotlib.transforms import Bbox

VERSION = "0.1.0"
OPTIONS = {"x_scale", "x_limits", "x_ticks", "y_scale", "y_limits", "y_ticks",
           "right_y_scale", "right_y_limits", "right_y_ticks", "axis_by_series",
           "curve_line_width_pt", "marker_diameter_pt", "band_alpha", "grid"}
SPEC_KEYS = {"chart", "fields", "uncertainty", "options", "layout", "typography",
             "formats", "order", "labels", "colors", "legends"}
SCHEMA = {
    "chart": "timecourse",
    "fields": {"x": "numeric time or dose", "estimate": "supplied central summary",
               "series": "optional literal category", "sd": "supplied SD OR lower and upper roles",
               "lower": "supplied lower bound", "upper": "supplied upper bound"},
    "uncertainty": {"kind": "sd|supplied_bounds", "label": "explicit uncertainty definition, kept in caption/settings"},
    "colors": {"every series, or all without fields.series": "opaque color"},
    "order": {"series": ["every observed series exactly once"]},
    "options": {"x_scale": "linear|log", "y_scale": "linear|log", "x_limits": ["min", "max"],
                "y_limits": ["min", "max"], "x_ticks": ["numeric"], "y_ticks": ["numeric"],
                "axis_by_series": {"series": "left|right; dual axes require one series each"},
                "right_y_scale": "linear|log", "right_y_limits": ["min", "max"], "right_y_ticks": ["numeric"],
                "curve_line_width_pt": .8, "marker_diameter_pt": 0, "band_alpha": .25, "grid": False},
    "layout": {"width_mm": 100, "height_mm": 76, "font": "Arial", "font_size_pt": 8, "dpi": 300, "auto_fit": True},
    "labels": {"x": "quantity and units", "y": "left quantity and units", "right_y": "required for right axis"},
    "formats": ["pdf", "svg", "png", "tiff"],
    "semantics": ["Each row is a supplied summary; it is not an individual replicate.",
                  "SD is drawn as estimate minus/plus supplied SD; no SEM or CI is inferred.",
                  "Explicit lower/upper values are preserved, including asymmetry.",
                  "Straight line/band edges join adjacent supplied x values, with no fitted model or new measurements.",
                  "Duplicate x within a series is rejected rather than averaged.",
                  "Limits must include every central value and complete band; log axes require strictly positive values.",
                  "Dual-axis heights cannot be compared across their independent scales.",
                  "Titles and statistical explanations belong in a separate caption."]}


def _object(value, allowed, name):
    require(isinstance(value, dict), f"{name} must be an object")
    require(all(isinstance(key, str) for key in value), f"{name} keys must be strings")
    require(not set(value) - allowed, f"Unknown {name} keys: {sorted(set(value) - allowed)}")


def _number(value, name, *, positive=False, nonnegative=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), f"{name} must be a finite JSON number")
    require(not positive or value > 0, f"{name} must be positive")
    require(not nonnegative or value >= 0, f"{name} must be nonnegative")
    return float(value)


def validate_spec(spec):
    _object(spec, SPEC_KEYS, "spec")
    require(spec.get("chart", "timecourse") == "timecourse", "chart must be timecourse")
    fields = spec.get("fields", {})
    _object(fields, {"x", "estimate", "series", "sd", "lower", "upper"}, "fields")
    require({"x", "estimate"} <= set(fields), "fields.x and fields.estimate are required")
    require(all(isinstance(value, str) and value.strip() for value in fields.values()), "fields must map to nonempty column names")
    require(len(set(fields.values())) == len(fields), "Mapped roles must use distinct columns")
    uncertainty = spec.get("uncertainty", {})
    _object(uncertainty, {"kind", "label"}, "uncertainty")
    require(uncertainty.get("kind") in ("sd", "supplied_bounds"), "uncertainty.kind must be sd or supplied_bounds")
    require(isinstance(uncertainty.get("label"), str) and uncertainty["label"].strip(), "uncertainty.label must explicitly define the supplied band")
    require((set(fields) & {"sd", "lower", "upper"}) == ({"sd"} if uncertainty["kind"] == "sd" else {"lower", "upper"}), "Use exactly sd for kind=sd, or lower and upper for kind=supplied_bounds")
    options = spec.get("options", {})
    _object(options, OPTIONS, "options")
    for prefix in ("x", "y", "right_y"):
        scale = options.get(prefix + "_scale", "linear")
        require(scale in ("linear", "log"), f"{prefix}_scale must be linear or log")
        if prefix + "_limits" in options:
            limits = options[prefix + "_limits"]
            require(isinstance(limits, list) and len(limits) == 2, f"{prefix}_limits must contain two numbers")
            low, high = [_number(value, prefix + "_limits", positive=scale == "log") for value in limits]
            require(low < high, f"{prefix}_limits must be strictly ascending")
        if prefix + "_ticks" in options:
            ticks = options[prefix + "_ticks"]
            require(isinstance(ticks, list) and ticks, f"{prefix}_ticks must be a nonempty list")
            for value in ticks:
                _number(value, prefix + "_ticks", positive=scale == "log")
            require(all(a < b for a, b in zip(ticks, ticks[1:])), f"{prefix}_ticks must be unique and ascending")
    _number(options.get("curve_line_width_pt", .8), "curve_line_width_pt", positive=True)
    _number(options.get("marker_diameter_pt", 0), "marker_diameter_pt", nonnegative=True)
    alpha = _number(options.get("band_alpha", .25), "band_alpha", positive=True)
    require(alpha <= 1, "band_alpha must be <= 1")
    require(isinstance(options.get("grid", False), bool), "grid must be boolean")
    _object(spec.get("order", {}), {"series"}, "order")
    if "series" in spec.get("order", {}):
        order = spec["order"]["series"]
        require(isinstance(order, list) and order and all(isinstance(v, str) and v.strip() for v in order) and len(order) == len(set(order)), "order.series must contain distinct nonempty strings")
    _object(spec.get("labels", {}), {"x", "y", "right_y"}, "labels")
    require(all(isinstance(value, str) for value in spec.get("labels", {}).values()), "labels must be text")
    colors = spec.get("colors", {})
    _object(colors, set(colors) if isinstance(colors, dict) else set(), "colors")
    require(spec.get("colors"), "Explicit colors are required")
    try:
        rgba = [core.matplotlib.colors.to_rgba(value) for value in spec["colors"].values()]
    except (ValueError, TypeError):
        raise SpecError("Every color must be valid") from None
    require(all(value[3] == 1 for value in rgba) and len(set(rgba)) == len(rgba), "Series colors must be opaque and distinct")
    core.figure_profile.validate_layout(spec.get("layout", {}))
    core.figure_profile.validate_typography(spec.get("typography", {}))
    _object(spec.get("typography", {}), {"axis", "tick", "legend"}, "typography")
    layout = spec.get("layout", {})
    require(not (layout.get("auto_fit", False) and "margins" in layout), "auto_fit and manual margins conflict")
    _object(spec.get("legends", {}), {"categorical", "review_thresholds"}, "legends")
    guide = spec.get("legends", {}).get("categorical", {})
    require(isinstance(guide, dict), "legends.categorical must be an object")
    require(not set(guide) & {"title", "edgecolor", "linewidth_pt", "markerscale", "allow_plot_overlap"}, "Legend keys must retain curve styling and remain outside the data region")
    formats = spec.get("formats", ["pdf", "svg", "png"])
    require(isinstance(formats, list) and formats and all(isinstance(fmt, str) and fmt in ("pdf", "svg", "png", "tiff") for fmt in formats) and len(formats) == len(set(formats)), "formats must be distinct pdf/svg/png/tiff entries")


def groups(data, spec):
    column = spec["fields"].get("series")
    values = data[column].drop_duplicates().tolist() if column else ["all"]
    adopted = spec.get("order", {}).get("series", values)
    require(set(adopted) == set(values) and len(adopted) == len(values), "order.series must include every observed series exactly once")
    return adopted


def axis_mapping(data, spec):
    order = groups(data, spec)
    mapping = spec.get("options", {}).get("axis_by_series", {group: "left" for group in order})
    require(isinstance(mapping, dict) and set(mapping) == set(order) and all(value in ("left", "right") for value in mapping.values()), "axis_by_series must assign every series to left or right")
    right = "right" in mapping.values()
    require("left" in mapping.values(), "The left axis must contain data")
    if right:
        require(len(order) == 2 and list(mapping.values()).count("left") == 1, "Dual axes require exactly one series on each axis")
        require(spec.get("labels", {}).get("y") and spec.get("labels", {}).get("right_y"), "Dual axes require explicit left and right quantity/unit labels")
        require(not spec.get("legends"), "Dual axes use their colored quantity labels; a separate legend is unsupported")
    else:
        require(not any(key.startswith("right_y") for key in spec.get("options", {})) and "right_y" not in spec.get("labels", {}), "Right-axis settings require an explicitly assigned right series")
        require(len(order) > 1 or not spec.get("legends"), "A single series does not need categorical legend settings")
    return mapping


def prepare(data_path, spec):
    validate_spec(spec)
    data = core.read_source_csv(data_path)
    require(len(data) > 0, "Input must contain summaries")
    require(not any(str(column).startswith("_easyviz_") for column in data.columns), "Input columns with reserved _easyviz_ prefix are unsupported")
    fields = spec["fields"]
    for role, column in fields.items():
        require(column in data.columns, f"Missing {role} column: {column}")
        require(not data[column].str.strip().eq("").any(), f"Empty {column}; summaries cannot be silently dropped")
        if role != "series":
            try:
                values = pd.to_numeric(data[column], errors="raise").to_numpy(float)
            except (ValueError, TypeError):
                raise SpecError(f"{column} must contain finite numeric summaries") from None
            require(np.isfinite(values).all(), f"{column} must contain finite numeric summaries")
            data["_easyviz_" + role] = values
    data["_easyviz_series"] = data[fields["series"]] if "series" in fields else "all"
    data["_easyviz_source_row"] = np.arange(1, len(data) + 1)
    if "sd" in fields:
        require((data["_easyviz_sd"] >= 0).all(), "Supplied SD must be nonnegative")
        data["_easyviz_lower"] = data["_easyviz_estimate"] - data["_easyviz_sd"]
        data["_easyviz_upper"] = data["_easyviz_estimate"] + data["_easyviz_sd"]
    require(np.isfinite(data[["_easyviz_lower", "_easyviz_upper"]].to_numpy(float)).all(), "Entire bands must remain finite")
    require((data["_easyviz_lower"] <= data["_easyviz_estimate"]).all() and (data["_easyviz_estimate"] <= data["_easyviz_upper"]).all(), "Every central estimate must lie inside its supplied band")
    require(not data.duplicated(["_easyviz_series", "_easyviz_x"]).any(), "Duplicate x within a series; resolve aggregation explicitly upstream")
    order, mapping = groups(data, spec), axis_mapping(data, spec)
    require(set(spec["colors"]) == set(order), "colors must map exactly every observed series")
    for group in order:
        subset = data[data["_easyviz_series"] == group]
        require(len(subset) >= 2, f"Series {group} needs at least two distinct x values")
        require(spec.get("options", {}).get("x_scale", "linear") != "log" or (subset["_easyviz_x"] > 0).all(), "Log x requires strictly positive source x values")
        prefix = "y" if mapping[group] == "left" else "right_y"
        require(spec.get("options", {}).get(prefix + "_scale", "linear") != "log" or (subset["_easyviz_lower"] > 0).all(), "Log y requires strictly positive entire bands")
    # Resolve display ranges here, before rendering, to reject clipping early.
    limits(data["_easyviz_x"].to_numpy(float), spec, "x")
    for side in set(mapping.values()):
        subset = data[data["_easyviz_series"].isin([g for g in order if mapping[g] == side])]
        limits(np.r_[subset["_easyviz_lower"], subset["_easyviz_upper"]], spec, "y" if side == "left" else "right_y")
    return data


def limits(values, spec, prefix):
    options = spec.get("options", {})
    minimum, maximum = float(np.min(values)), float(np.max(values))
    if prefix + "_limits" in options:
        low, high = options[prefix + "_limits"]
        require(low <= minimum and maximum <= high, f"{prefix}_limits would clip supplied summaries or bands")
    elif options.get(prefix + "_scale", "linear") == "log":
        low, high = minimum / 1.06, maximum * 1.06
    else:
        padding = (maximum - minimum) * .035 or max(abs(minimum), 1) * .035
        low, high = minimum - padding, maximum + padding
    if prefix + "_ticks" in options:
        require(all(low <= value <= high for value in options[prefix + "_ticks"]), f"{prefix}_ticks must lie within displayed limits")
    return float(low), float(high)


class _LineLegend(core.legend_layout.LegendLayout):
    def _categorical_or_size(self, request, cfg, position, ncol):
        entry = super()._categorical_or_size(request, cfg, position, ncol)
        for handle, color in zip(entry["artist"].legend_handles, request["colors"]):
            handle.set_marker("None")
            handle.set_linestyle("-")
            handle.set_color(color)
            handle.set_linewidth(request["linewidth_pt"])
        entry["chosen_settings"]["key_shape"] = "line"
        return entry


def _dual_fit(fig, axes, padding_mm=2):
    """Measure the union of both axis labels without changing canvas or fonts."""
    pad, width, height = padding_mm * fig.dpi / 25.4, fig.bbox.width, fig.bbox.height
    for _ in range(8):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        plot = axes[0].get_window_extent(renderer)
        tight = Bbox.union([axis.get_tightbbox(renderer) for axis in axes])
        bounds = [pad + max(0, plot.x0 - tight.x0), pad + max(0, plot.y0 - tight.y0),
                  width - pad - max(0, tight.x1 - plot.x1), height - pad - max(0, tight.y1 - plot.y1)]
        require(bounds[2] > bounds[0] and bounds[3] > bounds[1], "Both sets of axis labels cannot fit within the fixed canvas")
        position = [bounds[0] / width, bounds[1] / height, (bounds[2] - bounds[0]) / width, (bounds[3] - bounds[1]) / height]
        old = axes[0].get_position().bounds
        for axis in axes:
            axis.set_position(position)
        if max(abs(a - b) for a, b in zip(position, old)) * max(width, height) < .25:
            break
    fig.canvas.draw()
    position = axes[0].get_position()
    return {"status": "pass", "mode": "both_axis_text_measured", "padding_mm": padding_mm,
            "margins": {"left": position.x0, "right": position.x1, "bottom": position.y0, "top": position.y1}}


def draw(data, spec, layout, typography):
    options, order = spec.get("options", {}), groups(data, spec)
    mapping = axis_mapping(data, spec)
    fig, ax = plt.subplots(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    fig.subplots_adjust(**layout["margins"])
    axes = {"left": ax}
    if "right" in mapping.values():
        axes["right"] = ax.twinx()
        # Equal zorder lets BOTH uncertainty fills sit behind BOTH mean lines.
        # The right quantity uses its own transform while all marks share ax.
        axes["right"].patch.set_visible(False)
    records = []
    width, marker = options.get("curve_line_width_pt", .8), options.get("marker_diameter_pt", 0)
    for group in order:
        part = data[data["_easyviz_series"] == group].sort_values("_easyviz_x", kind="stable")
        side = mapping[group]
        transform = axes[side].transData
        x, center, low, high = [part["_easyviz_" + role].to_numpy(float) for role in ("x", "estimate", "lower", "upper")]
        band = ax.fill_between(x, low, high, facecolor=spec["colors"][group], alpha=options.get("band_alpha", .25), linewidth=0, edgecolor="none", transform=transform, zorder=1)
        line, = ax.plot(x, center, color=spec["colors"][group], linewidth=width, marker="o" if marker else "None", markersize=marker, markeredgewidth=0, markeredgecolor="none", transform=transform, zorder=3)
        line.get_path().should_simplify = False
        for path in band.get_paths():
            path.should_simplify = False
        records.append({"series": group, "side": side, "line": line, "band": band, "source_rows": part["_easyviz_source_row"].astype(int).tolist()})
        if hasattr(core, "figure_elements"):
            pointer = core.figure_elements.pointer
            keys = [{"series": group, "source_rows": records[-1]["source_rows"]}]
            core.figure_elements.register(fig, line, "mean-curve", group, key=group, source_keys=keys,
                spec_paths=[pointer("colors", group), pointer("options", "curve_line_width_pt"), pointer("options", "marker_diameter_pt")], editable=["color", "linewidth", "marker-size"])
            core.figure_elements.register(fig, band, "uncertainty-band", group, key=group, source_keys=keys,
                spec_paths=[pointer("colors", group), pointer("options", "band_alpha")], editable=["color", "opacity"])
    ax.set_xscale(options.get("x_scale", "linear"))
    ax.set_xlim(*limits(data["_easyviz_x"].to_numpy(float), spec, "x"))
    if "x_ticks" in options:
        ax.set_xticks(options["x_ticks"], [f"{value:g}" for value in options["x_ticks"]])
        ax.xaxis.set_minor_formatter(core.matplotlib.ticker.NullFormatter())
    ax.set_xlabel(spec.get("labels", {}).get("x", spec["fields"]["x"]), fontsize=typography["axis"])
    for side, axis in axes.items():
        prefix = "y" if side == "left" else "right_y"
        part = data[data["_easyviz_series"].isin([g for g in order if mapping[g] == side])]
        axis.set_yscale(options.get(prefix + "_scale", "linear"))
        axis.set_ylim(*limits(np.r_[part["_easyviz_lower"], part["_easyviz_upper"]], spec, prefix))
        if prefix + "_ticks" in options:
            axis.set_yticks(options[prefix + "_ticks"], [f"{value:g}" for value in options[prefix + "_ticks"]])
            axis.yaxis.set_minor_formatter(core.matplotlib.ticker.NullFormatter())
        color = spec["colors"][next(g for g in order if mapping[g] == side)] if len(axes) == 2 else "#222222"
        axis.set_ylabel(spec.get("labels", {}).get(prefix, spec["fields"]["estimate"]), fontsize=typography["axis"], color=color)
        axis.spines[side].set_color(color)
        axis.spines["top"].set_visible(False)
        axis.tick_params(axis="y", colors=color, direction="in")
        axis.set_axisbelow(True)
        if hasattr(core, "figure_elements"):
            core.figure_elements.register(fig, axis.yaxis.label, "axis-label", axis.yaxis.label.get_text(), key=["timecourse", side],
                spec_paths=[core.figure_elements.pointer("labels", prefix)], editable=["text"])
    ax.tick_params(axis="x", direction="in")
    ax.spines["right"].set_visible(False)
    if len(axes) == 2:
        axes["right"].spines["left"].set_visible(False)
        axes["right"].spines["bottom"].set_visible(False)
    if options.get("grid", False):
        ax.grid(axis="y", color="#e5e5e5", linewidth=.4, zorder=0)
    legend_config = deepcopy(spec.get("legends", {}))
    manager = _LineLegend(fig, ax, typography, legend_config)
    if len(axes) == 1 and len(order) > 1:
        legend_config.setdefault("categorical", {}).setdefault("key_width_mm", 6)
        manager.add_categorical(order, [spec["colors"][g] for g in order], shape="marker", linewidth_pt=width)
    if layout.get("auto_fit", False):
        fitted = _dual_fit(fig, list(axes.values())) if len(axes) == 2 else core.auto_layout.fit(fig, ax, manager, core.check_tick_label_overlap)
        fig._easyviz_auto_layout = fitted
        layout["margins"] = fitted["margins"]
    else:
        manager.layout()
    fig._easyviz_legend_layout, fig._easyviz_timecourse_artists = manager, records
    fig._easyviz_timecourse_axes = axes
    return fig


def _band_vertices(x, low, high):
    return np.vstack(([x[0], high[0]], np.column_stack((x, low)), [x[-1], high[-1]], np.column_stack((x[::-1], high[::-1])), [x[0], high[0]]))


def audit_source_artists(data_path, spec, fig):
    """Reread source strings and compare actual mean/band vertices in order."""
    source = prepare(data_path, spec)
    issues = []
    records = fig._easyviz_timecourse_artists
    if [record["series"] for record in records] != groups(source, spec):
        issues.append({"code": "series_order_changed"})
    for record in records:
        group = record["series"]
        part = source[source["_easyviz_series"] == group].sort_values("_easyviz_x", kind="stable")
        x, center, low, high = [part["_easyviz_" + role].to_numpy(float) for role in ("x", "estimate", "lower", "upper")]
        line, band = record["line"], record["band"]
        if not np.array_equal(line.get_xydata(), np.column_stack((x, center))):
            issues.append({"code": "mean_coordinates_changed", "series": group})
        paths = band.get_paths()
        expected = _band_vertices(x, low, high)
        if len(paths) != 1 or paths[0].vertices.shape != expected.shape or not np.array_equal(paths[0].vertices, expected):
            issues.append({"code": "band_vertices_changed", "series": group})
        if core.matplotlib.colors.to_rgba(line.get_color()) != core.matplotlib.colors.to_rgba(spec["colors"][group]):
            issues.append({"code": "curve_color_changed", "series": group})
        if line.get_linewidth() != spec.get("options", {}).get("curve_line_width_pt", .8):
            issues.append({"code": "curve_stroke_changed", "series": group})
        if line.get_markersize() != spec.get("options", {}).get("marker_diameter_pt", 0) or line.get_markeredgewidth() != 0:
            issues.append({"code": "sampling_marker_changed", "series": group})
        if band.get_alpha() != spec.get("options", {}).get("band_alpha", .25):
            issues.append({"code": "band_opacity_changed", "series": group})
        expected_color = core.matplotlib.colors.to_rgba(spec["colors"][group])[:3]
        if not len(band.get_facecolors()) or not np.array_equal(band.get_facecolors()[0][:3], expected_color) or np.any(band.get_linewidths() != 0):
            issues.append({"code": "band_color_or_outline_changed", "series": group})
        side = axis_mapping(source, spec)[group]
        if record["side"] != side or line.get_transform() != fig._easyviz_timecourse_axes[side].transData or band.get_transform() != fig._easyviz_timecourse_axes[side].transData:
            issues.append({"code": "axis_assignment_changed", "series": group})
        if record["source_rows"] != part["_easyviz_source_row"].astype(int).tolist():
            issues.append({"code": "source_row_membership_changed", "series": group})
    options = spec.get("options", {})
    left = fig._easyviz_timecourse_axes["left"]
    if left.get_xscale() != options.get("x_scale", "linear") or not np.allclose(left.get_xlim(), limits(source["_easyviz_x"].to_numpy(float), spec, "x"), atol=0, rtol=0):
        issues.append({"code": "x_axis_changed"})
    if "x_ticks" in options and not np.array_equal(left.get_xticks(), options["x_ticks"]):
        issues.append({"code": "x_ticks_changed"})
    for side, axis in fig._easyviz_timecourse_axes.items():
        prefix = "y" if side == "left" else "right_y"
        mapping = axis_mapping(source, spec)
        part = source[source["_easyviz_series"].isin([g for g in groups(source, spec) if mapping[g] == side])]
        expected = limits(np.r_[part["_easyviz_lower"], part["_easyviz_upper"]], spec, prefix)
        if axis.get_yscale() != options.get(prefix + "_scale", "linear") or not np.allclose(axis.get_ylim(), expected, atol=0, rtol=0):
            issues.append({"code": "y_axis_changed", "side": side})
        if prefix + "_ticks" in options and not np.array_equal(axis.get_yticks(), options[prefix + "_ticks"]):
            issues.append({"code": "y_ticks_changed", "side": side})
    return {"status": "pass" if not issues else "needs_revision", "summary_rows_checked": len(source),
            "curves_checked": len(records), "band_endpoints_checked": len(source) * 2, "issues": issues}


def _clipped_text(fig):
    renderer, skipped = fig.canvas.get_renderer(), set()
    for axis in fig.axes:
        for direction in (axis.xaxis, axis.yaxis):
            low, high = sorted(direction.get_view_interval())
            for tick in direction.get_major_ticks() + direction.get_minor_ticks():
                if not low <= tick.get_loc() <= high:
                    skipped.update((tick.label1, tick.label2))
    result = []
    for artist in fig.findobj(core.Text):
        if artist in skipped or not artist.get_visible() or not artist.get_text().strip():
            continue
        bounds = artist.get_window_extent(renderer)
        if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.width + 1 or bounds.y1 > fig.bbox.height + 1:
            result.append({"text": artist.get_text(), "bounds_px": list(map(float, bounds.extents))})
    return result


def _font_evidence(fig):
    """Measure actual post-layout text properties instead of repeating the spec."""
    labels = []

    def add(artist, role, axis_index=None):
        if not artist.get_visible() or not artist.get_text().strip():
            return
        properties = artist.get_fontproperties()
        font_path = core.font_manager.findfont(properties, fallback_to_default=False)
        labels.append({"role": role, "axis_index": axis_index, "text": artist.get_text(),
                       "size_pt": float(artist.get_fontsize()),
                       "family": core.font_manager.FontProperties(fname=font_path).get_name(),
                       "font_file": font_path, "font_sha256": hashlib.sha256(Path(font_path).read_bytes()).hexdigest()})

    for index, axis in enumerate(fig.axes):
        for direction_name in ("x", "y"):
            direction = getattr(axis, direction_name + "axis")
            add(direction.label, direction_name + "_axis_label", index)
            low, high = sorted(direction.get_view_interval())
            for tick in direction.get_major_ticks() + direction.get_minor_ticks():
                if low <= tick.get_loc() <= high:
                    add(tick.label1, direction_name + "_tick", index)
                    add(tick.label2, direction_name + "_tick", index)
    for entry in fig._easyviz_legend_layout.entries:
        for text in entry["artist"].get_texts():
            add(text, "legend")
    return {"measurement": "Actual visible Matplotlib Text properties after final layout; font resolved without fallback",
            "families": sorted({item["family"] for item in labels}),
            "sizes_pt": sorted({item["size_pt"] for item in labels}), "items": labels}


def render(data_path, spec, out, *, spec_path=None, track=None):
    data_path, out = Path(data_path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False})
    fig = None
    try:
        require(track in (None, "create", "reproduce"), "track must be create or reproduce when supplied")
        data = prepare(data_path, spec)
        input_hash = data.attrs["source_csv_sha256"]
        resolved = deepcopy(spec)
        resolved.setdefault("chart", "timecourse")
        resolved.setdefault("layout", {}).setdefault("auto_fit", "margins" not in resolved.get("layout", {}))
        layout, typography, rc = core.setup(resolved)
        rc["path.simplify"] = False
        with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig = draw(data, resolved, layout, typography)
            fig._easyviz_track = track
            fig._easyviz_source_script, fig._easyviz_data_file, fig._easyviz_spec_file = Path(__file__).resolve(), data_path.resolve(), Path(spec_path).resolve() if spec_path else None
            fig._easyviz_source_bindings = {"data_file": {"path": str(data_path.resolve()), "sha256": input_hash}}
            fig.canvas.draw()
            audit = audit_source_artists(data_path, resolved, fig)
            clipped = _clipped_text(fig)
            overlap, oblique = core.check_tick_label_overlap(fig, fig.canvas.get_renderer())
            legend = fig._easyviz_legend_layout.validate()
            exports = core.export(fig, out, resolved, layout)
            readability = core.panel_readability.measure(fig)
            unchanged = hashlib.sha256(data_path.read_bytes()).hexdigest() == input_hash
            missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            fitted = getattr(fig, "_easyviz_auto_layout", None)
            passed = audit["status"] == "pass" and unchanged and not clipped and not overlap and not missing and legend["status"] == "pass" and (not fitted or fitted["status"] == "pass")
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed,
                  "input_rows": len(data), "plotted_summary_rows": sum(len(r["source_rows"]) for r in fig._easyviz_timecourse_artists),
                  "input_sha256": input_hash, "source_unchanged_after_export": unchanged,
                  "source_to_artist_audit": audit, "clipped_text": clipped, "overlapping_tick_labels": overlap,
                  "unchecked_oblique_tick_labels": oblique, "missing_glyphs": missing, "legend_layout": legend,
                  "auto_layout": fitted, "exports": exports, "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "visual_review_required": True}
            qa["readability"] = readability
            qa["rendered_text"] = _font_evidence(fig)
            settings = deepcopy(resolved)
            settings.update(layout=layout, typography=typography, input_file=str(data_path.resolve()), input_sha256=input_hash,
                            supplied_spec=deepcopy(spec), renderer={"version": VERSION, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            "helper_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                              for name in ("render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py", "figure_elements.py", "panel_readability.py", "observation_clipping.py")
                                              if Path(__file__).with_name(name).is_file()}},
                            runtime={"python": platform.python_version(), **{name: package_version(name) for name in ("matplotlib", "numpy", "pandas", "Pillow", "pypdf")}},
                            axis_by_series=axis_mapping(data, spec), auto_layout=fitted,
                            axes={side: {"y_scale": axis.get_yscale(), "y_limits": list(map(float, axis.get_ylim()))} for side, axis in fig._easyviz_timecourse_axes.items()},
                            x_scale=fig.axes[0].get_xscale(), x_limits=list(map(float, fig.axes[0].get_xlim())),
                            curve_interpretation="Straight connections between supplied summaries; no fit or new observations")
            if spec_path:
                settings.update(spec_file=str(Path(spec_path).resolve()), spec_file_sha256=hashlib.sha256(Path(spec_path).read_bytes()).hexdigest())
            settings["source_bindings"] = deepcopy(fig._easyviz_source_bindings)
            write_json(out / "settings.json", settings)
            data.to_csv(out / "plotting-data.csv", index=False)
            write_json(out / "stats.json", {"method": "supplied_summaries", "uncertainty": spec["uncertainty"],
                       "sd_or_bounds_recomputed": False, "raw_observations_inferred": False, "experimental_independence_inferred": False,
                       "tests_performed": False, "model_fitted": False, "smoothing_performed": False,
                       "new_measurements_interpolated": False, "connections": "Straight segments between adjacent supplied x values"})
            write_json(out / "qa.json", qa)
            require(passed, "Source, labels or fixed-canvas QA needs revision; inspect qa.json and the render")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--describe-spec", action="store_true")
    parser.add_argument("--track", choices=("create", "reproduce"), help="Caller-selected track; chart geometry does not select it")
    args = parser.parse_args()
    if args.describe_spec:
        print(json.dumps(SCHEMA, indent=2))
        return
    if not all((args.data, args.spec, args.out)):
        parser.error("--data, --spec and --out are required")
    try:
        spec = json.loads(args.spec.read_text())
    except (ValueError, OSError) as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        write_json(args.out / "qa.json", {"status": "failed", "valid_outputs": False, "error": str(exc)})
        parser.exit(2, f"EasyViz timecourse: {exc}\n")
    try:
        qa = render(args.data, spec, args.out, spec_path=args.spec, track=args.track)
    except (ValueError, OSError, ImportError) as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        if not (args.out / "qa.json").exists():
            write_json(args.out / "qa.json", {"status": "failed", "valid_outputs": False, "error": str(exc)})
        parser.exit(2, f"EasyViz timecourse: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}))


if __name__ == "__main__":
    main()
