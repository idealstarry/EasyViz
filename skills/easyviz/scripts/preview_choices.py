#!/usr/bin/env python3
"""Render descriptive distribution choices from explicitly prepared observations.

Use --describe-contract before preparing a request. This helper never chooses
an aesthetic winner, infers study design, aggregates rows or performs a test.
Keep this file beside ecdf_plot.py, render.py and their sibling helpers.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import hashlib
import importlib.util
from importlib.metadata import version as package_version
import io
import json
import math
from pathlib import Path
import platform
import warnings


def _load(name, filename):
    loader = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


ecdf = _load("easyviz_preview_ecdf", "ecdf_plot.py")
core = ecdf.core
require, SpecError = core.require, core.SpecError
VERSION = "0.1.0"
HELPERS = ("ecdf_plot.py", *ecdf.HELPERS)
CONTRACT = {
    "version": VERSION,
    "command": "preview_choices.py --data prepared.csv --request request.json --out NEW_DIRECTORY",
    "scope": "Descriptive raw-observation distributions; two real previews, or three with an explicitly requested meaningful violin.",
    "request": {
        "row_kind": "observations (required; summaries and technical replicates rejected)",
        "fields": {"value": "required numeric column", "group": "required literal category column", "unit": "optional literal one-observation-per-unit ID"},
        "design": {"structure": "unknown|independent", "confirmed": False, "unit_definition": "required scientific definition or explicit unknown row-level definition"},
        "measurement_units": "required string or null for explicitly unknown units",
        "colors": {"every observed group exactly once": "distinct opaque color"},
        "order": {"group": "optional complete category order; otherwise first appearance"},
        "layout": {"width_mm": 88, "height_mm": 70, "font": "Arial", "font_size_pt": 8, "line_width_pt": .6, "dpi": 300},
        "typography": {"axis": "optional pt", "tick": "optional pt", "legend": "optional pt"},
        "labels": {"value": "optional measurement name without invented units", "group": "optional group label"},
        "formats": ["png", "pdf", "svg"],
        "options": {"value_scale": "linear|log", "value_limits": "optional complete ascending bounds", "point_layout": "jitter|beeswarm", "point_alpha": "finite 0 < alpha <= 1; default 0.65, raw observations only", "include_violin": False},
    },
    "choices": ["box-points: median/IQR/1.5-IQR whiskers and every raw observation", "ecdf: count(value <= x)/group row count, unsmoothed full tie jumps", "violin-points: optional Gaussian KDE, Scott bandwidth, all points; at least 5 distinct values in every group"],
    "invariants": ["Same byte-identical source snapshot, rows, literal IDs, dimensions, actual font, font sizes, category colors and value axis limits.", "No silent exclusion, transformation, aggregation, pairing, confidence interval or hypothesis test.", "Unknown units or independence permit clearly labeled descriptive previews only.", "Repeated unit IDs across groups and explicit paired/repeated designs require prepared complete paired data and paired_plot.py; these marginal choices do not encode pairing.", "Fresh output directory; failed QA remains marked invalid. PNG is required for inspection. Inspect all actual exports before choosing; no winner is selected."],
    "outputs": ["manifest.json", "qa.json", "request.json", "source.csv", "observation-trace.csv", "visual-review.md", "per-choice spec.json, caption.md, panel exports, plotting-data.csv, stats.json, settings.json, qa.json; ECDF cumulative-data.csv"],
}


def _object(value, keys, name):
    require(isinstance(value, dict), f"{name} must be an object")
    require(not set(value) - keys, f"Unknown {name} keys: {sorted(set(value) - keys)}")


def _number(value, name, *, positive=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), f"{name} must be a finite JSON number")
    require(not positive or value > 0, f"{name} must be positive")
    return float(value)


def _hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _hash(path):
    return _hash_bytes(Path(path).read_bytes())


def _json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _read_source(raw):
    try:
        table = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise SpecError(f"Prepared input must be a valid UTF-8 CSV: {exc}") from None
    require(len(table) > 1, "Prepared CSV requires a header and observations")
    headers, rows = table[0], table[1:]
    require(all(h.strip() for h in headers) and len(headers) == len(set(headers)), "CSV headers must be nonempty and unique")
    require(not any(h.startswith("_easyviz_") for h in headers), "Input columns starting _easyviz_ are reserved")
    require(all(len(row) == len(headers) for row in rows), "Ragged or empty CSV rows must be prepared explicitly; no row is dropped")
    return headers, rows


def prepare_request(raw, request):
    """Validate explicit semantics and preserve every source row before writing."""
    _object(request, {"row_kind", "fields", "design", "measurement_units", "colors", "order", "layout", "typography", "labels", "formats", "options"}, "request")
    require(request.get("row_kind") == "observations", "row_kind must explicitly be observations; prepare summaries or technical replicates upstream without silently aggregating them")
    fields = request.get("fields", {})
    _object(fields, {"group", "value", "unit"}, "fields")
    require({"group", "value"} <= set(fields), "fields requires explicit group and value columns")
    require(all(isinstance(c, str) and c.strip() for c in fields.values()), "fields must name nonempty source columns")
    require(len(set(fields.values())) == len(fields), "Mapped roles must name distinct source columns")
    design = request.get("design", {})
    _object(design, {"structure", "confirmed", "unit_definition"}, "design")
    require(set(design) == {"structure", "confirmed", "unit_definition"}, "design requires structure, confirmed and unit_definition; unknown is an explicit descriptive choice")
    require(design["structure"] not in ("paired", "repeated"), "Paired/repeated previews require explicit complete unit/condition/value data and paired_plot.py; marginal box/ECDF choices do not encode pairing")
    require(design["structure"] in ("unknown", "independent"), "design.structure must be unknown or independent")
    require(isinstance(design["confirmed"], bool), "design.confirmed must be a boolean")
    require(isinstance(design["unit_definition"], str) and design["unit_definition"].strip(), "design.unit_definition must describe the observational unit or state that it is unknown")
    require(design["structure"] != "unknown" or not design["confirmed"], "Unknown design cannot be confirmed")
    require(not design["confirmed"] or "unit" in fields, "Confirmed independent design requires an explicit fields.unit")
    require("measurement_units" in request and (request["measurement_units"] is None or isinstance(request["measurement_units"], str) and request["measurement_units"].strip()), "measurement_units must be an explicit nonempty string or null for unknown units")
    headers, rows = _read_source(raw)
    for role, column in fields.items():
        require(column in headers, f"Missing input column for {role}: {column}")
        require(all(row[headers.index(column)].strip() for row in rows), f"Empty mapped {role} values; prepare missing observations explicitly")
    value_i, group_i = headers.index(fields["value"]), headers.index(fields["group"])
    try:
        numeric = [float(row[value_i]) for row in rows]
    except ValueError:
        raise SpecError("Every value must be a raw finite number; no missing-token reinterpretation is applied") from None
    require(all(math.isfinite(v) for v in numeric), "Every value must be finite")
    groups = list(dict.fromkeys(row[group_i] for row in rows))
    order = request.get("order", {})
    _object(order, {"group"}, "order")
    if "group" in order:
        require(isinstance(order["group"], list) and all(isinstance(g, str) for g in order["group"]) and len(order["group"]) == len(groups) and set(order["group"]) == set(groups), "order.group must list every observed category exactly once")
        groups = order["group"]
    colors = request.get("colors")
    require(isinstance(colors, dict) and set(colors) == set(groups), "colors must map exactly every observed category")
    try:
        rgba = [core.mcolors.to_rgba(colors[g]) for g in groups]
    except (ValueError, TypeError):
        raise SpecError("colors must contain valid colors") from None
    require(all(c[3] == 1 for c in rgba) and len(set(rgba)) == len(groups), "Category colors must be opaque and distinct")
    if "unit" in fields:
        ui = headers.index(fields["unit"])
        keys = [(row[ui], row[group_i]) for row in rows]
        require(len(keys) == len(set(keys)), "Duplicate unit/group measurements: prepare technical repeats explicitly upstream; no aggregation is performed")
        ids = [row[ui] for row in rows]
        require(len(ids) == len(set(ids)), "Unit IDs repeated across groups require an explicit paired/repeated design and complete paired_plot.py input; pairing cannot be inferred or discarded")
    options = request.get("options", {})
    _object(options, {"value_scale", "value_limits", "point_layout", "point_alpha", "include_violin"}, "options")
    require(options.get("value_scale", "linear") in ("linear", "log"), "value_scale must be linear or log")
    require(options.get("point_layout", "jitter") in ("jitter", "beeswarm"), "point_layout must be jitter or beeswarm")
    point_alpha = _number(options.get("point_alpha", .65), "point_alpha", positive=True)
    require(point_alpha <= 1, "point_alpha must be greater than zero and at most one")
    require(isinstance(options.get("include_violin", False), bool), "include_violin must be an explicit boolean")
    scale = options.get("value_scale", "linear")
    require(scale != "log" or all(v > 0 for v in numeric), "Log display requires strictly positive values; no pseudocount is added")
    low, high = min(numeric), max(numeric)
    if "value_limits" in options:
        bounds = options["value_limits"]
        require(isinstance(bounds, list) and len(bounds) == 2, "value_limits requires two ascending bounds")
        a, b = [_number(v, "value_limits", positive=scale == "log") for v in bounds]
        require(a < b and a <= low and high <= b, "value_limits must contain every observation without clipping")
    elif scale == "log":
        pad = (math.log(high) - math.log(low)) * .08 if high != low else .15
        bounds = [math.exp(math.log(low) - pad), math.exp(math.log(high) + pad)]
    else:
        pad = (high - low) * .08 if high != low else max(1., abs(low) * .08)
        bounds = [low - pad, high + pad]
    require(all(math.isfinite(v) for v in bounds) and bounds[0] < bounds[1], "Displayed limits must be finite and ascending; supply explicit value_limits")
    if options.get("include_violin", False):
        for group in groups:
            unique = {v for row, v in zip(rows, numeric) if row[group_i] == group}
            require(len(unique) >= 5, f"Explicit violin requires at least 5 distinct raw values per group ({group!r} has {len(unique)}); use box and ECDF for sparse/constant data")
    layout = {"width_mm": 88, "height_mm": 70, "font": "Arial", "font_size_pt": 8, "line_width_pt": .6, "dpi": 300}
    _object(request.get("layout", {}), set(layout), "layout")
    layout.update(request.get("layout", {}))
    layout["auto_fit"] = True
    typography = request.get("typography", {})
    _object(typography, {"axis", "tick", "legend"}, "typography")
    labels = request.get("labels", {})
    _object(labels, {"value", "group"}, "labels")
    require(all(isinstance(v, str) for v in labels.values()), "labels must be strings")
    formats = request.get("formats", ["png", "pdf", "svg"])
    require(isinstance(formats, list) and all(isinstance(v, str) for v in formats) and "png" in formats and len(formats) == len(set(formats)) and set(formats) <= {"png", "pdf", "svg", "tiff"}, "formats must include png and contain only unique png/pdf/svg/tiff names")
    common = {"fields": deepcopy(fields), "colors": deepcopy(colors), "order": {"group": list(groups)}, "layout": layout, "typography": deepcopy(typography), "formats": list(formats)}
    # Core validation also resolves font availability and shared positive sizes.
    core.setup(common)
    measurement = labels.get("value", fields["value"])
    measurement += f" ({request['measurement_units']})" if request["measurement_units"] is not None else " (units unknown)"
    distribution = {**deepcopy(common), "chart": "distribution", "labels": {"x": measurement, "y": labels.get("group", fields["group"])}, "options": {"kind": "box", "orientation": "horizontal", "x_scale": scale, "x_limits": list(bounds), "point_layout": options.get("point_layout", "jitter"), "point_area_pt2": 9, "alpha": point_alpha}, "seed": 0}
    empirical = {**deepcopy(common), "chart": "ecdf", "labels": {"x": measurement, "y": "Cumulative fraction"}, "options": {"x_scale": scale, "x_limits": list(bounds), "curve_line_width_pt": .8}, "legends": {"categorical": {"position": "bottom"}}}
    core.validate_spec(distribution)
    ecdf.validate_spec(empirical)
    specs = [("box-points", distribution), ("ecdf", empirical)]
    if options.get("include_violin", False):
        violin = deepcopy(distribution)
        violin["options"]["kind"] = "violin"
        specs.append(("violin-points", violin))
    return headers, rows, specs


def audit_distribution_artists(raw, spec, fig):
    """Check actual rendered point offsets and box summaries against raw CSV."""
    headers, rows = _read_source(raw)
    fields, groups = spec["fields"], spec["order"]["group"]
    vi, gi = headers.index(fields["value"]), headers.index(fields["group"])
    from matplotlib.collections import PathCollection
    points = [p for p in fig.axes[0].collections if isinstance(p, PathCollection)]
    issues, counts, actual_facecolors = [], {}, {}
    numeric_values_unchanged = True
    intended_alpha = spec["options"]["alpha"]
    if len(points) != len(groups):
        issues.append("actual point collections do not match groups")
    for index, (group, artist) in enumerate(zip(groups, points)):
        expected = core.np.asarray([float(r[vi]) for r in rows if r[gi] == group])
        actual = core.np.asarray(artist.get_offsets(), dtype=float)
        counts[group] = len(actual)
        if actual.shape != (len(expected), 2) or not core.np.array_equal(actual[:, 0], expected):
            numeric_values_unchanged = False
            issues.append(f"actual observation coordinates differ for {group}")
        facecolors = artist.get_facecolors()
        expected_rgba = core.mcolors.to_rgba(spec["colors"][group], alpha=intended_alpha)
        actual_facecolors[group] = facecolors.tolist()
        if not len(facecolors) or not core.np.allclose(facecolors, expected_rgba):
            issues.append(f"actual observation color/alpha differs for {group}")
        if artist.get_alpha() is None or not core.np.allclose(artist.get_alpha(), intended_alpha):
            issues.append(f"actual observation alpha differs for {group}")
        if spec["options"]["kind"] == "box":
            quartiles = core.np.quantile(expected, [.25, .5, .75], method="linear")
            patches = fig.axes[0].patches
            if len(patches) <= index or not core.np.allclose([patches[index].get_path().vertices[:, 0].min(), patches[index].get_path().vertices[:, 0].max()], quartiles[[0, 2]]):
                issues.append(f"actual box quartiles differ for {group}")
            median = [line for line in fig.axes[0].lines if len(line.get_xdata()) == 2 and core.np.allclose(line.get_xdata(), [quartiles[1], quartiles[1]]) and core.np.allclose(line.get_ydata(), [index - .25, index + .25])]
            if len(median) != 1:
                issues.append(f"actual median differs for {group}")
    return {"status": "pass" if not issues else "needs_revision", "source_rows": len(rows), "audited_observations": sum(counts.values()), "group_counts": counts, "intended_point_alpha": intended_alpha, "actual_point_facecolors": actual_facecolors, "numeric_values_unchanged": numeric_values_unchanged, "tests_performed": False, "experimental_independence_inferred": False, "issues": issues}


def _render_distribution(source, raw, spec, out, spec_path):
    """Use existing core geometry/export while auditing the exported figure."""
    data = core.prepare(source, spec)
    layout, typography, rc = core.setup(spec)
    result = core.statistics(data, spec)
    fig, before = None, set(core.plt.get_fignums())
    with core.plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        try:
            fig, colors = core.draw(data, spec, layout, typography, result)
            fig.canvas.draw()
            audit = audit_distribution_artists(raw, spec, fig)
            clipped = ecdf._clipped_text(fig)
            overlaps, oblique = core.check_tick_label_overlap(fig, fig.canvas.get_renderer())
            legends = fig._easyviz_legend_layout.validate()
            fitted = getattr(fig, "_easyviz_auto_layout", None)
            point_layout = fig._easyviz_point_layout
            fig._easyviz_data_file, fig._easyviz_spec_file = source.resolve(), spec_path.resolve()
            fig._easyviz_source_script, fig._easyviz_track = Path(__file__).resolve(), "create"
            exports = core.export(fig, out, spec, layout)
            missing = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            passed = not clipped and not overlaps and not missing and audit["status"] == legends["status"] == "pass" and (not fitted or fitted["status"] == "pass") and point_layout["status"] != "needs_revision"
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "input_rows": len(data), "input_sha256": _hash(source), "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "exports": exports, "clipped_text": clipped, "overlapping_tick_labels": overlaps, "unchecked_oblique_tick_labels": oblique, "missing_glyphs": missing, "source_to_artist_audit": audit, "legend_layout": legends, "auto_layout": fitted, "point_layout": point_layout, "visual_review_required": True}
            settings = {**deepcopy(spec), "layout": layout, "typography": typography, "resolved_colors": colors, "input_file": str(source.resolve()), "input_sha256": _hash(source), "spec_file": str(spec_path.resolve()), "spec_file_sha256": _hash(spec_path), "track": "create", "renderer": {"version": VERSION, "sha256": _hash(Path(__file__)), "helper_sha256": {name: _hash(Path(__file__).with_name(name)) for name in HELPERS}}, "point_layout": point_layout, "axis": {"x_scale": fig.axes[0].get_xscale(), "x_limits": list(map(float, fig.axes[0].get_xlim()))}, "runtime": {"python": platform.python_version(), **{name: package_version(name) for name in ("matplotlib", "numpy", "pandas", "scipy", "Pillow", "pypdf")}}}
            headers, rows = _read_source(raw)
            data["_easyviz_source_row"] = range(1, len(rows) + 1)
            data["_easyviz_source_value_text"] = [row[headers.index(spec["fields"]["value"])] for row in rows]
            data.to_csv(out / "plotting-data.csv", index=False)
            result.update(tests_performed=False, confidence_intervals_computed=False, experimental_independence_inferred=False,
                          smoothing_applied=spec["options"]["kind"] == "violin", observation_counts=audit["group_counts"])
            _json(out / "settings.json", settings)
            _json(out / "stats.json", result)
            _json(out / "qa.json", qa)
            require(passed, "Distribution source or canvas QA needs revision; inspect qa.json and panel.png")
            return qa
        finally:
            if fig is not None:
                core.plt.close(fig)
            for number in set(core.plt.get_fignums()) - before:
                core.plt.close(number)


def _description(choice):
    if choice == "box-points":
        return ("Compare group medians, spread and all individual measurements", "Box: median and 25th/75th percentiles; whiskers reach observed values within 1.5 IQR. Every observation is also a point.", ["Quartiles and whiskers describe source observations, not confidence intervals.", "Box summaries can obscure multimodality; inspect every point and the ECDF."])
    if choice == "ecdf":
        return ("Compare the full observed distribution, tails and fraction at or below a value", "Right-continuous F(x)=count(value <= x)/group observation count; all ties contribute their full jump. Horizontal tails extend only for display.", ["Curve fractions use each group's own row-count denominator.", "Marginal distributions do not encode within-unit changes or establish independence.", "No density smoothing, fitted distribution or confidence band."])
    return ("Explore broad distribution shape while retaining all measurements", "Gaussian KDE with Scott bandwidth, 100 evaluation points; each violin's width is independently normalized. Every observation is also a point.", ["Density shape depends on smoothing bandwidth and can imply unsupported modes.", "Violin widths are not sample counts or confidence intervals.", "Five distinct values is a conservative eligibility guard, not scientific validation of a density estimate."])


def _caption(choice, request, rows, source_hash):
    task, definition, _ = _description(choice)
    fields = request["fields"]
    unit = request["design"]["unit_definition"]
    units = request["measurement_units"] or "unknown measurement units"
    text = f"Descriptive distribution of {fields['value']} by {fields['group']} ({units}). {definition} Observational unit: {unit}. All {len(rows)} supplied observation rows are retained with equal weight; no aggregation or exclusion is applied."
    if choice != "ecdf":
        policy = request.get("options", {}).get("point_layout", "jitter")
        text += " Categorical point offsets are deterministic jitter and carry no numerical meaning; points may overlap at the final size." if policy == "jitter" else " Beeswarm offsets affect only category position; measurement values are unchanged."
        text += f" Raw points use opacity {request.get('options', {}).get('point_alpha', .65):g}; this display setting changes neither measurement values nor category color assignments."
    if request["design"]["structure"] == "unknown" or not request["design"]["confirmed"]:
        text += " Experimental independence is unconfirmed; group row counts are descriptive observations and are not established independent sample sizes."
    if request["measurement_units"] is None:
        text += " Measurement units are unconfirmed; axis values are shown as supplied without a physical interpretation."
    text += f" No hypothesis test, confidence interval or effect inference is performed. Source snapshot SHA-256: {source_hash}.\n"
    return text


def _bindings(directory, root):
    return [{"path": str(path.relative_to(root)), "sha256": _hash(path)} for path in sorted(directory.iterdir()) if path.is_file()]


def preview(data_path, request_path, out):
    """Create a fresh, source-bound set of real previews and unresolved choices."""
    data_path, request_path, out = Path(data_path).resolve(), Path(request_path).resolve(), Path(out)
    require(not out.exists() and not out.is_symlink(), f"Output already exists; choose a fresh directory: {out}")
    raw, request_raw = data_path.read_bytes(), request_path.read_bytes()
    try:
        request = json.loads(request_raw)
    except (ValueError, UnicodeError) as exc:
        raise SpecError(f"Invalid request JSON: {exc}") from None
    headers, rows, specs = prepare_request(raw, request)
    # Validate both recipe contracts on the original before creating any output.
    for _, spec in specs:
        (ecdf.prepare if spec["chart"] == "ecdf" else core.prepare)(data_path, spec)
    source_hash, request_hash = _hash_bytes(raw), _hash_bytes(request_raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()  # Atomic fresh-directory claim, including a competing writer.
    manifest = {"version": VERSION, "status": "in_progress", "valid_outputs": False, "track": "create", "source_binding": {"original_path": str(data_path), "snapshot": "source.csv", "sha256": source_hash, "rows": len(rows)}, "request_binding": {"original_path": str(request_path), "snapshot": "request.json", "sha256": request_hash}, "fields": deepcopy(request["fields"]), "design": deepcopy(request["design"]), "measurement_units": request["measurement_units"], "shared_settings": {key: deepcopy(specs[0][1][key]) for key in ("layout", "typography", "colors", "order", "formats")}, "value_axis": {"scale": specs[0][1]["options"]["x_scale"], "limits": specs[0][1]["options"]["x_limits"]}, "choices": [], "selection": {"chosen_choice": None, "automatic_winner": False}, "visual_review_required": True, "helper_sha256": {name: _hash(Path(__file__).with_name(name)) for name in ("preview_choices.py", *HELPERS)}}
    _json(out / "manifest.json", manifest)
    _json(out / "qa.json", {"status": "in_progress", "valid_outputs": False})
    source = out / "source.csv"
    source.write_bytes(raw)
    (out / "request.json").write_bytes(request_raw)
    with (out / "observation-trace.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([*headers, "_easyviz_source_row", "_easyviz_source_value_text"])
        writer.writerows([*row, index, row[headers.index(request["fields"]["value"])]] for index, row in enumerate(rows, 1))
    (out / "visual-review.md").write_text("Visual review pending. Inspect every panel.png at the declared final size and its vector exports. Compare the stated reading tasks, label/mark crowding, curve distinguishability and point overlap. Record observations and a scientifically justified choice here; automated QA does not select a winner.\n", encoding="utf-8")
    try:
        resolved = []
        for choice, spec in specs:
            directory = out / choice
            directory.mkdir()
            spec_path = directory / "spec.json"
            _json(spec_path, spec)
            task, definition, limitations = _description(choice)
            if request.get("options", {}).get("point_layout", "jitter") == "jitter" and choice != "ecdf":
                limitations.append("Deterministic categorical jitter retains every point but may overlap; final-size visual review is required.")
            if not request["design"]["confirmed"]:
                limitations.append("Independent sampling is unconfirmed; rows are descriptive observation counts.")
            if request["measurement_units"] is None:
                limitations.append("Measurement units are unknown; values have only their supplied descriptive scale.")
            record = {"id": choice, "reading_task": task, "definition": definition, "limitations": limitations, "spec": f"{choice}/spec.json", "caption": f"{choice}/caption.md", "status": "in_progress"}
            manifest["choices"].append(record)
            _json(out / "manifest.json", manifest)
            (directory / "caption.md").write_text(_caption(choice, request, rows, source_hash), encoding="utf-8")
            _json(directory / "qa.json", {"status": "in_progress", "valid_outputs": False})
            qa = ecdf.render(source, spec, directory, spec_path=spec_path) if choice == "ecdf" else _render_distribution(source, raw, spec, directory, spec_path)
            record.update(status=qa["status"], valid_outputs=qa["valid_outputs"], files=_bindings(directory, out))
            settings = json.loads((directory / "settings.json").read_text(encoding="utf-8"))
            resolved.append({"choice": choice, "width_mm": settings["layout"]["width_mm"], "height_mm": settings["layout"]["height_mm"], "actual_font": settings["layout"]["actual_font"], "axis_font_pt": settings["typography"]["axis"], "tick_font_pt": settings["typography"]["tick"], "legend_font_pt": settings["typography"]["legend"], "colors": settings["resolved_colors"], "input_sha256": settings["input_sha256"], "value_scale": settings["axis"]["x_scale"], "value_limits": settings["axis"]["x_limits"]})
        equal = all({k: v for k, v in item.items() if k != "choice"} == {k: v for k, v in resolved[0].items() if k != "choice"} for item in resolved)
        unchanged = _hash(data_path) == _hash(source) == source_hash and _hash(request_path) == _hash(out / "request.json") == request_hash
        passed = equal and unchanged and all(record["valid_outputs"] for record in manifest["choices"])
        qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "source_unchanged": unchanged, "shared_settings_identical": equal, "resolved_choices": resolved, "tests_performed": False, "aggregation_performed": False, "excluded_rows": 0, "experimental_independence_inferred": False, "visual_review_required": True, "automatic_winner": False}
        _json(out / "qa.json", qa)
        manifest.update(status=qa["status"], valid_outputs=passed, common_files=[{"path": name, "sha256": _hash(out / name)} for name in ("source.csv", "request.json", "observation-trace.csv", "qa.json", "visual-review.md")])
        _json(out / "manifest.json", manifest)
        require(passed, "Shared settings or source integrity needs revision; inspect qa.json")
        return manifest
    except Exception as exc:
        manifest.update(status="failed", valid_outputs=False, error=str(exc))
        for record in manifest["choices"]:
            if record["status"] == "in_progress":
                record.update(status="failed", valid_outputs=False)
                directory = out / record["id"]
                child_qa = json.loads((directory / "qa.json").read_text())
                child_qa.update(valid_outputs=False, error=str(exc))
                if child_qa.get("status") == "in_progress":
                    child_qa["status"] = "failed"
                _json(directory / "qa.json", child_qa)
                record["files"] = _bindings(directory, out)
        _json(out / "manifest.json", manifest)
        current = json.loads((out / "qa.json").read_text())
        current.update(status="failed", valid_outputs=False, error=str(exc))
        _json(out / "qa.json", current)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-contract", action="store_true")
    parser.add_argument("--data", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.describe_contract:
        if any((args.data, args.request, args.out)):
            parser.error("--describe-contract does not accept rendering arguments")
        print(json.dumps(CONTRACT, indent=2, ensure_ascii=False))
        return
    if not all((args.data, args.request, args.out)):
        parser.error("--data, --request and a fresh --out directory are required")
    try:
        result = preview(args.data, args.request, args.out)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"EasyViz: {exc}\n")
    print(json.dumps({"status": result["status"], "output": str(args.out.resolve()), "manifest": str((args.out / "manifest.json").resolve()), "choices": [r["id"] for r in result["choices"]], "visual_review_required": True, "automatic_winner": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
