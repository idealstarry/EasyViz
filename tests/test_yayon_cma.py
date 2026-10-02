"""Actual source/artist and changed-schema checks for the source-backed case."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples/no-author-code/yayon-cma"
RUNTIME = ROOT / "skills/easyviz/scripts"
loader = importlib.util.spec_from_file_location("easyviz_yayon_test", CASE / "plot.py")
case = importlib.util.module_from_spec(loader)
loader.loader.exec_module(case)
runtime = case.runtime_at(RUNTIME)


class YayonCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-yayon-")
        self.root = Path(self.temp.name)
        self.spec = json.loads((CASE / "spec.json").read_text())
        self.data, self.summary = CASE / "inputs/source-data.csv", CASE / "inputs/summary.csv"

    def tearDown(self):
        runtime.plt.close("all")
        self.temp.cleanup()

    def test_all_original_cells_summaries_and_classes_then_actual_artist_mutations(self):
        prepared = case.prepare(self.data, self.summary, self.spec, runtime)
        fig, layout, typography = case.draw(prepared, self.spec, runtime)
        audit = case.audit(self.data, self.summary, self.spec, fig, runtime)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual((audit["cells_checked"], audit["summary_rows_checked"], audit["supplied_interaction_classes_checked"]), (1300, 65, 65))
        self.assertEqual(audit["alignment"]["status"], "pass")
        self.assertEqual(sum(r["point"] is not None for r in fig._case_artists["summary"]), 20)
        self.assertEqual(layout["width_mm"], 210)
        self.assertEqual(typography["tick"], 7.5)
        first = fig._case_artists["cells"][0]["artist"]
        first.set_visible(False)
        summary = fig._case_artists["summary"][0]
        summary["bar"].set_height(.123)
        summary["point"].set_sizes([1])
        fig._case_artists["ranges"][0]["artist"].set_x(.9)
        middle = fig._easyviz_aligned_frame.axes["supplied-summary"]
        middle.set_ylim(-10, 10)
        issues = {r["code"] for r in case.audit(self.data, self.summary, self.spec, fig, runtime)["issues"]}
        self.assertTrue({"cell_source_artist_mismatch", "summary_bar_source_artist_mismatch", "interaction_point_source_artist_mismatch", "emphasis_range_geometry_mismatch", "summary_value_domain_mismatch"} <= issues)

    def test_transfer_changes_all_schemas_orders_sizes_and_strict_thresholds(self):
        spec = json.loads((CASE / "transfer/spec.json").read_text())
        data, summary = CASE / "transfer/matrix.csv", CASE / "transfer/summary.csv"
        prepared = case.prepare(data, summary, spec, runtime)
        self.assertEqual(len(prepared["data"]), 40)
        self.assertEqual(len(prepared["summary"]), 5)
        self.assertIn("NA", prepared["data"]["Zone"].tolist())
        self.assertIn("001", prepared["data"]["Zone"].tolist())
        self.assertIn(" Feature 01 ", prepared["data"]["Feature"].tolist())
        fig, _, _ = case.draw(prepared, spec, runtime)
        points = {r["column"]: r for r in fig._case_artists["summary"]}
        self.assertEqual(points[" Feature 01 "]["class"], 1)  # exact .001 enters <.01
        self.assertEqual(points["ITEM-B"]["class"], 2)       # exact .01 enters <.05
        self.assertIsNone(points["feature /3"]["class"])   # exact .05 has no dot
        self.assertEqual(points["Feature#5"]["class"], 0)
        self.assertEqual(case.audit(data, summary, spec, fig, runtime)["status"], "pass")
        runtime.plt.close(fig)
        qa = case.render(data, summary, spec, self.root / "transfer", RUNTIME, font_override="DejaVu Sans")
        self.assertEqual(qa["status"], "pass")
        self.assertFalse(qa["dendrogram_reproduced"])
        with Image.open(self.root / "transfer/panel.png") as image:
            self.assertEqual(image.size, (round(210 / 25.4 * 300), round(111 / 25.4 * 300)))
        page = PdfReader(self.root / "transfer/panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, 210, places=5)
        self.assertAlmostEqual(float(page.mediabox.height) * 25.4 / 72, 111, places=5)
        settings = json.loads((self.root / "transfer/settings.json").read_text())
        self.assertEqual(settings["typography"]["tick"], 7.5)
        self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")
        self.assertEqual(settings["font_override"], "DejaVu Sans")
        self.assertFalse(json.loads((self.root / "transfer/stats.json").read_text())["anova_recomputed"])

    def test_join_coverage_duplicate_missing_and_unsupported_scope_fail(self):
        spec = json.loads((CASE / "transfer/spec.json").read_text())
        data = CASE / "transfer/matrix.csv"
        bad = self.root / "bad-summary.csv"
        bad.write_text("Feature key,Agreement,Corrected P\nFeature#5,0.3,.03\nFeature#5,0.4,.02\n")
        with self.assertRaisesRegex(ValueError, "one-to-one"): case.prepare(data, bad, spec, runtime)
        incomplete = self.root / "incomplete.csv"
        lines = data.read_text().splitlines()
        incomplete.write_text("\n".join(lines[:-1]) + "\n")
        with self.assertRaisesRegex(ValueError, "fully supplied"): case.prepare(incomplete, CASE / "transfer/summary.csv", spec, runtime)
        unknown = deepcopy(spec)
        unknown["clustering"] = True
        with self.assertRaisesRegex(ValueError, "Unknown or invalid spec"): case.validate_spec(unknown, runtime)
        duplicate = self.root / "duplicate.csv"
        duplicate.write_text(data.read_text() + lines[1] + "\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"): case.prepare(duplicate, CASE / "transfer/summary.csv", spec, runtime)

    def test_provenance_mismatch_fails_truthfully(self):
        provenance = json.loads((CASE / "inputs/provenance.json").read_text())
        provenance["prepared_hashes"]["source-data.csv"] = "0" * 64
        path = self.root / "provenance.json"
        path.write_text(json.dumps(provenance))
        with self.assertRaisesRegex(ValueError, "extraction provenance"):
            case.render(self.data, self.summary, self.spec, self.root / "failed", RUNTIME, provenance_path=path)
        qa = json.loads((self.root / "failed/qa.json").read_text())
        self.assertEqual(qa["status"], "failed")
        self.assertFalse(qa["valid_outputs"])


if __name__ == "__main__":
    unittest.main()
