# Independent review: BMI violin

**Status: ready_with_notes.** No critical, major, or minor correction is required. The current first-render candidate was reviewed without reading plotting implementation or author code; no additional rendering is requested.

The reference image and candidate PNG were both opened. All eight cohorts appear in the required order with complete labels. The linear BMI axis, 20/40/60 labels, purple bodies, fine outlines, and guides beneath the marks agree with the adopted specification. There are no extra summary marks, clipped labels, missing glyphs, or crowded rows.

| severity | location | evidence | requirement | action |
|---|---|---|---|---|
| note | Density profiles and extrema | Some lobes and flat ends differ from the reference. The stated Gaussian KDE, Scott bandwidths, trimming, and equal displayed-area rule account for these differences; exported polygons match the saved curves. | Preserve observations and disclose unknown author settings. | Keep the method and uncertainty notes; no correction. |
| note | Standalone proportions | The requested 132 × 99 mm panel expands the reference column and provides room for full cohort labels. | Preserve the requested canvas and 8 pt text. | Accepted adaptation; keep the current layout. |
| note | Final-size readability | The PNG is legible and the dimensions and 8 pt typography were measured directly. | Do not equate screen zoom with physical print proof. | No required change; paper printing was not checked. |

Numerical and export checks are separate from visual findings:

| check | status | evidence |
|---|---|---|
| Data preservation | passed | Independent numerical sub-review confirmed 864 unchanged source records, 858 available values, and six retained missing values. All original BMI strings and row order are preserved. |
| Density calculation | passed | Independent Gaussian-mixture calculation agrees with saved bandwidths and densities to floating-point tolerance. Each of eight 512-point displayed curves integrates to one; maximum full thickness is 0.9 row spacings. |
| SVG density geometry | passed | Reviewer directly compared all saved density samples with eight exported purple polygons. Coordinate differences are below 0.000001 pt. |
| PDF | passed | One page, 131.999996 × 98.999997 mm; all 12 text spans are 8 pt and within the page; ArialMT is embedded. |
| SVG | passed | 132 × 99 mm equivalent dimensions; 12 editable Arial text elements at size 8 in the point-scaled coordinate system. |
| PNG | passed | 1559 × 1169 pixels; 299.9994 dpi metadata, matching the requested 300 dpi export. |
| Authentication against original publication | not_checked | Supplied CSVs were accepted as inputs; no original workbook, article, or author code was accessed. Outside this review's required scope. |
| Physical print proof | not_checked | No paper print inspected; not a required deliverable. |

The original density choices and precise palette remain unknown. This is a review of the documented, data-preserving reproduction, not a claim of exact recovery of the original plotting method. Isolation was instruction based, not an operating-system sandbox guarantee. The reviewed file hashes are recorded in `independent-review.json`.

**Final status: ready_with_notes.**
