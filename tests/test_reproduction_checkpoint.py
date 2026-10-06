"""A Reproduce adoption checkpoint makes omissions actionable without certifying quality."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
def load(name):
    loader = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module

packet, checkpoint = load("reference_packet"), load("reproduction_checkpoint")


class ReproductionCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-adoption-")
        self.root = Path(self.temp.name)
        self.reference = self.root / "reference.png"
        self.reference.write_bytes(b"reference bytes; fixture does not claim image semantics")
        self.data = self.root / "data.csv"
        self.data.write_text("id,group,value\n001,A,2\n002,B,3\n")
        self.reading = packet.reading_template(packet.sha256(self.reference))
        self.reading["reader"].update(agent_id="reader", independence="main-agent", image_viewed=True,
                                      limitations=["Self-reading fixture, not an actual visual review"])
        self.reading["evidence"] = [
            {"id": "E1", "property": "layers.points", "description": "Two groups of points", "state": "observed", "source": "reference", "uncertainty": ""},
            {"id": "E2", "property": "statistics.interval", "description": "Visible uncertainty marks", "state": "unknown", "source": None, "uncertainty": "Are these SD, SEM or confidence intervals?"},
        ]
        self.reading["layers"] = [
            {"id": "points", "description": "Raw points", "evidence_ids": ["E1"], "required_data_meanings": ["measurement", "group"]},
            {"id": "intervals", "description": "Unknown intervals", "evidence_ids": ["E2"], "required_data_meanings": ["supported interval definition"]},
        ]
        reading_file = self.root / "reading.json"
        reading_file.write_text(json.dumps(self.reading))
        self.out = self.root / "packet"
        packet.build(self.reference, [self.data], self.out, reading_path=reading_file, custom_script="implementation/panel.py")
        self.plan_file = self.out / "implementation-plan.json"
        self.plan = json.loads(self.plan_file.read_text())
        self.plan["layout"].update(width_mm=88, height_mm=66, font="DejaVu Sans", typography_pt={"axes": 8, "ticks": 8})
        self.plan["implementation"]["selection_reason"] = "Implement both observed coordinate relationships explicitly"
        self.plan["adoption_contract"]["relationships"] = [{
            "id": "group-position", "property": "coordinates.category-order", "evidence_ids": ["E1"],
            "behavior": "adapt", "adopted_value": "Retain group lanes; use the actual user category order",
            "rationale": "New data may have a different category count",
        }]
        self.activate("points")
        interval = self.plan["layers"][1]
        interval["adoption"].update(decision="unresolved", priority="required", reason="No uncertainty definition was supplied")

    def tearDown(self):
        self.temp.cleanup()

    def activate(self, identity):
        layer = next(item for item in self.plan["layers"] if item["source_layer_id"] == identity)
        layer.update(status="implemented", data_artifacts=["data-1"], field_mapping={"y": "value", "group": "group"},
                     transform="none; all records retained", artist="scatter collection", backend="matplotlib Axes.scatter in data coordinates")
        layer["adoption"].update(decision="preserve", priority="required", reason="Preserve source measurement marks")

    def run_check(self):
        self.plan_file.write_text(json.dumps(self.plan))
        return checkpoint.check(self.out)

    def test_required_unknown_interval_allows_raw_layer_but_blocks_delivery(self):
        report = self.run_check()
        self.assertTrue(report["can_render_supported_layers"])
        self.assertEqual(report["status"], "partial_adoption")
        self.assertTrue(report["delivery_blocked_by_adoption"])
        self.assertEqual(report["active_layers"], ["points"])
        self.assertEqual(report["required_unresolved_or_omitted_layers"], ["intervals"])
        self.assertEqual(report["open_questions"][0]["question"], "Are these SD, SEM or confidence intervals?")
        self.assertFalse(report["ready_for_delivery"])
        self.assertFalse(report["visual_review_passed"])

    def test_unknown_layer_cannot_be_activated_without_resolution(self):
        self.activate("intervals")
        report = self.run_check()
        self.assertFalse(report["can_render_supported_layers"])
        self.assertIn("unresolved-layer", [item["code"] for item in report["errors"]])

    def test_explicit_definition_can_resolve_a_record_but_is_not_semantic_approval(self):
        self.activate("intervals")
        self.plan["adoption_contract"]["open_items"][0].update(
            state="resolved", resolution={"source": "user-decision", "description": "User specifies sample SD for this adapted layer; verify design separately"})
        report = self.run_check()
        self.assertTrue(report["can_render_supported_layers"])
        self.assertEqual(report["status"], "adoption_complete")
        self.assertFalse(report["ready_for_delivery"])
        self.assertFalse(report["visual_review_passed"])

    def test_required_omission_is_not_complete_even_with_a_reason(self):
        self.plan["layers"][1]["status"] = "omitted"
        self.plan["layers"][1]["adoption"].update(decision="omit", reason="Appearance is not enough to establish the statistic")
        question = self.plan["adoption_contract"]["open_items"][0]
        question.update(state="not-required", blocking="none", resolution={"source": "user-decision", "description": "Statistical layer not calculated"})
        report = self.run_check()
        self.assertTrue(report["delivery_blocked_by_adoption"])
        self.assertEqual(report["required_unresolved_or_omitted_layers"], ["intervals"])

    def test_deleted_layer_or_uncertainty_cannot_disappear_into_a_pass(self):
        for kind in ("layer", "question"):
            original = copy.deepcopy(self.plan)
            if kind == "layer": self.plan["layers"].pop()
            else: self.plan["adoption_contract"]["open_items"] = []
            report = self.run_check()
            self.assertFalse(report["can_render_supported_layers"])
            self.assertIn("layer-coverage" if kind == "layer" else "uncertainty-coverage", [item["code"] for item in report["errors"]])
            self.plan = original

    def test_adoption_needs_actual_layout_and_relationship_decisions(self):
        self.plan["layout"]["width_mm"] = True
        self.plan["layout"]["typography_pt"] = {"ticks": 0}
        self.plan["adoption_contract"]["relationships"] = []
        report = self.run_check()
        codes = [item["code"] for item in report["errors"]]
        self.assertTrue({"physical-layout", "typography", "visual-relationships"} <= set(codes))

    def test_wrong_image_or_source_bindings_fail(self):
        self.plan["adoption_contract"]["reference_sha256"] = "0" * 64
        self.plan["layers"][0]["data_artifacts"] = ["paper-source-not-staged"]
        report = self.run_check()
        self.assertTrue({"reference-identity", "layer-source"} <= {item["code"] for item in report["errors"]})

    def test_changed_staged_input_is_rejected_without_mutating_plan(self):
        self.plan_file.write_text(json.dumps(self.plan))
        before = self.plan_file.read_bytes()
        (self.out / "data/data-1-data.csv").write_text("id,value\nchanged,200\n")
        with self.assertRaisesRegex(checkpoint.PacketError, "Staged input changed"):
            checkpoint.check(self.out)
        self.assertEqual(before, self.plan_file.read_bytes())

    def test_unsafe_or_symlink_plan_path_is_rejected(self):
        (self.out / "linked-plan.json").symlink_to(self.plan_file)
        for path in ("../reading.json", str(self.plan_file), "linked-plan.json"):
            with self.subTest(path=path), self.assertRaises(checkpoint.PacketError):
                checkpoint.check(self.out, path)

    def test_staging_without_actual_reading_cannot_become_adopted(self):
        fresh = self.root / "no-reading"
        packet.build(self.reference, [self.data], fresh)
        with self.assertRaisesRegex(checkpoint.PacketError, "actual saved reading"):
            checkpoint.check(fresh)

    def test_malformed_json_roots_and_unhashable_ids_fail_with_controlled_cli_errors(self):
        command = [sys.executable, "-S", str(SCRIPTS / "reproduction_checkpoint.py"), "--packet", str(self.out)]
        manifest = self.out / "packet.json"
        before = manifest.read_text()
        for content in ("[]", "null"):
            manifest.write_text(content)
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
        manifest.write_text(before)
        self.plan["adoption_contract"]["open_items"][0]["evidence_id"] = ["E2"]
        self.plan_file.write_text(json.dumps(self.plan))
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_decision_types_report_inconsistent_adoption_without_tracebacks(self):
        self.plan["layers"][0]["status"] = []
        self.plan["layers"][0]["adoption"]["priority"] = {}
        self.plan["implementation"]["route"] = []
        self.plan["adoption_contract"]["relationships"][0]["behavior"] = []
        report = self.run_check()
        self.assertEqual(report["status"], "needs_adoption")
        self.assertFalse(report["can_render_supported_layers"])

    def test_duplicate_open_items_or_unknown_resolution_source_rejected(self):
        self.plan["adoption_contract"]["open_items"].append(copy.deepcopy(self.plan["adoption_contract"]["open_items"][0]))
        with self.assertRaisesRegex(checkpoint.PacketError, "uniquely"):
            self.run_check()
        self.plan["adoption_contract"]["open_items"].pop()
        self.plan["adoption_contract"]["open_items"][0].update(state="resolved", resolution={"source": "guessed-method", "description": "Guess SEM"})
        report = self.run_check()
        self.assertIn("question-resolution", [item["code"] for item in report["errors"]])

    def test_cli_without_scientific_dependencies_writes_once_and_reports_partial_honestly(self):
        self.plan_file.write_text(json.dumps(self.plan))
        out = self.root / "checkpoint.json"
        command = [sys.executable, "-S", str(SCRIPTS / "reproduction_checkpoint.py"), "--packet", str(self.out), "--out", str(out)]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "partial_adoption")
        before = out.read_bytes()
        rerun = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(rerun.returncode, 2)
        self.assertEqual(before, out.read_bytes())
        described = subprocess.run([sys.executable, "-S", str(SCRIPTS / "reproduction_checkpoint.py"), "--describe-contract"], text=True, capture_output=True)
        self.assertEqual(described.returncode, 0, described.stderr)


if __name__ == "__main__":
    unittest.main()
