#!/usr/bin/env python3
"""Independently audit literal workbook cells, transformations and exported marks.

This checker never imports the plotting script or its color/geometry functions.
It reads the actual SVG paths, actual PDF drawings/fonts and PNG center pixels,
then compares them with Decimal recomputation from the copied official workbook.
"""
import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import io
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
import pymupdf
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
SVG = {"s": "http://www.w3.org/2000/svg"}
NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def check(condition, message):
    if not condition: raise ValueError(message)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(newline="") as stream: return list(csv.DictReader(stream))


def source_cells(path, sheet_name):
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        identifier = next(node.get("{" + NS["r"] + "}id") for node in workbook.findall("x:sheets/x:sheet", NS) if node.get("name") == sheet_name)
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(node.get("Target") for node in rels if node.get("Id") == identifier)
        sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        xml = ET.fromstring(archive.read(sheet_path))
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(node.itertext()) for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        result = {}
        for cell in xml.findall(".//x:sheetData/x:row/x:c", NS):
            value = cell.find("x:v", NS)
            if value is not None:
                text = value.text
                result[cell.get("r")] = strings[int(text)] if cell.get("t") == "s" else text
            else:
                inline = cell.find("x:is", NS)
                if inline is not None: result[cell.get("r")] = "".join(inline.itertext())
        return result


def rgb(hex_color):
    hex_color = hex_color.strip()
    return tuple(int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5))


def color_for(value, spec):
    scale = spec["expression_scale"]
    t = (value - scale["limits"][0]) / (scale["limits"][1] - scale["limits"][0])
    check(0 <= t <= 1, "Source-derived expression would be clipped by the color scale")
    for left, right in zip(scale["anchors"], scale["anchors"][1:]):
        if left[0] <= t <= right[0]:
            relative = (t - left[0]) / (right[0] - left[0])
            return tuple(a + relative * (b - a) for a, b in zip(rgb(left[1]), rgb(right[1])))
    raise ValueError("Color anchors do not cover the source-derived expression")


def style(node):
    return dict(entry.strip().split(":", 1) for entry in node.get("style", "").split(";") if ":" in entry)


def path_rectangle(group):
    paths = group.findall("s:path", SVG)
    check(len(paths) == 1, "Expected exactly one vector rectangle in a mapped quantitative artist")
    node = paths[0]
    d = node.get("d", "")
    check(set(re.findall(r"[A-DF-Za-df-z]", re.sub(NUM, "", d))) <= {"M", "L", "z", "Z"}, "Quantitative artist is not a direct vector rectangle")
    values = [float(value) for value in re.findall(NUM, d)]
    check(len(values) == 8, "Mapped quantitative rectangle does not have four corners")
    points = list(zip(values[::2], values[1::2]))
    xmin, xmax = min(x for x, _ in points), max(x for x, _ in points)
    ymin, ymax = min(y for _, y in points), max(y for _, y in points)
    check(all(abs(x - xmin) < 1e-6 or abs(x - xmax) < 1e-6 for x, _ in points), "Rectangle has a non-rectangular x coordinate")
    check(all(abs(y - ymin) < 1e-6 or abs(y - ymax) < 1e-6 for _, y in points), "Rectangle has a non-rectangular y coordinate")
    return [xmin, ymin, xmax, ymax], style(node)


def expected_rectangle(box, row, column, row_count, column_count, canvas_height, *, start=0, end=1, row_height=1):
    x, y, width, height = box
    left = x + width * (column + start) / column_count
    right = x + width * (column + end) / column_count
    row_top = canvas_height - y - height + height * (row + (1 - row_height) / 2) / row_count
    row_bottom = row_top + height * row_height / row_count
    return [value / 25.4 * 72 for value in (left, row_top, right, row_bottom)]


def validate(output, *, data_file=None, contract_file=None, spec_file=None):
    data_file = data_file or HERE / "inputs/observations.csv"
    contract_file = contract_file or HERE / "inputs/input-contract.json"
    spec_file = spec_file or HERE / "spec.json"
    contract = json.loads(contract_file.read_text()); spec = json.loads((output / "settings.json").read_text())["spec"]
    adopted = json.loads(spec_file.read_text())
    # A declared explicit font override is permitted; every other adopted setting is fixed.
    candidate = json.loads(json.dumps(spec)); candidate["layout"]["font"] = adopted["layout"]["font"]
    check(candidate == adopted, "Saved resolved settings changed adopted science, scale or geometry")
    genes, samples = contract["genes"], contract["samples"]
    raw = csv_rows(data_file); transformed = csv_rows(output / "transformed-cells.csv"); contrasts = csv_rows(output / "genotype-contrasts.csv")
    check(len(raw) == len(transformed) == 174 and len(genes) == len(contrasts) == 29 and len(samples) == 6, "Incomplete source/derived matrix")
    workbook = contract_file.parent / contract["source_file"]
    check(digest(workbook) == contract["source_sha256"], "Official source workbook bytes changed")
    literal = source_cells(workbook, contract["source_sheet"])
    raw_by_key = {}; decimals = {}
    for row in raw:
        key = (row["gene"], row["sample"])
        check(key not in raw_by_key, "Duplicate biological expression coordinate")
        check(row["source_sheet"] == contract["source_sheet"] and literal[row["source_cell"]] == row["tpm"], "Source numeric text/cell trace changed")
        check(literal[row["source_gene_cell"]] == row["gene"] and literal[row["source_sample_cell"]] == row["sample"], "Source gene/sample labels do not bind the supplied cell")
        check(contract["condition_aliases"][row["sample"]] == row["condition"], "Unsupported genotype alias")
        value = Decimal(row["tpm"])
        check(value >= 0 and value.is_finite(), "Invalid or missing literal TPM")
        with localcontext() as context:
            context.prec = 50
            decimals[key] = (value + Decimal(1)).ln() / Decimal(2).ln()
        raw_by_key[key] = row
    check(set(raw_by_key) == {(gene, sample) for gene in genes for sample in samples}, "Source matrix coordinates are incomplete")
    check(sum(Decimal(row["tpm"]) == 0 for row in raw) == 6 and all(Decimal(raw_by_key[("Atp5o", sample)]["tpm"]) == 0 for sample in samples), "Author's six observed Atp5o zeros were not retained")

    svg = ET.parse(output / "panel.svg").getroot()
    ids = [node.get("id") for node in svg.iter() if node.get("id")]
    check(len(ids) == len(set(ids)), "Actual SVG contains duplicate IDs")
    groups = {node.get("id"): node for node in svg.iter() if node.get("id")}
    elements = json.loads((output / "elements.json").read_text())
    check(elements["version"]["figure_sha256"] == digest(output / "panel.svg") and elements["version"]["input_sha256"] == digest(data_file), "Element map no longer binds the current SVG/input")
    by_id = {record["id"]: record for record in elements["elements"]}
    check(len(by_id) == len(elements["elements"]) and all(identifier in groups for identifier in by_id), "Mapped IDs are duplicate or absent from actual SVG")
    width, height = spec["layout"]["width_mm"], spec["layout"]["height_mm"]
    observed_dimensions = [float(svg.get(key).removesuffix("pt")) / 72 * 25.4 for key in ("width", "height")]
    check(all(abs(a - b) < 1e-5 for a, b in zip(observed_dimensions, (width, height))), "SVG physical canvas changed")
    svg_text = list(svg.findall(".//s:text", SVG))
    check(svg_text and all(style(node).get("font-size", "").strip() == "8px" for node in svg_text), "SVG text is not uniformly the adopted 8 pt")
    check(not any(node.get("transform", "").startswith("scale") for node in svg_text), "SVG text has a hidden scale transformation")
    expected_font = json.loads((output / "settings.json").read_text())["layout"]["actual_font"]
    check(all(expected_font in style(node).get("font-family", "") for node in svg_text), "Actual SVG font differs from the resolved font")
    quantitative_paths = []; max_transform_error = 0; max_path_error = 0; max_color_error = 0
    ordered = {(row["gene"], row["sample"]): row for row in transformed}
    check(len(ordered) == 174 and set(ordered) == set(raw_by_key), "Transformed records omit or duplicate source cells")
    for row_index, gene in enumerate(genes):
        for column, sample in enumerate(samples):
            key = (gene, sample); raw_row = raw_by_key[key]; saved = ordered[key]
            check(all(saved[field] == raw_row[field] for field in raw_row), "Saved plotting data changed a literal source record")
            error = abs(float(saved["log2_tpm_plus_1"]) - float(decimals[key])); max_transform_error = max(max_transform_error, error)
            check(error < 1e-12, "Expression transform differs from Decimal recomputation")
            record = by_id[saved["artist_id"]]
            check(record["role"] == "expression-cell" and len(record["source_keys"]) == 1, "Expression coordinate is not one mapped vector cell")
            check(all(record["source_keys"][0][field] == raw_row[field] for field in ("source_sheet", "source_cell", "gene", "sample", "condition")), "Expression artist has a false source binding")
            actual, appearance = path_rectangle(groups[record["id"]])
            expected = expected_rectangle(spec["geometry_mm"]["matrix"], row_index, column, 29, 6, height)
            error = max(abs(a - b) for a, b in zip(actual, expected)); max_path_error = max(max_path_error, error)
            check(error < 1e-5, "Actual matrix rectangle moved, vanished, or changed size")
            color = color_for(float(decimals[key]), spec)
            color_error = max(abs(a - b) for a, b in zip(rgb(appearance["fill"]), color)); max_color_error = max(max_color_error, color_error)
            check(color_error <= .5 / 255 + 1e-8, "Actual SVG fill does not encode the source-derived expression")
            check(appearance.get("stroke", "").strip().lower() == spec["strokes"]["cell_seam"].lower(), "Actual matrix seam color differs")
            check(math.isclose(float(appearance["stroke-width"]), spec["strokes"]["cell_seam_width_pt"], abs_tol=1e-8), "Actual matrix seam width differs")
            quantitative_paths.append({"role": "expression-cell", "rectangle_pt": expected, "color": color})

    maximum_contrast_error = 0
    for row_index, (gene, saved) in enumerate(zip(genes, contrasts)):
        check(saved["gene"] == gene and saved["n_control"] == saved["n_ako"] == "3", "Contrast gene order or independent sample counts changed")
        expected_keys = [raw_by_key[(gene, sample)] for sample in samples]
        check(saved["source_cells"].split(";") == [row["source_cell"] for row in expected_keys], "Contrast summary is not bound to its six source cells")
        means = {condition: sum(decimals[(gene, sample)] for sample in samples if contract["condition_aliases"][sample] == condition) / 3 for condition in ("YT-FF", "YT-AKO")}
        wanted = means["YT-AKO"] - means["YT-FF"]
        for field, expected in (("control_mean_log2_tpm_plus_1", means["YT-FF"]), ("ako_mean_log2_tpm_plus_1", means["YT-AKO"]), ("descriptive_difference", wanted)):
            error = abs(float(saved[field]) - float(expected)); maximum_contrast_error = max(maximum_contrast_error, error)
            check(error < 1e-12, "Descriptive genotype mean/difference differs from independent recomputation")
        record = by_id[saved["artist_id"]]
        check(record["role"] == "mean-contrast" and [key["source_cell"] for key in record["source_keys"]] == [row["source_cell"] for row in expected_keys], "Contrast artist is bound to incorrect source cells")
        check(all(all(key[field] == row[field] for field in ("source_sheet", "source_cell", "gene", "sample", "condition")) for key, row in zip(record["source_keys"], expected_keys)), "Contrast artist has a false gene/sample/genotype association")
        actual, appearance = path_rectangle(groups[record["id"]])
        low, high = spec["contrast"]["limits"]
        expected = expected_rectangle(spec["geometry_mm"]["contrast"], row_index, 0, 29, 1, height,
                                      start=(min(0, float(wanted)) - low) / (high - low), end=(max(0, float(wanted)) - low) / (high - low), row_height=spec["contrast"]["bar_height_rows"])
        error = max(abs(a - b) for a, b in zip(actual, expected)); max_path_error = max(max_path_error, error)
        check(error < 1e-5, "Actual contrast bar does not encode the source-derived descriptive difference")
        check(appearance["fill"].strip().lower() == spec["contrast"]["bar_face"].lower() and appearance["stroke"].strip().lower() == spec["contrast"]["bar_edge"].lower(), "Actual contrast color roles changed")
        quantitative_paths.append({"role": "mean-contrast", "rectangle_pt": expected, "color": rgb(spec["contrast"]["bar_face"])})
    for role, count in (("expression-cell", 174), ("mean-contrast", 29), ("gene-label", 29), ("sample-label", 6), ("genotype-band", 6), ("zero-contrast", 1)):
        check(sum(record["role"] == role for record in elements["elements"]) == count, "Required selectable layer missing: " + role)
    for role, names in (("gene-label", genes), ("sample-label", samples), ("genotype-label", ["YT-FF", "YT-AKO"])):
        records = [record for record in elements["elements"] if record["role"] == role]
        check({record["label"] for record in records} == set(names), "Required data labels missing")
        check(all("".join(node.itertext()).strip() == record["label"] for record in records for node in groups[record["id"]].findall(".//s:text", SVG)), "Mapped labels differ from actual SVG text")
        for record in records:
            expected_rows = ([raw_by_key[(record["label"], sample)] for sample in samples] if role == "gene-label" else
                             [raw_by_key[(gene, record["label"])] for gene in genes] if role == "sample-label" else
                             [row for row in raw if row["condition"] == record["label"]])
            check(len(record["source_keys"]) == len(expected_rows) and
                  all(all(key[field] == row[field] for field in ("source_sheet", "source_cell", "gene", "sample", "condition")) for key, row in zip(record["source_keys"], expected_rows)),
                  "Data label has a false or incomplete source binding")
    bands = [record for record in elements["elements"] if record["role"] == "genotype-band"]
    check([record["source_keys"][0]["sample"] for record in bands] == samples, "Genotype band columns are reordered")
    for column, (sample, record) in enumerate(zip(samples, bands)):
        expected_rows = [raw_by_key[(gene, sample)] for gene in genes]
        check(len(record["source_keys"]) == 29 and all(all(key[field] == row[field] for field in ("source_sheet", "source_cell", "gene", "sample", "condition")) for key, row in zip(record["source_keys"], expected_rows)), "Genotype band has a false or incomplete source binding")
        actual, appearance = path_rectangle(groups[record["id"]])
        expected = expected_rectangle(spec["geometry_mm"]["genotype_band"], 0, column, 1, 6, height)
        check(max(abs(a - b) for a, b in zip(actual, expected)) < 1e-5, "Actual genotype band is not aligned with the sample column")
        check(appearance["fill"].strip().lower() == spec["colors"][contract["condition_aliases"][sample]].lower(), "Genotype band uses the wrong decoded categorical color")
    zero = next(record for record in elements["elements"] if record["role"] == "zero-contrast")
    check([key["source_cell"] for key in zero["source_keys"]] == [raw_by_key[("Atp5o", sample)]["source_cell"] for sample in samples], "Zero-contrast marker lacks its actual source-cell binding")
    uses = groups[zero["id"]].findall(".//s:use", SVG)
    check(len(uses) == 1, "Observed zero does not have one visible SVG marker")
    zero_expected = expected_rectangle(spec["geometry_mm"]["contrast"], 28, 0, 29, 1, height, start=0, end=0)
    check(abs(float(uses[0].get("x")) - zero_expected[0]) < 1e-5 and abs(float(uses[0].get("y")) - (zero_expected[1] + zero_expected[3]) / 2) < 1e-5, "Zero-contrast marker moved from the quantitative origin/source gene row")

    with pymupdf.open(output / "panel.pdf") as document:
        check(len(document) == 1, "PDF is not one individual panel")
        page = document[0]
        dimensions = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
        check(all(abs(a - b) < .001 for a, b in zip(dimensions, (width, height))), "PDF physical canvas changed")
        check(all(document.extract_font(font[0])[3] for font in page.get_fonts()), "A PDF font is not embedded")
        embedded_fonts = {font[3].split("+")[-1]: TTFont(io.BytesIO(document.extract_font(font[0])[3])) for font in page.get_fonts()}
        spans = [span for block in page.get_text("dict")["blocks"] if block["type"] == 0 for line in block["lines"] for span in line["spans"]]
        check(spans and all(abs(span["size"] - 8) < .001 for span in spans), "Actual PDF text is not uniformly 8 pt")
        normalized = re.sub(r"[^a-z0-9]", "", expected_font.lower())
        check(all(re.sub(r"[^a-z0-9]", "", span["font"].lower()).startswith(normalized) for span in spans), "PDF substituted a glyph or font family")
        check(all(span["bbox"][0] >= 0 and span["bbox"][1] >= 0 and span["bbox"][2] <= page.rect.width and span["bbox"][3] <= page.rect.height for span in spans), "PDF data labels are clipped")
        drawings = page.get_drawings()
        checked_pdf = 0; maximum_pdf_path_error = 0
        for mark_index, mark in enumerate(quantitative_paths):
            expected = mark["rectangle_pt"]
            item_counts = (1, 3, 4) if abs(expected[2] - expected[0]) < 1e-10 else (1, 4)
            candidates = [drawing for drawing in drawings if drawing["fill"] and len(drawing["items"]) in item_counts
                          and all(abs(float(a) - b) < .002 for a, b in zip(drawing["rect"], expected))
                          and max(abs(a - b) for a, b in zip(drawing["fill"], mark["color"])) < 1e-6]
            check(len(candidates) == 1, f"Actual PDF quantitative mark {mark_index} ({mark['role']}) is missing, duplicated, moved or miscolored")
            error = max(abs(float(a) - b) for a, b in zip(candidates[0]["rect"], expected))
            maximum_pdf_path_error = max(maximum_pdf_path_error, error); checked_pdf += 1
        gene_spans = sorted((span for span in spans if span["text"] in genes), key=lambda span: span["bbox"][1])
        check([span["text"] for span in gene_spans] == genes, "Actual PDF gene labels are reordered or absent")
        check(all("Italic" in span["font"] or "Oblique" in span["font"] for span in gene_spans), "PDF gene labels lost their adopted italic style")
        metric_gaps = [second["bbox"][1] - first["bbox"][3] for first, second in zip(gene_spans, gene_spans[1:])]
        # PDF span boxes contain font-wide ascender/descender padding. Inspect the
        # actual embedded glyph outlines and exported glyph positions instead of
        # treating empty metric padding as visible collisions.
        gene_traces = sorted((trace for trace in page.get_texttrace() if "".join(chr(char[0]) for char in trace["chars"]) in genes), key=lambda trace: trace["bbox"][1])
        check(len(gene_traces) == 29, "PDF trace lost a gene label")
        ink_bounds = []
        for trace in gene_traces:
            check(tuple(trace["dir"]) == (1.0, 0.0) and trace["type"] == 0, "Gene labels use an unverified text transform or stroke")
            font = embedded_fonts[trace["font"]]
            units = font["head"].unitsPerEm
            bounds = []
            for char in trace["chars"]:
                glyph = font["glyf"][font.getGlyphOrder()[char[1]]]
                if not glyph.numberOfContours: continue
                baseline = char[2][1]
                bounds.append((baseline - glyph.yMax * trace["size"] / units, baseline - glyph.yMin * trace["size"] / units))
            check(bounds, "Gene label has no visible embedded glyphs")
            ink_bounds.append((min(top for top, _ in bounds), max(bottom for _, bottom in bounds)))
        gaps = [second[0] - first[1] for first, second in zip(ink_bounds, ink_bounds[1:])]
        check(min(gaps) > 0, "Adjacent actual embedded gene glyph outlines overlap")

    with Image.open(output / "panel.png") as image:
        dpi = image.info.get("dpi", ())
        check(len(dpi) == 2 and all(abs(value - spec["layout"]["dpi"]) < .01 for value in dpi), "PNG resolution metadata changed")
        check(image.size == tuple(round(value / 25.4 * spec["layout"]["dpi"]) for value in (width, height)), "PNG physical raster grid changed")
        image = image.convert("RGB")
        for mark in quantitative_paths[:174]:
            left, top, right, bottom = mark["rectangle_pt"]
            x = round((left + right) / 2 / (width / 25.4 * 72) * image.width)
            y = round((top + bottom) / 2 / (height / 25.4 * 72) * image.height)
            actual = image.getpixel((x, y)); expected = [round(value * 255) for value in mark["color"]]
            check(max(abs(a - b) for a, b in zip(actual, expected)) <= 1, "Actual PNG cell center does not encode the correct expression")
    qa = json.loads((output / "qa.json").read_text())
    check(qa["input_sha256"] == digest(data_file), "Generation metadata no longer binds the current input")
    check(all(qa["exports"][extension]["sha256"] == digest(output / ("panel." + extension)) for extension in ("png", "pdf", "svg")), "An export changed since generation")
    return {"status": "pass", "source_observations": 174, "genes": 29, "samples": 6, "genotype_counts": [3, 3], "observed_zero_cells_retained": 6,
            "literal_source_cells_checked": 174, "independent_transform": "50-digit Decimal log2(TPM + 1), without importing plot.py", "maximum_transform_error": max_transform_error,
            "independent_group_mean_and_difference_checks": 87, "maximum_contrast_error": maximum_contrast_error,
            "actual_svg_expression_and_contrast_paths_checked": 203, "actual_pdf_expression_and_contrast_drawings_checked": checked_pdf,
            "maximum_svg_path_error_pt": max_path_error, "maximum_pdf_path_error_pt": maximum_pdf_path_error, "maximum_svg_color_rounding_error": max_color_error,
            "actual_png_cell_centers_checked": 174, "actual_font": expected_font, "all_pdf_fonts_embedded": True, "all_pdf_svg_text_size_pt": 8,
            "minimum_actual_pdf_gene_ink_gap_mm": min(gaps) / 72 * 25.4,
            "minimum_pdf_font_metric_box_gap_mm": min(metric_gaps) / 72 * 25.4,
            "glyph_gap_method": "Embedded TrueType yMin/yMax at actual PDF glyph origins and 8 pt size; font-wide empty ascender/descender padding is reported separately",
            "canvas_mm": [width, height], "exports_sha256": {extension: digest(output / ("panel." + extension)) for extension in ("png", "pdf", "svg")},
            "limits": "Checks this complete known-source case and its declared adaptations. Numerical/export success does not prove aesthetic superiority or general model effectiveness."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "output")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = validate(args.output)
    destination = args.out or args.output / "validation.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "observations": report["source_observations"], "actual_vector_marks": report["actual_svg_expression_and_contrast_paths_checked"]}))


if __name__ == "__main__": main()
