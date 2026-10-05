# EasyViz 0.5.0 preparation

**Proposal, researched 2026-10-05. No 0.5.0 runtime, MCP server or version change
is included in this work.** Reconcile this proposal with the completed 0.4.6
release before implementation; features already delivered in the minor releases
should become its baseline rather than another claimed addition.

The proposed major release has three themes: stronger first Create deliveries,
consistent source-to-element evidence for both tracks, and a shorter local
review-to-code loop. A new transport is useful only when it makes that loop
easier to use. **Create and Reproduce remain the only tracks.**

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

## 2. One attempt model for custom layers and optional figure assembly

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

## 3. Local review handoff, with an optional MCP adapter

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

## Implementation order and release decision

| Phase | Deliverable | Completion evidence |
| --- | --- | --- |
| A — after 0.4.6 review | Freeze the existing core baseline and unfamiliar evaluation tasks; settle the small attempt envelope and capability interface. | Current examples and older accepted attempts reopen; unsupported layers remain explicit; no new dependency is needed for inspection/help. |
| B — quality and composition | Add conditional mechanism retrieval, fresh complex Create exercises, custom selection capabilities and optional accepted-panel assembly. | Independent source/export checks and actual final-size literature comparison; basic panels retain distinct valid designs. |
| C — handoff | Shared local operations, bounded render jobs, browser submit/status and an opt-in MCP adapter on two tested hosts. | Equivalent CLI/MCP outputs and failures; real cancellation; no automatic execution claim on an unsupported host. |
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

Only themes A–D that meet their acceptance evidence should enter the eventual
0.5.0 release scope. This preparation makes no publication or implementation
claim and changes neither track.
