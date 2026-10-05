"""Check independent summary faces, contours, and raw observations on real artists."""
from copy import deepcopy
import csv
import importlib.util
import json
from pathlib import Path
from statistics import quantiles
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/render.py"
loader = importlib.util.spec_from_file_location("distribution_color_roles_renderer", SCRIPT)
core = importlib.util.module_from_spec(loader)
loader.loader.exec_module(core)


class DistributionColorRoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="easyviz-distribution-colors-")
        self.root = Path(self.temporary.name)
        self.source = self.root / "observations.csv"
        self.source.write_text("group,value,unit,note\nA/~,1,a1,keep\nA/~,2,a2,keep\nA/~,4,a3,keep\nA/~,8,a4,keep\nA/~,11,a5,keep\nB,2,b1,keep\nB,3,b2,keep\nB,5,b3,keep\nB,6,b4,keep\nB,10,b5,keep\n")
        self.base = {
            "chart": "distribution", "fields": {"group": "group", "value": "value", "unit": "unit"},
            "colors": {"A/~": "#BDD4E2", "B": "#D8C8E1"}, "order": {"group": ["A/~", "B"]},
            "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "font_size_pt": 8,
                       "dpi": 100, "auto_fit": True},
            "formats": ["png", "svg"], "seed": 41,
            "line_roles": {"data": {"color": "#424242", "line_width_pt": .5},
                           "summary": {"color": "#303030", "line_width_pt": .65}},
            "options": {"kind": "box", "point_area_pt2": 9, "alpha": 1, "point_layout": "beeswarm",
                        "point_max_offset_mm": 4, "point_gap_pt": .3, "point_category_offset": .18},
        }

    def tearDown(self):
        core.plt.close("all")
        self.temporary.cleanup()

    def specification(self, kind="box", orientation="vertical"):
        spec = deepcopy(self.base)
        spec["options"].update(kind=kind, orientation=orientation)
        spec["options"]["y_limits" if orientation == "vertical" else "x_limits"] = [0, 13]
        if kind == "violin":
            spec["options"].update(violin_inner="box", violin_fill_alpha=0)
        return spec

    def draw(self, spec):
        resolved = deepcopy(spec)
        data = core.prepare(self.source, resolved)
        layout, typography, rc = core.setup(resolved)
        result = core.statistics(data, resolved)
        with core.plt.rc_context(rc):
            fig, colors = core.draw(data, resolved, layout, typography, result)
            fig.canvas.draw()
        return fig, colors, result

    @staticmethod
    def elements(fig, role):
        return [entry for entry in fig._easyviz_elements if entry["role"] == role]

    def assert_raw_values_and_packing_unchanged(self, before, after, orientation):
        previous = self.elements(before, "point-group")
        current = self.elements(after, "point-group")
        with self.source.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        numeric_axis = 1 if orientation == "vertical" else 0
        observed = 0
        for old, new in zip(previous, current):
            self.assertEqual(old["source_keys"], new["source_keys"])
            expected = [float(row["value"]) for row in rows if row["group"] == new["label"]]
            actual = np.asarray(new["_artist"].get_offsets(), dtype=float)
            self.assertTrue(np.array_equal(actual, np.asarray(old["_artist"].get_offsets(), dtype=float)))
            self.assertTrue(np.array_equal(actual[:, numeric_axis], expected))
            self.assertTrue(np.array_equal(new["_artist"].get_sizes(), old["_artist"].get_sizes()))
            observed += len(actual)
        self.assertEqual(observed, len(rows))
        self.assertEqual(before._easyviz_point_layout, after._easyviz_point_layout)

    def assert_quartiles_from_source(self, fig, kind, orientation):
        with self.source.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        axis = fig.axes[0]
        for index, group in enumerate(("A/~", "B")):
            values = [float(row["value"]) for row in rows if row["group"] == group]
            q1, median, q3 = quantiles(values, n=4, method="inclusive")
            patch = axis.patches[index]
            display = patch.get_transform().transform(patch.get_path().vertices)
            actual = axis.transData.inverted().transform(display)
            dimension = 1 if orientation == "vertical" else 0
            self.assertAlmostEqual(actual[:, dimension].min(), q1)
            self.assertAlmostEqual(actual[:, dimension].max(), q3)
            if kind == "violin":
                median_entry = next(entry for entry in self.elements(fig, "summary-line")
                                    if entry["label"] == f"{group} · Median")
                line = median_entry["_artist"]
                coordinates = line.get_ydata() if orientation == "vertical" else line.get_xdata()
                self.assertTrue(np.allclose(coordinates, median, rtol=0, atol=1e-12))
            else:
                lines = [line for line in axis.lines
                         if len(line.get_ydata() if orientation == "vertical" else line.get_xdata()) == 2
                         and np.allclose(line.get_ydata() if orientation == "vertical" else line.get_xdata(), median)]
                self.assertTrue(lines)

    def test_opaque_pastel_box_faces_neutral_points_and_contours_preserve_actual_values(self):
        original = self.source.read_bytes()
        for orientation in ("vertical", "horizontal"):
            with self.subTest(orientation=orientation):
                old = self.specification(orientation=orientation)
                adopted = deepcopy(old)
                adopted["options"].update(point_color="#3C3C3C", box_fill_alpha=1)
                before, _, _ = self.draw(old)
                after, colors, _ = self.draw(adopted)
                self.assert_raw_values_and_packing_unchanged(before, after, orientation)
                self.assert_quartiles_from_source(after, "box", orientation)
                for entry in self.elements(after, "distribution"):
                    patch = entry["_artist"]
                    self.assertEqual(patch.get_facecolor(), core.mcolors.to_rgba(colors[entry["label"]], 1))
                    self.assertEqual(patch.get_edgecolor(), core.mcolors.to_rgba("#303030"))
                    self.assertEqual(entry["editable"]["facecolor"], core.figure_elements.pointer("colors", entry["label"]))
                    self.assertEqual(entry["editable"]["edgecolor"], "/line_roles/summary/color")
                    self.assertEqual(entry["editable"]["fill_alpha"], "/options/box_fill_alpha")
                for entry in self.elements(after, "point-group"):
                    self.assertTrue(np.allclose(entry["_artist"].get_facecolors(), [core.mcolors.to_rgba("#3C3C3C")]))
                    self.assertEqual(entry["editable"]["color"], "/options/point_color")
                    self.assertNotIn(core.figure_elements.pointer("colors", entry["label"]), entry["spec_paths"])
        self.assertEqual(self.source.read_bytes(), original)

    def test_opaque_violin_inner_area_neutral_points_and_contours_keep_kde_and_quartiles(self):
        for orientation in ("vertical", "horizontal"):
            with self.subTest(orientation=orientation):
                old = self.specification("violin", orientation)
                adopted = deepcopy(old)
                adopted["options"].update(point_color="#3C3C3C", violin_inner_fill_alpha=1)
                before, _, previous_result = self.draw(old)
                after, colors, result = self.draw(adopted)
                self.assert_raw_values_and_packing_unchanged(before, after, orientation)
                self.assert_quartiles_from_source(after, "violin", orientation)
                self.assertEqual(previous_result["violin_inner_summaries"], result["violin_inner_summaries"])
                for a, b in zip(self.elements(before, "distribution"), self.elements(after, "distribution")):
                    self.assertTrue(np.array_equal(a["_artist"].get_paths()[0].vertices, b["_artist"].get_paths()[0].vertices))
                    self.assertEqual(b["editable"]["color"], "/line_roles/data/color",
                                     "A face-free neutral KDE contour must point to its actual edge")
                for group, patch in zip(("A/~", "B"), after.axes[0].patches):
                    self.assertEqual(patch.get_facecolor(), core.mcolors.to_rgba(colors[group], 1))
                    self.assertEqual(patch.get_edgecolor(), core.mcolors.to_rgba("#303030"))
                    entry = next(entry for entry in self.elements(after, "summary-line")
                                 if entry["label"] == f"{group} · Q1–Q3")
                    self.assertEqual(entry["editable"]["facecolor"], core.figure_elements.pointer("colors", group))
                    self.assertEqual(entry["editable"]["edgecolor"], "/line_roles/summary/color")
                    self.assertEqual(entry["editable"]["fill_alpha"], "/options/violin_inner_fill_alpha")
                for entry in self.elements(after, "point-group"):
                    self.assertTrue(np.allclose(entry["_artist"].get_facecolors(), [core.mcolors.to_rgba("#3C3C3C")]))

    def test_filled_and_hollow_raw_point_overrides_follow_the_actual_color_channel(self):
        for kind in ("box", "violin"):
            for style in ("filled", "hollow"):
                with self.subTest(kind=kind, style=style):
                    spec = self.specification(kind)
                    spec["options"].update(point_color="#404850", point_style=style, alpha=.8)
                    if style == "hollow":
                        spec["options"]["point_edge_width_pt"] = .4
                    fig, _, _ = self.draw(spec)
                    for entry in self.elements(fig, "point-group"):
                        artist = entry["_artist"]
                        expected = core.mcolors.to_rgba("#404850", .8)
                        if style == "hollow":
                            self.assertEqual(len(artist.get_facecolors()), 0)
                            self.assertTrue(np.allclose(artist.get_edgecolors(), [expected]))
                        else:
                            self.assertTrue(np.allclose(artist.get_facecolors(), [expected]))
                            self.assertTrue(np.all(artist.get_linewidths() == 0), "Filled fixed marks keep the legacy zero-width edge")
                        self.assertEqual(entry["editable"]["color"], "/options/point_color")

    def test_outline_box_stays_unfilled_even_with_positive_face_option(self):
        for orientation in ("vertical", "horizontal"):
            spec = self.specification(orientation=orientation)
            spec["options"].update(box_style="outline", box_fill_alpha=1)
            fig, _, _ = self.draw(spec)
            for entry in self.elements(fig, "distribution"):
                self.assertEqual(entry["_artist"].get_facecolor()[3], 0)
                self.assertNotIn("facecolor", entry["editable"])
                self.assertNotIn("fill_alpha", entry["editable"])
                self.assertEqual(entry["editable"]["color"], "/line_roles/summary/color")

    def test_omitted_fill_defaults_are_pixel_identical_to_explicit_legacy_values(self):
        for orientation in ("vertical", "horizontal"):
            for kind, style in (("box", "filled"), ("box", "outline"), ("violin", "filled")):
                with self.subTest(orientation=orientation, kind=kind, style=style):
                    omitted = self.specification(kind, orientation)
                    if kind == "box":
                        omitted["options"]["box_style"] = style
                    explicit = deepcopy(omitted)
                    explicit["options"]["box_fill_alpha" if kind == "box" else "violin_inner_fill_alpha"] = .22 if kind == "box" else 0
                    first = self.root / f"omitted-{orientation}-{kind}-{style}"
                    second = self.root / f"explicit-{orientation}-{kind}-{style}"
                    self.assertEqual(core.render(self.source, omitted, first)["status"], "pass")
                    self.assertEqual(core.render(self.source, explicit, second)["status"], "pass")
                    with Image.open(first / "panel.png") as a, Image.open(second / "panel.png") as b:
                        self.assertTrue(np.array_equal(np.asarray(a), np.asarray(b)))
                    fig, colors, _ = self.draw(omitted)
                    for entry in self.elements(fig, "point-group"):
                        self.assertTrue(np.allclose(entry["_artist"].get_facecolors(), [core.mcolors.to_rgba(colors[entry["label"]])]))
                        self.assertEqual(entry["editable"]["color"], core.figure_elements.pointer("colors", entry["label"]))

    def test_alpha_type_range_and_chart_context_are_validated(self):
        invalid = (True, False, -.01, 1.01, float("nan"), float("inf"), "0.2", None, [], {})
        for field, kind in (("box_fill_alpha", "box"), ("violin_inner_fill_alpha", "violin")):
            for value in invalid:
                with self.subTest(field=field, value=value):
                    spec = self.specification(kind)
                    spec["options"][field] = value
                    with self.assertRaises(core.SpecError):
                        core.validate_spec(spec)
        contexts = [self.specification("violin"), self.specification("box"), self.specification("violin")]
        contexts[0]["options"]["box_fill_alpha"] = .5
        contexts[1]["options"]["violin_inner_fill_alpha"] = .5
        contexts[2]["options"].update(violin_inner="none", violin_inner_fill_alpha=.5)
        for spec in contexts:
            with self.subTest(options=spec["options"]), self.assertRaises(core.SpecError):
                core.validate_spec(spec)
        for kind, field in (("box", "box_fill_alpha"), ("violin", "violin_inner_fill_alpha")):
            for endpoint in (0, 1):
                spec = self.specification(kind)
                spec["options"][field] = endpoint
                core.validate_spec(spec)

    def test_point_override_rejects_invisible_and_invalid_color_values(self):
        for value in (None, True, False, 123, [], [1, 0, 0], "not-a-color", "none", "#11223300"):
            with self.subTest(value=value):
                spec = self.specification()
                spec["options"]["point_color"] = value
                with self.assertRaises(core.SpecError):
                    core.validate_spec(spec)
        for value in ("#343434", "black", "#34343480"):
            spec = self.specification()
            spec["options"]["point_color"] = value
            core.validate_spec(spec)

    def test_svg_and_exported_mapping_bind_the_actual_independent_faces_edges_and_points(self):
        spec = self.specification("violin")
        spec["options"].update(point_color="#3C3C3C", violin_inner_fill_alpha=1)
        output = self.root / "mapped"
        self.assertEqual(core.render(self.source, spec, output)["status"], "pass")
        state = json.loads((output / "elements.json").read_text())
        svg = ET.parse(output / "panel.svg").getroot()
        namespace = "{http://www.w3.org/2000/svg}"
        for element in state["elements"]:
            if element["role"] == "point-group":
                self.assertEqual(element["editable"]["color"], "/options/point_color")
                group = svg.find(f".//{namespace}g[@id='{element['id']}']")
                self.assertIsNotNone(group)
                self.assertTrue(any("#3c3c3c" in node.attrib.get("style", "").lower() for node in group.iter()))
            if element["role"] == "summary-line" and element["label"].endswith("Q1–Q3"):
                group_label = element["label"].split(" · ")[0]
                self.assertEqual(element["editable"]["facecolor"], core.figure_elements.pointer("colors", group_label))
                self.assertEqual(element["editable"]["edgecolor"], "/line_roles/summary/color")
                group = svg.find(f".//{namespace}g[@id='{element['id']}']")
                self.assertIsNotNone(group)
                styles = " ".join(node.attrib.get("style", "") for node in group.iter()).lower()
                self.assertIn(spec["colors"][group_label].lower(), styles)
                self.assertIn("#303030", styles)

    def test_rerendering_a_mapped_face_edit_changes_only_the_adopted_category_face(self):
        for kind in ("box", "violin"):
            with self.subTest(kind=kind):
                spec = self.specification(kind)
                spec["options"].update(point_color="#3C3C3C")
                spec["options"]["box_fill_alpha" if kind == "box" else "violin_inner_fill_alpha"] = 1
                before, _, _ = self.draw(spec)
                role = "distribution" if kind == "box" else "summary-line"
                label = "A/~" if kind == "box" else "A/~ · Q1–Q3"
                entry = next(item for item in self.elements(before, role) if item["label"] == label)
                changed = deepcopy(spec)
                parts = [part.replace("~1", "/").replace("~0", "~")
                         for part in entry["editable"]["facecolor"][1:].split("/")]
                target = changed
                for part in parts[:-1]:
                    target = target[part]
                target[parts[-1]] = "#E8D2B2"
                after, _, _ = self.draw(changed)
                for index, group in enumerate(("A/~", "B")):
                    patch = after.axes[0].patches[index]
                    expected = "#E8D2B2" if group == "A/~" else spec["colors"][group]
                    self.assertEqual(patch.get_facecolor(), core.mcolors.to_rgba(expected, 1))
                    self.assertEqual(patch.get_edgecolor(), core.mcolors.to_rgba("#303030"))
                for item in self.elements(after, "point-group"):
                    self.assertTrue(np.allclose(item["_artist"].get_facecolors(), [core.mcolors.to_rgba("#3C3C3C")]))
                self.assert_raw_values_and_packing_unchanged(before, after, "vertical")

    def test_color_choices_leave_requested_statistical_results_and_source_export_unchanged(self):
        source_bytes = self.source.read_bytes()
        spec = self.specification()
        spec["statistics"] = {"method": "mannwhitney", "groups": ["A/~", "B"]}
        adopted = deepcopy(spec)
        adopted["options"].update(point_color="#3C3C3C", box_fill_alpha=1)
        old, new = self.root / "statistics-old", self.root / "statistics-new"
        core.render(self.source, spec, old)
        core.render(self.source, adopted, new)
        self.assertEqual(json.loads((old / "stats.json").read_text()), json.loads((new / "stats.json").read_text()))
        with self.source.open(newline="") as stream:
            expected = list(csv.DictReader(stream))
        with (new / "plotting-data.csv").open(newline="") as stream:
            actual = list(csv.DictReader(stream))
        self.assertEqual(len(expected), len(actual))
        for raw, exported in zip(expected, actual):
            self.assertAlmostEqual(float(raw["value"]), float(exported["value"]))
            for field in ("group", "unit", "note"):
                self.assertEqual(raw[field], exported[field])
        self.assertEqual(self.source.read_bytes(), source_bytes)


if __name__ == "__main__":
    unittest.main()
