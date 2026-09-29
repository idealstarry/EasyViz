# Independent review of the final legend revision

**Status: ready with bounded notes.** No actionable legend collision, clipping, missing decoding, or disproportionate padding remains in the reviewed feasible outputs. This conclusion includes visual balance and exported-symbol checks; it is not based only on a geometry pass.

The review covers the current cell-atlas panel, paired-effects main and evaluation panels, and all ten final synthetic benchmark PNGs. The immutable before figures are under `current-baseline/`. File hashes, exact observations, and measurement provenance are recorded in `after-review.json`. The reviewed shared helper is `24e85216725ee68d21def0206a3656ba0a87d7c1de7e4580432a0d39116f7a2a`.

| Panel | Observed change | Assessment |
| --- | --- | --- |
| Cell atlas | Allocated bottom band 25.7 → 19.5 mm; row pitch 4.4 → 4.8 mm. Colorbar body 71 × 3.1 → 32 × 1.4 mm. Category keys use two columns; count keys form a compact three-value group. | The 6.2 mm recovery gives the data rows more room. The three guide groups stay clear and subordinate to the table. |
| Paired effects, main | Guide approximately 64.05 × 3.16 → 53.20 × 3.05 mm. Marker-to-label whitespace is reduced. | The legend was already short in height; this improves grouping without pretending to reclaim a large plotting region. |
| Paired effects, evaluation | Three-cohort guide is 68.92 × 3.05 mm at the existing position. | All labels and symbols remain inside the canvas, with clear cohort associations and no data collision. |

Cell-atlas guide envelopes are approximately **45.41 × 6.30 mm** (categories), **32.82 × 6.84 mm** (count), and **34.29 × 8.20 mm** (color). Their non-overlapping rectangular envelopes total **791.80 mm²**, 5.75% of the helper-defined main field. The enclosing rectangle includes empty gaps; available regions are not reserved bands. These numbers describe geometry and do not create a universal pass threshold. Baseline PDF text bounds and final renderer bounds come from different measurement backends, so small differences should not be read as exact typography changes.

The current cell PDF remains **180 × 120 mm with all extracted text at 8 pt**. Independently matching its 48 exported main-dot paths to the baseline gives **zero diameter difference** and identical fills. Final PNG and PDF inspection finds correctly positioned count keys centered on their numeric labels. No overall title, subtitle, or narrative footnote was introduced. Necessary column headings, axis labels, and decoding labels remain.

## Transfer evidence

I opened all ten final benchmark PNGs in addition to the contact sheet. The benchmark meets **10 of 10 expectations: nine feasible panels pass and one deliberately impossible panel remains `needs_revision`**. The impossible 88 × 32 mm output visibly clips and must not be treated as an accepted panel.

Short categorical labels form compact side guides. Long labels use complete top rows with appropriate separation; their necessary text width is not an automatic failure. The two heatmap cases retain labeled thin colorbars. Small- and large-area size keys are aligned and distinguishable without changing their quantitative areas. Explicit manual placement remains honored. These are bounded layout cases with fixed source data and axes, not evidence of universal whole-panel optimization.

The benchmark owner records exact categorical order, coverage, and fills; required colorbar meaning and range; quantitative values and areas; and direct exported SVG/PNG size-key measurements. Those checks supplement this independent inspection. Actual exports matter: the earlier transform and size-key alignment defects are corrected in the reviewed candidates.

## Limits and reusable guidance

The smallest positive cell counts remain difficult to distinguish in a 96 dpi PDF screen rendering under the preserved area mapping. This is a pre-existing scale limitation; this review does not claim that every rare dot becomes individually readable. No physical print proof was performed.

Retain full guide-envelope and combined-footprint measurements, fixed text size, exact quantitative symbol scale, and visual inspection at intended panel dimensions. Compact categorical keys and whitespace independently; preserve the complete decoding content. Treat ratios as review prompts, honor manual placement, and report an impossible fit instead of silently shrinking fonts or changing quantitative areas.

The annotated-inhibition panel was audited in `current-audit.md` but is outside this final integration review. Palette documentation cards are documentation, not manuscript panels.
