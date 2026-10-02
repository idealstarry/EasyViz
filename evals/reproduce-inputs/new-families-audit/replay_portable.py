#!/usr/bin/env python3
"""Replay six new views from an actual ZIP outside the checkout.

This is same-environment portability and byte-identical PNG replay evidence,
not cross-platform validation or a new aesthetic review. No plotting module is
imported into this evaluator. A Python audit hook records each wrapper's actual
child command, proving its discovered runtime is inside the extracted package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

import pymupdf

ROOT = Path(__file__).resolve().parents[3]

CASES = [
    {"name": "urschel-paired", "case": "urschel-paired", "reference": "examples/no-author-code/urschel-paired", "renderer": "paired_plot.py", "data": "source-data.csv", "spec": "spec.json", "original": "output", "args": []},
    {"name": "urschel-paired-connectors", "case": "urschel-paired", "reference": "examples/no-author-code/urschel-paired", "renderer": "paired_plot.py", "data": "source-data.csv", "spec": "connectors-spec.json", "original": "output-connectors", "args": ["--spec", "{spec}"]},
    {"name": "urschel-ecdf", "case": "urschel-ecdf", "reference": "examples/create/urschel-ecdf", "renderer": "ecdf_plot.py", "data": "source-data.csv", "spec": "spec.json", "original": "output", "args": []},
    {"name": "truong-components-stacked", "case": "truong-components", "reference": "examples/no-author-code/truong-components", "renderer": "replicate_plot.py", "data": "inputs/components.csv", "spec": "components-spec.json", "original": "output-components", "args": []},
    {"name": "truong-components-ratios", "case": "truong-components", "reference": "examples/no-author-code/truong-components", "renderer": "replicate_plot.py", "data": "inputs/ratios.csv", "spec": "ratios-spec.json", "original": "output-ratios", "args": ["--data", "{data}", "--spec", "{spec}"]},
    {"name": "truong-components-grouped", "case": "truong-components", "reference": "examples/no-author-code/truong-components", "renderer": "replicate_plot.py", "data": "inputs/components.csv", "spec": "grouped-spec.json", "original": "output-grouped", "args": ["--spec", "{spec}"]},
]

AUDIT_HARNESS = """
import json, pathlib, runpy, sys
log = pathlib.Path(sys.argv[1])
wrapper = sys.argv[2]
arguments = sys.argv[3:]
def record(event, args):
    if event == 'subprocess.Popen':
        executable, argv, cwd, env = args
        with log.open('a') as handle:
            handle.write(json.dumps({'executable': executable, 'argv': argv, 'cwd': cwd}) + '\\n')
sys.addaudithook(record)
sys.argv = [wrapper, *arguments]
runpy.run_path(wrapper, run_name='__main__')
"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "dist/easyviz-0.2.0.zip")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--report", type=Path, default=ROOT / "evals/reproduce-inputs/diversity-portable-replay.json")
    args = parser.parse_args()
    if sha(args.archive) != args.expected_sha:
        parser.error("Archive hash differs from the requested snapshot; supply its actual intended SHA explicitly.")
    working = Path(tempfile.mkdtemp(prefix=f"easyviz-diversity-replay-{args.expected_sha[:8]}-", dir="/private/tmp"))
    archive = working / "package.zip"
    shutil.copyfile(args.archive, archive)
    extracted = working / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            destination = (extracted / member.filename).resolve()
            if not destination.is_relative_to(extracted):
                raise ValueError(f"Unsafe package member: {member.filename}")
        file_count = sum(not member.is_dir() for member in bundle.infolist())
        bundle.extractall(extracted)
    package = extracted / "easyviz/skills/easyviz"
    runtime = package / "scripts"
    results = []
    environment = dict(os.environ, MPLCONFIGDIR=str(working / "font-cache"), PYTHONPATH="", PYTHONNOUSERSITE="1")
    environment.pop("PYTHONSTARTUP", None)
    for case in CASES:
        base = package / "assets/cases" / case["case"]
        reference = ROOT / case["reference"]
        data, spec = base / case["data"], base / case["spec"]
        input_before, spec_before = sha(data), sha(spec)
        original_png = reference / case["original"] / "panel.png"
        reviewed_png_sha = sha(original_png)
        source_png_sha = sha(base / case["original"] / "panel.png")
        output = working / "outputs" / case["name"]
        log = working / f"{case['name']}-child-commands.jsonl"
        arguments = [str(data) if value == "{data}" else str(spec) if value == "{spec}" else value for value in case["args"]]
        arguments.extend(["--out", str(output)])
        command = [sys.executable, "-c", AUDIT_HARNESS, str(log), str(base / "plot.py"), *arguments]
        completed = subprocess.run(command, cwd=working, env=environment, capture_output=True, text=True)
        source_equal = input_before == sha(reference / case["data"])
        spec_equal = json.loads(spec.read_text()) == json.loads((reference / case["spec"]).read_text())
        record = {"view": case["name"], "return_code": completed.returncode, "working_directory": str(working), "wrapper": str(base / "plot.py"), "arguments": arguments, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip(), "input_sha256": input_before, "spec_sha256": spec_before, "reviewed_repo_spec_sha256": sha(reference / case["spec"]), "spec_file_byte_identical_to_reviewed_case": spec_before == sha(reference / case["spec"]), "spec_semantically_equals_reviewed_case": spec_equal, "spec_serialization_note": "Packaged JSON may encode µ as \\u00b5; decoded keys and values must remain identical.", "reviewed_repo_png_sha256": reviewed_png_sha, "packaged_case_png_sha256": source_png_sha, "source_data_byte_identical_to_reviewed_case": source_equal, "source_inputs_equal_reviewed_case": source_equal and spec_equal, "packaged_inputs_unchanged": input_before == sha(data) and spec_before == sha(spec), "packaged_case_png_equals_reviewed_case": source_png_sha == reviewed_png_sha}
        if completed.returncode == 0:
            settings = json.loads((output / "settings.json").read_text())
            qa = json.loads((output / "qa.json").read_text())
            commands = [json.loads(line) for line in log.read_text().splitlines()]
            called = [Path(entry["argv"][1]).resolve() for entry in commands]
            intended_runtime = (runtime / case["renderer"]).resolve()
            discovered_inside = len(called) == 1 and called[0] == intended_runtime and called[0].is_relative_to(extracted)
            renderer_info = settings["renderer"]
            helper_hashes_match = bool(renderer_info.get("helper_sha256")) and all(value == sha(runtime / name) for name, value in renderer_info["helper_sha256"].items())
            spec_value = json.loads(spec.read_text())
            target_mm = [float(spec_value["layout"][key]) for key in ("width_mm", "height_mm")]
            with pymupdf.open(output / "panel.pdf") as pdf:
                physical_mm = [pdf[0].rect.width * 25.4 / 72, pdf[0].rect.height * 25.4 / 72]
            replay_sha = sha(output / "panel.png")
            record.update({"output": str(output), "observed_child_commands": commands, "discovered_runtime": str(called[0]) if called else None, "wrapper_discovered_extracted_runtime": discovered_inside, "renderer_hash_matches_extracted_runtime": renderer_info["sha256"] == sha(intended_runtime), "helper_hashes_match_extracted_runtime": helper_hashes_match, "settings_source_path_matches_extracted_input": Path(settings["input_file"]).resolve() == data.resolve(), "settings_input_sha_matches_unchanged_input": settings["input_sha256"] == input_before, "font_preserved": settings["layout"]["font"] == spec_value["layout"]["font"] == "Arial" and settings["layout"]["font_size_pt"] == spec_value["layout"]["font_size_pt"], "pdf_physical_mm": physical_mm, "requested_mm": target_mm, "pdf_dimensions_match": all(abs(actual - requested) < .001 for actual, requested in zip(physical_mm, target_mm)), "replayed_png_sha256": replay_sha, "png_byte_identical_to_reviewed_case": replay_sha == reviewed_png_sha, "qa_pass": qa["status"] == "pass" and qa.get("valid_outputs") is True})
            requirements = [record[key] for key in ("source_inputs_equal_reviewed_case", "packaged_inputs_unchanged", "packaged_case_png_equals_reviewed_case", "wrapper_discovered_extracted_runtime", "renderer_hash_matches_extracted_runtime", "helper_hashes_match_extracted_runtime", "settings_source_path_matches_extracted_input", "settings_input_sha_matches_unchanged_input", "font_preserved", "pdf_dimensions_match", "png_byte_identical_to_reviewed_case", "qa_pass")]
            record["status"] = "pass" if all(requirements) else "fail"
        else:
            record["status"] = "fail"
        results.append(record)
    report = {"status": "pass" if all(item["status"] == "pass" for item in results) and sha(archive) == args.expected_sha else "fail", "scope": "Actual ZIP extraction and public wrapper execution outside checkout, in the same Python/library/font environment. Byte-identical PNG replay and physical PDF dimensions; no cross-platform or new aesthetic claim.", "archive": str(args.archive.resolve()), "archive_sha256": sha(archive), "archive_files": file_count, "snapshot_archive": str(archive), "extracted_package": str(package), "working_directory": str(working), "python_executable": sys.executable, "python_version": platform.python_version(), "checkout_roles": ["audit orchestrator", "reviewed reference exports and source/spec comparisons", "same Python/library environment"], "runtime_code_loaded_from_extracted_package": all(item.get("wrapper_discovered_extracted_runtime") for item in results), "views_passed": sum(item["status"] == "pass" for item in results), "views_total": len(results), "results": results}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "archive_sha256", "archive_files", "views_passed", "views_total", "working_directory")}))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
