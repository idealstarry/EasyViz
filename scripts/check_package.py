"""Check ZIP structure and run the extracted core without comparing font pixels."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


SKILLS = ("easyviz", "easyviz-reference-reader", "easyviz-figure-reviewer")


def validate_plugin(plugin: Path) -> dict:
    manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
    if manifest.get("name") != "easyviz" or not isinstance(manifest.get("version"), str):
        raise ValueError("Expected an EasyViz manifest with a version")
    required = ["README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
                "skills/easyviz/scripts/render.py", "skills/easyviz/scripts/figure_profile.py",
                "skills/easyviz/scripts/legend_layout.py", "skills/easyviz/scripts/requirements.txt",
                "skills/easyviz/scripts/auto_layout.py", "skills/easyviz/scripts/annotation_review.py",
                "skills/easyviz/scripts/draft_spec.py",
                "skills/easyviz/scripts/interval_plot.py",
                "skills/easyviz/scripts/paired_plot.py",
                "skills/easyviz/scripts/replicate_plot.py",
                "skills/easyviz/scripts/ecdf_plot.py",
                "skills/easyviz/scripts/timecourse_plot.py",
                "skills/easyviz/scripts/annotated_matrix.py",
                "skills/easyviz/scripts/aligned_layers.py",
                "skills/easyviz/scripts/preview_choices.py",
                "skills/easyviz/scripts/apply_figure_requests.py",
                "skills/easyviz/scripts/inspect_data.py",
                "skills/easyviz/scripts/analyze.py",
                "skills/easyviz/scripts/reference_packet.py",
                "skills/easyviz/scripts/audit_reproduction.py",
                "skills/easyviz/scripts/figure_elements.py",
                "skills/easyviz/scripts/figure_workbench.py",
                "skills/easyviz/scripts/workbench/index.html",
                "skills/easyviz/scripts/workbench/workbench.js",
                "skills/easyviz/scripts/workbench/workbench.css",
                "skills/easyviz/assets/cases/shi-timecourse/plot.py",
                "skills/easyviz/assets/cases/shi-timecourse/source-data.csv",
                "skills/easyviz/assets/cases/shi-timecourse/spec.json",
                "skills/easyviz/assets/cases/yayon-cma/plot.py",
                "skills/easyviz/assets/cases/yayon-cma/inputs/source-data.csv",
                "skills/easyviz/assets/cases/yayon-cma/inputs/summary.csv",
                "skills/easyviz/assets/cases/yayon-cma/spec.json",
                "skills/easyviz/assets/cases/xiang-bubble-volcano/plot.py",
                "skills/easyviz/assets/cases/xiang-bubble-volcano/source-data.csv",
                "skills/easyviz/assets/cases/xiang-bubble-volcano/spec.json",
                "skills/easyviz/assets/cases/vabistsevits-forest/plot.py",
                "skills/easyviz/assets/cases/vabistsevits-forest/inputs/source-data-a.csv",
                "skills/easyviz/assets/cases/vabistsevits-forest/panel-a-spec.json",
                "skills/easyviz/assets/cases/urschel-paired/plot.py",
                "skills/easyviz/assets/cases/urschel-paired/source-data.csv",
                "skills/easyviz/assets/cases/urschel-paired/spec.json",
                "skills/easyviz/assets/cases/truong-components/plot.py",
                "skills/easyviz/assets/cases/truong-components/inputs/components.csv",
                "skills/easyviz/assets/cases/truong-components/components-spec.json",
                "skills/easyviz/assets/cases/urschel-ecdf/plot.py",
                "skills/easyviz/assets/cases/urschel-ecdf/source-data.csv",
                "skills/easyviz/assets/cases/urschel-ecdf/spec.json",
                "skills/easyviz/assets/palettes/palettes.json",
                "skills/easyviz/assets/fixtures/heatmap/data.csv",
                "skills/easyviz/assets/fixtures/heatmap/spec.json"]
    version = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", manifest["version"])
    if version and tuple(map(int, version.groups())) >= (0, 4, 3):
        required.extend(["skills/easyviz/scripts/create_style.py",
                         "skills/easyviz/scripts/panel_readability.py",
                         "skills/easyviz/assets/cases/basic-panels/plot.py",
                         "skills/easyviz/assets/cases/basic-panels/validate.py",
                         "skills/easyviz/assets/cases/basic-panels/manifest.json",
                         "skills/easyviz/assets/cases/basic-panels/README.md"])
        for case in ("replicate-bars", "paired-scatter", "cohort-box", "cohort-violin", "depot-heatmap"):
            required.extend(f"skills/easyviz/assets/cases/basic-panels/{case}/{name}"
                            for name in ("source-data.csv", "candidate-spec.json", "caption.md", "provenance.json"))
    for name in SKILLS:
        entry = plugin / "skills" / name / "SKILL.md"
        required.append(str(entry.relative_to(plugin)))
        if not entry.is_file():
            raise ValueError(f"Missing skill: {name}")
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", entry.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            destination = (entry.parent / target.split("#", 1)[0]).resolve()
            if not destination.is_relative_to(plugin.resolve()) or not destination.exists():
                raise ValueError(f"Broken skill resource: {name}: {target}")
    for key in ("logo", "composerIcon"):
        target = manifest.get("interface", {}).get(key)
        if target:
            required.append(target)
    for name in required:
        path = (plugin / name).resolve()
        if not path.is_relative_to(plugin.resolve()) or not path.is_file():
            raise ValueError(f"Missing or external package resource: {name}")
    return manifest


def extract_package(archive: Path, destination: Path) -> int:
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entries")
        for info in package.infolist():
            path = PurePosixPath(info.filename)
            if (not path.parts or path.parts[0] != "easyviz" or path.is_absolute()
                    or ".." in path.parts or "\\" in info.filename
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError(f"Unsafe or unexpected ZIP entry: {info.filename}")
            if any(p in (".venv", "__pycache__", ".git") for p in path.parts):
                raise ValueError(f"Development files in ZIP: {info.filename}")
        package.extractall(destination)
    return len(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Defaults to the archive in dist/build.json")
    parser.add_argument("--structure-only", action="store_true", help="No scientific dependencies needed")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    build = json.loads((root / "dist/build.json").read_text()) if args.archive is None else None
    archive = args.archive or root / "dist" / build["archive"]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if build and digest != build["sha256"]:
        raise ValueError("ZIP checksum differs from dist/build.json")
    with tempfile.TemporaryDirectory(prefix="easyviz-package-smoke-") as temporary:
        isolated = Path(temporary)
        file_count = extract_package(archive, isolated)
        plugin = isolated / "easyviz"
        manifest = validate_plugin(plugin)
        if build and (manifest["version"] != build["version"] or file_count != build["files"]):
            raise ValueError("ZIP version or file count differs from dist/build.json")
        if not args.structure_only:
            skill = (plugin / "skills/easyviz").resolve()
            fixture = skill / "assets/fixtures/heatmap"
            spec = json.loads((fixture / "spec.json").read_text())
            spec["layout"]["font"] = "DejaVu Sans"
            spec_path = isolated / "smoke-spec.json"
            spec_path.write_text(json.dumps(spec))
            env = os.environ.copy()
            env.update(MPLCONFIGDIR=str(isolated / "matplotlib"), MPLBACKEND="Agg")
            discovery = subprocess.run([sys.executable, str(skill / "scripts/render.py"),
                                        "--describe-spec"], cwd=isolated, env=env,
                                       capture_output=True, text=True)
            if discovery.returncode:
                raise RuntimeError(discovery.stdout + discovery.stderr)
            routes = json.loads(discovery.stdout).get("focused_recipes", {})
            if set(routes) != {"interval", "paired", "replicate", "ecdf", "timecourse", "annotated_matrix"}:
                raise ValueError("Extracted chart discovery does not identify every focused recipe")
            for route in routes.values():
                script, documentation = Path(route["script"]), Path(route["doc"])
                if not all(path.is_relative_to(skill) and path.is_file()
                           for path in (script, documentation)):
                    raise ValueError("Extracted recipe discovery points outside the selected skill")
                described = subprocess.run([sys.executable, str(script), "--describe-spec"],
                                           cwd=isolated, env=env, capture_output=True, text=True)
                if described.returncode:
                    raise RuntimeError(described.stdout + described.stderr)
                if not isinstance(json.loads(described.stdout), dict):
                    raise ValueError("Focused recipe specification must be a JSON object")
            workflows = json.loads(discovery.stdout).get("workflow_tools", {})
            if set(workflows) != {"inspect_data", "analyze", "reference_packet", "audit_reproduction", "figure_workbench", "preview_choices", "apply_figure_requests"}:
                raise ValueError("Extracted workflow discovery is incomplete")
            for route in workflows.values():
                if not all(Path(route[key]).is_relative_to(skill) and Path(route[key]).is_file()
                           for key in ("script", "doc")):
                    raise ValueError("Extracted workflow points outside the selected skill")
                described = subprocess.run([sys.executable, route["script"], "--help"],
                                           cwd=isolated, env=env, capture_output=True, text=True)
                if described.returncode:
                    raise RuntimeError(described.stdout + described.stderr)
            result = subprocess.run([sys.executable, str(skill / "scripts/render.py"),
                                     "--data", str(fixture / "data.csv"), "--spec", str(spec_path),
                                     "--out", str(isolated / "output")],
                                    cwd=isolated, env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            qa = json.loads((isolated / "output/qa.json").read_text())
            if qa.get("status") != "pass" or not qa.get("valid_outputs"):
                raise ValueError("Extracted core smoke failed canvas/export QA")
            teaching = skill / "assets/fixtures/statistical-analysis"
            for name, arguments, expected in (
                ("inspect_data", ["--input", str(teaching), "--out", str(isolated / "intake")], "analysis-options.json"),
                ("analyze", ["--data", str(teaching / "independent.csv"), "--plan", str(teaching / "independent-plan.json"),
                             "--out", str(isolated / "analysis")], "results.json"),
                ("reference_packet", ["--reference", str(isolated / "output/panel.png"), "--data", str(fixture / "data.csv"),
                                      "--out", str(isolated / "reference-packet")], "implementation-plan.json"),
            ):
                result = subprocess.run([sys.executable, workflows[name]["script"], *arguments],
                                        cwd=isolated, env=env, capture_output=True, text=True)
                if result.returncode:
                    raise RuntimeError(result.stdout + result.stderr)
                output = Path(arguments[arguments.index("--out") + 1])
                if not (output / expected).is_file():
                    raise ValueError(f"Extracted {name} did not produce its documented output")
            packet_plan = json.loads((isolated / "reference-packet/implementation-plan.json").read_text())
            if packet_plan.get("execution_ready") is not False:
                raise ValueError("A packet without image reading must remain unresolved")
            matrix = skill / "assets/fixtures/annotated-matrix"
            run = subprocess.run([sys.executable, routes["annotated_matrix"]["script"],
                                  "--data", str(matrix / "input.csv"), "--spec", str(matrix / "spec.json"),
                                  "--row-metadata", str(matrix / "row.csv"), "--column-metadata", str(matrix / "column.csv"),
                                  "--row-linkage", str(matrix / "row.json"), "--column-linkage", str(matrix / "column.json"),
                                  "--out", str(isolated / "matrix-output"), "--track", "reproduce"],
                                 cwd=isolated, env=env, capture_output=True, text=True)
            if run.returncode or json.loads((isolated / "matrix-output/qa.json").read_text()).get("status") != "pass":
                raise RuntimeError("Extracted compound matrix failed: " + run.stdout + run.stderr)
            previews = skill / "assets/fixtures/preview-choices"
            run = subprocess.run([sys.executable, workflows["preview_choices"]["script"],
                                  "--data", str(previews / "source.csv"), "--request", str(previews / "request.json"),
                                  "--out", str(isolated / "preview-output")],
                                 cwd=isolated, env=env, capture_output=True, text=True)
            if run.returncode or not (isolated / "preview-output/manifest.json").is_file():
                raise RuntimeError("Extracted actual previews failed: " + run.stdout + run.stderr)
            audit_output = isolated / "reference-audit.json"
            recorded_audit = subprocess.run(
                [sys.executable, workflows["audit_reproduction"]["script"],
                 "--packet", str(isolated / "reference-packet"), "--out", str(audit_output)],
                cwd=isolated, env=env, capture_output=True, text=True)
            if recorded_audit.returncode != 1 or not audit_output.is_file():
                raise ValueError("An unresolved packet must produce an incomplete extracted audit")
            audit_report = json.loads(audit_output.read_text())
            if (audit_report.get("status") != "incomplete" or not audit_report.get("missing_evidence")
                    or audit_report.get("semantic_correctness_verified") is not False
                    or audit_report.get("visual_review_passed") is not False):
                raise ValueError("Extracted audit must not certify an unresolved reference packet")
            draft_path = isolated / "draft-spec.json"
            draft_command = [sys.executable, str(skill / "scripts/draft_spec.py"),
                             "--data", str(fixture / "data.csv"), "--chart", spec["chart"],
                             "--font", "DejaVu Sans", "--out", str(draft_path)]
            for role, column in spec["fields"].items():
                draft_command.extend(["--field", f"{role}={column}"])
            draft_result = subprocess.run(draft_command, cwd=isolated, env=env,
                                          capture_output=True, text=True)
            if draft_result.returncode:
                raise RuntimeError(draft_result.stdout + draft_result.stderr)
            auto_result = subprocess.run([sys.executable, str(skill / "scripts/render.py"),
                                          "--data", str(fixture / "data.csv"), "--spec", str(draft_path),
                                          "--out", str(isolated / "measured-output")],
                                         cwd=isolated, env=env, capture_output=True, text=True)
            if auto_result.returncode:
                raise RuntimeError(auto_result.stdout + auto_result.stderr)
            auto_qa = json.loads((isolated / "measured-output/qa.json").read_text())
            if auto_qa.get("status") != "pass" or auto_qa.get("auto_layout", {}).get("status") != "pass":
                raise ValueError("Extracted draft and measured layout failed QA")
            for name, data_name, spec_name, expected_rows in (
                ("xiang-bubble-volcano", "source-data.csv", "spec.json", 1457),
                ("vabistsevits-forest", "inputs/source-data-a.csv", "panel-a-spec.json", 24),
                ("urschel-paired", "source-data.csv", "spec.json", 254),
                ("truong-components", "inputs/components.csv", "components-spec.json", 63),
                ("urschel-ecdf", "source-data.csv", "spec.json", 254),
                ("shi-timecourse", "source-data.csv", "spec.json", 120),
            ):
                case = skill / "assets/cases" / name
                case_spec = json.loads((case / spec_name).read_text())
                case_spec["layout"]["font"] = "DejaVu Sans"
                case_spec["formats"] = ["pdf", "svg", "png"]
                case_spec_path = isolated / f"{name}-spec.json"
                case_spec_path.write_text(json.dumps(case_spec))
                case_out = isolated / f"{name}-output"
                run = subprocess.run([sys.executable, str(case / "plot.py"),
                                      "--data", str(case / data_name), "--spec", str(case_spec_path),
                                      "--out", str(case_out)], cwd=isolated, env=env,
                                     capture_output=True, text=True)
                if run.returncode:
                    raise RuntimeError(run.stdout + run.stderr)
                case_qa = json.loads((case_out / "qa.json").read_text())
                if case_qa.get("status") != "pass" or case_qa.get("input_rows") != expected_rows:
                    raise ValueError(f"Extracted {name} case failed source/canvas QA")
            case = skill / "assets/cases/yayon-cma"
            run = subprocess.run([sys.executable, str(case / "plot.py"), "--runtime", str(skill / "scripts"),
                                  "--out", str(isolated / "yayon-output"),
                                  "--spec", str(case / "font-transfer/spec.json")], cwd=isolated, env=env, capture_output=True, text=True)
            if run.returncode:
                raise RuntimeError("Extracted Yayon aligned case failed: " + run.stdout + run.stderr)
            if json.loads((isolated / "yayon-output/qa.json").read_text()).get("status") != "pass":
                raise ValueError("Extracted Yayon case has incomplete source/export QA")
            basic = skill / "assets/cases/basic-panels"
            if basic.is_dir():
                output = isolated / "basic-output"
                for command in ([sys.executable, str(basic / "plot.py"), "--tools", str(skill / "scripts"),
                                 "--font", "DejaVu Sans", "--out", str(output)],
                                [sys.executable, str(basic / "validate.py"), "--tools", str(skill / "scripts"),
                                 "--candidate-only", "--font", "DejaVu Sans", "--outputs", str(output),
                                 "--out", str(isolated / "basic-validation.json")]):
                    checked = subprocess.run(command, cwd=isolated, env=env, capture_output=True, text=True)
                    if checked.returncode:
                        raise RuntimeError("Extracted basic panels failed: " + checked.stdout + checked.stderr)
    print(json.dumps({"status": "pass", "version": manifest["version"], "archive": archive.name,
                      "sha256": digest, "files": file_count,
                      "checks": "structure" if args.structure_only else "structure, extracted recipe/workflow discovery, core, draft/measured layout, compound matrix, actual previews, seven Source Data wrappers and basic panels when present"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as error:
        print(f"Package check failed: {error}", file=sys.stderr)
        raise SystemExit(1)
