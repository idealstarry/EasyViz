"""Evidence packets preserve inputs and cannot masquerade as semantic review."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/reference_packet.py"
loader = importlib.util.spec_from_file_location("easyviz_reference_packet", SCRIPT)
packet = importlib.util.module_from_spec(loader)
loader.loader.exec_module(packet)


class ReferencePacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-reference-packet-")
        self.root = Path(self.temp.name).resolve()
        # Binary fixture tests staging, not semantic reading or image decoding.
        self.reference = self.file("reference.png", b"\x89PNG\r\n\x1a\nreference bytes")
        self.data = self.file("user measurements.csv", b"unit,condition,value\nS1,A,2\nS1,B,4\n")
        self.caption = self.file("caption.txt", b"Visible intervals have an unspecified definition.\n")

    def tearDown(self):
        self.temp.cleanup()

    def file(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def reading(self):
        reading = packet.reading_template(packet.sha256(self.reference))
        reading["reader"].update(agent_id="fresh-reader", independence="independent", image_viewed=True)
        reading["reference"]["region"] = "panel B"
        reading["evidence"] = [
            {"id": "E1", "property": "layers.points", "description": "Visible points across two groups.", "state": "observed", "source": "reference", "uncertainty": ""},
            {"id": "E2", "property": "layers.interval", "description": "Intervals may show confidence bounds.", "state": "inferred", "source": "reference", "uncertainty": "The caption does not identify the interval statistic."},
            {"id": "E3", "property": "statistics.interval", "description": "Uncertainty definition is unknown.", "state": "unknown", "source": None, "uncertainty": "No definition was supplied."},
        ]
        reading["layers"] = [
            {"id": "points", "evidence_ids": ["E1"], "description": "Raw observed points", "required_data_meanings": ["condition", "measurement", "observation identifier"]},
            {"id": "intervals", "evidence_ids": ["E2", "E3"], "description": "Unknown summary intervals", "required_data_meanings": ["supplied endpoints or an established calculation"]},
        ]
        return reading

    def save_reading(self, reading):
        path = self.root / "reading.json"
        path.write_text(json.dumps(reading), encoding="utf-8")
        return path

    def build(self, name="packet", **kwargs):
        return packet.build(self.reference, [self.data], self.root / name, **kwargs)

    def test_new_packet_has_byte_identical_hashes_and_separate_reader_inputs(self):
        originals = {path: path.read_bytes() for path in (self.reference, self.data, self.caption)}
        manifest = self.build(captions=[self.caption])
        out = self.root / "packet"
        self.assertEqual(manifest["reader_input_ids"], ["caption-1", "reference"])
        for artifact in manifest["artifacts"]:
            staged = out / artifact["path"]
            self.assertEqual(staged.read_bytes(), originals[Path(artifact["original_path"])])
            self.assertEqual(packet.sha256(staged), artifact["sha256"])
            self.assertEqual(staged.stat().st_size, artifact["bytes"])
        self.assertFalse(any(path.suffix == ".csv" for path in (out / "reader-inputs").iterdir()))
        self.assertIn("Do not inspect data/", (out / "reader-request.md").read_text())
        self.assertNotIn(str(self.data), (out / "reader-request.md").read_text())
        for path, original in originals.items():
            self.assertEqual(path.read_bytes(), original)

    def test_packet_without_reading_claims_no_inspection_or_independence(self):
        manifest = self.build()
        self.assertFalse(manifest["reading"]["provided"])
        self.assertFalse(manifest["reading"]["schema_validated"])
        self.assertFalse(manifest["reading"]["reader_provenance"]["image_viewed"])
        self.assertFalse(manifest["reading"]["semantic_reading_verified"])
        self.assertFalse(manifest["reading"]["independence_verified"])
        plan = json.loads((self.root / "packet/implementation-plan.json").read_text())
        self.assertFalse(plan["execution_ready"])
        self.assertEqual(plan["layers"], [])
        self.assertIsNone(plan["layout"]["width_mm"])
        self.assertEqual(plan["statistical_layers"], [])
        self.assertEqual(plan["colors"], {})

    def test_reading_preserves_all_layers_but_adopts_no_unverified_statistics(self):
        reading = self.reading()
        manifest = self.build(reading_path=self.save_reading(reading), custom_script="implementation/panel.py")
        plan = json.loads((self.root / "packet/implementation-plan.json").read_text())
        self.assertEqual(plan["implementation"]["route"], "custom-script")
        self.assertEqual(plan["implementation"]["script"], "implementation/panel.py")
        self.assertEqual([layer["source_layer_id"] for layer in plan["layers"]], ["points", "intervals"])
        for layer in plan["layers"]:
            self.assertEqual(layer["status"], "unresolved")
            self.assertEqual(layer["field_mapping"], {})
            for key in ("transform", "artist", "backend"):
                self.assertIsNone(layer[key])
            self.assertEqual(layer["verification"], [])
        self.assertEqual(plan["evidence_decisions"][1]["evidence_state"], "inferred")
        self.assertTrue(all(item["adopted_requirement"] is None for item in plan["evidence_decisions"]))
        self.assertTrue(manifest["reading"]["schema_validated"])
        self.assertFalse(manifest["reading"]["semantic_reading_verified"])
        self.assertFalse(manifest["reading"]["independence_verified"])
        self.assertEqual(manifest["reading"]["reader_provenance"], reading["reader"])
        self.assertFalse((self.root / "packet/implementation/panel.py").exists())

    def test_main_agent_reading_is_accepted_and_recorded_truthfully(self):
        reading = self.reading()
        reading["reader"].update(agent_id="plotting-agent", independence="main-agent", limitations=["No independent delegate available."])
        manifest = self.build(reading_path=self.save_reading(reading))
        self.assertEqual(manifest["reading"]["reader_provenance"]["independence"], "main-agent")
        self.assertFalse(manifest["reading"]["independence_verified"])

    def test_mismatched_reference_and_unstaged_evidence_are_rejected(self):
        wrong_hash = self.reading()
        wrong_hash["reference"]["sha256"] = "0" * 64
        wrong_source = self.reading()
        wrong_source["evidence"][0]["source"] = "caption-1"
        for index, reading in enumerate((wrong_hash, wrong_source)):
            with self.assertRaises(packet.PacketError):
                self.build(f"bad-{index}", reading_path=self.save_reading(reading))
            self.assertFalse((self.root / f"bad-{index}").exists())

    def test_no_image_access_cannot_be_promoted_to_observed_image_evidence(self):
        reading = self.reading()
        reading["reader"].update(independence="main-agent", image_viewed=False)
        with self.assertRaisesRegex(packet.PacketError, "image access"):
            self.build(reading_path=self.save_reading(reading))
        reading["reader"]["independence"] = "independent"
        with self.assertRaisesRegex(packet.PacketError, "actual image access"):
            self.build(reading_path=self.save_reading(reading))
        self.assertFalse((self.root / "packet").exists())

    def test_invalid_schema_never_creates_a_packet(self):
        cases = []
        def changed(change):
            reading = self.reading()
            change(reading)
            cases.append(reading)
        changed(lambda value: value.update(statistics={"method": "guessed"}))
        changed(lambda value: value.update(version=True))
        changed(lambda value: value["reader"].update(image_viewed="yes"))
        changed(lambda value: value["evidence"][0].update(state="certain"))
        changed(lambda value: value["evidence"][1].update(uncertainty=""))
        changed(lambda value: value["evidence"][0].update(source=None))
        changed(lambda value: value["evidence"].append(copy.deepcopy(value["evidence"][0])))
        changed(lambda value: value["layers"][0].update(evidence_ids=["absent"]))
        changed(lambda value: value["layers"][0].update(evidence_ids=["E1", "E1"]))
        changed(lambda value: value["layers"][0].update(required_data_meanings="measurement"))
        for index, reading in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(packet.PacketError):
                    self.build(f"invalid-{index}", reading_path=self.save_reading(reading))
                self.assertFalse((self.root / f"invalid-{index}").exists())

    def test_duplicate_json_keys_and_nonfinite_constants_are_rejected(self):
        for index, content in enumerate(('{"version": 1, "version": 2}', '{"value": NaN}')):
            path = self.file(f"invalid-json-{index}.json", content.encode())
            with self.assertRaises(packet.PacketError):
                self.build(f"json-{index}", reading_path=path)
            self.assertFalse((self.root / f"json-{index}").exists())

    def test_existing_destination_and_dangling_symlink_survive(self):
        existing = self.root / "existing"
        existing.mkdir()
        marker = existing / "accepted.txt"
        marker.write_text("accepted")
        dangling = self.root / "dangling"
        dangling.symlink_to(self.root / "absent")
        for out in (existing, dangling, self.data):
            with self.assertRaises(packet.PacketError):
                packet.build(self.reference, [self.data], out)
        self.assertEqual(marker.read_text(), "accepted")
        self.assertTrue(dangling.is_symlink())

    def test_missing_data_duplicate_roles_and_unsafe_script_paths_fail_without_output(self):
        with self.assertRaisesRegex(packet.PacketError, "user-data"):
            packet.build(self.reference, [], self.root / "empty")
        with self.assertRaisesRegex(packet.PacketError, "once"):
            packet.build(self.reference, [self.reference], self.root / "duplicate")
        for index, path in enumerate(("../outside.py", "/tmp/outside.py", "notes.txt", "data/panel.py", "reader-inputs/panel.py", True)):
            with self.subTest(path=path):
                with self.assertRaises(packet.PacketError):
                    self.build(f"script-{index}", custom_script=path)
                self.assertFalse((self.root / f"script-{index}").exists())

    def test_input_change_during_staging_discards_partial_packet(self):
        real_copy = packet.shutil.copyfile
        original = self.data.read_bytes()
        def copy_then_change(source, target):
            result = real_copy(source, target)
            if source == self.data:
                self.data.write_bytes(original + b"S2,A,5\n")
            return result
        with patch.object(packet.shutil, "copyfile", side_effect=copy_then_change):
            with self.assertRaisesRegex(packet.PacketError, "changed while staging"):
                self.build()
        self.assertFalse((self.root / "packet").exists())

    def test_cli_runs_without_plotting_dependencies_and_never_reports_review_pass(self):
        result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--reference", str(self.reference), "--data", str(self.data), "--out", str(self.root / "cli")], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        self.assertFalse(status["image_reading_performed_by_tool"])
        self.assertFalse(status["supplied_reading_schema_validated"])
        self.assertFalse(status["visual_review_passed"])
        self.assertEqual(status["status"], "unresolved-scaffold")
        described = subprocess.run([sys.executable, "-S", str(SCRIPT), "--describe-reading"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(described.returncode, 0, described.stderr)
        self.assertEqual(json.loads(described.stdout)["version"], 1)

    def test_cli_supplied_reading_is_acknowledged_without_certifying_semantics(self):
        reading = self.save_reading(self.reading())
        result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--reference", str(self.reference),
                                 "--data", str(self.data), "--reading", str(reading),
                                 "--out", str(self.root / "with-reading")], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        self.assertTrue(status["supplied_reading_schema_validated"])
        self.assertFalse(status["image_reading_performed_by_tool"])
        self.assertFalse(status["semantic_reading_verified_by_tool"])
        self.assertIn("Review the supplied reading", status["next"])
        self.assertFalse(status["visual_review_passed"])


if __name__ == "__main__":
    unittest.main()
