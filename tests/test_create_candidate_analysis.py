"""Candidate planning must consume the same frozen inference/population as export."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"


def load(name):
    loader = importlib.util.spec_from_file_location("candidate_analysis_" + name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


analysis = load("analyze")
candidates = load("create_candidates")


class CreateCandidateAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-candidate-analysis-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.plan = {"schema_version": 1, "question": "Compare the declared specimen endpoint",
                     "design": {"unit": "id", "unit_definition": "one independent specimen", "structure": "independent", "confirmed": True},
                     "missing_policy": "error", "comparisons": [{"name": "primary", "method": "welch",
                     "fields": {"group": "group", "value": "value"}, "groups": ["A", "B"]}]}
        self.spec = {"chart": "distribution", "fields": {"group": "group", "value": "value", "unit": "id"},
                     "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "dpi": 100},
                     "formats": ["svg", "png"], "options": {"kind": "box"}, "seed": 4}

    def tearDown(self):
        candidates.core.plt.close("all")
        self.temp.cleanup()

    def adopt(self, body, *, plan=None, population="all", pvalue="raw"):
        self.source.write_text(body)
        report = analysis.analyze(self.source, deepcopy(plan or self.plan), self.root / "analysis")
        result = self.root / "analysis/results.json"
        self.spec["statistics"] = {"analysis": {"schema_version": 1, "results_file": "analysis/results.json",
            "results_sha256": hashlib.sha256(result.read_bytes()).hexdigest(), "comparison": "primary",
            "pvalue": pvalue, "population": population}, "annotate": False}
        spec_path = self.root / "spec.json"
        spec_path.write_text(json.dumps(self.spec))
        return report, spec_path

    def test_adjusted_adoption_is_reused_without_recomputing_and_survives_relative_path(self):
        plan = deepcopy(self.plan)
        secondary = deepcopy(plan["comparisons"][0])
        secondary.update(name="secondary", fields={"group": "group", "value": "value2"})
        plan["comparisons"].append(secondary)
        plan["multiplicity"] = {"family": "Endpoints", "adjustment": "holm", "comparisons": ["primary", "secondary"]}
        report, spec_path = self.adopt("id,group,value,value2\na1,A,1,2\na2,A,2,4\na3,A,3,3\nb1,B,4,3\nb2,B,5,2\nb3,B,6,1\n",
                                       plan=plan, pvalue="adjusted")
        before = {path: path.read_bytes() for path in (self.source, spec_path, *(self.root / "analysis").iterdir())}
        with patch("scipy.stats.ttest_ind", side_effect=AssertionError("Candidates must not recompute adopted tests")):
            manifest = candidates.create_candidates(self.source, spec_path, self.root / "candidates", new_draft=True, count=1)
        self.assertEqual(manifest["status"], "visual_review_pending")
        self.assertTrue(manifest["inputs_unchanged"])
        self.assertEqual(manifest["analysis_source_continuity"]["status"], "pass")
        out = self.root / "candidates/candidate-01"
        adopted = json.loads((out / "stats.json").read_text())
        self.assertEqual(adopted["annotation_pvalue"], report["comparisons"][0]["adjusted_pvalue"])
        self.assertFalse(adopted["adoption"]["recomputed"])
        self.assertEqual((out / "adopted-analysis/results.json").read_bytes(), (self.root / "analysis/results.json").read_bytes())
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_explicit_included_population_is_planned_and_exported_consistently(self):
        plan = deepcopy(self.plan)
        plan["design"].update(structure="paired", unit_definition="one independent paired subject")
        plan["missing_policy"] = "complete_case"
        plan["comparisons"][0]["method"] = "paired_t"
        _, spec_path = self.adopt("id,group,value\n002,B,4\n001,A,1\n003,B,5\n003,A,4\n001,B,2\n002,A,2\n004,A,30\n004,B,NA\n005,A,50\n",
                                 plan=plan, population="included")
        manifest = candidates.create_candidates(self.source, spec_path, self.root / "candidates", new_draft=True, count=1)
        self.assertEqual(manifest["status"], "visual_review_pending")
        self.assertEqual(manifest["features"]["source_input_rows"], 9)
        self.assertEqual(manifest["features"]["input_rows"], 6)
        self.assertEqual(manifest["features"]["group_counts"], {"B": 3, "A": 3})
        out = self.root / "candidates/candidate-01"
        qa = json.loads((out / "qa.json").read_text())
        self.assertEqual(qa["input_rows"], 9)
        self.assertEqual(qa["plotted_input_rows"], 6)
        self.assertEqual((out / "source-data.csv").read_bytes(), self.source.read_bytes())
        plotted = candidates.core.read_source_csv(out / "plotting-data.csv")
        self.assertEqual(plotted["id"].tolist(), ["002", "001", "003", "003", "001", "002"])

    def test_changed_companion_fails_without_creating_candidates(self):
        _, spec_path = self.adopt("id,group,value\na1,A,1\na2,A,2\na3,A,3\nb1,B,4\nb2,B,5\nb3,B,6\n")
        (self.root / "analysis/methodology.md").write_text("changed methodology")
        out = self.root / "candidates"
        with self.assertRaisesRegex(candidates.SpecError, "companion changed"):
            candidates.create_candidates(self.source, spec_path, out, new_draft=True)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
