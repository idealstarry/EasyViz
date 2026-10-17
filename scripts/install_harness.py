"""Install EasyViz skills into DeepSeek Harness's documented filesystem roots.

This installer only manages the three EasyViz skill bundles. It neither starts
the harness nor changes its models, credentials, profile, or MCP configuration.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from check_package import validate_plugin, validate_resource_tree
from install_plugin import (InstallError, content_hashes, installation_lock,
                            owned_path, remove_owned, verify_cached_content)


SKILL_NAMES = ("easyviz", "easyviz-reference-reader", "easyviz-figure-reviewer")
OWNER_FILE = ".easyviz-harness.json"
OWNER = "easyviz-deepseek-harness"


def target_directory(*, project: Path | None = None,
                     dsh_home: Path | None = None) -> Path:
    """Resolve the official project or user skill root without following links."""
    if project is not None and dsh_home is not None:
        raise InstallError("Choose --project or --dsh-home, not both")
    if project is not None:
        selected = project.expanduser().absolute()
        target = selected / ".dsh" / "skills"
    else:
        selected = (dsh_home if dsh_home is not None else
                    Path(os.environ.get("DSH_HOME") or Path.home() / ".dsh"))
        target = selected.expanduser().absolute() / "skills"
    # Resolve system directory aliases first, while refusing links at or below
    # the explicitly selected directory (including a symlink selected itself).
    owned_path(target, selected.expanduser().absolute())
    return target.resolve()


def _preflight_target(target: Path) -> None:
    """An existing bundle must carry this installer's matching ownership mark."""
    owned_path(target, target.parent)
    if not target.exists():
        return
    if not target.is_dir():
        raise InstallError(f"Skill path is not a directory; left untouched: {target}")
    validate_resource_tree(target)
    marker = target / OWNER_FILE
    try:
        owner = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise InstallError(f"Existing skill is not managed by EasyViz; left untouched: {target}") from error
    if (not isinstance(owner, dict) or owner.get("managed_by") != OWNER
            or owner.get("skill") != target.name or owner.get("schema") != 1):
        raise InstallError(f"Existing skill is not managed by EasyViz; left untouched: {target}")


def install(source: Path, *, project: Path | None = None,
            dsh_home: Path | None = None) -> dict:
    """Stage and verify complete bundles, then replace only owned skill paths."""
    manifest = validate_plugin(source)
    source = source.resolve()
    target = target_directory(project=project, dsh_home=dsh_home)
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise InstallError("Harness skills directory must not overlap the selected source package")
    if target.exists() and not target.is_dir():
        raise InstallError(f"Harness skills path is not a directory; left untouched: {target}")
    # Check conflicts before creating a lock or staging anything in user files.
    for name in SKILL_NAMES:
        _preflight_target(target / name)
    with installation_lock(target, relative=".easyviz-install.lock"):
        for name in SKILL_NAMES:
            _preflight_target(target / name)
        staging = Path(tempfile.mkdtemp(prefix=".easyviz-staging-", dir=target))
        preserve_backups = False
        try:
            backups = staging / "backups"
            backups.mkdir()
            expected = {}
            for name in SKILL_NAMES:
                bundle = staging / "new" / name
                shutil.copytree(source / "skills" / name, bundle)
                (bundle / OWNER_FILE).write_text(json.dumps({
                    "schema": 1, "managed_by": OWNER, "skill": name,
                    "version": manifest["version"],
                }, indent=2) + "\n", encoding="utf-8")
                validate_resource_tree(bundle)
                expected[name] = content_hashes(bundle)
            moved = []
            installed = []
            try:
                for name in SKILL_NAMES:
                    destination = target / name
                    _preflight_target(destination)
                    if destination.exists():
                        os.replace(destination, backups / name)
                        moved.append(name)
                    os.replace(staging / "new" / name, destination)
                    installed.append(name)
                for name in SKILL_NAMES:
                    validate_resource_tree(target / name)
                    verify_cached_content(expected[name], target / name)
            except Exception as error:
                rollback_errors = []
                for name in reversed(installed):
                    try:
                        remove_owned(target / name, target)
                    except (OSError, InstallError) as rollback_error:
                        rollback_errors.append(str(rollback_error))
                for name in reversed(moved):
                    try:
                        owned_path(target / name, target)
                        os.replace(backups / name, target / name)
                    except (OSError, InstallError) as rollback_error:
                        rollback_errors.append(str(rollback_error))
                if rollback_errors:
                    preserve_backups = True
                    raise InstallError(f"Installation failed and rollback could not finish. "
                                       f"Previous files are retained at {backups}: "
                                       + "; ".join(rollback_errors)) from error
                raise
        finally:
            if not preserve_backups:
                shutil.rmtree(staging)
    return {
        "status": "installed", "version": manifest["version"],
        "host": "deepseek-harness", "target": str(target),
        "paths": [str(target / name) for name in SKILL_NAMES],
        "discovery": "not_checked",
        "next_step": "In DeepSeek Harness, confirm easyviz is available and load it with the host's skill tool. "
                     "Filesystem discovery requires dsh-skill-filesystem and dsh-tool-skill in the active profile.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Validated EasyViz plugin directory, for example dist/easyviz")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--project", type=Path,
                       help="Install only in PROJECT/.dsh/skills")
    scope.add_argument("--dsh-home", type=Path,
                       help="Override DSH_HOME (default: $DSH_HOME or ~/.dsh)")
    args = parser.parse_args()
    try:
        result = install(args.source, project=args.project, dsh_home=args.dsh_home)
    except (InstallError, OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
