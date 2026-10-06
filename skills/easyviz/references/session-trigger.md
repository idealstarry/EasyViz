# Original-conversation workbench delivery

The workbench records numbered comments against real figure versions. **Save
drafts** stores them; **Submit edits** queues a batch for the project's original
authoring conversation. The same owner handles later turns and expired
connections. A separate CLI worker is available only when explicitly requested.

## While the Agent is active

The original Agent connects through MCP and calls `wait_for_submission` for at
most 45 seconds at a time. A returned batch means **received**. It reports
actual editing, rendering and reviewing starts with `report_session_progress`,
renders a fresh attempt, inspects it and calls `complete_session_job` for the
requests actually fulfilled. A timeout means no batch was received.

The page distinguishes waiting, received, editing and checked completion.
Successful rendering is not visual approval. Drafts, unresolved comments and
the original outputs remain available after cancellation or a failed result.
See the [MCP procedure](mcp.md#original-session-editing).

## After the Agent's turn ends

An MCP server cannot resume a finished conversation by itself. Optional host
scheduled checks use the host's own conversation scheduler to return to that
same original thread. They poll for submitted batches; they are not an immediate
web event or a generic capability of every MCP client.

The installation/editing Agent completes setup in this order:

1. Confirm the actual original host/session owner and the authorized project.
   Obtain the user's requested review duration and check frequency, or choose
   a stated bounded duration appropriate to the review session.
2. Create a native host task targeting that original conversation. Its prompt
   checks this project's submitted queue, handles a received batch in this
   conversation and stays quiet when no batch is available. It must stop at
   the agreed deadline. It should not treat saved drafts as submitted edits.
3. Confirm the host task was actually created and enabled. Keep its returned
   task ID and actual interval; a suggested task or local metadata is insufficient.
4. Call `register_session_trigger(owner_session_id, connection_token,
   automation_id, interval_seconds, expires_at)` with that exact native task.
   The current adapter supports a Codex Desktop heartbeat only. Its interval
   must be an integer from 60 to 3,600 seconds; `expires_at` is a finite Unix UTC
   timestamp allowing at least one interval and no more than 24 hours from now.
   These validation bounds do not establish the host's supported frequency.
   Do not register a task that the host could not create.
5. Verify a real browser submission after the original turn ends: native
   scheduling must resume the original thread, claim the batch, edit and review
   a fresh attempt, and record verified completion. Report the actual latency
   separately from the configured interval.

A one-minute requested interval does not establish a one-minute response time.
The host may reject or delay schedules, require the app/computer to remain
available, or lack this feature. A registered host task means the connection
has been configured; observed delivery establishes that it worked.

On each actual host callback, inspect `agent_status` and the registered
owner/project/automation ID. Stop when that registration is disabled or expired.
Use `renew_same_session(owner_session_id, connection_token)` only while its
original lease remains live. After expiry, reconnect the same owner through
`connect_session` to obtain a new private token; renewal cannot revive expired
credentials. Only matching queued jobs survive that scheduled reconnect.
An expired running claim fails instead of being silently resumed by a new
connection. Call `wait_for_submission(..., timeout_seconds=0)` for an immediate
check, or use a bounded wait when appropriate. No submitted batch means no edit.

At the deadline, local scheduling eligibility expires. When review ends earlier,
stop the native host task and disable its EasyViz registration. Disabling local
metadata alone does not remove a task in the host scheduler. Retain submitted
comments for the original Agent's next authorized turn.
Use `disable_session_trigger(owner_session_id, connection_token)` for local
disable and the native host tool to stop the actual task. Deliberate original
session disconnect also disables its trigger; later reconnect does not silently
reactivate it.

`agent_status.live_listener` describes the current cooperative lease;
`scheduled_dispatch` describes registered scheduling eligibility, and
`dispatch_mode` distinguishes `active_mcp`, `host_heartbeat` and `disconnected`.
The public `host_trigger.verification` value `owner_registered` and legacy
`existing_chat_wake` flag do not independently verify that the host has executed
a callback. Retain evidence of actual native creation and the idle delivery test.

## Connection and progress evidence

| Observation | What it establishes |
| --- | --- |
| MCP server discovered | The client can call the adapter. |
| Original-session connection registered | The fixed owner has a current cooperative connection. |
| Native task created and locally registered | The optional host check has been configured within its lifetime. |
| Batch claimed | The original Agent received these exact requests. |
| Editing/rendering/reviewing reported | Those stages actually began; they do not establish completion. |
| Fresh target verified and completion recorded | Fulfilled requests have a source-bound result ready for review. |
| Ended original turn later resumed by native task | Host-scheduled idle delivery was observed in that host. |

Do not report idle delivery based on the first six observations alone. Do not
start a new worker under the original session's label or replace a missing native
schedule with an undisclosed polling process.
