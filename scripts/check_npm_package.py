"""Verify an actual npm tarball, its installed CLI and Harness skill delivery."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile


def run(command: list[str], *, cwd: Path, env: dict) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"Package check failed: {result.stderr or result.stdout}")
    return result.stdout


def check(archive: Path) -> dict:
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        raise ValueError("Node.js and npm are required for the npm delivery check")
    archive = archive.resolve()
    with tempfile.TemporaryDirectory(prefix="easyviz npm delivery ") as temporary:
        root = Path(temporary).resolve()
        with tarfile.open(archive, "r:gz") as package:
            members = package.getmembers()
            if len(members) > 10000 or sum(item.size for item in members) > 200_000_000:
                raise ValueError("npm package exceeds delivery-check limits")
            paths = set()
            for item in members:
                name = PurePosixPath(item.name)
                if (name.is_absolute() or ".." in name.parts or not name.parts
                        or name.parts[0] != "package" or "\\" in item.name
                        or not (item.isfile() or item.isdir()) or item.name in paths):
                    raise ValueError(f"Unsafe or duplicate npm entry: {item.name}")
                paths.add(item.name)
                allowed = {"bin", "dist", "scripts", "package.json", "README.md",
                           "LICENSE", "THIRD_PARTY_NOTICES.md", "INSTALL.md"}
                if len(name.parts) > 1 and name.parts[1] not in allowed:
                    raise ValueError(f"Unexpected npm resource: {item.name}")
            metadata = json.load(package.extractfile("package/package.json"))
            if metadata.get("dependencies") or metadata.get("devDependencies"):
                raise ValueError("The npm entry must remain dependency-free")
            hooks = metadata.get("scripts", {})
            if any(key in hooks for key in ("preinstall", "install", "postinstall")):
                raise ValueError("npm installation must not execute registration hooks")

        env = {**os.environ, "NPM_CONFIG_CACHE": str(root / "npm-cache"),
               "PYTHONDONTWRITEBYTECODE": "1"}
        destination = root / "installed CLI"
        # Install through npm itself, rather than assuming extraction resembles
        # npm's bin wiring or nested package layout. No network or install hooks.
        run([npm, "install", "--prefix", str(destination), "--offline", "--ignore-scripts",
             "--no-audit", "--no-fund", "--package-lock=false", str(archive)], cwd=root, env=env)
        package_root = destination / "node_modules" / metadata["name"]
        entry = package_root / "bin/easyviz.mjs"
        elsewhere = root / "unrelated working directory"
        elsewhere.mkdir()
        version = run([node, str(entry), "--version"], cwd=elsewhere, env=env).strip()
        if version != metadata["version"]:
            raise ValueError("Installed npm CLI version differs from package metadata")
        payload = Path(run([node, str(entry), "path"], cwd=elsewhere, env=env).strip())
        sys.path.insert(0, str(package_root / "scripts"))
        from check_package import validate_plugin
        manifest = validate_plugin(payload)
        if manifest["version"] != version:
            raise ValueError("Installed portable payload differs from the npm CLI version")
        if not (destination / "node_modules/.bin/easyviz").exists():
            raise ValueError("npm did not expose the easyviz executable")
        dsh_home = root / "Harness home"
        profile = dsh_home / "cordis.patch.yml"
        profile.parent.mkdir()
        profile.write_text("existing profile\n", encoding="utf-8")
        output = run([node, str(entry), "install", "--target", "deepseek-harness",
                      "--python", sys.executable, "--dsh-home", str(dsh_home)], cwd=elsewhere, env=env)
        receipt = json.loads(output)
        if receipt["status"] != "installed" or receipt["version"] != version or len(receipt["paths"]) != 3:
            raise ValueError("Installed npm CLI did not deliver all Harness skills")
        if profile.read_text(encoding="utf-8") != "existing profile\n":
            raise ValueError("Harness installation changed an unrelated profile")
        return {"status": "passed", "version": version, "archive": archive.name,
                "files": len(members), "harness_skills": len(receipt["paths"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.archive), indent=2))
