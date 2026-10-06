# Optional local MCP connection

MCP lets a compatible Agent use the workbench's project-scoped figure service:
its library, source-bound requests, render jobs and original-session editing
queue. Create and Reproduce keep their existing workflows. **Save drafts** only
stores instructions. **Submit edits** queues a batch for the connected authoring
Agent, which receives it through an active bounded wait and edits within its
current conversation. Starting an MCP server does not connect a session or
wake an idle conversation. Optional host scheduled checks are a separate
connection whose actual creation and delivery must be verified.

A separate Codex CLI worker remains available only when explicitly requested.
`submit_agent_job` follows the actual connected backend: `session` queues for
the bound original Agent; an explicitly configured `codex` backend starts a
fresh dedicated session. Inspect `agent_status` before submitting and never
use the separate worker as a silent fallback.

## Connect a project

Use a Python environment with the plotting dependencies and the optional pinned
`scripts/requirements-mcp.txt`. Keep it separate from an unrelated scientific
environment when installing dependencies would change that environment.
The tested adapter uses the official Python SDK **`mcp==2.3.0`**. For an existing
environment with pip, install only this optional connection with
`python -m pip install -r /absolute/path/to/easyviz/scripts/requirements-mcp.txt`;
an installation Agent can use the environment's existing package manager.
Configure the selected client's STDIO server with:

```text
command: /absolute/path/to/python
arguments:
  /absolute/path/to/installed/easyviz/scripts/easyviz_mcp.py
  --project-dir
  /absolute/path/to/authorized-project
```

An optional `--figure-dir /absolute/path/to/authorized-project/attempt-01`
registers the first figure. Otherwise the Agent calls `register_attempt` on an
existing rendered attempt. The project must contain its attempts and declared
source inputs; use the same explicit `--project-dir` for the workbench. Each
project keeps its registry in `.easyviz-service/registry.json`. Never expand the
scope to an entire home directory to hide missing input paths.

For Codex, follow its supported MCP configuration or `codex mcp add` command
after checking the installed client's help. Use a distinct connection name for
each authorized project. The installation Agent can complete these steps;
users need not copy requests or maintain configuration by hand. Other clients
use their own STDIO configuration. Verify startup and actual tool discovery in
the selected client; SDK availability alone is not client compatibility.

The adapter exposes the project operations below and a sanitized SVG resource template.
`list_attempts` reports both the adapter's initial/current ID and
`review_attempt_id`, the latest attempt explicitly selected in the browser.
Default inspection and request tools follow that browser review focus;
an explicit `attempt_id` always overrides it. Starting an MCP process does not
overwrite the browser's selection. `list_jobs` discovers browser-submitted
batches, their original source IDs and newly rendered target IDs.

## Original-session editing

Use these tools from the conversation that actually invoked EasyViz. Obtain its
session ID from the host's real session context; never invent an ID or label a
separate worker with the original ID to claim same-session execution.

1. Call `connect_session(owner_session_id, host="codex", lease_seconds=300)`.
   The result includes a `connection_id` and a private `connection_token`.
   Retain them in this Agent's tool context; do not put the token in user-facing
   text, figures, captions or browser comments. The workbench can display this
   leased connection, but its label alone does not prove host delivery. The
   original owner stays fixed across lease expiry and deliberate disconnect;
   later editing turns reconnect that same host/session owner.
2. Keep this Agent active by calling
   `wait_for_submission(owner_session_id, connection_token, timeout_seconds=45)`.
   Each wait is bounded at 45 seconds and refreshes the lease. Repeat while the
   user is reviewing and waiting is still appropriate; otherwise report that the
   connection will expire. A timeout is not an editing request.
3. When the user presses **Submit edits**, the wait claims the queued job and
   returns its `job` and source-bound `plan`. The claim records **received**;
   call `report_session_progress(..., phase="editing")` when edits actually
   begin. Process that returned batch in
   this conversation. Preserve the adopted Create or Reproduce track, analysis,
   reference, fonts, dimensions, exports and source identities. Read the full
   request text and mapped targets rather than interpreting the badge alone.
   The equivalent MCP `submit_agent_job` operation also queues for this
   connection when `agent_status.backend` is `session`; it does not execute
   plotting code or start another session by itself.
4. Edit the declared source/specification. Report `phase="rendering"` when
   starting a fresh render and `phase="reviewing"` when opening and checking
   the actual result. Verify all requested exports and register the new attempt.
   Call `complete_session_job(owner_session_id, connection_token, job_id,
   target_attempt_id, request_ids, changed_files, validation)` with only the
   request IDs actually fulfilled. The service verifies the new target and
   records applied outcomes; remaining requests stay pending. Completion is
   not automatic aesthetic acceptance.
5. Display and compare the resulting attempt. Continue a bounded wait for the
   next submitted batch if the user is still editing. Use `get_job` and
   `cancel_job` to inspect or cancel work, without marking unverified edits
   applied. Call `disconnect_session(owner_session_id, connection_token)` when
   ending this connection deliberately. Keep the lease current during lengthy
   editing or review; a stale credential cannot complete a job.

The live connection is a lease for a cooperative Agent waiting in the same
session. After its turn ends, delivery needs a successfully created host
scheduled check or the user's next turn in that original chat. A new process
running under an original session ID does not establish that the original host
is executing the task. To report a
successful same-session flow, verify actual connection, browser submission,
claim, source edit, fresh output and verified completion in that conversation.

## Chat-triggered saved-comment iteration

When the user says “Apply the saved EasyViz workbench comments,” act in this
original conversation. **Save drafts** is sufficient; do not wait for another
browser submission. Use `list_attempts`/`get_attempt` to identify the reviewed
figure, and inspect `list_jobs` for a matching original-owner batch before edits.
Claim an existing queued job with `wait_for_submission`; continue a still-valid
claimed running job through its owning connection. Report actual progress and
use `complete_session_job` as above, instead of recording the same requests
separately and leaving the job active.

When no matching active job exists, use `list_requests(attempt_id)` and
`prepare_edits(version, request_ids, attempt_id)` to read and validate pending
instructions. Free-form comments require explicit Agent code/spec edits, not
automatic core preparation. Render and inspect a fresh attempt while retaining
the track, figure name, science and requested exports; call `register_attempt`,
then `record_outcome(source_attempt_id, target_attempt_id, request_ids,
changed_files, validation)` only for fulfilled requests. Show the new figure for
comparison. This route does not require a leased submission listener or host
scheduled task. Without MCP, follow the same [edit-application procedure](apply-figure-requests.md#iterate-from-the-original-chat)
using the saved `requests.json` and CLI recording helper.

## Optional host scheduled checks

Read [Original-conversation trigger setup](session-trigger.md) when the user
wants submissions processed after the original turn ends. First create and
enable the native host task successfully, then call
`register_session_trigger(owner_session_id, connection_token, automation_id,
interval_seconds, expires_at)` with its real identity and bounded lifetime.
The current registration supports Codex Desktop heartbeat metadata only;
`interval_seconds` is 60 to 3,600 and Unix `expires_at` must allow one interval
within a maximum 24-hour lifetime. These are local validation limits, not a
promise that the host can schedule or deliver at one-minute intervals.

`agent_status` separates `live_listener`, `scheduled_dispatch` and `dispatch_mode`.
`host_trigger.verification="owner_registered"` records the original owner's
registration, not observed execution. A callback in that same original host
conversation reconnects an expired lease or renews a still-live one with
`renew_same_session`, then claims an actually submitted batch. Wrong-owner,
expired-trigger and deliberately disconnected sessions cannot take over it.

Use `disable_session_trigger` and separately stop the actual native task when
review ends. Local disable does not remove the host's schedule. If native
creation is unavailable, leave scheduling unregistered and retain submitted
requests for the original conversation's next turn. Do not create a substitute
timer or silently switch to a new CLI session.

## Optional dedicated worker

1. Call `agent_status` to check the actual backend, connection and executable.
2. Configure it through `configure_agent(backend="codex", enabled=True)` when
   a separate editing worker is explicitly requested. The selected Codex client
   needs existing authentication; its environment must support the plotting code.
3. Call `submit_agent_job` with the current figure version, optional request IDs
   and optional attempt ID. The result contains a job like the core renderer's
   result. `get_job` reports progress and outcomes; `cancel_job` cancels it.

The service starts a fresh dedicated session in a separate attempt with a
bound request batch. It uses the installed client's configuration and passes
instructions through standard input. It does not install a model, rewrite
global client settings or resume a user's original chat. One active project
job is shared across browser and MCP processes.

Successful worker exit alone does not mark requests applied. The service checks
the reported target, captured source/data provenance, declared exports and QA
before recording fulfilled IDs. A partial result leaves unfulfilled requests
pending. Cancellation, timeout or stale outputs preserve the source request
state. The worker does not automatically accept the figure's visual design;
the user or reviewing Agent still inspects and accepts the new result.

## Active-Agent workflow

| Step | Tools and behavior |
| --- | --- |
| Inspect | `capabilities`, `list_attempts`, `get_attempt` expose real versions, mapped targets and export paths. A sanitized SVG preview is available as an MCP resource. |
| Name a figure | `rename_attempt(name, attempt_id)` saves the same workbench name shown by `get_attempt` and `list_attempts`. It travels with `.ev` and the worker context; it is not an in-image title or a task trigger. |
| Connect this conversation | `connect_session` binds the actual authoring-session ID. Keep its returned token private; `wait_for_submission` refreshes the lease and claims a queued browser submission while this Agent is active. |
| Report real progress | `report_session_progress` records editing, rendering and reviewing beginnings in order. Claim receipt and successful rendering do not establish reviewed completion. |
| Optional native checks | `register_session_trigger` records an actually created host task; `renew_same_session` retains a live original lease; `disable_session_trigger` disables its local eligibility. Host creation, stopping and actual idle delivery remain separate host operations. |
| Read changes | `list_requests`, then `prepare_edits` classify source-bound pending requests. Unsupported changes remain explicit Agent work. |
| Complete same-session work | Render and register a fresh inspected attempt, then `complete_session_job` verifies the target before recording fulfilled requests. Use `get_job` or `cancel_job` to follow the batch. |
| Use a separately requested worker | `agent_status`, `configure_agent`, then `submit_agent_job` dispatch a bound batch to the dedicated Codex worker. This starts a fresh session. |
| Render supported edits | `render_attempt` starts a bounded code-generated preview; poll `get_job`, or use `cancel_job`. This does not accept the visual result. |
| Apply custom instructions | Edit the declared plotting code, render a fresh attempt and inspect it. Register that attempt and `record_outcome` for the requests actually fulfilled. |
| Review and retain | Compare actual exports, then `accept_attempt` with the review finding. `restore_attempt` creates a separate copy from verified accepted inputs. |

The local core preview runs only the unchanged installed renderer. Region notes,
free-form instructions and custom plotting scripts need the authoring Agent's
explicit code edits, or a separately requested dedicated worker.
A mixed batch can preview supported cosmetics while reporting remaining
instructions. Those remaining instructions retain their original source
attempt/version; `agent_request_ids` and `source_attempt_id` identify the
handoff. Before editing a completed preview, explicitly adopt the remaining
instructions against its actual source and preserve the cosmetic changes.
Cancellation, stale inputs and failed exports do not mark
uncommitted requests as applied. One render job can run per project; retained
job history and execution time are bounded.
The current limits are one active job, 32 retained job records, 100 registered
attempts, a 120-second core-render limit and a 600-second Codex-worker limit. The command uses the same Python
interpreter as the adapter, so that interpreter needs plotting dependencies
for automatic rendering.

Saved drafts can also be read by an active Agent directly. The service supplies
bounded project operations and an original-session queue rather than an
unrestricted shell or file browser. Importing a validated `.ev` only stages
its files; it does not connect an Agent or execute plotting code.

Protocol logs remain off STDOUT. If startup reports a missing or incompatible
SDK, use the exact optional requirements file in the configured interpreter,
then verify again. CLI `--help` and the ordinary workbench remain available.

Host configuration references: [Codex MCP](https://developers.openai.com/codex/mcp)
and [MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools).
