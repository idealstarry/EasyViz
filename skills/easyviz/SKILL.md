---
name: easyviz
description: Create or reproduce scientific plots from bioinformatics source data, with supporting statistics, configurable palettes, and individual panels at final manuscript dimensions. Use for chart selection, reference-image reproduction, mark styling, typography, and scientific figure export.
---

# EasyViz

Turn a data directory or prepared tables, a scientific question or reference image, requested changes, and export preferences into individual panels ready for manuscript assembly. Preserve the final canvas dimensions and text sizes so the user can arrange panels at their recorded size.

## Inputs and scope

| Input | Establish |
| --- | --- |
| Data directory or source tables | Inventory relevant files and tables; establish field meanings, units, missing values, groups, and independent experimental units. |
| Chart type or reference | The intended visual message and the appropriate track. |
| Additions or changes | Layers, labels, statistics, palette, or styling to retain or modify. |
| Layout and export | Existing figure settings, physical panel dimensions, font, and requested formats. |

Accept data produced by upstream analysis. Data reshaping, descriptive statistics, statistical tests, correlation, fitting, and annotations are in scope. Bioinformatics software analysis belongs to the upstream Agent. Do not require author code to reproduce a reference.

Choose statistics from the study design: establish pairing, independent replicates, uncertainty definitions, and multiple comparisons when relevant. Cells and technical replicates are not automatically independent experimental units. Preserve supplied statistical results when appropriate; record any recalculation, method, sample size, effect size, and applicable correction. Missing scientific information may block a statistical layer without blocking the rest of the plot.

## Choose a track

| Track | Trigger | Read |
| --- | --- | --- |
| **reproduce** | A reference or “standard” defines the visual structure or style. Default input is a reference image plus user data, without author code. The reference paper need not publish Source Data. | [Reproduce](references/reproduce.md), then [Reference to code](references/reference-to-code.md) when staging inputs or implementing unfamiliar layers. |
| **create** | Build from data and a specified or yet-to-be-selected question/chart. A directory and no plot idea are valid inputs. | [Create](references/create.md), then [First reviewed delivery](references/first-draft.md) for a new panel; start with [Data exploration](references/data-exploration.md) when files or useful comparisons are unresolved. |

Honor an explicit track. Create can learn color and mark mechanisms from the
bundled literature guidance without a runtime reference image. Reproduce adopts
a supplied reference's structure/style. For additions to an existing plot,
retain its track, script, and accepted settings, then review the changed result.

Literature Source Data supplies auditable learning and validation cases for
reproduce; it is not required for runtime reproduction with the user's own data.
Directory inventory may help either track, but create recommendations must not
replace an adopted reference's structure. Keep only these two tracks.

## Shared resources

Read the resources needed for the current chart rather than loading the whole library.

| Resource | Use |
| --- | --- |
| [First reviewed delivery](references/first-draft.md) | New Create panels: scene-based actual candidates or justified custom code, image inspection, bounded correction and a review of current exports before delivery. |
| [Scenario design cards](references/design-cards.md) | Inspect visual mechanisms and failure examples eligible for the input features; transfer color roles and geometry without importing scientific assumptions. |
| [First panel](references/quick-start.md) | Generate a validated core-chart spec from explicit column roles; measure text and guide space. Use within the reviewed-delivery workflow for new Create panels. |
| [Statistical analysis](references/statistical-analysis.md) | Execute an explicit design and comparison plan separately from drawing; retain effects, supported intervals, exclusions and multiplicity. |
| [Actual preview choices](references/preview-choices.md) | In create, render comparable box/points and ECDF candidates from the same observations; optional KDE is explicit. Choose after inspecting reading tasks at final size. |
| [Annotated matrices](references/annotated-matrix.md) | Keyed metadata strips, observed/unmeasured/unsupplied states, declared mean/sum marginals and supplied trees; compose custom aligned tracks without inferring clustering. |
| [Point placement](references/collision-placement.md) | Resolve overlapping distribution points in physical units, preserving values and mark sizes; report unresolved packing. |
| [Figure workbench](references/figure-workbench.md) | Select SVG layers or canvas regions, save version-bound change requests, then edit source/spec and redraw all formats in either track. |
| [Edit application and history](references/apply-figure-requests.md) | Prepare verified cosmetic spec edits, record actual Agent rerenders, compare attempts and restore accepted source/export snapshots. |
| [Panel layout](references/panel-layout.md) | Final dimensions, font roles, export behavior, and assembly constraints. |
| [Legend layout](references/legend-layout.md) | Proportionate legend keys, measured placement, and data-to-legend hierarchy while preserving typography. |
| [Palettes](references/palettes.md) | Palette selection and consistent category-to-color mappings. |
| [Create colors and strokes](references/create-style.md) | Apply task-specific color and stroke roles; [design paths](references/design-space.md) describe multiple conditional organizations within a basic family. |
| [Literature design mechanisms](references/literature-style.md) | Transfer specific color, boundary and packing decisions from PROGENy, scWAT and Vanneste figures, with source anchors and applicability limits. |
| [Figure profile](references/figure-profile.md) | Share typography, category colors, continuous scales and named panel sizes across a manuscript figure. |
| [Dot data states](references/dot-states.md) | Distinguish measured zero, unmeasured and unsupplied cells while preserving exact dot area. |
| [Design decisions](references/design-decisions.md) | Reference-informed choices about grouping, alignment, visual priority, and competing layouts. |
| [Chart library](references/chart-library.md) | Supported chart recipes, input contracts, reusable scripts, and examples. |
| [Worked cases](references/examples.md) | Runnable panels and reviewed image-data reconstructions with explicit input contracts, scripts and provenance. |
| [Literature Source Data](references/literature-source-data.md) | Select auditable paper panels, retain source semantics, and extract reusable implementations with bounded transfer checks. |
| [Time courses](references/timecourse-plot.md) | Supplied estimates with SD or explicit interval bands, irregular x grids and explicitly labelled single/dual axes. |
| [Supplied intervals](references/interval-plot.md) | Plot estimates and asymmetric intervals with explicit log/reference/fill semantics; no sample-size requirement or model fitting. |
| [Paired observations](references/paired-plot.md) | Keep explicit unit correspondence across conditions; display raw values with median/IQR and optionally adopted connectors. |
| [Replicate bars](references/replicate-plot.md) | Stacked or grouped component summaries with raw replicate layers, or supplied ratio observations; distinguish component SD from total SD. |
| [Empirical cumulative distributions](references/ecdf-plot.md) | Compare complete raw distributions as unsmoothed cumulative steps, retaining tied values and explicit linear/log scales. |
| [Reference specification](references/reference-spec.md) | Separate image observations from decisions and record adopted requirements. |
| [Complex reproduction](references/complex-reproduction.md) | Implement aligned layers with explicit source keys and separate guides; optionally audit saved layer coverage, SVG alignment and numeric evidence. |
| [Visual review](references/visual-review.md) | Inspect rendered images, prioritize corrections, and record unresolved differences. |

## Execute

1. Inspect the data and user requirements. Fill missing cosmetic preferences from recorded project settings or the shared defaults; clarify only consequential ambiguity.
2. Follow the chosen track to produce an adopted plotting specification. In Create, decide the reading task, graphical organization and visual roles separately using [Design paths](references/design-space.md); a basic family has several valid solutions. Additional layers need a purpose. In Reproduce, obtain an independent image reading before selecting implementation templates.
3. Establish physical width and height, fonts, formats and project settings. Choose the leading layer and where category identity is decoded before choosing hues or outlines. Preserve shared profiles and category assignments, and resolve conflicts before rendering. A gallery palette or sample's complete layout is not the default for every task.
4. Check implementation contracts. For new Create panels, inspect relevant [card mechanisms](references/design-cards.md) and follow [First reviewed delivery](references/first-draft.md). Candidate helpers cover a limited design set; adapt a spec or write focused/custom code when proposals miss the chosen route, including within a supported chart family. Examples have bounded contracts; copy them into the writable project before adapting. Preserve scientific and explicit user constraints; never guess that an existing key was a default and remove it. Reproduce retains its adopted reference and settings.
5. Actually open the rendered images before presenting a finished result. Compare meaningful alternatives when design or reading-task choices are unresolved; routine corrections need no compulsory candidate set. Inspect palette decoding, point/summary crossings, contour hierarchy, category gaps, cell proportions, guide footprint, clipping and glyphs at final proportions. Use [Create design decisions](references/create-style.md), [physical point placement](references/collision-placement.md) and [Legend layout](references/legend-layout.md) where applicable. Obtain independent review when available; otherwise label self-review. Follow [Visual review](references/visual-review.md), correcting internally within three total visual passes while preserving science, agreed fonts and dimensions.
6. For new Create delivery, save and check the review bound to the selected current exports using [First reviewed delivery](references/first-draft.md); pending or stale records do not establish readiness. Deliver individual panels, separate `caption.md`, runnable code/settings, traceable data or input references, computed statistics when used, and actual review findings. Report unresolved limitations without claiming an unreviewed output is finished.

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
| Evidence | Distinguish image observations, caption or method evidence, author-code evidence, and design decisions. Report checks actually performed and their input scope; a successful example does not establish untested generalization. Disclose an unavailable visual review. |

For independent image reading and comparison, pass an explicit file path to [EasyViz Reference Reader](../easyviz-reference-reader/SKILL.md) or [EasyViz Figure Reviewer](../easyviz-figure-reviewer/SKILL.md). These are narrow helper skills, not automatic proof that a subagent used them. Supply accessible images and the permitted context. If a helper or collaboration tools are unavailable, follow the corresponding reference directly and record that the review was not independent.
