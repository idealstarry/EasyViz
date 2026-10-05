"""Version-bound cosmetic edits, truthful history and complete accepted restore."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
loader = importlib.util.spec_from_file_location("easyviz_apply_requests", SCRIPTS / "apply_figure_requests.py")
helper = importlib.util.module_from_spec(loader)
loader.loader.exec_module(helper)

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="120mm" height="90mm" viewBox="0 0 240 180"><g id="group-A"><circle cx="70" cy="80" r="8" fill="#2581B9"/></g><g id="key-A"><text x="170" y="40">A</text></g></svg>'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ApplyRequestsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-request-apply-")
        self.root = Path(self.temp.name).resolve()
        self.attempt = self.root / "attempt-01"
        self.spec = {"chart":"scatter","fields":{"x":"x","y":"y","group":"group"},"order":{"group":["A","B"]},"options":{"alpha":.85,"point_area_pt2":12},"layout":{"width_mm":120,"height_mm":90,"font_size_pt":8,"line_width_pt":.6},"formats":["svg","pdf","png"]}
        self.make_attempt(self.attempt, self.spec)
        self.app = helper.FigureWorkbench(self.attempt)
        self.state = self.app.state()

    def tearDown(self):
        self.temp.cleanup()

    def make_attempt(self, path, spec, *, svg=SVG):
        path.mkdir()
        spec_bytes=(json.dumps(spec,sort_keys=True)+"\n").encode()
        source=b'# A custom plotting script is provenance only, never executed by the helper.\nraise RuntimeError("MUST NOT EXECUTE")\n'
        data=b'x,y,group\n1,2,A\n2,3,A\n3,4,B\n'
        for name,content in {"plot-spec.json":spec_bytes,"plot.py":source,"source.csv":data,"panel.svg":svg,"panel.pdf":b"%PDF immutable paired export","panel.png":b"immutable paired PNG"}.items():
            (path/name).write_bytes(content)
        elements=[{"id":"group-A","role":"point-group","label":"A","source_keys":[{"group":"A","records":[1,2]}],"spec_paths":["/colors/A","/options/alpha"],"editable":{"color":"/colors/A","alpha":"/options/alpha"}}, {"id":"key-A","role":"legend-key","label":"A","source_keys":[{"category":"A"}],"spec_paths":["/colors/A"],"editable":["color"]}]
        manifest={"schema_version":1,"version":{"figure_sha256":digest(svg),"spec_sha256":digest(json.dumps(spec,sort_keys=True,separators=(",",":")).encode()),"input_sha256":digest(data),"source_script_sha256":digest(source),"resolved_colors_sha256":digest(json.dumps({"A":"#2581B9","B":"#E47751"},sort_keys=True,separators=(",",":")).encode())},"input":{"data_file":str(path/"source.csv"),"spec_file":str(path/"plot-spec.json"),"source_script":str(path/"plot.py"),"supplied_spec_sha256":digest(spec_bytes)},"panel":{"width_mm":120,"height_mm":90},"elements":elements}
        (path/"elements.json").write_text(json.dumps(manifest))
        (path/"settings.json").write_text(json.dumps({"resolved_colors":{"A":"#2581B9","B":"#E47751"},"track":"create"}))
        (path/"qa.json").write_text(json.dumps({"status":"pass","valid_outputs":True}))

    def request(self, **extra):
        payload={"version":self.state["version"],"selector":{"category":"A"},"property":"color","value":"#AA11CC","instruction":"Use purple for category A while preserving data and area.",**extra}
        return self.app.change(payload)["request"]

    def test_prepare_bulk_color_changes_complete_mapping_and_only_cosmetic_spec(self):
        item=self.request()
        originals={name:(self.attempt/name).read_bytes() for name in ("panel.svg","panel.pdf","panel.png","plot-spec.json","plot.py","source.csv")}
        out=self.root/"attempt-02"
        plan=helper.prepare_requests(self.attempt,out,[item["id"]])
        edited=json.loads((out/"plot-spec.json").read_text())
        self.assertEqual(edited["colors"],{"A":"#AA11CC","B":"#E47751"})
        self.assertEqual({key:value for key,value in edited.items() if key!="colors"},self.spec)
        self.assertEqual(plan["patches"][0]["affected_element_ids"],["group-A","key-A"])
        self.assertFalse(plan["rendered"])
        self.assertFalse((out/"panel.svg").exists())
        self.assertEqual(self.app.ledger()["requests"][0]["status"],"pending")
        self.assertEqual(self.app.ledger()["history"][-1]["action"],"prepared")
        for name,content in originals.items(): self.assertEqual((self.attempt/name).read_bytes(),content)

    def test_prepare_mapped_stroke_role_changes_actual_target_without_touching_global_width(self):
        spec = {**self.spec, "line_roles": {"data": {"line_width_pt": .85, "color": "#2581B9"},
                                          "axis": {"line_width_pt": .55}}}
        attempt = self.root / "stroke-attempt"
        self.make_attempt(attempt, spec)
        manifest_path = attempt / "elements.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["elements"][0].update(role="fit-line", spec_paths=["/line_roles/data/line_width_pt"],
                                        editable={"linewidth": "/line_roles/data/line_width_pt"})
        manifest_path.write_text(json.dumps(manifest))
        app = helper.FigureWorkbench(attempt)
        item = app.change({"version": app.state()["version"], "element_id": "group-A",
                           "property": "linewidth", "value": 1.1,
                           "instruction": "Increase this fitted line while retaining observations and axes."})["request"]
        output = self.root / "stroke-edited"
        helper.prepare_requests(attempt, output, [item["id"]])
        edited = json.loads((output / "plot-spec.json").read_text())
        expected = copy.deepcopy(spec)
        expected["line_roles"]["data"]["line_width_pt"] = 1.1
        self.assertEqual(edited, expected)
        self.assertFalse((output / "panel.svg").exists(), "Preparing a source edit does not claim an Agent rerender")
        for prop, path in (("color", "/line_roles/unknown/color"),
                           ("linewidth", "/line_roles/data/max_area_pt2"),
                           ("linestyle", "/line_roles/axis/linestyle")):
            self.assertFalse(helper.compatible(prop, path))

    def test_unbound_or_tampered_palette_cannot_change_unselected_category(self):
        item=self.request()
        manifest_path=self.attempt/"elements.json"
        original=manifest_path.read_bytes()
        manifest=json.loads(original)
        del manifest["version"]["resolved_colors_sha256"]
        manifest_path.write_text(json.dumps(manifest))
        state=self.app.state()
        self.app.write_ledger({"schema_version":1,"requests":[]})
        legacy=self.app.change({"version":state["version"],"selector":{"category":"A"},"property":"color","value":"#AA11CC","instruction":"Change A only."})["request"]
        with self.assertRaisesRegex(helper.WorkbenchError,"resolved-colors hash"):
            helper.prepare_requests(self.attempt,self.root/"unbound",[legacy["id"]])
        self.assertFalse((self.root/"unbound").exists())
        manifest_path.write_bytes(original)
        self.app.write_ledger({"schema_version":1,"requests":[]})
        current=self.request()
        settings_path=self.attempt/"settings.json"
        settings=json.loads(settings_path.read_text())
        settings["resolved_colors"]["B"]="#11CC00"
        settings_path.write_text(json.dumps(settings))
        self.assertFalse(self.app.state()["source_current"])
        with self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.root/"tampered-palette",[current["id"]])
        self.assertFalse((self.root/"tampered-palette").exists())

    def test_stale_source_spec_data_export_and_request_versions_reject_before_output(self):
        item=self.request()
        for name in ("plot.py","plot-spec.json","source.csv","panel.svg"):
            path=self.attempt/name
            original=path.read_bytes()
            path.write_bytes(original+b"\nchanged")
            out=self.root/"refused"
            with self.subTest(name=name), self.assertRaises(helper.WorkbenchError):
                helper.prepare_requests(self.attempt,out,[item["id"]])
            self.assertFalse(out.exists())
            path.write_bytes(original)
        ledger=self.app.ledger();ledger["requests"][0]["version"]={"figure_sha256":"stale"};self.app.write_ledger(ledger)
        with self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.root/"stale")

    def test_restricted_properties_ambiguous_paths_and_tampered_identity_never_apply(self):
        item=self.request()
        original=self.app.ledger()
        malicious=[{"property":"position","value":[1,2]}, {"property":"point_area_pt2","value":200}, {"property":"color","value":"url(https://example.com/x)"}, {"property":"alpha","value":2}, {"spec_path":"/fields/x"}, {"property":"linewidth","value":float("inf")}]
        for index,change in enumerate(malicious):
            ledger=copy.deepcopy(original);ledger["requests"][0].update(change)
            # JSON's nonfinite input is rejected by the shared strict reader.
            (self.attempt/"requests.json").write_text(json.dumps(ledger))
            out=self.root/f"refused-{index}"
            with self.subTest(change=change), self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,out,[item["id"]])
            self.assertFalse(out.exists())
        ledger=copy.deepcopy(original);ledger["requests"][0]["elements"][0]["source_keys"]=[{"group":"B"}];self.app.write_ledger(ledger)
        with self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.root/"tampered",[item["id"]])
        self.app.write_ledger(original)
        with self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.root/"custom-render",[item["id"]],render=True)
        self.assertFalse((self.root/"custom-render").exists())

    def test_pointer_escaping_and_numeric_values_are_finite_and_restricted(self):
        self.assertEqual(helper.pointer_parts("/colors/A~1B~0C"),["colors","A/B~C"])
        spec={"colors":{"A/B~C":"#2581B9"}}
        helper.set_pointer(spec,"/colors/A~1B~0C","#112233")
        self.assertEqual(spec["colors"]["A/B~C"],"#112233")
        for path in ("palette.colors.A","/colors/A~2B","/colors//A"):
            with self.assertRaises(helper.WorkbenchError): helper.pointer_parts(path)
        for value in (True,None,[],"0.8 pt","NaN","Infinity",-1,21):
            with self.subTest(value=value), self.assertRaises(helper.WorkbenchError): helper.cosmetic_value("linewidth",value)
        self.assertEqual(helper.cosmetic_value("alpha","0"),0)
        self.assertEqual(helper.cosmetic_value("alpha",1),1)
        self.assertFalse(helper.compatible("color","/fields/x"))
        self.assertFalse(helper.compatible("linewidth","/options/max_area_pt2"))

    def test_agent_application_records_applied_superseded_and_failed_qa_rejects(self):
        first=self.request()
        second=self.request(value="#112233")
        target=self.root/"attempt-02"
        self.make_attempt(target,{**self.spec,"colors":{"A":"#112233","B":"#E47751"}},svg=SVG.replace(b"#2581B9",b"#112233"))
        (target/"qa.json").write_text('{"status":"needs_revision"}')
        with self.assertRaises(helper.WorkbenchError): helper.record_requests(self.attempt,target,[first["id"],second["id"]],changed_files=["plot-spec.json"],validation="Inspected final dimensions and marks.")
        (target/"qa.json").write_text('{"status":"pass"}')
        target_app=helper.FigureWorkbench(target)
        target_item=target_app.change({"version":target_app.state()["version"],"element_id":"group-A","instruction":"Inspect this group in the new attempt."})["request"]
        event=helper.record_requests(self.attempt,target,[first["id"],second["id"]],changed_files=["plot-spec.json"],validation="Inspected final dimensions and marks.",superseded_ids=[first["id"]])
        records=self.app.ledger()["requests"]
        self.assertEqual([record["status"] for record in records],["superseded","applied"])
        self.assertEqual(records[0]["superseded_by"],[second["id"]])
        self.assertEqual(records[1]["result"]["target_version"],helper.FigureWorkbench(target).state()["version"])
        self.assertEqual(event["changed_files"],["plot-spec.json"])
        self.assertEqual(helper.FigureWorkbench(target).ledger()["history"][-1]["action"],"applied")
        self.assertEqual(helper.FigureWorkbench(target).ledger()["requests"][-1]["id"],target_item["id"],"Recording must preserve the target's own newer instructions")
        with self.assertRaises(helper.WorkbenchError): self.app.change({"version":self.state["version"],"request_id":second["id"]},undo=True)

    def test_accepted_restore_restores_source_spec_input_and_matching_exports(self):
        acceptance=helper.accept_attempt(self.attempt,validation="SVG/PNG inspected and PDF dimensions verified.")
        expected={name:(self.attempt/name).read_bytes() for name in ("plot.py","plot-spec.json","source.csv","panel.svg","panel.pdf","panel.png")}
        (self.attempt/"plot.py").write_text("changed plotting source")
        (self.attempt/"plot-spec.json").write_text('{"changed":true}')
        out=self.root/"restored-attempt"
        event=helper.restore_attempt(self.attempt,out)
        for original,restored in (("plot.py","plot-source.py"),("plot-spec.json","plot-spec.json"),("source.csv","source-data.csv"),("panel.svg","panel.svg"),("panel.pdf","panel.pdf"),("panel.png","panel.png")):
            self.assertEqual((out/restored).read_bytes(),expected[original])
        restored=helper.FigureWorkbench(out).state()
        self.assertTrue(restored["source_current"])
        self.assertEqual(restored["version"],acceptance["version"])
        self.assertEqual(restored["input"]["source_script"],str(out/"plot-source.py"))
        self.assertEqual(event["action"],"restored")
        self.assertIn("No author script was executed",event["note"])
        with self.assertRaises(helper.WorkbenchError): helper.restore_attempt(self.attempt,out)

    def test_record_target_publication_failure_restores_both_ledgers_and_retry_keeps_requests(self):
        item = self.request(annotation_number=1)
        target = self.root / "attempt-02"
        self.make_attempt(target, {**self.spec, "colors": {"A": "#AA11CC", "B": "#E47751"}},
                          svg=SVG.replace(b"#2581B9", b"#AA11CC"))
        other = helper.FigureWorkbench(target)
        pending = other.change({"version": other.state()["version"], "element_id": "group-A",
                                "instruction": "Keep this new attempt's own instruction.", "annotation_number": 2})["request"]
        before = {owner.root: owner.ledger_bytes() for owner in (self.app, other)}
        publish = helper.FigureWorkbench._replace_ledger_bytes
        failed = False
        def fail_after_target_replacement(owner, raw):
            nonlocal failed
            publish(owner, raw)
            if owner.root == target and not failed:
                failed = True
                raise OSError("Injected target write failure after atomic replacement")
        with patch.object(helper.FigureWorkbench, "_replace_ledger_bytes", new=fail_after_target_replacement):
            with self.assertRaisesRegex(OSError, "Injected target write failure"):
                helper.record_requests(self.attempt, target, [item["id"]], changed_files=["plot-spec.json"],
                                       validation="Reviewed target exports at the adopted canvas.")
        for owner in (self.app, other):
            self.assertEqual(owner.ledger_bytes(), before[owner.root])
        self.assertEqual(self.app.ledger()["requests"][0]["status"], "pending")
        event = helper.record_requests(self.attempt, target, [item["id"]], changed_files=["plot-spec.json"],
                                       validation="Reviewed target exports at the adopted canvas.")
        self.assertEqual(self.app.ledger()["requests"][0]["status"], "applied")
        self.assertEqual([record["id"] for record in other.ledger()["requests"]], [item["id"], pending["id"]])
        for owner in (self.app, other):
            self.assertEqual([entry["id"] for entry in owner.ledger()["history"]], [event["id"]])
        self.assertEqual(list(self.attempt.glob(".requests-*.tmp")), [])
        self.assertEqual(list(target.glob(".requests-*.tmp")), [])

    def test_record_detects_target_request_saved_after_planning_before_commit(self):
        item = self.request()
        target = self.root / "attempt-02"
        self.make_attempt(target, self.spec)
        other = helper.FigureWorkbench(target)
        serialize = helper.FigureWorkbench.ledger_serialized
        saved = []
        def save_new_target_request(owner, ledger):
            if owner.root == target and not saved:
                saved.append(None)
                saved[0] = other.change({"version": other.state()["version"], "element_id": "group-A",
                                         "instruction": "A new opinion saved in the publication window."})["request"]
            return serialize(owner, ledger)
        original = self.app.ledger_bytes()
        with patch.object(helper.FigureWorkbench, "ledger_serialized", new=save_new_target_request):
            with self.assertRaisesRegex(helper.WorkbenchError, "Request queue changed"):
                helper.record_requests(self.attempt, target, [item["id"]], changed_files=["plot-spec.json"],
                                       validation="Reviewed current target.")
        self.assertEqual(self.app.ledger_bytes(), original)
        self.assertEqual([record["id"] for record in other.ledger()["requests"]], [saved[0]["id"]])

    def test_accept_publication_failure_is_retryable_and_retains_pending_instructions(self):
        item = self.request(annotation_number=3)
        original = self.app.ledger_bytes()
        publish = helper.FigureWorkbench._replace_ledger_bytes
        failed = False
        def fail_after_acceptance_replacement(owner, raw):
            nonlocal failed
            publish(owner, raw)
            if not failed:
                failed = True
                raise OSError("Injected disk failure after atomic replacement")
        with patch.object(helper.FigureWorkbench, "_replace_ledger_bytes", new=fail_after_acceptance_replacement):
            with self.assertRaisesRegex(OSError, "Injected disk failure"):
                helper.accept_attempt(self.attempt, validation="Reviewed actual SVG and paired exports.")
        self.assertFalse((self.attempt / "accepted-snapshot").exists())
        self.assertEqual(self.app.ledger_bytes(), original)
        helper.accept_attempt(self.attempt, validation="Reviewed actual SVG and paired exports.")
        ledger = self.app.ledger()
        self.assertEqual([record["id"] for record in ledger["requests"]], [item["id"]])
        self.assertEqual(ledger["requests"][0]["status"], "pending")
        self.assertEqual([entry["action"] for entry in ledger["history"]], ["accepted"])

    def test_record_qa_bytes_changed_in_publication_windows_rejects_and_remains_retryable(self):
        invalid_flags = {"invalid_false": False, "invalid_zero": 0, "invalid_null": None, "invalid_string": "false"}
        for window in ("before_lock", "after_source", "after_target", "changed_passing_bytes", *invalid_flags):
            with self.subTest(window=window):
                source, target = self.root / ("source-" + window), self.root / ("target-" + window)
                self.make_attempt(source, self.spec)
                self.make_attempt(target, self.spec)
                source_app, target_app = helper.FigureWorkbench(source), helper.FigureWorkbench(target)
                item = source_app.change({"version": source_app.state()["version"], "element_id": "group-A",
                                          "annotation_number": 1, "instruction": "Retain this pending opinion until valid target QA."})["request"]
                target_item = target_app.change({"version": target_app.state()["version"], "element_id": "group-A",
                                                 "annotation_number": 2, "instruction": "Retain the target's own pending opinion."})["request"]
                before = {app.root: app.ledger_bytes() for app in (source_app, target_app)}
                qa_path = target / "qa.json"
                good_qa = qa_path.read_bytes()
                fired = False
                def invalidate():
                    nonlocal fired
                    fired = True
                    changed = {"status": "pass", "valid_outputs": True, "note": "Different passing evidence"} if window == "changed_passing_bytes" else {"status": "needs_revision", "valid_outputs": False}
                    qa_path.write_text(json.dumps(changed))
                serialize, publish = helper.FigureWorkbench.ledger_serialized, helper.FigureWorkbench._replace_ledger_bytes
                def serialize_with_invalidation(app, ledger):
                    if app.root == target and not fired and window in ("before_lock", "changed_passing_bytes"):
                        invalidate()
                    return serialize(app, ledger)
                def publish_with_invalidation(app, raw):
                    publish(app, raw)
                    if not fired and ((window == "after_source" and app.root == source) or (window == "after_target" and app.root == target)):
                        invalidate()
                if window in invalid_flags:
                    qa_path.write_text(json.dumps({"status": "pass", "valid_outputs": invalid_flags[window]}))
                with patch.object(helper.FigureWorkbench, "ledger_serialized", new=serialize_with_invalidation), patch.object(helper.FigureWorkbench, "_replace_ledger_bytes", new=publish_with_invalidation):
                    with self.assertRaisesRegex(helper.WorkbenchError, "QA|qa"):
                        helper.record_requests(source, target, [item["id"]], changed_files=["plot-spec.json"], validation="Target is valid only when its captured QA still passes.")
                for app in (source_app, target_app):
                    self.assertEqual(app.ledger_bytes(), before[app.root])
                self.assertEqual(source_app.ledger()["requests"][0]["status"], "pending")
                qa_path.write_bytes(good_qa)
                event = helper.record_requests(source, target, [item["id"]], changed_files=["plot-spec.json"], validation="Fresh target QA rechecked.")
                self.assertEqual(event["target_qa_sha256"], digest(good_qa))
                self.assertEqual(source_app.ledger()["requests"][0]["result"]["target_qa_sha256"], digest(good_qa))
                self.assertEqual([record["id"] for record in target_app.ledger()["requests"]], [item["id"], target_item["id"]])

    def test_accept_actual_snapshot_qa_and_publication_bytes_must_still_pass(self):
        invalid_flags = {"invalid_false": False, "invalid_zero": 0, "invalid_null": None, "invalid_string": "false"}
        windows = ("before_capture", "after_captured_read", "changed_passing_bytes", "before_publication", "after_publication", "snapshot_corrupted", *invalid_flags)
        for window in windows:
            with self.subTest(window=window):
                source = self.root / ("accept-" + window)
                self.make_attempt(source, self.spec)
                app = helper.FigureWorkbench(source)
                app.change({"version": app.state()["version"], "element_id": "group-A", "annotation_number": 3,
                            "instruction": "Retain the pending request if acceptance cannot publish."})
                original = app.ledger_bytes()
                qa_path, snapshot = source / "qa.json", source / "accepted-snapshot"
                good_qa = qa_path.read_bytes()
                fired = False
                def invalidate(path=qa_path):
                    nonlocal fired
                    fired = True
                    changed = {"status": "pass", "valid_outputs": True, "note": "Changed passing QA bytes"} if window == "changed_passing_bytes" else {"status": "in_progress", "valid_outputs": False}
                    path.write_text(json.dumps(changed))
                read, write, publish = helper.read_regular, helper.write_json, helper.FigureWorkbench._replace_ledger_bytes
                def read_with_invalidation(path):
                    raw = read(path)
                    if not fired and ((window in ("before_capture", "changed_passing_bytes") and Path(path) == source / "plot-spec.json") or
                                      (window == "after_captured_read" and Path(path) == qa_path)):
                        invalidate()
                    return raw
                def write_with_invalidation(path, value):
                    write(path, value)
                    if not fired and Path(path) == snapshot / "acceptance.json" and window in ("before_publication", "snapshot_corrupted"):
                        invalidate(snapshot / "qa.json" if window == "snapshot_corrupted" else qa_path)
                def publish_with_invalidation(owner, raw):
                    publish(owner, raw)
                    if not fired and owner.root == source and window == "after_publication":
                        invalidate()
                if window in invalid_flags:
                    qa_path.write_text(json.dumps({"status": "pass", "valid_outputs": invalid_flags[window]}))
                with patch.object(helper, "read_regular", side_effect=read_with_invalidation), patch.object(helper, "write_json", side_effect=write_with_invalidation), patch.object(helper.FigureWorkbench, "_replace_ledger_bytes", new=publish_with_invalidation):
                    with self.assertRaisesRegex(helper.WorkbenchError, "QA|qa"):
                        helper.accept_attempt(source, validation="Acceptance requires actual captured and current passing QA.")
                self.assertEqual(app.ledger_bytes(), original)
                self.assertFalse(snapshot.exists())
                qa_path.write_bytes(good_qa)
                accepted = helper.accept_attempt(source, validation="Fresh passing QA and frozen exports verified.")
                self.assertEqual(accepted["qa_sha256"], digest(good_qa))
                self.assertEqual(accepted["files"]["qa.json"], digest(good_qa))
                self.assertEqual((snapshot / "qa.json").read_bytes(), good_qa)
                self.assertEqual([entry["action"] for entry in app.ledger()["history"]], ["accepted"])

    def test_snapshot_tampering_path_escape_and_symlink_restores_are_refused(self):
        helper.accept_attempt(self.attempt,validation="Visual review passed.")
        snapshot=self.attempt/"accepted-snapshot"
        source=(snapshot/"plot-source.py").read_bytes()
        (snapshot/"plot-source.py").write_bytes(source+b"changed")
        with self.assertRaises(helper.WorkbenchError): helper.restore_attempt(self.attempt,self.root/"tampered")
        self.assertFalse((self.root/"tampered").exists())
        (snapshot/"plot-source.py").write_bytes(source)
        acceptance=json.loads((snapshot/"acceptance.json").read_text())
        acceptance["files"]["../outside.py"]="bad"
        (snapshot/"acceptance.json").write_text(json.dumps(acceptance))
        with self.assertRaises(helper.WorkbenchError): helper.restore_attempt(self.attempt,self.root/"escape")
        del acceptance["files"]["../outside.py"]
        (snapshot/"acceptance.json").write_text(json.dumps(acceptance))
        (snapshot/"plot-source.py").unlink();(snapshot/"plot-source.py").symlink_to(self.attempt/"plot.py")
        with self.assertRaises(helper.WorkbenchError): helper.restore_attempt(self.attempt,self.root/"symlink")
        self.assertFalse((self.root/"symlink").exists())

    def test_missing_provenance_and_output_reuse_do_not_prepare_or_accept(self):
        item=self.request()
        with self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.attempt,[item["id"]])
        (self.attempt/"plot.py").unlink()
        with self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.root/"missing",[item["id"]])
        with self.assertRaises(helper.WorkbenchError): helper.accept_attempt(self.attempt,validation="Visual review.")

    def test_apply_and_restore_reject_parent_traversal_into_reviewed_attempt(self):
        item=self.request()
        helper.accept_attempt(self.attempt,validation="Final-size visual review passed.")
        sibling=self.root/"sibling"
        sibling.mkdir()
        bypass=sibling/".."/self.attempt.name/"nested-output"
        self.assertEqual(bypass.resolve(),self.attempt/"nested-output")
        originals={path.relative_to(self.attempt):path.read_bytes() for path in self.attempt.rglob("*") if path.is_file()}
        for action in (lambda:helper.prepare_requests(self.attempt,bypass,[item["id"]]), lambda:helper.restore_attempt(self.attempt,bypass)):
            with self.assertRaisesRegex(helper.WorkbenchError,"parent traversal"):
                action()
            self.assertFalse((self.attempt/"nested-output").exists())
            self.assertEqual({path.relative_to(self.attempt):path.read_bytes() for path in self.attempt.rglob("*") if path.is_file()},originals)

    def test_shared_profile_requires_agent_and_preserves_attempt(self):
        item=self.request()
        settings_path=self.attempt/"settings.json"
        original=settings_path.read_bytes()
        settings=json.loads(original);settings["figure_profile"]={"path":"outside-profile.json","sha256":"unverified"}
        settings_path.write_text(json.dumps(settings))
        with self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.root/"profile",[item["id"]])
        with self.assertRaises(helper.WorkbenchError): helper.accept_attempt(self.attempt,validation="Reviewed.")
        self.assertFalse((self.root/"profile").exists())
        settings_path.write_bytes(original)

    def test_ambiguous_legacy_paths_and_malformed_request_snapshots_are_refused(self):
        item=self.request()
        original=self.app.ledger()
        for malformed in (["group-A",{}], [True], ["group-A","group-A"]):
            ledger=copy.deepcopy(original);ledger["requests"][0]["element_ids"]=malformed;self.app.write_ledger(ledger)
            with self.subTest(ids=malformed), self.assertRaises(helper.WorkbenchError): helper.prepare_requests(self.attempt,self.root/"malformed",[item["id"]])
        self.app.write_ledger(original)
        element={"editable":["color"],"spec_paths":["/colors/A","/options/point_color"]}
        with self.assertRaises(helper.WorkbenchError): helper.resolve_path({"property":"color"},element)
        self.assertEqual(helper.resolve_path({"property":"color","spec_path":"/colors/A"},element),"/colors/A")


class CoreRenderRequestTests(unittest.TestCase):
    def test_real_replaced_pdf_and_tiff_cannot_reuse_passing_qa_hashes(self):
        import render
        with tempfile.TemporaryDirectory(prefix="easyviz-workbench-export-binding-") as folder:
            root = Path(folder).resolve()
            data = root / "input.csv"
            data.write_text("x,y\n1,2\n2,3\n3,5\n4,4\n")
            spec = {"chart": "scatter", "fields": {"x": "x", "y": "y"},
                    "layout": {"width_mm": 120, "height_mm": 90, "dpi": 120, "font": "DejaVu Sans"},
                    "options": {"point_area_pt2": 12}, "formats": ["svg", "pdf", "png", "tiff"]}
            source, target = root / "source", root / "target"
            for path, adopted in ((source, spec), (target, {**spec, "options": {"point_area_pt2": 25, "point_style": "hollow"}})):
                path.mkdir()
                spec_path = path / "plot-spec.json"
                spec_path.write_text(json.dumps(adopted))
                render.render(data, adopted, path, spec_path=spec_path, track="create")
                self.assertEqual(json.loads((path / "qa.json").read_text())["status"], "pass")
            source_app, target_app = helper.FigureWorkbench(source), helper.FigureWorkbench(target)
            item = source_app.change({"version": source_app.state()["version"], "instruction": "Review this cosmetic alternative."})["request"]
            source_before, target_before = source_app.ledger_bytes(), target_app.ledger_bytes()
            qa_bytes = (target / "qa.json").read_bytes()
            qa = json.loads(qa_bytes)
            for extension in ("pdf", "tiff"):
                with self.subTest(extension=extension):
                    export = target / ("panel." + extension)
                    original, replacement = export.read_bytes(), (source / export.name).read_bytes()
                    self.assertEqual(qa["exports"][extension]["sha256"], digest(original))
                    self.assertNotEqual(digest(original), digest(replacement))
                    export.write_bytes(replacement)
                    self.assertEqual((target / "qa.json").read_bytes(), qa_bytes)
                    self.assertEqual(target_app.state()["version"], json.loads((target / "elements.json").read_text())["version"])
                    with self.assertRaisesRegex(helper.WorkbenchError, "QA export hash"):
                        helper.record_requests(source, target, [item["id"]], changed_files=["plot-spec.json"], validation="Old measurements cannot validate replaced exports.")
                    with self.assertRaisesRegex(helper.WorkbenchError, "QA export hash"):
                        helper.accept_attempt(target, validation="Old measurements cannot validate replaced exports.")
                    self.assertEqual(source_app.ledger_bytes(), source_before)
                    self.assertEqual(target_app.ledger_bytes(), target_before)
                    self.assertFalse((target / "accepted-snapshot").exists())
                    export.write_bytes(original)
            write = helper.write_json
            good_pdf = (target / "panel.pdf").read_bytes()
            def replace_live_export_after_snapshot(path, value):
                write(path, value)
                if Path(path) == target / "accepted-snapshot" / "acceptance.json":
                    (target / "panel.pdf").write_bytes((source / "panel.pdf").read_bytes())
            with patch.object(helper, "write_json", side_effect=replace_live_export_after_snapshot):
                with self.assertRaisesRegex(helper.WorkbenchError, "QA export hash"):
                    helper.accept_attempt(target, validation="Captured bundle cannot certify changed current exports.")
            self.assertEqual(target_app.ledger_bytes(), target_before)
            self.assertFalse((target / "accepted-snapshot").exists())
            (target / "panel.pdf").write_bytes(good_pdf)
            event = helper.record_requests(source, target, [item["id"]], changed_files=["plot-spec.json"], validation="Matching actual export hashes rechecked.")
            self.assertEqual(event["target_qa_sha256"], digest(qa_bytes))
            accepted = helper.accept_attempt(target, validation="Matching actual export hashes rechecked.")
            for extension in ("pdf", "tiff"):
                self.assertEqual(accepted["files"]["panel." + extension], qa["exports"][extension]["sha256"])

    def test_real_focused_restore_rebinds_every_settings_source_and_preserves_exports(self):
        import replicate_plot
        import create_review
        with tempfile.TemporaryDirectory(prefix="easyviz-focused-restore-") as folder:
            root = Path(folder).resolve()
            data = root / "data.csv"
            data.write_text("condition,unit,value\nA,one,2\nA,two,3\nA,three,4\nB,one,4\nB,two,5\nB,three,6\n")
            spec = {"chart": "replicate", "fields": {"condition": "condition", "unit": "unit", "value": "value"},
                    "options": {"mode": "summary", "uncertainty": "sample_sd"},
                    "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans", "font_size_pt": 8},
                    "formats": ["svg", "pdf", "png"]}
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec))
            initial = root / "attempt-01"
            qa = replicate_plot.render(data, spec, initial, spec_path=spec_path)
            self.assertEqual(qa["status"], "pass")
            settings = json.loads((initial / "settings.json").read_text())
            self.assertEqual(settings["input_file"], str(data))
            expected_exports = {name: (initial / name).read_bytes() for name in
                                ("panel.svg", "panel.pdf", "panel.png", "plotting-data.csv", "stats.json")}
            helper.accept_attempt(initial, validation="Verified real fixed-canvas exports and adopted source bindings.")
            data.write_text("condition,unit,value\nchanged,one,999\n")
            spec_path.write_text('{"changed": true}')
            restored = root / "restored"
            helper.restore_attempt(initial, restored)
            fresh_settings = json.loads((restored / "settings.json").read_text())
            self.assertEqual(fresh_settings["input_file"], str(restored / "source-data.csv"))
            expected_settings = copy.deepcopy(settings)
            expected_settings["input_file"] = str(restored / "source-data.csv")
            self.assertEqual(fresh_settings, expected_settings, "Only frozen provenance pointer changes")
            for name, raw in expected_exports.items():
                self.assertEqual((restored / name).read_bytes(), raw)
            self.assertTrue(helper.FigureWorkbench(restored).state()["source_current"])
            records = {name: json.loads((restored / name).read_text()) for name in ("settings.json", "elements.json", "qa.json")}
            bindings = create_review.source_bindings(restored, records)
            for role in ("data_file", "source_script", "spec_file"):
                self.assertTrue(bindings[role], role)
                self.assertTrue(all(entry["status"] == "passed" for entry in bindings[role]), bindings[role])
                self.assertTrue(all(Path(entry["path"]).parent == restored for entry in bindings[role]), bindings[role])

    def test_reference_style_alias_prepares_valid_core_spec_and_rerenders_same_position(self):
        import render
        with tempfile.TemporaryDirectory(prefix="easyviz-reference-style-") as folder:
            root = Path(folder).resolve()
            data = root / "data.csv"
            data.write_text("x,y\n1,2\n2,3\n3,5\n")
            spec = {"chart": "scatter", "fields": {"x": "x", "y": "y"},
                    "layout": {"width_mm": 120, "height_mm": 90, "font": "DejaVu Sans"},
                    "formats": ["svg", "pdf", "png"],
                    "options": {"reference_lines": {"y": [3.5]}},
                    "line_roles": {"reference": {"line_width_pt": .45, "linestyle": ":"}}}
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec))
            initial = root / "attempt-01"
            render.render(data, spec, initial, spec_path=spec_path, track="create")
            app = helper.FigureWorkbench(initial)
            state = app.state()
            reference = next(element for element in state["elements"] if element["role"] == "reference-line")
            item = app.change({"version": state["version"], "element_id": reference["id"],
                               "property": "linestyle", "value": "dashed",
                               "instruction": "Draw this supplied reference as a dashed line at the same value."})["request"]
            output = root / "attempt-02"
            plan = helper.prepare_requests(initial, output, [item["id"]], render=True)
            self.assertTrue(plan["rendered"])
            self.assertEqual(plan["patches"][0]["value"], "--")
            edited = json.loads((output / "plot-spec.json").read_text())
            expected = copy.deepcopy(spec)
            expected["line_roles"]["reference"]["linestyle"] = "--"
            self.assertEqual(edited, expected)
            self.assertEqual(json.loads((output / "qa.json").read_text())["status"], "pass")
            self.assertEqual((output / "plotting-data.csv").read_bytes(), (initial / "plotting-data.csv").read_bytes())
            self.assertEqual(json.loads(spec_path.read_text()), spec)
            paths = []
            for directory in (initial, output):
                svg = ET.parse(directory / "panel.svg")
                group = next(element for element in svg.iter() if element.get("id") == reference["id"])
                paths.append(group.find("{http://www.w3.org/2000/svg}path"))
            self.assertEqual(paths[0].get("d"), paths[1].get("d"), "Reference geometry retains its supplied position")
            self.assertNotEqual(paths[0].get("style"), paths[1].get("style"))
            self.assertEqual(app.ledger()["requests"][0]["status"], "applied")

    def test_bulk_request_core_rerender_updates_new_exports_and_manifest_only(self):
        try:
            import render
        except ImportError:
            self.skipTest("Core renderer dependencies are needed for this end-to-end check")
        with tempfile.TemporaryDirectory(prefix="easyviz-request-render-") as folder:
            root=Path(folder).resolve()
            data=root/"data.csv";data.write_text("x,y,group\n1,2,A\n2,3,A\n3,4,A\n1,4,B\n2,5,B\n3,6,B\n")
            spec={"chart":"scatter","fields":{"x":"x","y":"y","group":"group"},"labels":{"x":"X","y":"Y"},"layout":{"width_mm":120,"height_mm":90,"font":"DejaVu Sans","font_size_pt":8,"line_width_pt":.6},"formats":["svg","pdf","png"],"options":{"point_area_pt2":12},"seed":41}
            spec_path=root/"spec.json";spec_path.write_text(json.dumps(spec))
            initial=root/"attempt-01";render.render(data,spec,initial,spec_path=spec_path,track="create")
            helper.accept_attempt(initial,validation="Reviewed baseline source/spec/data and all exports.")
            app=helper.FigureWorkbench(initial);state=app.state()
            old_exports={name:(initial/name).read_bytes() for name in ("panel.svg","panel.pdf","panel.png","plotting-data.csv")}
            item=app.change({"version":state["version"],"selector":{"category":"A"},"property":"color","value":"#8822AA","instruction":"Use purple for all category A marks and guide keys."})["request"]
            out=root/"attempt-02"
            plan=helper.prepare_requests(initial,out,[item["id"]],render=True)
            self.assertTrue(plan["rendered"])
            fresh=helper.FigureWorkbench(out).state()
            self.assertTrue(fresh["manifest_valid"])
            self.assertTrue(fresh["source_current"])
            self.assertNotEqual(state["version"]["figure_sha256"],fresh["version"]["figure_sha256"])
            self.assertEqual(state["version"]["input_sha256"],fresh["version"]["input_sha256"])
            self.assertEqual((out/"plotting-data.csv").read_bytes(),old_exports["plotting-data.csv"])
            self.assertEqual(json.loads((out/"settings.json").read_text())["resolved_colors"]["A"],"#8822AA")
            self.assertEqual(app.ledger()["requests"][0]["status"],"applied")
            history=helper.FigureWorkbench(out).ledger()["history"]
            self.assertEqual(history[0]["action"],"accepted")
            self.assertEqual(history[0]["target_attempt"],str(initial),"Merged baseline acceptance must preserve its actual attempt name")
            self.assertEqual(history[-1]["target_attempt"],str(out))
            for name,content in old_exports.items(): self.assertEqual((initial/name).read_bytes(),content)
            manifest=json.loads((initial/"elements.json").read_text())
            manifest["version"]["spec_sha256"]="a"*64
            (initial/"elements.json").write_text(json.dumps(manifest))
            newer_state=app.state()
            wrong=app.change({"version":newer_state["version"],"selector":{"category":"A"},"property":"color","value":"#123456","instruction":"A new color request with an incorrect resolved-spec binding."})["request"]
            refused=root/"refused-resolved-version"
            with self.assertRaisesRegex(helper.WorkbenchError,"Resolved specification differs"):
                helper.prepare_requests(initial,refused,[wrong["id"]],render=True)
            self.assertFalse(refused.exists())


if __name__ == "__main__":
    unittest.main()
