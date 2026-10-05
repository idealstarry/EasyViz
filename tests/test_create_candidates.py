"""New Create candidates must preserve the source and actual quantitative artists."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/create_candidates.py"
loader = importlib.util.spec_from_file_location("easyviz_candidate_tests", SCRIPT)
candidates = importlib.util.module_from_spec(loader)
loader.loader.exec_module(candidates)
core = candidates.core


class CreateCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-create-candidates-")
        self.root = Path(self.temp.name)
        self.layout = {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100}

    def tearDown(self):
        core.plt.close("all")
        self.temp.cleanup()

    def run_candidates(self, body, spec, name="output", **kwargs):
        source = self.root / f"{name}.csv"
        source.write_text(body, encoding="utf-8")
        spec_path = self.root / f"{name}.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        data_before, spec_before = source.read_bytes(), spec_path.read_bytes()
        out = self.root / name
        manifest = candidates.create_candidates(source, spec_path, out, new_draft=True, **kwargs)
        self.assertEqual(source.read_bytes(), data_before)
        self.assertEqual(spec_path.read_bytes(), spec_before)
        self.assertEqual((out / "source.csv").read_bytes(), data_before)
        self.assertEqual((out / "source-spec.json").read_bytes(), spec_before)
        self.assertTrue(manifest["inputs_unchanged"])
        self.assertIsNone(manifest["aesthetic_winner"])
        for record in manifest["candidates"]:
            self.assertEqual(record["visual_review"]["status"], "pending")
        return manifest, out

    def spec(self, chart, fields, **kwargs):
        return {"chart": chart, "fields": fields, "layout": deepcopy(self.layout), "formats": ["png", "svg"], **kwargs}

    def read_candidates(self, out, manifest):
        for record in manifest["candidates"]:
            directory = out / record["id"]
            yield record, json.loads((directory / "spec.json").read_text()), json.loads((directory / "geometry-evidence.json").read_text()), directory

    def test_few_group_box_compacts_actual_axes_and_separates_raw_summary(self):
        body = "id,g,v\n001,NA,1\n002,NA,2\n003,NA,3\n004,null,2\n005,null,4\n006,null,6\n"
        spec = self.spec("distribution", {"group": "g", "value": "v", "unit": "id"},
                         order={"group": ["null", "NA"]}, options={"point_area_pt2": 16, "y_limits": [0, 8]},
                         statistics={"method": "welch", "groups": ["null", "NA"], "annotate": False})
        manifest, out = self.run_candidates(body, spec)
        self.assertEqual(manifest["status"], "visual_review_pending")
        self.assertEqual(len(manifest["candidates"]), 2)
        widths = []
        stats = []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(result["options"]["point_area_pt2"], 16)
            self.assertEqual(result["statistics"], spec["statistics"])
            self.assertEqual(result["order"], spec["order"])
            self.assertEqual(geometry["category_tick_labels"]["x"], ["null", "NA"])
            self.assertEqual(geometry["source_to_artist"]["status"], "pass")
            self.assertEqual(geometry["raw_summary_categorical_envelope_crossings"], 0)
            self.assertEqual(geometry["numeric_limits"]["y"], [0., 8.])
            widths.append(geometry["data_region_mm"][2])
            self.assertLess(widths[-1], manifest["baseline_geometry"]["data_region_mm"][2] * .5)
            self.assertEqual(geometry["typography"]["tick"], 8)
            with Image.open(directory / "panel.png") as image:
                self.assertEqual(image.size, (round(120 / 25.4 * 100), round(90 / 25.4 * 100)))
            plotted = pd.read_csv(directory / "plotting-data.csv", dtype={"id": str}, keep_default_na=False)
            self.assertEqual(plotted.id.tolist(), [f"{v:03d}" for v in range(1, 7)])
            self.assertEqual(plotted.v.tolist(), [1, 2, 3, 2, 4, 6])
            stats.append(json.loads((directory / "stats.json").read_text()))
        self.assertNotEqual(*widths)
        self.assertEqual(*stats)

    def test_horizontal_log_distribution_retains_numeric_axes(self):
        spec = self.spec("distribution", {"group": "g", "value": "v"},
                         options={"orientation": "horizontal", "x_scale": "log", "x_limits": [.1, 100], "point_area_pt2": 9})
        manifest, out = self.run_candidates("g,v\nA,.2\nA,2\nA,20\nB,.3\nB,3\nB,30\n", spec)
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(geometry["scales"]["x"], "log")
            self.assertEqual(geometry["numeric_limits"]["x"], [.1, 100.])
            self.assertTrue(geometry["source_to_artist"]["numeric_coordinates_preserved"])
            self.assertLess(geometry["data_region_mm"][3], manifest["baseline_geometry"]["data_region_mm"][3])
            self.assertEqual(geometry["raw_summary_categorical_envelope_crossings"], 0)

    def test_violin_method_and_inner_quantiles_identical_across_geometry(self):
        body = "g,v\n" + "".join(f"{g},{v}\n" for g, values in (("A", [1, 2, 3, 4, 5, 8]), ("B", [2, 3, 4, 5, 6, 9])) for v in values)
        spec = self.spec("distribution", {"group": "g", "value": "v"},
                         options={"kind": "violin", "violin_inner": "box", "point_area_pt2": 9})
        manifest, out = self.run_candidates(body, spec)
        baseline_method, summaries = None, None
        shapes = []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            stats = json.loads((directory / "stats.json").read_text())
            if baseline_method is None:
                baseline_method, summaries = stats["violin_definition"], stats["violin_inner_summaries"]
            self.assertEqual(stats["violin_definition"], baseline_method)
            self.assertEqual(stats["violin_inner_summaries"], summaries)
            self.assertEqual(geometry["source_to_artist"]["observation_count"], 12)
            fig, _, _, _ = candidates._draw(out / "source.csv", result)
            bodies = [item["_artist"] for item in fig._easyviz_elements if item["role"] == "distribution"]
            shapes.append([body.get_paths()[0].vertices.copy() for body in bodies])
            core.plt.close(fig)
        # KDE evaluation coordinates and normalized density shape survive;
        # only the categorical width differs between these real artists.
        for first, second in zip(*shapes):
            np.testing.assert_array_equal(first[:, 1], second[:, 1])
            center = (first[:, 0].min() + first[:, 0].max()) / 2
            np.testing.assert_allclose((first[:, 0] - center) / spec.get("options", {}).get("violin_width", .38),
                                       (second[:, 0] - center) / .46, atol=1e-12)
        self.assertIn("Scott", baseline_method)

    def test_tall_narrow_matrix_values_order_norm_annotation_fonts_and_geometry(self):
        body = "r,c,v\n" + "".join(f"R{i},C{j},{i * 2 + j + .25}\n" for i in range(8) for j in range(2))
        spec = self.spec("heatmap", {"row": "r", "column": "c", "value": "v"},
                         order={"y": [f"R{i}" for i in reversed(range(8))], "x": ["C1", "C0"]},
                         typography={"annotation": 9}, options={"color_limits": [0, 20], "annotate_values": True, "value_format": ".2f", "x_rotation": 0})
        manifest, out = self.run_candidates(body, spec)
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(result["order"], spec["order"])
            self.assertEqual(geometry["source_to_artist"]["color_limits"], [0., 20.])
            self.assertTrue(geometry["source_to_artist"]["matrix_values_preserved"])
            self.assertEqual(geometry["typography"]["annotation"], 9)
            self.assertEqual(geometry["cell_annotations"]["status"], "pass")
            self.assertLess(geometry["data_region_mm"][2], 20)
            self.assertLess(abs(geometry["cell_dimensions_mm"][0] - geometry["cell_dimensions_mm"][1]), .01)
            self.assertEqual(len(pd.read_csv(directory / "plotting-data.csv")), 16)

    def test_fixed_scatter_coordinates_sizes_scales_and_reference_lines_preserved(self):
        spec = self.spec("scatter", {"x": "x", "y": "y", "group": "g"},
                         colors={"A": "#0066A6", "B": "#CC5500"}, options={"x_scale": "log", "y_scale": "log", "x_limits": [.1, 100], "y_limits": [.1, 100], "point_area_pt2": 23, "alpha": .7, "reference_lines": {"x": [1], "y": [3]}})
        manifest, out = self.run_candidates("x,y,g\n.2,2,A\n2,.3,B\n20,20,A\n", spec)
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(result["colors"], spec["colors"])
            for key, value in spec["options"].items():
                self.assertEqual(result["options"][key], value)
            self.assertEqual(geometry["scales"], {"x": "log", "y": "log"})
            self.assertEqual(geometry["source_to_artist"]["status"], "pass")
            fig, _, _, _ = candidates._draw(out / "source.csv", result)
            refs = [item["_artist"] for item in fig._easyviz_elements if item["role"] == "reference-line"]
            self.assertEqual([list(line.get_xdata()) for line in refs[:1]], [[1, 1]])
            self.assertEqual([list(line.get_ydata()) for line in refs[1:]], [[3, 3]])
            core.plt.close(fig)

    def test_profile_snapshot_retains_canvas_typography_and_colors(self):
        profile = {"version": 1, "layout": {"font": "DejaVu Sans", "font_size_pt": 9, "line_width_pt": .6, "dpi": 100}, "typography": {"axis": 10, "tick": 9, "legend": 9}, "panels": {"main": {"width_mm": 120, "height_mm": 90}}, "colors": {"A": "#0066A6", "B": "#CC5500"}}
        profile_path = self.root / "shared.json"
        profile_path.write_text(json.dumps(profile))
        before = profile_path.read_bytes()
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v"}, "profile": "shared.json", "panel": "main", "formats": ["png"]}
        manifest, out = self.run_candidates("g,v\nA,1\nA,2\nB,3\nB,4\n", spec)
        self.assertEqual(manifest["suggested_dimension_keys"], [])
        self.assertEqual(profile_path.read_bytes(), before)
        self.assertEqual((out / "profile.json").read_bytes(), before)
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(result["profile"], "../profile.json")
            self.assertEqual(geometry["canvas_mm"], [120., 90.])
            self.assertEqual(geometry["typography"]["axis"], 10)
            self.assertEqual(result["colors"], profile["colors"])
            resolved, _ = core.resolve_spec(result, spec_path=directory / "spec.json")
            self.assertEqual(resolved["layout"]["font_size_pt"], 9)

    def test_grouped_replicate_method_and_artist_values_unchanged(self):
        body = "condition,unit,component,value\n" + "".join(f"{c},{u},{k},{value}\n" for c in ("Control", "Treatment") for u in ("01", "02", "03") for k, value in (("RNA", int(u) + 1), ("Protein", int(u) + 3)))
        spec = self.spec("replicate", {"condition": "condition", "unit": "unit", "component": "component", "value": "value"},
                         options={"mode": "grouped", "uncertainty": "sample_sd", "marker_area_pt2": 12, "y_limits": [0, 8]}, order={"condition": ["Treatment", "Control"], "component": ["Protein", "RNA"]})
        manifest, out = self.run_candidates(body, spec)
        summaries = []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(geometry["source_to_artist"]["status"], "pass")
            self.assertEqual(result["order"], spec["order"])
            self.assertEqual(result["options"]["marker_area_pt2"], 12)
            self.assertEqual(result["options"]["uncertainty"], "sample_sd")
            self.assertEqual(geometry["numeric_limits"]["y"], [0., 8.])
            stats = json.loads((directory / "stats.json").read_text())
            self.assertFalse(stats["tests_performed"])
            self.assertFalse(stats["normalization_performed"])
            summaries.append(json.loads((directory / "summary-data.json").read_text()))
        self.assertEqual(*summaries)

    def test_explicit_cosmetics_and_manual_geometry_are_locked_and_deduplicated(self):
        spec = self.spec("distribution", {"group": "g", "value": "v"}, options={"point_layout": "jitter", "box_width": .27, "box_style": "filled", "point_color": "#000000", "point_category_offset": -.1, "alpha": .4, "point_area_pt2": 12})
        spec["layout"].update(auto_fit=False, margins={"left": .2, "right": .8, "bottom": .2, "top": .9})
        manifest, out = self.run_candidates("g,v\nA,1\nA,2\nB,3\nB,4\n", spec, count=3, render=False)
        self.assertEqual(len(manifest["candidates"]), 1)
        record, result, geometry, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(result["layout"]["margins"], spec["layout"]["margins"])
        for key, value in spec["options"].items():
            self.assertEqual(result["options"][key], value)
        self.assertEqual(record["technical_review"]["status"], "not_rendered")
        self.assertFalse((directory / "panel.png").exists())
        self.assertEqual(geometry["source_to_artist"]["status"], "pass")

    def test_only_omitted_dimensions_are_suggested_and_candidate_count_capped(self):
        spec = {"chart": "distribution", "fields": {"group": "g", "value": "v"}, "layout": {"width_mm": 93, "font": "DejaVu Sans", "dpi": 100}, "formats": ["svg"]}
        manifest, out = self.run_candidates("g,v\nA,1\nA,2\nB,3\nB,4\n", spec, count=3, render=False)
        self.assertEqual(manifest["suggested_dimension_keys"], ["height_mm"])
        self.assertLessEqual(len(manifest["candidates"]), 3)
        for _, result, geometry, _ in self.read_candidates(out, manifest):
            self.assertEqual(result["layout"]["width_mm"], 93)
            self.assertIn("png", result["formats"])
            self.assertAlmostEqual(geometry["canvas_mm"][0], 93)

    def test_color_roles_are_actual_scene_suggestions_and_explicit_palettes_remain_authoritative(self):
        body = "g,v\nA,1\nA,2\nA,3\nB,2\nB,3\nB,4\n"
        spec = self.spec("distribution", {"group": "g", "value": "v"})
        manifest, out = self.run_candidates(body, spec, count=1)
        record, result, geometry, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(result["palette"], "progeny-summary")
        self.assertEqual(result["options"]["box_style"], "filled")
        self.assertIn("EasyViz adaptations", record["color_decisions"]["palette"]["provenance"])
        fig, data, _, _ = candidates._draw(out / "source.csv", result)
        bodies = [item["_artist"] for item in fig._easyviz_elements if item["role"] == "distribution"]
        self.assertEqual(core.mcolors.to_hex(bodies[0].get_facecolor()), "#8787de")
        self.assertEqual(core.mcolors.to_hex(bodies[0].get_edgecolor()), "#333333")
        points = [item["_artist"] for item in fig._easyviz_elements if item["role"] == "point-group"]
        self.assertEqual(core.mcolors.to_hex(points[0].get_facecolors()[0]), "#454545")
        core.plt.close(fig)
        explicit = deepcopy(spec)
        explicit["palette"] = "notch2-balanced"
        explicit["line_roles"] = {"summary": {"color": "#123456", "line_width_pt": 1.25}}
        manifest, out = self.run_candidates(body, explicit, name="explicit-palette", count=1)
        _, result, _, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(result["palette"], "notch2-balanced")
        self.assertEqual(result["line_roles"]["summary"], explicit["line_roles"]["summary"])
        settings = json.loads((directory / "settings.json").read_text())
        self.assertEqual(settings["resolved_colors"]["A"], "#2581B9")
        scatter = self.spec("scatter", {"x": "x", "y": "y", "group": "g"}, options={"point_area_pt2": 12})
        manifest, out = self.run_candidates("x,y,g\n1,2,A\n3,4,B\n", scatter, name="small-mark", count=1)
        record, result, _, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(result["palette"], "scwat-blue-pink")
        settings = json.loads((directory / "settings.json").read_text())
        self.assertEqual(settings["resolved_colors"], {"A": "#3795D3", "B": "#FF5FBD"})
        self.assertIn("fitted-line vector", record["color_decisions"]["palette"]["provenance"])

    def test_heatmap_ramp_eligibility_preserves_adopted_center_and_bounds(self):
        body = "r,c,v\nA,X,-2\nA,Y,1\nB,X,0\nB,Y,3\n"
        for name, options, explicit_map, expected in (
            ("unadopted", {}, None, None),
            ("linear", {"color_limits": [-3, 4]}, None, "notch2-blue"),
            ("centered", {"color_limits": [-3, 4], "color_center": .5}, None, "scwat-blue-white-coral"),
            ("explicit", {"color_limits": [-3, 4], "color_center": .5}, "RdBu_r", "RdBu_r"),
        ):
            with self.subTest(name=name):
                spec = self.spec("heatmap", {"row": "r", "column": "c", "value": "v"}, options=options)
                if explicit_map:
                    spec["colormap"] = explicit_map
                manifest, out = self.run_candidates(body, spec, name=name, count=1)
                _, result, geometry, directory = next(self.read_candidates(out, manifest))
                self.assertEqual(result.get("colormap"), expected)
                self.assertEqual(result["options"].get("color_center"), options.get("color_center"))
                self.assertEqual(result["options"].get("color_limits"), options.get("color_limits"))
                self.assertEqual(geometry["source_to_artist"]["color_limits"], options.get("color_limits", [-2., 3.]))

    def test_more_than_four_labeled_groups_use_actual_neutral_summary_roles(self):
        body = "g,v\n" + "".join(f"G{i},{value}\n" for i in range(6) for value in (1, 2, 3))
        spec = self.spec("distribution", {"group": "g", "value": "v"})
        manifest, out = self.run_candidates(body, spec, count=1)
        record, result, geometry, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(record["technical_review"]["status"], "pass")
        self.assertEqual(geometry["category_tick_labels"]["x"], [f"G{i}" for i in range(6)])
        self.assertEqual(result["options"]["box_style"], "outline")
        self.assertIn("no multicolor mixture", record["color_decisions"]["area_role"])
        fig, _, _, _ = candidates._draw(out / "source.csv", result)
        bodies = [item["_artist"] for item in fig._easyviz_elements if item["role"] == "distribution"]
        self.assertEqual(len(bodies), 6)
        self.assertTrue(all(body.get_facecolor()[3] == 0 for body in bodies))
        self.assertTrue(all(core.mcolors.to_hex(body.get_edgecolor()) == "#333333" for body in bodies))
        core.plt.close(fig)

    def test_profile_drift_after_planning_uses_only_original_adopted_snapshot(self):
        profile = {"version": 1, "layout": {"font": "DejaVu Sans", "font_size_pt": 9, "line_width_pt": .6, "dpi": 100}, "panels": {"main": {"width_mm": 120, "height_mm": 90}}, "colors": {"A": "#0066A6", "B": "#CC5500"}}
        profile_path = self.root / "profile-drift.json"
        profile_path.write_text(json.dumps(profile))
        before = profile_path.read_bytes()
        source, spec_path, out = self.root / "profile-source.csv", self.root / "profile-source.json", self.root / "profile-output"
        source.write_text("g,v\nA,1\nA,2\nB,3\nB,4\n")
        spec_path.write_text(json.dumps({"chart": "distribution", "fields": {"group": "g", "value": "v"}, "profile": profile_path.name, "panel": "main", "formats": ["png"]}))
        draw = candidates._draw
        calls = []
        def mutate_live_profile_after_first_draw(*args, **kwargs):
            result = draw(*args, **kwargs)
            if not calls:
                changed = deepcopy(profile)
                changed["panels"]["main"]["width_mm"] = 144
                changed["colors"]["A"] = "#111111"
                profile_path.write_text(json.dumps(changed))
            calls.append(1)
            return result
        with patch.object(candidates, "_draw", side_effect=mutate_live_profile_after_first_draw):
            manifest = candidates.create_candidates(source, spec_path, out, new_draft=True, count=1)
        self.assertEqual((out / "profile.json").read_bytes(), before)
        self.assertEqual(manifest["profile"]["sha256"], candidates._digest(before))
        self.assertFalse(manifest["inputs_unchanged"])
        self.assertEqual(manifest["status"], "needs_revision")
        record, _, geometry, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(record["technical_review"]["status"], "pass")
        self.assertEqual(geometry["canvas_mm"], [120., 90.])
        self.assertEqual(json.loads((directory / "settings.json").read_text())["resolved_colors"]["A"], "#0066A6")

    def test_exception_after_passing_renderer_qa_is_failed_unconditionally(self):
        render = core.render
        def render_then_raise(*args, **kwargs):
            render(*args, **kwargs)
            raise ValueError("late render failure after QA publication")
        spec = self.spec("scatter", {"x": "x", "y": "y"})
        with patch.object(core, "render", side_effect=render_then_raise):
            manifest, out = self.run_candidates("x,y\n1,2\n2,3\n", spec, count=1)
        record, _, _, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(record["technical_review"]["renderer_status"], "pass")
        self.assertEqual(record["technical_review"]["status"], "failed")
        self.assertIn("late render failure", record["technical_review"]["error"])
        self.assertEqual(manifest["status"], "needs_revision")

    def test_invalid_unmapped_ragged_and_quantitative_area_requests_write_nothing(self):
        cases = [("scatter", {"x": "x"}, "x,y\n1,2\n"),
                 ("scatter", {"x": "x", "y": "y", "size": "s"}, "x,y,s\n1,2,4\n"),
                 ("scatter", {"x": "x", "y": "y"}, "x,y\n1,2,3\n"),
                 ("heatmap", {"row": "r", "column": "c", "value": "v"}, "r,c,v\nA,X,1\nB,Y,2\n"),
                 ("replicate", {"condition": "x", "unit": "y", "value": "s"}, "x,y,s\nA,1,4\n")]
        for number, (chart, fields, body) in enumerate(cases):
            with self.subTest(chart=chart, fields=fields):
                source, spec_path, out = self.root / "invalid.csv", self.root / "invalid.json", self.root / f"invalid-{number}"
                source.write_text(body)
                spec_path.write_text(json.dumps(self.spec(chart, fields)))
                with self.assertRaises(ValueError):
                    candidates.create_candidates(source, spec_path, out, new_draft=True)
                self.assertFalse(out.exists())

    def test_new_draft_and_fresh_directory_are_required_and_failed_packing_is_not_certified(self):
        spec = self.spec("distribution", {"group": "g", "value": "v"}, options={"point_area_pt2": 36})
        source, spec_path = self.root / "dense.csv", self.root / "dense.json"
        source.write_text("g,v\n" + "A,5\n" * 100 + "B,7\n" * 100)
        spec_path.write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, "new_draft"):
            candidates.create_candidates(source, spec_path, self.root / "undeclared")
        manifest = candidates.create_candidates(source, spec_path, self.root / "dense", new_draft=True, count=1)
        self.assertEqual(manifest["status"], "needs_revision")
        self.assertEqual(manifest["candidates"][0]["technical_review"]["status"], "failed")
        self.assertEqual(manifest["candidates"][0]["technical_review"]["renderer_status"], "needs_revision")
        self.assertEqual(manifest["candidates"][0]["visual_review"]["status"], "pending")
        plotting_data = pd.read_csv(self.root / "dense/candidate-01/plotting-data.csv")
        self.assertEqual(len(plotting_data), 200)
        self.assertEqual(plotting_data.v.tolist(), [5] * 100 + [7] * 100)
        with self.assertRaisesRegex(ValueError, "NEW directory"):
            candidates.create_candidates(source, spec_path, self.root / "dense", new_draft=True)
        planned = candidates.create_candidates(source, spec_path, self.root / "dense-plan", new_draft=True, count=1, render=False)
        self.assertEqual(planned["status"], "needs_revision")
        self.assertEqual(planned["candidates"][0]["technical_review"]["status"], "needs_revision")
        self.assertFalse((self.root / "dense-plan/candidate-01/panel.png").exists())

    def test_actual_numeric_artist_violation_cannot_be_masked_by_canvas_qa_pass(self):
        original_draw = core.draw
        def draw_with_incorrect_values(*args, **kwargs):
            fig, colors = original_draw(*args, **kwargs)
            for item in fig._easyviz_elements:
                if item["role"] == "point-group":
                    artist = item["_artist"]
                    coords = np.asarray(artist.get_offsets(), dtype=float).copy()
                    coords[:, 1] += .05
                    artist.set_offsets(coords)
            return fig, colors
        spec = self.spec("distribution", {"group": "g", "value": "v"})
        with patch.object(core, "draw", side_effect=draw_with_incorrect_values):
            manifest, out = self.run_candidates("g,v\nA,1\nA,2\nB,3\nB,4\n", spec, count=1)
        record, _, geometry, directory = next(self.read_candidates(out, manifest))
        self.assertEqual(json.loads((directory / "qa.json").read_text())["status"], "pass")
        self.assertEqual(record["technical_review"]["renderer_status"], "pass")
        self.assertEqual(geometry["source_to_artist"]["status"], "needs_revision")
        self.assertFalse(geometry["source_to_artist"]["numeric_coordinates_preserved"])
        self.assertEqual(record["technical_review"]["status"], "needs_revision")
        self.assertEqual(manifest["status"], "needs_revision")

    def test_extracted_scripts_portably_describe_contract(self):
        portable = self.root / "extracted/easyviz/scripts"
        shutil.copytree(SCRIPT.parent, portable, ignore=shutil.ignore_patterns("__pycache__"))
        result = subprocess.run([sys.executable, str(portable / SCRIPT.name), "--describe-spec"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["track"], "create")
        palettes = portable.parent / "assets/palettes"
        palettes.mkdir(parents=True)
        shutil.copy2(SCRIPT.parent.parent / "assets/palettes/palettes.json", palettes)
        source, spec, out = self.root / "portable.csv", self.root / "portable.json", self.root / "portable-output"
        source.write_text("x,y,g\n1,2,A\n2,3,B\n")
        spec.write_text(json.dumps(self.spec("scatter", {"x": "x", "y": "y", "group": "g"})))
        result = subprocess.run([sys.executable, str(portable / SCRIPT.name), "--data", str(source), "--spec", str(spec), "--out", str(out), "--new-draft", "--count", "1"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "visual_review_pending")
        self.assertTrue((out / "candidate-01/panel.png").exists())


if __name__ == "__main__":
    unittest.main()
