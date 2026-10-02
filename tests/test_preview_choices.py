"""Real preview choices must share evidence without guessing design or a winner."""
from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/preview_choices.py"
loader = importlib.util.spec_from_file_location("easyviz_test_preview_choices", SCRIPT)
preview = importlib.util.module_from_spec(loader)
loader.loader.exec_module(preview)
core = preview.core


class PreviewChoicesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-previews-")
        self.root = Path(self.temp.name)
        self.source = self.root / "original observations.csv"
        self.source.write_text("id,condition,reading,note\n001,NA,1.0000,first\nNA,NA,1,tie\nnull,NA,2.5,literal\na4,NA,4,\na5,NA,8,fifth\na6,NA,11,sixth\nb1,null,2,first\nb2,null,3,second\nb3,null,3,tie\nb4,null,6,fourth\nb5,null,9,fifth\nb6,null,14,sixth\n", encoding="utf-8")
        self.request = {"row_kind": "observations", "fields": {"group": "condition", "value": "reading", "unit": "id"},
                        "design": {"structure": "unknown", "confirmed": False, "unit_definition": "Unknown sampling unit; each row is one supplied measurement"},
                        "measurement_units": None, "colors": {"NA": "#0072B2", "null": "#D55E00"},
                        "layout": {"width_mm": 88, "height_mm": 70, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 120},
                        "formats": ["png"]}
        self.request_path = self.root / "request.json"

    def tearDown(self):
        core.plt.close("all")
        self.temp.cleanup()

    def run_preview(self, request=None, name="outputs"):
        self.request_path.write_text(json.dumps(self.request if request is None else request), encoding="utf-8")
        out = self.root / name
        manifest = preview.preview(self.source, self.request_path, out)
        return out, manifest

    def read(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def rows(self, path):
        with path.open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_two_real_exports_retain_source_ids_ties_and_fixed_comparison(self):
        original = self.source.read_bytes()
        self.request["formats"] = ["png", "pdf", "svg", "tiff"]
        out, manifest = self.run_preview()
        self.assertEqual(manifest["status"], "pass")
        self.assertEqual([c["id"] for c in manifest["choices"]], ["box-points", "ecdf"])
        self.assertIsNone(manifest["selection"]["chosen_choice"])
        self.assertFalse(manifest["selection"]["automatic_winner"])
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual((out / "source.csv").read_bytes(), original)
        self.assertEqual(manifest["source_binding"]["sha256"], hashlib.sha256(original).hexdigest())
        qa = self.read(out / "qa.json")
        self.assertTrue(qa["shared_settings_identical"])
        self.assertTrue(qa["source_unchanged"])
        self.assertTrue(qa["visual_review_required"])
        self.assertEqual(qa["excluded_rows"], 0)
        original_rows = self.rows(self.source)
        for choice in manifest["choices"]:
            with self.subTest(choice=choice["id"]):
                directory = out / choice["id"]
                qa_child = self.read(directory / "qa.json")
                self.assertEqual(qa_child["source_to_artist_audit"]["audited_observations"], len(original_rows))
                self.assertEqual((qa_child["width_mm"], qa_child["height_mm"]), (88, 70))
                for extension in ("pdf", "svg"):
                    self.assertAlmostEqual(qa_child["exports"][extension]["width_mm"], 88, places=5)
                    self.assertAlmostEqual(qa_child["exports"][extension]["height_mm"], 70, places=5)
                self.assertEqual(qa_child["exports"]["png"]["pixels"], [round(88 / 25.4 * 120), round(70 / 25.4 * 120)])
                self.assertEqual(qa_child["exports"]["tiff"]["pixels"], qa_child["exports"]["png"]["pixels"])
                with core.Image.open(directory / "panel.png") as image:
                    self.assertGreater(len(image.getcolors(maxcolors=10_000_000)), 10)
                settings = self.read(directory / "settings.json")
                self.assertEqual(settings["resolved_colors"], self.request["colors"])
                self.assertEqual(settings["input_sha256"], manifest["source_binding"]["sha256"])
                self.assertIn("units unknown", (directory / "panel.svg").read_text())
                plotted = self.rows(directory / "plotting-data.csv")
                self.assertEqual([r["id"] for r in plotted], [r["id"] for r in original_rows])
                self.assertEqual([r["condition"] for r in plotted], [r["condition"] for r in original_rows])
                self.assertEqual([r["_easyviz_source_value_text"] for r in plotted], [r["reading"] for r in original_rows])
                self.assertEqual([int(r["_easyviz_source_row"]) for r in plotted], list(range(1, 13)))
                self.assertEqual([float(r["reading"]) for r in plotted], [float(r["reading"]) for r in original_rows])
                self.assertIn("Experimental independence is unconfirmed", (directory / "caption.md").read_text())
                self.assertFalse(self.read(directory / "stats.json")["tests_performed"])
                if choice["id"] != "ecdf":
                    self.assertEqual(settings["options"]["alpha"], .65)
                    self.assertEqual(qa_child["source_to_artist_audit"]["intended_point_alpha"], .65)
                    for color in qa_child["source_to_artist_audit"]["actual_point_facecolors"].values():
                        self.assertTrue(all(rgba[3] == .65 for rgba in color))
                for file in choice["files"]:
                    self.assertEqual(file["sha256"], hashlib.sha256((out / file["path"]).read_bytes()).hexdigest())
        cumulative = self.rows(out / "ecdf/cumulative-data.csv")
        tied = next(row for row in cumulative if row["group"] == "NA" and float(row["value"]) == 1)
        self.assertEqual((int(tied["jump_count"]), int(tied["observation_count"])), (2, 6))
        self.assertAlmostEqual(float(tied["cumulative_fraction"]), 2 / 6)
        self.assertEqual(json.loads(tied["source_rows"]), [1, 2])
        self.assertFalse(self.read(out / "ecdf/stats.json")["smoothing_applied"])
        self.assertFalse(self.read(out / "box-points/stats.json")["confidence_intervals_computed"])

    def test_explicit_violin_is_a_third_output_with_density_limitations(self):
        self.request["options"] = {"include_violin": True}
        out, manifest = self.run_preview()
        self.assertEqual([r["id"] for r in manifest["choices"]], ["box-points", "ecdf", "violin-points"])
        self.assertTrue((out / "violin-points/panel.png").is_file())
        self.assertTrue(self.read(out / "violin-points/stats.json")["smoothing_applied"])
        self.assertIn("Scott bandwidth", (out / "violin-points/caption.md").read_text())
        self.assertIn("not sample counts", " ".join(manifest["choices"][2]["limitations"]))

    def test_unsafe_or_ambiguous_requests_fail_before_creating_outputs(self):
        changes = [
            ({"row_kind": "summaries"}, "row_kind"),
            ({"row_kind": "technical_replicates"}, "technical replicates"),
            ({"statistics": {"method": "welch"}}, "Unknown request"),
            ({"design": {"structure": "paired", "confirmed": True, "unit_definition": "participant"}}, "paired_plot"),
            ({"measurement_units": ""}, "measurement_units"),
            ({"options": {"value_limits": [2, 10]}}, "every observation"),
            ({"options": {"value_scale": "log", "value_limits": [0, 20]}}, "positive"),
            ({"fields": {"group": "condition", "value": "reading", "unit": "condition"}}, "distinct"),
            ({"order": {"group": ["NA", "NA"]}}, "exactly once"),
            ({"colors": {"NA": "red", "null": "red"}}, "distinct"),
            ({"formats": ["svg"]}, "include png"),
        ]
        for index, (change, message) in enumerate(changes):
            with self.subTest(change=change):
                request = deepcopy(self.request)
                request.update(change)
                self.request_path.write_text(json.dumps(request))
                out = self.root / f"invalid-{index}"
                with self.assertRaisesRegex(SpecError, message):
                    preview.preview(self.source, self.request_path, out)
                self.assertFalse(out.exists())

    def test_duplicate_repeated_ids_and_bad_csv_never_drop_rows(self):
        for index, (source, message) in enumerate([
            ("id,condition,reading\n001,A,1\n001,A,2\n", "technical repeats"),
            ("id,condition,reading\n001,A,1\n001,B,2\n", "paired/repeated"),
            ("id,condition,reading\n001,A,NaN\n", "finite"),
            ("id,condition,reading\n001,A,\n", "Empty"),
            ("id,condition,reading\n001,A,1\n\n", "Ragged"),
            ("id,condition,reading,reading\n001,A,1,2\n", "headers"),
        ]):
            with self.subTest(source=source):
                self.source.write_text(source)
                self.request["colors"] = {"A": "red", "B": "blue"} if ",B," in source else {"A": "red"}
                self.request_path.write_text(json.dumps(self.request))
                out = self.root / f"bad-data-{index}"
                with self.assertRaisesRegex(SpecError, message):
                    preview.preview(self.source, self.request_path, out)
                self.assertFalse(out.exists())

    def test_sparse_violin_does_not_replace_requested_kind(self):
        self.source.write_text("id,condition,reading\n001,NA,1\n002,NA,2\n003,null,3\n004,null,4\n")
        self.request["options"] = {"include_violin": True}
        with self.assertRaisesRegex(SpecError, "5 distinct"):
            self.run_preview()
        self.assertFalse((self.root / "outputs").exists())

    def test_actual_point_coordinate_corruption_invalidates_exports_and_retains_audit(self):
        original_draw = core.draw

        def bad_draw(*args):
            fig, colors = original_draw(*args)
            from matplotlib.collections import PathCollection
            points = next(p for p in fig.axes[0].collections if isinstance(p, PathCollection))
            coordinates = points.get_offsets().copy()
            coordinates[0, 0] += .01
            points.set_offsets(coordinates)
            return fig, colors

        with patch.object(core, "draw", side_effect=bad_draw):
            with self.assertRaisesRegex(SpecError, "source or canvas QA"):
                self.run_preview()
        out = self.root / "outputs"
        self.assertFalse(self.read(out / "manifest.json")["valid_outputs"])
        qa = self.read(out / "box-points/qa.json")
        self.assertFalse(qa["valid_outputs"])
        self.assertIn("actual observation coordinates differ", " ".join(qa["source_to_artist_audit"]["issues"]))
        self.assertFalse((out / "ecdf").exists())

    def test_point_alpha_applies_only_to_raw_marks_and_rejects_invalid_values(self):
        request = deepcopy(self.request)
        request["options"] = {"include_violin": True}
        _, _, default = preview.prepare_request(self.source.read_bytes(), request)
        request["options"]["point_alpha"] = 1
        _, _, opaque = preview.prepare_request(self.source.read_bytes(), request)
        for (choice, default_spec), (_, opaque_spec) in zip(default, opaque):
            with self.subTest(choice=choice):
                if choice == "ecdf":
                    self.assertEqual(default_spec, opaque_spec)
                else:
                    self.assertEqual(default_spec["options"]["alpha"], .65)
                    self.assertEqual(opaque_spec["options"]["alpha"], 1)
                    adjusted = deepcopy(default_spec)
                    adjusted["options"]["alpha"] = 1
                    self.assertEqual(adjusted, opaque_spec)
                    data = core.prepare(self.source, default_spec)
                    layout, typography, rc = core.setup(default_spec)
                    with core.plt.rc_context(rc):
                        fig, _ = core.draw(data, default_spec, layout, typography, core.statistics(data, default_spec))
                        from matplotlib.collections import PathCollection
                        points = [p for p in fig.axes[0].collections if isinstance(p, PathCollection)]
                        self.assertTrue(all(p.get_alpha() == .65 for p in points))
                        self.assertTrue(all(core.np.array_equal(p.get_sizes(), [9]) for p in points))
                        core.plt.close(fig)
        for index, value in enumerate([0, -.1, 1.01, float("nan"), float("inf"), True, "0.65"]):
            with self.subTest(alpha=value):
                request["options"]["point_alpha"] = value
                self.request_path.write_text(json.dumps(request))
                out = self.root / f"bad-alpha-{index}"
                with self.assertRaisesRegex(SpecError, "point_alpha"):
                    preview.preview(self.source, self.request_path, out)
                self.assertFalse(out.exists())

    def test_actual_point_alpha_corruption_invalidates_exports_with_numeric_values_retained(self):
        original_draw = core.draw

        def bad_alpha(*args):
            fig, colors = original_draw(*args)
            from matplotlib.collections import PathCollection
            points = next(p for p in fig.axes[0].collections if isinstance(p, PathCollection))
            points.set_alpha(1)
            return fig, colors

        with patch.object(core, "draw", side_effect=bad_alpha):
            with self.assertRaisesRegex(SpecError, "source or canvas QA"):
                self.run_preview()
        qa = self.read(self.root / "outputs/box-points/qa.json")
        self.assertFalse(qa["valid_outputs"])
        audit = qa["source_to_artist_audit"]
        self.assertTrue(audit["numeric_values_unchanged"])
        self.assertIn("actual observation alpha differs", " ".join(audit["issues"]))
        self.assertEqual(audit["intended_point_alpha"], .65)

    def test_source_mutation_after_render_cannot_claim_a_passing_set(self):
        original_render = preview._render_distribution

        def mutate(*args):
            result = original_render(*args)
            self.source.write_bytes(self.source.read_bytes().replace(b"1.0000", b"1.0001"))
            return result

        with patch.object(preview, "_render_distribution", side_effect=mutate):
            with self.assertRaisesRegex(SpecError, "source integrity"):
                self.run_preview()
        qa = self.read(self.root / "outputs/qa.json")
        self.assertFalse(qa["source_unchanged"])
        self.assertFalse(qa["valid_outputs"])

    def test_fresh_directory_and_symlink_are_never_overwritten(self):
        existing = self.root / "accepted"
        existing.mkdir()
        (existing / "panel.png").write_text("accepted bytes")
        dangling = self.root / "dangling"
        dangling.symlink_to(self.root / "missing")
        for name in ("accepted", "dangling"):
            with self.assertRaisesRegex(SpecError, "fresh directory"):
                self.run_preview(name=name)
        self.assertEqual((existing / "panel.png").read_text(), "accepted bytes")
        self.assertTrue(dangling.is_symlink())

    def test_cli_contract_and_extracted_scripts_are_portable(self):
        portable = self.root / "extracted plugin" / "scripts"
        portable.mkdir(parents=True)
        for filename in ("preview_choices.py", *preview.HELPERS):
            shutil.copy2(SCRIPT.with_name(filename), portable / filename)
        script = portable / "preview_choices.py"
        described = subprocess.run([sys.executable, str(script), "--describe-contract"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(described.returncode, 0, described.stderr)
        self.assertIn("request", json.loads(described.stdout))
        self.request_path.write_text(json.dumps(self.request))
        out = self.root / "portable outputs"
        result = subprocess.run([sys.executable, str(script), "--data", str(self.source), "--request", str(self.request_path), "--out", str(out)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["choices"], ["box-points", "ecdf"])
        self.assertTrue(self.read(out / "manifest.json")["valid_outputs"])
        rejected = subprocess.run([sys.executable, str(script), "--describe-contract", "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)


SpecError = preview.SpecError

if __name__ == "__main__":
    unittest.main()
