# Independent local figure workbench

Use the same review page in **create** and **reproduce**. It records requested
changes to a rendered panel; it does not choose or replace the track. In
reproduce, compare each change with the adopted reference specification. In
create, retain the accepted scientific question, analysis and data encodings.

## Default activation

When the user asks the Agent to use EasyViz for plotting or editing, open this
workbench as part of delivery after the first current validated SVG and `.ev`
are ready. The user does not need a separate workbench request. A discussion
about EasyViz alone does not start a server. Honor files-only, no-browser or
headless operation; provide the local address if a browser cannot be opened.

For the first attempt, start the launcher with the actual project and figure:

```sh
python /absolute/path/to/easyviz/scripts/easyviz_workbench.py \
  --project-dir /absolute/path/to/project \
  --figure-dir /absolute/path/to/project/attempt-01 --port 0
```

Keep the service alive in the Agent's managed background session and provide the
printed address. An Agent with a supported browser tool may use `--no-open` and
open that address through the host browser instead. If this project already
has a running workbench, reuse its address and select the new attempt through
its library; do not start another service for each render. Opening the page
alone does not connect an Agent.

The authoring conversation remains the default owner of the edits. Its Agent
calls MCP `connect_session` using the host's actual session ID, then uses
bounded `wait_for_submission` calls while active. The page's **Connect original
Agent** control explains this connection; it does not create another Agent or
enable a CLI worker. **Original Agent connected** reports the current leased
binding. Verify actual submission and completion in that conversation before
claiming the end-to-end connection works.

A submitted job returns to the active original Agent's waiting call. This
does not wake a conversation whose turn has ended. If the binding expires or
MCP is unavailable, preserve saved requests and tell the user to trigger the
original Agent again. A separate dedicated CLI worker starts fresh sessions;
use it only when the user explicitly requests that route. Never silently
substitute it for original-session editing.

If the user asks to open the workbench before plotting, start the empty library
below. The user can choose an existing attempt or import an `.ev` project.

## Open the library

Run this standard-library tool from the discovered EasyViz skill directory:

```sh
python /absolute/path/to/easyviz/scripts/easyviz_workbench.py \
  --project-dir /absolute/path/to/project --port 0
```

The launcher opens the browser by default; `--no-open` only prints the address.
If this project's workbench is already running, it reuses that service. The page
opens without a selected figure. Choose a registered attempt under **Figures**,
use **Refresh** to discover valid project outputs, or use **Open .ev** to import
a project. The existing
`figure_workbench.py` entry also accepts standalone `--project-dir`;
add `--figure-dir /absolute/path/to/project/attempt-01` to open an existing
rendered attempt immediately. The page and optional MCP share this project's
attempt registry and review focus.

Add `--compare-dir /absolute/path/to/project/accepted-attempt` to display an
earlier attempt beside the current panel. The previous preview is read-only,
sanitized in the same way, and bound to that attempt's SVG hash. Both previews
must load successfully before a reload replaces the visible figure/version.

Open the printed `http://127.0.0.1:PORT/` address in a browser. Keep the process
running during review and close it with Ctrl+C afterwards. `--port 0` chooses an
available port; a requested fixed port is also accepted. The service listens on
`127.0.0.1` only. The library, SVG review and draft storage use the standard
library; optional rendering needs plotting dependencies. Same-session delivery
requires its MCP connection and an active authoring Agent. The separate optional
editing worker needs a configured, authenticated Codex client.

## Editable `.ev` projects and SVG interaction

`.ev` is one validated project bundle containing the current SVG, its real
nonempty element map, source provenance, plotting code/settings and explicitly declared
data and auxiliary inputs. It may also contain requested PDF, PNG or TIFF
exports. Bundle only the inputs actually declared for this figure, rather than
an entire data directory. Import validates and copies its contents into a fresh
project attempt; importing does not execute source code.

SVG is the default graphic export and the workbench's interactive canvas.
Vector selection is backed by actual SVG IDs and matching element mappings.
An SVG may contain rasterized layers; those layers do not become editable
vectors. A registered collection selects its mapped group; individual points
need individual registrations. PDF and PNG support explicit output/preview
uses, without supplying equivalent semantic selections. Renaming an existing
graphic to `.ev` cannot supply missing code, inputs or mappings.

The footer's **.ev project** download packages the current verified attempt.
An Agent can also prepare or inspect a project from the installed scripts:

```sh
python /absolute/path/to/easyviz/scripts/ev_document.py export \
  /absolute/path/to/project/attempt-01 --out /absolute/path/to/project/figure.ev

python /absolute/path/to/easyviz/scripts/ev_document.py inspect \
  /absolute/path/to/project/figure.ev

python /absolute/path/to/easyviz/scripts/ev_document.py import \
  /absolute/path/to/figure.ev --project-dir /absolute/path/to/project
```

The exporter requires current source/data/specification, a matching real element
map and passing QA for every declared export. A source receipt alone does not
enable an editable project. Re-export unmapped or stale historical figures from
their actual plotting code before packaging them.

The directory must contain `panel.svg` with a finite viewBox and physical width
and height. Existing `panel.pdf`, `panel.png`, `settings.json`, `qa.json` and
`elements.json` and `handoff.json` are optional. SVG, PDF and PNG downloads
return the original exports. The SVG displayed on the page excludes scripts, active HTML and
external-resource references while retaining safe symbol and arrow-marker
definitions and their local references.

## Create numbered change drafts

Click the heading or its pencil button to edit the figure's workbench name.
**Save name** persists it in `figure-info.json`; library entries, MCP inspection,
the next `.ev` export and new editing attempts retain it. Enter saves and Escape
cancels. Naming preserves unsaved annotations, source paths and scientific
versions. This is a project label; it does not authorize adding a title to the
scientific canvas. Agents read the name on their next inspection or in the
editing worker's `agent-context.json`; renaming alone does not start a task.

- Select an SVG element on the figure. Mapped elements can include marks, axes,
  labels, legends and colorbars. Keyboard users can focus a mapped target and
  press Enter or Space to add its annotation.
  In element mode, hovering names the mapped target and clicking permits a
  6 screen-pixel tolerance around actual painted content. A collection's empty
  bounding-box area does not select its points. Use a region when targets
  overlap. Scatter collections select the whole group; a single observation
  requires its own source-bound artist registration.
  Fresh shared exports register visible axis spines, tick marks and tick labels;
  older exports need rerendering to receive these mappings. Tick-label changes
  are cosmetic, not permission to alter the displayed measurement values.
- Click mapped targets one after another or draw separate regions to create
  independent numbered drafts. Each selection box displays its number at the
  upper-right. No modifier keys are needed; consecutive selections do not merge
  their instructions. Use the numbered draft control on the right to return to
  a selection and edit its own comment. Switching drafts
  retains the changes already entered in each draft.
- Write one free-form comment for each annotation, such as “Move this legend
  2 mm to the right.” The page retains the genuine mapped IDs or selected
  region for the Agent; the user does not need property or source-path menus.
  Annotations, requests and history use compact pages instead of a scrolling
  inspector. Paging never excludes completed annotations from a saved batch.
- Use **Select region** to drag a rectangle over a crowded area. Region
  coordinates are measured in millimetres from the **top-left of the entire
  canvas**, including margins and guides. They are not data-axis values.
- Use **Save drafts** once to save all completed drafts together. Blank
  entries remain unsaved drafts. Remove a single draft or use **Clear drafts**
  to discard unsaved drafts before saving. These controls do not cancel saved
  instructions.
- In **Requests**, **Undo pending** marks the last current pending request as
  undone; the record remains in the queue. Downloading requests is optional
  because the Agent can read `requests.json` directly in the attempt directory.
  **Read instruction** opens the full saved comment; long text is summarized
  on its request card without discarding any of the instruction.

Draft numbers and selection boxes are browser review overlays. They do not
alter source values, become scientific labels, or appear in downloaded SVG,
PDF or PNG exports. Saved requests remain separate instructions for the Agent.
Saving drafts does not submit an editing task.

## Render and review saved changes

A collection remains a group; the page does not manufacture individual-point
identity. Source keys and specification paths remain in the recorded mapping
and request for the Agent.

The normal review loop can stay in the original chat:

1. Select elements or regions, write comments and click **Save drafts**.
2. Tell the original Agent: “Apply the saved EasyViz workbench comments to the
   current figure.” No extra **Submit edits** or copied comments are needed.
3. The Agent reads the saved pending requests, edits the source/specification,
   renders a fresh attempt and inspects the actual result. It preserves the
   track, figure name, adopted science and requested export formats, and records
   only fulfilled requests. See [Edit application](apply-figure-requests.md#iterate-from-the-original-chat).
4. Compare the new attempt in this workbench and repeat with further comments.

If these requests already belong to a queued or still-valid running
original-session job, the Agent processes that existing job. It does not apply
them separately and leave the job queued. This loop needs an active original
chat turn; host scheduled checks are optional.

Once the original Agent has established its leased MCP connection, **Submit
edits** saves completed drafts and queues the selected pending batch for that
same conversation. The page distinguishes submission waiting, confirmed
receipt, editing, rendering and reviewing. `wait_for_submission` records receipt;
the original Agent reports the later stages only when they actually begin.
The returned job includes the source-bound requests and edit plan. The original
Agent edits the plotting code/specification, rerenders the requested formats
into a fresh attempt, inspects the result and calls `complete_session_job` for
the requests actually fulfilled. Verified completion updates the page and
leaves the result available for comparison.

The page shows progress and lets the user cancel. Drafts entered during a job
stay in the page. A disconnected or expired session leaves saved drafts intact
and reports that submission is unavailable. **Disconnect** disables future
submissions without deleting saved instructions. **Save drafts** does not queue
a task. The connection can receive work only while the original Agent remains
active and waiting. Optional host scheduled checks can provide a separate
delivery route after the turn ends, once the host has actually created and
enabled the task. The page's local connection alone is not proof of idle
delivery, and the registered original owner stays fixed across reconnects.

The optional dedicated Codex worker is a different execution route. Configure
it only if the user explicitly requests a separate worker; it uses the selected
client's existing authentication and starts a fresh headless session. Plugin
installation and `.ev` import enable neither route. See the [MCP
guide](mcp.md#original-session-editing) for connection, waiting and completion.
Read [Optional original-session checks](session-trigger.md) for native host
creation, expiry, same-owner reconnect and the separate idle-delivery evidence.

Supported core cosmetic edits also have a bounded local preview route through
MCP and the installed renderer. This route can apply supported properties while leaving
region, layout or free-form instructions pending for an Agent. Every path
retains source versions and records outcomes only after new exports pass their
source and export checks. A render or fulfilled instruction is not a visual
quality judgment.

Open the completed attempt, compare it with its predecessor and inspect the
actual figure. **Accept** preserves verified source/spec/data/exports for later
restoration; **Restore accepted** creates a separate restored attempt. Neither
a successful render nor acceptance is an automatic aesthetic judgment.
The attempt selector and History refer only to registered figures within the
explicit project scope. A changed source or failed preview keeps the previous
visible figure and reports the failure.

The chat-triggered loop reads `requests.json` directly or uses the optional
[MCP connection](mcp.md#chat-triggered-saved-comment-iteration). It remains
available when browser delivery is disconnected, without claiming automatic
delivery to an idle Agent.

The **Edit**, **Requests** and **History** tabs share a compact inspector aligned
with the preview's height on desktop. Numbered annotations and saved records
use pagination; **Read instruction** or **Read details** opens long text in a
separate dialog. On small screens the inspector follows the figure in normal
page flow. Arrow keys, Home and End move between inspector tabs. Mapped SVG
targets and numbered badges support keyboard focus and Enter/Space selection.
The page uses the bundled plugin SVG mark and plain surfaces; document previews
keep their opaque white canvas.
The attempt menu opens below its control with separate rounded borders. Use arrow keys,
Home/End and Enter to choose an option, Escape to cancel, or Tab to continue.

The browser correctly maps a nonzero SVG viewBox origin, zoomed display and
letterboxed preview through the SVG screen transformation. Each region retains
its physical dimensions. A region is a visual location, not an identification
of the observations inside it.

A matching `elements.json` enables semantic selection. Its `schema_version: 1`
manifest contains `panel`, `version`, optional `input`, and an `elements` list.
Each element names an actual SVG ID and may record `role`, `label`, `source_keys`,
`spec_paths` and `editable`. `version.figure_sha256` must match the full original
`panel.svg` bytes; physical dimensions must also match. Optional spec, input and
source-script hashes are preserved with the figure version. The manifest can
also express these hashes at the top level for compatibility.
When original source/data/spec paths are available, their bytes are checked
against the recorded hashes. A changed source blocks new requests even when the
SVG is unchanged. Missing historical paths are shown as unavailable; they do not
invent current provenance or authorize automatic application.

A custom script first captures its source bytes before plotting and uses those
returned data/spec/auxiliary byte payloads in its analysis. After final exports,
it writes a source handoff receipt (`handoff.json`) that checks continuity and
binds the actual SVG/PDF/PNG/TIFF bytes to the adopted specification and those
declared consumed inputs. This enables verified region/general request recording and
accepted restore even when the script has not registered selectable artists.
The receipt does not create element IDs or permit automatic property edits.

Each declared auxiliary input is checked independently. A changed metadata,
linkage or other declared source blocks saving against the old export. A
missing file remains unverified and cannot be accepted or recorded as an applied
target. Existing `input.aligned_layer_inputs` maps use these same checks.

Without a matching map, a registered legacy attempt supports general and region
notes and explains that element identity is unavailable. The library import
entry requires a valid `.ev` bundle; an arbitrary external SVG is not an
editable project.
Fallback coordinates use the SVG's actual physical dimensions. Stale or malformed
maps supply neither source/spec provenance nor additional version hashes to a
new note. Regenerate the map or render a fresh captured attempt to restore
traceability. A stale or conflicting receipt blocks new requests.
A PDF alone cannot supply semantic SVG IDs or recover its source code; render
SVG and package the actual code, inputs and mappings in `.ev`.

## Add selection to a custom plotting script

Custom scripts in either track can use the shared `figure_elements.py` helper
without adopting a bundled chart recipe. Register real Matplotlib artists before
export, identify the relevant source records and specification paths, and write
the manifest after saving the final SVG:

```python
# Import figure_elements from the discovered EasyViz scripts directory.
figure_elements.register(
    fig, fitted_line, "fitted-line", "Treatment trend", key="treatment-trend",
    source_keys=[{"condition": "Treatment"}],
    spec_paths=["/style/treatment_line"], editable=["color", "linewidth"],
)
fig._easyviz_data_file = source_csv
fig._easyviz_spec_file = adopted_spec_json
fig._easyviz_source_script = __file__
fig.savefig(output_dir / "panel.svg", bbox_inches=None)
figure_elements.write(
    fig, output_dir, {**spec, "formats": ["svg"]},
    {"width_mm": 120, "height_mm": 90},
)
```

For custom code, capture every consumed source before plotting into a fresh
attempt. Read the returned bytes directly; reopening files could consume a
replacement while preserving a hash from a different version:

```python
import io
import json
import pandas as pd
from figure_handoff import capture_inputs, write_receipt

capture = capture_inputs(
    output_dir,  # no panel exports or handoff.json may exist yet
    data_file=source_csv,
    source_script=__file__,
    spec_file=adopted_spec_json,
    auxiliary_inputs={"metadata": source_metadata_csv},  # omit if none
)
data = pd.read_csv(io.BytesIO(capture.read("data_file")))
spec = json.loads(capture.read("spec_file"))
metadata = pd.read_csv(io.BytesIO(capture.read_auxiliary("metadata")))
# Analyze these captured inputs, draw/register actual artists, and save exports.
write_receipt(
    output_dir,
    capture=capture,
    resolved_spec=spec,  # the actual adopted spec, including resolved defaults
    formats=["svg"],  # add PDF/PNG/TIFF only when actually exported
    track="create",  # or the explicitly adopted reproduce track
)
```

The receipt refuses a changed primary, spec, script or declared auxiliary file.
Its complete declared consumption record is checked by the workbench. A normal
capture cannot be added after old exports to claim that newly read inputs
produced them. The helper records the caller's declared consumption; it cannot
certify arbitrary code execution or that code used a returned payload.

Declare auxiliary files by stable roles and actual paths, including metadata,
linkage, source contracts or author modules that the attempt consumes. The
helper does not guess imports, missing mouse IDs or point identities. `formats`
lists only actual exported files and must include SVG. A receipt supports
region/general notes; register real artists as above for element selection. An
empty artist registry keeps selection disabled and preserves source bindings.

Legacy exports with complete consumed source/spec/script hashes and matching
passing QA/export identities may use the separate `migrate_receipt` API. Supply
each auxiliary's explicit settings JSON pointers, for example
`auxiliary_claims={"source_contract": {"path": "/input/contract_file",
"sha256": "/version/contract_sha256"}}`. Migration verifies the original claims
against the current source and every declared export; it does not restamp old
outputs with replacement inputs. Missing or ambiguous consumption evidence
requires a fresh render with `capture_inputs`. Region/general note collection
remains available for a raw external SVG, while acceptance stays unverified.

Set `fig._easyviz_track` to the adopted `"create"` or `"reproduce"` track when
using a custom script. The core CLI accepts `--track create|reproduce`; it never
invents the track from chart geometry.

Use the actual adopted dimensions, output formats and resolved specification;
export any requested PDF and PNG from the same figure. Call `attach_layout(fig, spec)` before
export when shared axes/guide registration is appropriate, or explicitly register
the custom legend artists. A scatter collection selects its entire registered
group. Core scatter `source_keys.records` are one-based observation positions
in the parsed plotting table, excluding its header; they are not physical CSV
line numbers. Other implementations should explicitly state their key scheme. Per-point editing requires per-point identity and traceable source keys;
the helper does not fabricate those identities from image coordinates. Register
only cosmetic properties that the plotting script can actually change. Preserve
stable category identity across reordering and never make quantitative marker
position or area freely draggable.

An optional property-to-pointer binding makes cosmetic preparation unambiguous.
For example, use `editable={"color": "/colors/Treatment", "alpha":
"/options/alpha"}` together with those same `spec_paths`. Existing
`editable=["color"]` maps remain valid when exactly one compatible path exists.
Only register bindings consumed by the actual plotting script.

## Agent handoff

1. Read `requests.json`, the original manifest, adopted specification and plotting
   script. Process the saved annotations as separate requests, retaining each
   target and instruction. Process only `status: "pending"` records bound to the
   intended version. Each request retains its own SHA256 binding, element identity,
   original source keys, relevant specification paths and optional input paths.
   Do not apply an older request to a new figure merely because an element ID
   happens to match.
2. Translate the instruction into explicit specification or script edits. Keep
   the data, transformations, uncertainty semantics, category-color assignments,
   agreed fonts and canvas dimensions unless the instruction expressly changes
   them. Moving a label or guide is a layout edit; moving a data mark could change
   its scientific meaning. Recolor a category through its stable mapping, rather
   than editing a random SVG path.
3. Save a fresh specification/script and render into `attempt-02`, preserving
   accepted and previously reviewed exports. Recompute the element map for the
   new outputs. Never patch the SVG alone and then deliver a PDF from old code.
4. Inspect the resulting SVG at the recorded panel proportions and check every
   additional declared export's dimensions and content. Record the request ID, files changed and validation
   in the attempt's review notes. Use `apply_figure_requests.py record` to mark
   requests as `applied` or `superseded`, retaining the target version, changed
   files and validation. Update the separate caption if meaning changed.
5. Open the new attempt for review. If files change in an already open page,
   **Reload figure** refreshes the version. Requests saved against a stale
   browser version are rejected, and older queue records are labelled clearly.
   Saving is disabled during reload. The displayed SVG and its version change
   together only after the replacement preview succeeds; a failed reload keeps
   the original SVG, coordinates and version.

The browser records instructions and submits work to the local service. The
connected original Agent claims a queued job through its active MCP wait and
performs code edits within its conversation. A separately requested dedicated
worker runs in a fresh session. An active Agent can also read saved requests
directly. The companion `apply_figure_requests.py` can
prepare a fresh cosmetic specification from verified mapped paths; `--render`
opts into the verified installed core renderer. Author scripts and complex
changes require Agent execution and actual result verification.
See [request application and accepted restore](apply-figure-requests.md) for
exact limits, history recording and source/spec/export restoration.

## Request format and local API

`requests.json` records the saved instructions. The service also maintains its
project registry, job state and fresh attempts. The request root has
`schema_version: 1`, the latest `version`, `updated_at`, and a `requests` list.
Each saved request resembles:

```json
{
  "id": "generated-uuid",
  "created_at": "UTC timestamp",
  "status": "pending",
  "version": {
    "figure_sha256": "original-svg-sha256",
    "spec_sha256": "original-spec-sha256"
  },
  "element_id": "easyviz-legend-main",
  "element": {
    "role": "legend",
    "label": "Group legend",
    "source_keys": [],
    "spec_paths": ["legend"],
    "editable": ["position"]
  },
  "instruction": "Move this legend 2 mm to the right; keep the font size."
}
```

Region/general notes have a null `element_id`; regions add `region_mm` with
`x`, `y`, `width`, `height` and an explicit coordinate origin. Supported property
requests add `property` and `value`. Numbered annotations may also retain
`annotation_number` and `anchor_mm` as described below. Undo changes `status` to
`undone` and adds `undone_at`, preserving the original ID and content.
Bulk requests add `element_ids` and `elements` with every real identity, source
key, spec path and supported property. Singleton requests retain the legacy
`element_id` and `element`. Server-expanded requests also record their
`selector`. Optional `spec_path` must belong to every selected element and
disambiguates the intended mapped parameter. No observation IDs are fabricated
for a collection or raster panel. Agent helper outcomes add `applied` or
`superseded` statuses and root `history` events. Undo cancels instructions;
restoring an applied version requires its matching source/spec/input/exports.

`GET /api/state` returns the current version, element-map validity (`manifest_valid`), independent source binding validity (`provenance_valid`), any receipt error (`handoff_error`), available
exports, queue, history, source-version checks, optional comparison metadata and
ephemeral session token. `GET /api/preview.svg?v=HASH` returns
the safe preview only when the supplied figure hash is current.
`POST /api/requests` accepts a version, instruction, optional element/region and
optional supported property/value. It accepts one selection form: `element_id`,
`element_ids`, or `selector` with any intersection of `role`, `category`,
`spec_path` and `source_key`. Selectors expand against the current manifest on
the server.

`POST /api/requests/batch` accepts a body containing exactly `version` and
`requests`, with **1 to 100** request objects. Copy the complete `version` object
from `GET /api/state` into the batch's `version` and into **every** request's
`version`; the outer version does not replace each item's binding. Each item
uses the same target, instruction and optional property/value fields as a
single request. Two additional optional fields are supported:

| Field | Contract |
| --- | --- |
| `annotation_number` | An integer from 1 to 1,000,000, unique within the same complete figure version across existing saved requests and this batch. A number remains reserved after undo or application; an `undone` record does not release it. |
| `anchor_mm` | An object containing exactly finite `x` and `y` coordinates in millimetres from the top-left of the full canvas: `0 <= x <= width_mm` and `0 <= y <= height_mm`. It locates a review annotation, not a data observation. |

The service validates every item and rechecks the figure/source version before
writing the complete batch once. A failed batch leaves the existing ledger
unchanged and saves no partial requests; the page retains its drafts for
correction. Blank drafts are not submitted. The original single-request and
undo endpoints remain compatible.

`GET /api/compare.svg?v=HASH` exposes only the previously supplied comparison
attempt. `POST /api/undo` accepts a version and request ID. Writes require JSON,
the exact local `Origin` and the `X-EasyViz-Token` from the current state.
These constraints reject cross-site
requests and DNS-rebinding hosts. Downloads remain limited to declared figure
exports. Library import and worker configuration use their dedicated validated
service operations; request text is not an unrestricted shell endpoint.
