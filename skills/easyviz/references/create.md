# Create track

Create an individual scientific panel from source data, a communication goal or chart type, optional additions, and export preferences. Reuse the same data, typography, palette, and physical-size rules as reproduce.

Start with the scientific comparison and a basic chart family. A scatter, bar,
box, violin or heatmap can form a complete manuscript panel when it presents
the relevant groups, quantities and supported summaries clearly. A basic
family can include real grouped comparisons; it does not require restricting
the data to a single outcome. Make colors, strokes and proportions work at the
adopted size. Add another track or encoding when that reading task needs it.

If the user supplies a directory without a clear question or chart, start with
[Data exploration](data-exploration.md). Inventory the tables, inspect actual
values, and propose a few concrete reading tasks with field mappings and small
descriptive previews. Candidate fields are hints, not established units or study
design. Ask only for scientific facts that change a proposed analysis; keep
descriptive exploration moving while those facts remain unknown. The user need
not choose a renderer or write a specification.

For an eligible observation table with an unresolved reading task, use [Actual preview choices](preview-choices.md)
to show box + all points and an unsmoothed ECDF at the same final dimensions,
fonts, colors and numeric scale. State which helps the proposed reading task,
inspect the actual exports, and retain the user's choice. The manifest contains
no automatic winner. Unknown units/design remain explicit and descriptive;
pairing, technical repeats and summary tables require a different prepared
contract. A directory recommendation without a rendered image is only a proposal.

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

### Basic chart choices

| Starting chart | Use when | Resolve before styling |
| --- | --- | --- |
| Scatter | The relationship between two supplied variables is the task. | Point identity, units, scale and overlap; add a fitted curve only with an adopted model. A line joining unordered observations invents a relationship. |
| Bar | An adopted estimate, count, total or composition is the quantity to compare. | What height summarizes, the zero baseline, denominator and uncertainty meaning. Do not turn raw measurements into means merely because bars look compact. |
| Box with raw points | Median, spread and individual measurements matter. | Quartiles and whisker convention, independent unit or pairing, point capacity and summary crossings. Separate lanes or small facets can help without adding statistics. |
| Violin | Density shape adds a useful question beyond median, spread and raw observations. | KDE method/bandwidth and width normalization. Choose contour, inner summary and raw-layer emphasis deliberately; small or repeated-value groups may be clearer as box/points. A wide violin is not automatically a larger sample. |
| Simple heatmap | Readers compare values across a row/column matrix. | Identifier order, observed/missing states, shared numeric normalization and cell proportions. Metadata strips, marginals and trees are optional, separately justified layers. |

These starting choices preserve the user’s chart preference when its meaning
fits the data. ECDF, intervals, paired trajectories and other supported families
remain available when they answer the reading task more directly.

### Complete the scientific comparison

Establish what changes, relative to which groups or control, and which supplied
outcomes answer that question. A minimal API demonstration can omit this
context; a manuscript panel should retain the adopted comparison scope.

- For grouped bars, use actual supplied grouping variables and repeat the same
  series order within each category. Comparable outcomes may share an axis
  when their units and reading task justify it; unrelated scales need separate
  axes or panels, not an invented normalization. Shared percentage units alone
  do not authorize stacking outcomes as a composition.
- Consider narrow individual manuscript panels when several outcomes have
  very different ranges and readers compare treatments within each outcome.
  Repeat treatment order, inner-axis geometry and stroke/type settings; an
  adjacent preview must preserve the individual panel sizes and fonts. State
  different ranges clearly, retain the original units, and do not imply equal
  absolute amounts from equal heights on different axes. A global-scale
  grouped alternative serves a different comparison and may be retained.
- Show the independent observations and an adopted summary/uncertainty when
  available and useful. Define SD, SEM or confidence intervals honestly in the
  caption; never substitute one for another, invent error bars from a mean,
  or add significance marks to make the panel look finished.
- Keep relevant controls, contrasts and required layers. If the available
  data are sparse, make that small comparison crisp and compact. Add real
  supported outcomes when they serve the question; do not add decorative
  tracks, unrelated columns or larger marks to fill space.

### Design the comparison

Identify what the reader should compare first and which context makes that comparison valid. Use the relevant [Design decisions](design-decisions.md) pattern for its transferable relationships, without inheriting sample-specific filtering, colors, or coordinates. A single panel can contain aligned annotations or summaries; each layer should contribute to the scientific reading task.

| Decision | Compare |
| --- | --- |
| Ordering and grouping | Scientific or experimental order versus ordering by a declared data summary. Keep related rows together when within-group comparison matters; do not imply a new upstream clustering analysis. |
| Visual priority | Distinguish primary evidence, supporting context, and decoding aids. Allocate contrast and space accordingly; additional layers and saturated colors do not automatically add information. |
| Alignment and encoding | Align layers that readers must compare by shared identifiers and coordinates. A second encoding needs a distinct purpose; define its quantity, denominator, summary population, and uncertainty when applicable. |
| Decoding | Compare local labels and legends by lookup effort, label length, and mark density. The smallest guide is not automatically the clearest. |
| Density and space | Set the data rectangle from category/matrix shape and mark capacity. Inspect within-category, between-category and outer gaps separately; spare canvas width need not become stretched cells or blank group bands. |

For a refinement request or a consequential design choice, compare the accepted baseline and a materially different candidate at the same final size. State the intended gain, inspect both actual exports, and retain the baseline when that gain is not visible or introduces a worse tradeoff. Routine cosmetic edits do not require multiple alternatives. Do not add layers merely to make a demonstration look complex.

For a selected matrix view, preserve the complete input and record the selection rule and displayed IDs. Align metadata and marginal summaries by identifiers rather than row position. Distinguish summaries of the displayed subset from summaries of the full source data. Select feature labels by a scientific or user-specified criterion. Counts of cells or taxa are descriptive observations; they do not by themselves provide independent biological replicates for inference.

## 2. Resolve statistics and visual settings

For a related panel set, save and reuse a [figure profile](figure-profile.md) so category subsets cannot change colors and each panel retains its agreed dimensions. Inspect or reject conflicting and unknown settings before producing files. For sparse dot matrices, use the [data-state contract](dot-states.md) instead of treating all blank-looking cells as equivalent.

Add descriptive statistics, tests, fitted models, uncertainty intervals, or significance annotations only when supported by the user's data and study design. Record calculation details and exact sample sizes. A missing replicate identifier cannot be replaced by treating every row as an independent biological sample.

Use [Statistical analysis](statistical-analysis.md) for an explicit executable
analysis plan, supported effect intervals and declared comparison families.
Keep its saved results separate from styling. A different view of the same
analysis must retain its units, comparisons, exclusions and calculated results.
Multiple groups do not authorize trying all tests until one is significant.

For three or more complete repeated conditions, the analysis helper supports
an explicitly planned Friedman omnibus test with Kendall's W and either a
declared chi-square approximation or bounded within-subject permutation. It
retains literal subject joins and whole-subject exclusions. W is nondirectional
concordance; no pairwise conclusions or confidence intervals are invented.
Covariates, unbalanced longitudinal sampling and requested model-specific
effects require an adopted model and a custom analysis script.

Use [Panel layout](panel-layout.md) for physical dimensions and typography, and [Palettes](palettes.md) for colors. Reuse existing category-color assignments. Determine canvas proportions from chart shape, label length, category count, and expected density before the first render. Include space for adopted annotation tracks, marginal axes, and legends inside the same fixed canvas; their text uses the shared typography roles.

Declare styling by mark role: fixed-size sample points may be opaque filled or hollow; bars or distribution summaries may use clear outlines; quantitative filled-area dots retain their exact fill-area contract. Match legend symbols to the chosen treatment. Avoid assuming that borderless, thinner or lower-alpha marks are always more refined. Inspect palette combinations together on the actual panel, including small marks and adjacent annotation tracks; a palette's appearance in a paper is not evidence that it suits this data or works with the other colors. Read [Literature design mechanisms](literature-style.md) when the user asks for crisp, compact paper-like figures.

Before the first render, assign color and stroke roles to observations,
adopted summaries and guides. Use [Create colors and strokes](create-style.md)
for the shared new-task treatment and `line_roles`, or equivalent settings in a
custom script. Compare all colors together, including legend keys and any
continuous scale. Choose a coordinated pair for two groups when useful;
additional categories need distinct colors that still form a coherent panel.
The main evidence needs useful contrast. An auxiliary track should not become
the visual focus merely because it is saturated or large.

When cohorts overlap into an indistinct cloud, compare neighboring group lanes
or aligned facets with the same numeric scale before fading every point. For
box/points, separate the raw-point lane from the summary when medians or
whiskers are hidden. For violin, establish a reason to show density and choose
which of contour, summary and points leads; avoid three equally strong layers.
These choices change categorical geometry, not numeric observations or KDE.
Use a sequential heatmap scale when the task is magnitude reading; values of both
signs alone do not require a diverging palette. A scientifically meaningful
center can justify a diverging alternative, with its center, endpoints and
normalization recorded. Review a single-hue starting scale before adding more
hues. Keep every observation and the original numeric axis; useful density
comes from readable geometry, spacing and decoding.

Use [Legend layout](legend-layout.md) to distinguish categorical keys, quantitative size keys, and continuous scales. Choose placement from measured key/text bounds and chart geometry; protect agreed fonts and quantitative area mappings. Inspect the legend's footprint and reserved space relative to the main plot, rather than accepting a large legend because it fits without overlap.

Keep axis names and units, ticks, legends, colorbars, and essential data annotations in the panel. Place explanatory prose, abbreviation definitions, methods, source notes, caveats, and standalone dataset overview counts in `caption.md`. Extra titles, subtitles, and explanatory footnotes are omitted by default; add an in-image title only on explicit user request. Do not apply a fixed top-left header layout. Metadata strips, marginal-axis labels, and plotted count values remain valid scientific layers.

## 3. Select an implementation

For a supported core chart, [First panel](quick-start.md) provides a short
draft-to-render path using explicit column roles. New drafts measure text and
guide space rather than requiring the Agent to guess margins. Keep scientific
choices explicit and review the exported image; use the full specification for
additional supported options.

Inspect the recipe's input contract and supported options in the chart library. Reuse the relevant script or write an implementation that preserves the adopted mappings and export settings. The core renderer supplies basic chart families; linked metadata tracks, aligned marginal plots, and specialized annotations can require a custom script. Use [Worked cases](examples.md) for implementation patterns and provenance, and synthetic fixtures only for small runnable API examples. Keep transformation and statistics steps inspectable rather than burying them in styling code.

Treat each case's schema, selection, denominators, annotation joins, and layout capacity as an explicit applicability boundary. Reuse directly only when they fit; otherwise adapt and verify them, or write a new implementation. If a requested feature remains unsupported, state that boundary without silently replacing the chart, deleting observations, or claiming the existing example validated the new use.

For edits to an existing panel, reuse its data, script, and accepted settings. Record the requested addition and any consequent layout change. Do not silently change denominators, tests, category colors, axis limits, or experimental units while adding a layer.

For detailed changes, the [Figure workbench](figure-workbench.md) records selected
layers or canvas regions and the version the user inspected. Apply requests to
the original spec/profile or script, preserve the accepted attempt, and redraw
the affected formats. It is a shared editing tool, not another plotting track.

## 4. Render and refine

Inspect an actual rendering at final-size proportions. First check the whole
palette, visible axes and mark edges, point/summary overlap, category spacing,
and the plot-to-guide proportions. Use the family-specific checks in
[Create colors and strokes](create-style.md): thin boxes cannot compensate for
excessive category spacing, and a three-column matrix need not fill a wide
axis. Adjust wrapping, ticks, guides and inner-axis bounds at the agreed canvas
and font size. If the canvas cannot fit the content,
use the shared procedure for choosing a larger panel or splitting the content.

For a styling refinement, compare the accepted and candidate exports at the
same dimensions. Check the main data, palest positive marks, interval endpoints,
reference lines and guide keys before calling the result an improvement. Also
inspect the actual delivery thumbnail: a three-panel comparison compressed
into one README row may hide good individual figures. Present a complete
representative panel with readable labels, and keep alternatives accessible on
the case page; do not alter manuscript font sizes to compensate for a small
web preview.

Follow [Visual review](visual-review.md) with the same typography, readability, and correction standard used in reproduce. A reviewer assesses create outputs against the adopted specification without needing a reference image. For integrated panels, also verify that tracks and marginals align with the correct rows or columns, size and color legends explain their distinct quantities, and annotations remain readable without obscuring data. Check that narrative material is in the separate caption and no unrequested title/header has been added. Independently recompute displayed summaries and denominators from the recorded input scope. Numerical checks and visual review are separate evidence: a clean image does not prove calculations correct, and a successful export does not prove labels readable.

## 5. Deliver

Provide the individual panel in the requested formats, a PNG preview when useful, separate `caption.md`, runnable script, actual settings, traceable plotting data, and calculated statistical results if applicable. Follow the journal-style caption guidance in [Panel layout](panel-layout.md); use figure/panel identifiers only when known. State meaningful unresolved limitations and the recorded placement dimensions. The user assembles panels at those dimensions.
