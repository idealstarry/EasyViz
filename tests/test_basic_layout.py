"""Optional layer geometry must preserve source values and old specifications."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/render.py"
loader = importlib.util.spec_from_file_location("basic_layout_renderer", SCRIPT)
core = importlib.util.module_from_spec(loader)
loader.loader.exec_module(core)


class BasicLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-basic-layout-")
        self.root = Path(self.temp.name)
        self.source = self.root / "observations.csv"
        self.source.write_text("id,g,v\n" + "".join(f"A{i},A,{i + 2}\n" for i in range(7))
                               + "".join(f"B{i},B,{i + 4}\n" for i in range(7)))
        self.base = {"chart": "distribution", "fields": {"group": "g", "value": "v", "unit": "id"},
                     "layout": {"width_mm": 110, "height_mm": 88, "font": "DejaVu Sans", "dpi": 120,
                                "margins": {"left": .2, "right": .85, "bottom": .18, "top": .93}},
                     "options": {"kind": "box", "point_area_pt2": 9, "point_layout": "beeswarm"},
                     "seed": 17, "formats": ["svg", "png"]}

    def tearDown(self):
        core.plt.close("all")
        self.temp.cleanup()

    def draw(self, spec, source=None):
        data = core.prepare(source or self.source, spec)
        result = core.statistics(data, spec)
        layout, typography, rc = core.setup(deepcopy(spec))
        with core.plt.rc_context(rc):
            fig, _ = core.draw(data, spec, layout, typography, result)
            fig.canvas.draw()
        return fig, data, result

    @staticmethod
    def raw_points(fig):
        return [entry["_artist"] for entry in fig._easyviz_elements if entry["role"] == "point-group"]

    def test_shifted_points_preserve_values_and_summary_in_both_orientations(self):
        for orientation in ("vertical", "horizontal"):
            for policy in ("jitter", "beeswarm"):
                with self.subTest(orientation=orientation, policy=policy):
                    spec = deepcopy(self.base)
                    spec["options"].update(orientation=orientation, point_layout=policy)
                    before, source, _ = self.draw(spec)
                    shifted = deepcopy(spec)
                    shifted["options"]["point_category_offset"] = .2
                    after, moved, _ = self.draw(shifted)
                    category_axis = 0 if orientation == "vertical" else 1
                    value_axis = 1 - category_axis
                    for first, second in zip(self.raw_points(before), self.raw_points(after)):
                        np.testing.assert_array_equal(first.get_offsets()[:, value_axis], second.get_offsets()[:, value_axis])
                        np.testing.assert_allclose(second.get_offsets()[:, category_axis] - first.get_offsets()[:, category_axis], .2, atol=1e-12)
                        np.testing.assert_array_equal(first.get_sizes(), second.get_sizes())
                    for first, second in zip(before.axes[0].patches, after.axes[0].patches):
                        np.testing.assert_array_equal(first.get_path().vertices, second.get_path().vertices)
                    for first, second in zip(before.axes[0].lines, after.axes[0].lines):
                        np.testing.assert_array_equal(first.get_xydata(), second.get_xydata())
                    self.assertEqual(source.id.tolist(), moved.id.tolist())
                    self.assertEqual(after._easyviz_point_layout["categorical_boundary_rows"], [])

    def test_shifted_beeswarm_capacity_reports_failure_without_dropping_ties(self):
        self.source.write_text("id,g,v\n" + "".join(f"A{i},A,5\n" for i in range(15)) + "B,B,9\n")
        spec = deepcopy(self.base)
        spec["layout"]["margins"].update(left=.45, right=.6)
        spec["options"].update(point_category_offset=.4, point_max_offset_mm=4)
        fig, data, _ = self.draw(spec)
        report = fig._easyviz_point_layout
        self.assertEqual(report["status"], "needs_revision")
        self.assertGreater(report["spacing_violation_pairs"], 0)
        self.assertEqual(len(data), 16)
        self.assertEqual(len(self.raw_points(fig)[0].get_offsets()), 15)
        np.testing.assert_array_equal(self.raw_points(fig)[0].get_offsets()[:, 1], np.full(15, 5))

    def test_jitter_shift_cannot_silently_escape_original_category_lane(self):
        spec = deepcopy(self.base)
        spec["options"].update(point_layout="jitter", point_category_offset=.4)
        fig, data, _ = self.draw(spec)
        self.assertEqual(fig._easyviz_point_layout["status"], "needs_revision")
        self.assertTrue(fig._easyviz_point_layout["categorical_boundary_rows"])
        self.assertEqual(len(data), 14)

    def test_violin_width_changes_only_categorical_kde_geometry(self):
        for orientation in ("vertical", "horizontal"):
            spec = deepcopy(self.base)
            spec["options"].update(kind="violin", orientation=orientation, violin_inner="box")
            original, source, first_stats = self.draw(spec)
            narrow = deepcopy(spec)
            narrow["options"]["violin_width"] = .35
            changed, moved, second_stats = self.draw(narrow)
            numeric = 1 if orientation == "vertical" else 0
            categorical = 1 - numeric
            first = [entry["_artist"] for entry in original._easyviz_elements if entry["role"] == "distribution"]
            second = [entry["_artist"] for entry in changed._easyviz_elements if entry["role"] == "distribution"]
            for center, (wide, thin) in enumerate(zip(first, second)):
                wide_vertices, thin_vertices = wide.get_paths()[0].vertices, thin.get_paths()[0].vertices
                np.testing.assert_array_equal(wide_vertices[:, numeric], thin_vertices[:, numeric])
                np.testing.assert_allclose(thin_vertices[:, categorical] - center, (wide_vertices[:, categorical] - center) / 2, atol=1e-12)
            self.assertEqual(first_stats["violin_inner_summaries"], second_stats["violin_inner_summaries"])
            np.testing.assert_array_equal(source.v, moved.v)

    def heatmap(self):
        self.source.write_text("r,c,v\nR1,long A,1\nR1,long B,2\nR1,long C,3\nR2,long A,4\nR2,long B,5\nR2,long C,6\n")
        return {"chart": "heatmap", "fields": {"row": "r", "column": "c", "value": "v"},
                "layout": deepcopy(self.base["layout"]), "formats": ["svg", "png"],
                "options": {"color_limits": [0, 6], "x_rotation": 0},
                "order": {"x": ["long A", "long B", "long C"], "y": ["R1", "R2"]}}

    def test_heatmap_display_labels_and_vector_seams_keep_numeric_mapping(self):
        spec = self.heatmap()
        before, data, _ = self.draw(spec)
        changed = deepcopy(spec)
        changed["options"].update(column_labels={"long A": "A", "long B": "B", "long C": "C"},
                                  cell_border_color="#FFFFFF", cell_border_width_pt=.35)
        after, moved, _ = self.draw(changed)
        np.testing.assert_array_equal(before.axes[0].images[0].get_array(), after.axes[0].images[0].get_array())
        self.assertEqual([after.axes[0].images[0].norm.vmin, after.axes[0].images[0].norm.vmax], [0, 6])
        np.testing.assert_array_equal(before.axes[0].images[0].get_extent(), after.axes[0].images[0].get_extent())
        self.assertEqual([text.get_text() for text in after.axes[0].get_xticklabels()], ["A", "B", "C"])
        seams = next(entry["_artist"] for entry in after._easyviz_elements if entry["role"] == "grid-line")
        np.testing.assert_array_equal(seams.get_segments(), [[[.5, -.5], [.5, 1.5]], [[1.5, -.5], [1.5, 1.5]], [[-.5, .5], [2.5, .5]]])
        self.assertEqual(len([entry for entry in after._easyviz_elements if entry["role"] == "matrix"][0]["source_keys"]), 6)
        np.testing.assert_array_equal(data.v, moved.v)
        core.figure_elements.attach_layout(after, changed)
        aliases = [entry for entry in after._easyviz_elements if entry["role"] == "tick-label" and entry["spec_paths"]]
        self.assertEqual([entry["source_keys"][0]["column"] for entry in aliases], ["long A", "long B", "long C"])
        self.assertEqual([entry["spec_paths"][0] for entry in aliases], ["/options/column_labels/long A", "/options/column_labels/long B", "/options/column_labels/long C"])
        output = self.root / "seams.svg"
        after.savefig(output)
        self.assertIn(seams.get_gid(), output.read_text())

    def test_explicit_zero_new_geometry_preserves_legacy_pixels(self):
        for spec in (deepcopy(self.base), self.heatmap()):
            if spec["chart"] == "distribution":
                # heatmap() changed the temporary input; restore the observations.
                self.source.write_text("id,g,v\nA1,A,2\nA2,A,4\nB1,B,5\nB2,B,7\n")
            else:
                spec = self.heatmap()
            first, _, _ = self.draw(spec)
            pixels = np.asarray(first.canvas.buffer_rgba()).copy()
            zero = deepcopy(spec)
            zero["options"]["point_category_offset" if spec["chart"] == "distribution" else "cell_border_width_pt"] = 0
            second, _, _ = self.draw(zero)
            np.testing.assert_array_equal(pixels, np.asarray(second.canvas.buffer_rgba()))

    def test_invalid_width_offsets_and_aliases_are_rejected(self):
        for value in (True, "0.2", None, float("nan"), -.41, .41):
            spec = deepcopy(self.base)
            spec["options"]["point_category_offset"] = value
            with self.subTest(offset=value), self.assertRaises(core.SpecError):
                core.validate_spec(spec)
        for value in (True, "0.3", None, float("inf"), 0, -1, 1.01):
            spec = deepcopy(self.base)
            spec["options"].update(kind="violin", violin_width=value)
            with self.subTest(width=value), self.assertRaises(core.SpecError):
                core.validate_spec(spec)
        for options in ({"cell_border_width_pt": -1}, {"cell_border_width_pt": True},
                        {"cell_border_color": "invalid"}, {"column_labels": {}},
                        {"column_labels": {"long A": ""}}, {"column_labels": {"long A": "A", "long B": "A"}},
                        {"column_labels": {"long A": "A"}},
                        {"column_labels": {"long A": "A", "long B": "B", "wrong": "C"}}):
            spec = self.heatmap()
            spec["options"].update(options)
            with self.subTest(options=options), self.assertRaises(core.SpecError):
                self.draw(spec)


if __name__ == "__main__":
    unittest.main()
