# Adopted Create design

Purpose: compare the supplied normalized cell-number distributions between −DT and +DT within each of nine populations. All 156 mouse observations are retained. The source contract adopts group mean ± SEM; no pairing, IDs, normalization denominator or batches can be reconstructed.

Reading burden: 18 groups, 8–10 observations each, range 0.135519–3.527703. The supplied population order and −DT / +DT order are fixed. No fitted density, tests or count labels are needed.

Organization: one vertical categorical plot with repeated two-condition blocks on the same 0–4 numeric axis. The 120 × 60 mm canvas uses an approximately 101 × 38 mm data rectangle and 11.22 mm population pitch. Condition centers are 5 mm apart. Raw marks have a categorical-only packing lane, with each mean/SEM beside its own lane. This keeps the required summary readable without hiding observations. The point-to-summary association and grouping gaps require actual-image review.

Hierarchy: opaque 2.5 pt circular observations carry the distribution and condition identity; definite 0.65 pt SEM strokes and a 1.05 pt short mean stroke provide secondary lookup. Graphite (#454545) and blue (#0072B2) decode −DT and +DT, repeated in the compact top legend. All readable text is Arial 8 pt. White background, dark 0.55 pt axes, no grid, title or panel letter.

Learning mechanism: current literature guidance describes repeated two-series geometry with closely associated treatment pairs and raw observations beside visible uncertainty strokes. The distribution-summary-lane card visibly separates raw values from summary boundaries; its good/failure images were inspected. I adapt that separation to mean ± SEM, retaining the adopted summary rather than copying the card's median/quartiles. The card's three-group layout and area palette are not adopted.

Expected benefit: every observation remains individually distinguishable, within-population treatment groups remain closer than adjacent population blocks, and SEM/mean strokes remain uninterrupted. Check those properties on the actual final-proportions image.

Implementation choice: custom code. The core distribution contract supports box/violin summaries, while the focused replicate recipe requires explicit unit IDs and supports sample SD, not SEM. The frozen create-candidate helper does not offer this two-level grouped raw-lane plus mean/SEM organization. No synthetic experimental IDs or substitute uncertainty will be introduced to use it.

## Actual correction and accepted settings

The initial narrow greedy lanes produced visible raw-point crowding and 15 insufficiently separated circle pairs. Attempt 02 preserves the initial render and adopts bounded constrained packing with ±1.3 mm raw displacement, 5.3 mm treatment separation and the summary center 1.75 mm right of its treatment center. No numeric coordinate, point size, font, canvas, source order or statistical definition changed. It has zero point-pair spacing failures, raw/summary crossings or boundary violations. PNG uses rounded 1417 × 709 pixels at 300 dpi; one missing white raster edge pixel is padded without resampling or changing the vector canvas. The final choice is attempt 02, following two actual-image self-review passes.
