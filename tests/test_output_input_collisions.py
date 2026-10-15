"""Reject accidental source replacement before any attempted render mutates files."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def load(name):
    loader = importlib.util.spec_from_file_location("output_collision_" + name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


core = load("render")
RECIPES = {name: load(name) for name in
           ("paired_plot", "replicate_plot", "ecdf_plot", "interval_plot", "timecourse_plot", "annotated_matrix")}


class OutputInputCollisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-output-input-")
        self.root = Path(self.temp.name)
        self.out = self.root / "output"
        self.out.mkdir()
        self.source = self.root / "source.csv"
        self.source.write_bytes(b"group,value\nA,01\nA,2\nA,3\nB,4\nB,5\nB,6\n")
        self.spec = {"chart": "distribution", "fields": {"group": "group", "value": "value"},
                     "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
                     "formats": ["svg"], "options": {"kind": "box"}}

    def tearDown(self):
        core.plt.close("all")
        self.temp.cleanup()

    def test_in_place_augmented_csv_is_rejected_without_rewriting_source(self):
        source = self.out / "plotting-data.csv"
        source.write_bytes(self.source.read_bytes())
        before = source.read_bytes()
        with self.assertRaisesRegex(core.OutputCollisionError, "would replace data"):
            core.render(source, self.spec, self.out)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(set(path.name for path in self.out.iterdir()), {"plotting-data.csv"})

    def test_reserved_specification_and_default_spec_collision_preserve_bytes(self):
        for name in ("qa.json", "settings.json", "elements.json"):
            with self.subTest(name=name):
                spec = self.out / name
                spec.write_text(json.dumps(self.spec))
                before = spec.read_bytes()
                with self.assertRaises(core.OutputCollisionError):
                    core.render_spec_file(self.source, spec, self.out)
                self.assertEqual(spec.read_bytes(), before)
                spec.unlink()
        source = self.out / "plot-spec.json"
        source.write_bytes(self.source.read_bytes())
        with self.assertRaises(core.OutputCollisionError):
            core.render(source, self.spec, self.out)
        self.assertEqual(source.read_bytes(), self.source.read_bytes())

    def test_linked_output_aliases_do_not_overwrite_external_input(self):
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                destination = self.out / "plotting-data.csv"
                if kind == "symlink":
                    destination.symlink_to(self.source)
                else:
                    os.link(self.source, destination)
                before = self.source.read_bytes()
                with self.assertRaises(core.OutputCollisionError):
                    core.render(self.source, self.spec, self.out)
                self.assertEqual(self.source.read_bytes(), before)
                self.assertFalse((self.out / "qa.json").exists())
                destination.unlink()

    def test_profile_and_analysis_companions_are_checked_before_qa_write(self):
        profile = self.out / "settings.json"
        profile.write_text('{"profile": "preserve me"}')
        spec = deepcopy(self.spec)
        spec.update(profile=str(profile), panel="a")
        with self.assertRaisesRegex(core.OutputCollisionError, "figure profile"):
            core.render(self.source, spec, self.out)
        self.assertEqual(profile.read_text(), '{"profile": "preserve me"}')
        profile.unlink()
        folder = self.out / "adopted-analysis"
        folder.mkdir()
        companion = folder / "summary.csv"
        companion.write_bytes(b"preserve,original\n1,2\n")
        spec = deepcopy(self.spec)
        spec["statistics"] = {"analysis": {"results_file": str(folder / "results.json")}}
        with self.assertRaisesRegex(core.OutputCollisionError, "analysis (result|companion)"):
            core.render(self.source, spec, self.out)
        self.assertEqual(companion.read_bytes(), b"preserve,original\n1,2\n")
        self.assertFalse((self.out / "qa.json").exists())

    def test_linked_output_cannot_replace_executing_runtime(self):
        runtime = SCRIPTS / "render.py"
        before = runtime.read_bytes()
        (self.out / "qa.json").symlink_to(runtime)
        with self.assertRaisesRegex(core.OutputCollisionError, "runtime source render.py"):
            core.render(self.source, self.spec, self.out)
        self.assertEqual(runtime.read_bytes(), before)

    def test_all_focused_recipes_reject_before_preparation(self):
        source = self.out / "plotting-data.csv"
        before = self.source.read_bytes()
        source.write_bytes(before)
        for name, recipe in RECIPES.items():
            with self.subTest(recipe=name):
                with self.assertRaisesRegex(recipe.core.OutputCollisionError, "would replace data"):
                    recipe.render(source, {}, self.out)
                self.assertEqual(source.read_bytes(), before)
                self.assertFalse((self.out / "qa.json").exists())

    def test_annotated_auxiliary_input_is_protected(self):
        auxiliary = self.out / "matrix-cells.csv"
        auxiliary.write_text("key,state\na,test\n")
        recipe = RECIPES["annotated_matrix"]
        with self.assertRaisesRegex(recipe.core.OutputCollisionError, "row_metadata"):
            recipe.render(self.source, {}, self.out, row_metadata=auxiliary)
        self.assertEqual(auxiliary.read_text(), "key,state\na,test\n")
        self.assertFalse((self.out / "qa.json").exists())

    def test_cli_does_not_corrupt_spec_before_parsing_or_error_reporting(self):
        spec_path = self.out / "qa.json"
        for name in ("render", *RECIPES):
            with self.subTest(recipe=name):
                raw = b"invalid json that is still the user's original specification\n"
                spec_path.write_bytes(raw)
                result = subprocess.run([sys.executable, str(SCRIPTS / f"{name}.py"), "--data", str(self.source),
                                         "--spec", str(spec_path), "--out", str(self.out)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("would replace specification", result.stderr)
                self.assertEqual(spec_path.read_bytes(), raw)

    def test_saved_spec_and_ordinary_source_in_output_directory_remain_supported(self):
        source = self.out / "original.csv"
        source.write_bytes(self.source.read_bytes())
        spec_path = self.out / "plot-spec.json"
        spec_path.write_text(json.dumps(self.spec))
        source_before, spec_before = source.read_bytes(), spec_path.read_bytes()
        qa = core.render_spec_file(source, spec_path, self.out)
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(source.read_bytes(), source_before)
        self.assertEqual(spec_path.read_bytes(), spec_before)


if __name__ == "__main__":
    unittest.main()
