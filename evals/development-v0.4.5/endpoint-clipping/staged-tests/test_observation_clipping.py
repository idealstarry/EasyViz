"""Real-export checks for final observation envelopes and locked plot semantics."""
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
from pypdf import PdfReader

SCRIPT = Path(__file__).resolve().parents[1] / "staged-runtime/render.py"
module = importlib.util.spec_from_file_location("easyviz_endpoint_test", SCRIPT)
renderer = importlib.util.module_from_spec(module)
module.loader.exec_module(renderer)
checker = renderer.observation_clipping


class ObservationClippingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-endpoint-")
        self.root = Path(self.temp.name)
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "y"},
                     "layout": {"width_mm": 88, "height_mm": 66, "font": "DejaVu Sans", "dpi": 160},
                     "labels": {"x": "X", "y": "Y"}, "formats": ["png", "svg", "pdf"],
                     "options": {"point_area_pt2": 100, "alpha": 1, "x_limits": [0, 1], "y_limits": [0, 1]}}

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def run_panel(self, text, spec=None, fails=False, name="output"):
        data = self.root / (name + ".csv")
        data.write_text(text)
        out = self.root / name
        adopted = deepcopy(spec or self.spec)
        if fails:
            with self.assertRaisesRegex(renderer.SpecError, "clipped observation envelopes"):
                renderer.render(data, adopted, out)
        else:
            renderer.render(data, adopted, out)
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["valid_outputs"], not fails)
        for suffix in adopted["formats"]:
            self.assertTrue((out / ("panel." + suffix)).is_file())
        self.assertEqual((out / "source-data.csv").read_bytes(), data.read_bytes())
        return out, qa

    def make_artist(self, xy, *, size=100, edge="none", linewidth=0, clip=True,
                    marker="o", face="#29ACF3", role="point-group"):
        fig = renderer.plt.figure(figsize=(4, 3), dpi=120)
        ax = fig.add_axes([.2, .2, .6, .6])
        points = ax.scatter(*np.asarray(xy).T, marker=marker, s=size,
                            facecolors=face, edgecolors=edge, linewidths=linewidth, clip_on=clip)
        ax.set(xlim=(0, 1), ylim=(0, 1))
        renderer.figure_elements.register(fig, points, role, "Observed", key="observed",
                                          source_keys=[{"records": list(range(1, len(xy) + 1))}])
        fig.canvas.draw()
        return fig, ax, points

    def test_endpoint_exports_fail_and_keep_locked_area_coordinates_and_ranges(self):
        out, qa = self.run_panel("x,y\n0,0\n0.5,0.5\n1,1\n", fails=True)
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["options"], self.spec["options"])
        self.assertEqual(settings["layout"]["width_mm"], 88)
        self.assertEqual(settings["layout"]["height_mm"], 66)
        self.assertEqual(settings["mark_geometry"]["marker_size_parameter_pt2"], 100)
        self.assertEqual(settings["observation_clipping"], qa["observation_clipping"])
        for suffix, report in qa["observation_clipping"]["by_format"].items():
            self.assertEqual(report["checked_observations"], 3)
            self.assertEqual(report["clipped_observations"], 2)
            self.assertEqual([item["source"]["record"] for item in report["clipped"]], [1, 3])
            for item in report["clipped"]:
                violations = item["violations"]
                self.assertEqual(len(violations), 1)
                self.assertEqual(violations[0]["boundary"], "artist_clip_box")
                for amount in violations[0]["exceeded_mm"].values():
                    self.assertAlmostEqual(amount, 5 * 25.4 / 72, places=10)
                bounds = item["outer_bounds_mm"]
                self.assertAlmostEqual(bounds[2] - bounds[0], 10 * 25.4 / 72, places=10)
        with Image.open(out / "panel.png") as im:
            self.assertEqual(im.size, (554, 416))
        self.assertAlmostEqual(float(PdfReader(out / "panel.pdf").pages[0].mediabox.width) * 25.4 / 72, 88, places=5)

    def test_safe_inside_control_preserves_same_marker_size_and_limits(self):
        out, qa = self.run_panel("x,y\n0.1,0.1\n0.5,0.5\n0.9,0.9\n")
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["checked_observations"], 3)
            self.assertEqual(report["clipped"], [])
        self.assertEqual(json.loads((out / "settings.json").read_text())["options"], self.spec["options"])

    def test_logarithmic_offset_transform_endpoint_and_safe_exports(self):
        spec = deepcopy(self.spec)
        spec["options"].update(x_scale="log", y_scale="log", x_limits=[1, 100], y_limits=[1, 100])
        for text, fails, name in [("x,y\n1,1\n10,10\n100,100\n", True, "log-ends"),
                                  ("x,y\n3,3\n10,10\n30,30\n", False, "log-inside")]:
            out, qa = self.run_panel(text, spec, fails, name)
            for report in qa["observation_clipping"]["by_format"].values():
                self.assertEqual(report["clipped_observations"], 2 if fails else 0)
                self.assertEqual(report["unmeasured_observations"], 0)
            self.assertEqual(json.loads((out / "settings.json").read_text())["options"], spec["options"])

    def test_hollow_stroke_outer_edge_can_clip_when_filled_path_is_inside(self):
        spec = deepcopy(self.spec)
        spec["options"]["point_area_pt2"] = 64
        # Nominal plot width is (0.77-0.19)*88 = 51.04 mm. This
        # center is 1.75 mm inside; filled radius is 1.411 mm, while
        # the hollow circle's 4-pt stroke extends the radius to 2.117 mm.
        x = 1.75 / (.58 * 88)
        text = f"x,y\n{x},0.5\n"
        self.run_panel(text, spec, False, "filled")
        spec["options"].update(point_style="hollow", point_edge_width_pt=4)
        out, qa = self.run_panel(text, spec, True, "hollow")
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(report["clipped_observations"], 1)
            point = report["clipped"][0]
            self.assertEqual(point["visible_stroke_width_pt"], 4)
            self.assertAlmostEqual(point["outer_bounds_mm"][2] - point["outer_bounds_mm"][0], 12 * 25.4 / 72, places=9)
        self.assertEqual(json.loads((out / "settings.json").read_text())["options"]["point_edge_width_pt"], 4)

    def test_each_format_uses_its_actual_final_canvas_including_raster_rounding(self):
        spec = deepcopy(self.spec)
        radius = 5 * 25.4 / 72
        x = radius * 1.0001 / (.58 * 88)
        out, qa = self.run_panel(f"x,y\n{x},0.5\n", spec, True, "raster-rounding")
        reports = qa["observation_clipping"]["by_format"]
        self.assertEqual(reports["svg"]["status"], "pass")
        self.assertEqual(reports["pdf"]["status"], "pass")
        self.assertEqual(reports["png"]["status"], "needs_revision")
        self.assertAlmostEqual(reports["png"]["canvas_mm"][0], 554 / 160 * 25.4, places=10)
        self.assertGreater(reports["png"]["clipped"][0]["violations"][0]["exceeded_mm"]["left"], 0)

    def test_quantitative_scatter_keeps_true_circle_area_and_source_rows(self):
        spec = deepcopy(self.spec)
        spec["fields"]["size"] = "area"
        spec["options"].pop("point_area_pt2")
        spec["options"].update(size_max=1, max_area_pt2=100, size_legend=[.25, 1])
        out, qa = self.run_panel("x,y,area\n0,0,1\n0.5,0.5,0.25\n1,1,0\n", spec, True, "mapped")
        plotted = renderer.pd.read_csv(out / "plotting-data.csv")
        np.testing.assert_allclose(plotted["_easyviz_area_pt2"], [100, 25, 0])
        np.testing.assert_allclose(plotted["_easyviz_marker_size_parameter_pt2"], np.array([100, 25, 0]) * 4 / math.pi)
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(report["checked_observations"], 2)
            self.assertEqual(report["ignored_observations"]["zero_area"], 1)
            self.assertEqual(report["clipped"][0]["source"]["record"], 1)
            amount = report["clipped"][0]["violations"][0]["exceeded_mm"]["left"]
            self.assertAlmostEqual(amount, math.sqrt(100 / math.pi) * 25.4 / 72, places=9)

    def test_distribution_numeric_endpoints_are_checked_after_final_beeswarm(self):
        spec = deepcopy(self.spec)
        spec.update(chart="distribution", fields={"group": "g", "value": "v"})
        spec["options"] = {"point_area_pt2": 100, "alpha": 1, "y_limits": [0, 1],
                           "point_layout": "beeswarm", "point_max_offset_mm": 4}
        out, qa = self.run_panel("g,v\nA,0\nA,0.5\nA,1\n", spec, True, "distribution")
        self.assertEqual(qa["point_layout"]["status"], "pass")
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual([point["source"]["record"] for point in report["clipped"]], [1, 3])
            self.assertEqual(report["clipped_observations"], 2)
        np.testing.assert_allclose(renderer.pd.read_csv(out / "plotting-data.csv")["v"], [0, .5, 1])

    def test_dotplot_large_quantitative_area_is_not_shrunk_to_fit(self):
        spec = deepcopy(self.spec)
        spec.update(chart="dotplot", fields={"x": "x", "y": "y", "size": "s", "color": "c"},
                    colormap="viridis")
        # At fixed 88x66 mm the radius of the supplied 20000 pt² area
        # is larger than the smallest available categorical margin.
        spec["options"] = {"size_max": 1, "max_area_pt2": 20000, "size_legend": [.001]}
        out, qa = self.run_panel("x,y,s,c\na,b,1,1\n", spec, True, "dotplot-large")
        plotted = renderer.pd.read_csv(out / "plotting-data.csv")
        self.assertEqual(plotted["_easyviz_area_pt2"].tolist(), [20000])
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(report["clipped_observations"], 1)
            self.assertEqual(report["clipped"][0]["source"], {"record": 1, "x": "a", "y": "b"})
        spec["options"]["max_area_pt2"] = 90
        self.run_panel("x,y,s,c\na,b,1,1\n", spec, False, "dotplot-safe")

    def test_clip_disabled_allows_axes_crossing_but_still_checks_figure(self):
        fig, ax, points = self.make_artist([[0, .5]], clip=False)
        report = checker.measure(fig)
        self.assertEqual(report["status"], "pass")
        points.set_offsets([[-.34, .5]])
        report = checker.measure(fig)
        self.assertEqual(report["status"], "needs_revision")
        self.assertEqual([v["boundary"] for v in report["clipped"][0]["violations"]], ["figure"])

    def test_tangent_is_allowed_but_any_real_geometric_excess_is_not(self):
        fig, ax, points = self.make_artist([[.5, .5]])
        radius_px = math.sqrt(100) / 2 * fig.dpi / 72
        center = ax.transData.inverted().transform([ax.bbox.x0 + radius_px, ax.bbox.y0 + ax.bbox.height / 2])
        points.set_offsets([center])
        self.assertEqual(checker.measure(fig)["status"], "pass")
        center[0] -= 1e-8
        points.set_offsets([center])
        self.assertEqual(checker.measure(fig)["status"], "needs_revision")

    def test_masked_zero_and_invisible_marks_are_counted_without_fake_violations(self):
        fig, ax, points = self.make_artist([[0, 0], [.5, .5], [1, 1]], size=[0, 100, 100])
        points.set_offsets(np.ma.array([[0, 0], [.5, .5], [1, 1]], mask=[[False, False], [True, True], [False, False]]))
        points.set_facecolors([[1, 0, 0, 1], [1, 0, 0, 1], [1, 0, 0, 0]])
        report = checker.measure(fig)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["checked_observations"], 0)
        self.assertEqual(report["ignored_observations"], {"nonfinite_or_masked": 1, "zero_area": 1, "invisible": 1})

    def test_invisible_edge_does_not_add_linewidth_to_filled_circle(self):
        fig, ax, points = self.make_artist([[.5, .5]], edge=(0, 0, 0, 0), linewidth=40)
        radius_px = 5 * fig.dpi / 72
        points.set_offsets([ax.transData.inverted().transform([ax.bbox.x0 + radius_px, ax.bbox.y0 + ax.bbox.height / 2])])
        self.assertEqual(checker.measure(fig)["status"], "pass")

    def test_bar_baseline_and_legend_markers_are_not_observation_clipping(self):
        spec = deepcopy(self.spec)
        spec.update(chart="composition", fields={"sample": "s", "category": "c", "value": "v"})
        spec["options"] = {"normalization": "sample_sum"}
        out, qa = self.run_panel("s,c,v\na,A,1\na,B,1\nb,A,2\nb,B,3\n", spec, False, "bars")
        self.assertEqual(qa["observation_clipping"]["status"], "not_applicable")
        for report in qa["observation_clipping"]["by_format"].values():
            self.assertEqual(report["checked_observations"], 0)

    def test_nonstandard_glyph_and_custom_clip_are_explicitly_advisory(self):
        from matplotlib.patches import Circle
        for marker, custom_clip in [("s", False), ("o", True)]:
            with self.subTest(marker=marker, custom_clip=custom_clip):
                fig, ax, points = self.make_artist([[0, 0]], marker=marker)
                if custom_clip:
                    points.set_clip_path(Circle((.5, .5), .4, transform=ax.transData))
                report = checker.measure(fig)
                self.assertEqual(report["status"], "advisory")
                self.assertEqual(report["checked_observations"], 0)
                self.assertEqual(report["unmeasured_observations"], 1)
                self.assertEqual(report["clipped"], [])


if __name__ == "__main__":
    unittest.main()
