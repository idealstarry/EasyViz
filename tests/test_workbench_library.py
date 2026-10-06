"""Independent library, portable document and Agent-submit HTTP contracts."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/easyviz/scripts"
sys.path.insert(0, str(SCRIPTS))
from figure_workbench import create_server, existing_workbench
import test_figure_workbench as legacy_workbench


class WorkbenchLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="easyviz-library-")
        self.project = Path(self.temp.name).resolve()
        self.server = create_server(project_dir=self.project)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, payload=None, *, raw=None, headers=None):
        supplied = {}
        body = raw
        if payload is not None:
            body = json.dumps(payload).encode()
            supplied["Content-Type"] = "application/json"
        if body is not None:
            supplied.update(Origin=self.origin, **{"X-EasyViz-Token": self.server.service.token})
        supplied.update(headers or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        connection.request(method, path, body, supplied)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def data(self, method, path, payload=None, **kwargs):
        status, body = self.request(method, path, payload, **kwargs)
        return status, json.loads(body)

    def render_fixture(self, formats=None):
        import render
        data = self.project / "data.csv"
        data.write_text("x,y,group\n1,2,A\n2,3,A\n3,4,A\n1,4,B\n2,5,B\n3,6,B\n")
        spec = {"chart": "scatter", "fields": {"x": "x", "y": "y", "group": "group"},
                "labels": {"x": "X", "y": "Y"}, "formats": formats or ["svg"], "seed": 41,
                "layout": {"width_mm": 100, "height_mm": 80, "font": "DejaVu Sans", "font_size_pt": 8}}
        if formats is None:
            spec.pop("formats")  # Exercise the actual default SVG-only export.
        source = self.project / "spec.json"
        source.write_text(json.dumps(spec))
        attempt = self.project / "attempt-01"
        render.render(data, spec, attempt, spec_path=source, track="create")
        return attempt

    def test_empty_project_opens_without_fake_figure_and_rejects_edits(self):
        status, state = self.data("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(state["empty"])
        self.assertEqual(state["token"], self.server.service.token)
        self.assertNotIn("version", state)
        self.assertEqual(self.data("GET", "/api/library")[1]["attempts"], [])
        self.assertEqual(self.request("GET", "/")[0], 200)
        self.assertEqual(self.request("GET", "/api/preview.svg")[0], 404)
        self.assertEqual(self.data("POST", "/api/requests/batch", {"version": {}, "requests": []})[0], 400)

    def test_refresh_discovers_source_bound_svg_only_attempt_and_no_arbitrary_images(self):
        arbitrary = self.project / "ordinary-images"
        arbitrary.mkdir()
        (arbitrary / "panel.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20mm" height="20mm" viewBox="0 0 20 20"/>')
        (arbitrary / "panel.pdf").write_bytes(b"PDF export")
        attempt = self.render_fixture()
        status, library = self.data("POST", "/api/library/refresh", {})
        self.assertEqual(status, 200)
        self.assertEqual(len(library["attempts"]), 1)
        row = library["attempts"][0]
        self.assertEqual(Path(row["path"]), attempt)
        self.assertEqual(set(row["files"]), {"svg"})
        self.assertEqual(self.data("POST", "/api/attempts/switch", {"attempt_id": row["id"]})[0], 200)
        self.assertEqual(self.request("GET", "/files/panel.png")[0], 404)

    def test_svg_rerender_preserves_but_hides_previous_pdf_png_in_state_library_and_downloads(self):
        attempt = self.render_fixture(["svg", "pdf", "png"])
        original = {name: (attempt / name).read_bytes() for name in ("panel.pdf", "panel.png")}
        row = self.server.service.register_attempt(attempt)
        self.server.service.switch_attempt(row["id"])
        self.assertEqual(set(self.data("GET", "/api/library")[1]["attempts"][0]["files"]), {"svg", "pdf", "png"})
        self.render_fixture()
        state = self.data("GET", "/api/state")[1]
        self.assertIn("panel.svg", state["files"])
        self.assertNotIn("panel.pdf", state["files"])
        self.assertNotIn("panel.png", state["files"])
        self.assertEqual(set(self.data("GET", "/api/library")[1]["attempts"][0]["files"]), {"svg"})
        for name, raw in original.items():
            self.assertEqual((attempt / name).read_bytes(), raw, "older exports remain available on disk")
            self.assertEqual(self.request("GET", "/files/" + name)[0], 404)
            self.assertEqual(self.request("GET", f'/api/attempts/{row["id"]}/files/{name}')[0], 404)
        self.assertEqual(self.request("GET", "/files/panel.svg")[0], 200)
        # Merely deleting current QA cannot restore stale optional formats for
        # an otherwise source-bound EasyViz attempt.
        (attempt / "qa.json").unlink()
        self.assertNotIn("panel.pdf", self.data("GET", "/api/state")[1]["files"])

    def test_ev_round_trip_import_keeps_original_source_and_vector_map(self):
        attempt = self.render_fixture()
        row = self.server.service.register_attempt(attempt)
        self.server.service.switch_attempt(row["id"])
        original = (attempt / "panel.svg").read_bytes()
        status, archive = self.request("GET", "/files/panel.ev")
        self.assertEqual(status, 200)
        status, imported = self.data("POST", "/api/documents/import?name=example.ev", raw=archive,
                                     headers={"Content-Type": "application/octet-stream"})
        self.assertEqual(status, 200, imported)
        target = Path(imported["attempt"]["path"])
        self.assertNotEqual(target, attempt)
        self.assertTrue(target.is_relative_to(self.project))
        self.assertEqual((attempt / "panel.svg").read_bytes(), original)
        self.assertTrue(imported["state"]["manifest_valid"])
        self.assertTrue(imported["state"]["source_current"])
        self.assertEqual(imported["state"]["panel"], {"width_mm": 100, "height_mm": 80})
        self.assertTrue(imported["state"]["elements"])
        self.assertEqual(set(imported["attempt"]["files"]), {"svg"})
        self.assertEqual(len(self.data("GET", "/api/library")[1]["attempts"]), 2)

    def test_import_rejects_plain_exports_renames_and_foreign_origins(self):
        raw = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
        upload = {"Content-Type": "application/octet-stream"}
        for name in ("panel.svg", "panel.pdf", "panel.png", "..%2Fpanel.ev", "panel.ev"):
            with self.subTest(name=name):
                self.assertEqual(self.data("POST", "/api/documents/import?name=" + name, raw=raw, headers=upload)[0], 400)
        self.assertEqual(self.data("POST", "/api/documents/import?name=panel.ev", raw=raw,
                                  headers={**upload, "Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.data("POST", "/api/documents/import?name=panel.ev", raw=raw,
                                  headers={**upload, "X-EasyViz-Token": "wrong"})[0], 403)
        self.assertEqual(self.data("GET", "/api/library")[1]["attempts"], [])
        self.assertFalse(list(self.project.glob("ev-import-*")))

    def test_agent_http_submit_uses_explicit_source_and_never_reports_success_at_queue(self):
        attempt = self.render_fixture()
        row = self.server.service.register_attempt(attempt)
        self.server.service.switch_attempt(row["id"])
        state = self.server.service.state()
        job = {"id": "job-" + "a" * 32, "status": "queued", "kind": "agent", "target_attempt_id": None}
        with patch.object(self.server.service, "submit_agent_job", return_value={"job": job}) as submit:
            payload = {"version": state["version"], "request_ids": ["request-example"], "attempt_id": row["id"]}
            status, result = self.data("POST", "/api/agent/jobs", payload)
            self.assertEqual(status, 200)
            submit.assert_called_once_with(state["version"], ["request-example"], row["id"])
            self.assertEqual(result["job"]["status"], "queued")
            self.assertIsNone(result["job"]["target_attempt_id"])
            self.assertEqual(self.data("POST", "/api/agent/jobs", {**payload, "command": "arbitrary"})[0], 400)

    def test_instance_reuse_requires_matching_scope_and_live_session(self):
        endpoint = self.server.service.storage / "workbench.json"
        record = {"port": self.server.server_port, "token": self.server.service.token}
        endpoint.write_text(json.dumps(record))
        self.assertEqual(existing_workbench(self.project), self.origin + "/")
        endpoint.write_text(json.dumps({**record, "token": "stale"}))
        self.assertIsNone(existing_workbench(self.project))
        endpoint.write_text(json.dumps({**record, "port": True}))
        self.assertIsNone(existing_workbench(self.project))

    def test_reopening_project_with_missing_last_figure_still_opens_the_library(self):
        attempt = self.render_fixture()
        row = self.server.service.register_attempt(attempt)
        self.server.service.switch_attempt(row["id"])
        (attempt / "panel.svg").unlink()
        reopened = create_server(project_dir=self.project)
        try:
            self.assertIsNone(reopened.service.app)
            self.assertTrue(reopened.service.list_attempts()["attempts"][0]["unavailable"])
        finally:
            reopened.server_close()


class WorkbenchSubmitClientTests(unittest.TestCase):
    run_client = legacy_workbench.WorkbenchClientTests.run_client

    def test_rename_updates_labels_and_retains_drafts_across_reload(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let renamed=0;
let row={id:'attempt-original',name:h.data.figure_name,preview_url:'/preview',panel:h.data.panel};
h.override=(path,options)=>{
 if(path==='/api/library')return jsonResponse({attempts:[row]});
 if(path==='/api/attempts/rename'){
  renamed++;const payload=JSON.parse(options.body);
  assert.deepEqual(payload,{attempt_id:'attempt-original',name:'心肌修复 · HDR'});
  h.data={...h.data,figure_name:payload.name};row={...row,name:payload.name};
  return jsonResponse({attempt:row,state:h.data});
 }
};
await h.start();h.point('use-A');h.input('instruction','Keep the first comment.');
h.point('use-B');h.input('instruction','Keep the second comment.');
const originalSvg=h.svg(),version=h.inspect('JSON.stringify(state.version)');
await h.click('figure-name');assert.equal(h.node('figure-name-form').hidden,false);
h.input('figure-name-input','  心肌修复 · HDR  ');
await h.node('figure-name-form').listeners.submit({preventDefault(){}});
assert.equal(renamed,1);assert.equal(h.node('figure-name').textContent,row.name);
assert.equal(h.node('current-label').textContent,'Current · '+row.name);
assert.equal(h.node('attempt-list').options[0].textContent,row.name);
assert.equal(h.node('library-list').children[0].children[1].textContent,row.name);
assert.equal(h.node('figure-name-form').hidden,true);
assert.equal(h.svg(),originalSvg,'renaming cannot replace the SVG or disturb selection');
assert.equal(h.inspect('JSON.stringify(state.version)'),version);
assert.equal(h.inspect('annotations.map(note=>note.instruction).join("|")'),'Keep the first comment.|Keep the second comment.');
assert.equal(h.posted.length,0,'renaming is metadata, not a render request');
const restarted=harness(h.data,h.storage);await restarted.start();
assert.equal(restarted.node('figure-name').textContent,row.name);
assert.deepEqual(restarted.numbers(),[1,2]);
assert.equal(restarted.inspect('annotations.map(note=>note.instruction).join("|")'),'Keep the first comment.|Keep the second comment.');
''')

    def test_rename_failure_cancel_and_busy_state_do_not_lose_edits(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let calls=0,finish;
h.override=(path)=>{
 if(path==='/api/attempts/rename'){calls++;return new Promise(resolve=>{finish=resolve;});}
};
await h.start();h.point('use-A');h.input('instruction','Retain this unsaved comment.');
await h.click('rename-figure');h.input('figure-name-input','\u0001');
await h.node('figure-name-form').listeners.submit({preventDefault(){}});
assert.equal(calls,0);assert.match(h.node('message').textContent,/1–120 characters/);
h.input('figure-name-input','Custom name');
const pending=h.node('figure-name-form').listeners.submit({preventDefault(){}});await tick();
assert.equal(h.node('rename-figure').disabled,true);assert.equal(h.node('cancel-figure-name').disabled,true);
await h.click('rename-figure');assert.equal(calls,1);
finish(jsonResponse({error:'The name could not be saved.'},false));await pending;
assert.equal(h.node('figure-name').textContent,'same-attempt');
assert.equal(h.node('figure-name-form').hidden,false);assert.equal(h.node('figure-name-input').value,'Custom name');
assert.equal(h.inspect('annotations[0].instruction'),'Retain this unsaved comment.');
assert.equal(h.node('rename-figure').disabled,false);
h.node('figure-name-input').listeners.keydown({key:'Escape',preventDefault(){}});
assert.equal(h.node('figure-name-form').hidden,true);assert.equal(h.posted.length,0);
''')

    def test_rename_migrates_legacy_drafts_and_treats_name_as_plain_text(self):
        self.run_client(r'''
const initial=figure('A',{attempt_id:'attempt-original'}),storage=new Map();
storage.set('easyviz-annotations:'+initial.figure_name+':'+JSON.stringify(initial.version),JSON.stringify({nextNumber:2,activeNumber:1,notes:[{number:1,element_ids:['group-A'],instruction:'Legacy comment.'}]}));
const h=harness(initial,storage);
h.override=(path,options)=>{
 if(path==='/api/attempts/rename'){
  const name=JSON.parse(options.body).name;h.data={...h.data,figure_name:name};
  return jsonResponse({attempt:{id:'attempt-original',name},state:h.data});
 }
};
await h.start();assert.deepEqual(h.numbers(),[1]);
await h.click('rename-figure');h.input('figure-name-input','<b>Figure name</b>');
await h.node('figure-name-form').listeners.submit({preventDefault(){}});
assert.equal(h.node('figure-name').textContent,'<b>Figure name</b>');assert.equal(h.node('figure-name').children.length,0);
const restarted=harness(h.data,storage);await restarted.start();assert.deepEqual(restarted.numbers(),[1]);
assert.equal(restarted.inspect('annotations[0].instruction'),'Legacy comment.');
''')

    def test_named_drafts_stay_with_their_project_and_attempt(self):
        self.run_client(r'''
const storage=new Map(),first=figure('A',{project_id:'project-one',attempt_id:'attempt-original'});
const a=harness(first,storage);await a.start();a.point('use-A');a.input('instruction','Only project one.');
const b=harness({...first,project_id:'project-two'},storage);await b.start();
assert.deepEqual(b.numbers(),[],'the same folder, attempt ID and SVG in another project cannot inherit comments');
b.point('use-B');b.input('instruction','Only project two.');
const again=harness(first,storage);await again.start();assert.deepEqual(again.numbers(),[1]);
assert.equal(again.inspect('annotations[0].instruction'),'Only project one.');
const other=harness({...first,attempt_id:'attempt-copy'},storage);await other.start();assert.deepEqual(other.numbers(),[]);
''')

    def test_request_pages_open_full_comments_without_editing_saved_instructions(self):
        self.run_client(r'''
const version=figure('A').version;
const requests=Array.from({length:7},(_,index)=>({
 id:'request-'+(index+1),version,status:'pending',current_version:true,annotation_number:index+1,
 element_ids:['group-A'],element:{label:'A',role:'point-group'},
 instruction:'Instruction '+(index+1)+': '+('Retain the measured values. '.repeat(35))+'<strong>plain text</strong>'
}));
const h=harness(figure('A',{requests}));await h.start();await h.click('requests-tab');
const cards=()=>h.descendants(h.node('request-list')).filter(node=>node.className==='request-item');
const labels=()=>cards().map(card=>h.descendants(card).find(node=>node.className==='request-label').textContent);
assert.equal(cards().length,3,'long queues show three request cards at a time');
assert.deepEqual(labels(),['#1 · A','#2 · A','#3 · A']);
assert.equal(h.node('requests-previous').disabled,true);assert.equal(h.node('requests-next').disabled,false);
const firstRead=h.descendants(cards()[0]).find(node=>node.tagName==='BUTTON'&&node.textContent==='Read instruction');
assert.ok(firstRead,'a concise request card exposes the full saved instruction');
firstRead.listeners.click();
assert.equal(h.node('note-dialog').open,true);assert.equal(h.node('note-dialog-text').tagName,'P');
assert.equal(h.node('note-dialog-text').textContent,requests[0].instruction,'full instructions retain literal text, including markup-looking characters');
assert.equal(h.data.requests[0].instruction,requests[0].instruction);
await h.click('note-dialog-close');assert.equal(h.node('note-dialog').open,false);
await h.click('requests-next');assert.deepEqual(labels(),['#4 · A','#5 · A','#6 · A']);
await h.click('requests-next');assert.deepEqual(labels(),['#7 · A']);assert.equal(h.node('requests-next').disabled,true);
const lastRead=h.descendants(cards()[0]).find(node=>node.tagName==='BUTTON'&&node.textContent==='Read instruction');
lastRead.listeners.click();assert.equal(h.node('note-dialog-text').textContent,requests[6].instruction);
await h.click('note-dialog-close');await h.click('requests-previous');
assert.deepEqual(labels(),['#4 · A','#5 · A','#6 · A']);
assert.equal(h.posted.length,0,'reading and paging saved instructions cannot resubmit them');
assert.equal(h.data.requests.length,7);
''')

    def test_history_pages_preserve_complete_audit_history(self):
        self.run_client(r'''
const history=Array.from({length:7},(_,index)=>({action:'applied',target_attempt:'/project/attempt-'+(index+1)}));
const h=harness(figure('A',{history}));await h.start();await h.click('history-tab');
const rows=()=>h.node('history-list').children.map(row=>h.descendants(row).find(node=>node.className==='attempt-title').textContent);
assert.deepEqual(rows(),['applied · attempt-1','applied · attempt-2','applied · attempt-3']);
assert.equal(h.node('history-previous').disabled,true);
await h.click('history-next');assert.deepEqual(rows(),['applied · attempt-4','applied · attempt-5','applied · attempt-6']);
await h.click('history-next');assert.deepEqual(rows(),['applied · attempt-7']);
assert.equal(h.node('history-next').disabled,true);
await h.click('history-previous');assert.deepEqual(rows(),['applied · attempt-4','applied · attempt-5','applied · attempt-6']);
assert.equal(h.inspect('state.history.length'),7);assert.equal(h.posted.length,0);
''')

    def test_submit_saves_complete_drafts_and_dispatches_once_with_mapped_source(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));
let submitted=0;
h.override=(path,options)=>{
 if(path==='/api/agent')return jsonResponse({backend:'codex',enabled:true,available:true});
 if(path==='/api/library')return jsonResponse({attempts:[],project_name:'Project'});
 if(path==='/api/agent/jobs'){
   submitted++;const payload=JSON.parse(options.body);
   assert.equal(payload.attempt_id,'attempt-original');assert.equal(payload.request_ids.length,4);
   assert.deepEqual(payload.request_ids,h.data.requests.map(item=>item.id),'dispatch includes requests beyond the first visible page');
   assert.equal(payload.version.figure_sha256,'A');
   return jsonResponse({job:{id:'job-test',status:'queued',kind:'agent',target_attempt_id:null}});
 }
};
await h.start();h.point('use-A');h.input('instruction','Make A green.');
h.point('use-B');h.input('instruction','Move B legend right.');
h.point('text-A');h.input('instruction','Use a shorter label for A.');
h.point('stroke');h.input('instruction','Make the axis stroke 0.6 pt.');
await h.click('submit-edits');
assert.equal(submitted,1);assert.equal(h.posted.length,1);assert.equal(h.data.requests.length,4);
assert.deepEqual(h.posted[0].requests.map(item=>item.element_id),['group-A','group-B','key-A','axis-line']);
for(const item of h.posted[0].requests){assert.equal(item.version.figure_sha256,'A');assert.equal(item.property,undefined);assert.equal(item.value,undefined);}
assert.equal(h.node('job-title').textContent,'Submitted · waiting for Agent');
assert.equal(h.node('open-job-result').hidden,true,'queued work is not a finished output');
assert.equal(h.node('submit-edits').disabled,true,'double submit is disabled while running');
assert.equal(h.inspect('annotations.filter(note=>note.saved).length'),4);
''')

    def test_submit_failure_retains_saved_opinions_and_save_drafts_never_dispatches(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let submitted=0;
h.override=(path,options)=>{
 if(path==='/api/agent')return jsonResponse({enabled:true,available:true});
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(path==='/api/agent/jobs'){submitted++;return jsonResponse({error:'Agent is unavailable.'},false);}
};
await h.start();h.point('use-A');h.input('instruction','Make A green.');await h.submit();
assert.equal(submitted,0,'saving drafts cannot silently start an Agent');
await h.click('submit-edits');assert.equal(submitted,1);assert.equal(h.data.requests.length,1);
assert.equal(h.data.requests[0].status,'pending');assert.match(h.node('message').textContent,/Saved instructions have been kept/);
assert.equal(h.inspect('annotations[0].saved'),true);
''')

    def test_empty_library_loads_without_requesting_a_fake_svg(self):
        self.run_client(r'''
const h=harness({empty:true,project_name:'Empty project',token:'session',requests:[],history:[],elements:[]});
let previews=0;
h.override=(path)=>{
 if(path.startsWith('/api/preview.svg'))previews++;
 if(path==='/api/library')return jsonResponse({attempts:[],project_name:'Empty project'});
 if(path==='/api/agent')return jsonResponse({enabled:false,available:true});
};
await h.start();assert.equal(previews,0);assert.equal(h.node('editor-layout').hidden,true);
assert.equal(h.node('figure-library').hidden,false);assert.equal(h.node('figure-name').textContent,'Empty project');
assert.equal(h.node('library-empty').hidden,false);assert.equal(h.node('submit-edits').disabled,true);
''')

    def test_partial_agent_result_exposes_original_requests_without_rebinding_to_preview(self):
        self.run_client(r'''
const original=figure('A',{attempt_id:'attempt-original',requests:[{
 id:'remaining-request',version:{figure_sha256:'A',spec_sha256:'spec-A'},status:'pending',current_version:true,
 instruction:'Move the label right.',annotation_number:2,element_ids:['group-A']}]});
const h=harness(figure('B',{attempt_id:'attempt-preview'}));let switched=null;
h.override=(path,options)=>{
 if(path==='/api/agent')return jsonResponse({enabled:true,available:true});
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(path==='/api/attempts/switch'){
   switched=JSON.parse(options.body);h.data=original;return jsonResponse({state:original});
 }
};
await h.start();
h.inspect(`activeJob={id:'job-partial',kind:'agent',status:'succeeded',source_attempt_id:'attempt-original',target_attempt_id:'attempt-preview',agent_request_ids:['remaining-request'],message:'One request remains.'};renderJob()`);
assert.equal(h.node('review-remaining-requests').hidden,false);
assert.match(h.node('job-detail').textContent,/pending on the original figure/);
await h.click('review-remaining-requests');
assert.equal(switched.attempt_id,'attempt-original');
assert.equal(h.inspect('state.attempt_id'),'attempt-original');
assert.equal(h.inspect('state.requests[0].version.figure_sha256'),'A');
assert.equal(h.node('submit-edits').textContent,'Submit from original');
assert.match(h.node('message').textContent,/another branch from the original/);
assert.match(h.node('handoff-hint').textContent,/annotate the new version/);
h.inspect(`activeJob={id:'job-empty',kind:'agent',status:'succeeded',phase:'agent_handoff',source_attempt_id:'attempt-original',target_attempt_id:null,agent_request_ids:['remaining-request']};renderJob()`);
assert.equal(h.node('job-title').textContent,'No new figure');
assert.equal(h.node('open-job-result').hidden,true);
''')


if __name__ == "__main__":
    unittest.main()
