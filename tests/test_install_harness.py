"""Check Harness skill installation preserves files and rolls back as a unit."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install_harness


class HarnessInstallerTests(unittest.TestCase):
    def setUp(self):
        # Reuse the complete portable-package fixture without running Codex.
        from test_install_plugin import InstallerTests
        fixture = InstallerTests(methodName="test_update_refreshes_the_actual_cached_manifest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.source = fixture.root, fixture.source
        self.home = self.root / "dsh"
        self.target = self.home / "skills"

    def install(self, **kwargs):
        return install_harness.install(self.source, dsh_home=self.home, **kwargs)

    def test_all_three_skills_install_without_changing_profile_or_other_skills(self):
        unrelated = self.target / "user-skill" / "SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("user instructions")
        profile = self.home / "profiles/web/cordis.patch.yml"
        profile.parent.mkdir(parents=True)
        profile.write_text("existing profile")
        result = self.install()
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["discovery"], "not_checked")
        self.assertEqual(len(result["paths"]), 3)
        for name in install_harness.SKILL_NAMES:
            self.assertEqual((self.target / name / "SKILL.md").read_bytes(),
                             (self.source / "skills" / name / "SKILL.md").read_bytes())
        self.assertEqual(unrelated.read_text(), "user instructions")
        self.assertEqual(profile.read_text(), "existing profile")

    def test_owned_same_version_update_replaces_every_bundle(self):
        self.install()
        for name in install_harness.SKILL_NAMES:
            (self.source / "skills" / name / "SKILL.md").write_text("updated " + name)
        self.install()
        for name in install_harness.SKILL_NAMES:
            self.assertEqual((self.target / name / "SKILL.md").read_text(), "updated " + name)

    def test_unowned_existing_skill_is_preserved_before_any_install(self):
        existing = self.target / "easyviz" / "SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("custom instructions")
        with self.assertRaisesRegex(install_harness.InstallError, "not managed"):
            self.install()
        self.assertEqual(existing.read_text(), "custom instructions")
        self.assertEqual(list(self.target.iterdir()), [existing.parent])

    def test_wrong_skill_ownership_marker_is_not_accepted(self):
        self.install()
        marker = self.target / "easyviz" / install_harness.OWNER_FILE
        owner = json.loads(marker.read_text())
        owner["skill"] = "unrelated"
        marker.write_text(json.dumps(owner))
        with self.assertRaisesRegex(install_harness.InstallError, "not managed"):
            self.install()
        self.assertEqual(json.loads(marker.read_text())["skill"], "unrelated")

    def test_symlink_root_or_bundle_never_modifies_external_files(self):
        external = self.root / "external"
        external.mkdir()
        (external / "keep").write_text("untouched")
        self.home.mkdir()
        self.target.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(install_harness.InstallError, "symlink"):
            self.install()
        self.target.unlink()
        self.target.mkdir()
        (self.target / "easyviz").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(install_harness.InstallError, "symlink"):
            self.install()
        self.assertEqual((external / "keep").read_text(), "untouched")

    def test_symlink_inside_owned_bundle_is_rejected(self):
        self.install()
        external = self.root / "private.txt"
        external.write_text("untouched")
        (self.target / "easyviz" / "private.txt").symlink_to(external)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.install()
        self.assertEqual(external.read_text(), "untouched")

    def test_source_overlap_is_rejected_without_creating_target(self):
        nested = self.source / "dsh"
        with self.assertRaisesRegex(install_harness.InstallError, "overlap"):
            install_harness.install(self.source, dsh_home=nested)
        self.assertFalse(nested.exists())

    def test_copy_failure_keeps_existing_installation(self):
        self.install()
        before = {name: (self.target / name / "SKILL.md").read_bytes()
                  for name in install_harness.SKILL_NAMES}
        with mock.patch.object(install_harness.shutil, "copytree", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.install()
        for name, contents in before.items():
            self.assertEqual((self.target / name / "SKILL.md").read_bytes(), contents)
        self.assertFalse(list(self.target.glob(".easyviz-staging-*")))

    def test_partial_commit_restores_all_previous_bundles(self):
        self.install()
        before = {name: (self.target / name / "SKILL.md").read_bytes()
                  for name in install_harness.SKILL_NAMES}
        original_replace = os.replace
        def replace_with_failure(source, destination):
            if (Path(source).parent.name == "new"
                    and Path(destination).name == "easyviz-reference-reader"):
                raise OSError("interrupted commit")
            return original_replace(source, destination)
        with mock.patch.object(install_harness.os, "replace", side_effect=replace_with_failure):
            with self.assertRaisesRegex(OSError, "interrupted commit"):
                self.install()
        for name, contents in before.items():
            self.assertEqual((self.target / name / "SKILL.md").read_bytes(), contents)

    def test_failed_first_commit_leaves_no_half_installed_skills(self):
        with mock.patch.object(install_harness, "verify_cached_content", side_effect=ValueError("bad copy")):
            with self.assertRaisesRegex(ValueError, "bad copy"):
                self.install()
        self.assertEqual([p.name for p in self.target.iterdir()], [".easyviz-install.lock"])

    def test_failed_rollback_retains_previous_files_for_recovery(self):
        self.install()
        previous = (self.target / "easyviz" / "SKILL.md").read_bytes()
        original_replace = os.replace
        def replace_with_failure(source, destination):
            if Path(source).parent.name == "backups":
                raise OSError("cannot restore yet")
            return original_replace(source, destination)
        with mock.patch.object(install_harness.os, "replace", side_effect=replace_with_failure):
            with mock.patch.object(install_harness, "verify_cached_content", side_effect=ValueError("bad copy")):
                with self.assertRaisesRegex(install_harness.InstallError, "retained at"):
                    self.install()
        staging = list(self.target.glob(".easyviz-staging-*"))
        self.assertEqual(len(staging), 1)
        self.assertEqual((staging[0] / "backups/easyviz/SKILL.md").read_bytes(), previous)

    def test_rollback_safety_error_keeps_backups_and_restores_remaining_skills(self):
        self.install()
        previous = {name: (self.target / name / "SKILL.md").read_bytes()
                    for name in install_harness.SKILL_NAMES}
        original_remove = install_harness.remove_owned
        def remove_with_safety_error(path, boundary):
            if path.name == "easyviz-figure-reviewer":
                raise install_harness.InstallError("installation boundary changed")
            return original_remove(path, boundary)
        with mock.patch.object(install_harness, "remove_owned", side_effect=remove_with_safety_error):
            with mock.patch.object(install_harness, "verify_cached_content", side_effect=ValueError("bad copy")):
                with self.assertRaisesRegex(install_harness.InstallError, "retained at"):
                    self.install()
        for name in install_harness.SKILL_NAMES[:2]:
            self.assertEqual((self.target / name / "SKILL.md").read_bytes(), previous[name])
        staging = list(self.target.glob(".easyviz-staging-*"))
        self.assertEqual(len(staging), 1)
        self.assertEqual((staging[0] / "backups/easyviz-figure-reviewer/SKILL.md").read_bytes(),
                         previous["easyviz-figure-reviewer"])

    def test_project_and_user_targets_remain_independent(self):
        project = self.root / "project"
        project.mkdir()
        result = install_harness.install(self.source, project=project)
        self.assertEqual(Path(result["target"]), project / ".dsh" / "skills")
        self.assertFalse(self.home.exists())

    def test_environment_home_and_explicit_override(self):
        with mock.patch.dict(os.environ, {"DSH_HOME": str(self.home)}):
            self.assertEqual(install_harness.target_directory(), self.target)
            explicit = self.root / "explicit"
            self.assertEqual(install_harness.target_directory(dsh_home=explicit), explicit / "skills")
        with mock.patch.object(Path, "home", return_value=self.root / "user"):
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(install_harness.target_directory(), self.root / "user/.dsh/skills")

    def test_running_installation_lock_refuses_concurrent_update(self):
        from install_plugin import installation_lock
        with installation_lock(self.target, relative=".easyviz-install.lock"):
            with self.assertRaisesRegex(install_harness.InstallError, "Another EasyViz"):
                self.install()

    def test_cli_rejects_both_scopes_before_creating_files(self):
        script = Path(install_harness.__file__)
        result = subprocess.run([sys.executable, str(script), "--source", str(self.source),
                                 "--project", str(self.root / "project"),
                                 "--dsh-home", str(self.home)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.home.exists())


if __name__ == "__main__":
    unittest.main()
