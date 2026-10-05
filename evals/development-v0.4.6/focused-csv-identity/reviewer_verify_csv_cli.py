"""Independent CLI replay of literal CSV fields and source identities.

Only writes reviewer evidence into a new directory; does not edit runtime.
Uses the saved pre-fix source/spec bytes as controls, without importing the
implementation owner's verifier or tests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
NAMES = ("replicate_plot", "ecdf_plot", "interval_plot", "timecourse_plot")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_table(path):
    return list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"), newline=""), strict=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    if args.out.exists():
        raise RuntimeError("Reviewer evidence is immutable; choose a fresh folder")
    out = args.out.resolve()
    out.mkdir(parents=True)
    before = json.loads((BASE / "before-exports/evidence.json").read_text())
    baseline = {(x["recipe"], x["variant"]): x for x in before["cases"]}
    identities = {name: digest(runtime / (name + ".py")) for name in NAMES}
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["MPLCONFIGDIR"] = str(out / "matplotlib-cache")
    result = {"review_scope": "Four focused CSV readers only; no aesthetic or first-delivery claim", "runtime": str(runtime),
              "runtime_sha256": identities, "cases": []}
    for name in NAMES:
        for variant in ("legal", "extra-leading-cell", "legal-crlf-bom-literal-identities"):
            control = BASE / "before-exports" / (name + "-" + ("extra-leading-cell" if variant == "extra-leading-cell" else "legal"))
            case = out / (name + "-" + variant)
            case.mkdir()
            source, spec, exports = case / "source.csv", case / "spec.json", case / "exports"
            original = (control / "source.csv").read_bytes()
            if variant == "legal-crlf-bom-literal-identities":
                rows = read_table(control / "source.csv")
                if name == "timecourse_plot":
                    rows[0].append("sample_identifier")
                    for row, label in zip(rows[1:], ("001", "NA", "002,α", "0004")):
                        row.append(label)
                else:
                    for row, label in zip(rows[1:], ("001", "NA", "002,α", "0004")):
                        row[0] = label
                stream = io.StringIO(newline="")
                csv.writer(stream, lineterminator="\r\n").writerows(rows)
                original = b"\xef\xbb\xbf" + stream.getvalue().encode()
            source.write_bytes(original)
            spec.write_bytes((control / "spec.json").read_bytes())
            execution = subprocess.run([sys.executable, "-I", "-B", str(runtime / (name + ".py")),
                                        "--data", str(source), "--spec", str(spec), "--out", str(exports)],
                                       cwd=case, env=environment, capture_output=True, text=True)
            (case / "cli.log").write_text(execution.stdout + execution.stderr)
            qa = json.loads((exports / "qa.json").read_text())
            export_hashes = {suffix: digest(exports / ("panel." + suffix)) for suffix in ("png", "pdf", "svg")
                             if (exports / ("panel." + suffix)).exists()}
            entry = {"recipe": name, "variant": variant, "exit_code": execution.returncode,
                     "qa_valid_outputs": qa["valid_outputs"], "qa_status": qa["status"], "error": qa.get("error"),
                     "source_sha256": digest(source), "exports": export_hashes}
            assert source.read_bytes() == original, entry
            if variant == "extra-leading-cell":
                assert execution.returncode != 0 and not qa["valid_outputs"] and not export_hashes, entry
                assert not (exports / "elements.json").exists(), entry
                assert "exactly match header width" in qa["error"], entry
                entry["rejected_before_exports"] = True
            else:
                assert execution.returncode == 0 and qa["valid_outputs"] and len(export_hashes) == 3, entry
                settings = json.loads((exports / "settings.json").read_text())
                elements = json.loads((exports / "elements.json").read_text())
                source_hash = hashlib.sha256(original).hexdigest()
                assert qa["input_sha256"] == settings["input_sha256"] == elements["version"]["input_sha256"] == source_hash, entry
                assert settings["source_bindings"]["data_file"] == {"path": str(source), "sha256": source_hash}, entry
                assert elements["input"]["data_file"] == str(source), entry
                table, prepared = read_table(source), read_table(exports / "plotting-data.csv")
                numeric = {"value", "est", "lo", "hi"} if name != "timecourse_plot" else set()
                for column in table[0]:
                    if column in numeric:
                        assert [float(row[table[0].index(column)]) for row in table[1:]] == [float(row[prepared[0].index(column)]) for row in prepared[1:]], entry
                    else:
                        assert [row[table[0].index(column)] for row in table[1:]] == [row[prepared[0].index(column)] for row in prepared[1:]], entry
                entry["all_original_cells_preserved"] = True
                entry["all_source_identities_agree"] = True
                if variant == "legal":
                    assert export_hashes == baseline[(name, "legal")]["exports"], entry
                    entry["all_exports_byte_identical_to_before"] = True
            result["cases"].append(entry)
    assert identities == {name: digest(runtime / (name + ".py")) for name in NAMES}, "Candidate changed during review"
    result["all_cases_pass"] = True
    (out / "evidence.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"all_cases_pass": True, "cases": len(result["cases"]), "evidence": str(out / "evidence.json")}))


if __name__ == "__main__":
    main()
