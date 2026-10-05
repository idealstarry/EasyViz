#!/usr/bin/env python3
"""Reject scientific/vector corruptions using temporary copies only."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def edit_csv(path, change):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream)); fields = list(rows[0])
    change(rows)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def rebind_copied_paths(output, case):
    """Keep a temporary byte-identical copy current before testing mutations."""
    primary = {"data_file": str((case / "inputs/coefficients.csv").resolve()),
               "source_script": str((case / "plot.py").resolve()), "spec_file": str((case / "spec.json").resolve())}
    contract = str((case / "inputs/input-contract.json").resolve())
    for name in ("settings.json", "qa.json", "elements.json", "handoff.json", "consumed-sources.json"):
        path = output / name; record = json.loads(path.read_text())
        if "input" in record:
            record["input"].update(primary)
            if "auxiliary_inputs" in record["input"]:
                record["input"]["auxiliary_inputs"]["source_contract"]["path"] = contract
        for role, binding in record.get("source_bindings", {}).items():
            if role in primary: binding["path"] = primary[role]
            elif role == "source_contract": binding["path"] = contract
        if "source_paths" in record:
            record["source_paths"].update(primary); record["source_paths"]["contract_file"] = contract
        path.write_text(json.dumps(record, indent=2) + "\n")
    path = output / "consumed-sources.json"; record = json.loads(path.read_text())
    record["handoff_sha256"] = digest(output / "handoff.json")
    path.write_text(json.dumps(record, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "output")
    args = parser.parse_args()
    loader = importlib.util.spec_from_file_location("independent_signature_validator", HERE / "validate.py")
    module = importlib.util.module_from_spec(loader); loader.loader.exec_module(module)
    module.validate(args.out)
    results = []

    def false_empty_agreement(output, case):
        def change(rows):
            next(row for row in rows if row["shared_nonzero_genes"] == "0")["sign_agreement"] = "0"
        edit_csv(output / "all-pair-overlaps.csv", change)

    def false_overlap(output, case):
        def change(rows):
            rows[0]["shared_nonzero_genes"] = str(int(rows[0]["shared_nonzero_genes"]) + 1)
        edit_csv(output / "all-pair-overlaps.csv", change)

    def false_contributor(output, case):
        path = output / "elements.json"; data = json.loads(path.read_text())
        record = next(record for record in data["elements"] if record["role"] == "paired-coefficient-gene")
        record["source_keys"][0]["gene"] = "FALSE_GENE"
        path.write_text(json.dumps(data))

    def shifted_actual_marker(output, case):
        mapping = output / "elements.json"; data = json.loads(mapping.read_text())
        record = next(record for record in data["elements"] if record["role"] == "paired-coefficient-gene")
        path = output / "panel.svg"; tree = ET.parse(path)
        group = next(node for node in tree.iter() if node.get("id") == record["id"])
        use = group.find(".//{http://www.w3.org/2000/svg}use")
        use.set("x", str(float(use.get("x")) + 5)); tree.write(path)
        # Refresh hashes deliberately: this tests vector values, not merely
        # the stale-file guard.
        data["version"]["figure_sha256"] = digest(path); mapping.write_text(json.dumps(data))
        qa_path = output / "qa.json"; qa = json.loads(qa_path.read_text())
        qa["exports"]["svg"]["sha256"] = digest(path); qa_path.write_text(json.dumps(qa))

    def changed_literal_source(output, case):
        def change(rows):
            row = next(row for row in rows if float(row["coefficient"]) != 0)
            row["coefficient"] = str(-float(row["coefficient"]))
        edit_csv(case / "inputs/coefficients.csv", change)

    def lost_retained_gene(output, case):
        edit_csv(output / "all-shared-gene-coefficients.csv", lambda rows: rows.pop())

    def changed_consumed_contract(output, case):
        path = case / "inputs/input-contract.json"
        path.write_bytes(path.read_bytes() + b"\n")

    def false_executed_helper(output, case):
        path = output / "qa.json"; record = json.loads(path.read_text())
        record["executed_helper_sha256"]["helper:figure_handoff.py"] = "0" * 64
        path.write_text(json.dumps(record))

    def wrong_current_receipt(output, case):
        path = output / "consumed-sources.json"; record = json.loads(path.read_text())
        record["handoff_sha256"] = "0" * 64
        path.write_text(json.dumps(record))

    probes = [false_empty_agreement, false_overlap, false_contributor, shifted_actual_marker, changed_literal_source,
              lost_retained_gene, changed_consumed_contract, false_executed_helper, wrong_current_receipt]
    with tempfile.TemporaryDirectory(prefix="easyviz-signature-probes-") as directory:
        for index, probe in enumerate(probes):
            case = Path(directory) / str(index); case.mkdir()
            shutil.copytree(HERE / "inputs", case / "inputs")
            shutil.copy2(HERE / "spec.json", case / "spec.json")
            shutil.copy2(HERE / "plot.py", case / "plot.py")
            output = case / "output"; shutil.copytree(args.out, output)
            rebind_copied_paths(output, case)
            module.HERE = case
            module.validate(output)
            probe(output, case)
            try:
                module.validate(output)
            except (ValueError, KeyError) as error:
                results.append({"probe": probe.__name__, "status": "rejected", "evidence": str(error)})
            else:
                raise AssertionError(f"The validator accepted corruption: {probe.__name__}")
    result = {"status": "passed", "scope": "Nine deliberate source/derived/artist/consumption corruptions rejected in verified current temporary copies; no aesthetic claim", "probes": results}
    (args.out / "validation-probes.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__": main()
