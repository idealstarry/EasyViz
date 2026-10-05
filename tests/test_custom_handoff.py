"""Source-bound custom figures and complete declared auxiliary-input restoration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
from figure_workbench import FigureWorkbench, WorkbenchError
from figure_handoff import capture_inputs, write_receipt, migrate_receipt, HandoffError, canonical, digest
from apply_figure_requests import prepare_requests, record_requests, accept_attempt, restore_attempt

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="120mm" height="60mm" viewBox="0 0 240 120"><g id="real-data"><circle cx="70" cy="80" r="3" fill="#0072B2"/></g><text x="20" y="25">Condition</text></svg>'


class CustomHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-custom-handoff-")
        self.root = Path(self.temp.name).resolve()
        self.captures = {}
        self.spec = {"chart": "custom", "layout": {"width_mm": 120, "height_mm": 60}, "formats": ["svg"]}

    def tearDown(self):
        self.temp.cleanup()

    def make(self, name, *, svg=SVG, auxiliary=None, register=False, receipt=True):
        root = self.root / name
        root.mkdir()
        for filename, raw in {"source.csv": b"id,x,y\n001,1,2\n",
                          "plot.py": b'# Custom source retained, never executed.\nraise RuntimeError("MUST NOT EXECUTE")\n',
                          "spec.json": (json.dumps(self.spec) + "\n").encode()}.items():
            (root / filename).write_bytes(raw)
        inputs = {}
        for role, raw in (auxiliary or {}).items():
            path = root / (role + ".csv")
            path.write_bytes(raw)
            inputs[role] = path
        capture = capture_inputs(root, data_file=root / "source.csv", source_script=root / "plot.py",
            spec_file=root / "spec.json", auxiliary_inputs=inputs or None)
        self.captures[root] = capture
        self.assertEqual(json.loads(capture.read("spec_file")), self.spec)
        self.assertEqual(capture.read("data_file"), (root / "source.csv").read_bytes())
        (root / "panel.svg").write_bytes(svg)
        (root / "settings.json").write_text(json.dumps({"track": "create", "layout": self.spec["layout"]}))
        (root / "qa.json").write_text(json.dumps({"status": "pass", "valid_outputs": True,
            "exports": {"svg": {"sha256": hashlib.sha256(svg).hexdigest()}}}))
        receipt_record = None
        if receipt or register:
            receipt_record = write_receipt(root, capture=capture, formats=["svg"], track="create")
            if not receipt:
                (root / "handoff.json").unlink()
        if register:
            manifest = {"schema_version": 1, "version": receipt_record["version"], "input": receipt_record["input"],
                "panel": receipt_record["panel"], "elements": [{"id": "real-data", "role": "point-group", "label": "Condition",
                    "source_keys": [{"source_row": 1, "id": "001"}], "spec_paths": [], "editable": []}]}
            (root / "elements.json").write_text(json.dumps(manifest))
        return root

    def request(self, app, *, number=1, region=True):
        payload = {"version": app.state()["version"], "annotation_number": number,
            "instruction": "Move only the selected label; retain source values and final dimensions."}
        if region:
            payload["region_mm"] = {"x": 10, "y": 5, "width": 20, "height": 10}
        return app.change(payload)["request"]

    def test_unmapped_custom_receipt_records_and_restores_regions_without_inventing_ids(self):
        source = self.make("attempt-01")
        app = FigureWorkbench(source)
        state = app.state()
        self.assertFalse(state["manifest_valid"])
        self.assertTrue(state["provenance_valid"])
        self.assertTrue(state["source_current"])
        self.assertEqual(state["elements"], [])
        region, general = self.request(app), self.request(app, number=2, region=False)
        with self.assertRaisesRegex(WorkbenchError, "semantic element map"):
            prepare_requests(source, self.root / "automatic")
        self.assertFalse((self.root / "automatic").exists())
        target = self.make("attempt-02", svg=SVG.replace(b'y="25"', b'y="24"'))
        ids = [region["id"], general["id"]]
        record_requests(source, target, ids, changed_files=["spec.json"], validation="Actual bounded label-only source/export change reviewed.")
        self.assertEqual([item["status"] for item in app.ledger()["requests"]], ["applied", "applied"])
        accept_attempt(target, validation="Actual SVG label location and source records reviewed.")
        restored = self.root / "restored"
        restore_attempt(target, restored)
        for name in ("panel.svg",):
            self.assertEqual((target / name).read_bytes(), (restored / name).read_bytes())
        (target / "source.csv").unlink()
        (target / "plot.py").unlink()
        (target / "spec.json").unlink()
        current = FigureWorkbench(restored).state()
        self.assertTrue(current["provenance_valid"])
        self.assertFalse(current["manifest_valid"])
        self.assertTrue(current["source_current"])
        self.assertEqual(current["elements"], [])
        self.assertEqual(current["version"], state["version"] | {"figure_sha256": hashlib.sha256((restored / "panel.svg").read_bytes()).hexdigest()})

    def test_changed_auxiliary_source_blocks_saving_and_acceptance(self):
        source = self.make("attempt", auxiliary={"row_metadata": b"id,group\n001,A\n"})
        app = FigureWorkbench(source)
        old = app.state()
        self.assertTrue(old["source_current"])
        (source / "row_metadata.csv").write_text("id,group\n001,B\n")
        current = app.state()
        self.assertFalse(current["source_current"])
        self.assertFalse(current["source_versions"]["auxiliary_inputs:row_metadata"]["current"])
        with self.assertRaisesRegex(WorkbenchError, "source has changed"):
            self.request(app)
        with self.assertRaisesRegex(WorkbenchError, "available and current"):
            accept_attempt(source, validation="Changed metadata cannot validate old category colors.")
        self.assertFalse((source / "requests.json").exists())
        self.assertFalse((source / "accepted-snapshot").exists())

    def test_all_declared_auxiliary_files_are_snapshotted_and_rebound(self):
        source = self.make("attempt", auxiliary={"row_metadata": b"id,group\n001,A\n", "row_linkage": b"a,b,height\n1,2,0.5\n"}, register=True)
        app = FigureWorkbench(source)
        self.assertTrue(app.state()["manifest_valid"])
        original_version = app.state()["version"]
        self.request(app)
        accepted = accept_attempt(source, validation="Actual map, source dependencies and export inspected.")
        self.assertEqual(set(accepted["provenance"]["auxiliary_inputs"]), {"row_metadata", "row_linkage"})
        restored = self.root / "restored"
        restore_attempt(source, restored)
        for name in ("row_metadata.csv", "row_linkage.csv", "source.csv", "plot.py", "spec.json"):
            (source / name).unlink()
        state = FigureWorkbench(restored).state()
        self.assertEqual(state["version"], original_version)
        self.assertTrue(state["source_current"])
        self.assertTrue(state["manifest_valid"])
        for role, record in state["input"]["auxiliary_inputs"].items():
            self.assertTrue(Path(record["path"]).is_relative_to(restored))
            self.assertEqual(hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest(), record["sha256"])
            self.assertTrue(state["source_versions"]["auxiliary_inputs:" + role]["current"])
        self.assertEqual(FigureWorkbench(restored).ledger()["requests"][0]["status"], "superseded")

    def test_legacy_aligned_layer_bindings_are_also_checked_and_restored(self):
        source = self.make("attempt", auxiliary={"row_metadata": b"id,group\n001,A\n"}, register=True, receipt=False)
        manifest_path = source / "elements.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["input"]["aligned_layer_inputs"] = manifest["input"].pop("auxiliary_inputs")
        manifest["version"].pop("auxiliary_inputs_sha256")
        manifest_path.write_text(json.dumps(manifest))
        app = FigureWorkbench(source)
        self.assertTrue(app.state()["source_current"])
        self.assertIn("auxiliary_inputs_sha256", app.state()["version"])
        accepted = accept_attempt(source, validation="Legacy registered aligned-layer inputs inspected.")
        self.assertIn("row_metadata", accepted["provenance"]["auxiliary_inputs"])
        restored = self.root / "restored"
        restore_attempt(source, restored)
        (source / "row_metadata.csv").unlink()
        current = FigureWorkbench(restored).state()
        self.assertTrue(current["source_current"])
        self.assertEqual(current["input"]["aligned_layer_inputs"], current["input"]["auxiliary_inputs"])

    def test_unbound_region_fallback_can_save_but_cannot_claim_applied_or_accepted(self):
        source = self.make("external", receipt=False)
        app = FigureWorkbench(source)
        self.assertFalse(app.state()["manifest_valid"])
        self.assertFalse(app.state()["provenance_valid"])
        self.assertIsNone(app.state()["source_current"])
        item = self.request(app)
        target = self.make("target")
        with self.assertRaisesRegex(WorkbenchError, "source/spec/export"):
            record_requests(source, target, [item["id"]], changed_files=["spec.json"], validation="Unavailable provenance must remain unverified.")
        with self.assertRaisesRegex(WorkbenchError, "source/spec/export"):
            accept_attempt(source, validation="A region is not a source identity.")
        self.assertEqual(app.ledger()["requests"][0]["status"], "pending")

    def test_stale_receipt_or_export_hash_blocks_old_mapping_and_requests(self):
        for kind in ("svg", "export", "auxiliary-version", "conflicting-map"):
            with self.subTest(kind=kind):
                source = self.make("stale-" + kind, auxiliary={"row_metadata": b"id,group\n001,A\n"}, register=True)
                if kind == "svg":
                    (source / "panel.svg").write_bytes(SVG.replace(b'cy="80"', b'cy="79"'))
                else:
                    name = "elements.json" if kind == "conflicting-map" else "handoff.json"
                    record = json.loads((source / name).read_text())
                    if kind == "export":
                        record["exports"]["panel.svg"] = "0" * 64
                    else:
                        record["version"]["spec_sha256" if kind == "conflicting-map" else "auxiliary_inputs_sha256"] = "0" * 64
                    (source / name).write_text(json.dumps(record))
                app = FigureWorkbench(source)
                state = app.state()
                self.assertFalse(state["provenance_valid"])
                self.assertFalse(state["manifest_valid"])
                self.assertFalse(state["source_current"])
                self.assertTrue(state["handoff_error"])
                with self.assertRaises(WorkbenchError):
                    self.request(app)

    def test_record_rejects_changed_auxiliary_data_with_identical_primary_data(self):
        source = self.make("source", auxiliary={"row_metadata": b"id,group\n001,A\n"})
        app = FigureWorkbench(source)
        item = self.request(app)
        target = self.make("target", auxiliary={"row_metadata": b"id,group\n001,B\n"})
        with self.assertRaisesRegex(WorkbenchError, "unchanged primary and declared auxiliary"):
            record_requests(source, target, [item["id"]], changed_files=["spec.json"], validation="Cosmetic history cannot hide a changed data layer.")
        self.assertEqual(app.ledger()["requests"][0]["status"], "pending")
        self.assertFalse((target / "requests.json").exists())

    def test_restore_refuses_missing_or_corrupted_auxiliary_snapshot_before_output(self):
        for kind in ("missing", "tampered", "declaration"):
            with self.subTest(kind=kind):
                source = self.make("accepted-" + kind, auxiliary={"row_metadata": b"id,group\n001,A\n"})
                accepted = accept_attempt(source, validation="All declared sources inspected.")
                snapshot = source / "accepted-snapshot"
                name = accepted["provenance"]["auxiliary_inputs"]["row_metadata"]
                if kind == "missing":
                    (snapshot / name).unlink()
                elif kind == "tampered":
                    (snapshot / name).write_text("id,group\n001,WRONG\n")
                else:
                    accepted["provenance"]["auxiliary_inputs"] = {}
                    (snapshot / "acceptance.json").write_text(json.dumps(accepted))
                target = self.root / ("failed-" + kind)
                with self.assertRaises(WorkbenchError):
                    restore_attempt(source, target)
                self.assertFalse(target.exists())

    def test_missing_auxiliary_is_unverified_and_cannot_be_accepted(self):
        source = self.make("attempt", auxiliary={"row_metadata": b"id,group\n001,A\n"})
        (source / "row_metadata.csv").unlink()
        state = FigureWorkbench(source).state()
        self.assertIsNone(state["source_current"])
        self.assertFalse(state["source_versions"]["auxiliary_inputs:row_metadata"]["available"])
        with self.assertRaisesRegex(WorkbenchError, "available and current"):
            accept_attempt(source, validation="Missing secondary inputs prevent verified acceptance.")

    def test_malformed_auxiliary_bindings_disable_provenance(self):
        source = self.make("attempt")
        record = json.loads((source / "handoff.json").read_text())
        record["input"]["auxiliary_inputs"] = {"metadata": {"path": "../other.csv"}}
        (source / "handoff.json").write_text(json.dumps(record))
        current = FigureWorkbench(source).state()
        self.assertFalse(current["provenance_valid"])
        self.assertFalse(current["source_current"])
        self.assertEqual(current["input"], {})

    def test_auxiliary_version_cannot_silently_drop_its_entire_source_collection(self):
        source = self.make("attempt", auxiliary={"metadata": b"id,group\n001,A\n"})
        receipt = json.loads((source / "handoff.json").read_text())
        receipt["input"].pop("auxiliary_inputs")
        (source / "handoff.json").write_text(json.dumps(receipt))
        (source / "metadata.csv").unlink()
        current = FigureWorkbench(source).state()
        self.assertFalse(current["provenance_valid"])
        self.assertFalse(current["source_current"])
        self.assertIn("complete", current["handoff_error"])
        with self.assertRaises(WorkbenchError):
            accept_attempt(source, validation="A declared auxiliary version cannot omit its actual dependency records.")
        self.assertFalse((source / "accepted-snapshot").exists())

    def test_receipt_cannot_grant_unregistered_element_or_property_selection(self):
        source = self.make("attempt")
        app = FigureWorkbench(source)
        for selection in ({"element_id": "real-data"}, {"selector": {"role": "point-group"}}, {"property": "color", "value": "#FF0000"}):
            with self.subTest(selection=selection), self.assertRaises(WorkbenchError):
                app.change({"version": app.state()["version"], "instruction": "A receipt cannot infer an artist identity.", **selection})
        self.assertFalse((source / "requests.json").exists())

    def test_empty_real_registry_binds_sources_without_claiming_selectable_artists(self):
        source = self.make("attempt", register=True, receipt=False)
        manifest_path = source / "elements.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["elements"] = []
        manifest_path.write_text(json.dumps(manifest))
        current = FigureWorkbench(source).state()
        self.assertFalse(current["manifest_valid"])
        self.assertTrue(current["provenance_valid"])
        self.assertTrue(current["source_current"])
        self.assertEqual(current["elements"], [])
        self.assertIn("No selectable artists", current["selection_message"])

    def test_receipt_write_rejects_wrong_adopted_canvas_before_publication(self):
        source = self.make("attempt", receipt=False)
        wrong = dict(self.spec, layout={"width_mm": 120, "height_mm": 59})
        with self.assertRaisesRegex(HandoffError, "specification dimensions"):
            write_receipt(source, capture=self.captures[source], formats=["svg"], resolved_spec=wrong)
        self.assertFalse((source / "handoff.json").exists())

    def test_post_export_capture_cannot_restamp_consumption_on_old_output_bytes(self):
        source = self.make("attempt", receipt=False)
        (source / "source.csv").write_bytes(b"id,x,y\n001,100,200\n")
        with self.assertRaisesRegex(HandoffError, "before exports"):
            capture_inputs(source, data_file=source / "source.csv", source_script=source / "plot.py", spec_file=source / "spec.json")
        self.assertFalse((source / "handoff.json").exists())
        self.assertFalse(FigureWorkbench(source).state()["provenance_valid"])
        with self.assertRaises(WorkbenchError):
            accept_attempt(source, validation="Post-export hashing cannot establish consumption.")

    def test_current_files_must_match_all_actual_pre_export_captured_payloads(self):
        for filename in ("source.csv", "plot.py", "spec.json", "metadata.csv"):
            with self.subTest(source=filename):
                source = self.make("capture-" + filename, auxiliary={"metadata": b"id,group\n001,A\n"}, receipt=False)
                original = (source / filename).read_bytes()
                (source / filename).write_bytes(original + b"\n# Replaced after the figure's declared consumption.\n")
                with self.assertRaisesRegex(HandoffError, "changed after its bytes were captured"):
                    write_receipt(source, capture=self.captures[source], formats=["svg"])
                self.assertFalse((source / "handoff.json").exists())
                (source / filename).write_bytes(original)
                write_receipt(source, capture=self.captures[source], formats=["svg"])
                self.assertTrue(FigureWorkbench(source).state()["source_current"])

    def test_declared_consumption_proof_cannot_disagree_or_be_omitted(self):
        for mutation in ("absent", "primary", "auxiliary"):
            source = self.make(mutation, auxiliary={"metadata": b"id,group\n001,A\n"})
            record = json.loads((source / "handoff.json").read_text())
            if mutation == "absent":
                record.pop("consumption")
            elif mutation == "primary":
                record["consumption"]["source_sha256"]["data_file"] = "0" * 64
            else:
                record["consumption"]["auxiliary_sha256"] = {}
            (source / "handoff.json").write_text(json.dumps(record))
            state = FigureWorkbench(source).state()
            self.assertFalse(state["provenance_valid"])
            self.assertFalse(state["source_current"])
            with self.assertRaises(WorkbenchError):
                accept_attempt(source, validation="Incomplete declarations cannot establish accepted source identities.")

    def test_existing_explicit_consumed_and_adopted_evidence_cannot_be_ignored(self):
        for kind in ("top_data", "top_script", "source_bindings", "adopted_spec"):
            with self.subTest(kind=kind):
                source = self.make(kind, receipt=False)
                settings = json.loads((source / "settings.json").read_text())
                if kind == "top_data":
                    settings["input_sha256"] = "0" * 64
                elif kind == "top_script":
                    settings["source_script_sha256"] = "0" * 64
                elif kind == "source_bindings":
                    settings["source_bindings"] = {"data_file": {"path": str(source / "source.csv"), "sha256": "0" * 64}}
                else:
                    settings["spec"] = {**self.spec, "labels": {"y": "A different adopted measurement"}}
                (source / "settings.json").write_text(json.dumps(settings))
                with self.assertRaisesRegex(HandoffError, "contradict"):
                    write_receipt(source, capture=self.captures[source], formats=["svg"])
                self.assertFalse((source / "handoff.json").exists())

    def test_restored_current_source_bindings_rebase_primary_and_declared_auxiliary_paths(self):
        source = self.make("bound-settings", auxiliary={"metadata": b"id,group\n001,A\n"}, receipt=False)
        capture = self.captures[source]
        settings = json.loads((source / "settings.json").read_text())
        settings["source_bindings"] = {field: {"path": str(capture.paths[field]), "sha256": digest(capture.read(field))}
                                       for field in ("data_file", "spec_file", "source_script")}
        settings["source_bindings"]["metadata"] = {"path": str(source / "metadata.csv"), "sha256": digest(capture.read_auxiliary("metadata"))}
        (source / "settings.json").write_text(json.dumps(settings))
        write_receipt(source, capture=capture, formats=["svg"])
        accept_attempt(source, validation="Consumed byte payloads, bound settings and matching actual SVG verified.")
        restored = self.root / "rebound-settings"
        restore_attempt(source, restored)
        for name in ("source.csv", "plot.py", "spec.json", "metadata.csv"):
            (source / name).unlink()
        state = FigureWorkbench(restored).state()
        self.assertTrue(state["source_current"])
        updated = json.loads((restored / "settings.json").read_text())["source_bindings"]
        for role, record in updated.items():
            self.assertTrue(Path(record["path"]).is_relative_to(restored), role)
            self.assertEqual(digest(Path(record["path"]).read_bytes()), record["sha256"])

    def test_receipt_publication_failure_preserves_previous_complete_receipt(self):
        from unittest.mock import patch
        source = self.make("atomic")
        original = (source / "handoff.json").read_bytes()
        with patch("os.replace", side_effect=OSError("Injected receipt publication failure")):
            with self.assertRaisesRegex(OSError, "publication failure"):
                write_receipt(source, capture=self.captures[source], formats=["svg"])
        self.assertEqual((source / "handoff.json").read_bytes(), original)
        self.assertEqual(list(source.glob(".handoff-*.json")), [])
        self.assertTrue(FigureWorkbench(source).state()["source_current"])

    def test_legacy_migration_refuses_replaced_primary_or_auxiliary_consumed_inputs(self):
        import shutil
        repository = SCRIPTS.parents[2]
        original = repository / "evals/create-purpose-overhaul-v0.4.4/fresh-run/with-skill/attempt-02"
        for filename in ("source.csv", "input-contract.json", "plot.py", "spec.json"):
            with self.subTest(source=filename):
                source = self.root / ("legacy-" + filename)
                source.mkdir()
                for name in ("panel.svg", "panel.pdf", "panel.png", "source.csv", "plot.py", "spec.json", "qa.json", "settings.json", "input-contract.json"):
                    shutil.copy2(original / name, source / name)
                (source / filename).write_bytes((source / filename).read_bytes() + b"\n ")
                with self.assertRaisesRegex(HandoffError, "contradict"):
                    migrate_receipt(source, data_file=source / "source.csv", source_script=source / "plot.py",
                        spec_file=source / "spec.json", formats=["svg", "pdf", "png"],
                        auxiliary_inputs={"source_contract": source / "input-contract.json"},
                        auxiliary_claims={"source_contract": {"path": "/input/contract_file", "sha256": "/version/contract_sha256"}})
                self.assertFalse((source / "handoff.json").exists())

    def test_incomplete_legacy_evidence_remains_note_only(self):
        source = self.make("legacy-no-consumption", receipt=False)
        with self.assertRaisesRegex(HandoffError, "evidence is missing"):
            migrate_receipt(source, data_file=source / "source.csv", source_script=source / "plot.py", spec_file=source / "spec.json", formats=["svg"])
        self.assertFalse((source / "handoff.json").exists())
        self.request(FigureWorkbench(source))
        with self.assertRaises(WorkbenchError):
            accept_attempt(source, validation="Unknown consumption requires a fresh captured render.")

    def test_actual_three_format_custom_export_copy_keeps_all_bytes_and_frozen_trial(self):
        import shutil
        repository = SCRIPTS.parents[2]
        original = repository / "evals/create-purpose-overhaul-v0.4.4/fresh-run/with-skill/attempt-02"
        original_hashes = {name: hashlib.sha256((original / name).read_bytes()).hexdigest() for name in (
            "panel.svg", "panel.pdf", "panel.png", "source.csv", "plot.py", "spec.json")}
        source = self.root / "actual-source"
        source.mkdir()
        for name in (*original_hashes, "qa.json", "settings.json", "input-contract.json"):
            shutil.copy2(original / name, source / name)
        receipt = migrate_receipt(source, data_file=source / "source.csv", source_script=source / "plot.py",
            spec_file=source / "spec.json", formats=["svg", "pdf", "png"],
            auxiliary_inputs={"source_contract": source / "input-contract.json"},
            auxiliary_claims={"source_contract": {"path": "/input/contract_file", "sha256": "/version/contract_sha256"}}, track="create")
        self.assertEqual(set(receipt["exports"]), {"panel.svg", "panel.pdf", "panel.png"})
        self.assertEqual(receipt["consumption"]["kind"], "legacy-recorded-evidence")
        app = FigureWorkbench(source)
        self.assertFalse(app.state()["manifest_valid"])
        self.assertTrue(app.state()["source_current"])
        self.request(app)
        accept_attempt(source, validation="Existing independently reviewed real PNG/PDF/SVG copied for source handoff eligibility only.")
        restored = self.root / "actual-restored"
        restore_attempt(source, restored)
        for name in ("panel.svg", "panel.pdf", "panel.png"):
            self.assertEqual(hashlib.sha256((restored / name).read_bytes()).hexdigest(), original_hashes[name])
        shutil.rmtree(source)
        self.assertTrue(FigureWorkbench(restored).state()["source_current"])
        settings = json.loads((restored / "settings.json").read_text())
        self.assertTrue(Path(settings["input"]["contract_file"]).is_relative_to(restored))
        self.assertTrue(Path(settings["input"]["contract_file"]).is_file())
        self.assertEqual(original_hashes, {name: hashlib.sha256((original / name).read_bytes()).hexdigest() for name in original_hashes})


if __name__ == "__main__":
    unittest.main()
