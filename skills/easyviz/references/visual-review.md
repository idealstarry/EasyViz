# Visual review and bounded correction

Review actual output images against the adopted specification. For reproduce, also inspect the reference. Keep visual findings separate from numerical checks and export measurements.

## Review packet

Provide accessible reference and candidate images, the adopted specification, separate `caption.md`, intentional differences, and measured export dimensions and font information if available. For a claimed refinement, also supply the accepted baseline and the intended reading task. A create review does not need a reference image. Use the [Figure Reviewer](../../easyviz-figure-reviewer/SKILL.md) with an explicit skill path when delegating.

Ask the reviewer to open the images before making findings. Do not prime it with a desired pass result or the implementer's self-assessment. The review can inspect an enlarged image for clipping and mark detail, but should also consider the intended physical size and avoid confusing screen zoom with print-size legibility.

## What to inspect

| Area | Evidence to compare |
| --- | --- |
| Meaning | Variables, axis labels, units, scales, category order, legend mapping, and whether the plotted layers agree with the specification. |
| Structure | Mark types, grouping, overlays, relative placement, aspect constraints, and adopted reference features. |
| Readability | Label collisions, truncation, missing glyphs, crowded marks, legend spacing, and annotation legibility. |
| Legend proportions | Assess complete key/text bounds and reserved legend space against the primary data region using [Legend layout](legend-layout.md). Judge data prominence, not just lack of overlap. Preserve agreed fonts and exact quantitative-size mapping; treat proportional warnings as adjustable heuristics. |
| Panel text and caption | Preserve axes/units, ticks, legends, colorbars, and essential data annotations. By default, extra titles, subtitles, standalone overview counts, and explanatory footnotes belong outside the image. Check explanatory prose, definitions, methods, source attribution, and caveats in separate `caption.md`, with figure/panel identifiers only when known. |
| Palette | Inspect the complete combination of category colors, continuous scales, backgrounds and guide keys. Check identity in small marks and adjacent fills; literature provenance alone does not establish a coherent or distinguishable palette. |
| Strokes and boundaries | Inspect visible data, summary, reference, axis and grid roles at final size; check adopted fills/outlines and matching legend symbols. Purposeful exceptions can differ by mark role. Check thin interval endpoints, box medians and heatmap seams rather than approving enlarged appearance alone. |
| Geometry | Inspect point/summary crossings, physical bar/box/violin thickness, within- and between-category gaps, matrix cell aspect and plot-to-guide proportions. Ask whether spare width creates blank categorical bands or stretched cells. Keep aspect constraints and every source observation. |
| Final-size export | Independent page/pixel measurements, preserved canvas boundaries, actual font records, matching format dimensions. These require measurements, not a visual guess. |

Do not use pixel similarity as a pass condition when data, fonts, or final physical dimensions differ. Different data-driven shapes and documented adaptations are expected. Exact colors, statistical correctness, physical size, and font embedding cannot be certified from a screenshot alone.

Core exports record `qa.json` → `readability` advisory measurements from the
actual Matplotlib artists. Use point extents, small-mark/background contrast,
role-specific stroke widths and legend bounds to locate a possible problem,
then inspect the exported image. A `review_suggested` flag is a review cue;
`no_advisory_flags` does not establish a good palette or absence of overlap.
These adjustable thresholds are EasyViz heuristics. The check does not measure
color-vision accessibility, differences between category hues, point/summary
occlusion or missing layers. Real zero-area marks are retained, and intentional
white matrix seams are not treated as faint data strokes. Custom scripts can
use `panel_readability.measure(fig)` before export for the same limited evidence.

Review palette combinations together in the actual panel, including contrasts between continuous maps, category colors, annotation tracks, and the background. Do not approve a combination solely because it comes from literature, or request the same combination for every dataset. Flag incidental outline mismatches within comparable mark roles or their legends. Fixed-size observations, distribution boundaries, quantitative filled-area dots and binary metadata may need different purposeful treatments. Check hollow-point/whisker crossings, overly thick boxes, washed-out observations and oversized empty bands. Reproduce follows its adopted policy; neither borderless nor hollow marks automatically improve Create.

For create, identify which layer attracts attention first and compare it with
the adopted reading task. In box/points, check whether the median and quartile
boundaries remain continuous; side lanes need unmistakable category association.
In violin, distinguish the contour, inner summary and raw points: an equally
strong silhouette and summary can compete even without label collisions.
Flag supporting marginal bars or metadata strips
that dominate the primary evidence, grids as strong as intervals, zero guides
as heavy as fitted curves, and pale marks that disappear on white. Assess the
benefit of a styling revision using before/after images at the same size; a
quieter image is not automatically easier to read. If the figure is shown in a
README, inspect that display size separately from the manuscript export.

A basic single plot is a complete review target. Do not request marginals,
insets, extra statistics, sample counts or annotation strips solely to make it
look more sophisticated. If one is already adopted, check its meaning and
reading benefit as well as its space. A clean scatter, bar, box, violin or
heatmap is judged by the same color, stroke and final-size standards.

For both tracks, flag an added in-image title unless it was explicitly requested. A title visible in the reference is not authorization to copy it. Do not ask the implementer to restore omitted reference prose or a fixed top-left header; moving that material to the caption is the default manuscript adaptation. Keep plotted counts and necessary annotations when they convey data, rather than treating every number or label as an unwanted overview. Check the caption as a separate artifact, not as figure text to be inserted.

## Compare a claimed improvement

A candidate can satisfy numerical, export, and collision checks yet be visually inferior to the baseline. For a claimed refinement, inspect both actual exports at the same physical size. Compare the intended reading task: visibility of the important pattern, grouping and order, association of related layers, lookup effort, contrast, and use of space. Return a preference of `baseline`, `candidate`, or `no_clear_preference`, with concrete visible reasons. Retaining the baseline is a valid outcome. Smaller bounds, fewer ticks, more layers, and more passing tests do not establish improvement.

Keep requirement failures separate from preferences. An incorrect mapping or clipped required label needs correction; a preference for spacing or guide position can remain provisional. If the baseline cannot be inspected, record comparative preference as `not_checked` and make no improvement claim. This comparison supports substantive refinement; routine edits do not require competing designs.

Record what the baseline represents: an accepted delivered panel or an
omitted-option/default demonstration. Beating a weak default does not establish
the requested literature-level finish. When a paper is the Create design target,
assess the transferable hierarchy, grouping, cell proportions and guide balance
separately; report remaining design gaps. Different source data and tasks make
this a visual design comparison, not a matched quality or model-performance test.

## Findings

Return a concise table with `severity`, `location`, `evidence`, `requirement`, and `action`. Use observable details such as “the third legend item overlaps the right edge,” not “make it more polished.”

| Severity | Meaning | Response |
| --- | --- | --- |
| `critical` | The visual result misstates a required variable, mapping, scale, or statistical meaning. | Correct before presenting it as scientifically ready. |
| `major` | A required layer, label, canvas specification, or important adopted feature fails; text is clipped or unreadable. | Correct if feasible; otherwise mark the requirement unresolved. |
| `minor` | A small, avoidable style or spacing discrepancy that does not change meaning. | Correct when useful without disrupting accepted requirements. |
| `note` | An uncertainty, intentional adaptation, or optional improvement. | Record; do not manufacture a defect to force another pass. |

Record numerical/export checks separately as `passed`, `failed`, or `not_checked`, with the tool or evidence used. A reviewer without measurement evidence must mark those checks `not_checked`.

## Correction loop

1. Review the first rendering and prioritize required scientific mappings, final-size requirements, and readability before cosmetic fidelity.
2. Make changes supported by concrete findings. Re-render all affected formats and rerun checks affected by those changes.
3. Review again only after a meaningful change. Allow at most **three visual review passes in total**, including the first rendering. Stop earlier when required items pass and no meaningful correctable discrepancy remains.

If the same issue persists, a required input is missing, or the third pass still has failures, stop and report what remains. Do not keep shrinking fonts, dropping data, or changing the specification to obtain a pass. An agreed user change to scope or dimensions can start a new iteration with a revised specification.

## Final record

Save the review packet identity, reviewer role (independent or self-review), pass number, findings, corrections, and residual issues. Choose one overall status:

| Status | Use |
| --- | --- |
| `ready` | Required checks were actually completed and satisfied; no unresolved critical or major finding remains. |
| `ready_with_notes` | Required checks passed, with documented minor differences or intentional adaptations. |
| `needs_revision` | A critical/major issue or a required unchecked item remains. |
| `not_reviewed` | The images could not be inspected; state why. |

A successful renderer invocation or schema validation is not a visual review. Deliver only claims supported by the saved checks, including the limitations of self-review or unavailable inspection. Record the candidate and input scope reviewed; a passed case does not establish arbitrary-data or unsupported-chart generalization.

`ready` records satisfaction of the checked requirements. It does not establish aesthetic superiority over the baseline or publication acceptance. Save any comparative preference and its reasons separately from that status.

If the correction changes reusable library styling, verify the affected related chart families and representative category counts, label lengths, and panel sizes. Report the coverage actually checked; do not restrict the evidence to one showcase or change unrelated families merely to make them look alike.
