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

    def proportion_fixture(self, font="Arial", dpi=100):
        deltas = [0, .65787, .64164, .05019, -.35801, -.03462, .72981, 1.13898, .80398, .18921, .07989, .68163]
        groups = ["Control", "Low", "Medium", "High"]
        body = "id,g,v\n" + "".join(f"{group}-{i:02d},{group},{2.3 + j * 1.3 + deltas[i]}\n" for j, group in enumerate(groups) for i in range(9 + j))
        spec = self.spec("distribution", {"group": "g", "value": "v", "unit": "id"},
                         order={"group": groups}, options={"kind": "box", "point_area_pt2": 12, "y_limits": [0, 10]},
                         labels={"x": "Condition", "y": "Response (a.u.)"},
                         statistics={"method": "welch", "groups": ["Control", "High"], "annotate": False})
        spec["layout"].update(width_mm=80, height_mm=70, font=font, dpi=dpi)
        return body, spec, groups

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
        self.assertEqual(*widths, "A material color-role alternative does not need width-only variation")
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
        # Color-role alternatives keep both KDE evaluation and categorical
        # geometry unchanged, rather than presenting width tweaks as designs.
        for first, second in zip(*shapes):
            np.testing.assert_array_equal(first, second)
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
            self.assertNotIn("distribution_lane_planning", record)
            self.assertEqual(geometry["font_resolution"], {"requested": "DejaVu Sans", "actual": "DejaVu Sans", "substituted": False})
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

    def test_distribution_routes_change_painted_roles_without_changing_geometry_or_statistics(self):
        body = "g,v\nA,1\nA,2\nA,3\nB,2\nB,4\nB,6\n"
        spec = self.spec("distribution", {"group": "g", "value": "v"},
                         options={"point_area_pt2": 16, "y_limits": [0, 8]}, order={"group": ["B", "A"]},
                         statistics={"method": "welch", "groups": ["B", "A"], "annotate": False})
        manifest, out = self.run_candidates(body, spec, count=3)
        self.assertEqual(len(manifest["candidates"]), 3)
        painted, coordinates, bodies, statistics, images = [], [], [], [], []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(result["statistics"], spec["statistics"])
            self.assertEqual(result["order"], spec["order"])
            self.assertEqual(geometry["source_to_artist"]["observation_count"], 6)
            fig, _, _, _ = candidates._draw(out / "source.csv", result)
            raw = [entry["_artist"] for entry in fig._easyviz_elements if entry["role"] == "point-group"]
            summaries = [entry["_artist"] for entry in fig._easyviz_elements if entry["role"] == "distribution"]
            painted.append({"raw": [core.mcolors.to_hex(point.get_facecolors()[0]) for point in raw],
                            "faces": [patch.get_facecolor() for patch in summaries]})
            coordinates.append([np.asarray(point.get_offsets()).copy() for point in raw])
            bodies.append([patch.get_path().vertices.copy() for patch in summaries])
            self.assertTrue(all(np.array_equal(point.get_sizes(), [16]) for point in raw))
            self.assertEqual(candidates._visual_facets(fig), record["visual_facet_evidence"])
            self.assertEqual(geometry["visual_facets"], record["visual_facet_evidence"])
            core.plt.close(fig)
            statistics.append(json.loads((directory / "stats.json").read_text()))
            images.append((directory / "panel.png").read_bytes())
        self.assertTrue(all(face[3] > 0 for face in painted[0]["faces"]))
        self.assertEqual(len(set(painted[0]["raw"])), 1, "Summary-area treatment keeps raw marks uniform")
        self.assertTrue(all(face[3] == 0 for face in painted[1]["faces"]))
        self.assertEqual(len(set(painted[1]["raw"])), 2, "Raw observations really carry category color")
        self.assertTrue(all(face[3] == 0 for face in painted[2]["faces"]))
        self.assertEqual(len(set(painted[2]["raw"])), 1, "Positions/labels can decode neutral marks")
        for alternative in (1, 2):
            for old, new in zip(coordinates[0], coordinates[alternative]): np.testing.assert_array_equal(old, new)
            for old, new in zip(bodies[0], bodies[alternative]): np.testing.assert_array_equal(old, new)
            self.assertEqual(statistics[0], statistics[alternative])
            self.assertTrue(manifest["candidates"][alternative]["changed_facets_vs_candidate_01"])
        self.assertEqual(len(set(images)), 3, "Actual exports differ beyond spec-only labels")

    def test_moderate_near_equal_observations_get_physical_lanes_without_scientific_changes(self):
        # Distinct values can collide after transformation although count/tie
        # heuristics call them sparse. These are independent synthetic values.
        clusters = [0, .03, .09, .28, .72, .91, 1.01, 1.04, 1.12, 1.39, 1.73, 2.18]
        for kind, counts in (("box", [9, 10, 11, 12]), ("violin", [14, 17, 20])):
            with self.subTest(kind=kind):
                values = clusters if kind == "box" else [0, .02, .27, .5, .54, .8, 1.03, 1.05, 1.3, 1.54, 1.56, 1.8, 2.03, 2.05, 2.3, 2.54, 2.56, 2.8, 3.03, 3.05]
                body = "id,g,v\n" + "".join(f"{group}-{i:02d},G{group},{1.4 + group * .8 + values[i]}\n" for group, count in enumerate(counts) for i in range(count))
                options = {"kind": kind, "point_area_pt2": 12 if kind == "box" else 10, "y_limits": [0, 9]}
                if kind == "violin": options["violin_inner"] = "box"
                spec = self.spec("distribution", {"group": "g", "value": "v", "unit": "id"}, options=options,
                                 order={"group": [f"G{i}" for i in reversed(range(len(counts)))]})
                spec["layout"].update(width_mm=80, height_mm=70)
                manifest, out = self.run_candidates(body, spec, name="moderate-" + kind, count=3)
                self.assertEqual(manifest["status"], "visual_review_pending")
                self.assertFalse(manifest["features"]["dense_raw_layer"])
                self.assertEqual(manifest["features"]["maximum_tie_count"], 1)
                for record, result, geometry, directory in self.read_candidates(out, manifest):
                    self.assertEqual(record["technical_review"]["status"], "pass")
                    self.assertEqual(record["distribution_lane_planning"]["status"], "pass")
                    self.assertEqual(geometry["canvas_mm"], [80., 70.])
                    self.assertEqual(geometry["typography"]["tick"], 8)
                    self.assertEqual(geometry["point_layout"]["spacing_violation_pairs"], 0)
                    self.assertEqual(geometry["point_layout"]["categorical_boundary_rows"], [])
                    self.assertEqual(geometry["raw_summary_categorical_envelope_crossings"], 0)
                    self.assertEqual(geometry["source_to_artist"]["observation_count"], sum(counts))
                    self.assertEqual(result["order"], spec["order"])
                    for key, value in options.items(): self.assertEqual(result["options"][key], value)
                    self.assertEqual(json.loads((directory / "qa.json").read_text())["status"], "pass")
                    self.assertTrue((directory / "panel.png").exists())
                    fig, plotted, _, _ = candidates._draw(out / "source.csv", result)
                    display = []
                    for item in fig._easyviz_elements:
                        if item["role"] != "point-group": continue
                        artist = item["_artist"]
                        coordinates = np.asarray(artist.get_offsets(), dtype=float)
                        selected = plotted[plotted.g == item["label"]]
                        np.testing.assert_array_equal(coordinates[:, 1], selected.v.to_numpy())
                        np.testing.assert_array_equal(artist.get_sizes(), [options["point_area_pt2"]])
                        display.extend(fig.axes[0].transData.transform(coordinates) * 72 / fig.dpi)
                    distances = np.linalg.norm(np.asarray(display)[:, None] - np.asarray(display)[None, :], axis=2)
                    distances[np.diag_indices_from(distances)] = np.inf
                    self.assertGreaterEqual(float(distances.min()), np.sqrt(options["point_area_pt2"]) + result["options"]["point_gap_pt"] - 1e-7)
                    self.assertEqual(fig.axes[0].get_ylim(), (0., 9.))
                    core.plt.close(fig)

    def test_explicit_lane_limits_and_infeasible_summary_geometry_stay_invalid_and_retryable(self):
        body = "g,v\n" + "".join(f"{group},{base + delta}\n" for group, base in (("A", 2), ("B", 4)) for delta in (0, .005, .01, .1, .105, .11, .2, .205, .21))
        spec = self.spec("distribution", {"group": "g", "value": "v"},
                         options={"kind": "box", "point_layout": "beeswarm", "box_width": .3,
                                  "point_category_offset": .35, "point_max_offset_mm": .03,
                                  "point_gap_pt": .3, "point_area_pt2": 16, "y_limits": [0, 8]})
        spec["layout"].update(width_mm=65, height_mm=60, auto_fit=False,
                              margins={"left": .25, "right": .85, "bottom": .2, "top": .9})
        for render in (False, True):
            with self.subTest(render=render):
                manifest, out = self.run_candidates(body, spec, name="locked-lane-" + str(render), count=1, render=render)
                self.assertEqual(manifest["status"], "needs_revision")
                record, result, geometry, directory = next(self.read_candidates(out, manifest))
                self.assertIn(record["technical_review"]["status"], ("failed", "needs_revision"))
                self.assertEqual(geometry["point_layout"]["status"], "needs_revision")
                self.assertGreater(geometry["point_layout"]["spacing_violation_pairs"], 0)
                self.assertEqual(geometry["source_to_artist"]["status"], "pass")
                self.assertEqual(geometry["source_to_artist"]["observation_count"], 18)
                for key, value in spec["options"].items(): self.assertEqual(result["options"][key], value)
                self.assertEqual(result["layout"]["margins"], spec["layout"]["margins"])
                self.assertEqual(geometry["canvas_mm"], [65., 60.])
                self.assertEqual(record["visual_review"]["status"], "pending")
                if render:
                    self.assertEqual(json.loads((directory / "qa.json").read_text())["status"], "needs_revision")
                    self.assertEqual(len(pd.read_csv(directory / "plotting-data.csv")), 18)
                else:
                    self.assertFalse((directory / "panel.png").exists())

    def test_summary_proportion_floor_and_positive_gap_trial_preserve_actual_box_quantiles(self):
        # Regression for the reviewed four-category 80 mm manuscript panel.
        # The former solver passed spacing by making boxes thinner than dots.
        body, spec, groups = self.proportion_fixture()
        manifest, out = self.run_candidates(body, spec, name="box-proportion", count=3)
        self.assertEqual(manifest["status"], "visual_review_pending")
        self.assertEqual(len(manifest["candidates"]), 3)
        raw_coordinates, summaries, stats = [], [], []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            plan = record["distribution_lane_planning"]
            self.assertTrue(plan["summary_floor_met"])
            self.assertEqual(plan["actual_gap_pt"], .2)
            self.assertIn(".3 pt", plan["gap_reduction_reason"])
            self.assertEqual(result["options"]["point_gap_pt"], .2)
            self.assertEqual(result["statistics"], spec["statistics"])
            self.assertEqual(geometry["canvas_mm"], [80., 70.])
            self.assertEqual(result["layout"]["font"], "Arial")
            self.assertEqual(geometry["typography"]["tick"], 8)
            self.assertEqual(geometry["point_layout"]["spacing_violation_pairs"], 0)
            self.assertEqual(geometry["raw_summary_categorical_envelope_crossings"], 0)
            fig, data, _, _ = candidates._draw(out / "source.csv", result)
            coordinates, quantiles = [], []
            for index, group in enumerate(groups):
                values = data.loc[data.g == group, "v"].to_numpy()
                point = next(item["_artist"] for item in fig._easyviz_elements if item["role"] == "point-group" and item["label"] == group)
                patch = next(item["_artist"] for item in fig._easyviz_elements if item["role"] == "distribution" and item["label"] == group)
                vertices = patch.get_path().vertices
                physical_width = np.ptp(patch.get_transform().transform(vertices)[:, 0]) * 72 / fig.dpi
                outer_diameter = np.sqrt(point.get_sizes()[0]) + point.get_linewidths()[0]
                self.assertGreaterEqual(physical_width + 1e-8, outer_diameter)
                np.testing.assert_allclose([vertices[:, 1].min(), vertices[:, 1].max()], np.quantile(values, [.25, .75]))
                medians = [line for line in fig.axes[0].lines if np.isclose(np.ptp(line.get_xdata()), result["options"]["box_width"]) and np.isclose(np.mean(line.get_xdata()), index) and np.isclose(np.ptp(line.get_ydata()), 0)]
                self.assertEqual(len(medians), 1)
                self.assertAlmostEqual(float(medians[0].get_ydata()[0]), float(np.median(values)))
                np.testing.assert_array_equal(np.asarray(point.get_offsets())[:, 1], values)
                np.testing.assert_array_equal(point.get_sizes(), [12])
                coordinates.append(np.asarray(point.get_offsets()).copy())
                quantiles.append(vertices.copy())
            self.assertEqual(fig.axes[0].get_ylim(), (0., 10.))
            raw_coordinates.append(coordinates); summaries.append(quantiles)
            core.plt.close(fig)
            stats.append(json.loads((directory / "stats.json").read_text()))
        for alternative in (1, 2):
            for first, other in zip(raw_coordinates[0], raw_coordinates[alternative]): np.testing.assert_array_equal(first, other)
            for first, other in zip(summaries[0], summaries[alternative]): np.testing.assert_array_equal(first, other)
            self.assertEqual(stats[0], stats[alternative])
        # An explicitly adopted .3 pt gap cannot be silently reduced to fit.
        locked = deepcopy(spec)
        locked["options"].update(point_layout="beeswarm", point_gap_pt=.3)
        rejected, rejected_out = self.run_candidates(body, locked, name="explicit-gap-floor", count=1)
        self.assertEqual(rejected["status"], "needs_revision")
        record, result, geometry, directory = next(self.read_candidates(rejected_out, rejected))
        self.assertEqual(result["options"]["point_gap_pt"], .3)
        self.assertIsNone(record["distribution_lane_planning"]["gap_reduction_reason"])
        self.assertTrue(record["distribution_lane_planning"]["summary_floor_met"])
        self.assertEqual(geometry["point_layout"]["status"], "needs_revision")
        self.assertEqual(json.loads((directory / "qa.json").read_text())["status"], "needs_revision")

    def test_measured_margin_handles_explicit_and_fallback_fonts_without_changing_marks_or_numeric_region(self):
        real_findfont = core.font_manager.findfont
        fallback_path = real_findfont(core.font_manager.FontProperties(family="DejaVu Sans"))
        def unavailable_arial(properties, *args, **kwargs):
            if hasattr(properties, "get_family") and "Arial" in properties.get_family():
                return fallback_path
            return real_findfont(properties, *args, **kwargs)
        borrowed = []
        for name, requested, dpi, missing in (("dejavu-100", "DejaVu Sans", 100, False),
                                              ("dejavu-160", "DejaVu Sans", 160, False),
                                              ("fallback-100", "Arial", 100, True)):
            with self.subTest(font=requested, dpi=dpi, arial_missing=missing):
                body, spec, groups = self.proportion_fixture(requested, dpi)
                with patch.object(core.font_manager, "findfont", side_effect=unavailable_arial if missing else real_findfont):
                    manifest, out = self.run_candidates(body, spec, name=name, count=3 if name == "dejavu-100" else 1)
                    self.assertEqual(manifest["status"], "visual_review_pending")
                    for record, result, geometry, directory in self.read_candidates(out, manifest):
                        self.assertEqual(record["technical_review"]["status"], "pass")
                        resolution = {"requested": requested, "actual": "DejaVu Sans", "substituted": missing}
                        self.assertEqual(record["font_resolution"], resolution)
                        self.assertEqual(geometry["font_resolution"], resolution)
                        plan = record["distribution_lane_planning"]
                        borrowing = plan["available_region_margin_borrowing"]
                        self.assertTrue(borrowing["applied"])
                        self.assertGreater(borrowing["required_extra_mm"], 0)
                        self.assertLessEqual(borrowing["required_extra_mm"], borrowing["available_extra_mm"])
                        baseline, region = manifest["baseline_geometry"]["data_region_mm"], geometry["data_region_mm"]
                        np.testing.assert_allclose([region[i] for i in (0, 1, 3)], [baseline[i] for i in (0, 1, 3)], atol=1e-8)
                        self.assertAlmostEqual(region[2] - baseline[2], borrowing["required_extra_mm"])
                        self.assertGreaterEqual(80 - region[0] - region[2], borrowing["minimum_canvas_padding_mm"] - 1e-8)
                        self.assertEqual(result["layout"]["font"], requested)
                        self.assertEqual(result["layout"]["font_size_pt"], 8)
                        self.assertEqual(result["statistics"], spec["statistics"])
                        self.assertEqual(result["order"], spec["order"])
                        self.assertEqual(geometry["canvas_mm"], [80., 70.])
                        self.assertEqual(geometry["numeric_limits"]["y"], [0., 10.])
                        self.assertEqual(geometry["source_to_artist"]["observation_count"], 42)
                        self.assertEqual(geometry["issues"], [])
                        self.assertEqual(geometry["raw_summary_categorical_envelope_crossings"], 0)
                        self.assertEqual(json.loads((directory / "qa.json").read_text())["status"], "pass")
                        settings = json.loads((directory / "settings.json").read_text())
                        self.assertEqual(settings["layout"]["actual_font"], "DejaVu Sans")
                        self.assertEqual(settings["layout"]["font_substituted"], missing)
                        fig, data, _, _ = candidates._draw(out / "source.csv", result)
                        display = []
                        for group in groups:
                            point = next(item["_artist"] for item in fig._easyviz_elements if item["role"] == "point-group" and item["label"] == group)
                            coordinates = np.asarray(point.get_offsets(), dtype=float)
                            np.testing.assert_array_equal(coordinates[:, 1], data.loc[data.g == group, "v"].to_numpy())
                            np.testing.assert_array_equal(point.get_sizes(), [12])
                            patch_artist = next(item["_artist"] for item in fig._easyviz_elements if item["role"] == "distribution" and item["label"] == group)
                            vertices = patch_artist.get_path().vertices
                            body_width = np.ptp(patch_artist.get_transform().transform(vertices)[:, 0]) * 72 / fig.dpi
                            outer_diameter = np.sqrt(point.get_sizes()[0]) + point.get_linewidths()[0]
                            self.assertGreaterEqual(body_width + 1e-8, outer_diameter)
                            np.testing.assert_allclose([vertices[:, 1].min(), vertices[:, 1].max()], np.quantile(data.loc[data.g == group, "v"], [.25, .75]))
                            display.extend(fig.axes[0].transData.transform(coordinates) * 72 / fig.dpi)
                        distances = np.linalg.norm(np.asarray(display)[:, None] - np.asarray(display)[None, :], axis=2)
                        distances[np.diag_indices_from(distances)] = np.inf
                        self.assertEqual(result["options"]["point_gap_pt"], .2)
                        self.assertGreaterEqual(float(distances.min()), outer_diameter + .2 - 1e-7)
                        for label in fig.axes[0].get_xticklabels() + fig.axes[0].get_yticklabels():
                            self.assertEqual(label.get_fontsize(), 8)
                        core.plt.close(fig)
                    borrowed.append(manifest["candidates"][0]["distribution_lane_planning"]["available_region_margin_borrowing"]["required_extra_mm"])
        # Real glyph metrics depend on resolution: correction is measured,
        # while the simulated missing Arial resolves to the same real font.
        self.assertGreater(abs(borrowed[0] - borrowed[1]), .01)
        self.assertAlmostEqual(borrowed[0], borrowed[2])

    def test_horizontal_margin_borrowing_keeps_numeric_transform_and_reversed_category_order(self):
        body, spec, groups = self.proportion_fixture("DejaVu Sans")
        spec["options"].update(orientation="horizontal", x_limits=spec["options"].pop("y_limits"))
        spec["labels"] = {"x": "Response (a.u.)", "y": "Condition"}
        spec["layout"].update(width_mm=70, height_mm=80)
        manifest, out = self.run_candidates(body, spec, name="horizontal-margin", count=1)
        self.assertEqual(manifest["status"], "visual_review_pending")
        record, result, geometry, directory = next(self.read_candidates(out, manifest))
        borrowing = record["distribution_lane_planning"]["available_region_margin_borrowing"]
        self.assertTrue(borrowing["applied"])
        self.assertEqual(borrowing["edge"], "bottom")
        self.assertGreater(borrowing["required_extra_mm"], 0)
        self.assertLessEqual(borrowing["required_extra_mm"], borrowing["available_extra_mm"])
        baseline, region = manifest["baseline_geometry"]["data_region_mm"], geometry["data_region_mm"]
        np.testing.assert_allclose([region[0], region[2]], [baseline[0], baseline[2]], atol=1e-8)
        self.assertAlmostEqual(region[1] + region[3], baseline[1] + baseline[3])
        self.assertAlmostEqual(baseline[1] - region[1], borrowing["required_extra_mm"])
        self.assertEqual(geometry["category_tick_labels"]["y"], groups)
        self.assertEqual(geometry["numeric_limits"]["x"], [0., 10.])
        self.assertEqual(geometry["issues"], [])
        self.assertEqual(geometry["raw_summary_categorical_envelope_crossings"], 0)
        self.assertEqual(json.loads((directory / "qa.json").read_text())["status"], "pass")
        self.assertEqual(result["statistics"], spec["statistics"])
        self.assertEqual(result["order"], spec["order"])
        fig, data, _, _ = candidates._draw(out / "source.csv", result)
        self.assertGreater(fig.axes[0].get_ylim()[0], fig.axes[0].get_ylim()[1])
        for group in groups:
            point = next(item["_artist"] for item in fig._easyviz_elements if item["role"] == "point-group" and item["label"] == group)
            np.testing.assert_array_equal(np.asarray(point.get_offsets())[:, 0], data.loc[data.g == group, "v"].to_numpy())
            np.testing.assert_array_equal(point.get_sizes(), [12])
            patch_artist = next(item["_artist"] for item in fig._easyviz_elements if item["role"] == "distribution" and item["label"] == group)
            vertices = patch_artist.get_path().vertices
            np.testing.assert_allclose([vertices[:, 0].min(), vertices[:, 0].max()], np.quantile(data.loc[data.g == group, "v"], [.25, .75]))
            physical_width = np.ptp(patch_artist.get_transform().transform(vertices)[:, 1]) * 72 / fig.dpi
            self.assertGreaterEqual(physical_width + 1e-8, np.sqrt(point.get_sizes()[0]) + point.get_linewidths()[0])
        core.plt.close(fig)

    def test_explicit_margin_lock_retains_cross_font_spacing_failure_and_source_values(self):
        body, spec, _ = self.proportion_fixture("DejaVu Sans")
        baseline, _ = self.run_candidates(body, spec, name="before-margin-lock", count=1, render=False)
        x, y, width, height = baseline["baseline_geometry"]["data_region_mm"]
        margins = {"left": x / 80, "right": (x + width) / 80, "bottom": y / 70, "top": (y + height) / 70}
        for manual_fit in (None, False):
            with self.subTest(auto_fit=manual_fit):
                locked = deepcopy(spec)
                locked["layout"]["margins"] = margins
                if manual_fit is not None:
                    locked["layout"]["auto_fit"] = manual_fit
                manifest, out = self.run_candidates(body, locked, name="locked-margin-" + str(manual_fit), count=1)
                self.assertEqual(manifest["status"], "needs_revision")
                record, result, geometry, directory = next(self.read_candidates(out, manifest))
                self.assertEqual(result["layout"]["margins"], margins)
                self.assertFalse(result["layout"].get("auto_fit", False))
                self.assertIsNone(record["distribution_lane_planning"]["available_region_margin_borrowing"])
                self.assertTrue(record["distribution_lane_planning"]["summary_floor_met"])
                self.assertEqual(geometry["font_resolution"], {"requested": "DejaVu Sans", "actual": "DejaVu Sans", "substituted": False})
                self.assertEqual(geometry["source_to_artist"]["status"], "pass")
                self.assertEqual(geometry["source_to_artist"]["observation_count"], 42)
                self.assertGreater(geometry["point_layout"]["spacing_violation_pairs"], 0)
                self.assertEqual(json.loads((directory / "qa.json").read_text())["status"], "needs_revision")
                fig, data, _, _ = candidates._draw(out / "source.csv", result)
                self.assertEqual(fig.axes[0].get_ylim(), (0., 10.))
                for item in fig._easyviz_elements:
                    if item["role"] == "point-group":
                        np.testing.assert_array_equal(np.asarray(item["_artist"].get_offsets())[:, 1], data.loc[data.g == item["label"], "v"].to_numpy())
                        np.testing.assert_array_equal(item["_artist"].get_sizes(), [12])
                core.plt.close(fig)

    def test_unsupported_explicit_category_limits_are_rejected_instead_of_removed_or_rewritten(self):
        for orientation, axis in (("vertical", "x"), ("horizontal", "y")):
            with self.subTest(orientation=orientation):
                spec = self.spec("distribution", {"group": "g", "value": "v"}, options={"orientation": orientation, axis + "_limits": [-.45, 1.45]})
                source, path, out = self.root / f"cat-{axis}.csv", self.root / f"cat-{axis}.json", self.root / f"cat-{axis}"
                source.write_text("g,v\nA,1\nA,2\nB,2\nB,3\n")
                path.write_text(json.dumps(spec))
                before = (source.read_bytes(), path.read_bytes())
                with self.assertRaisesRegex(ValueError, "only on numeric"):
                    candidates.create_candidates(source, path, out, new_draft=True)
                self.assertEqual((source.read_bytes(), path.read_bytes()), before)
                self.assertFalse(out.exists())

    def test_replicate_summary_has_actual_filled_and_open_bars_with_identical_means_sd_and_points(self):
        body = "c,u,v\nControl,01,1\nControl,02,2\nControl,03,3\nDrug,01,3\nDrug,02,4\nDrug,03,5\n"
        spec = self.spec("replicate", {"condition": "c", "unit": "u", "value": "v"},
                         options={"mode": "summary", "uncertainty": "sample_sd", "marker_area_pt2": 12, "y_limits": [0, 7]})
        manifest, out = self.run_candidates(body, spec, count=3)
        self.assertEqual(len(manifest["candidates"]), 2, "Count is not padded with different bar widths")
        observed, summaries, stats = [], [], []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(geometry["source_to_artist"]["status"], "pass")
            fig, _, _, _ = candidates._draw(out / "source.csv", result)
            observed.append([(patch.get_x(), patch.get_y(), patch.get_width(), patch.get_height(), patch.get_facecolor()[3]) for patch in fig.axes[0].patches])
            self.assertEqual(len(fig.axes[0].collections[0].get_offsets()), 1)
            core.plt.close(fig)
            summaries.append(json.loads((directory / "summary-data.json").read_text()))
            stats.append(json.loads((directory / "stats.json").read_text()))
        self.assertTrue(all(row[-1] == 1 for row in observed[0]))
        self.assertTrue(all(row[-1] == 0 for row in observed[1]))
        self.assertEqual([row[:-1] for row in observed[0]], [row[:-1] for row in observed[1]])
        self.assertEqual(*summaries)
        self.assertEqual(*stats)

    def test_heatmap_routes_have_actual_ramps_and_guide_organization_under_one_numeric_contract(self):
        body = "r,c,v\n" + "".join(f"R{i},C{j},{i+j}\n" for i in range(8) for j in range(2))
        spec = self.spec("heatmap", {"row": "r", "column": "c", "value": "v"},
                         options={"color_limits": [-1, 10], "color_center": 1.5},
                         order={"x": ["C1", "C0"], "y": [f"R{i}" for i in reversed(range(8))]})
        manifest, out = self.run_candidates(body, spec, count=3)
        self.assertEqual(len(manifest["candidates"]), 3)
        norms, arrays, colors, guides = [], [], [], []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            self.assertEqual(record["technical_review"]["status"], "pass")
            self.assertEqual(result["options"]["color_limits"], [-1, 10])
            self.assertEqual(result["options"]["color_center"], 1.5)
            fig, _, _, _ = candidates._draw(out / "source.csv", result)
            image = fig.axes[0].images[0]
            norms.append([image.norm.vmin, image.norm.vcenter, image.norm.vmax])
            arrays.append(np.asarray(image.get_array()).copy())
            colors.append(image.cmap(np.linspace(0, 1, 5)))
            chosen = fig._easyviz_legend_layout.entries[0]["chosen_settings"]
            guides.append((chosen["position"], chosen["orientation"]))
            self.assertEqual(candidates._visual_facets(fig), geometry["visual_facets"])
            self.assertEqual(geometry["guide_geometry"]["status"], "pass")
            core.plt.close(fig)
        self.assertEqual(norms, [[-1., 1.5, 10.]] * 3)
        np.testing.assert_array_equal(arrays[0], arrays[1]); np.testing.assert_array_equal(arrays[0], arrays[2])
        self.assertFalse(np.array_equal(colors[0], colors[1]))
        np.testing.assert_array_equal(colors[0], colors[2])
        self.assertEqual(guides[0], ("right", "vertical"))
        self.assertEqual(guides[2], ("bottom", "horizontal"))

    def test_scatter_palette_alternatives_are_real_and_explicit_decoding_prevents_count_inflation(self):
        body = "x,y,g\n1,2,A\n2,3,A\n3,4,B\n4,5,B\n"
        spec = self.spec("scatter", {"x": "x", "y": "y", "group": "g"},
                         options={"point_area_pt2": 19, "point_style": "filled", "x_limits": [0, 5], "y_limits": [0, 6]})
        manifest, out = self.run_candidates(body, spec, count=3)
        self.assertEqual(len(manifest["candidates"]), 2, "Two decoding choices survive an explicit filled-glyph lock")
        paints, coordinates = [], []
        for record, result, geometry, directory in self.read_candidates(out, manifest):
            fig, _, _, _ = candidates._draw(out / "source.csv", result)
            points = [entry["_artist"] for entry in fig._easyviz_elements if entry["role"] == "point-group"]
            paints.append([point.get_facecolors().copy() for point in points])
            coordinates.append([point.get_offsets().copy() for point in points])
            self.assertTrue(all(np.array_equal(point.get_sizes(), [19]) for point in points))
            self.assertEqual(geometry["numeric_limits"], {"x": [0., 5.], "y": [0., 6.]})
            core.plt.close(fig)
        self.assertTrue(any(not np.array_equal(a, b) for a, b in zip(*paints)))
        for a, b in zip(*coordinates): np.testing.assert_array_equal(a, b)
        adopted = deepcopy(spec)
        adopted.update(colors={"A": "#004488", "B": "#AA3377"}, line_roles={"reference": {"line_width_pt": 1.2, "color": "#667788"}})
        adopted["layout"].update(auto_fit=False, margins={"left": .2, "right": .8, "bottom": .2, "top": .9})
        locked, locked_out = self.run_candidates(body, adopted, name="locked-decoding", count=3)
        self.assertEqual(len(locked["candidates"]), 1)
        _, result, _, _ = next(self.read_candidates(locked_out, locked))
        self.assertEqual(result["colors"], adopted["colors"])
        for key, value in adopted["line_roles"]["reference"].items():
            self.assertEqual(result["line_roles"]["reference"][key], value)
        self.assertEqual(result["layout"]["margins"], adopted["layout"]["margins"])

    def test_default_crisp_seed_keeps_explicit_values_but_can_compare_unassigned_color_roles(self):
        draft_loader = importlib.util.spec_from_file_location("easyviz_choice_draft_tests", SCRIPT.with_name("draft_spec.py"))
        draft_spec = importlib.util.module_from_spec(draft_loader)
        draft_loader.loader.exec_module(draft_spec)
        data, path = self.root / "draft.csv", self.root / "draft.json"
        data.write_text("g,v\nA,1\nA,2\nA,3\nB,2\nB,3\nB,4\n")
        adopted = draft_spec.draft(data, "distribution", ["group=g", "value=v"], path,
                                   panel_size_mm=[120, 90], font="DejaVu Sans")
        manifest = candidates.create_candidates(data, path, self.root / "crisp-choice", new_draft=True, count=3)
        self.assertEqual(len(manifest["candidates"]), 2)
        paints = []
        for record, result, geometry, directory in self.read_candidates(self.root / "crisp-choice", manifest):
            for key, value in adopted["options"].items(): self.assertEqual(result["options"][key], value)
            for role, properties in adopted["line_roles"].items():
                for key, value in properties.items(): self.assertEqual(result["line_roles"][role][key], value)
            paints.append(geometry["visual_facets"]["painted_mark_roles"])
        self.assertNotEqual(*paints)
        self.assertEqual(manifest["features"]["reading_task_source"], "chart_family_hint_only")
        self.assertIn("not the complete", manifest["design_space"]["scope"])

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
