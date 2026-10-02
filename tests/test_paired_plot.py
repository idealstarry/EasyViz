"""Checks for explicit pairing, raw-scale summaries, and transferable rendering."""
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image
from pypdf import PdfReader

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/paired_plot.py"
loader = importlib.util.spec_from_file_location("easyviz_paired_test", SCRIPT)
paired = importlib.util.module_from_spec(loader)
loader.loader.exec_module(paired)


class PairedPlotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-paired-")
        self.root = Path(self.temp.name)
        self.spec = {"chart": "paired", "fields": {"unit": "id", "condition": "visit", "value": "measurement"},
                     "order": {"condition": ["A", "B", "C"]},
                     "options": {"point_layout": "jitter", "point_area_pt2": 5, "connect_pairs": True, "y_scale": "log", "quantile_method": "linear"},
                     "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100, "auto_fit": True},
                     "labels": {"y": "Measurement (units)"}, "formats": ["pdf", "svg", "png"]}
        self.source = self.root / "source.csv"
        self.source.write_text("id,visit,measurement\n" + "".join(f"{unit:03d},{visit},{unit * factor}\n" for unit in range(1, 5) for visit, factor in [("A", 1), ("B", 4), ("C", 16)]))

    def tearDown(self):
        paired.plt.close("all")
        self.temp.cleanup()

    def draw(self, source=None, spec=None):
        source, spec = source or self.source, spec or self.spec
        data = paired.prepare(source, spec)
        layout, typography, rc = paired.core.setup(spec)
        with paired.plt.rc_context(rc):
            fig, colors = paired.draw(data, spec, layout, typography)
            fig.canvas.draw()
        return data, fig

    def test_three_conditions_preserve_ids_raw_median_and_exact_connectors(self):
        data, fig = self.draw()
        self.assertEqual(set(data["id"]), {"001", "002", "003", "004"})
        audit = paired.audit_source_artists(self.source, self.spec, fig)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual((audit["source_points_checked"], audit["complete_units"], audit["connectors_drawn"]), (12, 4, 8))
        expected = {"A": (1.75, 2.5, 3.25), "B": (7, 10, 13), "C": (28, 40, 52)}
        for row in audit["summary_rows"]:
            self.assertEqual((row["q1"], row["median"], row["q3"]), expected[row["condition"]])
        self.assertNotEqual(audit["summary_rows"][0]["median"], math.sqrt(2 * 3), "Log display must not change a raw-scale median")
        for segment, (_, unit, first, second) in zip(fig._easyviz_paired_connectors.get_segments(), fig._easyviz_paired_keys):
            factor = {"A": 1, "B": 4, "C": 16}
            self.assertEqual(list(segment[:, 1]), [int(unit) * factor[first], int(unit) * factor[second]])
            self.assertAlmostEqual(segment[1, 0] - segment[0, 0], 1)

    def test_weibull_is_explicit_and_distinct_from_linear(self):
        spec = deepcopy(self.spec)
        spec["options"]["quantile_method"] = "weibull"
        _, fig = self.draw(spec=spec)
        audit = paired.audit_source_artists(self.source, spec, fig)
        self.assertEqual(audit["summary_rows"][0]["q1"], 1.25)
        self.assertEqual(audit["summary_rows"][0]["q3"], 3.75)
        self.assertEqual(audit["quantile_method"], "weibull")

    def test_swarm_is_stable_for_renamed_fields_and_reordered_source(self):
        spec = deepcopy(self.spec)
        spec["options"]["point_layout"] = "swarm"
        original, fig = self.draw(spec=spec)
        renamed = self.root / "renamed.csv"
        paired.pd.read_csv(self.source, dtype=object).sample(frac=1, random_state=3).rename(columns={"id": "person", "visit": "stage", "measurement": "amount"}).to_csv(renamed, index=False)
        transfer = deepcopy(spec)
        transfer["fields"] = {"unit": "person", "condition": "stage", "value": "amount"}
        moved, other = self.draw(source=renamed, spec=transfer)
        first = {(row["id"], row["visit"]): row["_easyviz_x"] for _, row in original.iterrows()}
        second = {(row["person"], row["stage"]): row["_easyviz_x"] for _, row in moved.iterrows()}
        self.assertEqual(first, second)
        self.assertEqual(paired.audit_source_artists(renamed, transfer, other)["status"], "pass")
        points = fig._easyviz_paired_artists[0]["point"]
        self.assertAlmostEqual(points.get_sizes()[0] * math.pi / 4, 5)

    def test_missing_duplicate_invalid_measurements_and_ambiguous_roles_fail(self):
        original = self.source.read_text()
        samples = {"incomplete": original.replace("004,C,64\n", ""), "duplicate": original + "001,A,1\n", "empty id": original.replace("001,A,1", ",A,1"), "zero log": original.replace("001,A,1", "001,A,0"), "nonfinite": original.replace("001,A,1", "001,A,inf")}
        for label, text in samples.items():
            with self.subTest(label=label):
                source = self.root / f"{label}.csv"
                source.write_text(text)
                with self.assertRaises(paired.SpecError):
                    paired.prepare(source, self.spec)
        spec = deepcopy(self.spec)
        spec["fields"]["unit"] = "visit"
        with self.assertRaisesRegex(paired.SpecError, "distinct"):
            paired.prepare(self.source, spec)
        spec = deepcopy(self.spec)
        spec["options"]["point_alpha"] = 0
        with self.assertRaises(paired.SpecError):
            paired.prepare(self.source, spec)

    def test_exclusive_blocks_preserve_counts_and_reject_shared_ids_or_transparent_colors(self):
        source = self.root / "blocks.csv"
        data = paired.pd.read_csv(self.source, dtype=object)
        data["cohort"] = ["One" if unit in ("001", "002") else "Two" for unit in data["id"]]
        data.to_csv(source, index=False)
        spec = deepcopy(self.spec)
        spec["fields"]["block"] = "cohort"
        spec["order"]["block"] = ["One", "Two"]
        spec["colors"] = {"One": "#0072B2", "Two": "#D55E00"}
        _, fig = self.draw(source, spec)
        audit = paired.audit_source_artists(source, spec, fig)
        self.assertEqual(len(audit["summary_rows"]), 6)
        self.assertTrue(all(row["n"] == 2 for row in audit["summary_rows"]))
        data.loc[1, "cohort"] = "Two"
        data.to_csv(source, index=False)
        with self.assertRaisesRegex(paired.SpecError, "one block"):
            paired.prepare(source, spec)
        data.loc[1, "cohort"] = "One"
        data.to_csv(source, index=False)
        spec["colors"]["Two"] = "#D55E0000"
        with self.assertRaisesRegex(paired.SpecError, "transparent"):
            self.draw(source, spec)

    def test_artist_audit_detects_changed_values_summaries_connectors_and_colors(self):
        _, fig = self.draw()
        point = fig._easyviz_paired_artists[0]["point"]
        offsets = point.get_offsets().copy()
        offsets[0, 1] += .25
        point.set_offsets(offsets)
        codes = {r["code"] for r in paired.audit_source_artists(self.source, self.spec, fig)["issues"]}
        self.assertIn("source_point_mismatch", codes)
        _, fig = self.draw()
        summary = fig._easyviz_paired_summaries[0]["horizontal"]
        segments = summary.get_segments()
        segments[0][:, 1] += .25
        summary.set_segments(segments)
        self.assertIn("raw_scale_summary_mismatch", {r["code"] for r in paired.audit_source_artists(self.source, self.spec, fig)["issues"]})
        _, fig = self.draw()
        connectors = fig._easyviz_paired_connectors
        segments = connectors.get_segments()
        segments[0][1, 1] = segments[1][1, 1]
        connectors.set_segments(segments)
        self.assertIn("connector_pair_mismatch", {r["code"] for r in paired.audit_source_artists(self.source, self.spec, fig)["issues"]})
        _, fig = self.draw()
        fig._easyviz_paired_artists[0]["point"].set_facecolor("red")
        self.assertIn("point_color_changed", {r["code"] for r in paired.audit_source_artists(self.source, self.spec, fig)["issues"]})

    def test_swarm_overflow_never_discards_or_shrinks_rows(self):
        source = self.root / "dense.csv"
        source.write_text("id,visit,measurement\n" + "".join(f"u{i},{condition},1\n" for i in range(30) for condition in ["A", "B", "C"]))
        spec = deepcopy(self.spec)
        spec["options"].update(point_layout="swarm", point_area_pt2=50, point_spread=.1)
        with self.assertRaisesRegex(paired.SpecError, "Swarm cannot fit"):
            paired.render(source, spec, self.root / "dense-output")
        qa = json.loads((self.root / "dense-output/qa.json").read_text())
        self.assertEqual(qa["status"], "failed")
        self.assertFalse(qa["valid_outputs"])

    def test_exports_keep_dimensions_fonts_and_stale_output_fails_truthfully(self):
        out = self.root / "output"
        qa = paired.render(self.source, self.spec, out)
        self.assertEqual(qa["status"], "pass")
        with Image.open(out / "panel.png") as image:
            width, height = image.size
        self.assertEqual((width, height), (round(100 / 25.4 * 100), round(80 / 25.4 * 100)))
        page = PdfReader(out / "panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, 100, places=7)
        self.assertAlmostEqual(float(page.mediabox.height) * 25.4 / 72, 80, places=7)
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(settings["summary_policy"]["scale"], "raw measurements")
        self.assertFalse(settings["summary_policy"]["tests_performed"])
        self.source.write_text(self.source.read_text().replace("004,C,64\n", ""))
        with self.assertRaises(paired.SpecError):
            paired.render(self.source, self.spec, out)
        self.assertTrue((out / "panel.png").exists(), "Old exports may exist, but must never retain a passing record")
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["status"], "failed")
        self.assertFalse(qa["valid_outputs"])

    def test_source_change_during_export_invalidates_outputs(self):
        export = paired.core.export
        def change_after_export(*args):
            result = export(*args)
            self.source.write_text(self.source.read_text().replace("004,C,64", "004,C,65"))
            return result
        out = self.root / "changed-output"
        with mock.patch.object(paired.core, "export", side_effect=change_after_export):
            with self.assertRaises(paired.SpecError):
                paired.render(self.source, self.spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertIn("source_changed_during_render", {r["code"] for r in qa["source_to_artist_audit"]["issues"]})

    def test_portable_cli_without_checkout_preserves_complete_three_condition_design(self):
        runtime = self.root / "copied-runtime"
        runtime.mkdir()
        for name in ("paired_plot.py", *paired.HELPERS):
            shutil.copyfile(SCRIPT.with_name(name), runtime / name)
        spec = self.root / "spec.json"
        spec.write_text(json.dumps(self.spec))
        out = self.root / "portable-output"
        result = subprocess.run([sys.executable, str(runtime / "paired_plot.py"), "--data", str(self.source), "--spec", str(spec), "--out", str(out)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["source_to_artist_audit"]["complete_units"], 4)
        self.assertEqual(qa["source_to_artist_audit"]["conditions"], ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
