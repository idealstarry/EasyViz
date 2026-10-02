"""Numerical and scientific-design checks for the planned create-track helper."""
from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/analyze.py"
loader = importlib.util.spec_from_file_location("easyviz_analyze", SCRIPT)
analysis = importlib.util.module_from_spec(loader)
loader.loader.exec_module(analysis)


class AnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-analysis-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.base = {"schema_version": 1, "question": "Does the planned measurement differ between independent groups?",
                     "design": {"unit": "id", "unit_definition": "one independently sampled specimen", "structure": "independent", "confirmed": True},
                     "missing_policy": "error",
                     "comparisons": [{"name": "primary", "method": "welch", "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]}]}

    def tearDown(self):
        self.temp.cleanup()

    def run_analysis(self, text, plan=None, name="out"):
        self.source.write_text(text, encoding="utf-8")
        return analysis.analyze(self.source, deepcopy(plan or self.base), self.root / name)

    def paired_plan(self, method="paired_t"):
        plan = deepcopy(self.base)
        plan["design"].update(structure="paired", unit_definition="one independently sampled subject, measured before and after")
        plan["comparisons"][0]["method"] = method
        return plan

    def correlation_plan(self, method="pearson"):
        plan = deepcopy(self.base)
        plan["comparisons"][0] = {"name": "association", "method": method, "fields": {"x": "x", "y": "y"}}
        return plan

    def test_welch_known_statistic_effect_and_interval(self):
        report = self.run_analysis("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        result = report["comparisons"][0]
        self.assertAlmostEqual(result["statistic"], -3.6742346141747673)
        self.assertAlmostEqual(result["pvalue"], 0.021311641128756713)
        self.assertAlmostEqual(result["effect"]["estimate"], -3)
        self.assertAlmostEqual(result["degrees_of_freedom"], 4)
        # t_(.975,4)=2.7764451051977987; SE=sqrt(2/3).
        self.assertAlmostEqual(result["interval"]["lower"], -3 - 2.7764451051977987 * math.sqrt(2/3))
        self.assertAlmostEqual(result["interval"]["upper"], -3 + 2.7764451051977987 * math.sqrt(2/3))
        self.assertIsNone(result["adjusted_pvalue"])
        self.assertIsNone(result["adjustment"])
        self.assertEqual(result["counts"]["independent_unit_count"], 6)
        self.assertEqual(result["summaries"][0]["sd"], 1)
        self.assertEqual(result["summaries"][0]["q1"], 1.5)
        self.assertEqual(result["summaries"][0]["q3"], 2.5)
        self.assertEqual(result["summaries"][0]["quantile_method"], "linear")
        self.assertEqual(result["interval"]["scope"], "pointwise; not multiplicity-adjusted")

    def test_paired_alignment_preserves_leading_zero_ids_and_direction(self):
        # Deliberately shuffled, values A=[1,2,4], B=[2,4,5], d=[-1,-2,-1].
        text = "id,group,value\n002,B,4\n001,A,1\n003,B,5\n003,A,4\n001,B,2\n002,A,2\n"
        report = self.run_analysis(text, self.paired_plan())
        result = report["comparisons"][0]
        self.assertEqual(result["pair_unit_ids"], ["002", "001", "003"])
        self.assertEqual(result["counts"]["complete_pairs"], 3)
        self.assertAlmostEqual(result["statistic"], -4)
        self.assertAlmostEqual(result["pvalue"], 0.05719095841793663)
        self.assertAlmostEqual(result["effect"]["estimate"], -4/3)
        self.assertAlmostEqual(result["interval"]["lower"], -4/3 - 4.302652729696142/3)
        self.assertAlmostEqual(result["interval"]["upper"], -4/3 + 4.302652729696142/3)
        with (self.root / "out/analyzed-data.csv").open() as stream:
            trace = list(csv.DictReader(stream))
        self.assertEqual([row["id"] for row in trace], ["002", "001", "003", "003", "001", "002"])
        self.assertEqual(self.source.read_text(), text)

    def test_rank_tests_known_results_and_effect_directions(self):
        plan = deepcopy(self.base)
        plan["comparisons"][0]["method"] = "mannwhitney"
        report = self.run_analysis("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n", plan)
        result = report["comparisons"][0]
        self.assertEqual(result["statistic"], 0)
        self.assertAlmostEqual(result["pvalue"], 0.1)
        self.assertAlmostEqual(result["effect"]["estimate"], -1)
        self.assertIsNone(result["interval"])
        self.assertIn("not generally a test of median", " ".join(result["notes"]))
        report = self.run_analysis("id,group,value\n1,A,2\n1,B,1\n2,A,4\n2,B,2\n3,A,6\n3,B,3\n4,A,8\n4,B,4\n", self.paired_plan("wilcoxon"), name="wilcoxon")
        result = report["comparisons"][0]
        self.assertEqual(result["statistic"], 0)
        self.assertAlmostEqual(result["pvalue"], 0.125)
        self.assertEqual(result["effect"]["estimate"], 1)
        self.assertEqual(result["counts"]["nonzero_pairs"], 4)

    def test_tied_rank_tests_use_exact_permutations_and_account_for_zeros(self):
        plan = deepcopy(self.base)
        plan["comparisons"][0]["method"] = "mannwhitney"
        result = self.run_analysis("id,group,value\na1,A,1\na2,A,1\nb1,B,1\nb2,B,2\n", plan)["comparisons"][0]
        self.assertEqual(result["statistic"], 1)
        self.assertEqual(result["pvalue"], 1)
        self.assertEqual(result["effect"]["estimate"], -0.5)
        self.assertIn("permutation", result["pvalue_method"])
        result = self.run_analysis("id,group,value\n1,A,2\n1,B,1\n2,A,2\n2,B,1\n3,A,0\n3,B,1\n4,A,1\n4,B,1\n", self.paired_plan("wilcoxon"), name="wilcoxon")["comparisons"][0]
        self.assertEqual(result["counts"]["zero_difference_pairs"], 1)
        self.assertEqual(result["counts"]["nonzero_pairs"], 3)
        self.assertAlmostEqual(result["effect"]["estimate"], 1/3)
        self.assertEqual(result["pvalue"], 1)
        self.assertIn("permutation", result["pvalue_method"])

    def test_wilcoxon_explicit_precision_resolves_false_ties(self):
        plan = self.paired_plan("wilcoxon")
        plan["comparisons"][0]["difference_decimals"] = 3
        text = "id,group,value\n1,A,0.5\n1,B,0.525\n2,A,0.825\n2,B,0.775\n3,A,0.375\n3,B,0.325\n4,A,0.5\n4,B,0.55\n"
        result = self.run_analysis(text, plan)["comparisons"][0]
        self.assertEqual(result["statistic"], 4)
        self.assertAlmostEqual(result["effect"]["estimate"], 0.2)
        self.assertIn("rounded to 3", " ".join(result["notes"]))

    def test_wilcoxon_zero_heavy_pairs_route_by_effective_sign_sample(self):
        # Only five signs can affect the statistic: the two all-same-sign
        # allocations among 2**5 yield the exact two-sided p-value 0.0625.
        # Routing by all 20 pairs wrongly used an approximation (p~0.0431).
        for values, expected_route in (([1, 2, 3, 4, 5], "Exact signed-rank"),
                                       ([1, 1, 1, 1, 1], "Exact sign permutation")):
            with self.subTest(values=values):
                differences = values + [0] * 15
                records = ["id,group,value"]
                for index, difference in enumerate(differences, start=1):
                    records.extend([f"{index:03},A,{difference}", f"{index:03},B,0"])
                output = "zero-heavy-" + str(values[-1])
                result = self.run_analysis("\n".join(records) + "\n", self.paired_plan("wilcoxon"), name=output)["comparisons"][0]
                self.assertEqual(result["statistic"], 0)
                self.assertEqual(result["pvalue"], 0.0625)
                self.assertIn(expected_route, result["pvalue_method"])
                self.assertIn("nonzero differences", result["pvalue_method"])
                self.assertEqual(result["counts"]["complete_pairs"], 20)
                self.assertEqual(result["counts"]["nonzero_pairs"], 5)
                self.assertEqual(result["counts"]["zero_difference_pairs"], 15)
                self.assertEqual(result["counts"]["included_rows"], 40)
                self.assertEqual(result["counts"]["excluded_rows"], 0)
                self.assertEqual(result["summaries"][0]["n_rows"], 20)
                self.assertEqual(result["summaries"][0]["mean"], sum(values) / 20)
                self.assertEqual(result["effect"]["estimate"], 1)
                with (self.root / output / "analyzed-data.csv").open() as stream:
                    trace = list(csv.DictReader(stream))
                self.assertEqual(len(trace), 40)
                self.assertEqual(set(row["_easyviz_status"] for row in trace), {"included"})

    def test_pearson_fisher_interval_and_spearman_exact_pvalue(self):
        text = "id,x,y\n01,1,2\n02,2,1\n03,3,3\n04,4,5\n05,5,4\n"
        result = self.run_analysis(text, self.correlation_plan())["comparisons"][0]
        self.assertAlmostEqual(result["statistic"], 0.8)
        self.assertAlmostEqual(result["pvalue"], 0.1040880386618278)
        z, half = math.atanh(.8), 1.959963984540054 / math.sqrt(2)
        self.assertAlmostEqual(result["interval"]["lower"], math.tanh(z-half))
        self.assertAlmostEqual(result["interval"]["upper"], math.tanh(z+half))
        result = self.run_analysis("id,x,y\n01,1,1\n02,2,2\n03,3,3\n04,4,4\n", self.correlation_plan("spearman"), name="spearman")["comparisons"][0]
        self.assertAlmostEqual(result["statistic"], 1)
        self.assertAlmostEqual(result["pvalue"], 2/24)
        self.assertIn("Exact pairing", result["pvalue_method"])
        self.assertIsNone(result["interval"])

    def test_missing_policy_reports_rows_and_complete_pair_exclusions(self):
        plan = self.paired_plan()
        plan["missing_policy"] = "complete_case"
        text = "id,group,value\n01,A,1\n01,B,2\n02,A,2\n02,B,4\n03,A,3\n03,B,\n04,A,7\n99,C,500\n"
        report = self.run_analysis(text, plan)
        result = report["comparisons"][0]
        self.assertEqual(result["counts"]["complete_pairs"], 2)
        self.assertEqual(result["counts"]["excluded_pair_units"], 2)
        self.assertEqual(result["counts"]["selected_rows"], 7)
        self.assertEqual(result["counts"]["included_rows"], 4)
        self.assertEqual(result["counts"]["excluded_rows"], 3)
        self.assertEqual(result["counts"]["unselected_rows"], 1)
        self.assertEqual(set(result["excluded_pair_unit_ids"]), {"03", "04"})
        with (self.root / "out/analyzed-data.csv").open() as stream:
            trace = list(csv.DictReader(stream))
        self.assertEqual(len(trace), 7)
        self.assertEqual(sum(row["_easyviz_status"] == "excluded" for row in trace), 3)
        self.assertEqual(trace[5]["value"], "")
        self.assertEqual(trace[5]["_easyviz_exclusion"], "missing_measurement:value;incomplete_pair")
        # Error policy rejects both absent partner and missing measurements.
        for body in ["id,group,value\n1,A,1\n1,B,2\n2,A,3\n", "id,group,value\n1,A,1\n1,B,\n"]:
            self.source.write_text(body)
            with self.assertRaises(analysis.AnalysisError):
                analysis.analyze(self.source, self.paired_plan(), self.root / "error")
            self.assertFalse((self.root / "error").exists())

    def test_row_descriptions_never_claim_independent_samples(self):
        plan = deepcopy(self.base)
        plan["design"] = {"unit": None, "unit_definition": "unknown; exploratory rows", "structure": "unknown", "confirmed": False}
        plan["comparisons"] = [{"name": "overview", "method": "descriptive", "fields": {"group": "group", "value": "value"}}]
        result = self.run_analysis("id,group,value\n01,A,1\n01,A,3\n02,B,4\n", plan)["comparisons"][0]
        self.assertIsNone(result["counts"]["independent_unit_count"])
        self.assertEqual(result["summaries"][0]["mean"], 2)
        self.assertEqual(result["summaries"][0]["n_rows"], 2)
        self.assertIsNone(result["summaries"][0]["independent_unit_count"])
        self.assertIsNone(result["pvalue"])
        self.assertIsNone(result["interval"])

    def test_missing_numeric_tokens_do_not_transform_ids_or_categories(self):
        plan = deepcopy(self.base)
        plan["comparisons"] = [{"name": "overview", "method": "descriptive", "fields": {"group": "group", "value": "value"}}]
        plan["missing_policy"] = "complete_case"
        report = self.run_analysis("id,group,value\nNA,NA,2\n001,NA,NA\n002,NA,4\n", plan)
        result = report["comparisons"][0]
        self.assertEqual(result["summaries"][0]["group"], "NA")
        self.assertEqual(result["summaries"][0]["mean"], 3)
        self.assertEqual(result["exclusions"][0]["unit"], "001")
        self.assertEqual(result["counts"]["included_units"], 2)

    def test_multiplicity_matches_hand_calculated_holm_and_bh(self):
        p = [.03, .01, .04, .2]
        self.assertTrue(np.allclose(analysis.adjust_pvalues(p, "holm"), [.09, .04, .09, .2]))
        self.assertTrue(np.allclose(analysis.adjust_pvalues(p, "benjamini_hochberg"), [4*.04/3, .04, 4*.04/3, .2]))
        self.assertTrue(np.allclose(analysis.adjust_pvalues([.8,.8,1], "holm"), [1,1,1]))
        self.assertTrue(np.allclose(analysis.adjust_pvalues([0,.1,.1], "benjamini_hochberg"), [0,.1,.1]))
        for bad in ([math.nan], [-.1], [1.1], []):
            with self.assertRaises(analysis.AnalysisError):
                analysis.adjust_pvalues(bad, "holm")

    def test_multiple_planned_comparisons_adjust_exactly_declared_family(self):
        plan = deepcopy(self.base)
        plan["comparisons"].append({"name": "rank", "method": "mannwhitney", "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]})
        text = "id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n"
        self.source.write_text(text)
        with self.assertRaisesRegex(analysis.AnalysisError, "multiplicity"):
            analysis.analyze(self.source, plan, self.root / "invalid")
        plan["multiplicity"] = {"family": "planned two-method sensitivity check", "adjustment": "holm", "comparisons": ["rank", "primary"]}
        results = analysis.analyze(self.source, plan, self.root / "out")["comparisons"]
        self.assertAlmostEqual(results[0]["adjusted_pvalue"], 2 * results[0]["pvalue"])
        self.assertAlmostEqual(results[1]["adjusted_pvalue"], .1)
        self.assertEqual(results[0]["adjustment"]["family_size"], 2)
        self.assertIn("not multiplicity-adjusted", results[0]["interval"]["scope"])
        for members in [["primary"], ["primary", "rank", "extra"], ["rank", "rank"]]:
            bad = deepcopy(plan)
            bad["multiplicity"]["comparisons"] = members
            with self.assertRaises(analysis.AnalysisError):
                analysis.validate_plan(bad)

    def test_design_rejects_pseudoreplication_and_unknown_independence(self):
        bodies = ["id,group,value\n1,A,1\n1,A,2\n2,B,3\n3,B,4\n", "id,group,value\n1,A,1\n2,A,2\n1,B,3\n2,B,4\n", "id,group,value\n,A,1\n2,A,2\n3,B,3\n4,B,4\n"]
        for body in bodies:
            with self.subTest(body=body):
                self.source.write_text(body)
                with self.assertRaises(analysis.AnalysisError):
                    analysis.analyze(self.source, self.base, self.root / "bad")
                self.assertFalse((self.root / "bad").exists())
        plan = deepcopy(self.base)
        plan["design"]["confirmed"] = False
        with self.assertRaisesRegex(analysis.AnalysisError, "confirmed=true"):
            analysis.validate_plan(plan)
        plan = deepcopy(self.base)
        plan["design"]["structure"] = "paired"
        with self.assertRaisesRegex(analysis.AnalysisError, "structure=independent"):
            analysis.validate_plan(plan)
        correlation = self.correlation_plan()
        self.source.write_text("id,x,y\n01,1,1\n01,2,2\n02,3,3\n")
        with self.assertRaisesRegex(analysis.AnalysisError, "Repeated unit"):
            analysis.analyze(self.source, correlation, self.root / "bad")

    def test_rejects_invalid_numeric_data_degenerate_tests_and_duplicate_headers(self):
        bodies = ["id,group,value\n1,A,one\n", "id,group,value\n1,A,inf\n", "id,group,value\n1,A,NaN\n", "id,group,value,value\n1,A,2,3\n", "id,group,value\n1,A,1\n\n", "id,group,value\n1,A,1\n2,A,1\n3,B,1\n4,B,1\n"]
        for body in bodies:
            with self.subTest(body=body):
                self.source.write_text(body)
                with self.assertRaises(analysis.AnalysisError):
                    analysis.analyze(self.source, self.base, self.root / "bad")
                self.assertFalse((self.root / "bad").exists())
        for plan in [self.correlation_plan(), self.paired_plan(), self.paired_plan("wilcoxon")]:
            body = "id,x,y\n1,1,1\n2,1,2\n3,1,3\n" if plan["comparisons"][0]["method"] == "pearson" else "id,group,value\n1,A,1\n1,B,1\n2,A,2\n2,B,2\n"
            self.source.write_text(body)
            with self.assertRaises(analysis.AnalysisError):
                analysis.analyze(self.source, plan, self.root / "bad")

    def test_explicit_schema_rejects_ambiguous_or_unsupported_roles(self):
        for mutate in [lambda p: p.update(schema_version=True), lambda p: p.update(unknown=1),
                       lambda p: p["design"].update(unit="value"), lambda p: p["comparisons"][0].update(groups=["A", "A"]),
                       lambda p: p["comparisons"][0].update(method=["welch"]), lambda p: p["comparisons"][0].update(confidence_level=1), lambda p: p["comparisons"][0].update(difference_decimals=3),
                       lambda p: p["comparisons"][0]["fields"].update(x="value"), lambda p: p.update(missing_tokens=["NA"])]:
            with self.subTest(mutate=mutate):
                plan = deepcopy(self.base)
                mutate(plan)
                with self.assertRaises(analysis.AnalysisError):
                    analysis.validate_plan(plan)

    def test_source_identity_artifact_hashes_and_fresh_output_policy(self):
        text = "id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n"
        self.source.write_text(text)
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(self.base))
        report = analysis.analyze(self.source, self.base, self.root / "out", plan_path=plan_path)
        self.assertEqual(report["provenance"]["data"]["sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(report["provenance"]["plan"]["source_sha256"], hashlib.sha256(plan_path.read_bytes()).hexdigest())
        self.assertIn("scipy", report["provenance"]["runtime"])
        for name, identity in report["artifacts"].items():
            raw = (self.root / "out" / name).read_bytes()
            self.assertEqual(identity["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(identity["bytes"], len(raw))
        before = (self.root / "out/results.json").read_bytes()
        with self.assertRaisesRegex(analysis.AnalysisError, "fresh attempt"):
            analysis.analyze(self.source, self.base, self.root / "out")
        self.assertEqual((self.root / "out/results.json").read_bytes(), before)
        self.assertEqual(self.source.read_text(), text)

    def test_publication_failure_removes_partial_attempt_and_preserves_source(self):
        text = "id,group,value\na1,A,1\na2,A,2\nb1,B,4\nb2,B,5\n"
        self.source.write_text(text)
        with patch.object(analysis.os, "link", side_effect=OSError("publication failed")):
            with self.assertRaises(OSError):
                analysis.analyze(self.source, self.base, self.root / "out")
        self.assertFalse((self.root / "out").exists())
        self.assertEqual(self.source.read_text(), text)

    def test_plan_source_mismatch_and_duplicate_json_are_rejected(self):
        self.source.write_text("id,group,value\na1,A,1\na2,A,2\nb1,B,4\nb2,B,5\n")
        plan_path = self.root / "plan.json"
        changed = deepcopy(self.base)
        changed["question"] = "Another question"
        plan_path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(analysis.AnalysisError, "differs from plan_path"):
            analysis.analyze(self.source, self.base, self.root / "out", plan_path=plan_path)
        self.assertFalse((self.root / "out").exists())
        plan_path.write_text('{"schema_version": 1, "schema_version": 2}')
        with self.assertRaisesRegex(analysis.AnalysisError, "Duplicate JSON key"):
            analysis.read_plan(plan_path)
        completed = subprocess.run([sys.executable, str(SCRIPT), "--data", str(self.source), "--plan", str(plan_path), "--out", str(self.root / "cli")], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("Duplicate JSON key", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_padded_unit_identity_is_not_silently_split(self):
        self.source.write_text("id,group,value\n01,A,1\n01 ,A,2\n02,B,3\n03,B,4\n")
        with self.assertRaisesRegex(analysis.AnalysisError, "Padded unit ID"):
            analysis.analyze(self.source, self.base, self.root / "out")
        self.assertFalse((self.root / "out").exists())

    def test_cli_describes_contract_and_rejects_incomplete_invocation(self):
        completed = subprocess.run([sys.executable, str(SCRIPT), "--describe-plan"], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        description = json.loads(completed.stdout)
        self.assertEqual(description["track"], "create")
        self.assertIn("holm", description["multiplicity"]["adjustment"])
        completed = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
