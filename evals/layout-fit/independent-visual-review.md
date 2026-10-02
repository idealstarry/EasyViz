# Independent visual review of layout-fit panels

Scope: actual rendered PNG comparison of three synthetic engineering examples. `fixed` is the baseline; `measured` is the candidate. I opened all six supplied images at their original raster dimensions. I did not read implementation code, helper scripts, evaluation reports, or other reviewers' findings. The supplied specification states identical source data, Arial 8 pt, and an 88 × 70 mm canvas for each pair. This review does not establish journal or CNS acceptance or generalization to other figures.

## Pair preferences

| Pair | Preference | Visible reasons | Remaining limitations |
| --- | --- | --- | --- |
| Scatter | `no_clear_preference` | Both images preserve all plotted points, axes, units, and a clear increasing pattern. Neither has obvious clipping or overlap. The fixed image has generous top and right whitespace and a compact set of x ticks. The measured image fills more of the canvas and exposes horizontal point separations more strongly, but adds many decimal-formatted x ticks. That additional tick detail is not necessary to read the increasing pattern. Marks remain visually primary in both. The larger data rectangle does not by itself demonstrate better reading. | The measured image has less breathing room at the top and right, although no content is visibly cut off. Its denser ticks remain readable, but a simpler set would reduce lookup effort. This is an optional tradeoff, not a requirement failure. |
| Long-label distribution | `candidate` (`measured`) | The measured image shows the complete four category names: Resident macrophages, Activated monocytes, Interferon macrophages, and Antigen-presenting cells. In the fixed image, several name beginnings run beyond the left canvas edge, leaving two macrophage rows distinguishable mainly through color and position. The candidate restores direct row identification while preserving the boxes, median lines, whiskers, and individual observations. The actual horizontal plotting span is broadly comparable across the two images; the improvement is complete labels and row legibility, not merely a larger data area. | The long names consume substantial width, but are necessary reading information and remain subordinate to their associated rows. The measured vertical row spacing is generous; it creates separation without crowding or overlap. No mandatory visual correction is evident in the candidate. |
| Rectangular heatmap | `candidate` (`measured`) | Both images show all seven gene rows, nine sample columns, and the same visible color arrangement, with a compact continuous scale carrying −2, 0, and 2 labels. The fixed image places the bottom `Sample` axis name partly below the canvas edge; the candidate makes it fully visible and preserves all rotated sample names. The candidate also uses the available width more evenly, while keeping its color scale narrow enough that the heatmap remains the primary element. The cells are closer to square, but this is secondary to the recovered label. | The vertical sample labels require reading rotated text, but do not overlap. The color scale is short relative to the heatmap; its three labeled anchors are still visible and adequate for this supplied synthetic scale. No mandatory visual correction is evident in the candidate. |

## Findings

| severity | location | evidence | requirement | action |
| --- | --- | --- | --- | --- |
| major | Long-label distribution, fixed, left edge | The beginnings of multiple category names extend outside the image. Visible fragments include clipped macrophage names and a clipped presenting-cells name. | Category labels must remain complete and readable so each row can be identified independently. | Reserve the width required by the actual full category strings before positioning the plotting region. The supplied measured image visibly resolves this. |
| major | Rectangular heatmap, fixed, bottom edge | The `Sample` axis name is visibly cut by the lower canvas boundary. | Required axis names must remain fully inside the final canvas. | Reserve bottom space for both the rotated sample ticks and the axis name. The supplied measured image visibly resolves this. |
| note | Scatter, measured, x-axis | The candidate shows 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, and 17.5, whereas the fixed image uses a sparser tick sequence. The candidate labels fit, but require more decoding for the same visible trend. | Tick density should support the actual reading task without dominating the data. | Optionally use fewer ticks or omit unnecessary decimal places. Preserve the agreed font size and plotted values. This does not prevent visual use of the candidate. |
| note | All panels, manuscript context | No extra title, subtitle, overview text, or explanatory footnote is present. Essential axes and color scale text remain. A separate caption was not supplied for this task. | Keep narrative material in a separate caption and retain data-reading elements in the image. | Preserve this text hierarchy; inspect the caption separately when a manuscript caption is supplied. |

## Checks and limits

| Check | Result | Evidence |
| --- | --- | --- |
| Actual image inspection | passed | All six named PNGs were opened and compared. |
| Canvas consistency | passed | Every PNG has IHDR dimensions of 1039 × 827 pixels. |
| Nominal physical canvas | passed | Every PNG has pHYs of 11811 × 11811 pixels per metre, approximately 300 dpi. The metadata implies 87.97 × 70.02 mm, consistent with nominal 88 × 70 mm after raster rounding. This is metadata evidence, not a printed-page measurement. |
| No obvious missing plotted content between paired images | passed, visual only | Each pair visibly retains the same plotted observations, category/row order, and broad color structure. Exact numerical identity was not checked. |
| Complete visible required text | failed for two baselines; passed for all three candidates | Fixed distribution category names and fixed heatmap axis name are clipped. The measured panels show their full required text without visible overlap. |
| Actual Arial font and 8 pt font size | not_checked | Raster inspection and PNG metadata cannot establish the font family or exact point size. The values are supplied specifications, not independently verified export facts. |
| Numerical data and statistical summaries | not_checked | Source values and computation were outside this image-review scope. |
| Caption completeness | not_checked | No caption was supplied or inspected. |
| Physical print legibility | not_checked | All panels were inspected at identical raster dimensions and intended proportions. A screen zoom is not a proof of legibility on an actual 88 × 70 mm printed page. |

The candidates have no visible major layout failure in these supplied renders. Measured fitting visibly improves the two examples where required text was cropped, while the scatter pair remains a tradeoff with no clear preference. The evidence is limited to these three synthetic examples.

Status: `needs_revision` for the full supplied set, because two fixed baselines visibly clip required text and the actual font/point-size requirement remains independently unchecked. This status is separate from the per-pair aesthetic preferences. The most useful corrections are the measured label reservations already demonstrated for the distribution and heatmap, plus verification of actual export typography; no mandatory visual revision is identified in the measured renders.
