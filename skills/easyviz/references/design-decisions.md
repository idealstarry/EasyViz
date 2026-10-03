# Design decisions with worked alternatives

Use a pattern when its reading task matches the user's data and question. These are conditional decisions demonstrated on real source tables. They do not require every chart to be dense, and their examples are not universal presets.

## Paired changes: retain people or emphasize distributions

**Evidence.** [Massier et al. (2023)](https://doi.org/10.1038/s41467-023-36983-2) released precomputed deconvolution scores in `Figure_8d_8e.xlsx`. The [paired myeloid case](../assets/cases/paired-myeloid-remodeling/README.md) compares all 16 myeloid subtypes in 15 Petrus and 37 Kerr participants with matched baseline and two-year observations. These are source scores, including negative values, not measured cell counts or percentages. EasyViz's three layouts are new create designs; they do not reproduce the paper's figure or use author plotting code.

| Reading task | Design decision | What the alternative costs |
| --- | --- | --- |
| Compare typical change and spread between cohorts | Keep a common quantitative x-axis and row order. Compare opaque observations with separately outlined median/IQR summaries in aligned cohort facets. Align a descriptive fraction below zero only if consistency of direction matters. | Facets reduce each cohort's plot width; the packed case needs very small fixed-size marks. A plain box/points view retains familiar whiskers. The extra percentage column can be unnecessary. |
| Follow several subtype changes within the same person | Assign one fixed column per participant across every subtype row. Split cohorts with a gap, preserve biological row groups, and put a compact median/IQR margin on the same row coordinates. | A color matrix preserves participant identity but sacrifices precise individual value reading. A distribution panel gives more quantitative resolution. |
| Recognize which changes are coherent across people | Order participants once within each cohort by a declared summary across the selected subtypes, and preserve that order in all rows. Save the rank-to-participant map. | Sorting each row independently destroys the within-person correspondence. Sorting by median change creates a visible gradient by construction; it is not independent evidence of a cluster or coordinated mechanism. |

The distinction is data identity, not chart complexity. A row of scattered points does not let the reader trace the same person across subtypes unless that identity is explicitly encoded. A matrix supports that lookup only when each column means the same person in every row. A descriptive median/IQR margin supports cohort comparison without converting participant variability into a confidence interval.

**Adaptation conditions.** Join baseline and follow-up by cohort, participant and subtype before computing differences; fail on unmatched pairs instead of treating visits as independent groups. State any selection and missingness. Preserve a meaningful zero. Keep one shared color normalization when comparing subtype magnitudes; independent row normalization would change the question. For many more participants, widen the data field or choose a distribution representation according to the requested lookup task. The bundled recipe is explicitly limited to one or two cohorts and at most 16 annotated rows at its fixed canvas; it is not an arbitrary longitudinal plotting engine.

**Support and tested variation.** The case includes a competent box-and-points baseline, a participant matrix, and a distribution view with aligned summaries, all at 180 × 125 mm and 8 pt. The same implementation is exercised on Kerr's five-year matched follow-up. Use the saved alternatives and decision record to explain the tradeoff; do not claim one layout wins for every reading task. The script supports the source contract directly; other longitudinal schemas require explicit adaptation.

## Signed matrices: decide what color distance should convey

**Evidence.** In the [Gontijo et al. (2022)](https://doi.org/10.3390/microorganisms10091794) development case, the 20 × 20 selected inhibition matrix has quartiles around 79, 139 and 201 minutes within a full color range of −400 to 1000 minutes. A sequential coral scale leaves most cells similar and fails to distinguish negative from positive values clearly. Full-matrix marginal means are useful context, but saturated bars can draw attention away from the individual pairwise measurements.

| Intended comparison | Candidate | Retain or reject it based on |
| --- | --- | --- |
| Compare differences in the original measurement units | A value-linear scale with an explicit zero tick and a distinct negative hue | Equal numerical increments retain equal scale increments. Moving neutral to zero can make common small positive values even paler; sign decoding improves without necessarily improving pattern visibility. |
| Distinguish signs and moderate positive regions without changing values | Explicit `TwoSlopeNorm(-400, 0, 1000)` plus reviewed blue/white/gold/orange/coral stops | Zero occupies the midpoint; each arm is linear in raw minutes but has a different slope. Gold/orange separates moderate positives from high coral cells. This is a declared color-encoding change, not one globally linear scale. |
| Inspect moderate-value structure alongside a few extremes | A disclosed signed `asinh(x / a)` color normalization, with original-unit ticks and zero anchored to neutral | Moderate differences gain color separation and high-value differences lose it. The scale parameter `a` is a recorded display choice, not a biological threshold. Use only when this tradeoff supports the reading task. |
| Keep marginal summaries secondary | Reduce the bars' visual weight relative to the matrix, while keeping their numerical axes and correct alignment | A quieter margin may restore data hierarchy. It does not justify muted colors everywhere, or removing a scientifically primary summary. |

For an asymmetric range, neutral belongs at the adopted `norm(0)`. It is halfway only when explicitly normalized that way. In the historical −400…1000 development experiment with `a = 100 min`, zero lies at approximately 0.4113 of the asinh scale; on a globally value-linear scale it lies at approximately 0.2857. The refreshed case deliberately uses two linear branches with zero at 0.5 and records their forward/inverse mapping. Retain the complete value range and all summaries, and label the chosen encoding. Never silently cap values, quantile-map them, or normalize rows to make a stronger-looking pattern.

**Support and boundary.** The [annotated heatmap recipe](../assets/recipes/annotated-heatmap/README.md) supplies alignment, selection, full-matrix marginals and the explicitly configured signed scale. The historical linear-zero and asinh experiments remain alternatives; none is a universal core default. The restricted source matrix is not bundled. Preserve a shared adopted scale when comparing panels; choose asinh only when its compression tradeoff serves the reading task.

## When to keep the earlier design

A short colorbar is not a better colorbar merely because it occupies fewer square millimeters. A dense top legend can fix clipping while making category names the strongest element on the page. If the plot gains no useful room, decoding is slower, or a primary pattern becomes harder to see, keep the baseline or compare another feasible design. Record a visible reading benefit before claiming an improvement; technical checks remain necessary evidence of correctness, not a substitute for that comparison.
