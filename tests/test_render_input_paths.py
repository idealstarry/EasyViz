"""Input paths keep their original base before generated specs are relocated."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def load(name):
    loader = importlib.util.spec_from_file_location("input_path_" + name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


core = load("render")
analysis = load("analyze")


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class RenderInputPathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="easyviz-render-input-paths-")
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.csv"
        self.source.write_text("x,y\n1,2\n2,3\n3,2\n")
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "y"}, "formats": ["svg"]}
        self.profile = self.root / "profile.json"
        self.profile_bytes = json.dumps({"version": 1,
            "layout": {"font": "DejaVu Sans", "font_size_pt": 9, "line_width_pt": .7, "dpi": 100},
            "panels": {"A": {"width_mm": 100, "height_mm": 80}}}).encode()
        self.profile.write_bytes(self.profile_bytes)
        (self.root / "elsewhere").mkdir()

    def tearDown(self):
        core.plt.close("all")
        self.temporary.cleanup()

    def test_generated_spec_freezes_cwd_relative_declared_and_explicit_profiles(self):
        for route in ("declared", "override"):
            with self.subTest(route=route):
                spec, options = deepcopy(self.spec), {}
                if route == "declared":
                    spec.update(profile=self.profile.name, panel="A")
                else:
                    options.update(profile=self.profile.name, panel="A")
                original = deepcopy(spec)
                out = self.root / route
                with working_directory(self.root):
                    qa = core.render(self.source, spec, out, **options)
                self.assertEqual(qa["status"], "pass")
                self.assertEqual(spec, original)
                saved_path = out / "plot-spec.json"
                saved = json.loads(saved_path.read_text())
                self.assertEqual(saved["profile"], str(self.profile.resolve()))
                self.assertEqual(saved["panel"], "A")
                with working_directory(self.root / "elsewhere"):
                    replay = core.render_spec_file(self.source, saved_path, self.root / (route + "-replay"))
                self.assertEqual(replay["status"], "pass")
                self.assertEqual(self.profile.read_bytes(), self.profile_bytes)

    def test_generated_spec_freezes_cwd_relative_adopted_analysis_without_recomputing(self):
        source = self.root / "analysis-source.csv"
        source.write_text("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        plan = {"schema_version": 1, "question": "Compare the declared specimen endpoint",
            "design": {"unit": "id", "unit_definition": "one independent specimen", "structure": "independent", "confirmed": True},
            "missing_policy": "error", "comparisons": [{"name": "primary", "method": "welch",
            "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]}]}
        report = analysis.analyze(source, plan, self.root / "analysis")
        result = self.root / "analysis/results.json"
        spec = {"chart": "distribution", "fields": {"group": "group", "value": "value", "unit": "id"},
            "formats": ["svg"], "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
            "options": {"kind": "box"}, "colors": {"A": "#2687bd", "B": "#ed8b43"}, "statistics": {"analysis": {"schema_version": 1,
            "results_file": "analysis/results.json", "results_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
            "comparison": "primary", "pvalue": "raw", "population": "all"}, "annotate": False}}
        original = deepcopy(spec)
        out = self.root / "analysis-panel"
        with patch("scipy.stats.ttest_ind", side_effect=AssertionError("Rendering must retain adopted inference")):
            with working_directory(self.root):
                qa = core.render(source, spec, out)
            self.assertEqual(qa["status"], "pass")
            saved_path = out / "plot-spec.json"
            saved = json.loads(saved_path.read_text())
            self.assertEqual(saved["statistics"]["analysis"]["results_file"], str(result.resolve()))
            with working_directory(self.root / "elsewhere"):
                replay = core.render_spec_file(source, saved_path, self.root / "analysis-replay")
        self.assertEqual(replay["status"], "pass")
        self.assertEqual(spec, original)
        adopted = json.loads((out / "stats.json").read_text())
        self.assertEqual(adopted["pvalue"], report["comparisons"][0]["pvalue"])
        self.assertFalse(adopted["adoption"]["recomputed"])

    def test_explicit_profile_guard_uses_cwd_with_a_spec_in_another_directory(self):
        profile = self.root / "settings.json"
        profile.write_bytes(self.profile_bytes)
        spec_path = self.root / "specs/spec.json"
        spec_path.parent.mkdir()
        spec_path.write_text(json.dumps(self.spec))
        with working_directory(self.root):
            for operation in (
                lambda: core.render(self.source, self.spec, self.root, profile=profile.name, panel="A", spec_path=spec_path),
                lambda: core.render_spec_file(self.source, spec_path, self.root, profile=profile.name, panel="A"),
            ):
                with self.assertRaisesRegex(core.OutputCollisionError, "figure profile"):
                    operation()
                self.assertEqual(profile.read_bytes(), self.profile_bytes)
                self.assertFalse((self.root / "qa.json").exists())
            cli = subprocess.run([sys.executable, str(SCRIPTS / "render.py"), "--data", str(self.source),
                "--spec", str(spec_path), "--out", str(self.root), "--profile", profile.name, "--panel", "A"],
                capture_output=True, text=True)
        self.assertEqual(cli.returncode, 2, cli.stderr)
        self.assertIn("would replace figure profile", cli.stderr)
        self.assertEqual(profile.read_bytes(), self.profile_bytes)
        self.assertFalse((self.root / "qa.json").exists())

    def test_declared_profile_is_protected_even_when_an_override_disagrees(self):
        profile = self.root / "qa.json"
        profile.write_bytes(self.profile_bytes)
        spec = {**self.spec, "profile": str(profile), "panel": "A"}
        with self.assertRaisesRegex(core.OutputCollisionError, "figure profile"):
            core.render(self.source, spec, self.root, profile=self.profile, panel="A")
        self.assertEqual(profile.read_bytes(), self.profile_bytes)


if __name__ == "__main__":
    unittest.main()
