# Apply figure requests and restore accepted attempts

Use `apply_figure_requests.py` after the workbench has saved requests. It is an
Agent-facing helper with no remote model/API calls. Its default `apply` operation
prepares a new spec and an inspectable `request-plan.json`; it does not run an
author script or claim that a new SVG/PDF has been produced.

The [local workbench](figure-workbench.md) and optional [MCP adapter](mcp.md)
also share these verified preparation, recording and snapshot operations via
`figure_service.py`. The service adds registered attempts and bounded cancellable
jobs. Its core preview runs only the installed renderer; **Submit edits** queues
code, layout and free-form changes for the original Agent connected through
MCP. That active Agent receives the batch through `wait_for_submission` and
reports actual editing/rendering/reviewing through `report_session_progress`
before verified fresh exports through `complete_session_job`. Idle delivery
requires a separate, successfully created host scheduled check; a local queue
does not wake the host. A separate Codex worker requires
explicit authorization. **Save drafts** remains a storage operation.

## Iterate from the original chat

A request such as “Apply the saved EasyViz workbench comments to the current
figure” authorizes this Agent to carry out the saved edits now. **Save drafts**
already writes them to the attempt's `requests.json`; an additional browser
submission or host scheduled task is unnecessary.

Read the current reviewed attempt, its full pending comments, mappings and
source/version bindings. When MCP is available, inspect `list_jobs` first.
Claim a matching original-owner queued job with `wait_for_submission`, or
continue its still-valid claimed running job, and finish through
`complete_session_job`. Do not process that batch independently or create a
duplicate job. Without an active matching job, read the ledger directly or use
`list_requests` and `prepare_edits` as described in the [MCP guide](mcp.md#chat-triggered-saved-comment-iteration).

Interpret free-form comments and explicitly edit the plotting source/spec;
`apply --render` does not interpret prose. Preserve the adopted track,
workbench name, science, dimensions, fonts and requested formats. Render a
fresh attempt, open the actual result, verify the requested changes and exports,
then [record](#record-agent-edits) only fulfilled request IDs. With MCP, register
that attempt and use `record_outcome` for this unqueued flow. Leave unresolved
requests pending and show the result for comparison in the existing workbench.

## Prepare a cosmetic change

```sh
python /absolute/path/to/easyviz/scripts/apply_figure_requests.py apply \
  --figure-dir /absolute/path/to/project/attempt-01 \
  --out /absolute/path/to/project/attempt-02 \
  --request-id REQUEST_UUID
```

Repeat `--request-id` to process several requests. Omitting IDs selects all
pending requests, and refuses the batch if any selected request is stale. The
output must be a fresh directory outside the reviewed attempt. The original
source, spec, data and figure exports remain intact; the separate request ledger
records a `prepared` event and the requests remain pending until fresh exports
have been produced and recorded.

The helper requires a matching element map plus available, current SHA256
bindings for the original SVG, source script, input data and supplied spec.
Each requested element snapshot must exactly match the current map's identity,
source keys, spec paths and editable properties. A surviving element ID alone
cannot authorize applying an old request to a new version. Shared figure-profile
changes require an Agent to preserve the profile and its dependent panels.

When the supplied spec omits explicit category colors, the helper preserves
the resolved palette only if its canonical map matches the element manifest's
`version.resolved_colors_sha256`. A modified or unbound legacy map requires
Agent verification. A request for one category cannot silently recolor another.

Supported automatic preparation is deliberately narrow:

| Property | Allowed mapped JSON pointer | Value |
| --- | --- | --- |
| `color`, `facecolor`, `edgecolor` | `/colors/CATEGORY`, `/options/point_color`, `/options/regression_color`, or `/style/.../color`, `facecolor`, `edgecolor` | `#RRGGBB` or `#RRGGBBAA` |
| `alpha` | `/options/alpha` or `/style/.../alpha` | finite number from 0 to 1 |
| `linewidth`, `line_width_pt` | `/layout/line_width_pt` or `/style/.../linewidth`, `line_width_pt` | finite number greater than 0 and at most 20 pt |
| `linestyle` | `/style/.../linestyle` | `-`, `--`, `-.`, `:`, or named equivalents |

Paths must already be declared by the selected elements. An `editable` dict
can explicitly bind each property to one of its `spec_paths`; legacy lists work
when exactly one compatible pointer exists. Dotted paths, ambiguous bindings,
unmapped source changes, arbitrary code, quantitative data positions/areas,
scales, fields, normalizations, font changes and layout moves require explicit
Agent edits. Numeric values contain no units. Custom `/style` bindings prepare
spec changes only; the Agent must ensure its author code consumes them.

Category colors preserve the complete accepted mapping. If the original spec
uses a palette, `settings.json.resolved_colors` seeds every accepted category
before the requested color changes. JSON-pointer escaping preserves literal
category names such as `A/B~C`. A path can affect several elements; the plan
lists their actual IDs, including linked guide keys. A global option such as
opacity applies to its documented shared scope, even if one group initiated the
request; inspect the affected IDs and source/spec paths before rendering.

## Explicit core rerender

Append `--render` only for the unchanged installed `render.py`. The source path,
source hash and resolved-spec hash must match the reviewed attempt. The helper
imports this known renderer directly, validates the edited spec and produces
new exports plus a fresh map in the new attempt. It never executes a path or
command supplied in a request. Custom source scripts and custom style bindings
are rejected by this option. Renderer dependencies are needed only here.

After successful core QA, requests are recorded as `applied`; requests fully
replaced by a later request in the same batch become `superseded`. Automated QA
does not replace final-size visual review. A failed render leaves a failed fresh
attempt for diagnosis and keeps source requests pending.

## Record Agent edits

For an author script, the active Agent or connected project worker makes explicit
source/spec edits, renders a fresh attempt, recomputes the map and inspects the
final output. Preserve all explicitly requested formats; SVG is the default
graphic output. A genuine map enables vector targets; source receipts alone
enable general/region instructions. Then record the outcome:

```sh
python /absolute/path/to/easyviz/scripts/apply_figure_requests.py record \
  --figure-dir /absolute/path/to/project/attempt-01 \
  --target-dir /absolute/path/to/project/attempt-02 \
  --request-id REQUEST_UUID --changed-file plot-spec.json \
  --validation 'Inspected SVG at final dimensions and verified all declared exports.'
```

The target needs a current source handoff receipt or a current element map,
verified declared consumption/source provenance, unchanged primary and declared
auxiliary data hashes, and passing `qa.json`. New custom receipts require a
pre-export byte capture; complete legacy recorded claims use explicit migration.
Post-export hashing cannot verify consumption of unknown historical inputs. Region/general requests do not require fabricated element
identities. A raw external SVG can collect notes, but missing source provenance
cannot be recorded as an applied or accepted result. Changed files must be regular files contained in the target
attempt. Repeat `--changed-file` for the changed source/spec files. Use
`--superseded-id` for a processed request replaced by another processed request.
The source and target ledgers retain original requests, their target version,
changed files, validation and an `applied` history event. An Agent may have
intentionally changed the original source/spec while producing the target;
recording still requires the original figure/request binding and verifies the
target's actual new provenance. This is a record of explicit Agent work.

## Accept and restore

After visual inspection, preserve the accepted source/spec/data and matching
exports together:

```sh
python /absolute/path/to/easyviz/scripts/apply_figure_requests.py accept \
  --figure-dir /absolute/path/to/project/attempt-02 \
  --validation 'Reviewed SVG, marks and guides; declared export dimensions match.'

python /absolute/path/to/easyviz/scripts/apply_figure_requests.py restore \
  --figure-dir /absolute/path/to/project/attempt-02 \
  --out /absolute/path/to/project/attempt-restored
```

Acceptance requires current source/spec/data and every declared auxiliary input hash, matching actual export bytes, and passing QA. It saves
one immutable `accepted-snapshot` inside that attempt. Restoring verifies every
snapshot hash, the accepted QA identity and its actual export bindings, plus
matching SVG/source/spec/input provenance, then copies the bundle into a fresh attempt, rebinds the map/receipt and corresponding settings input locations to the new copies, and writes `restoration.json` plus a `restored` history event. Existing
attempts are never overwritten. Pending instructions inherited from the accepted
attempt become superseded in the restored attempt's ledger.

Snapshots retain all declared auxiliary input bytes, including aligned matrix
metadata and supplied linkage files. A changed or missing secondary source
cannot be omitted from acceptance; a missing or tampered dependency in the
snapshot prevents restoration before creating a new output. Restored file
locations may change, while source role/hash identity and original export bytes
remain unchanged.

For an adopted `statistics.analysis` result, the report and its four verified
companions remain together under `adopted-analysis/` with their required
basenames. The restored `plot-spec.json` retains the exact accepted bytes and
export provenance. Restoration also creates an explicit `rerender-spec.json`
that points to the preserved report bundle; adopt that derived spec for a new
render after the original analysis directory moves or disappears. Its result
digest, selected population and raw/adjusted P choice stay unchanged.

Restoration executes no author code. It restores the accepted source contents,
spec, input and already reviewed exports together; it cannot infer lost code
from SVG/PDF. This workflow handles one source/spec/data attempt and its explicitly declared auxiliary files. Shared profiles still require Agent preservation of every dependent panel. Imported author modules and external assets are preserved only when explicitly declared; the helper cannot discover undeclared runtime dependencies. A restored copy of a core source file is
provenance, not permission for `--render` to execute it as an arbitrary script.

Package the accepted/current attempt in `.ev` with only its declared inputs for
transport and library import; this does not recover missing historical source
or turn raster content into vectors. Importing and registering a bundle do not
execute its code.

Open the project library with `easyviz_workbench.py --project-dir PROJECT
--port 0`, or open the fresh result with `figure_workbench.py --project-dir
PROJECT --figure-dir NEW_ATTEMPT --compare-dir PREVIOUS_ATTEMPT --port 0`
to compare versions. The browser's
**Undo pending** only cancels a pending instruction; applied results are restored
through the accepted source/spec/export bundle.
