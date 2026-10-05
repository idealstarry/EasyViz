"""Local figure review boundaries and version-preserving request behavior."""
from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts/figure_workbench.py"
loader = importlib.util.spec_from_file_location("easyviz_figure_workbench", SCRIPT)
workbench = importlib.util.module_from_spec(loader)
loader.loader.exec_module(workbench)

SVG = b'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg" width="120mm" height="90mm" viewBox="10 20 240 180">
<g id="data-group-a"><circle cx="70" cy="80" r="8" fill="#2581B9"/></g>
<g id="legend"><text x="170" y="40">Group A</text></g>
</svg>'''


class FigureWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-workbench-")
        self.root = Path(self.temp.name)
        (self.root / "panel.svg").write_bytes(SVG)
        (self.root / "panel.pdf").write_bytes(b"%PDF-1.4\nimmutable export")
        (self.root / "panel.png").write_bytes(b"immutable PNG")
        (self.root / "settings.json").write_text(json.dumps({"track":"reproduce"}))
        self.version = {"figure_sha256": hashlib.sha256(SVG).hexdigest(), "spec_sha256":"a"*64,"input_sha256":"b"*64,"source_script_sha256":"c"*64}
        self.manifest = {"schema_version":1,"version":self.version,"panel":{"width_mm":120,"height_mm":90},"input":{"data_file":"/original/source.csv","spec_file":"/original/plot.json"},"elements":[{"id":"data-group-a","role":"data_marks","label":"Group A","source_keys":[{"group":"A"}],"spec_paths":["palette.colors.A"],"editable":["color","linewidth"]},{"id":"legend","role":"legend","label":"Group legend","source_keys":[],"spec_paths":["legend"],"editable":["position","text"]}]}
        (self.root / "elements.json").write_text(json.dumps(self.manifest))
        self.initial = {path.name:path.read_bytes() for path in self.root.iterdir()}
        self.server = workbench.create_server(self.root)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, payload=None, *, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=3)
        request_headers={}
        body=None
        if payload is not None:
            body=json.dumps(payload)
            request_headers.update({"Content-Type":"application/json","Origin":self.origin,"X-EasyViz-Token":self.server.app.token})
        request_headers.update(headers or {})
        connection.request(method,path,body,request_headers)
        response=connection.getresponse()
        result=(response.status,dict(response.getheaders()),response.read())
        connection.close()
        return result

    def data(self, method, path, payload=None, **kwargs):
        status,headers,body=self.request(method,path,payload,**kwargs)
        return status,json.loads(body)

    def change(self, **extra):
        return {"version":self.version,"element_id":"data-group-a","property":"color","value":"#E47751","instruction":"Use coral for Group A; retain point values and sizes.",**extra}

    def test_http_state_and_original_exports_keep_physical_geometry_and_sources(self):
        self.assertEqual(self.server.server_address[0],"127.0.0.1")
        code,state=self.data("GET","/api/state")
        self.assertEqual(code,200)
        self.assertTrue(state["manifest_valid"])
        self.assertEqual(state["panel"],{"width_mm":120,"height_mm":90})
        self.assertEqual(state["view_box"],[10,20,240,180])
        self.assertEqual(state["track"],"reproduce")
        self.assertEqual(state["input"],self.manifest["input"])
        status,headers,body=self.request("GET","/files/panel.pdf")
        self.assertEqual(status,200)
        self.assertEqual(body,self.initial["panel.pdf"])
        self.assertIn('attachment; filename="panel.pdf"',headers["Content-Disposition"])
        for path in ("/","/workbench.css","/workbench.js","/logo.svg","/api/preview.svg"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET",path)[0],200)
        status,headers,body=self.request("GET","/logo.svg")
        self.assertEqual(headers["Content-Type"],"image/svg+xml")
        self.assertEqual(body,(SCRIPT.parents[3]/"plugins/easyviz/assets/logo.svg").read_bytes())

    def test_logo_url_changes_with_artwork_and_serves_current_svg(self):
        logo = self.root / "logo.svg"
        previous_url = None
        with patch.object(workbench, "LOGO", logo):
            for artwork in (SVG, SVG.replace(b"#2581B9", b"#E47751")):
                logo.write_bytes(artwork)
                url = f'/logo.svg?v={hashlib.sha256(artwork).hexdigest()}'
                status, headers, body = self.request("GET", "/")
                self.assertEqual(status, 200)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertIn(f'<link rel="icon" href="{url}" type="image/svg+xml" sizes="any">'.encode(), body)
                self.assertIn(f'src="{url}"'.encode(), body)
                self.assertNotIn(b"__LOGO_VERSION__", body)
                self.assertNotIn(b'="/logo.svg"', body)
                if previous_url is not None:
                    self.assertNotIn(previous_url.encode(), body)
                self.assertEqual(self.request("GET", "/")[2], body)
                status, headers, body = self.request("GET", url)
                self.assertEqual(status, 200)
                self.assertEqual(headers["Content-Type"], "image/svg+xml")
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(body, artwork)
                previous_url = url

    def test_semantic_request_saves_binding_and_undo_without_changing_exports(self):
        code,result=self.data("POST","/api/requests",self.change())
        self.assertEqual(code,200)
        item=result["request"]
        self.assertEqual(item["status"],"pending")
        self.assertEqual(item["version"],self.version)
        self.assertEqual(item["element"]["source_keys"],[{"group":"A"}])
        self.assertEqual(item["element"]["spec_paths"],["palette.colors.A"])
        self.assertEqual(item["input"],self.manifest["input"])
        code,result=self.data("POST","/api/undo",{"version":self.version,"request_id":item["id"]})
        self.assertEqual(code,200)
        self.assertEqual(result["request"]["status"],"undone")
        ledger=json.loads((self.root/"requests.json").read_text())
        self.assertEqual(len(ledger["requests"]),1)
        self.assertEqual(ledger["requests"][0]["id"],item["id"])
        for name,body in self.initial.items():
            self.assertEqual((self.root/name).read_bytes(),body)

    def test_batch_saves_independent_numbered_requests_with_one_ledger_write(self):
        _,previous = self.data("POST","/api/requests",self.change())
        saved_before = self.server.app.ledger()["requests"][0]
        payload = {"version": self.version, "requests": [
            self.change(annotation_number=1, anchor_mm={"x": 30, "y": 45}),
            {"version": self.version, "element_id": "legend", "property": "position",
             "value": [85, 10], "instruction": "Move the guide to the right.",
             "annotation_number": 2, "anchor_mm": {"x": 120, "y": 0}},
        ]}
        with patch.object(self.server.app, "write_ledger", wraps=self.server.app.write_ledger) as writer:
            code,result = self.data("POST","/api/requests/batch",payload)
        self.assertEqual(code,200,result)
        self.assertEqual(writer.call_count,1)
        self.assertEqual(set(result),{"requests","state"})
        self.assertEqual([item["annotation_number"] for item in result["requests"]],[1,2])
        self.assertEqual(result["requests"][0]["anchor_mm"],{"x":30,"y":45})
        self.assertEqual(result["requests"][0]["coordinate_origin"],"top-left of full canvas")
        self.assertEqual(result["requests"][0]["element"]["source_keys"],[{"group":"A"}])
        self.assertEqual(result["requests"][1]["element"]["spec_paths"],["legend"])
        self.assertEqual(len({item["id"] for item in result["requests"]}),2)
        ledger = self.server.app.ledger()
        self.assertEqual(len(ledger["requests"]),3)
        self.assertEqual(ledger["requests"][0],saved_before)
        self.assertEqual(ledger["requests"][0]["id"],previous["request"]["id"])
        self.assertEqual(len(result["state"]["requests"]),3)
        for name,body in self.initial.items():
            self.assertEqual((self.root/name).read_bytes(),body)

    def test_invalid_batch_is_atomic_for_new_and_existing_ledgers(self):
        bad_batches = [
            {"version": self.version, "requests": []},
            {"version": self.version, "requests": [self.change()] * 101},
            {"version": self.version, "requests": self.change()},
            {"version": self.version, "requests": [self.change(), self.change(element_id="missing")]},
            {"version": self.version, "requests": [self.change(annotation_number=1), self.change(annotation_number=1)]},
            {"version": self.version, "requests": [self.change(), "another request"]},
            {"version": self.version, "requests": [self.change(), self.change(instruction="")]},
            {"version": self.version, "requests": [self.change()], "command": "unsupported"},
        ]
        for payload in bad_batches:
            with self.subTest(payload=payload), patch.object(self.server.app,"write_ledger",wraps=self.server.app.write_ledger) as writer:
                code,result = self.data("POST","/api/requests/batch",payload)
                self.assertEqual(code,400,result)
                self.assertEqual(writer.call_count,0)
                self.assertFalse((self.root/"requests.json").exists())
        self.assertEqual(self.data("POST","/api/requests",self.change(annotation_number=8))[0],200)
        original = (self.root/"requests.json").read_bytes()
        for payload in bad_batches + [{"version":self.version,"requests":[self.change(annotation_number=9),self.change(annotation_number=8)]}]:
            with self.subTest(payload=payload), patch.object(self.server.app,"write_ledger",wraps=self.server.app.write_ledger) as writer:
                self.assertEqual(self.data("POST","/api/requests/batch",payload)[0],400)
                self.assertEqual(writer.call_count,0)
                self.assertEqual((self.root/"requests.json").read_bytes(),original)

    def test_number_anchor_validation_undo_reservation_and_version_scope(self):
        for number in (0,-1,1000001,1.0,True,"1",None):
            with self.subTest(number=number):
                self.assertEqual(self.data("POST","/api/requests",self.change(annotation_number=number))[0],400)
                self.assertFalse((self.root/"requests.json").exists())
        for anchor in (None,{"x":0},{"x":0,"y":0,"width":1},{"x":-0.001,"y":0},{"x":120.001,"y":0},{"x":0,"y":90.001},{"x":0,"y":-1},{"x":True,"y":0},{"x":"1","y":0},{"x":float("inf"),"y":0}):
            with self.subTest(anchor=anchor):
                self.assertEqual(self.data("POST","/api/requests",self.change(anchor_mm=anchor))[0],400)
                self.assertFalse((self.root/"requests.json").exists())
        code,result = self.data("POST","/api/requests",self.change(annotation_number=1,anchor_mm={"x":0,"y":90}))
        self.assertEqual(code,200,result)
        self.assertEqual(self.data("POST","/api/undo",{"version":self.version,"request_id":result["request"]["id"]})[0],200)
        original = (self.root/"requests.json").read_bytes()
        self.assertEqual(self.data("POST","/api/requests",self.change(annotation_number=1))[0],400)
        self.assertEqual(self.data("POST","/api/requests/batch",{"version":self.version,"requests":[self.change(annotation_number=2),self.change(annotation_number=1)]})[0],400)
        self.assertEqual((self.root/"requests.json").read_bytes(),original)
        self.assertEqual(self.data("POST","/api/requests",self.change(annotation_number=1000000,anchor_mm={"x":120,"y":90}))[0],200)
        old_requests = self.server.app.ledger()["requests"]
        (self.root/"panel.svg").write_bytes(SVG.replace(b"#2581B9",b"#00DCDC"))
        _,state = self.data("GET","/api/state")
        code,result = self.data("POST","/api/requests",{"version":state["version"],"instruction":"This new export uses annotation one.","annotation_number":1,"anchor_mm":{"x":0,"y":0}})
        self.assertEqual(code,200,result)
        self.assertEqual(self.server.app.ledger()["requests"][:2],old_requests)
        self.assertEqual(result["request"]["annotation_number"],1)

    def test_batch_requires_full_version_for_top_and_every_child(self):
        partial = {"figure_sha256":self.version["figure_sha256"]}
        for payload in ({"version":partial,"requests":[self.change()]},
                        {"version":self.version,"requests":[self.change(),self.change(version=partial)]},
                        {"version":self.version,"requests":[self.change(),{"instruction":"Version is required."}]}):
            with self.subTest(payload=payload), patch.object(self.server.app,"write_ledger",wraps=self.server.app.write_ledger) as writer:
                self.assertEqual(self.data("POST","/api/requests/batch",payload)[0],409)
                self.assertEqual(writer.call_count,0)
                self.assertFalse((self.root/"requests.json").exists())

    def test_batch_detects_export_or_source_change_during_validation_before_writing(self):
        source = self.root/"source.csv"
        source.write_text("original source")
        self.version["input_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        self.manifest["input"]["data_file"] = str(source)
        (self.root/"elements.json").write_text(json.dumps(self.manifest))
        self.assertEqual(self.data("POST","/api/requests",self.change())[0],200)
        original = (self.root/"requests.json").read_bytes()
        prepare = self.server.app.prepare_request
        for changed in ("figure","source"):
            count = 0
            def mutate_after_validation(payload,state,used_numbers):
                nonlocal count
                item = prepare(payload,state,used_numbers)
                count += 1
                if count == 2:
                    if changed == "figure":
                        (self.root/"panel.svg").write_bytes(SVG.replace(b"#2581B9",b"#00DCDC"))
                    else:
                        source.write_text("new source")
                return item
            with self.subTest(changed=changed), patch.object(self.server.app,"prepare_request",side_effect=mutate_after_validation), patch.object(self.server.app,"write_ledger",wraps=self.server.app.write_ledger) as writer:
                code,result = self.data("POST","/api/requests/batch",{"version":self.version,"requests":[self.change(annotation_number=1),self.change(annotation_number=2)]})
                self.assertEqual(code,409,result)
                self.assertEqual(writer.call_count,0)
                self.assertEqual((self.root/"requests.json").read_bytes(),original)
            (self.root/"panel.svg").write_bytes(SVG)
            source.write_text("original source")

    def test_batch_atomic_replace_failure_keeps_previous_ledger_and_cleans_temporary(self):
        self.assertEqual(self.data("POST","/api/requests",self.change())[0],200)
        original = (self.root/"requests.json").read_bytes()
        with patch.object(Path,"replace",side_effect=OSError("Save interrupted")):
            code,result = self.data("POST","/api/requests/batch",{"version":self.version,"requests":[self.change(annotation_number=1),self.change(annotation_number=2)]})
        self.assertEqual(code,400,result)
        self.assertEqual((self.root/"requests.json").read_bytes(),original)
        self.assertEqual(list(self.root.glob(".requests-*.tmp")),[])

    def test_batch_accepts_one_hundred_requests_without_single_body_limit(self):
        requests = [self.change(annotation_number=index,instruction="An independent change. " + "x"*800) for index in range(1,101)]
        payload = {"version":self.version,"requests":requests}
        self.assertGreater(len(json.dumps(payload)),workbench.MAX_REQUEST_BYTES)
        code,result = self.data("POST","/api/requests/batch",payload)
        self.assertEqual(code,200,result)
        self.assertEqual(len(result["requests"]),100)
        self.assertEqual([item["annotation_number"] for item in result["requests"]],list(range(1,101)))

    def test_batch_ledger_size_failure_does_not_publish_unreadable_results(self):
        self.assertEqual(self.data("POST","/api/requests",self.change())[0],200)
        original = (self.root/"requests.json").read_bytes()
        with patch.object(workbench,"MAX_FILE_BYTES",len(original)+10):
            code,result = self.data("POST","/api/requests/batch",{"version":self.version,"requests":[self.change(annotation_number=1),self.change(annotation_number=2)]})
        self.assertEqual(code,400,result)
        self.assertIn("size limit",result["error"])
        self.assertEqual((self.root/"requests.json").read_bytes(),original)
        self.assertEqual(list(self.root.glob(".requests-*.tmp")),[])

    def test_agent_queue_update_during_batch_validation_is_never_overwritten(self):
        self.assertEqual(self.data("POST","/api/requests",self.change(annotation_number=7))[0],200)
        agent_ledger = self.server.app.ledger()
        agent_ledger["requests"][0]["status"] = "applied"
        agent_ledger["history"] = [{"action":"applied","target_attempt":"attempt-02"}]
        agent_bytes = (json.dumps(agent_ledger,sort_keys=True,separators=(",",":"))+"\n").encode()
        prepare = self.server.app.prepare_request
        calls = 0
        def agent_update(payload,state,used_numbers):
            nonlocal calls
            item = prepare(payload,state,used_numbers)
            calls += 1
            if calls == 1:
                (self.root/"requests.json").write_bytes(agent_bytes)
            return item
        with patch.object(self.server.app,"prepare_request",side_effect=agent_update), patch.object(self.server.app,"write_ledger",wraps=self.server.app.write_ledger) as writer:
            code,result = self.data("POST","/api/requests/batch",{"version":self.version,"requests":[self.change(annotation_number=1),self.change(annotation_number=2)]})
        self.assertEqual(code,409,result)
        self.assertIn("Saved requests changed",result["error"])
        self.assertEqual(writer.call_count,0)
        self.assertEqual((self.root/"requests.json").read_bytes(),agent_bytes)
        self.assertEqual(self.server.app.ledger()["requests"][0]["status"],"applied")
        self.assertEqual(self.server.app.ledger()["history"],agent_ledger["history"])

    def test_agent_queue_update_also_blocks_stale_single_save_and_undo(self):
        code,saved = self.data("POST","/api/requests",self.change(annotation_number=7))
        self.assertEqual(code,200)
        original = (self.root/"requests.json").read_bytes()
        agent_ledger = json.loads(original)
        agent_ledger["requests"][0]["status"] = "applied"
        agent_ledger["history"] = [{"action":"applied","target_attempt":"attempt-02"}]
        agent_bytes = (json.dumps(agent_ledger,sort_keys=True,separators=(",",":"))+"\n").encode()
        current_state = self.server.app.current_state
        for path,payload in (("/api/requests",self.change(annotation_number=1)),
                             ("/api/undo",{"version":self.version,"request_id":saved["request"]["id"]})):
            (self.root/"requests.json").write_bytes(original)
            calls = 0
            def agent_update_before_publish(version):
                nonlocal calls
                calls += 1
                if calls == 2:
                    (self.root/"requests.json").write_bytes(agent_bytes)
                return current_state(version)
            with self.subTest(path=path), patch.object(self.server.app,"current_state",side_effect=agent_update_before_publish), patch.object(self.server.app,"write_ledger",wraps=self.server.app.write_ledger) as writer:
                code,result = self.data("POST",path,payload)
                self.assertEqual(code,409,result)
                self.assertIn("Saved requests changed",result["error"])
                self.assertEqual(writer.call_count,0)
                self.assertEqual((self.root/"requests.json").read_bytes(),agent_bytes)

    def test_independent_instance_save_in_last_publication_window_is_preserved(self):
        other = workbench.FigureWorkbench(self.root)
        publish = self.server.app.write_ledger
        saved = []
        def publish_after_other_instance(ledger, **guards):
            saved.append(other.change(self.change(annotation_number=2))["request"])
            return publish(ledger, **guards)
        with patch.object(self.server.app, "write_ledger", side_effect=publish_after_other_instance):
            code, result = self.data("POST", "/api/requests/batch", {
                "version": self.version, "requests": [self.change(annotation_number=1)]})
        self.assertEqual(code, 409, result)
        self.assertIn("Saved requests changed", result["error"])
        self.assertEqual([item["id"] for item in other.ledger()["requests"]], [saved[0]["id"]])
        self.assertEqual(self.data("POST", "/api/requests", self.change(annotation_number=1))[0], 200)
        self.assertEqual([item["annotation_number"] for item in other.ledger()["requests"]], [2, 1])
        for name, raw in self.initial.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def lock_process(self, *, publish=False):
        script = textwrap.dedent('''
            import json, sys
            sys.path.insert(0, sys.argv[1])
            from figure_workbench import FigureWorkbench, ledger_file_lock
            app = FigureWorkbench(sys.argv[2])
            with ledger_file_lock(app.root):
                print("locked", flush=True)
                sys.stdin.readline()
                if sys.argv[3] == "publish":
                    state = app.state()
                    _, ledger = app.ledger_snapshot()
                    item = app.prepare_request({"version": state["version"], "element_id": "data-group-a",
                        "instruction": "Keep this independently saved opinion.", "annotation_number": 5}, state, set())
                    ledger["requests"].append(item)
                    app._replace_ledger_bytes(app.ledger_serialized(ledger))
                    print(item["id"], flush=True)
        ''')
        child = subprocess.Popen([sys.executable, "-c", script, str(SCRIPT.parent), str(self.root),
                                  "publish" if publish else "hold"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.stop_process, child)
        self.assertEqual(child.stdout.readline().strip(), "locked")
        return child

    @staticmethod
    def stop_process(child):
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)

    def test_process_lock_wait_rechecks_bytes_before_publishing_and_dead_owner_releases(self):
        child = self.lock_process(publish=True)
        with self.assertRaisesRegex(workbench.WorkbenchError, "busy"):
            with workbench.ledger_file_lock(self.root, timeout=.05):
                self.fail("An independent live process owns the lock")
        entering = threading.Event()
        errors = []
        publish = self.server.app.write_ledger
        def waiting_publish(ledger, **guards):
            entering.set()
            return publish(ledger, **guards)
        def save():
            try:
                self.server.app.change(self.change(annotation_number=1))
            except Exception as exc:
                errors.append(exc)
        with patch.object(self.server.app, "write_ledger", side_effect=waiting_publish):
            writer = threading.Thread(target=save)
            writer.start()
            self.assertTrue(entering.wait(2))
            self.assertTrue(writer.is_alive(), "Second writer must wait for the actual OS lock")
            child.stdin.write("release\n")
            child.stdin.flush()
            saved_id = child.stdout.readline().strip()
            child.wait(timeout=5)
            writer.join(timeout=5)
        self.assertFalse(writer.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], workbench.WorkbenchError)
        self.assertIn("Saved requests changed", str(errors[0]))
        self.assertEqual([item["id"] for item in self.server.app.ledger()["requests"]], [saved_id])
        abandoned = self.lock_process()
        abandoned.kill()
        abandoned.wait(timeout=5)
        self.assertTrue((self.root / ".requests.lock").exists())
        self.server.app.change(self.change(annotation_number=1))
        self.assertEqual([item["annotation_number"] for item in self.server.app.ledger()["requests"]], [5, 1])

    def test_lock_symlink_cannot_redirect_request_writes(self):
        outside = self.root / "unchanged-lock-target"
        outside.write_bytes(b"immutable")
        (self.root / ".requests.lock").symlink_to(outside)
        code, result = self.data("POST", "/api/requests", self.change(annotation_number=1))
        self.assertEqual(code, 400, result)
        self.assertIn("regular local file", result["error"])
        self.assertEqual(outside.read_bytes(), b"immutable")
        self.assertFalse((self.root / "requests.json").exists())

    def test_regions_work_without_map_and_mm_bounds_are_enforced(self):
        (self.root/"elements.json").unlink()
        code,state=self.data("GET","/api/state")
        self.assertFalse(state["manifest_valid"])
        request={"version":state["version"],"instruction":"Reduce unused margin in this region.","region_mm":{"x":5,"y":10,"width":20,"height":15}}
        code,result=self.data("POST","/api/requests",request)
        self.assertEqual(code,200)
        self.assertEqual(result["request"]["coordinate_origin"],"top-left of full canvas")
        for invalid in ({"x":-1,"y":0,"width":1,"height":1},{"x":119,"y":0,"width":2,"height":1},{"x":0,"y":89,"width":1,"height":2},{"x":0,"y":0,"width":0,"height":1},{"x":0,"y":0,"width":"1","height":1}):
            with self.subTest(region=invalid):
                self.assertEqual(self.data("POST","/api/requests",{**request,"region_mm":invalid})[0],400)
        self.assertEqual(self.data("POST","/api/requests",{**request,"element_id":"data-group-a"})[0],400)

    def test_receipt_bound_region_and_general_http_requests_keep_real_sources_without_fake_ids(self):
        from figure_handoff import capture_inputs, write_receipt
        (self.root / "elements.json").unlink()
        (self.root / "source.csv").write_text("id,x,y\n001,1,2\n")
        (self.root / "metadata.csv").write_text("id,group\n001,A\n")
        (self.root / "plot.py").write_text('raise RuntimeError("Must never execute recorded source")\n')
        (self.root / "spec.json").write_text(json.dumps({"chart": "custom",
            "layout": {"width_mm": 120, "height_mm": 90}}))
        for name in ("panel.svg", "panel.pdf", "panel.png"):
            (self.root / name).unlink()
        capture = capture_inputs(self.root, data_file=self.root / "source.csv",
            source_script=self.root / "plot.py", spec_file=self.root / "spec.json",
            auxiliary_inputs={"metadata": self.root / "metadata.csv"})
        (self.root / "panel.svg").write_bytes(SVG)
        receipt = write_receipt(self.root, capture=capture, formats=["svg"], track="create")
        code, state = self.data("GET", "/api/state")
        self.assertEqual(code, 200)
        self.assertTrue(state["provenance_valid"])
        self.assertTrue(state["source_current"])
        self.assertFalse(state["manifest_valid"])
        self.assertEqual(state["elements"], [])
        self.assertEqual(state["version"], receipt["version"])
        requests = [{"version": state["version"], "annotation_number": 1,
            "instruction": "Move the selected region label.",
            "region_mm": {"x": 5, "y": 10, "width": 20, "height": 15}},
            {"version": state["version"], "annotation_number": 2,
             "instruction": "Retain the whole figure's source values and dimensions."}]
        code, result = self.data("POST", "/api/requests/batch", {"version": state["version"], "requests": requests})
        self.assertEqual(code, 200)
        self.assertEqual([item["annotation_number"] for item in result["requests"]], [1, 2])
        for item in result["requests"]:
            self.assertEqual(item["input"]["auxiliary_inputs"], receipt["input"]["auxiliary_inputs"])
            self.assertEqual(item["element_ids"], [])
        (self.root / "metadata.csv").write_text("id,group\n001,B\n")
        code, stale = self.data("GET", "/api/state")
        self.assertEqual(code, 200)
        self.assertFalse(stale["source_current"])
        self.assertEqual(self.data("POST", "/api/requests", requests[0])[0], 409)

    def test_stale_export_or_map_cannot_receive_semantic_edits(self):
        self.assertEqual(self.data("POST","/api/requests",self.change())[0],200)
        newer=SVG.replace(b"#2581B9",b"#00DCDC")
        (self.root/"panel.svg").write_bytes(newer)
        code,error=self.data("POST","/api/requests",self.change())
        self.assertEqual(code,409)
        self.assertIn("changed",error["error"])
        _,state=self.data("GET","/api/state")
        self.assertFalse(state["manifest_valid"])
        self.assertEqual(state["elements"],[])
        self.assertFalse(state["requests"][0]["current_version"])
        self.assertEqual(self.data("POST","/api/requests",self.change(version=state["version"]))[0],400)
        self.assertEqual(self.request("GET","/api/preview.svg?v="+self.version["figure_sha256"])[0],409)
        self.assertEqual(self.data("POST","/api/requests",{"version":state["version"],"instruction":"Please regenerate the element map."})[0],200)

    def test_remote_origins_dns_rebinding_and_missing_session_are_rejected(self):
        for headers in ({"Origin":"https://example.com"},{"Origin":"null"},{"Origin":""},{"X-EasyViz-Token":""},{"Host":"attacker.example:8000"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.data("POST","/api/requests",self.change(),headers=headers)[0],403)
        self.assertEqual(self.data("GET","/api/state",headers={"Origin":"https://example.com"})[0],403)
        self.assertEqual(self.data("GET","/api/state",headers={"Host":"localhost:1234"})[0],403)
        self.assertFalse((self.root/"requests.json").exists())

    def test_path_traversal_unknown_properties_and_command_fields_are_rejected(self):
        for path in ("/files/../panel.svg","/files/%2e%2e/panel.svg","/files/elements.json/../settings.json","/files/source.csv","/../../etc/passwd"):
            self.assertEqual(self.request("GET",path)[0],404)
        for change in (self.change(property="data",value="invent new values"),self.change(element_id="missing"),self.change(instruction=""),self.change(command="rm -rf /"),self.change(property=None),self.change(region_mm={"x":0,"y":0,"width":2,"height":2})):
            with self.subTest(change=change):
                self.assertEqual(self.data("POST","/api/requests",change)[0],400)
        (self.root/"qa.json").symlink_to(self.root/"settings.json")
        self.assertEqual(self.data("GET","/files/qa.json")[0],400)
        (self.root/"requests.json").symlink_to(self.root/"settings.json")
        self.assertEqual(self.data("POST","/api/requests",self.change())[0],400)
        self.assertEqual((self.root/"settings.json").read_bytes(),self.initial["settings.json"])

    def test_active_svg_content_is_removed_from_preview_but_download_stays_exact(self):
        unsafe=SVG.replace(b"</svg>",b'<defs><clipPath id="data-clip"><rect x="10" y="20" width="240" height="180"/></clipPath></defs><g clip-path="url( &quot;#data-clip&quot; )"><path d="M 10 20 L 20 30"/></g><script>alert(1)</script><foreignObject><div>HTML</div></foreignObject><image href="https://example.com/a.png" onload="alert(1)"/><style>@import url(https://example.com/x.css)</style></svg>')
        (self.root/"panel.svg").write_bytes(unsafe)
        status,_,body=self.request("GET","/api/preview.svg")
        self.assertEqual(status,200)
        for marker in (b"<script",b"foreignObject",b"onload",b"https://example.com",b"@import"):
            self.assertNotIn(marker,body)
        self.assertIn(b"data-group-a",body)
        self.assertIn(b'clip-path="url( &quot;#data-clip&quot; )"',body)
        self.assertEqual(self.request("GET","/files/panel.svg")[2],unsafe)

    def test_invalid_manifest_falls_back_and_json_nonfinite_values_are_rejected(self):
        self.manifest["elements"][0]["id"]="missing"
        (self.root/"elements.json").write_text(json.dumps(self.manifest))
        _,state=self.data("GET","/api/state")
        self.assertFalse(state["manifest_valid"])
        connection=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=3)
        connection.request("POST","/api/requests",'{"version":{},"instruction":"note","region_mm":{"x":NaN}}',{"Content-Type":"application/json","Origin":self.origin,"X-EasyViz-Token":self.server.app.token})
        response=connection.getresponse();self.assertEqual(response.status,400);response.read();connection.close()

    def test_stale_map_cannot_supply_dimensions_or_input_provenance(self):
        newer=SVG.replace(b'width="120mm" height="90mm"',b'width="240mm" height="180mm"')
        (self.root/"panel.svg").write_bytes(newer)
        _,state=self.data("GET","/api/state")
        self.assertFalse(state["manifest_valid"])
        self.assertEqual(state["panel"],{"width_mm":240,"height_mm":180})
        self.assertEqual(state["version"],{"figure_sha256":hashlib.sha256(newer).hexdigest()})
        self.assertEqual(state["input"],{})
        request={"version":state["version"],"instruction":"Adjust the rightmost margin.","region_mm":{"x":200,"y":100,"width":20,"height":20}}
        code,result=self.data("POST","/api/requests",request)
        self.assertEqual(code,200)
        self.assertEqual(result["request"]["input"],{})
        self.assertEqual(result["request"]["version"],state["version"])
        self.assertEqual(result["request"]["region_mm"]["x"],200)

    def test_malformed_panel_metadata_falls_back_to_actual_svg(self):
        for panel in (None,[],"120 x 90",False,{"width_mm":120}):
            with self.subTest(panel=panel):
                self.manifest["panel"]=panel
                (self.root/"elements.json").write_text(json.dumps(self.manifest))
                code,state=self.data("GET","/api/state")
                self.assertEqual(code,200)
                self.assertFalse(state["manifest_valid"])
                self.assertEqual(state["panel"],{"width_mm":120,"height_mm":90})
                self.assertEqual(state["version"],{"figure_sha256":self.version["figure_sha256"]})
                self.assertEqual(state["input"],{})

    def test_safe_symbol_and_marker_definitions_keep_their_referenced_geometry(self):
        definitions=b'''<defs>
        <symbol id="dot-shape" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" onload="alert(1)"/></symbol>
        <marker id="arrow-head" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8Z"/><script>alert(1)</script></marker>
        </defs><use href="#dot-shape" x="70" y="80"/><path d="M20 30 L120 30" marker-end="url(#arrow-head)"/>'''
        (self.root/"panel.svg").write_bytes(SVG.replace(b"</svg>",definitions+b"</svg>"))
        code,_,body=self.request("GET","/api/preview.svg")
        self.assertEqual(code,200)
        root=workbench.ET.fromstring(body)
        ids={node.attrib.get("id"):node for node in root.iter()}
        self.assertEqual(ids["dot-shape"].tag.split("}")[-1],"symbol")
        self.assertEqual(ids["arrow-head"].tag.split("}")[-1],"marker")
        self.assertIn(b'href="#dot-shape"',body)
        self.assertIn(b'marker-end="url(#arrow-head)"',body)
        self.assertNotIn(b"<script",body)
        self.assertNotIn(b"onload",body)

    def test_bulk_selection_expands_real_category_source_and_spec_identities(self):
        self.manifest["elements"][0].update(source_keys=[{"group":"A","records":[1,3]}],spec_paths=["/colors/A"])
        self.manifest["elements"][1].update(role="legend-key",source_keys=[{"category":"A"}],spec_paths=["/colors/A"],editable={"color":"/colors/A"})
        (self.root/"elements.json").write_text(json.dumps(self.manifest))
        for selector in ({"category":"A"},{"spec_path":"/colors/A"}):
            code,result=self.data("POST","/api/requests",self.change(element_id=None,selector=selector))
            self.assertEqual(code,200,result)
            self.assertEqual(result["request"]["element_ids"],["data-group-a","legend"])
            self.assertIsNone(result["request"]["element_id"])
            self.assertEqual(result["request"]["elements"][0]["source_keys"],[{"group":"A","records":[1,3]}])
            self.assertEqual(result["request"]["selector"],selector)
        code,result=self.data("POST","/api/requests",self.change(element_id=None,selector={"source_key":{"records":[1,3]}}))
        self.assertEqual(code,200)
        self.assertEqual(result["request"]["element_ids"],["data-group-a"])
        for extra in ({"element_ids":["legend","missing"]},{"element_ids":["legend","legend"]},{"element_ids":"legend"},{"selector":{"category":"unknown"}},{"selector":{"position":[1,2]}},{"selector":{"source_key":{}}},{"selector":{"source_key":{"unknown":None}}},{"selector":{"source_key":{"records":[True,3]}}},{"element_ids":["legend"],"selector":{"category":"A"}}):
            code,result=self.data("POST","/api/requests",self.change(element_id=None,**extra))
            self.assertEqual(code,400,result)
        self.assertEqual(self.data("POST","/api/requests",self.change(element_id=None,element_ids=["data-group-a","legend"],property="linewidth"))[0],400)
        self.assertEqual(self.data("POST","/api/requests",self.change(element_id=None,element_ids=["data-group-a","legend"],spec_path="/options/alpha"))[0],400)

    def test_existing_source_changes_block_requests_even_when_svg_is_unchanged(self):
        paths={"data_file":self.root/"source.csv","source_script":self.root/"plot.py","spec_file":self.root/"spec.json"}
        for path in paths.values(): path.write_text("original")
        digest=hashlib.sha256(b"original").hexdigest()
        self.version.update(input_sha256=digest,source_script_sha256=digest)
        self.manifest["version"]=self.version
        self.manifest["input"]={**{key:str(path) for key,path in paths.items()},"supplied_spec_sha256":digest}
        (self.root/"elements.json").write_text(json.dumps(self.manifest))
        self.assertTrue(self.data("GET","/api/state")[1]["source_current"])
        self.assertEqual(self.data("POST","/api/requests",self.change())[0],200)
        for field,path in paths.items():
            with self.subTest(source=field):
                path.write_text("new source")
                state=self.data("GET","/api/state")[1]
                self.assertTrue(state["manifest_valid"])
                self.assertFalse(state["source_current"])
                self.assertFalse(state["source_versions"][field]["current"])
                code,error=self.data("POST","/api/requests",self.change())
                self.assertEqual(code,409,error)
                path.write_text("original")

    def test_previous_attempt_preview_is_fixed_sanitized_and_version_bound(self):
        previous=self.root/"previous"
        previous.mkdir()
        unsafe=SVG.replace(b"</svg>",b"<script>untrusted()</script></svg>")
        (previous/"panel.svg").write_bytes(unsafe)
        self.server.app.comparison=workbench.FigureWorkbench(previous)
        state=self.data("GET","/api/state")[1]
        self.assertEqual(state["comparison"]["figure_name"],"previous")
        digest=state["comparison"]["version"]["figure_sha256"]
        code,_,preview=self.request("GET","/api/compare.svg?v="+digest)
        self.assertEqual(code,200)
        self.assertNotIn(b"<script",preview)
        self.assertEqual(self.request("GET","/api/compare.svg?v=stale")[0],409)
        self.assertEqual(self.request("GET","/files/previous/panel.svg")[0],404)
        self.server.app.comparison=None
        self.assertEqual(self.request("GET","/api/compare.svg")[0],404)

    def test_history_statuses_are_preserved_and_undo_cannot_cancel_applied_records(self):
        _,result=self.data("POST","/api/requests",self.change())
        request_id=result["request"]["id"]
        ledger=self.server.app.ledger()
        ledger["requests"][0]["status"]="applied"
        ledger["history"]=[{"action":"applied","target_attempt":"attempt-02"}]
        self.server.app.write_ledger(ledger)
        state=self.data("GET","/api/state")[1]
        self.assertEqual(state["history"],ledger["history"])
        self.assertEqual(self.data("POST","/api/undo",{"version":self.version,"request_id":request_id})[0],400)


CLIENT_HARNESS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(process.argv[1],'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const jsonResponse=(body,ok=true)=>({ok,json:async()=>body});
class Element {
  constructor(name='',tagName='DIV') {
    this.name=name;this.id=name;this.tagName=tagName;this.value='';this.disabled=false;
    this.children=[];this.listeners={};this.attributes={};this.style={};
    this.classList={toggle(){},add(){},remove(){}};
    this.box={x:30,y:40,width:20,height:10};
  }
  addEventListener(name,callback){this.listeners[name]=callback;}
  setAttribute(name,value){this.attributes[name]=value;if(name==='class')this.className=value;}
  getAttribute(name){return this.attributes[name];}removeAttribute(name){delete this.attributes[name];}
  append(...children){for(const child of children){child.parentNode=this;this.children.push(child);}}
  replaceChildren(...children){for(const child of this.children)child.parentNode=null;this.children=[];this.append(...children);}
  add(child){this.append(child);}remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(child=>child!==this);this.parentNode=null;}
  contains(node){return node===this||!!node?.parentNode&&this.contains(node.parentNode);}
  getElementById(id){if(this.id===id)return this;for(const child of this.children){const found=child.getElementById(id);if(found)return found;}return null;}
  querySelectorAll(selector){const attr=selector.match(/^\[([^\]]+)\]$/)?.[1],result=[];for(const child of this.children){if(attr&&Object.hasOwn(child.attributes,attr))result.push(child);result.push(...child.querySelectorAll(selector));}return result;}
  closest(selector){if(selector==='.'+this.className)return this;return this.parentNode?.closest(selector)||null;}
  getBBox(){return this.box;}
  getScreenCTM(){return{a:1,b:0,c:0,d:1,inverse(){return this;},multiply(){return this;}};}
  createSVGPoint(){return{x:0,y:0,matrixTransform(){return{x:this.x,y:this.y};}};}
  setPointerCapture(){}focus(){}
  get options(){return this.children;}
  get selectedOptions(){return this.children.filter(option=>option.value===this.value);}
}
function makeSvg(name) {
  const root=new Element(name,'SVG'),axes=new Element('axes','G'),a=new Element('group-A','G'),b=new Element('group-B','G'),key=new Element('key-A','G'),line=new Element('axis-line','G');
  a.box={x:60,y:70,width:10,height:20};b.box={x:110,y:90,width:20,height:20};key.box={x:170,y:40,width:35,height:10};line.box={x:20,y:150,width:100,height:1};
  a.append(new Element('use-A','USE'));b.append(new Element('use-B','USE'));key.append(new Element('text-A','TEXT'));line.append(new Element('stroke','PATH'));
  axes.append(a,b,line);root.append(axes,key);return root;
}
function figure(name='A',extra={}) {
  return{schema_version:1,figure_name:'same-attempt',track:'create',version:{figure_sha256:name,spec_sha256:'spec-'+name},panel:{width_mm:120,height_mm:90},view_box:[10,20,240,180],manifest_valid:true,source_current:true,elements:[
    {id:'axes',role:'axes',label:'Data region',source_keys:[],spec_paths:[],editable:[]},
    {id:'group-A',role:'point-group',label:'A',source_keys:[{group:'A',records:[1,3]}],spec_paths:['/colors/A','/options/alpha'],editable:{color:'/colors/A',alpha:'/options/alpha'}},
    {id:'key-A',role:'legend-key',label:'A guide',source_keys:[{category:'A'}],spec_paths:['/colors/A'],editable:['color']},
    {id:'group-B',role:'point-group',label:'B',source_keys:[{group:'B',records:[2,4]}],spec_paths:['/colors/B'],editable:['color']},
    {id:'axis-line',role:'axis-line',label:'X axis line',source_keys:[],spec_paths:[],editable:['linewidth']}
  ],requests:[],history:[],files:['panel.svg'],token:'session',selection_message:'Mapped elements.',...extra};
}
function harness(initial,storage=new Map(),brokenStorage=false) {
  const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
  const h={data:initial,posted:[],nodes,node,storage,paint:()=>null,override:null,batchFailure:false};
  const current=(item)=>({...item,current_version:JSON.stringify(item.version)===JSON.stringify(h.data.version)});
  async function fetch(path,options) {
    if(h.override){const intercepted=h.override(path,options);if(intercepted!==undefined)return intercepted;}
    if(path==='/api/state')return jsonResponse({...h.data,requests:h.data.requests.map(current)});
    if(path.startsWith('/api/preview.svg'))return{ok:true,text:async()=>'SVG-'+h.data.version.figure_sha256};
    if(path==='/api/requests/batch') {
      const payload=JSON.parse(options.body);h.posted.push(payload);
      if(h.batchFailure)return jsonResponse({error:'The second requested change is invalid.'},false);
      const saved=payload.requests.map((request,index)=>{
        let ids=request.element_ids||[request.element_id].filter(Boolean);
        if(request.selector)ids=h.data.elements.filter(element=>!request.selector.category||(element.source_keys||[]).some(key=>key.group===request.selector.category||key.category===request.selector.category)).map(element=>element.id);
        return{...request,id:'saved-'+h.posted.length+'-'+index,status:'pending',element_ids:ids};
      });
      h.data={...h.data,requests:[...h.data.requests,...saved]};
      return jsonResponse({requests:saved,state:{...h.data,requests:h.data.requests.map(current)}});
    }
    if(path==='/api/undo') {
      const payload=JSON.parse(options.body);
      h.data={...h.data,requests:h.data.requests.map(item=>item.id===payload.request_id?{...item,status:'undone'}:item)};
      return jsonResponse({request:h.data.requests.find(item=>item.id===payload.request_id),state:{...h.data,requests:h.data.requests.map(current)}});
    }
    throw new Error('Unexpected request '+path);
  }
  h.context=vm.createContext({document:{getElementById:node,createElement:tag=>new Element('',tag.toUpperCase()),createElementNS:(_,tag)=>new Element('',tag.toUpperCase()),importNode:element=>element,elementFromPoint:(x,y)=>h.paint(x,y)},
    Option:class extends Element{constructor(text,value){super('','OPTION');this.textContent=text;this.value=value;}},
    DOMParser:class{parseFromString(text){return{querySelector:()=>null,documentElement:makeSvg(text)};}},
    sessionStorage:{getItem:key=>{if(brokenStorage)throw new Error('Storage blocked');return storage.get(key)||null;},setItem:(key,value)=>{if(brokenStorage)throw new Error('Storage blocked');storage.set(key,value);}},
    window:{addEventListener(){}},fetch,console});
  h.inspect=expr=>vm.runInContext(expr,h.context);
  h.svg=()=>node('figure-host').children[0];
  h.click=(id,event={})=>{const target=node(id);if(target.disabled)return;return target.listeners.click?.({target,preventDefault(){},stopPropagation(){},...event});};
  h.point=(id,x=120,y=80)=>h.click('figure-host',{target:h.svg().getElementById(id),clientX:x,clientY:y});
  h.input=(id,value)=>{node(id).value=value;node(id).listeners.input?.({target:node(id)});};
  h.choose=(id,value)=>{node(id).value=value;node(id).listeners.change?.({target:node(id)});};
  h.chip=number=>{const chip=node('annotation-list').children.find(item=>item.tagName==='BUTTON'&&item.textContent===String(number));assert.ok(chip,'Annotation '+number+' must be present');return chip.listeners.click();};
  h.numbers=()=>node('annotation-list').children.filter(item=>item.tagName==='BUTTON').map(item=>Number(item.textContent));
  h.submit=()=>node('request-form').listeners.submit({preventDefault(){}});
  h.region=()=>{h.click('region-mode');const root=h.svg();node('figure-host').listeners.pointerdown({target:root,button:0,pointerId:1,clientX:20,clientY:40,preventDefault(){}});node('figure-host').listeners.pointerup({target:root,pointerId:1,clientX:60,clientY:70});};
  vm.runInContext(source,h.context);
  h.start=async()=>{await tick();await tick();};
  return h;
}
"""


class WorkbenchClientTests(unittest.TestCase):
    def run_client(self,scenario):
        if not shutil.which("node"):
            self.skipTest("Node is needed for the client event regressions")
        script=SCRIPT.with_name("workbench")/"workbench.js"
        wrapped=CLIENT_HARNESS+"\n(async()=>{\n"+scenario+"\n})().catch(error=>{console.error(error);process.exitCode=1;});"
        result=subprocess.run([shutil.which("node"),"-e",wrapped,str(script)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_clicks_resolve_painted_targets_nearby_without_guessing_group_boxes(self):
        self.run_client(r"""
const h=harness(figure());await h.start();
assert.equal(h.node('save').disabled,true,'an empty form must not enable Save requests');
h.paint=(x,y)=>Math.hypot(x-125,y-80)<=2?h.svg().getElementById('use-A'):h.svg().getElementById('axes');
h.point('use-A',125,80);assert.deepEqual(h.numbers(),[1]);
assert.match(h.node('selection-details').textContent,/^A · point-group/);
h.input('instruction','Keep these point values; change only their color.');
h.point('axes',130,80);assert.deepEqual(h.numbers(),[1],'a near miss reactivates the same painted target');
assert.equal(h.node('instruction').value,'Keep these point values; change only their color.');
h.point('text-A',300,20);assert.deepEqual(h.numbers(),[1,2],'an ordinary second click creates an independent annotation');
assert.equal(h.node('instruction').value,'','a new annotation has its own empty instruction');
h.point('axes',200,80);assert.deepEqual(h.numbers(),[1,2,3]);
assert.match(h.node('selection-details').textContent,/Data region/,'empty collection space must select axes, not the surrounding point group');
h.paint=(x,y)=>Math.abs(y-150)<.5?h.svg().getElementById('stroke'):h.svg().getElementById('axes');
h.point('axes',200,155);assert.deepEqual(h.numbers(),[1,2,3,4]);
assert.match(h.node('selection-details').textContent,/X axis line/,'nearby painted thin strokes remain selectable');
const previous=makeSvg('read-only-previous'),duplicate=previous.getElementById('use-A');h.paint=()=>duplicate;
h.click('figure-host',{target:duplicate,clientX:1,clientY:1});assert.deepEqual(h.numbers(),[1,2,3,4],'read-only previous SVG IDs cannot create a current target');
h.inspect('state.manifest_valid=false');h.paint=()=>h.svg().getElementById('use-A');
h.point('use-A',125,80);assert.deepEqual(h.numbers(),[1,2,3,4],'a stale map cannot guess identities');
""")

    def test_client_bulk_selection_intersects_properties_and_blocks_changed_sources(self):
        self.run_client(r"""
const initial=figure('B',{history:[{action:'accepted',target_attempt:'/trial/attempt-01'},{action:'applied',target_attempt:'/trial/attempt-02'},{action:'accepted',version:{figure_sha256:'legacy-hash'}}]});
const h=harness(initial);await h.start();
assert.deepEqual(h.node('history-list').children.map(row=>row.textContent),['accepted · attempt-01','applied · attempt-02','accepted · version legacy-h']);
h.choose('semantic-list',JSON.stringify({category:'A'}));
assert.deepEqual(h.node('property').children.map(option=>option.value),['','color'],'bulk editable properties must intersect every real mapped member');
h.choose('property','color');h.input('property-value','#112233');h.input('instruction','Use this color for category A.');
await h.submit();assert.equal(h.posted.length,1);
assert.deepEqual(h.posted[0].version,initial.version);
assert.deepEqual(h.posted[0].requests[0].selector,{category:'A'});
assert.equal(h.posted[0].requests[0].property,'color');assert.equal(h.posted[0].requests[0].value,'#112233');
assert.equal(h.posted[0].requests[0].annotation_number,1);assert.deepEqual(h.posted[0].requests[0].version,initial.version);
const anchor=h.posted[0].requests[0].anchor_mm;
assert.ok(Number.isFinite(anchor.x)&&Number.isFinite(anchor.y)&&anchor.x>=0&&anchor.x<=120&&anchor.y>=0&&anchor.y<=90);
assert.equal(h.node('instruction').disabled,true,'saved instructions must be read-only');
h.choose('semantic-list',JSON.stringify({category:'B'}));h.input('instruction','Keep group B separate.');
await h.submit();assert.equal(h.posted.length,2);assert.equal(h.posted[1].requests[0].annotation_number,2);
h.data={...h.data,source_current:false};await h.click('reload');
assert.equal(h.node('save').disabled,true);
h.point('use-A');h.input('instruction','Must refuse stale source.');await h.submit();
assert.equal(h.posted.length,2,'a changed source prevents sending any batch');
""")

    def test_reload_and_queue_responses_never_rebind_an_old_svg_annotation(self):
        self.run_client(r"""
const a=figure('A',{manifest_valid:false,elements:[]}),b=figure('B',{manifest_valid:false,elements:[],panel:{width_mm:240,height_mm:180}});
const h=harness(a);await h.start();h.region();h.input('instruction','Move this region label.');
assert.deepEqual(h.numbers(),[1]);assert.equal(h.node('save').disabled,false);
let resolvePreview;
h.data=b;h.override=path=>path.startsWith('/api/preview.svg')?new Promise(resolve=>{resolvePreview=resolve;}):undefined;
const reload=h.click('reload');await tick();
assert.equal(h.svg().name,'SVG-A');assert.equal(h.node('save').disabled,true);
await h.submit();assert.equal(h.posted.length,0,'saving is frozen while a replacement preview is loading');
resolvePreview(jsonResponse({error:'Preview failed'},false));await reload;
assert.equal(h.svg().name,'SVG-A');assert.equal(h.node('instruction').value,'Move this region label.');assert.equal(h.node('save').disabled,false);
h.override=(path,options)=>{
 if(path!=='/api/requests/batch')return undefined;
 const payload=JSON.parse(options.body);h.posted.push(payload);
 const item={...payload.requests[0],id:'saved',status:'pending',element_ids:[],current_version:false};
 h.data={...b,requests:[item]};return jsonResponse({requests:[item],state:h.data});
};
await h.submit();assert.equal(h.posted.length,1);
assert.deepEqual(h.posted[0].version,a.version);assert.deepEqual(h.posted[0].requests[0].version,a.version);
assert.deepEqual(h.posted[0].requests[0].region_mm,{x:5,y:10,width:20,height:15});
assert.equal(h.posted[0].requests[0].annotation_number,1);
assert.equal(h.svg().name,'SVG-A');assert.equal(h.node('dimensions').textContent,'120.0 × 90.0 mm');
assert.equal(h.node('request-count').textContent,'1','a queue response for a newer export must be rebound to the visible version');
h.override=null;await h.click('reload');
assert.equal(h.svg().name,'SVG-B');assert.equal(h.node('dimensions').textContent,'240.0 × 180.0 mm');
assert.deepEqual(h.numbers(),[],'a new figure version must not inherit old geometry or notes');
assert.equal(h.node('save').disabled,true);
""")

    def test_independent_instructions_switch_remove_and_batch_failure_keeps_drafts(self):
        self.run_client(r"""
const h=harness(figure());await h.start();
h.point('use-A');h.choose('property','color');h.input('property-value','#112233');h.input('instruction','First independent instruction.');
h.point('use-B');h.input('instruction','Second independent instruction.');
h.point('text-A');h.input('instruction','Third independent instruction.');
assert.deepEqual(h.numbers(),[1,2,3]);
h.chip(1);assert.equal(h.node('instruction').value,'First independent instruction.');assert.equal(h.node('property-value').value,'#112233');
h.chip(2);assert.equal(h.node('instruction').value,'Second independent instruction.');assert.equal(h.node('property').value,'','property edits do not bleed across notes');
h.click('remove-annotation');assert.deepEqual(h.numbers(),[1,3],'removing one annotation must not renumber its neighbours');
h.point('stroke');assert.deepEqual(h.numbers(),[1,3,4]);assert.equal(h.node('instruction').value,'');
let resolveBatch;
h.override=(path,options)=>{if(path!=='/api/requests/batch')return undefined;h.posted.push(JSON.parse(options.body));return new Promise(resolve=>{resolveBatch=resolve;});};
const saving=h.submit();await tick();
assert.equal(h.node('save').disabled,true);assert.equal(h.node('reload').disabled,true);assert.equal(h.node('instruction').disabled,true);
h.point('use-B');h.click('clear');h.click('remove-annotation');
assert.deepEqual(h.numbers(),[1,3,4],'saving freezes new selections, clearing and removal');
resolveBatch(jsonResponse({error:'The second requested change is invalid.'},false));await saving;h.override=null;
assert.equal(h.posted.length,1);assert.deepEqual(h.posted[0].requests.map(item=>item.annotation_number),[1,3],'only filled drafts are submitted, leaving the blank annotation untouched');
assert.equal(h.posted[0].requests[0].element_id,'group-A');assert.equal(h.posted[0].requests[1].element_id,'key-A');
assert.equal(h.posted[0].requests[0].property,'color');assert.equal(h.posted[0].requests[1].property,undefined);
assert.match(h.node('message').textContent,/draft instructions have been kept/);
h.chip(1);assert.equal(h.node('instruction').value,'First independent instruction.');assert.equal(h.node('instruction').disabled,false);
h.chip(3);assert.equal(h.node('instruction').value,'Third independent instruction.');assert.equal(h.node('instruction').disabled,false);
await h.submit();assert.equal(h.posted.length,2);
assert.deepEqual(h.posted[1].requests,h.posted[0].requests,'retry preserves complete independent requests');
h.chip(4);assert.equal(h.node('instruction').disabled,false);assert.equal(h.node('instruction').value,'');
h.chip(1);assert.equal(h.node('instruction').disabled,true,'successful saving marks only committed notes read-only');
""")

    def test_refresh_restores_same_version_and_isolates_a_new_version(self):
        self.run_client(r"""
const storage=new Map(),h=harness(figure('A'),storage);await h.start();
h.point('use-A');h.input('instruction','A persisted point instruction.');h.point('use-B');h.input('instruction','A second persisted instruction.');
const restored=harness(figure('A'),storage);await restored.start();
assert.deepEqual(restored.numbers(),[1,2]);assert.equal(restored.node('instruction').value,'A second persisted instruction.');
restored.chip(1);assert.equal(restored.node('instruction').value,'A persisted point instruction.');
await restored.submit();assert.deepEqual(restored.posted[0].requests.map(item=>item.annotation_number),[1,2]);
const newer=harness(figure('B'),storage);await newer.start();assert.deepEqual(newer.numbers(),[]);assert.equal(newer.node('save').disabled,true);
newer.point('use-A');assert.deepEqual(newer.numbers(),[1]);assert.equal(newer.node('instruction').value,'');
""")

    def test_clear_restarts_unsaved_numbers_without_reusing_saved_or_undone_numbers(self):
        self.run_client(r"""
const h=harness(figure());await h.start();h.point('use-A');h.point('use-B');assert.deepEqual(h.numbers(),[1,2]);
h.click('clear');assert.deepEqual(h.numbers(),[]);h.point('text-A');assert.deepEqual(h.numbers(),[1]);
h.click('clear');await h.click('reload');h.point('use-A');assert.deepEqual(h.numbers(),[1],'repeated clearing and same-version Reload figure keep numbering at one');
h.input('instruction','Save annotation one permanently.');await h.submit();
h.click('new-instruction');assert.deepEqual(h.numbers(),[1,2],'a saved target supports a separate new instruction');
h.input('instruction','This second draft will be cleared.');h.click('clear');assert.deepEqual(h.numbers(),[1]);
h.point('use-B');assert.deepEqual(h.numbers(),[1,2],'clear restarts after saved numbers, never reuses saved one');
h.click('clear');await h.click('undo');assert.deepEqual(h.numbers(),[]);
h.point('use-A');assert.deepEqual(h.numbers(),[2],'undone saved numbers remain occupied');
h.input('instruction','Use a fresh annotation after undo.');await h.submit();assert.equal(h.posted[1].requests[0].annotation_number,2);
""")

    def test_same_version_reload_keeps_memory_drafts_when_storage_is_unavailable(self):
        self.run_client(r"""
const h=harness(figure(),new Map(),true);await h.start();
h.point('use-A');h.input('instruction','Keep this instruction even when browser storage is blocked.');
h.choose('property','color');h.input('property-value','#334455');
await h.click('reload');assert.deepEqual(h.numbers(),[1]);
assert.equal(h.node('instruction').value,'Keep this instruction even when browser storage is blocked.');
assert.equal(h.node('property').value,'color');assert.equal(h.node('property-value').value,'#334455');
await h.submit();assert.equal(h.posted.length,1);assert.equal(h.posted[0].requests[0].instruction,'Keep this instruction even when browser storage is blocked.');
assert.equal(h.posted[0].requests[0].value,'#334455');
""")


if __name__ == "__main__":
    unittest.main()
