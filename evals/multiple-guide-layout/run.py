#!/usr/bin/env python3
"""Rerun a frozen runtime pair for a post-hoc engineering layout diagnostic.

This is not a WorkBuddy/model evaluation. Requires the dependencies declared in
the EasyViz renderer requirements; no network access or model API is used.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-matplotlib"))

import matplotlib.collections as collections
import numpy as np
import pandas as pd

from marker_geometry import collection_fill_areas_pt2

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def load(path, name):
    loader = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def capture(fig):
    """Measure actual artists before export, excluding display-space offsets."""
    fig.canvas.draw()
    axis = fig.axes[0]
    marks = []
    for artist in axis.collections:
        mark = {"type": type(artist).__name__,
                "facecolors": artist.get_facecolors().tolist(),
                "edgecolors": artist.get_edgecolors().tolist(),
                "linewidths_pt": artist.get_linewidths().tolist()}
        if isinstance(artist, collections.PathCollection):
            mark.update(offsets_data=np.asarray(artist.get_offsets()).tolist(),
                        marker_size_parameters_pt2=artist.get_sizes().tolist(),
                        actual_path_fill_areas_pt2=collection_fill_areas_pt2(artist, fig).tolist())
        if isinstance(artist, collections.LineCollection):
            mark["segments_data"] = [segment.tolist() for segment in artist.get_segments()]
        marks.append(mark)
    manager = fig._easyviz_legend_layout
    guide_keys = []
    for entry in manager.entries:
        for key in entry["artist"].legend_handles if entry["kind"] != "colorbar" else []:
            if isinstance(key, collections.PathCollection):
                guide_keys.append({"marker_size_parameters_pt2": key.get_sizes().tolist(),
                                   "actual_path_fill_areas_pt2": collection_fill_areas_pt2(key, fig).tolist()})
    return {"axis_collections": marks, "quantitative_guide_keys": guide_keys,
            "data_axis_count": 1, "all_axes_count": len(fig.axes),
            "axis_limits": {"x": list(axis.get_xlim()), "y": list(axis.get_ylim())},
            "canvas_mm": [fig.get_figwidth() * 25.4, fig.get_figheight() * 25.4],
            "dpi": fig.dpi}


def round_numbers(value):
    if isinstance(value, dict):
        return {key: round_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [round_numbers(item) for item in value]
    if isinstance(value, float):
        return round(value, 10)
    return value


def render_one(runtime, case, out):
    script = "interval_plot.py" if case == "interval" else "render.py"
    module = load(ROOT / f"{runtime}-runtime/scripts" / script, f"diagnostic_{runtime}_{case}")
    core = module.core if case == "interval" else module
    original_export = core.export
    observed = {}

    def observed_export(fig, *args, **kwargs):
        observed.update(capture(fig))
        return original_export(fig, *args, **kwargs)

    core.export = observed_export
    spec_path, data_path = ROOT / "inputs" / f"{case}.json", ROOT / "inputs" / f"{case}.csv"
    spec = json.loads(spec_path.read_text())
    error = None
    try:
        module.render(data_path, deepcopy(spec), out, spec_path=spec_path)
    except ValueError as exc:
        # Truthful failures are part of this diagnostic, with saved exports/QA.
        error = str(exc)
    finally:
        core.export = original_export
    qa = json.loads((out / "qa.json").read_text())
    settings = json.loads((out / "settings.json").read_text())
    write(out / "artist-measurements.json", observed)
    box = settings["auto_layout"]["data_region_mm"]
    guides = settings["legend_layout"]
    return {"status": qa["status"], "error": error,
            "width_mm": box[2], "height_mm": box[3], "data_area_mm2": box[2] * box[3],
            "data_area_fraction": settings["auto_layout"]["data_area_fraction"],
            "chosen_sides": [g["chosen_settings"]["position"] for g in guides["legends"]],
            "attempts": settings["auto_layout"]["attempts"],
            "legend_issues": guides["issues"], "guide_count": guides["combined"]["guide_count"],
            "guide_envelope_overlap_mm2": guides["combined"]["envelope_overlap_area_mm2"],
            "source_rows": qa["input_rows"], "source_sha256": digest(data_path),
            "plotting_data_sha256": digest(out / "plotting-data.csv"),
            "typography": settings["typography"],
            "font": settings["layout"]["font"], "canvas_mm": observed["canvas_mm"],
            "exports": qa["exports"], "artist_measurements": observed,
            "stats": json.loads((out / "stats.json").read_text())}


def compare(case, versions):
    before, after = versions["before"], versions["after"]
    equality = {"source_rows": before["source_rows"] == after["source_rows"],
                "plotting_data_exact": before["plotting_data_sha256"] == after["plotting_data_sha256"],
                "typography": before["typography"] == after["typography"],
                "actual_font": before["font"] == after["font"],
                "canvas": before["canvas_mm"] == after["canvas_mm"],
                "stats": before["stats"] == after["stats"],
                "actual_artists_and_quantitative_keys": round_numbers(before["artist_measurements"]) == round_numbers(after["artist_measurements"])}
    if not all(equality.values()):
        raise AssertionError(f"Unexpected semantic or physical change for {case}: {equality}")
    source = pd.read_csv(ROOT / "inputs" / f"{case}.csv")
    if len(source) != after["source_rows"]:
        raise AssertionError(f"Rows changed for {case}")
    if after["status"] != "pass":
        raise AssertionError(f"After-fix QA needs revision for {case}")
    return {"before": before, "after": after, "equality": equality,
            "width_change_mm": after["width_mm"] - before["width_mm"],
            "data_area_change_mm2": after["data_area_mm2"] - before["data_area_mm2"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New output directory; existing paths are refused")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out already exists; use a new directory to preserve earlier evidence")
    manifest = json.loads((ROOT / "provenance.json").read_text())
    for runtime in ("before", "after"):
        for relative, expected in manifest[f"{runtime}_runtime"].items():
            if digest(ROOT / relative) != expected:
                raise ValueError(f"Runtime snapshot hash changed: {relative}")
    for item in manifest["frozen_inputs"]:
        if digest(ROOT / item["copy"]) != item["sha256"]:
            raise ValueError(f"Copied frozen input hash changed: {item['copy']}")
    args.out.mkdir(parents=True)
    report = {"experiment": manifest["experiment"], "cases": {},
              "area_definition": "Data-axis width times height, excluding axes labels and guides.",
              "geometry_definition": "Actual circle Bézier path area and artist display transform, excluding edge stroke; the cubic approximation differs from the ideal circle by about 2.9e-7 relative.",
              "limitations": ["This is an engineering diagnostic after the GLM review, not another model run or unbiased benchmark.",
                              "Before is the canonical runtime captured before this fix, not the originally frozen WorkBuddy helper runtime.",
                              "The objective compares the three grouped side candidates with existing declared variant order, not all guide arrangements or aesthetics.",
                              "Automatic numeric tick locator counts can change as available data width changes; explicit intervals/data mappings, labels, fonts, marker sizes and canvas remain fixed.",
                              "Technical fit and larger data area still require independent visual judgment."]}
    for case in ("interval", "scatter", "dot", "dot-auto"):
        versions = {runtime: render_one(runtime, case, args.out / case / runtime)
                    for runtime in ("before", "after")}
        before, after = versions["before"], versions["after"]
        report["cases"][case] = compare(case, versions)
        print(f"{case}: {before['width_mm']:.6f} -> {after['width_mm']:.6f} mm data width; "
              f"{before['data_area_mm2']:.6f} -> {after['data_area_mm2']:.6f} mm² data area; equality passed")
    write(args.out / "comparison.json", report)


if __name__ == "__main__":
    main()
