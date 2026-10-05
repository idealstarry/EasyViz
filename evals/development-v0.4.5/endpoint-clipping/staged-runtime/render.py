#!/usr/bin/env python3
"""Render one manuscript panel from a CSV and an explicit JSON specification."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import importlib.util
from importlib.metadata import version as package_version
import json
import io
import math
import os
import platform
from pathlib import Path
import sys
import tempfile
import warnings

# Capture this executing renderer before importing third-party code or sibling
# helpers. Timestamp/size-valid .pyc caches can still contain different code;
# compare the compiled source with the actual executing module, rather than
# declaring whatever file happens to exist to be the code that ran. Code
# equality does not depend on the loader's filename or module metadata.
_RENDER_SOURCE_BYTES = Path(__file__).read_bytes()
if compile(_RENDER_SOURCE_BYTES, str(Path(__file__)), "exec", dont_inherit=True) != sys._getframe().f_code:
    raise RuntimeError("Executing renderer code differs from its source file; remove stale bytecode and reload the current renderer")
RUNTIME_SOURCE_DIGESTS = {"render.py": hashlib.sha256(_RENDER_SOURCE_BYTES).hexdigest()}

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors, font_manager
from matplotlib.text import Text
import numpy as np
import pandas as pd
from PIL import Image

def _load_captured_helper(module_name, filename):
    """Execute and bind one exact sibling source snapshot, never cached code."""
    path = Path(__file__).with_name(filename)
    raw = path.read_bytes()
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(module_spec)
    # exec_module can execute an existing .pyc or read bytes independently of
    # the later digest. Compile the captured bytes so the digest describes the
    # helper that actually ran, even if its source changes during execution.
    RUNTIME_SOURCE_DIGESTS[filename] = hashlib.sha256(raw).hexdigest()
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


# Portable importlib callers retain normal module metadata and sibling paths.
legend_layout = _load_captured_helper("easyviz_legend_layout", "legend_layout.py")
figure_profile = _load_captured_helper("easyviz_figure_profile", "figure_profile.py")
auto_layout = _load_captured_helper("easyviz_auto_layout", "auto_layout.py")
annotation_review = _load_captured_helper("easyviz_annotation_review", "annotation_review.py")
figure_elements = _load_captured_helper("easyviz_figure_elements", "figure_elements.py")
panel_readability = _load_captured_helper("easyviz_panel_readability", "panel_readability.py")
observation_clipping = _load_captured_helper("easyviz_observation_clipping", "observation_clipping.py")


class SpecError(ValueError):
    """The requested panel cannot faithfully represent the supplied input."""


VERSION = "0.4.4"


REQUIRED = {
    "heatmap": ("row", "column", "value"),
    "composition": ("sample", "category", "value"),
    "dotplot": ("x", "y", "size", "color"),
    "scatter": ("x", "y"),
    "distribution": ("group", "value"),
}
# Discovery metadata only: focused recipes remain separate scientific contracts.
FOCUSED_RECIPES = {
    chart: {"script": str(Path(__file__).resolve().with_name(f"{chart}_plot.py")),
            "required_roles": roles,
            "doc": str(Path(__file__).resolve().parents[1] / "references" / f"{chart}-plot.md")}
    for chart, roles in {
        "paired": ["unit", "condition", "value"],
        "replicate": ["condition", "unit", "value"],
        "ecdf": ["value"],
        "interval": ["label", "estimate", "lower", "upper"],
        "timecourse": ["x", "estimate"],
    }.items()
}
FOCUSED_RECIPES["replicate"]["conditional_roles"] = {
    "component": "Required for stacked/grouped modes; rejected for summary mode."
}
FOCUSED_RECIPES["timecourse"]["conditional_roles"] = {
    "sd": "Required for uncertainty.kind=sd; supplied nonnegative SD, no inference from mean-only rows.",
    "lower,upper": "Required for uncertainty.kind=supplied_bounds; explicit lower/upper meanings must be declared.",
}
FOCUSED_RECIPES["annotated_matrix"] = {
    "script": str(Path(__file__).resolve().with_name("annotated_matrix.py")),
    "required_roles": ["row", "column", "value"],
    "doc": str(Path(__file__).resolve().parents[1] / "references/annotated-matrix.md"),
}
WORKFLOW_TOOLS = {
    name: {"script": str(Path(__file__).resolve().with_name(f"{name}.py")),
           "doc": str(Path(__file__).resolve().parents[1] / "references" / document),
           "tracks": tracks, "purpose": purpose}
    for name, document, tracks, purpose in (
        ("inspect_data", "data-exploration.md", ["create", "reproduce"],
         "Inventory files in either track; propose descriptive reading tasks only in create. Use --inventory-only for reproduce."),
        ("analyze", "statistical-analysis.md", ["create"],
         "Execute a declared analysis plan and retain design, effects, exclusions and multiplicity."),
        ("reference_packet", "reference-to-code.md", ["reproduce"],
         "Stage reference and user data; turn explicit image readings into an unresolved implementation plan."),
        ("audit_reproduction", "complex-reproduction.md", ["reproduce"],
         "Check adopted layer coverage, source/output bindings and supplied numeric evidence; visual and scientific review remain separate."),
        ("figure_workbench", "figure-workbench.md", ["create", "reproduce"],
         "Collect SVG element/region instructions for an Agent to edit plotting code and rerender."),
        ("preview_choices", "preview-choices.md", ["create"],
         "Render same-source descriptive candidates with fixed dimensions, typography and scales; choose by the reading task after image review."),
        ("apply_figure_requests", "apply-figure-requests.md", ["create", "reproduce"],
         "Prepare verified cosmetic spec edits, record Agent rerenders, and restore accepted source/export snapshots into fresh attempts."),
        ("create_candidates", "first-draft.md", ["create"],
         "Render bounded scene proposals for an explicitly new draft while preserving scientific mappings, source data and locked settings; inspect actual exports before choosing."),
        ("create_review", "first-draft.md", ["create"],
         "Stage and validate a hash-bound pre-delivery review attestation with actual export/source evidence. A recorded attestation cannot prove image inspection or aesthetic quality."),
    )
}
OPTIONAL_FIELDS = {"scatter": {"group", "unit", "size"}, "distribution": {"unit"}, "composition": {"denominator"}, "dotplot": {"state"}}
DEFAULT_COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#F0E442"]
SHARED_OPTIONS = {"grid", "x_rotation", "x_limits", "y_limits", "x_scale", "y_scale"}
CHART_OPTIONS = {
    "heatmap": {"color_limits", "color_center", "cell_aspect", "annotate_values", "value_format", "cell_border_color", "cell_border_width_pt", "column_labels"},
    "composition": {"normalization", "missing_categories", "bar_width", "percent_axis"},
    "dotplot": {"color_limits", "color_center", "size_max", "max_area_pt2", "size_legend", "missing_cells", "state_markers", "small_positive_area_pt2"},
    "scatter": {"point_area_pt2", "alpha", "point_style", "point_edge_width_pt", "point_color", "regression", "regression_color", "size_max", "max_area_pt2", "size_legend", "reference_lines"},
    "distribution": {"point_area_pt2", "alpha", "point_style", "point_edge_width_pt", "point_color", "kind", "box_style", "box_width", "box_fill_alpha", "violin_width", "violin_fill_alpha", "violin_inner", "violin_inner_width", "violin_inner_fill_alpha", "violin_median_visible", "orientation", "point_layout", "point_max_offset_mm", "point_gap_pt", "point_category_offset"},
}
SCHEMA = {
    "chart": list(REQUIRED), "fields_by_chart": REQUIRED,
    "focused_recipes": FOCUSED_RECIPES,
    "workflow_tools": WORKFLOW_TOOLS,
    "track": "Optional CLI --track create|reproduce records the caller's adopted track; it is not a plot-spec key or a chart classifier.",
    "optional_fields": {chart: sorted(fields) for chart, fields in OPTIONAL_FIELDS.items()},
    "figure_profile": {"profile": "path/to/figure-profile.json", "panel": "named panel", "continuous_scale": "optional named shared continuous scale", "size_scale": "optional named shared area scale for dotplot or scatter with fields.size"},
    "layout": {"width_mm": 88, "height_mm": 88, "font": "Arial", "font_size_pt": 8, "line_width_pt": .6, "dpi": 300, "auto_fit": False, "margins": {"left": .19, "right": .77, "bottom": .23, "top": .88}},
    "typography": {"axis": 8, "tick": 8, "legend": 8, "annotation": 8, "title": 9, "panel": 9},
    "line_roles": {"data": {"line_width_pt": .85}, "summary": {"line_width_pt": .75}, "reference": {"line_width_pt": .45, "color": "#747474", "linestyle": "--"}, "axis": {"line_width_pt": .55, "color": "#222222"}, "grid": {"line_width_pt": .3, "color": "#E8E8E8", "linestyle": "-"}},
    "formats": ["pdf", "svg", "png", "tiff"], "seed": 0,
    "colors": {"category label": "#0072B2"}, "palette": "somerville-bright",
    "colormap": "somerville-sky, another registered preset/Matplotlib colormap, or hex colors",
    "order": {"x": [], "y": [], "group": [], "sample": [], "category": []},
    "labels": {"x": "", "y": "", "color": "", "size": "", "title": "", "panel": ""},
    "legends": {"categorical": {"position": "auto", "key_width_mm": 1.5, "key_height_mm": 1.5, "handletext_gap_mm": .7, "row_gap_mm": .6, "column_gap_mm": 2}, "size": {"position": "auto"}, "colorbar": {"position": "auto", "thickness_mm": 2}},
    "legend_semantics": ["Size marker areas are immutable; key dimensions/markerscale are not accepted for size legends.", "Colorbar default length is 18-28 mm, guided by plot side; labels/range are measured.", "Manual categorical/size settings: position=manual, anchor_mm=[x,y], loc, ncol. Manual colorbar settings: position=manual, rect_mm=[x,y,w,h], orientation. Coordinates start at canvas lower left."],
    "shared_options": sorted(SHARED_OPTIONS),
    "chart_options": {k: sorted(v) for k, v in CHART_OPTIONS.items()},
    "scatter_reference_lines": {"x": [-1, 1], "y": [1.3]},
    "observation_style": {"point_style": "filled (legacy default) or hollow; hollow is limited to fixed scatter/distribution marks", "point_edge_width_pt": "Positive finite JSON number; requires hollow; default 0.45 pt", "alpha": "Explicit opacity is preserved; new unprofiled create drafts use 1", "meaning": "Hollow observations retain the same Matplotlib s and coordinates, have no face fill and use their group/point color for edges. Group legend keys match. Hollow and edge options are rejected with scatter fields.size because quantitative circle fill area must remain filled."},
    "distribution_box_style": {"box_style": "filled (legacy default) or outline; requires kind=box", "box_fill_alpha": "Optional finite JSON number in [0, 1], kind=box only; default 0.22. Filled boxes use the category color at this face opacity; outline boxes remain unfilled.", "meaning": "Summary face color is independent of the raw-point override and an explicitly adopted summary edge color. Outline boxes have no face fill."},
    "distribution_box_width": "Optional finite 0 < box_width <= 1, in category-center spacing units; legacy default 0.5. New drafts use 0.18; inspect the actual physical thickness after layout.",
    "distribution_violin_style": {"violin_fill_alpha": "Optional JSON number in [0, 1], controlling only the KDE face; explicit values keep the outline opaque. Omission preserves the legacy artist opacity.", "violin_inner": "none (legacy default)|box; requires kind=violin", "violin_inner_width": "Optional 0 < width <= 0.7 category-center units, requires violin_inner=box; default 0.12", "violin_inner_fill_alpha": "Optional finite JSON number in [0, 1], requires kind=violin and violin_inner=box; default 0 retains the hollow box. Positive values fill the raw-value IQR box with the category color, independently of point and contour colors.", "violin_median_visible": "Optional boolean, requires violin_inner=box; default true", "meaning": "The optional inner box spans raw-observation Q1 to Q3, with an optional median line and no whiskers. Its optional categorical fill does not encode a further statistic. These summaries are independent of the KDE's separately normalized width; neither width encodes sample count."},
    "distribution_color_roles": {"point_color": "Optional visible color string overriding every raw observation's group color; omitted keeps group-colored points. It affects filled faces or hollow edges only, retaining the adopted alpha, size, placement, values and summaries.", "meaning": "Category colors can identify summary areas while explicitly adopted neutral colors identify raw observations and contour strokes. This is an optional panel choice, not a new Create default."},
    "distribution_point_layout": {"point_layout": "jitter (default) or beeswarm", "point_max_offset_mm": 4, "point_gap_pt": .3, "meaning": "Beeswarm moves only the categorical coordinate after final layout; preserves values, rows, marker size and canvas. Unresolved mark overlaps fail QA and remain in exported data."},
    "distribution_layer_geometry": {"point_category_offset": "Optional finite JSON number in [-0.4, 0.4], default 0; shifts the raw layer in category-spacing units, not measurement units. Positive is right for vertical plots; orientation/reversed axes determine physical direction. Packing spread is measured around the shifted anchor; point envelopes must stay in the original category lane.", "violin_width": "Optional finite 0 < width <= 1, default 0.7; changes categorical silhouette width only. Scott bandwidth, numeric evaluation values and density normalization are unchanged."},
    "heatmap_cell_geometry": {"cell_border_width_pt": "Optional finite nonnegative JSON number, default 0; draws editable vector internal seams exactly at half-integer cell boundaries.", "cell_border_color": "Optional valid color string, default white.", "column_labels": "Optional complete mapping from actual column keys to distinct nonempty display strings. Source keys, order and numeric values stay unchanged; define abbreviations in the caption."},
    "statistics": {"method": "none; pearson|spearman (scatter); welch|mannwhitney|wilcoxon (distribution)", "groups": ["A", "B"], "unit": "pairing ID column (mandatory for wilcoxon)", "annotate": False},
    "semantics": ["Margins are subplot bounds in 0..1, not padding widths.", "layout.auto_fit=true measures labels and guides within the unchanged canvas; do not combine it with margins or manual guide coordinates. It is a technical fit, not aesthetic certification.", "orders must include every category exactly once.", "dotplot and mapped scatter max_area_pt2 denote true circle geometric fill area, excluding stroke; area=size/size_max*max_area_pt2 and Matplotlib s=4/pi*area. Zero means zero area.", "Legacy point_area_pt2 for fixed scatter/distribution marks is the Matplotlib s parameter (squared diameter), not geometric circle fill area; settings record both quantities.", "Scatter size options require fields.size and cannot be combined with point_area_pt2.", "Scatter options.reference_lines draws supplied numeric positions only; it does not compute classes or significance.", "composition normalization is mandatory; sample_sum uses only supplied categories.", "denominator values repeat for all categories within a sample; incomplete composition remains below 1.", "No test is run unless requested; default distributions are descriptive boxplots and all observations.", "SVG preserves editable text and references the font; PDF embeds the selected font."]
}


def require(condition, message):
    if not condition:
        raise SpecError(message)


def read_source_csv(data_path):
    """Parse the exact captured UTF-8 bytes without index or header inference."""
    raw = Path(data_path).read_bytes()
    try:
        table = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise SpecError(f"Input must be a valid UTF-8 CSV: {exc}") from None
    require(len(table) > 1, "Input requires a header and nonempty records")
    header, rows = table[0], table[1:]
    require(header and all(name.strip() for name in header) and len(header) == len(set(header)),
            "CSV headers must be nonempty and unique before mapping fields")
    require(all(len(row) == len(header) and any(cell.strip() for cell in row) for row in rows),
            "CSV rows must be nonempty and exactly match header width; no index is inferred or row skipped")
    data = pd.DataFrame(rows, columns=header, dtype=object)
    data.attrs["source_csv_bytes"] = raw
    data.attrs["source_csv_sha256"] = hashlib.sha256(raw).hexdigest()
    return data


def source_continuity(bindings):
    """Check actual current bytes against digests captured when inputs were used."""
    issues = []
    for role, record in bindings.items():
        try:
            actual = hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest()
        except OSError:
            actual = None
        if actual != record["sha256"]:
            issues.append({"code": "source_changed_during_render", "role": role,
                           "path": record["path"], "captured_sha256": record["sha256"],
                           "current_sha256": actual})
    return {"status": "needs_revision" if issues else "pass", "issues": issues,
            "scope": "Current-file continuity against actually captured source/spec/profile bytes; not an aesthetic or independent scientific audit."}


def composition_normalization(data, fields, normalization, raw_numeric):
    """Use exact source decimals for sums, then finite plotted proportions."""
    values = [Decimal(value) for value in raw_numeric["value"]]
    denominators = [Decimal(value) for value in raw_numeric["denominator"]] if normalization == "denominator" else None
    fractions = np.empty(len(data), dtype=float)
    totals_out, total_text = [None] * len(data), [None] * len(data)
    for sample, indices in data.groupby(fields["sample"], sort=False).groups.items():
        indices = list(indices)
        supplied = [values[index] for index in indices]
        participating = supplied + ([denominators[index] for index in indices] if denominators else [])
        # Enough precision for the exact decimal sum, including unequal
        # exponents and a carry from the entire group; no fixed-width integer
        # arithmetic or float-infinity total is used.
        nonzero = [value for value in participating if value]
        precision = max((value.adjusted() for value in nonzero), default=0) - min((value.as_tuple().exponent for value in nonzero), default=0) + len(str(len(indices))) + 2
        with localcontext() as context:
            context.prec = max(28, precision)
            # Literal zero may carry an arbitrary exponent (0e-1000000000);
            # it contributes no significant digits or value to this sum.
            total = sum((value for value in supplied if value), Decimal(0))
            require(total > 0 or normalization == "denominator", "Every sample sum must be positive")
            if denominators is not None:
                selected = {denominators[index] for index in indices}
                require(len(selected) == 1, "Each sample must have one consistent denominator")
                denominator = selected.pop()
                require(denominator > 0, "Denominators must be positive")
                require(total <= denominator + max(Decimal(1), denominator) * Decimal("1e-12"),
                        "Category sum exceeds the supplied sample denominator")
            else:
                denominator = total
            for index in indices:
                proportion = float(values[index] / denominator)
                require(math.isfinite(proportion) and 0 <= proportion <= 1 + 1e-12,
                        "Composition fractions must remain finite and within the declared denominator")
                require(not values[index] or proportion > 0,
                        "A positive composition fraction is below floating-point representability; provide an explicit alternative scale")
                fractions[index] = proportion
                total_text[index] = str(denominator)
                numeric = float(denominator)
                # A finite source can have a sum above binary64 capacity.
                # Preserve its exact decimal total as text instead of infinity.
                totals_out[index] = numeric if math.isfinite(numeric) else str(denominator)
            if normalization == "sample_sum":
                require(math.isclose(math.fsum(fractions[index] for index in indices), 1., rel_tol=1e-12, abs_tol=1e-12),
                        "Sample-sum proportions must sum to one")
    data["_easyviz_denominator"] = totals_out
    data["_easyviz_denominator_text"] = total_text
    data["_easyviz_plotted_value"] = fractions


def require_core_chart(chart):
    """Reject a recipe at the core boundary with an actionable entry point."""
    if isinstance(chart, str) and chart in FOCUSED_RECIPES:
        script = FOCUSED_RECIPES[chart]["script"]
        raise SpecError(f"chart '{chart}' uses the focused recipe {script}; inspect it with --describe-spec. "
                        f"The core renderer and draft helper support only {list(REQUIRED)}.")
    require(isinstance(chart, str) and chart in REQUIRED, f"chart must be one of {list(REQUIRED)}")


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def number(value, name, minimum=0, strict=True):
    require(not isinstance(value, bool), f"{name} must be a finite number")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise SpecError(f"{name} must be a finite number") from None
    require(math.isfinite(result), f"{name} must be finite")
    require(result > minimum if strict else result >= minimum, f"{name} must be {'>' if strict else '>='} {minimum}")
    return result


def validate_spec(spec):
    if isinstance(spec, dict) and isinstance(spec.get("chart"), str) and spec["chart"] in FOCUSED_RECIPES:
        require_core_chart(spec["chart"])
    try:
        figure_profile.validate_spec(spec, REQUIRED, OPTIONAL_FIELDS, CHART_OPTIONS, SHARED_OPTIONS)
    except figure_profile.ConfigurationError as exc:
        raise SpecError(str(exc)) from None
    if spec.get("chart") in ("scatter", "distribution"):
        options = spec.get("options", {})
        style = options.get("point_style", "filled")
        require(isinstance(style, str) and style in ("filled", "hollow"), "options.point_style must be filled or hollow")
        if spec["chart"] == "scatter" and "size" in spec["fields"]:
            require(style != "hollow" and "point_edge_width_pt" not in options,
                    "Scatter fields.size encodes circle fill area; hollow points and point_edge_width_pt are unsupported")
        if "point_edge_width_pt" in options:
            require(style == "hollow", "options.point_edge_width_pt requires point_style='hollow'")
            width = options["point_edge_width_pt"]
            require(isinstance(width, (int, float)) and not isinstance(width, bool),
                    "options.point_edge_width_pt must be a positive finite JSON number")
            number(width, "options.point_edge_width_pt")
    if spec.get("chart") == "distribution":
        options = spec.get("options", {})
        if "point_color" in options:
            color = options["point_color"]
            require(isinstance(color, str) and mcolors.is_color_like(color) and mcolors.to_rgba(color)[3] > 0,
                    "options.point_color must be a visible color string")
        if "box_fill_alpha" in options:
            require(options.get("kind", "box") == "box", "options.box_fill_alpha requires kind='box'")
            alpha = options["box_fill_alpha"]
            require(isinstance(alpha, (int, float)) and not isinstance(alpha, bool) and math.isfinite(alpha) and 0 <= alpha <= 1,
                    "options.box_fill_alpha must be a finite JSON number in [0, 1]")
        if "box_width" in options:
            require(options.get("kind", "box") == "box", "options.box_width requires kind='box'")
            width = options["box_width"]
            require(isinstance(width, (int, float)) and not isinstance(width, bool), "options.box_width must be a finite JSON number in (0, 1]")
            number(width, "options.box_width")
            require(width <= 1, "options.box_width must be in (0, 1]")
        if "box_style" in options:
            require(isinstance(options["box_style"], str) and options["box_style"] in ("filled", "outline"),
                    "options.box_style must be filled or outline")
            require(options.get("kind", "box") == "box", "options.box_style requires kind='box'")
        violin_options = {"violin_width", "violin_fill_alpha", "violin_inner", "violin_inner_width", "violin_inner_fill_alpha", "violin_median_visible"} & set(options)
        if violin_options:
            require(options.get("kind", "box") == "violin", "violin styling options require kind='violin'")
        if "violin_width" in options:
            width = options["violin_width"]
            require(isinstance(width, (int, float)) and not isinstance(width, bool), "options.violin_width must be a finite JSON number in (0, 1]")
            number(width, "options.violin_width")
            require(width <= 1, "options.violin_width must be in (0, 1]")
        if "point_category_offset" in options:
            offset = options["point_category_offset"]
            require(isinstance(offset, (int, float)) and not isinstance(offset, bool) and math.isfinite(offset) and -.4 <= offset <= .4,
                    "options.point_category_offset must be a finite JSON number in [-0.4, 0.4]")
        if "violin_fill_alpha" in options:
            alpha = options["violin_fill_alpha"]
            require(isinstance(alpha, (int, float)) and not isinstance(alpha, bool) and math.isfinite(alpha) and 0 <= alpha <= 1,
                    "options.violin_fill_alpha must be a finite JSON number in [0, 1]")
        if "violin_inner" in options:
            require(isinstance(options["violin_inner"], str) and options["violin_inner"] in ("none", "box"),
                    "options.violin_inner must be none or box")
        if "violin_inner_width" in options:
            require(options.get("violin_inner", "none") == "box", "options.violin_inner_width requires violin_inner='box'")
            width = options["violin_inner_width"]
            require(isinstance(width, (int, float)) and not isinstance(width, bool), "options.violin_inner_width must be a finite JSON number in (0, 0.7]")
            number(width, "options.violin_inner_width")
            require(width <= .7, "options.violin_inner_width must be in (0, 0.7]")
        if "violin_inner_fill_alpha" in options:
            require(options.get("violin_inner", "none") == "box", "options.violin_inner_fill_alpha requires violin_inner='box'")
            alpha = options["violin_inner_fill_alpha"]
            require(isinstance(alpha, (int, float)) and not isinstance(alpha, bool) and math.isfinite(alpha) and 0 <= alpha <= 1,
                    "options.violin_inner_fill_alpha must be a finite JSON number in [0, 1]")
        if "violin_median_visible" in options:
            require(options.get("violin_inner", "none") == "box", "options.violin_median_visible requires violin_inner='box'")
            require(isinstance(options["violin_median_visible"], bool), "options.violin_median_visible must be a boolean")
        policy = options.get("point_layout", "jitter")
        require(isinstance(policy, str) and policy in ("jitter", "beeswarm"), "options.point_layout must be jitter or beeswarm")
        require(policy == "beeswarm" or not ({"point_max_offset_mm", "point_gap_pt"} & set(options)), "point_max_offset_mm and point_gap_pt require point_layout='beeswarm'")
        if policy == "beeswarm":
            number(options.get("point_area_pt2", 9), "options.point_area_pt2")
            for key in ("point_max_offset_mm", "point_gap_pt"):
                if key in options:
                    require(isinstance(options[key], (int, float)) and not isinstance(options[key], bool), f"options.{key} must be a numeric JSON value")
            number(options.get("point_max_offset_mm", 4), "options.point_max_offset_mm")
            number(options.get("point_gap_pt", .3), "options.point_gap_pt", strict=False)
    if spec.get("chart") == "heatmap":
        options = spec.get("options", {})
        if "cell_border_width_pt" in options:
            width = options["cell_border_width_pt"]
            require(isinstance(width, (int, float)) and not isinstance(width, bool), "options.cell_border_width_pt must be a finite nonnegative JSON number")
            number(width, "options.cell_border_width_pt", strict=False)
        if "cell_border_color" in options:
            color = options["cell_border_color"]
            require(isinstance(color, str) and mcolors.is_color_like(color), "options.cell_border_color must be a valid color string")
        if "column_labels" in options:
            mapping = options["column_labels"]
            require(isinstance(mapping, dict) and bool(mapping), "options.column_labels must be a nonempty category-to-label object")
            require(all(isinstance(key, str) and isinstance(label, str) and bool(label.strip()) for key, label in mapping.items()),
                    "options.column_labels must map string categories to nonempty display strings")
            require(len(set(mapping.values())) == len(mapping), "options.column_labels display labels must remain distinct")


def resolve_spec(spec, *, profile=None, panel=None, spec_path=None):
    """Resolve one panel against a shared figure profile without changing inputs."""
    try:
        resolved, record = figure_profile.resolve(spec, profile_path=profile, panel=panel, spec_path=spec_path)
    except figure_profile.ConfigurationError as exc:
        raise SpecError(str(exc)) from None
    validate_spec(resolved)
    return resolved, record


def scatter_area_scale(values, options):
    """Resolve proportional scatter areas without changing supplied values."""
    require((values >= 0).all(), "Scatter sizes must be nonnegative")
    maximum = number(options.get("size_max", max(float(values.max()), 1)), "size_max")
    require(values.max() <= maximum, "Scatter values exceed size_max")
    max_area = number(options.get("max_area_pt2", 90), "max_area_pt2")
    levels = options.get("size_legend", [maximum * .25, maximum * .5, maximum])
    require(all(0 < float(v) <= maximum for v in levels), "size_legend values must be within 0..size_max")
    return maximum, max_area, levels


def circle_size_parameter(area_pt2):
    """Convert ideal circular fill area, excluding stroke, to Matplotlib s."""
    return area_pt2 / legend_layout.CIRCLE_AREA_PER_SIZE_PARAMETER


def mapped_circle_geometry(field, maximum, max_area):
    return {"mode": "mapped_circle_fill_area", "source_field": field, "size_max": maximum,
            "max_area_pt2": max_area, "max_marker_size_parameter_pt2": float(circle_size_parameter(max_area)),
            "fill_area_definition": "Ideal circle geometric fill area in pt², excluding stroke; the rendered circle uses a Bézier path approximation.",
            "area_formula": "circle_fill_area_pt2 = size / size_max * max_area_pt2",
            "parameter_formula": "matplotlib_s = 4 / pi * circle_fill_area_pt2",
            "diameter_formula": "diameter_pt = 2 * sqrt(circle_fill_area_pt2 / pi)",
            "stroke_policy": "Fill area excludes edge stroke; core quantitative circles are borderless."}


def fixed_circle_geometry(parameter, options=None):
    geometry = {"mode": "fixed_matplotlib_size_parameter", "marker_size_parameter_pt2": float(parameter),
            "circle_fill_area_pt2": float(parameter) * legend_layout.CIRCLE_AREA_PER_SIZE_PARAMETER,
            "fill_area_definition": "Ideal circle geometric fill area in pt², excluding stroke; the rendered circle uses a Bézier path approximation.",
            "diameter_pt": math.sqrt(float(parameter)),
            "parameter_source": "Legacy point_area_pt2 option or its fixed-mark default; no field-mapped size scale.",
            "stroke_policy": "Fill area excludes edge stroke; core observation circles have zero linewidth."}
    if (options or {}).get("point_style") == "hollow":
        width = float(options.get("point_edge_width_pt", .45))
        geometry.update(point_style="hollow", point_edge_width_pt=width,
                        circle_enclosed_area_pt2=geometry["circle_fill_area_pt2"], circle_fill_area_pt2=0.,
                        outer_diameter_pt=geometry["diameter_pt"] + width,
                        fill_area_definition="Hollow observations have no filled face; circle_enclosed_area_pt2 is the nominal centerline-enclosed area.",
                        stroke_policy="Group/point-colored edge stroke centered on the circle path; physical envelope includes its linewidth.")
    return geometry


def observation_style(options, color):
    """Explicit hollow styling; an omitted style keeps legacy artist options."""
    if options.get("point_style") == "hollow":
        return {"facecolors": "none", "edgecolors": color,
                "alpha": options.get("alpha", .85), "linewidths": options.get("point_edge_width_pt", .45)}
    return {"color": color, "alpha": options.get("alpha", .85), "linewidths": 0}


def pack_distribution_points(value_positions_pt, diameter_pt, max_offset_pt, *, gap_pt=.3, seed=0):
    """Pack equal circles along their categorical direction in physical points.

    Numeric coordinates are read-only. A greedy, value-sorted placement chooses
    the nearest unoccupied categorical location; the seed breaks symmetric and
    equal-value ties. If a bounded lane has no feasible center, a fixed 65-center
    grid chooses the least crowded location and records that unresolved row.
    This is a spacing heuristic, not a density estimator or a fit guarantee.
    """
    values = np.asarray(value_positions_pt, dtype=float)
    require(values.ndim == 1 and np.isfinite(values).all(), "Point value positions must be a finite one-dimensional array")
    diameter = number(diameter_pt, "circle diameter")
    maximum = number(max_offset_pt, "maximum point offset", strict=False)
    gap = number(gap_pt, "point gap", strict=False)
    require(isinstance(seed, int) and not isinstance(seed, bool) and seed >= 0, "Point packing seed must be a nonnegative integer")
    separation = diameter + gap
    rng = np.random.default_rng(seed)
    order = np.lexsort((rng.random(len(values)), values))
    offsets = np.zeros(len(values))
    # Identical display centers share a weighted entry. Dense tied groups can
    # then retain tens of thousands of rows without quadratic duplicate work.
    active, fallback = {}, []
    epsilon = max(1., separation) * 1e-10
    grid = np.linspace(-maximum, maximum, 65) if maximum else np.array([0.])
    for row in order:
        active = {center: count for center, count in active.items()
                  if values[row] - center[0] < separation - epsilon}
        if not active:
            offsets[row] = 0.
            active[(float(values[row]), 0.)] = 1
            continue
        previous = np.asarray(list(active))
        weights = np.asarray(list(active.values()), dtype=int)
        dy = values[row] - previous[:, 0]
        radii = np.sqrt(np.maximum(0., separation ** 2 - dy ** 2))
        intervals = sorted(zip(previous[:, 1] - radii, previous[:, 1] + radii))
        # Join overlapping open intervals. Exact touching endpoints remain a
        # feasible tangent center and must not be merged into a false blockage.
        merged = []
        for low, high in intervals:
            if merged and low < merged[-1][1] - epsilon:
                merged[-1][1] = max(merged[-1][1], float(high))
            else:
                merged.append([float(low), float(high)])
        candidates = [0.]
        candidates.extend(bound for interval in merged for bound in interval
                          if -maximum - epsilon <= bound <= maximum + epsilon)
        candidates.extend([-maximum, maximum])
        feasible = []
        for candidate in candidates:
            candidate = float(np.clip(candidate, -maximum, maximum))
            if all(not (low + epsilon < candidate < high - epsilon) for low, high in merged):
                feasible.append(candidate)
        prefer_positive = bool(rng.integers(2))
        if feasible:
            chosen = min(feasible, key=lambda offset: (round(abs(offset), 10), offset < 0 if prefer_positive else offset > 0))
        else:
            # Difference-array coverage avoids testing every old circle against
            # every fallback candidate when a large tied group cannot fit.
            left = np.searchsorted(grid, previous[:, 1] - radii + epsilon, side="right")
            right = np.searchsorted(grid, previous[:, 1] + radii - epsilon, side="left")
            counts = np.zeros(len(grid) + 1, dtype=int)
            np.add.at(counts, left, weights)
            np.add.at(counts, right, -weights)
            coverage = np.cumsum(counts[:-1])
            choices = np.flatnonzero(coverage == coverage.min())
            selected = min(choices, key=lambda index: (round(abs(float(grid[index])), 10), grid[index] < 0 if prefer_positive else grid[index] > 0))
            chosen = float(grid[selected])
            fallback.append(int(row))
        offsets[row] = chosen
        center = (float(values[row]), chosen)
        active[center] = active.get(center, 0) + 1
    return offsets, {"fallback_rows": [row + 1 for row in fallback],
                     "fallback_count": len(fallback), "seed": seed,
                     "max_offset_pt": maximum, "minimum_requested_center_distance_pt": separation}


def distribution_collision_report(coordinates_pt, diameter_pt, gap_pt):
    """Audit every pair of equal circles, including compressed duplicate centers.

    Exact duplicate centers are counted with multiplicity without allocating
    their full pair list. Nearby distinct centers use a spatial tree. Pair
    samples are one-based parsed observation positions, excluding the header.
    """
    from scipy.spatial import cKDTree
    coordinates = np.asarray(coordinates_pt, dtype=float)
    require(coordinates.ndim == 2 and coordinates.shape[1] == 2 and np.isfinite(coordinates).all(), "Circle coordinates must be a finite n-by-2 array")
    diameter_pt = number(diameter_pt, "circle diameter")
    gap_pt = number(gap_pt, "point gap", strict=False)
    unique, first, multiplicity = np.unique(coordinates, axis=0, return_index=True, return_counts=True)
    spacing = float(diameter_pt + gap_pt)
    tolerance = max(1., spacing) * 1e-8
    overlaps = int(sum(int(count) * (int(count) - 1) // 2 for count in multiplicity))
    spacing_violations = overlaps
    examples = []
    for index, count in enumerate(multiplicity):
        if count > 1 and len(examples) < 20:
            rows = np.flatnonzero(np.all(coordinates == unique[index], axis=1))[:2] + 1
            examples.append({"rows": [int(row) for row in rows], "center_distance_pt": 0.})
    minimum = 0. if overlaps else None
    if len(unique) > 1:
        tree = cKDTree(unique)
        nearest, _ = tree.query(unique, k=2)
        nearest_distance = float(nearest[:, 1].min())
        minimum = min(minimum, nearest_distance) if minimum is not None else nearest_distance
        for a, b in tree.query_pairs(spacing, output_type="ndarray"):
            distance = float(np.linalg.norm(unique[a] - unique[b]))
            pairs = int(multiplicity[a]) * int(multiplicity[b])
            if distance < spacing - tolerance:
                spacing_violations += pairs
            if distance < diameter_pt - tolerance:
                overlaps += pairs
                if len(examples) < 20:
                    examples.append({"rows": [int(first[a]) + 1, int(first[b]) + 1],
                                     "center_distance_pt": distance})
    return {"status": "pass" if spacing_violations == 0 else "needs_revision",
            "overlapping_circle_pairs": overlaps, "spacing_violation_pairs": spacing_violations,
            "minimum_center_distance_pt": minimum, "sample_overlapping_pairs": examples,
            "pair_sample_definition": "One-based parsed observation positions excluding the header; no observations are dropped."}


def place_distribution_points(fig, ax, data, spec, pending):
    """Resolve beeswarm positions only after scales and final axes geometry."""
    options, fields = spec.get("options", {}), spec["fields"]
    orientation = options.get("orientation", "vertical")
    category_axis = 0 if orientation == "vertical" else 1
    numeric_axis = 1 - category_axis
    marker_diameter = math.sqrt(float(options.get("point_area_pt2", 9)))
    edge_width = float(options.get("point_edge_width_pt", .45)) if options.get("point_style") == "hollow" else 0.
    diameter = marker_diameter + edge_width
    gap = float(options.get("point_gap_pt", .3))
    maximum = float(options.get("point_max_offset_mm", 4)) / 25.4 * 72
    anchor_offset = float(options.get("point_category_offset", 0))
    fig.canvas.draw()
    px_to_pt = 72 / fig.dpi
    plot = ax.get_window_extent()
    edges = ([plot.x0, plot.x1] if category_axis == 0 else [plot.y0, plot.y1])
    low, high = sorted(edge * px_to_pt for edge in edges)
    coordinates = np.zeros((len(data), 2))
    reports = []
    boundary_rows = []
    for center, group, sample, rows, artist in pending:
        base = np.column_stack((np.full(len(sample), center), sample)) if category_axis == 0 else np.column_stack((sample, np.full(len(sample), center)))
        physical = ax.transData.transform(base) * px_to_pt
        category_center = float(physical[0, category_axis])
        unit = base[0].copy()
        unit[category_axis] += 1.
        category_step = float(ax.transData.transform(unit)[category_axis] * px_to_pt - category_center)
        # Keep circle edges inside both the axes and a separate 90%-wide lane
        # for each category. Quantitative values and circle areas stay fixed.
        lane_low = max(low, category_center - .45 * abs(category_step))
        lane_high = min(high, category_center + .45 * abs(category_step))
        anchor = category_center + anchor_offset * category_step
        room = min(anchor - lane_low - diameter / 2,
                   lane_high - anchor - diameter / 2)
        allowed = max(0., min(maximum, room))
        stable_group_seed = int.from_bytes(hashlib.sha256(str(group).encode()).digest()[:4], "big")
        offsets, packed = pack_distribution_points(physical[:, numeric_axis], diameter, allowed,
                                                   gap_pt=gap, seed=(spec.get("seed", 0) + stable_group_seed))
        positions = center + anchor_offset + offsets / category_step
        updated = base.copy()
        updated[:, category_axis] = positions
        artist.set_offsets(updated)
        data.loc[rows, "_easyviz_jitter_position"] = positions
        data.loc[rows, "_easyviz_point_offset_pt"] = offsets + anchor_offset * category_step
        rendered = ax.transData.transform(updated) * px_to_pt
        coordinates[rows] = rendered
        clipped = np.flatnonzero((rendered[:, category_axis] - diameter / 2 < lane_low - 1e-8) |
                                 (rendered[:, category_axis] + diameter / 2 > lane_high + 1e-8))
        boundary_rows.extend(int(rows[index]) + 1 for index in clipped)
        reports.append({"group": group, "rows": len(rows), "category_spacing_pt": abs(category_step),
                        "available_max_offset_mm": allowed / 72 * 25.4,
                        "actual_max_offset_mm": float(np.abs(offsets).max()) / 72 * 25.4,
                        "category_anchor_offset": anchor_offset,
                        "actual_total_offset_mm": float(np.abs(offsets + anchor_offset * category_step).max()) / 72 * 25.4,
                        "fallback_source_rows": [int(rows[index - 1]) + 1 for index in packed["fallback_rows"]],
                        "fallback_count": packed["fallback_count"], "packing_seed": packed["seed"]})
    report = distribution_collision_report(coordinates, diameter, gap)
    report.update(policy="beeswarm", orientation=orientation, seed=spec.get("seed", 0),
                  categorical_axis="x" if category_axis == 0 else "y",
                  quantitative_axis="y" if category_axis == 0 else "x",
                  numeric_values_changed=False, input_rows=len(data), placed_rows=len(data),
                  diameter_pt=diameter, gap_pt=gap,
                  requested_max_offset_mm=float(options.get("point_max_offset_mm", 4)),
                  point_category_offset=anchor_offset,
                  packing_origin="Category center plus point_category_offset; maximum spread is measured around that anchor.",
                  categorical_boundary_rows=boundary_rows, groups=reports,
                  algorithm="Greedy nearest-center circle packing in final physical geometry; bounded least-crowded fallback grid when infeasible.",
                  note="Only categorical coordinates move. This arrangement is not a KDE/density estimate. Circle-circle spacing is audited; point-summary and text overlaps still need visual review. Explicitly enlarge the allowed lane/canvas or choose another reading task if circles cannot fit.")
    if edge_width:
        report.update(marker_diameter_pt=marker_diameter, point_edge_width_pt=edge_width,
                      diameter_definition="Outer circle envelope: sqrt(Matplotlib s) + edge linewidth in physical points.")
    if boundary_rows:
        report["status"] = "needs_revision"
    fig._easyviz_point_layout = report


def prepare(data_path, spec):
    validate_spec(spec)
    chart = spec.get("chart")
    require(chart in REQUIRED, f"chart must be one of {list(REQUIRED)}")
    options = spec.get("options", {})
    require(isinstance(options, dict), "options must be an object")
    require(not (set(options) - SHARED_OPTIONS - CHART_OPTIONS[chart]), f"Unknown {chart} options: {sorted(set(options) - SHARED_OPTIONS - CHART_OPTIONS[chart])}")
    require(isinstance(spec.get("seed", 0), int) and spec.get("seed", 0) >= 0, "seed must be a nonnegative integer")
    fields = spec.get("fields", {})
    require(isinstance(fields, dict), "fields must be an object")
    require(all(k in fields for k in REQUIRED[chart]), f"{chart} requires fields {REQUIRED[chart]}")
    # Preserve literal category names such as "NA" and "null". Empty fields are
    # rejected explicitly below; numeric non-finite tokens still fail validation.
    data = read_source_csv(data_path)
    require(len(data) > 0, "Input has no observations")
    require(not any(c.startswith("_easyviz_") for c in data.columns), "Input columns starting _easyviz_ are reserved")
    observed = pd.Series(True, index=data.index)
    if chart == "dotplot":
        if "state" in fields:
            require(fields["state"] in data.columns, f"Missing input column for state: {fields['state']}")
            states = data[fields["state"]]
            require(states.isin(["observed", "unmeasured"]).all(), "Dot state must be observed or unmeasured; do not infer it from a blank numeric value")
            observed = states.eq("observed")
        data["_easyviz_state"] = np.where(observed, "observed", "unmeasured")
    for role, column in fields.items():
        require(isinstance(column, str) and column in data.columns, f"Missing input column for {role}: {column}")
        values = data.loc[observed, column] if chart == "dotplot" and role in ("size", "color") else data[column]
        require(not values.isna().any(), f"Missing values in {column}; supply an explicit cleaned input")
        require(not values.astype(str).str.strip().eq("").any(), f"Empty values in {column}")
        if chart == "dotplot" and role in ("size", "color"):
            require(data.loc[~observed, column].eq("").all(), f"Unmeasured dots require empty {column}; zero is an observed value")
    numerical = {
        "heatmap": ["value"], "composition": ["value", "denominator"],
        "dotplot": ["size", "color"], "scatter": ["x", "y", "size"], "distribution": ["value"],
    }[chart]
    raw_numeric = {}
    for role in numerical:
        if role not in fields:
            continue
        col = fields[role]
        selected = data.loc[observed, col] if chart == "dotplot" else data[col]
        raw_numeric[role] = selected.astype(str).tolist()
        try:
            converted = pd.to_numeric(selected, errors="raise")
        except (ValueError, TypeError):
            raise SpecError(f"{col} must contain only numeric values") from None
        require(np.isfinite(converted.to_numpy(dtype=float)).all(), f"Non-finite values in {col}")
        require(all(float(value) != 0 or Decimal(text) == 0 for value, text in zip(converted, raw_numeric[role])),
                f"A nonzero value in {col} is below floating-point representability; no source value is silently replaced by zero")
        if chart == "dotplot":
            data[col] = pd.Series(np.nan, index=data.index, dtype=float)
            data.loc[observed, col] = converted.to_numpy(dtype=float)
        else:
            data[col] = converted
    if chart in ("heatmap", "dotplot", "composition"):
        pair = {"heatmap": ("row", "column"), "dotplot": ("x", "y"), "composition": ("sample", "category")}[chart]
        require(not data.duplicated([fields[p] for p in pair]).any(), f"Duplicate {pair} cells; aggregate explicitly before rendering")
    if chart == "heatmap":
        require(len(data) == data[fields["row"]].nunique() * data[fields["column"]].nunique(), "Heatmap matrix is incomplete; missing cells are not silently imputed")
    if chart == "dotplot":
        require((data.loc[observed, fields["size"]] >= 0).all(), "Dot sizes must be nonnegative")
        require(options.get("missing_cells", "unsupplied") in ("unsupplied", "unmeasured", "error"), "missing_cells must be unsupplied, unmeasured or error")
        require(isinstance(options.get("state_markers", True), bool), "state_markers must be a boolean")
        number(options.get("small_positive_area_pt2", 0), "small_positive_area_pt2", strict=False)
    if chart == "scatter" and "size" in fields:
        scatter_area_scale(data[fields["size"]], options)
    if chart == "composition":
        require((data[fields["value"]] >= 0).all(), "Composition values must be nonnegative")
        normalization = spec.get("options", {}).get("normalization")
        require(normalization in ("none", "sample_sum", "denominator"), "Composition requires options.normalization: none, sample_sum, or denominator")
        values = data[fields["value"]].astype(float)
        if normalization == "none":
            data["_easyviz_plotted_value"] = values
        else:
            require(normalization != "denominator" or "denominator" in fields, "Denominator normalization requires fields.denominator")
            composition_normalization(data, fields, normalization, raw_numeric)
    return data


def ordered(data, column, spec, role):
    observed = list(dict.fromkeys(data[column].astype(str)))
    requested = spec.get("order", {}).get(role, observed)
    require(isinstance(requested, list), f"order.{role} must be a list")
    requested = [str(v) for v in requested]
    require(len(requested) == len(set(requested)) and set(requested) == set(observed), f"order.{role} must list every observed category exactly once")
    return requested


def palette_colors(spec, categories):
    mapping = spec.get("colors")
    if mapping is not None:
        require(isinstance(mapping, dict), "colors must map category labels to colors")
        require(all(c in mapping for c in categories), "colors must cover every category; colors are never cycled")
        result = {c: mapping[c] for c in categories}
    else:
        palette = DEFAULT_COLORS
        name = spec.get("palette", "somerville-bright")
        if name:
            palette_path = Path(__file__).resolve().parents[1] / "assets" / "palettes" / "palettes.json"
            catalog = json.loads(palette_path.read_text())
            # Accept a plain name->record mapping or a {palettes: [...]} catalog.
            records = catalog.get("palettes", catalog)
            if isinstance(records, list):
                records = {r["name"]: r for r in records}
            require(name in records, f"Unknown palette: {name}")
            record = records[name]
            require(record.get("type") == "categorical", "Category colors require a categorical palette")
            palette = record["colors"]
        require(len(categories) <= len(palette), f"{len(categories)} categories exceed palette capacity {len(palette)}; provide an explicit larger mapping")
        result = dict(zip(categories, palette))
    require(all(mcolors.is_color_like(c) for c in result.values()), "Invalid category color")
    require(len(set(mcolors.to_hex(c) for c in result.values())) == len(result), "Distinct categories must have distinct colors")
    return result


def continuous(spec, values):
    name = spec.get("colormap", "somerville-sky")
    if isinstance(name, str) and name not in matplotlib.colormaps:
        catalog_path = Path(__file__).resolve().parents[1] / "assets" / "palettes" / "palettes.json"
        catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
        records = catalog.get("palettes", catalog)
        if isinstance(records, list):
            records = {r["name"]: r for r in records}
        require(name in records, f"Unknown colormap: {name}")
        record = records[name]
        require(record.get("type") in ("sequential", "diverging"), "Continuous color requires a sequential or diverging palette")
        name = record.get("colormap", record.get("colors"))
    if isinstance(name, list):
        require(len(name) >= 2 and all(mcolors.is_color_like(c) for c in name), "colormap list needs at least two colors")
        cmap = mcolors.LinearSegmentedColormap.from_list("easyviz", name)
    else:
        require(name in matplotlib.colormaps, f"Unknown colormap: {name}")
        cmap = matplotlib.colormaps[name]
    limits = spec.get("options", {}).get("color_limits", [float(min(values)), float(max(values))])
    require(len(limits) == 2 and np.isfinite(limits).all() and limits[0] <= limits[1], "color_limits must be two finite ascending numbers")
    require(min(values) >= limits[0] and max(values) <= limits[1], "color_limits would clip source values")
    low, high = limits
    if low == high:
        low, high = low - .5, high + .5
    center = spec.get("options", {}).get("color_center")
    if center is None:
        norm = mcolors.Normalize(low, high)
    else:
        require(low < center < high, "color_center must lie strictly within color_limits")
        norm = mcolors.TwoSlopeNorm(vcenter=center, vmin=low, vmax=high)
    return cmap, norm


def statistics(data, spec):
    config = spec.get("statistics")
    if not config:
        return {"method": "none", "note": "Descriptive visualization; no inferential test requested."}
    require(isinstance(config, dict), "statistics must be an object")
    require(not (set(config) - {"method", "groups", "unit", "annotate"}), "Unknown statistics options; supported: method, groups, unit, annotate")
    if config.get("method") == "none":
        require("groups" not in config and "unit" not in config and not config.get("annotate", False), "statistics.method='none' cannot be combined with groups, unit, or annotate=true")
        return {"method": "none", "note": "Descriptive visualization; no inferential test requested."}
    from scipy import stats
    chart, f = spec["chart"], spec["fields"]
    if "unit" in config and "unit" in f:
        require(config["unit"] == f["unit"], "statistics.unit and fields.unit must name the same independent unit column")
    unit = config.get("unit", f.get("unit"))
    if "unit" in config or "unit" in f:
        require(isinstance(unit, str) and bool(unit.strip()), "Statistical unit must name a nonempty input column")
        require(unit in data.columns and not data[unit].isna().any(), "Missing statistical unit IDs")
        require(not data[unit].astype(str).str.strip().eq("").any(), "Empty statistical unit IDs")
    method = config.get("method")
    result = {"method": method, "alternative": "two-sided"}
    if chart == "scatter":
        require(method in ("pearson", "spearman"), "Scatter statistics supports pearson or spearman")
        x, y = data[f["x"]].to_numpy(float), data[f["y"]].to_numpy(float)
        require(len(x) >= 3 and np.ptp(x) > 0 and np.ptp(y) > 0, "Correlation requires at least 3 observations and nonconstant x and y")
        if unit is not None:
            require(not data[unit].duplicated().any(), "Correlation requires one observation per supplied independent unit")
        test = getattr(stats, "pearsonr" if method == "pearson" else "spearmanr")(x, y)
        result.update(n=len(x), statistic=float(test.statistic), pvalue=float(test.pvalue))
    elif chart == "distribution":
        require(method in ("welch", "mannwhitney", "wilcoxon"), "Distribution statistics supports welch, mannwhitney, or paired wilcoxon")
        groups = config.get("groups")
        require(isinstance(groups, list) and len(groups) == 2 and groups[0] != groups[1], "Statistics requires two distinct groups")
        selected = [data[data[f["group"]].astype(str) == str(g)] for g in groups]
        require(all(len(v) >= 2 for v in selected), "Each tested group needs at least 2 observations")
        if unit is not None:
            require(all(not d[unit].duplicated().any() for d in selected), "Repeated observations within a group need explicit aggregation or a repeated-measures model")
        if method == "wilcoxon":
            require(unit is not None, "Paired Wilcoxon requires an explicit pairing unit column")
            require(set(selected[0][unit]) == set(selected[1][unit]), "Paired groups must have exactly matching unit IDs")
            aligned = selected[1].set_index(unit).loc[selected[0][unit], f["value"]]
            a, b = selected[0][f["value"]].to_numpy(float), aligned.to_numpy(float)
            require(np.any(a != b), "All paired differences are zero; Wilcoxon is undefined")
            test = stats.wilcoxon(a, b, alternative="two-sided", zero_method="wilcox", method="auto")
            result["pairing_unit"] = unit
            result["pair_order"] = selected[0][unit].astype(str).tolist()
        else:
            if unit:
                require(set(selected[0][unit]).isdisjoint(set(selected[1][unit])), "Independent-group tests cannot reuse unit IDs across groups; choose a paired test")
            a, b = [d[f["value"]].to_numpy(float) for d in selected]
            if method == "welch":
                require(np.var(a) > 0 or np.var(b) > 0, "Welch test is undefined when both groups are constant")
                test = stats.ttest_ind(a, b, equal_var=False, alternative="two-sided")
            else:
                test = stats.mannwhitneyu(a, b, alternative="two-sided", method="auto")
        result.update(groups=groups, n=[len(a), len(b)], statistic=float(test.statistic), pvalue=float(test.pvalue))
    else:
        raise SpecError("Inferential statistics is only available for scatter and distribution")
    require(math.isfinite(result["statistic"]) and math.isfinite(result["pvalue"]), "Requested test is undefined for these data")
    if result["pvalue"] == 0:
        result["pvalue_display"] = {"text": "p < 0.001", "upper_bound": .001, "raw_library_value_preserved": 0.0, "note": "The numerical library returned zero, potentially from floating-point underflow or a limiting exact correlation. Display a bound rather than claiming an empirically exact zero probability."}
    result["multiplicity"] = "One specified test; no multiple-testing correction."
    return result


def setup(spec):
    try:
        figure_profile.validate_layout(spec.get("layout", {}))
        figure_profile.validate_typography(spec.get("typography", {}))
        figure_profile.validate_line_roles(spec.get("line_roles", {}))
    except figure_profile.ConfigurationError as exc:
        raise SpecError(str(exc)) from None
    layout = {"width_mm": 88, "height_mm": 88, "font": "Arial", "font_size_pt": 8, "line_width_pt": .6, "dpi": 300}
    layout.update(spec.get("layout", {}))
    for key in ("width_mm", "height_mm", "font_size_pt", "line_width_pt", "dpi"):
        layout[key] = number(layout[key], key)
    require(float(layout["dpi"]).is_integer(), "dpi must be an integer")
    layout["dpi"] = int(layout["dpi"])
    font_path = font_manager.findfont(font_manager.FontProperties(family=layout["font"]), fallback_to_default=True)
    actual_font = font_manager.FontProperties(fname=font_path).get_name()
    typography = dict.fromkeys(("axis", "tick", "legend", "annotation"), layout["font_size_pt"])
    typography.update(title=9, panel=9)
    typography.update(spec.get("typography", {}))
    typography = {k: number(v, f"typography.{k}") for k, v in typography.items()}
    rc = {"font.family": actual_font, "font.size": layout["font_size_pt"], "axes.labelsize": typography["axis"], "axes.titlesize": typography["title"], "xtick.labelsize": typography["tick"], "ytick.labelsize": typography["tick"], "legend.fontsize": typography["legend"], "axes.linewidth": layout["line_width_pt"], "lines.linewidth": layout["line_width_pt"], "xtick.major.width": layout["line_width_pt"], "ytick.major.width": layout["line_width_pt"], "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "easyviz", "savefig.bbox": None}
    margins = {"left": .19, "right": .77, "bottom": .23, "top": .88}
    margins.update(layout.get("margins", {}))
    require(all(isinstance(v, (float, int)) and math.isfinite(v) for v in margins.values()), "Margins must be finite numbers")
    require(0 < margins["left"] < margins["right"] < 1 and 0 < margins["bottom"] < margins["top"] < 1, "Margins must define a positive plotting region within 0..1")
    layout["margins"] = margins
    layout["actual_font"] = actual_font
    layout["font_substituted"] = actual_font.casefold() != str(layout["font"]).casefold()
    return layout, typography, rc


def line_style(spec, role, *, linewidth, color=None, linestyle=None):
    """Resolve only declared stroke properties, retaining each legacy fallback."""
    overrides = spec.get("line_roles", {}).get(role, {})
    properties = {"linewidth": overrides.get("line_width_pt", linewidth)}
    if "linestyle" in overrides or linestyle is not None:
        properties["linestyle"] = overrides.get("linestyle", linestyle)
    if "color" in overrides or color is not None:
        properties["color"] = overrides.get("color", color)
    return properties


def line_width_path(spec, role):
    return (figure_elements.pointer("line_roles", role, "line_width_pt")
            if "line_width_pt" in spec.get("line_roles", {}).get(role, {})
            else "/layout/line_width_pt")


def draw(data, spec, layout, typography, result):
    chart, f, options, labels = spec["chart"], spec["fields"], spec.get("options", {}), spec.get("labels", {})
    fig, ax = plt.subplots(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    fig.subplots_adjust(**layout["margins"])
    legend_manager = legend_layout.LegendLayout(fig, ax, typography, spec.get("legends"))
    ax.set_axisbelow(True)
    axis_style = spec.get("line_roles", {}).get("axis", {})
    if axis_style:
        for spine in ax.spines.values():
            if "line_width_pt" in axis_style:
                spine.set_linewidth(axis_style["line_width_pt"])
            if "color" in axis_style:
                spine.set_edgecolor(axis_style["color"])
        tick_style = {}
        if "line_width_pt" in axis_style:
            tick_style["width"] = axis_style["line_width_pt"]
        if "color" in axis_style:
            tick_style["color"] = axis_style["color"]
        ax.tick_params(axis="both", which="both", **tick_style)
    if options.get("grid", False):
        ax.grid(True, **line_style(spec, "grid", linewidth=.4, color="#e5e5e5"), zorder=0)
    resolved_colors = {}
    distribution_points = []
    rng = np.random.default_rng(spec.get("seed", 0))
    if chart == "heatmap":
        rows, cols = ordered(data, f["row"], spec, "y"), ordered(data, f["column"], spec, "x")
        matrix = data.assign(**{f["row"]: data[f["row"]].astype(str), f["column"]: data[f["column"]].astype(str)}).pivot(index=f["row"], columns=f["column"], values=f["value"]).loc[rows, cols]
        cmap, norm = continuous(spec, data[f["value"]])
        artist = ax.imshow(matrix, aspect=options.get("cell_aspect", "auto"), cmap=cmap, norm=norm, interpolation="nearest")
        figure_elements.register(fig, artist, "matrix", "Heatmap values", key="heatmap",
                                 source_keys=[{"row": row, "column": column} for row in rows for column in cols],
                                 spec_paths=["/colormap", "/options/color_limits"], editable=["color"])
        column_labels = options.get("column_labels")
        if column_labels is not None:
            require(set(column_labels) == set(cols), "options.column_labels must include every actual column category exactly once")
            fig._easyviz_column_label_keys = cols
        display_columns = [column_labels[column] for column in cols] if column_labels is not None else cols
        ax.set_xticks(range(len(cols)), display_columns, rotation=options.get("x_rotation", 90))
        ax.set_yticks(range(len(rows)), rows)
        border_width = options.get("cell_border_width_pt", 0)
        if border_width > 0:
            from matplotlib.collections import LineCollection
            segments = [((j - .5, -.5), (j - .5, len(rows) - .5)) for j in range(1, len(cols))]
            segments += [((-.5, i - .5), (len(cols) - .5, i - .5)) for i in range(1, len(rows))]
            seams = LineCollection(segments, colors=options.get("cell_border_color", "white"), linewidths=border_width, zorder=1)
            ax.add_collection(seams, autolim=False)
            figure_elements.register(fig, seams, "grid-line", "Heatmap cell boundaries", key="heatmap-cell-borders",
                                     spec_paths=["/options/cell_border_color", "/options/cell_border_width_pt"],
                                     editable={"color": "/options/cell_border_color", "linewidth": "/options/cell_border_width_pt"})
        legend_manager.add_colorbar(artist, labels.get("color", f["value"]))
        if options.get("annotate_values", False):
            fig._easyviz_cell_annotations = []
            for i in range(len(rows)):
                for j in range(len(cols)):
                    rgba = cmap(norm(matrix.iloc[i, j]))
                    luminance = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
                    text = ax.text(j, i, format(matrix.iloc[i, j], options.get("value_format", ".2g")), ha="center", va="center", color="black" if luminance > .55 else "white", fontsize=typography["annotation"])
                    fig._easyviz_cell_annotations.append({"text": text, "row": i, "column": j})
    elif chart == "composition":
        samples, groups = ordered(data, f["sample"], spec, "sample"), ordered(data, f["category"], spec, "category")
        resolved_colors = palette_colors(spec, groups)
        matrix = data.assign(**{f["sample"]: data[f["sample"]].astype(str), f["category"]: data[f["category"]].astype(str)}).pivot(index=f["sample"], columns=f["category"], values="_easyviz_plotted_value").reindex(index=samples, columns=groups)
        require(not matrix.isna().any().any() or options.get("missing_categories") == "zero", "Missing sample/category combinations; explicitly set options.missing_categories='zero' only for known zeros")
        matrix = matrix.fillna(0)
        bottom = np.zeros(len(samples))
        for group in groups:
            heights = matrix[group].to_numpy(float)
            bars = ax.bar(range(len(samples)), heights, bottom=bottom, label=group, color=resolved_colors[group], width=options.get("bar_width", .8), linewidth=0, zorder=2)
            for bar, sample in zip(bars, samples):
                figure_elements.register(fig, bar, "component", f"{sample} · {group}", key=[sample, group],
                                         source_keys=[{"sample": sample, "category": group}],
                                         spec_paths=[figure_elements.pointer("colors", group)], editable=["color"])
            bottom += heights
        ax.set_xticks(range(len(samples)), samples, rotation=options.get("x_rotation", 90))
        if options["normalization"] != "none":
            ax.set_ylim(0, 1)
        else:
            ax.set_ylim(bottom=0)
        legend_manager.add_categorical(groups, [resolved_colors[g] for g in groups])
        if options.get("percent_axis", False):
            require(options["normalization"] != "none", "percent_axis requires normalization to proportions")
            from matplotlib.ticker import PercentFormatter
            ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    elif chart == "dotplot":
        xs, ys = ordered(data, f["x"], spec, "x"), ordered(data, f["y"], spec, "y")
        measured = data[data["_easyviz_state"].eq("observed")]
        default_maximum = max(float(measured[f["size"]].max()), 1) if len(measured) else 1
        maximum = number(options.get("size_max", default_maximum), "size_max")
        require(not len(measured) or measured[f["size"]].max() <= maximum, "Dot values exceed size_max")
        max_area = number(options.get("max_area_pt2", 90), "max_area_pt2")
        data["_easyviz_area_pt2"] = data[f["size"]] / maximum * max_area
        data["_easyviz_marker_size_parameter_pt2"] = circle_size_parameter(data["_easyviz_area_pt2"])
        fig._easyviz_mark_geometry = mapped_circle_geometry(f["size"], maximum, max_area)
        fig._easyviz_mark_geometry["observed_rows"] = len(measured)
        xmap, ymap = {v: i for i, v in enumerate(xs)}, {v: i for i, v in enumerate(ys)}
        if len(measured):
            cmap, norm = continuous(spec, measured[f["color"]])
            artist = ax.scatter(measured[f["x"]].astype(str).map(xmap), measured[f["y"]].astype(str).map(ymap), marker="o", s=data.loc[measured.index, "_easyviz_marker_size_parameter_pt2"], c=measured[f["color"]], cmap=cmap, norm=norm, edgecolors="none", zorder=3)
            figure_elements.register(fig, artist, "point-group", "Observed dot values", key="dotplot:observed",
                                     source_keys=[{"record": int(index) + 1, "x": str(row[f["x"]]), "y": str(row[f["y"]])} for index, row in measured.iterrows()],
                                     spec_paths=["/colormap"], editable=["color"])
            legend_manager.add_colorbar(artist, labels.get("color", f["color"]))
            levels = options.get("size_legend", [maximum * .25, maximum * .5, maximum])
            require(all(0 < float(v) <= maximum for v in levels), "size_legend values must be within 0..size_max")
            legend_manager.add_size(levels, [float(v) / maximum * max_area for v in levels], title=labels.get("size", f["size"]), area_semantics="geometric_circle_area")
        ax.set_xticks(range(len(xs)), xs, rotation=options.get("x_rotation", 90))
        ax.set_yticks(range(len(ys)), ys)
        ax.set_xlim(-.6, len(xs) - .4)
        ax.set_ylim(len(ys) - .4, -.6)
        present = set(zip(data[f["x"]].astype(str), data[f["y"]].astype(str)))
        absent = [(x, y) for y in ys for x in xs if (x, y) not in present]
        absent_state = options.get("missing_cells", "unsupplied")
        require(not absent or absent_state != "error", "Missing dot coordinates; declare missing_cells as unsupplied or unmeasured")
        threshold = number(options.get("small_positive_area_pt2", 0), "small_positive_area_pt2", strict=False)
        zeros = data[data["_easyviz_state"].eq("observed") & data[f["size"]].eq(0)]
        unmeasured = data[data["_easyviz_state"].eq("unmeasured")]
        small = data[data["_easyviz_area_pt2"].gt(0) & data["_easyviz_area_pt2"].lt(threshold)]
        state_labels, state_symbols = [], []

        def state_marks(coordinates, marker, label, side=False):
            if not coordinates:
                return
            if options.get("state_markers", True):
                px, py = zip(*coordinates)
                # State glyphs have fixed display size and carry no magnitude.
                # A small-positive flag is beside the exact proportional dot.
                ax.scatter([xmap[str(x)] + (.18 if side else 0) for x in px], [ymap[str(y)] for y in py], marker=marker, s=16, c="#666666", linewidths=.6, zorder=4)
                state_labels.append(label)
                state_symbols.append(marker)

        def coordinates(frame):
            return list(zip(frame[f["x"]].astype(str), frame[f["y"]].astype(str)))

        state_marks(coordinates(zeros), "_", "Measured zero")
        unmeasured_coordinates = coordinates(unmeasured)
        if absent_state == "unmeasured":
            unmeasured_coordinates += absent
        state_marks(unmeasured_coordinates, "x", "Not measured")
        if absent_state == "unsupplied":
            state_marks(absent, "+", "Not supplied")
        state_marks(coordinates(small), "|", "Small positive", side=True)
        if state_labels:
            legend_manager.add_symbols(state_labels, state_symbols)
        fig._easyviz_dot_states = {"observed_rows": len(measured), "zero_rows": len(zeros), "unmeasured_rows": len(unmeasured), "missing_coordinates": [list(pair) for pair in absent], "missing_cells_meaning": absent_state, "small_positive_rows": len(small), "small_positive_area_threshold_pt2": threshold, "state_markers": options.get("state_markers", True), "symbols": dict(zip(state_labels, state_symbols)), "note": "State glyphs are separate nonquantitative marks. Observed geometric circle fill area remains size / size_max * max_area_pt2, with Matplotlib s = 4/pi times that area; an absent row is not a measured zero."}
    elif chart == "scatter":
        if "size" in f:
            maximum, max_area, levels = scatter_area_scale(data[f["size"]], options)
            data["_easyviz_area_pt2"] = data[f["size"]] / maximum * max_area
            data["_easyviz_marker_size_parameter_pt2"] = circle_size_parameter(data["_easyviz_area_pt2"])
            fig._easyviz_mark_geometry = mapped_circle_geometry(f["size"], maximum, max_area)
        else:
            fig._easyviz_mark_geometry = fixed_circle_geometry(options.get("point_area_pt2", 12), options)
        if "group" in f:
            groups = ordered(data, f["group"], spec, "group")
            resolved_colors = palette_colors(spec, groups)
            for group in groups:
                part = data[data[f["group"]].astype(str) == group]
                areas = part["_easyviz_marker_size_parameter_pt2"] if "size" in f else options.get("point_area_pt2", 12)
                points = ax.scatter(part[f["x"]], part[f["y"]], label=group, marker="o", s=areas, **observation_style(options, resolved_colors[group]), zorder=3)
                figure_elements.register(fig, points, "point-group", group, key=["scatter", group],
                                         source_keys=[{"group": group, "records": [int(index) + 1 for index in part.index]}],
                                         spec_paths=[figure_elements.pointer("colors", group), "/options/alpha"],
                                         editable={"color": figure_elements.pointer("colors", group), "alpha": "/options/alpha"})
            if options.get("point_style") == "hollow":
                legend_manager.add_categorical(groups, [resolved_colors[g] for g in groups], shape="marker",
                                               marker_style="hollow", linewidth_pt=options.get("point_edge_width_pt", .45), alpha=options.get("alpha", .85))
            else:
                legend_manager.add_categorical(groups, [resolved_colors[g] for g in groups], shape="marker")
        else:
            areas = data["_easyviz_marker_size_parameter_pt2"] if "size" in f else options.get("point_area_pt2", 12)
            points = ax.scatter(data[f["x"]], data[f["y"]], marker="o", s=areas, **observation_style(options, options.get("point_color", DEFAULT_COLORS[0])), zorder=3)
            figure_elements.register(fig, points, "point-group", "Observations", key="scatter:observations",
                                     source_keys=[{"records": [int(index) + 1 for index in data.index]}],
                                     spec_paths=["/options/point_color", "/options/alpha"],
                                     editable={"color": "/options/point_color", "alpha": "/options/alpha"})
        if "size" in f:
            legend_manager.add_size(levels, [float(v) / maximum * max_area for v in levels], title=labels.get("size", f["size"]), area_semantics="geometric_circle_area")
        if options.get("regression", False):
            from scipy.stats import linregress
            require(options.get("x_scale", "linear") == options.get("y_scale", "linear") == "linear", "OLS regression overlay currently requires linear x and y axes; fit and draw a transformed model explicitly for logarithmic axes")
            require(data[f["x"]].nunique() > 1 and len(data) >= 3, "Regression requires at least 3 observations and nonconstant x")
            fit = linregress(data[f["x"]].to_numpy(float), data[f["y"]].to_numpy(float))
            require(all(math.isfinite(v) for v in [fit.slope, fit.intercept]), "Undefined regression")
            ends = np.array([data[f["x"]].min(), data[f["x"]].max()])
            stroke = line_style(spec, "data", linewidth=layout["line_width_pt"], color="#333333")
            if "regression_color" in options:
                stroke["color"] = options["regression_color"]
            line, = ax.plot(ends, fit.intercept + fit.slope * ends, **stroke, zorder=4)
            width_path = line_width_path(spec, "data")
            color_path = ("/options/regression_color" if "regression_color" in options or "color" not in spec.get("line_roles", {}).get("data", {})
                          else "/line_roles/data/color")
            figure_elements.register(fig, line, "fit-line", "OLS regression", key="scatter:ols",
                                     spec_paths=[color_path, width_path],
                                     editable={"color": color_path, "linewidth": width_path})
            result["regression"] = {"method": "ordinary least squares, pooled observations", "slope": float(fit.slope), "intercept": float(fit.intercept), "n": len(data), "interval": "none"}
    elif chart == "distribution":
        fig._easyviz_mark_geometry = fixed_circle_geometry(options.get("point_area_pt2", 9), options)
        groups = ordered(data, f["group"], spec, "group")
        resolved_colors = palette_colors(spec, groups)
        samples = [data.loc[data[f["group"]].astype(str) == g, f["value"]].to_numpy(float) for g in groups]
        orientation = options.get("orientation", "vertical")
        require(orientation in ("vertical", "horizontal"), "orientation must be vertical or horizontal")
        kind = options.get("kind", "box")
        require(kind in ("box", "violin"), "Distribution kind must be box or violin")
        if kind == "box":
            boxes = ax.boxplot(samples, positions=np.arange(len(groups)), widths=options.get("box_width", .5), patch_artist=True, showfliers=False, manage_ticks=False, orientation=orientation,
                               medianprops=line_style(spec, "summary", linewidth=layout["line_width_pt"], color="#222222"),
                               whiskerprops=line_style(spec, "summary", linewidth=layout["line_width_pt"]),
                               capprops=line_style(spec, "summary", linewidth=layout["line_width_pt"]))
            bodies = boxes["boxes"]
            result["box_definition"] = "Median; 25th and 75th percentiles; whiskers to observations within 1.5 IQR. Every observation is drawn as a point."
        else:
            require(all(len(s) >= 2 and np.ptp(s) > 0 for s in samples), "Violin KDE requires at least 2 nonconstant observations per group")
            violins = ax.violinplot(samples, positions=np.arange(len(groups)), widths=options.get("violin_width", .7), showextrema=False, showmedians=False, orientation=orientation, bw_method="scott")
            bodies = violins["bodies"]
            result["violin_definition"] = "Gaussian KDE with Scott bandwidth, 100 evaluation points; each violin width independently normalized. Every observation is drawn as a point."
        for body, group in zip(bodies, groups):
            fill_alpha = options.get("violin_fill_alpha", .22) if kind == "violin" else options.get("box_fill_alpha", .22)
            if kind == "violin" and "violin_fill_alpha" in options:
                # Matplotlib initially assigns collection alpha=.3. Clear that
                # override only for explicitly requested face/edge separation.
                body.set_alpha(None)
            body.set_facecolor("none" if options.get("box_style") == "outline" else mcolors.to_rgba(resolved_colors[group], fill_alpha))
            stroke_role = "summary" if kind == "box" else "data"
            stroke = line_style(spec, stroke_role, linewidth=layout["line_width_pt"], color=resolved_colors[group])
            body.set_edgecolor(stroke["color"])
            body.set_linewidth(stroke["linewidth"])
            if "linestyle" in stroke:
                body.set_linestyle(stroke["linestyle"])
            width_path = line_width_path(spec, stroke_role)
            category_color_path = figure_elements.pointer("colors", group)
            paths = [category_color_path, width_path]
            edits = {"color": category_color_path, "linewidth": width_path}
            has_visible_face = options.get("box_style") != "outline" and fill_alpha > 0
            if has_visible_face:
                edits["facecolor"] = category_color_path
            if "color" in spec.get("line_roles", {}).get(stroke_role, {}):
                edge_path = figure_elements.pointer("line_roles", stroke_role, "color")
                paths.append(edge_path)
                edits["edgecolor"] = edge_path
                if not has_visible_face:
                    edits["color"] = edge_path
            else:
                edits["edgecolor"] = category_color_path
            if kind == "box" and "box_fill_alpha" in options:
                paths.append("/options/box_fill_alpha")
                if options.get("box_style") != "outline":
                    edits["fill_alpha"] = "/options/box_fill_alpha"
            if kind == "violin" and "violin_fill_alpha" in options:
                paths.append("/options/violin_fill_alpha")
                edits["fill_alpha"] = "/options/violin_fill_alpha"
            if kind == "violin" and "violin_width" in options:
                paths.append("/options/violin_width")
            figure_elements.register(fig, body, "distribution", group, key=[kind, group],
                                     source_keys=[{"group": group}],
                                     spec_paths=paths, editable=edits)
        if kind == "violin" and options.get("violin_inner", "none") == "box":
            from matplotlib.patches import Rectangle
            inner_width = options.get("violin_inner_width", .12)
            inner_fill_alpha = options.get("violin_inner_fill_alpha", 0)
            median_visible = options.get("violin_median_visible", True)
            result["violin_inner_definition"] = "Hollow raw-value Q1/Q3 box with an optional median line; NumPy linear quantiles; no whiskers. Fixed categorical width independent of KDE density and sample count."
            if inner_fill_alpha > 0:
                result["violin_inner_definition"] = "Category-filled raw-value Q1/Q3 box with an optional median line; NumPy linear quantiles; no whiskers. Fixed categorical width independent of KDE density and sample count."
            result["violin_inner_summaries"] = []
            for i, (sample, group) in enumerate(zip(samples, groups)):
                q1, median, q3 = map(float, np.quantile(sample, [.25, .5, .75], method="linear"))
                box_stroke = line_style(spec, "summary", linewidth=layout["line_width_pt"], color=resolved_colors[group])
                median_stroke = line_style(spec, "summary", linewidth=layout["line_width_pt"], color="#222222")
                lower, upper = i - inner_width / 2, i + inner_width / 2
                rect = Rectangle((lower, q1) if orientation == "vertical" else (q1, lower),
                                 inner_width if orientation == "vertical" else q3 - q1,
                                 q3 - q1 if orientation == "vertical" else inner_width,
                                 facecolor="none" if inner_fill_alpha == 0 else mcolors.to_rgba(resolved_colors[group], inner_fill_alpha),
                                 edgecolor=box_stroke["color"], linewidth=box_stroke["linewidth"],
                                 linestyle=box_stroke.get("linestyle", "-"), zorder=4)
                ax.add_patch(rect)
                summaries = [(rect, "Q1–Q3", "iqr")]
                if median_visible:
                    line, = ax.plot([lower, upper] if orientation == "vertical" else [median, median],
                                    [median, median] if orientation == "vertical" else [lower, upper],
                                    **median_stroke, zorder=4)
                    summaries.append((line, "Median", "median"))
                width_path = line_width_path(spec, "summary")
                for artist, label, part in summaries:
                    paths = [width_path, "/options/violin_inner_width"]
                    edits = {"linewidth": width_path}
                    summary_color_path = figure_elements.pointer("line_roles", "summary", "color") if "color" in spec.get("line_roles", {}).get("summary", {}) else None
                    if part == "iqr":
                        category_color_path = figure_elements.pointer("colors", group)
                        edge_color_path = summary_color_path or category_color_path
                        paths.append(edge_color_path)
                        edits.update(color=category_color_path if inner_fill_alpha > 0 else edge_color_path,
                                     edgecolor=edge_color_path)
                        if inner_fill_alpha > 0:
                            if category_color_path not in paths:
                                paths.append(category_color_path)
                            edits["facecolor"] = category_color_path
                        if "violin_inner_fill_alpha" in options:
                            paths.append("/options/violin_inner_fill_alpha")
                            edits["fill_alpha"] = "/options/violin_inner_fill_alpha"
                    elif summary_color_path is not None:
                        paths.append(summary_color_path)
                        edits["color"] = summary_color_path
                    figure_elements.register(fig, artist, "summary-line", f"{group} · {label}", key=["violin-inner", group, part],
                                             source_keys=[{"group": group}],
                                             spec_paths=paths, editable=edits)
                result["violin_inner_summaries"].append({"group": group, "n_observations": len(sample),
                                                       "q1": q1, "median": median, "q3": q3,
                                                       "categorical_width": inner_width, "median_line_visible": median_visible})
        for i, (sample, group) in enumerate(zip(samples, groups)):
            positions = (np.full(len(sample), i, dtype=float) if options.get("point_layout") == "beeswarm"
                         else i + rng.uniform(-.13, .13, len(sample)))
            positions += options.get("point_category_offset", 0)
            rows = data.index[data[f["group"]].astype(str) == group].to_numpy()
            data.loc[rows, "_easyviz_jitter_position"] = positions
            points = ax.scatter(positions if orientation == "vertical" else sample, sample if orientation == "vertical" else positions, marker="o", s=options.get("point_area_pt2", 9), **observation_style(options, options.get("point_color", resolved_colors[group])), zorder=3)
            distribution_points.append((i, group, sample, rows, points))
            point_color_path = "/options/point_color" if "point_color" in options else figure_elements.pointer("colors", group)
            figure_elements.register(fig, points, "point-group", group, key=["distribution", group],
                                     source_keys=[{"group": group, "records": [int(index) + 1 for index in rows]}],
                                     spec_paths=[point_color_path, "/options/alpha"]
                                                + (["/options/point_category_offset"] if "point_category_offset" in options else []),
                                     editable={"color": point_color_path, "alpha": "/options/alpha"})
        if orientation == "vertical":
            ax.set_xticks(range(len(groups)), groups, rotation=options.get("x_rotation", 0))
            ax.set_xlim(-.6, len(groups) - .4)
        else:
            ax.set_yticks(range(len(groups)), groups)
            ax.set_ylim(len(groups) - .4, -.6)
    for dimension in ("x", "y"):
        if dimension in labels:
            getattr(ax, f"set_{dimension}label")(labels[dimension], fontsize=typography["axis"])
        if f"{dimension}_limits" in options:
            limits = options[f"{dimension}_limits"]
            require(len(limits) == 2 and np.isfinite(limits).all() and limits[0] < limits[1], f"{dimension}_limits must be finite and ascending")
            if options.get(f"{dimension}_scale", "linear") == "log":
                require(limits[0] > 0 and limits[1] > 0, f"Logarithmic {dimension}_limits must be strictly positive")
            value_axis = "x" if options.get("orientation") == "horizontal" else "y"
            require(chart == "scatter" or (chart == "distribution" and dimension == value_axis), "Explicit axis limits are supported only on numeric scatter/distribution axes")
            if chart == "scatter" or (chart == "distribution" and dimension == value_axis):
                role = dimension if chart == "scatter" else "value"
                require(data[f[role]].min() >= limits[0] and data[f[role]].max() <= limits[1], f"{dimension}_limits would hide observations")
            getattr(ax, f"set_{dimension}lim")(*limits)
        scale = options.get(f"{dimension}_scale", "linear")
        require(scale in ("linear", "log"), f"Unsupported {dimension}_scale")
        if scale == "log":
            value_axis = "x" if options.get("orientation") == "horizontal" else "y"
            require(chart == "scatter" or (chart == "distribution" and dimension == value_axis), "Log scale only supported on numeric scatter/distribution axes")
            role = dimension if chart == "scatter" else "value"
            require((data[f[role]] > 0).all(), "Log axes require strictly positive values")
            getattr(ax, f"set_{dimension}scale")("log")
    if chart == "scatter":
        for dimension, positions in options.get("reference_lines", {}).items():
            draw_line = ax.axvline if dimension == "x" else ax.axhline
            for reference_index, position in enumerate(positions):
                line = draw_line(position, **line_style(spec, "reference", linewidth=layout["line_width_pt"], color="#999999", linestyle="--"), zorder=1)
                width_path = line_width_path(spec, "reference")
                paths = [width_path, figure_elements.pointer("options", "reference_lines", dimension)]
                edits = {"linewidth": width_path}
                for property_name in ("color", "linestyle"):
                    if property_name in spec.get("line_roles", {}).get("reference", {}):
                        path = figure_elements.pointer("line_roles", "reference", property_name)
                        paths.append(path)
                        edits[property_name] = path
                figure_elements.register(fig, line, "reference-line", f"{dimension.upper()} reference at {position:g}",
                                         key=[dimension, reference_index, position], source_keys=[{"axis": dimension, "position": position}],
                                         spec_paths=paths, editable=edits)
    if labels.get("title"):
        ax.set_title(labels["title"], fontsize=typography["title"], pad=6)
    if labels.get("panel"):
        fig.text(.035, .965, labels["panel"], ha="left", va="top", fontsize=typography["panel"], fontweight="bold")
    if spec.get("statistics", {}).get("annotate", False):
        require(result.get("method") != "none", "Statistical annotation requires a test")
        ptext = "p < 0.001" if result["pvalue"] == 0 else f"p = {result['pvalue']:.3g}"
        note = f"{result['method']}: {ptext}"
        if result["method"] in ("pearson", "spearman"):
            note = f"{'r' if result['method'] == 'pearson' else 'rho'} = {result['statistic']:.2f}; {ptext}"
        elif "groups" in result:
            note = f"{' vs '.join(map(str, result['groups']))}\n{note}"
        ax.text(.02, .98, note, ha="left", va="top", transform=ax.transAxes, fontsize=typography["annotation"], bbox={"facecolor": "white", "edgecolor": "none", "alpha": .85, "pad": 1}, zorder=6)
    if chart != "heatmap":
        ax.spines[["top", "right"]].set_visible(False)
    if layout.get("auto_fit", False):
        try:
            fig._easyviz_auto_layout = auto_layout.fit(fig, ax, legend_manager, check_tick_label_overlap,
                annotation_check=lambda canvas, axes: annotation_review.check_heatmap_annotations(
                    canvas, axes, getattr(canvas, "_easyviz_cell_annotations", [])))
        except ValueError as exc:
            raise SpecError(str(exc)) from None
        layout["margins"] = fig._easyviz_auto_layout["margins"]
    else:
        legend_manager.layout()
    if chart == "distribution":
        if options.get("point_layout") == "beeswarm":
            place_distribution_points(fig, ax, data, spec, distribution_points)
        else:
            fig._easyviz_point_layout = {"policy": "jitter", "status": "unchecked",
                                        "seed": spec.get("seed", 0), "categorical_half_width": .13,
                                        "point_category_offset": options.get("point_category_offset", 0),
                                        "numeric_values_changed": False,
                                        "note": "Legacy uniform categorical jitter retained. Circle overlap is not automatically checked; inspect the rendered panel or explicitly use point_layout='beeswarm'."}
            if options.get("point_category_offset", 0):
                # An explicitly shifted raw layer must stay in its original
                # category, even when legacy jitter has no collision audit.
                fig.canvas.draw()
                cat_axis = 1 if options.get("orientation") == "horizontal" else 0
                px_to_pt = 72 / fig.dpi
                diameter = math.sqrt(float(options.get("point_area_pt2", 9)))
                if options.get("point_style") == "hollow":
                    diameter += float(options.get("point_edge_width_pt", .45))
                plot = ax.get_window_extent()
                bounds = sorted(([plot.x0, plot.x1] if cat_axis == 0 else [plot.y0, plot.y1]))
                boundary_rows = []
                for center, group, sample, rows, artist in distribution_points:
                    base = [sample[0], center] if cat_axis else [center, sample[0]]
                    category_center = ax.transData.transform(base)[cat_axis]
                    unit = base.copy()
                    unit[cat_axis] += 1
                    step = abs(ax.transData.transform(unit)[cat_axis] - category_center)
                    lower = max(bounds[0], category_center - .45 * step) * px_to_pt
                    upper = min(bounds[1], category_center + .45 * step) * px_to_pt
                    actual = ax.transData.transform(artist.get_offsets())[:, cat_axis] * px_to_pt
                    outside = np.flatnonzero((actual - diameter / 2 < lower - 1e-8) | (actual + diameter / 2 > upper + 1e-8))
                    boundary_rows.extend(int(rows[index]) + 1 for index in outside)
                fig._easyviz_point_layout["categorical_boundary_rows"] = boundary_rows
                if boundary_rows:
                    fig._easyviz_point_layout["status"] = "needs_revision"
    fig._easyviz_legend_layout = legend_manager
    return fig, resolved_colors


def export(fig, out, spec, layout):
    formats = spec.get("formats", ["pdf", "png"])
    require(isinstance(formats, list) and len(formats) > 0 and len(formats) == len(set(formats)), "formats must be a nonempty list without duplicates")
    require(all(f in ("pdf", "svg", "png", "tiff") for f in formats), "Supported formats: pdf, svg, png, tiff")
    figure_elements.attach_layout(fig, spec)
    width_px = round(layout["width_mm"] / 25.4 * layout["dpi"])
    height_px = round(layout["height_mm"] / 25.4 * layout["dpi"])
    sizes = {}
    clipping_reports = {}
    for extension in formats:
        path = out / f"panel.{extension}"
        if extension in ("png", "tiff"):
            # The raster grid rounds to whole pixels while text retains its point size.
            old_size = fig.get_size_inches().copy()
            fig.set_size_inches(width_px / layout["dpi"], height_px / layout["dpi"])
            fig.canvas.draw()
            clipping_reports[extension] = observation_clipping.measure(fig)
            rgba = np.asarray(fig.canvas.buffer_rgba())
            im = Image.fromarray(rgba).convert("RGB")
            im.save(path, dpi=(layout["dpi"], layout["dpi"]), **({"compression": "tiff_lzw"} if extension == "tiff" else {}))
            fig.set_size_inches(old_size)
            with Image.open(path) as check:
                sizes[extension] = {"pixels": list(check.size), "dpi": [float(v) for v in check.info.get("dpi", [])]}
                require(check.size == (width_px, height_px), "Raster pixel dimensions do not match rounded physical dimensions")
        else:
            metadata = {"Creator": "EasyViz", "CreationDate": None, "ModDate": None} if extension == "pdf" else {"Creator": "EasyViz", "Date": None}
            clipping_reports[extension] = observation_clipping.measure(fig)
            fig.savefig(path, format=extension, dpi=layout["dpi"], bbox_inches=None, metadata=metadata)
            if extension == "pdf":
                from pypdf import PdfReader
                page = PdfReader(path).pages[0]
                dims = [float(page.mediabox.width) / 72 * 25.4, float(page.mediabox.height) / 72 * 25.4]
                sizes[extension] = {"width_mm": dims[0], "height_mm": dims[1]}
                require(np.allclose(dims, [layout["width_mm"], layout["height_mm"]], atol=1e-5), "PDF page dimensions differ from settings")
            else:
                import xml.etree.ElementTree as ET
                root = ET.parse(path).getroot()
                dims = [float(root.attrib[k].removesuffix("pt")) / 72 * 25.4 for k in ("width", "height")]
                sizes[extension] = {"width_mm": dims[0], "height_mm": dims[1], "text_preserved": True, "font_embedding": "SVG references the recorded font; install it on the assembly system."}
        # Bind these measurements to the exact bytes independently measured
        # above. Review helpers can reject an export replaced before staging
        # without pretending old page/pixel metadata describes the new file.
        sizes[extension]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    figure_elements.write(fig, out, spec, layout)
    fig._easyviz_observation_clipping = observation_clipping.summarize(clipping_reports)
    return sizes


def check_tick_label_overlap(fig, painter):
    """Conservative same-axis text-box checks for horizontal/vertical tick labels.

    Oblique labels require polygon/glyph geometry rather than axis-aligned boxes,
    so record them for visual review without manufacturing false positives.
    """
    overlaps, skipped = [], []
    for ax_number, axes in enumerate(fig.axes):
        for direction, axis in (("x", axes.xaxis), ("y", axes.yaxis)):
            low, high = sorted(axis.get_view_interval())
            tolerance = max(1, abs(high - low)) * 1e-10
            labels = []
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low - tolerance <= tick.get_loc() <= high + tolerance:
                    continue
                for label in (tick.label1, tick.label2):
                    if not label.get_visible() or not label.get_text().strip():
                        continue
                    rotation = float(label.get_rotation()) % 180
                    if not (math.isclose(rotation, 0, abs_tol=1e-8) or math.isclose(rotation, 90, abs_tol=1e-8)):
                        skipped.append({"axes": ax_number, "axis": direction, "text": label.get_text(), "rotation": rotation})
                    else:
                        labels.append(label)
            for i, a in enumerate(labels):
                ra = a.get_window_extent(painter)
                for b in labels[i + 1:]:
                    rb = b.get_window_extent(painter)
                    w, h = min(ra.x1, rb.x1) - max(ra.x0, rb.x0), min(ra.y1, rb.y1) - max(ra.y0, rb.y0)
                    if w > .01 and h > .01:
                        overlaps.append({"axes": ax_number, "axis": direction, "labels": [a.get_text(), b.get_text()], "intersection_px": [round(float(w), 2), round(float(h), 2)]})
    return overlaps, skipped


def _render(data_path, spec, out, profile_record=None, spec_path=None, track=None, source_bindings=None):
    data_path, out = Path(data_path), Path(out)
    data = prepare(data_path, spec)
    bindings = dict(source_bindings or {})
    bindings["data_file"] = {"path": str(data_path.resolve()), "sha256": data.attrs["source_csv_sha256"]}
    for name, digest in RUNTIME_SOURCE_DIGESTS.items():
        role = "source_script" if name == "render.py" else f"helper:{name}"
        bindings[role] = {"path": str(Path(__file__).with_name(name).resolve()), "sha256": digest}
    if profile_record is not None:
        bindings["figure_profile"] = {"path": profile_record["path"], "sha256": profile_record["sha256"]}
    continuity = source_continuity(bindings)
    require(continuity["status"] == "pass", "Source/spec/profile changed before rendering; prepare the current inputs again")
    results = statistics(data, spec)
    layout, typography, rc = setup(spec)
    out.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        figures_before = set(plt.get_fignums())
        try:
            fig, colors = draw(data, spec, layout, typography, results)
        except Exception:
            for number_ in set(plt.get_fignums()) - figures_before:
                plt.close(number_)
            raise
        try:
            fig._easyviz_data_file = data_path.resolve()
            fig._easyviz_source_script = Path(__file__).resolve()
            fig._easyviz_spec_file = Path(spec_path).resolve() if spec_path else None
            fig._easyviz_track = track
            fig._easyviz_resolved_colors = colors
            fig._easyviz_source_bindings = bindings
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            width, height = fig.bbox.width, fig.bbox.height
            clipped = []
            # Locators may create visible Text objects for ticks beyond the view.
            # Axis.draw does not paint those; they must not cause a clipping failure.
            undrawn_ticks = set()
            for axes in fig.axes:
                for axis in (axes.xaxis, axes.yaxis):
                    low, high = sorted(axis.get_view_interval())
                    tolerance = max(1, abs(high - low)) * 1e-10
                    for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                        if not low - tolerance <= tick.get_loc() <= high + tolerance:
                            undrawn_ticks.update((tick.label1, tick.label2))
            for artist in fig.findobj(Text):
                if artist in undrawn_ticks or not artist.get_visible() or not artist.get_text().strip():
                    continue
                bounds = artist.get_window_extent(renderer)
                if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > width + 1 or bounds.y1 > height + 1:
                    clipped.append({"text": artist.get_text(), "bounds_px": [round(v, 2) for v in bounds.extents]})
            overlaps, oblique_labels = check_tick_label_overlap(fig, renderer)
            legends = fig._easyviz_legend_layout.validate()
            cell_annotations = annotation_review.check_heatmap_annotations(fig, fig.axes[0], getattr(fig, "_easyviz_cell_annotations", []))
            fitted = getattr(fig, "_easyviz_auto_layout", None)
            continuity = source_continuity(bindings)
            require(continuity["status"] == "pass", "Source/spec/profile changed before export; prepare the current inputs again")
            exports = export(fig, out, spec, layout)
            continuity = source_continuity(bindings)
            readability = panel_readability.measure(fig)
            clipping_report = fig._easyviz_observation_clipping
            missing_glyphs = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            settings = dict(spec)
            settings.update(layout=layout, typography=typography, resolved_colors=colors, formats=spec.get("formats", ["pdf", "png"]), seed=spec.get("seed", 0), input_file=data_path.name, input_sha256=bindings["data_file"]["sha256"])
            settings["source_bindings"] = bindings
            settings["source_snapshot"] = {"file": "source-data.csv", "sha256": bindings["data_file"]["sha256"],
                                           "row_count": len(data), "semantics": "Exact captured CSV bytes, including literal numeric spellings and source-cell/ID columns; parsed once with strict header/record width."}
            settings["renderer"] = {"version": VERSION, "sha256": RUNTIME_SOURCE_DIGESTS["render.py"]}
            if track is not None:
                settings["track"] = track
            settings["renderer"]["legend_helper_sha256"] = RUNTIME_SOURCE_DIGESTS["legend_layout.py"]
            settings["renderer"]["profile_helper_sha256"] = RUNTIME_SOURCE_DIGESTS["figure_profile.py"]
            settings["renderer"]["auto_layout_helper_sha256"] = RUNTIME_SOURCE_DIGESTS["auto_layout.py"]
            settings["renderer"]["annotation_helper_sha256"] = RUNTIME_SOURCE_DIGESTS["annotation_review.py"]
            settings["renderer"]["readability_helper_sha256"] = RUNTIME_SOURCE_DIGESTS["panel_readability.py"]
            settings["renderer"]["observation_clipping_helper_sha256"] = RUNTIME_SOURCE_DIGESTS["observation_clipping.py"]
            settings["observation_clipping"] = clipping_report
            if fitted:
                settings["auto_layout"] = fitted
            if profile_record is not None:
                settings["figure_profile"] = profile_record
            settings["legend_layout"] = legends
            if mark_geometry := getattr(fig, "_easyviz_mark_geometry", None):
                settings["mark_geometry"] = mark_geometry
            if chart_states := getattr(fig, "_easyviz_dot_states", None):
                settings["dot_states"] = chart_states
            point_layout = getattr(fig, "_easyviz_point_layout", None)
            if point_layout:
                settings["point_layout"] = point_layout
            settings["runtime"] = {"python": platform.python_version(), **{name: package_version(name) for name in ("matplotlib", "numpy", "pandas", "scipy", "Pillow", "pypdf")}}
            passed = continuity["status"] == "pass" and not clipped and not missing_glyphs and not overlaps and legends["status"] == "pass" and cell_annotations["status"] == "pass" and (not fitted or fitted["status"] == "pass") and (not point_layout or point_layout["status"] != "needs_revision") and clipping_report["status"] != "needs_revision"
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "input_rows": len(data), "plotted_input_rows": len(data), "input_sha256": settings["input_sha256"], "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "clipped_text": clipped, "overlapping_tick_labels": overlaps, "unchecked_oblique_tick_labels": oblique_labels, "missing_glyphs": missing_glyphs, "exports": exports, "visual_review_required": True, "note": "Automated checks cover text canvas boundaries, same-axis horizontal/vertical tick-label overlap, heatmap cell annotations and final circular observation envelopes at each export canvas size. Oblique text, other label/mark overlaps, statistical design and visual fidelity still require visual review."}
            qa["legend_layout"] = legends
            qa["cell_annotations"] = cell_annotations
            qa["readability"] = readability
            qa["observation_clipping"] = clipping_report
            qa["source_continuity"] = continuity
            if fitted:
                qa["auto_layout"] = fitted
            if chart_states:
                qa["dot_states"] = chart_states
            if point_layout:
                qa["point_layout"] = point_layout
            data.to_csv(out / "plotting-data.csv", index=False)
            (out / "source-data.csv").write_bytes(data.attrs["source_csv_bytes"])
            write_json(out / "settings.json", settings)
            write_json(out / "stats.json", results)
            write_json(out / "qa.json", qa)
            require(continuity["status"] == "pass", "Source/spec/profile changed during export; old consumed bytes are preserved in source-data.csv and this run is invalid")
            point_issues = point_layout.get("spacing_violation_pairs", 0) if point_layout else 0
            point_boundary_issues = len(point_layout.get("categorical_boundary_rows", [])) if point_layout else 0
            clipped_marks = max((report["clipped_observations"] for report in clipping_report["by_format"].values()), default=0)
            require(qa["status"] == "pass", f"Canvas QA needs revision: {len(clipped)} clipped text elements, {len(overlaps)} tick-label overlaps, {len(legends['issues'])} legend issues, {len(cell_annotations['issues'])} cell annotation issues, {point_issues} observation spacing conflicts, {point_boundary_issues} observation marker boundary issues, {clipped_marks} clipped observation envelopes, {len(missing_glyphs)} missing glyph warnings; inspect qa.json and panel.png. Preserve text and mark sizes; explicitly revise the adopted range/layout or split a panel that cannot fit.")
            return qa
        finally:
            plt.close(fig)


def parse_spec_bytes(raw):
    """Parse one exact spec byte snapshot without duplicate or nonfinite JSON."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON keys")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeError, ValueError) as exc:
        raise SpecError("Specification must be finite UTF-8 JSON without duplicate keys") from exc


def render(data_path, spec, out, *, profile=None, panel=None, spec_path=None, track=None, captured_spec_bytes=None):
    """Mark every attempted run so stale exports cannot retain a passing QA record."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    status = {"status": "in_progress", "valid_outputs": False, "note": "Until this run passes, any exports in this directory are unverified and may belong to an earlier run."}
    write_json(out / "qa.json", status)
    try:
        require(track in (None, "create", "reproduce"), "track must be create or reproduce when supplied")
        bindings = {}
        require(captured_spec_bytes is None or isinstance(captured_spec_bytes, bytes) and spec_path is not None,
                "captured_spec_bytes requires exact bytes and the corresponding spec_path")
        if spec_path is not None:
            spec_file = Path(spec_path).resolve()
            # Python callers can use a not-yet-saved spec path only as the
            # base for a relative profile. Preserve that established API, but
            # never claim bytes were consumed from an absent file or bind a
            # file that first appears during rendering.
            spec_raw = captured_spec_bytes if captured_spec_bytes is not None else spec_file.read_bytes() if spec_file.is_file() else None
            require(spec_raw is None or parse_spec_bytes(spec_raw) == spec,
                    "Supplied specification differs from the captured spec file; save the adopted dictionary or omit the file claim")
            bindings["spec_file"] = {"path": str(spec_file), "sha256": hashlib.sha256(spec_raw).hexdigest() if spec_raw is not None else None}
        resolved, profile_record = resolve_spec(spec, profile=profile, panel=panel, spec_path=spec_path)
        return _render(data_path, resolved, out, profile_record, spec_path=spec_path, track=track, source_bindings=bindings)
    except Exception as exc:
        current = json.loads((out / "qa.json").read_text())
        if current.get("status") == "in_progress":
            current.update(status="failed", error=str(exc))
            write_json(out / "qa.json", current)
        raise


def render_spec_file(data_path, spec_path, out, *, profile=None, panel=None, track=None):
    """Load and render one captured spec snapshot; failed parsing invalidates QA."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False,
                                "note": "Specification loading and rendering must both finish before these exports are validated."})
    try:
        raw = Path(spec_path).read_bytes()
        return render(data_path, parse_spec_bytes(raw), out, profile=profile, panel=panel,
                      spec_path=spec_path, track=track, captured_spec_bytes=raw)
    except Exception as exc:
        current = json.loads((out / "qa.json").read_text())
        if current.get("status") == "in_progress":
            current.update(status="failed", error=str(exc))
            write_json(out / "qa.json", current)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="Source CSV; rows are never silently dropped")
    parser.add_argument("--spec", type=Path, help="JSON plot specification")
    parser.add_argument("--out", type=Path, help="Directory for panel exports, plotting data, settings, statistics, and QA")
    parser.add_argument("--profile", type=Path, help="Shared figure-profile JSON; conflicts with local settings are errors")
    parser.add_argument("--panel", help="Panel name whose physical dimensions are declared in the profile")
    parser.add_argument("--track", choices=("create", "reproduce"), help="Record the adopted track without inferring it from the chart")
    parser.add_argument("--describe-spec", action="store_true", help="Print supported fields, options, and semantics as JSON")
    args = parser.parse_args()
    if args.describe_spec:
        print(json.dumps(SCHEMA, indent=2))
        return
    if not all([args.data, args.spec, args.out]):
        parser.error("--data, --spec and --out are required unless --describe-spec is used")
    try:
        qa = render_spec_file(args.data, args.spec, args.out, profile=args.profile, panel=args.panel, track=args.track)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}))


if __name__ == "__main__":
    main()
