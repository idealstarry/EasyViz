# Local figure review

Use the same review page in **create** and **reproduce**. It records requested
changes to a rendered panel; it does not choose or replace the track. In
reproduce, compare each change with the adopted reference specification. In
create, retain the accepted scientific question, analysis and data encodings.

## Open a panel

Run this standard-library tool from the discovered EasyViz skill directory:

```sh
python /absolute/path/to/easyviz/scripts/figure_workbench.py \
  --figure-dir /absolute/path/to/project/attempt-01 --port 0
```

Add `--compare-dir /absolute/path/to/project/accepted-attempt` to display an
earlier attempt beside the current panel. The previous preview is read-only,
sanitized in the same way, and bound to that attempt's SVG hash. Both previews
must load successfully before a reload replaces the visible figure/version.

Open the printed `http://127.0.0.1:PORT/` address in a browser. Keep the process
running during review and close it with Ctrl+C afterwards. `--port 0` chooses an
available port; a requested fixed port is also accepted. The service listens on
`127.0.0.1` only and requires no model API, API key or additional package.

The directory must contain `panel.svg` with a finite viewBox and physical width
and height. Existing `panel.pdf`, `panel.png`, `settings.json`, `qa.json` and
`elements.json` and `handoff.json` are optional. SVG, PDF and PNG downloads
return the original exports. The SVG displayed on the page excludes scripts, active HTML and
external-resource references while retaining safe symbol and arrow-marker
definitions and their local references.

## Create numbered change drafts

- Select an SVG element on the figure or in the keyboard-accessible element
  list. Mapped elements can include marks, axes, labels, legends and colorbars.
  In element mode, hovering names the mapped target and clicking permits a
  6 screen-pixel tolerance around actual painted content. A collection's empty
  bounding-box area does not select its points. Use the list when targets
  overlap. Scatter collections select the whole group; a single observation
  requires its own source-bound artist registration.
  Fresh shared exports register visible axis spines, tick marks and tick labels;
  older exports need rerendering to receive these mappings. Tick-label changes
  are cosmetic, not permission to alter the displayed measurement values.
- Click mapped targets one after another or draw separate regions to create
  independent numbered drafts. Each selection box displays its number at the
  upper-right. No modifier keys are needed; consecutive selections do not merge
  their instructions. Use the numbered draft control on the right to return to
  a selection and edit its own text and property values. Switching drafts
  retains the changes already entered in each draft.
- **Select a mapped group** expands a category, role, source
  key or specification path to actual mapped IDs. Category selection uses
  `source_keys.category` or `source_keys.group`, so it remains stable when labels
  or order change and can include both marks and guide keys. Source filters use
  recorded keys, never image coordinates.
- Choose a supported property, such as color or line width, and enter the value;
  or leave a free-form instruction such as “Move this legend 2 mm to the right.”
  A group draft offers only properties shared by every mapped member. For
  example, one draft can recolor all Control marks and their matching legend,
  while another moves a separate legend.
- Use **Select region** to drag a rectangle over a crowded area. Region
  coordinates are measured in millimetres from the **top-left of the entire
  canvas**, including margins and guides. They are not data-axis values.
- Use **Save requests** once to save all completed drafts together. Blank
  entries remain unsaved drafts. Remove a single draft or use **Clear drafts**
  to discard unsaved drafts before saving. These controls do not cancel saved
  instructions.
- In **Requests**, **Undo pending** marks the last current pending request as
  undone; the record remains in the queue. Downloading requests is optional
  because the Agent can read `requests.json` directly in the attempt directory.

Draft numbers and selection boxes are browser review overlays. They do not
alter source values, become scientific labels, or appear in downloaded SVG,
PDF or PNG exports. Saved requests remain separate instructions for the Agent.

The **Edit**, **Requests** and **History** tabs keep the inspector within the
desktop viewport; long content scrolls inside the active tab. On small screens
it follows the figure in normal page flow. Expand **Mapped elements** to
use the keyboard-accessible element list. Arrow keys, Home and End
move between inspector tabs. The page uses the bundled plugin SVG mark and
plain surfaces; document previews keep their opaque white canvas.
Group and property menus open directly below their controls. Use arrow keys,
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

Without a matching map, the page supports general and region notes and explains
that element identity is unavailable. An external SVG can be reviewed this way.
Fallback coordinates use the SVG's actual physical dimensions. Stale or malformed
maps supply neither source/spec provenance nor additional version hashes to a
new note. Regenerate the map or render a fresh captured attempt to restore
traceability. A stale or conflicting receipt blocks new requests.
A PDF alone cannot supply semantic SVG IDs or recover its source code; export an
SVG from the plotting script, or collect PDF annotations separately.

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
    fig, output_dir, {**spec, "formats": ["svg", "pdf", "png"]},
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
    formats=["svg", "pdf", "png"],
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
export the PDF and PNG from the same figure. Call `attach_layout(fig, spec)` before
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
4. Inspect the resulting SVG/PNG at the recorded panel proportions and check the
   PDF dimensions and content. Record the request ID, files changed and validation
   in the attempt's review notes. Use `apply_figure_requests.py record` to mark
   requests as `applied` or `superseded`, retaining the target version, changed
   files and validation. Update the separate caption if meaning changed.
5. Open the new attempt for review. If files change in an already open page,
   **Reload figure** refreshes the version. Requests saved against a stale
   browser version are rejected, and older queue records are labelled clearly.
   Saving is disabled during reload. The displayed SVG and its version change
   together only after the replacement preview succeeds; a failed reload keeps
   the original SVG, coordinates and version.

The browser records instructions and does not execute code. The companion
`apply_figure_requests.py` can prepare a fresh cosmetic specification from
verified mapped paths; `--render` separately opts into the hash-verified
installed core renderer. Author scripts and complex changes remain Agent work.
See [request application and accepted restore](apply-figure-requests.md) for
exact limits, history recording and source/spec/export restoration.

## Request format and local API

`requests.json` is the only file the service writes. The root has
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
requests and DNS-rebinding hosts. No filesystem paths or executable commands are accepted;
only a fixed list of figure files is downloadable.
