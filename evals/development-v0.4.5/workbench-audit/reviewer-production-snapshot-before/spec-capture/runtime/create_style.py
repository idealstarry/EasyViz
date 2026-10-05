"""Editable visual starting values for new Create requests only.

This module uses only the standard library. Applying these values never selects
a palette, changes data/axis semantics or upgrades an already saved panel spec.
Legacy mode and figure-profile drafts retain their accepted fallback behavior.
"""
from __future__ import annotations

from copy import deepcopy


STYLE_MODES = ("crisp", "legacy")
LINE_ROLES = {
    "data": {"line_width_pt": .85},
    "summary": {"line_width_pt": .75},
    "reference": {"line_width_pt": .45, "color": "#747474", "linestyle": "--"},
    "axis": {"line_width_pt": .55, "color": "#222222"},
    "grid": {"line_width_pt": .3, "color": "#E8E8E8", "linestyle": "-"},
}


def apply_defaults(spec, *, mode="crisp", layout_stroke_explicit=None):
    """Return a new spec, filling missing cosmetics while retaining overrides.

    A caller that constructs a default layout must state whether its stroke
    width came from the user. A supplied global width retains the renderer's
    global-width fallback; explicit per-role widths still take precedence.
    Profiles are accepted figure-level decisions and do not receive new values.
    """
    if mode not in STYLE_MODES:
        raise ValueError("style_mode must be crisp or legacy")
    result = deepcopy(spec)
    if mode == "legacy" or "profile" in result:
        return result
    explicit_width = ("line_width_pt" in result.get("layout", {})
                      if layout_stroke_explicit is None else layout_stroke_explicit)
    supplied_roles = result.get("line_roles", {})
    if not isinstance(supplied_roles, dict):
        raise ValueError("line_roles must be an object")
    defaults = deepcopy(LINE_ROLES)
    if explicit_width:
        for properties in defaults.values():
            properties.pop("line_width_pt", None)
    for role, properties in supplied_roles.items():
        if not isinstance(properties, dict):
            raise ValueError(f"line_roles.{role} must be an object")
        defaults.setdefault(role, {}).update(deepcopy(properties))
    result["line_roles"] = defaults
    options = result.get("options", {})
    if not isinstance(options, dict):
        raise ValueError("options must be an object")
    observation_defaults = {}
    if result.get("chart") in ("scatter", "distribution"):
        observation_defaults.update(alpha=1, point_style="filled")
    if result.get("chart") == "distribution" and options.get("kind", "box") == "box":
        observation_defaults.update(box_style="outline", box_width=.18)
    if observation_defaults:
        result["options"] = {**observation_defaults, **deepcopy(options)}
    return result
