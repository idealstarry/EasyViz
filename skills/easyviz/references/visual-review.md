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
| Style | Category colors, continuous scale direction, marker shape, line weights, typography hierarchy, and relative margins. Check one declared outline policy across comparable filled dots, bars, and matching legend swatches, including any documented scientific/readability exceptions. |
| Final-size export | Independent page/pixel measurements, preserved canvas boundaries, actual font records, matching format dimensions. These require measurements, not a visual guess. |

Do not use pixel similarity as a pass condition when data, fonts, or final physical dimensions differ. Different data-driven shapes and documented adaptations are expected. Exact colors, statistical correctness, physical size, and font embedding cannot be certified from a screenshot alone.

Review palette combinations together in the actual panel, including contrasts between continuous maps, category colors, annotation tracks, and the background. Do not approve a combination solely because it comes from literature, or request the same combination for every dataset. Flag incidental outline mismatches across related marks or legends; create defaults to borderless marks, while reproduce follows the adopted policy.

For create, identify which layer attracts attention first and compare it with
the adopted reading task. Flag supporting marginal bars or metadata strips
that dominate the primary evidence, grids as strong as intervals, zero guides
as heavy as fitted curves, and pale marks that disappear on white. Assess the
benefit of a styling revision using before/after images at the same size; a
quieter image is not automatically easier to read. If the figure is shown in a
README, inspect that display size separately from the manuscript export.

For both tracks, flag an added in-image title unless it was explicitly requested. A title visible in the reference is not authorization to copy it. Do not ask the implementer to restore omitted reference prose or a fixed top-left header; moving that material to the caption is the default manuscript adaptation. Keep plotted counts and necessary annotations when they convey data, rather than treating every number or label as an unwanted overview. Check the caption as a separate artifact, not as figure text to be inserted.

## Compare a claimed improvement

A candidate can satisfy numerical, export, and collision checks yet be visually inferior to the baseline. For a claimed refinement, inspect both actual exports at the same physical size. Compare the intended reading task: visibility of the important pattern, grouping and order, association of related layers, lookup effort, contrast, and use of space. Return a preference of `baseline`, `candidate`, or `no_clear_preference`, with concrete visible reasons. Retaining the baseline is a valid outcome. Smaller bounds, fewer ticks, more layers, and more passing tests do not establish improvement.

Keep requirement failures separate from preferences. An incorrect mapping or clipped required label needs correction; a preference for spacing or guide position can remain provisional. If the baseline cannot be inspected, record comparative preference as `not_checked` and make no improvement claim. This comparison supports substantive refinement; routine edits do not require competing designs.

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
