#!/usr/bin/env python3
"""Extract Fig. 2c cells from Huang et al.'s Source Data XLSX without author code."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
DISPLAY = {"ucp1": "Ucp1", "cidea": "Cidea", "dio2": "Dio2", "cox8b": "Cox8b", "elovl3": "Elovl3", "prdm16": "Prdm16"}


def extract(workbook, out):
    """Preserve stored numeric strings and literal P-value evidence."""
    workbook, out = Path(workbook).resolve(), Path(out)
    with zipfile.ZipFile(workbook) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ["".join(item.itertext()) for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        sheet = next(item for item in ET.fromstring(archive.read("xl/workbook.xml")).findall("m:sheets/m:sheet", NS) if item.attrib["name"] == "Fig. 2c")
        relations = {item.attrib["Id"]: item.attrib["Target"] for item in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        target = relations[sheet.attrib[f"{{{NS['r']}}}id"]]
        sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        cells = {}
        for cell in ET.fromstring(archive.read(sheet_path)).findall(".//m:c", NS):
            value = cell.find("m:v", NS)
            text = value.text if value is not None else ""
            if cell.attrib.get("t") == "s": text = shared[int(text)]
            elif cell.attrib.get("t") == "inlineStr": text = "".join(cell.find("m:is", NS).itertext())
            cells[cell.attrib["r"]] = text
    if cells.get("A2") != "gene" or cells.get("B2") != "YT-FF" or cells.get("G2") != "YT-AKO":
        raise ValueError("Source sheet headers changed; resolve genotype meanings before extraction")
    observations, p_values = [], []
    for row in range(3, 9):
        gene = cells[f"A{row}"]
        if gene not in DISPLAY: raise ValueError(f"Unexpected source gene {gene!r}")
        for group, letters in (("YT-FF", "BCDEF"), ("YT-AKO", "GHIJK")):
            for position, column in enumerate(letters, 1):
                address = f"{column}{row}"
                observations.append({"observation_id": f"{gene}/{group}/{position}", "gene": gene, "display_gene": DISPLAY[gene], "group": group,
                                     "source_column_index": position, "relative_expression": cells[address], "source_sheet": "Fig. 2c", "source_cell": address})
        address = f"L{row}"
        p_values.append({"gene": gene, "reported_p": cells[address], "source_sheet": "Fig. 2c", "source_cell": address})
    out.mkdir(parents=True, exist_ok=True)
    for filename, records in (("observations.csv", observations), ("author-p-values.csv", p_values)):
        path = out / filename
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    provenance = {
        "article": "Huang et al., Nature Communications 14, 7102 (2023)", "doi": "10.1038/s41467-023-43021-8", "figure": "2c",
        "article_url": "https://www.nature.com/articles/s41467-023-43021-8",
        "source_url": "https://static-content.springer-cdn.com/esm/art%3A10.1038%2Fs41467-023-43021-8/MediaObjects/41467_2023_43021_MOESM8_ESM.xlsx",
        "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "rights_evidence": "Primary article Rights and permissions plus user-provided article PDF; no separate third-party credit was found for panel 2c",
        "workbook_name": workbook.name, "workbook_sha256": hashlib.sha256(workbook.read_bytes()).hexdigest(), "sheet": "Fig. 2c", "sheet_xml": sheet_path,
        "observation_cells": 60, "author_p_cells": 6,
        "extraction": "Stored numeric strings copied from worksheet XML; no digitization, interpolation, author plotting code or statistical recomputation",
        "observation_identity": "IDs identify source cells within gene and genotype. Column position is not a supplied mouse ID and does not establish pairing across genes.",
        "normalization": "The supplied relative-expression values are retained; their underlying RT-qPCR normalization is not recomputed",
        "reference_crop": {"page_1based": 4, "bounds_pdf_pt": [284, 48, 490, 181], "resolution_scale": 4, "changes": "Cropped only; marks/colors/text unmodified"},
    }
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=HERE / "inputs")
    args = parser.parse_args(); print(json.dumps(extract(args.workbook, args.out)))


if __name__ == "__main__": main()
