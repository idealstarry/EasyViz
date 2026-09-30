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
                "skills/easyviz/assets/palettes/palettes.json",
                "skills/easyviz/assets/fixtures/heatmap/data.csv",
                "skills/easyviz/assets/fixtures/heatmap/spec.json"]
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
            skill = plugin / "skills/easyviz"
            fixture = skill / "assets/fixtures/heatmap"
            spec = json.loads((fixture / "spec.json").read_text())
            spec["layout"]["font"] = "DejaVu Sans"
            spec_path = isolated / "smoke-spec.json"
            spec_path.write_text(json.dumps(spec))
            env = os.environ.copy()
            env.update(MPLCONFIGDIR=str(isolated / "matplotlib"), MPLBACKEND="Agg")
            result = subprocess.run([sys.executable, str(skill / "scripts/render.py"),
                                     "--data", str(fixture / "data.csv"), "--spec", str(spec_path),
                                     "--out", str(isolated / "output")],
                                    cwd=isolated, env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            qa = json.loads((isolated / "output/qa.json").read_text())
            if qa.get("status") != "pass" or not qa.get("valid_outputs"):
                raise ValueError("Extracted core smoke failed canvas/export QA")
    print(json.dumps({"status": "pass", "version": manifest["version"], "archive": archive.name,
                      "sha256": digest, "files": file_count,
                      "checks": "structure" if args.structure_only else "structure and extracted core smoke"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as error:
        print(f"Package check failed: {error}", file=sys.stderr)
        raise SystemExit(1)
