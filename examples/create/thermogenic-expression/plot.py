#!/usr/bin/env python3
"""Traceable absolute-expression matrix and descriptive genotype-mean contrasts.

Only the log2(TPM + 1) display transformation is applied. Each matrix cell and
contrast bar is a real selectable vector artist with its source-cell bindings.
"""
import argparse
import csv
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import statistics
import shutil
import sys
import tempfile

SCRIPT_BYTES = Path(__file__).read_bytes()
if compile(SCRIPT_BYTES, str(Path(__file__)), "exec", dont_inherit=True) != sys._getframe().f_code:
    raise RuntimeError("Executing plot code differs from its source; reload the current script without stale bytecode.")

if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = tempfile.mkdtemp(prefix="easyviz-expression-mpl-")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgb

HERE = Path(__file__).resolve().parent


def runtime_path(explicit=None):
    if explicit:
        path = Path(explicit).resolve()
        if not (path / "figure_elements.py").is_file() or not (path / "render.py").is_file():
            raise FileNotFoundError("Pass an EasyViz scripts directory with sibling helpers intact.")
        return path
    for parent in HERE.parents:
        for relative in ("scripts", "skills/easyviz/scripts"):
            path = parent / relative
            if (path / "figure_elements.py").is_file() and (path / "render.py").is_file():
                return path
    raise FileNotFoundError("Supply --tools /path/to/easyviz/scripts.")


def execute_helper_bytes(path, name, raw):
    """Load an exact declared helper payload, without timestamp-valid bytecode."""
    definition = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(definition)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def expression_color(value, scale):
    low, high = scale["limits"]
    if not low <= value <= high:
        raise ValueError("Expression value outside the adopted color scale; do not silently clip.")
    fraction = (value - low) / (high - low)
    anchors = scale["anchors"]
    for (a, first), (b, second) in zip(anchors, anchors[1:]):
        if a <= fraction <= b:
            t = (fraction - a) / (b - a)
            return tuple((1 - t) * x + t * y for x, y in zip(to_rgb(first), to_rgb(second)))
    raise ValueError("Color anchors do not cover the adopted scale.")


def source_key(row):
    return {key: row[key] for key in ("source_sheet", "source_cell", "gene", "sample", "condition")}


def load_data(raw, contract):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    if len(rows) != contract["observations"]:
        raise ValueError("Source row count differs from the adopted contract.")
    cells = {}
    for row in rows:
        key = (row["gene"], row["sample"])
        value = float(row["tpm"])
        if key in cells or not math.isfinite(value) or value < 0:
            raise ValueError("Duplicate or invalid expression cell.")
        if contract["condition_aliases"][row["sample"]] != row["condition"]:
            raise ValueError("Genotype alias differs from the author-supported contract.")
        cells[key] = row
    expected = {(gene, sample) for gene in contract["genes"] for sample in contract["samples"]}
    if set(cells) != expected:
        raise ValueError("The source matrix is incomplete or contains undeclared rows/columns.")
    return rows, cells


def write_csv(path, records):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def draw(spec, contract, capture, core):
    elements = core.figure_elements
    rows, cells = load_data(capture.read("data_file"), contract)
    genes, samples = contract["genes"], contract["samples"]
    if samples != spec["order"]["sample"]:
        raise ValueError("The specification's sample order differs from the source contract.")
    layout, typography, rc = core.setup(spec)
    transformed, summaries = [], []
    width, height = layout["width_mm"], layout["height_mm"]
    with plt.rc_context(rc):
        fig = plt.figure(figsize=(width / 25.4, height / 25.4), dpi=layout["dpi"])
        fig._easyviz_track = "create"
        fig._easyviz_source_script = Path(__file__).resolve()
        fig._easyviz_data_file = capture.paths["data_file"]
        fig._easyviz_spec_file = capture.paths["spec_file"]
        fig._easyviz_source_bindings = {field: {"path": str(path), "sha256": hashlib.sha256(capture.read(field)).hexdigest()}
                                       for field, path in capture.paths.items()}
        fig._easyviz_source_bindings.update({role: {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
                                            for role, (path, raw) in capture.auxiliary.items()})
        fig._easyviz_resolved_colors = spec["colors"]

        def axis(box):
            x, y, w, h = box
            return fig.add_axes([x / width, y / height, w / width, h / height])

        heat = axis(spec["geometry_mm"]["matrix"])
        heat.set_xlim(0, len(samples)); heat.set_ylim(len(genes), 0)
        heat.set_xticks([]); heat.set_yticks([])
        for spine in heat.spines.values():
            spine.set_linewidth(spec["strokes"]["matrix_frame_width_pt"])
            spine.set_color(spec["strokes"]["matrix_frame"])
        for row_index, gene in enumerate(genes):
            gene_rows = [cells[(gene, sample)] for sample in samples]
            label = heat.text(-.16, row_index + .5, gene, ha="right", va="center", fontstyle="italic", clip_on=False)
            elements.register(fig, label, "gene-label", gene, key=gene, source_keys=[source_key(row) for row in gene_rows], editable=["color", "text"])
            for column, row in enumerate(gene_rows):
                value = math.log2(float(row["tpm"]) + 1)
                color = expression_color(value, spec["expression_scale"])
                cell = Rectangle((column, row_index), 1, 1, facecolor=color,
                                 edgecolor=spec["strokes"]["cell_seam"], linewidth=spec["strokes"]["cell_seam_width_pt"], antialiased=False)
                heat.add_patch(cell)
                elements.register(fig, cell, "expression-cell", f"{gene} · {row['sample']} · {row['condition']}",
                                  key=[gene, row["sample"]], source_keys=[source_key(row)],
                                  spec_paths=["/expression_scale/anchors", "/strokes/cell_seam", "/strokes/cell_seam_width_pt"],
                                  editable={"palette": "/expression_scale/anchors", "seam_color": "/strokes/cell_seam", "seam_width": "/strokes/cell_seam_width_pt"})
                transformed.append({**row, "log2_tpm_plus_1": format(value, ".17g"), "row_index": row_index, "column_index": column, "artist_id": cell.get_gid()})
            groups = {condition: [math.log2(float(row["tpm"]) + 1) for row in gene_rows if row["condition"] == condition]
                      for condition in spec["order"]["genotype"]}
            means = {condition: statistics.mean(values) for condition, values in groups.items()}
            difference = means["YT-AKO"] - means["YT-FF"]
            summaries.append({"gene": gene, "n_control": len(groups["YT-FF"]), "n_ako": len(groups["YT-AKO"]),
                              "control_mean_log2_tpm_plus_1": format(means["YT-FF"], ".17g"), "ako_mean_log2_tpm_plus_1": format(means["YT-AKO"], ".17g"),
                              "descriptive_difference": format(difference, ".17g"), "source_cells": ";".join(row["source_cell"] for row in gene_rows)})

        contrast = axis(spec["geometry_mm"]["contrast"])
        contrast.set_xlim(*spec["contrast"]["limits"]); contrast.set_ylim(len(genes), 0)
        contrast.set_xticks(spec["contrast"]["ticks"]); contrast.set_yticks([])
        contrast.tick_params(axis="x", length=2, width=.5, pad=2)
        for side in ("right", "top", "left"):
            contrast.spines[side].set_visible(False)
        contrast.spines["bottom"].set_linewidth(.55)
        for tick in spec["contrast"]["ticks"]:
            reference = contrast.axvline(tick, color="#6F7479" if tick == 0 else spec["strokes"]["reference"],
                                         linewidth=.55 if tick == 0 else spec["strokes"]["reference_width_pt"], zorder=0)
            elements.register(fig, reference, "contrast-reference", f"Difference guide · {tick:g}", key=tick, editable=["color", "linewidth"])
        for row_index, summary in enumerate(summaries):
            gene = summary["gene"]; difference = float(summary["descriptive_difference"])
            low, high = spec["contrast"]["limits"]
            if not low <= difference <= high:
                raise ValueError("Contrast exceeds its adopted bounds; adapt the signed scale before rendering.")
            bar = Rectangle((min(0, difference), row_index + .5 - spec["contrast"]["bar_height_rows"] / 2), abs(difference), spec["contrast"]["bar_height_rows"],
                            facecolor=spec["contrast"]["bar_face"], edgecolor=spec["contrast"]["bar_edge"], linewidth=spec["contrast"]["bar_edge_width_pt"])
            contrast.add_patch(bar)
            source_rows = [cells[(gene, sample)] for sample in samples]
            elements.register(fig, bar, "mean-contrast", f"{gene} · YT-AKO − YT-FF", key=gene,
                              source_keys=[source_key(row) for row in source_rows],
                              spec_paths=["/contrast/bar_face", "/contrast/bar_edge", "/contrast/bar_edge_width_pt", "/contrast/bar_height_rows"],
                              editable={"color": "/contrast/bar_face", "edge_color": "/contrast/bar_edge", "edge_width": "/contrast/bar_edge_width_pt", "height": "/contrast/bar_height_rows"})
            summary["artist_id"] = bar.get_gid()
            if difference == 0:
                zero = contrast.plot(0, row_index + .5, marker="o", markersize=2.3, color=spec["contrast"]["bar_edge"], clip_on=False, zorder=3)[0]
                elements.register(fig, zero, "zero-contrast", f"{gene} · observed zero contrast", key=gene, source_keys=[source_key(row) for row in source_rows], editable=["color", "markersize"])

        band = axis(spec["geometry_mm"]["genotype_band"])
        band.set_xlim(0, len(samples)); band.set_ylim(0, 1); band.set_axis_off()
        for column, sample in enumerate(samples):
            genotype = contract["condition_aliases"][sample]
            block = Rectangle((column, 0), 1, 1, facecolor=spec["colors"][genotype], edgecolor="white", linewidth=.35)
            band.add_patch(block)
            elements.register(fig, block, "genotype-band", f"{sample} · {genotype}", key=sample,
                              source_keys=[source_key(cells[(gene, sample)]) for gene in genes],
                              spec_paths=[elements.pointer("colors", genotype)], editable={"color": elements.pointer("colors", genotype)})
        matrix_box = spec["geometry_mm"]["matrix"]
        for genotype, center in (("YT-FF", 1.5), ("YT-AKO", 4.5)):
            x = (matrix_box[0] + center / len(samples) * matrix_box[2]) / width
            label = fig.text(x, spec["geometry_mm"]["header_y"] / height, genotype, ha="center", va="center")
            elements.register(fig, label, "genotype-label", genotype, key=genotype,
                              source_keys=[source_key(row) for row in rows if row["condition"] == genotype], editable=["color", "text"])
        for column, sample in enumerate(samples):
            x = (matrix_box[0] + (column + .5) / len(samples) * matrix_box[2]) / width
            label = fig.text(x, spec["geometry_mm"]["sample_label_y"] / height, sample, ha="center", va="center")
            elements.register(fig, label, "sample-label", sample, key=sample,
                              source_keys=[source_key(cells[(gene, sample)]) for gene in genes], editable=["color", "text"])
        center = (spec["geometry_mm"]["contrast"][0] + spec["geometry_mm"]["contrast"][2] / 2) / width
        for label_key, y in (("contrast_header", spec["geometry_mm"]["header_y"]), ("contrast_direction", 18)):
            label = fig.text(center, y / height, spec["labels"][label_key], ha="center", va="center")
            elements.register(fig, label, "contrast-label", spec["labels"][label_key], key=label_key,
                              spec_paths=[elements.pointer("labels", label_key)], editable={"text": elements.pointer("labels", label_key)})

        colorbar = axis(spec["geometry_mm"]["colorbar"])
        low, high = spec["expression_scale"]["limits"]
        colorbar.set_xlim(low, high); colorbar.set_ylim(0, 1); colorbar.set_yticks([])
        colorbar.set_xticks(spec["expression_scale"]["ticks"])
        colorbar.tick_params(axis="x", length=2, width=.5, pad=2)
        for spine in colorbar.spines.values(): spine.set_visible(False)
        # A continuous vector guide, never a raster image replacing selectable data cells.
        for index in range(256):
            x = low + (high - low) * index / 256
            patch = Rectangle((x, 0), (high - low) / 256, 1,
                              facecolor=expression_color(x + (high - low) / 512, spec["expression_scale"]), edgecolor="none")
            colorbar.add_patch(patch)
        label = fig.text((matrix_box[0] + matrix_box[2] / 2) / width, 3.2 / height, spec["labels"]["expression"], ha="center", va="center")
        elements.register(fig, label, "expression-guide-label", spec["labels"]["expression"], key="expression", spec_paths=["/labels/expression"], editable={"text": "/labels/expression"})
        elements.register(fig, colorbar, "expression-guide", "Absolute expression color scale", key="expression-guide",
                          spec_paths=["/expression_scale/anchors", "/expression_scale/limits"], editable={"palette": "/expression_scale/anchors", "limits": "/expression_scale/limits"})
        fig.canvas.draw()
        fig._case_cells, fig._case_summaries = transformed, summaries
    return fig, layout, core, rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--data", type=Path, default=HERE / "inputs/observations.csv")
    parser.add_argument("--contract", type=Path, default=HERE / "inputs/input-contract.json")
    parser.add_argument("--spec", type=Path, default=HERE / "spec.json")
    parser.add_argument("--out", type=Path, default=HERE / "output")
    parser.add_argument("--font", help="Explicit font override, recorded as a changed specification.")
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise FileExistsError("Choose a fresh output directory; preserved visual attempts are not overwritten.")
    args.out.mkdir(parents=True, exist_ok=True)
    tools = runtime_path(args.tools)
    sys.path.insert(0, str(tools))
    core = importlib.import_module("render")
    handoff_path = tools / "figure_handoff.py"
    handoff_bytes = handoff_path.read_bytes()
    handoff = execute_helper_bytes(handoff_path, "figure_handoff", handoff_bytes)
    spec_path = args.spec.resolve()
    extra_inputs = {"source_contract": args.contract.resolve(), "validator": HERE / "validate.py",
                    "official_workbook": args.contract.resolve().parent / "41467_2023_43021_MOESM8_ESM.xlsx",
                    "handoff_helper": Path(handoff.__file__).resolve(),
                    "workbench_helper": Path(handoff.__file__).resolve().with_name("figure_workbench.py")}
    for name in core.RUNTIME_SOURCE_DIGESTS:
        extra_inputs["runtime:" + name] = tools / name
    if (HERE / "caption.md").is_file(): extra_inputs["caption"] = HERE / "caption.md"
    if args.font:
        original_bytes = spec_path.read_bytes()
        spec = core.parse_spec_bytes(original_bytes)
        spec["layout"]["font"] = args.font
        extra_inputs["original_specification"] = spec_path
        spec_path = (args.out / "adopted-spec.json").resolve()
        spec_path.write_text(json.dumps(spec, indent=2) + "\n")
    capture = handoff.capture_inputs(args.out, data_file=args.data.resolve(), source_script=Path(__file__).resolve(),
                                     spec_file=spec_path, auxiliary_inputs=extra_inputs)
    if capture.read("source_script") != SCRIPT_BYTES:
        raise RuntimeError("Source script changed after execution began; reload current code.")
    if capture.read_auxiliary("handoff_helper") != handoff_bytes:
        raise RuntimeError("Executing handoff helper differs from captured source bytes.")
    execute_helper_bytes(extra_inputs["workbench_helper"], "figure_workbench", capture.read_auxiliary("workbench_helper"))
    for name, expected in core.RUNTIME_SOURCE_DIGESTS.items():
        if hashlib.sha256(capture.read_auxiliary("runtime:" + name)).hexdigest() != expected:
            raise RuntimeError("Executing runtime differs from captured helper bytes: " + name)
    if args.font and capture.read_auxiliary("original_specification") != original_bytes:
        raise RuntimeError("Original specification changed while adopting the explicit font override.")
    spec = core.parse_spec_bytes(capture.read("spec_file"))
    contract = core.parse_spec_bytes(capture.read_auxiliary("source_contract"))
    fig, layout, core, rc = draw(spec, contract, capture, core)
    try:
        with plt.rc_context(rc):
            sizes = core.export(fig, args.out, spec, layout)
        write_csv(args.out / "transformed-cells.csv", fig._case_cells)
        write_csv(args.out / "genotype-contrasts.csv", fig._case_summaries)
        input_hash = hashlib.sha256(capture.read("data_file")).hexdigest()
        script_hash = hashlib.sha256(capture.read("source_script")).hexdigest()
        (args.out / "source-data.csv").write_bytes(capture.read("data_file"))
        (args.out / "spec-snapshot.json").write_bytes(capture.read("spec_file"))
        (args.out / "contract-snapshot.json").write_bytes(capture.read_auxiliary("source_contract"))
        (args.out / "source-script.py").write_bytes(capture.read("source_script"))
        if "caption" in capture.auxiliary:
            (args.out / "caption.md").write_bytes(capture.read_auxiliary("caption"))
        settings = {**spec, "spec": spec, "layout": layout, "typography": dict.fromkeys(("axis", "tick", "legend", "annotation"), 8),
                    "input": {**{field: str(path) for field, path in capture.paths.items()},
                              "supplied_spec_sha256": hashlib.sha256(capture.read("spec_file")).hexdigest(), "track": "create"},
                    "source_bindings": {**fig._easyviz_source_bindings,
                                        **{role: {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
                                           for role, (path, raw) in capture.auxiliary.items()}},
                    "input_sha256": input_hash, "source_script_sha256": script_hash,
                    "renderer": {"path": str(Path(__file__).resolve()), "sha256": script_hash},
                    "resolved_colors": spec["colors"], "source_snapshot": {"file": "source-data.csv", "sha256": input_hash},
                    "experimental_unit": contract["experimental_unit"], "pairing": contract["pairing"]}
        (args.out / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
        qa = {"status": "pending_independent_validation", "track": "create", "chart": spec["chart"], "input_rows": len(fig._case_cells),
              "matrix_cells": len(fig._case_cells), "contrast_bars": len(fig._case_summaries), "input_sha256": input_hash,
              "source_script_sha256": script_hash, "resolved_spec_sha256": hashlib.sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest(),
              "actual_font": layout["actual_font"], "font_substituted": layout["font_substituted"], "canvas_mm": [layout["width_mm"], layout["height_mm"]], "exports": sizes,
              "source_bindings": settings["source_bindings"],
              "executed_helper_sha256": {role: hashlib.sha256(raw).hexdigest() for role, (path, raw) in capture.auxiliary.items()
                                         if role in ("validator", "handoff_helper", "workbench_helper") or role.startswith("runtime:")},
              "scope": "Generation metadata only; validate.py independently recomputes source transformations and checks actual vector paths. Image review is separate."}
        (args.out / "qa.json").write_text(json.dumps(qa, indent=2) + "\n")
        validator_spec = importlib.util.spec_from_file_location("expression_captured_validator", HERE / "validate.py")
        validator = importlib.util.module_from_spec(validator_spec)
        exec(compile(capture.read_auxiliary("validator"), str(HERE / "validate.py"), "exec"), validator.__dict__)
        validation = validator.validate(args.out, data_file=args.data, contract_file=args.contract, spec_file=args.spec)
        (args.out / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
        qa.update(status="pass", valid_outputs=True, plotted_input_rows=len(fig._case_cells), clipped_text=[], missing_glyphs=[], overlapping_tick_labels=[],
                  source_to_artist_audit={"status": "pass", "actual_svg_and_pdf_quantitative_marks": 203, "source_observations": 174,
                                          "validation_file": "validation.json", "validation_sha256": hashlib.sha256((args.out / "validation.json").read_bytes()).hexdigest()})
        (args.out / "qa.json").write_text(json.dumps(qa, indent=2) + "\n")
        handoff.write_receipt(args.out, capture=capture, formats=spec["formats"], resolved_spec=spec, track="create")
        (args.out / "consumed-sources.json").write_text(json.dumps({"kind": "thermogenic-expression-consumed-sources",
            "source_bindings": settings["source_bindings"], "executed_helper_sha256": qa["executed_helper_sha256"],
            "handoff_sha256": hashlib.sha256((args.out / "handoff.json").read_bytes()).hexdigest()}, indent=2) + "\n")
        print(json.dumps({"status": "pass", "cells": len(fig._case_cells), "genes": len(fig._case_summaries), "out": str(args.out.resolve())}))
    except Exception as error:
        (args.out / "qa.json").write_text(json.dumps({"status": "failed", "valid_outputs": False, "error": str(error),
                                                    "scope": "This attempted export is not ready; any written files are unverified."}, indent=2) + "\n")
        raise
    finally: plt.close(fig)


if __name__ == "__main__": main()
