"""Regression checks for preserving user files during local plugin installation."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install_plugin
from check_package import extract_package, validate_plugin


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="easyviz-installer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.source = self.root / "source"
        files = ["README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
                 "skills/easyviz/scripts/render.py", "skills/easyviz/scripts/figure_profile.py",
                 "skills/easyviz/scripts/legend_layout.py", "skills/easyviz/scripts/requirements.txt",
                 "skills/easyviz/assets/palettes/palettes.json",
                 "skills/easyviz/assets/fixtures/heatmap/data.csv",
                 "skills/easyviz/assets/fixtures/heatmap/spec.json"]
        files += [f"skills/{name}/SKILL.md" for name in
                  ("easyviz", "easyviz-reference-reader", "easyviz-figure-reviewer")]
        for name in files:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test resource\n")
        self.manifest = self.source / ".codex-plugin/plugin.json"
        self.manifest.parent.mkdir()
        self.manifest.write_text(json.dumps({"name": "easyviz", "version": "1.0.0"}))
        self.catalog = self.home / ".agents/plugins/marketplace.json"
        self.catalog.parent.mkdir(parents=True)
        self.other = {"name": "another-plugin", "custom": ["keep", 7]}
        self.original = {"name": "my-personal", "interface": {"displayName": "My list"},
                         "plugins": [self.other], "extra": {"preserve": True}}
        self.catalog.write_text(json.dumps(self.original))
        self.original_bytes = self.catalog.read_bytes()
        self.codex_home = self.home / ".codex"
        self.target = self.codex_home / "plugins/easyviz"
        self.cli = mock.patch.object(install_plugin, "detect_cli", return_value="test-codex")
        self.cli.start()
        self.addCleanup(self.cli.stop)

    def fake_cli(self, command, *, env, cwd):
        if command[1:3] == ["plugin", "add"]:
            self.selector = command[3]
            version = json.loads((self.target / ".codex-plugin/plugin.json").read_text())["version"]
            self.cache = Path(env["CODEX_HOME"]) / "plugins/cache/test/easyviz" / version
            if self.cache.exists():
                shutil.rmtree(self.cache)
            shutil.copytree(self.target, self.cache)
            output = {"installedPath": str(self.cache)}
        elif command[1:3] == ["plugin", "list"]:
            output = {"installed": [{"pluginId": self.selector, "installed": True, "enabled": True}]}
        else:
            output = {}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(output), stderr="")

    def install(self):
        return install_plugin.install(self.source, self.home, self.codex_home, None)

    def test_repeat_install_preserves_catalog_metadata_and_other_plugins(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
            result = self.install()
        catalog = json.loads(self.catalog.read_text())
        self.assertEqual(catalog["plugins"][0], self.other)
        self.assertEqual(len(catalog["plugins"]), 2)
        for key in ("name", "interface", "extra"):
            self.assertEqual(catalog[key], self.original[key])
        self.assertTrue(Path(result["installed_path"]).is_relative_to(self.home))
        self.assertEqual(len(result["backups"]), 2)

    def test_update_refreshes_the_actual_cached_manifest(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
            self.manifest.write_text(json.dumps({"name": "easyviz", "version": "1.1.0",
                                                 "interface": {"websiteURL": "https://example.org"}}))
            result = self.install()
        installed = Path(result["installed_path"]) / ".codex-plugin/plugin.json"
        self.assertEqual(json.loads(installed.read_text()), json.loads(self.manifest.read_text()))
        self.assertEqual(json.loads(self.catalog.read_text())["plugins"][0], self.other)

    def test_same_version_stale_cache_fails_instead_of_claiming_installation(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
        catalog_before = self.catalog.read_bytes()
        renderer = "skills/easyviz/scripts/render.py"
        previous_renderer = (self.target / renderer).read_bytes()
        (self.source / renderer).write_text("updated code, same manifest version\n")

        def stale_cli(command, *, env, cwd):
            if command[1:3] == ["plugin", "add"]:
                return subprocess.CompletedProcess(command, 0,
                    stdout=json.dumps({"installedPath": str(self.cache)}), stderr="")
            return self.fake_cli(command, env=env, cwd=cwd)

        with mock.patch.object(install_plugin, "run", side_effect=stale_cli):
            with self.assertRaisesRegex(install_plugin.InstallError, "changed: skills/easyviz/scripts/render.py"):
                self.install()
        self.assertEqual(self.catalog.read_bytes(), catalog_before)
        self.assertEqual((self.target / renderer).read_bytes(), previous_renderer)

    def test_cache_file_set_mismatch_is_rejected(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
        expected = install_plugin.content_hashes(self.target)
        (self.cache / "unexpected-source.py").write_text("old file\n")
        with self.assertRaisesRegex(install_plugin.InstallError, "unexpected: unexpected-source.py"):
            install_plugin.verify_cached_content(expected, self.cache)
        (self.cache / "unexpected-source.py").unlink()
        (self.cache / "README.md").unlink()
        with self.assertRaisesRegex(install_plugin.InstallError, "missing: README.md"):
            install_plugin.verify_cached_content(expected, self.cache)

    def test_generated_cache_artifacts_do_not_invalidate_package_content(self):
        def cli_with_artifacts(command, *, env, cwd):
            result = self.fake_cli(command, env=env, cwd=cwd)
            if command[1:3] == ["plugin", "add"]:
                cache_dir = self.cache / "skills/easyviz/scripts/__pycache__"
                cache_dir.mkdir()
                (cache_dir / "render.cpython-312.pyc").write_bytes(b"generated cache")
                (self.cache / ".DS_Store").write_bytes(b"macOS metadata")
                (self.cache / "loose.pyc").write_bytes(b"Python bytecode")
            return result
        with mock.patch.object(install_plugin, "run", side_effect=cli_with_artifacts):
            result = self.install()
        self.assertEqual(result["status"], "installed")

    def test_missing_runtime_helper_or_palette_rejects_source_and_extracted_package(self):
        for name in ("scripts/figure_profile.py", "scripts/legend_layout.py", "assets/palettes/palettes.json"):
            with self.subTest(resource=name):
                resource = self.source / "skills/easyviz" / name
                contents = resource.read_bytes()
                resource.unlink()
                try:
                    with self.assertRaisesRegex(ValueError, "Missing or external package resource"):
                        self.install()
                    self.assertEqual(self.catalog.read_bytes(), self.original_bytes)
                    self.assertFalse(self.target.exists())
                    archive = self.root / "missing-resource.zip"
                    with zipfile.ZipFile(archive, "w") as package:
                        for path in self.source.rglob("*"):
                            if path.is_file():
                                package.write(path, "easyviz/" + path.relative_to(self.source).as_posix())
                    extracted = self.root / ("extracted-" + resource.stem)
                    extract_package(archive, extracted)
                    with self.assertRaisesRegex(ValueError, "Missing or external package resource"):
                        validate_plugin(extracted / "easyviz")
                finally:
                    resource.write_bytes(contents)

    def test_older_easyviz_source_can_be_upgraded_with_new_runtime_resources(self):
        shutil.copytree(self.source, self.target)
        (self.target / "skills/easyviz/scripts/figure_profile.py").unlink()
        (self.target / ".codex-plugin/plugin.json").write_text(json.dumps({"name": "easyviz", "version": "0.1.2"}))
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            result = self.install()
        self.assertEqual(result["status"], "installed")
        self.assertTrue((self.target / "skills/easyviz/scripts/figure_profile.py").is_file())
        backup = Path(result["backups"][0])
        self.assertFalse((backup / "skills/easyviz/scripts/figure_profile.py").exists())

    def test_cli_failure_restores_exact_catalog_and_previous_source(self):
        shutil.copytree(self.source, self.target)
        note = self.target / "user-note.txt"
        note.write_text("keep this")
        with mock.patch.object(install_plugin, "run", side_effect=install_plugin.InstallError("CLI failed")):
            with self.assertRaises(install_plugin.InstallError):
                self.install()
        self.assertEqual(self.catalog.read_bytes(), self.original_bytes)
        self.assertEqual(note.read_text(), "keep this")

    def test_staging_failure_does_not_remove_existing_source(self):
        shutil.copytree(self.source, self.target)
        note = self.target / "user-note.txt"
        note.write_text("keep this")
        with mock.patch.object(install_plugin.shutil, "copytree", side_effect=OSError("copy failed")):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual(self.catalog.read_bytes(), self.original_bytes)
        self.assertEqual(note.read_text(), "keep this")

    def test_invalid_catalog_is_left_untouched(self):
        self.catalog.write_bytes(b"{ invalid JSON")
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.catalog.read_bytes(), b"{ invalid JSON")
        self.assertFalse(self.target.exists())

    def test_unsafe_zip_is_rejected_before_extraction(self):
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("easyviz/../escape.txt", "unsafe")
        with self.assertRaises(ValueError):
            extract_package(archive, self.root / "extracted")
        self.assertFalse((self.root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
