"""Behavioral checks for physical legends, faithful keys, and real exports."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.transforms import Affine2D, Bbox
import numpy as np
from PIL import Image
from scipy.ndimage import label, find_objects
from marker_geometry import collection_fill_areas_pt2

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/legend_layout.py"
loader = importlib.util.spec_from_file_location("easyviz_legend_layout", SCRIPT)
helper = importlib.util.module_from_spec(loader)
loader.loader.exec_module(helper)
benchmark_loader = importlib.util.spec_from_file_location("easyviz_legend_benchmark", Path(__file__).with_name("check_legend_layouts.py"))
benchmark = importlib.util.module_from_spec(benchmark_loader)
benchmark_loader.loader.exec_module(benchmark)


class LegendLayoutTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def figure(self, width=100, height=70):
        fig = plt.figure(figsize=(width / 25.4, height / 25.4), dpi=100)
        ax = fig.add_axes([.15, .4, .7, .5])
        ax.set_axis_off()
        return fig, ax

    def size_guide(self, area_semantics="matplotlib_size_parameter", dpi=100):
        fig, ax = self.figure()
        fig.set_dpi(dpi)
        manager = helper.LegendLayout(fig, ax, {"legend": 8}, {
            "size": {"position": "manual", "anchor_mm": [10, 18], "ncol": 3}})
        manager.add_size([10, 40, 160], [9, 36, 144], title="Count", color="#ff0000", area_semantics=area_semantics)
        report = manager.layout()
        self.assertEqual(report["status"], "pass")
        return fig, manager, report

    def test_size_keys_export_at_correct_positions_and_diameters_across_dpi(self):
        # This tests the actual saved pixels, not only get_sizes() or layout box.
        # Unset PathCollection transforms formerly passed geometry QA but gave
        # displaced PDF/SVG keys and 4.17x oversized 300-DPI PNG keys.
        fig, manager, report = self.size_guide()
        boxes = report["legends"][0]["key_bboxes_mm"]
        # Text metrics vary slightly with backend/DPI: centers allow 2.5 px / 0.5 pt.
        centers_mm = [(b[0] + b[2] / 2, b[1] + b[3] / 2) for b in boxes]
        painter = fig.canvas.get_renderer()
        for key, text in zip(boxes, manager.entries[0]["artist"].get_texts()):
            label_box = text.get_window_extent(painter)
            self.assertAlmostEqual(key[1] + key[3] / 2, (label_box.y0 + label_box.y1) / 2 * 25.4 / fig.dpi, places=6)
        with tempfile.TemporaryDirectory(prefix="easyviz-legend-") as folder:
            folder = Path(folder)
            for dpi in (100, 300):
                with self.subTest(dpi=dpi):
                    path = folder / f"keys-{dpi}.png"
                    fig.savefig(path, dpi=dpi)
                    pixels = np.asarray(Image.open(path).convert("RGB"))
                    mask = (pixels[:, :, 0] > 220) & (pixels[:, :, 1] < 80) & (pixels[:, :, 2] < 80)
                    components = sorted(find_objects(label(mask)[0]), key=lambda s: s[1].start)
                    self.assertEqual(len(components), 3)
                    for slices, area, center in zip(components, (9, 36, 144), centers_mm):
                        ys, xs = slices
                        diameter = math.sqrt(area) * dpi / 72
                        self.assertAlmostEqual(xs.stop - xs.start, diameter, delta=2)
                        self.assertAlmostEqual(ys.stop - ys.start, diameter, delta=2)
                        self.assertAlmostEqual((xs.stop + xs.start) / 2, center[0] * dpi / 25.4, delta=2.5)
                        self.assertAlmostEqual((ys.stop + ys.start) / 2, pixels.shape[0] - center[1] * dpi / 25.4, delta=2.5)
            path = folder / "keys.svg"
            with plt.rc_context({"svg.fonttype": "none"}): fig.savefig(path)
            tree = ET.parse(path).getroot()
            ns = {"s": "http://www.w3.org/2000/svg"}
            markers = [p for p in tree.findall(".//s:path", ns) if "#ff0000" in p.attrib.get("style", "")]
            self.assertEqual(len(markers), 3)
            for marker, area, center in zip(markers, (9, 36, 144), centers_mm):
                coordinates = np.array([float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", marker.attrib["d"])]).reshape(-1, 2)
                np.testing.assert_allclose(np.ptp(coordinates, axis=0), math.sqrt(area), atol=1e-5)
                actual_center = (coordinates.max(axis=0) + coordinates.min(axis=0)) / 2
                self.assertAlmostEqual(actual_center[0], center[0] * 72 / 25.4, delta=.5)
                self.assertAlmostEqual(actual_center[1], (70 - center[1]) * 72 / 25.4, delta=.5)
        self.assertEqual(manager.validate()["status"], "pass")

    def test_rendered_key_bounds_detect_corrupt_transform_even_with_same_area(self):
        _, manager, report = self.size_guide()
        handle = manager.entries[0]["artist"].legend_handles[-1]
        handle.set_transform(Affine2D().scale(3).translate(250, 180))
        self.assertEqual(float(handle.get_sizes()[0]), 144)
        broken = manager.validate()
        self.assertEqual(broken["status"], "needs_revision")
        self.assertGreater(broken["legends"][0]["bbox_mm"][2], report["legends"][0]["bbox_mm"][2])

    def test_geometric_circle_area_keys_use_actual_path_area_and_separate_parameter(self):
        fig, ax = self.figure()
        manager = helper.LegendLayout(fig, ax, {"legend": 8}, {
            "size": {"position": "manual", "anchor_mm": [10, 18], "ncol": 3}})
        manager.add_size([10, 40, 160], [9, 36, 144], title="Count", area_semantics="geometric_circle_area")
        report = manager.layout()
        self.assertEqual(report["status"], "pass")
        handles = manager.entries[0]["artist"].legend_handles
        np.testing.assert_allclose([collection_fill_areas_pt2(handle, fig)[0] for handle in handles], [9, 36, 144], rtol=1e-6)
        item = report["legends"][0]
        self.assertEqual(item["marker_areas_pt2"], [9, 36, 144])
        np.testing.assert_allclose(item["marker_size_parameters_pt2"], np.array([9, 36, 144]) * 4 / math.pi)
        self.assertEqual(item["area_semantics"], "geometric_circle_area")
        handles[-1].set_sizes([144])
        self.assertIn("quantitative_marker_area_changed", manager.validate()["legends"][0]["issues"])

    def test_legacy_size_keys_keep_rendering_and_correctly_record_fill_area(self):
        fig, manager, report = self.size_guide()
        handles = manager.entries[0]["artist"].legend_handles
        self.assertEqual([float(handle.get_sizes()[0]) for handle in handles], [9, 36, 144])
        geometric = np.array([9, 36, 144]) * math.pi / 4
        np.testing.assert_allclose([collection_fill_areas_pt2(handle, fig)[0] for handle in handles], geometric, rtol=1e-6)
        item = report["legends"][0]
        self.assertEqual(item["marker_size_parameters_pt2"], [9, 36, 144])
        np.testing.assert_allclose(item["marker_areas_pt2"], geometric)
        self.assertEqual(item["area_semantics"], "matplotlib_size_parameter")

    def test_geometric_area_export_benchmark_checks_actual_svg_and_png(self):
        fig, _, _ = self.size_guide(area_semantics="geometric_circle_area", dpi=300)
        spec = {"chart": "dotplot", "layout": {"width_mm": 100, "height_mm": 70, "dpi": 300},
                "options": {"size_max": 160, "max_area_pt2": 144, "size_legend": [10, 40, 160]}}
        geometry = benchmark.inspect_figure(fig, spec)
        with tempfile.TemporaryDirectory(prefix="easyviz-circle-export-") as folder:
            folder = Path(folder)
            fig.savefig(folder / "panel.png", dpi=300)
            fig.savefig(folder / "panel.svg")
            checked = benchmark.inspect_size_exports(folder, geometry, spec)
        self.assertTrue(checked["svg_pass"], checked)
        self.assertTrue(checked["png_pass"], checked)
        np.testing.assert_allclose(checked["expected_diameters_pt"], 2 * np.sqrt(np.array([9, 36, 144]) / math.pi))

    def test_explicit_placement_columns_and_font_are_honored(self):
        fig, ax = self.figure(132, 96)
        manager = helper.LegendLayout(fig, ax, {"legend": 8}, {
            "categorical": {"position": "manual", "anchor_mm": [18, 25], "loc": "upper left", "ncol": 2}})
        manager.add_categorical(["Control", "Group A", "Group B", "Group C"], ["#0072B2", "#D55E00", "#009E73", "#CC79A7"], shape="marker", edgecolor="black", linewidth_pt=.4)
        report = manager.layout()
        self.assertEqual(report["status"], "pass")
        chosen = report["legends"][0]["chosen_settings"]
        self.assertEqual((chosen["position"], chosen["ncol"], chosen["loc"]), ("manual", 2, "upper left"))
        np.testing.assert_allclose(chosen["anchor_mm"], [18, 25])
        self.assertTrue(all(t.get_fontsize() == 8 for t in manager.entries[0]["artist"].get_texts()))
        self.assertTrue(all(h.get_markeredgewidth() == .4 for h in manager.entries[0]["artist"].legend_handles))

    def test_impossible_legend_is_rejected_without_shrinking_font_or_canvas(self):
        fig, ax = self.figure(60, 25)
        manager = helper.LegendLayout(fig, ax, {"legend": 8})
        manager.add_categorical(["Extremely long categorical label " + str(i) for i in range(8)], ["#0072B2"] * 8)
        report = manager.layout()
        self.assertEqual(report["status"], "needs_revision")
        np.testing.assert_allclose(fig.get_size_inches() * 25.4, [60, 25])
        self.assertTrue(all(t.get_fontsize() == 8 for t in manager.entries[0]["artist"].get_texts()))
        self.assertGreater(len(report["legends"][0]["attempts"]), 1)

    def test_manual_colorbar_retains_range_ticks_and_physical_rect(self):
        fig, ax = self.figure(132, 96)
        manager = helper.LegendLayout(fig, ax, {"legend": 8}, {
            "colorbar": {"position": "manual", "orientation": "horizontal", "rect_mm": [60, 15, 28, 2], "ticks": [0, 20, 40], "label_position": "top"}})
        manager.add_colorbar(plt.cm.ScalarMappable(norm=Normalize(0, 40), cmap="viridis"), "Signal (%)")
        report = manager.layout()
        self.assertEqual(report["status"], "pass")
        item = report["legends"][0]
        self.assertEqual(item["mapped_range"], [0, 40])
        self.assertEqual(item["chosen_settings"]["ticks"], [0, 20, 40])
        np.testing.assert_allclose(item["chosen_settings"]["rect_mm"], [60, 15, 28, 2])
        self.assertGreater(item["bbox_mm"][3], 2)  # Labels are measured too.
        self.assertEqual(manager.entries[0]["artist"].xaxis.get_label_position(), "top")

    def test_combined_union_excludes_empty_gaps_and_distinguishes_available_region(self):
        fig, ax = self.figure(132, 96)
        manager = helper.LegendLayout(fig, ax, {"legend": 8}, {
            "categorical": {"position": "manual", "anchor_mm": [8, 20], "ncol": 2},
            "size": {"position": "manual", "anchor_mm": [75, 20], "ncol": 2}})
        manager.add_categorical(["A", "B"], ["#0072B2", "#D55E00"])
        manager.add_size([1, 4], [9, 36])
        report = manager.layout()
        self.assertEqual(report["status"], "pass")
        combined = report["combined"]
        self.assertEqual(combined["guide_count"], 2)
        self.assertFalse(combined["has_envelope_overlap"])
        self.assertAlmostEqual(combined["occupied_envelope_union_area_mm2"], combined["sum_envelope_area_mm2"])
        enclosing = combined["enclosing_bbox_mm"]
        self.assertLess(combined["occupied_envelope_union_area_mm2"], enclosing[2] * enclosing[3])
        item = report["legends"][0]
        self.assertIsNone(item["reserved_band_mm"])
        self.assertIsNotNone(item["available_region_mm"])
        actual_reserved = helper.measure_bbox(fig, Bbox.from_bounds(10, 10, 20, 10), [10, 30, 100, 50], reserved_band_mm=[0, 0, 132, 25])
        self.assertIsNotNone(actual_reserved["reserved_band_fraction"])
        self.assertIsNone(actual_reserved["available_region_fraction"])

    def test_overlapping_legends_report_overlap_and_union_not_double_counted(self):
        fig, ax = self.figure()
        manager = helper.LegendLayout(fig, ax, {"legend": 8}, {
            "categorical": {"position": "manual", "anchor_mm": [8, 20], "ncol": 2},
            "size": {"position": "manual", "anchor_mm": [8, 20], "ncol": 2}})
        manager.add_categorical(["A", "B"], ["#0072B2", "#D55E00"])
        manager.add_size([1, 4], [9, 36])
        report = manager.layout()
        self.assertEqual(report["status"], "needs_revision")
        self.assertTrue(report["combined"]["has_envelope_overlap"])
        self.assertLess(report["combined"]["occupied_envelope_union_area_mm2"], report["combined"]["sum_envelope_area_mm2"])


if __name__ == "__main__":
    unittest.main()
