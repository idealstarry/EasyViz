---
name: easyviz
description: Create or reproduce scientific plots from bioinformatics source data, with supporting statistics, configurable palettes, and individual panels at final manuscript dimensions. Use for reference-image reproduction, chart selection, additional layers, typography, and scientific figure export.
---

# EasyViz

Turn source data, a chart type or reference image, requested changes, and export preferences into individual panels ready for manuscript assembly. Preserve the final canvas dimensions and text sizes so the user can arrange panels at their recorded size.

## Inputs and scope

| Input | Establish |
| --- | --- |
| Source data | Field meanings, units, missing values, groups, and independent experimental units. |
| Chart type or reference | The intended visual message and the appropriate track. |
| Additions or changes | Layers, labels, statistics, palette, or styling to retain or modify. |
| Layout and export | Existing figure settings, physical panel dimensions, font, and requested formats. |

Accept data produced by upstream analysis. Data reshaping, descriptive statistics, statistical tests, correlation, fitting, and annotations are in scope. Bioinformatics software analysis belongs to the upstream Agent. Do not require author code to reproduce a reference.

Choose statistics from the study design: establish pairing, independent replicates, uncertainty definitions, and multiple comparisons when relevant. Cells and technical replicates are not automatically independent experimental units. Preserve supplied statistical results when appropriate; record any recalculation, method, sample size, effect size, and applicable correction. Missing scientific information may block a statistical layer without blocking the rest of the plot.

## Choose a track

| Track | Trigger | Read |
| --- | --- | --- |
| **reproduce** | A reference or “standard” defines the visual structure or style. Default input is a reference image plus user data, without author code. | [Reproduce](references/reproduce.md) |
| **create** | Build from data and a specified or yet-to-be-selected chart type. | [Create](references/create.md) |

Honor an explicit track. Color-only inspiration can remain in create. For additions to an existing plot, retain its track, script, and accepted settings, then review the changed result.

## Shared resources

Read the resources needed for the current chart rather than loading the whole library.

| Resource | Use |
| --- | --- |
| [First panel](references/quick-start.md) | Generate a validated core-chart spec from explicit column roles; measure text and guide space within the fixed canvas. |
| [Panel layout](references/panel-layout.md) | Final dimensions, font roles, export behavior, and assembly constraints. |
| [Legend layout](references/legend-layout.md) | Proportionate legend keys, measured placement, and data-to-legend hierarchy while preserving typography. |
| [Palettes](references/palettes.md) | Palette selection and consistent category-to-color mappings. |
| [Figure profile](references/figure-profile.md) | Share typography, category colors, continuous scales and named panel sizes across a manuscript figure. |
| [Dot data states](references/dot-states.md) | Distinguish measured zero, unmeasured and unsupplied cells while preserving exact dot area. |
| [Design decisions](references/design-decisions.md) | Reference-informed choices about grouping, alignment, visual priority, and competing layouts. |
| [Chart library](references/chart-library.md) | Supported chart recipes, input contracts, reusable scripts, and examples. |
| [Worked cases](references/examples.md) | Rich create panels and reviewed image-data reconstructions with scripts and provenance. |
| [Reference specification](references/reference-spec.md) | Separate image observations from decisions and record adopted requirements. |
| [Visual review](references/visual-review.md) | Inspect rendered images, prioritize corrections, and record unresolved differences. |

## Execute

1. Inspect the data and user requirements. Fill missing cosmetic preferences from recorded project settings or the shared defaults; clarify only consequential ambiguity.
2. Follow the chosen track to produce an adopted plotting specification. In reproduce, obtain an independent image reading before selecting implementation templates.
3. Establish physical width and height, text sizes, font availability, palette, mark-outline policy, and formats. Reuse the figure's shared profile when one exists; save stable category-color assignments and named panel sizes when starting a related panel set. A category disappearing or changing order must not change its color. Resolve configuration conflicts and unknown fields before rendering. Evaluate all palettes together on the actual panel. Defaults are adjustable EasyViz starting values, not journal standards.
4. Select an implementation after checking its input contract and supported layers. For a basic create panel, use [First panel](references/quick-start.md) to generate a validated spec from explicit fields and render it with measured layout. Examples demonstrate specific reusable contracts, not arbitrary-data support. Copy bundled cases into the user's writable project before running or adapting them. Reuse, adapt, or write a script according to the real data; report unsupported requirements explicitly without silently substituting a chart or dropping data.
5. Render the full canvas. Check exported dimensions and inspect crowding, clipping, missing glyphs, labels, and visual hierarchy. Assess the complete legend footprint and reserved space relative to the data region; no overlap alone is insufficient. Follow [Legend layout](references/legend-layout.md) and the bounded correction process in [Visual review](references/visual-review.md).
6. Deliver the individual panels, a separate `caption.md`, runnable plotting script, actual settings, traceable plotting data or input references, and review findings. Include computed statistics when used.

## Output rules

| Area | Requirement |
| --- | --- |
| Assembly | Export one panel per file. Leave assembly and panel lettering to the user unless lettering is requested; reserve any requested letter inside the fixed canvas. |
| Panel text | Keep axis names and units, ticks, legends, colorbars, and essential data annotations. By default, omit extra titles, subtitles, standalone overview counts, and explanatory footnotes inside the image. Add an in-image title only when the user explicitly requests it, including in reproduce; a title present in the reference does not authorize copying it. |
| Caption | Put explanatory prose, abbreviation definitions, methods, source attribution, and caveats in a separate `caption.md`. Use journal-style figure/panel prose with identifiers only when known; do not invent a figure number or panel letter. The caption is a separate deliverable, not text to place on the canvas. |
| Fixed size | Keep the entire canvas, including legends and margins. Avoid export cropping that changes physical dimensions. Use the same physical size across formats. |
| Typography | Keep agreed font sizes while adjusting wrapping, margins, ticks, and legend position. If content needs a different canvas, resolve that change before replacing an agreed assembly size. |
| Mark styling | Declare one outline policy for comparable filled dots, bars, and their legend swatches. Create defaults to borderless marks; reproduce follows the adopted specification and user requirements. Record purposeful scientific/readability exceptions and set styles explicitly instead of mixing library defaults. |
| Data integrity | Do not silently omit observations, reinterpret uncertainty, recompute upstream bioinformatics analysis, or invent values from reference pixels. |
| Availability | In sparse dot matrices, distinguish observed zero, explicitly unmeasured and coordinates absent from the supplied table. A missing row does not establish that measurement was attempted. Retain quantitative areas; use a separate decoded presence flag if tiny positive marks need help at the final size. |
| Traceability | Save the track, reference input mode, source paths, transformations, mappings, statistics, actual font and palette, dimensions, formats, and dpi. |
| Evidence | Distinguish image observations, caption or method evidence, author-code evidence, and design decisions. Report checks actually performed and their input scope; a successful example does not establish untested generalization. Disclose an unavailable visual review. |

For independent image reading and comparison, pass an explicit file path to [EasyViz Reference Reader](../easyviz-reference-reader/SKILL.md) or [EasyViz Figure Reviewer](../easyviz-figure-reviewer/SKILL.md). These are narrow helper skills, not automatic proof that a subagent used them. Supply accessible images and the permitted context. If a helper or collaboration tools are unavailable, follow the corresponding reference directly and record that the review was not independent.
