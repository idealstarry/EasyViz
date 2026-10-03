"""Version-bound cosmetic edits, truthful history and complete accepted restore."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
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
