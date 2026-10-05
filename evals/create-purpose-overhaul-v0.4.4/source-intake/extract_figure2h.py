"""Extract exact published numeric strings and cell provenance; do not pair slots."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
EXPECTED = "9d22b0726cea419ea7c06c57ff380bae25a930d3618bfbd68cedac0af64fa545"
POPULATIONS = ["cMo", "pMo", "SPM", "LPM", "RPM", "KC", "SILPM", "CLPM", "MG"]


def extract() -> None:
    source = ROOT / "41590_2023_1468_MOESM4_ESM.xlsx"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == EXPECTED
    with ZipFile(source) as z:
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        sheet = next(s for s in workbook.find("s:sheets", NS) if s.attrib["name"] == "2h")
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = next(r.attrib["Target"] for r in rels if r.attrib["Id"] == sheet.attrib[R + "id"])
        path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        tree = ET.fromstring(z.read(path))
        cells = {c.attrib["r"]: c for c in tree.findall(".//s:c", NS)}
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(t.text or "" for t in si.findall(".//s:t", NS))
                      for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        styles = ET.fromstring(z.read("xl/styles.xml")).find("s:cellXfs", NS)

        def text(c):
            v = c.find("s:v", NS)
            if c.attrib.get("t") == "s":
                return shared[int(v.text)]
            if c.attrib.get("t") == "inlineStr":
                return "".join(t.text or "" for t in c.findall(".//s:t", NS))
            return None if v is None else v.text

        def fill(c):
            return styles[int(c.attrib.get("s", "0"))].attrib["fillId"]

        assert text(cells["W3"]).strip() == "-DT" and text(cells["W4"]).strip() == "+DT"
        rows = []
        counts = []
        for row_number, population in enumerate(POPULATIONS, 3):
            assert text(cells[f"A{row_number}"]) == population
            group_counts = {}
            for condition, columns, legend in [
                ("-DT", "BCDEFGHIJK", "W3"), ("+DT", "LMNOPQRSTU", "W4")
            ]:
                n = 0
                for col in columns:
                    coord = f"{col}{row_number}"
                    c = cells.get(coord)
                    if c is None or text(c) is None:
                        continue
                    assert c.attrib.get("t", "n") == "n", coord
                    assert c.find("s:f", NS) is None, coord
                    assert fill(c) == fill(cells[legend]), coord
                    rows.append({"population": population, "condition": condition,
                                 "normalized_count": text(c), "source_sheet": "2h",
                                 "source_cell": coord})
                    n += 1
                group_counts[condition] = n
            counts.append({"population": population, **group_counts})
    assert len(rows) == 156 and sum(c["-DT"] for c in counts) == 76
    assert sum(c["+DT"] for c in counts) == 80
    with (ROOT / "observations.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    contract = {
        "source": source.name, "source_sha256": EXPECTED, "sheet": "2h",
        "doi": "10.1038/s41590-023-01468-3", "license": "CC BY 4.0",
        "population_order": POPULATIONS, "condition_order": ["-DT", "+DT"],
        "observation_count": len(rows), "counts": counts,
        "units": "Author-supplied normalized cell number (dimensionless); exact denominator unavailable.",
        "summary": "Mean and SEM calculated within each supplied population/condition group.",
        "experimental_unit": "Mouse; pooled experiments, but IDs and batches are absent.",
        "pairing": "No pairing may be inferred from cell/column positions.",
        "missing": "Empty workbook slots are absent observations, never zeros.",
        "normalization": "Values already normalized by authors; preserve without re-normalizing.",
        "inference": "Descriptive plotting only; no additional tests or reconstructed significance."
    }
    (ROOT / "input-contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    print(json.dumps({"observations": len(rows), "counts": counts}, indent=2))


if __name__ == "__main__":
    extract()
