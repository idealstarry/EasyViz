#!/usr/bin/env python3
"""Compact, source-bound reproduction of the selected depot kBET radar.

Only supplied acceptance rates are used. No author code, integration, uncertainty
estimate, rank test, central jitter or inferred inner radial padding is used.
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

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "easyviz-radar-revision-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle
import numpy as np
from PIL import Image
import pymupdf

BASE = Path(__file__).resolve().parent


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def capture(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return raw, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


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




def load_rows(raw, spec):
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    header = next(reader)
    if header != ["integration_method", "cell_class", "acceptance_rate"]:
        raise ValueError("Expected the exact supplied acceptance-rate fields.")
    rows = []
    for line_number, fields in enumerate(reader, 2):
        if len(fields) != len(header):
            raise ValueError(f"Malformed source row {line_number}.")
        row = dict(zip(header, fields))
        value = float(row["acceptance_rate"])
        if not math.isfinite(value) or not spec["radial_limits"][0] <= value <= spec["radial_limits"][1]:
            raise ValueError("The fixed zero-origin scale must contain every supplied acceptance rate.")
        row["source_row"] = str(line_number)
        rows.append(row)
    expected = {(m["source"], c["source"]) for m in spec["methods"] for c in spec["classes"]}
    actual = [(r["integration_method"], r["cell_class"]) for r in rows]
    if len(rows) != 25 or len(set(actual)) != 25 or set(actual) != expected:
        raise ValueError("Source must contain all 25 unique method–class pairs.")
    return rows


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
    rows = load_rows(data_raw, spec)
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
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, width), ylim=(0, height), aspect="equal")
    ax.axis("off")
    ax.set_axisbelow(True)
    cx, cy = layout["center_mm"]
    radius = layout["radius_mm"]
    maximum = spec["radial_limits"][1]
    if spec["radial_limits"][0] != 0:
        raise ValueError("This reproduction retains a true zero radial origin.")
    angles = 90 - np.arange(5) * 72
    theta = np.deg2rad(angles)
    direction = np.column_stack([np.cos(theta), np.sin(theta)])
    ax.add_patch(Circle((cx, cy), radius, facecolor=spec["colors"]["background"], edgecolor="none", zorder=0))
    for index, (dx, dy) in enumerate(direction):
        spoke, = ax.plot([cx, cx + radius * dx], [cy, cy + radius * dy],
                        color=spec["colors"]["spokes"], linewidth=layout["grid_line_width_pt"], zorder=1)
        elements.register(fig, spoke, "axis-line", spec["classes"][index]["display"], key=index,
            editable=["color", "linewidth"])
    for value in spec["radial_ticks"][1:]:
        color = spec["colors"]["intermediate_ring"] if value != maximum else spec["colors"]["spokes"]
        ring = Circle((cx, cy), radius * value / maximum, fill=False, edgecolor=color,
                      linewidth=layout["grid_line_width_pt"], linestyle=(0, (4, 3)), zorder=1)
        ax.add_patch(ring)
        elements.register(fig, ring, "reference-line", f"Acceptance rate {value:g}", key=value,
                          editable=["color", "linewidth"])
    lookup = {(r["integration_method"], r["cell_class"]): r for r in rows}
    artist_checks, plotted_rows = [], []
    for index, method in enumerate(spec["methods"]):
        ordered_rows = [lookup[(method["source"], cell["source"])] for cell in spec["classes"]]
        rates = np.array([float(row["acceptance_rate"]) for row in ordered_rows])
        points = np.array([cx, cy]) + (radius * rates / maximum)[:, None] * direction
        closed = np.vstack([points, points[0]])
        line, = ax.plot(closed[:, 0], closed[:, 1], color=method["color"], linewidth=layout["line_width_pt"], zorder=3 + index * .1)
        point_artist, = ax.plot(points[:, 0], points[:, 1], linestyle="none", marker="o",
            markersize=layout["marker_diameter_pt"], markeredgewidth=0, color=method["color"], zorder=4 + index * .1)
        path = elements.pointer("methods", index, "color")
        source_keys = [{"source_row": row["source_row"], "integration_method": row["integration_method"],
                        "cell_class": row["cell_class"]} for row in ordered_rows]
        elements.register(fig, line, "data-line", method["display"], key=method["source"], source_keys=source_keys,
                          spec_paths=[path, "/layout/line_width_pt"], editable={"color": path, "linewidth": "/layout/line_width_pt"})
        elements.register(fig, point_artist, "point-group", method["display"], key=method["source"], source_keys=source_keys,
                          spec_paths=[path, "/layout/marker_diameter_pt"], editable={"color": path, "markersize": "/layout/marker_diameter_pt"})
        line_ok = np.array_equal(np.column_stack([line.get_xdata(), line.get_ydata()]), closed)
        points_ok = np.array_equal(np.column_stack([point_artist.get_xdata(), point_artist.get_ydata()]), points)
        artist_checks.append({"method": method["source"], "closed_trace_matches": bool(line_ok), "points_match": bool(points_ok)})
        for cell_index, (cell, row) in enumerate(zip(spec["classes"], ordered_rows)):
            plotted_rows.append({**row, "method_label": method["display"], "class_label": cell["display"],
                "angle_degrees": int(angles[cell_index]), "x_mm": float(points[cell_index, 0]), "y_mm": float(points[cell_index, 1])})

    texts = []
    def label(x, y, value, role, key, **kwargs):
        artist = ax.text(x, y, value, fontsize=spec["typography"][role], va="center", zorder=10, **kwargs)
        elements.register(fig, artist, f"{role}-label", value, key=key, editable=["text", "position"])
        texts.append(artist)
        return artist
    label(cx, 60, "all", "axis", "ALL", ha="center")
    label(cx + radius * direction[1, 0] + 1.5, cy + radius * direction[1, 1], "FAPs", "axis", "FAP", ha="left")
    label(cx + radius * direction[4, 0] - 1.5, cy + radius * direction[4, 1], "adipocytes", "axis", "ADIPOCYTES", ha="right")
    label(43.7, 23.5, "vascular", "axis", "ENDO", ha="left")
    label(21.3, 23.5, "immune", "axis", "IMMUNE", ha="right")
    for value in spec["radial_ticks"]:
        label(cx - 2.4, cy + radius * value / maximum, f"{value:g}", "tick", value, ha="right")
    label(cx, 17, "kBET acceptance rate", "axis", "metric", ha="center")
    legend_positions = [(3, 10), (23, 10), (48, 10), (14, 5), (37, 5)]
    for index, (method, (x, y)) in enumerate(zip(spec["methods"], legend_positions)):
        key, = ax.plot([x, x + 2, x + 4], [y, y, y], color=method["color"], linewidth=layout["line_width_pt"],
                       marker="o", markevery=[1], markersize=layout["marker_diameter_pt"], markeredgewidth=0, zorder=5)
        path = elements.pointer("methods", index, "color")
        elements.register(fig, key, "legend-key", method["display"], key=method["source"], spec_paths=[path], editable={"color": path})
        label(x + 5.5, y, method["display"], "legend", method["source"], ha="left")
    elements.attach_layout(fig, spec)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [(t, t.get_window_extent(renderer)) for t in texts]
    outside = [t.get_text() for t, b in boxes if b.x0 < 0 or b.y0 < 0 or b.x1 > fig.bbox.x1 or b.y1 > fig.bbox.y1]
    overlaps = [[a.get_text(), b.get_text()] for i, (a, ab) in enumerate(boxes) for b, bb in boxes[i + 1:] if ab.overlaps(bb)]
    if not continuous():
        raise ValueError("A consumed source changed before export.")
    expected = [round(width / 25.4 * dpi), round(height / 25.4 * dpi)]
    for extension in ("pdf", "svg"):
        fig.savefig(out / f"panel.{extension}", bbox_inches=None, pad_inches=0)
    fig.set_size_inches(expected[0] / dpi, expected[1] / dpi)
    fig.savefig(out / "panel.png", dpi=dpi, bbox_inches=None, pad_inches=0)
    fig.set_size_inches(width / 25.4, height / 25.4)
    manifest = elements.write(fig, out, spec, layout)
    manifest["input"]["auxiliary_inputs"] = {role: receipt["sources"][role] for role in captured.auxiliary}
    manifest["version"] = handoff.bound_version(manifest["version"], manifest["input"])
    write_json(out / "elements.json", manifest)
    plt.close(fig)
    (out / "source-data.csv").write_bytes(data_raw)
    columns = ["integration_method", "cell_class", "acceptance_rate", "source_row", "method_label", "class_label", "angle_degrees", "x_mm", "y_mm"]
    with (out / "plotting-data.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(plotted_rows)
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
    checks = {"source_coverage": len(plotted_rows) == 25,
        "live_artists": all(row["closed_trace_matches"] and row["points_match"] for row in artist_checks),
        "source_continuity": continuity, "pdf_canvas": bool(np.allclose(pdf_mm, [width, height], atol=.001)),
        "svg_canvas": bool(np.allclose(svg_mm, [width, height], atol=.001)), "png_canvas": pixels == expected,
        "pdf_fonts": sizes == [8.0] and embedded, "editable_svg_text": bool(svg.findall('.//{http://www.w3.org/2000/svg}text')),
        "text_bounds": not outside, "text_overlap": not overlaps}
    write_json(out / "artist-checks.json", {"methods": artist_checks, "vertices": plotted_rows})
    write_json(out / "settings.json", {**spec, "adopted_spec": spec, "actual_font": actual_font, "font_file": font_path,
        "layout": {**layout, "actual_font": actual_font, "font_substituted": False},
        "input": {"data_file": str(captured.paths["data_file"]), "spec_file": str(captured.paths["spec_file"]),
                  "source_script": str(captured.paths["source_script"]), "supplied_spec_sha256": spec_binding["sha256"],
                  "auxiliary_inputs": {role: receipt["sources"][role] for role in captured.auxiliary}},
        "version": {"input_sha256": data_binding["sha256"], "source_script_sha256": code_binding["sha256"]},
        "source_snapshot": {"file": "source-data.csv", "sha256": data_binding["sha256"]},
        "font_override": spec.get("font_override"), "source_bindings": receipt["sources"]})
    rates = [float(row["acceptance_rate"]) for row in rows]
    write_json(out / "stats.json", {"source_rows": 25, "method_count": 5, "class_count": 5,
        "zero_values": sum(value == 0 for value in rates), "minimum": min(rates), "maximum": max(rates),
        "new_inference": False, "excluded_rows": 0, "imputed_rows": 0, "source_binding": data_binding,
        "description": "Only supplied kBET acceptance rates; upstream integration is not rerun."})
    qa = {"technical_passed": all(checks.values()), "visual_status": "requires_independent_review",
        "checks": checks, "measurements": {"pdf_mm": pdf_mm, "svg_mm": svg_mm, "png_pixels": pixels,
            "expected_pixels": expected, "pdf_font_sizes_pt": sizes, "pdf_fonts_embedded": embedded,
            "text_outside": outside, "text_overlap": overlaps}, "sources": receipt["sources"],
        "limits": ["Text checks do not prove all text–mark relationships or aesthetic quality.",
                   "Three valid zeros coincide at the origin; no jitter or negative radial padding is inferred."]}
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
