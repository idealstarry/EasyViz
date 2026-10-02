#!/usr/bin/env python3
"""Extract only Fig. 1b prepared numerical data; no author plotting code."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean, stdev
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SOURCE_SHA256 = "5a9283a1a16e5ca2f8fe0db16af0656e06ddb275dbfe64751643eb2a6dd8cc51"
SOURCE_URL = "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41592-023-02162-w/MediaObjects/41592_2023_2162_MOESM6_ESM.xlsx"
NAMESPACE = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def extract(source, out):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("The selected official Source Data archive has changed")
    with ZipFile(source) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.findall("m:sheets/m:sheet", NAMESPACE)
        assert [sheet.attrib["name"] for sheet in sheets] == ["Fig. 1b"]
        strings = ["".join(node.itertext()) for node in
                   ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", NAMESPACE)]
        cells = {}
        for cell in ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall(".//m:c", NAMESPACE):
            value = cell.find("m:v", NAMESPACE)
            if value is not None:
                assert cell.find("m:f", NAMESPACE) is None, "No cached formula substitution is allowed"
                cells[cell.attrib["r"]] = strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text
    assert [cells[f"{column}1"] for column in "BEHK"] == ["mutEJ", "HDR & mutEJ", "HDR", "HDR/mutEJ"]
    labels = ["No donor/Cas9", "NTC", "DMSO", "NU-7441 (1 µM)", "KU-0060548 (0.25 µM)", "L755507 (5 µM)", "SCR7 pyrazine (1 µM)"]
    groups = [("HDR", "HIJ"), ("HDR and mutEJ", "EFG"), ("mutEJ", "BCD")]
    wide, components, ratios, summary = [], [], [], []
    max_ratio_residual = 0.
    for number, label in enumerate(labels, 2):
        condition = f"condition_{number - 1}"
        state = "uninterpretable" if number in (2, 3) else "interpretable"
        totals, official_ratios = [], []
        for index in range(3):
            unit = f"{condition}_replicate_{index + 1}"
            values = {name: cells[f"{columns[index]}{number}"] for name, columns in groups}
            ratio_cell = f"{'KLM'[index]}{number}"
            ratio = cells[ratio_cell]
            numeric = {name: float(value) for name, value in values.items()}
            total = sum(numeric.values())
            assert 0 <= total <= 100
            max_ratio_residual = max(max_ratio_residual,
                abs(float(ratio) - (numeric["HDR"] + numeric["HDR and mutEJ"]) / (numeric["mutEJ"] + numeric["HDR and mutEJ"])))
            common = {"source_sheet": "Fig. 1b", "source_row": number,
                      "source_label": cells[f"A{number}"], "condition": label,
                      "condition_id": condition, "unit": unit, "replicate_ordinal": index + 1}
            wide.append({**common, "HDR_percent": values["HDR"],
                         "both_percent": values["HDR and mutEJ"], "mutEJ_percent": values["mutEJ"],
                         "HDR_mutEJ_ratio": ratio, "ratio_state": state,
                         "source_cells": "|".join(f"{columns[index]}{number}" for _, columns in groups) + "|" + ratio_cell})
            for component, columns in groups:
                components.append({**common, "component": component, "value": values[component],
                                   "units": "percent of cells", "source_cell": f"{columns[index]}{number}"})
            ratios.append({**common, "value": ratio, "state": state, "units": "ratio",
                           "source_cell": ratio_cell})
            totals.append(total)
            official_ratios.append(float(ratio))
        for component, columns in groups:
            values = [float(cells[f"{column}{number}"]) for column in columns]
            summary.append({"condition": label, "metric": component, "n_units": 3,
                            "mean": mean(values), "sample_sd": stdev(values), "units": "percent of cells"})
        for metric, values, units in [("total measured components", totals, "percent of cells"),
                                     ("supplied HDR/mutEJ ratio", official_ratios, "ratio")]:
            summary.append({"condition": label, "metric": metric, "n_units": 3,
                            "mean": mean(values), "sample_sd": stdev(values), "units": units})
    assert len(wide) == len(ratios) == 21 and len(components) == 63
    assert max_ratio_residual < 1e-12
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [("source-data.csv", wide), ("components.csv", components),
                       ("ratios.csv", ratios), ("source-summary.csv", summary)]:
        with (out / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    audit = {"status": "pass", "source_url": SOURCE_URL, "source_sha256": digest,
             "source_bytes": source.stat().st_size, "source_sheet": "Fig. 1b",
             "selected_excel_rows": list(range(2, 9)), "source_numeric_cells": 84,
             "conditions": 7, "biological_replicates_per_condition": 3,
             "component_long_rows": 63, "supplied_ratio_rows": 21,
             "source_zeros_preserved": sum(float(row["value"]) == 0 for row in components),
             "numeric_lexemes_preserved": True, "formula_cells": 0,
             "ratio_semantics_check_max_absolute_residual": max_ratio_residual,
             "ratio_values_recomputed": False,
             "not_informative_ratio_conditions": labels[:2],
             "uncertainty": "Sample standard deviation, ddof=1, calculated over the 3 supplied biological replicate values; not SEM or confidence intervals.",
             "unit_ids": "Condition-local replicate ordinals identify rows; they do not establish cross-condition pairing.",
             "control_labels": "A2 and A3 are both '-'; resolved from the published Fig. 1b axis rows and caption as no donor/Cas9 and NTC, respectively.",
             "csv_sha256": {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                            for name in ["source-data.csv", "components.csv", "ratios.csv", "source-summary.csv"]}}
    (out / "source-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(extract(args.source, args.out), indent=2))
