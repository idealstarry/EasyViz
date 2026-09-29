# Legend transfer benchmark

Only the 10 rendered cases listed below from the ten-case synthetic manifest; no universal legend-layout claim.

The before and after renderer receive identical source bytes and JSON specifications. Font, text sizes, canvas, values, and mappings are fixed within each case.

| Case | Before renderer | After renderer | Benchmark checks |
| --- | --- | --- | --- |
| categorical-2-short-88 | pass | pass | passed |
| categorical-4-long-132 | needs_revision | pass | passed |
| categorical-8-short-180 | pass | pass | passed |
| categorical-8-long-180 | needs_revision | pass | passed |
| colorbar-landscape-132 | pass | pass | passed |
| colorbar-square-88 | pass | pass | passed |
| dot-small-88 | pass | pass | passed |
| dot-large-132 | pass | pass | passed |
| manual-categorical-132 | pass | pass | passed |
| impossible-8-long-88 | needs_revision | needs_revision | passed |

Each run's `measured-geometry.json` records actual legend, symbol, label, colorbar, and plot boxes, including both the data rectangle and its decorated axis footprint. Renderer reports supply selected placement, available regions, occupied envelopes, candidate attempts, and warnings where available. Quantitative size keys are checked against the exact supplied point-area mapping.

Area/length ratios are descriptive diagnostics. A high ratio alone does not fail a panel; failures concern collisions, clipping, missing decoding, changes to values or quantitative areas, font/canvas changes, ignored explicit placement, or an impossible footprint reported as ready.

Inspect `visual-review.md` and original PNGs for visual findings. `contact-sheet.png` is a documentation aid rendered at a common physical scale; it does not establish 8 pt readability by itself.

| Case | Occupied legend boxes, before → after (mm²) | Plot, before → after (mm²) |
| --- | --- | --- |
| categorical-2-short-88 | 124.5 → 39.8 | 2388.7 → 2388.7 |
| categorical-4-long-132 | 688.6 → 359.4 | 4379.2 → 4379.2 |
| categorical-8-short-180 | 462.7 → 163.1 | 6514.6 → 6514.6 |
| categorical-8-long-180 | 1545.5 → 1033.9 | 7328.9 → 7328.9 |
| colorbar-landscape-132 | 410.1 → 218.0 | 3782.1 → 3782.1 |
| colorbar-square-88 | 431.3 → 239.3 | 2919.5 → 2919.5 |
| dot-small-88 | 701.7 → 338.7 | 2919.5 → 2919.5 |
| dot-large-132 | 759.1 → 432.4 | 4777.3 → 4777.3 |
| manual-categorical-132 | 237.2 → 89.7 | 3601.4 → 3601.4 |
| impossible-8-long-88 | 1545.5 → 1001.1 | 1061.6 → 1061.6 |

These occupied boxes include decoding text; smaller is useful only when all required labels and quantitative key sizes remain readable. Manual placement and the intentionally impossible case are behavior checks, not evidence of automatic compaction.
