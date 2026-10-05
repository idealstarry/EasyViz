#!/usr/bin/env python3
"""Exercise actual late-change reject paths in fresh disposable render attempts.

Run with the adopted EasyViz runtime on PYTHONPATH. Selected case inputs and
exports are untouched; changes occur only to disposable copied input files.
"""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def run():
    records = []
    for role in ("data_file", "spec_file", "source_contract"):
        with tempfile.TemporaryDirectory(prefix="easyviz-expression-receipt-check-") as temporary:
            root = Path(temporary)
            inputs = root / "inputs"
            shutil.copytree(HERE / "inputs", inputs)
            data, contract, spec = inputs / "observations.csv", inputs / "input-contract.json", root / "spec.json"
            shutil.copyfile(HERE / "spec.json", spec)
            target = {"data_file": data, "spec_file": spec, "source_contract": contract}[role]
            original = target.read_bytes()
            destination = root / "output"
            write = Path.write_text
            injected = False

            def mutate_after_validated_qa(path, text, *args, **kwargs):
                # The numeric/export audit has already finished. The receipt
                # must refuse newly changed bytes, even when semantics do not.
                nonlocal injected
                result = write(path, text, *args, **kwargs)
                if path == destination / "qa.json" and json.loads(text).get("status") == "pass" and not injected:
                    target.write_bytes(original + b"\n")
                    injected = True
                return result

            arguments = [str(HERE / "plot.py"), "--data", str(data), "--contract", str(contract),
                         "--spec", str(spec), "--out", str(destination)]
            with patch.object(sys, "argv", arguments), patch.object(Path, "write_text", mutate_after_validated_qa):
                try:
                    runpy.run_path(str(HERE / "plot.py"), run_name="__main__")
                except Exception as error:
                    assert injected and "changed after" in str(error), "The intended late-mutation guard was not exercised"
                    qa = json.loads((destination / "qa.json").read_text())
                    assert qa["status"] == "failed" and qa["valid_outputs"] is False
                    assert not (destination / "handoff.json").exists()
                    snapshot = {"data_file": "source-data.csv", "spec_file": "spec-snapshot.json", "source_contract": "contract-snapshot.json"}[role]
                    assert (destination / snapshot).read_bytes() == original
                    records.append({"scenario": role + " changed after numerical validation and before receipt publication", "status": "rejected",
                                    "reason": str(error), "failure_qa_preserved": True, "original_consumed_snapshot_preserved": True})
                else:
                    raise RuntimeError("A changed consumed input was accepted: " + role)
    return {"status": "pass", "scenarios": records,
            "scope": "Three real export/late-mutation checks. Exact snapshots, failed QA and absent receipt verified; no claim about arbitrary undeclared dependencies."}


if __name__ == "__main__":
    result = run()
    (HERE / "receipt-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "pass", "late_mutations_rejected": len(result["scenarios"])}))
