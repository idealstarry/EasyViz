# Independent forest-panel review

Outcome: both reviewed candidates have no blocking visual revision. One minor concern remains for final proofing: the source-derived pale yellow is the weakest mark color on white. This review does not establish scientific validity or publication suitability.

## Scope and actual inspection

I viewed the supplied reference image and both full-resolution candidate PNGs. I also viewed 397 × 510 px reduced previews of both candidates. I read the adopted specification, both separate captions, each saved QA/stats report, and `verification.json`. I independently inspected the two PDFs' page boxes, font resources, and font-size operators. I did not read implementation scripts or source tables, rerun upstream analysis, or render the PDFs or SVGs for visual inspection.

The reduced previews are a useful density check for the 105 × 135 mm design, but display scaling is uncalibrated. They are not physical or print proofs.

## Reference comparison and adopted changes

Both candidates retain three exposure blocks, eight outcome-color associations per block, horizontal uncapped intervals, circles, hollow/filled states, and the null reference at 1. The original reference's compact two-panel plot uses rotated exposure labels and a shared outcome legend. These outputs intentionally use horizontal bold exposure headers and repeat 24 neutral outcome labels per panel. That gives each pale-colored row an immediate identity.

The absent panel letters, total/direct titles, outer Exposure label, gray enclosing frame, and x = 2 guide match the adopted adaptation. Both panels use the same circle size, while the reference shows differing circle diameters between its two panels. Effect identity is supplied by the separate captions; the panels contain no titles, as specified.

The repeated outcome order and colors are visibly consistent across all three blocks and both candidates. There are 24 outcome labels, three exposure headers, three major numeric tick labels (0.5, 1, 2), one axis label, and two fill-state guide labels in each output. I found no visibly missing row, cropped label, colliding tick, or crowded guide.

## Physical balance, density, and hierarchy

The PDF page boxes independently confirm 105 × 135 mm (within numerical precision). The PDFs use embedded ArialMT and Arial-BoldMT, and all observed font-size operators are 8 pt. Both PNGs are 1240 × 1594 px with approximately 300 dpi metadata; their tiny physical-size rounding difference from the PDF is raster quantization.

The label column uses about one third of the width, leaving a roughly 69 mm plot region. The dense 24-row arrangement remains orderly at approximately 4 mm between adjacent rows, with larger gaps between blocks. Bold gray exposure headers are distinct from ordinary dark outcome labels. The horizontal intervals are thin but visible, and circles remain the primary estimate marks. The dashed null reference stays restrained. The small gray two-row fill-state guide below the axis does not compete with the rows or collide with the axis label.

The direct-effect intervals are visibly shorter than many total-effect intervals, while sharing the same axis and physical geometry. The larger resulting white space in panel B is not a layout failure: both outputs maintain consistent scales and row locations for comparison.

## Pale colors and actionable concern

Pale yellow, blue, and pink remain visible in the reduced previews, and neutral labels preserve row identification. Yellow intervals and hollow circles are the weakest on white. This matches an intentional source-derived palette choice, so I do not require an automatic palette change. Check those marks in the final production proof; if that proof loses them, document any contrast adjustment and apply it consistently to both panels. No blocking crowding or clipping concern was observed.

## Saved numerical and export evidence

Both saved QA reports report 24 input, plotted, and audited rows, with no clipped text or overlapping tick labels. Both saved stats reports identify supplied intervals with no interval recomputation, inferred weights or per-estimate sample sizes, or new tests.

The separately saved exported-PDF audit reports that all 48 original records and raw numeric strings are preserved across the exact partitions. It reports 24 PDF intervals and 24 circles in each panel, correspondence of estimates/asymmetric endpoints and fill states to source records, and geometric 20 pt² circles. Its candidate hashes match the exact files viewed here. I read those results; I did not independently recompute the source-table comparison or infer numeric correctness from the plotted appearance.

## Exact reviewed candidate hashes

- `output-a/panel.png`: `6f92ee38e250baef3f465207f8cf93c98f3ef540bda7bfa5a9e362aaad55c554`
- `output-a/panel.pdf`: `1ffe9f4ff070f01742f6e555f915c97a4ef6d0c0a5539ca7193c08ef705c185e`
- `output-a/panel.svg`: `b8f7602194067e4d2ec8f2725c1bce4efe0d9060dd3d74936ac679fc017e7530`
- `output-b/panel.png`: `96ff894dc6ed0a6f10f4a74c6fa723ad7e246d8ab5460576ff2890cac492b48c`
- `output-b/panel.pdf`: `912ffac130df041212115d1e909495a37d53479ca14e9ea174156c3bd5746f70`
- `output-b/panel.svg`: `2a2041ad9d1bc19721338bdf0e0e7fae3e95b8feb50f456ae424eecca02db0ac`

## Residual uncertainty

No calibrated print proof or color-management check was performed. PNGs were the visual candidates; PDFs were inspected for dimensions/fonts/font sizes without a separate visual page rendering. SVG was hashed and its saved export checks read, but not visually rendered. The reference raster cannot establish original physical typography or dimensions. The scientific analysis and independent source-table arithmetic are outside this visual review. No claim of journal readiness is made.

The JSON companion records exact evidence-file hashes, observed checks, the minor concern, and these review limits.
