# Independent visual review

## Scope and evidence

Reviewed the actual `previews/box-points/panel.png` and `previews/ecdf/panel.png` with `view_image`, then their specifications, captions, settings, QA records, and preview manifest. Inspected the delivered PDF/SVG/PNG export headers and verified their hashes against the manifest. No earlier evaluation, other candidate, implementation code, or prior review was inspected.

Reading task: a compact Control versus Condition distribution comparison that shows every independent synthetic subject and a descriptive summary, with bright colors, a 110 × 85 mm canvas, Arial 8 pt, PDF/SVG/PNG exports, a separate caption, and no hypothesis tests. Supplied source binding: 54 rows, Control 24 and Condition 30, SHA-256 `2ad11453299a8ab513c291384259897094241b2f6c2845bfffecada60504b4fd`.

## Chart choice

**Prefer box-points for the requested primary panel.** It shows separate colored marks for the subjects, including repeated measurements, and supplies directly readable medians, quartiles, and whiskers. Condition is visibly concentrated farther to the right, while the Control box is broader. The dots preserve the tails and local concentrations that the box alone would hide. Neither group requires a legend lookup because its row is labeled directly.

**ECDF is useful as an additional distribution view.** Its steps support reading the fraction at or below a measurement, comparing tails, and recognizing concentration through steep versus shallow sections. However, the curves have no subject markers. Tied observations combine into one vertical jump; the supplied QA records 22 unique Control values and 23 unique Condition values. Retaining all 54 observations in the curve calculation does not make all 54 subjects individually visible. A reader also has to trace from a curve to the bottom legend and read a median from the 0.5 level rather than a marked median. It therefore does not fully meet the explicit individual-subject display requirement as a standalone alternative.

No accepted baseline was supplied and no refinement comparison was requested. A baseline/candidate improvement preference is `not_checked`; the preference above is between chart types for this specific reading task.

## Findings

| severity | location | evidence | requirement | action |
| --- | --- | --- | --- | --- |
| major | ECDF subject display | Both groups appear only as step lines; tied measurements are merged into jumps and there are no separately visible subject marks. The QA records 45 unique values across 54 subjects. | Show every independent synthetic subject. | Use box-points as the primary requested panel. If ECDF must be the standalone panel, add a clearly separate raw-subject layer that distinguishes ties without moving measurement coordinates. Do not treat source-row retention as proof of individual visual visibility. |
| minor | Box-points full-panel spacing and summary weight | The two row centers are about 32.6 mm apart according to the supplied geometry. Each shaded box is approximately 16 mm tall in the image, while each point is about 1.1 mm across and the swarm offsets use only about 1.2–1.7 mm on either side. This creates a large empty gap and gives the shaded summary much more visual area than the narrow strip of subjects. | A compact comparison with readable subjects and descriptive summaries. | Test a shallower box and a more deliberate balance between row spacing and the two mark layers, preserving the 110 × 85 mm canvas, Arial 8 pt, all subjects, and measurement coordinates. Re-review the complete panel; merely reducing box height can increase unused space. This is a balance issue, not a loss of data. |
| note | Box-points point-summary intersection | The black whisker line passes through the point centers, for example at the Control extremes and along the dense Condition center. Filled dots remain visible and the median lines remain readable above and below the points. Circle-to-circle separation is supported by both the image and the supplied layout audit. | Both individual values and summaries should be readable. | No required correction. If raw-subject prominence is the priority, compare a nearby separate summary lane while keeping the same quantitative coordinates; do not infer that zero circle collisions resolves all layer interactions. |
| note | ECDF legend and complete panel | The bottom legend has two rows but is visibly modest: the supplied full bounds are about 18.7 × 6.3 mm against a 94.1 × 63.5 mm data region. The legend is readable, does not overlap the axis title, and leaves the curves visually primary. | Readable guidance without excessive reserved space. | No required correction. A one-row legend may be tested if reducing the bottom band is desirable, with the agreed font and line key sizes preserved. The current layout is technically and visually usable. |
| minor | Both separate captions | The observational-unit sentence ends in `task..`. Both captions give the total 54 rows but omit the individual group counts. | Clear separate explanatory caption, especially for the ECDF's group-specific denominators. | Remove the duplicated period and include Control n = 24 and Condition n = 30 in the caption. Keep these counts and explanatory prose outside the image. |

The blue and coral colors are distinct on the white background, and the stronger point fills remain visible over their pale boxes. Raw points are borderless. The box outlines identify a different summary role; they are not an incidental point-outline mismatch. Both panels preserve units, category mappings, linear measurement limits, and readable tick labels. Neither actual image has an extra title, overview count, explanatory footnote, clipped label, missing glyph, or visibly crowded tick label.

## Numerical and export checks

| check | status | evidence and limit |
| --- | --- | --- |
| Source binding and observation retention | passed | Both supplied QA records bind to the stated source hash and audit 54 observations. Box-points reports 24 Control and 30 Condition subjects, unchanged measurement values, and 54 placed points. ECDF reports retained ties and no smoothing. These are supplied audit results; source values were not independently recomputed in this visual review. |
| Circle separation | passed | Box-points QA reports zero overlapping circle pairs and zero spacing violations, minimum center distance 3.3 pt for 3.0 pt circles. The opened image visibly separates repeated values. Point-summary intersections were assessed separately above. |
| Summary and ECDF arithmetic | not_checked | No independent recomputation of quartiles, whisker endpoints, or cumulative ordinates was performed. This review assesses their visible form against the adopted definitions and relies on the supplied audit for source-to-artist correspondence. |
| PDF/SVG physical canvas | passed | Both actual PDFs have MediaBox 311.811023622 × 240.9448818898 pt, equivalent to 110 × 85 mm. Actual SVG roots declare 311.811024 × 240.944882 pt with matching viewBox. |
| Font and text size | passed | Both PDFs declare subset ArialMT and contain a FontFile2 embedding entry. Both actual SVGs retain text with Arial and size 8 in a viewBox whose units map to points at the declared physical size. Settings independently record Arial, no substitution, and 8 pt axis/tick/legend text. Exact PDF text-operation font sizes were not separately decoded. |
| PNG size and resolution | passed | Both actual PNG headers are 1299 × 1004 px; supplied export QA reports approximately 300 dpi, consistent with the requested physical dimensions after pixel rounding. |
| Export identity | passed | All six actual PDF/SVG/PNG file hashes match their manifest entries. |
| Caption and descriptive scope | passed | Separate captions define the displayed summaries or ECDF, state equal observation weight, and state that no hypothesis test, confidence interval, or effect inference is performed. Neither image includes inferential annotations. Computational absence of tests was not independently established by inspecting implementation code. |
| Full-panel readability | passed | Both actual opened PNGs show readable labels and no clipping or text/legend collisions. Supplied QA agrees. Print-size judgement uses confirmed physical dimensions and supplied 8 pt typography; screen zoom alone was not treated as proof. |

## Readiness

Box-points is `ready_with_notes` for this request; its spacing and caption edits are minor. ECDF is `needs_revision` as a standalone answer to the explicit every-subject display requirement, although it is usable as a supplementary distribution view. The most useful next step is to select box-points, tidy the caption, and optionally adjust the oversized summary/row spacing after a full-panel comparison. Independent arithmetic recomputation remains outside this bounded visual review. These findings apply only to the supplied panels and do not establish benchmark gains or performance on other data.

**Status: ready_with_notes** — for the recommended box-points primary panel.
