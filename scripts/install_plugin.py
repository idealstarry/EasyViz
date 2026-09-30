"""Install or refresh EasyViz in a local ChatGPT Desktop/Codex plugin client."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from check_package import validate_plugin


class InstallError(RuntimeError):
    pass


def run(command: list[str], *, env: dict, cwd: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        message = (result.stderr or result.stdout).strip()
        raise InstallError(f"{' '.join(command[:3])} failed ({result.returncode}): {message}")
    return result


def detect_cli(explicit: str | None, env: dict, cwd: Path) -> str:
    candidates = [explicit] if explicit else [shutil.which("codex"),
        "/opt/homebrew/bin/codex", "/usr/local/bin/codex",
        "/Applications/Codex.app/Contents/Resources/codex",
        "/Applications/ChatGPT.app/Contents/Resources/codex"]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        result = subprocess.run([candidate, "plugin", "add", "--help"],
                                cwd=cwd, env=env, capture_output=True, text=True)
        if result.returncode == 0 and "--json" in result.stdout:
            return str(Path(candidate).resolve())
    raise InstallError("No compatible Codex CLI found. A local client with 'codex plugin add --json' "
                       "is required; update the selected Codex installation or pass --codex /path/to/codex.")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".easyviz-", delete=False) as stream:
        staging = Path(stream.name)
        stream.write(data)
    try:
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def content_hashes(folder: Path) -> dict[str, str]:
    """Identify package content while ignoring files created by local Python/macOS runs."""
    hashes = {}
    for path in folder.rglob("*"):
        relative = path.relative_to(folder)
        if ("__pycache__" in relative.parts or path.name == ".DS_Store"
                or path.suffix in (".pyc", ".pyo") or not path.is_file()):
            continue
        hashes[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def verify_cached_content(expected: dict[str, str], installed_path: Path) -> None:
    actual = content_hashes(installed_path)
    missing = sorted(expected.keys() - actual.keys())
    unexpected = sorted(actual.keys() - expected.keys())
    changed = sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name])
    if missing or unexpected or changed:
        details = [f"{label}: {', '.join(paths[:8])}" for label, paths in
                   (("missing", missing), ("unexpected", unexpected), ("changed", changed)) if paths]
        raise InstallError("Installed cache differs from the selected EasyViz package (" +
                           "; ".join(details) + "). Installation was not verified.")


def merged_catalog(original: bytes | None, entry: dict) -> dict:
    catalog = json.loads(original) if original is not None else {
        "name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
    if not isinstance(catalog, dict) or not isinstance(catalog.get("plugins"), list):
        raise InstallError("Personal marketplace must contain a plugins array; existing file was not changed")
    if not isinstance(catalog.get("name"), str) or not re.fullmatch(r"[A-Za-z0-9_-]+", catalog["name"]):
        raise InstallError("Personal marketplace has no usable name; existing file was not changed")
    entries = catalog["plugins"]
    if any(not isinstance(item, dict) for item in entries):
        raise InstallError("Personal marketplace contains an invalid entry; existing file was not changed")
    matches = [index for index, item in enumerate(entries) if item.get("name") == "easyviz"]
    if len(matches) > 1:
        raise InstallError("Personal marketplace contains duplicate EasyViz entries; resolve them before installing")
    if matches:
        # Retain optional metadata on the existing EasyViz entry too.
        entries[matches[0]] = {**entries[matches[0]], **entry}
    else:
        entries.append(entry)
    return catalog


def install(source: Path, home: Path, codex_home: Path, explicit_cli: str | None) -> dict:
    manifest = validate_plugin(source)
    catalog_path = home / ".agents/plugins/marketplace.json"
    target = codex_home / "plugins/easyviz"
    if catalog_path.is_symlink() or target.is_symlink():
        raise InstallError("Refusing to replace a symlink marketplace or EasyViz source directory")
    if target.exists():
        try:
            # Recognize ownership without requiring new-release resources in an old installation.
            previous = json.loads((target / ".codex-plugin/plugin.json").read_text())
            if not isinstance(previous, dict) or previous.get("name") != "easyviz":
                raise ValueError("manifest name is not easyviz")
        except (OSError, ValueError) as error:
            raise InstallError(f"Existing {target} is not identified as an EasyViz source; left untouched: {error}") from error
    original = catalog_path.read_bytes() if catalog_path.exists() else None
    relative = os.path.relpath(target, home).replace(os.sep, "/")
    entry = {"name": "easyviz", "source": {"source": "local", "path": "./" + relative},
             "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
             "category": "Productivity"}
    catalog = merged_catalog(original, entry)
    codex_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    cli = detect_cli(explicit_cli, env, home)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".easyviz-stage-", dir=target.parent))
    backup = None
    catalog_backup = None
    target_replaced = False
    catalog_replaced = False
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    try:
        shutil.copytree(source, staging, dirs_exist_ok=True)
        validate_plugin(staging)
        expected_content = content_hashes(staging)
        if target.exists():
            backup = target.with_name(f"easyviz.backup-{suffix}")
            target.rename(backup)
        staging.rename(target)
        target_replaced = True
        if original is not None:
            catalog_backup = catalog_path.with_name(f"marketplace.json.easyviz-backup-{suffix}")
            atomic_write(catalog_backup, original)
        atomic_write(catalog_path, (json.dumps(catalog, indent=2) + "\n").encode())
        catalog_replaced = True
        marketplace = catalog["name"]
        if home != Path.home().resolve():
            # CLI default discovery still reads the real OS home even with CODEX_HOME.
            # A uniquely named catalog prevents an isolated test selecting the real Personal source.
            isolated_root = target.parent
            marketplace = "easyviz-isolated-" + hashlib.sha256(str(home).encode()).hexdigest()[:12]
            view_entry = {**entry, "source": {"source": "local", "path": "./easyviz"}}
            isolated_catalog = {"name": marketplace, "interface": {"displayName": "Isolated EasyViz"},
                                "plugins": [view_entry]}
            atomic_write(isolated_root / ".agents/plugins/marketplace.json",
                         (json.dumps(isolated_catalog, indent=2) + "\n").encode())
            run([cli, "plugin", "marketplace", "add", str(isolated_root), "--json"], env=env, cwd=home)
        installed = run([cli, "plugin", "add", f"easyviz@{marketplace}", "--json"], env=env, cwd=home)
        result = json.loads(installed.stdout)
        installed_path = Path(result["installedPath"]).resolve()
        if not installed_path.is_relative_to(codex_home.resolve()):
            raise InstallError("CLI returned an installed path outside the selected Codex home")
        cached_manifest = validate_plugin(installed_path)
        if cached_manifest != manifest:
            raise InstallError("Installed manifest does not match the selected EasyViz package")
        verify_cached_content(expected_content, installed_path)
        listed = run([cli, "plugin", "list", "--marketplace", marketplace, "--json"], env=env, cwd=home)
        listing = json.loads(listed.stdout)
        rows = listing.get("installed", [])
        if not any(item.get("pluginId") == f"easyviz@{marketplace}" and item.get("installed")
                   and item.get("enabled") for item in rows):
            raise InstallError("Codex did not confirm EasyViz is installed and enabled")
        return {"status": "installed", "version": manifest["version"], "plugin_id": f"easyviz@{marketplace}",
                "source": str(target), "installed_path": str(installed_path),
                "marketplace": str(catalog_path), "codex": cli,
                "backups": [str(p) for p in (backup, catalog_backup) if p is not None],
                "next_step": "Start a new chat; restart ChatGPT Desktop if its plugin list has not refreshed."}
    except Exception:
        if target_replaced and target.exists():
            shutil.rmtree(target)
        if backup is not None and backup.exists():
            backup.rename(target)
        if catalog_replaced and original is None:
            catalog_path.unlink(missing_ok=True)
        elif catalog_replaced:
            atomic_write(catalog_path, original)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Local checkout, dist/easyviz, or extracted easyviz package")
    parser.add_argument("--build", action="store_true", help="Build a checkout first using only the Python standard library")
    parser.add_argument("--home", type=Path, help="Explicit OS home for an isolated installation test")
    parser.add_argument("--codex", help="Explicit compatible Codex CLI executable")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if args.build:
        builder = source / "scripts/build_plugin.py"
        if not builder.is_file():
            raise InstallError("--build requires a full EasyViz checkout")
        build = subprocess.run([sys.executable, str(builder)], cwd=source, capture_output=True, text=True)
        if build.returncode:
            raise InstallError(f"Plugin build failed: {build.stdout}{build.stderr}")
    if (source / "dist/easyviz/.codex-plugin/plugin.json").is_file():
        source = source / "dist/easyviz"
    elif not (source / ".codex-plugin/plugin.json").is_file():
        raise InstallError("No built EasyViz package found. For a checkout run this installer with --build.")
    home = args.home.expanduser().resolve() if args.home else Path.home().resolve()
    if args.home:
        home.mkdir(parents=True, exist_ok=True)
        codex_home = home / ".codex"
    else:
        codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser().resolve()
    print(json.dumps(install(source, home, codex_home, args.codex), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, InstallError, KeyError) as error:
        print(f"EasyViz installation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
