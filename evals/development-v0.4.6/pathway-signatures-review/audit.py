#!/usr/bin/env python3
"""Independent review of literal coefficient cells, all pairs and selected SVG points."""
import argparse
import csv
from decimal import Decimal
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import pymupdf

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / "examples/create/pathway-signatures"
DEST = Path(__file__).parent
S = {"s": "http://www.w3.org/2000/svg"}


def rows(path):
    with path.open(newline="") as stream: return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=CASE / "output")
    parser.add_argument("--review-dir", type=Path, default=DEST)
    args = parser.parse_args()
    args.review_dir.mkdir(parents=True, exist_ok=True)
    loader = importlib.util.spec_from_file_location("independent_source_xml_reader", ROOT / "examples/create/thermogenic-expression/validate.py")
    xml_reader = importlib.util.module_from_spec(loader); loader.loader.exec_module(xml_reader)
    contract = json.loads((CASE / "inputs/input-contract.json").read_text()); spec = json.loads((CASE / "spec.json").read_text())
    book = CASE / "inputs" / contract["source_file"]
    assert hashlib.sha256(book.read_bytes()).hexdigest() == contract["source_sha256"]
    workbook = xml_reader.source_cells(book, "Sheet1")
    source = rows(CASE / "inputs/coefficients.csv")
    assert len(source) == 11143
    by_pair = {}; supports = {pathway: set() for pathway in contract["pathways"]}
    for row in source:
        assert workbook[row["source_cell"]] == row["coefficient"]
        key = (row["gene"], row["pathway"]); assert key not in by_pair
        by_pair[key] = row
        if Decimal(row["coefficient"]) != 0: supports[row["pathway"]].add(row["gene"])
    genes = {row["gene"] for row in source}
    assert len(genes) == 1013 and len(by_pair) == len(genes) * 11
    assert all(len(support) == 100 for support in supports.values())
    assert sum(Decimal(row["coefficient"]) == 0 for row in source) == 10043
    derived = rows(args.output / "all-pair-overlaps.csv")
    assert len(derived) == 55
    nonempty = {}; pair_keys = set()
    for row in derived:
        first, second = row["pathway_a"], row["pathway_b"]
        key = frozenset((first, second)); assert len(key) == 2 and key not in pair_keys; pair_keys.add(key)
        shared = supports[first] & supports[second]; union = supports[first] | supports[second]
        assert int(row["shared_nonzero_genes"]) == len(shared) and int(row["nonzero_union_genes"]) == len(union)
        assert abs(float(row["jaccard"]) - len(shared) / len(union)) < 1e-15
        assert set(row["source_genes"].split(";")) == shared if shared else row["source_genes"] == ""
        concordant = sum(Decimal(by_pair[(gene, first)]["coefficient"]) * Decimal(by_pair[(gene, second)]["coefficient"]) > 0 for gene in shared)
        assert int(row["concordant_nonzero_genes"]) == concordant
        if shared:
            assert abs(float(row["sign_agreement"]) - concordant / len(shared)) < 1e-15
            nonempty[key] = {"first": first, "second": second, "genes": shared, "concordant": concordant}
        else: assert row["sign_agreement"] == "", "An empty overlap must have undefined sign agreement"
    assert pair_keys == {frozenset(pair) for pair in itertools.combinations(contract["pathways"], 2)}
    assert len(nonempty) == 7 and len(derived) - len(nonempty) == 48
    degrees = {gene: sum(gene in supports[pathway] for pathway in supports) for gene in genes}
    assert sum(degree == 2 for degree in degrees.values()) == 87 and max(degrees.values()) == 2
    assert sum(degree == 1 for degree in degrees.values()) == 926

    selected = rows(args.output / "selected-paired-coefficients.csv")
    expected = {(gene, frozenset((record["first"], record["second"]))) for key, record in nonempty.items() if len(record["genes"]) > spec["coefficient_selection"]["minimum_shared_exclusive"] for gene in record["genes"]}
    assert {(row["gene"], frozenset((row["pathway_x"], row["pathway_y"]))) for row in selected} == expected
    assert len(selected) == 80
    svg = ET.parse(args.output / "panel.svg").getroot(); groups = {node.get("id"): node for node in svg.iter() if node.get("id")}
    max_coordinate_error = 0
    for row in selected:
        for side in ("x", "y"):
            original = by_pair[(row["gene"], row["pathway_" + side])]
            assert row["coefficient_" + side] == original["coefficient"] and row["source_cell_" + side] == original["source_cell"]
        view = next(view for view in spec["coefficient_views"] if view["pair"] == [row["pathway_x"], row["pathway_y"]])
        left, bottom, width, height = spec["geometry_mm"][view["geometry"]]
        expected_x = (left + (float(row["coefficient_x"]) - view["x_limits"][0]) / (view["x_limits"][1] - view["x_limits"][0]) * width) / 25.4 * 72
        expected_y = (spec["layout"]["height_mm"] - bottom - (float(row["coefficient_y"]) - view["y_limits"][0]) / (view["y_limits"][1] - view["y_limits"][0]) * height) / 25.4 * 72
        uses = groups[row["artist_id"]].findall(".//s:use", S); assert len(uses) == 1
        error = max(abs(float(uses[0].get("x")) - expected_x), abs(float(uses[0].get("y")) - expected_y)); max_coordinate_error = max(max_coordinate_error, error); assert error < 1e-5
    agreement = rows(args.output / "nonempty-sign-agreement.csv")
    assert len(agreement) == 7 and {frozenset((row["pathway_a"], row["pathway_b"])) for row in agreement} == set(nonempty)

    # Run the separate export checker on a copied directory because it writes
    # a PDF preview. No selected case exports or frozen source files are changed.
    copied = args.review_dir / "copied-export-check"
    if copied.exists(): shutil.rmtree(copied)
    shutil.copytree(args.output, copied)
    export_loader = importlib.util.spec_from_file_location("separate_pathway_export_validator", CASE / "validate.py")
    export_checker = importlib.util.module_from_spec(export_loader); export_loader.loader.exec_module(export_checker)
    export_result = export_checker.validate(copied)
    (args.review_dir / "rerun-export-validation.json").write_text(json.dumps(export_result, indent=2) + "\n")
    result = {"status": "pass", "literal_coefficient_coordinates": 11143, "structural_zero_coefficients": 10043, "signature_support_sizes": {pathway: len(support) for pathway, support in supports.items()},
              "all_unordered_pair_records": 55, "zero_overlap_pairs_with_undefined_sign_agreement": 48, "nonempty_pairs": 7, "shared_genes_in_exactly_two_signatures": 87,
              "selected_pairs": [[record["first"], record["second"], len(record["genes"])] for record in nonempty.values() if len(record["genes"]) > 10],
              "selected_actual_svg_gene_markers": 80, "maximum_actual_svg_marker_coordinate_error_pt": max_coordinate_error,
              "reviewed_output": str(args.output.resolve()),
              "all_nonempty_sign_agreement_pairs": 7, "exports_sha256": {extension: hashlib.sha256((args.output / ("panel." + extension)).read_bytes()).hexdigest() for extension in ("png", "pdf", "svg")},
              "scope": "Independent source-support/pair/sign/selection recomputation and actual SVG centers; copied-export standalone validation supplies separate source-to-PDF/font/size evidence. No inference of measured pathway activity or causal crosstalk."}
    (args.review_dir / "numeric-evidence.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "pass", "source_coordinates": 11143, "pairs": 55, "selected_actual_svg_points": 80}))


if __name__ == "__main__": main()
