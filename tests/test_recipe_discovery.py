"""Public discovery must route to real recipe CLIs without expanding the core."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1] / "skills/easyviz"
CORE = {"heatmap", "composition", "dotplot", "scatter", "distribution"}
RECIPES = {"paired", "replicate", "ecdf", "interval", "timecourse"}


class RecipeDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-discovery-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.source.write_text("x,y\n1,2\n2,3\n")

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, script, *arguments):
        return subprocess.run([sys.executable, str(script), *map(str, arguments)],
                              cwd=self.root, capture_output=True, text=True)

    def discovery(self, skill=SKILL):
        result = self.cli(skill / "scripts/render.py", "--describe-spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_discovered_routes_execute_and_core_families_stay_unchanged(self):
        described = self.discovery()
        self.assertEqual(set(described["chart"]), CORE)
        self.assertEqual(set(described["fields_by_chart"]), CORE)
        self.assertEqual(set(described["focused_recipes"]), RECIPES)
        for chart, route in described["focused_recipes"].items():
            with self.subTest(chart=chart):
                script, doc = Path(route["script"]), Path(route["doc"])
                self.assertTrue(script.is_absolute())
                self.assertTrue(doc.is_absolute() and doc.is_file())
                # Run the advertised path from an unrelated cwd, not an
                # internally imported registry or a duplicated script map.
                result = self.cli(script, "--describe-spec")
                self.assertEqual(result.returncode, 0, result.stderr)
                recipe = json.loads(result.stdout)
                self.assertEqual(recipe["chart"], chart)
                self.assertTrue(set(route["required_roles"]) <= set(recipe["fields"]))
        self.assertIn("component", described["focused_recipes"]["replicate"]["conditional_roles"])

    def test_draft_rejects_recipes_with_real_route_before_creating_spec(self):
        before = self.source.read_bytes()
        for chart, route in self.discovery()["focused_recipes"].items():
            with self.subTest(chart=chart):
                out = self.root / f"{chart}.json"
                result = self.cli(SKILL / "scripts/draft_spec.py", "--data", self.source,
                                  "--chart", chart, "--field", "value=y", "--out", out)
                self.assertEqual(result.returncode, 2)
                self.assertIn(route["script"], result.stderr)
                self.assertIn("--describe-spec", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(out.exists())
        self.assertEqual(self.source.read_bytes(), before)
        help_result = self.cli(SKILL / "scripts/draft_spec.py", "--help")
        self.assertEqual(help_result.returncode, 0)
        for chart in RECIPES:
            self.assertIn(f"{chart}_plot.py", help_result.stdout)

    def test_workflows_route_to_real_commands_with_only_two_tracks(self):
        routes = self.discovery()["workflow_tools"]
        self.assertEqual(set(routes), {"inspect_data", "analyze", "reference_packet", "figure_workbench"})
        for name, route in routes.items():
            with self.subTest(workflow=name):
                self.assertTrue(Path(route["doc"]).is_file())
                self.assertTrue(set(route["tracks"]) <= {"create", "reproduce"})
                result = self.cli(route["script"], "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(routes["analyze"]["tracks"], ["create"])
        self.assertEqual(routes["reference_packet"]["tracks"], ["reproduce"])

    def test_core_rejects_recipe_specs_with_truthful_failed_qa_and_route(self):
        before = self.source.read_bytes()
        for chart, route in self.discovery()["focused_recipes"].items():
            with self.subTest(chart=chart):
                spec = self.root / f"{chart}.json"
                spec.write_text(json.dumps({"chart": chart, "fields": {"value": "y"}}))
                out = self.root / f"{chart}-attempt"
                result = self.cli(SKILL / "scripts/render.py", "--data", self.source,
                                  "--spec", spec, "--out", out)
                self.assertEqual(result.returncode, 2)
                self.assertIn(route["script"], result.stderr)
                self.assertIn("--describe-spec", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                qa = json.loads((out / "qa.json").read_text())
                self.assertFalse(qa["valid_outputs"])
                self.assertEqual(qa["status"], "failed")
                self.assertFalse((out / "panel.png").exists())
        self.assertEqual(self.source.read_bytes(), before)

    def test_unknown_chart_has_no_invented_route_or_draft(self):
        out = self.root / "unknown.json"
        result = self.cli(SKILL / "scripts/draft_spec.py", "--data", self.source,
                          "--chart", "imagined_plot", "--field", "value=y", "--out", out)
        self.assertEqual(result.returncode, 2)
        self.assertIn("chart must be one of", result.stderr)
        self.assertNotIn("uses the focused recipe", result.stderr)
        self.assertFalse(out.exists())

    def test_discovery_relocates_with_portable_skill_copy(self):
        copied = self.root / "portable skill"
        (copied / "scripts").mkdir(parents=True)
        for script in (SKILL / "scripts").glob("*.py"):
            shutil.copy2(script, copied / "scripts" / script.name)
        (copied / "references").mkdir()
        for chart in RECIPES:
            shutil.copy2(SKILL / "references" / f"{chart}-plot.md", copied / "references" / f"{chart}-plot.md")
        for name in ("data-exploration.md", "statistical-analysis.md", "reference-to-code.md", "figure-workbench.md"):
            shutil.copy2(SKILL / "references" / name, copied / "references" / name)
        described = self.discovery(copied)
        for chart, route in described["focused_recipes"].items():
            self.assertEqual(Path(route["script"]).parent, (copied / "scripts").resolve())
            self.assertEqual(Path(route["doc"]).parent, (copied / "references").resolve())
        for route in described["workflow_tools"].values():
            self.assertEqual(Path(route["script"]).parent, (copied / "scripts").resolve())
            self.assertEqual(Path(route["doc"]).parent, (copied / "references").resolve())
        # At least one public focused CLI must work through its relocated path.
        result = self.cli(described["focused_recipes"]["interval"]["script"], "--describe-spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["chart"], "interval")


if __name__ == "__main__":
    unittest.main()
