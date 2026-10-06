"""Adopted scientific purpose must affect design without changing evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/create_candidates.py"
loader = importlib.util.spec_from_file_location("easyviz_intent_tests", SCRIPT)
candidates = importlib.util.module_from_spec(loader)
loader.loader.exec_module(candidates)
mechanisms = candidates.mechanisms


class DesignMechanismTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-intent-")
        self.root = Path(self.temp.name)
        self.spec = {"chart": "distribution", "fields": {"group": "condition", "value": "response", "unit": "sample"},
                     "options": {"kind": "box", "y_limits": [0, 9], "point_area_pt2": 9},
                     "layout": {"width_mm": 88, "height_mm": 70, "font": "DejaVu Sans", "font_size_pt": 8, "dpi": 100},
                     "labels": {"x": "Condition", "y": "Response (a.u.)"}, "formats": ["png", "svg", "pdf"]}
        self.body = "sample,condition,response\n001,Vehicle,1\n002,Vehicle,2\n003,Vehicle,3\n004,Low,2\n005,Low,3\n006,Low,4\n007,High,4\n008,High,5\n009,High,7\n"

    def tearDown(self):
        candidates.core.plt.close("all")
        self.temp.cleanup()

    def intent(self, task="compare_distributions", **options):
        return {"schema_version": 1, "question": "Compare the supplied specimen responses across the adopted conditions", "reading_task": task, **options}

    def run_draft(self, spec=None, body=None, name="draft", **kwargs):
        data_path, spec_path, out = self.root / (name + ".csv"), self.root / (name + ".json"), self.root / name
        data_path.write_text(body or self.body)
        spec_path.write_text(json.dumps(spec or self.spec))
        before = data_path.read_bytes(), spec_path.read_bytes()
        result = candidates.create_candidates(data_path, spec_path, out, new_draft=True, count=1, **kwargs)
        self.assertEqual(before, (data_path.read_bytes(), spec_path.read_bytes()))
        return result, out

    def test_same_family_purpose_changes_actual_painted_roles_not_statistics(self):
        rendered = []
        for name, task, layer in (("summary", "compare_distributions", "summary"), ("samples", "inspect_observations", "observations")):
            spec = deepcopy(self.spec)
            spec["create_intent"] = self.intent(task, leading_layer=layer)
            manifest, out = self.run_draft(spec, name=name)
            record = manifest["candidates"][0]
            self.assertEqual(manifest["status"], "visual_review_pending")
            self.assertEqual(manifest["features"]["reading_task_source"], "adopted_create_intent")
            candidate = json.loads((out / record["spec"]).read_text())
            self.assertNotIn("create_intent", candidate)
            geometry = json.loads((out / record["geometry_evidence"]).read_text())
            self.assertEqual(geometry["source_to_artist"]["observation_count"], 9)
            self.assertTrue(geometry["source_to_artist"]["numeric_coordinates_preserved"])
            self.assertEqual(geometry["numeric_limits"]["y"], [0, 9])
            self.assertEqual(record["physical_preflight"]["status"], "capacity_checked")
            for extension in ("png", "svg", "pdf"):
                self.assertTrue((out / record["id"] / ("panel." + extension)).is_file())
            rendered.append((record, candidate, geometry))
        self.assertEqual([item[0]["route_id"] for item in rendered], ["summary-area", "observation-color"])
        self.assertNotEqual(rendered[0][0]["visual_facet_evidence"], rendered[1][0]["visual_facet_evidence"])
        for _, spec, _ in rendered:
            fig, data, _, _ = candidates._draw(self.root / "summary.csv", spec)
            groups = candidates.core.ordered(data, "condition", spec, "group")
            boxes = [entry for entry in fig._easyviz_elements if entry["role"] == "distribution"]
            for box in boxes:
                values = data[data.condition == box["label"]].response.to_numpy(float)
                q1, q3 = np.quantile(values, [.25, .75])
                numeric_vertices = box["_artist"].get_path().vertices[:, 1]
                self.assertAlmostEqual(float(numeric_vertices.min()), q1)
                self.assertAlmostEqual(float(numeric_vertices.max()), q3)
            candidates.core.plt.close(fig)

    def test_purpose_ranking_includes_sources_limits_and_unresolved_conditions(self):
        features = {"chart": "distribution", "kind": "violin", "category_count": 4, "dense_raw_layer": False}
        density = mechanisms.rank_mechanisms(features, self.intent("inspect_density", leading_layer="density"))
        self.assertEqual(density["mechanisms"][0]["id"], "density-contour-hierarchy")
        self.assertTrue(density["mechanisms"][0]["observed"])
        self.assertTrue(density["mechanisms"][0]["boundary"])
        unresolved = mechanisms.rank_mechanisms({"chart": "replicate"}, self.intent("compare_estimates"))
        neutral = next(item for item in unresolved["mechanisms"] if item["id"] == "neutral-single-quantity")
        self.assertEqual(neutral["applicability"], "unresolved")

    def test_selected_mechanism_must_actually_match_the_data(self):
        with self.assertRaisesRegex(ValueError, "not established as applicable"):
            mechanisms.rank_mechanisms({"chart": "scatter", "group_count": 2}, self.intent("assess_association", mechanism_id="distribution-summary-hierarchy"))
        result = mechanisms.rank_mechanisms({"chart": "heatmap", "matrix_rows": 9, "matrix_columns": 3}, self.intent("read_matrix_values", mechanism_id="matrix-shape-first"))
        self.assertEqual(result["mechanisms"][0]["id"], "matrix-shape-first")

    def test_unknown_analysis_keys_and_unhashable_intent_roles_are_rejected(self):
        for value in (self.intent(statistics={"method": "welch"}), self.intent(leading_layer=[]), self.intent(reading_task=[]), {"schema_version": True, "question": "q", "reading_task": "compare_estimates"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                mechanisms.validate_intent(value)

    def test_unsupported_organization_is_not_silently_rendered_as_overlay(self):
        spec = deepcopy(self.spec)
        spec["create_intent"] = self.intent(organization="aligned_facets")
        with self.assertRaisesRegex(ValueError, "custom code"):
            self.run_draft(spec, render=False)
        self.assertFalse((self.root / "draft").exists())

    def test_density_intent_cannot_invent_kde(self):
        spec = deepcopy(self.spec)
        spec["create_intent"] = self.intent("inspect_density")
        with self.assertRaisesRegex(ValueError, "already adopted violin"):
            self.run_draft(spec, render=False)

    def test_conflicting_color_intent_preserves_adopted_colors_without_publishing(self):
        spec = deepcopy(self.spec)
        spec.update(colors={"Vehicle": "#252525", "Low": "#0072B2", "High": "#D55E00"}, create_intent=self.intent(color_role="labels"))
        with self.assertRaisesRegex(ValueError, "conflicts with explicit settings"):
            self.run_draft(spec, render=False)
        self.assertFalse((self.root / "draft").exists())

    def test_sidecar_is_snapshot_bound_and_ambiguous_purposes_rejected(self):
        path = self.root / "intent.json"
        raw = json.dumps(self.intent("inspect_observations"), indent=3).encode()
        path.write_bytes(raw)
        result, out = self.run_draft(intent_path=path, render=False)
        self.assertEqual((out / "source-intent.json").read_bytes(), raw)
        self.assertEqual(result["adopted_create_intent"]["leading_layer"], "observations")
        spec = deepcopy(self.spec)
        spec["create_intent"] = self.intent("compare_distributions")
        with self.assertRaisesRegex(ValueError, "disagree"):
            self.run_draft(spec, name="conflict", intent_path=path, render=False)

    def test_planning_metadata_does_not_break_strict_focused_renderer(self):
        spec = {"chart": "replicate", "fields": {"condition": "condition", "component": "component", "unit": "sample", "value": "response"},
                "options": {"mode": "grouped", "uncertainty": "sample_sd"},
                "layout": deepcopy(self.spec["layout"]), "formats": ["svg", "png"],
                "create_intent": self.intent("compare_estimates", organization="repeated_groups", color_role="series")}
        body = "sample,condition,component,response\n" + "".join(f"{unit},{condition},{component},{2 + ci + si + ui * .2}\n" for ci, condition in enumerate(("Vehicle", "Treated")) for si, component in enumerate(("A", "B")) for ui, unit in enumerate(("01", "02", "03")))
        manifest, out = self.run_draft(spec, body, render=True)
        self.assertEqual(manifest["status"], "visual_review_pending")
        record = manifest["candidates"][0]
        candidate = json.loads((out / record["spec"]).read_text())
        candidates.replicate.prepare(out / "source.csv", candidate)
        self.assertNotIn("create_intent", candidate)
        self.assertTrue(record["replicate_gap_planning"])

    def test_separate_lanes_and_explicit_global_strokes_remain_scientifically_fixed(self):
        spec = deepcopy(self.spec)
        spec["options"].update(kind="violin", violin_inner="box")
        spec["layout"]["line_width_pt"] = 1.1
        spec["create_intent"] = self.intent("inspect_density", leading_layer="density", organization="separate_lanes")
        result, out = self.run_draft(spec, render=False)
        candidate = json.loads((out / result["candidates"][0]["spec"]).read_text())
        self.assertEqual(candidate["layout"]["line_width_pt"], 1.1)
        for role in candidate.get("line_roles", {}).values():
            self.assertNotIn("line_width_pt", role)
        self.assertGreater(candidate["options"]["point_category_offset"], 0)
        self.assertLessEqual(candidate["options"]["point_category_offset"], .4)
        self.assertEqual(candidate["options"]["violin_inner"], "box")

    def test_preflight_separates_capacity_failures_from_visual_advisories(self):
        geometry = {"data_region_mm": [10, 10, 44, 30], "technical_measurement_status": "pass", "issues": [],
                    "raw_summary_categorical_envelope_crossings": 50}
        result = mechanisms.physical_preflight({"chart": "distribution"}, geometry)
        self.assertEqual(result["status"], "capacity_checked")
        self.assertFalse(result["capacity_failures"])
        self.assertTrue(result["design_advisories"])
        geometry.update(technical_measurement_status="needs_revision", issues=["point_layout"])
        self.assertEqual(mechanisms.physical_preflight({"chart": "distribution"}, geometry)["capacity_failures"], ["point_layout"])

    def test_legacy_drafts_keep_family_hints_and_route_order(self):
        result, _ = self.run_draft(render=False)
        self.assertIsNone(result["adopted_create_intent"])
        self.assertEqual(result["features"]["reading_task_source"], "chart_family_hint_only")
        self.assertEqual(result["candidates"][0]["route_id"], "summary-area")


if __name__ == "__main__":
    unittest.main()
