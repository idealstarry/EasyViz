#!/usr/bin/env python3
"""Draw an empirical cumulative distribution from raw, unweighted observations.

Run with --data source.csv --spec ecdf.json --out output-directory. Copy this
script with render.py and its sibling helpers for portable execution.
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

_loader = importlib.util.spec_from_file_location("easyviz_ecdf_core", Path(__file__).with_name("render.py"))
core = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(core)
plt, np, pd = core.plt, core.np, core.pd
SpecError, require, write_json = core.SpecError, core.require, core.write_json

VERSION = "0.1.0"
SPEC_KEYS = {"chart", "fields", "options", "layout", "typography", "formats", "order", "labels", "colors", "legends"}
OPTIONS = {"x_scale", "x_limits", "x_ticks", "x_tick_format", "curve_line_width_pt", "grid"}
HELPERS = ("render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py")
SCHEMA = {
    "chart": "ecdf", "fields": {"value": "raw numeric observation", "group": "optional category", "unit": "optional observation identifier"},
    "layout": {"width_mm": 88, "height_mm": 70, "font": "Arial", "font_size_pt": 8, "dpi": 300, "auto_fit": True},
    "options": {"x_scale": "linear|log", "x_limits": ["minimum", "maximum"], "x_ticks": "optional strictly ascending positions", "x_tick_format": "plain|power10 (power10 requires log scale and exact powers of ten)", "curve_line_width_pt": .8, "grid": False},
    "order": {"group": ["every observed group exactly once"]},
    "colors": {"each group, or all for ungrouped inputs": "explicit color"},
    "labels": {"x": "measurement and units", "y": "Cumulative fraction"},
    "formats": ["pdf", "svg", "png", "tiff"],
    "semantics": ["F(x) = count(value <= x) / observation count, independently within each group.", "Right-continuous empirical steps; equal values form a jump of their full count.", "No smoothing, fitted distribution, weights, confidence interval or statistical test.", "A unit role rejects duplicate unit/group rows; it does not establish experimental independence.", "Displayed horizontal tails extend to the axis limits; no artificial observation is added.", "Titles and narrative belong in a separate caption."],
}


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
    require(spec.get("chart", "ecdf") == "ecdf", "chart must be ecdf")
    fields = spec.get("fields", {})
    _object(fields, {"value", "group", "unit"}, "fields")
    require("value" in fields, "fields.value is required")
    require(all(isinstance(v, str) and v.strip() for v in fields.values()), "fields must map roles to nonempty column names")
    require(len(set(fields.values())) == len(fields), "Value, group and unit roles must name distinct source columns")
    options = spec.get("options", {})
    _object(options, OPTIONS, "options")
    require(options.get("x_scale", "linear") in ("linear", "log"), "x_scale must be linear or log")
    require(isinstance(options.get("grid", False), bool), "grid must be a boolean")
    _number(options.get("curve_line_width_pt", .8), "curve_line_width_pt", positive=True)
    if "x_limits" in options:
        limits = options["x_limits"]
        require(isinstance(limits, list) and len(limits) == 2, "x_limits must contain two finite numbers")
        low, high = [_number(v, "x_limits", positive=options.get("x_scale") == "log") for v in limits]
        require(low < high, "x_limits must be strictly ascending")
    if "x_ticks" in options:
        ticks = options["x_ticks"]
        require(isinstance(ticks, list) and ticks, "x_ticks must be a nonempty numeric list")
        for value in ticks:
            _number(value, "x_ticks", positive=options.get("x_scale") == "log")
        require(all(a < b for a, b in zip(ticks, ticks[1:])), "x_ticks must be unique and strictly ascending")
        require("x_limits" not in options or all(options["x_limits"][0] <= v <= options["x_limits"][1] for v in ticks), "x_ticks must lie within x_limits")
    tick_format = options.get("x_tick_format", "plain")
    require(tick_format in ("plain", "power10"), "x_tick_format must be plain or power10")
    require("x_tick_format" not in options or "x_ticks" in options, "x_tick_format requires explicit x_ticks")
    if tick_format == "power10":
        require(options.get("x_scale") == "log", "power10 tick labels require x_scale=log")
        require(all(float(v) == 10. ** round(math.log10(v)) for v in options["x_ticks"]), "power10 x_ticks must be exact integer powers of ten")
    order = spec.get("order", {})
    _object(order, {"group"}, "order")
    require("group" not in order or "group" in fields, "order.group requires fields.group")
    if "group" in order:
        require(isinstance(order["group"], list) and all(isinstance(v, str) and v.strip() for v in order["group"]), "order.group must list nonempty category strings")
    labels = spec.get("labels", {})
    _object(labels, {"x", "y"}, "labels")
    require(all(isinstance(v, str) for v in labels.values()), "labels must contain strings")
    colors = spec.get("colors")
    require(isinstance(colors, dict) and colors and all(isinstance(k, str) for k in colors), "colors must explicitly map every group to a color, or use the all key for ungrouped inputs")
    require(all(core.mcolors.is_color_like(v) and core.mcolors.to_rgba(v)[3] > 0 for v in colors.values()), "Colors must be valid with nonzero alpha")
    _object(spec.get("typography", {}), {"axis", "tick", "legend"}, "typography")
    legends = spec.get("legends", {})
    _object(legends, {"categorical", "review_thresholds"}, "legends")
    require("group" in fields or not legends, "Ungrouped ECDF has no legend; legend settings would be unused")
    if "categorical" in legends:
        require(isinstance(legends["categorical"], dict), "legends.categorical must be an object")
        # Curve keys must retain their actual color and stroke width.
        require(not {"edgecolor", "linewidth_pt", "title"} & set(legends["categorical"]), "ECDF legend colors and widths follow the curves; set curve_line_width_pt for both. Legend prose belongs in the caption.")
    formats = spec.get("formats", ["pdf", "svg", "png"])
    require(isinstance(formats, list) and formats and all(isinstance(v, str) for v in formats) and len(formats) == len(set(formats)), "formats must be a nonempty list without duplicates")
    require(set(formats) <= {"pdf", "svg", "png", "tiff"}, "Supported formats: pdf, svg, png, tiff")
    try:
        core.figure_profile.validate_layout(spec.get("layout", {}))
        core.figure_profile.validate_typography(spec.get("typography", {}))
    except core.figure_profile.ConfigurationError as exc:
        raise SpecError(str(exc)) from None


def prepare(data_path, spec):
    """Keep all raw observations and literal category/unit strings."""
    validate_spec(spec)
    data = pd.read_csv(data_path, dtype=object, keep_default_na=False)
    require(len(data) > 0, "Input has no observations")
    require(not any(c.startswith("_easyviz_") for c in data.columns), "Input columns starting _easyviz_ are reserved")
    f, options = spec["fields"], spec.get("options", {})
    for role, column in f.items():
        require(column in data.columns, f"Missing input column for {role}: {column}")
        require(not data[column].astype(str).str.strip().eq("").any(), f"Empty values in {column}; observations cannot be silently dropped")
    data["_easyviz_source_value_text"] = data[f["value"]].astype(str)
    try:
        data[f["value"]] = pd.to_numeric(data[f["value"]], errors="raise")
    except (ValueError, TypeError):
        raise SpecError(f"{f['value']} must contain only raw numeric values") from None
    values = data[f["value"]].to_numpy(float)
    require(np.isfinite(values).all(), "ECDF observations must be finite")
    require(options.get("x_scale", "linear") != "log" or np.all(values > 0), "Log x axes require strictly positive observations")
    if "x_limits" in options:
        low, high = options["x_limits"]
        require(np.all(values >= low) and np.all(values <= high), "x_limits would clip supplied observations")
    if "unit" in f:
        keys = [f["unit"]] + ([f["group"]] if "group" in f else [])
        require(not data.duplicated(keys).any(), "Duplicate unit/group rows; aggregate or select observations explicitly upstream")
    groups = core.ordered(data, f["group"], spec, "group") if "group" in f else ["all"]
    require(set(spec["colors"]) == set(groups), "colors must map exactly every observed group (or all without fields.group)")
    core.palette_colors(spec, groups)
    data["_easyviz_source_row"] = np.arange(1, len(data) + 1)
    return data


def setup(spec):
    layout, typography, rc = core.setup(spec)
    # Matplotlib's display-space simplifier can discard narrow ECDF steps in
    # vector exports even when the in-memory data are correct.
    rc["path.simplify"] = False
    if spec.get("options", {}).get("x_tick_format") == "power10":
        # MathText's regular face follows the actual text font, avoiding a
        # silent DejaVu switch for power labels in an Arial manuscript panel.
        rc["mathtext.default"] = "regular"
    return layout, typography, rc


def cumulative_data(data, spec):
    """Count all ties; one row per distinct numeric value in each group."""
    f = spec["fields"]
    groups = core.ordered(data, f["group"], spec, "group") if "group" in f else ["all"]
    rows = []
    for group in groups:
        subset = data[data[f["group"]] == group] if "group" in f else data
        count = 0
        for value, tied in subset.groupby(f["value"], sort=True):
            count += len(tied)
            rows.append({"group": group, "value": float(value), "jump_count": len(tied), "cumulative_count": count,
                         "observation_count": len(subset), "cumulative_fraction": count / len(subset),
                         "source_rows": json.dumps(tied["_easyviz_source_row"].astype(int).tolist(), separators=(",", ":"))})
    return pd.DataFrame(rows)


class _CurveLegendLayout(core.legend_layout.LegendLayout):
    """Use measured shared placement with line keys matching the ECDF curves."""
    def _categorical_or_size(self, request, cfg, position, ncol):
        entry = super()._categorical_or_size(request, cfg, position, ncol)
        for handle, color in zip(entry["artist"].legend_handles, request["colors"]):
            handle.set_marker("None")
            handle.set_linestyle("-")
            handle.set_color(color)
            handle.set_linewidth(request["linewidth_pt"])
            handle.set_solid_capstyle("butt")
        entry["chosen_settings"]["key_shape"] = "line"
        entry["chosen_settings"]["curve_line_width_pt"] = request["linewidth_pt"]
        return entry

    def _key_bounds(self, entry):
        boxes = super()._key_bounds(entry)
        return [box.padded(handle.get_linewidth() * self.fig.dpi / 144)
                for box, handle in zip(boxes, entry["artist"].legend_handles)]


def _limits(data, spec):
    options = spec.get("options", {})
    if "x_limits" in options:
        return list(map(float, options["x_limits"]))
    values = data[spec["fields"]["value"]].to_numpy(float)
    low, high = float(values.min()), float(values.max())
    if options.get("x_scale", "linear") == "log":
        pad = (math.log(high) - math.log(low)) * .08 if high != low else .15
        return [math.exp(math.log(low) - pad), math.exp(math.log(high) + pad)]
    pad = (high - low) * .08 if high != low else max(1., abs(low) * .08)
    return [low - pad, high + pad]


def _tick_labels(options):
    if options.get("x_tick_format", "plain") == "power10":
        return [f"$10^{{{round(math.log10(v))}}}$" for v in options["x_ticks"]]
    return [format(v, ".12g") for v in options["x_ticks"]]


def draw(data, spec, layout, typography):
    f, options = spec["fields"], spec.get("options", {})
    summary, limits = cumulative_data(data, spec), _limits(data, spec)
    groups = list(dict.fromkeys(summary["group"]))
    colors, width = core.palette_colors(spec, groups), options.get("curve_line_width_pt", .8)
    fig, ax = plt.subplots(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    fig.subplots_adjust(**layout["margins"])
    legend_config = deepcopy(spec.get("legends", {}))
    if "group" in f:
        # A curve key needs a visible line segment rather than the shared
        # circular-marker footprint. Retain explicit widths and all anchors.
        legend_config.setdefault("categorical", {}).setdefault("key_width_mm", 6.)
    manager = _CurveLegendLayout(fig, ax, typography, legend_config)
    artists = []
    for group_index, group in enumerate(groups):
        rows = summary[summary["group"] == group]
        x = np.r_[limits[0], rows["value"].to_numpy(float), limits[1]]
        y = np.r_[0., rows["cumulative_fraction"].to_numpy(float), 1.]
        line, = ax.step(x, y, where="post", color=colors[group], linewidth=width, linestyle="-", marker="None", solid_capstyle="butt", solid_joinstyle="miter", zorder=3)
        line.get_path().should_simplify = False
        line.set_gid(f"easyviz-ecdf-curve-{group_index}")
        artists.append({"group": group, "line": line})
    ax.set_axisbelow(True)
    if options.get("grid", False):
        ax.grid(axis="y", color="#e5e5e5", linewidth=.4, zorder=0)
    ax.set_xscale(options.get("x_scale", "linear"))
    ax.set_xlim(*limits)
    if "x_ticks" in options:
        require(all(limits[0] <= v <= limits[1] for v in options["x_ticks"]), "x_ticks must lie within displayed x_limits; supply explicit limits when needed")
        ax.set_xticks(options["x_ticks"], _tick_labels(options))
        ax.xaxis.set_minor_formatter(core.matplotlib.ticker.NullFormatter())
    # A small display-only vertical pad retains the entire 0/1 endpoint stroke.
    ax.set_ylim(-.02, 1.02)
    ax.set_yticks([0, .25, .5, .75, 1], ["0", "0.25", "0.5", "0.75", "1"])
    ax.set_xlabel(spec.get("labels", {}).get("x", f["value"]), fontsize=typography["axis"])
    ax.set_ylabel(spec.get("labels", {}).get("y", "Cumulative fraction"), fontsize=typography["axis"])
    ax.spines[["top", "right"]].set_visible(False)
    if "group" in f:
        manager.add_categorical(groups, [colors[g] for g in groups], shape="marker", linewidth_pt=width)
    if layout.get("auto_fit", False):
        fig._easyviz_auto_layout = core.auto_layout.fit(fig, ax, manager, core.check_tick_label_overlap)
        layout["margins"] = fig._easyviz_auto_layout["margins"]
    else:
        manager.layout()
    fig._easyviz_legend_layout, fig._easyviz_ecdf_artists = manager, artists
    return fig, colors, summary


def audit_source_artists(data_path, spec, fig):
    """Reread source values and derive expected step vertices independently."""
    raw = pd.read_csv(data_path, dtype=object, keep_default_na=False)
    f, options, issues, counts = spec["fields"], spec.get("options", {}), [], {}
    groups = spec.get("order", {}).get("group", list(dict.fromkeys(raw[f["group"]]))) if "group" in f else ["all"]
    ax, records = fig.axes[0], getattr(fig, "_easyviz_ecdf_artists", [])
    if [r["group"] for r in records] != groups:
        issues.append({"code": "group_order_or_curve_count_changed"})
    low, high = ax.get_xlim()
    for record in records:
        group, line = record["group"], record["line"]
        subset = raw[raw[f["group"]] == group] if "group" in f else raw
        values = sorted(float(v) for v in subset[f["value"]])
        unique, frequencies = [], []
        for value in values:
            if unique and value == unique[-1]:
                frequencies[-1] += 1
            else:
                unique.append(value)
                frequencies.append(1)
        fractions, running = [], 0
        for count in frequencies:
            running += count
            fractions.append(running / len(values))
        x, y = [low, *unique, high], [0., *fractions, 1.]
        vertices = [[x[0], y[0]]]
        for index in range(1, len(x)):
            vertices.extend([[x[index], y[index - 1]], [x[index], y[index]]])
        actual = line.get_path().vertices
        if line.get_drawstyle() != "steps-post" or line.get_path().should_simplify or actual.shape != (len(vertices), 2) or not np.allclose(actual, vertices, rtol=1e-12, atol=1e-12):
            issues.append({"code": "empirical_step_coordinates_changed", "group": group})
        if not np.allclose(core.mcolors.to_rgba(line.get_color()), core.mcolors.to_rgba(spec["colors"][group])) or not math.isclose(line.get_linewidth(), options.get("curve_line_width_pt", .8), abs_tol=1e-12) or line.get_linestyle() != "-" or line.get_marker() not in ("None", "none", "", " ") or line.get_alpha() not in (None, 1):
            issues.append({"code": "curve_style_changed", "group": group})
        if any(value < low or value > high for value in values):
            issues.append({"code": "axis_limits_hide_observations", "group": group})
        counts[group] = {"observations": len(values), "unique_values": len(unique), "tie_counts": frequencies}
    if set(ax.lines) != {r["line"] for r in records} or ax.collections or ax.patches or ax.images:
        issues.append({"code": "unaccounted_data_artist"})
    if ax.get_xscale() != options.get("x_scale", "linear") or not np.allclose(ax.get_ylim(), [-.02, 1.02]):
        issues.append({"code": "axis_scale_or_fraction_display_changed"})
    if "x_limits" in options and not np.allclose(ax.get_xlim(), options["x_limits"], rtol=0, atol=1e-12):
        issues.append({"code": "explicit_x_limits_changed"})
    if "x_ticks" in options and (len(ax.get_xticks()) != len(options["x_ticks"]) or not np.allclose(ax.get_xticks(), options["x_ticks"], rtol=0, atol=1e-12)):
        issues.append({"code": "explicit_x_ticks_changed"})
    if "x_ticks" in options and [t.get_text() for t in ax.get_xticklabels()] != _tick_labels(options):
        issues.append({"code": "explicit_x_tick_labels_changed"})
    manager = fig._easyviz_legend_layout
    if "group" in f:
        keys = [h for entry in manager.entries for h in entry["artist"].legend_handles]
        labels = [t.get_text() for entry in manager.entries for t in entry["artist"].get_texts()]
        if labels != groups or len(keys) != len(groups) or any(not np.allclose(core.mcolors.to_rgba(handle.get_color()), core.mcolors.to_rgba(spec["colors"][group])) or handle.get_linewidth() != options.get("curve_line_width_pt", .8) or handle.get_linestyle() != "-" or handle.get_marker() not in ("None", "none", "", " ") for group, handle in zip(groups, keys)):
            issues.append({"code": "curve_legend_mapping_changed"})
    return {"status": "pass" if not issues else "needs_revision", "source_rows": len(raw), "audited_observations": sum(v["observations"] for v in counts.values()), "groups": counts, "ties_retained": True, "smoothing_applied": False, "experimental_independence_inferred": False, "issues": issues}


def _clipped_text(fig):
    renderer, result, skipped = fig.canvas.get_renderer(), [], set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            low, high = sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                    skipped.update((tick.label1, tick.label2))
    for artist in fig.findobj(core.Text):
        if artist in skipped or not artist.get_visible() or not artist.get_text().strip():
            continue
        bounds = artist.get_window_extent(renderer)
        if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.width + 1 or bounds.y1 > fig.bbox.height + 1:
            result.append({"text": artist.get_text(), "bounds_px": list(map(float, bounds.extents))})
    return result


def render(data_path, spec, out, *, spec_path=None):
    """Persist failed QA before raising; old exports never imply a new pass."""
    data_path, out = Path(data_path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False, "note": "Exports may be stale or unverified until this run passes."})
    fig, before = None, set(plt.get_fignums())
    try:
        input_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
        data = prepare(data_path, spec)
        resolved = deepcopy(spec)
        resolved.setdefault("chart", "ecdf")
        resolved.setdefault("formats", ["pdf", "svg", "png"])
        resolved.setdefault("layout", {}).setdefault("auto_fit", "margins" not in resolved.get("layout", {}))
        layout, typography, rc = setup(resolved)
        with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig, colors, summary = draw(data, resolved, layout, typography)
            fig.canvas.draw()
            audit = audit_source_artists(data_path, resolved, fig)
            clipped = _clipped_text(fig)
            overlap, oblique = core.check_tick_label_overlap(fig, fig.canvas.get_renderer())
            legends, fitted = fig._easyviz_legend_layout.validate(), getattr(fig, "_easyviz_auto_layout", None)
            exports = core.export(fig, out, resolved, layout)
            if hashlib.sha256(data_path.read_bytes()).hexdigest() != input_hash:
                audit["status"] = "needs_revision"
                audit["issues"].append({"code": "source_changed_during_render"})
            missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            passed = not clipped and not overlap and not missing and audit["status"] == legends["status"] == "pass" and (not fitted or fitted["status"] == "pass")
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "input_rows": len(data), "input_sha256": input_hash, "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "clipped_text": clipped, "overlapping_tick_labels": overlap, "unchecked_oblique_tick_labels": oblique, "missing_glyphs": missing, "source_to_artist_audit": audit, "legend_layout": legends, "exports": exports, "visual_review_required": True}
            settings = deepcopy(resolved)
            settings.update(layout=layout, typography=typography, resolved_colors=colors, input_file=str(data_path.resolve()), input_sha256=input_hash, supplied_spec=deepcopy(spec), spec_sha256=hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest())
            settings["axis"] = {"x_scale": fig.axes[0].get_xscale(), "x_limits": list(map(float, fig.axes[0].get_xlim())), "y_limits": list(map(float, fig.axes[0].get_ylim())), "explicit_x_ticks": resolved.get("options", {}).get("x_ticks"), "x_tick_format": resolved.get("options", {}).get("x_tick_format", "plain"), "x_tick_labels": [t.get_text() for t in fig.axes[0].get_xticklabels()]}
            settings["curve_policy"] = {"method": "count(value <= x) / observation_count", "drawstyle": "steps-post", "ties": "full jump count", "line_width_pt": resolved.get("options", {}).get("curve_line_width_pt", .8), "horizontal_tails": "display extension to x limits", "fraction_range": [0, 1], "vertical_display_padding": .02, "markers": "none", "path_simplification": False}
            settings["renderer"] = {"version": VERSION, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "helper_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in HELPERS}}
            settings["runtime"] = {"python": platform.python_version(), **{name: package_version(name) for name in ("matplotlib", "numpy", "pandas", "Pillow", "pypdf")}}
            if spec_path is not None:
                settings["spec_file"], settings["spec_file_sha256"] = str(Path(spec_path).resolve()), hashlib.sha256(Path(spec_path).read_bytes()).hexdigest()
            if fitted:
                qa["auto_layout"] = settings["auto_layout"] = fitted
            settings["legend_layout"] = legends
            settings["resolved_legends"] = deepcopy(fig._easyviz_legend_layout.config)
            data.to_csv(out / "plotting-data.csv", index=False)
            summary.to_csv(out / "cumulative-data.csv", index=False)
            write_json(out / "settings.json", settings)
            write_json(out / "stats.json", {"method": "unweighted_empirical_distribution", "tests_performed": False, "smoothing_applied": False, "distributions_fitted": False, "confidence_intervals_computed": False, "experimental_independence_inferred": False, "observation_counts": {group: int(rows["observation_count"].iloc[0]) for group, rows in summary.groupby("group", sort=False)}})
            write_json(out / "qa.json", qa)
            require(passed, "Canvas or source-to-curve QA needs revision; inspect qa.json and the exported panel. Preserve final dimensions and fonts or explicitly request a larger panel.")
            return qa
    except Exception as exc:
        status = json.loads((out / "qa.json").read_text())
        if status.get("status") == "in_progress":
            status.update(status="failed", error=str(exc), valid_outputs=False)
            write_json(out / "qa.json", status)
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
        parser.error("--data, --spec and --out are required unless --describe-spec is used")
    try:
        spec = json.loads(args.spec.read_text())
        qa = render(args.data, spec, args.out, spec_path=args.spec)
    except (ValueError, OSError, ImportError) as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / "qa.json"
        if not path.exists() or not isinstance(locals().get("spec"), dict):
            write_json(path, {"status": "failed", "valid_outputs": False, "error": str(exc)})
        parser.exit(2, f"EasyViz ECDF: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}))


if __name__ == "__main__":
    main()
