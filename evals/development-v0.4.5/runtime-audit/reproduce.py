#!/usr/bin/env python3
"""Actual current-main runtime audit; preserve exports and machine evidence.

This is a bug reproduction exercise, not a model-quality or aesthetic benchmark.
No runtime or tests are modified by this script.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import warnings
import zlib

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / (sys.argv[1] if len(sys.argv) > 1 else "reproduced")
SCRIPTS = ROOT / "skills/easyviz/scripts"


def module(name, filename):
    loader = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


core = module("runtime_audit_core", "render.py")
review = module("runtime_audit_review", "create_review.py")
replicate = module("runtime_audit_replicate", "replicate_plot.py")


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def case(name, csv, spec):
    folder = OUT / name
    folder.mkdir(exist_ok=False)
    source = folder / "input.csv"
    source.write_text(csv)
    save(folder / "spec.json", spec)
    (folder / "caption.md").write_text("Bug reproduction only. Each source record is retained; no inferential test is requested.\n")
    return folder, source


SCATTER = {
    "chart": "scatter", "fields": {"x": "x", "y": "y"},
    "layout": {"width_mm": 88, "height_mm": 66, "dpi": 160, "font": "DejaVu Sans"},
    "labels": {"x": "X", "y": "Y"}, "formats": ["png", "svg", "pdf"],
    "options": {"point_area_pt2": 36, "alpha": 1},
}


def render(folder, source, spec):
    return core.render(source, deepcopy(spec), folder / "output", spec_path=folder / "spec.json", track="create")


def main():
    OUT.mkdir(exist_ok=False)
    findings = {}
    # Core source changes after prepare/draw but before exporter saves bindings.
    original = "x,y\n1,2\n2,3\n3,5\n4,4\n"
    changed = "x,y\n1,200\n2,300\n3,500\n4,400\n"
    folder, source = case("01-source-race", original, SCATTER)
    (folder / "before.csv").write_text(original)
    (folder / "after.csv").write_text(changed)
    actual_export = core.export

    def source_changed_during_export(fig, out, spec, layout):
        source.write_text(changed)
        return actual_export(fig, out, spec, layout)

    core.export = source_changed_during_export
    try:
        qa = render(folder, source, SCATTER)
    finally:
        core.export = actual_export
    snapshot = review.snapshot(folder / "output", caption=folder / "caption.md")
    settings = json.loads((folder / "output/settings.json").read_text())
    plotted = core.pd.read_csv(folder / "output/plotting-data.csv")
    findings["source_race"] = {
        "qa_status": qa["status"], "valid_outputs": qa["valid_outputs"],
        "plotted_y": plotted["y"].tolist(), "current_source_y": core.pd.read_csv(source)["y"].tolist(),
        "settings_source_hash": settings["input_sha256"], "before_hash": digest(original.encode()),
        "after_hash": digest(changed.encode()),
        "review_source_provenance_status": snapshot["measured_checks"]["source_provenance"]["status"],
    }
    save(folder / "snapshot.json", snapshot)

    # Pandas infers an unannounced index when every row has one extra cell.
    folder, source = case("02-ragged-csv", "x,y\n1,2,9\n2,4,8\n3,6,7\n", SCATTER)
    qa = render(folder, source, SCATTER)
    data = core.prepare(source, SCATTER)
    findings["ragged_csv"] = {
        "qa_status": qa["status"], "valid_outputs": qa["valid_outputs"],
        "input_rows_claim": qa["input_rows"], "inferred_index": data.index.tolist(),
        "mapped_x": data["x"].tolist(), "mapped_y": data["y"].tolist(),
        "raw_csv": source.read_text(),
    }
    # A focused source-to-artist audit rejects duplicate headers late; core does not.
    dup = {"chart": "replicate", "fields": {"condition": "arm", "unit": "id", "value": "value"},
           "options": {"mode": "summary", "uncertainty": "sample_sd"},
           "layout": {"width_mm": 88, "height_mm": 66, "dpi": 160, "font": "DejaVu Sans", "auto_fit": True},
           "formats": ["png", "svg", "pdf"]}
    folder, source = case("03-duplicate-csv-header", "arm,id,value,value\nA,01,2,200\nA,02,3,300\nB,01,4,400\nB,02,5,500\n", dup)
    try:
        replicate.render(source, dup, folder / "output", spec_path=folder / "spec.json")
        focused_exception = None
    except Exception as exc:
        focused_exception = str(exc)
    qa = json.loads((folder / "output/qa.json").read_text())
    data = replicate.prepare(source, dup)
    core_dup = {**deepcopy(SCATTER), "chart": "distribution", "fields": {"group": "arm", "value": "value"},
                "labels": {"x": "Arm", "y": "Value"}, "options": {"kind": "box", "point_area_pt2": 12}}
    save(folder / "core-spec.json", core_dup)
    core_qa = core.render(source, core_dup, folder / "core-output", spec_path=folder / "core-spec.json", track="create")
    findings["duplicate_header"] = {
        "focused_qa_status": qa["status"], "focused_valid_outputs": qa["valid_outputs"], "focused_exception": focused_exception,
        "core_qa_status": core_qa["status"], "core_valid_outputs": core_qa["valid_outputs"],
        "parsed_columns": data.columns.tolist(), "mapped_values": data["value"].tolist(),
        "second_literal_value_column": data["value.1"].tolist(),
    }

    # Finite source values can overflow finite pandas group sums silently.
    comp = {"chart": "composition", "fields": {"sample": "sample", "category": "category", "value": "value"},
            "options": {"normalization": "sample_sum"},
            "layout": {"width_mm": 88, "height_mm": 66, "dpi": 160, "font": "DejaVu Sans", "auto_fit": True},
            "formats": ["png", "svg", "pdf"]}
    for label, csv in (
        ("04-float-composition-overflow", "sample,category,value\nA,c1,1e308\nA,c2,1e308\n"),
        ("05-integer-composition-overflow", "sample,category,value\nA,c1,18000000000000000000\nA,c2,1000000000000000000\n"),
    ):
        folder, source = case(label, csv, comp)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            data = core.prepare(source, comp)
            try:
                qa = render(folder, source, comp)
                status = {"qa_status": qa["status"], "valid_outputs": qa["valid_outputs"]}
            except Exception as exc:
                status = {"render_exception": str(exc)}
        findings[label] = {
            **status, "value_dtype": str(data["value"].dtype),
            "denominator": [str(x) for x in data["_easyviz_denominator"]],
            "plotted_fractions": data["_easyviz_plotted_value"].tolist(),
            "fraction_sum": float(data["_easyviz_plotted_value"].sum()),
            "warnings": [str(item.message) for item in captured],
        }

    # Valid numeric centers at explicit limits still lose half their glyph.
    clipped = deepcopy(SCATTER)
    clipped["options"].update(point_area_pt2=100, x_limits=[0, 1], y_limits=[0, 1])
    folder, source = case("06-numeric-marker-clipping", "x,y\n0,0\n0.5,0.5\n1,1\n", clipped)
    qa = render(folder, source, clipped)
    data = core.prepare(source, clipped)
    layout, typography, rc = core.setup(clipped)
    with core.plt.rc_context(rc):
        fig, _ = core.draw(data, clipped, layout, typography, core.statistics(data, clipped))
        fig.canvas.draw()
        ax = fig.axes[0]
        painter = fig.canvas.get_renderer()
        plot = ax.get_window_extent(painter)
        centers = ax.transData.transform(data[["x", "y"]].to_numpy(float))
        radius_px = 5 * fig.dpi / 72
        cuts = []
        for index, (x, y) in enumerate(centers, 1):
            deficits = {"left": plot.x0 - (x - radius_px), "right": (x + radius_px) - plot.x1,
                        "bottom": plot.y0 - (y - radius_px), "top": (y + radius_px) - plot.y1}
            positive = {key: value * 25.4 / fig.dpi for key, value in deficits.items() if value > 1e-8}
            if positive:
                cuts.append({"row": index, "clipped_outer_footprint_mm": positive})
        core.plt.close(fig)
    findings["numeric_marker_clipping"] = {
        "qa_status": qa["status"], "valid_outputs": qa["valid_outputs"],
        "clipped_marker_rows": cuts,
        "qa_clipped_text": qa["clipped_text"],
    }

    # PNG structural headers can describe a non-decodable image; no IDAT.
    folder, source = case("07-png-no-image-payload", original, SCATTER)
    qa = render(folder, source, SCATTER)
    png = folder / "output/panel.png"
    measured = review.png_measurement(png.read_bytes())
    ihdr = struct.pack(">IIBBBBB", *measured["pixels"], 8, 2, 0, 0, 0)
    ppm = round(160 / .0254)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)

    invalid_png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1)) + chunk(b"IEND", b"")
    png.write_bytes(invalid_png)
    qa["exports"]["png"].update(sha256=digest(invalid_png), **measured)
    save(folder / "output/qa.json", qa)
    snapshot = review.snapshot(folder / "output", caption=folder / "caption.md")
    try:
        with core.Image.open(png) as im:
            im.load()
        actual_decode = "passed"
    except Exception as exc:
        actual_decode = type(exc).__name__ + ": " + str(exc)
    findings["nondecodable_png"] = {
        "actual_png_decode": actual_decode,
        "review_export_dimensions_status": snapshot["measured_checks"]["export_dimensions"]["status"],
        "review_technical_qa_status": snapshot["measured_checks"]["technical_qa"]["status"],
        "actual_bytes": len(invalid_png), "actual_png_header_measurement": review.png_measurement(invalid_png),
    }
    save(folder / "snapshot.json", snapshot)
    save(OUT / "results.json", {
        "scope": "Actual minimal current-main runtime reproductions; no aesthetic efficacy claims.",
        "runtime_hashes": {name: digest((SCRIPTS / name).read_bytes()) for name in ("render.py", "create_review.py", "replicate_plot.py")},
        "findings": findings,
    })
    print(json.dumps(findings, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
