#!/usr/bin/env python3
"""Reproduce the two published forest lanes with a shared outcome key.

No author plotting code is used. Input estimates and confidence endpoints are
literal supplied values; only their layout is revised. Pass --runtime when
copying this case outside EasyViz, keeping figure_elements.py alongside it.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

_SCRIPT_SOURCE_BYTES = Path(__file__).read_bytes()
if compile(_SCRIPT_SOURCE_BYTES, str(Path(__file__)), "exec", dont_inherit=True) != sys._getframe().f_code:
    raise RuntimeError("Executing case code differs from the source file; reload current source without stale bytecode.")

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-forest-revision-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullLocator
import numpy as np
from PIL import Image
import pymupdf

BASE = Path(__file__).resolve().parent


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def captured_module(name, path, raw):
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def runtime_path(explicit):
    candidates = [explicit] if explicit else []
    if not explicit:
        for parent in (BASE, *BASE.parents):
            candidates.extend(parent / relative for relative in (
                "runtime", "scripts", "skills/easyviz/scripts"))
    path = next((p for p in candidates if all((p / name).is_file() for name in
                ("figure_elements.py", "figure_handoff.py", "figure_workbench.py"))), None)
    if path is None:
        raise ValueError("This case requires EasyViz >=0.4.6 source-handoff helpers; pass --runtime /path/to/easyviz/scripts.")
    return path.resolve()


def prepare_attempt(args, out):
    tools = runtime_path(args.runtime)
    handoff_path = (tools / "figure_handoff.py").resolve()
    handoff_raw = handoff_path.read_bytes()
    handoff = captured_module("figure_handoff", handoff_path, handoff_raw)
    original_path = args.spec.resolve()
    spec_path = original_path
    auxiliaries = {"figure_elements_helper": (tools / "figure_elements.py").resolve(),
                   "figure_handoff_helper": handoff_path,
                   "figure_workbench_helper": (tools / "figure_workbench.py").resolve()}
    original_raw = None
    if args.font:
        original_raw = original_path.read_bytes()
        adopted = json.loads(original_raw)
        font_manager.findfont(args.font, fallback_to_default=False)
        adopted["font_override"] = {"requested": args.font, "supplied_spec_font": adopted["layout"]["font"],
            "adopted_before_render": True,
            "supplied_spec_binding": {"path": str(original_path), "sha256": hashlib.sha256(original_raw).hexdigest()}}
        adopted["layout"]["font"] = args.font
        adopted["formats"] = ["png", "pdf", "svg"]
        spec_path = out / "adopted-spec.json"
        write_json(spec_path, adopted)
        auxiliaries["original_spec_file"] = original_path
    captured = handoff.capture_inputs(out, data_file=args.data.resolve(), source_script=Path(__file__).resolve(),
                                     spec_file=spec_path, auxiliary_inputs=auxiliaries)
    if captured.read("source_script") != _SCRIPT_SOURCE_BYTES:
        raise ValueError("The executing source changed before byte capture.")
    if captured.read_auxiliary("figure_handoff_helper") != handoff_raw:
        raise ValueError("The loaded source-handoff helper changed before capture.")
    if args.font and captured.read_auxiliary("original_spec_file") != original_raw:
        raise ValueError("The original specification changed during explicit font adoption.")
    elements = captured_module("revision_elements", auxiliaries["figure_elements_helper"],
                               captured.read_auxiliary("figure_elements_helper"))
    captured_module("figure_workbench", auxiliaries["figure_workbench_helper"],
                    captured.read_auxiliary("figure_workbench_helper"))
    snapshots = {role: (captured.read(role), {"path": str(path), "sha256": hashlib.sha256(captured.read(role)).hexdigest()})
                 for role, path in captured.paths.items()}
    snapshots.update({role: (raw, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
                      for role, (path, raw) in captured.auxiliary.items()})
    def continuous():
        return all(Path(binding["path"]).read_bytes() == raw for raw, binding in snapshots.values())
    if not continuous():
        raise ValueError("A consumed source changed before rendering.")
    data_raw, data_binding = snapshots["data_file"]
    spec_raw, spec_binding = snapshots["spec_file"]
    code_binding = snapshots["source_script"][1]
    spec = json.loads(spec_raw)
    spec["formats"] = ["png", "pdf", "svg"]
    (out / "source-data.csv").write_bytes(data_raw)
    (out / "spec-snapshot.json").write_bytes(spec_raw)
    (out / "supplied-spec.json").write_bytes(original_raw if original_raw is not None else spec_raw)
    (out / "source-script.py").write_bytes(captured.read("source_script"))
    (out / "source-inputs").mkdir(exist_ok=True)
    for role, (path, raw) in captured.auxiliary.items():
        (out / "source-inputs" / (role + path.suffix)).write_bytes(raw)
    receipt = {"status": "validated_before_render", "continuity_passed": True,
               "sources": {role: item[1] for role, item in snapshots.items()}}
    write_json(out / "input-receipt.json", receipt)
    return handoff, captured, elements, data_raw, data_binding, spec_raw, spec_binding, code_binding, spec, receipt, continuous


def capture(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return raw, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def load_rows(raw, spec):
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    header = next(reader)
    if len(set(header)) != len(header):
        raise ValueError("Duplicate source headers.")
    required = {"source_row", "source_sheet", "panel", "effect", "exposure", "outcome",
                "estimate", "ci_low", "ci_high", "ci_level", "effect_measure", "null_value", "effect_direction", "n"}
    if set(header) != required:
        raise ValueError("Expected the exact supplied forest table fields.")
    rows = []
    for line_number, fields in enumerate(reader, 2):
        if len(fields) != len(header):
            raise ValueError(f"Malformed source row {line_number}.")
        row = dict(zip(header, fields))
        low, estimate, high = [float(row[key]) for key in ("ci_low", "estimate", "ci_high")]
        if not all(math.isfinite(v) and v > 0 for v in (low, estimate, high)) or not low <= estimate <= high:
            raise ValueError(f"Invalid supplied confidence interval on row {line_number}.")
        if not spec["x_limits"][0] <= low <= high <= spec["x_limits"][1]:
            raise ValueError("The adopted log axis must contain every confidence endpoint.")
        if row["ci_level"] != "0.95" or row["effect_measure"] != "odds ratio" or row["null_value"] != "1":
            raise ValueError("Unexpected supplied statistical semantics.")
        state = "overlaps null" if low <= 1 <= high else "ok"
        if row["effect_direction"] != state or row["n"]:
            raise ValueError("Retain the supplied overlap states and unknown per-estimate sample sizes.")
        rows.append(row)
    expected = {(panel, exposure, outcome) for panel in ("a", "b")
                for exposure in spec["exposures"] for outcome in spec["outcomes"]}
    actual = [(row["panel"], row["exposure"], row["outcome"]) for row in rows]
    if len(rows) != 48 or len(set(actual)) != 48 or set(actual) != expected:
        raise ValueError("The source must contain all 48 unique supplied estimates.")
    if any(row["effect"] != {"a": "Total effect", "b": "Direct effect"}[row["panel"]] for row in rows):
        raise ValueError("Source panel/effect identities disagree.")
    return header, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=BASE.parent / "inputs/source-data.csv")
    parser.add_argument("--spec", type=Path, default=BASE / "adopted-spec.json")
    parser.add_argument("--out", type=Path, default=BASE / "output")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--overwrite", action="store_true", help="Archive an existing attempt before fresh byte capture.")
    parser.add_argument("--font", help="Explicitly adopt another installed font family; no silent fallback.")
    args = parser.parse_args()
    state = {"started": False}
    try:
        return render(args, state)
    except Exception as error:
        if state["started"]:
            out = args.out.resolve()
            write_json(out / "qa.json", {"status": "needs_revision", "valid_outputs": False,
                "technical_passed": False, "error_type": type(error).__name__, "error": str(error)})
            (out / "handoff.json").unlink(missing_ok=True)
            if (out / "elements.json").is_file():
                (out / "elements.json").replace(out / "failed-elements.json")
        raise


def render(args, state):
    out = args.out.resolve()
    existing = any((out / name).exists() for name in ("panel.svg", "panel.pdf", "panel.png", "handoff.json"))
    if existing and not args.overwrite:
        raise FileExistsError("Use a fresh --out directory or --overwrite to archive the previous attempt.")
    if existing:
        from datetime import datetime, timezone
        import shutil
        archive = out.parent / "previous-exports" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") / out.name
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(archive))
    state["started"] = True
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "qa.json", {"technical_passed": False, "status": "in_progress"})
    handoff, captured, elements, data_raw, data_binding, spec_raw, spec_binding, code_binding, spec, receipt, continuous = prepare_attempt(args, out)
    layout = spec["layout"]
    header, rows = load_rows(data_raw, spec)
    font_path = font_manager.findfont(layout["font"], fallback_to_default=False)
    actual_font = font_manager.FontProperties(fname=font_path).get_name()
    plt.rcParams.update({"font.family": actual_font, "font.size": 8,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none", "savefig.bbox": None,
        "axes.unicode_minus": False})
    width, height, dpi = (layout[key] for key in ("width_mm", "height_mm", "dpi"))
    fig = plt.figure(figsize=(width / 25.4, height / 25.4), dpi=dpi, facecolor="white")
    fig._easyviz_track = "reproduce"
    fig._easyviz_data_file = args.data.resolve()
    fig._easyviz_source_script = Path(__file__).resolve()
    fig._easyviz_spec_file = captured.paths["spec_file"]
    fig._easyviz_source_bindings = receipt["sources"].copy()
    spec["formats"] = ["png", "pdf", "svg"]
    write_json(out / "adopted-spec.json", spec)
    receipt.update(status="validated_before_render", continuity_passed=True)
    write_json(out / "input-receipt.json", receipt)
    texts, artist_checks, plotting_rows = [], [], []
    lookup = {(r["panel"], r["exposure"], r["outcome"]): r for r in rows}

    def text(x_mm, y_mm, value, role, key, **kwargs):
        artist = fig.text(x_mm / width, y_mm / height, value, fontsize=spec["typography"][role],
                          va="center", **kwargs)
        elements.register(fig, artist, role, value, key=key, editable=["text", "position"])
        texts.append(artist)
        return artist

    axes = []
    for index, panel in enumerate(("a", "b")):
        left = layout["plot_left_mm"][index]
        ax = fig.add_axes([left / width, layout["plot_bottom_mm"] / height,
                           layout["plot_width_mm"] / width, layout["plot_height_mm"] / height])
        axes.append(ax)
        ax.set_xscale("log")
        ax.set_xlim(spec["x_limits"])
        ax.set_ylim(spec["y_limits"])
        ax.xaxis.set_major_locator(FixedLocator(spec["x_ticks"]))
        ax.set_xticklabels([str(v) for v in spec["x_ticks"]], fontsize=spec["typography"]["tick"])
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_yticks([])
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_linewidth(spec["strokes"]["frame_pt"])
            spine.set_color("#D9D9D9")
        ax.tick_params(axis="x", length=2.5, width=.6, pad=2, color="#777777")
        ax.set_xlabel("Odds ratio", fontsize=spec["typography"]["axis"], labelpad=2.5)
        guide, = ax.plot([2, 2], spec["y_limits"], color="#D9D9D9", linewidth=spec["strokes"]["reference_grid_pt"], zorder=0)
        null = ax.axvline(1, color="#222222", linewidth=spec["strokes"]["null_pt"], linestyle=(0, (3, 3)), zorder=1)
        elements.register(fig, guide, "reference-line", "Odds ratio 2", key=[panel, 2], editable=["color", "linewidth"])
        elements.register(fig, null, "reference-line", "Null odds ratio 1", key=[panel, 1], editable=["color", "linewidth"])
        text(left + layout["plot_width_mm"] / 2, 129, {"a": "Total effect", "b": "Direct effect"}[panel],
             "column_header", panel, ha="center", fontweight=spec["font_weight"]["column_header"])
        for exposure_index, exposure in enumerate(spec["exposures"]):
            first_y = spec["first_y_by_exposure"][exposure_index]
            for outcome_index, outcome in enumerate(spec["outcomes"]):
                row = lookup[(panel, exposure, outcome)]
                y = first_y - outcome_index
                estimate, low, high = [float(row[key]) for key in ("estimate", "ci_low", "ci_high")]
                color = spec["colors"][outcome]
                interval, = ax.plot([low, high], [y, y], color=color, linewidth=spec["strokes"]["interval_pt"],
                                    solid_capstyle="butt", zorder=3)
                filled = row["effect_direction"] == "ok"
                point, = ax.plot([estimate], [y], marker="o", linestyle="none", markersize=spec["marker_diameter_pt"],
                                 markerfacecolor=color if filled else "white", markeredgecolor=color,
                                 markeredgewidth=0 if filled else spec["strokes"]["marker_outline_pt"], zorder=4)
                source_keys = [{"source_row": row["source_row"], "source_sheet": row["source_sheet"],
                                "panel": panel, "exposure": exposure, "outcome": outcome}]
                color_path = elements.pointer("colors", outcome)
                elements.register(fig, interval, "interval", f"{panel} · {exposure} · {outcome} · 95% CI",
                    key=[panel, exposure, outcome], source_keys=source_keys,
                    spec_paths=[color_path, "/strokes/interval_pt"], editable={"color": color_path, "linewidth": "/strokes/interval_pt"})
                elements.register(fig, point, "point", f"{panel} · {exposure} · {outcome}",
                    key=[panel, exposure, outcome], source_keys=source_keys,
                    spec_paths=[color_path, "/marker_diameter_pt"], editable={"color": color_path, "markersize": "/marker_diameter_pt"})
                point_ok = np.array_equal(point.get_xdata(), [estimate]) and np.array_equal(point.get_ydata(), [y])
                interval_ok = np.array_equal(interval.get_xdata(), [low, high]) and np.array_equal(interval.get_ydata(), [y, y])
                artist_checks.append({"source_row": row["source_row"], "point_matches": bool(point_ok),
                    "interval_matches": bool(interval_ok), "fill_matches": bool((point.get_markerfacecolor() != "white") == filled),
                    "x": estimate, "ci_low": low, "ci_high": high, "y": y})
                plotting_rows.append({**row, "plot_y": y, "marker_fill": "filled" if filled else "hollow"})
    for exposure_index, exposure in enumerate(spec["exposures"]):
        middle_y = spec["first_y_by_exposure"][exposure_index] - 3.5
        y_mm = layout["plot_bottom_mm"] + layout["plot_height_mm"] * (middle_y - spec["y_limits"][0]) / (spec["y_limits"][1] - spec["y_limits"][0])
        text(13, y_mm, exposure, "exposure", exposure, rotation=90, ha="center")
    text(3.4, layout["plot_bottom_mm"] + layout["plot_height_mm"] / 2, "Exposure", "axis", "exposure-axis",
         rotation=90, ha="center", fontweight=spec["font_weight"]["shared_variable_header"])
    text(14, 23.5, "Outcome", "legend", "outcome-variable", ha="left", fontweight=spec["font_weight"]["shared_variable_header"])
    for index, outcome in enumerate(spec["outcomes"]):
        x, y = (14 if index < 4 else 61), (19 - 4 * (index % 4))
        # Figure transforms keep one shared lookup aligned independently of either lane.
        key = Line2D([(x - 1.5) / width, x / width, (x + 1.5) / width], [y / height] * 3,
                     transform=fig.transFigure, color=spec["colors"][outcome], linewidth=.8,
                     marker="o", markevery=[1], markersize=spec["marker_diameter_pt"], markeredgewidth=0)
        fig.add_artist(key)
        path = elements.pointer("colors", outcome)
        elements.register(fig, key, "legend-key", outcome, key=outcome,
                          source_keys=[{"outcome": outcome}], spec_paths=[path], editable={"color": path})
        text(x + 4, y, outcome, "legend", outcome, ha="left")
    elements.attach_layout(fig, spec)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    all_text = [artist for artist in fig.findobj(matplotlib.text.Text) if artist.get_visible() and artist.get_text().strip()]
    boxes = [(t, t.get_window_extent(renderer)) for t in all_text]
    outside = [t.get_text() for t, b in boxes if b.x0 < 0 or b.y0 < 0 or b.x1 > fig.bbox.x1 or b.y1 > fig.bbox.y1]
    overlaps = [[a.get_text(), b.get_text()] for i, (a, ab) in enumerate(boxes) for b, bb in boxes[i + 1:] if ab.overlaps(bb)]
    expected = [round(width / 25.4 * dpi), round(height / 25.4 * dpi)]
    for extension in ("pdf", "svg"):
        fig.savefig(out / f"panel.{extension}", bbox_inches=None, pad_inches=0)
    # Quantize only the raster canvas to the declared 300 dpi pixel grid.
    fig.set_size_inches(expected[0] / dpi, expected[1] / dpi)
    fig.savefig(out / "panel.png", dpi=dpi, bbox_inches=None, pad_inches=0)
    fig.set_size_inches(width / 25.4, height / 25.4)
    manifest = elements.write(fig, out, spec, layout)
    manifest["input"]["auxiliary_inputs"] = {role: receipt["sources"][role] for role in captured.auxiliary}
    manifest["version"] = handoff.bound_version(manifest["version"], manifest["input"])
    write_json(out / "elements.json", manifest)
    plt.close(fig)
    (out / "source-data.csv").write_bytes(data_raw)
    with (out / "plotting-data.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=header + ["plot_y", "marker_fill"])
        writer.writeheader()
        writer.writerows(plotting_rows)
    with pymupdf.open(out / "panel.pdf") as document:
        page = document[0]
        pdf_mm = [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]
        spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b for line in b["lines"] for s in line["spans"]]
        sizes = sorted({round(s["size"], 4) for s in spans})
        embedded = all(bool(document.extract_font(f[0])[3]) for f in page.get_fonts())
    svg = ET.parse(out / "panel.svg").getroot()
    svg_mm = [float(svg.attrib[key].removesuffix("pt")) * 25.4 / 72 for key in ("width", "height")]
    with Image.open(out / "panel.png") as image:
        image.load()
        pixels = list(image.size)
        png_dpi = list(image.info["dpi"])
    continuity = continuous()
    receipt.update(status="passed" if continuity else "failed", continuity_passed=continuity)
    write_json(out / "input-receipt.json", receipt)
    checks = {"source_coverage": len(plotting_rows) == 48,
        "live_artists": all(all(row[k] for k in ("point_matches", "interval_matches", "fill_matches")) for row in artist_checks),
        "source_continuity": continuity, "pdf_canvas": bool(np.allclose(pdf_mm, [width, height], atol=.001)),
        "svg_canvas": bool(np.allclose(svg_mm, [width, height], atol=.001)), "png_canvas": pixels == expected,
        "pdf_fonts": sizes == [8.0] and embedded, "editable_svg_text": bool(svg.findall('.//{http://www.w3.org/2000/svg}text')),
        "text_bounds": not outside, "text_overlap": not overlaps}
    write_json(out / "artist-checks.json", {"rows": artist_checks, "coverage": 48})
    write_json(out / "settings.json", {**spec, "adopted_spec": spec, "actual_font": actual_font, "font_file": font_path,
        "layout": {**layout, "actual_font": actual_font, "font_substituted": False},
        "input": {"data_file": str(captured.paths["data_file"]), "spec_file": str(captured.paths["spec_file"]),
                  "source_script": str(captured.paths["source_script"]), "supplied_spec_sha256": spec_binding["sha256"],
                  "auxiliary_inputs": {role: receipt["sources"][role] for role in captured.auxiliary}},
        "version": {"input_sha256": data_binding["sha256"], "source_script_sha256": code_binding["sha256"]},
        "source_snapshot": {"file": "source-data.csv", "sha256": data_binding["sha256"]},
        "font_override": spec.get("font_override"), "source_bindings": receipt["sources"]})
    write_json(out / "stats.json", {"source_rows": 48, "estimates_per_lane": 24, "confidence_level": .95,
        "unknown_per_estimate_n": 48, "new_inference": False, "excluded_rows": 0, "imputed_rows": 0,
        "source_binding": data_binding, "description": "Only supplied univariable and multivariable MR estimates/95% confidence intervals."})
    qa = {"technical_passed": all(checks.values()), "visual_status": "requires_independent_review",
        "checks": checks, "measurements": {"pdf_mm": pdf_mm, "svg_mm": svg_mm, "png_pixels": pixels,
            "expected_pixels": expected, "pdf_font_sizes_pt": sizes, "pdf_fonts_embedded": embedded,
            "text_outside": outside, "text_overlap": overlaps}, "sources": receipt["sources"],
        "limits": ["Text checks do not prove all text–mark relationships or aesthetic quality.",
                   "The source forest glyphs are outlined, so source font sizes are unknown."]}
    qa.update(status="pass" if qa["technical_passed"] else "needs_revision", valid_outputs=qa["technical_passed"],
              source_bindings=receipt["sources"], input_sha256=data_binding["sha256"],
              input_rows=len(rows), plotted_input_rows=len(rows))
    qa["exports"] = {extension: {"sha256": hashlib.sha256((out / ("panel." + extension)).read_bytes()).hexdigest(),
        **({"pixels": pixels, "dpi": png_dpi} if extension == "png" else
           {"width_mm": (pdf_mm if extension == "pdf" else svg_mm)[0],
            "height_mm": (pdf_mm if extension == "pdf" else svg_mm)[1]})} for extension in ("png", "pdf", "svg")}
    write_json(out / "qa.json", qa)
    if qa["technical_passed"]:
        handoff.write_receipt(out, capture=captured, formats=["png", "pdf", "svg"], resolved_spec=spec, track="reproduce")
    print(json.dumps({"output": str(out), "technical_passed": qa["technical_passed"], "checks": checks}))
    if not qa["technical_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
