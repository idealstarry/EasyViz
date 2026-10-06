"""Validate panel specifications and resolve shared figure settings.

This module only reads configuration. It never changes inputs, assigns colors by
the categories present in a panel, or assembles separate panel exports.
"""
from __future__ import annotations

from copy import deepcopy
import difflib
import hashlib
import json
import math
from pathlib import Path

from matplotlib import colors as mcolors


class ConfigurationError(ValueError):
    """A misspelled, ambiguous or conflicting plotting configuration."""


LAYOUT_KEYS = {"width_mm", "height_mm", "font", "font_size_pt", "line_width_pt", "dpi", "margins", "auto_fit"}
SHARED_LAYOUT_KEYS = {"font", "font_size_pt", "line_width_pt", "dpi"}
TYPOGRAPHY_KEYS = {"axis", "tick", "legend", "annotation", "title", "panel"}
ORDER_KEYS = {"x", "y", "group", "sample", "category"}
LABEL_KEYS = {"x", "y", "color", "size", "title", "panel"}
SPEC_KEYS = {"chart", "fields", "layout", "typography", "options", "order", "labels", "colors", "palette", "colormap", "formats", "seed", "statistics", "legends", "profile", "panel", "continuous_scale", "size_scale", "line_roles"}
LINE_ROLES = {"data", "summary", "reference", "axis", "grid"}
MARGIN_KEYS = {"left", "right", "bottom", "top"}


def _require(condition, message):
    if not condition:
        raise ConfigurationError(message)


def _object(value, path):
    _require(isinstance(value, dict), f"{path} must be an object")
    _require(all(isinstance(key, str) for key in value), f"{path} keys must be strings")


def _keys(value, allowed, path):
    _object(value, path)
    unknown = sorted(set(value) - allowed)
    if unknown:
        hints = []
        for key in unknown:
            # The common spelling otherwise silently leaves the default at 8 pt.
            matches = ["font_size_pt"] if key == "fontsize_pt" and "font_size_pt" in allowed else difflib.get_close_matches(key, sorted(allowed), n=1, cutoff=.65)
            if matches:
                hints.append(f"{key}: use {matches[0]}")
        suffix = f" ({'; '.join(hints)})" if hints else ""
        raise ConfigurationError(f"Unknown {path} keys: {unknown}{suffix}")


def _string(value, path, *, empty=False):
    _require(isinstance(value, str) and (empty or bool(value.strip())), f"{path} must be a {'string' if empty else 'nonempty string'}")


def _number(value, path, *, positive=False):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), f"{path} must be a finite JSON number")
    if positive:
        _require(value > 0, f"{path} must be positive")


def _limits(value, path):
    _require(isinstance(value, list) and len(value) == 2, f"{path} must be two finite numbers")
    for item in value:
        _number(item, path)
    _require(value[0] <= value[1], f"{path} must be ascending")


def validate_layout(layout, path="layout", *, shared=False):
    _keys(layout, SHARED_LAYOUT_KEYS if shared else LAYOUT_KEYS, path)
    if "auto_fit" in layout:
        _require(isinstance(layout["auto_fit"], bool), f"{path}.auto_fit must be a boolean")
        _require(not layout["auto_fit"] or "margins" not in layout,
                 f"{path}.auto_fit and explicit margins are conflicting layout choices")
    for key, value in layout.items():
        if key == "auto_fit":
            continue
        elif key == "font":
            _string(value, f"{path}.font")
        elif key == "margins":
            _keys(value, MARGIN_KEYS, f"{path}.margins")
            for edge, bound in value.items():
                _number(bound, f"{path}.margins.{edge}")
                _require(0 < bound < 1, f"{path}.margins.{edge} must lie within 0..1")
        else:
            _number(value, f"{path}.{key}", positive=True)
            if key == "dpi":
                _require(float(value).is_integer(), f"{path}.dpi must be an integer")


def validate_typography(typography, path="typography"):
    _keys(typography, TYPOGRAPHY_KEYS, path)
    for role, size in typography.items():
        _number(size, f"{path}.{role}", positive=True)


def validate_line_roles(roles, path="line_roles"):
    """Validate optional explicit stroke overrides without adding a theme."""
    _keys(roles, LINE_ROLES, path)
    for role, properties in roles.items():
        allowed = {"line_width_pt", "color"}
        if role != "axis":
            allowed.add("linestyle")
        _keys(properties, allowed, f"{path}.{role}")
        if "line_width_pt" in properties:
            _number(properties["line_width_pt"], f"{path}.{role}.line_width_pt", positive=True)
        if "color" in properties:
            color = properties["color"]
            _require(isinstance(color, str) and mcolors.is_color_like(color),
                     f"Invalid {path}.{role}.color")
        if "linestyle" in properties:
            _require(isinstance(properties["linestyle"], str)
                     and properties["linestyle"] in ("-", "--", ":", "-."),
                     f"{path}.{role}.linestyle must be -, --, : or -.")


def _colors(mapping, path):
    _object(mapping, path)
    _require(bool(mapping), f"{path} must contain category-to-color mappings")
    canonical = []
    for label, color in mapping.items():
        _string(label, f"{path} category")
        _require(mcolors.is_color_like(color), f"Invalid color for {path}.{label}")
        canonical.append(mcolors.to_hex(color, keep_alpha=True))
    _require(len(set(canonical)) == len(canonical), f"Distinct categories in {path} must have distinct colors")


def _colormap(value, path):
    if isinstance(value, str):
        _string(value, path)
    else:
        _require(isinstance(value, list) and len(value) >= 2 and all(mcolors.is_color_like(c) for c in value), f"{path} must be a colormap name or a list of at least two colors")


def validate_spec(spec, required_fields, optional_fields, chart_options, shared_options):
    """Check declared keys and types before loading or transforming source data.

    Chart contracts are supplied by the renderer so new chart-specific roles and
    options have one owner. Their scientific value checks remain in the renderer.
    """
    _keys(spec, SPEC_KEYS, "specification")
    chart = spec.get("chart")
    _require(isinstance(chart, str) and chart in required_fields, f"chart must be one of {list(required_fields)}")
    for key in ("fields", "layout", "typography", "options", "order", "labels", "statistics", "legends"):
        if key in spec:
            _object(spec[key], key)
    validate_layout(spec.get("layout", {}))
    validate_typography(spec.get("typography", {}))
    validate_line_roles(spec.get("line_roles", {}))
    fields = spec.get("fields", {})
    _keys(fields, set(required_fields[chart]) | set(optional_fields.get(chart, ())), "fields")
    _require(all(role in fields for role in required_fields[chart]), f"{chart} requires fields {required_fields[chart]}")
    for role, column in fields.items():
        _string(column, f"fields.{role}")
    _keys(spec.get("labels", {}), LABEL_KEYS, "labels")
    for role, value in spec.get("labels", {}).items():
        _string(value, f"labels.{role}", empty=True)
    _keys(spec.get("order", {}), ORDER_KEYS, "order")
    for role, values in spec.get("order", {}).items():
        _require(isinstance(values, list), f"order.{role} must be a list")
        _require(all(isinstance(v, (str, int, float)) and not isinstance(v, bool) and (not isinstance(v, float) or math.isfinite(v)) for v in values), f"order.{role} must contain category labels, not objects or nulls")
        _require(len(set(map(str, values))) == len(values), f"order.{role} contains duplicate category labels")
    options = spec.get("options", {})
    unknown = sorted(set(options) - shared_options - chart_options[chart])
    _require(not unknown, f"Unknown {chart} options: {unknown}")
    if chart == "scatter":
        size_options = {"size_max", "max_area_pt2", "size_legend"}
        if "size" in fields:
            _require("point_area_pt2" not in options, "options.point_area_pt2 conflicts with scatter fields.size; use max_area_pt2 for proportional areas")
        else:
            _require(not (size_options & set(options)), "Scatter size options require fields.size")
    for key in ("grid", "regression", "annotate_values", "percent_axis", "state_markers"):
        if key in options:
            _require(isinstance(options[key], bool), f"options.{key} must be a boolean")
    for key in ("x_rotation", "point_area_pt2", "alpha", "bar_width", "size_max", "max_area_pt2", "small_positive_area_pt2"):
        if key in options:
            _number(options[key], f"options.{key}")
    for key in ("x_limits", "y_limits", "color_limits"):
        if key in options:
            _limits(options[key], f"options.{key}")
    if "color_center" in options:
        _number(options["color_center"], "options.color_center")
    for key in ("x_scale", "y_scale"):
        if key in options:
            _require(options[key] in ("linear", "log"), f"options.{key} must be linear or log")
    for key in ("point_color", "regression_color"):
        if key in options:
            _require(mcolors.is_color_like(options[key]), f"Invalid options.{key}")
    for key in ("kind", "orientation", "normalization", "missing_categories", "missing_cells", "value_format"):
        if key in options:
            _string(options[key], f"options.{key}")
    if "cell_aspect" in options:
        value = options["cell_aspect"]
        if isinstance(value, str):
            _require(value in ("auto", "equal"), "options.cell_aspect must be auto, equal or a positive number")
        else:
            _number(value, "options.cell_aspect", positive=True)
    if "size_legend" in options:
        _require(isinstance(options["size_legend"], list) and bool(options["size_legend"]), "options.size_legend must be a nonempty list")
        for value in options["size_legend"]:
            _number(value, "options.size_legend", positive=True)
    if "reference_lines" in options:
        lines = options["reference_lines"]
        _keys(lines, {"x", "y"}, "options.reference_lines")
        for direction, positions in lines.items():
            _require(isinstance(positions, list), f"options.reference_lines.{direction} must be a list")
            for position in positions:
                _number(position, f"options.reference_lines.{direction}")
                if options.get(f"{direction}_scale", "linear") == "log":
                    _require(position > 0, f"Logarithmic reference_lines.{direction} positions must be strictly positive")
    if "colors" in spec:
        _colors(spec["colors"], "colors")
    if "palette" in spec:
        _string(spec["palette"], "palette")
    if "colormap" in spec:
        _colormap(spec["colormap"], "colormap")
    if "formats" in spec:
        formats = spec["formats"]
        _require(isinstance(formats, list) and bool(formats) and all(isinstance(v, str) and v in ("pdf", "png", "svg", "tiff") for v in formats), "formats must be a nonempty list of pdf, png, svg or tiff")
        _require(len(formats) == len(set(formats)), "formats must not contain duplicates")
    if "seed" in spec:
        _require(isinstance(spec["seed"], int) and not isinstance(spec["seed"], bool) and spec["seed"] >= 0, "seed must be a nonnegative integer")
    statistics = spec.get("statistics", {})
    _keys(statistics, {"method", "groups", "unit", "annotate", "analysis"}, "statistics")
    if "analysis" in statistics:
        _require(not ({"method", "groups", "unit"} & set(statistics)),
                 "statistics.analysis cannot be combined with legacy method, groups or unit; the adopted analysis supplies them")
        _require(isinstance(statistics["analysis"], dict), "statistics.analysis must be an adopted-analysis binding object")
    for key in ("method", "unit"):
        if key in statistics:
            _string(statistics[key], f"statistics.{key}")
    if "groups" in statistics:
        groups = statistics["groups"]
        _require(isinstance(groups, list) and len(groups) == 2 and all(isinstance(v, (str, int, float)) and not isinstance(v, bool) for v in groups), "statistics.groups must be two category labels")
    if "annotate" in statistics:
        _require(isinstance(statistics["annotate"], bool), "statistics.annotate must be a boolean")
    if statistics.get("method") == "none":
        _require("groups" not in statistics and "unit" not in statistics and not statistics.get("annotate", False), "statistics.method='none' cannot be combined with groups, unit, or annotate=true")
    for key in ("profile", "panel", "continuous_scale", "size_scale"):
        if key in spec:
            _string(spec[key], key)


def validate_profile(profile):
    _keys(profile, {"version", "layout", "typography", "colors", "continuous_scales", "size_scales", "panels"}, "figure profile")
    _require(type(profile.get("version")) is int and profile["version"] == 1, "figure profile version must be 1")
    _require("layout" in profile, "figure profile requires shared layout")
    validate_layout(profile["layout"], "figure profile.layout", shared=True)
    _require(SHARED_LAYOUT_KEYS <= set(profile["layout"]), f"figure profile.layout requires {sorted(SHARED_LAYOUT_KEYS)}")
    validate_typography(profile.get("typography", {}), "figure profile.typography")
    if "colors" in profile:
        _colors(profile["colors"], "figure profile.colors")
    panels = profile.get("panels", {})
    _object(panels, "figure profile.panels")
    _require(bool(panels), "figure profile requires at least one named panel")
    for name, dimensions in panels.items():
        _string(name, "figure profile panel name")
        _keys(dimensions, {"width_mm", "height_mm"}, f"figure profile.panels.{name}")
        _require(set(dimensions) == {"width_mm", "height_mm"}, f"figure profile.panels.{name} requires width_mm and height_mm")
        for key, value in dimensions.items():
            _number(value, f"figure profile.panels.{name}.{key}", positive=True)
    scales = profile.get("continuous_scales", {})
    _object(scales, "figure profile.continuous_scales")
    for name, scale in scales.items():
        _string(name, "figure profile scale name")
        _keys(scale, {"colormap", "color_limits", "color_center"}, f"figure profile.continuous_scales.{name}")
        _require("colormap" in scale and "color_limits" in scale, f"continuous scale {name} requires colormap and color_limits")
        _colormap(scale["colormap"], f"continuous scale {name}.colormap")
        _limits(scale["color_limits"], f"continuous scale {name}.color_limits")
        _require(scale["color_limits"][0] < scale["color_limits"][1], f"continuous scale {name}.color_limits must have a strictly increasing range")
        if "color_center" in scale:
            _number(scale["color_center"], f"continuous scale {name}.color_center")
            _require(scale["color_limits"][0] < scale["color_center"] < scale["color_limits"][1], f"continuous scale {name}.color_center must lie strictly within color_limits")
    size_scales = profile.get("size_scales", {})
    _object(size_scales, "figure profile.size_scales")
    for name, scale in size_scales.items():
        _string(name, "figure profile size scale name")
        _keys(scale, {"size_max", "max_area_pt2", "size_legend"}, f"figure profile.size_scales.{name}")
        _require("size_max" in scale and "max_area_pt2" in scale, f"size scale {name} requires size_max and max_area_pt2")
        # max_area_pt2 is an ideal circle's geometric fill area, excluding
        # stroke. The renderer converts it to Matplotlib's squared diameter.
        for key in ("size_max", "max_area_pt2"):
            _number(scale[key], f"size scale {name}.{key}", positive=True)
        if "size_legend" in scale:
            levels = scale["size_legend"]
            _require(isinstance(levels, list) and bool(levels), f"size scale {name}.size_legend must be a nonempty list")
            for level in levels:
                _number(level, f"size scale {name}.size_legend", positive=True)
                _require(level <= scale["size_max"], f"size scale {name}.size_legend values must not exceed size_max")
            _require(len(set(levels)) == len(levels), f"size scale {name}.size_legend values must be distinct")


def _equal(a, b, *, color=False):
    if color:
        return mcolors.to_rgba(a) == mcolors.to_rgba(b)
    return a == b


def _merge_shared(local, shared, path, *, colors=False):
    result = deepcopy(shared)
    for key, value in local.items():
        _require(key not in shared or _equal(value, shared[key], color=colors), f"{path}.{key} conflicts with the figure profile; update the shared profile or remove the local setting")
        _require(not colors or key in shared, f"{path}.{key} is absent from the figure profile; add it to the shared colors mapping")
        result[key] = deepcopy(value)
    return result


def resolve(spec, *, profile_path=None, panel=None, spec_path=None):
    """Return a new resolved spec and its profile provenance, without mutation.

    A path declared inside the spec is relative to that spec's directory. A CLI
    or Python profile_path follows the caller's working directory. Declarations
    must agree when both are supplied. All shared-setting conflicts are errors.
    """
    _object(spec, "specification")
    source = deepcopy(spec)
    declared = source.get("profile")
    if declared is not None:
        _string(declared, "profile")
        base = Path(spec_path).resolve().parent if spec_path is not None else Path.cwd()
        declared = (base / declared).resolve()
    supplied = Path(profile_path).resolve() if profile_path is not None else None
    if supplied is not None and declared is not None:
        _require(supplied == declared, "--profile and specification.profile name different files")
    selected_path = supplied or declared
    selected_panel = panel if panel is not None else source.get("panel")
    if panel is not None and "panel" in source:
        _require(panel == source["panel"], "--panel and specification.panel disagree")
    if selected_path is None:
        _require(selected_panel is None and "continuous_scale" not in source and "size_scale" not in source, "panel and continuous_scale require a figure profile; size_scale also requires a figure profile")
        return source, None
    _string(selected_panel, "panel")
    raw = selected_path.read_bytes()
    profile = json.loads(raw)
    validate_profile(profile)
    _require(selected_panel in profile["panels"], f"Unknown panel {selected_panel!r}; available panels: {list(profile['panels'])}")
    # Validate objects before merging, including local typos even when the profile
    # supplies the correctly spelled field.
    validate_layout(source.get("layout", {}))
    validate_typography(source.get("typography", {}))
    source["layout"] = _merge_shared(source.get("layout", {}), {**profile["layout"], **profile["panels"][selected_panel]}, "layout")
    source["typography"] = _merge_shared(source.get("typography", {}), profile.get("typography", {}), "typography")
    if "colors" in profile:
        _require("palette" not in source, "palette cannot be combined with figure profile.colors; remove palette and use the shared category mapping")
        if "colors" in source:
            _colors(source["colors"], "colors")
        source["colors"] = _merge_shared(source.get("colors", {}), profile["colors"], "colors", colors=True)
    scale_name = source.get("continuous_scale")
    if scale_name is not None:
        _string(scale_name, "continuous_scale")
        _require(source.get("chart") in ("heatmap", "dotplot"), "continuous_scale is supported for heatmap and dotplot")
        _require(scale_name in profile.get("continuous_scales", {}), f"Unknown continuous_scale: {scale_name}")
        scale = profile["continuous_scales"][scale_name]
        if "colormap" in source:
            _require(source["colormap"] == scale["colormap"], "colormap conflicts with the figure profile continuous scale")
        source["colormap"] = deepcopy(scale["colormap"])
        _object(source.get("options", {}), "options")
        shared = {key: value for key, value in scale.items() if key != "colormap"}
        if "color_center" not in shared:
            _require("color_center" not in source.get("options", {}), "options.color_center conflicts with the uncentered figure profile continuous scale")
        source["options"] = _merge_shared(source.get("options", {}), shared, "options")
    size_scale_name = source.get("size_scale")
    if size_scale_name is not None:
        _string(size_scale_name, "size_scale")
        fields = source.get("fields", {})
        _object(fields, "fields")
        _require(source.get("chart") == "dotplot" or (source.get("chart") == "scatter" and "size" in fields), "size_scale is supported only for dotplot or scatter with fields.size")
        _require(size_scale_name in profile.get("size_scales", {}), f"Unknown size_scale: {size_scale_name}")
        _object(source.get("options", {}), "options")
        source["options"] = _merge_shared(source.get("options", {}), profile["size_scales"][size_scale_name], "options")
    source["profile"] = str(selected_path)
    source["panel"] = selected_panel
    record = {"path": str(selected_path), "sha256": hashlib.sha256(raw).hexdigest(), "panel": selected_panel, "continuous_scale": scale_name, "size_scale": size_scale_name, "source_specification": deepcopy(spec), "shared_settings": deepcopy(profile)}
    return source, record
