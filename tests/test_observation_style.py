"""Explicit open observations preserve data, physical size and source bindings."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def load(name, filename):
    loader = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


core = load("observation_style_renderer", "render.py")
requests = load("observation_style_requests", "apply_figure_requests.py")


class ObservationStyleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-observation-style-")
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source.csv"
        self.source.write_text("id,g,x,v,size\n001,A,1,2,0\n002,A,2,3,25\n003,B,3,4,50\n004,B,4,6,100\n")
        self.spec = {"chart": "scatter", "fields": {"x": "x", "y": "v", "group": "g", "unit": "id"},
                     "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "dpi": 120,
                                "margins": {"left": .19, "right": .77, "bottom": .23, "top": .88}},
                     "colors": {"A": "#0072B2", "B": "#D55E00"},
                     "options": {"point_area_pt2": 9}, "formats": ["svg", "pdf", "png"], "seed": 23}

    def tearDown(self):
        core.plt.close("all")
        self.temp.cleanup()

    def distribution(self):
        spec = deepcopy(self.spec)
        spec.update(chart="distribution", fields={"group": "g", "value": "v", "unit": "id"})
        return spec

    def draw(self, spec):
        data = core.prepare(self.source, spec)
        layout, typography, rc = core.setup(spec)
        with core.plt.rc_context(rc):
            fig, _ = core.draw(data, spec, layout, typography, core.statistics(data, spec))
            fig.canvas.draw()
        return fig, data

    @staticmethod
    def points(fig):
        return {element["label"]: element["_artist"] for element in fig._easyviz_elements
                if element["role"] == "point-group"}

    def test_hollow_scatter_coordinates_size_opacity_and_legend_match(self):
        spec = deepcopy(self.spec)
        spec["options"].update(point_style="hollow", point_edge_width_pt=.6, alpha=.7)
        fig, data = self.draw(spec)
        for group, artist in self.points(fig).items():
            np.testing.assert_array_equal(artist.get_offsets(), data.loc[data.g == group, ["x", "v"]])
            np.testing.assert_array_equal(artist.get_sizes(), [9])
            self.assertEqual(len(artist.get_facecolors()), 0)
            np.testing.assert_allclose(artist.get_edgecolors(), [core.mcolors.to_rgba(spec["colors"][group], .7)])
            np.testing.assert_array_equal(artist.get_linewidths(), [.6])
            self.assertEqual(artist.get_alpha(), .7)
        legend = fig._easyviz_legend_layout.entries[0]["artist"]
        for group, handle in zip(("A", "B"), legend.legend_handles):
            self.assertEqual(handle.get_markerfacecolor(), "none")
            self.assertEqual(handle.get_markeredgecolor(), spec["colors"][group])
            self.assertEqual(handle.get_markeredgewidth(), .6)
            self.assertEqual(handle.get_alpha(), .7)
        self.assertEqual(fig._easyviz_mark_geometry["circle_fill_area_pt2"], 0)
        self.assertEqual(fig._easyviz_mark_geometry["outer_diameter_pt"], 3.6)
        self.assertEqual(fig._easyviz_legend_layout.validate()["status"], "pass")

    def test_ungrouped_hollow_uses_explicit_point_color_and_default_stroke(self):
        spec = deepcopy(self.spec)
        del spec["fields"]["group"]
        spec["options"].update(point_style="hollow", point_color="#AA11CC", alpha=1)
        fig, data = self.draw(spec)
        artist = self.points(fig)["Observations"]
        np.testing.assert_array_equal(artist.get_offsets(), data[["x", "v"]])
        np.testing.assert_allclose(artist.get_edgecolors(), [core.mcolors.to_rgba("#AA11CC")])
        np.testing.assert_array_equal(artist.get_linewidths(), [.45])

    def test_omitted_options_and_explicit_filled_keep_identical_legacy_pixels_and_geometry(self):
        for spec in (self.spec, self.distribution()):
            with self.subTest(chart=spec["chart"]):
                legacy, original = self.draw(spec)
                expected_pixels = np.asarray(legacy.canvas.buffer_rgba()).copy()
                explicit = deepcopy(spec)
                explicit["options"]["point_style"] = "filled"
                if spec["chart"] == "distribution":
                    explicit["options"]["box_style"] = "filled"
                filled, repeated = self.draw(explicit)
                np.testing.assert_array_equal(np.asarray(filled.canvas.buffer_rgba()), expected_pixels)
                self.assertEqual(filled._easyviz_mark_geometry, legacy._easyviz_mark_geometry)
                pd.testing.assert_frame_equal(original, repeated)
                for artist in self.points(legacy).values():
                    self.assertEqual(artist.get_alpha(), .85)
                    np.testing.assert_array_equal(artist.get_linewidths(), [0])
                if spec["chart"] == "distribution":
                    for patch in legacy.axes[0].patches:
                        self.assertEqual(patch.get_facecolor()[3], .22)

    def test_hollow_outline_distribution_retains_numeric_values_jitter_rows_and_size(self):
        spec = self.distribution()
        legacy, before = self.draw(spec)
        for orientation in ("vertical", "horizontal"):
            with self.subTest(orientation=orientation):
                styled = deepcopy(spec)
                styled["options"].update(point_style="hollow", point_edge_width_pt=.45,
                                         box_style="outline", alpha=1, orientation=orientation)
                fig, data = self.draw(styled)
                pd.testing.assert_frame_equal(data, before)
                numeric_axis = 1 if orientation == "vertical" else 0
                for group, artist in self.points(fig).items():
                    np.testing.assert_array_equal(artist.get_offsets()[:, numeric_axis], data.loc[data.g == group, "v"])
                    np.testing.assert_array_equal(artist.get_sizes(), [9])
                    self.assertEqual(len(artist.get_facecolors()), 0)
                    self.assertEqual(artist.get_alpha(), 1)
                for patch in fig.axes[0].patches:
                    self.assertEqual(patch.get_facecolor()[3], 0)
                    self.assertGreater(patch.get_linewidth(), 0)

    def test_compact_box_retains_quartiles_and_every_raw_value(self):
        for orientation in ("vertical", "horizontal"):
            spec = self.distribution()
            spec["options"].update(box_width=.18, box_style="outline", alpha=1, orientation=orientation)
            fig, data = self.draw(spec)
            numeric_axis = 1 if orientation == "vertical" else 0
            for i, (group, artist) in enumerate(self.points(fig).items()):
                values = data.loc[data.g == group, "v"].to_numpy()
                np.testing.assert_array_equal(artist.get_offsets()[:, numeric_axis], values)
                vertices = fig.axes[0].patches[i].get_path().vertices
                np.testing.assert_allclose([vertices[:, numeric_axis].min(), vertices[:, numeric_axis].max()], np.quantile(values, [.25, .75]))
                self.assertAlmostEqual(np.ptp(vertices[:, 1 - numeric_axis]), .18)
        for width in (True, 0, -.1, 1.01, float("nan"), float("inf"), ".18"):
            spec = self.distribution()
            spec["options"]["box_width"] = width
            with self.subTest(width=width), self.assertRaises(core.SpecError):
                core.validate_spec(spec)

    def test_hollow_beeswarm_uses_outer_stroke_envelope_and_retains_tied_values(self):
        self.source.write_text("id,g,v\n" + "".join(f"{i:03d},A,5\n" for i in range(7)))
        for orientation in ("vertical", "horizontal"):
            with self.subTest(orientation=orientation):
                spec = self.distribution()
                spec["options"].update(point_style="hollow", point_edge_width_pt=.6, alpha=1,
                                        point_layout="beeswarm", point_max_offset_mm=5,
                                        point_gap_pt=.3, orientation=orientation)
                fig, data = self.draw(spec)
                report = fig._easyviz_point_layout
                artist = self.points(fig)["A"]
                numeric_axis = 1 if orientation == "vertical" else 0
                np.testing.assert_array_equal(artist.get_offsets()[:, numeric_axis], np.full(7, 5))
                np.testing.assert_array_equal(artist.get_sizes(), [9])
                positions = fig.axes[0].transData.transform(artist.get_offsets()) * 72 / fig.dpi
                audited = core.distribution_collision_report(positions, 3.6, .3)
                self.assertEqual(audited["status"], "pass")
                self.assertAlmostEqual(audited["minimum_center_distance_pt"], 3.9, places=7)
                self.assertEqual(report["diameter_pt"], 3.6)
                self.assertEqual(report["marker_diameter_pt"], 3)
                self.assertEqual(report["point_edge_width_pt"], .6)
                self.assertEqual(report["status"], "pass")
                self.assertEqual(len(data), 7)

    def test_stroke_capacity_failure_keeps_all_rows_and_exports(self):
        self.source.write_text("id,g,v\n" + "".join(f"{i:03d},A,5\n" for i in range(7)))
        spec = self.distribution()
        spec["options"].update(point_layout="beeswarm", point_max_offset_mm=4, point_gap_pt=.3)
        filled, _ = self.draw(spec)
        self.assertEqual(filled._easyviz_point_layout["status"], "pass")
        spec["options"].update(point_style="hollow", point_edge_width_pt=1, alpha=1)
        output = self.root / "stroke-capacity"
        with self.assertRaisesRegex(core.SpecError, "observation spacing conflicts"):
            core.render(self.source, spec, output)
        qa = json.loads((output / "qa.json").read_text())
        self.assertEqual(qa["point_layout"]["status"], "needs_revision")
        self.assertEqual(qa["point_layout"]["diameter_pt"], 4)
        self.assertGreater(qa["point_layout"]["spacing_violation_pairs"], 0)
        self.assertEqual(qa["input_rows"], 7)
        self.assertEqual(len(pd.read_csv(output / "plotting-data.csv")), 7)
        for extension in spec["formats"]:
            self.assertTrue((output / f"panel.{extension}").is_file())

    def test_options_reject_invalid_types_and_quantitative_fill_area_before_input(self):
        cases = [{"point_style": value} for value in ("open", None, 1, [], {})]
        cases += [{"point_style": "hollow", "point_edge_width_pt": value}
                  for value in (0, -1, float("nan"), float("inf"), True, ".45", None)]
        cases += [{"point_edge_width_pt": .45}, {"point_style": "filled", "point_edge_width_pt": .45}]
        for chart in ("scatter", "distribution"):
            for options in cases:
                with self.subTest(chart=chart, options=options):
                    spec = deepcopy(self.spec) if chart == "scatter" else self.distribution()
                    spec["options"] = options
                    with self.assertRaises(core.SpecError):
                        core.prepare(self.root / "absent.csv", spec)
        for options in ({"point_style": "hollow"}, {"point_style": "hollow", "point_edge_width_pt": .45},
                        {"point_style": "filled", "point_edge_width_pt": .45}):
            with self.subTest(mapped=options):
                spec = deepcopy(self.spec)
                spec["fields"]["size"] = "size"
                spec["options"] = options
                with self.assertRaisesRegex(core.SpecError, "circle fill area"):
                    core.prepare(self.root / "absent.csv", spec)
        dot = {"chart": "dotplot", "fields": {"x": "g", "y": "id", "size": "size", "color": "v"}}
        for options in ({"point_style": "hollow"}, {"point_edge_width_pt": .45}):
            with self.subTest(dot=options):
                dot["options"] = options
                with self.assertRaisesRegex(core.SpecError, "Unknown dotplot options"):
                    core.prepare(self.root / "absent.csv", dot)
        for options in ({"box_style": "open"}, {"box_style": None}, {"kind": "violin", "box_style": "outline"}):
            with self.subTest(box=options):
                spec = self.distribution()
                spec["options"] = options
                with self.assertRaises(core.SpecError):
                    core.prepare(self.root / "absent.csv", spec)

    def test_render_and_category_color_request_preserve_rows_and_change_edges_and_legend(self):
        spec = deepcopy(self.spec)
        spec["options"].update(point_style="hollow", point_edge_width_pt=.45, alpha=1)
        path = self.root / "spec.json"
        path.write_text(json.dumps(spec))
        output = self.root / "original"
        original = self.source.read_bytes()
        qa = core.render(self.source, spec, output, spec_path=path)
        self.assertEqual(qa["status"], "pass")
        plotted = pd.read_csv(output / "plotting-data.csv", dtype={"id": str})
        pd.testing.assert_frame_equal(plotted, pd.read_csv(self.source, dtype={"id": str}))
        manifest = json.loads((output / "elements.json").read_text())
        self.assertEqual(manifest["version"]["input_sha256"], hashlib.sha256(original).hexdigest())
        app = requests.FigureWorkbench(output)
        item = app.change({"version": app.state()["version"], "selector": {"category": "A"},
                           "property": "color", "value": "#AA11CC", "instruction": "Use purple for A."})["request"]
        target = self.root / "edited"
        plan = requests.prepare_requests(output, target, [item["id"]])
        self.assertEqual(plan["patches"][0]["spec_path"], "/colors/A")
        edited = json.loads((target / "plot-spec.json").read_text())
        fig, data = self.draw(edited)
        np.testing.assert_allclose(self.points(fig)["A"].get_edgecolors(), [core.mcolors.to_rgba("#AA11CC")])
        handle = fig._easyviz_legend_layout.entries[0]["artist"].legend_handles[0]
        self.assertEqual(handle.get_markeredgecolor(), "#AA11CC")
        pd.testing.assert_frame_equal(data, core.prepare(self.source, spec))
        self.assertEqual(self.source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
