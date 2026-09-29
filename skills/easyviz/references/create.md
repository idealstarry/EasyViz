# Create track

Create an individual scientific panel from source data, a communication goal or chart type, optional additions, and export preferences. Reuse the same data, typography, palette, and physical-size rules as reproduce.

## 1. Choose the visual mapping

Honor the user's requested chart when the data supports it. Otherwise use the [Chart library](chart-library.md) to choose a visual encoding for the question. Explain consequential changes such as switching from cell-level observations to sample-level summaries before using them.

| Question | Establish before drawing |
| --- | --- |
| Compare groups or distributions | Measurement unit, independent samples, pairing, category order, summary and raw-observation layers. |
| Compare composition | Numerator, denominator, sample or group aggregation, included categories, and whether fractions sum to one. |
| Show association | Variables, units, transformation, independent observations, fit family, and uncertainty definition if shown. |
| Show a matrix | Row and column meaning, value scale, missing-value encoding, explicit order, and any provided annotations. |
| Show an existing embedding or analysis result | Supplied coordinates or results and their interpretation; upstream computation remains outside this skill. |

Record the adopted chart type, field mappings, transformations, order, and requested layers. The compact specification in [Reference specification](reference-spec.md) can be used without a reference-observation section.

### Design the comparison

Identify what the reader should compare first and which context makes that comparison valid. Use the relevant [Design decisions](design-decisions.md) pattern for its transferable relationships, without inheriting sample-specific filtering, colors, or coordinates. A single panel can contain aligned annotations or summaries; each layer should contribute to the scientific reading task.

| Decision | Compare |
| --- | --- |
| Ordering and grouping | Scientific or experimental order versus ordering by a declared data summary. Keep related rows together when within-group comparison matters; do not imply a new upstream clustering analysis. |
| Visual priority | Distinguish primary evidence, supporting context, and decoding aids. Allocate contrast and space accordingly; additional layers and saturated colors do not automatically add information. |
| Alignment and encoding | Align layers that readers must compare by shared identifiers and coordinates. A second encoding needs a distinct purpose; define its quantity, denominator, summary population, and uncertainty when applicable. |
| Decoding | Compare local labels and legends by lookup effort, label length, and mark density. The smallest guide is not automatically the clearest. |
| Density and space | Fit data-field proportions, group gaps, ticks, and selective labels to the actual data. A smaller guide should improve balance or release useful plotting space, rather than leave the same oversized reserved band. |

For a refinement request or a consequential design choice, compare the accepted baseline and a materially different candidate at the same final size. State the intended gain, inspect both actual exports, and retain the baseline when that gain is not visible or introduces a worse tradeoff. Routine cosmetic edits do not require multiple alternatives. Do not add layers merely to make a demonstration look complex.

For a selected matrix view, preserve the complete input and record the selection rule and displayed IDs. Align metadata and marginal summaries by identifiers rather than row position. Distinguish summaries of the displayed subset from summaries of the full source data. Select feature labels by a scientific or user-specified criterion. Counts of cells or taxa are descriptive observations; they do not by themselves provide independent biological replicates for inference.

## 2. Resolve statistics and visual settings

Add descriptive statistics, tests, fitted models, uncertainty intervals, or significance annotations only when supported by the user's data and study design. Record calculation details and exact sample sizes. A missing replicate identifier cannot be replaced by treating every row as an independent biological sample.

Use [Panel layout](panel-layout.md) for physical dimensions and typography, and [Palettes](palettes.md) for colors. Reuse existing category-color assignments. Determine canvas proportions from chart shape, label length, category count, and expected density before the first render. Include space for adopted annotation tracks, marginal axes, and legends inside the same fixed canvas; their text uses the shared typography roles.

Default comparable filled dots, bars, and matching legend swatches to one borderless policy. Set edge styling explicitly, and record any scientific or readability exception by mark role. Inspect palette combinations together on the actual panel, including small marks and adjacent annotation tracks; a palette's appearance in a paper is not evidence that it suits this data or works with the other colors.

Use [Legend layout](legend-layout.md) to distinguish categorical keys, quantitative size keys, and continuous scales. Choose placement from measured key/text bounds and chart geometry; protect agreed fonts and quantitative area mappings. Inspect the legend's footprint and reserved space relative to the main plot, rather than accepting a large legend because it fits without overlap.

Keep axis names and units, ticks, legends, colorbars, and essential data annotations in the panel. Place explanatory prose, abbreviation definitions, methods, source notes, caveats, and standalone dataset overview counts in `caption.md`. Extra titles, subtitles, and explanatory footnotes are omitted by default; add an in-image title only on explicit user request. Do not apply a fixed top-left header layout. Metadata strips, marginal-axis labels, and plotted count values remain valid scientific layers.

## 3. Select an implementation

Inspect the recipe's input contract and supported options in the chart library. Reuse the relevant script or write an implementation that preserves the adopted mappings and export settings. The core renderer supplies basic chart families; linked metadata tracks, aligned marginal plots, and specialized annotations can require a custom script. Use [Worked cases](examples.md) for implementation patterns and provenance, and synthetic fixtures only for small runnable API examples. Keep transformation and statistics steps inspectable rather than burying them in styling code.

Treat each case's schema, selection, denominators, annotation joins, and layout capacity as an explicit applicability boundary. Reuse directly only when they fit; otherwise adapt and verify them, or write a new implementation. If a requested feature remains unsupported, state that boundary without silently replacing the chart, deleting observations, or claiming the existing example validated the new use.

For edits to an existing panel, reuse its data, script, and accepted settings. Record the requested addition and any consequent layout change. Do not silently change denominators, tests, category colors, axis limits, or experimental units while adding a layer.

## 4. Render and refine

Inspect an actual rendering at final-size proportions. Adjust label wrapping, tick density, legend placement, and margins to suit the data without automatically shrinking text. If the canvas cannot fit the content, use the shared procedure for selecting a larger panel or splitting the content.

Follow [Visual review](visual-review.md) with the same typography, readability, and correction standard used in reproduce. A reviewer assesses create outputs against the adopted specification without needing a reference image. For integrated panels, also verify that tracks and marginals align with the correct rows or columns, size and color legends explain their distinct quantities, and annotations remain readable without obscuring data. Check that narrative material is in the separate caption and no unrequested title/header has been added. Independently recompute displayed summaries and denominators from the recorded input scope. Numerical checks and visual review are separate evidence: a clean image does not prove calculations correct, and a successful export does not prove labels readable.

## 5. Deliver

Provide the individual panel in the requested formats, a PNG preview when useful, separate `caption.md`, runnable script, actual settings, traceable plotting data, and calculated statistical results if applicable. Follow the journal-style caption guidance in [Panel layout](panel-layout.md); use figure/panel identifiers only when known. State meaningful unresolved limitations and the recorded placement dimensions. The user assembles panels at those dimensions.
