#!/usr/bin/env python3
"""Exercise meaningful reject paths without changing the selected source/exports."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

import pymupdf
from validate import validate

HERE = Path(__file__).resolve().parent
SVG = {"s": "http://www.w3.org/2000/svg"}


def alter_table(folder):
    path = folder / "transformed-cells.csv"
    with path.open(newline="") as stream: records = list(csv.DictReader(stream))
    records[0]["log2_tpm_plus_1"] = str(float(records[0]["log2_tpm_plus_1"]) + .1)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)


def alter_svg(folder, operation):
    path = folder / "panel.svg"
    tree = ET.parse(path); mapping = json.loads((folder / "elements.json").read_text())
    identifier = next(record["id"] for record in mapping["elements"] if record["role"] == "expression-cell")
    group = next(node for node in tree.iter() if node.get("id") == identifier)
    artist = group.find("s:path", SVG)
    if operation == "fill": artist.set("style", re.sub(r"fill:\s*#[0-9a-fA-F]{6}", "fill: #000000", artist.get("style")))
    else:
        # A valid rectangle shifted by exactly 1 pt; metadata hashes are updated
        # so the numeric geometry audit, rather than a stale-hash check, rejects it.
        values = [float(value) for value in re.findall(r"[-+]?\d+(?:\.\d*)?", artist.get("d"))]
        artist.set("d", "M " + " L ".join(f"{x + 1} {y}" for x, y in zip(values[::2], values[1::2])) + " z")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    mapping["version"]["figure_sha256"] = digest
    (folder / "elements.json").write_text(json.dumps(mapping))
    qa = json.loads((folder / "qa.json").read_text()); qa["exports"]["svg"]["sha256"] = digest
    (folder / "qa.json").write_text(json.dumps(qa))


def alter_source_binding(folder):
    path = folder / "elements.json"; mapping = json.loads(path.read_text())
    record = next(record for record in mapping["elements"] if record["role"] == "expression-cell")
    record["source_keys"][0]["source_cell"] = "B4"
    path.write_text(json.dumps(mapping))


def crop_pdf(folder):
    path = folder / "panel.pdf"
    with pymupdf.open(path) as document:
        page = document[0]; page.set_mediabox(pymupdf.Rect(0, 0, page.rect.width, page.rect.height - 5))
        document.save(folder / "changed.pdf")
    (folder / "changed.pdf").replace(path)
    qa = json.loads((folder / "qa.json").read_text()); qa["exports"]["pdf"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (folder / "qa.json").write_text(json.dumps(qa))


def omit_required_helper(folder):
    role = "runtime:observation_clipping.py"
    for filename in ("settings.json", "qa.json", "consumed-sources.json"):
        path = folder / filename; saved = json.loads(path.read_text())
        saved["source_bindings"].pop(role)
        if "executed_helper_sha256" in saved: saved["executed_helper_sha256"].pop(role)
        path.write_text(json.dumps(saved))
    receipt = folder / "handoff.json"; saved = json.loads(receipt.read_text())
    saved["input"]["auxiliary_inputs"].pop(role); saved["consumption"]["auxiliary_sha256"].pop(role)
    receipt.write_text(json.dumps(saved))
    consumed = folder / "consumed-sources.json"; saved = json.loads(consumed.read_text())
    saved["handoff_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    consumed.write_text(json.dumps(saved))


def alter_receipt_dimensions(folder):
    receipt = folder / "handoff.json"; saved = json.loads(receipt.read_text())
    saved["panel"]["height_mm"] += 1
    receipt.write_text(json.dumps(saved))
    consumed = folder / "consumed-sources.json"; saved = json.loads(consumed.read_text())
    saved["handoff_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    consumed.write_text(json.dumps(saved))


def run(selected_output=None):
    selected_output = selected_output or HERE / "output"
    records = []
    scenarios = [("changed transformed abundance", alter_table), ("wrong expression fill with refreshed byte hashes", lambda folder: alter_svg(folder, "fill")),
                 ("moved expression rectangle with refreshed byte hashes", lambda folder: alter_svg(folder, "geometry")),
                 ("false source-cell artist identity", alter_source_binding), ("cropped actual PDF with refreshed byte hash", crop_pdf),
                 ("required renderer helper omitted from mutually refreshed metadata", omit_required_helper),
                 ("wrong receipt physical height with refreshed receipt evidence hash", alter_receipt_dimensions)]
    with tempfile.TemporaryDirectory(prefix="easyviz-expression-negative-checks-") as temporary:
        for index, (name, operation) in enumerate(scenarios):
            folder = Path(temporary) / str(index); shutil.copytree(selected_output, folder)
            operation(folder)
            try: validate(folder)
            except ValueError as error: records.append({"scenario": name, "status": "rejected", "reason": str(error)})
            else: raise RuntimeError("The independent validator accepted " + name)
    return {"status": "pass", "scenarios": records, "scope": "Seven fault-injection checks for actual source/geometry/closure/receipt invariants; selected source and exports are untouched."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "output")
    parser.add_argument("--report", type=Path, default=HERE / "mutation-validation.json")
    args = parser.parse_args()
    report = run(args.output)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "pass", "rejected_scenarios": len(report["scenarios"])}))
