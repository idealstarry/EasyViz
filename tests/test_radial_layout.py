"""Radial layout keeps identities, real class boundaries, and explicit capacity."""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/radial_layout.py"
loader = importlib.util.spec_from_file_location("easyviz_radial_layout", SCRIPT)
radial = importlib.util.module_from_spec(loader)
loader.loader.exec_module(radial)


class CategoryRunTests(unittest.TestCase):
    def test_seam_merge_preserves_original_items_and_exact_boundaries(self):
        result = radial.merge_category_runs(["a", "b", "c", "d", "e"], ["X", "Y", "Y", "Z", "X"], circular=True, start_angle_deg=-90)
        self.assertEqual(result["item_ids"], ["a", "b", "c", "d", "e"])
        self.assertEqual(result["runs"][0]["item_ids"], ["e", "a"])
        self.assertEqual(result["runs"][0]["index_intervals"], [[4, 5], [0, 1]])
        self.assertTrue(result["runs"][0]["wraps_seam"])
        self.assertEqual(result["runs"][0]["start_angle_deg"], 198)
        self.assertEqual(result["runs"][0]["end_angle_deg"], 342)
        self.assertEqual(result["runs"][1]["item_ids"], ["b", "c"])
        self.assertEqual([item["run_index"] for item in result["items"]], [0, 1, 1, 2, 0])
        for left, right in zip(result["items"], result["items"][1:]):
            self.assertEqual(left["end_angle_deg"], right["start_angle_deg"])
        self.assertEqual(sum(run["end_angle_deg"] - run["start_angle_deg"] for run in result["runs"]), 360)

    def test_partial_and_linear_tracks_keep_terminal_categories_separate(self):
        for sweep in (180, 360):
            result = radial.merge_category_runs(["a", "b", "c"], ["X", "Y", "X"], sweep_angle_deg=sweep)
            self.assertEqual(len(result["runs"]), 3)
            self.assertFalse(any(run["wraps_seam"] for run in result["runs"]))
        with self.assertRaises(ValueError):
            radial.merge_category_runs(["a"], ["X"], circular=True, sweep_angle_deg=359)

    def test_single_class_and_single_item_remain_one_exact_turn(self):
        for ids in (["a"], ["a", "b", "c"]):
            result = radial.merge_category_runs(ids, ["same"] * len(ids), circular=True)
            self.assertEqual(len(result["runs"]), 1)
            self.assertEqual(result["runs"][0]["item_ids"], ids)
            self.assertEqual(result["runs"][0]["index_intervals"], [[0, len(ids)]])
            self.assertEqual(result["runs"][0]["end_angle_deg"], 360)
            self.assertFalse(result["runs"][0]["wraps_seam"])

    def test_literal_ids_and_category_labels_are_not_sorted_or_normalized(self):
        result = radial.merge_category_runs(["010", "1", "001"], ["A", " A", "A"])
        self.assertEqual(result["item_ids"], ["010", "1", "001"])
        self.assertEqual([run["category"] for run in result["runs"]], ["A", " A", "A"])
        for kwargs in ({"item_ids": ["a", "a"], "categories": ["X", "X"]},
                       {"item_ids": ["a"], "categories": ["X", "Y"]},
                       {"item_ids": ["a"], "categories": [True]},
                       {"item_ids": ["a"], "categories": ["X"], "circular": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                radial.merge_category_runs(**kwargs)

    def test_unrepresentable_intervals_and_oversized_integers_fail_cleanly(self):
        for start in (1e100, 10 ** 1000):
            with self.subTest(start=str(start)[:15]), self.assertRaises(ValueError):
                radial.merge_category_runs(["a", "b"], ["A", "B"], start_angle_deg=start)


class BoundedLabelsTests(unittest.TestCase):
    def labels(self, angles, extents=2):
        if isinstance(extents, (int, float)):
            extents = [extents] * len(angles)
        return [{"id": f"item-{i}", "angle_deg": a, "extent_deg": e} for i, (a, e) in enumerate(zip(angles, extents))]

    def test_crowded_neighbors_move_both_directions_with_minimum_total_shift(self):
        result = radial.pack_labels_in_window(self.labels([10, 11, 12]), window_deg=[0, 20], radius_mm=180 / math.pi, gap_mm=1)
        self.assertEqual(result["status"], "ready")
        self.assertEqual([label["placed_angle_deg"] for label in result["labels"]], [8, 11, 14])
        self.assertEqual([label["shift_deg"] for label in result["labels"]], [-2, 0, 2])
        self.assertFalse(result["circular_seam_checked"])

    def test_variable_measured_extents_fit_window_without_touching(self):
        result = radial.pack_labels_in_window(self.labels([3, 3.2, 4], [2, 4, 2]), window_deg=[0, 12], radius_mm=180 / math.pi, gap_mm=1, max_shift_deg=5)
        self.assertEqual(result["status"], "ready")
        labels = result["labels"]
        self.assertEqual([item["id"] for item in labels], ["item-0", "item-1", "item-2"])
        self.assertGreaterEqual(labels[0]["placed_angle_deg"] - labels[0]["extent_deg"] / 2, 0)
        self.assertLessEqual(labels[-1]["placed_angle_deg"] + labels[-1]["extent_deg"] / 2, 12)
        for a, b in zip(labels, labels[1:]):
            self.assertGreaterEqual(b["placed_angle_deg"] - a["placed_angle_deg"], (a["extent_deg"] + b["extent_deg"]) / 2 + 1 - 1e-10)
        self.assertLessEqual(result["max_shift_used_deg"], 5)

    def test_mm_and_degrees_have_equivalent_geometry_and_unwrapped_order(self):
        labels = self.labels([355, 356, 370])
        mm = [{"id": item["id"], "angle_deg": item["angle_deg"], "extent_mm": math.radians(item["extent_deg"]) * 40} for item in labels]
        a = radial.pack_labels_in_window(labels, window_deg=[350, 380], radius_mm=40)
        b = radial.pack_labels_in_window(mm, window_deg=[350, 380], radius_mm=40)
        self.assertEqual(a["status"], b["status"])
        for x, y in zip(a["labels"], b["labels"]):
            self.assertAlmostEqual(x["placed_angle_deg"], y["placed_angle_deg"])

    def test_impossible_window_keeps_all_ids_without_partial_or_clipped_positions(self):
        result = radial.pack_labels_in_window(self.labels([2, 3, 4], 3), window_deg=[0, 8], radius_mm=40)
        self.assertEqual(result["status"], "infeasible")
        self.assertIn("occupied_extents_and_gaps_exceed_window", result["issues"])
        self.assertEqual(len(result["labels"]), 3)
        self.assertTrue(all(item["placed_angle_deg"] is None for item in result["labels"]))

    def test_displacement_limit_can_make_an_otherwise_large_window_infeasible(self):
        result = radial.pack_labels_in_window(self.labels([5, 5.1, 5.2]), window_deg=[0, 90], radius_mm=40, max_shift_deg=.2)
        self.assertEqual(result["status"], "infeasible")
        self.assertEqual(result["issues"], ["window_or_shift_bounds_infeasible"])
        self.assertTrue(all(item["placed_angle_deg"] is None for item in result["labels"]))

    def test_single_label_respects_window_and_optional_zero_displacement(self):
        result = radial.pack_labels_in_window(self.labels([0], 4), window_deg=[0, 10], radius_mm=30)
        self.assertEqual(result["labels"][0]["placed_angle_deg"], 2)
        locked = radial.pack_labels_in_window(self.labels([0], 4), window_deg=[0, 10], radius_mm=30, max_shift_deg=0)
        self.assertEqual(locked["status"], "infeasible")
        fixed = radial.pack_labels_in_window(self.labels([5]), window_deg=[0, 10], radius_mm=30, max_shift_deg=0)
        self.assertEqual(fixed["labels"][0]["placed_angle_deg"], 5)

    def test_bad_types_nonfinite_values_duplicates_and_implicit_sort_are_rejected(self):
        valid = self.labels([5, 6])
        cases = [({"labels": self.labels([6, 5])}),
                 ({"labels": [valid[0], valid[0]]}),
                 ({"labels": [{"id": "a", "angle_deg": math.nan, "extent_mm": 2}]}),
                 ({"labels": [{"id": "a", "angle_deg": 2, "extent_deg": True}]}),
                 ({"radius_mm": True}), ({"gap_mm": -1}), ({"max_shift_deg": math.inf}),
                 ({"window_deg": [10, 0]})]
        for extra in cases:
            kwargs = {"labels": valid, "window_deg": [0, 20], "radius_mm": 20, **extra}
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                radial.pack_labels_in_window(**kwargs)

    def test_derived_nonfinite_spans_are_rejected_instead_of_json_infinity(self):
        with self.assertRaises(ValueError):
            radial.pack_labels_in_window([{"id": "a", "angle_deg": 1, "extent_mm": 1e308}], window_deg=[0, 10], radius_mm=1e-300)
        with self.assertRaises(ValueError):
            radial.pack_labels_in_window(self.labels([2, 3, 4], 1e308), window_deg=[0, 10], radius_mm=30)


class RadialGeometryTests(unittest.TestCase):
    def test_report_separates_tree_tracks_label_gap_and_guides_without_ratio_rule(self):
        result = radial.radial_geometry(30, [{"id": "source", "inner_radius_mm": 34, "width_mm": 2}],
                                        label_radius_mm=38, label_depth_mm=5, center_mm=[50, 50], canvas_mm=[150, 100],
                                        guides=[{"id": "key", "bbox_mm": [100, 60, 25, 10]}])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["tracks"][0]["gap_from_previous_envelope_mm"], 4)
        self.assertEqual(result["label_gap_from_tracks_mm"], 2)
        self.assertEqual(result["radial_envelope_mm"], [7, 7, 86, 86])
        self.assertFalse(result["aesthetic_threshold_applied"])
        self.assertAlmostEqual(result["tree_area_fraction_of_outer_track_disk"], (30 / 36) ** 2)

    def test_overlap_and_canvas_failures_are_reported_without_geometry_repair(self):
        result = radial.radial_geometry(30, [{"id": "source", "inner_radius_mm": 29, "width_mm": 2}],
                                        label_radius_mm=30, label_depth_mm=5, center_mm=[20, 20], canvas_mm=[80, 80],
                                        guides=[{"id": "key", "bbox_mm": [25, 25, 15, 5]}])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["tracks"][0]["inner_radius_mm"], 29)
        codes = [item["code"] for item in result["issues"]]
        self.assertIn("radial_track_overlap", codes)
        self.assertIn("label_anchors_inside_radial_tracks", codes)
        self.assertIn("radial_envelope_outside_canvas", codes)
        self.assertIn("guide_intersects_radial_envelope", codes)

    def test_literal_order_and_finite_physical_dimensions_are_enforced(self):
        for tracks in ([{"id": "x", "inner_radius_mm": 30, "width_mm": 0}],
                       [{"id": "x", "inner_radius_mm": 30, "width_mm": 1}, {"id": "x", "inner_radius_mm": 32, "width_mm": 1}],
                       [{"id": "x", "inner_radius_mm": 35, "width_mm": 1}, {"id": "y", "inner_radius_mm": 32, "width_mm": 1}]):
            with self.subTest(tracks=tracks), self.assertRaises(ValueError):
                radial.radial_geometry(20, tracks)
        with self.assertRaises(ValueError):
            radial.radial_geometry(20, [], label_depth_mm=2)
        with self.assertRaises(ValueError):
            radial.radial_geometry(math.inf, [])
        with self.assertRaises(ValueError):
            radial.radial_geometry(1e308, [])


class RadialCliTests(unittest.TestCase):
    def test_contract_and_stdin_request_need_no_plotting_dependency(self):
        result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--describe-contract"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("labels", json.loads(result.stdout)["operations"])
        payload = {"operation": "runs", "item_ids": ["001", "002"], "categories": ["a", "a"], "circular": True}
        result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--input", "-"], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["runs"][0]["item_ids"], ["001", "002"])

    def test_malformed_request_is_rejected_and_capacity_has_distinct_exit_status(self):
        for payload in ({"operation": "labels", "labels": [], "unknown": True}, {"operation": []}, []):
            result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--input", "-"], input=json.dumps(payload), capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("error", json.loads(result.stderr))
        payload = {"operation": "labels", "labels": [{"id": "a", "angle_deg": 1, "extent_deg": 20}], "window_deg": [0, 10], "radius_mm": 20}
        result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--input", "-"], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "infeasible")


if __name__ == "__main__":
    unittest.main()
