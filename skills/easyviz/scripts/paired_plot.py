#!/usr/bin/env python3
"""Plot complete repeated observations with raw-scale medians and IQRs.

Pairing is explicit in unit IDs; it is never guessed from input order. Optional
connectors show within-unit trajectories and do not perform a hypothesis test.
Keep this script together with render.py and its sibling helpers when copying.
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

_loader = importlib.util.spec_from_file_location("easyviz_paired_core", Path(__file__).with_name("render.py"))
core = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(core)
plt, np, pd = core.plt, core.np, core.pd
require, write_json, SpecError = core.require, core.write_json, core.SpecError
from matplotlib.collections import LineCollection

VERSION = "0.1.0"
REQUIRED = {"unit", "condition", "value"}
FIELDS = REQUIRED | {"block"}
OPTIONS = {"y_scale", "y_limits", "y_ticks", "quantile_method", "point_layout", "point_spread", "point_area_pt2", "point_alpha", "point_edge_color", "point_edge_width_pt", "point_color", "connect_pairs", "pair_alpha", "pair_line_width_pt", "summary_color", "summary_width", "summary_cap_width", "summary_line_width_pt", "block_gap", "grid", "seed"}
SPEC_KEYS = {"chart", "fields", "options", "layout", "typography", "formats", "order", "labels", "colors", "palette", "legends"}
HELPERS = ("render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py")
SCHEMA = {
    "chart": "paired", "fields": {"unit": "participant ID", "condition": "time point or repeated condition", "value": "raw numerical measurement", "block": "optional mutually exclusive group"},
    "layout": {"width_mm": 88, "height_mm": 88, "font": "Arial", "font_size_pt": 8, "dpi": 300, "auto_fit": True},
    "options": {"y_scale": "linear|log", "y_limits": "optional two ascending limits containing all values", "y_ticks": "optional ascending numeric positions", "quantile_method": "linear|weibull", "point_layout": "swarm|jitter", "point_spread": .7, "point_area_pt2": 10, "point_alpha": 1, "point_edge_width_pt": 0, "point_edge_color": "#777777", "point_color": "#0072B2 (only without block)", "connect_pairs": False, "pair_alpha": .18, "pair_line_width_pt": .4, "summary_color": "#222222", "summary_width": .7, "summary_cap_width": .22, "summary_line_width_pt": .8, "block_gap": .4, "seed": 0, "grid": False},
    "order": {"condition": ["every condition exactly once"], "block": ["every block exactly once, if mapped"]},
    "labels": {"x": "optional", "y": "measurement and units"}, "colors": {"block label": "categorical color"},
    "formats": ["pdf", "svg", "png", "tiff"],
    "semantics": ["Two or more repeated conditions are supported; each unit must have exactly one value for every condition within its block.", "An ID belongs to one block; namespace separate studies' IDs before combining them.", "Medians and quartiles are computed on raw values; log display does not transform the summary calculation.", "IQRs describe the observations, not confidence intervals.", "No sample pairing, missing measurements, p-values, or tests are inferred.", "Swarm placement is measured after fitting the fixed-size canvas; a cloud that cannot fit fails rather than dropping or shrinking points.", "Jitter is deterministic and shared within each unit; point overlaps remain possible and require visual review.", "Circle area is geometric fill area; raw Matplotlib s is 4/pi times that area.", "Default points are borderless; reference-specific thin outlines are explicit options."]}


def _object(value, allowed, name):
    require(isinstance(value, dict), f"{name} must be an object")
    require(all(isinstance(k, str) for k in value), f"{name} keys must be strings")
    require(not set(value) - allowed, f"Unknown {name} keys: {sorted(set(value) - allowed)}")


def _number(value, name, *, minimum=None, strict=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), f"{name} must be a finite JSON number")
    if minimum is not None:
        require(value > minimum if strict else value >= minimum, f"{name} must be {'greater than' if strict else 'at least'} {minimum}")
    return float(value)


def validate_spec(spec):
    _object(spec, SPEC_KEYS, "spec")
    require(spec.get("chart", "paired") == "paired", "chart must be paired")
    fields = spec.get("fields", {})
    _object(fields, FIELDS, "fields")
    require(REQUIRED <= set(fields), "fields requires unit, condition and value")
    require(all(isinstance(v, str) and v.strip() for v in fields.values()), "fields must map roles to nonempty column names")
    require(len(set(fields.values())) == len(fields), "Unit, condition, value and optional block must name distinct source columns")
    opts = spec.get("options", {})
    _object(opts, OPTIONS, "options")
    require(opts.get("y_scale", "linear") in ("linear", "log"), "y_scale must be linear or log")
    require(opts.get("quantile_method", "linear") in ("linear", "weibull"), "quantile_method must be linear or weibull")
    require(opts.get("point_layout", "swarm") in ("swarm", "jitter"), "point_layout must be swarm or jitter")
    for key in ("grid", "connect_pairs"):
        require(isinstance(opts.get(key, False), bool), f"{key} must be a boolean")
    for key, default in (("point_area_pt2", 10), ("summary_line_width_pt", .8), ("pair_line_width_pt", .4)):
        _number(opts.get(key, default), key, minimum=0, strict=True)
    for key, default in (("point_alpha", 1), ("pair_alpha", .18)):
        require(0 < _number(opts.get(key, default), key) <= 1, f"{key} must be greater than zero and at most one")
    for key, default in (("point_spread", .7), ("summary_width", .7), ("summary_cap_width", .22)):
        require(0 < _number(opts.get(key, default), key) <= .9, f"{key} must be greater than zero and at most 0.9 condition units")
    require(opts.get("summary_cap_width", .22) <= opts.get("summary_width", .7), "summary_cap_width cannot exceed summary_width")
    _number(opts.get("point_edge_width_pt", 0), "point_edge_width_pt", minimum=0)
    require(0 <= _number(opts.get("block_gap", .4), "block_gap") <= 2, "block_gap must be between zero and two condition units")
    seed = opts.get("seed", 0)
    require(isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed < 2 ** 32, "seed must be an integer in 0..2**32-1")
    for key, default in (("point_color", "#0072B2"), ("point_edge_color", "#777777"), ("summary_color", "#222222")):
        color = opts.get(key, default)
        require(core.mcolors.is_color_like(color), f"{key} must be a valid color")
        require(core.mcolors.to_rgba(color)[3] > 0, f"{key} cannot be fully transparent")
    require("point_color" not in opts or "block" not in fields, "point_color applies only without fields.block; use colors for mapped blocks")
    if "y_limits" in opts:
        limits = opts["y_limits"]
        require(isinstance(limits, list) and len(limits) == 2, "y_limits must be two finite numbers")
        low, high = [_number(v, "y_limits") for v in limits]
        require(low < high, "y_limits must be strictly ascending")
        require(opts.get("y_scale") != "log" or low > 0, "Log y_limits must be strictly positive")
    if "y_ticks" in opts:
        ticks = opts["y_ticks"]
        require(isinstance(ticks, list) and bool(ticks), "y_ticks must be a nonempty numeric list")
        for value in ticks:
            _number(value, "y_ticks", minimum=0 if opts.get("y_scale") == "log" else None, strict=opts.get("y_scale") == "log")
        require(all(a < b for a, b in zip(ticks, ticks[1:])), "y_ticks must be strictly ascending")
        require("y_limits" not in opts or all(opts["y_limits"][0] <= value <= opts["y_limits"][1] for value in ticks), "y_ticks must lie within y_limits")
    order = spec.get("order", {})
    _object(order, {"condition", "block"}, "order")
    require("block" not in order or "block" in fields, "order.block requires fields.block")
    for role, values in order.items():
        require(isinstance(values, list) and bool(values) and all(isinstance(v, str) and v.strip() for v in values), f"order.{role} must list nonempty category strings")
    labels = spec.get("labels", {})
    _object(labels, {"x", "y"}, "labels")
    require(all(isinstance(v, str) for v in labels.values()), "labels must contain strings")
    for key in ("layout", "typography", "legends"):
        require(isinstance(spec.get(key, {}), dict), f"{key} must be an object")
    if "colors" in spec:
        require("block" in fields, "colors requires fields.block")
        require(isinstance(spec["colors"], dict), "colors must map block labels to colors")
    require("palette" not in spec or "block" in fields, "palette requires fields.block")
    formats = spec.get("formats", ["pdf", "png"])
    require(isinstance(formats, list) and bool(formats) and all(v in ("pdf", "svg", "png", "tiff") for v in formats), "formats must list pdf, svg, png and/or tiff")
    require(len(set(formats)) == len(formats), "formats cannot contain duplicates")


def prepare(data_path, spec):
    """Reject ambiguous, duplicate, incomplete and non-finite repeated measures."""
    validate_spec(spec)
    data = pd.read_csv(data_path, dtype=object, keep_default_na=False)
    require(len(data) > 0, "Input has no observations")
    require(not any(c.startswith("_easyviz_") for c in data.columns), "Input columns starting _easyviz_ are reserved")
    fields, opts = spec["fields"], spec.get("options", {})
    for role, column in fields.items():
        require(column in data, f"Missing input column for {role}: {column}")
        require(not data[column].astype(str).str.strip().eq("").any(), f"Empty values in {column}; no measurement or pairing is inferred")
    data["_easyviz_source_value_text"] = data[fields["value"]].astype(str)
    try:
        data[fields["value"]] = pd.to_numeric(data[fields["value"]], errors="raise")
    except (ValueError, TypeError):
        raise SpecError(f"{fields['value']} must contain only numeric values") from None
    values = data[fields["value"]].to_numpy(float)
    require(np.isfinite(values).all(), "Measurements must all be finite")
    require(opts.get("y_scale") != "log" or (values > 0).all(), "Log display requires strictly positive measurements; no pseudocount is added")
    conditions = core.ordered(data, fields["condition"], spec, "condition")
    require(len(conditions) >= 2, "Paired observations require at least two conditions")
    data["_easyviz_block"] = data[fields["block"]] if "block" in fields else "Observations"
    if "block" in fields:
        core.ordered(data, fields["block"], spec, "block")
        require((data.groupby(fields["unit"])["_easyviz_block"].nunique() == 1).all(), "Each unit ID must belong to one block; namespace IDs from separate studies explicitly")
    keys = ["_easyviz_block", fields["unit"], fields["condition"]]
    require(not data.duplicated(keys).any(), "Duplicate unit/condition observations; aggregate technical repeats explicitly before plotting")
    counts = data.groupby(["_easyviz_block", fields["unit"]], sort=False)[fields["condition"]].nunique()
    require((counts == len(conditions)).all(), "Incomplete repeated measurements: every unit must have exactly one value for every declared condition; no pair is dropped or filled")
    if "y_limits" in opts:
        require((values >= opts["y_limits"][0]).all() and (values <= opts["y_limits"][1]).all(), "y_limits would clip source measurements")
    data["_easyviz_source_row"] = np.arange(1, len(data) + 1)
    return data


def _stable_fraction(block, unit, seed):
    digest = hashlib.sha256(json.dumps([str(block), str(unit), seed], ensure_ascii=False).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2 ** 64


def _swarm_offsets(cell, center, ax, area, edge_width, spread, seed, fields):
    """Greedy pixel-space packing, stable under row reordering and role renaming."""
    separation = (math.sqrt(4 / math.pi * area) + edge_width + .15) * ax.figure.dpi / 72
    cx = ax.transData.transform([center, float(cell.iloc[0][fields["value"]])])[0]
    max_dx = abs(ax.transData.transform([center + spread / 2, float(cell.iloc[0][fields["value"]])])[0] - cx)
    placed, offsets = [], {}
    ordered = cell.sort_values([fields["value"], fields["unit"]], kind="stable")
    for _, row in ordered.iterrows():
        y = ax.transData.transform([center, float(row[fields["value"]])])[1]
        active = [(x, py) for x, py in placed if abs(py - y) < separation]
        candidates = [0.]
        for x, py in active:
            dx = math.sqrt(max(0., separation ** 2 - (py - y) ** 2)) + 1e-6
            candidates.extend([x - dx, x + dx])
        preference = -1 if _stable_fraction(row["_easyviz_block"], row[fields["unit"]], seed) < .5 else 1
        candidates.sort(key=lambda x: (abs(x), 0 if x * preference >= 0 else 1))
        feasible = [x for x in candidates if abs(x) <= max_dx + 1e-6 and all(math.hypot(x - px, y - py) >= separation - 1e-6 for px, py in active)]
        require(bool(feasible), "Swarm cannot fit all source points at the adopted area and canvas; increase the panel width/height or explicitly adopt jitter, preserving all observations")
        x = feasible[0]
        placed.append((x, y))
        offsets[int(row["_easyviz_source_row"])] = float(ax.transData.inverted().transform([cx + x, y])[0] - center)
    return offsets


def draw(data, spec, layout, typography):
    fields, opts, labels = spec["fields"], spec.get("options", {}), spec.get("labels", {})
    conditions = core.ordered(data, fields["condition"], spec, "condition")
    blocks = core.ordered(data, fields["block"], spec, "block") if "block" in fields else ["Observations"]
    colors = core.palette_colors(spec, blocks) if "block" in fields else {"Observations": opts.get("point_color", "#0072B2")}
    require(all(core.mcolors.to_rgba(v)[3] > 0 for v in colors.values()), "Block colors cannot be fully transparent")
    centers = {(block, condition): i * (len(conditions) + opts.get("block_gap", .4)) + j for i, block in enumerate(blocks) for j, condition in enumerate(conditions)}
    fig, ax = plt.subplots(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    fig.subplots_adjust(**layout["margins"])
    manager = core.legend_layout.LegendLayout(fig, ax, typography, spec.get("legends"))
    ax.set_axisbelow(True)
    if opts.get("grid", False):
        ax.grid(axis="y", color="#e5e5e5", linewidth=.4, zorder=0)
    ax.set_yscale(opts.get("y_scale", "linear"))
    values = data[fields["value"]].to_numpy(float)
    low, high = float(values.min()), float(values.max())
    if "y_limits" in opts:
        limits = opts["y_limits"]
    elif opts.get("y_scale") == "log":
        span = math.log(high) - math.log(low)
        pad = span * .1 if span else .15
        limits = [math.exp(math.log(low) - pad), math.exp(math.log(high) + pad)]
    else:
        pad = (high - low) * .1 if high != low else max(1., abs(low) * .1)
        limits = [low - pad, high + pad]
    ax.set_ylim(*limits)
    if "y_ticks" in opts:
        require(all(limits[0] <= v <= limits[1] for v in opts["y_ticks"]), "y_ticks lie outside displayed limits; supply appropriate y_limits")
        if opts.get("y_scale") == "log":
            ax.yaxis.set_major_locator(core.matplotlib.ticker.FixedLocator(opts["y_ticks"]))
            ax.yaxis.set_major_formatter(core.matplotlib.ticker.LogFormatterMathtext(base=10))
        else:
            ax.set_yticks(opts["y_ticks"])
        ax.yaxis.set_minor_formatter(core.matplotlib.ticker.NullFormatter())
    ax.set_xlim(-.65, max(centers.values()) + .65)
    ax.set_xticks(list(centers.values()), [condition for _, condition in centers])
    ax.set_xlabel(labels.get("x", ""), fontsize=typography["axis"])
    ax.set_ylabel(labels.get("y", fields["value"]), fontsize=typography["axis"])
    ax.spines[["top", "right"]].set_visible(False)
    if "block" in fields and len(blocks) > 1:
        edge = opts.get("point_edge_width_pt", 0)
        manager.add_categorical(blocks,
                                [core.mcolors.to_rgba(colors[v], alpha=opts.get("point_alpha", 1)) for v in blocks],
                                shape="marker", edgecolor=opts.get("point_edge_color", "#777777") if edge else "none",
                                linewidth_pt=edge)
    if layout.get("auto_fit", False):
        fig._easyviz_auto_layout = core.auto_layout.fit(fig, ax, manager, core.check_tick_label_overlap)
        layout["margins"] = fig._easyviz_auto_layout["margins"]
    else:
        manager.layout()
    fig.canvas.draw()
    artists, summaries, point_map = [], [], {}
    area, edge = opts.get("point_area_pt2", 10), opts.get("point_edge_width_pt", 0)
    spread, seed = opts.get("point_spread", .7), opts.get("seed", 0)
    x_by_row = {}
    for block in blocks:
        for condition in conditions:
            center = centers[(block, condition)]
            cell = data.loc[(data["_easyviz_block"] == block) & (data[fields["condition"]] == condition)].sort_values([fields["value"], fields["unit"]], kind="stable")
            if opts.get("point_layout", "swarm") == "swarm":
                offsets = _swarm_offsets(cell, center, ax, area, edge, spread, seed, fields)
            else:
                offsets = {int(row["_easyviz_source_row"]): (_stable_fraction(block, row[fields["unit"]], seed) - .5) * spread for _, row in cell.iterrows()}
            xs = [center + offsets[int(row["_easyviz_source_row"])] for _, row in cell.iterrows()]
            ys = cell[fields["value"]].to_numpy(float)
            point = ax.scatter(xs, ys, s=core.circle_size_parameter(area), marker="o", c=colors[block], alpha=opts.get("point_alpha", 1), edgecolors=opts.get("point_edge_color", "#777777") if edge else "none", linewidths=edge, zorder=2)
            rows = list(map(int, cell["_easyviz_source_row"]))
            artists.append({"block": block, "condition": condition, "source_rows": rows, "point": point, "center": center})
            for (_, row), x, y in zip(cell.iterrows(), xs, ys):
                point_map[(block, str(row[fields["unit"]]), condition)] = (float(x), float(y))
                x_by_row[int(row["_easyviz_source_row"])] = x
            q1, median, q3 = np.quantile(ys, [.25, .5, .75], method=opts.get("quantile_method", "linear"))
            width, cap = opts.get("summary_width", .7), opts.get("summary_cap_width", .22)
            horizontal = ax.hlines([median, q1, q3], [center - width / 2, center - cap / 2, center - cap / 2], [center + width / 2, center + cap / 2, center + cap / 2], colors=opts.get("summary_color", "#222222"), linewidth=opts.get("summary_line_width_pt", .8), zorder=3)
            vertical = ax.vlines(center, q1, q3, colors=opts.get("summary_color", "#222222"), linewidth=opts.get("summary_line_width_pt", .8), zorder=3)
            summaries.append({"block": block, "condition": condition, "n": len(cell), "q1": float(q1), "median": float(median), "q3": float(q3), "horizontal": horizontal, "vertical": vertical, "center": center})
    segments, pair_keys = [], []
    if opts.get("connect_pairs", False):
        pair_colors = []
        for block in blocks:
            units = sorted(data.loc[data["_easyviz_block"] == block, fields["unit"]].unique())
            for unit in units:
                for first, second in zip(conditions, conditions[1:]):
                    segments.append([point_map[(block, unit, first)], point_map[(block, unit, second)]])
                    pair_keys.append((block, unit, first, second))
                    pair_colors.append(colors[block])
        connectors = LineCollection(segments, colors=pair_colors, linewidths=opts.get("pair_line_width_pt", .4), alpha=opts.get("pair_alpha", .18), zorder=1)
        ax.add_collection(connectors)
    else:
        connectors = None
    data["_easyviz_x"] = data["_easyviz_source_row"].map(x_by_row)
    data["_easyviz_marker_area_pt2"] = area
    data["_easyviz_matplotlib_s"] = core.circle_size_parameter(area)
    fig._easyviz_paired_artists, fig._easyviz_paired_summaries = artists, summaries
    fig._easyviz_paired_connectors, fig._easyviz_paired_keys = connectors, pair_keys
    fig._easyviz_legend_layout = manager
    return fig, colors


def audit_source_artists(data_path, spec, fig):
    """Reread the source and compare actual mark, summary, and connector values."""
    source, issues = prepare(data_path, spec), []
    fields, opts = spec["fields"], spec.get("options", {})
    conditions = core.ordered(source, fields["condition"], spec, "condition")
    blocks = core.ordered(source, fields["block"], spec, "block") if "block" in fields else ["Observations"]
    centers = {(block, condition): i * (len(conditions) + opts.get("block_gap", .4)) + j for i, block in enumerate(blocks) for j, condition in enumerate(conditions)}
    colors = core.palette_colors(spec, blocks) if "block" in fields else {"Observations": opts.get("point_color", "#0072B2")}
    by_row = source.set_index("_easyviz_source_row")
    seen, point_map = [], {}
    for entry in fig._easyviz_paired_artists:
        actual = np.asarray(entry["point"].get_offsets(), dtype=float)
        rows = entry["source_rows"]
        if len(actual) != len(rows):
            issues.append({"code": "point_count_changed", "block": entry["block"], "condition": entry["condition"]})
            continue
        for source_row, (x, y) in zip(rows, actual):
            row = by_row.loc[source_row]
            seen.append(source_row)
            expected_center = centers[(row["_easyviz_block"], row[fields["condition"]])]
            if row["_easyviz_block"] != entry["block"] or row[fields["condition"]] != entry["condition"] or not math.isclose(y, float(row[fields["value"]]), rel_tol=1e-12, abs_tol=1e-12) or abs(x - expected_center) > opts.get("point_spread", .7) / 2 + 1e-9 or not math.isclose(entry["center"], expected_center, abs_tol=1e-12):
                issues.append({"code": "source_point_mismatch", "source_row": source_row})
            point_map[(entry["block"], row[fields["unit"]], entry["condition"])] = [float(x), float(y)]
        sizes = entry["point"].get_sizes()
        if not np.allclose(sizes, core.circle_size_parameter(opts.get("point_area_pt2", 10)), rtol=1e-12, atol=1e-12):
            issues.append({"code": "point_area_changed"})
        rgba = list(core.mcolors.to_rgba(colors[entry["block"]]))
        rgba[3] = opts.get("point_alpha", 1)
        if not np.allclose(entry["point"].get_facecolors(), rgba, rtol=1e-12, atol=1e-12):
            issues.append({"code": "point_color_changed", "block": entry["block"]})
    if sorted(seen) != list(range(1, len(source) + 1)):
        issues.append({"code": "source_rows_not_drawn_exactly_once"})
    summary_rows = []
    summary_cells = [(entry["block"], entry["condition"]) for entry in fig._easyviz_paired_summaries]
    if len(summary_cells) != len(centers) or len(set(summary_cells)) != len(centers) or set(summary_cells) != set(centers):
        issues.append({"code": "summary_cell_count_mismatch"})
    for entry in fig._easyviz_paired_summaries:
        mask = (source["_easyviz_block"] == entry["block"]) & (source[fields["condition"]] == entry["condition"])
        values = source.loc[mask, fields["value"]].to_numpy(float)
        q1, median, q3 = map(float, np.quantile(values, [.25, .5, .75], method=opts.get("quantile_method", "linear")))
        center, width, cap = centers[(entry["block"], entry["condition"])], opts.get("summary_width", .7), opts.get("summary_cap_width", .22)
        expected_h = [[[center - width / 2, median], [center + width / 2, median]], [[center - cap / 2, q1], [center + cap / 2, q1]], [[center - cap / 2, q3], [center + cap / 2, q3]]]
        expected_v = [[[center, q1], [center, q3]]]
        if entry["n"] != len(values) or not np.allclose(entry["horizontal"].get_segments(), expected_h, rtol=1e-12, atol=1e-12) or not np.allclose(entry["vertical"].get_segments(), expected_v, rtol=1e-12, atol=1e-12):
            issues.append({"code": "raw_scale_summary_mismatch", "block": entry["block"], "condition": entry["condition"]})
        summary_rows.append({"block": entry["block"], "condition": entry["condition"], "n": len(values), "q1": q1, "median": median, "q3": q3, "iqr_width": q3 - q1})
    actual_pairs = fig._easyviz_paired_connectors.get_segments() if fig._easyviz_paired_connectors is not None else []
    expected_pair_count = source.groupby(["_easyviz_block", fields["unit"]]).ngroups * (len(conditions) - 1) if opts.get("connect_pairs", False) else 0
    if len(actual_pairs) != expected_pair_count or len(actual_pairs) != len(fig._easyviz_paired_keys):
        issues.append({"code": "connector_count_mismatch"})
    for actual, (block, unit, first, second) in zip(actual_pairs, fig._easyviz_paired_keys):
        expected = [point_map[(block, unit, first)], point_map[(block, unit, second)]]
        if not np.allclose(actual, expected, rtol=1e-12, atol=1e-12):
            issues.append({"code": "connector_pair_mismatch", "unit": unit})
    return {"status": "pass" if not issues else "needs_revision", "issues": issues, "source_points_checked": len(seen), "complete_units": source.groupby(["_easyviz_block", fields["unit"]]).ngroups, "conditions": conditions, "summary_scale": "raw measurement values", "quantile_method": opts.get("quantile_method", "linear"), "summary_rows": summary_rows, "connectors_drawn": len(actual_pairs), "pairing_field": fields["unit"]}


def _geometry(fig, spec):
    issues, painter = [], fig.canvas.get_renderer()
    opts = spec.get("options", {})
    radius = (math.sqrt(4 / math.pi * opts.get("point_area_pt2", 10)) + opts.get("point_edge_width_pt", 0)) / 2 * fig.dpi / 72
    box = fig.axes[0].get_window_extent(painter)
    for entry in fig._easyviz_paired_artists:
        points = entry["point"].get_offset_transform().transform(entry["point"].get_offsets())
        for source_row, (x, y) in zip(entry["source_rows"], points):
            if x - radius < box.x0 - .01 or x + radius > box.x1 + .01 or y - radius < box.y0 - .01 or y + radius > box.y1 + .01:
                issues.append({"code": "point_clipped", "source_row": source_row})
    return {"status": "pass" if not issues else "needs_revision", "issues": issues, "point_diameter_pt": math.sqrt(4 / math.pi * opts.get("point_area_pt2", 10)), "circle_geometric_area_pt2": opts.get("point_area_pt2", 10), "outline_width_pt": opts.get("point_edge_width_pt", 0)}


def _clipped_text(fig):
    painter, issues = fig.canvas.get_renderer(), []
    skipped = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            low, high = sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                    skipped.update((tick.label1, tick.label2))
    for text in fig.findobj(core.Text):
        if text in skipped or not text.get_visible() or not text.get_text().strip():
            continue
        bounds = text.get_window_extent(painter)
        if bounds.x0 < -.5 or bounds.y0 < -.5 or bounds.x1 > fig.bbox.width + .5 or bounds.y1 > fig.bbox.height + .5:
            issues.append({"text": text.get_text(), "bounds_px": list(map(float, bounds.bounds))})
    return issues


def render(data_path, spec, out, *, spec_path=None):
    """Persist truthful QA even on failure, so stale panel exports cannot pass."""
    data_path, out = Path(data_path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False, "note": "Exports are unverified until this attempted run passes."})
    fig, figures_before = None, set(plt.get_fignums())
    try:
        input_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
        data = prepare(data_path, spec)
        resolved = deepcopy(spec)
        resolved.setdefault("chart", "paired")
        resolved.setdefault("layout", {}).setdefault("auto_fit", "margins" not in resolved.get("layout", {}))
        layout, typography, rc = core.setup(resolved)
        rc["path.simplify"] = False
        with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig, colors = draw(data, resolved, layout, typography)
            fig.canvas.draw()
            audit = audit_source_artists(data_path, resolved, fig)
            clipped = _clipped_text(fig)
            overlap, oblique = core.check_tick_label_overlap(fig, fig.canvas.get_renderer())
            legends = fig._easyviz_legend_layout.validate()
            geometry = _geometry(fig, resolved)
            fitted = getattr(fig, "_easyviz_auto_layout", None)
            exports = core.export(fig, out, resolved, layout)
            if hashlib.sha256(data_path.read_bytes()).hexdigest() != input_hash:
                audit["status"] = "needs_revision"
                audit["issues"].append({"code": "source_changed_during_render"})
            missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            passed = not clipped and not overlap and not missing and all(record["status"] == "pass" for record in (audit, legends, geometry)) and (not fitted or fitted["status"] == "pass")
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "input_rows": len(data), "plotted_input_rows": sum(len(r["source_rows"]) for r in fig._easyviz_paired_artists), "input_sha256": input_hash, "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "clipped_text": clipped, "overlapping_tick_labels": overlap, "unchecked_oblique_tick_labels": oblique, "missing_glyphs": missing, "source_to_artist_audit": audit, "mark_geometry": geometry, "legend_layout": legends, "exports": exports, "visual_review_required": True, "note": "Automated geometry and source checks do not establish aesthetic quality or statistical appropriateness; inspect the actual panel."}
            settings = deepcopy(resolved)
            settings.update(layout=layout, typography=typography, resolved_colors=colors, formats=resolved.get("formats", ["pdf", "png"]), input_file=str(data_path.resolve()), input_sha256=input_hash, supplied_spec=deepcopy(spec), spec_sha256=hashlib.sha256(json.dumps(spec, sort_keys=True, allow_nan=False).encode()).hexdigest())
            settings["axis"] = {"y_scale": fig.axes[0].get_yscale(), "y_limits": list(map(float, fig.axes[0].get_ylim())), "condition_order": audit["conditions"]}
            settings["summary_policy"] = {"method": "median_iqr", "scale": "raw measurements", "quantile_method": resolved.get("options", {}).get("quantile_method", "linear"), "interval_meaning": "interquartile range of observations, not a confidence interval", "tests_performed": False}
            settings["mark_policy"] = {"geometric_circle_area_pt2": geometry["circle_geometric_area_pt2"], "matplotlib_s": core.circle_size_parameter(geometry["circle_geometric_area_pt2"]), "diameter_pt": geometry["point_diameter_pt"], "placement": resolved.get("options", {}).get("point_layout", "swarm"), "placement_measured_after_layout": True, "connect_pairs": resolved.get("options", {}).get("connect_pairs", False), "jitter_shared_within_unit": True if resolved.get("options", {}).get("point_layout") == "jitter" else None, "outline_width_pt": geometry["outline_width_pt"]}
            settings["renderer"] = {"version": VERSION, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "path_simplification": False, "connector_representation": "one exact two-point segment per adjacent condition and unit", "helper_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in HELPERS}}
            settings["runtime"] = {"python": platform.python_version(), **{name: package_version(name) for name in ("matplotlib", "numpy", "pandas", "Pillow", "pypdf")}}
            if spec_path is not None:
                settings["spec_file"], settings["spec_file_sha256"] = str(Path(spec_path).resolve()), hashlib.sha256(Path(spec_path).read_bytes()).hexdigest()
            if fitted:
                qa["auto_layout"] = settings["auto_layout"] = fitted
            data.to_csv(out / "plotting-data.csv", index=False)
            pd.DataFrame(audit["summary_rows"]).to_csv(out / "summary-data.csv", index=False)
            write_json(out / "settings.json", settings)
            write_json(out / "stats.json", {**settings["summary_policy"], "complete_units": audit["complete_units"], "observations": len(data), "pairing_inferred": False, "missing_values_filled": False})
            write_json(out / "qa.json", qa)
            require(passed, "Canvas or source-to-artist QA needs revision; inspect qa.json and the actual exported panel. Preserve final dimensions and fonts or explicitly adopt a larger panel.")
            return qa
    except Exception as exc:
        status = json.loads((out / "qa.json").read_text())
        if status.get("status") == "in_progress":
            status.update(status="failed", valid_outputs=False, error=str(exc))
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
        parser.exit(2, f"EasyViz paired: {exc}\n")
    try:
        qa = render(args.data, spec, args.out, spec_path=args.spec)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"EasyViz paired: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}))


if __name__ == "__main__":
    main()
