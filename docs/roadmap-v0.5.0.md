# EasyViz 0.5.0 research and delivery scope

**Research proposal: 2026-10-05; implemented scope reviewed: 2026-10-06.**
The sections below retain the research targets, including targets that need
more evidence. The delivery table distinguishes the implemented 0.5.0 work
from those remaining targets. Existing 0.4.6 features remain the baseline.

| Area | Delivered and checked in 0.5.0 | Remaining research target |
| --- | --- | --- |
| Create | Adopted reading-task intent, 11 conditional literature mechanisms, physical preflight, and adopted analysis-result binding; eight forwarded tasks produced ten independently inspected final panels. | Inputs were frozen after development began and before the forward runs. They use seven known studies with renamed fields and changed questions, plus one synthetic ambiguous input. They do not establish unseen-study, novice or model-wide efficacy. |
| Reproduce | Explicit relationship/adaptation/unknown checkpoint; a new Source Data-backed scWAT broken-axis panel, an independent reference reading and actual SVG/PDF mapping checks; a separate changed-data transfer. | Four new unfamiliar reference trials, including raster-only and no-Source-Data references, remain a larger evaluation target. Optional accepted-panel assembly and source-data packs are deferred. |
| Workbench | Shared local service, actual code-backed core cosmetic previews, per-request outcomes, attempt comparison, acceptance and restoration, bounded jobs and source checks. | Custom code and free-form changes require an active Agent. Saving does not start an idle chat. Individual selection exists only where a renderer supplies the mapping. |
| MCP | Optional official-SDK stdio adapter with 13 tools, equivalent service operations, protocol/tool/resource round trips and project-scoped access. | Cross-client Agent execution and automatic host activation remain separate compatibility targets. Protocol connectivity alone does not establish them. |
| Repository | Runtime failure-path review, transactional packaging/installation fixes, streaming file digests, removed duplicate build paths and repaired the demonstration driver. | Checked failure classes and measured package costs are recorded in release QA; neither test count nor gallery appearance proves absence of all defects. |

See [release QA](../evals/release-qa/v0.5.0/README.md) for the current evidence,
source versions and limitations. The workbench works without the optional MCP
dependency.

The proposed major release has three themes: stronger first Create deliveries,
consistent source-to-element evidence for both tracks, and a shorter local
review-to-code loop. A new transport is useful only when it makes that loop
easier to use. **Create and Reproduce remain the only tracks.**

**Priorities confirmed by the user on 2026-10-06:** MCP integration and the
workbench upgrade are major 0.5.0 deliverables alongside both track workflows.
The MCP adapter remains an optional installation dependency, while its
implementation and actual host compatibility are part of the release work.

The [research record](../evals/v0.5.0-research/README.md) compares nine public
repositories at pinned commits, separates implemented facts from proposed
adaptations, and records licensing and evidence limits. Repository popularity
and names such as “publication-ready” are not quality evidence.

## Starting architecture

The [inspected snapshot](../evals/v0.5.0-research/architecture-snapshot.json)
already supports these foundations:

| Existing foundation | Source | Consequence for 0.5.0 |
| --- | --- | --- |
| Purpose, data-region geometry and layer hierarchy precede palette selection | [Design space](../skills/easyviz/references/design-space.md), [first delivery](../skills/easyviz/references/first-draft.md) | Improve selection and transfer of design mechanisms; preserve the Agent's ability to write custom code. |
| Core and focused recipes export physical manuscript panels; custom scripts use shared helpers | [Chart library](../skills/easyviz/references/chart-library.md) | Retain one local drawing core and an explicit custom route. |
| Reference reading distinguishes observed, inferred and unknown layers; complex audits retain adoption and alignment | [Reference to code](../skills/easyviz/references/reference-to-code.md), [complex reproduction](../skills/easyviz/references/complex-reproduction.md) | Reuse these contracts for unfamiliar reference figures, including references with no Source Data. |
| Real artists have role, source keys, spec pointers and editable properties | [figure_elements.py](../skills/easyviz/scripts/figure_elements.py) | An element map can connect a human selection to a code change. A collection is currently a group, not an invented individual observation. |
| The local page saves version-bound batches; the application helper prepares supported cosmetics and records new attempts | [Workbench](../skills/easyviz/references/figure-workbench.md), [application helper](../skills/easyviz/scripts/apply_figure_requests.py) | Add a handoff and job interface around this behavior, retaining source checks and immutable exports. |

The inspected 0.4.4 archive was about 12.2 MB with 854 entries. The integrated
0.4.6 archive, measured on 2026-10-06, is 18,703,087 bytes with 921 files. Its
baseline now includes consumed-input handoff, focused CSV identity checks,
registered-observation clipping, three distinct integrated Create cases and
measured reference geometry. These are existing foundations for 0.5.0. Optional
source-data packs could contain future corpus growth without expanding every
installation; this remains a proposal. The local workbench uses the Python
standard library; rendering has a separate scientific dependency set.

## 1. Better first Create deliveries through conditional design knowledge

Make literature learning retrievable by **reading task and graphical burden**,
not only by plot name. Each mechanism should state its source panel, observable
geometry, applicability, adaptations and a counterexample. For example, a
compact paired observation view and a dense annotated matrix solve different
reading problems even when both use two treatment colors.

Extend the existing design cards with searchable metadata: observation grain,
category count, within-category series count, available data-region span,
required statistical layers, guide types and supported missing states. Search
should return a few applicable mechanisms with reasons and non-applicability
notes. A mechanism teaches an arrangement or layer relationship; it does not
require the source paper's palette, complete template or statistical method.

[AgentFigureGallery](https://github.com/Dsadd4/AgentFigureGallery/blob/0b55f26fd575a00b5ebacb619d953b0a008e0126/skills/agent-figure-gallery/SKILL.md)
provides a useful pattern for external reference packs and scoped preferences.
For EasyViz, optional visual selection should help users express taste while
the normal path remains an autonomous first finished panel. A liked design
should be scoped to its task and mark role; it must not establish a denominator,
uncertainty definition or universal color assignment.

Use representative real Source Data for mechanisms that need several related
layers: longitudinal estimates with individual trajectories; paired changes
with explicit unit identity; annotated matrices with keyed tracks and marginals;
and count/fraction panels with independent quantitative guides. Retain strong
basic bar, interval, box and violin cases. More layers require a scientific
purpose, and simple comparisons should stay simple.

**Acceptance evidence:** freeze eight unfamiliar Create tasks, covering basic
and integrated arrangements, before development tuning. Give the Agent data,
the question and final size, without the original literature image at runtime.
Retain the first candidate and first finished delivery separately. Independently
verify source values and summaries, then compare delivered panels with relevant
literature on spacing, hierarchy, line clarity, color roles and usable density.
An improvement must identify a visible reading benefit. A particular panel's
preference result does not establish a general CNS-level guarantee.

For continuous color, audit the adopted scale and perceptual ordering in
addition to appearance. Brightness preferences must not manufacture extrema or
an unsupported center. [Crameri et al.](https://www.nature.com/articles/s41467-020-19160-7)
explain how uneven gradients can create visual emphasis absent from the data.

### Create workflow polish

The existing Create, data-exploration, statistical-analysis and first-delivery
guides already require a scientific purpose, confirmed inference design,
task-specific geometry and actual image review. The improvement should connect
their decisions to execution, rather than add another mandatory reading list.
Reuse current inventory, analysis and spec artifacts where possible; a simple
panel needs a short design brief, not a large planning document.

| Stage | Proposed execution improvement |
| --- | --- |
| Directory to question | Carry field meaning, units, observation grain, pairing, supplied summaries and consequential unknowns from intake into the adopted drawing/analysis plan. Present one concise list of information that affects the result. Descriptive work can proceed while an unsupported inference stays unresolved. |
| Adopted analysis to plotted statistics | Bind statistical labels and derived summaries to the adopted comparison/result, including actual analysis units, included records, exclusions, effect direction, interval meaning and raw/adjusted P where applicable. Cosmetic changes reuse that result. Keep displayed observations distinct from the subset contributing to a comparison. |
| Question to design | Retrieve mechanisms against the adopted reading task, then check available dimensions and actual data before choosing a recipe or custom implementation. Keep several valid designs within a family. A candidate's index, familiar example or category count must not choose the scientific purpose. |
| Design to physical panel | Extend current physical placement and guide measurements across basic families: visible body width, stroke-inclusive gaps, raw-point capacity, label room and matrix-cell aspect. Report infeasible space with an actionable alternative; preserve explicit dimensions, text sizes and all observations. |
| Contextual color and stroke roles | Bind identity to the layer that readers actually use, retain accepted project mappings, and compare complete treatments on the real panel. Control-focused, position-decoded and multi-series tasks can use different treatments. Record quantitative scale endpoints, units, transformations and any scientifically adopted center before selecting a ramp. |
| Internal review to first delivery | Turn concrete review findings into supported next operations and rerender affected outputs before presenting the finished panel. Retain the current bounded review/history rules. Separate scientific failures, physical/export failures and visual preferences; neither a passing record nor a prettier palette settles the others. |

The current [candidate helper](../skills/easyviz/scripts/create_candidates.py)
explicitly marks its reading task as a chart-family hint, not the user's adopted
objective. Its finite routes use chart/data features and preserve explicit
locks. Improve the handoff from the Agent's task/mechanism decision to that
helper or to custom code; do not describe the existing helper as a general
automatic designer or remove legitimate source/settings constraints.

**Observed analysis-to-plot gap:**
[analyze.py](../skills/easyviz/scripts/analyze.py) requires confirmed design and
declared comparisons, while
[render.py](../skills/easyviz/scripts/render.py) still computes its own limited
statistics and uses them for annotations. The latter permits omitted unit IDs
for some methods and records a single unadjusted test; it does not consume the
analysis helper's results. These are separate inferential paths, so a saved
analysis report alone does not establish that its result is what the plot
displays. Prioritize an explicit adopted-result binding in 0.5.0, accepting
traceable supplied upstream results as well as EasyViz computations. Define
legacy compatibility/migration without silently changing the methods or
meaning of older accepted outputs. This binding is relevant to statistical
layers in either track; descriptive-only panels need no inferential result.

Check a tied small-sample comparison and an incomplete paired comparison across
two supported visual designs and a workbench recolor. Adopted numerical results
must stay consistent, annotations must identify the actual comparison, and a
changed source or analysis plan must invalidate the old binding. Verify
unadjusted versus adjusted results explicitly when a declared comparison family
uses adjustment; do not infer the family from whichever panels are visible.

Include in the eight frozen tasks a directory with ambiguous sampling units,
a long-label compact comparison, and two tasks in the same basic family that
justify different hierarchy/color roles. Verify that the Agent resolves these
without human cosmetic coaching, forced extra layers or scientific drift.

## 2. Stronger Reproduce adoption, shared attempts and optional figure assembly

### Reproduce workflow polish

The production workflow already separates independent reference reading,
adoption, layer-to-code planning and actual comparison. Make these decisions
visible and easier to execute for unfamiliar references, using the existing
reference packet/specification instead of a second parallel contract.

| Stage | Proposed execution improvement |
| --- | --- |
| Reference to adopted relationships | Present a compact card of what should match, what adapts to the user's data and what remains unknown. Inspect the selected panel with its relevant shared guides and context; retain observed/inferred/unknown evidence and the chosen input mode. |
| Geometry before fine styling | Produce an early structure/layout check of plot regions, aligned layers, guide footprint and relative mark/type scales. Use PDF geometry when available; a screenshot supplies relative relationships, not recovered mm/pt values. Tune appearance after the structural relationships work. |
| New data adaptation | Explicitly handle changed category counts, value ranges, missing states and longer labels without dropping data or forcing old coordinates. Preserve the adopted encodings and scientific relationships; record required layout/order/scale adaptations and unresolved capacity limits. |
| Uncertain layers to action | Name the missing fact, affected layer and parts that can already be implemented. Unknown uncertainty definitions, normalization or clustering are not filled by visual imitation. Required unresolved layers remain incomplete, while supported layers can proceed. |
| Custom layers to review | Connect each implemented layer to actual artists, retained records, editable bindings and relevant numerical/geometry evidence. Supply a selected original-reference crop beside the new output, with a concise list of structural matches, data-driven adaptations and residual differences. |

For the four frozen references, vary the user data's category count and label
length on an adopted structure, include unknown statistical meaning, and verify
custom layer selection. Keep numeric checks separate from visual fidelity.
Document known versus unknown reference physical size before comparison; do
not stretch a reference or use pixel similarity to certify a reproduction
whose data and physical dimensions differ. Preserve the manuscript text and
separate-caption defaults in both tracks.

### Shared attempt envelope and optional assembly

Introduce a small compatibility envelope around existing outputs, rather than
a replacement plotting language. An ordinary panel can retain its current
settings, QA and element files. The envelope should identify the track, source
artifacts, adopted settings, implementation, exports and review state. Complex
panels add the existing layer dependencies when they are useful.

Learn explicit layer composition and shared/independent scale resolution from
[Vega-Lite's layer contract](https://github.com/vega/vega-lite/blob/213faf313cd2e8b1f94b61d24e90cac2e77b576e/src/spec/layer.ts).
Apply those ideas to EasyViz's adopted scientific relationships. A renderer
must declare which layers it consumes; unsupported layers remain visible as
requirements rather than disappearing behind a successful export.

Add an optional **assembly operation**, available to either track, that places
already accepted panels at their recorded millimetre dimensions. Keep each
panel's data, typography and caption accessible. Shared guides, scale changes,
panel letters and a changed layout need an explicit adopted assembly plan.
Assembling an SVG/PDF must preserve vector marks and text without silently
resizing the individual panels. This answers the practical need for several
compact barplots in one figure while retaining individual panel exports.

For selection, expose capability separately for groups, individual records,
matrix cells, annotations and guides. [mplcursors](https://github.com/anntzer/mplcursors/blob/566963caa0c527825e735c9146c9fae129ac898c/src/mplcursors/_pick_info.py)
demonstrates artist-specific picking and indices. EasyViz should use the same
principle with explicit source-record bindings in its SVG manifest; a nearest
pixel alone cannot establish biological identity. Dense panels can retain group
and region review when per-record mapping would be costly.

**Acceptance evidence:** four unfamiliar Reproduce references, at least two
with custom coordinate/layer relationships, use the user's supplied tables and
no author plotting code. Record every adopted layer and compare original and
output at consistent physical size. Verify numeric mappings, alignment and
guide meanings independently. Test a reference with no published Source Data,
an intentionally unresolved statistical layer, and a raster-only reference.
For assembly, verify actual PDF/SVG dimensions, font sizes and source-bound
element identity through an export-and-reopen round trip.

## 3. Workbench upgrade and local review handoff, with an optional MCP adapter

**Scope confirmed, 2026-10-06:** both the workbench upgrade and MCP integration
are 0.5.0 priorities. Keep the adapter opt-in at installation, and the upgraded
local page usable with an ordinary code-capable Agent. Both tracks use the same
review workflow and keep their adopted science. Verify host delivery separately
from protocol connectivity before claiming automatic Agent processing.

### Workbench changes worth implementing

Consecutive numbered drafts, separate per-location instructions, batch saving,
mapped category selection, previous/current comparison and history are already
available. Verified acceptance and restoration already exist in the application
helper. These are the baseline, not new 0.5.0 claims. The current page does not
execute the helper or activate an Agent when saving requests.

| Proposed upgrade | User-visible benefit | Implementation boundary |
| --- | --- | --- |
| Selection inspector and finer targets | Show what was selected, its source identity and actual editable properties; support individual observations, matrix cells and guide parts where registered. | A collection remains a group unless its implementation supplies per-record identity. A region cannot invent source records. Dense figures retain a truthful group/region fallback. |
| Code-backed cosmetic preview | Adjust supported colors, strokes and line styles, then preview a newly rendered attempt. Add text size and legend/annotation offsets where explicit bindings permit them. | Use pt for typography/strokes and mm for layout. Existing automatic bindings cover a narrow property set; font and offset support requires new renderer bindings. Custom script edits remain Agent work. SVG/PDF/PNG must come from the same implementation, rather than a browser-only SVG patch. |
| Batch submission and per-request results | Retain each numbered opinion, show waiting/editing/checking/ready states, and explain which requests were applied, conflicting or unresolved. | Separate persisted requests, actual host delivery and running work. A disconnected or unsupported host must not be shown as editing. Duplicate submission must not apply a batch twice. |
| Version review, acceptance and restore controls | Switch attempts, compare at matched physical sizes, inspect changed elements and accept or restore a reviewed result from the page. | Wrap the existing verified attempt operations. Restore source/spec/data/exports into a fresh attempt, preserving every prior attempt; swapping the visible SVG alone is insufficient. |

Keep the canvas dominant and the inspector compact. Show controls for the
current target, with clear property units and scope, instead of exposing every
setting at once. Review UI, source notes and request badges stay outside the
downloaded manuscript panel; retain its agreed dimensions, typography and
separate caption. Preview jobs may replace temporary candidates, but must not
silently replace the accepted attempt or mark unrendered requests applied.

### What MCP would add

An optional MCP adapter can let a connected Agent discover these local
operations, obtain typed inputs and actionable errors, read the exact pending
batch, and return the new preview and verification record. This should reduce
client-specific command/path handling when using several local Agents. The
design and scientific judgment still come from the skills and rendering code;
the adapter does not establish better aesthetics or numerical correctness.

MCP notifications are useful for synchronization when a host subscribes and
handles them; they do not guarantee that an idle conversation will start a
turn. An embedded review UI through
[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) is a later
option on hosts that support the extension. Keep the localhost page as the
portable interface and verify actual client behavior before promising direct
submission to an Agent.

### Shared local operations and execution

The useful user flow is: open an attempt, annotate several locations, submit
the batch, let the attached Agent revise code, then inspect the next attempt.
The current page's save action only persists requests. Automatic dispatch needs
a verified host integration and an active attached Agent; an MCP server alone
does not wake a chat or create an Agent turn.

First expose one transport-independent Python service contract and a CLI JSON
view. The browser and any later MCP adapter should call the same operations.
Proposed operation names below are design sketches, not existing APIs:

| Operation | Minimum result and boundary |
| --- | --- |
| `capabilities` | Actual installed core/adapter version, supported input types, selection granularity, renderers and host handoff availability. |
| `inspect_sources` / `stage_reference` | Source artifact IDs, table/schema or staged reference evidence, consequential unknowns; no inferred pairing or statistics. |
| `render_attempt` | New attempt identity, actual files, measured canvas/fonts and diagnostics; consumes an adopted spec or a registered custom renderer. |
| `get_attempt` / `list_requests` | Explicit attempt/version, source-bound element map, pending batch and review/acceptance status. |
| `prepare_edits` | A concrete supported spec change or an Agent handoff for custom work, retaining each numbered request and its target version. |
| `record_outcome` / `accept_attempt` | Applied request IDs, actual changed implementation/spec/exports, verification and adopted outcome. |

Each result should include structured fields plus a short human-readable
explanation. Return preview images and resource links to the exact attempt;
avoid sending large tables through tool arguments when a registered local
artifact suffices. [The MCP tool specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
supports structured results and explicit state handles; use them to preserve
identity across calls.

Use separate identities for the project, source snapshot, attempt, element,
request batch and render job. An element ID is stable only within its documented
key scheme; applying an old request to a changed source needs fresh adoption.
The source snapshot can retain internal content bindings while the user sees
clear version names rather than checksum management.

Long rendering jobs need explicit handles with `queued`, `running`, `succeeded`,
`failed` and `cancelled` states. Report real phases and diagnostics, preserve
the accepted attempt, and publish a new output only after its files and checks
complete. Cancelling must stop the owned renderer process and prevent a
cancelled job from marking requests applied. A host disconnect and a job
cancellation need defined, tested behavior; cancelling a handler does not
automatically terminate a synchronous worker or child process.
[The SDK cancellation guide](https://py.sdk.modelcontextprotocol.io/handlers/cancellation/)
documents this distinction and HTTP modes that do not propagate cancellation.

For local agents, begin with an optional stdio adapter pinned to a tested SDK
release. The observed latest stable Python SDK is
[2.3.0, published 2026-10-02](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0).
Protocol and host support must be checked again before implementation. The
[2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28)
moves durable Tasks and MCP Apps into optional extensions. Use Tasks only after
both sides demonstrably support the extension; the core job handles and CLI
status route remain usable without it. An inline MCP App may reuse the review
page later, but is not a prerequisite for localhost editing.

Configure project access and renderer execution through the host's existing
authorization. Bind reads/writes to registered local artifacts and fresh output
directories, retain the page's Origin/token protection, and never treat protocol
roots or tool annotations as filesystem authorization. A custom script runs
through the authorized Agent/runtime scope, with its implementation identity
recorded. An adapter must not add a free-form shell tool or transmit source
tables to a remote rendering endpoint by default.

Use explicit configured project/artifact handles for new integrations. The
[current SDK guide](https://py.sdk.modelcontextprotocol.io/handlers/sampling-and-roots/)
marks roots and sampling deprecated under the 2026-07-28 protocol; legacy
support can be tested without making either a new architectural dependency.

**Acceptance evidence:** submit a mixed element/region batch, dispatch it once,
revise both core and custom plots, and show the new attempt beside the old.
Verify duplicate submission, stale source, cancellation during render, two
concurrent batches, missing MCP, unavailable host notification and process
restart. Without host dispatch, show a truthful “saved; tell the Agent to apply”
fallback and let the Agent read the ledger directly. No copying of the user's
individual instructions should be required.

Also verify code-backed cosmetic previews against actual SVG/PDF/PNG exports,
selection identity at each advertised granularity, per-request outcomes and
page-driven acceptance/restoration. Test rapid repeated edits and a failed
preview without losing the visible accepted version. The local workbench
upgrade must work with the optional MCP package absent. Adapter acceptance
separately requires equivalent local/MCP results on two actual hosts; automatic
Agent dispatch is claimed only for the host routes tested successfully.

## Implementation order and release decision

| Phase | Deliverable | Completion evidence |
| --- | --- | --- |
| A — after 0.4.6 review | Freeze the existing core baseline and unfamiliar evaluation tasks; settle adopted analysis-to-plot binding, the small attempt envelope and capability interface. | Current examples and older accepted attempts reopen; unsupported layers remain explicit; no new dependency is needed for inspection/help. |
| B — track quality and composition | Connect adopted purpose/analysis to rendering, add conditional mechanism retrieval and physical preflight, strengthen unfamiliar-reference adoption/comparison, custom selection and optional accepted-panel assembly. | Independent source/analysis/export checks and actual final-size literature comparison; basic panels retain distinct valid designs and cosmetic changes preserve adopted statistics. |
| C — workbench and MCP handoff | Shared local operations, selection inspector, code-backed cosmetic previews, page-driven attempt review/restore, bounded jobs, browser submit/status and an opt-in MCP adapter on two actual hosts. | The local upgrade works without MCP; export/selection identity, per-request results, restore and cancellation are verified. The adapter requires equivalent CLI/MCP results; automatic dispatch is reported per tested host. |
| D — major-release review | First-delivery evaluation on two actual local Agent/model routes, including one available domestic model, plus compatibility and package inspection. | Record exact model/client/runtime, science failures, blind visual judgments, attempts and human intervention separately; publish known limits. |

Keep package/runtime boundaries explicit: a standard-library inspection/review
layer, the current scientific rendering dependencies, optional reference packs,
and optional MCP dependencies. Set a byte/dependency/startup budget using the
0.4.6 baseline. Test core installation and help with network access disabled;
do not install the SDK, Node or external corpora merely to render a local panel.

The unresolved evidence is substantial: new-model generalization, novice use,
unknown-reference interpretation, cross-platform font appearance, large dense
SVG selection cost, and real host handoff compatibility. None is resolved by
more gallery images or a higher unit-test count. Do not promise “all bugs
fixed”; enumerate covered failure classes, residual cases and the actual
major-release acceptance evidence.

The delivery scope above supersedes these proposed phase targets. Publish
implemented behavior with its actual verification; keep incomplete evaluation
targets visible instead of reporting them as completed. Both tracks remain
Create and Reproduce.
