"""Original-conversation status and submit behavior in the workbench client."""
from __future__ import annotations

import unittest

import test_figure_workbench as workbench


class WorkbenchSessionClientTests(unittest.TestCase):
    run_client = workbench.WorkbenchClientTests.run_client

    def test_disconnected_button_explains_original_agent_connection_without_starting_worker(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let mutations=0;
h.override=(path,options)=>{
 if(path==='/api/agent')return jsonResponse({backend:'session',enabled:false,available:false,runtime_state:'disconnected'});
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(options?.method==='POST'){mutations++;return jsonResponse({error:'No mutation should be made.'},false);}
};
await h.start();
assert.equal(h.node('connect-agent').textContent,'Connect original Agent');
assert.equal(h.node('agent-label').textContent,'Agent disconnected');
await h.click('connect-agent');await h.click('connect-agent');
assert.equal(mutations,0);assert.equal(h.node('note-dialog').open,true);
assert.match(h.node('note-dialog-text').textContent,/conversation that opened EasyViz/);
assert.match(h.node('note-dialog-text').textContent,/cannot identify or wake/);
assert.equal(h.node('submit-edits').disabled,true);
''')

    def test_live_original_session_submission_keeps_source_attempt_and_real_queue_state(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let submitted=0;
const connection={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',host:'codex',lease_expires_at:Date.now()/1000+120};
h.override=(path,options)=>{
 if(path==='/api/agent')return jsonResponse(connection);
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(path==='/api/agent/jobs'){
  submitted++;const payload=JSON.parse(options.body);
  assert.equal(payload.attempt_id,'attempt-original');
  assert.deepEqual(payload.request_ids,h.data.requests.map(item=>item.id));
  assert.equal(payload.version.figure_sha256,'A');
  return jsonResponse({job:{id:'session-job',backend:'session',kind:'agent',status:'queued',owner_session_id:'original-chat',source_attempt_id:payload.attempt_id,message:'Waiting for the connected original conversation'}});
 }
};
await h.start();
assert.equal(h.node('agent-label').textContent,'Original Agent connected');
assert.match(h.node('agent-label').title,/original-chat/);
h.point('use-A');h.input('instruction','Use black open outlines; keep the same values.');
await h.click('submit-edits');
assert.equal(submitted,1);assert.equal(h.posted.length,1);
assert.equal(h.node('job-title').textContent,'Submitted · waiting for Agent');
assert.match(h.node('message').textContent,/original conversation/);
assert.equal(h.node('submit-edits').disabled,true);
h.inspect("activeJob.status='running';activeJob.phase='session_received';activeJob.claimed_at=new Date().toISOString();activeJob.received_at=activeJob.claimed_at;renderJob()");
assert.equal(h.node('job-title').textContent,'Agent received');
h.inspect("activeJob.phase='session_editing';renderJob()");
assert.equal(h.node('job-title').textContent,'Agent received','legacy phase text cannot invent actual editing evidence');
h.inspect("activeJob.editing_started_at=new Date().toISOString();renderJob()");
assert.equal(h.node('job-title').textContent,'Editing');
''')

    def test_expired_or_unverified_session_cannot_dispatch_and_retains_written_draft(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let jobs=0;
let connection={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',lease_expires_at:Date.now()/1000+120};
h.override=(path)=>{
 if(path==='/api/agent')return jsonResponse(connection);
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(path==='/api/agent/jobs'){jobs++;return jsonResponse({job:{status:'queued'}});}
};
await h.start();h.point('use-A');h.input('instruction','Keep this unsaved comment.');
assert.equal(h.node('submit-edits').disabled,false);
for(const bad of [{...connection,lease_expires_at:Date.now()/1000-1},{...connection,same_session:false},{...connection,owner_session_id:''},{...connection,lease_expires_at:null}]){
 connection=bad;await h.inspect('pollAgent()');
 assert.equal(h.node('submit-edits').disabled,true);
 await h.node('submit-edits').listeners.click();
 assert.equal(jobs,0);assert.equal(h.posted.length,0);
 assert.equal(h.node('instruction').value,'Keep this unsaved comment.');
}
''')

    def test_progress_requires_claim_and_start_evidence_and_keeps_owner_connection_independent(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));
h.override=path=>path==='/api/agent'?jsonResponse({backend:'session',enabled:false,available:false,runtime_state:'disconnected'}):path==='/api/library'?jsonResponse({attempts:[]}):undefined;
await h.start();const timestamp=new Date().toISOString();
h.inspect(`activeJob={id:'job-proof',kind:'agent',backend:'session',status:'queued',phase:'queued',received_at:${JSON.stringify(timestamp)},editing_started_at:${JSON.stringify(timestamp)}};renderJob()`);
assert.equal(h.node('job-title').textContent,'Submitted · waiting for Agent','queued work has not been received even if unrelated timestamps exist');
assert.equal(h.node('agent-label').textContent,'Agent disconnected','a job cannot impersonate a live connection');
h.inspect("activeJob.status='running';delete activeJob.received_at;delete activeJob.editing_started_at;renderJob()");
assert.equal(h.node('job-title').textContent,'Processing','unverified running status does not assert receipt');
h.inspect(`activeJob.claimed_at=${JSON.stringify(timestamp)};activeJob.phase='session_received';renderJob()`);
assert.equal(h.node('job-title').textContent,'Agent received');
for(const phase of ['session_editing','session_rendering','session_reviewing']){
 h.inspect(`activeJob.phase=${JSON.stringify(phase)};renderJob()`);
 assert.equal(h.node('job-title').textContent,'Agent received','a phase label alone must not assert editing');
}
h.inspect("activeJob.editing_started_at='invalid timestamp';renderJob()");
assert.equal(h.node('job-title').textContent,'Agent received');
h.inspect(`activeJob.editing_started_at=${JSON.stringify(timestamp)};activeJob.phase='session_editing';renderJob()`);
assert.equal(h.node('job-title').textContent,'Editing');assert.match(h.node('job-detail').textContent,/updating/);
h.inspect("activeJob.phase='session_rendering';renderJob()");
assert.equal(h.node('job-title').textContent,'Editing');assert.match(h.node('job-detail').textContent,/rendering fresh exports/);
h.inspect("activeJob.phase='session_reviewing';renderJob()");
assert.match(h.node('job-detail').textContent,/checking the rendered figure/);
assert.equal(h.node('agent-label').textContent,'Agent disconnected');
assert.equal(h.node('open-job-result').hidden,true);
''')

    def test_fresh_result_needs_acceptance_and_all_submitted_comments_before_completed(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));await h.start();
h.inspect("attempts=[{id:'attempt-result',name:'Result',accepted:false}];activeJob={id:'job-result',backend:'session',kind:'agent',status:'succeeded',phase:'complete',source_attempt_id:'attempt-original',target_attempt_id:'attempt-result',agent_request_ids:[]};renderJob()");
assert.equal(h.node('job-title').textContent,'Ready to review');
assert.match(h.node('job-detail').textContent,/before accepting/);
assert.equal(h.node('open-job-result').hidden,false);
assert.equal(h.node('cancel-job').hidden,true);
h.inspect("attempts[0].accepted=true;renderAttempts()");
assert.equal(h.node('job-title').textContent,'Completed','observing a separate explicit acceptance completes the review');
h.inspect("activeJob.agent_request_ids=['unfulfilled-comment'];renderJob()");
assert.equal(h.node('job-title').textContent,'Ready to review','accepting one output cannot complete unfulfilled submitted comments');
assert.match(h.node('job-detail').textContent,/1 instruction remains pending/);
assert.equal(h.node('review-remaining-requests').hidden,false);
h.inspect("activeJob.target_attempt_id=null;renderJob()");
assert.equal(h.node('job-title').textContent,'No new figure','successful handoff without a figure is not a completed edit');
assert.equal(h.node('open-job-result').hidden,true);
''')

    def test_terminal_failures_keep_comments_and_error_detail_compact_without_losing_diagnostics(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));await h.start();
h.point('use-A');h.input('instruction','Preserve my scientific values.');
const svg=h.svg(),diagnostic='Export validation failed. '+ 'Full worker diagnostics. '.repeat(30);
h.inspect(`activeJob={id:'job-failure',backend:'session',kind:'agent',status:'failed',error:${JSON.stringify(diagnostic)}};renderJob()`);
assert.equal(h.node('job-title').textContent,'Failed');
assert.ok(h.node('job-detail').textContent.length<=240);
assert.equal(h.node('job-detail').title,diagnostic.trim(),'full diagnostics remain available without expanding the inspector');
assert.equal(h.node('open-job-result').hidden,true);assert.equal(h.node('cancel-job').hidden,true);
assert.equal(h.node('instruction').value,'Preserve my scientific values.');assert.equal(h.svg(),svg);
h.inspect("activeJob.status='cancelled';activeJob.error=null;renderJob()");
assert.equal(h.node('job-title').textContent,'Cancelled');
assert.match(h.node('job-detail').textContent,/comments remain saved/);
assert.equal(h.node('instruction').value,'Preserve my scientific values.');assert.equal(h.posted.length,0);
''')

    def test_status_failure_never_restores_stale_editing_and_fresh_poll_can_recover(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));
let unavailable=false;
const connection={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',lease_expires_at:Date.now()/1000+120};
const job={id:'job-status',backend:'session',kind:'agent',status:'running',phase:'session_editing',source_attempt_id:'attempt-original',claimed_at:new Date().toISOString(),editing_started_at:new Date().toISOString()};
h.override=(path)=>{
 if(path==='/api/agent')return unavailable?jsonResponse({error:'Connection status unavailable.'},false):jsonResponse(connection);
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(path==='/api/jobs')return unavailable?jsonResponse({error:'Status service unavailable.'},false):jsonResponse({jobs:[job]});
 if(path==='/api/jobs/job-status')return unavailable?jsonResponse({error:'Status service unavailable.'},false):jsonResponse({job});
};
await h.start();h.point('use-A');h.input('instruction','Preserve this draft while checking status.');
assert.equal(h.node('job-title').textContent,'Editing');
unavailable=true;await h.inspect('pollJob()');
assert.equal(h.node('job-title').textContent,'Status unavailable');
assert.equal(h.node('job-status').getAttribute('data-state'),'unknown');
assert.equal(h.node('cancel-job').hidden,true);
h.inspect('renderAttempts()');assert.equal(h.node('job-title').textContent,'Status unavailable','other UI refreshes cannot restore stale Editing');
await h.inspect('refreshService()');
assert.equal(h.node('job-title').textContent,'Status unavailable');
assert.equal(h.node('agent-label').textContent,'Connection status unavailable','a failed connection check is not a verified disconnect');
assert.equal(h.node('instruction').value,'Preserve this draft while checking status.');
unavailable=false;await h.inspect('refreshService()');
assert.equal(h.node('job-title').textContent,'Editing');
assert.equal(h.node('agent-label').textContent,'Original Agent connected');
assert.equal(h.posted.length,0);
''')

    def test_registered_scheduled_check_enables_submit_without_claiming_an_idle_agent_received_it(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let submitted=0;
const connection={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',live_listener:false,scheduled_dispatch:true,dispatch_mode:'host_heartbeat',lease_expires_at:Date.now()/1000-1,host:'codex',host_trigger:{kind:'heartbeat',host:'codex_desktop',automation_id:'isolated-test-fixture',owner_session_id:'original-chat',interval_seconds:60,expires_at:Date.now()/1000+300,enabled:true,registered:true,active:true,verification:'owner_registered'}};
h.override=(path,options)=>{
 if(path==='/api/agent')return jsonResponse(connection);
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(path==='/api/agent/jobs'){
  submitted++;const payload=JSON.parse(options.body);
  assert.equal(payload.attempt_id,'attempt-original');assert.equal(payload.version.figure_sha256,'A');
  assert.deepEqual(payload.request_ids,h.data.requests.map(item=>item.id));
  return jsonResponse({job:{id:'scheduled-job',backend:'session',kind:'agent',status:'queued',phase:'queued',owner_session_id:'original-chat',host_trigger_id:'isolated-test-fixture',source_attempt_id:payload.attempt_id}});
 }
};
await h.start();h.point('use-A');h.input('instruction','Keep every observation, change the label.');
assert.equal(h.node('agent-label').textContent,'Automatic check enabled');
assert.match(h.node('agent-label').title,/original-chat/);
assert.equal(h.node('agent-check-hint').textContent,'About every 1 minute.');
assert.equal(h.node('agent-check-hint').hidden,false);assert.equal(h.node('submit-edits').disabled,false);
await h.click('submit-edits');assert.equal(submitted,1);assert.equal(h.posted.length,1);
assert.equal(h.node('job-title').textContent,'Waiting for automatic check');
assert.match(h.node('job-detail').textContent,/About every 1 minute/);
assert.equal(h.node('open-job-result').hidden,true);
h.inspect("activeJob.status='running';activeJob.phase='session_received';activeJob.received_at=new Date().toISOString();renderJob()");
assert.equal(h.node('job-title').textContent,'Agent received','only an actual claim advances scheduled waiting');
h.inspect("activeJob.phase='session_editing';activeJob.editing_started_at=new Date().toISOString();renderJob()");
assert.equal(h.node('job-title').textContent,'Editing');
''')

    def test_missing_expired_or_wrong_owner_trigger_never_enables_idle_submission(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let jobs=0;
const valid={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',live_listener:false,scheduled_dispatch:true,dispatch_mode:'host_heartbeat',lease_expires_at:Date.now()/1000+120,host_trigger:{kind:'heartbeat',host:'codex_desktop',automation_id:'isolated-test-fixture',owner_session_id:'original-chat',interval_seconds:120,expires_at:Date.now()/1000+300,enabled:true,registered:true,active:true,verification:'owner_registered'}};
let connection=valid;
h.override=path=>path==='/api/agent'?jsonResponse(connection):path==='/api/library'?jsonResponse({attempts:[]}):path==='/api/agent/jobs'?(jobs++,jsonResponse({job:{status:'queued'}})):undefined;
await h.start();h.point('use-A');h.input('instruction','Keep this comment while reconnecting.');
for(const bad of [
 {...valid,host_trigger:null},
 {...valid,scheduled_dispatch:false},
 {...valid,dispatch_mode:'disconnected'},
 {...valid,host_trigger:{...valid.host_trigger,registered:false}},
 {...valid,host_trigger:{...valid.host_trigger,active:false}},
 {...valid,host_trigger:{...valid.host_trigger,enabled:false}},
 {...valid,host_trigger:{...valid.host_trigger,owner_session_id:'different-chat'}},
 {...valid,host_trigger:{...valid.host_trigger,automation_id:''}},
 {...valid,host_trigger:{...valid.host_trigger,interval_seconds:0}},
 {...valid,host_trigger:{...valid.host_trigger,interval_seconds:true}},
 {...valid,host_trigger:{...valid.host_trigger,interval_seconds:3601}},
 {...valid,host_trigger:{...valid.host_trigger,expires_at:Date.now()/1000-1}}
]){
 connection=bad;await h.inspect('pollAgent()');
 assert.equal(h.node('submit-edits').disabled,true);
 assert.equal(h.node('agent-check-hint').hidden,true);
 assert.notEqual(h.node('agent-label').textContent,'Automatic check enabled');
 await h.node('submit-edits').listeners.click();
 assert.equal(jobs,0);assert.equal(h.posted.length,0);
 assert.equal(h.node('instruction').value,'Keep this comment while reconnecting.');
}
connection={...valid,enabled:false,available:false,dispatch_mode:'disconnected',scheduled_dispatch:false,runtime_state:'disconnected'};await h.inspect('pollAgent()');
assert.equal(h.node('agent-label').textContent,'Agent disconnected');
''')

    def test_live_listener_to_scheduled_check_updates_status_without_reloading_the_figure(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));
const base={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',host:'codex'};
let connection={...base,live_listener:true,scheduled_dispatch:false,dispatch_mode:'active_mcp',lease_expires_at:Date.now()/1000+120};
h.override=path=>path==='/api/agent'?jsonResponse(connection):path==='/api/library'?jsonResponse({attempts:[]}):undefined;
await h.start();h.point('use-A');h.input('instruction','Keep the existing annotation draft.');const svg=h.svg();
h.inspect("activeJob={id:'queued-job',backend:'session',kind:'agent',status:'queued',phase:'queued',owner_session_id:'original-chat',host_trigger_id:'isolated-test-fixture',source_attempt_id:'attempt-original'};renderJob()");
assert.equal(h.node('agent-label').textContent,'Original Agent connected');
assert.equal(h.node('job-title').textContent,'Submitted · waiting for Agent');
connection={...base,live_listener:false,scheduled_dispatch:true,dispatch_mode:'host_heartbeat',lease_expires_at:Date.now()/1000-1,host_trigger:{kind:'heartbeat',host:'codex_desktop',automation_id:'isolated-test-fixture',owner_session_id:'original-chat',interval_seconds:90,expires_at:Date.now()/1000+300,enabled:true,registered:true,active:true,verification:'owner_registered'}};
await h.inspect('pollAgent()');
assert.equal(h.node('job-title').textContent,'Waiting for automatic check');
assert.equal(h.node('agent-check-hint').textContent,'About every 1.5 minutes.');
assert.equal(h.svg(),svg);assert.equal(h.node('instruction').value,'Keep the existing annotation draft.');
connection={...connection,scheduled_dispatch:false,enabled:false,available:false,dispatch_mode:'disconnected',runtime_state:'disconnected'};
await h.inspect('pollAgent()');
assert.equal(h.node('job-title').textContent,'Submitted · waiting for Agent','expired scheduled checks do not advertise future automatic receipt');
assert.equal(h.node('agent-label').textContent,'Agent disconnected');
assert.equal(h.posted.length,0);
''')

    def test_disconnect_routes_to_session_backend_without_cli_fallback(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let changed=0;
let connection={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',lease_expires_at:Date.now()/1000+120};
h.override=(path,options)=>{
 if(path==='/api/agent')return jsonResponse(connection);
 if(path==='/api/library')return jsonResponse({attempts:[]});
 if(path==='/api/agent/configure'){
  changed++;assert.deepEqual(JSON.parse(options.body),{backend:'session',enabled:false});
  connection={backend:'session',enabled:false,available:false,runtime_state:'disconnected'};
  return jsonResponse({agent:connection});
 }
};
await h.start();await h.click('connect-agent');
assert.equal(changed,1);assert.equal(h.node('agent-label').textContent,'Agent disconnected');
await h.click('connect-agent');assert.equal(changed,1,'reconnecting requires the original Agent, never CLI configure');
''')

    def test_status_poll_observes_mcp_connection_and_disconnect_without_reloading_figure(self):
        self.run_client(r'''
const h=harness(figure('A',{attempt_id:'attempt-original'}));let connection={backend:'session',enabled:false,available:false};
h.override=(path)=>{
 if(path==='/api/agent')return jsonResponse(connection);
 if(path==='/api/library')return jsonResponse({attempts:[]});
};
await h.start();const originalSvg=h.svg();h.point('use-A');h.input('instruction','Preserve this draft while connecting.');
connection={backend:'session',enabled:true,available:true,same_session:true,owner_session_id:'original-chat',lease_expires_at:Date.now()/1000+120};
await h.inspect('pollAgent()');
assert.equal(h.node('agent-label').textContent,'Original Agent connected');
assert.equal(h.node('submit-edits').disabled,false);
connection={backend:'session',enabled:false,available:false,runtime_state:'expired'};
await h.inspect('pollAgent()');
assert.equal(h.node('agent-label').textContent,'Original Agent connection expired');
assert.equal(h.node('submit-edits').disabled,true);assert.equal(h.svg(),originalSvg);
assert.equal(h.node('instruction').value,'Preserve this draft while connecting.');
assert.equal(h.posted.length,0);
''')


if __name__ == "__main__":
    unittest.main()
