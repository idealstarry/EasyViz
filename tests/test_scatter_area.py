"""Mapped scatter areas and supplied reference lines retain their meanings."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from marker_geometry import collection_fill_areas_pt2


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/render.py"
loader = importlib.util.spec_from_file_location("easyviz_scatter_area_renderer", SCRIPT)
renderer = importlib.util.module_from_spec(loader)
loader.loader.exec_module(renderer)


class ScatterAreaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-scatter-area-")
        self.root = Path(self.temp.name)
        self.source = self.csv("source.csv", "effect,score,count,class,id\n-2,0.2,0,A,S1\n-0.5,2,25,A,S2\n0.5,1,50,B,S3\n2,4,100,B,S4\n")
        self.spec = {"chart": "scatter", "fields": {"x": "effect", "y": "score", "size": "count", "group": "class", "unit": "id"},
                     "layout": {"width_mm": 140, "height_mm": 100, "font": "DejaVu Sans", "dpi": 100, "auto_fit": True},
                     "labels": {"x": "Effect", "y": "Score", "size": "Count"},
                     "options": {"size_max": 100, "max_area_pt2": 144, "size_legend": [25, 50, 100]},
                     "formats": ["pdf", "svg", "png"]}

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def csv(self, name, content):
        path = self.root / name
        path.write_text(content)
        return path

    def draw(self, source=None, spec=None):
        source = self.source if source is None else source
        spec = self.spec if spec is None else spec
        data = renderer.prepare(source, spec)
        result = renderer.statistics(data, spec)
        layout, typography, rc = renderer.setup(spec)
        with renderer.plt.rc_context(rc):
            fig, colors = renderer.draw(data, spec, layout, typography, result)
            fig.canvas.draw()
        return data, fig, colors

    def test_actual_point_and_legend_areas_include_zero_and_both_group_keys(self):
        data, fig, colors = self.draw()
        actual = {}
        for collection in fig.axes[0].collections:
            for coordinates, area in zip(collection.get_offsets(), collection_fill_areas_pt2(collection, fig)):
                actual[tuple(map(float, coordinates))] = float(area)
        self.assertEqual(set(actual), {(-2., .2), (-.5, 2.), (.5, 1.), (2., 4.)})
        np.testing.assert_allclose(list(actual.values()), [0, 36, 72, 144], rtol=1e-6, atol=1e-10)
        np.testing.assert_allclose(data["_easyviz_area_pt2"], [0, 36, 72, 144], rtol=0, atol=0)
        np.testing.assert_allclose(data["_easyviz_marker_size_parameter_pt2"], np.array([0, 36, 72, 144]) * 4 / np.pi)
        self.assertEqual(set(colors), {"A", "B"})
        manager = fig._easyviz_legend_layout
        self.assertEqual({entry["kind"] for entry in manager.entries}, {"categorical", "size"})
        size_entry = next(entry for entry in manager.entries if entry["kind"] == "size")
        np.testing.assert_allclose([collection_fill_areas_pt2(handle, fig)[0] for handle in size_entry["artist"].legend_handles], [36, 72, 144], rtol=1e-6, atol=1e-10)
        self.assertEqual(size_entry["marker_areas_pt2"], [36, 72, 144])
        np.testing.assert_allclose(size_entry["marker_size_parameters_pt2"], np.array([36, 72, 144]) * 4 / np.pi)
        self.assertEqual(manager.validate()["status"], "pass")

    def test_exported_rows_and_supplied_classes_are_preserved(self):
        spec = deepcopy(self.spec)
        spec["options"]["reference_lines"] = {"x": [-1, 1], "y": [1.3]}
        original = self.source.read_bytes()
        output = self.root / "output"
        qa = renderer.render(self.source, spec, output)
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(qa["input_rows"], 4)
        self.assertEqual(qa["plotted_input_rows"], 4)
        plotted = pd.read_csv(output / "plotting-data.csv")
        pd.testing.assert_frame_equal(plotted[list(pd.read_csv(self.source).columns)], pd.read_csv(self.source))
        np.testing.assert_allclose(plotted["_easyviz_area_pt2"], [0, 36, 72, 144])
        np.testing.assert_allclose(plotted["_easyviz_marker_size_parameter_pt2"], np.array([0, 36, 72, 144]) * 4 / np.pi)
        self.assertEqual(json.loads((output / "stats.json").read_text())["method"], "none")
        settings = json.loads((output / "settings.json").read_text())
        self.assertEqual(settings["options"]["reference_lines"], {"x": [-1, 1], "y": [1.3]})
        self.assertEqual(settings["mark_geometry"]["mode"], "mapped_circle_fill_area")
        self.assertEqual(settings["mark_geometry"]["max_area_pt2"], 144)
        self.assertAlmostEqual(settings["mark_geometry"]["max_marker_size_parameter_pt2"], 144 * 4 / np.pi)
        self.assertEqual(settings["input_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(self.source.read_bytes(), original)
        for extension in spec["formats"]:
            self.assertTrue((output / f"panel.{extension}").exists())

    def test_ungrouped_scatter_uses_same_proportional_area_and_size_legend(self):
        spec = deepcopy(self.spec)
        del spec["fields"]["group"]
        data, fig, _ = self.draw(spec=spec)
        np.testing.assert_allclose(collection_fill_areas_pt2(fig.axes[0].collections[0], fig), [0, 36, 72, 144], rtol=1e-6, atol=1e-10)
        self.assertEqual(len(fig.axes[0].collections[0].get_offsets()), len(data))
        self.assertEqual([entry["kind"] for entry in fig._easyviz_legend_layout.entries], ["size"])

    def test_circle_area_contract_does_not_depend_on_external_scatter_marker_default(self):
        with renderer.plt.rc_context({"scatter.marker": "s"}):
            _, fig, _ = self.draw()
        areas = [value for collection in fig.axes[0].collections for value in collection_fill_areas_pt2(collection, fig)]
        np.testing.assert_allclose(areas, [0, 36, 72, 144], rtol=1e-6, atol=1e-10)

    def test_default_area_scale_and_all_zero_values_are_defined(self):
        source = self.csv("zero.csv", "x,y,s\n1,2,0\n2,3,0\n3,4,0\n")
        spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "size": "s"},
                "layout": {"font": "DejaVu Sans", "auto_fit": True}}
        data, fig, _ = self.draw(source=source, spec=spec)
        np.testing.assert_array_equal(fig.axes[0].collections[0].get_sizes(), [0, 0, 0])
        self.assertEqual(len(data), 3)
        entry = next(e for e in fig._easyviz_legend_layout.entries if e["kind"] == "size")
        self.assertEqual(entry["marker_areas_pt2"], [22.5, 45, 90])

    def test_fixed_area_scatter_retains_previous_default_and_explicit_area(self):
        for area in (None, 17):
            with self.subTest(area=area):
                spec = deepcopy(self.spec)
                del spec["fields"]["size"]
                spec["options"] = {} if area is None else {"point_area_pt2": area}
                data, fig, _ = self.draw(spec=spec)
                for collection in fig.axes[0].collections:
                    np.testing.assert_array_equal(collection.get_sizes(), [12 if area is None else area])
                self.assertNotIn("_easyviz_area_pt2", data)
                self.assertNotIn("_easyviz_marker_size_parameter_pt2", data)
                geometry = fig._easyviz_mark_geometry
                self.assertEqual(geometry["mode"], "fixed_matplotlib_size_parameter")
                self.assertNotIn("size_max", geometry)
                self.assertNotIn("max_area_pt2", geometry)
                self.assertAlmostEqual(geometry["circle_fill_area_pt2"], (12 if area is None else area) * np.pi / 4)
                np.testing.assert_allclose(collection_fill_areas_pt2(fig.axes[0].collections[0], fig), [geometry["circle_fill_area_pt2"]], rtol=1e-6)
                self.assertEqual([entry["kind"] for entry in fig._easyviz_legend_layout.entries], ["categorical"])

    def test_size_options_require_mapping_and_fixed_area_cannot_override_mapping(self):
        for option, value in (("size_max", 100), ("max_area_pt2", 144), ("size_legend", [25, 50])):
            with self.subTest(option=option):
                spec = deepcopy(self.spec)
                del spec["fields"]["size"]
                spec["options"] = {option: value}
                with self.assertRaisesRegex(renderer.SpecError, "require fields.size"):
                    renderer.prepare(self.source, spec)
        spec = deepcopy(self.spec)
        spec["options"]["point_area_pt2"] = 12
        with self.assertRaisesRegex(renderer.SpecError, "conflicts with scatter fields.size"):
            renderer.prepare(self.source, spec)

    def test_fixed_scatter_settings_do_not_invent_a_mapped_area_scale(self):
        spec = deepcopy(self.spec)
        del spec["fields"]["size"]
        spec["options"] = {}
        output = self.root / "fixed-metadata"
        renderer.render(self.source, spec, output)
        settings = json.loads((output / "settings.json").read_text())
        geometry = settings["mark_geometry"]
        self.assertEqual(geometry["mode"], "fixed_matplotlib_size_parameter")
        self.assertEqual(geometry["marker_size_parameter_pt2"], 12)
        self.assertAlmostEqual(geometry["circle_fill_area_pt2"], 12 * np.pi / 4)
        for key in ("size_max", "max_area_pt2", "source_field", "area_formula"):
            self.assertNotIn(key, geometry)
        self.assertEqual(settings["options"], {})

    def test_invalid_size_values_and_scale_values_fail_before_render(self):
        for value in ("-1", "", "NaN", "inf", "hello", "True"):
            with self.subTest(value=value):
                source = self.csv("bad-size.csv", f"effect,score,count,class,id\n1,2,{value},A,S1\n")
                with self.assertRaises(renderer.SpecError):
                    renderer.prepare(source, self.spec)
        for option, value in (("size_max", 0), ("size_max", 50), ("size_max", True),
                              ("max_area_pt2", -1), ("max_area_pt2", "144"),
                              ("size_legend", [0, 25]), ("size_legend", [101]),
                              ("size_legend", [True]), ("size_legend", "25"),
                              ("size_legend", [float("inf")])):
            with self.subTest(option=option, value=value):
                spec = deepcopy(self.spec)
                spec["options"][option] = value
                with self.assertRaises(renderer.SpecError):
                    renderer.prepare(self.source, spec)

    def test_size_legend_cannot_be_rescaled_by_display_settings(self):
        for key in ("markerscale", "key_width_mm", "key_height_mm"):
            with self.subTest(key=key):
                spec = deepcopy(self.spec)
                spec["legends"] = {"size": {key: 2}}
                with self.assertRaisesRegex(ValueError, "Unknown size legend settings"):
                    self.draw(spec=spec)

    def test_reference_lines_draw_only_supplied_numeric_positions_behind_marks(self):
        spec = deepcopy(self.spec)
        spec["options"]["reference_lines"] = {"x": [-1, 1], "y": [1.3]}
        data, fig, _ = self.draw(spec=spec)
        ax = fig.axes[0]
        self.assertEqual(len(ax.lines), 3)
        self.assertEqual([list(line.get_xdata()) for line in ax.lines[:2]], [[-1, -1], [1, 1]])
        self.assertEqual(list(ax.lines[2].get_ydata()), [1.3, 1.3])
        for line in ax.lines:
            self.assertEqual(line.get_linestyle(), "--")
            self.assertEqual(line.get_color(), "#999999")
            self.assertLess(line.get_zorder(), min(collection.get_zorder() for collection in ax.collections))
        self.assertEqual(data["class"].tolist(), ["A", "A", "B", "B"])

    def test_reference_line_keys_and_types_are_strict_and_scatter_only(self):
        for lines in ([], {"z": [1]}, {"x": 1}, {"x": (1, 2)}, {"x": [True]},
                      {"x": ["1"]}, {"y": [float("nan")]}, {"y": [float("inf")]}):
            with self.subTest(lines=lines):
                spec = deepcopy(self.spec)
                spec["options"]["reference_lines"] = lines
                with self.assertRaises(renderer.SpecError):
                    renderer.prepare(self.source, spec)
        spec = {"chart": "distribution", "fields": {"group": "class", "value": "score"},
                "options": {"reference_lines": {"y": [1]}}}
        with self.assertRaisesRegex(renderer.SpecError, "Unknown distribution options"):
            renderer.prepare(self.source, spec)

    def test_reference_lines_on_log_axes_require_positive_positions(self):
        source = self.csv("log.csv", "effect,score,count,class,id\n1,2,0,A,S1\n2,3,25,A,S2\n3,5,50,B,S3\n")
        spec = deepcopy(self.spec)
        spec["options"].update(x_scale="log", y_scale="log", reference_lines={"x": [1.5], "y": [4]})
        _, fig, _ = self.draw(source=source, spec=spec)
        self.assertEqual(fig.axes[0].get_xscale(), "log")
        self.assertEqual(fig.axes[0].get_yscale(), "log")
        self.assertEqual(list(fig.axes[0].lines[0].get_xdata()), [1.5, 1.5])
        for direction in ("x", "y"):
            for position in (0, -1):
                with self.subTest(direction=direction, position=position):
                    invalid = deepcopy(spec)
                    invalid["options"]["reference_lines"] = {direction: [position]}
                    with self.assertRaisesRegex(renderer.SpecError, "must be strictly positive"):
                        renderer.prepare(source, invalid)

    def test_named_profile_area_scale_is_shared_across_different_subsets(self):
        profile = self.root / "figure-profile.json"
        profile_data = {"version": 1, "layout": {"font": "DejaVu Sans", "font_size_pt": 8, "line_width_pt": .6, "dpi": 100},
                        "colors": {"A": "#0072B2", "B": "#D55E00"},
                        "panels": {"A": {"width_mm": 140, "height_mm": 100}},
                        "size_scales": {"count": {"size_max": 100, "max_area_pt2": 144, "size_legend": [25, 50, 100]}}}
        profile.write_text(json.dumps(profile_data))
        subset = self.csv("subset.csv", "effect,score,count,class,id\n0.5,1,50,B,S3\n1.5,3,75,B,S5\n")
        base = deepcopy(self.spec)
        base.update(profile=profile.name, panel="A", size_scale="count")
        base["options"] = {}
        for name, source in (("full", self.source), ("subset", subset)):
            with self.subTest(name=name):
                original = deepcopy(base)
                resolved, record = renderer.resolve_spec(base, spec_path=self.root / "panel.json")
                self.assertEqual(base, original)
                self.assertEqual(record["size_scale"], "count")
                data, fig, _ = self.draw(source=source, spec=resolved)
                self.assertEqual(data.loc[data["count"].eq(50), "_easyviz_area_pt2"].tolist(), [72])
                entry = next(e for e in fig._easyviz_legend_layout.entries if e["kind"] == "size")
                self.assertEqual(entry["marker_areas_pt2"], [36, 72, 144])
                np.testing.assert_allclose([collection_fill_areas_pt2(handle, fig)[0] for handle in entry["artist"].legend_handles], [36, 72, 144], rtol=1e-6)
                output = self.root / name
                qa = renderer.render(source, base, output, spec_path=self.root / "panel.json")
                self.assertEqual(qa["status"], "pass")
                settings = json.loads((output / "settings.json").read_text())
                self.assertEqual(settings["figure_profile"]["size_scale"], "count")
                self.assertEqual(settings["options"]["size_max"], 100)
        for option, value in (("size_max", 50), ("max_area_pt2", 100), ("size_legend", [25, 50])):
            with self.subTest(option=option):
                conflict = deepcopy(base)
                conflict["options"] = {option: value}
                with self.assertRaisesRegex(renderer.SpecError, f"{option} conflicts"):
                    renderer.resolve_spec(conflict, spec_path=self.root / "panel.json")
        no_mapping = deepcopy(base)
        del no_mapping["fields"]["size"]
        with self.assertRaisesRegex(renderer.SpecError, "scatter with fields.size"):
            renderer.resolve_spec(no_mapping, spec_path=self.root / "panel.json")
        unknown = deepcopy(base)
        unknown["size_scale"] = "missing"
        with self.assertRaisesRegex(renderer.SpecError, "Unknown size_scale"):
            renderer.resolve_spec(unknown, spec_path=self.root / "panel.json")


if __name__ == "__main__":
    unittest.main()
