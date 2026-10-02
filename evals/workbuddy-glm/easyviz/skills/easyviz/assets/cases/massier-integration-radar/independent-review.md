# Independent review: depot kBET radar

**Status: ready_with_notes.** No critical, major, or minor correction is required. The current second-render candidate was reviewed without reading plotting implementation or author code. No third render is warranted.

The reference image and candidate PNG were both opened. All five cell classes follow the required clockwise order, and all five methods have the correct legend colors. The unfilled straight traces, circular markers, radial tick labels, dashed rings, and pale background match the adopted specification. Grid and spokes remain beneath the evidence. Direct labels and the two-row legend fit within the canvas without clipping or avoidable collisions.

| severity | location | evidence | requirement | action |
|---|---|---|---|---|
| note | Center and near-zero vertices | Three exact zeros and other small values overlap. The adopted zero origin changes some shapes relative to possible reference padding. All 25 vertices are present in the SVG. | Preserve valid zeros and supplied rates; disclose unknown original padding. | Keep the documented adaptation. Do not jitter or offset scientific values. |
| note | Standalone assembly | Direct class labels, a two-row method key and the depot title replace shared whole-figure elements. All categories remain readable and identifiable. | Deliver a self-contained 88 × 88 mm chart with 8 pt text. | Accepted adaptation; keep the current layout. |
| note | Final-size readability | The PNG is legible and the dimensions and 8 pt typography were measured directly. | Do not equate screen zoom with physical print proof. | No required change; paper printing was not checked. |

Numerical and export checks are separate from visual findings:

| check | status | evidence |
|---|---|---|
| Data preservation | passed | Independent numerical sub-review confirmed all 25 exact source strings and unique pairs, complete five-by-five coverage, no missingness, three zeros, and range 0–0.47525. |
| Coordinate mapping | passed | Independent Cartesian calculations match every saved coordinate exactly; all zeros lie at (44,52) mm. |
| SVG markers and traces | passed | Reviewer directly verified five data markers per method, plus one legend marker. All 25 positions match the saved coordinates within 0.000001 pt; each unfilled trace joins five ordered vertices and closes. |
| PDF | passed | One page, 88.000001 × 88.000001 mm; all 16 text spans are 8 pt and within the page; ArialMT is embedded. |
| SVG | passed | 88 × 88 mm equivalent dimensions; 16 editable Arial text elements at size 8 in the point-scaled coordinate system. |
| PNG | passed | 1039 × 1039 pixels; 299.9994 dpi metadata, matching the requested 300 dpi export. |
| Authentication against original publication | not_checked | Supplied CSVs were accepted as inputs; the original workbook, author code and upstream kBET analysis were outside this review's required scope. |
| Physical print proof | not_checked | No paper print inspected; not a required deliverable. |

The original radial padding, overlap order and exact styling remain unknown. The documented zero-origin choice and standalone key placement are intentional adaptations, not mapping failures. Isolation was instruction based, not an operating-system sandbox guarantee. The reviewed file hashes are recorded in `independent-review.json`.

**Final status: ready_with_notes.**
