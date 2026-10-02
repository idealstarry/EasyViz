"""Behavioral checks for portable panel rendering and unsafe-data rejection.

Run: .venv/bin/python -m unittest discover -s tests -p test_renderer.py -v
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/render.py"
loader = importlib.util.spec_from_file_location("easyviz_render", SCRIPT)
renderer = importlib.util.module_from_spec(loader)
loader.loader.exec_module(renderer)
from PIL import Image
from pypdf import PdfReader
import pandas as pd
from marker_geometry import collection_fill_areas_pt2


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-test-")
        self.root = Path(self.temp.name)
        self.base = {"chart": "scatter", "fields": {"x": "x", "y": "y"}, "layout": {"width_mm": 88, "height_mm": 66, "font": "DejaVu Sans", "dpi": 120}, "labels": {"x": "Input", "y": "Output"}, "formats": ["pdf", "svg", "png", "tiff"], "seed": 29}

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def csv(self, text):
        path = self.root / "input.csv"
        path.write_text(text)
        return path

    def test_physical_dimensions_and_metadata_across_sizes_and_formats(self):
        data = self.csv("x,y\n1,1.5\n2,3\n3,2\n4,5\n")
        for width, height in [(88, 66), (132, 88)]:
            with self.subTest(width=width, height=height):
                spec = deepcopy(self.base)
                spec["layout"].update(width_mm=width, height_mm=height)
                output = self.root / str(width)
                qa = renderer.render(data, spec, output)
                self.assertEqual(qa["status"], "pass")
                page = PdfReader(output / "panel.pdf").pages[0]
                self.assertAlmostEqual(float(page.mediabox.width) / 72 * 25.4, width, places=5)
                self.assertAlmostEqual(float(page.mediabox.height) / 72 * 25.4, height, places=5)
                expected_px = (round(width / 25.4 * 120), round(height / 25.4 * 120))
                for suffix in ["png", "tiff"]:
                    with Image.open(output / f"panel.{suffix}") as image:
                        self.assertEqual(image.size, expected_px)
                        self.assertAlmostEqual(float(image.info["dpi"][0]), 120, places=1)
                svg = ET.parse(output / "panel.svg").getroot()
                self.assertAlmostEqual(float(svg.attrib["width"][:-2]) / 72 * 25.4, width, places=4)
                self.assertTrue(svg.findall(".//{http://www.w3.org/2000/svg}text"), "SVG must preserve editable text")
                settings = json.loads((output / "settings.json").read_text())
                self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")
                self.assertEqual(settings["typography"]["tick"], 8)
                self.assertEqual(len(settings["renderer"]["sha256"]), 64)
                self.assertIn("scipy", settings["runtime"])
                self.assertEqual(len(pd.read_csv(output / "plotting-data.csv")), 4)

    def test_rejects_bad_numeric_values_and_missing_schema(self):
        for body in ["x,y\n1,NaN\n", "x,y\n1,inf\n", "x,y\n1,hello\n", "x,z\n1,2\n"]:
            with self.subTest(body=body):
                with self.assertRaises(renderer.SpecError):
                    renderer.prepare(self.csv(body), self.base)

    def test_heatmap_rejects_duplicate_and_missing_cells(self):
        spec = {"chart": "heatmap", "fields": {"row": "r", "column": "c", "value": "v"}}
        for body in ["r,c,v\na,x,1\na,x,2\n", "r,c,v\na,x,1\na,y,2\nb,x,3\n"]:
            with self.assertRaises(renderer.SpecError):
                renderer.prepare(self.csv(body), spec)

    def test_composition_denominator_remains_explicit_and_incomplete(self):
        spec = {"chart": "composition", "fields": {"sample": "s", "category": "c", "value": "v", "denominator": "total"}, "options": {"normalization": "denominator"}}
        data = renderer.prepare(self.csv("s,c,v,total\ns1,A,20,100\ns1,B,30,100\ns2,A,2,10\ns2,B,3,10\n"), spec)
        self.assertEqual(list(data["_easyviz_plotted_value"]), [.2, .3, .2, .3])
        self.assertEqual(list(data.groupby("s")["_easyviz_plotted_value"].sum()), [.5, .5])
        for body in ["s,c,v,total\ns,A,-1,10\n", "s,c,v,total\ns,A,6,10\ns,B,6,10\n", "s,c,v,total\ns,A,2,10\ns,B,2,12\n"]:
            with self.assertRaises(renderer.SpecError):
                renderer.prepare(self.csv(body), spec)
        no_normalization = deepcopy(spec)
        no_normalization["options"] = {}
        with self.assertRaises(renderer.SpecError):
            renderer.prepare(self.csv("s,c,v,total\ns,A,2,10\n"), no_normalization)

    def test_category_order_and_colors_never_drop_or_cycle(self):
        categories = [f"group {i}" for i in range(9)]
        with self.assertRaises(renderer.SpecError):
            renderer.palette_colors({}, categories)
        with self.assertRaises(renderer.SpecError):
            renderer.palette_colors({"colors": {"a": "#0072B2"}}, ["a", "b"])
        with self.assertRaises(renderer.SpecError):
            renderer.ordered(pd.DataFrame({"g": ["a", "b"]}), "g", {"order": {"group": ["a"]}}, "group")

    def test_statistics_known_result_and_constant_rejection(self):
        spec = deepcopy(self.base)
        spec["statistics"] = {"method": "pearson"}
        data = renderer.prepare(self.csv("x,y\n1,2\n2,4\n3,6\n4,8\n"), spec)
        result = renderer.statistics(data, spec)
        self.assertAlmostEqual(result["statistic"], 1)
        self.assertLess(result["pvalue"], 1e-12)
        constant = renderer.prepare(self.csv("x,y\n1,2\n1,4\n1,6\n"), spec)
        with self.assertRaises(renderer.SpecError):
            renderer.statistics(constant, spec)
        self.assertEqual(renderer.statistics(data, self.base)["method"], "none")

    def test_explicit_none_is_descriptive_and_rejects_incompatible_statistical_requests(self):
        source = self.csv("x,y,subject\n1,2,S1\n2,3,S1\n3,4,S2\n")
        spec = deepcopy(self.base)
        spec["fields"]["unit"] = "subject"
        spec["statistics"] = {"method": "none", "annotate": False}
        qa = renderer.render(source, spec, self.root / "explicit-none")
        self.assertEqual(qa["status"], "pass")
        result = json.loads((self.root / "explicit-none/stats.json").read_text())
        self.assertEqual(result["method"], "none")
        self.assertNotIn("pvalue", result)
        self.assertEqual(len(pd.read_csv(self.root / "explicit-none/plotting-data.csv")), 3)
        data = renderer.prepare(source, spec)
        self.assertEqual(result, renderer.statistics(data, self.base))
        for forbidden in ({"annotate": True}, {"groups": ["A", "B"]}, {"unit": "subject"}):
            with self.subTest(forbidden=forbidden):
                conflict = deepcopy(spec)
                conflict["statistics"].update(forbidden)
                with self.assertRaisesRegex(renderer.SpecError, "cannot be combined"):
                    renderer.prepare(source, conflict)
                with self.assertRaisesRegex(renderer.SpecError, "cannot be combined"):
                    renderer.statistics(data, conflict)

    def test_welch_and_independence_checks(self):
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v", "unit": "id"}, "statistics": {"method": "welch", "groups": ["A", "B"]}}
        data = renderer.prepare(self.csv("g,v,id\nA,1,a1\nA,2,a2\nA,3,a3\nB,4,b1\nB,5,b2\nB,6,b3\n"), spec)
        result = renderer.statistics(data, spec)
        self.assertAlmostEqual(result["statistic"], -3.6742346141747673)
        self.assertAlmostEqual(result["pvalue"], .021311641128756727)
        annotated = deepcopy(spec)
        annotated["statistics"]["annotate"] = True
        layout, typography, rc = renderer.setup(annotated)
        with renderer.plt.rc_context(rc):
            fig, _ = renderer.draw(data, annotated, layout, typography, result)
            annotations = [item.get_text() for item in fig.findobj(renderer.Text)]
            self.assertTrue(any("A vs B\nwelch" in text for text in annotations))
            renderer.plt.close(fig)
        data.loc[data.g == "B", "id"] = ["a1", "a2", "a3"]
        with self.assertRaises(renderer.SpecError):
            renderer.statistics(data, spec)

    def test_scatter_rejects_repeated_units_from_either_alias(self):
        source = self.csv("x,y,subject\n1,2,S1\n2,5,S1\n3,6,S2\n4,9,S2\n5,11,S3\n6,10,S3\n")
        for method in ("pearson", "spearman"):
            for location in ("fields", "statistics"):
                with self.subTest(method=method, location=location):
                    spec = deepcopy(self.base)
                    spec["statistics"] = {"method": method}
                    spec[location]["unit"] = "subject"
                    data = renderer.prepare(source, spec)
                    with self.assertRaisesRegex(renderer.SpecError, "one observation per supplied independent unit"):
                        renderer.statistics(data, spec)

    def test_scatter_unit_aliases_preserve_results_and_reject_conflicts(self):
        spec = deepcopy(self.base)
        spec["statistics"] = {"method": "pearson", "unit": "subject"}
        source = self.csv("x,y,subject,row\n1,2,S1,R1\n2,4,S2,R2\n3,6,S3,R3\n4,8,S4,R4\n")
        data = renderer.prepare(source, spec)
        expected = renderer.statistics(data, spec)
        self.assertEqual(expected["n"], 4)
        self.assertAlmostEqual(expected["statistic"], 1)
        spec["fields"]["unit"] = "subject"
        self.assertEqual(renderer.statistics(data, spec), expected)
        spec["statistics"]["unit"] = "row"
        with self.assertRaisesRegex(renderer.SpecError, "must name the same independent unit column"):
            renderer.statistics(data, spec)

    def test_scatter_statistics_unit_requires_present_nonempty_ids(self):
        spec = deepcopy(self.base)
        spec["statistics"] = {"method": "spearman", "unit": "subject"}
        for source in ("x,y\n1,2\n2,4\n3,6\n", "x,y,subject\n1,2,S1\n2,4,\n3,6,S3\n"):
            with self.subTest(source=source):
                data = renderer.prepare(self.csv(source), spec)
                with self.assertRaisesRegex(renderer.SpecError, "statistical unit IDs"):
                    renderer.statistics(data, spec)

    def test_paired_test_aligns_ids_and_rejects_unmatched_pairs(self):
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v", "unit": "id"}, "statistics": {"method": "wilcoxon", "groups": ["A", "B"]}}
        data = renderer.prepare(self.csv("g,v,id\nA,1,u1\nA,2,u2\nA,3,u3\nA,4,u4\nB,5,u4\nB,3,u2\nB,2,u1\nB,4,u3\n"), spec)
        result = renderer.statistics(data, spec)
        self.assertEqual(result["pair_order"], ["u1", "u2", "u3", "u4"])
        self.assertEqual(result["statistic"], 0)
        self.assertAlmostEqual(result["pvalue"], .125)
        data.loc[data.g == "B", "id"] = ["u4", "u2", "u1", "u5"]
        with self.assertRaises(renderer.SpecError):
            renderer.statistics(data, spec)

    def test_distribution_preserves_points_and_seed_across_orientation(self):
        data = self.csv("g,v\nA,1\nA,2\nA,3\nB,2\nB,4\nB,9\n")
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v"}, "layout": {"font": "DejaVu Sans", "dpi": 100}, "formats": ["png"], "seed": 4}
        for orientation in ["vertical", "horizontal"]:
            spec["options"] = {"orientation": orientation, "kind": "violin"}
            renderer.render(data, spec, self.root / orientation)
        a = pd.read_csv(self.root / "vertical/plotting-data.csv")
        b = pd.read_csv(self.root / "horizontal/plotting-data.csv")
        self.assertEqual(list(a["_easyviz_jitter_position"]), list(b["_easyviz_jitter_position"]))
        self.assertEqual(list(a["v"]), [1, 2, 3, 2, 4, 9])

    def test_rejects_hidden_values_unknown_options_and_clipped_labels(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        spec["options"] = {"fit": "linear"}
        with self.assertRaisesRegex(renderer.SpecError, "Unknown"):
            renderer.prepare(data, spec)
        spec["options"] = {"x_limits": [1, 2]}
        with self.assertRaisesRegex(renderer.SpecError, "hide observations"):
            renderer.render(data, spec, self.root / "hidden")
        spec["options"] = {}
        spec["labels"]["x"] = "Very long axis label " * 15
        with self.assertRaisesRegex(renderer.SpecError, "Canvas QA"):
            renderer.render(data, spec, self.root / "clipped")
        qa = json.loads((self.root / "clipped/qa.json").read_text())
        self.assertEqual(qa["status"], "needs_revision")
        self.assertTrue(qa["clipped_text"])

    def test_dot_area_and_custom_continuous_palette(self):
        spec = {"chart": "dotplot", "fields": {"x": "x", "y": "y", "size": "s", "color": "c"}, "layout": {"width_mm": 110, "font": "DejaVu Sans", "dpi": 100}, "colormap": "blue-white-red", "options": {"size_max": 1, "max_area_pt2": 100, "color_limits": [-2, 2], "color_center": 0}, "formats": ["png"]}
        data = self.csv("x,y,s,c\nG1,A,0,-1\nG2,A,.25,0\nG1,B,1,1\nG2,B,.5,2\n")
        renderer.render(data, spec, self.root / "dots")
        plotted = pd.read_csv(self.root / "dots/plotting-data.csv")
        self.assertEqual(list(plotted["_easyviz_area_pt2"]), [0, 25, 100, 50])
        renderer.np.testing.assert_allclose(plotted["_easyviz_marker_size_parameter_pt2"], [0, 25 * 4 / math.pi, 100 * 4 / math.pi, 50 * 4 / math.pi])
        data = renderer.prepare(data, spec)
        layout, typography, rc = renderer.setup(spec)
        with renderer.plt.rc_context(rc):
            fig, _ = renderer.draw(data, spec, layout, typography, {"method": "none"})
            renderer.np.testing.assert_allclose(collection_fill_areas_pt2(fig.axes[0].collections[0], fig), [0, 25, 100, 50], rtol=1e-6, atol=1e-10)
        settings = json.loads((self.root / "dots/settings.json").read_text())
        self.assertEqual(settings["mark_geometry"]["mode"], "mapped_circle_fill_area")
        with self.assertRaises(renderer.SpecError):
            renderer.continuous({"options": {"color_limits": [0, 1]}}, [-1, 0, 1])

    def test_failed_rerun_invalidates_previous_passing_exports(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        spec["formats"] = ["png"]
        output = self.root / "rerun"
        renderer.render(data, spec, output)
        self.assertTrue(json.loads((output / "qa.json").read_text())["valid_outputs"])
        data.write_text("x,y\n1,NaN\n")
        with self.assertRaises(renderer.SpecError):
            renderer.render(data, spec, output)
        qa = json.loads((output / "qa.json").read_text())
        self.assertEqual(qa["status"], "failed")
        self.assertFalse(qa["valid_outputs"])

    def test_missing_glyphs_fail_qa_instead_of_silent_font_loss(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        spec["formats"] = ["png"]
        spec["labels"]["title"] = "Missing glyph \U0010ffff"
        with self.assertRaisesRegex(renderer.SpecError, "Canvas QA"):
            renderer.render(data, spec, self.root / "glyph")
        qa = json.loads((self.root / "glyph/qa.json").read_text())
        self.assertTrue(qa["missing_glyphs"])

    def test_ols_overlay_rejects_log_scales(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        spec = deepcopy(self.base)
        for axis in ("x", "y"):
            spec["options"] = {"regression": True, f"{axis}_scale": "log"}
            with self.assertRaisesRegex(renderer.SpecError, "requires linear"):
                renderer.render(data, spec, self.root / axis)

    def test_literal_na_labels_and_truly_empty_values_are_distinct(self):
        spec = {"chart": "distribution", "fields": {"group": "group", "value": "value"}}
        data = renderer.prepare(self.csv("group,value\nNA,1\nnull,2\nControl,3\n"), spec)
        self.assertEqual(data.group.tolist(), ["NA", "null", "Control"])
        for body in ["group,value\n,1\n", "group,value\nNA,NaN\n"]:
            with self.assertRaises(renderer.SpecError):
                renderer.prepare(self.csv(body), spec)

    def test_tick_collisions_fail_then_layout_repair_preserves_font(self):
        data = self.csv("r,c,v\n" + "".join(f"r{i},Group {j:02d},{i + j}\n" for i in range(3) for j in range(12)))
        spec = {"chart": "heatmap", "fields": {"row": "r", "column": "c", "value": "v"}, "layout": {"font": "DejaVu Sans", "width_mm": 88, "height_mm": 88, "dpi": 120}, "colormap": "viridis", "options": {"x_rotation": 0}, "formats": ["png"]}
        with self.assertRaisesRegex(renderer.SpecError, "tick-label overlaps"):
            renderer.render(data, spec, self.root / "crowded")
        qa = json.loads((self.root / "crowded/qa.json").read_text())
        self.assertFalse(qa["valid_outputs"])
        self.assertTrue(qa["overlapping_tick_labels"])
        self.assertEqual(qa["clipped_text"], [])
        spec["layout"]["width_mm"] = 132
        spec["options"]["x_rotation"] = 90
        renderer.render(data, spec, self.root / "repaired")
        settings = json.loads((self.root / "repaired/settings.json").read_text())
        self.assertEqual(settings["typography"]["tick"], 8)
        self.assertEqual(len(pd.read_csv(self.root / "repaired/plotting-data.csv")), 36)

    def test_oblique_tick_boxes_are_not_rejected_as_axis_aligned_collisions(self):
        fig, ax = renderer.plt.subplots(figsize=(4, 3), dpi=100)
        ax.set_xticks(range(6), [f"Category {i}" for i in range(6)], rotation=45)
        fig.canvas.draw()
        overlaps, skipped = renderer.check_tick_label_overlap(fig, fig.canvas.get_renderer())
        self.assertFalse(overlaps)
        self.assertEqual(len(skipped), 6)
        renderer.plt.close(fig)

    def test_log_limits_require_positive_bounds(self):
        data = self.csv("x,y\n1,2\n2,3\n3,4\n")
        for low in [0, -1]:
            spec = deepcopy(self.base)
            spec["options"] = {"x_scale": "log", "x_limits": [low, 10]}
            with self.assertRaisesRegex(renderer.SpecError, "must be strictly positive"):
                renderer.render(data, spec, self.root / str(low))

    def test_zero_library_p_value_displays_a_bound_and_keeps_raw_value(self):
        spec = deepcopy(self.base)
        spec.update(statistics={"method": "pearson", "annotate": True}, formats=["svg"])
        renderer.render(self.csv("x,y\n1,2\n2,4\n3,6\n4,8\n"), spec, self.root / "bound")
        stats = json.loads((self.root / "bound/stats.json").read_text())
        self.assertEqual(stats["pvalue"], 0)
        self.assertEqual(stats["pvalue_display"]["upper_bound"], .001)
        svg = ET.parse(self.root / "bound/panel.svg").getroot()
        text = " ".join(svg.itertext())
        self.assertIn("p < 0.001", text)
        self.assertNotIn("p = 0", text)


if __name__ == "__main__":
    unittest.main()
