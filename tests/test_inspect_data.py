"""Directory intake preserves sources and makes only bounded candidate claims."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/inspect_data.py"
loader = importlib.util.spec_from_file_location("intake", SCRIPT)
intake = importlib.util.module_from_spec(loader)
loader.loader.exec_module(intake)


class InspectDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-intake-")
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.source = self.data / "observations.csv"
        self.source.write_text("sample_id,condition,measurement,other\n001,A,1.0,9\n002,A,2.0,8\n003,B,NA,7\n004,B,4.0,6\n", encoding="utf-8")
        self.out = self.root / "exploration"

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *extra, input_path=None, out=None):
        return subprocess.run([sys.executable, str(SCRIPT), "--input", str(input_path or self.data),
                               "--out", str(out or self.out), *map(str, extra)],
                              cwd=self.root, capture_output=True, text=True)

    def test_mixed_directory_inventory_preserves_identifiers_and_sources(self):
        sub = self.data / "nested"
        sub.mkdir()
        (sub / "metadata.tsv").write_text("sample_id\tbatch\n001\tfirst\n002\tsecond\n")
        (self.data / "README.md").write_text("not a table")
        (self.data / "broken.csv").write_text("a,b\n1,2,3\n")
        before = {path: path.read_bytes() for path in self.data.rglob("*") if path.is_file()}
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(len(manifest["tables"]), 2)
        self.assertEqual(len(manifest["errors"]), 1)
        table = next(table for table in manifest["tables"] if table["path"] == self.source.name)
        self.assertEqual(table["sample_rows"][0]["sample_id"], "001")
        self.assertEqual(table["columns"][0]["type_hint"], "identifier_candidate")
        self.assertEqual(table["columns"][0]["storage"], "string")
        measurement = next(column for column in table["columns"] if column["name"] == "measurement")
        self.assertEqual(measurement["missing"], 1)
        self.assertEqual(measurement["descriptive"]["n"], 3)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse(manifest["inference_run"])
        self.assertFalse(manifest["sources_modified"])
        self.assertTrue((self.out / "exploration.md").is_file())

    def test_candidates_do_not_invent_design_or_run_significance(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        options = json.loads((self.out / "analysis-options.json").read_text())
        self.assertEqual(options["track"], "create")
        self.assertFalse(options["inference_run"])
        table = options["tables"][0]
        self.assertIsNone(table["declared_design"])
        distribution = next(option for option in table["options"] if option["id"] == "distribution")
        plan = distribution["descriptive_analysis_plan"]
        self.assertEqual(plan["comparisons"][0]["method"], "descriptive")
        self.assertIsNone(plan["design"]["unit"])
        self.assertFalse(plan["design"]["confirmed"])
        for option in table["options"]:
            self.assertTrue(option["inference"]["questions"])
            self.assertNotIn("p_value", option)
        self.assertLessEqual(len(table["options"]), 3)

    def test_inventory_only_preserves_source_profiles_without_track_or_recommendations(self):
        original = self.source.read_bytes()
        result = self.cli("--inventory-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({path.name for path in self.out.iterdir()}, {"manifest.json", "exploration.md"})
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertIsNone(manifest["track"])
        self.assertEqual(manifest["mode"], "inventory")
        self.assertEqual(manifest["tables"][0]["sample_rows"][0]["sample_id"], "001")
        self.assertEqual(manifest["tables"][0]["rows_inspected"], 4)
        self.assertFalse(manifest["inference_run"])
        report = (self.out / "exploration.md").read_text()
        self.assertIn("active plotting track remains unchanged", report)
        self.assertNotIn("analysis-options.json", report)
        self.assertNotIn("candidate reading tasks", report)
        self.assertEqual(self.source.read_bytes(), original)
        # The shared inventory path must not even invoke the create recommender.
        with patch.object(intake, "_options", side_effect=AssertionError("create recommender invoked")):
            _, recommendations = intake.inspect(self.source, self.root / "api-inventory", inventory_only=True)
        self.assertIsNone(recommendations)

    def test_safe_scan_excludes_symlinks_hidden_output_and_dependencies(self):
        outside = self.root / "outside.csv"
        outside.write_text("secret\nexternal\n")
        (self.data / "escape.csv").symlink_to(outside)
        for name in (".hidden", "outputs", "venv", "node_modules"):
            directory = self.data / name
            directory.mkdir()
            (directory / "ignored.csv").write_text("x\n1\n")
        result = self.cli(out=self.data / "review-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.data / "review-run/manifest.json").read_text())
        self.assertEqual([table["path"] for table in manifest["tables"]], ["observations.csv"])
        self.assertTrue(any(entry["path"] == "escape.csv" and "symlink" in entry["reason"] for entry in manifest["skipped"]))

    def test_outputs_never_replace_sources_or_prior_review(self):
        for out in (self.data, self.source):
            result = self.cli(out=out)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
        self.out.mkdir()
        sentinel = self.out / "manifest.json"
        sentinel.write_text("original")
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(sentinel.read_text(), "original")

    def test_explicit_input_symlink_is_rejected_without_reading(self):
        link = self.root / "linked.csv"
        link.symlink_to(self.source)
        result = self.cli(input_path=link)
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", result.stderr)
        self.assertFalse(self.out.exists())

    def test_no_usable_table_has_actionable_error_and_no_partial_report(self):
        self.source.write_text("a,a\n1,2\n")
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate column names", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.out.exists())

    def test_empty_and_non_utf8_tables_are_reported_in_mixed_input(self):
        (self.data / "empty.csv").write_text("")
        (self.data / "legacy.tsv").write_bytes(b"id\n\xff\n")
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        errors = json.loads((self.out / "manifest.json").read_text())["errors"]
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("UTF-8" in error["reason"] for error in errors))

    def test_declared_roles_are_preserved_without_selecting_inference(self):
        declaration = {"table": "observations.csv", "question": "Compare the adopted measurement",
                       "fields": {"group": "condition", "value": "measurement"},
                       "design": {"unit": "sample_id", "unit_definition": "one independently sampled specimen", "structure": "independent", "confirmed": True},
                       "missing_tokens": ["", "NA"], "missing_policy": "complete_case"}
        design_path = self.root / "design.json"
        design_path.write_text(json.dumps(declaration))
        result = self.cli("--design", design_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        table = json.loads((self.out / "analysis-options.json").read_text())["tables"][0]
        self.assertEqual(table["declared_design"], declaration)
        plan = table["options"][0]["descriptive_analysis_plan"]
        self.assertEqual(plan["design"], declaration["design"])
        self.assertEqual(plan["comparisons"][0]["fields"], declaration["fields"])
        self.assertEqual(plan["comparisons"][0]["method"], "descriptive")
        self.assertNotIn("paired_candidate", [option["id"] for option in table["options"]])
        methods = table["options"][0]["inference"]["methods_to_consider_after_design"]
        self.assertEqual(methods, ["welch or mannwhitney for independent two-group questions"])

    def test_missing_declared_column_fails_before_creating_output(self):
        path = self.root / "design.json"
        path.write_text(json.dumps({"table": "observations.csv", "fields": {"value": "imagined"}}))
        result = self.cli("--design", path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Declared columns not found", result.stderr)
        self.assertFalse(self.out.exists())

    def test_row_limits_make_profile_scope_explicit(self):
        with patch.dict(intake.LIMITS, rows_per_table=2):
            manifest, options = intake.inspect(self.source, self.out)
        table = manifest["tables"][0]
        self.assertFalse(table["rows_complete"])
        self.assertIsNone(table["row_count"])
        self.assertEqual(table["rows_inspected"], 2)
        self.assertIn("prefix", options["tables"][0]["profile_scope"])

    def test_duplicate_rows_are_reported_not_removed(self):
        self.source.write_text("sample_id,measurement\n001,2\n001,2\n002,3\n")
        manifest, _ = intake.inspect(self.source, self.out)
        self.assertEqual(manifest["tables"][0]["rows_inspected"], 3)
        self.assertEqual(manifest["tables"][0]["duplicate_rows_in_inspected_scope"], 1)

    def test_identifiers_and_nonnumeric_tables_do_not_become_measurements(self):
        self.source.write_text("sample_id,label\n001,case\n002,control\n")
        _, options = intake.inspect(self.source, self.out)
        self.assertEqual(options["tables"][0]["candidate_columns"]["numeric"], [])
        self.assertEqual(options["tables"][0]["options"][0]["id"], "table_structure")

    def test_custom_missing_tokens_keep_na_category(self):
        self.source.write_text("condition,value\nNA,1\nB,2\n")
        path = self.root / "design.json"
        path.write_text(json.dumps({"table": "observations.csv", "missing_tokens": [""]}))
        manifest, _ = intake.inspect(self.source, self.out, path)
        self.assertEqual(manifest["tables"][0]["columns"][0]["missing"], 0)
        self.assertIn("NA", manifest["tables"][0]["columns"][0]["levels"])

    def test_xlsx_sheets_formula_text_and_string_identifiers(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl is optional outside the installed runtime")
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Observations"
        sheet.append(["sample_id", "measurement", "formula"])
        sheet.append(["001", 2, "=1+1"])
        second = workbook.create_sheet("Metadata")
        second.append(["sample_id", "batch"])
        second.append(["001", "first"])
        path = self.data / "book.xlsx"
        workbook.save(path)
        result = self.cli(input_path=path)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(len(manifest["tables"]), 2)
        observed = manifest["tables"][0]
        self.assertEqual(observed["sample_rows"][0]["sample_id"], "001")
        self.assertEqual(observed["sample_rows"][0]["formula"], "=1+1")
        self.assertEqual(observed["columns"][2]["formula_cells"], 1)

    def test_corrupt_xlsx_in_mixed_directory_is_recorded(self):
        (self.data / "bad.xlsx").write_bytes(b"not a zip workbook")
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads((self.out / "manifest.json").read_text())["errors"]), 1)

    def test_valid_xlsx_sheet_survives_unusable_sheet_in_same_workbook(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl is optional outside the installed runtime")
        workbook = openpyxl.Workbook()
        workbook.active.title = "Bad"
        workbook.active.append(["duplicate", "duplicate"])
        workbook.active.append([1, 2])
        good = workbook.create_sheet("Good")
        good.append(["value"])
        good.append([3])
        path = self.data / "sheets.xlsx"
        workbook.save(path)
        manifest, _ = intake.inspect(path, self.out)
        self.assertEqual([table["sheet"] for table in manifest["tables"]], ["Good"])
        self.assertEqual(len(manifest["errors"]), 1)

    def test_missing_tokens_match_analysis_exactly_without_trimming(self):
        self.source.write_text("measurement\n NA \n2\n")
        manifest, _ = intake.inspect(self.source, self.out)
        column = manifest["tables"][0]["columns"][0]
        self.assertEqual(column["missing"], 0)
        self.assertEqual(column["nonmissing"], 2)
        self.assertEqual(column["numeric_parseable"], 1)

    def test_descriptive_candidate_executes_through_analysis_cli(self):
        script = SCRIPT.with_name("analyze.py")
        self.assertTrue(script.is_file(), "Directory intake requires the advertised analysis entry point")
        _, options = intake.inspect(self.source, self.out)
        plan = options["tables"][0]["options"][0]["descriptive_analysis_plan"]
        # Adopting complete_case is a recorded user/Agent choice, not a hidden
        # effect of the inventory step. Unknown units remain unknown.
        plan["missing_policy"] = "complete_case"
        path = self.root / "adopted-plan.json"
        path.write_text(json.dumps(plan))
        result = subprocess.run([sys.executable, str(script), "--data", str(self.source),
                                 "--plan", str(path), "--out", str(self.root / "analysis")],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.root / "analysis/results.json").read_text())
        comparison = report["comparisons"][0]
        self.assertEqual(comparison["method"], "descriptive")
        self.assertIsNone(comparison["pvalue"])
        self.assertIsNone(comparison["counts"]["independent_unit_count"])
        self.assertEqual(comparison["counts"]["included_rows"], 3)
        self.assertIn("001", (self.root / "analysis/analyzed-data.csv").read_text())

    def test_extreme_finite_numbers_do_not_emit_nonfinite_json(self):
        self.source.write_text("measurement\n1e308\n1e308\n")
        manifest, _ = intake.inspect(self.source, self.out)
        summary = manifest["tables"][0]["columns"][0]["descriptive"]
        self.assertEqual(summary["median"], 1e308)
        self.assertNotIn("Infinity", (self.out / "manifest.json").read_text())


if __name__ == "__main__":
    unittest.main()
