"""Check component integrity, replicate-level SD and truthful export failures."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image
from pypdf import PdfReader

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/replicate_plot.py"
loader = importlib.util.spec_from_file_location("easyviz_replicate_tests", SCRIPT)
replicate = importlib.util.module_from_spec(loader)
loader.loader.exec_module(replicate)


class ReplicatePlotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="easyviz-replicate-")
        self.root = Path(self.temporary.name)
        self.spec = {"chart": "replicate", "fields": {"condition": "arm", "unit": "person", "value": "amount", "component": "part"},
                     "options": {"mode": "stacked"}, "colors": {"X": "#0072B2", "Y": "#D55E00"},
                     "layout": {"width_mm": 95, "height_mm": 75, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100},
                     "formats": ["png"], "labels": {"y": "Amount (units)"}}
        self.text = "arm,person,part,amount,unused\nNA,001,X,10,not n\nNA,001,Y,0,not n\nNA,002,X,0,not n\nNA,002,Y,10,not n\nnull,001,X,1,not n\nnull,001,Y,2,not n\nnull,002,X,4,not n\nnull,002,Y,3,not n\n"

    def tearDown(self):
        replicate.plt.close("all")
        self.temporary.cleanup()

    def source(self, text=None):
        path = self.root / "source.csv"
        path.write_text(self.text if text is None else text)
        return path

    def draw(self, source, spec=None):
        spec = deepcopy(self.spec if spec is None else spec)
        spec.setdefault("layout", {}).setdefault("auto_fit", True)
        data = replicate.prepare(source, spec)
        layout, typography, rc = replicate.core.setup(spec)
        with replicate.plt.rc_context(rc):
            fig, colors = replicate.draw(data, spec, layout, typography)
            fig.canvas.draw()
        return data, fig, colors

    def test_stacked_sd_uses_unit_totals_not_component_sd(self):
        source = self.source()
        data, fig, _ = self.draw(source)
        artists = fig._easyviz_replicate_artists
        self.assertEqual([point["value"] for point in artists["points"]], [10, 10, 3, 7])
        # Anticorrelated components have nonzero component SD but constant total.
        self.assertEqual(artists["intervals"][0]["artist"].get_segments()[0].tolist(), [[0, 10], [0, 10]])
        self.assertAlmostEqual(artists["intervals"][1]["sample_sd"], 2 ** .5 * 2)
        self.assertEqual([bar["bottom"] for bar in artists["bars"]], [0, 5, 0, 2.5])
        self.assertEqual(replicate.audit_source_artists(source, self.spec, fig)["status"], "pass")
        self.assertEqual(data["arm"].unique().tolist(), ["NA", "null"])
        self.assertEqual(data["person"].unique().tolist(), ["001", "002"])
        self.assertEqual(data["unused"].unique().tolist(), ["not n"])

    def test_grouped_retains_raw_zeros_and_component_sd(self):
        source, spec = self.source(), deepcopy(self.spec)
        spec["options"]["mode"] = "grouped"
        _, fig, _ = self.draw(source, spec)
        artists = fig._easyviz_replicate_artists
        self.assertEqual(len(artists["points"]), 8)
        self.assertEqual(sum(point["value"] == 0 for point in artists["points"]), 2)
        self.assertAlmostEqual(artists["intervals"][0]["sample_sd"], 50 ** .5)
        self.assertTrue(all(bar["bottom"] == 0 for bar in artists["bars"]))
        self.assertEqual(replicate.audit_source_artists(source, spec, fig)["status"], "pass")

    def test_supplied_ratio_and_declared_states_are_preserved(self):
        source = self.source("arm,person,amount,state,numerator,denominator\nA,01,.01,weak,900,1\nA,02,.02,weak,800,1\nB,01,4,good,1,900\nB,02,8,good,1,800\n")
        spec = deepcopy(self.spec)
        spec["fields"].pop("component")
        spec["fields"]["state"] = "state"
        spec.pop("colors")
        spec["options"].update(mode="summary", state_hatches={"good": "", "weak": "///"})
        data, fig, _ = self.draw(source, spec)
        self.assertEqual([point["value"] for point in fig._easyviz_replicate_artists["points"]], [.01, .02, 4, 8])
        self.assertEqual([bar["artist"].get_hatch() for bar in fig._easyviz_replicate_artists["bars"]], ["///", ""])
        self.assertEqual(data["numerator"].tolist(), ["900", "800", "1", "1"])
        self.assertFalse(replicate.audit_source_artists(source, spec, fig)["ratios_derived"])
        self.assertEqual(replicate.audit_source_artists(source, spec, fig)["status"], "pass")

    def test_component_missing_duplicate_negative_and_bad_sd_fail(self):
        for text in ["\n".join(self.text.splitlines()[:-1]) + "\n", self.text + "NA,001,X,10,not n\n", self.text.replace("X,10", "X,-10"), self.text.replace("X,10", "X,NaN"), self.text.replace("X,10", "X,"), "arm,person,part,amount\nA,1,X,1\nA,1,Y,2\n"]:
            with self.subTest(text=text), self.assertRaises(replicate.SpecError):
                replicate.prepare(self.source(text), self.spec)
        spec = deepcopy(self.spec)
        spec["options"]["uncertainty"] = "none"
        self.assertEqual(len(replicate.prepare(self.source("arm,person,part,amount\nA,1,X,1\nA,1,Y,2\n"), spec)), 2)

    def test_input_reordering_and_renamed_roles_do_not_change_points(self):
        source, spec = self.source(), deepcopy(self.spec)
        spec["order"] = {"condition": ["null", "NA"], "component": ["Y", "X"]}
        _, first, _ = self.draw(source, spec)
        expected = [(point["condition"], point["unit"], point["x"], point["value"]) for point in first._easyviz_replicate_artists["points"]]
        body = self.text.splitlines()
        source.write_text(body[0] + "\n" + "\n".join(reversed(body[1:])) + "\n")
        _, second, _ = self.draw(source, spec)
        actual = [(point["condition"], point["unit"], point["x"], point["value"]) for point in second._easyviz_replicate_artists["points"]]
        self.assertEqual(actual, expected)
        source.write_text(source.read_text().replace("arm,person,part,amount,unused", "cohort,sample,piece,score,unused"))
        spec["fields"] = {"condition": "cohort", "unit": "sample", "component": "piece", "value": "score"}
        _, renamed, _ = self.draw(source, spec)
        self.assertEqual(replicate.audit_source_artists(source, spec, renamed)["status"], "pass")

    def test_actual_artist_mutations_are_detected(self):
        source = self.source()
        _, fig, _ = self.draw(source)
        artists = fig._easyviz_replicate_artists
        artists["bars"][0]["artist"].set_height(99)
        artists["bars"][1]["artist"].set_facecolor("green")
        artists["intervals"][0]["artist"].set_segments([[[0, 1], [0, 19]]])
        artists["points"][0]["artist"].set_offsets([[0, 99]])
        artists["points"][1]["artist"].remove()
        codes = {issue["code"] for issue in replicate.audit_source_artists(source, self.spec, fig)["issues"]}
        self.assertTrue({"bar_mean_or_base_mismatch", "bar_color_mismatch", "sample_sd_endpoint_mismatch", "raw_observation_coordinate_mismatch", "unaccounted_or_removed_data_artist"} <= codes)

    def test_fixed_dimensions_fonts_exports_and_statistics(self):
        source, spec = self.source(), deepcopy(self.spec)
        spec["formats"] = ["pdf", "png", "svg", "tiff"]
        out = self.root / "out"
        qa = replicate.render(source, spec, out)
        self.assertTrue(qa["valid_outputs"])
        self.assertEqual(qa["source_to_artist_audit"]["raw_points"], 4)
        page = PdfReader(out / "panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) / 72 * 25.4, 95, places=5)
        self.assertAlmostEqual(float(page.mediabox.height) / 72 * 25.4, 75, places=5)
        for extension in ("png", "tiff"):
            with Image.open(out / f"panel.{extension}") as image:
                self.assertEqual(image.size, (374, 295))
        stats = json.loads((out / "stats.json").read_text())
        self.assertEqual(stats["sd_ddof"], 1)
        self.assertFalse(stats["tests_performed"])
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")

    def test_failed_and_clipped_runs_invalidate_previous_exports(self):
        source, out = self.source(), self.root / "out"
        replicate.render(source, self.spec, out)
        source.write_text("arm,person,part,amount\nA,1,X,1\n")
        with self.assertRaises(replicate.SpecError):
            replicate.render(source, self.spec, out)
        self.assertFalse(json.loads((out / "qa.json").read_text())["valid_outputs"])
        self.assertEqual(json.loads((out / "qa.json").read_text())["status"], "failed")
        source = self.source("arm,person,amount\nA,1,0\nA,2,4\n")
        spec = deepcopy(self.spec)
        spec["fields"].pop("component")
        spec.pop("colors")
        spec["options"].update(mode="summary", uncertainty="none", y_limits=[0, 5])
        with self.assertRaises(replicate.SpecError):
            replicate.render(source, spec, out)
        self.assertEqual(json.loads((out / "qa.json").read_text())["status"], "needs_revision")
        self.assertFalse(json.loads((out / "qa.json").read_text())["valid_outputs"])
        broken = self.root / "spec.json"
        broken.write_text("{broken")
        result = subprocess.run([sys.executable, str(SCRIPT), "--data", str(source), "--spec", str(broken), "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads((out / "qa.json").read_text())["status"], "failed")

    def test_source_change_during_export_is_not_validated(self):
        source, out = self.source(), self.root / "changed"
        export = replicate.core.export
        def modifying(*args, **kwargs):
            result = export(*args, **kwargs)
            source.write_text(source.read_text().replace("X,10", "X,11"))
            return result
        with mock.patch.object(replicate.core, "export", side_effect=modifying), self.assertRaises(replicate.SpecError):
            replicate.render(source, self.spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertIn("source_changed_during_render", {i["code"] for i in qa["source_to_artist_audit"]["issues"]})

    def test_copied_runtime_works_outside_checkout(self):
        runtime, out = self.root / "runtime", self.root / "portable"
        runtime.mkdir()
        for name in ("replicate_plot.py", "render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py"):
            shutil.copy2(SCRIPT.with_name(name), runtime / name)
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.spec))
        result = subprocess.run([sys.executable, str(runtime / "replicate_plot.py"), "--data", str(self.source()), "--spec", str(spec_path), "--out", str(out)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads((out / "qa.json").read_text())["valid_outputs"])


if __name__ == "__main__":
    unittest.main()
