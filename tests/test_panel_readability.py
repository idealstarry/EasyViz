"""Actual artist measurements are advisory and leave panel geometry/pixels intact."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("MPLCONFIGDIR", "/tmp/easyviz-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


readability = load("panel_readability_test_helper", "panel_readability.py")
elements = load("panel_readability_test_elements", "figure_elements.py")
core = load("panel_readability_test_core", "render.py")


class ReadabilityTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def figure(self, *, dpi=100):
        fig, ax = plt.subplots(figsize=(4, 3), dpi=dpi)
        return fig, ax

    def test_scatter_uses_actual_circle_physical_span_and_counts_zero_separately(self):
        for dpi in (72, 240):
            fig, ax = self.figure(dpi=dpi)
            artist = ax.scatter([1, 2, 3], [2, 4, 3], s=[0, 1, 36], color="#29ACF3", linewidths=0)
            elements.register(fig, artist, "point-group", "Observed fractions")
            record = readability.measure(fig)
            points = next(item["points"] for item in record["artists"] if item["role"] == "point-group")
            self.assertEqual(points["finite_mark_count"], 3)
            self.assertEqual(points["zero_size_parameter_count"], 1)
            self.assertEqual(points["positive_size_parameter_count"], 2)
            self.assertEqual(points["size_parameter_pt2_range"], [0, 36])
            np.testing.assert_allclose(points["positive_marker_bbox_width_mm_range"], [25.4 / 72, 6 * 25.4 / 72])
            self.assertEqual(points["small_visible_count"], 0)
            np.testing.assert_array_equal(artist.get_sizes(), [0, 1, 36])
            self.assertEqual(record["totals"]["zero_size_parameters"], 1)

    def test_rgba_alpha_is_composited_once_and_hollow_edge_carries_contrast(self):
        fig, ax = self.figure()
        filled = ax.scatter([1], [1], s=.25, color="black", alpha=.5, linewidths=0)
        hollow = ax.scatter([2], [2], s=.25, facecolors="none", edgecolors="black", alpha=.5, linewidths=.4)
        elements.register(fig, filled, "point-group", "Filled", key="filled")
        elements.register(fig, hollow, "point-group", "Hollow", key="hollow")
        report = readability.measure(fig, thresholds={"small_point_span_mm": .5})
        contrast = (1.05 / (.21404114048223255 + .05))  # black .5 over white = RGB .5
        for item in report["artists"]:
            if item["role"] == "point-group":
                np.testing.assert_allclose(item["points"]["visible_component_contrast_ratio_range"], [contrast, contrast])
                self.assertEqual(item["points"]["low_contrast_small_count"], 0)
        hollow_points = next(item["points"] for item in report["artists"] if item["label"] == "Hollow")
        self.assertAlmostEqual(hollow_points["positive_outer_span_mm_range"][0], .9 * 25.4 / 72)
        np.testing.assert_array_equal(filled.get_alpha(), .5)

    def test_faint_small_points_warn_against_actual_axes_background(self):
        fig, ax = self.figure()
        ax.set_facecolor("#F2F2F2")
        faint = ax.scatter([1, 2], [3, 2], s=[.04, 16], color="#FCFCFC", linewidths=0)
        elements.register(fig, faint, "point-group", "Faint observations")
        report = readability.measure(fig)
        self.assertEqual(report["totals"]["small_visible_marks"], 1)
        self.assertEqual(report["totals"]["low_contrast_small_marks"], 1)
        self.assertEqual({warning["kind"] for warning in report["warnings"]}, {"small_positive_marks", "low_contrast_small_marks"})
        self.assertTrue(report["advisory_only"])

    def test_linecollection_and_line2d_widths_use_registered_roles_and_exempt_white_seams(self):
        fig, ax = self.figure()
        line, = ax.plot([0, 1], [0, 1], color="black", linewidth=.1)
        summary = LineCollection([[(0, 1), (1, 1)], [(0, 2), (1, 2)]], linewidths=[.5, 1], colors=["black", "#29ACF3"])
        grid = LineCollection([[(0, .5), (1, .5)]], colors="white", linewidths=.08)
        ax.add_collection(summary)
        ax.add_collection(grid)
        elements.register(fig, line, "fit-line", "Regression")
        elements.register(fig, summary, "summary-line", "IQR")
        elements.register(fig, grid, "heatmap-grid", "Cell seams")
        report = readability.measure(fig)
        self.assertEqual(report["stroke_roles"]["fit-line"]["width_pt_range"], [.1, .1])
        self.assertEqual(report["stroke_roles"]["summary-line"]["width_pt_range"], [.5, 1])
        self.assertEqual([warning["role"] for warning in report["warnings"]], ["fit-line"])
        self.assertEqual(report["totals"]["thin_data_stroke_artists"], 1)

    def test_fallback_custom_artists_and_legend_bbox_measurements(self):
        fig, ax = self.figure()
        ax.plot([1, 2, 3], [3, 1, 2], marker="o", markersize=4, markeredgewidth=0, linewidth=.8, color="black", label="Measurements")
        ax.legend()
        report = readability.measure(fig)
        line = next(item for item in report["artists"] if item["role"] == "unregistered-line")
        self.assertEqual(line["mapping"], "axes-fallback")
        self.assertEqual(line["points"]["markersize_pt_range"], [4, 4])
        self.assertEqual(line["strokes"]["positive_width_pt_range"], [.8, .8])
        legend = next(item["legend"] for item in report["artists"] if "legend" in item)
        self.assertGreater(legend["canvas_area_fraction"], 0)
        self.assertLess(legend["canvas_area_fraction"], 1)
        self.assertIn("occlusion", legend["scope"])

    def test_zero_masked_and_fully_transparent_marks_are_not_low_contrast_small_marks(self):
        fig, ax = self.figure()
        artist = ax.scatter([1, 2, 3], np.ma.array([2, 3, 4], mask=[False, True, False]), s=[0, .04, .04], alpha=0, linewidths=0)
        elements.register(fig, artist, "point-group", "Fractions")
        report = readability.measure(fig)
        points = next(item["points"] for item in report["artists"] if "points" in item)
        self.assertEqual(points["zero_size_parameter_count"], 1)
        self.assertEqual(points["masked_or_nonfinite_count"], 1)
        self.assertEqual(points["positive_without_visible_face_or_edge_count"], 1)
        self.assertEqual(report["totals"]["low_contrast_small_marks"], 0)
        self.assertEqual(report["warning_count"], 0)

    def test_measure_keeps_rendered_pixels_and_artists_unchanged_and_report_bounded(self):
        fig, ax = self.figure()
        for index in range(6):
            ax.scatter([index], [index], s=.04, color="#F9F9F9", linewidths=0)
        ax.plot([0, 5], [1, 4], linewidth=.1, color="black")
        fig.canvas.draw()
        before = np.asarray(fig.canvas.buffer_rgba()).copy()
        sizes = [artist.get_sizes().copy() for artist in ax.collections]
        report = readability.measure(fig, max_items=2, max_warnings=2)
        np.testing.assert_array_equal(np.asarray(fig.canvas.buffer_rgba()), before)
        for expected, artist in zip(sizes, ax.collections):
            np.testing.assert_array_equal(artist.get_sizes(), expected)
        self.assertEqual(len(report["artists"]), 2)
        self.assertEqual(len(report["warnings"]), 2)
        self.assertGreater(report["artists_omitted_from_detail"], 0)
        self.assertGreater(report["warnings_omitted_from_detail"], 0)
        json.dumps(report, allow_nan=False)

    def test_core_advisories_do_not_fail_qa_or_change_legacy_export_pixels(self):
        with tempfile.TemporaryDirectory(prefix="easyviz-readability-") as directory:
            root = Path(directory)
            source = root / "input.csv"
            source.write_text("x,y\n1,3\n2,4\n3,2\n")
            spec = {"chart": "scatter", "fields": {"x": "x", "y": "y"},
                    "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
                    "options": {"point_area_pt2": .04, "point_color": "#FBFBFB"}, "formats": ["png"]}
            qa = core.render(source, deepcopy(spec), root / "actual")
            self.assertEqual(qa["status"], "pass")
            self.assertTrue(qa["readability"]["advisory_only"])
            self.assertGreater(qa["readability"]["warning_count"], 0)
            settings = json.loads((root / "actual/settings.json").read_text())
            expected = hashlib.sha256((SCRIPTS / "panel_readability.py").read_bytes()).hexdigest()
            self.assertEqual(settings["renderer"]["readability_helper_sha256"], expected)
            with patch.object(core.panel_readability, "measure", return_value={"advisory_only": True}):
                core.render(source, deepcopy(spec), root / "control")
            self.assertEqual((root / "actual/panel.png").read_bytes(), (root / "control/panel.png").read_bytes())

    def test_invalid_thresholds_are_rejected_without_mutating_artists(self):
        fig, ax = self.figure()
        for thresholds in ({"thin_stroke_pt": 0}, {"thin_stroke_pt": float("nan")}, {"thin_stroke_pt": True}, {"unknown": 1}):
            with self.subTest(thresholds=thresholds), self.assertRaises(ValueError):
                readability.measure(fig, thresholds=thresholds)

    def test_all_nonfinite_line_segments_do_not_create_thin_stroke_flags(self):
        fig, ax = self.figure()
        line, = ax.plot([1, 2], [float("nan"), float("nan")], linewidth=.01, color="black")
        collection = LineCollection([[(1, float("nan")), (2, float("nan"))]], colors="black", linewidths=.01)
        ax.add_collection(collection)
        elements.register(fig, line, "fit-line", "Undefined fit")
        elements.register(fig, collection, "summary-line", "Undefined summary")
        report = readability.measure(fig)
        self.assertEqual(report["totals"]["thin_data_stroke_artists"], 0)
        self.assertEqual(report["warning_count"], 0)

    def test_violin_boundary_reads_edge_width_without_treating_fill_as_points(self):
        fig, ax = self.figure()
        violin = ax.violinplot([[1, 2, 3, 4, 5]], showextrema=False)["bodies"][0]
        violin.set_alpha(None)
        violin.set_facecolor((.2, .7, 1, .05))
        violin.set_edgecolor("black")
        violin.set_linewidth(.5)
        elements.register(fig, violin, "distribution", "Violin")
        report = readability.measure(fig)
        self.assertEqual(report["stroke_roles"]["distribution"]["width_pt_range"], [.5, .5])
        self.assertEqual(report["totals"]["point_artists"], 0)
        self.assertEqual(report["totals"]["low_contrast_small_marks"], 0)


if __name__ == "__main__":
    unittest.main()
