#!/usr/bin/env python3
"""Extract Figure 2b observations directly from the official XLSX XML."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
SOURCE_URL = "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-024-47429-8/MediaObjects/41467_2024_47429_MOESM4_ESM.xlsx"
EXPECTED_SHA = "d902e7608caa56172bac12515bb0e0b79efb075b669424b8b63858ad21d371be"


def read_sheets(path: Path) -> dict[str, dict[str, str]]:
    with ZipFile(path) as archive:
        strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = ["".join(n.itertext()) for n in strings.findall("m:si", NS)]
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {n.attrib["Id"]: n.attrib["Target"].lstrip("/") for n in relations}
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        result = {}
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            target = targets[sheet.attrib[RID]]
            target = target if target.startswith("xl/") else "xl/" + target
            xml = ET.fromstring(archive.read(target))
            cells = {}
            for cell in xml.findall(".//m:sheetData/m:row/m:c", NS):
                value = cell.find("m:v", NS)
                if value is not None and value.text is not None:
                    cells[cell.attrib["r"]] = shared[int(value.text)] if cell.get("t") == "s" else value.text
                elif cell.get("t") == "inlineStr":
                    cells[cell.attrib["r"]] = "".join(cell.find("m:is", NS).itertext())
            result[sheet.attrib["name"]] = cells
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    sha = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if sha != EXPECTED_SHA:
        raise ValueError("Official workbook identity differs from the audited snapshot")
    sheets = read_sheets(args.source)
    cells = sheets["figure 2"]
    expected = {"A3": "NatCom_ID", "B3": "prior SARS-CoV-2 infection", "C3": "Spike IgG before", "D3": "Spike IgG after"}
    if any(cells.get(cell) != text for cell, text in expected.items()):
        raise ValueError("Selected Figure 2 headers changed")
    rows = []
    mapping = {"yes": "Prior infection", "yes/NCAP+": "Prior infection", "no": "No prior infection"}
    for r in range(4, 131):
        sid, status = cells[f"A{r}"], cells[f"B{r}"]
        if status not in mapping:
            raise ValueError(f"Unrecognized infection classification at B{r}")
        for col, time in [("C", "Before"), ("D", "After")]:
            value = cells[f"{col}{r}"]
            if not Decimal(value).is_finite() or Decimal(value) <= 0:
                raise ValueError(f"Cannot display source value on log axis: {col}{r}")
            rows.append({"participant_id": sid, "infection_group": mapping[status], "timepoint": time,
                         "igg_bau_ml": value, "source_infection_status": status,
                         "source_sheet": "figure 2", "source_row": r, "source_cell": f"{col}{r}"})
    ids = {r["participant_id"] for r in rows}
    if len(ids) != 127 or len(rows) != 254:
        raise ValueError("Participant or observation counts changed")
    master = sheets["Urschel et al NatCom all data"]
    master_rows = {master[f"A{r}"]: r for r in range(4, 131)}
    for row in rows:
        r = master_rows[row["participant_id"]]
        col = "AE" if row["timepoint"] == "Before" else "AF"
        if Decimal(master[f"{col}{r}"]) != Decimal(row["igg_bau_ml"]) or master[f"B{r}"] != row["source_infection_status"]:
            raise ValueError("Figure 2 selected measurement differs from master sheet")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / "source-data.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    group_counts = Counter(r["infection_group"] for r in rows if r["timepoint"] == "Before")
    checks = {
        "source_url": SOURCE_URL, "source_sha256": sha,
        "csv_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "selected_sheet": "figure 2", "selected_rows": [4, 130], "selected_measurement_columns": ["C", "D"],
        "participants": len(ids), "observations": len(rows), "complete_pairs": len(ids),
        "participants_by_group": dict(group_counts), "missing_values": 0, "nonpositive_values": 0,
        "raw_classification_counts": dict(Counter(r["source_infection_status"] for r in rows if r["timepoint"] == "Before")),
        "yes_ncap_positive_ids": [r["participant_id"] for r in rows if r["timepoint"] == "Before" and r["source_infection_status"] == "yes/NCAP+"],
        "master_sheet_agreement": "All 254 selected values and 127 infection classifications agree with master-sheet AE/AF/B by ID",
        "all_values_preserved": True, "float_rounding_in_csv": False,
    }
    (args.out_dir / "source-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
