---
name: easyviz
description: Create or reproduce scientific plots from bioinformatics source data, with supporting statistics, configurable palettes, and individual panels at final manuscript dimensions. Use for chart selection, reference-image reproduction, mark styling, typography, scientific figure export, and editing mapped SVG figures through .ev projects and the local workbench.
---

# EasyViz

Turn a data directory or prepared tables, a scientific question or reference image, requested changes, and export preferences into individual panels ready for manuscript assembly. Preserve the final canvas dimensions and text sizes so the user can arrange panels at their recorded size. SVG is the default graphic export; retain explicitly requested PDF, PNG or TIFF outputs. Deliver reviewed graphics directly in the conversation. The workbench, MCP connection and `.ev` project are optional editing tools.

Candidate helpers may also generate PNG for actual image review. That preview
does not require additional PDF or PNG formats in the final delivery.

## First use and focused intake

On the first EasyViz plotting use in each conversation, give one short introduction
in the user's language. It must briefly communicate both reviewed delivery with
direct chat refinements **and** the optional workbench for selecting/annotating
elements or regions, including a phrase the user can say to open it (for example,
“open the workbench” or “打开工作台”). Do not omit workbench discovery when
shortening the introduction. Adapt the wording naturally; this is not a required
verbatim template. For example:

> EasyViz is ready. I'll draw and inspect the figure before delivery; you can ask
> for small changes here. Say “open the workbench” if you'd like to select elements
> or regions and annotate several changes. Save the comments there, then ask me
> to apply them in this conversation.

Remember that introduction in the conversation context only. Do not create a
global flag, telemetry, extra file or persistent preference for it. Do not repeat
it for every panel or while applying edits. A discussion about EasyViz or its
installation alone does not begin a plotting task or start the workbench.

Read available data, project notes, accepted settings and, for Reproduce, the
reference before asking questions. For each new plotting request, use **at most
two intake rounds**, with one or two consequential questions per round; skip
questions already answered or unnecessary for a sound result. Do not restart
the budget for each table, candidate or routine revision. Prioritize the purpose,
experimental unit, pairing, units and uncertainty definition. Ask about manuscript
versus presentation use or a material layout preference when it changes the
design. Give brief answer choices and a reasoned recommendation when helpful;
“recommend for me” delegates design judgment, not missing scientific facts.

For Create, settle what the reader should compare and recommend an encoding.
For Reproduce, settle the reference region, real-data mapping and intended
adaptations. The user need not specify a renderer, every hue or line width.
Honor supplied choices and carry adopted answers into the existing plotting
specification, settings or project context using their supported fields; retain
their provenance without adding unsupported keys to strict schemas. After two
rounds, keep unresolved facts explicit and proceed with supported descriptive
layers. Do not invent pairing, units or inferential assumptions to finish a
statistical layer. If even a descriptive mapping remains undefined, state that
specific blocker instead of drawing a misleading figure.

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

1. Give the first-use introduction once, inspect the data and user requirements, and follow the focused intake above. Fill missing cosmetic preferences from accepted project settings or task-appropriate design judgment.
2. Follow the chosen track to produce an adopted plotting specification. In Create, decide the reading task, graphical organization and visual roles separately using [Design paths](references/design-space.md); a basic family has several valid solutions. For a custom/multi-layer panel or related set, use [Evidence before layout](references/evidence-first-create.md) to distinguish the main comparison from lookup detail and allocate supporting tracks before rendering. Additional layers need a purpose. In Reproduce, obtain an independent image reading before selecting implementation templates.
3. Establish physical width and height, fonts, formats and project settings. Choose the leading layer and where category identity is decoded before choosing hues or outlines. Preserve shared profiles and category assignments, and resolve conflicts before rendering. A gallery palette or sample's complete layout is not the default for every task.
4. Check implementation contracts. For new Create panels, inspect relevant [card mechanisms](references/design-cards.md) and follow [First reviewed delivery](references/first-draft.md). Candidate helpers cover a limited design set; adapt a spec or write focused/custom code when proposals miss the chosen route, including within a supported chart family. Examples have bounded contracts; copy them into the writable project before adapting. Preserve scientific and explicit user constraints; never guess that an existing key was a default and remove it. Reproduce retains its adopted reference and settings.
5. Actually open the rendered images before presenting a finished result. Compare meaningful alternatives when design or reading-task choices are unresolved; routine corrections need no compulsory candidate set. Inspect palette decoding, point/summary crossings, contour hierarchy, category gaps, cell proportions, guide footprint, clipping and glyphs at final proportions. Use [Create design decisions](references/create-style.md), [physical point placement](references/collision-placement.md) and [Legend layout](references/legend-layout.md) where applicable. Obtain independent review when available; otherwise label self-review. Follow [Visual review](references/visual-review.md), using at most three initial visual passes while preserving science, agreed fonts and dimensions. Later feedback or explicitly continued work retains the cumulative history as a followup; it does not establish three-pass first-delivery success.
6. For new Create delivery, save and check the review bound to the selected current exports using [First reviewed delivery](references/first-draft.md); pending or stale records do not establish readiness. Deliver individual panels, separate `caption.md`, runnable code/settings, traceable data or input references, computed statistics when used, and actual review findings. Report unresolved limitations without claiming an unreviewed output is finished.
7. Deliver the reviewed result and support ordinary chat refinements from the accepted code/settings. Start the [local workbench](references/figure-workbench.md#optional-activation) only when the user requests it or accepts an offer for visual annotations. Generate `.ev` only for a requested workbench/editable-project workflow. Browser, element-map, project-packaging or MCP failures do not invalidate otherwise reviewed graphic exports; report the affected optional capability separately. They never waive scientific, size, font or export checks.

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
| Editable project | Only for a requested workbench/editable-project workflow, package the current SVG, genuine nonempty element map, code/settings, source provenance and declared plotting inputs in `.ev`. Ordinary delivery needs no `.ev`. Renaming a PDF, PNG or SVG does not create an editable project. Include requested additional exports when present; bundle only declared inputs. |
| Evidence | Distinguish image observations, caption or method evidence, author-code evidence, and design decisions. Report checks actually performed and their input scope; a successful example does not establish untested generalization. Disclose an unavailable visual review. |

## Optional local editing and MCP

For installation or host-specific setup in DeepSeek Harness, read
[DeepSeek Harness](references/deepseek-harness.md). Host setup does not change
these two tracks or their first-delivery review.

Apply ordinary chat changes directly to the accepted script/specification and
inspect the fresh output. Do not start a browser, require an element map or
connect MCP for a color, line, legend or layout correction in chat.

When visual selection is requested, read [Figure workbench](references/figure-workbench.md).
It provides numbered annotations, attempt comparison and validated `.ev`
transport. Keep edits in the original authoring conversation. On “apply the
saved workbench comments,” follow [Edit application](references/apply-figure-requests.md#iterate-from-the-original-chat):
**Save drafts** is sufficient, and existing matching jobs must be checked to
avoid applying a batch twice. Preserve the user's workbench name; it does not
authorize an in-image title.

Read [MCP](references/mcp.md#original-session-editing) only when connecting the
optional editing queue. It can deliver submissions to an actively waiting
original Agent; it does not by itself wake an idle conversation. Preserve saved
comments for the next message in that same conversation when no live connection
is available. Never substitute a fresh dedicated worker for the original
session without the user's explicit request.

For independent image reading and comparison, pass accessible file paths to
[EasyViz Reference Reader](../easyviz-reference-reader/SKILL.md) or
[EasyViz Figure Reviewer](../easyviz-figure-reviewer/SKILL.md), with their permitted
context. These narrow helpers do not require a workbench. If independent
collaboration is unavailable, follow their references directly and label the
review as self-review.
