#!/usr/bin/env python3
"""Extract unchanged Figure 1d mean/SD text from the official Source Data XML."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
from zipfile import ZipFile

SOURCE_URL = "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-021-22092-5/MediaObjects/41467_2021_22092_MOESM5_ESM.xlsx"
EXPECTED_SHA = "d90396f86e637919fb5159d12b4d2ad35ebd5857c810f4e22a220661dfd437b8"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def extract(source, out):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError("Source Data workbook differs from the audited snapshot")
    with ZipFile(source) as archive:
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {node.get("Id"): node.get("Target") for node in relationships}
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(node for node in workbook.findall("m:sheets/m:sheet", NS) if node.get("name") == "Figure 1d")
        target = targets[sheet.get(RID)]
        target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        original_xml = archive.read(target)
        cells = {node.get("r"): node for node in ET.fromstring(original_xml).findall(".//m:sheetData/m:row/m:c", NS)}
        strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = ["".join(node.itertext()) for node in strings.findall("m:si", NS)]

    def text(cell):
        node = cells[cell]
        value = node.find("m:v", NS).text
        return shared[int(value)] if node.get("t") == "s" else value

    headers = {"B3": "Time", "C3": "Cell width", "D3": "std(Cell width)",
               "F3": "Time", "G3": "Cell length", "H3": "std(Cell length)"}
    if any(text(cell) != value for cell, value in headers.items()):
        raise ValueError("Figure 1d source headers changed")
    rows = []
    for row in range(4, 64):
        for curve, cols in [("Cell width", ("B", "C", "D")), ("Cell length", ("F", "G", "H"))]:
            coordinates = [f"{col}{row}" for col in cols]
            values = [text(cell) for cell in coordinates]
            if any(not Decimal(value).is_finite() for value in values) or Decimal(values[2]) < 0:
                raise ValueError(f"Invalid supplied summary at source row {row}")
            rows.append({"time_min": values[0], "dimension": curve, "mean_um": values[1], "sd_um": values[2],
                         "source_sheet": "Figure 1d", "source_row": row,
                         "time_cell": coordinates[0], "mean_cell": coordinates[1], "sd_cell": coordinates[2]})
    if len(rows) != 120 or set(Decimal(row["time_min"]) for row in rows) != set(map(Decimal, range(1, 61))):
        raise ValueError("Expected all 60 original times for both dimensions")
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "source-data.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    checks = {"source_url": SOURCE_URL, "source_sha256": digest, "source_bytes": source.stat().st_size,
              "source_sheet": "Figure 1d", "source_rows": [4, 63], "source_headers": headers,
              "worksheet_xml_sha256": hashlib.sha256(original_xml).hexdigest(),
              "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
              "summary_rows": len(rows), "timepoints_per_curve": 60,
              "all_selected_numeric_xml_text_preserved": True, "raw_cell_measurements_available": False,
              "uncertainty": "supplied standard deviation, caption n=146 single cells",
              "values_digitized_from_image": False, "author_code_used": False,
              "transformations": ["Selected all Figure 1d B/C/D and F/G/H data cells, rows 4:63.",
                                  "Reshaped wide summary columns into long rows; unchanged original numeric XML text retained.",
                                  "No rounding, filtering, normalization, SD-to-SEM conversion, fitting or inferential test."]}
    (out / "source-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(extract(args.source, args.out), indent=2))


if __name__ == "__main__":
    main()
