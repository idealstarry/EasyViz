#!/usr/bin/env python3
"""Independent workbook-to-derived-table-to-vector checks for this Create case.

Does not import the plotting script or its derivation/geometry functions.
Checks actual SVG paths/marker uses, PDF drawing centers/fonts and full source
membership; this is numerical/export evidence, not an aesthetic certification.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
import pymupdf

HERE = Path(__file__).resolve().parent
X = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
S = {"s": "http://www.w3.org/2000/svg"}
NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def check(condition, message):
    if not condition: raise ValueError(message)


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="") as stream: return list(csv.DictReader(stream))


def workbook_cells(path):
    with zipfile.ZipFile(path) as archive:
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = book.findall("x:sheets/x:sheet", X)
        check(len(sheets) == 1 and sheets[0].get("name") == "Sheet1", "Unexpected source sheet contract")
        relid = sheets[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(node.get("Target") for node in rels if node.get("Id") == relid)
        location = target.lstrip("/") if target.startswith("/") else "xl/" + target
        strings = ["".join(node.itertext()) for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        result = {}
        for cell in ET.fromstring(archive.read(location)).findall("x:sheetData/x:row/x:c", X):
            value = cell.find("x:v", X)
            if value is not None:
                result[cell.get("r")] = strings[int(value.text)] if cell.get("t") == "s" else value.text
        return result


def appearance(node):
    return {key.strip(): value.strip() for key, value in (item.split(":", 1) for item in node.get("style", "").split(";") if ":" in item)}


def rgb(value): return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def source_binding(row): return {key: row[key] for key in ("gene", "pathway", "source_sheet", "source_cell")}


def mapped_source(record, pair, genes, rows):
    a, b = pair
    expected_scopes = [{"kind": "coefficient-column", "pathway": pathway, "selection": "all supplied coefficients"} for pathway in pair]
    check(record["source_keys"][:2] == expected_scopes, "A derived artist lost its full signature column scopes")
    expected = [source_binding(rows[gene, pathway]) for gene in sorted(genes) for pathway in pair]
    check(record["source_keys"][2:] == expected, "A derived artist has missing, reordered or false contributors")


def vector_marker(group, ids):
    uses = group.findall(".//s:use", S)
    check(len(uses) == 1, "A source gene must map to exactly one actual vector marker")
    node = uses[0]
    path_id = node.get("{http://www.w3.org/1999/xlink}href", "").removeprefix("#")
    check(path_id in ids and ids[path_id].tag.endswith("path"), "Marker path reference is missing")
    return [float(node.get("x")), float(node.get("y"))], appearance(node), ids[path_id]


def pixel_center(box, x, y, x_limits, y_limits, canvas_height):
    left, bottom, width, height = box
    px = left + width * (x - x_limits[0]) / (x_limits[1] - x_limits[0])
    py = canvas_height - bottom - height * (y - y_limits[0]) / (y_limits[1] - y_limits[0])
    return [value / 25.4 * 72 for value in (px, py)]


def validate(out, *, spec_file=None):
    spec_file = spec_file or HERE / "spec.json"
    contract = json.loads((HERE / "inputs/input-contract.json").read_text())
    saved = json.loads((out / "settings.json").read_text())
    spec = saved["spec"]
    adopted = json.loads(spec_file.read_text())
    comparable = json.loads(json.dumps(spec)); comparable["layout"]["font"] = adopted["layout"]["font"]
    check(comparable == adopted, "Resolved settings changed adopted science, size or geometry")
    check(not saved["layout"]["font_substituted"], "An unapproved font fallback was used")
    data_file = HERE / "inputs/coefficients.csv"
    workbook = HERE / "inputs" / contract["source_file"]
    check(digest(workbook) == contract["source_sha256"], "Official workbook bytes changed")
    literal = workbook_cells(workbook)
    coefficients = read_csv(data_file)
    by_key = {}; values = {}
    for row in coefficients:
        key = row["gene"], row["pathway"]
        check(key not in by_key and row["source_sheet"] == "Sheet1", "Duplicate coordinate or false source sheet")
        cell = row["source_cell"]
        match = re.fullmatch(r"([A-Z]+)([0-9]+)", cell)
        check(match is not None and literal[cell] == row["coefficient"], "Literal source numeric text/cell changed")
        column, line = match.groups()
        check(literal["A" + line] == row["gene"] and literal[column + "2"] == row["pathway"], "Source coefficient has a false gene/pathway binding")
        value = Decimal(row["coefficient"])
        check(value.is_finite(), "Missing or nonfinite published coefficient")
        by_key[key] = row; values[key] = value
    pathways = contract["pathways"]
    genes = list(dict.fromkeys(row["gene"] for row in coefficients))
    check(len(values) == 11143 and len(genes) == 1013 and set(values) == {(gene, pathway) for gene in genes for pathway in pathways}, "Full source matrix omitted or duplicated coordinates")
    signatures = {pathway: {gene for gene in genes if values[gene, pathway] != 0} for pathway in pathways}
    check(all(len(signature) == 100 for signature in signatures.values()), "Signature denominator is not exactly 100")
    check(sum(value == 0 for value in values.values()) == 10043, "Structural zero coefficients were changed or dropped")
    memberships = {gene: [pathway for pathway in pathways if gene in signatures[pathway]] for gene in genes}
    shared_genes = {gene for gene in genes if len(memberships[gene]) > 1}
    check(len(shared_genes) == 87 and all(len(memberships[gene]) == 2 for gene in shared_genes), "Shared gene count/degree changed")
    expected = {}
    for index, a in enumerate(pathways):
        for b in pathways[index + 1:]:
            shared = signatures[a] & signatures[b]
            union = signatures[a] | signatures[b]
            concordant = sum(values[gene, a] * values[gene, b] > 0 for gene in shared)
            expected[a, b] = (shared, len(union), concordant)
    table = read_csv(out / "all-pair-overlaps.csv")
    check(len(table) == 55 and len({(row["pathway_a"], row["pathway_b"]) for row in table}) == 55, "The overlap view does not retain 55 unique unordered pairs")
    zero_pairs = 0
    for row in table:
        pair = row["pathway_a"], row["pathway_b"]
        check(pair in expected, "Unknown or reversed unordered overlap pair")
        shared, union, concordant = expected[pair]
        check(int(row["shared_nonzero_genes"]) == len(shared) and int(row["nonzero_union_genes"]) == union and int(row["concordant_nonzero_genes"]) == concordant, "Saved overlap/count/union differs from independent source recomputation")
        check(math.isclose(float(row["jaccard"]), len(shared) / union, abs_tol=1e-14), "Jaccard was redefined or rounded incorrectly")
        check(row["source_genes"].split(";") == sorted(shared) if shared else row["source_genes"] == "", "Saved contributing gene set changed")
        if not shared:
            zero_pairs += 1
            check(row["sign_agreement"] == "", "Empty-pair sign agreement is undefined, never zero")
        else:
            check(math.isclose(float(row["sign_agreement"]), concordant / len(shared), abs_tol=1e-14), "Sign agreement differs from the source products")
    check(zero_pairs == 48, "Zero-overlap pairs were removed or misrepresented")

    svg = ET.parse(out / "panel.svg").getroot()
    nodes = [node for node in svg.iter() if node.get("id")]
    ids = {node.get("id"): node for node in nodes}
    check(len(ids) == len(nodes) and not svg.findall(".//s:image", S), "SVG has duplicate IDs or rasterized data")
    element_map = json.loads((out / "elements.json").read_text())
    check(element_map["version"]["figure_sha256"] == digest(out / "panel.svg") and element_map["version"]["input_sha256"] == digest(data_file), "Element map is stale for the exported SVG or source")
    mapped = {record["id"]: record for record in element_map["elements"]}
    check(len(mapped) == len(element_map["elements"]) and all(identifier in ids for identifier in mapped), "Mapped artist is absent from the real SVG")
    width, height = spec["layout"]["width_mm"], spec["layout"]["height_mm"]
    for key, dimension in (("width", width), ("height", height)):
        check(abs(float(svg.get(key).removesuffix("pt")) / 72 * 25.4 - dimension) < 1e-5, "SVG canvas size changed")
    actual_font = saved["layout"]["actual_font"]
    texts = svg.findall(".//s:text", S)
    check(texts and all(appearance(node).get("font-size") == "8px" for node in texts), "Actual SVG text is not 8 pt")
    check(all(actual_font in appearance(node).get("font-family", "") for node in texts), "Actual SVG font differs from the resolved choice")

    max_vector_error = 0
    count_labels = {(record["source_keys"][0]["pathway"], record["source_keys"][1]["pathway"]): record for record in mapped.values() if record["role"] == "shared-count-label"}
    check(len(count_labels) == 55, "Count labels omit or duplicate a pathway pair")
    for row in table:
        pair = row["pathway_a"], row["pathway_b"]
        record = mapped[row["artist_id"]]
        check(record["role"] == "shared-count-cell", "Overlap record is not a mapped count cell")
        mapped_source(record, pair, expected[pair][0], by_key)
        label = count_labels[pair]
        mapped_source(label, pair, expected[pair][0], by_key)
        actual_label = "".join(ids[label["id"]].itertext()).strip()
        check(actual_label == str(len(expected[pair][0])), "Actual count-label glyphs contradict the source-derived count")
        paths = ids[row["artist_id"]].findall("s:path", S)
        check(len(paths) == 1, "A count cell lost its actual vector rectangle")
        numbers = [float(value) for value in re.findall(NUM, paths[0].get("d"))]
        check(len(numbers) == 8, "Count cell is not a four-corner rectangle")
        points = list(zip(numbers[::2], numbers[1::2]))
        actual = [min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)]
        x, y, w, h = spec["geometry_mm"]["overlap"]
        r, c, n = int(row["row_index"]), int(row["column_index"]), len(spec["pathway_order"])
        check(spec["pathway_order"][r] in pair and spec["pathway_order"][c] in pair and r > c, "Cell row/column relationship changed")
        bounds = [(x + w * c / n) / 25.4 * 72, (height - y - h + h * r / n) / 25.4 * 72,
                  (x + w * (c + 1) / n) / 25.4 * 72, (height - y - h + h * (r + 1) / n) / 25.4 * 72]
        error = max(abs(a - b) for a, b in zip(actual, bounds)); max_vector_error = max(max_vector_error, error)
        check(error < 1e-5, "Actual count rectangle moved, vanished or changed dimensions")
        style = appearance(paths[0])
        check(style.get("stroke", "").lower() == spec["strokes"]["seam"].lower() and math.isclose(float(style["stroke-width"]), spec["strokes"]["seam_width_pt"], abs_tol=1e-8), "Actual matrix seams differ from the adopted settings")
        count = len(expected[pair][0]); scale = spec["overlap_scale"]
        check(scale["limits"][0] <= count <= scale["limits"][1], "Count scale clips the source quantity")
        # Check continuous colors with independently reconstructed anchors and
        # the renderer's declared 65,536-level LUT quantization.
        t = (count - scale["limits"][0]) / (scale["limits"][1] - scale["limits"][0])
        t = min(int(t * 65536), 65535) / 65535
        for (left, first), (right, second) in zip(scale["anchors"], scale["anchors"][1:]):
            if left <= t <= right:
                position = (t - left) / (right - left)
                color = tuple(a + position * (b - a) for a, b in zip(rgb(first), rgb(second)))
                break
        check(max(abs(a - b) for a, b in zip(rgb(style["fill"]), color)) <= .5 / 255 + 1e-7, "Actual count-cell fill does not encode its source-derived count")

    chosen = {pair for pair, result in expected.items() if len(result[0]) > spec["coefficient_selection"]["minimum_shared_exclusive"]}
    records = read_csv(out / "selected-paired-coefficients.csv")
    expected_points = {(a, b, gene) for a, b in chosen for gene in expected[a, b][0]}
    actual_points = {(row["pathway_x"], row["pathway_y"], row["gene"]) for row in records}
    check(len(records) == len(actual_points) == 80 and actual_points == expected_points, "Selected coefficient views omit/duplicate genes or violate the >10 rule")
    point_centers = []
    for row in records:
        a, b, gene = row["pathway_x"], row["pathway_y"], row["gene"]
        first, second = by_key[gene, a], by_key[gene, b]
        check(row["coefficient_x"] == first["coefficient"] and row["coefficient_y"] == second["coefficient"] and row["source_cell_x"] == first["source_cell"] and row["source_cell_y"] == second["source_cell"], "A paired point changed an original signed coefficient")
        record = mapped[row["artist_id"]]
        check(record["role"] == "paired-coefficient-gene" and record["source_keys"] == [source_binding(first), source_binding(second)], "A paired gene has a false source-to-artist identity")
        view = next(view for view in spec["coefficient_views"] if view["pair"] == [a, b])
        center = pixel_center(spec["geometry_mm"][view["geometry"]], float(values[gene, a]), float(values[gene, b]), view["x_limits"], view["y_limits"], height)
        actual, style, path = vector_marker(ids[row["artist_id"]], ids)
        error = max(abs(x - y) for x, y in zip(actual, center)); max_vector_error = max(max_vector_error, error)
        check(error < 1e-5, "Actual source-bound point is at false coefficient coordinates")
        check(style["fill"].lower() == spec["point"]["face"].lower(), "Coefficient mark fill changed")
        check(style.get("stroke", "").lower() == spec["point"]["edge"].lower() and math.isclose(float(style["stroke-width"]), spec["point"]["edge_width_pt"], abs_tol=1e-8), "Coefficient point boundary changed")
        numbers = [float(value) for value in re.findall(NUM, path.get("d"))]
        check(math.isclose(max(abs(number) for number in numbers), spec["point"]["diameter_pt"] / 2, abs_tol=1e-6), "Actual coefficient marker has a false physical diameter")
        point_centers.append(center)

    agreement_rows = read_csv(out / "nonempty-sign-agreement.csv")
    nonempty = {pair for pair, result in expected.items() if result[0]}
    check(len(agreement_rows) == 7 and {(row["pathway_a"], row["pathway_b"]) for row in agreement_rows} == nonempty, "Agreement view omits/duplicates nonempty pairs or invents values for empty pairs")
    sign_labels = {(record["source_keys"][0]["pathway"], record["source_keys"][1]["pathway"]): record for record in mapped.values() if record["role"] == "sign-count-label"}
    check(set(sign_labels) == nonempty, "Sign-fraction labels omit/duplicate nonempty pairs")
    for row in agreement_rows:
        pair = row["pathway_a"], row["pathway_b"]
        shared, union, concordant = expected[pair]
        check(int(row["shared_nonzero_genes"]) == len(shared) and int(row["concordant_nonzero_genes"]) == concordant and math.isclose(float(row["sign_agreement"]), concordant / len(shared), abs_tol=1e-14), "Agreement numerator/denominator changed")
        record = mapped[row["artist_id"]]
        mapped_source(record, pair, shared, by_key)
        sign_label = sign_labels[pair]
        mapped_source(sign_label, pair, shared, by_key)
        check("".join(ids[sign_label["id"]].itertext()).strip() == f"{concordant}/{len(shared)}", "Actual sign-fraction label contradicts its numerator/denominator")
        box = spec["geometry_mm"]["agreement"]
        center = pixel_center(box, concordant / len(shared), int(row["row_index"]) + .5, spec["agreement"]["limits"], [7, 0], height)
        actual, style, path = vector_marker(ids[row["artist_id"]], ids)
        error = max(abs(x - y) for x, y in zip(actual, center)); max_vector_error = max(max_vector_error, error)
        check(error < 1e-5, "Actual agreement marker is at false signed-fraction coordinates")
        point_centers.append(center)

    all_shared = read_csv(out / "all-shared-gene-coefficients.csv")
    check(len(all_shared) == 87 and {row["gene"] for row in all_shared} == shared_genes, "The full shared-gene table omitted the seven nonselected genes")
    for row in all_shared:
        gene, a, b = row["gene"], row["pathway_a"], row["pathway_b"]
        check({a, b} == set(memberships[gene]), "Shared-gene partner identities changed")
        check(row["coefficient_a"] == by_key[gene, a]["coefficient"] and row["coefficient_b"] == by_key[gene, b]["coefficient"], "The all-shared table changed an exact coefficient")
        shown = (a, b, gene) in expected_points
        check(row["shown_in_coefficient_view"] == str(shown), "A selected/retained coefficient view flag is false")
        check((row["coefficient_artist_id"] in mapped) if shown else row["coefficient_artist_id"] == "", "Unplotted genes were assigned fake selectable artists")

    qa = json.loads((out / "qa.json").read_text())
    check(qa["input_sha256"] == digest(data_file), "Generation metadata lost the full source binding")
    check(qa["source_script_sha256"] == digest(HERE / "plot.py"), "Generation metadata refers to a different plotting script")
    for extension in ("svg", "pdf", "png"):
        check(qa["exports"][extension]["sha256"] == digest(out / ("panel." + extension)), "Export measurement hash is stale")
    doc = pymupdf.open(out / "panel.pdf")
    check(len(doc) == 1, "PDF has an unexpected page count")
    page = doc[0]
    dimensions = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
    check(all(abs(a - b) < 1e-5 for a, b in zip(dimensions, (width, height))), "Actual PDF physical page changed")
    spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block for line in block["lines"] for span in line["spans"]]
    check(spans and all(abs(span["size"] - 8) < 1e-5 for span in spans), "Actual PDF text is not uniformly 8 pt")
    check(all("\ufffd" not in span["text"] for span in spans), "PDF text contains missing glyph placeholders")
    fonts = page.get_fonts(full=True)
    check(fonts and all(font[1] not in ("n/a", "") for font in fonts), "A PDF font is not embedded")
    drawings = page.get_drawings()
    circles = [drawing for drawing in drawings if len(drawing["items"]) == 8 and all(item[0] == "c" for item in drawing["items"]) and drawing.get("fill") is not None]
    expected_color = rgb(spec["point"]["face"])
    circles = [drawing for drawing in circles if max(abs(a - b) for a, b in zip(drawing["fill"], expected_color)) < 1e-6]
    check(len(circles) == 87, "The PDF lost or rasterized source-bound point/agreement circles")
    centers = [[(drawing["rect"].x0 + drawing["rect"].x1) / 2, (drawing["rect"].y0 + drawing["rect"].y1) / 2] for drawing in circles]
    check(all(any(max(abs(a - b) for a, b in zip(center, actual)) < 1e-4 for actual in centers) for center in point_centers), "Actual PDF drawing centers disagree with source-derived coordinates")
    preview = page.get_pixmap(matrix=pymupdf.Matrix(96 / 72, 96 / 72), alpha=False)
    preview.save(out / "pdf-preview-96dpi.png")
    doc.close()
    with Image.open(out / "panel.png") as png:
        pixels = [round(value / 25.4 * spec["layout"]["dpi"]) for value in (width, height)]
        check(list(png.size) == pixels, "Actual PNG grid differs from the fixed canvas")
    return {"status": "passed", "scope": "Independent numerical/source/vector/export checks; image review remains separate", "literal_source_coordinates": len(values), "structural_zeros": 10043,
            "unordered_pairs": 55, "zero_overlap_pairs": zero_pairs, "nonempty_pairs": 7, "shared_genes": 87, "selected_paired_gene_marks": len(records),
            "maximum_vector_coordinate_error_pt": max_vector_error, "pdf_source_bound_circles": len(circles), "pdf_dimensions_mm": dimensions,
            "actual_font": actual_font, "embedded_pdf_fonts": [font[3] for font in fonts], "actual_font_size_pt": 8,
            "nominal_pdf_preview": "pdf-preview-96dpi.png", "font_override": spec["layout"]["font"] != adopted["layout"]["font"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "output")
    parser.add_argument("--spec", type=Path)
    args = parser.parse_args()
    result = validate(args.out, spec_file=args.spec)
    (args.out / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    qa_path = args.out / "qa.json"
    qa = json.loads(qa_path.read_text())
    qa.update(status="pass", valid_outputs=True, numerical_validation="validation.json",
              validator_sha256=digest(Path(__file__).resolve()), visual_review="separate; independent review remains required")
    qa_path.write_text(json.dumps(qa, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__": main()
