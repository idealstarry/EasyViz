# Optional local MCP connection

MCP lets a compatible active Agent read the workbench's saved requests and
operate its project-scoped figure service. Create and Reproduce keep their
existing workflows. The standard-library workbench and ordinary skill do not
require this connection.

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

The adapter exposes **13 tools** and one sanitized SVG resource template.
`list_attempts` reports both the adapter's initial/current ID and
`review_attempt_id`, the latest attempt explicitly selected in the browser.
Default inspection and request tools follow that browser review focus;
an explicit `attempt_id` always overrides it. Starting an MCP process does not
overwrite the browser's selection. `list_jobs` discovers browser-submitted
batches, their original source IDs and newly rendered target IDs.

## Active-Agent workflow

| Step | Tools and behavior |
| --- | --- |
| Inspect | `capabilities`, `list_attempts`, `get_attempt` expose real versions, mapped targets and export paths. A sanitized SVG preview is available as an MCP resource. |
| Read changes | `list_requests`, then `prepare_edits` classify source-bound pending requests. Unsupported changes remain explicit Agent work. |
| Render supported edits | `render_attempt` starts a bounded code-generated preview; poll `get_job`, or use `cancel_job`. This does not accept the visual result. |
| Apply custom instructions | Edit the declared plotting code, render a fresh attempt and inspect it. Register that attempt and `record_outcome` for the requests actually fulfilled. |
| Review and retain | Compare actual exports, then `accept_attempt` with the review finding. `restore_attempt` creates a separate copy from verified accepted inputs. |

Only the unchanged installed core renderer runs automatically. Region notes,
free-form instructions and custom plotting scripts require the active Agent.
A mixed batch can preview supported cosmetics while reporting remaining
instructions. Those remaining instructions retain their original source
attempt/version; `agent_request_ids` and `source_attempt_id` identify the
handoff. Before editing a completed preview, explicitly adopt the remaining
instructions against its actual source and preserve the cosmetic changes.
Cancellation, stale inputs and failed exports do not mark
uncommitted requests as applied. One render job can run per project; retained
job history and execution time are bounded.
The current limits are one active job, 32 retained job records, 100 registered
attempts and a 120-second core-render limit. The command uses the same Python
interpreter as the adapter, so that interpreter needs plotting dependencies
for automatic rendering.

Saving a web request does not wake an idle chat. Tell the connected Agent that
the requests are ready; it reads their text and targets directly. The service
does not send messages to other chats, run arbitrary shell commands or provide
an unrestricted file browser.

Protocol logs remain off STDOUT. If startup reports a missing or incompatible
SDK, use the exact optional requirements file in the configured interpreter,
then verify again. CLI `--help` and the ordinary workbench remain available.

Host configuration references: [Codex MCP](https://developers.openai.com/codex/mcp)
and [MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools).
