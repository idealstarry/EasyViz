"""Source-backed checks for exact supplied intervals and truthful failed QA."""
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

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/interval_plot.py"
loader = importlib.util.spec_from_file_location("easyviz_interval_test", SCRIPT)
interval = importlib.util.module_from_spec(loader)
loader.loader.exec_module(interval)


class IntervalPlotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-interval-")
        self.root = Path(self.temp.name)
        self.base = {"chart": "interval", "fields": {"label": "label", "estimate": "est", "lower": "lo", "upper": "hi"},
                     "layout": {"width_mm": 88, "height_mm": 70, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100},
                     "formats": ["png"], "labels": {"x": "Supplied estimate"}}

    def tearDown(self):
        interval.plt.close("all")
        self.temp.cleanup()

    def csv(self, text):
        path = self.root / "input.csv"
        path.write_text(text)
        return path

    def draw(self, source, spec):
        data = interval.prepare(source, spec)
        resolved = deepcopy(spec)
        resolved["layout"].setdefault("auto_fit", True)
        layout, typography, rc = interval.core.setup(resolved)
        with interval.plt.rc_context(rc):
            fig, colors = interval.draw(data, resolved, layout, typography)
            fig.canvas.draw()
        return data, fig, colors

    def test_supplied_asymmetry_is_audited_against_actual_artists(self):
        source = self.csv("label,est,lo,hi,n\nNA,2,-1,9,not a sample size\nnull,-.5,-5,0,unknown\n001,4,3.9,20,999\n")
        spec = deepcopy(self.base)
        spec["options"] = {"reference_value": 0, "cap_height": .1}
        data, fig, _ = self.draw(source, spec)
        expected = [(-1, 2, 9), (-5, -.5, 0), (3.9, 4, 20)]
        for record, (low, estimate, high) in zip(fig._easyviz_interval_artists, expected):
            segment = record["interval"].get_segments()[0]
            self.assertEqual(segment[:, 0].tolist(), [low, high])
            self.assertEqual(record["point"].get_offsets()[0, 0], estimate)
            self.assertEqual(len(record["caps"].get_segments()), 2)
            self.assertEqual(len(record["point"].get_edgecolors()), 0)
        audit = interval.audit_source_artists(source, spec, fig)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual([r["label"] for r in audit["rows"]], ["NA", "null", "001"])
        # A symmetric interval substitution must fail even though it brackets the estimate.
        fig._easyviz_interval_artists[0]["interval"].set_segments([[[-5, 0], [9, 0]]])
        self.assertIn("interval_endpoint_mismatch", {i["code"] for i in interval.audit_source_artists(source, spec, fig)["issues"]})
        self.assertEqual(data["n"].tolist(), ["not a sample size", "unknown", "999"])
        interval.plt.close(fig)
        out = self.root / "output"
        qa = interval.render(source, spec, out)
        self.assertEqual(qa["input_rows"], 3)
        stats = json.loads((out / "stats.json").read_text())
        self.assertFalse(stats["sample_size_inferred"])
        self.assertNotIn("n", stats)
        table = interval.pd.read_csv(out / "plotting-data.csv", dtype=object, keep_default_na=False)
        self.assertEqual(table["n"].tolist(), ["not a sample size", "unknown", "999"])
        self.assertEqual(table["_easyviz_source_row"].tolist(), ["1", "2", "3"])

    def test_log_axis_keeps_source_endpoints_and_fixed_canvas(self):
        source = self.csv("label,est,lo,hi\nA,.7,.2,2\nB,5,3,50\n")
        spec = deepcopy(self.base)
        spec["options"] = {"x_scale": "log", "reference_value": 1, "x_limits": [.1, 100]}
        spec["formats"] = ["pdf", "png", "svg", "tiff"]
        data, fig, _ = self.draw(source, spec)
        self.assertEqual(fig.axes[0].get_xscale(), "log")
        self.assertEqual(fig._easyviz_interval_artists[1]["interval"].get_segments()[0][:, 0].tolist(), [3, 50])
        self.assertEqual(interval.audit_source_artists(source, spec, fig)["status"], "pass")
        interval.plt.close(fig)
        out = self.root / "log"
        qa = interval.render(source, spec, out)
        self.assertEqual(qa["status"], "pass")
        page = PdfReader(out / "panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) / 72 * 25.4, 88, places=5)
        self.assertAlmostEqual(float(page.mediabox.height) / 72 * 25.4, 70, places=5)
        for extension in ("png", "tiff"):
            with Image.open(out / f"panel.{extension}") as image:
                self.assertEqual(image.size, (round(88 / 25.4 * 100), round(70 / 25.4 * 100)))
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["axis"]["x_scale"], "log")
        self.assertEqual(settings["axis"]["reference_value"], 1)
        self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(len(settings["renderer"]["helper_sha256"]["render.py"]), 64)
        self.assertEqual(data["lo"].tolist(), [.2, 3])

    def test_sparse_series_use_global_offsets_and_do_not_impute(self):
        source = self.csv("label,series,est,lo,hi\nA,S1,1,.2,2\nA,S2,1.4,.4,2\nB,S1,.6,-1,1\nC,S2,.2,-.5,.8\n")
        spec = deepcopy(self.base)
        spec["fields"]["series"] = "series"
        spec["order"] = {"label": ["C", "B", "A"], "series": ["S2", "S1"]}
        spec["colors"] = {"S1": "#0072B2", "S2": "#D55E00"}
        out = self.root / "sparse"
        qa = interval.render(source, spec, out)
        self.assertEqual(qa["source_to_artist_audit"]["source_rows"], 4)
        table = interval.pd.read_csv(out / "plotting-data.csv")
        self.assertEqual(len(table), 4)
        self.assertEqual(table["_easyviz_y"].tolist(), [2.3, 1.7, 1.3, -.3])
        self.assertFalse(qa["source_to_artist_audit"]["missing_combinations_imputed"])

    def test_blocks_separate_series_from_color_and_preserve_sparse_pairs(self):
        source = self.csv("label,series,est,lo,hi,state\nB,S1,2,1,4,filled\nA,S2,1,.5,2,hollow\nA,S1,3,2,4,filled\n")
        spec = deepcopy(self.base)
        spec["fields"].update(series="series", color="label", mark_state="state")
        spec["options"] = {"series_layout": "blocks", "mark_fill": "input", "x_scale": "log", "reference_value": 1, "x_ticks": [.5, 1, 2, 4]}
        spec["order"] = {"label": ["A", "B"], "series": ["S1", "S2"]}
        spec["colors"] = {"A": "#0072B2", "B": "#D55E00"}
        spec["legends"] = {"categorical": {"position": "bottom"}}
        data, fig, colors = self.draw(source, spec)
        self.assertEqual([text.get_text() for text in fig.axes[0].get_yticklabels()], ["S1", "A", "B", "S2", "A"])
        self.assertEqual(data["_easyviz_y"].tolist(), [2, 4.6, 1])
        self.assertEqual(colors, spec["colors"])
        self.assertEqual(fig.axes[0].get_yticklabels()[0].get_color(), "#444444")
        self.assertEqual(interval.audit_source_artists(source, spec, fig)["status"], "pass")
        self.assertEqual(len(fig._easyviz_legend_layout.requests), 1, "Only provided mark states need a guide; block/row labels decode other categories")
        interval.plt.close(fig)
        qa = interval.render(source, spec, self.root / "blocks")
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(qa["input_rows"], 3)

    def test_fill_policy_is_explicit_and_overlap_is_inclusive(self):
        source = self.csv("label,est,lo,hi\nA,2,1,3\nB,.7,.5,.8\nC,1,1,1\n")
        spec = deepcopy(self.base)
        spec["options"] = {"x_scale": "log", "reference_value": 1}
        data, fig, _ = self.draw(source, spec)
        self.assertEqual(data["_easyviz_mark_state"].tolist(), ["filled"] * 3)
        self.assertEqual(interval.audit_source_artists(source, spec, fig)["status"], "pass")
        interval.plt.close(fig)
        spec["options"]["mark_fill"] = "reference_overlap"
        data, fig, _ = self.draw(source, spec)
        self.assertEqual(data["_easyviz_mark_state"].tolist(), ["hollow", "filled", "hollow"])
        self.assertEqual(interval.audit_source_artists(source, spec, fig)["status"], "pass")
        self.assertEqual(len(fig._easyviz_interval_artists[0]["point"].get_facecolors()), 0)
        interval.plt.close(fig)

    def test_invalid_intervals_log_limits_fields_and_orders_fail(self):
        for body in ("label,est,lo,hi\nA,2,3,4\n", "label,est,lo,hi\nA,2,1,1.5\n", "label,est,lo,hi\nA,2,NaN,4\n", "label,est,lo,hi\nA,2,,4\n", "label,est,lo,hi\nA,2,1,4\nA,3,2,5\n"):
            with self.subTest(body=body), self.assertRaises(interval.SpecError):
                interval.prepare(self.csv(body), self.base)
        source = self.csv("label,est,lo,hi,state\nA,2,.5,4,filled\nB,3,2,5,hollow\n")
        bad_specs = [
            {"options": {"x_scale": "log", "reference_value": 0}},
            {"options": {"x_scale": "log", "x_limits": [0, 6]}},
            {"options": {"x_limits": [1, 6]}},
            {"options": {"x_limits": [0, 4]}},
            {"options": {"x_limits": [0, 6], "reference_value": 10}},
            {"options": {"reference_value": True}},
            {"options": {"mark_fill": "reference_overlap"}},
            {"options": {"mark_fill": "input"}},
            {"fields": {**self.base["fields"], "mark_state": "state"}},
            {"order": {"label": ["A"]}},
            {"order": {"label": ["A", "A", "B"]}},
            {"statistics": {"n": 50}},
            {"options": {"series_layout": "blocks"}},
        ]
        for change in bad_specs:
            spec = deepcopy(self.base)
            spec.update(change)
            with self.subTest(change=change), self.assertRaises(interval.SpecError):
                interval.prepare(source, spec)
        spec = deepcopy(self.base)
        spec["options"] = {"x_scale": "log"}
        with self.assertRaisesRegex(interval.SpecError, "strictly positive"):
            interval.prepare(self.csv("label,est,lo,hi\nA,2,-1,4\n"), spec)

    def test_artist_collision_keeps_failed_record_and_stale_runs_are_invalidated(self):
        source = self.csv("label,series,est,lo,hi\nA,S1,1,.5,2\nA,S2,1,.5,2\nB,S1,1,.5,2\nB,S2,1,.5,2\n")
        spec = deepcopy(self.base)
        spec["fields"]["series"] = "series"
        spec["colors"] = {"S1": "#0072B2", "S2": "#D55E00"}
        out = self.root / "collision"
        interval.render(source, spec, out)
        spec["options"] = {"series_span": .02, "marker_area_pt2": 64}
        with self.assertRaisesRegex(interval.SpecError, "QA needs revision"):
            interval.render(source, spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["status"], "needs_revision")
        self.assertFalse(qa["valid_outputs"])
        self.assertTrue(qa["mark_geometry"]["issues"])
        self.assertEqual(qa["source_to_artist_audit"]["status"], "pass")
        source.write_text("label,series,est,lo,hi\nA,S1,1,NaN,2\n")
        with self.assertRaises(interval.SpecError):
            interval.render(source, spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["status"], "failed")
        self.assertFalse(qa["valid_outputs"])

    def test_cli_runs_after_copying_sibling_helpers_outside_repo(self):
        portable = self.root / "portable"
        portable.mkdir()
        for name in ("interval_plot.py", "render.py", "legend_layout.py", "figure_profile.py", "auto_layout.py", "annotation_review.py"):
            shutil.copy(SCRIPT.with_name(name), portable / name)
        source = self.csv("label,est,lo,hi\nA,2,1,4\nB,3,2,5\n")
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.base))
        out = self.root / "portable-output"
        run = subprocess.run([sys.executable, str(portable / "interval_plot.py"), "--data", str(source), "--spec", str(spec_path), "--out", str(out)], cwd=portable, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "pass")
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["spec_file"], str(spec_path.resolve()))
        self.assertEqual(len(settings["spec_file_sha256"]), 64)

    def test_fully_transparent_rows_fail_but_pale_colors_remain_valid(self):
        source = self.csv("label,est,lo,hi,state\nA,1,.5,2,hollow\nB,2,1,3,hollow\n")
        spec = deepcopy(self.base)
        spec["fields"]["mark_state"] = "state"
        spec["options"] = {"mark_fill": "input"}
        spec["colors"] = {"A": "#00000000", "B": "#ff000000"}
        out = self.root / "invisible"
        with self.assertRaisesRegex(interval.SpecError, "nonzero alpha"):
            interval.render(source, spec, out)
        self.assertFalse(json.loads((out / "qa.json").read_text())["valid_outputs"])
        spec["colors"] = {"A": "#ffffcc", "B": "#ff000080"}
        self.assertEqual(interval.render(source, spec, out)["status"], "pass")

    def test_source_change_during_actual_export_invalidates_output(self):
        source = self.csv("label,est,lo,hi\nA,2,1,4\n")
        original_export = interval.core.export
        def export_then_change(*args):
            result = original_export(*args)
            source.write_text("label,est,lo,hi\nA,9,1,10\n")
            return result
        out = self.root / "changed"
        with mock.patch.object(interval.core, "export", side_effect=export_then_change):
            with self.assertRaisesRegex(interval.SpecError, "QA needs revision"):
                interval.render(source, self.base, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertIn("source_changed_during_render", {i["code"] for i in qa["source_to_artist_audit"]["issues"]})

    def test_default_interval_stroke_cannot_overlap_another_circle(self):
        source = self.csv("label,series,est,lo,hi\nA,S1,1,.5,4\nA,S2,3,2,4\n")
        spec = deepcopy(self.base)
        spec["fields"]["series"] = "series"
        spec["colors"] = {"S1": "#0072B2", "S2": "#D55E00"}
        spec["layout"].update(auto_fit=False, margins={"left": .19, "right": .77, "bottom": .23, "top": .88}, line_width_pt=.6)
        spec["options"] = {"series_span": 2.7 / (70 / 25.4 * 72 * .65)}
        out = self.root / "stroke-collision"
        with self.assertRaisesRegex(interval.SpecError, "QA needs revision"):
            interval.render(source, spec, out)
        issues = json.loads((out / "qa.json").read_text())["mark_geometry"]["issues"]
        self.assertIn("interval_overlaps_other_estimate", {i["code"] for i in issues})
        spec["options"]["series_span"] = 6 / (70 / 25.4 * 72 * .65)
        self.assertEqual(interval.render(source, spec, out)["status"], "pass")

    def test_vertical_endpoint_caps_account_for_stroke_clipping(self):
        source = self.csv("label,est,lo,hi\nA,2,1,4\n")
        spec = deepcopy(self.base)
        spec["options"] = {"x_limits": [1,4], "cap_height": .1}
        out = self.root / "cap-clipping"
        with self.assertRaisesRegex(interval.SpecError, "QA needs revision"):
            interval.render(source, spec, out)
        issues = json.loads((out / "qa.json").read_text())["mark_geometry"]["issues"]
        self.assertTrue(any(i["code"] == "interval_stroke_clipped" and i["role"] == "caps" for i in issues))
        spec["options"]["x_limits"] = [.9,4.1]
        self.assertEqual(interval.render(source, spec, out)["status"], "pass")


if __name__ == "__main__":
    unittest.main()
