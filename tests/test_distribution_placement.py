"""Physical circle spacing must preserve observations and final panel geometry."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from PIL import Image, ImageChops
from pypdf import PdfReader

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/render.py"
loader = importlib.util.spec_from_file_location("distribution_placement_renderer", SCRIPT)
core = importlib.util.module_from_spec(loader)
loader.loader.exec_module(core)


class PhysicalPackingTests(unittest.TestCase):
    def test_tied_values_fit_without_changing_numeric_coordinates(self):
        numeric = np.full(7, 37.25)
        before = numeric.copy()
        offsets, report = core.pack_distribution_points(numeric, 3, 11.4, gap_pt=.3, seed=7)
        audited = core.distribution_collision_report(np.column_stack((offsets, numeric)), 3, .3)
        np.testing.assert_array_equal(numeric, before)
        self.assertLessEqual(abs(offsets).max(), 11.4)
        self.assertEqual(report["fallback_count"], 0)
        self.assertEqual(audited["spacing_violation_pairs"], 0)
        self.assertAlmostEqual(audited["minimum_center_distance_pt"], 3.3, places=8)

    def test_close_numeric_values_use_circle_geometry_instead_of_fixed_bins(self):
        numeric = np.array([0., .1, .1, 2.2, 4.9, 5., 7., 7.01, 9.])
        offsets, report = core.pack_distribution_points(numeric, 3, 15, gap_pt=.5, seed=3)
        audited = core.distribution_collision_report(np.column_stack((offsets, numeric)), 3, .5)
        self.assertEqual(audited["status"], "pass")
        self.assertEqual(report["fallback_count"], 0)
        self.assertGreaterEqual(audited["minimum_center_distance_pt"], 3.5 - 1e-8)

    def test_seed_replays_equal_values_and_breaks_ties(self):
        numeric = np.array([1.] * 7 + [12.] * 7)
        first, report = core.pack_distribution_points(numeric, 3, 11.4, seed=49)
        repeated, repeated_report = core.pack_distribution_points(numeric, 3, 11.4, seed=49)
        different, _ = core.pack_distribution_points(numeric, 3, 11.4, seed=50)
        np.testing.assert_array_equal(first, repeated)
        self.assertEqual(report, repeated_report)
        self.assertFalse(np.array_equal(first, different))

    def test_large_impossible_group_reports_exact_pair_multiplicity(self):
        numeric = np.zeros(400)
        offsets, report = core.pack_distribution_points(numeric, 3, 5, gap_pt=.3, seed=11)
        audited = core.distribution_collision_report(np.column_stack((offsets, numeric)), 3, .3)
        distances = abs(offsets[:, None] - offsets[None, :])
        expected = int(np.count_nonzero(np.triu(distances < 3 - 1e-8, 1)))
        self.assertEqual(len(offsets), 400)
        self.assertTrue(np.isfinite(offsets).all())
        self.assertLessEqual(abs(offsets).max(), 5)
        self.assertGreater(report["fallback_count"], 0)
        self.assertEqual(audited["overlapping_circle_pairs"], expected)
        self.assertEqual(audited["status"], "needs_revision")

    def test_zero_width_lane_keeps_all_points_and_reports_all_pairs(self):
        offsets, report = core.pack_distribution_points(np.zeros(12), 3, 0, seed=9)
        audited = core.distribution_collision_report(np.column_stack((offsets, np.zeros(12))), 3, .3)
        np.testing.assert_array_equal(offsets, np.zeros(12))
        self.assertEqual(audited["overlapping_circle_pairs"], 66)
        self.assertEqual(report["fallback_count"], 11)

    def test_ten_thousand_ties_preserve_rows_and_count_compressed_collisions(self):
        values = np.zeros(10000)
        offsets, report = core.pack_distribution_points(values, 3, 0, seed=17)
        audited = core.distribution_collision_report(np.column_stack((offsets, values)), 3, .3)
        self.assertEqual(len(offsets), 10000)
        self.assertEqual(report["fallback_count"], 9999)
        self.assertEqual(audited["overlapping_circle_pairs"], 10000 * 9999 // 2)
        self.assertEqual(audited["spacing_violation_pairs"], 10000 * 9999 // 2)
        self.assertEqual(audited["status"], "needs_revision")

    def test_separated_values_stay_centered_and_no_fallback_is_invented(self):
        offsets, report = core.pack_distribution_points(np.arange(500) * 4., 3, .2, seed=12)
        np.testing.assert_array_equal(offsets, np.zeros(500))
        self.assertEqual(report["fallback_count"], 0)

    def test_invalid_geometry_rejected(self):
        for values, diameter, maximum, gap in (([1, np.nan], 3, 4, .3), ([1], 0, 4, .3), ([1], 3, -1, .3), ([1], 3, 4, -1)):
            with self.subTest(values=values, diameter=diameter, maximum=maximum, gap=gap):
                with self.assertRaises(core.SpecError):
                    core.pack_distribution_points(values, diameter, maximum, gap_pt=gap)


class DistributionPlacementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-distribution-placement-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.source.write_text("id,g,v\n" + "".join(f"{i:03d},A,5\n" for i in range(1, 8))
                               + "".join(f"{i:03d},B,{value}\n" for i, value in enumerate([2, 3, 4, 5, 6, 7, 8], 8)))
        self.spec = {"chart": "distribution", "fields": {"group": "g", "value": "v", "unit": "id"},
                     "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8,
                                "dpi": 120, "margins": {"left": .19, "right": .87, "bottom": .23, "top": .91}},
                     "labels": {"x": "Condition", "y": "Observed measurement"},
                     "options": {"point_layout": "beeswarm", "point_area_pt2": 9, "point_gap_pt": .3, "point_max_offset_mm": 4},
                     "formats": ["svg", "pdf", "png"], "seed": 23}

    def tearDown(self):
        core.plt.close("all")
        self.temp.cleanup()

    def draw(self, spec=None):
        spec = deepcopy(self.spec if spec is None else spec)
        data = core.prepare(self.source, spec)
        layout, typography, rc = core.setup(spec)
        with core.plt.rc_context(rc):
            fig, _ = core.draw(data, spec, layout, typography, core.statistics(data, spec))
        return fig, data, layout

    def test_vertical_and_horizontal_artist_values_ids_and_size_preserved(self):
        source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        for orientation in ("vertical", "horizontal"):
            with self.subTest(orientation=orientation):
                spec = deepcopy(self.spec)
                spec["options"]["orientation"] = orientation
                fig, data, _ = self.draw(spec)
                numeric_axis = 1 if orientation == "vertical" else 0
                for element in fig._easyviz_elements:
                    if element["role"] == "point-group":
                        artist = element["_artist"]
                        expected = data.loc[data.g == element["label"], "v"].to_numpy(float)
                        np.testing.assert_array_equal(artist.get_offsets()[:, numeric_axis], expected)
                        np.testing.assert_array_equal(artist.get_sizes(), [9])
                        self.assertFalse(set(element["editable"]) & {"x", "y", "value", "size"})
                self.assertEqual(data.id.tolist(), [f"{i:03d}" for i in range(1, 15)])
                self.assertEqual(fig._easyviz_point_layout["status"], "pass")
                self.assertEqual(fig._easyviz_point_layout["categorical_boundary_rows"], [])
                core.plt.close(fig)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), source_hash)

    def test_auto_fit_and_log_scale_use_final_transform(self):
        for orientation in ("vertical", "horizontal"):
            with self.subTest(orientation=orientation):
                spec = deepcopy(self.spec)
                spec["layout"].pop("margins")
                spec["layout"]["auto_fit"] = True
                spec["options"].update(orientation=orientation)
                spec["options"]["y_scale" if orientation == "vertical" else "x_scale"] = "log"
                fig, data, layout = self.draw(spec)
                report = fig._easyviz_point_layout
                self.assertEqual(report["status"], "pass")
                self.assertEqual(report["overlapping_circle_pairs"], 0)
                self.assertLessEqual(max(group["actual_max_offset_mm"] for group in report["groups"]), 4 + 1e-8)
                self.assertEqual(layout["width_mm"], 120)
                self.assertEqual(fig._easyviz_auto_layout["status"], "pass")
                self.assertEqual(data.v.tolist(), [5] * 7 + [2, 3, 4, 5, 6, 7, 8])
                core.plt.close(fig)

    def test_margin_and_category_capacity_limit_requested_lane(self):
        self.source.write_text("g,v\n" + "".join(f"G{i},{10 * i}\n" for i in range(7)))
        spec = deepcopy(self.spec)
        spec["fields"].pop("unit")
        spec["colors"] = {f"G{i}": f"#{i * 28 + 25:02x}5070" for i in range(7)}
        spec["layout"]["margins"].update(left=.3, right=.75)
        spec["options"]["point_max_offset_mm"] = 50
        fig, _, _ = self.draw(spec)
        report = fig._easyviz_point_layout
        self.assertEqual(report["status"], "pass")
        self.assertTrue(all(group["available_max_offset_mm"] < 5 for group in report["groups"]))
        self.assertEqual(report["categorical_boundary_rows"], [])

    def test_oversized_circles_report_category_boundary_failure(self):
        self.source.write_text("id,g,v\n001,A,5\n002,B,8\n")
        spec = deepcopy(self.spec)
        spec["layout"]["margins"].update(left=.4, right=.5)
        spec["options"]["point_area_pt2"] = 1600
        fig, data, _ = self.draw(spec)
        report = fig._easyviz_point_layout
        self.assertEqual(report["status"], "needs_revision")
        self.assertEqual(report["categorical_boundary_rows"], [1, 2])
        self.assertEqual(len(data), 2)
        self.assertEqual(report["diameter_pt"], 40)

    def test_violin_summary_uses_identical_value_preserving_point_contract(self):
        self.source.write_text("id,g,v\n" + "".join(f"{i:03d},A,{value}\n" for i, value in enumerate([4.8, 5, 5, 5, 5, 5, 5, 5, 5.2], 1)))
        spec = deepcopy(self.spec)
        spec["options"]["kind"] = "violin"
        fig, data, _ = self.draw(spec)
        report = fig._easyviz_point_layout
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["overlapping_circle_pairs"], 0)
        artist = next(element["_artist"] for element in fig._easyviz_elements if element["role"] == "point-group")
        np.testing.assert_array_equal(artist.get_offsets()[:, 1], data.v.to_numpy(float))

    def test_infeasible_output_remains_complete_and_needs_revision(self):
        self.source.write_text("id,g,v\n" + "".join(f"{i:03d},A,5\n" for i in range(1, 51)))
        out = self.root / "infeasible"
        with self.assertRaisesRegex(core.SpecError, "observation spacing conflicts"):
            core.render(self.source, self.spec, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertEqual(qa["point_layout"]["status"], "needs_revision")
        self.assertGreater(qa["point_layout"]["overlapping_circle_pairs"], 0)
        self.assertEqual(qa["input_rows"], 50)
        self.assertEqual(len(pd.read_csv(out / "plotting-data.csv")), 50)
        self.assertTrue((out / "panel.svg").is_file())
        self.assertTrue((out / "panel.pdf").is_file())
        self.assertTrue((out / "panel.png").is_file())

    def test_export_canvas_fonts_report_and_replay(self):
        original = self.source.read_bytes()
        first, second = self.root / "first", self.root / "second"
        qa = core.render(self.source, self.spec, first)
        core.render(self.source, self.spec, second)
        self.assertEqual(qa["point_layout"]["status"], "pass")
        self.assertEqual(qa["point_layout"]["placed_rows"], 14)
        settings = json.loads((first / "settings.json").read_text())
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(settings["point_layout"], qa["point_layout"])
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual((first / "plotting-data.csv").read_bytes(), (second / "plotting-data.csv").read_bytes())
        with Image.open(first / "panel.png") as a, Image.open(second / "panel.png") as b:
            self.assertIsNone(ImageChops.difference(a, b).getbbox())
            self.assertEqual(a.size, (round(120 / 25.4 * 120), round(90 / 25.4 * 120)))
        page = PdfReader(first / "panel.pdf").pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) / 72 * 25.4, 120, places=5)
        self.assertAlmostEqual(float(page.mediabox.height) / 72 * 25.4, 90, places=5)

    def test_default_jitter_replays_original_rng_and_is_explicitly_unchecked(self):
        spec = deepcopy(self.spec)
        spec["options"] = {"point_area_pt2": 9}
        fig, data, _ = self.draw(spec)
        rng = np.random.default_rng(spec["seed"])
        expected = np.concatenate((rng.uniform(-.13, .13, 7), 1 + rng.uniform(-.13, .13, 7)))
        np.testing.assert_array_equal(data._easyviz_jitter_position.to_numpy(), expected)
        self.assertEqual(fig._easyviz_point_layout["policy"], "jitter")
        self.assertEqual(fig._easyviz_point_layout["status"], "unchecked")
        self.assertNotIn("_easyviz_point_offset_pt", data)

    def test_config_types_and_ignored_options_rejected_before_input(self):
        for options in ({"point_layout": "auto"}, {"point_layout": {}},
                        {"point_layout": "jitter", "point_gap_pt": .3},
                        {"point_layout": "beeswarm", "point_max_offset_mm": "4"},
                        {"point_layout": "beeswarm", "point_gap_pt": True},
                        {"point_layout": "beeswarm", "point_max_offset_mm": 0},
                        {"point_layout": "beeswarm", "point_gap_pt": -1}):
            with self.subTest(options=options):
                spec = deepcopy(self.spec)
                spec["options"] = options
                with self.assertRaises(core.SpecError):
                    core.validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
