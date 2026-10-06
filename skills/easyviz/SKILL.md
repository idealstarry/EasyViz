---
name: easyviz
description: Create or reproduce scientific plots from bioinformatics source data, with supporting statistics, configurable palettes, and individual panels at final manuscript dimensions. Use for chart selection, reference-image reproduction, mark styling, typography, scientific figure export, and editing mapped SVG figures through .ev projects and the local workbench.
---

# EasyViz

Turn a data directory or prepared tables, a scientific question or reference image, requested changes, and export preferences into individual panels ready for manuscript assembly. Preserve the final canvas dimensions and text sizes so the user can arrange panels at their recorded size. SVG is the default graphic export; retain explicitly requested PDF, PNG or TIFF outputs. Use a validated `.ev` project for workbench editing and transport of declared plotting inputs.

Candidate helpers may also generate PNG for actual image review. That preview
does not require additional PDF or PNG formats in the final delivery.

## Inputs and scope

| Input | Establish |
| --- | --- |
| Data directory or source tables | Inventory relevant files and tables; establish field meanings, units, missing values, groups, and independent experimental units. |
| Chart type or reference | The intended visual message and the appropriate track. |
| Additions or changes | Layers, labels, statistics, palette, or styling to retain or modify. |
| Layout and export | Existing figure settings, physical panel dimensions, font, and requested formats. |

Accept data produced by upstream analysis. Data reshaping, descriptive statistics, statistical tests, correlation, fitting, and annotations are in scope. Bioinformatics software analysis belongs to the upstream Agent. Do not require author code to reproduce a reference.

Choose statistics from the study design: establish pairing, independent replicates, uncertainty definitions, and multiple comparisons when relevant. Cells and technical replicates are not automatically independent experimental units. Preserve supplied statistical results when appropriate; record any recalculation, method, sample size, effect size, and applicable correction. Missing scientific information may block a statistical layer without blocking the rest of the plot.

When using an adopted analysis, bind the plotted comparison to its current
result through [Statistical analysis](references/statistical-analysis.md).
Explicitly choose raw or adjusted P and whether observations show the included
analysis population or all supplied measurements. Cosmetic edits must reuse the
adopted result; a separate renderer test is not its substitute.

## Choose a track

| Track | Trigger | Read |
| --- | --- | --- |
| **reproduce** | A reference or “standard” defines the visual structure or style. Default input is a reference image plus user data, without author code. The reference paper need not publish Source Data. | [Reproduce](references/reproduce.md), then [Reference to code](references/reference-to-code.md) when staging inputs or implementing unfamiliar layers. |
| **create** | Build from data and a specified or yet-to-be-selected question/chart. A directory and no plot idea are valid inputs. | [Create](references/create.md), then [First reviewed delivery](references/first-draft.md) for a new panel; start with [Data exploration](references/data-exploration.md) when files or useful comparisons are unresolved. |

Honor an explicit track. Create first establishes the scientific comparison and
why each panel is useful; numeric-field eligibility or a gallery type is not a
plotting purpose. It can learn color and mark mechanisms from the
bundled literature guidance without a runtime reference image. Reproduce adopts
a supplied reference's structure/style. For additions to an existing plot,
retain its track, script, and accepted settings, then review the changed result.

Literature Source Data supplies auditable learning and validation cases for
reproduce; it is not required for runtime reproduction with the user's own data.
Directory inventory may help either track, but create recommendations must not
replace an adopted reference's structure. Keep only these two tracks.

## Shared resources

For a new Create panel, begin with the linked Create workflow. Read the relevant
scene in [Literature mechanisms](references/literature-style.md) and write the
short [first-panel design brief](references/design-space.md#plan-the-first-panel)
before selecting colors or a recipe. Then follow [First reviewed delivery](references/first-draft.md).
A useful first result needs task-specific geometry and layer relationships,
not just an exported template. Read only the details needed for this panel.
Carry the adopted question and leading layer into `create_intent` when using
the candidate helper. Its ranked mechanisms and physical-capacity measurements
support the choice; they do not select a scientific purpose or certify beauty.
Use custom code when the adopted organization is outside its supported routes.

| Need | Resource |
| --- | --- |
| Unresolved data/question or an adopted statistical analysis | [Data exploration](references/data-exploration.md), then [Statistical analysis](references/statistical-analysis.md) for an explicit plan. |
| Implement the chosen chart | [Chart library](references/chart-library.md): choose a core/focused recipe or custom code from its contract. [Worked cases](references/examples.md) are adaptable examples. |
| Decide graphical organization and mark/color roles | [Design paths](references/design-space.md), [Create colors and strokes](references/create-style.md), [Palettes](references/palettes.md). |
| An applicable local design mechanism or failure example | [Design cards](references/design-cards.md). Inspect relevant cards, not the whole gallery; their complete layout is not mandatory. |
| A matrix contrast, compartment time course or another justified companion layer | [Purposeful extra layers](references/complex-create.md). Preserve the exact transform, shared identities and independent units. |
| Physical size, fonts, guides and profiles | [Panel layout](references/panel-layout.md), [Legend layout](references/legend-layout.md), [Figure profile](references/figure-profile.md). |
| Reproduce proportions, shared keys and type hierarchy | [Reference geometry](references/reference-geometry.md). Observe relationships before adopting a canvas; source physical scale or font parameters may be unknown. |
| Actual-image review and unresolved overlaps | [Visual review](references/visual-review.md), [Point placement](references/collision-placement.md). Measurements support image inspection. |
| User-selected edits and attempt history | [Figure workbench](references/figure-workbench.md), then [Edit application](references/apply-figure-requests.md). |

For an unfamiliar Reproduce layer, read [Reference to code](references/reference-to-code.md)
and, when needed, [Complex reproduction](references/complex-reproduction.md).
Record what should match, what adapts to the user's data and what remains
unknown using the [Reproduction checkpoint](references/reproduction-checkpoint.md).
Check structure and shared guides before fine styling; compare the original
crop and actual output, with explicit residual differences.
[Source Data cases](references/literature-source-data.md) supply learning material;
they do not require the user's reference paper to publish its data or code.

## Execute

1. Inspect the data and user requirements. Fill missing cosmetic preferences from recorded project settings or the shared defaults; clarify only consequential ambiguity.
2. Follow the chosen track to produce an adopted plotting specification. In Create, decide the reading task, graphical organization and visual roles separately using [Design paths](references/design-space.md); a basic family has several valid solutions. Additional layers need a purpose. In Reproduce, obtain an independent image reading before selecting implementation templates.
3. Establish physical width and height, fonts, formats and project settings. Choose the leading layer and where category identity is decoded before choosing hues or outlines. Preserve shared profiles and category assignments, and resolve conflicts before rendering. A gallery palette or sample's complete layout is not the default for every task.
4. Check implementation contracts. For new Create panels, inspect relevant [card mechanisms](references/design-cards.md) and follow [First reviewed delivery](references/first-draft.md). Candidate helpers cover a limited design set; adapt a spec or write focused/custom code when proposals miss the chosen route, including within a supported chart family. Examples have bounded contracts; copy them into the writable project before adapting. Preserve scientific and explicit user constraints; never guess that an existing key was a default and remove it. Reproduce retains its adopted reference and settings.
5. Actually open the rendered images before presenting a finished result. Compare meaningful alternatives when design or reading-task choices are unresolved; routine corrections need no compulsory candidate set. Inspect palette decoding, point/summary crossings, contour hierarchy, category gaps, cell proportions, guide footprint, clipping and glyphs at final proportions. Use [Create design decisions](references/create-style.md), [physical point placement](references/collision-placement.md) and [Legend layout](references/legend-layout.md) where applicable. Obtain independent review when available; otherwise label self-review. Follow [Visual review](references/visual-review.md), using at most three initial visual passes while preserving science, agreed fonts and dimensions. Later feedback or explicitly continued work retains the cumulative history as a followup; it does not establish three-pass first-delivery success.
6. For new Create delivery, save and check the review bound to the selected current exports using [First reviewed delivery](references/first-draft.md); pending or stale records do not establish readiness. Deliver individual panels, separate `caption.md`, runnable code/settings, traceable data or input references, computed statistics when used, and actual review findings. Report unresolved limitations without claiming an unreviewed output is finished.
7. When the user asks to use EasyViz to create, reproduce or edit a figure, open the [local workbench](references/figure-workbench.md#default-activation) by default after the first current validated SVG and `.ev` are ready. Show that attempt and provide its local address. Reuse the project's running page for subsequent revisions. When MCP tools are available, connect the actual authoring session and wait for submitted annotations through the [same-session workflow](references/mcp.md#original-session-editing). Honor a request for files only or no browser; if browser opening is unavailable, report that and provide the address. An explicit request to open the workbench can start the library before a figure exists. Opening the page alone does not establish an Agent connection.

## Output rules

| Area | Requirement |
| --- | --- |
| Assembly | Export one panel per file. Leave assembly and panel lettering to the user unless lettering is requested; reserve any requested letter inside the fixed canvas. |
| Panel text | Keep axis names and units, ticks, legends, colorbars, and essential data annotations. By default, omit extra titles, subtitles, standalone overview counts, and explanatory footnotes inside the image. Add an in-image title only when the user explicitly requests it, including in reproduce; a title present in the reference does not authorize copying it. |
| Caption | Put explanatory prose, abbreviation definitions, methods, source attribution, and caveats in a separate `caption.md`. Use journal-style figure/panel prose with identifiers only when known; do not invent a figure number or panel letter. The caption is a separate deliverable, not text to place on the canvas. |
| Fixed size | Keep the entire canvas, including legends and margins. Avoid export cropping that changes physical dimensions. Use the same physical size across formats. |
| Typography | Keep agreed font sizes while adjusting wrapping, margins, ticks, and legend position. Format count labels as *n* = 15: italicize only *n*, keep the equals sign and digits upright, and leave spaces on both sides of `=`. If content needs a different canvas, resolve that change before replacing an agreed assembly size. |
| Mark styling | Choose an explicit policy per comparable mark role and match its legend: fixed-size observations may be opaque filled or hollow, distribution summaries may be outlined, and quantitative filled-area circles retain their area contract. Avoid blanket fading or removing every boundary. Reproduce follows the adopted specification and user requirements. |
| Data integrity | Do not silently omit observations, reinterpret uncertainty, recompute upstream bioinformatics analysis, or invent values from reference pixels. |
| Availability | In sparse dot matrices, distinguish observed zero, explicitly unmeasured and coordinates absent from the supplied table. A missing row does not establish that measurement was attempted. Retain quantitative areas; use a separate decoded presence flag if tiny positive marks need help at the final size. |
| Traceability | Save the track, reference input mode, source paths, transformations, mappings, statistics, actual font and palette, dimensions, formats, and dpi. |
| Editable project | Package the current SVG, genuine nonempty element map, code/settings, source provenance and declared plotting inputs in `.ev` for workbench use. Renaming a PDF, PNG or SVG does not create an editable project. Include requested additional exports when present; bundle only declared inputs. |
| Evidence | Distinguish image observations, caption or method evidence, author-code evidence, and design decisions. Report checks actually performed and their input scope; a successful example does not establish untested generalization. Disclose an unavailable visual review. |

## Local editing and MCP

Keep workbench edits in the conversation that first invoked EasyViz unless the
user explicitly requests a separate editing worker. When the user says “Apply
the saved EasyViz workbench comments,” read the current figure's pending
requests and perform the [edit application](references/apply-figure-requests.md#iterate-from-the-original-chat)
in this turn. **Save drafts** is sufficient; do not require an extra **Submit
edits** or copied instructions. First inspect existing jobs when available:
process a matching queued or still-valid running original-session job rather
than applying the same requests twice. Free-form comments require explicit
Agent source/specification edits, fresh exports and actual-image review.

For browser-submitted batches with MCP, call
`connect_session` using the current host's actual authoring-session ID, keep its
connection token private, and call bounded `wait_for_submission` while the
Agent remains active. A submitted job returns to that waiting Agent; continue
the adopted track, edit the source and render a fresh attempt in this same
conversation. Report actual editing, rendering and reviewing starts through
`report_session_progress`; claiming a job establishes receipt, not editing.
Register the new attempt and use `complete_session_job` only for fulfilled
requests after inspecting the actual result. The project's original-session
owner persists across expired connections; reconnect that owner rather than
substituting another conversation.

Live MCP waits receive work only while the Agent is active. An optional host
scheduled check is a separate way to resume the original conversation: create
it successfully in the host first, then register its actual ID, scope and
expiration using [MCP guidance](references/mcp.md). A local registration or a
requested interval does not prove idle delivery. If no host task is verified,
retain saved requests for the original Agent's next turn. Do not silently enable the
dedicated Codex worker: it starts fresh sessions and cannot fulfill an
original-session requirement.

Open the [independent workbench](references/figure-workbench.md) for its project
library, validated `.ev` imports, numbered selections, comparison and restoration.
Read the user's editable workbench name from `figure-info.json` or service
inspection and preserve it in new attempts. It identifies the project figure;
it does not authorize adding an in-image title.
SVG supplies vector interaction through its genuine element map; collections
remain groups unless observations have individual mappings. Raster layers do
not become vectors. **Save drafts** retains instructions; **Submit edits**
queues them for the connected original session and exposes progress or
cancellation. The optional dedicated worker remains a separate, explicitly
requested execution route. Preserve original attempts, the adopted science
and source bindings; record outcomes only against verified new exports. See
[Edit application](references/apply-figure-requests.md) for manual processing.

An optional [project-scoped MCP connection](references/mcp.md) exposes the same
library, requests, render jobs and original-session queue to compatible Agents.
It also exposes the separate dedicated-worker route. These are editing
interfaces for the existing two tracks.

For independent image reading and comparison, pass an explicit file path to [EasyViz Reference Reader](../easyviz-reference-reader/SKILL.md) or [EasyViz Figure Reviewer](../easyviz-figure-reviewer/SKILL.md). These are narrow helper skills, not automatic proof that a subagent used them. Supply accessible images and the permitted context. If a helper or collaboration tools are unavailable, follow the corresponding reference directly and record that the review was not independent.
