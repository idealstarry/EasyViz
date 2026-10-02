"""Local figure review boundaries and version-preserving request behavior."""
from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest

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
        for path in ("/","/workbench.css","/workbench.js","/api/preview.svg"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET",path)[0],200)

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


class WorkbenchClientTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is needed for the mocked client runtime check")
    def test_reload_and_queue_responses_never_rebind_an_old_svg_selection(self):
        # Execute the actual client in a minimal DOM with controlled HTTP promises.
        # No browser or real network is needed to reproduce the asynchronous race.
        harness=r'''
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
class Element {
  constructor(name='') {this.name=name;this.value='';this.disabled=false;this.children=[];this.listeners={};this.classList={toggle(){}};}
  addEventListener(name,callback){this.listeners[name]=callback;}
  setAttribute(){}
  replaceChildren(...children){this.children=children;}
  append(...children){this.children.push(...children);}
  add(child){this.children.push(child);}
  querySelectorAll(){return [];}
  getElementById(){return null;}
}
const nodes=new Map();
const node=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
const stateFor=name=>({schema_version:1,figure_name:name,track:'create',version:{figure_sha256:name},panel:{width_mm:name==='A'?120:240,height_mm:name==='A'?90:180},view_box:[10,20,240,180],manifest_valid:false,elements:[],requests:[],files:['panel.svg'],token:'session',selection_message:'Select a region.'});
const a=stateFor('A'),b=stateFor('B');
let phase='initial',resolvePreview,posted=[];
const response=state=>({ok:true,json:async()=>state});
const context=vm.createContext({
  document:{getElementById:node,createElement:()=>new Element(),createElementNS:()=>new Element(),importNode:element=>element},
  Option:class extends Element {constructor(text,value){super(text);this.value=value;}},
  DOMParser:class {parseFromString(text){return {querySelector:()=>null,documentElement:new Element(text)};}},
  fetch:async(path,options)=>{
    if(path==='/api/state')return response(phase==='initial'?a:b);
    if(path.startsWith('/api/preview.svg')){
      if(phase==='pending')return new Promise(resolve=>{resolvePreview=resolve;});
      return {ok:true,text:async()=>phase==='initial'?'SVG-A':'SVG-B'};
    }
    if(path==='/api/requests'){
      const payload=JSON.parse(options.body);posted.push(payload);
      return response({state:{...b,requests:[{id:'saved',status:'pending',instruction:payload.instruction,version:payload.version,current_version:false}]}});
    }
    throw new Error('Unexpected request '+path);
  },console,
});
const inspect=source=>vm.runInContext(source,context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
  await tick();await tick();
  assert.equal(inspect('state.version.figure_sha256'),'A');
  assert.equal(inspect('svg.name'),'SVG-A');
  inspect('region={x:5,y:10,width:20,height:15}');
  phase='pending';
  const reload=inspect('load()');await tick();
  assert.equal(inspect('state.version.figure_sha256'),'A','pending state must not replace visible figure version');
  assert.equal(inspect('svg.name'),'SVG-A');
  assert.equal(node('save').disabled,true);
  await node('request-form').listeners.submit({preventDefault(){}});
  assert.equal(posted.length,0,'submission must be blocked during reload');
  resolvePreview({ok:false,json:async()=>({error:'Preview failed'})});await reload;
  assert.equal(inspect('state.version.figure_sha256'),'A','failed reload must retain original version');
  assert.equal(inspect('region.x'),5);
  assert.equal(node('save').disabled,false);
  phase='queue-response';node('instruction').value='Move this region label.';
  await node('request-form').listeners.submit({preventDefault(){}});
  assert.equal(posted.length,1);
  assert.equal(posted[0].version.figure_sha256,'A');
  assert.deepEqual(posted[0].region_mm,{x:5,y:10,width:20,height:15});
  assert.equal(inspect('state.version.figure_sha256'),'A','newer queue response must not rebind old SVG');
  assert.equal(inspect('state.panel.width_mm'),120);
  assert.equal(inspect('svg.name'),'SVG-A');
  assert.equal(inspect('state.requests[0].current_version'),true);
  phase='success';await inspect('load()');
  assert.equal(inspect('state.version.figure_sha256'),'B');
  assert.equal(inspect('svg.name'),'SVG-B');
  assert.equal(inspect('region'),null,'successful reload clears old coordinates');
  assert.equal(node('save').disabled,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        script=SCRIPT.with_name("workbench")/"workbench.js"
        result=subprocess.run([shutil.which("node"),"-e",harness,str(script)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == "__main__":
    unittest.main()
