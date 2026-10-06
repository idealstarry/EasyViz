"""Adopted statistical results stay bound to populations and real exports."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from pypdf import PdfReader


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def module(name, filename):
    loader = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


analysis = module("easyviz_analysis_binding_test_analyze", "analyze.py")
renderer = module("easyviz_analysis_binding_test_render", "render.py")


class AnalysisBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-analysis-binding-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.plan = {"schema_version": 1, "question": "Compare the prespecified independent specimen endpoint",
                     "design": {"unit": "id", "unit_definition": "one independently sampled specimen", "structure": "independent", "confirmed": True},
                     "missing_policy": "error", "comparisons": [{"name": "primary", "method": "welch", "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]}]}
        self.spec = {"chart": "distribution", "fields": {"group": "group", "value": "value", "unit": "id"},
                     "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
                     "formats": ["pdf", "svg", "png"], "labels": {"x": "Condition", "y": "Response (a.u.)"},
                     "options": {"kind": "box"}, "seed": 4}

    def tearDown(self):
        renderer.plt.close("all")
        self.temp.cleanup()

    def adopt(self, text, plan=None, *, population="all", pvalue="raw"):
        self.source.write_text(text)
        report = analysis.analyze(self.source, deepcopy(plan or self.plan), self.root / "analysis")
        results = self.root / "analysis/results.json"
        self.spec["statistics"] = {"analysis": {"schema_version": 1, "results_file": str(results),
                                               "results_sha256": hashlib.sha256(results.read_bytes()).hexdigest(),
                                               "comparison": report["comparisons"][0]["name"], "pvalue": pvalue, "population": population}, "annotate": True}
        return report

    def render(self, name="plot", spec=None):
        out = self.root / name
        qa = renderer.render(self.source, spec or self.spec, out)
        return out, qa, json.loads((out / "stats.json").read_text())

    def test_adjusted_p_is_in_svg_pdf_and_recolor_preserves_exact_result(self):
        plan = deepcopy(self.plan)
        secondary = deepcopy(plan["comparisons"][0])
        secondary.update(name="secondary", fields={"group": "group", "value": "value2"})
        plan["comparisons"].append(secondary)
        plan["multiplicity"] = {"family": "Two endpoints", "adjustment": "holm", "comparisons": ["primary", "secondary"]}
        report = self.adopt("id,group,value,value2\na1,A,1,1\na2,A,2,2\na3,A,3,4\nb1,B,4,1\nb2,B,5,2\nb3,B,6,3\n", plan, pvalue="adjusted")
        expected = report["comparisons"][0]
        self.spec["colors"] = {"A": "#2687bd", "B": "#ed8b43"}
        with patch("scipy.stats.ttest_ind", side_effect=AssertionError("Plotting must not recompute adopted inference")):
            out, qa, result = self.render()
            revised = deepcopy(self.spec)
            revised["colors"] = {"A": "#22b6aa", "B": "#ee7198"}
            changed_out, _, changed = self.render("recolor", revised)
        self.assertEqual(qa["status"], "pass")
        self.assertEqual(result, changed)
        self.assertEqual(result["effect"], expected["effect"])
        self.assertEqual(result["interval"], expected["interval"])
        self.assertEqual(result["pvalue"], expected["pvalue"])
        self.assertEqual(result["annotation_pvalue"], expected["adjusted_pvalue"])
        self.assertNotEqual(expected["pvalue"], expected["adjusted_pvalue"])
        svg_text = " ".join(node.text or "" for node in ET.parse(out / "panel.svg").findall(".//{http://www.w3.org/2000/svg}text"))
        self.assertIn(result["annotation_text"], svg_text)
        self.assertIn("adjusted P", PdfReader(out / "panel.pdf").pages[0].extract_text())
        self.assertNotEqual((out / "panel.png").read_bytes(), (changed_out / "panel.png").read_bytes())
        self.assertEqual((out / "adopted-analysis/results.json").read_bytes(), (self.root / "analysis/results.json").read_bytes())
        caption = (out / "analysis-caption.md").read_text()
        self.assertIn("holm, family `Two endpoints`, 2 hypotheses", caption)
        self.assertIn("A minus B", caption)
        self.assertIn("pointwise", caption)
        self.assertFalse(result["adoption"]["recomputed"])
        settings = json.loads((out / "settings.json").read_text())
        self.assertEqual(settings["source_bindings"]["helper:analysis_result.py"]["sha256"],
                         hashlib.sha256((SCRIPTS / "analysis_result.py").read_bytes()).hexdigest())
        annotations = [item for item in json.loads((out / "elements.json").read_text())["elements"] if item["role"] == "statistical-annotation"]
        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0]["editable"], {"fontsize": "/typography/annotation"})

    def test_explicit_included_population_keeps_exclusion_trace_and_literal_source_ids(self):
        plan = deepcopy(self.plan)
        plan["design"].update(structure="paired", unit_definition="one independent paired subject")
        plan["missing_policy"] = "complete_case"
        plan["comparisons"][0]["method"] = "paired_t"
        original = "id,group,value\n002,B,4\n001,A,1\n003,B,5\n003,A,4\n001,B,2\n002,A,2\n004,A,30\n004,B,NA\n005,A,50\n"
        report = self.adopt(original, plan, population="included")
        out, qa, result = self.render()
        self.assertEqual(qa["input_rows"], 9)
        self.assertEqual(qa["plotted_input_rows"], 6)
        self.assertEqual(result["pair_unit_ids"], ["002", "001", "003"])
        self.assertEqual(result["effect"], report["comparisons"][0]["effect"])
        self.assertEqual(result["adoption"]["plotted_source_records"], [2, 3, 4, 5, 6, 7])
        self.assertEqual((out / "source-data.csv").read_text(), original)
        plotted = renderer.read_source_csv(out / "plotting-data.csv")
        self.assertNotIn("004", plotted["id"].tolist())
        self.assertEqual(plotted["id"].tolist(), ["002", "001", "003", "003", "001", "002"])
        self.assertIn("excludes 3 selected rows", (out / "analysis-caption.md").read_text())
        metadata = json.loads((out / "settings.json").read_text())
        self.assertEqual(metadata["source_snapshot"]["row_count"], 9)
        self.assertEqual(metadata["adopted_analysis"]["population"], "included")

    def test_all_preserves_unmatched_visible_observation_and_discloses_subset(self):
        plan = deepcopy(self.plan)
        plan["design"]["structure"] = "paired"
        plan["missing_policy"] = "complete_case"
        plan["comparisons"][0]["method"] = "paired_t"
        self.adopt("id,group,value\n001,A,1\n001,B,2\n002,A,2\n002,B,4\n003,A,4\n003,B,5\n004,A,7\n", plan, population="all")
        out, qa, result = self.render()
        self.assertEqual(qa["plotted_input_rows"], 7)
        self.assertEqual(result["counts"]["included_rows"], 6)
        self.assertIn("recorded included subset", (out / "analysis-caption.md").read_text())
        self.assertIn("004", renderer.read_source_csv(out / "plotting-data.csv")["id"].tolist())

    def test_stale_source_result_trace_and_wrong_fields_fail_before_new_exports(self):
        self.adopt("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        out, _, _ = self.render()
        prior = (out / "panel.svg").read_bytes()
        original_source = self.source.read_bytes()
        original_result = (self.root / "analysis/results.json").read_bytes()
        original_trace = (self.root / "analysis/analyzed-data.csv").read_bytes()
        for changed in ("source", "result", "trace", "fields", "unit", "comparison", "schema", "adjusted"):
            with self.subTest(changed=changed):
                self.source.write_bytes(original_source)
                (self.root / "analysis/results.json").write_bytes(original_result)
                (self.root / "analysis/analyzed-data.csv").write_bytes(original_trace)
                spec = deepcopy(self.spec)
                if changed == "source":
                    self.source.write_bytes(original_source.replace(b"a1,A,1", b"a1,A,9"))
                elif changed == "result":
                    (self.root / "analysis/results.json").write_bytes(original_result + b"\n")
                elif changed == "trace":
                    (self.root / "analysis/analyzed-data.csv").write_bytes(original_trace + b"\n")
                elif changed == "fields":
                    spec["fields"]["value"] = "other"
                elif changed == "unit":
                    spec["fields"]["unit"] = "other"
                elif changed == "comparison":
                    spec["statistics"]["analysis"]["comparison"] = "not_adopted"
                elif changed == "schema":
                    spec["statistics"]["analysis"]["schema_version"] = 2
                else:
                    spec["statistics"]["analysis"]["pvalue"] = "adjusted"
                with self.assertRaises(renderer.SpecError):
                    renderer.render(self.source, spec, out)
                self.assertEqual((out / "panel.svg").read_bytes(), prior)
                self.assertFalse(json.loads((out / "qa.json").read_text())["valid_outputs"])

    def test_rank_ties_and_zero_pairs_use_frozen_adopted_route(self):
        plan = deepcopy(self.plan)
        plan["design"]["structure"] = "paired"
        plan["comparisons"][0]["method"] = "wilcoxon"
        self.adopt("id,group,value\n1,A,2\n1,B,1\n2,A,2\n2,B,1\n3,A,0\n3,B,1\n4,A,1\n4,B,1\n", plan)
        with patch("scipy.stats.wilcoxon", side_effect=AssertionError("Must retain adopted tied-rank calculation")):
            _, _, result = self.render()
        self.assertEqual(result["pvalue"], 1)
        self.assertEqual(result["counts"]["zero_difference_pairs"], 1)
        self.assertAlmostEqual(result["effect"]["estimate"], 1/3)
        self.assertIn("Exact sign permutation", result["pvalue_method"])

    def test_spearman_keeps_small_sample_exact_permutation_result(self):
        plan = deepcopy(self.plan)
        plan["comparisons"][0] = {"name": "association", "method": "spearman", "fields": {"x": "x", "y": "y"}}
        report = self.adopt("id,x,y\n001,1,1\n002,2,2\n003,3,4\n004,4,3\n", plan)
        self.spec.update(chart="scatter", fields={"x": "x", "y": "y", "unit": "id"}, options={})
        with patch("scipy.stats.spearmanr", side_effect=AssertionError("Must retain adopted exact permutation")):
            _, _, result = self.render()
        self.assertEqual(result["pvalue"], report["comparisons"][0]["pvalue"])
        self.assertIn("Exact pairing permutation", result["pvalue_method"])
        self.assertAlmostEqual(result["statistic"], .8)

    def test_relative_binding_is_resolved_before_relocation_and_snapshot_is_reusable(self):
        self.adopt("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        self.spec["statistics"]["analysis"]["results_file"] = "analysis/results.json"
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.spec))
        resolved, _ = renderer.resolve_spec(self.spec, spec_path=spec_path)
        self.assertEqual(resolved["statistics"]["analysis"]["results_file"], str((self.root / "analysis/results.json").resolve()))
        self.assertEqual(self.spec["statistics"]["analysis"]["results_file"], "analysis/results.json")
        out = self.root / "plot"
        renderer.render_spec_file(self.source, spec_path, out)
        revised = deepcopy(resolved)
        revised["statistics"]["analysis"]["results_file"] = str(out / "adopted-analysis/results.json")
        _, _, result = self.render("snapshot-replay", revised)
        self.assertFalse(result["adoption"]["recomputed"])

    def test_legacy_compatibility_is_explicit_and_cannot_mix_with_adoption(self):
        self.adopt("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        mixed = deepcopy(self.spec)
        mixed["statistics"]["method"] = "welch"
        with self.assertRaisesRegex(renderer.SpecError, "cannot be combined"):
            renderer.render(self.source, mixed, self.root / "mixed")
        self.spec["statistics"] = {"method": "welch", "groups": ["A", "B"]}
        _, _, result = self.render()
        self.assertEqual(result["compatibility"]["mode"], "legacy_render_statistics")
        self.assertAlmostEqual(result["pvalue"], .021311641128756727)

    def test_analysis_rejects_broken_quote_before_publishing_report(self):
        # The permissive CSV reader previously accepted an unterminated quoted
        # final numerical field, even though the renderer rejected that source.
        with self.assertRaisesRegex(analysis.AnalysisError, "Malformed CSV"):
            self.adopt('id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,"6\n')
        self.assertFalse((self.root / "analysis/results.json").exists())

    def test_legacy_focused_runtime_does_not_require_optional_analysis_helper(self):
        fresh = module("easyviz_analysis_binding_fresh_runtime", "render.py")
        self.assertNotIn("analysis_result.py", fresh.RUNTIME_SOURCE_DIGESTS)
        runtime = self.root / "legacy-runtime"
        runtime.mkdir()
        for name in fresh.RUNTIME_SOURCE_DIGESTS:
            shutil.copyfile(SCRIPTS / name, runtime / name)
        loader = importlib.util.spec_from_file_location("easyviz_analysis_binding_legacy_copy", runtime / "render.py")
        legacy = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(legacy)
        self.source.write_text("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        self.spec["statistics"] = {"method": "welch", "groups": ["A", "B"]}
        self.spec["colors"] = {"A": "#2687bd", "B": "#ed8b43"}
        qa = legacy.render(self.source, self.spec, self.root / "legacy-replay")
        self.assertEqual(qa["status"], "pass")
        self.assertFalse((runtime / "analysis_result.py").exists())
        self.assertNotIn("analysis_result.py", legacy.RUNTIME_SOURCE_DIGESTS)

    def test_rehashed_trace_cannot_change_source_values_or_omit_selected_records(self):
        self.adopt("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        report_path = self.root / "analysis/results.json"
        trace_path = self.root / "analysis/analyzed-data.csv"
        original_trace = trace_path.read_bytes()
        original_report = json.loads(report_path.read_bytes())
        for altered in (original_trace.replace(b"a1,A,1", b"a1,A,9"), b"\n".join(original_trace.split(b"\n")[:-2]) + b"\n"):
            with self.subTest(altered=altered):
                trace_path.write_bytes(altered)
                report = deepcopy(original_report)
                report["artifacts"]["analyzed-data.csv"] = {"sha256": hashlib.sha256(altered).hexdigest(), "bytes": len(altered)}
                report_path.write_text(json.dumps(report))
                self.spec["statistics"]["analysis"]["results_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(renderer.SpecError, "literal source values|every selected source record"):
                    self.render("tampered")


if __name__ == "__main__":
    unittest.main()
