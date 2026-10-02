#!/usr/bin/env python3
"""Replay preserved local-agent trials from relocated copies, without overwrites.

The default interpreter is the repository .venv Python. The independent audit
is called as a utility; this script does not open evaluator or expected files.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[2]
CACHE_NAMES = {"__pycache__", ".matplotlib-cache", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ignore_caches(_root, names):
    return [name for name in names if name in CACHE_NAMES or Path(name).suffix in {".pyc", ".pyo"}]


def tree_hashes(root: Path) -> dict:
    return {str(path.relative_to(root)): sha(path) for path in sorted(root.rglob("*"))
            if path.is_file() and not any(part in CACHE_NAMES for part in path.parts)
            and path.suffix not in {".pyc", ".pyo"}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=REPO / ".venv/bin/python")
    parser.add_argument("--work-dir", type=Path,
                        help="New, nonexistent work directory; defaults to a fresh system tmp directory")
    parser.add_argument("--report", type=Path, default=PACKAGE / "verification/portable-replay.json")
    parser.add_argument("--audit-script", type=Path,
                        default=REPO / "evals/workbuddy/v0.4.1/scripts/audit_outputs.py")
    args = parser.parse_args()
    if args.work_dir:
        work = args.work_dir.resolve()
        work.mkdir(parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="easyviz-v041-package-replay-", dir="/private/tmp"))
    report_path = args.report.resolve()
    evidence = report_path.parent
    evidence.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        raise SystemExit(f"Refuse to overwrite an existing replay record: {report_path}")
    reserved = [evidence / name for name in ["replay-logs", "create-audit-mapping.json",
                "create-numeric-export-audit.json", "reproduce-numeric-export-audit.json"]]
    collisions = [str(path) for path in reserved if path.exists()]
    if collisions:
        raise SystemExit("Choose a fresh evidence directory; existing records are preserved: " + ", ".join(collisions))
    python = args.python.absolute()
    audit = args.audit_script.resolve()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               MPLCONFIGDIR=str(work / "matplotlib-cache"))
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "purpose": "Portable replay of preserved local Codex-agent trials, not a baseline comparison or WorkBuddy evaluation",
        "package_root_at_execution": str(PACKAGE),
        "replay_entrypoint": {"package_relative_path": "replay_and_verify.py", "sha256": sha(Path(__file__))},
        "fresh_temporary_root": str(work),
        "runtime": {"python": str(python), "host_python": platform.python_version()},
        "audit_utility": {"path_at_execution": str(audit), "repo_relative_path": str(audit.relative_to(REPO)), "sha256": sha(audit)},
        "commands": [], "archive_checks": [], "comparisons": [], "audits": {},
        "portable_commands": [
            "{python} {package}/replay_and_verify.py --work-dir {new_tmp_dir} --report {new_report_json}",
            "{python} {relocated_create}/run_analysis_plot.py --run-dir {fresh_create_output}",
            "{python} {relocated_create}/verify_outputs.py --run-dir {fresh_create_output}",
            "{python} {relocated_reproduce}/plot_panel.py --out {fresh_reproduce_output}"
        ],
        "limits": [
            "The replay uses external Python dependencies and an installed Arial font; portability means relocated trial paths succeeded in this recorded environment.",
            "Only PNG and tabular artifact byte equality is required here; JSON numeric/analysis blocks are compared separately from historical absolute paths and metadata.",
            "The run scripts do not regenerate final captions, reviews, delivery manifests, or manually augmented final settings.",
            "The audit utility inspects its own fixture/expected resources internally; this packaging script reads neither directly.",
            "No baseline condition, no WorkBuddy effectiveness comparison, and no claim that all v0.4.1 features were exercised."
        ]
    }

    def run(label, argv, cwd):
        result = subprocess.run([str(item) for item in argv], cwd=cwd, env=env,
                                text=True, capture_output=True)
        log = evidence / "replay-logs" / f"{label}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout + ("\nSTDERR\n" + result.stderr if result.stderr else ""), encoding="utf-8")
        report["commands"].append({"label": label, "argv_at_execution": [str(item) for item in argv],
                                    "cwd_at_execution": str(cwd), "returncode": result.returncode,
                                    "log_relative_to_report_dir": str(log.relative_to(evidence))})
        if result.returncode:
            report["status"] = "failed"
            report["failure"] = {"label": label, "returncode": result.returncode, "log": str(log)}
            save(report_path, report)
            raise SystemExit(f"{label} failed; preserved log: {log}")

    def compare_bytes(name, accepted, replayed):
        left, right = sha(accepted), sha(replayed)
        report["comparisons"].append({"name": name, "kind": "exact_bytes", "pass": left == right,
            "accepted_package_relative_path": str(accepted.relative_to(PACKAGE)),
            "replay_relative_path": str(replayed.relative_to(work)),
            "accepted_sha256": left, "replay_sha256": right})

    def compare_json(name, accepted_path, replay_path, keys):
        left, right = load(accepted_path), load(replay_path)
        a, b = {key: left[key] for key in keys}, {key: right[key] for key in keys}
        report["comparisons"].append({"name": name, "kind": "json_values_exact", "pass": a == b,
            "accepted_package_relative_path": str(accepted_path.relative_to(PACKAGE)),
            "replay_relative_path": str(replay_path.relative_to(work)), "compared_keys": keys,
            "accepted_values": a, "replay_values": b})

    # Preserve the package. All execution and incidental caches belong to fresh
    # relocated copies, whose input/script/helper bytes are checked first.
    manifest = load(PACKAGE / "copy-manifest.json")
    for tree in manifest["trees"]:
        root = PACKAGE / tree["package_relative_root"]
        failures = [entry["path"] for entry in tree["entries"]
                    if sha(root / entry["path"]) != entry["sha256"]]
        report["archive_checks"].append({"tree": tree["name"], "files": tree["file_count"],
                                         "pass": not failures, "mismatches": failures})
    if not all(item["pass"] for item in report["archive_checks"]):
        report["status"] = "failed_archive_hashes"
        save(report_path, report)
        raise SystemExit("Archived trial bytes changed; inspect replay report")
    create = work / "relocated-create"
    reproduce = work / "relocated-reproduce"
    for source, target in [(PACKAGE / "create", create), (PACKAGE / "reproduce", reproduce)]:
        shutil.copytree(source, target, ignore=ignore_caches)
        assert tree_hashes(source) == tree_hashes(target), "Relocated copy changed preserved bytes"
    create_output = work / "create-replay-output"
    reproduce_output = work / "reproduce-replay-output"
    run("create-render", [python, create / "run_analysis_plot.py", "--run-dir", create_output], create)
    run("create-independent-arithmetic-export", [python, create / "verify_outputs.py", "--run-dir", create_output], create)
    run("reproduce-render", [python, reproduce / "plot_panel.py", "--out", reproduce_output], reproduce)
    accepted_create = PACKAGE / "create/output/final"
    for accepted_rel, replay_rel in [
        ("plotting_data.csv", "plotting_data.csv"),
        ("renderer-plotting-data.csv", "panel/plotting-data.csv"),
        ("statistics/analyzed-data.csv", "statistics/analyzed-data.csv"),
        ("statistics/summary.csv", "statistics/summary.csv"),
        ("panel.png", "panel/panel.png")
    ]:
        compare_bytes("create:" + accepted_rel, accepted_create / accepted_rel, create_output / replay_rel)
    compare_json("create:statistical-results", accepted_create / "statistics/results.json",
                 create_output / "statistics/results.json", ["schema_version", "status", "track", "plan", "comparisons"])
    compare_json("create:raw-to-mouse-accounting", accepted_create / "preparation.json", create_output / "preparation.json",
                 ["unit", "operation", "source_rows", "measured_reads", "failed_technical_reads", "final_rows", "group_counts", "missing_policy", "plotting_data_sha256", "unit_accounting"])
    compare_json("create:independent-verification", accepted_create / "verification.json", create_output / "verification.json",
                 ["status", "source_unit_checks", "independent_descriptions", "independent_rank_and_holm_calculations", "exports"])
    accepted_reproduce = PACKAGE / "reproduce/output"
    for name in ["plotting_data.csv", "feature-means.csv", "specimen-metadata.csv", "panel.png"]:
        compare_bytes("reproduce:" + name, accepted_reproduce / name, reproduce_output / name)
    compare_json("reproduce:source-to-cell-and-bar-audit", accepted_reproduce / "checks.json", reproduce_output / "checks.json",
                 ["numeric_and_export_status", "source_artist_audit", "column_strip_alignment", "row_mean_alignment", "text_canvas_clipping", "all_visible_text_Arial_8pt", "missing_glyphs", "exports", "layout_footprints_mm", "warnings"])
    report["create_independent_verifier_status"] = load(create_output / "verification.json")["status"]

    # The generic utility expects project/output. The accepted create trial uses
    # output/final. Stage exact accepted bytes in a new audit-only project;
    # no accepted directory or source record is renamed or rewritten.
    audit_create = work / "audit-only-create"
    audit_create.mkdir()
    shutil.copytree(PACKAGE / "create/input", audit_create / "input")
    shutil.copytree(accepted_create, audit_create / "output")
    shutil.copy2(PACKAGE / "create/run_analysis_plot.py", audit_create / "run_analysis_plot.py")
    mapping = {"purpose": "Temporary audit-only layout; no original trial changed",
        "staged_project_at_execution": str(audit_create),
        "mapping": [{"package_relative_source": "create/input", "staged_relative_target": "input"},
                    {"package_relative_source": "create/output/final", "staged_relative_target": "output"},
                    {"package_relative_source": "create/run_analysis_plot.py", "staged_relative_target": "run_analysis_plot.py"}],
        "accepted_output_sha256": tree_hashes(accepted_create),
        "staged_output_sha256": tree_hashes(audit_create / "output")}
    mapping["all_accepted_output_bytes_unchanged"] = mapping["accepted_output_sha256"] == mapping["staged_output_sha256"]
    save(evidence / "create-audit-mapping.json", mapping)
    for task, project, extras in [
        ("create", audit_create, ["--settings", "output/figure-settings.json", "--script", "run_analysis_plot.py"]),
        ("reproduce", reproduce, ["--settings", "output/figure-settings.json", "--script", "plot_panel.py", "--reading", "reference-reading.json"])
    ]:
        audit_report = evidence / f"{task}-numeric-export-audit.json"
        run(task + "-accepted-output-audit", [python, audit, "--project", project, "--task", task,
                                             "--report", audit_report, *extras], work)
        result = load(audit_report)
        report["audits"][task] = {"report_relative_to_report_dir": str(audit_report.relative_to(evidence)),
            "pass": result["pass"], "passed_checks": sum(item["pass"] for item in result["checks"]),
            "total_checks": len(result["checks"]), "failures": [item for item in result["checks"] if not item["pass"]]}
    report["create_audit_mapping"] = {"report_relative_to_report_dir": "create-audit-mapping.json",
                                      "all_accepted_output_bytes_unchanged": mapping["all_accepted_output_bytes_unchanged"]}
    report["comparison_count"] = len(report["comparisons"])
    report["passed_comparison_count"] = sum(item["pass"] for item in report["comparisons"])
    report["status"] = "passed" if (all(item["pass"] for item in report["comparisons"])
        and all(item["pass"] for item in report["audits"].values())
        and report["create_independent_verifier_status"] == "passed"
        and mapping["all_accepted_output_bytes_unchanged"]) else "failed"
    report["unresolved_failures"] = [item for item in report["comparisons"] if not item["pass"]]
    save(report_path, report)
    print(json.dumps({"status": report["status"], "report": str(report_path), "fresh_temporary_root": str(work),
        "comparisons_passed": report["passed_comparison_count"], "comparisons_total": report["comparison_count"],
        "audits": report["audits"]}, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
