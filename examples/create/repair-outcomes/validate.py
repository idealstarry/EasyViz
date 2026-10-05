#!/usr/bin/env python3
"""Check every source value, summary artist and saved export in both real cases."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev
import xml.etree.ElementTree as ET

from PIL import Image
import pymupdf

from plot import HERE, renderer, runtime_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(source, output, spec, plotter):
    raw = list(csv.DictReader((source / "source-data.csv").open(newline="")))
    f = spec["fields"]
    qa = json.loads((output / "qa.json").read_text())
    assert qa["status"] == "pass" and qa["input_rows"] == len(raw)
    assert qa["input_sha256"] == digest(source / "source-data.csv")
    exported = list(csv.DictReader((output / "plotting-data.csv").open(newline="")))
    assert len(exported) == len(raw)
    for wanted, actual in zip(raw, exported):
        assert all(actual[key] == value for key, value in wanted.items() if key != f["value"])
        assert actual["_easyviz_source_value_text"] == wanted[f["value"]]
        assert math.isclose(float(actual[f["value"]]), float(wanted[f["value"]]), rel_tol=1e-12)
    data = plotter.prepare(source / "source-data.csv", spec)
    layout, typography, rc = plotter.core.setup(spec)
    with plotter.plt.rc_context(rc):
        fig, _ = plotter.draw(data, spec, layout, typography)
        try:
            audit = plotter.audit_source_artists(source / "source-data.csv", spec, fig)
            assert audit["status"] == "pass", audit
            for record in fig._easyviz_replicate_summary:
                values = [float(row[f["value"]]) for row in raw
                          if row[f["condition"]] == record["condition"] and
                          ("component" not in f or row[f["component"]] == record["component"])]
                assert len(values) == 3
                assert math.isclose(record["mean"], mean(values), rel_tol=1e-12)
                assert math.isclose(record["sample_sd"], stdev(values), rel_tol=1e-12)
            assert list(fig.axes[0].get_ylim()) == spec["options"]["y_limits"]
        finally:
            plotter.plt.close(fig)
    expected = [spec["layout"]["width_mm"], spec["layout"]["height_mm"]]
    with pymupdf.open(output / "panel.pdf") as doc:
        page = doc[0]
        dimensions = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
        assert all(abs(a - b) < .001 for a, b in zip(dimensions, expected))
        assert all(doc.extract_font(font[0])[3] for font in page.get_fonts())
        spans = [span for block in page.get_text("dict")["blocks"] if block["type"] == 0
                 for line in block["lines"] for span in line["spans"]]
        assert spans and all(math.isclose(span["size"], 8, abs_tol=.001) for span in spans)
        font_name = spec["layout"]["font"].replace(" ", "").casefold()
        assert all(span["font"].replace(" ", "").casefold().startswith(font_name) for span in spans)
    svg = ET.parse(output / "panel.svg").getroot()
    assert svg.findall(".//{http://www.w3.org/2000/svg}text")
    assert all(abs(float(svg.attrib[key].removesuffix("pt")) / 72 * 25.4 - mm) < .001
               for key, mm in zip(("width", "height"), expected))
    with Image.open(output / "panel.png") as image:
        assert all(abs(value - 300) < .01 for value in image.info["dpi"])
        assert all(abs(a - b) <= 1 for a, b in zip(image.size, [round(mm / 25.4 * 300) for mm in expected]))
    return {"status": "pass", "source_rows": len(raw), "source_value_strings_preserved": True,
            "per_outcome_mean_sample_sd": True, "source_to_artist": audit,
            "dimensions_mm": expected, "font": spec["layout"]["font"], "font_size_pt": 8,
            "pdf_embedded_fonts": True, "svg_editable_text": True, "png_dpi": 300,
            "global_y_limits": spec["options"]["y_limits"],
            "exports_sha256": {name: digest(output / ("panel." + name)) for name in ("png", "pdf", "svg")}}


def check_composition(output, panel_outputs):
    expected_spans = []
    left = 0
    for folder in panel_outputs:
        with pymupdf.open(folder / "panel.pdf") as doc:
            page = doc[0]
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            expected_spans.append((span["text"], span["size"],
                                [span["bbox"][0] + left, span["bbox"][1], span["bbox"][2] + left, span["bbox"][3]]))
            left += page.rect.width
    with pymupdf.open(output / "panel.pdf") as doc:
        assert len(doc) == 1 and math.isclose(doc[0].rect.width, left, abs_tol=.001)
        actual = [span for block in doc[0].get_text("dict")["blocks"] if block["type"] == 0
                  for line in block["lines"] for span in line["spans"]]
        assert len(actual) == len(expected_spans)
        for (text, size, bbox), span in zip(expected_spans, actual):
            assert span["text"] == text and math.isclose(span["size"], size, abs_tol=.001)
            assert all(math.isclose(a, b, abs_tol=.002) for a, b in zip(bbox, span["bbox"]))
        assert all(doc.extract_font(font[0])[3] for font in doc[0].get_fonts())
    svg = ET.parse(output / "panel.svg").getroot()
    ids = [node.attrib["id"] for node in svg.iter() if "id" in node.attrib]
    assert len(ids) == len(set(ids)), "Composed SVG identifiers collide"
    with Image.open(output / "panel.png") as image:
        assert all(abs(value - 300) < .01 for value in image.info["dpi"])
    return {"status": "pass", "panel_count": len(panel_outputs), "individual_sizes_retained": True,
            "all_pdf_text_and_physical_positions_preserved": True, "all_pdf_fonts_embedded": True,
            "svg_ids_unique": True, "data_redrawn": False, "original_font_sizes_retained": True,
            "exports_sha256": {name: digest(output / ("panel." + name)) for name in ("png", "pdf", "svg")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--outputs", type=Path, default=HERE)
    parser.add_argument("--font")
    parser.add_argument("--out", type=Path, default=HERE / "validation.json")
    args = parser.parse_args()
    plotter = renderer(runtime_path(args.tools))
    records = []
    for role, source, destination in [("candidate", HERE, args.outputs),
                                     ("transfer", HERE / "transfer", args.outputs / "transfer")]:
        spec = json.loads((source / "spec.json").read_text())
        if args.font:
            spec["layout"]["font"] = args.font
        grouped = check(source, destination / "grouped-output", spec, plotter)
        panels, panel_outputs = [], []
        for panel in json.loads((source / "panel-manifest.json").read_text())["panels"]:
            panel_source = source / "panels" / panel["id"]
            panel_output = destination / "panels" / panel["id"] / "output"
            panel_spec = json.loads((panel_source / "spec.json").read_text())
            if args.font:
                panel_spec["layout"]["font"] = args.font
            panels.append({"id": panel["id"], **check(panel_source, panel_output, panel_spec, plotter)})
            panel_outputs.append(panel_output)
        assert sum(panel["source_rows"] for panel in panels) == grouped["source_rows"]
        records.append({"run": role, "status": "pass", "grouped_alternative": grouped,
                        "individual_panels": panels,
                        "composition": check_composition(destination / "output", panel_outputs)})
    report = {"status": "pass", "runs": records,
              "scope": "Two known-source grouped comparisons; numerical/export checks do not assess aesthetics or model-wide effectiveness."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "pass", "runs": len(records)}))


if __name__ == "__main__":
    main()
