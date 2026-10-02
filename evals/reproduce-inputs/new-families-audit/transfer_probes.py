#!/usr/bin/env python3
"""Independent changed-schema CLI probes; these are synthetic engineering inputs.

No production module is imported. Generated exports are checked with the
independent SVG/PDF evaluator beside this file, then input failures are tried
in a directory that already contains a passing export to verify stale QA.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import verify

HERE, ROOT = Path(__file__).resolve().parent, verify.ROOT


def inputs(folder, data, spec):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "source.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    (folder / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")


def run(name, folder, output="output"):
    env = dict(os.environ, MPLCONFIGDIR="/private/tmp/easyviz-diversity-audit-mpl")
    return subprocess.run([sys.executable, str(ROOT / "skills/easyviz/scripts" / f"{name}_plot.py"), "--data", str(folder / "source.csv"), "--spec", str(folder / "spec.json"), "--out", str(folder / output)], env=env, capture_output=True, text=True)


def probe(name, data, spec, invalid_data, invalid_spec, auditor):
    folder = HERE / "transfer" / name
    inputs(folder, data, spec)
    result = run(name, folder)
    verify.check(f"Changed schema {name}: public CLI render", result.returncode == 0, return_code=result.returncode, output=result.stdout.strip(), error=result.stderr[-500:])
    if result.returncode:
        return
    shutil.copyfile(folder / "source.csv", folder / "source-original.csv")
    plotted = verify.rows(folder / "output/plotting-data.csv")
    identity_roles = [column for role, column in spec["fields"].items() if role != "value"]
    verify.check(f"Changed schema {name}: literal IDs and category strings preserved", len(plotted) == len(data) and all(str(source[column]) == actual[column] for source, actual in zip(data, plotted) for column in identity_roles), mapped_string_columns=identity_roles)
    auditor(folder / "output", folder / "source.csv", folder / "spec.json")
    first_digest = verify.digest(folder / "output/panel.png")
    inputs(folder, list(reversed(data)), spec)
    shutil.copyfile(folder / "source.csv", folder / "source-reversed.csv")
    result = run(name, folder, "output-reversed")
    verify.check(f"Changed schema {name}: source row permutation preserves picture", result.returncode == 0 and verify.digest(folder / "output-reversed/panel.png") == first_digest, original_png_sha256=first_digest, return_code=result.returncode)
    # A failed attempt must invalidate the earlier successful output directory.
    inputs(folder, invalid_data, invalid_spec)
    shutil.copyfile(folder / "source.csv", folder / "source-rejected.csv")
    result = run(name, folder)
    qa = json.loads((folder / "output/qa.json").read_text())
    verify.check(f"Changed schema {name}: ambiguity rejected and old exports invalidated", result.returncode != 0 and qa.get("valid_outputs") is False and qa.get("status") == "failed", return_code=result.returncode, attempt_status=qa.get("status"), error=qa.get("error"))
    # Restore the inspectable passing case without overwriting failure evidence.
    (folder / "rejected-qa.json").write_text(json.dumps(qa, indent=2) + "\n")
    inputs(folder, data, spec)
    result = run(name, folder)
    verify.check(f"Changed schema {name}: repaired run returns original picture", result.returncode == 0 and verify.digest(folder / "output/panel.png") == first_digest)


def main():
    layout = {"width_mm": 110, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 200, "auto_fit": True}
    ecdf = [{"pid": f"{i:03d}", "phase": group, "v": value} for group, values in (("NA", [0, 0, 2]), ("001", [1, 2, 2, 2])) for i, value in enumerate(values, 1)]
    ecdf_spec = {"chart": "ecdf", "fields": {"value": "v", "group": "phase", "unit": "pid"}, "order": {"group": ["001", "NA"]}, "colors": {"001": "#A05272", "NA": "#4E78A0"}, "labels": {"x": "Measurement", "y": "Cumulative fraction"}, "options": {"x_scale": "linear", "x_limits": [-1, 3], "x_ticks": [-1, 0, 1, 2, 3]}, "layout": deepcopy(layout), "legends": {"categorical": {"position": "bottom", "ncol": 2}}, "formats": ["png", "pdf", "svg"]}
    invalid_ecdf = deepcopy(ecdf)
    invalid_ecdf.append(deepcopy(ecdf[0]))
    probe("ecdf", ecdf, ecdf_spec, invalid_ecdf, ecdf_spec, verify.audit_ecdf)

    paired = []
    for arm, identifiers in (("Arm Z", ["001", "002"]), ("Arm A", ["003", "004"])):
        for number, unit in enumerate(identifiers, 1):
            for visit, value in (("Baseline", number - 2), ("Interim", number * 2), ("Follow-up", number * 4)):
                paired.append({"wid": unit, "visit": visit, "measurement": value, "arm": arm})
    paired_spec = {"chart": "paired", "fields": {"unit": "wid", "condition": "visit", "value": "measurement", "block": "arm"}, "order": {"condition": ["Follow-up", "Baseline", "Interim"], "block": ["Arm Z", "Arm A"]}, "colors": {"Arm Z": "#4E78A0", "Arm A": "#A05272"}, "labels": {"y": "Measurement"}, "options": {"y_scale": "linear", "y_limits": [-4, 12], "quantile_method": "weibull", "point_layout": "jitter", "point_area_pt2": 7, "connect_pairs": True, "block_gap": .4}, "layout": deepcopy(layout), "legends": {"categorical": {"position": "bottom", "ncol": 2}}, "formats": ["png", "pdf", "svg"]}
    probe("paired", paired, paired_spec, paired[:-1], paired_spec, verify.audit_paired)

    replicate = [{"treatment": condition, "run": f"{unit:03d}", "analyte": component, "observation": value + unit} for condition in ("Zulu", "Alpha") for component, value in (("001", -3), ("002", 0), ("003", 5)) for unit in (1, 2)]
    replicate_spec = {"chart": "replicate", "fields": {"condition": "treatment", "unit": "run", "value": "observation", "component": "analyte"}, "order": {"condition": ["Zulu", "Alpha"], "component": ["003", "001", "002"]}, "colors": {"003": "#4E78A0", "001": "#A05272", "002": "#C49E54"}, "labels": {"y": "Measurement"}, "options": {"mode": "grouped", "uncertainty": "sample_sd", "bar_width": .6, "marker_area_pt2": 7, "y_limits": [-5, 15]}, "layout": deepcopy(layout), "legends": {"categorical": {"position": "top", "ncol": 3}}, "formats": ["png", "pdf", "svg"]}
    probe("replicate", replicate, replicate_spec, replicate[:-1], replicate_spec, verify.audit_replicate)
    report = {"status": "pass" if all(c["status"] == "pass" for c in verify.CHECKS) else "fail", "scope": "Synthetic engineering transfer only, not independent literature evidence or new biological replication.", "independence": "Public CLI only; independent SVG/PDF evaluator imports no plotting implementation.", "passed": sum(c["status"] == "pass" for c in verify.CHECKS), "total": len(verify.CHECKS), "checks": verify.CHECKS}
    (HERE / "transfer-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "passed", "total")}))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
