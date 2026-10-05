"""Check ZIP structure and run the extracted core without comparing font pixels."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
import unicodedata
from urllib.parse import unquote, urlsplit


SKILLS = ("easyviz", "easyviz-reference-reader", "easyviz-figure-reviewer")
CREATE_DESIGN_CARDS = ("replicate-neutral-compact", "distribution-summary-lane", "violin-summary-hierarchy",
                       "heatmap-tall-narrow", "scatter-small-mark-color")
# Files consumed by the two Create case plotters and independent source/vector
# validators. Version gating leaves older portable archives installable.
CURATED_CREATE_RESOURCES = {
    "thermogenic-expression": ("plot.py", "validate.py", "spec.json", "caption.md",
        "inputs/observations.csv", "inputs/input-contract.json",
        "inputs/41467_2023_43021_MOESM8_ESM.xlsx"),
    "compartment-ccl2": ("plot.py", "validate.py", "caption.md",
        "panels/lung/spec.json", "panels/serum/spec.json", "inputs/observations.csv",
        "inputs/input-contract.json", "inputs/author-adjusted-p.csv", "inputs/blank-cells.csv",
        "inputs/descriptive-summary.csv", "inputs/41590_2023_1468_MOESM5_ESM.xlsx"),
}
V046_CASE_RESOURCES = {
    "pathway-signatures": ("plot.py", "validate.py", "spec.json", "caption.md",
        "source-record.json", "inputs/coefficients.csv", "inputs/input-contract.json",
        "inputs/41467_2017_2391_MOESM4_ESM.xlsx"),
    "vabistsevits-forest": ("inputs/source-data.csv", "revision-v0.4.6/plot.py",
        "revision-v0.4.6/adopted-spec.json", "revision-v0.4.6/caption.md"),
    "massier-integration-radar": ("inputs/source-data.csv", "revision-v0.4.6/plot.py",
        "revision-v0.4.6/adopted-spec.json", "revision-v0.4.6/caption.md"),
}
MAX_ZIP_ENTRIES = 10000
MAX_ZIP_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 256 * 1024 * 1024


def version_at_least(value: str, target: tuple[int, int, int]) -> bool:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    return bool(match and tuple(map(int, match.groups())) >= target)


def validate_resource_tree(plugin: Path) -> None:
    """Portable packages contain only owned regular files and directories."""
    if plugin.is_symlink() or not plugin.is_dir():
        raise ValueError("Plugin source must be a regular directory")
    for path in plugin.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"Symlink or special package resource: {path.relative_to(plugin)}")


def markdown_destinations(text: str) -> list[str]:
    """Read direct Markdown links/images, excluding literal code examples."""
    prose = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1]
                    and not marker[2].strip()):
                fence = None
            continue
        if marker:
            fence = (marker[1][0], len(marker[1]))
            continue
        prose.append(line)
    text = re.sub(r"(?s)<!--.*?-->", "", "".join(prose))
    text = re.sub(r"(`+)(?!`)(.*?)\1(?!`)", "", text, flags=re.S)
    label = r"(?:\\.|[^\]\\])*"
    destination = r"(?:<(?P<angle>[^<>\n]+)>|(?P<bare>(?:\\.|[^()\s\\]|\((?:\\.|[^()\\])*\))+))"
    title = r'''(?:\s+(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\([^()]*\)))?'''
    inline = re.compile(r"(?<!\\)\[" + label + r"\]\(\s*" + destination + title + r"\s*\)")
    targets = [match["angle"] or match["bare"] for match in inline.finditer(text)]
    # Backslash-escaped Markdown punctuation is part of the resource filename.
    return [re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]^_`{|}~\\])", r"\1", target)
            for target in targets]


def validate_markdown_resources(plugin: Path) -> int:
    """Resolve local Markdown resources inside the portable package only."""
    root = plugin.resolve()
    checked = 0
    for entry in sorted(plugin.rglob("*.md")):
        for target in markdown_destinations(entry.read_text()):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            destination = (entry.parent / unquote(url.path)).resolve()
            if not destination.is_relative_to(root) or not destination.exists():
                raise ValueError(f"Broken Markdown resource: {entry.relative_to(plugin)}: {target}")
            checked += 1
    return checked


def validate_plugin(plugin: Path) -> dict:
    validate_resource_tree(plugin)
    manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
    if (not isinstance(manifest, dict) or manifest.get("name") != "easyviz"
            or not isinstance(manifest.get("version"), str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])):
        raise ValueError("Expected an EasyViz manifest with a numeric major.minor.patch version")
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
    if version_at_least(manifest["version"], (0, 4, 3)):
        required.extend(["skills/easyviz/scripts/create_style.py",
                         "skills/easyviz/scripts/panel_readability.py",
                         "skills/easyviz/assets/cases/basic-panels/plot.py",
                         "skills/easyviz/assets/cases/basic-panels/validate.py",
                         "skills/easyviz/assets/cases/basic-panels/manifest.json",
                         "skills/easyviz/assets/cases/basic-panels/README.md"])
        for case in ("replicate-bars", "paired-scatter", "cohort-box", "cohort-violin", "depot-heatmap"):
            required.extend(f"skills/easyviz/assets/cases/basic-panels/{case}/{name}"
                            for name in ("source-data.csv", "candidate-spec.json", "caption.md", "provenance.json"))
    if version_at_least(manifest["version"], (0, 4, 4)):
        required.extend(["skills/easyviz/scripts/create_candidates.py", "skills/easyviz/scripts/create_review.py",
                         "skills/easyviz/references/first-draft.md", "skills/easyviz/references/design-cards.md",
                         "skills/easyviz/assets/design-cards/index.json"])
        for card in CREATE_DESIGN_CARDS:
            required.extend(f"skills/easyviz/assets/design-cards/{card}/{name}" for name in
                            ("card.json", "data.csv", "good-spec.json", "failure-spec.json", "caption.md",
                             "good/panel.png", "failure/panel.png", "good/preview-96dpi.png", "failure/preview-96dpi.png"))
    if version_at_least(manifest["version"], (0, 4, 5)):
        required.extend(("skills/easyviz/scripts/figure_handoff.py",
                         "skills/easyviz/scripts/observation_clipping.py"))
        for case, resources in CURATED_CREATE_RESOURCES.items():
            required.extend(f"skills/easyviz/assets/cases/{case}/{name}" for name in resources)
    if version_at_least(manifest["version"], (0, 4, 6)):
        required.append("skills/easyviz/references/reference-geometry.md")
        for case, resources in V046_CASE_RESOURCES.items():
            required.extend(f"skills/easyviz/assets/cases/{case}/{name}" for name in resources)
    for name in SKILLS:
        entry = plugin / "skills" / name / "SKILL.md"
        required.append(str(entry.relative_to(plugin)))
        if not entry.is_file():
            raise ValueError(f"Missing skill: {name}")
    grouped = plugin / "skills/easyviz/assets/cases/repair-outcomes"
    if grouped.exists():
        required.extend(f"skills/easyviz/assets/cases/repair-outcomes/{name}" for name in
                        ("plot.py", "compose.py", "validate.py", "spec.json", "source-data.csv", "caption.md", "provenance.json",
                         "panel-manifest.json", "transfer/spec.json", "transfer/source-data.csv", "transfer/panel-manifest.json"))
        for relative in ("panels/hdr", "panels/both", "panels/mutej", "transfer/panels/hdr", "transfer/panels/mutej"):
            required.extend(f"skills/easyviz/assets/cases/repair-outcomes/{relative}/{name}"
                            for name in ("spec.json", "source-data.csv", "caption.md"))
    for key in ("logo", "composerIcon"):
        target = manifest.get("interface", {}).get(key)
        if target:
            required.append(target)
    for name in required:
        path = (plugin / name).resolve()
        if not path.is_relative_to(plugin.resolve()) or not path.is_file():
            raise ValueError(f"Missing or external package resource: {name}")
    if version_at_least(manifest["version"], (0, 4, 4)):
        cards_root = plugin / "skills/easyviz/assets/design-cards"
        index = json.loads((cards_root / "index.json").read_text())
        cards = index.get("cards", [])
        if (index.get("schema_version") != 1 or index.get("track") != "create"
                or not isinstance(cards, list) or not all(isinstance(card, dict) for card in cards)):
            raise ValueError("Create design-card index is invalid")
        ids = [card.get("id") for card in cards]
        if not all(isinstance(identity, str) for identity in ids) or len(ids) != len(set(ids)) or not set(CREATE_DESIGN_CARDS) <= set(ids):
            raise ValueError("Create design-card index must retain the five bundled scenarios without duplicate IDs")
        for card in cards:
            rendered = {item["variant"]: item for item in card.get("rendered", [])}
            for variant, field in (("good", "good_image"), ("failure", "failure_image")):
                relative = card.get(field)
                if not isinstance(relative, str):
                    raise ValueError("Design card needs full good/failure PNG paths")
                image = (cards_root / relative).resolve()
                if not image.is_relative_to(cards_root.resolve()) or image.name != "panel.png" or not image.is_file():
                    raise ValueError("Design-card image must be a bundled full panel.png")
                raw = image.read_bytes()
                if not raw.startswith(b"\x89PNG\r\n\x1a\n") or len(raw) < 33:
                    raise ValueError("Design-card panel is not a PNG")
                if hashlib.sha256(raw).hexdigest() != rendered.get(variant, {}).get("png_sha256"):
                    raise ValueError("Design-card image hash differs from its recorded index")
    validate_markdown_resources(plugin)
    return manifest


def extract_package(archive: Path, destination: Path) -> int:
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise ValueError("ZIP entry count exceeds the package budget")
        paths = {}
        total_bytes = 0
        for info in entries:
            path = PurePosixPath(info.filename)
            mode = stat.S_IFMT(info.external_attr >> 16)
            if (not path.parts or path.parts[0] != "easyviz" or path.is_absolute()
                    or ".." in path.parts or "\\" in info.filename
                    or mode not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or (len(path.parts) == 1 and not info.is_dir())):
                raise ValueError(f"Unsafe or unexpected ZIP entry: {info.filename}")
            if any(p in (".venv", "__pycache__", ".git") for p in path.parts):
                raise ValueError(f"Development files in ZIP: {info.filename}")
            canonical = path.as_posix()
            key = unicodedata.normalize("NFC", canonical).casefold()
            if key in paths:
                raise ValueError(f"Duplicate normalized ZIP entry: {canonical}")
            paths[key] = (canonical, info.is_dir())
            if info.file_size > MAX_ZIP_MEMBER_BYTES:
                raise ValueError(f"ZIP member exceeds the package budget: {canonical}")
            total_bytes += info.file_size
            if total_bytes > MAX_ZIP_TOTAL_BYTES:
                raise ValueError("ZIP expanded size exceeds the package budget")
        for name, is_directory in paths.values():
            path = PurePosixPath(name)
            if any(paths.get(unicodedata.normalize("NFC", parent.as_posix()).casefold(), (None, True))[1] is False
                   for parent in path.parents):
                raise ValueError(f"Conflicting file/directory ZIP paths: {name}")
            # Existing extraction paths must not redirect a safe archive outside
            # its selected destination. Preflight every entry before any writes.
            parents = (destination, *(destination / str(parent) for parent in reversed(path.parents)))
            for candidate in (*parents, destination / name):
                if candidate.is_symlink():
                    raise ValueError(f"Symlink extraction path: {candidate}")
            if any(candidate.exists() and not candidate.is_dir() for candidate in parents):
                raise ValueError(f"Conflicting existing extraction parent: {name}")
            target = destination / name
            if target.exists() and target.is_dir() != is_directory:
                raise ValueError(f"Conflicting existing extraction path: {name}")
        package.extractall(destination)
    return len(entries)


def check_curated_create_cases(skill: Path, isolated: Path, env: dict) -> dict:
    """Redraw shipped cases and verify actual source precision/vector/font/map bindings."""
    # Redraw from this extracted package in a fresh unrelated folder;
    # packaged canonical metadata may retain labeled historical paths.
    results = {}
    for name in CURATED_CREATE_RESOURCES:
        case = skill / "assets/cases" / name
        output = isolated / f"{name}-fresh-output"
        commands = [[sys.executable, "-I", "-B", str(case / "plot.py"),
                     "--font", "DejaVu Sans", "--out", str(output)]]
        validation = isolated / f"{name}-validation.json"
        if name == "thermogenic-expression":
            commands.append([sys.executable, "-I", "-B", str(case / "validate.py"),
                             "--output", str(output), "--out", str(validation)])
            figures = [output]
        else:
            commands.append([sys.executable, "-I", "-B", str(case / "validate.py"),
                             "--outputs", str(output), "--font", "DejaVu Sans",
                             "--out", str(validation)])
            figures = [output / "panels" / panel / "output" for panel in ("lung", "serum")]
        for command in commands:
            checked = subprocess.run(command, cwd=isolated, env=env,
                                     capture_output=True, text=True)
            if checked.returncode:
                raise RuntimeError(f"Extracted {name} source/vector/font redraw failed: " + checked.stdout + checked.stderr)
        if json.loads(validation.read_text()).get("status") != "pass":
            raise ValueError(f"Extracted {name} must pass independent source/vector checks")
        bindings = []
        for figure in figures:
            settings = json.loads((figure / "settings.json").read_text())
            qa = json.loads((figure / "qa.json").read_text())
            if (qa.get("status") != "pass" or not qa.get("valid_outputs")
                    or settings.get("layout", {}).get("actual_font") != "DejaVu Sans"
                    or settings.get("layout", {}).get("font_substituted")):
                raise ValueError(f"Extracted {name} font/export QA is incomplete")
            binding_check = (
                "import json,sys; from pathlib import Path; "
                "sys.path.insert(0,sys.argv[1]); from figure_workbench import FigureWorkbench; "
                "s=FigureWorkbench(Path(sys.argv[2])).state(); "
                "assert s['manifest_valid'] and s['provenance_valid'] and s['source_current'] is True,s; "
                "assert s['elements'],s; "
                "assert all(v.get('current') is True for v in s['source_versions'].values()),s; "
                "print(json.dumps({'source_current':s['source_current'],'elements':len(s['elements']),'declared_inputs':len(s['source_versions'])}))")
            checked = subprocess.run([sys.executable, "-I", "-B", "-c", binding_check,
                                      str(skill / "scripts"), str(figure)],
                                     cwd=isolated, env=env, capture_output=True, text=True)
            if checked.returncode:
                raise RuntimeError(f"Extracted {name} workbench source bindings failed: " + checked.stdout + checked.stderr)
            bindings.append(json.loads(checked.stdout))
        results[name] = {"status": "pass", "font": "DejaVu Sans", "figures": bindings,
                         "source_vector_validation": json.loads(validation.read_text())}
    return results


def check_v046_cases(skill: Path, isolated: Path, env: dict, root: Path) -> None:
    """Draw real new cases from copied/extracted files, then independently read exports."""
    pathway = isolated / "copied-pathway-signatures"
    shutil.copytree(skill / "assets/cases/pathway-signatures", pathway)
    pathway_out = isolated / "pathway-fresh-output"
    commands = [
        [sys.executable, "-I", "-B", str(pathway / "plot.py"), "--tools", str(skill / "scripts"),
         "--font", "DejaVu Sans", "--out", str(pathway_out)],
        [sys.executable, "-I", "-B", str(pathway / "validate.py"), "--out", str(pathway_out)],
    ]
    copied = {}
    for name in ("vabistsevits-forest", "massier-integration-radar"):
        copied[name] = isolated / ("copied-" + name)
        shutil.copytree(skill / "assets/cases" / name, copied[name])
        revision = copied[name] / "revision-v0.4.6"
        # Only the disposable copy is replaced. Frozen packaged previews stay intact.
        shutil.rmtree(revision / "output")
        commands.append([sys.executable, "-I", "-B", str(revision / "plot.py"),
                         "--runtime", str(skill / "scripts"), "--font", "DejaVu Sans",
                         "--out", str(revision / "output")])
    commands.append([sys.executable, "-I", "-B", str(root / "evals/development-v0.4.6/reproduce-design/verify_revisions.py"),
                     "--forest-case", str(copied["vabistsevits-forest"]),
                     "--radar-case", str(copied["massier-integration-radar"]),
                     "--expected-font", "DejaVu Sans", "--out", str(isolated / "reproduce-geometry-verification.json")])
    for command in commands:
        checked = subprocess.run(command, cwd=isolated, env=env, capture_output=True, text=True)
        if checked.returncode:
            raise RuntimeError("Extracted 0.4.6 actual source/vector/font validation failed: " + checked.stdout + checked.stderr)
    for figure in (pathway_out, *(case / "revision-v0.4.6/output" for case in copied.values())):
        probe = ("import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
                 "from figure_workbench import FigureWorkbench; s=FigureWorkbench(Path(sys.argv[2])).state(); "
                 "assert s['manifest_valid'] and s['provenance_valid'] and s['source_current'] is True,s; "
                 "assert s['elements'] and all(v.get('current') is True for v in s['source_versions'].values()),s")
        checked = subprocess.run([sys.executable, "-I", "-B", "-c", probe, str(skill / "scripts"), str(figure)],
                                 cwd=isolated, env=env, capture_output=True, text=True)
        if checked.returncode:
            raise RuntimeError("Extracted 0.4.6 actual source/map receipt is not current: " + checked.stdout + checked.stderr)


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
            expected_workflows = {"inspect_data", "analyze", "reference_packet", "audit_reproduction", "figure_workbench", "preview_choices", "apply_figure_requests"}
            new_create_workflow = version_at_least(manifest["version"], (0, 4, 4))
            if new_create_workflow:
                expected_workflows.update(("create_candidates", "create_review"))
            if set(workflows) != expected_workflows:
                raise ValueError("Extracted workflow discovery is incomplete")
            for route in workflows.values():
                if not all(Path(route[key]).is_relative_to(skill) and Path(route[key]).is_file()
                           for key in ("script", "doc")):
                    raise ValueError("Extracted workflow points outside the selected skill")
                described = subprocess.run([sys.executable, route["script"], "--help"],
                                           cwd=isolated, env=env, capture_output=True, text=True)
                if described.returncode:
                    raise RuntimeError(described.stdout + described.stderr)
            if new_create_workflow:
                for name in ("create_candidates", "create_review"):
                    described = subprocess.run([sys.executable, workflows[name]["script"], "--describe-spec"],
                                               cwd=isolated, env=env, capture_output=True, text=True)
                    if described.returncode or json.loads(described.stdout).get("track") != "create":
                        raise ValueError(f"Extracted {name} has no valid Create specification")
                candidate_spec = {"chart": spec["chart"], "fields": spec["fields"], "labels": spec.get("labels", {}),
                                  "options": spec.get("options", {}), "colormap": spec["colormap"], "seed": spec.get("seed", 0),
                                  "layout": {"font": "DejaVu Sans", "font_size_pt": 8, "line_width_pt": .6, "dpi": 120},
                                  "formats": ["pdf", "svg", "png"]}
                candidate_spec_path = isolated / "new-create-spec.json"
                candidate_spec_path.write_text(json.dumps(candidate_spec))
                candidate_output = isolated / "create-candidates"
                run = subprocess.run([sys.executable, workflows["create_candidates"]["script"],
                                      "--data", str(fixture / "data.csv"), "--spec", str(candidate_spec_path),
                                      "--out", str(candidate_output), "--new-draft", "--count", "1"],
                                     cwd=isolated, env=env, capture_output=True, text=True)
                if run.returncode:
                    raise RuntimeError("Extracted Create candidates failed: " + run.stdout + run.stderr)
                candidate_manifest = json.loads((candidate_output / "manifest.json").read_text())
                if candidate_manifest.get("status") != "visual_review_pending" or candidate_manifest.get("aesthetic_winner") is not None:
                    raise ValueError("Extracted Create candidates must await actual image review")
                candidate = candidate_output / candidate_manifest["candidates"][0]["id"]
                if not (candidate / "panel.png").is_file() or json.loads((candidate / "qa.json").read_text()).get("status") != "pass":
                    raise ValueError("Extracted Create candidate must have actual technically checked exports")
                caption = isolated / "create-caption.md"
                caption.write_text("Matrix cells show supplied scores for the source features and samples.\n")
                review_output = isolated / "create-review"
                staged = subprocess.run([sys.executable, workflows["create_review"]["script"], "stage",
                                         "--figure-dir", str(candidate), "--reading-task", "Read supplied scores across features and samples.",
                                         "--caption", str(caption), "--out", str(review_output)],
                                        cwd=isolated, env=env, capture_output=True, text=True)
                if staged.returncode or json.loads(staged.stdout).get("gate_status") != "pending":
                    raise ValueError("Extracted Create review must stage a pending record")
                checked = subprocess.run([sys.executable, workflows["create_review"]["script"], "check",
                                          "--packet", str(review_output / "packet.json")],
                                         cwd=isolated, env=env, capture_output=True, text=True)
                report = json.loads(checked.stdout)
                if checked.returncode != 1 or report.get("gate_status") != "blocked" or report.get("readiness") != "not_reviewed":
                    raise ValueError("Extracted Create review cannot pass without actual image-opening attestations")
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
            if version_at_least(manifest["version"], (0, 4, 5)):
                check_curated_create_cases(skill, isolated, env)
            if version_at_least(manifest["version"], (0, 4, 6)):
                check_v046_cases(skill, isolated, env, root)
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
            grouped = skill / "assets/cases/repair-outcomes"
            if grouped.is_dir():
                output = isolated / "grouped-output"
                for command in ([sys.executable, str(grouped / "plot.py"), "--tools", str(skill / "scripts"),
                                 "--font", "DejaVu Sans", "--transfer", "--out", str(output)],
                                [sys.executable, str(grouped / "validate.py"), "--tools", str(skill / "scripts"),
                                 "--font", "DejaVu Sans", "--outputs", str(output),
                                 "--out", str(isolated / "grouped-validation.json")]):
                    checked = subprocess.run(command, cwd=isolated, env=env, capture_output=True, text=True)
                    if checked.returncode:
                        raise RuntimeError("Extracted grouped comparison failed: " + checked.stdout + checked.stderr)
    print(json.dumps({"status": "pass", "version": manifest["version"], "archive": archive.name,
                      "sha256": digest, "files": file_count,
                      "checks": "structure" if args.structure_only else "structure, extracted recipe/workflow discovery, core, draft/measured layout, compound matrix, actual previews, seven Source Data wrappers, basic panels and individual repair-outcome panels/grouped alternative when present; scene proposals and honestly pending Create review for 0.4.4+; fresh thermogenic-expression/compartment-ccl2 source/vector/font/mapped-source checks for 0.4.5+; actual copied pathway/forest/radar source/vector/font and current artist/receipt checks for 0.4.6+"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as error:
        print(f"Package check failed: {error}", file=sys.stderr)
        raise SystemExit(1)
