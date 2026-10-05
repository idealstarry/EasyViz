"""Actual mapped exports bind consumed helpers through review and restoration.

Recorded attestations are fixtures; these tests do not claim images were opened.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_create_review as base

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
from figure_workbench import FigureWorkbench, WorkbenchError
from apply_figure_requests import accept_attempt, restore_attempt


class SourceAuxiliaryContinuityTests(unittest.TestCase):
    tearDown = base.CreateReviewTests.tearDown
    read = staticmethod(base.CreateReviewTests.read)
    write = staticmethod(base.CreateReviewTests.write)
    stage = base.CreateReviewTests.stage
    recorded_fixture = base.CreateReviewTests.recorded_fixture

    def setUp(self):
        base.CreateReviewTests.setUp(self)
        self.runtime = self.root / "copied-runtime"
        self.runtime.mkdir()
        for path in SCRIPTS.glob("*.py"):
            shutil.copy2(path, self.runtime / path.name)
        self.figure = self.root / "actual-copied-output"
        result = subprocess.run([sys.executable, "-I", "-B", str(self.runtime / "render.py"),
                                 "--data", str(self.data), "--spec", str(self.spec_path),
                                 "--out", str(self.figure), "--track", "create"],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_changed_consumed_helper_blocks_workbench_acceptance_and_recorded_review(self):
        state = FigureWorkbench(self.figure).state()
        self.assertTrue(state["manifest_valid"] and state["provenance_valid"])
        self.assertIs(state["source_current"], True)
        settings = self.read(self.figure / "settings.json")
        declared = {role: record for role, record in settings["source_bindings"].items()
                    if role not in ("data_file", "spec_file", "source_script")}
        self.assertEqual(state["input"]["auxiliary_inputs"], declared)
        self.assertIn("helper:observation_clipping.py", declared)
        staged = self.stage()
        self.recorded_fixture(staged)
        self.assertEqual(base.gate.check(staged["packet"])["gate_status"], "recorded")
        artifacts = {path.name: path.read_bytes() for path in self.figure.glob("panel.*")}
        helper = self.runtime / "legend_layout.py"
        helper.write_bytes(helper.read_bytes() + b"\n# isolated late dependency replacement\n")
        self.assertIs(FigureWorkbench(self.figure).state()["source_current"], False)
        with self.assertRaisesRegex(WorkbenchError, "[Ss]ource"):
            accept_attempt(self.figure, validation="Isolated provenance regression only.")
        self.assertFalse((self.figure / "accepted-snapshot").exists())
        self.assertEqual(artifacts, {path.name: path.read_bytes() for path in self.figure.glob("panel.*")})
        report = base.gate.check(staged["packet"])
        self.assertEqual(report["gate_status"], "blocked")
        self.assertIn("source_provenance", "\n".join(report["errors"]))
        self.assertEqual(base.gate.snapshot(self.figure)["measured_checks"]["source_provenance"]["status"], "failed")

    def test_all_declared_helpers_restore_after_original_code_data_and_spec_are_deleted(self):
        before = FigureWorkbench(self.figure).state()
        source_roles = self.read(self.figure / "settings.json")["source_bindings"]
        original_exports = {path.name: path.read_bytes() for path in self.figure.glob("panel.*")}
        accept_attempt(self.figure, validation="Isolated export/source-byte restoration regression only.")
        shutil.rmtree(self.runtime)
        self.data.unlink()
        self.spec_path.unlink()
        restored = self.root / "restored"
        restore_attempt(self.figure, out=restored)
        after = FigureWorkbench(restored).state()
        self.assertIs(after["source_current"], True)
        self.assertTrue(after["manifest_valid"] and after["provenance_valid"])
        self.assertEqual(after["version"], before["version"])
        self.assertEqual(original_exports, {path.name: path.read_bytes() for path in restored.glob("panel.*")})
        bindings = self.read(restored / "settings.json")["source_bindings"]
        self.assertEqual(set(bindings), set(source_roles))
        self.assertTrue(all(Path(record["path"]).is_file() and Path(record["path"]).is_relative_to(restored)
                            for record in bindings.values()))
        self.assertEqual(base.gate.snapshot(restored, caption=self.caption)["measured_checks"]["source_provenance"]["status"], "passed")

    def test_settings_only_auxiliary_claims_block_missing_source(self):
        # A genuine older map shape can rely on complete captured settings for
        # an auxiliary declaration; no element identity is inferred or changed.
        map_path = self.figure / "elements.json"
        mapping = self.read(map_path)
        mapping["input"].pop("auxiliary_inputs")
        mapping["version"].pop("auxiliary_inputs_sha256")
        self.write(map_path, mapping)
        staged = self.stage()
        self.recorded_fixture(staged)
        self.assertEqual(base.gate.check(staged["packet"])["gate_status"], "recorded")
        (self.runtime / "legend_layout.py").unlink()
        snapshot = base.gate.snapshot(self.figure, caption=self.caption)
        self.assertEqual(snapshot["measured_checks"]["source_provenance"]["status"], "not_checked")
        self.assertEqual(base.gate.check(staged["packet"])["gate_status"], "blocked")

    def test_primary_only_legacy_provenance_keeps_existing_support(self):
        map_path = self.figure / "elements.json"
        mapping = self.read(map_path)
        mapping["input"].pop("auxiliary_inputs")
        mapping["version"].pop("auxiliary_inputs_sha256")
        self.write(map_path, mapping)
        settings_path = self.figure / "settings.json"
        settings = self.read(settings_path)
        settings.pop("source_bindings")
        self.write(settings_path, settings)
        snapshot = base.gate.snapshot(self.figure, caption=self.caption)
        self.assertEqual(set(snapshot["source_bindings"]), {"data_file", "source_script", "spec_file", "figure_profile"})
        self.assertEqual(snapshot["measured_checks"]["source_provenance"]["status"], "passed")
        staged = self.stage()
        self.recorded_fixture(staged)
        self.assertEqual(base.gate.check(staged["packet"])["gate_status"], "recorded")


if __name__ == "__main__":
    unittest.main()
