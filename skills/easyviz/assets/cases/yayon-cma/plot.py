#!/usr/bin/env python3
"""Portable two-matrix / supplied-summary case using the reusable EasyViz runtime.

All field mappings, orders, aliases, emphasis and geometry come from --spec.
No clustering, normalization, cosine computation or statistical test is run.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import warnings

HERE = Path(__file__).resolve().parent


def runtime_at(path):
    path = Path(path)
    if path.is_file(): path = path.parent
    loader = importlib.util.spec_from_file_location("easyviz_yayon_runtime", path / "annotated_matrix.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def _object(obj, keys, name):
    if not isinstance(obj, dict) or set(obj) - keys: raise ValueError(f"Unknown or invalid {name}: expected keys {sorted(keys)}")


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (positive and value <= 0): raise ValueError(f"{name} must be a finite {'positive ' if positive else ''}JSON number")
    return float(value)


def validate_spec(spec, runtime):
    _object(spec, {"chart", "fields", "summary_fields", "order", "label_aliases", "labels", "emphasis", "layout", "geometry", "formats", "expression_scale", "summary_scale", "significance", "scope"}, "spec")
    if spec.get("chart") != "aligned_two_matrix": raise ValueError("chart must be aligned_two_matrix")
    for key, roles in (("fields", {"group", "row", "column", "value"}), ("summary_fields", {"column", "value", "p_adjusted"})):
        _object(spec.get(key), roles, key)
        if set(spec[key]) != roles or any(not isinstance(v, str) or not v.strip() for v in spec[key].values()) or len(set(spec[key].values())) != len(roles): raise ValueError(f"{key} must map distinct required roles to nonempty fields")
    _object(spec.get("order"), {"group", "row", "column"}, "order")
    if set(spec["order"]) != {"group", "row", "column"}: raise ValueError("All explicit literal orders are required")
    for role, order in spec["order"].items(): runtime.aligned_layers.literal_order(order, f"order.{role}")
    if len(spec["order"]["group"]) != 2: raise ValueError("This reviewed layout requires exactly two matrix groups")
    runtime.core.figure_profile.validate_layout(spec.get("layout", {}))
    if spec.get("layout", {}).get("auto_fit", False): raise ValueError("The reviewed composite uses explicit geometry; auto_fit must be false")
    if "margins" in spec.get("layout", {}): raise ValueError("Explicit composite geometry cannot also use layout.margins")
    if not isinstance(spec.get("scope"), str) or not spec["scope"].strip(): raise ValueError("A nonempty reproduction/adaptation scope is required")
    _object(spec.get("geometry"), {"matrix_mm", "upper_mm", "summary_mm", "expression_colorbar_mm", "summary_colorbar_mm", "group_label_x_mm", "group_divider_x_mm", "p_title_mm", "p_key_mm", "p_label_x_mm", "range_y_mm"}, "geometry")
    required = {"matrix_mm", "upper_mm", "summary_mm", "expression_colorbar_mm", "summary_colorbar_mm", "group_label_x_mm", "group_divider_x_mm", "p_title_mm", "p_key_mm", "p_label_x_mm", "range_y_mm"}
    if set(spec["geometry"]) != required: raise ValueError("Explicit geometry is incomplete")
    for key in ("matrix_mm", "upper_mm", "summary_mm", "expression_colorbar_mm", "summary_colorbar_mm"):
        rect = spec["geometry"][key]
        if not isinstance(rect, list) or len(rect) != 4: raise ValueError(f"{key} must be [left,bottom,width,height]")
        for v in rect: _finite(v, key)
        if min(rect[2:]) <= 0: raise ValueError(f"{key} must have positive dimensions")
    for key in ("group_label_x_mm", "group_divider_x_mm", "p_label_x_mm"): _finite(spec["geometry"][key], key)
    if not isinstance(spec["geometry"]["range_y_mm"], list) or len(spec["geometry"]["range_y_mm"]) != 2 or spec["geometry"]["range_y_mm"][0] >= spec["geometry"]["range_y_mm"][1]: raise ValueError("range_y_mm must be [bottom,top]")
    for v in spec["geometry"]["range_y_mm"]: _finite(v, "range_y_mm")
    if not isinstance(spec["geometry"]["p_title_mm"], list) or len(spec["geometry"]["p_title_mm"]) != 2: raise ValueError("p_title_mm must be [x,y]")
    for v in spec["geometry"]["p_title_mm"]: _finite(v, "p_title_mm")
    aliases = spec.get("label_aliases", {})
    _object(aliases, {"group", "row", "column"}, "label_aliases")
    for role, mapping in aliases.items():
        if not isinstance(mapping, dict) or not set(mapping) <= set(spec["order"][role]) or any(not isinstance(v, str) or not v.strip() for v in mapping.values()): raise ValueError("Label aliases require literal in-domain keys and nonempty labels")
        labels = [mapping.get(v, v) for v in spec["order"][role]]
        if len(set(labels)) != len(labels): raise ValueError("Aliases must preserve distinct displayed identities")
    _object(spec.get("labels"), {"expression", "summary", "interaction", "column"}, "labels")
    if not {"expression", "summary", "interaction"} <= set(spec["labels"]): raise ValueError("Expression, summary and interaction decoding labels are required")
    if any(not isinstance(v, str) for v in spec["labels"].values()): raise ValueError("Labels must be strings")
    for key in ("expression_scale", "summary_scale"):
        scale = spec.get(key)
        _object(scale, {"colormap", "limits", "ticks"}, key)
        if set(scale) != {"colormap", "limits", "ticks"}: raise ValueError(f"{key} requires colormap, limits and ticks")
        if not isinstance(scale["limits"], list) or len(scale["limits"]) != 2: raise ValueError("Scale limits must be two numbers")
        low, high = [_finite(v, key) for v in scale["limits"]]
        if low >= high: raise ValueError("Scale limits must strictly ascend")
        ticks = scale["ticks"]
        if not isinstance(ticks, list) or not ticks or any(_finite(v, "scale tick") < low or v > high for v in ticks) or any(a >= b for a, b in zip(ticks, ticks[1:])): raise ValueError("Scale ticks must be strictly increasing in-range values")
    bins = spec.get("significance")
    if not isinstance(bins, list) or not bins: raise ValueError("Significance classes must be explicitly supplied")
    thresholds = []
    for rule in bins:
        _object(rule, {"threshold", "area_pt2", "label"}, "significance rule")
        threshold = _finite(rule.get("threshold"), "P threshold", True)
        if threshold > 1: raise ValueError("P threshold must lie in (0,1]")
        _finite(rule.get("area_pt2"), "circle area", True)
        if not isinstance(rule.get("label"), str) or not rule["label"].strip(): raise ValueError("Significance rule requires label")
        thresholds.append(threshold)
    if any(a >= b for a, b in zip(thresholds, thresholds[1:])): raise ValueError("P thresholds must strictly ascend, strongest first")
    if any(a["area_pt2"] <= b["area_pt2"] for a, b in zip(bins, bins[1:])): raise ValueError("Stronger P classes must have larger areas")
    if not isinstance(spec["geometry"]["p_key_mm"], list) or len(spec["geometry"]["p_key_mm"]) != len(bins): raise ValueError("A physical [x,y] key position is required for every significance class")
    for point in spec["geometry"]["p_key_mm"]:
        if not isinstance(point, list) or len(point) != 2: raise ValueError("P key centers must be [x,y]")
        for v in point: _finite(v, "P key center")
    emphasis = spec.get("emphasis", {})
    _object(emphasis, {"column_colors", "ranges", "range_color", "range_linewidth_pt"}, "emphasis")
    for key, color in emphasis.get("column_colors", {}).items():
        if key not in spec["order"]["column"] or not runtime.core.mcolors.is_color_like(color): raise ValueError("Emphasis colors require literal column IDs and valid colors")
    for selected in emphasis.get("ranges", []):
        _object(selected, {"start", "end"}, "emphasis range")
        order = spec["order"]["column"]
        if selected.get("start") not in order or selected.get("end") not in order or order.index(selected["start"]) > order.index(selected["end"]): raise ValueError("Emphasis ranges require ordered in-domain endpoints")
    if not runtime.core.mcolors.is_color_like(emphasis.get("range_color", "#222222")): raise ValueError("Invalid range outline color")
    _finite(emphasis.get("range_linewidth_pt", .55), "range linewidth", True)
    formats = spec.get("formats", ["pdf", "svg", "png"])
    if not isinstance(formats, list) or not formats or any(not isinstance(v, str) for v in formats) or len(set(formats)) != len(formats) or not set(formats) <= {"pdf", "svg", "png", "tiff"}: raise ValueError("Unsupported export formats")


def prepare(data_path, summary_path, spec, runtime):
    validate_spec(spec, runtime)
    data, summary = runtime._csv(data_path), runtime._csv(summary_path)
    f, sf = spec["fields"], spec["summary_fields"]
    if not set(f.values()) <= set(data) or not set(sf.values()) <= set(summary): raise ValueError("Mapped field absent from source input")
    for role in ("group", "row", "column"):
        if set(data[f[role]]) != set(spec["order"][role]): raise ValueError(f"order.{role} must have exact literal source coverage")
    if data.duplicated([f["group"], f["row"], f["column"]]).any(): raise ValueError("Duplicate group/row/column coordinates")
    expected = math.prod(len(v) for v in spec["order"].values())
    if len(data) != expected: raise ValueError("Both matrices must be fully supplied; no missing or invented measurements")
    if summary[sf["column"]].duplicated().any() or set(summary[sf["column"]]) != set(spec["order"]["column"]): raise ValueError("Summary requires exact one-to-one literal column-ID coverage")
    for table, field, limits in ((data, f["value"], spec["expression_scale"]["limits"]), (summary, sf["value"], spec["summary_scale"]["limits"]), (summary, sf["p_adjusted"], [0, 1])):
        try: values = runtime.pd.to_numeric(table[field], errors="raise").to_numpy(float)
        except (ValueError, TypeError): raise ValueError(f"{field} must contain finite numeric values") from None
        if not runtime.np.isfinite(values).all() or values.min() < limits[0] or values.max() > limits[1]: raise ValueError(f"{field} values must remain within the declared limits")
    return {"data": data, "summary": summary, "hashes": {"matrix": data.attrs["source_sha256"], "summary": summary.attrs["source_sha256"]}}


def _scale(runtime, config, values):
    cmap, norm = runtime.core.continuous({"colormap": config["colormap"], "options": {"color_limits": config["limits"]}}, values)
    return runtime.ScalarMappable(norm=norm, cmap=cmap)


def _class(value, bins):
    return next((i for i, rule in enumerate(bins) if value < rule["threshold"]), None)


def draw(prepared, spec, runtime):
    core, plt, np = runtime.core, runtime.plt, runtime.np
    from matplotlib.patches import Rectangle, Ellipse
    from matplotlib.lines import Line2D
    layout, typography, rc = core.setup(spec)
    with plt.rc_context(rc):
        fig = plt.figure(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
        g, f, sf, order = spec["geometry"], spec["fields"], spec["summary_fields"], spec["order"]
        width, height = layout["width_mm"], layout["height_mm"]
        frame = runtime.aligned_layers.AlignedFrame(fig, order["row"], order["column"], g["matrix_mm"])
        lower = frame.main
        upper = frame.add_aligned("upper-matrix", "column", g["upper_mm"])
        middle = frame.add_aligned("supplied-summary", "column", g["summary_mm"])
        fig._easyviz_aligned_frame, fig._case_artists = frame, {"cells": [], "summary": [], "ranges": []}
        matrix_values = prepared["data"][f["value"]].astype(float).tolist()
        summary_values = prepared["summary"][sf["value"]].astype(float).tolist()
        expression, similarity = _scale(runtime, spec["expression_scale"], matrix_values), _scale(runtime, spec["summary_scale"], summary_values)
        register = core.figure_elements.register
        for group, ax in ((order["group"][0], upper), (order["group"][1], lower)):
            ax.set_ylim(len(order["row"]) - .5, -.5)
            ax.set_yticks(range(len(order["row"])), [spec.get("label_aliases", {}).get("row", {}).get(v, v) for v in order["row"]])
            ax.set_xticks(range(len(order["column"])))
            ax.tick_params(axis="y", length=0, pad=2)
            ax.tick_params(axis="x", length=1.5, width=.4, labelbottom=ax is lower, pad=2)
            for spine in ax.spines.values(): spine.set_visible(False)
            if ax is lower:
                ax.set_xticklabels([spec.get("label_aliases", {}).get("column", {}).get(v, v) for v in order["column"]], rotation=90, fontstyle="italic", fontsize=typography["tick"])
                ax.set_xlabel(spec["labels"].get("column", ""), fontsize=typography["axis"])
                for identifier, text in zip(order["column"], ax.get_xticklabels()):
                    color = spec.get("emphasis", {}).get("column_colors", {}).get(identifier, "#222222")
                    text.set_color(color)
                    register(fig, text, "column-label", identifier, key=identifier, source_keys=[{"column": identifier}], spec_paths=[core.figure_elements.pointer("emphasis", "column_colors", identifier)], editable=["color", "text"])
            lookup = prepared["data"].set_index([f["group"], f["row"], f["column"]])
            for y, row in enumerate(order["row"]):
                for x, column in enumerate(order["column"]):
                    source = lookup.loc[(group, row, column)]
                    value = float(source[f["value"]])
                    patch = Rectangle((x - .5, y - .5), 1, 1, facecolor=expression.to_rgba(value), edgecolor="none", linewidth=0, zorder=2)
                    ax.add_patch(patch)
                    register(fig, patch, "matrix-cell", f"{group}: {row} × {column}", key=[group, row, column], source_keys=[{"group": group, "row": row, "column": column, "source_cell": source.get("source_cell", "")}], spec_paths=["/expression_scale"], editable=["color"])
                    fig._case_artists["cells"].append({"group": group, "row": row, "column": column, "artist": patch, "axes": ax})
            box = ax.get_position()
            label = fig.text(g["group_label_x_mm"] / width, (box.y0 + box.y1) / 2, spec.get("label_aliases", {}).get("group", {}).get(group, group), rotation=90, ha="center", va="center", fontsize=typography["axis"])
            register(fig, label, "group-label", group, key=group, source_keys=[{"group": group}], editable=["text"])
            divider = Line2D([g["group_divider_x_mm"] / width] * 2, [box.y0, box.y1], transform=fig.transFigure, color="#222222", linewidth=.4)
            fig.add_artist(divider)
            register(fig, divider, "group-divider", group, key=group)
        middle.set_ylim(*spec["summary_scale"]["limits"])
        middle.set_yticks([])
        middle.set_xticks([])
        for spine in middle.spines.values(): spine.set_visible(False)
        baseline = middle.axhline(0, color="#707070", linewidth=.4, zorder=1)
        register(fig, baseline, "summary-baseline", "Supplied summary zero", key="summary-zero")
        summaries = prepared["summary"].set_index(sf["column"])
        for x, column in enumerate(order["column"]):
            record = summaries.loc[column]
            value, p_value = float(record[sf["value"]]), float(record[sf["p_adjusted"]])
            bar = middle.bar(x, value, width=.82, color=similarity.to_rgba(value), linewidth=0, zorder=2)[0]
            register(fig, bar, "supplied-summary-bar", column, key=column, source_keys=[{"column": column, "source_cell": record.get("cosine_cell", "")}], spec_paths=["/summary_scale"], editable=["color"])
            selected = _class(p_value, spec["significance"])
            point = None
            if selected is not None:
                point = middle.scatter([x], [0], s=[4 / math.pi * spec["significance"][selected]["area_pt2"]], facecolors="white", edgecolors="#222222", linewidths=.4, zorder=3)
                register(fig, point, "supplied-interaction-class", f"{column}: {spec['significance'][selected]['label']}", key=column, source_keys=[{"column": column, "source_cell": record.get("p_cell", ""), "p_adjusted": record[sf["p_adjusted"]]}], spec_paths=[core.figure_elements.pointer("significance", selected)], editable=[])
            fig._case_artists["summary"].append({"column": column, "bar": bar, "point": point, "class": selected})
        # This left-hand key occupies an empty corner outside the data box.
        # The complete compound text/key checks below protect actual labels;
        # the single-axis enclosing tight rectangle includes that empty corner.
        manager = core.legend_layout.LegendLayout(fig, lower, typography, {"colorbar": {"position": "manual", "rect_mm": g["expression_colorbar_mm"], "orientation": "horizontal", "ticks": spec["expression_scale"]["ticks"], "label": spec["labels"]["expression"]}}, main_plot_bbox_mm=g["matrix_mm"])
        manager.add_colorbar(expression, spec["labels"]["expression"])
        manager.layout()
        fig._easyviz_legend_layout = manager
        rect = g["summary_colorbar_mm"]
        cbax = fig.add_axes([rect[0] / width, rect[1] / height, rect[2] / width, rect[3] / height])
        cb = fig.colorbar(similarity, cax=cbax, orientation="vertical", ticks=spec["summary_scale"]["ticks"])
        cb.ax.yaxis.set_ticks_position("left")
        cb.ax.yaxis.set_label_position("left")
        cb.set_label(spec["labels"]["summary"], fontsize=typography["legend"], labelpad=2)
        cb.ax.tick_params(labelsize=typography["legend"], length=1.5, pad=1)
        cb.outline.set_linewidth(.4)
        fig._case_colorbars = {"expression": manager.entries[0]["colorbar"], "summary": cb}
        register(fig, cbax, "legend", "Supplied summary color scale", key="summary-color", spec_paths=["/summary_scale"], editable=["layout"])
        title = fig.text(g["p_title_mm"][0] / width, g["p_title_mm"][1] / height, spec["labels"]["interaction"], ha="left", va="top", fontsize=typography["legend"])
        register(fig, title, "guide-label", "Supplied interaction classes", key="interaction-label", editable=["text"])
        key_artists = [title]
        for i, (rule, center) in enumerate(zip(spec["significance"], g["p_key_mm"])):
            diameter_mm = math.sqrt(4 / math.pi * rule["area_pt2"]) * 25.4 / 72
            key = Ellipse((center[0] / width, center[1] / height), diameter_mm / width, diameter_mm / height, transform=fig.transFigure, facecolor="white", edgecolor="#222222", linewidth=.4)
            fig.add_artist(key)
            label = fig.text(g["p_label_x_mm"] / width, center[1] / height, rule["label"], va="center", ha="left", fontsize=typography["legend"])
            register(fig, key, "legend-key", rule["label"], key=["interaction", i], spec_paths=[core.figure_elements.pointer("significance", i)], editable=[])
            register(fig, label, "guide-label", rule["label"], key=["interaction", i], spec_paths=[core.figure_elements.pointer("significance", i, "label")], editable=["text"])
            key_artists.extend([key, label])
        fig._case_guides = {"interaction": key_artists, "summary": [cbax], "expression": [manager.entries[0]["artist"]]}
        bottom, top = g["range_y_mm"]
        for selected in spec.get("emphasis", {}).get("ranges", []):
            first, last = order["column"].index(selected["start"]), order["column"].index(selected["end"])
            x, _, plotwidth, _ = g["matrix_mm"]
            left, span = x + first / len(order["column"]) * plotwidth, (last - first + 1) / len(order["column"]) * plotwidth
            patch = Rectangle((left / width, bottom / height), span / width, (top - bottom) / height, transform=fig.transFigure, facecolor="none", edgecolor=spec["emphasis"].get("range_color", "#222222"), linewidth=spec["emphasis"].get("range_linewidth_pt", .55), zorder=5)
            fig.add_artist(patch)
            register(fig, patch, "emphasis-range", f"{selected['start']} to {selected['end']}", key=[selected["start"], selected["end"]], source_keys=[{"columns": order["column"][first:last + 1]}], spec_paths=["/emphasis/ranges"], editable=[])
            fig._case_artists["ranges"].append({"start": selected["start"], "end": selected["end"], "artist": patch})
        for key, axes in frame.axes.items(): register(fig, axes.patch, "aligned-axes", key, key=key, source_keys=[{"column_order": order["column"]}], editable=["layout"])
        fig.canvas.draw()
    return fig, layout, typography


def audit(data_path, summary_path, spec, fig, runtime):
    source = prepare(data_path, summary_path, spec, runtime)
    f, sf, order = spec["fields"], spec["summary_fields"], spec["order"]
    lookup = source["data"].set_index([f["group"], f["row"], f["column"]])
    summary = source["summary"].set_index(sf["column"])
    expression = _scale(runtime, spec["expression_scale"], source["data"][f["value"]].astype(float).tolist())
    similarity = _scale(runtime, spec["summary_scale"], source["summary"][sf["value"]].astype(float).tolist())
    issues, table, seen = [], [], set()
    if len(fig._case_artists["cells"]) != len(source["data"]): issues.append({"code": "cell_artist_count_mismatch"})
    for record in fig._case_artists["cells"]:
        key = record["group"], record["row"], record["column"]
        if key in seen or key not in lookup.index:
            issues.append({"code": "cell_artist_key_mismatch"})
            continue
        seen.add(key)
        x, y = order["column"].index(key[2]), order["row"].index(key[1])
        value = float(lookup.loc[key, f["value"]])
        expected = expression.to_rgba(value)
        patch, axes = record["artist"], record["axes"]
        target_axes = fig._easyviz_aligned_frame.axes["upper-matrix"] if key[0] == order["group"][0] else fig._easyviz_aligned_frame.main
        if axes is not target_axes or not runtime._rectangle_display_match(patch, target_axes, [x - .5, y - .5, 1, 1]) or not runtime.np.allclose(patch.get_facecolor(), expected, rtol=0, atol=1e-12): issues.append({"code": "cell_source_artist_mismatch", "key": list(key)})
        table.append({"layer": "matrix", "group": key[0], "row": key[1], "column": key[2], "source_value": value, "artist_x": patch.get_x() + .5, "artist_y": patch.get_y() + .5, "source_red": expected[0], "source_green": expected[1], "source_blue": expected[2], "artist_red": patch.get_facecolor()[0], "artist_green": patch.get_facecolor()[1], "artist_blue": patch.get_facecolor()[2], "svg_id": patch.get_gid()})
    if len(fig._case_artists["summary"]) != len(summary): issues.append({"code": "summary_artist_count_mismatch"})
    seen = set()
    middle = fig._easyviz_aligned_frame.axes["supplied-summary"]
    for record in fig._case_artists["summary"]:
        column = record["column"]
        if column in seen or column not in summary.index:
            issues.append({"code": "summary_artist_key_mismatch"})
            continue
        seen.add(column)
        x = order["column"].index(column)
        value, p_value = float(summary.loc[column, sf["value"]]), float(summary.loc[column, sf["p_adjusted"]])
        bar, point, selected = record["bar"], record["point"], _class(p_value, spec["significance"])
        if not runtime._rectangle_display_match(bar, middle, [x - .41, 0, .82, value]) or not runtime.np.allclose(bar.get_facecolor(), similarity.to_rgba(value), rtol=0, atol=1e-12): issues.append({"code": "summary_bar_source_artist_mismatch", "column": column})
        if selected != record["class"] or (selected is None) != (point is None): issues.append({"code": "interaction_class_mismatch", "column": column})
        if selected is not None and point is not None:
            area = spec["significance"][selected]["area_pt2"]
            actual = point.get_offsets()
            if not runtime._attached(point, middle, middle.collections) or actual.shape != (1, 2) or not runtime.np.allclose(actual, [[x, 0]], atol=1e-12, rtol=0) or not runtime.np.allclose(point.get_sizes(), [4 / math.pi * area], atol=1e-12, rtol=0) or not runtime.np.allclose(point.get_offset_transform().transform(actual), middle.transData.transform([[x, 0]]), atol=1e-9, rtol=0) or not runtime.np.allclose(point.get_facecolors(), [[1, 1, 1, 1]], atol=1e-12) or not runtime.np.allclose(point.get_edgecolors(), [runtime.to_rgba("#222222")], atol=1e-12) or not runtime.np.allclose(point.get_linewidths(), [.4], atol=1e-12): issues.append({"code": "interaction_point_source_artist_mismatch", "column": column})
        table.append({"layer": "supplied-summary", "column": column, "source_value": value, "artist_value": bar.get_height(), "source_p_adjusted": p_value, "class": None if selected is None else spec["significance"][selected]["label"], "point_area_pt2": None if point is None else float(point.get_sizes()[0] * math.pi / 4), "svg_id": bar.get_gid()})
    alignment = fig._easyviz_aligned_frame.audit()
    issues.extend(alignment["issues"])
    for key in ("matrix", "upper-matrix"):
        axes = fig._easyviz_aligned_frame.axes[key]
        if not runtime.np.allclose(axes.get_ylim(), [len(order["row"]) - .5, -.5], atol=1e-12, rtol=0): issues.append({"code": "matrix_row_order_mismatch", "axes": key})
    if not runtime.np.allclose(middle.get_ylim(), spec["summary_scale"]["limits"], rtol=0, atol=1e-12): issues.append({"code": "summary_value_domain_mismatch"})
    for name, expected_scale in (("expression", expression), ("summary", similarity)):
        actual_scale = fig._case_colorbars[name].mappable
        samples = spec[f"{name}_scale"]["ticks"]
        if not runtime.np.allclose(actual_scale.to_rgba(samples), expected_scale.to_rgba(samples), atol=1e-12, rtol=0): issues.append({"code": "source_color_guide_mismatch", "guide": name})
    lower = fig._easyviz_aligned_frame.main
    for column, text in zip(order["column"], lower.get_xticklabels()):
        expected_label = spec.get("label_aliases", {}).get("column", {}).get(column, column)
        expected_color = spec.get("emphasis", {}).get("column_colors", {}).get(column, "#222222")
        if text.get_text() != expected_label or not runtime.np.allclose(runtime.to_rgba(text.get_color()), runtime.to_rgba(expected_color), atol=1e-12): issues.append({"code": "column_label_or_emphasis_mismatch", "column": column})
    if len(fig._case_artists["ranges"]) != len(spec.get("emphasis", {}).get("ranges", [])): issues.append({"code": "emphasis_range_count_mismatch"})
    width, height = fig.get_size_inches() * 25.4
    x, _, plotwidth, _ = spec["geometry"]["matrix_mm"]
    bottom, top = spec["geometry"]["range_y_mm"]
    for record, selected in zip(fig._case_artists["ranges"], spec.get("emphasis", {}).get("ranges", [])):
        first, last = order["column"].index(selected["start"]), order["column"].index(selected["end"])
        left, right = x + first / len(order["column"]) * plotwidth, x + (last + 1) / len(order["column"]) * plotwidth
        expected = fig.transFigure.transform([[left / width, bottom / height], [right / width, top / height]])
        actual = record["artist"].get_transform().transform([[0, 0], [1, 1]])
        if record["start"] != selected["start"] or record["end"] != selected["end"] or not record["artist"].get_visible() or not runtime.np.allclose(actual, expected, atol=1e-9, rtol=0): issues.append({"code": "emphasis_range_geometry_mismatch"})
    return {"status": "pass" if not issues else "needs_revision", "issues": issues, "cells_checked": len(source["data"]), "summary_rows_checked": len(summary), "supplied_interaction_classes_checked": len(summary), "alignment": alignment, "artist_values": table, "source_hashes": source["hashes"]}


def _layout_checks(fig, spec, runtime):
    fig.canvas.draw()
    painter = fig.canvas.get_renderer()
    texts = []
    for axes in fig.axes: texts.extend(runtime._axis_texts(axes))
    texts.extend(t for t in fig.texts if t.get_visible() and t.get_text().strip())
    clipped, collisions = [], []
    for text in texts:
        box = text.get_window_extent(painter)
        if box.x0 < -1 or box.y0 < -1 or box.x1 > fig.bbox.width + 1 or box.y1 > fig.bbox.height + 1: clipped.append(text.get_text())
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if runtime.core.legend_layout._intersects(a.get_window_extent(painter), b.get_window_extent(painter)):
                collisions.append([a.get_text(), b.get_text()])
    guide_reports = {}
    for name, artists in fig._case_guides.items():
        boxes = [a.get_tightbbox(painter) if hasattr(a, "get_tightbbox") else a.get_window_extent(painter) for a in artists]
        bbox = runtime.core.legend_layout.Bbox.union(boxes)
        report = runtime.core.legend_layout.measure_bbox(fig, bbox, spec["geometry"]["matrix_mm"])
        report["outside_canvas"] = not runtime.core.legend_layout._contains(fig.bbox, bbox)
        report["overlaps_data"] = any(runtime.core.legend_layout._intersects(bbox, ax.get_window_extent()) for ax in fig._easyviz_aligned_frame.axes.values())
        own_texts = {t for artist in artists for t in artist.findobj(runtime.core.Text)}
        report["overlaps_other_text"] = any(runtime.core.legend_layout._intersects(bbox, text.get_window_extent(painter)) for text in texts if text not in own_texts)
        guide_reports[name] = report
    issues = []
    if clipped: issues.append("clipped_text")
    if collisions: issues.append("overlapping_text")
    if any(r["outside_canvas"] or r["overlaps_data"] or r["overlaps_other_text"] for r in guide_reports.values()): issues.append("guide_outside_canvas_or_overlaps_data_or_text")
    return {"status": "pass" if not issues else "needs_revision", "issues": issues, "clipped_text": clipped, "text_collisions": collisions, "guides": guide_reports}


def render(data_path, summary_path, spec, out, runtime_path, *, spec_path=None, provenance_path=None, font_override=None):
    runtime = runtime_at(runtime_path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    runtime.write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False})
    fig, before = None, set(runtime.plt.get_fignums())
    try:
        source = prepare(data_path, summary_path, spec, runtime)
        supplied_spec = deepcopy(spec)
        paths = {"matrix": Path(data_path).resolve(), "summary": Path(summary_path).resolve()}
        hashes = source["hashes"]
        if spec_path:
            payload = Path(spec_path).read_bytes()
            if json.loads(payload.decode("utf-8")) != spec: raise ValueError("Specification file differs from the supplied spec")
            paths["spec"] = Path(spec_path).resolve()
            hashes["spec"] = hashlib.sha256(payload).hexdigest()
        provenance = None
        if provenance_path:
            paths["provenance"] = Path(provenance_path).resolve()
            payload = paths["provenance"].read_bytes()
            hashes["provenance"] = hashlib.sha256(payload).hexdigest()
            provenance = json.loads(payload.decode("utf-8"))
            for key, path in (("matrix", paths["matrix"]), ("summary", paths["summary"])):
                declared = provenance.get("prepared_hashes", {}).get(path.name)
                if declared is not None and declared != hashes[key]: raise ValueError("Prepared source bytes differ from the declared extraction provenance")
            workbook = paths["provenance"].parent / provenance.get("source_workbook", "")
            if provenance.get("source_workbook") and provenance.get("source_sha256"):
                if not workbook.is_file() or hashlib.sha256(workbook.read_bytes()).hexdigest() != provenance["source_sha256"]: raise ValueError("Original source workbook hash does not match provenance")
                paths["workbook"] = workbook.resolve()
                hashes["workbook"] = provenance["source_sha256"]
        if font_override is not None:
            if not isinstance(font_override, str) or not font_override.strip(): raise ValueError("Font override must be a nonempty family name")
            spec = deepcopy(spec)
            spec.setdefault("layout", {})["font"] = font_override
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig, layout, typography = draw(source, spec, runtime)
            source_audit = audit(data_path, summary_path, spec, fig, runtime)
            layout_audit = _layout_checks(fig, spec, runtime)
            legends = fig._easyviz_legend_layout.validate()
            fig._easyviz_source_script, fig._easyviz_data_file = Path(__file__).resolve(), Path(data_path).resolve()
            fig._easyviz_spec_file = Path(spec_path).resolve() if spec_path else None
            fig._easyviz_track = "reproduce"
            exports = runtime.core.export(fig, out, spec, layout)
            changed = [key for key, path in paths.items() if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]]
            if changed:
                source_audit["status"] = "needs_revision"
                source_audit["issues"].append({"code": "source_changed_during_render", "inputs": changed})
            missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            passed = source_audit["status"] == layout_audit["status"] == legends["status"] == "pass" and not missing
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "source_to_artist_audit": {k: v for k, v in source_audit.items() if k != "artist_values"}, "layout": layout_audit, "expression_guide": legends, "missing_glyphs": missing, "exports": exports, "track": "reproduce", "scope": spec["scope"], "dendrogram_reproduced": False, "visual_review_required": True}
            settings = {**deepcopy(spec), "layout": layout, "typography": typography, "runtime": str(Path(runtime_path).resolve()), "runtime_sha256": {name: hashlib.sha256(Path(runtime_path).joinpath(name).read_bytes()).hexdigest() for name in ("aligned_layers.py", "annotated_matrix.py", "render.py", "figure_elements.py")}, "inputs": {key: {"path": str(path), "sha256": hashes[key]} for key, path in paths.items()}, "provenance": provenance, "summary_calculations": "none; supplied values and strict declared P classes only", "outline_policy": "Borderless matrix cells and supplied bars; hollow significance circle and source-emphasis outlines are explicit exceptions"}
            settings["supplied_spec"] = supplied_spec
            settings["font_override"] = font_override
            runtime.write_json(out / "qa.json", qa)
            runtime.write_json(out / "settings.json", settings)
            runtime.pd.DataFrame(source_audit["artist_values"]).to_csv(out / "artist-values.csv", index=False)
            source["data"].to_csv(out / "plotting-data.csv", index=False)
            source["summary"].to_csv(out / "supplied-summary.csv", index=False)
            runtime.write_json(out / "stats.json", {"normalization_recomputed": False, "cosine_recomputed": False, "anova_recomputed": False, "clustering_performed": False, "supplied_summary_rows": len(source["summary"]), "declared_significance_classes": spec["significance"]})
            manifest = json.loads((out / "elements.json").read_text())
            manifest["input"]["aligned_layer_inputs"] = settings["inputs"]
            runtime.write_json(out / "elements.json", manifest)
            caption = HERE / "caption.md"
            if caption.is_file() and provenance_path: (out / "caption.md").write_text(caption.read_text())
            else: (out / "caption.md").write_text("Synthetic transfer panel. Two supplied matrices and supplied summary values share literal ordered feature IDs. Significance circles decode supplied adjusted P values; no normalization, cosine, test or clustering was recomputed.\n")
            if not passed: raise ValueError("Composite source/geometry/guide QA needs revision; inspect qa.json and the rendered PNG. Final canvas and fonts were preserved.")
            return qa
    except Exception as exc:
        qa = json.loads((out / "qa.json").read_text())
        if qa["status"] == "in_progress":
            qa.update(status="failed", error=str(exc))
            runtime.write_json(out / "qa.json", qa)
        raise
    finally:
        if fig is not None: runtime.plt.close(fig)
        for n in set(runtime.plt.get_fignums()) - before: runtime.plt.close(n)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path, help="Directory containing the installed EasyViz scripts")
    parser.add_argument("--data", default=HERE / "inputs/source-data.csv", type=Path)
    parser.add_argument("--summary", default=HERE / "inputs/summary.csv", type=Path)
    parser.add_argument("--spec", default=HERE / "spec.json", type=Path)
    parser.add_argument("--out", default=HERE / "output", type=Path)
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--font", help="Explicit family override for another assembly system; point sizes/canvas stay fixed")
    args = parser.parse_args()
    provenance = args.provenance
    if provenance is None and args.data.resolve() == (HERE / "inputs/source-data.csv").resolve(): provenance = HERE / "inputs/provenance.json"
    try:
        qa = render(args.data, args.summary, json.loads(args.spec.read_text()), args.out, args.runtime, spec_path=args.spec, provenance_path=provenance, font_override=args.font)
    except (OSError, ValueError, ImportError) as exc: parser.exit(2, f"EasyViz supplied two-matrix case: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"], "dendrogram_reproduced": False}))


if __name__ == "__main__":
    main()
