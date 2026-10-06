#!/usr/bin/env python3
"""Render field-mapped matrices with keyed strips, marginals and supplied trees.

Run --describe-spec for the contract. No clustering is performed. Custom
scripts may reuse prepare(), draw() and aligned_layers.AlignedFrame.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
import io
import math
from pathlib import Path
import warnings

_loader = importlib.util.spec_from_file_location("easyviz_matrix_core", Path(__file__).with_name("render.py"))
core = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(core)
_aligned_loader = importlib.util.spec_from_file_location("easyviz_aligned_layers", Path(__file__).with_name("aligned_layers.py"))
aligned_layers = importlib.util.module_from_spec(_aligned_loader)
_aligned_loader.loader.exec_module(aligned_layers)
from matplotlib.colors import to_rgba
from matplotlib.patches import Rectangle
from matplotlib.cm import ScalarMappable

plt, np, pd = core.plt, core.np, core.pd
SpecError, require, write_json = core.SpecError, core.require, core.write_json
VERSION = "0.1.0"
SPEC_KEYS = {"chart", "fields", "order", "options", "metadata", "marginals", "dendrograms", "tracks", "layout", "typography", "labels", "colormap", "formats", "legends"}
OPTIONS = {"color_limits", "color_center", "missing_cells", "x_rotation", "annotate_values", "value_format"}
TRACK_KEYS = {"gap_mm", "strip_mm", "marginal_mm", "dendrogram_mm", "padding_mm", "matrix_mm"}
STATE_COLORS = {"unmeasured": "#D8D8D8", "unsupplied": "#F5F5F5"}
STATE_HATCHES = {"unmeasured": "xx", "unsupplied": "++"}
SCHEMA = {
    "chart": "annotated_matrix",
    "fields": {"row": "literal row ID", "column": "literal column ID", "value": "finite measurement", "state": "optional observed|unmeasured"},
    "order": {"row": ["every supplied row ID exactly once"], "column": ["every supplied column ID exactly once"]},
    "options": {"missing_cells": "error (default)|unsupplied", "color_limits": ["minimum", "maximum"], "color_center": "optional", "x_rotation": "0 or 90", "annotate_values": False, "value_format": ".2g"},
    "metadata": {"row": {"id": "row ID field", "tracks": [{"field": "categorical field", "label": "guide label", "colors": {"literal category": "color"}}]}, "column": "same contract; optional"},
    "marginals": {"row": {"statistic": "mean|sum", "missing": "error|omit (required)", "label": "axis label", "color": "optional color", "limits": "optional numeric [low,high] including zero and all bars"}, "column": "same contract; optional"},
    "dendrograms": {"row": {"label": "supplied height units/meaning"}, "column": "same contract; optional; a supplied linkage file is required"},
    "tracks": {"gap_mm": 2, "strip_mm": 2, "marginal_mm": 12, "dendrogram_mm": 14, "padding_mm": 2, "matrix_mm": "optional explicit [left,bottom,width,height]; incompatible with auto_fit=true"},
    "layout": {"width_mm": 88, "height_mm": 88, "font": "Arial", "font_size_pt": 8, "dpi": 300, "auto_fit": True},
    "labels": {"x": "column meaning", "y": "row meaning", "color": "value meaning and units"},
    "colormap": "registered continuous palette, Matplotlib map, or color list",
    "formats": ["pdf", "svg", "png", "tiff"],
    "linkage_file": {"leaf_ids": ["IDs indexed by linkage leaves"], "linkage": [["left node", "right node", "height", "recursive leaf count"]]},
    "semantics": ["IDs are literal strings, including 001, NA and null. Duplicate pairs are errors, never aggregated.", "Observed zero is a numeric cell; unmeasured requires an explicit state and exactly blank value; absent coordinates remain unsupplied.", "All metadata files join one-to-one on exact IDs with complete coverage; each track supplies stable category colors.", "Marginals use the displayed grid only; omit excludes both missing states, records denominators and rejects all-missing groups. Sum does not assume missing values are zero.", "Linkage must be one complete ordered binary tree; parent heights cannot be below children. No inversion repair, child swaps or clustering. Singleton/zero-height trees are supported.", "Measured layout moves aligned axes together and preserves final fonts and canvas; an infeasible panel fails QA.", "No titles, narrative, clustering or upstream analyses are accepted by this focused recipe."],
}


def _object(value, allowed, name):
    require(isinstance(value, dict), f"{name} must be an object")
    require(not set(value) - allowed, f"Unknown {name} keys: {sorted(set(value) - allowed)}")


def _number(value, name, *, positive=False):
    require(isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value), f"{name} must be a finite JSON number")
    require(not positive or value > 0, f"{name} must be positive")
    return float(value)


def validate_spec(spec):
    _object(spec, SPEC_KEYS, "spec")
    require(spec.get("chart", "annotated_matrix") == "annotated_matrix", "chart must be annotated_matrix")
    fields = spec.get("fields", {})
    _object(fields, {"row", "column", "value", "state"}, "fields")
    require({"row", "column", "value"} <= set(fields), "fields requires row, column and value")
    require(all(isinstance(v, str) and v.strip() for v in fields.values()), "fields must map roles to nonempty column names")
    require(len(set(fields.values())) == len(fields), "Each matrix role must map to a distinct field")
    order = spec.get("order", {})
    _object(order, {"row", "column"}, "order")
    require(set(order) == {"row", "column"}, "Explicit order.row and order.column are required")
    for role in order:
        aligned_layers.literal_order(order[role], f"order.{role}")
    options = spec.get("options", {})
    _object(options, OPTIONS, "options")
    require(options.get("missing_cells", "error") in ("error", "unsupplied"), "missing_cells must be error or unsupplied; absent rows never establish unmeasured status")
    require(options.get("x_rotation", 90) in (0, 90) and not isinstance(options.get("x_rotation", 90), bool), "x_rotation must be 0 or 90")
    require(isinstance(options.get("annotate_values", False), bool), "annotate_values must be boolean")
    require(isinstance(options.get("value_format", ".2g"), str), "value_format must be a format string")
    try:
        format(1.0, options.get("value_format", ".2g"))
    except (ValueError, TypeError):
        raise SpecError("Invalid value_format") from None
    if "color_limits" in options:
        limits = options["color_limits"]
        require(isinstance(limits, list) and len(limits) == 2, "color_limits must be two ascending finite numbers")
        low, high = [_number(v, "color_limits") for v in limits]
        require(low <= high, "color_limits must ascend")
    if "color_center" in options:
        _number(options["color_center"], "color_center")
    metadata = spec.get("metadata", {})
    _object(metadata, {"row", "column"}, "metadata")
    for axis, config in metadata.items():
        _object(config, {"id", "tracks"}, f"metadata.{axis}")
        require(isinstance(config.get("id"), str) and config["id"].strip(), f"metadata.{axis}.id must name a field")
        tracks = config.get("tracks")
        require(isinstance(tracks, list) and tracks, f"metadata.{axis}.tracks must be nonempty")
        fields_seen = set()
        for index, track in enumerate(tracks):
            _object(track, {"field", "label", "colors"}, f"metadata.{axis}.tracks[{index}]")
            field = track.get("field")
            require(isinstance(field, str) and field.strip() and field != config["id"] and field not in fields_seen, "Metadata track fields must be distinct and differ from the ID field")
            fields_seen.add(field)
            require(isinstance(track.get("label"), str) and track["label"].strip(), "Metadata track requires a nonempty guide label")
            try:
                core.figure_profile._colors(track.get("colors"), f"metadata.{axis}.tracks[{index}].colors")
            except core.figure_profile.ConfigurationError as exc:
                raise SpecError(str(exc)) from None
    marginals = spec.get("marginals", {})
    _object(marginals, {"row", "column"}, "marginals")
    for axis, config in marginals.items():
        _object(config, {"statistic", "missing", "label", "color", "limits"}, f"marginals.{axis}")
        require(config.get("statistic") in ("mean", "sum"), "Marginal statistic must be mean or sum")
        require(config.get("missing") in ("error", "omit"), "Marginal missing rule must be explicit: error or omit")
        require(isinstance(config.get("label"), str), "Marginal label must be supplied as a string")
        require(core.mcolors.is_color_like(config.get("color", "#687983")), "Invalid marginal color")
        if "limits" in config:
            require(isinstance(config["limits"], list) and len(config["limits"]) == 2, "Marginal limits must be [low,high]")
            low, high = [_number(v, "marginal limits") for v in config["limits"]]
            require(low < high, "Marginal limits must strictly ascend")
    trees = spec.get("dendrograms", {})
    _object(trees, {"row", "column"}, "dendrograms")
    for axis, config in trees.items():
        _object(config, {"label"}, f"dendrograms.{axis}")
        require(isinstance(config.get("label"), str), "Dendrogram requires the supplied height meaning/units as label")
    tracks = spec.get("tracks", {})
    _object(tracks, TRACK_KEYS, "tracks")
    for key, value in tracks.items():
        if key == "matrix_mm":
            require(isinstance(value, list) and len(value) == 4, "tracks.matrix_mm must be [left,bottom,width,height]")
            for v in value: _number(v, "matrix_mm")
            require(min(value[2:]) > 0, "matrix_mm width and height must be positive")
        else:
            require(_number(value, key) >= 0 if key == "gap_mm" else _number(value, key) > 0, f"{key} must be {'nonnegative' if key == 'gap_mm' else 'positive'}")
    labels = spec.get("labels", {})
    _object(labels, {"x", "y", "color"}, "labels")
    require(all(isinstance(v, str) for v in labels.values()), "labels must contain strings")
    require(isinstance(spec.get("legends", {}), dict), "legends must be an object")
    formats = spec.get("formats", ["svg"])
    require(isinstance(formats, list) and formats and all(isinstance(v, str) for v in formats) and len(set(formats)) == len(formats) and set(formats) <= {"pdf", "svg", "png", "tiff"}, "Supported unique formats: pdf, svg, png, tiff")
    try:
        core.figure_profile.validate_layout(spec.get("layout", {}))
        core.figure_profile.validate_typography(spec.get("typography", {}))
    except core.figure_profile.ConfigurationError as exc:
        raise SpecError(str(exc)) from None
    automatic = spec.get("layout", {}).get("auto_fit", "margins" not in spec.get("layout", {}) and "matrix_mm" not in tracks)
    require(not automatic or "matrix_mm" not in tracks, "tracks.matrix_mm conflicts with layout.auto_fit=true")
    require(not ("matrix_mm" in tracks and "margins" in spec.get("layout", {})), "matrix_mm and layout.margins are conflicting geometry choices")


def _csv(path):
    path = Path(path)
    payload = path.read_bytes()
    with io.StringIO(payload.decode("utf-8-sig"), newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        require(header and all(h.strip() for h in header) and len(set(header)) == len(header), "CSV headers must be nonempty and unique before parsing")
        rows = list(reader)
    require(rows and all(len(r) == len(header) for r in rows), "CSV requires nonempty records with exact header width")
    require(not any(h.startswith("_easyviz_") for h in header), "Input columns starting _easyviz_ are reserved")
    data = pd.DataFrame(rows, columns=header)
    data.attrs["source_sha256"] = hashlib.sha256(payload).hexdigest()
    return data


def prepare(data_path, spec, *, row_metadata=None, column_metadata=None, row_linkage=None, column_linkage=None):
    """Validate literal joins, preserve source rows and expand only data states."""
    validate_spec(spec)
    data = _csv(data_path)
    f = spec["fields"]
    require(set(f.values()) <= set(data.columns), "A mapped matrix field is absent from the input")
    for role in ("row", "column"):
        values = data[f[role]]
        require(values.str.strip().ne("").all(), f"Empty {role} IDs are unsupported")
        require(set(values) == set(spec["order"][role]), f"order.{role} must cover every supplied ID exactly once, with no extras")
    require(not data.duplicated([f["row"], f["column"]]).any(), "Duplicate row/column pairs; aggregate explicitly before rendering")
    states = data[f["state"]] if "state" in f else pd.Series("observed", index=data.index)
    require(states.isin(["observed", "unmeasured"]).all(), "Matrix state must be observed or unmeasured")
    observed = states.eq("observed")
    require(data.loc[~observed, f["value"]].eq("").all(), "Unmeasured cells require an exactly blank value; zero remains observed")
    require(data.loc[observed, f["value"]].str.strip().ne("").all(), "Observed cells need numeric values; blank does not establish unmeasured")
    try:
        numeric = pd.to_numeric(data.loc[observed, f["value"]], errors="raise").to_numpy(float)
    except (ValueError, TypeError):
        raise SpecError("Observed matrix values must be numeric") from None
    require(np.isfinite(numeric).all(), "Observed matrix values must be finite")
    require(len(numeric) > 0, "At least one observed value is required for a continuous matrix scale")
    data["_easyviz_source_row"] = np.arange(1, len(data) + 1)
    data["_easyviz_state"] = states
    data["_easyviz_value"] = np.nan
    data.loc[observed, "_easyviz_value"] = numeric
    rows, columns = spec["order"]["row"], spec["order"]["column"]
    require(len(rows) * len(columns) <= 10000, "This per-cell semantic recipe supports at most 10000 cells; use an explicitly reviewed custom raster implementation for a larger matrix")
    lookup = {(r[f["row"]], r[f["column"]]): r for _, r in data.iterrows()}
    cells = []
    for y, row in enumerate(rows):
        for x, column in enumerate(columns):
            source = lookup.get((row, column))
            require(source is not None or spec.get("options", {}).get("missing_cells", "error") == "unsupplied", "Matrix has absent coordinates; declare missing_cells=unsupplied or supply them explicitly")
            cells.append({"row": row, "column": column, "row_index": y, "column_index": x,
                          "state": source["_easyviz_state"] if source is not None else "unsupplied",
                          "value": float(source["_easyviz_value"]) if source is not None and source["_easyviz_state"] == "observed" else None,
                          "source_row": int(source["_easyviz_source_row"]) if source is not None else None})
    metadata, trees, inputs = {}, {}, {"matrix": Path(data_path).resolve()}
    input_hashes = {"matrix": data.attrs["source_sha256"]}
    for axis, metadata_path, linkage_path in (("row", row_metadata, row_linkage), ("column", column_metadata, column_linkage)):
        config = spec.get("metadata", {}).get(axis)
        require((config is not None) == (metadata_path is not None), f"metadata.{axis} configuration and --{axis}-metadata file must be supplied together")
        if config:
            table = _csv(metadata_path)
            require(config["id"] in table, f"Missing metadata ID field: {config['id']}")
            identifiers = table[config["id"]]
            require(identifiers.str.strip().ne("").all() and identifiers.is_unique, "Metadata IDs must be nonempty and unique")
            require(set(identifiers) == set(spec["order"][axis]), f"{axis} metadata must have exact one-to-one displayed ID coverage")
            ordered = table.set_index(config["id"]).loc[spec["order"][axis]]
            metadata[axis] = []
            for index, track in enumerate(config["tracks"]):
                require(track["field"] in ordered, f"Missing metadata field: {track['field']}")
                values = ordered[track["field"]].tolist()
                require(all(v.strip() for v in values), "Metadata categories must be explicit nonempty strings")
                require(set(values) <= set(track["colors"]), "Metadata colors must cover every literal category; colors never cycle")
                metadata[axis].append({**deepcopy(track), "index": index, "values": values})
            inputs[f"{axis}_metadata"] = Path(metadata_path).resolve()
            input_hashes[f"{axis}_metadata"] = table.attrs["source_sha256"]
        tree_config = spec.get("dendrograms", {}).get(axis)
        require((tree_config is not None) == (linkage_path is not None), f"dendrograms.{axis} configuration and --{axis}-linkage file must be supplied together")
        if linkage_path:
            payload = Path(linkage_path).read_bytes()
            trees[axis] = aligned_layers.supplied_linkage(json.loads(payload.decode("utf-8")), spec["order"][axis])
            inputs[f"{axis}_linkage"] = Path(linkage_path).resolve()
            input_hashes[f"{axis}_linkage"] = hashlib.sha256(payload).hexdigest()
    prepared = {"data": data, "cells": cells, "rows": list(rows), "columns": list(columns), "metadata": metadata, "trees": trees, "inputs": inputs, "input_hashes": input_hashes}
    prepared["marginals"] = _marginals(prepared, spec)
    return prepared


def _marginals(prepared, spec):
    result = {}
    for axis, config in spec.get("marginals", {}).items():
        result[axis] = []
        for identifier in prepared["rows" if axis == "row" else "columns"]:
            cells = [c for c in prepared["cells"] if c[axis] == identifier]
            values = [c["value"] for c in cells if c["state"] == "observed"]
            require(config["missing"] != "error" or len(values) == len(cells), f"{axis} marginal has missing cells; missing=error forbids an incomplete grid")
            require(values, f"{axis} marginal has an all-missing group: {identifier!r}; no value is inferred")
            try:
                value = math.fsum(v / len(values) for v in values) if config["statistic"] == "mean" else math.fsum(values)
            except OverflowError:
                raise SpecError("Marginal aggregation overflowed; no finite result can be plotted") from None
            require(math.isfinite(value), "Marginal aggregation must remain finite")
            result[axis].append({"id": identifier, "value": value, "statistic": config["statistic"], "missing_rule": config["missing"],
                                 "observed_count": len(values), "grid_count": len(cells),
                                 "unmeasured_count": sum(c["state"] == "unmeasured" for c in cells),
                                 "unsupplied_count": sum(c["state"] == "unsupplied" for c in cells)})
        if "limits" in config:
            values = [r["value"] for r in result[axis]] + [0]
            require(config["limits"][0] <= min(values) and max(values) <= config["limits"][1], "Marginal limits would clip bars or their zero baseline")
    return result


class _CompoundGuides(core.legend_layout.LegendLayout):
    def __init__(self, frame, typography, config):
        super().__init__(frame.fig, frame.main, typography, config)
        self.frame = frame

    def _tight_plot(self):
        return self.frame.tight_bbox()

    def _categorical_or_size(self, request, cfg, position, ncol):
        entry = super()._categorical_or_size(request, cfg, position, ncol)
        for handle, hatch in zip(entry["artist"].legend_handles, request.get("hatches", [])):
            handle.set_hatch(hatch)
            if hatch:
                handle.set_edgecolor("#777777")
                handle.set_linewidth(0)
        return entry


def _register(fig, artist, role, label, key, source_keys=None, spec_paths=None, editable=None):
    return core.figure_elements.register(fig, artist, role, label, key=key, source_keys=source_keys, spec_paths=spec_paths, editable=editable)


def _clean_track(ax, axis, *, numeric=False):
    if not numeric:
        # Retain a visible rectangular axes patch for SVG alignment evidence.
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)
    elif axis == "row":
        ax.tick_params(axis="y", left=False, labelleft=False)
        ax.xaxis.set_major_locator(core.matplotlib.ticker.MaxNLocator(nbins=3))
        ax.spines[["left", "right", "top"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="x", linewidth=.35, color="#E4E4E4", zorder=0)
    else:
        ax.tick_params(axis="x", bottom=False, labelbottom=False)
        ax.yaxis.set_major_locator(core.matplotlib.ticker.MaxNLocator(nbins=3))
        ax.spines[["bottom", "right", "top"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="y", linewidth=.35, color="#E4E4E4", zorder=0)


def draw(prepared, spec, layout, typography):
    """Draw all layers, then jointly fit their actual text and guide envelopes."""
    settings = {"gap_mm": 2., "strip_mm": 2., "marginal_mm": 12., "dendrogram_mm": 14., "padding_mm": 2., **spec.get("tracks", {})}
    fig = plt.figure(figsize=(layout["width_mm"] / 25.4, layout["height_mm"] / 25.4), dpi=layout["dpi"])
    margins = layout["margins"]
    rect = settings.get("matrix_mm", [layout["width_mm"] * margins["left"], layout["height_mm"] * margins["bottom"], layout["width_mm"] * (margins["right"] - margins["left"]), layout["height_mm"] * (margins["top"] - margins["bottom"])])
    frame = aligned_layers.AlignedFrame(fig, prepared["rows"], prepared["columns"], rect, gap_mm=settings["gap_mm"])
    fig._easyviz_aligned_frame = frame
    fig._easyviz_matrix_artists = {"cells": [], "metadata": [], "marginals": [], "trees": []}
    ax, artists = frame.main, fig._easyviz_matrix_artists
    observed = [c["value"] for c in prepared["cells"] if c["state"] == "observed"]
    cmap, norm = core.continuous(spec, observed)
    mappable = ScalarMappable(norm=norm, cmap=cmap)
    fig._easyviz_matrix_scale = mappable
    for cell in prepared["cells"]:
        state = cell["state"]
        color = mappable.to_rgba(cell["value"]) if state == "observed" else STATE_COLORS[state]
        patch = Rectangle((cell["column_index"] - .5, cell["row_index"] - .5), 1, 1, facecolor=color,
                          edgecolor="none" if state == "observed" else "#777777", linewidth=0,
                          hatch=None if state == "observed" else STATE_HATCHES[state], zorder=2)
        ax.add_patch(patch)
        _register(fig, patch, "matrix-cell", f"{cell['row']} × {cell['column']}: {state}", [cell["row"], cell["column"]],
                  [{"row": cell["row"], "column": cell["column"], "source_row": cell["source_row"]}],
                  ["/fields/value", "/options/color_limits"], ["color"])
        annotation = None
        if state == "observed" and spec.get("options", {}).get("annotate_values", False):
            annotation = ax.text(cell["column_index"], cell["row_index"], format(cell["value"], spec.get("options", {}).get("value_format", ".2g")), ha="center", va="center", fontsize=typography["annotation"], zorder=3)
            _register(fig, annotation, "cell-annotation", annotation.get_text(), [cell["row"], cell["column"]], [{"row": cell["row"], "column": cell["column"]}], ["/options/value_format"], ["text"])
        artists["cells"].append({**cell, "artist": patch, "annotation": annotation})
    rotation = spec.get("options", {}).get("x_rotation", 90)
    ax.set_xticks(range(len(prepared["columns"])), prepared["columns"], rotation=rotation)
    ax.set_yticks(range(len(prepared["rows"])), prepared["rows"])
    ax.tick_params(length=0, pad=2)
    ax.set_xlabel(spec.get("labels", {}).get("x", ""), fontsize=typography["axis"])
    ax.set_ylabel(spec.get("labels", {}).get("y", ""), fontsize=typography["axis"])
    for spine in ax.spines.values(): spine.set_visible(False)
    guide_labels, guide_colors, guide_hatches, guide_bindings = [], [], [], []
    for axis, tracks in prepared["metadata"].items():
        ids = prepared["rows" if axis == "row" else "columns"]
        for track in tracks:
            strip = frame.add_track(f"{axis}-metadata-{track['field']}", axis, settings["strip_mm"])
            if axis == "row": strip.set_xlim(-.5, .5)
            else: strip.set_ylim(-.5, .5)
            _clean_track(strip, axis)
            for index, (identifier, category) in enumerate(zip(ids, track["values"])):
                patch = Rectangle((-.5, index - .5) if axis == "row" else (index - .5, -.5), 1, 1, facecolor=track["colors"][category], edgecolor="none", linewidth=0)
                strip.add_patch(patch)
                path = core.figure_elements.pointer("metadata", axis, "tracks", track["index"], "colors", category)
                _register(fig, patch, "metadata-cell", f"{track['label']}: {category}", [axis, track["field"], identifier], [{"axis": axis, "id": identifier, "field": track["field"], "category": category}], [path], ["color"])
                artists["metadata"].append({"axis": axis, "id": identifier, "index": index, "field": track["field"], "category": category, "color": track["colors"][category], "artist": patch})
            for category, color in track["colors"].items():
                guide_labels.append(f"{track['label']}: {category}")
                guide_colors.append(color)
                guide_hatches.append("")
                guide_bindings.append({"key": [axis, track["field"], category], "source_keys": [{"axis": axis, "field": track["field"], "category": category}], "spec_paths": [core.figure_elements.pointer("metadata", axis, "tracks", track["index"], "colors", category)]})
    for axis, summaries in prepared["marginals"].items():
        config = spec["marginals"][axis]
        marginal = frame.add_track(f"{axis}-marginal", axis, settings["marginal_mm"])
        values = [r["value"] for r in summaries]
        bars = marginal.barh(range(len(values)), values, height=.8, linewidth=0, color=config.get("color", "#687983"), zorder=2) if axis == "row" else marginal.bar(range(len(values)), values, width=.8, linewidth=0, color=config.get("color", "#687983"), zorder=2)
        _clean_track(marginal, axis, numeric=True)
        limits = config.get("limits")
        if limits:
            (marginal.set_xlim if axis == "row" else marginal.set_ylim)(*limits)
        if axis == "row": marginal.set_xlabel(config["label"], fontsize=typography["axis"])
        else: marginal.set_ylabel(config["label"], fontsize=typography["axis"])
        for index, (summary, bar) in enumerate(zip(summaries, bars)):
            _register(fig, bar, "marginal-bar", f"{axis} {config['statistic']}: {summary['id']}", [axis, config["statistic"], summary["id"]], [{"axis": axis, "id": summary["id"]}], [f"/marginals/{axis}/color"], ["color"])
            artists["marginals"].append({**summary, "axis": axis, "index": index, "artist": bar})
    for axis, tree in prepared["trees"].items():
        dendrogram = frame.add_track(f"{axis}-dendrogram", axis, settings["dendrogram_mm"])
        _clean_track(dendrogram, axis, numeric=True)
        maximum = tree["maximum_height"]
        (dendrogram.set_xlim if axis == "row" else dendrogram.set_ylim)(0, maximum * 1.05 if maximum > 0 else 1)
        label = spec["dendrograms"][axis]["label"]
        if axis == "row": dendrogram.set_xlabel(label, fontsize=typography["axis"])
        else: dendrogram.set_ylabel(label, fontsize=typography["axis"])
        for branch in tree["branches"]:
            vertices = np.asarray(branch["vertices"])
            if axis == "row": vertices = vertices[:, ::-1]
            line, = dendrogram.plot(vertices[:, 0], vertices[:, 1], color="#555555", linewidth=layout["line_width_pt"], solid_capstyle="butt", zorder=2)
            _register(fig, line, "dendrogram-branch", f"Supplied {axis} branch", [axis, sorted(branch["leaf_ids"])], [{"axis": axis, "leaf_ids": branch["leaf_ids"], "node": branch["node"]}], [f"/dendrograms/{axis}"], [])
            artists["trees"].append({**branch, "axis": axis, "vertices": vertices.tolist(), "artist": line})
    for state in ("unmeasured", "unsupplied"):
        if any(c["state"] == state for c in prepared["cells"]):
            guide_labels.append("Unmeasured" if state == "unmeasured" else "Unsupplied coordinate")
            guide_colors.append(STATE_COLORS[state])
            guide_hatches.append(STATE_HATCHES[state])
            guide_bindings.append({"key": ["matrix-state", state], "source_keys": [{"state": state}], "spec_paths": ["/fields/state" if state == "unmeasured" else "/options/missing_cells"]})
    manager = _CompoundGuides(frame, typography, deepcopy(spec.get("legends", {})))
    manager.add_colorbar(mappable, spec.get("labels", {}).get("color", spec["fields"]["value"]))
    if guide_labels:
        manager.add_categorical(guide_labels, guide_colors)
        manager.requests[-1]["hatches"] = guide_hatches
    fig._easyviz_legend_layout = manager
    automatic = spec.get("layout", {}).get("auto_fit", "margins" not in spec.get("layout", {}) and "matrix_mm" not in settings)
    fig._easyviz_matrix_layout = _fit(frame, manager, settings["padding_mm"]) if automatic else {"status": "pass", "policy": "explicit matrix geometry", "matrix_mm": list(frame.rect_mm)}
    if not automatic: manager.layout()
    for entry in manager.entries:
        if entry["kind"] == "categorical":
            for handle, label, binding in zip(entry["artist"].legend_handles, guide_labels, guide_bindings):
                _register(fig, handle, "legend-key", label, binding["key"], binding["source_keys"], binding["spec_paths"], ["color"])
    for key, axes in frame.axes.items():
        _register(fig, axes.patch, "aligned-axes", key, key, [{"ordered_rows": prepared["rows"], "ordered_columns": prepared["columns"]}], [], ["layout"])
    return fig


def _fit(frame, manager, padding_mm):
    """Bounded joint fit using shared legend measurement, with unchanged fonts."""
    manual = any(manager.config.get(kind, {}).get("position") == "manual" for kind in ("categorical", "colorbar"))
    require(not manual and manager.override is None, "Automatic compound layout cannot use manual guide coordinates; use tracks.matrix_mm with auto_fit=false")
    original = deepcopy(manager.config)
    automatic = any(original.get(r["kind"], {}).get("position", "auto") == "auto" for r in manager.requests)
    attempts, solutions = [], []
    for side in (["bottom", "right", "top"] if automatic else ["bottom"]):
        manager.config = deepcopy(original)
        for request in manager.requests:
            config = manager.config.setdefault(request["kind"], {})
            if config.get("position", "auto") == "auto": config["position"] = side
        reserve = {"bottom": 0., "right": 0., "top": 0.}
        possible = True
        for _ in range(7):
            core.auto_layout._clear(manager)
            possible = _fit_frame(frame, reserve, padding_mm)
            if not possible: break
            manager.layout()
            measured = core.auto_layout._reservation(frame.fig, manager, padding_mm)
            updated = {edge: max(reserve[edge], measured[edge]) for edge in reserve}
            if max(abs(updated[e] - reserve[e]) for e in reserve) < .05: break
            reserve = updated
        core.auto_layout._clear(manager)
        possible = possible and _fit_frame(frame, reserve, padding_mm)
        if possible: manager.layout()
        issues = _layout_issues(frame, manager) if possible else ["no_positive_matrix_region"]
        area = frame.main.get_window_extent().width * frame.main.get_window_extent().height if possible else 0
        record = {"guide_side": side if automatic else None, "reserved_mm": reserve, "issues": issues, "matrix_mm": list(frame.rect_mm)}
        attempts.append(record)
        solutions.append((len(issues), -area, len(solutions), list(frame.rect_mm), deepcopy(manager.config)))
    selected = min(solutions, key=lambda item: item[:3])
    core.auto_layout._clear(manager)
    frame.reshape(selected[3])
    manager.config = selected[4]
    manager.layout()
    issues = _layout_issues(frame, manager)
    if all("no_positive_matrix_region" in a["issues"] for a in attempts): issues.append("no_positive_matrix_region")
    return {"status": "pass" if not issues else "needs_revision", "issues": issues, "attempts": attempts, "matrix_mm": list(frame.rect_mm), "padding_mm": padding_mm,
            "policy": "Measured compound envelope and guide reservation; preserve all IDs, point sizes, fonts and full canvas"}


def _fit_frame(frame, reserve, padding):
    width, height = frame.fig.get_size_inches() * 25.4
    extra = frame.additions_mm()
    for _ in range(6):
        frame.fig.canvas.draw()
        body, tight = frame.body_bbox(), frame.tight_bbox()
        scale = 25.4 / frame.fig.dpi
        overhang = [max(0, body.x0 - tight.x0) * scale, max(0, body.y0 - tight.y0) * scale,
                    max(0, tight.x1 - body.x1) * scale, max(0, tight.y1 - body.y1) * scale]
        x, y = padding + overhang[0], padding + reserve["bottom"] + overhang[1]
        w = width - padding - reserve["right"] - overhang[2] - extra["row"] - x
        h = height - padding - reserve["top"] - overhang[3] - extra["column"] - y
        if w <= 0 or h <= 0: return False
        old = frame.rect_mm
        frame.reshape([x, y, w, h])
        if max(abs(a - b) for a, b in zip(old, frame.rect_mm)) < .03: break
    return True


def _layout_issues(frame, manager):
    frame.fig.canvas.draw()
    box, canvas = frame.tight_bbox(), frame.fig.bbox
    issues = []
    if box.x0 < -1 or box.y0 < -1 or box.x1 > canvas.x1 + 1 or box.y1 > canvas.y1 + 1: issues.append("compound_text_outside_canvas")
    overlaps, _ = core.check_tick_label_overlap(frame.fig, frame.fig.canvas.get_renderer())
    if overlaps: issues.append("tick_label_overlap")
    axes = list(frame.axes.items())
    painter = frame.fig.canvas.get_renderer()
    # Tight rectangles include empty corners around labels. Use the actual
    # text rectangles for inter-axis collisions, not those empty corners.
    texts = {name: _axis_texts(ax) for name, ax in axes}
    for i, (name, ax) in enumerate(axes):
        for other_name, other in axes[i + 1:]:
            collided = core.legend_layout._intersects(ax.get_window_extent(), other.get_window_extent())
            collided = collided or any(core.legend_layout._intersects(text.get_window_extent(painter), other.get_window_extent()) for text in texts[name])
            collided = collided or any(core.legend_layout._intersects(text.get_window_extent(painter), ax.get_window_extent()) for text in texts[other_name])
            collided = collided or any(core.legend_layout._intersects(a.get_window_extent(painter), b.get_window_extent(painter)) for a in texts[name] for b in texts[other_name])
            if collided: issues.append(f"compound_axes_or_text_overlap:{name}:{other_name}")
    issues.extend(manager.validate()["issues"])
    return sorted(set(issues))


def _axis_texts(ax):
    """Visible text with out-of-domain locator ticks excluded, as in core QA."""
    excluded = set()
    for axis in (ax.xaxis, ax.yaxis):
        low, high = sorted(axis.get_view_interval())
        for tick in axis.get_major_ticks() + axis.get_minor_ticks():
            if not low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                excluded.update((tick.label1, tick.label2))
    return [t for t in ax.findobj(core.Text) if t not in excluded and t.get_visible() and t.get_text().strip()]


def audit_source_artists(data_path, spec, fig, **inputs):
    """Re-read source files and compare values, colors, IDs and actual geometry."""
    source = prepare(data_path, spec, **inputs)
    records = fig._easyviz_matrix_artists
    issues, values = [], []
    frame = fig._easyviz_aligned_frame
    expected_cmap, expected_norm = core.continuous(spec, [c["value"] for c in source["cells"] if c["state"] == "observed"])
    expected_scale = ScalarMappable(norm=expected_norm, cmap=expected_cmap)
    expected = {(c["row"], c["column"]): c for c in source["cells"]}
    require(len(records["cells"]) == len(expected), "Matrix artist count differs from displayed grid")
    seen = set()
    for record in records["cells"]:
        key = (record["row"], record["column"])
        cell = expected.get(key)
        if cell is None or key in seen:
            issues.append({"code": "matrix_artist_key_mismatch", "row": key[0], "column": key[1]})
            continue
        seen.add(key)
        patch = record["artist"]
        target = [cell["column_index"] - .5, cell["row_index"] - .5, 1., 1.]
        actual = [patch.get_x(), patch.get_y(), patch.get_width(), patch.get_height()]
        color = expected_scale.to_rgba(cell["value"]) if cell["state"] == "observed" else to_rgba(STATE_COLORS[cell["state"]])
        if not np.allclose(actual, target, atol=1e-12, rtol=0): issues.append({"code": "matrix_cell_geometry_mismatch", "row": key[0], "column": key[1]})
        if not _rectangle_display_match(patch, frame.main, target): issues.append({"code": "matrix_cell_display_geometry_mismatch", "row": key[0], "column": key[1]})
        if not np.allclose(patch.get_facecolor(), color, atol=1e-12, rtol=0): issues.append({"code": "matrix_cell_color_mismatch", "row": key[0], "column": key[1]})
        if patch.get_hatch() != (None if cell["state"] == "observed" else STATE_HATCHES[cell["state"]]): issues.append({"code": "matrix_state_encoding_mismatch", "row": key[0], "column": key[1]})
        annotation = record["annotation"]
        if spec.get("options", {}).get("annotate_values", False) and cell["state"] == "observed" and (annotation is None or not _attached(annotation, frame.main, frame.main.texts)):
            issues.append({"code": "matrix_value_annotation_absent", "row": key[0], "column": key[1]})
        if annotation is not None and (annotation.get_position() != (cell["column_index"], cell["row_index"]) or annotation.get_text() != format(cell["value"], spec.get("options", {}).get("value_format", ".2g"))): issues.append({"code": "matrix_value_annotation_mismatch", "row": key[0], "column": key[1]})
        values.append({"layer": "matrix", "row": cell["row"], "column": cell["column"], "state": cell["state"], "source_value": cell["value"],
                       **{f"source_{channel}": float(component) for channel, component in zip(("red", "green", "blue", "alpha"), color)},
                       **{f"artist_{channel}": float(component) for channel, component in zip(("red", "green", "blue", "alpha"), patch.get_facecolor())},
                       "artist_x": patch.get_x() + .5, "artist_y": patch.get_y() + .5, "svg_id": patch.get_gid()})
    metadata_expected = {(axis, track["field"], identifier): (i, category, track["colors"][category])
                         for axis, tracks in source["metadata"].items() for track in tracks
                         for i, (identifier, category) in enumerate(zip(source["rows" if axis == "row" else "columns"], track["values"]))}
    if len(records["metadata"]) != len(metadata_expected): issues.append({"code": "metadata_artist_count_mismatch"})
    metadata_seen = set()
    for record in records["metadata"]:
        key = record["axis"], record["field"], record["id"]
        if key not in metadata_expected or key in metadata_seen:
            issues.append({"code": "metadata_artist_key_mismatch"})
            continue
        metadata_seen.add(key)
        index, category, color = metadata_expected[key]
        patch = record["artist"]
        position = [-.5, index - .5] if record["axis"] == "row" else [index - .5, -.5]
        if record["category"] != category or not np.allclose(patch.get_facecolor(), to_rgba(color), atol=1e-12, rtol=0) or not np.allclose([patch.get_x(), patch.get_y(), patch.get_width(), patch.get_height()], position + [1, 1], atol=1e-12, rtol=0): issues.append({"code": "metadata_source_artist_mismatch", "axis": key[0], "field": key[1], "id": key[2]})
        metadata_ax = frame.axes[f"{key[0]}-metadata-{key[1]}"]
        if not _rectangle_display_match(patch, metadata_ax, position + [1, 1]): issues.append({"code": "metadata_display_geometry_mismatch", "axis": key[0], "field": key[1], "id": key[2]})
    marginal_expected = {(axis, row["id"]): (index, row) for axis, summaries in source["marginals"].items() for index, row in enumerate(summaries)}
    if len(records["marginals"]) != len(marginal_expected): issues.append({"code": "marginal_artist_count_mismatch"})
    marginal_seen = set()
    for record in records["marginals"]:
        key = record["axis"], record["id"]
        if key not in marginal_expected or key in marginal_seen:
            issues.append({"code": "marginal_artist_key_mismatch"})
            continue
        marginal_seen.add(key)
        index, summary = marginal_expected[key]
        bar = record["artist"]
        value = bar.get_width() if key[0] == "row" else bar.get_height()
        center = bar.get_y() + bar.get_height() / 2 if key[0] == "row" else bar.get_x() + bar.get_width() / 2
        baseline = bar.get_x() if key[0] == "row" else bar.get_y()
        if not math.isclose(value, summary["value"], abs_tol=1e-12, rel_tol=0) or not math.isclose(center, index, abs_tol=1e-12) or baseline != 0: issues.append({"code": "marginal_source_artist_mismatch", "axis": key[0], "id": key[1]})
        expected_rect = [0., index - .4, summary["value"], .8] if key[0] == "row" else [index - .4, 0., .8, summary["value"]]
        if not _rectangle_display_match(bar, frame.axes[f"{key[0]}-marginal"], expected_rect): issues.append({"code": "marginal_display_geometry_mismatch", "axis": key[0], "id": key[1]})
        values.append({"layer": f"{key[0]}-marginal", "id": key[1], "source_value": summary["value"], "artist_value": value, "artist_category_center": center, "svg_id": bar.get_gid()})
    tree_expected = {(axis, branch["node"]): branch for axis, tree in source["trees"].items() for branch in tree["branches"]}
    if len(records["trees"]) != len(tree_expected): issues.append({"code": "dendrogram_artist_count_mismatch"})
    tree_seen = set()
    for record in records["trees"]:
        key = record["axis"], record["node"]
        if key not in tree_expected or key in tree_seen:
            issues.append({"code": "dendrogram_artist_key_mismatch"})
            continue
        tree_seen.add(key)
        expected_vertices = np.asarray(tree_expected[key]["vertices"])
        if key[0] == "row": expected_vertices = expected_vertices[:, ::-1]
        line = record["artist"]
        actual_vertices = np.column_stack((line.get_xdata(), line.get_ydata()))
        if actual_vertices.shape != expected_vertices.shape or not np.allclose(actual_vertices, expected_vertices, atol=1e-12, rtol=0): issues.append({"code": "dendrogram_source_artist_mismatch", "axis": key[0], "node": key[1]})
        tree_ax = frame.axes[f"{key[0]}-dendrogram"]
        if not _attached(line, tree_ax, tree_ax.lines) or line.get_alpha() == 0 or line.get_linewidth() <= 0 or actual_vertices.shape != expected_vertices.shape or not np.allclose(line.get_transform().transform(actual_vertices), tree_ax.transData.transform(expected_vertices), atol=1e-9, rtol=0): issues.append({"code": "dendrogram_display_geometry_mismatch", "axis": key[0], "node": key[1]})
    alignment = fig._easyviz_aligned_frame.audit()
    issues.extend(alignment["issues"])
    return {"status": "pass" if not issues else "needs_revision", "issues": issues, "source_rows": len(source["data"]), "displayed_cells": len(source["cells"]), "alignment": alignment, "artist_values": values,
            "scope": "Source-bound cell color/state/geometry, keyed strip color/geometry, marginal bar values/baseline/centers and supplied-tree vertices; no upstream scientific validity claim"}


def _attached(artist, axes, container):
    return axes.get_visible() and axes in axes.figure.axes and artist.get_visible() and artist.axes is axes and artist in container


def _rectangle_display_match(patch, axes, expected_rect):
    if not _attached(patch, axes, axes.patches): return False
    x, y, width, height = expected_rect
    expected = axes.transData.transform([[x, y], [x + width, y], [x + width, y + height], [x, y + height]])
    actual = patch.get_transform().transform([[0, 0], [1, 0], [1, 1], [0, 1]])
    return np.isfinite(actual).all() and np.allclose(actual, expected, atol=1e-9, rtol=0)


def _caption(prepared, spec):
    labels = spec.get("labels", {})
    parts = [f"Matrix colors encode supplied {labels.get('color') or spec['fields']['value']}. Row and column orders were explicitly supplied."]
    present_states = {c["state"] for c in prepared["cells"]}
    if "unmeasured" in present_states: parts.append("Cross-hatched cells indicate explicitly unmeasured values.")
    if "unsupplied" in present_states: parts.append("Plus-hatched cells indicate coordinates absent from the supplied table.")
    if present_states != {"observed"}: parts.append("Numeric zero remains an observed value.")
    for axis, tracks in prepared["metadata"].items(): parts.append(f"{axis.capitalize()} strips show " + ", ".join(t["label"] for t in tracks) + ", joined by literal IDs.")
    for axis, config in spec.get("marginals", {}).items():
        parts.append(f"{axis.capitalize()} marginal bars show the {config['statistic']} across the displayed grid; " + ("missing cells are excluded and denominators are recorded in marginal-data.csv." if config["missing"] == "omit" else "all cells are required to be observed."))
    if prepared["trees"]: parts.append("Dendrograms use supplied linkage heights and exact supplied leaf traversal; clustering was not recalculated.")
    return " ".join(parts) + "\n"


def render(data_path, spec, out, *, spec_path=None, track=None, **inputs):
    """Persist reviewable exports plus truthful failed or successful QA."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"status": "in_progress", "valid_outputs": False})
    spec_path = core.begin_document(out, spec, spec_path)
    before, fig = set(plt.get_fignums()), None
    try:
        spec_hash = None
        if spec_path:
            spec_payload = Path(spec_path).read_bytes()
            require(json.loads(spec_payload.decode("utf-8")) == spec, "spec_path contents differ from the supplied specification")
            spec_hash = hashlib.sha256(spec_payload).hexdigest()
        prepared = prepare(data_path, spec, **inputs)
        hashes = prepared["input_hashes"]
        resolved = deepcopy(spec)
        resolved.setdefault("chart", "annotated_matrix")
        layout, typography, rc = core.setup(resolved)
        with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig = draw(prepared, resolved, layout, typography)
            fig._easyviz_data_file, fig._easyviz_source_script = Path(data_path).resolve(), Path(__file__).resolve()
            fig._easyviz_spec_file = Path(spec_path).resolve() if spec_path else None
            fig._easyviz_track = track
            fig.canvas.draw()
            audit = audit_source_artists(data_path, resolved, fig, **inputs)
            changed = [key for key, path in prepared["inputs"].items() if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]]
            if spec_path and hashlib.sha256(Path(spec_path).read_bytes()).hexdigest() != spec_hash: changed.append("specification")
            if changed:
                audit["status"] = "needs_revision"
                audit["issues"].append({"code": "source_changed_during_render", "inputs": changed})
            geometry = _layout_issues(fig._easyviz_aligned_frame, fig._easyviz_legend_layout)
            annotations = []
            painter = fig.canvas.get_renderer()
            for record in fig._easyviz_matrix_artists["cells"]:
                text = record["annotation"]
                if text is not None and not core.legend_layout._contains(record["artist"].get_window_extent(painter), text.get_window_extent(painter)):
                    annotations.append({"code": "cell_annotation_does_not_fit", "row": record["row"], "column": record["column"]})
            legends = fig._easyviz_legend_layout.validate()
            exports = core.export(fig, out, resolved, layout)
            readability = core.panel_readability.measure(fig)
            changed = [key for key, path in prepared["inputs"].items() if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]]
            if spec_path and hashlib.sha256(Path(spec_path).read_bytes()).hexdigest() != spec_hash: changed.append("specification")
            if changed and not any(i["code"] == "source_changed_during_render" for i in audit["issues"]):
                audit["status"] = "needs_revision"
                audit["issues"].append({"code": "source_changed_during_render", "inputs": changed})
            glyphs = sorted({str(w.message) for w in captured if "Glyph" in str(w.message) and "missing" in str(w.message)})
            passed = audit["status"] == "pass" and not geometry and not annotations and not glyphs and fig._easyviz_matrix_layout["status"] == "pass"
            qa = {"status": "pass" if passed else "needs_revision", "valid_outputs": passed, "input_rows": len(prepared["data"]), "displayed_cells": len(prepared["cells"]), "width_mm": layout["width_mm"], "height_mm": layout["height_mm"], "source_to_artist_audit": {k: v for k, v in audit.items() if k != "artist_values"}, "compound_layout": fig._easyviz_matrix_layout, "layout_issues": geometry, "annotation_issues": annotations, "missing_glyphs": glyphs, "legend_layout": legends, "exports": exports, "visual_review_required": True}
            qa["readability"] = readability
            settings = {**resolved, "layout": layout, "typography": typography, "compound_layout": fig._easyviz_matrix_layout, "inputs": {key: {"path": str(path), "sha256": hashes[key]} for key, path in prepared["inputs"].items()}, "renderer": {"version": VERSION, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "helper_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("aligned_layers.py", "render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py", "figure_elements.py", "panel_readability.py", "observation_clipping.py")}}, "track": track, "outline_policy": "Observed cells, strips and marginal bars borderless; missing-state hatch strokes are decoding exceptions", "statistical_scope": "Displayed grid descriptive mean/sum only; no tests, clustering or upstream analysis"}
            settings["resolved_color_scale"] = {"minimum": float(fig._easyviz_matrix_scale.norm.vmin), "maximum": float(fig._easyviz_matrix_scale.norm.vmax), "center": spec.get("options", {}).get("color_center"), "colormap": spec.get("colormap", "somerville-sky")}
            if spec_path:
                settings["spec_file"] = {"path": str(Path(spec_path).resolve()), "sha256": spec_hash}
            prepared["data"].to_csv(out / "plotting-data.csv", index=False)
            pd.DataFrame(prepared["cells"]).to_csv(out / "matrix-cells.csv", index=False)
            pd.DataFrame(audit["artist_values"]).to_csv(out / "artist-values.csv", index=False)
            summaries = [{"axis": axis, **summary} for axis, rows in prepared["marginals"].items() for summary in rows]
            if summaries: pd.DataFrame(summaries).to_csv(out / "marginal-data.csv", index=False)
            (out / "caption.md").write_text(_caption(prepared, spec))
            write_json(out / "settings.json", settings)
            write_json(out / "stats.json", {"tests_performed": False, "clustering_performed": False, "marginal_population": "displayed grid", "marginals": prepared["marginals"], "supplied_dendrograms": prepared["trees"]})
            manifest_path = out / "elements.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["input"]["aligned_layer_inputs"] = settings["inputs"]
            write_json(manifest_path, manifest)
            write_json(out / "qa.json", qa)
            require(passed, "Compound matrix QA needs revision; inspect qa.json and the exported preview. Preserve final fonts and canvas or request a larger panel.")
            core.save_document(out)
            return qa
    except Exception as exc:
        qa = json.loads((out / "qa.json").read_text())
        if qa["status"] == "in_progress":
            qa.update(status="failed", valid_outputs=False, error=str(exc))
            write_json(out / "qa.json", qa)
        raise
    finally:
        if fig is not None: plt.close(fig)
        for number in set(plt.get_fignums()) - before: plt.close(number)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--track", choices=("create", "reproduce"))
    parser.add_argument("--describe-spec", action="store_true")
    for axis in ("row", "column"):
        parser.add_argument(f"--{axis}-metadata", type=Path)
        parser.add_argument(f"--{axis}-linkage", type=Path)
    args = parser.parse_args()
    if args.describe_spec:
        print(json.dumps(SCHEMA, indent=2))
        return
    if not all((args.data, args.spec, args.out)): parser.error("--data, --spec and --out are required unless --describe-spec is used")
    try:
        spec = json.loads(args.spec.read_text())
        qa = render(args.data, spec, args.out, spec_path=args.spec, track=args.track,
                    **{f"{axis}_{kind}": getattr(args, f"{axis}_{kind}") for axis in ("row", "column") for kind in ("metadata", "linkage")})
    except (ValueError, OSError, ImportError) as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        if not (args.out / "qa.json").exists(): write_json(args.out / "qa.json", {"status": "failed", "valid_outputs": False, "error": str(exc)})
        parser.exit(2, f"EasyViz annotated matrix: {exc}\n")
    print(json.dumps({"status": qa["status"], "output": str(args.out), "width_mm": qa["width_mm"], "height_mm": qa["height_mm"]}))


if __name__ == "__main__":
    main()
