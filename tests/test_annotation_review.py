"""Behavioral checks for heatmap labels on new matrix shapes at fixed font size."""
import importlib.util
import json
from pathlib import Path
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/annotation_review.py"
loader = importlib.util.spec_from_file_location("easyviz_annotation_review", SCRIPT)
review = importlib.util.module_from_spec(loader)
loader.loader.exec_module(review)


class AnnotationReviewTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def heatmap(self, rows, columns, *, width_mm=88, height_mm=88, bounds=(.19, .23, .58, .65), dpi=120):
        with plt.rc_context({"font.family": "DejaVu Sans"}):
            fig = plt.figure(figsize=(width_mm / 25.4, height_mm / 25.4), dpi=dpi)
            ax = fig.add_axes(bounds)
            values = np.arange(rows * columns).reshape(rows, columns) + 100
            ax.imshow(values, aspect="auto")
            records = []
            for row in range(rows):
                for column in range(columns):
                    text = ax.text(column, row, str(values[row, column]), ha="center", va="center", fontsize=8)
                    records.append({"text": text, "row": row, "column": column})
            fig._easyviz_cell_annotations = records
            return fig, ax

    def test_crowded_new_matrix_reports_values_that_current_tick_qa_misses(self):
        fig, ax = self.heatmap(12, 14)
        size_before = fig.get_size_inches().copy()
        report = review.check_heatmap_annotations(fig, ax)
        self.assertEqual(report["status"], "needs_revision")
        self.assertEqual(report["checked_count"], 168)
        self.assertEqual(report["overflow_count"], 168)
        self.assertGreater(report["overlap_pair_count"], 0)
        self.assertTrue(any(issue["code"] == "cell_annotations_overlap" for issue in report["issues"]))
        self.assertIn("text_bbox_mm", report["issues"][0])
        np.testing.assert_array_equal(fig.get_size_inches(), size_before)
        self.assertEqual({text.get_fontsize() for text in ax.texts}, {8})
        json.dumps(report, allow_nan=False)

    def test_roomy_cells_pass_and_report_minimum_cell_dimensions(self):
        fig, ax = self.heatmap(3, 4)
        report = review.check_heatmap_annotations(fig, ax)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["checked_count"], 12)
        minimum = report["minimum_sufficient_cell_dimensions_mm"]
        self.assertGreater(minimum["width"], 0)
        self.assertGreater(minimum["height"], 0)
        first = report["cells"][0]
        self.assertLess(minimum["width"], first["cell_bbox_mm"][2])
        self.assertLess(minimum["height"], first["cell_bbox_mm"][3])

    def test_unequal_cells_and_inverted_y_use_transformed_bounds(self):
        fig, ax = self.heatmap(2, 3, width_mm=132, height_mm=44, bounds=(.1, .15, .8, .7))
        report = review.check_heatmap_annotations(fig, ax)
        self.assertEqual(report["status"], "pass")
        cells = {(cell["row"], cell["column"]): cell for cell in report["cells"]}
        width, height = cells[(0, 0)]["cell_bbox_mm"][2:]
        self.assertAlmostEqual(width, 132 * .8 / 3)
        self.assertAlmostEqual(height, 44 * .7 / 2)
        self.assertGreater(cells[(0, 0)]["cell_bbox_mm"][1], cells[(1, 0)]["cell_bbox_mm"][1])
        ax.invert_yaxis()
        reversed_report = review.check_heatmap_annotations(fig, ax)
        self.assertEqual(reversed_report["status"], "pass")
        reversed_cells = {(cell["row"], cell["column"]): cell for cell in reversed_report["cells"]}
        self.assertLess(reversed_cells[(0, 0)]["cell_bbox_mm"][1], reversed_cells[(1, 0)]["cell_bbox_mm"][1])

    def test_explicit_records_exclude_unrelated_statistical_note(self):
        fig, ax = self.heatmap(2, 2)
        ax.text(.02, .98, "p = 0.02", transform=ax.transAxes, ha="left", va="top", fontsize=8)
        report = review.check_heatmap_annotations(fig, ax)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["checked_count"], 4)
        del fig._easyviz_cell_annotations
        fallback = review.check_heatmap_annotations(fig, ax)
        self.assertEqual(fallback["checked_count"], 4)

    def test_padding_can_reveal_near_edge_fit_without_changing_labels(self):
        fig, ax = self.heatmap(1, 1)
        plain = review.check_heatmap_annotations(fig, ax, padding_mm=0)
        width = plain["cells"][0]["text_bbox_mm"][2]
        cell = plain["cells"][0]["cell_bbox_mm"]
        excessive_padding = (cell[2] - width) / 2 + .1
        padded = review.check_heatmap_annotations(fig, ax, padding_mm=excessive_padding)
        self.assertEqual(plain["status"], "pass")
        self.assertEqual(padded["status"], "needs_revision")
        self.assertEqual(padded["overflow_count"], 1)
        self.assertEqual(ax.texts[0].get_fontsize(), 8)
        for invalid in (-1, float("nan")):
            with self.assertRaisesRegex(ValueError, "padding_mm"):
                review.check_heatmap_annotations(fig, ax, padding_mm=invalid)


if __name__ == "__main__":
    unittest.main()
