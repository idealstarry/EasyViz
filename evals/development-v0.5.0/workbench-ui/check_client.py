#!/usr/bin/env python3
"""Exercise the real workbench client with deterministic local service responses.

This verifies event and version handling. It does not claim browser layout QA.
"""
from pathlib import Path
import importlib.util
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("workbench_tests", ROOT / "tests/test_figure_workbench.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
node = shutil.which("node")
if not node:
    raise SystemExit("Node is required to run the client contract checks.")

SETUP = r"""
function connected(initial=figure('A')) {
  const h=harness({...initial,attempt_id:'attempt-A',project_id:'project'});
  const currentVersion=()=>JSON.stringify(h.data.version);
  h.jobs=[];h.attempts=[{id:'attempt-A',name:'attempt-01',panel:{width_mm:120,height_mm:90},accepted:false,files:{svg:'/attempts/attempt-A/panel.svg'}}];
  h.data={...h.data,attempt_id:'attempt-A',project_id:'project'};
  h.caps={preview:{supported:true,properties:['color','alpha','linewidth'],reason:''},agent:{automatic_dispatch:false}};
  h.calls=[];h.previewJob=null;h.jobReadError=false;
  h.override=async(path,options)=>{
    if(!path.startsWith('/api/'))return undefined;
    const payload=options?.body?JSON.parse(options.body):null;
    if(path==='/api/state'||path==='/api/requests/batch'||path==='/api/undo'||path.startsWith('/api/preview.svg'))return undefined;
    h.calls.push({path,payload});
    if(path==='/api/capabilities')return jsonResponse(h.caps);
    if(path==='/api/attempts')return jsonResponse({current_attempt_id:h.data.attempt_id,attempts:h.attempts});
    if(path==='/api/jobs'&&!payload)return jsonResponse({jobs:h.jobs});
    if(path==='/api/jobs'&&payload){
      if(JSON.stringify(payload.version)!==currentVersion())return jsonResponse({error:'The viewed source is stale.'},false);
      h.previewJob={id:'job-1',status:'queued',source_attempt_id:h.data.attempt_id,target_attempt_id:null,request_ids:payload.request_ids,agent_request_ids:[],message:'Queued'};
      h.jobs=[h.previewJob];return jsonResponse({job:h.previewJob});
    }
    if(path==='/api/jobs/job-1'){
      if(h.jobReadError)throw new Error('Service disconnected');
      return jsonResponse({job:h.previewJob});
    }
    if(path==='/api/jobs/job-1/cancel'){
      h.previewJob={...h.previewJob,status:'cancelled',message:'Renderer stopped'};h.jobs=[h.previewJob];return jsonResponse({job:h.previewJob});
    }
    if(path==='/api/attempts/switch'){
      const attempt=h.attempts.find(item=>item.id===payload.attempt_id);
      if(!attempt)return jsonResponse({error:'Unknown attempt'},false);
      h.attemptStates??=new Map();h.attemptStates.set(h.data.attempt_id,h.data);
      h.data=h.attemptStates.get(attempt.id)||{...figure(payload.attempt_id==='attempt-A'?'A':payload.attempt_id==='attempt-R'?'R':'B'),attempt_id:attempt.id,project_id:'project',figure_name:attempt.name};
      return jsonResponse({state:h.data});
    }
    if(path==='/api/attempts/accept'){
      const attempt=h.attempts.find(item=>item.id===payload.attempt_id);attempt.accepted=true;
      return jsonResponse({acceptance:{attempt_id:attempt.id},state:h.data});
    }
    if(path==='/api/attempts/restore'){
      const attempt={id:'attempt-R',name:'restored-01',panel:{width_mm:120,height_mm:90},accepted:false,files:{}};
      h.attempts.push(attempt);
      return jsonResponse({attempt,state:h.data});
    }
    throw new Error('Unexpected connected request '+path);
  };
  return h;
}
"""
# The base harness intercepts synchronously; return undefined synchronously when
# delegating to its old endpoints, and a promise only for the new API contract.
SETUP = SETUP.replace("h.override=async(path,options)=>{", "h.override=(path,options)=>{")

SCENARIOS = {
    "editable_identity_and_structured_save": r"""
const initial=figure('A');initial.elements[1].editable_values={color:'#2581B9',alpha:1};
const h=connected(initial);await h.start();await tick();
h.point('use-A');assert.equal(h.node('selection-details').hidden,false);
assert.equal(h.node('target-details').hidden,false);assert.ok(h.node('target-identity').children.length);
h.choose('property','color');assert.match(h.node('property-help').textContent,/Current: #2581B9/);
h.input('property-value','#E47751');await h.submit();
assert.equal(h.posted.length,1);assert.match(h.posted[0].requests[0].instruction,/Set Color to #E47751/);
assert.equal(h.node('preview-edits').hidden,false);assert.equal(h.node('preview-edits').disabled,false);
assert.match(h.node('workflow-description').textContent,/does not start an Agent automatically/);
""",
    "preview_completion_keeps_new_drafts": r"""
const h=connected();await h.start();await tick();h.point('use-A');h.choose('property','color');h.input('property-value','#E47751');await h.submit();
await h.click('preview-edits');assert.equal(h.previewJob.status,'queued');assert.equal(h.node('preview-edits').disabled,true);
h.point('use-B');h.input('instruction','Keep this separate request draft.');
h.attempts.push({id:'attempt-B',name:'attempt-02',panel:{width_mm:120,height_mm:90},accepted:false,files:{}});
h.previewJob={...h.previewJob,status:'succeeded',target_attempt_id:'attempt-B',message:'Exports checked',agent_request_ids:['needs-agent']};h.jobs=[h.previewJob];
h.data.requests=h.data.requests.map(item=>({...item,status:'applied',result:{message:'Updated color from plotting code.'}}));
await h.inspect('pollJob()');assert.equal(h.inspect('state.attempt_id'),'attempt-A','new draft must prevent an automatic view change');
assert.equal(h.node('open-job-result').hidden,false);assert.match(h.node('job-detail').textContent,/instruction remains for your Agent/);
assert.equal(h.node('instruction').value,'Keep this separate request draft.');assert.match(h.node('request-list').children[0].children.at(-1).textContent,/Updated color/);
await h.click('open-job-result');assert.equal(h.inspect('state.attempt_id'),'attempt-B');
assert.deepEqual(h.numbers(),[],'new version cannot inherit old targets');
""",
    "preview_auto_open_accept_restore": r"""
const h=connected();await h.start();await tick();h.point('use-A');h.choose('property','alpha');h.input('property-value','0.8');await h.submit();await h.click('preview-edits');
h.attempts.push({id:'attempt-B',name:'attempt-02',panel:{width_mm:120,height_mm:90},accepted:false,files:{svg:'/attempts/attempt-B/panel.svg',pdf:'/attempts/attempt-B/panel.pdf'}});
h.previewJob={...h.previewJob,status:'succeeded',target_attempt_id:'attempt-B',message:'Exports checked'};h.jobs=[h.previewJob];await h.inspect('pollJob()');
assert.equal(h.inspect('state.attempt_id'),'attempt-B');assert.equal(h.svg().name,'SVG-B');
await h.click('accept-attempt');assert.equal(h.node('accept-attempt').textContent,'Accepted');assert.equal(h.node('restore-attempt').hidden,false);
await h.click('restore-attempt');assert.equal(h.inspect('state.attempt_id'),'attempt-R');assert.equal(h.svg().name,'SVG-R');
assert.equal(h.calls.find(item=>item.path==='/api/attempts/accept').payload.validation,'Reviewed by the user in the EasyViz workbench.');
""",
    "remaining_requests_return_to_source_and_preserve_new_drafts": r"""
const h=connected();await h.start();await tick();
h.point('use-A');h.choose('property','color');h.input('property-value','#E47751');
h.region();h.input('instruction','Move this annotation without changing the data.');await h.submit();
const remaining=h.data.requests[1].id;await h.click('preview-edits');
h.attempts.push({id:'attempt-B',name:'attempt-02',panel:{width_mm:120,height_mm:90},accepted:false,files:{}});
h.data.requests=h.data.requests.map((item,index)=>index===0?{...item,status:'applied'}:item);
h.previewJob={...h.previewJob,status:'succeeded',target_attempt_id:'attempt-B',agent_request_ids:[remaining],message:'Color rendered'};h.jobs=[h.previewJob];
await h.inspect('pollJob()');assert.equal(h.inspect('state.attempt_id'),'attempt-B');assert.equal(h.node('review-remaining-requests').hidden,false);
await h.click('accept-attempt');assert.equal(h.node('accept-attempt').textContent,'Accepted');
assert.equal(h.node('review-remaining-requests').disabled,false,'finishing acceptance must re-enable the remaining-request action without another job response');
h.point('use-B');h.input('instruction','Keep this new-attempt draft.');
await h.click('review-remaining-requests');assert.equal(h.inspect('state.attempt_id'),'attempt-A');
assert.equal(h.node('requests-panel').hidden,false);assert.equal(h.node('requests-tab').attributes['aria-selected'],'true');
assert.equal(h.inspect("state.requests.find(item=>item.id==='"+remaining+"').status"),'pending');
assert.equal(h.inspect("state.requests.find(item=>item.id==='"+remaining+"').version.figure_sha256"),'A');
assert.match(h.node('message').textContent,/original source attempt/);
await h.inspect("switchAttempt('attempt-B')");assert.equal(h.node('instruction').value,'Keep this new-attempt draft.');
""",
    "cancel_and_disconnect_do_not_claim_success": r"""
const h=connected();await h.start();await tick();h.point('use-A');h.choose('property','color');h.input('property-value','#E47751');await h.submit();await h.click('preview-edits');
await h.click('cancel-job');assert.equal(h.inspect('activeJob.status'),'cancelled');assert.equal(h.inspect('state.attempt_id'),'attempt-A');assert.equal(h.node('open-job-result').hidden,true);
assert.equal(h.node('preview-edits').disabled,false,'a cancelled job must allow retry');
await h.click('preview-edits');h.jobReadError=true;await h.inspect('pollJob()');
assert.equal(h.node('job-title').textContent,'Status unavailable');assert.equal(h.node('open-job-result').hidden,true);assert.match(h.node('message').textContent,/saved instructions remain available/);
assert.equal(h.inspect('state.attempt_id'),'attempt-A');assert.equal(h.data.requests[0].status,'pending');
""",
    "stale_source_blocks_preview_and_retains_annotations": r"""
const h=connected();await h.start();await tick();h.point('use-A');h.choose('property','color');h.input('property-value','#E47751');await h.submit();
h.data={...h.data,source_current:false};await h.click('reload');
assert.equal(h.node('preview-edits').disabled,true);await h.click('preview-edits');assert.equal(h.previewJob,null);
assert.equal(h.numbers()[0],1);assert.equal(h.node('instruction').disabled,true);
""",
}

for name, scenario in SCENARIOS.items():
    wrapped = module.CLIENT_HARNESS + "\n" + SETUP + "\n(async()=>{\n" + scenario + "\n})().catch(error=>{console.error(error);process.exitCode=1;});"
    result = subprocess.run([node, "-e", wrapped, str(ROOT / "skills/easyviz/scripts/workbench/workbench.js")], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise SystemExit(f"FAIL {name}\n{result.stdout}{result.stderr}")
    print(f"PASS {name}")
