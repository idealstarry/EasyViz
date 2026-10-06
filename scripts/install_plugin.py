"""Install or refresh EasyViz in a local ChatGPT Desktop/Codex plugin client."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

from check_package import validate_plugin, validate_resource_tree
from package_io import file_sha256


class InstallError(RuntimeError):
    pass


_UNCHECKED = object()


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


def atomic_write(path: Path, data: bytes, *, expected_bytes: object = _UNCHECKED) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".easyviz-")
    staging = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        if expected_bytes is not _UNCHECKED:
            current = path.read_bytes() if path.exists() else None
            if current != expected_bytes:
                raise InstallError("Personal marketplace changed before commit; existing file was left untouched")
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
        hashes[relative.as_posix()] = file_sha256(path)
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


def owned_path(path: Path, boundary: Path) -> None:
    """Do not follow a symlink inside a selected installation boundary."""
    relative = path.relative_to(boundary)
    for candidate in (boundary, *(boundary.joinpath(*relative.parts[:index])
                                 for index in range(1, len(relative.parts) + 1))):
        if candidate.is_symlink():
            raise InstallError(f"Refusing to write through a symlink installation path: {candidate}")


def rollback_catalog(path: Path, original: bytes | None, written: dict) -> None:
    """Undo only our entry when another writer has changed unrelated metadata."""
    if not path.exists() or path.is_symlink():
        return
    try:
        current_bytes = path.read_bytes()
        current = json.loads(current_bytes)
        previous = json.loads(original) if original is not None else None
        if not isinstance(current, dict) or not isinstance(current.get("plugins"), list):
            return
        current_entries = current["plugins"]
        written_entry = next(item for item in written["plugins"] if item.get("name") == "easyviz")
        matches = [i for i, item in enumerate(current_entries) if isinstance(item, dict) and item.get("name") == "easyviz"]
        if len(matches) != 1 or current_entries[matches[0]] != written_entry:
            return  # A concurrent change to EasyViz itself is not ours to undo.
        if current == written:
            if original is None:
                if path.read_bytes() == current_bytes:
                    path.unlink()
            else:
                atomic_write(path, original, expected_bytes=current_bytes)
            return
        previous_entry = next((item for item in previous["plugins"] if item.get("name") == "easyviz"), None) if previous else None
        if previous_entry is None:
            current_entries.pop(matches[0])
        else:
            current_entries[matches[0]] = previous_entry
        atomic_write(path, (json.dumps(current, indent=2) + "\n").encode(), expected_bytes=current_bytes)
    except (ValueError, KeyError, TypeError, InstallError):
        # Preserve an externally edited invalid catalog rather than replacing it.
        return


def remove_owned(path: Path, boundary: Path) -> None:
    """Remove only a predetermined leaf; never follow its replacement symlink."""
    owned_path(path.parent, boundary)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


@contextmanager
def installation_lock(codex_home: Path, relative: str = "plugins/.easyviz-install.lock"):
    """Only one cooperating EasyViz installer may mutate this client at a time."""
    lock = codex_home / relative
    owned_path(lock, codex_home)
    if lock.exists() and not lock.is_file():
        raise InstallError("EasyViz installation lock is not a regular file; left untouched")
    lock.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "r+b") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise InstallError("EasyViz installation lock is not a regular file; left untouched")
        if os.name == "nt":
            import msvcrt
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise InstallError("Another EasyViz installation is running; retry after it completes") from error
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise InstallError("Another EasyViz installation is running; retry after it completes") from error
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def install(source: Path, home: Path, codex_home: Path, explicit_cli: str | None) -> dict:
    home, codex_home = home.resolve(), codex_home.resolve()
    validate_plugin(source)
    owned_path(home / ".agents/plugins/marketplace.json", home)
    owned_path(codex_home / "plugins/easyviz", codex_home)
    if (codex_home / "plugins").is_relative_to(source.resolve()):
        raise InstallError("Installation home must be outside the selected source package")
    # The catalog can be shared by different CODEX_HOME selections, so lock it
    # first, then the client source/cache. Every installer uses this same order.
    with ExitStack() as locks:
        held = set()
        for boundary, relative in ((home, ".agents/plugins/.easyviz-install.lock"),
                                   (codex_home, "plugins/.easyviz-install.lock")):
            path = boundary / relative
            owned_path(path, boundary)
            identity = path.resolve()
            if identity not in held:
                locks.enter_context(installation_lock(boundary, relative))
                held.add(identity)
        return _install(source, home, codex_home, explicit_cli)


def _install(source: Path, home: Path, codex_home: Path, explicit_cli: str | None) -> dict:
    home, codex_home = home.resolve(), codex_home.resolve()
    manifest = validate_plugin(source)
    catalog_path = home / ".agents/plugins/marketplace.json"
    target = codex_home / "plugins/easyviz"
    owned_path(catalog_path, home)
    owned_path(target, codex_home)
    if target.parent.is_relative_to(source.resolve()):
        raise InstallError("Installation home must be outside the selected source package")
    if target.exists():
        try:
            # Recognize ownership without requiring new-release resources in an old installation.
            owned_path(target / ".codex-plugin/plugin.json", target)
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
    isolated = home != Path.home().resolve()
    marketplace = ("easyviz-isolated-" + hashlib.sha256(str(home).encode()).hexdigest()[:12]) if isolated else catalog["name"]
    isolated_path = target.parent / ".agents/plugins/marketplace.json"
    isolated_original = None
    isolated_catalog = None
    if isolated:
        owned_path(isolated_path, codex_home)
        if isolated_path.exists() and not isolated_path.is_file():
            raise InstallError("Isolated marketplace is not a file; existing path was left untouched")
    cache = codex_home / "plugins/cache" / marketplace / "easyviz" / manifest["version"]
    owned_path(cache, codex_home)
    if cache.exists():
        validate_resource_tree(cache)
        previous_cache = json.loads((cache / ".codex-plugin/plugin.json").read_text())
        if (not isinstance(previous_cache, dict) or previous_cache.get("name") != "easyviz"
                or previous_cache.get("version") != manifest["version"]):
            raise InstallError("Existing selected cache is not identified as this EasyViz version; left untouched")
    codex_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    cli = detect_cli(explicit_cli, env, home)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".easyviz-stage-", dir=target.parent))
    backup = None
    catalog_backup = None
    cache_backup = None
    cache_attempted = False
    target_replaced = False
    catalog_replaced = False
    isolated_replaced = False
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
        # Re-merge an unrelated concurrent catalog edit before writing our entry.
        latest = catalog_path.read_bytes() if catalog_path.exists() else None
        if latest != original:
            latest_catalog = merged_catalog(latest, entry)
            if latest_catalog["name"] != catalog["name"]:
                raise InstallError("Personal marketplace name changed while preparing installation")
            original, catalog = latest, latest_catalog
        if original is not None:
            catalog_backup = catalog_path.with_name(f"marketplace.json.easyviz-backup-{suffix}")
            atomic_write(catalog_backup, original)
        atomic_write(catalog_path, (json.dumps(catalog, indent=2) + "\n").encode(), expected_bytes=original)
        catalog_replaced = True
        if isolated:
            # CLI default discovery still reads the real OS home even with CODEX_HOME.
            # A uniquely named catalog prevents an isolated test selecting the real Personal source.
            isolated_root = target.parent
            view_entry = {**entry, "source": {"source": "local", "path": "./easyviz"}}
            latest_isolated = isolated_path.read_bytes() if isolated_path.exists() else None
            template = {"name": marketplace, "interface": {"displayName": "Isolated EasyViz"}, "plugins": []}
            isolated_catalog = merged_catalog(latest_isolated if latest_isolated is not None
                                              else json.dumps(template).encode(), view_entry)
            if isolated_catalog["name"] != marketplace:
                raise InstallError("Isolated marketplace is not identified as this installation; left untouched")
            isolated_original = latest_isolated
            owned_path(isolated_path, codex_home)
            atomic_write(isolated_path,
                         (json.dumps(isolated_catalog, indent=2) + "\n").encode(),
                         expected_bytes=isolated_original)
            isolated_replaced = True
            run([cli, "plugin", "marketplace", "add", str(isolated_root), "--json"], env=env, cwd=home)
        # Snapshot the trusted, predetermined cache location before invoking a
        # CLI that can overwrite the same-version cache and then fail validation.
        owned_path(cache, codex_home)
        if cache.exists():
            validate_resource_tree(cache)
            cache_backup = target.with_name(f"easyviz.cache-backup-{suffix}")
            try:
                shutil.copytree(cache, cache_backup)
            except Exception:
                remove_owned(cache_backup, codex_home)
                cache_backup = None
                raise
        cache_attempted = True
        installed = run([cli, "plugin", "add", f"easyviz@{marketplace}", "--json"], env=env, cwd=home)
        result = json.loads(installed.stdout)
        if not isinstance(result, dict) or not isinstance(result.get("installedPath"), str):
            raise InstallError("CLI did not identify a valid installed cache path")
        owned_path(cache, codex_home)
        installed_path = Path(result["installedPath"]).resolve()
        if installed_path != cache.resolve():
            raise InstallError("CLI returned an installed path outside the selected EasyViz cache")
        cached_manifest = validate_plugin(installed_path)
        if cached_manifest != manifest:
            raise InstallError("Installed manifest does not match the selected EasyViz package")
        verify_cached_content(expected_content, installed_path)
        listed = run([cli, "plugin", "list", "--marketplace", marketplace, "--json"], env=env, cwd=home)
        listing = json.loads(listed.stdout)
        rows = listing.get("installed", []) if isinstance(listing, dict) else []
        if not isinstance(rows, list) or not any(isinstance(item, dict) and item.get("pluginId") == f"easyviz@{marketplace}"
                   and item.get("installed") is True and item.get("enabled") is True for item in rows):
            raise InstallError("Codex did not confirm EasyViz is installed and enabled")
        return {"status": "installed", "version": manifest["version"], "plugin_id": f"easyviz@{marketplace}",
                "source": str(target), "installed_path": str(installed_path),
                "marketplace": str(catalog_path), "codex": cli,
                "backups": [str(p) for p in (backup, catalog_backup, cache_backup) if p is not None],
                "next_step": "Start a new chat; restart ChatGPT Desktop if its plugin list has not refreshed."}
    except Exception as error:
        rollback_errors = []
        try:
            if cache_attempted:
                remove_owned(cache, codex_home)
                if cache_backup is not None and cache_backup.exists():
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache_backup.rename(cache)
        except (OSError, InstallError) as rollback_error:
            rollback_errors.append(str(rollback_error))
        try:
            if target_replaced:
                remove_owned(target, codex_home)
            if backup is not None and backup.exists():
                owned_path(target.parent, codex_home)
                backup.rename(target)
        except (OSError, InstallError) as rollback_error:
            rollback_errors.append(str(rollback_error))
        try:
            if catalog_replaced:
                owned_path(catalog_path, home)
                rollback_catalog(catalog_path, original, catalog)
        except (OSError, InstallError) as rollback_error:
            rollback_errors.append(str(rollback_error))
        try:
            if isolated_replaced:
                owned_path(isolated_path, codex_home)
                rollback_catalog(isolated_path, isolated_original, isolated_catalog)
        except (OSError, InstallError) as rollback_error:
            rollback_errors.append(str(rollback_error))
        if rollback_errors:
            raise InstallError(f"{error}; rollback could not safely restore: {'; '.join(rollback_errors)}") from error
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
