# Forward font-margin repair diagnostic

This is a known engineering regression fixture, not a fresh quality benchmark. No prior three-pass evaluation artifacts were changed. The initial diagnostic preceded independent review; the later [actual-image check](independent-image-review.md) records its completed PNG scope and retained locked failure.

The CI failure was real: Arial fallback to DejaVu reduced category pitch. Before repair, the 80 × 70 mm four-group panel had a 0.023516 mm half-spread deficit even at the existing 0.2 pt positive-gap trial, one spacing conflict and one fallback. Source-to-artist checks passed, so accepting the old unconditional success expectation would have weakened the geometry gate.

Version 0.2.3 derives additional category-axis space from actual marker diameter, summary body/stroke/retained-inner envelope, packing demand and measured available padding. Only an omitted category far edge can borrow space within a fresh 1.5 mm padding fit. Numeric-axis geometry is retained. Explicit/manual/profile geometry stays authoritative. The original gap, marker area, fonts, canvas, source values and statistical contract are retained. This does not promise every font/canvas can fit; the actual final renderer and artist gates remain decisive.

- `arial-present`: requested/actual Arial, no extra margin; all three routes pass actual PNG/SVG QA.
- `explicit-dejavu`: requested/actual DejaVu Sans, right-edge borrow 0.448964 mm within measured 0.5 mm; all three routes pass. Physical box body 3.470176 pt is at least the 3.464102 pt marker outer diameter.
- `arial-forced-unavailable`: only Arial font lookup is injected to the installed real DejaVu font path throughout planning and export. Requested font remains Arial; actual family and substitution are disclosed. Same three-route geometry and passing QA as explicit DejaVu.
- `explicit-dejavu-160`: right-edge borrow 0.316193 mm at 160 dpi, showing correction derives from real metrics rather than a fixed DejaVu adjustment.
- `horizontal-dejavu`: bottom-edge borrow 0.084465 mm; numeric x transform, source values and reversed categorical axis remain unchanged; actual QA passes.
- `explicit-locked-margins`: same observations with an explicitly adopted original fitted region; no borrowing, one spacing conflict, source-to-artist passes, actual QA correctly remains needs_revision. This failure fixture is a lock regression, not a reclassification of the original source spec.

All cases preserve 42 observations, numeric limits, point area 12 pt², 8 pt tick fonts and source-defined Welch statistics. Normal and fallback cases use gap 0.2 pt, with no new smaller-gap fallback. Each candidate directory has actual panel.png/panel.svg, spec.json, settings.json, geometry-evidence.json, qa.json, stats.json and plotting-data.csv. Source/spec snapshots are in the case root.

Final focused result: 30 tests passed in 67.766 seconds. The log is focused-tests.log. Owner source snapshots and hashes are in owner-runtime-snapshot and diagnostic-context.json. These two source snapshots are not the full runtime dependency closure.
