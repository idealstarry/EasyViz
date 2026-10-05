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

    def test_optional_bar_boundaries_preserve_summary_grouped_and_stacked_quantities(self):
        source = self.source()
        for mode in ("summary", "grouped", "stacked"):
            with self.subTest(mode=mode):
                spec = deepcopy(self.spec)
                spec["options"].update(mode=mode)
                if mode == "summary":
                    spec["fields"].pop("component")
                    spec["colors"] = {"NA": "#29ACF3", "null": "#FF797C"}
                    path = self.source("arm,person,amount\nNA,001,0\nNA,002,10\nnull,001,-2\nnull,002,4\n")
                else:
                    path = self.source()
                before = path.read_bytes()
                _, legacy, _ = self.draw(path, spec)
                expected = legacy._easyviz_replicate_artists
                self.assertTrue(all(bar["artist"].get_linewidth() == 0 and bar["artist"].get_edgecolor()[3] == 0 for bar in expected["bars"]))
                spec["options"].update(bar_style="outline", bar_edge_width_pt=.65)
                _, outlined, colors = self.draw(path, spec)
                actual = outlined._easyviz_replicate_artists
                self.assertEqual([(p["source_rows"], p["value"]) for p in actual["points"]], [(p["source_rows"], p["value"]) for p in expected["points"]])
                for left, right in zip(expected["bars"], actual["bars"]):
                    a, b = left["artist"], right["artist"]
                    self.assertEqual((a.get_x(), a.get_y(), a.get_width(), a.get_height()), (b.get_x(), b.get_y(), b.get_width(), b.get_height()))
                    self.assertEqual(b.get_facecolor()[3], 0)
                    self.assertEqual(b.get_linewidth(), .65)
                    key = right["component"] if right["component"] is not None else right["condition"]
                    self.assertEqual(b.get_edgecolor(), replicate.core.mcolors.to_rgba(colors[key]))
                self.assertEqual([(i["mean"], i["sample_sd"]) for i in actual["intervals"]], [(i["mean"], i["sample_sd"]) for i in expected["intervals"]])
                self.assertEqual(replicate.audit_source_artists(path, spec, outlined)["status"], "pass")
                if mode != "summary":
                    handles = outlined._easyviz_legend_layout.entries[0]["artist"].legend_handles
                    self.assertEqual([h.get_facecolor()[3] for h in handles], [0, 0])
                    self.assertEqual([h.get_edgecolor() for h in handles], [replicate.core.mcolors.to_rgba(colors[c]) for c in ("X", "Y")])
                    handles[0].set_facecolor("green")
                    self.assertIn("bar_legend_boundary_mismatch", {i["code"] for i in replicate.audit_source_artists(path, spec, outlined)["issues"]})
                actual["bars"][0]["artist"].set_linewidth(0)
                self.assertIn("bar_boundary_mismatch", {i["code"] for i in replicate.audit_source_artists(path, spec, outlined)["issues"]})
                self.assertEqual(path.read_bytes(), before)

    def test_filled_bar_optional_edge_and_invalid_outline_options(self):
        spec = deepcopy(self.spec)
        spec["options"].update(bar_edge_width_pt=.4, bar_edge_color="#444444")
        _, fig, colors = self.draw(self.source(), spec)
        for record in fig._easyviz_replicate_artists["bars"]:
            patch = record["artist"]
            self.assertEqual(patch.get_facecolor(), replicate.core.mcolors.to_rgba(colors[record["component"]]))
            self.assertEqual(patch.get_edgecolor(), replicate.core.mcolors.to_rgba("#444444"))
            self.assertEqual(patch.get_linewidth(), .4)
        self.assertEqual(replicate.audit_source_artists(self.source(), spec, fig)["status"], "pass")
        for options in ({"bar_style": "outline", "bar_edge_width_pt": 0}, {"bar_style": "outline", "bar_edge_width_pt": True},
                        {"bar_style": "outline", "bar_edge_color": "none"}, {"bar_style": "fuzzy"},
                        {"bar_edge_width_pt": -1}, {"bar_edge_width_pt": float("nan")}, {"bar_edge_color": "#111111"}):
            invalid = deepcopy(self.spec)
            invalid["options"].update(options)
            with self.subTest(options=options), self.assertRaises(replicate.SpecError):
                replicate.validate_spec(invalid)
        states = deepcopy(self.spec)
        states["fields"].pop("component")
        states["fields"]["state"] = "state"
        states["options"].update(mode="summary", bar_style="outline", state_hatches={"declared": "/"})
        with self.assertRaisesRegex(replicate.SpecError, "mapped states"):
            replicate.validate_spec(states)

    def test_outline_zero_axis_baseline_is_intentional_but_other_stroke_clipping_fails(self):
        spec = deepcopy(self.spec)
        spec["fields"].pop("component")
        spec.pop("colors")
        spec["options"].update(mode="summary", bar_style="outline", bar_edge_width_pt=.65, y_limits=[0, 15])
        source = self.source("arm,person,amount\nA,1,1\nA,2,2\nA,3,3\nB,1,5\nB,2,6\nB,3,7\n")
        qa = replicate.render(source, spec, self.root / "zero-baseline")
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(len(qa["mark_geometry"]["intentional_baseline_contacts"]), 2)
        settings = json.loads((self.root / "zero-baseline/settings.json").read_text())
        self.assertEqual(settings["options"]["y_limits"], [0, 15])
        _, fig, _ = self.draw(source, spec)
        ax = fig.axes[0]
        ax.set_ylim(0, 6)
        fig.canvas.draw()
        self.assertIn("bar_boundary_clipped", {issue["code"] for issue in replicate._canvas_checks(fig)[1]["issues"]}, "An outlined top edge at the upper limit remains clipped")
        ax.set_ylim(1, 15)
        fig.canvas.draw()
        geometry = replicate._canvas_checks(fig)[1]
        self.assertEqual(geometry["intentional_baseline_contacts"], [])
        self.assertIn("bar_boundary_clipped", {issue["code"] for issue in geometry["issues"]}, "A nonzero lower limit cannot excuse a hidden bar baseline")

    def test_stacked_outline_keeps_zero_components_and_unit_total_endpoints(self):
        spec = deepcopy(self.spec)
        spec["options"].update(bar_style="outline", y_limits=[0, 15])
        source = self.source("arm,person,part,amount\nA,01,X,0\nA,01,Y,3\nA,02,X,0\nA,02,Y,5\n")
        before = source.read_bytes()
        qa = replicate.render(source, spec, self.root / "zero-components")
        self.assertEqual(qa["status"], "pass")
        _, fig, _ = self.draw(source, spec)
        artists = fig._easyviz_replicate_artists
        self.assertEqual([bar["artist"].get_height() for bar in artists["bars"]], [0, 4])
        self.assertEqual([bar["artist"].get_y() for bar in artists["bars"]], [0, 0])
        self.assertEqual([point["value"] for point in artists["points"]], [3, 5])
        replicate.np.testing.assert_allclose(artists["intervals"][0]["artist"].get_segments()[0][:, 1], [4 - 2 ** .5, 4 + 2 ** .5])
        self.assertEqual(replicate.audit_source_artists(source, spec, fig)["status"], "pass")
        self.assertEqual(source.read_bytes(), before)

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
        for name in ("replicate_plot.py", "render.py", "legend_layout.py", "auto_layout.py", "figure_profile.py", "annotation_review.py", "figure_elements.py", "panel_readability.py", "observation_clipping.py"):
            shutil.copy2(SCRIPT.with_name(name), runtime / name)
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.spec))
        result = subprocess.run([sys.executable, str(runtime / "replicate_plot.py"), "--data", str(self.source()), "--spec", str(spec_path), "--out", str(out)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads((out / "qa.json").read_text())["valid_outputs"])


if __name__ == "__main__":
    unittest.main()
