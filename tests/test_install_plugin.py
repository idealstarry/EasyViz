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
from check_package import CURATED_CREATE_RESOURCES, extract_package, validate_plugin


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
                 "skills/easyviz/scripts/auto_layout.py", "skills/easyviz/scripts/annotation_review.py",
                 "skills/easyviz/scripts/draft_spec.py",
                 "skills/easyviz/scripts/create_style.py",
                 "skills/easyviz/scripts/panel_readability.py",
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
                 "skills/easyviz/scripts/figure_handoff.py",
                 "skills/easyviz/scripts/observation_clipping.py",
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
        files += [f"skills/easyviz/assets/cases/basic-panels/{name}"
                  for name in ("README.md", "plot.py", "validate.py", "manifest.json")]
        files += [f"skills/easyviz/assets/cases/basic-panels/{case}/{name}"
                  for case in ("replicate-bars", "paired-scatter", "cohort-box", "cohort-violin", "depot-heatmap")
                  for name in ("source-data.csv", "candidate-spec.json", "caption.md", "provenance.json")]
        files += [f"skills/{name}/SKILL.md" for name in
                  ("easyviz", "easyviz-reference-reader", "easyviz-figure-reviewer")]
        for name in files:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test resource\n")
        # Structure fixtures include every future runtime-consumed dependency;
        # actual numeric/vector correctness is tested by the extracted smoke.
        for case, resources in CURATED_CREATE_RESOURCES.items():
            for name in resources:
                path = self.source / "skills/easyviz/assets/cases" / case / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"portable case test resource\n")
        self.manifest = self.source / ".codex-plugin/plugin.json"
        self.manifest.parent.mkdir()
        self.manifest.write_text(json.dumps({"name": "easyviz", "version": "0.4.2"}))
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
            marketplace = self.selector.split("@", 1)[1]
            self.cache = Path(env["CODEX_HOME"]) / "plugins/cache" / marketplace / "easyviz" / version
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
        self.assertEqual(len(result["backups"]), 3)

    def test_update_refreshes_the_actual_cached_manifest(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
            self.manifest.write_text(json.dumps({"name": "easyviz", "version": "0.4.3",
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
        self.assertEqual((self.cache / renderer).read_bytes(), previous_renderer)

    def test_current_release_installs_with_real_design_card_resources(self):
        for name in ("scripts/create_candidates.py", "scripts/create_review.py",
                     "references/first-draft.md", "references/design-cards.md"):
            path = self.source / "skills/easyviz" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("release test resource\n")
        repo = Path(__file__).resolve().parents[1]
        shutil.copytree(repo / "skills/easyviz/assets/design-cards",
                        self.source / "skills/easyviz/assets/design-cards")
        for version in ("0.4.4", "0.4.5"):
            with self.subTest(version=version):
                self.manifest.write_text(json.dumps({"name": "easyviz", "version": version}))
                with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
                    result = self.install()
                self.assertEqual(result["version"], version)
                self.assertEqual(validate_plugin(Path(result["installed_path"]))["version"], version)

    def test_new_handoff_dependency_is_required_before_install_writes_but_old_packages_remain_valid(self):
        for name in ("scripts/create_candidates.py", "scripts/create_review.py",
                     "references/first-draft.md", "references/design-cards.md"):
            path = self.source / "skills/easyviz" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("release test resource\n")
        repo = Path(__file__).resolve().parents[1]
        shutil.copytree(repo / "skills/easyviz/assets/design-cards",
                        self.source / "skills/easyviz/assets/design-cards")
        for helper_name in ("figure_handoff.py", "observation_clipping.py"):
            with self.subTest(helper=helper_name):
                helper = self.source / "skills/easyviz/scripts" / helper_name
                original = helper.read_bytes()
                helper.unlink()
                self.manifest.write_text(json.dumps({"name": "easyviz", "version": "0.4.4"}))
                self.assertEqual(validate_plugin(self.source)["version"], "0.4.4")
                self.manifest.write_text(json.dumps({"name": "easyviz", "version": "0.4.5"}))
                with mock.patch.object(install_plugin, "run") as cli:
                    with self.assertRaisesRegex(ValueError, helper_name):
                        self.install()
                    cli.assert_not_called()
                self.assertEqual(self.catalog.read_bytes(), self.original_bytes)
                self.assertFalse(self.target.exists())
                self.assertFalse((self.codex_home / "plugins/cache").exists())
                helper.write_bytes(original)
                self.assertEqual(validate_plugin(self.source)["version"], "0.4.5")

    def test_missing_curated_source_workbook_refuses_future_install_without_writes(self):
        for name in ("scripts/create_candidates.py", "scripts/create_review.py",
                     "references/first-draft.md", "references/design-cards.md"):
            path = self.source / "skills/easyviz" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("release test resource\n")
        repo = Path(__file__).resolve().parents[1]
        shutil.copytree(repo / "skills/easyviz/assets/design-cards",
                        self.source / "skills/easyviz/assets/design-cards")
        workbook = self.source / "skills/easyviz/assets/cases/compartment-ccl2/inputs/41590_2023_1468_MOESM5_ESM.xlsx"
        workbook.unlink()
        self.manifest.write_text(json.dumps({"name": "easyviz", "version": "0.4.4"}))
        self.assertEqual(validate_plugin(self.source)["version"], "0.4.4")
        self.manifest.write_text(json.dumps({"name": "easyviz", "version": "0.4.5"}))
        with mock.patch.object(install_plugin, "run") as cli:
            with self.assertRaisesRegex(ValueError, "41590_2023_1468_MOESM5_ESM.xlsx"):
                self.install()
            cli.assert_not_called()
        self.assertEqual(self.catalog.read_bytes(), self.original_bytes)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.codex_home / "plugins/cache").exists())

    def test_extra_source_links_and_special_files_are_rejected_before_writes(self):
        outside = self.root / "private-file.txt"
        outside.write_text("private fixture\n")
        external_directory = self.root / "private-directory"
        external_directory.mkdir()
        (external_directory / "private-file.txt").write_text("private fixture\n")
        link = self.source / "extra-resource"
        for selected in (outside, external_directory):
            with self.subTest(selected=selected.name):
                link.symlink_to(selected)
                try:
                    with mock.patch.object(install_plugin, "run") as cli:
                        with self.assertRaisesRegex(ValueError, "Symlink or special package resource"):
                            self.install()
                        cli.assert_not_called()
                    self.assertEqual(self.catalog.read_bytes(), self.original_bytes)
                    self.assertFalse(self.target.exists())
                    self.assertEqual(outside.read_text(), "private fixture\n")
                finally:
                    link.unlink()
        import os
        os.mkfifo(link)
        with self.assertRaisesRegex(ValueError, "Symlink or special package resource"):
            validate_plugin(self.source)

    def test_failed_same_version_overwrite_restores_cache_and_retains_concurrent_catalog_edits(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
        source_before = install_plugin.content_hashes(self.target)
        cache_before = install_plugin.content_hashes(self.cache)
        previous_entry = json.loads(self.catalog.read_text())["plugins"][1]
        renderer = "skills/easyviz/scripts/render.py"
        (self.source / renderer).write_text("new selected code\n")
        concurrent = {"name": "added-during-install", "custom": "retain"}

        def corrupting_cli(command, *, env, cwd):
            result = self.fake_cli(command, env=env, cwd=cwd)
            if command[1:3] == ["plugin", "add"]:
                (self.cache / renderer).write_text("corrupted installed code\n")
                catalog = json.loads(self.catalog.read_text())
                catalog["plugins"].append(concurrent)
                catalog["concurrent-metadata"] = {"retain": True}
                self.catalog.write_text(json.dumps(catalog))
            return result

        with mock.patch.object(install_plugin, "run", side_effect=corrupting_cli):
            with self.assertRaisesRegex(install_plugin.InstallError, "changed: skills/easyviz/scripts/render.py"):
                self.install()
        self.assertEqual(install_plugin.content_hashes(self.target), source_before)
        self.assertEqual(install_plugin.content_hashes(self.cache), cache_before)
        catalog = json.loads(self.catalog.read_text())
        self.assertEqual(catalog["plugins"], [self.other, previous_entry, concurrent])
        self.assertEqual(catalog["concurrent-metadata"], {"retain": True})

    def test_first_install_failure_removes_only_our_catalog_entry_and_new_cache(self):
        concurrent = {"name": "added-during-install", "custom": "retain"}

        def failing_cli(command, *, env, cwd):
            result = self.fake_cli(command, env=env, cwd=cwd)
            if command[1:3] == ["plugin", "add"]:
                catalog = json.loads(self.catalog.read_text())
                catalog["plugins"].append(concurrent)
                self.catalog.write_text(json.dumps(catalog))
                raise install_plugin.InstallError("CLI failed after installing cache")
            return result

        with mock.patch.object(install_plugin, "run", side_effect=failing_cli):
            with self.assertRaisesRegex(install_plugin.InstallError, "CLI failed after installing cache"):
                self.install()
        self.assertFalse(self.target.exists())
        self.assertFalse(self.cache.exists())
        self.assertEqual(json.loads(self.catalog.read_text())["plugins"], [self.other, concurrent])

    def test_failed_install_does_not_undo_a_concurrent_change_to_easyviz_entry(self):
        concurrent_bytes = None

        def failing_cli(command, *, env, cwd):
            nonlocal concurrent_bytes
            result = self.fake_cli(command, env=env, cwd=cwd)
            if command[1:3] == ["plugin", "add"]:
                catalog = json.loads(self.catalog.read_text())
                catalog["plugins"][1]["concurrent-owner"] = "retain"
                concurrent_bytes = json.dumps(catalog).encode()
                self.catalog.write_bytes(concurrent_bytes)
                raise install_plugin.InstallError("CLI failed")
            return result

        with mock.patch.object(install_plugin, "run", side_effect=failing_cli):
            with self.assertRaises(install_plugin.InstallError):
                self.install()
        self.assertEqual(self.catalog.read_bytes(), concurrent_bytes)

    def test_wrong_cli_path_is_not_used_for_rollback(self):
        for selected in (self.root / "external-cli-result", self.codex_home / "unrelated-cli-result"):
            with self.subTest(selected=selected.name):
                selected.mkdir(parents=True)
                marker = selected / "user-file.txt"
                marker.write_text("do not delete\n")

                def misleading_cli(command, *, env, cwd):
                    result = self.fake_cli(command, env=env, cwd=cwd)
                    if command[1:3] == ["plugin", "add"]:
                        return subprocess.CompletedProcess(command, 0,
                            stdout=json.dumps({"installedPath": str(selected)}), stderr="")
                    return result

                with mock.patch.object(install_plugin, "run", side_effect=misleading_cli):
                    with self.assertRaisesRegex(install_plugin.InstallError, "outside the selected EasyViz cache"):
                        self.install()
                self.assertEqual(marker.read_text(), "do not delete\n")
                self.assertFalse(self.cache.exists())
                self.assertFalse(self.target.exists())
                self.assertEqual(self.catalog.read_bytes(), self.original_bytes)

    def test_cli_replacing_cache_with_symlink_cannot_modify_external_data(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
        source_before = install_plugin.content_hashes(self.target)
        cache_before = install_plugin.content_hashes(self.cache)
        catalog_before = self.catalog.read_bytes()
        external = self.root / "external-cache-target"
        external.mkdir()
        marker = external / "private-file.txt"
        marker.write_text("do not modify\n")

        def linking_cli(command, *, env, cwd):
            result = self.fake_cli(command, env=env, cwd=cwd)
            if command[1:3] == ["plugin", "add"]:
                shutil.rmtree(self.cache)
                self.cache.symlink_to(external)
            return result

        with mock.patch.object(install_plugin, "run", side_effect=linking_cli):
            with self.assertRaisesRegex(install_plugin.InstallError, "symlink installation path"):
                self.install()
        self.assertFalse(self.cache.is_symlink())
        self.assertEqual(install_plugin.content_hashes(self.cache), cache_before)
        self.assertEqual(install_plugin.content_hashes(self.target), source_before)
        self.assertEqual(self.catalog.read_bytes(), catalog_before)
        self.assertEqual(marker.read_text(), "do not modify\n")

    def test_catalog_parent_symlink_is_rejected_without_modifying_external_data(self):
        external = self.root / "external-agent-directory"
        (self.home / ".agents").rename(external)
        (self.home / ".agents").symlink_to(external)
        with mock.patch.object(install_plugin, "run") as cli:
            with self.assertRaisesRegex(install_plugin.InstallError, "symlink installation path"):
                self.install()
            cli.assert_not_called()
        self.assertEqual((external / "plugins/marketplace.json").read_bytes(), self.original_bytes)
        self.assertFalse(self.target.exists())

    def test_failed_new_version_keeps_previous_version_cache_and_source(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
        old_cache = self.cache
        old_cache_content = install_plugin.content_hashes(old_cache)
        old_source_content = install_plugin.content_hashes(self.target)
        old_catalog = self.catalog.read_bytes()
        self.manifest.write_text(json.dumps({"name": "easyviz", "version": "0.4.3"}))

        def disabled_cli(command, *, env, cwd):
            result = self.fake_cli(command, env=env, cwd=cwd)
            if command[1:3] == ["plugin", "list"]:
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"installed": [
                    {"pluginId": self.selector, "installed": True, "enabled": False}]}), stderr="")
            return result

        with mock.patch.object(install_plugin, "run", side_effect=disabled_cli):
            with self.assertRaisesRegex(install_plugin.InstallError, "did not confirm EasyViz"):
                self.install()
        self.assertFalse(self.cache.exists())
        self.assertEqual(install_plugin.content_hashes(old_cache), old_cache_content)
        self.assertEqual(install_plugin.content_hashes(self.target), old_source_content)
        self.assertEqual(self.catalog.read_bytes(), old_catalog)

    def test_cli_boolean_strings_cannot_claim_enabled_installation(self):
        def malformed_cli(command, *, env, cwd):
            result = self.fake_cli(command, env=env, cwd=cwd)
            if command[1:3] == ["plugin", "list"]:
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"installed": [
                    {"pluginId": self.selector, "installed": "false", "enabled": "false"}]}), stderr="")
            return result

        with mock.patch.object(install_plugin, "run", side_effect=malformed_cli):
            with self.assertRaisesRegex(install_plugin.InstallError, "did not confirm EasyViz"):
                self.install()
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.target.exists())
        self.assertEqual(self.catalog.read_bytes(), self.original_bytes)

    def test_partial_cache_backup_failure_keeps_previous_cache_and_restores_source(self):
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.install()
        cache_content = install_plugin.content_hashes(self.cache)
        source_content = install_plugin.content_hashes(self.target)
        catalog_bytes = self.catalog.read_bytes()
        copytree = shutil.copytree
        (self.source / "README.md").write_text("new selected readme\n")

        def interrupted_copy(source, target, *args, **kwargs):
            if ".cache-backup-" in Path(target).name:
                Path(target).mkdir()
                (Path(target) / "partial.txt").write_text("partial backup")
                raise OSError("cache backup interrupted")
            return copytree(source, target, *args, **kwargs)

        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            with mock.patch.object(install_plugin.shutil, "copytree", side_effect=interrupted_copy):
                with self.assertRaisesRegex(OSError, "cache backup interrupted"):
                    self.install()
        self.assertEqual(install_plugin.content_hashes(self.cache), cache_content)
        self.assertEqual(install_plugin.content_hashes(self.target), source_content)
        self.assertEqual(self.catalog.read_bytes(), catalog_bytes)
        self.assertEqual(list(self.target.parent.glob("easyviz.cache-backup-*")), [])

    def test_installation_inside_source_is_rejected_before_recursive_copy(self):
        nested_home = self.source / "nested-home"
        with mock.patch.object(install_plugin, "run") as cli:
            with self.assertRaisesRegex(install_plugin.InstallError, "outside the selected source package"):
                install_plugin.install(self.source, nested_home, nested_home / ".codex", None)
            cli.assert_not_called()
        self.assertFalse(nested_home.exists())
        self.assertEqual(self.catalog.read_bytes(), self.original_bytes)

    def test_catalog_edit_in_commit_window_aborts_and_preserves_external_bytes(self):
        atomic_write = install_plugin.atomic_write
        concurrent_bytes = None

        def write_with_external_edit(path, content, **kwargs):
            nonlocal concurrent_bytes
            if path == self.catalog:
                catalog = json.loads(self.catalog.read_text())
                catalog["plugins"].append({"name": "added-before-replace", "keep": True})
                concurrent_bytes = json.dumps(catalog).encode()
                self.catalog.write_bytes(concurrent_bytes)
            return atomic_write(path, content, **kwargs)

        with mock.patch.object(install_plugin, "atomic_write", side_effect=write_with_external_edit):
            with mock.patch.object(install_plugin, "run") as cli:
                with self.assertRaisesRegex(install_plugin.InstallError, "marketplace changed before commit"):
                    self.install()
                cli.assert_not_called()
        self.assertEqual(self.catalog.read_bytes(), concurrent_bytes)
        self.assertFalse(self.target.exists())

    def test_process_lock_blocks_concurrent_install_and_releases_after_exit(self):
        scripts = str(Path(__file__).resolve().parents[1] / "scripts")
        program = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from install_plugin import installation_lock
with installation_lock(Path(sys.argv[2])):
    print('locked', flush=True)
    sys.stdin.readline()
"""
        process = subprocess.Popen([sys.executable, "-c", program, scripts, str(self.codex_home)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            with mock.patch.object(install_plugin, "run") as cli:
                with self.assertRaisesRegex(install_plugin.InstallError, "Another EasyViz installation is running"):
                    self.install()
                cli.assert_not_called()
            self.assertEqual(self.catalog.read_bytes(), self.original_bytes)
            self.assertFalse(self.target.exists())
            output, errors = process.communicate("release\n", timeout=10)
            self.assertEqual(process.returncode, 0, errors)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            self.assertEqual(self.install()["status"], "installed")

    def test_shared_catalog_and_client_lock_path_is_acquired_only_once(self):
        self.codex_home = self.home / ".agents"
        self.target = self.codex_home / "plugins/easyviz"
        with mock.patch.object(install_plugin, "run", side_effect=self.fake_cli):
            result = self.install()
        self.assertEqual(result["status"], "installed")
        self.assertEqual(json.loads(self.catalog.read_text())["plugins"][0], self.other)
        self.assertTrue(Path(result["installed_path"]).is_relative_to(self.codex_home))

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
