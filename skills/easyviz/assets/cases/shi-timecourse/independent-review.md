# Independent figure review

## Scope and inspected evidence

**Review pass:** 2 of at most 3. Pass 1 identified an absent rendered-font measurement record; pass 2 verified the added evidence and freshly opened both final candidates. The complete reference, main candidate, and synthetic transfer candidate were actually opened in the image viewer at original detail. The source caption was read during the independent reference reading and retained in this review context.

Allowed specification/caption/check inputs inspected: main `adopted-spec.md`, `spec.json`, `caption.md`, `output/qa.json`; transfer `spec.json`, `caption.md`, and `output/qa.json`. No plotting code, source data, other case files, or author code was inspected. Candidate PNG metadata was additionally checked directly; both images are 1181 × 898 pixels at 300 DPI. The implementation agent subsequently supplied two additional allowed 96-DPI PDF-derived previews; both were actually viewed in pass 2. At these intended page proportions, all axis labels, ticks, and the transfer legend remain legible, with no clipping or overlap.

This is a reference reproduction and a separately labelled synthetic transfer review, not a claimed refinement. Baseline-versus-candidate preference is **not applicable**.

## Main Shi time-course panel

The visible image preserves the required scientific mapping: blue cell width on the left, orange cell length on the right, shared time in minutes, thin central lines, filled summary-time markers, and pale bands behind the lines. Colored axes correctly identify the series without a legend. The early rise and later flattening of width and the accelerating late rise of length agree with the reference's visible reading task. Labels and units are complete and legible, the top spine is absent, ticks point inward, and the entire bands remain visible.

The caption correctly assigns means and supplied mean ± SD to 146 followed cells, assigns the tiny markers to the supplied minute summaries, explains the distinct y scales, and avoids treating the cell count as independent biological replication. Source credit and explanatory prose are outside the image. The panel-letter omission and the larger lower-axis extent are documented adaptations.

| Severity | Location | Evidence | Requirement | Action |
|---|---|---|---|---|
| note | Typography verification — resolved | The updated QA records 18 actual visible axis-label/tick Text objects after final layout; all are Arial 8 pt and resolve without fallback to the recorded Arial font file and hash. | Adopted fixed typography must be supported by a measurement/check record. | No repair. The pass-1 evidence gap is closed. |
| note | Plot geometry | The candidate plot bounds are approximately [0.111, 0.026, 0.912, 0.869], derived from supplied layout measurements; the reference crop is approximately [0.165, 0.110, 0.858, 0.858]. The candidate gives more canvas area to the data and uses smaller relative text. | Fixed 100 × 76 mm canvas and 8 pt text are explicit EasyViz adaptations; exact pixel geometry is not required. | Retain the adopted physical dimensions and font size. This is a residual layout difference, not a mapping failure. |
| note | Right vertical title | The reference's right title reads top-to-bottom; the candidate's right title reads bottom-to-top. It remains readable and clearly associated with the orange scale. | The adopted specification requires the labelled colored right axis but does not prescribe this rotation direction. | No required repair. Record the residual orientation difference. |
| note | Bands and axes | The candidate shows additional clearance around the band edges because width limits are 0.88–1.27 and length limits are 1.5–5.5. The reference band approaches or touches its plot boundaries. | The adopted limits intentionally show every supplied bound. | No repair. Do not crop supplied SD bands to match the source crop. |
| note | Source/statistical verification scope | The supplied QA reports all 120 source summaries and 240 band endpoints checked with no issues. Source values were excluded from this review. | Preserve source coordinates and supplied SD meaning. | Treat the numerical audit as supplied check evidence, not as a recalculation performed by this reviewer. |

**Visual repairs needed:** none identified. **Residual differences:** larger relative plot area, compact fixed-size typography, right-title rotation direction, estimated rather than recovered exact hues, and intentionally expanded y bounds. These do not change the data meanings.

## Synthetic transfer panel — separate fixture

The transfer is clearly identified in its caption as synthetic and unrelated to the Shi measurements. The visible six concentrations per curve match the stated sparse summary role: filled markers indicate supplied central summaries, straight segments connect them, and pale asymmetric bands stay behind all three lines. The x axis shows the prescribed positive ticks on a logarithmic scale; the response axis is shared and linear. Literal identifiers `001`, `NA`, and `null` are retained.

The bottom legend correctly associates green with `001`, blue with `NA`, and orange with `null`, in the specified order. It fits without overlap and remains subordinate to the data. The supplied complete key/text envelope is 37.2 × 3.05 mm versus an 86.13 × 59.01 mm plot; its area is approximately 2.23% of the data region. The line handles are categorical proxies, with no quantitative-size meaning. Filled markers show no incidental dark outline. Labels, tick numbers, and legend identifiers are clear.

| Severity | Location | Evidence | Requirement | Action |
|---|---|---|---|---|
| note | Typography verification — resolved | The updated QA records 16 actual visible axis-label/tick/legend Text objects after final layout; all are Arial 8 pt and resolve without fallback to the recorded Arial font file and hash. | Adopted fixed typography must be supported by a measurement/check record. | No repair. The pass-1 evidence gap is closed. |
| note | Scientific scope | The caption defines deliberately supplied asymmetric bounds without a confidence level, model, test, or biological interpretation. Those meanings are consistent with the visible bands and central markers. | Keep this exercise separate from source-measurement reproduction. | Retain the explicit synthetic caption and limited claim. |
| note | Source/statistical verification scope | The supplied QA reports 18 summaries and 36 band endpoints checked with no issues. Source rows were excluded from this review. | Preserve all supplied central values and bounds. | Treat the audit as supplied evidence, not an independent recalculation. |

**Visual repairs needed:** none identified. No mapping, clipping, glyph, legend-fit, or line/band contrast issue is apparent. Successful rendering of this one fixture does not establish generalization to untested datasets.

## Synthetic reproduce transfer — third view

**Name:** `synthetic_reproduce_transfer`. This bounded additional review is appended to the accepted pass-2 main and create-fixture reviews; their conclusions and candidate hashes remain unchanged. The new candidate PNG was actually opened at original detail. Only its supplied `spec.json`, `caption.md`, PNG, and QA record were additionally inspected; no data or code was opened. Its reproduction role is stated in the supplied caption and review task.

The image preserves the adopted reference structure: shared linear elapsed time, blue left and orange right y axes, thin central summary lines with tiny filled sampling markers, pale supplied-SD bands behind both lines, no top spine, inward ticks, and no standalone legend. New labels `Width variant (a.u.)` and `Length variant (a.u.)` correctly avoid claiming measured cell dimensions. Six visibly irregularly spaced summary markers per series agree with the supplied 12-row check record. Both colored titles and all ticks are complete and readable; there is no clipping, crowding, incidental dark marker outline, or line/band contrast problem.

The blue curve rises and then declines slightly late, while the orange curve dips early and rises later. Their sparse straight segments and broader numerical ranges visibly differ from the original dense time course. These shapes are appropriate to this explicitly synthetic fixture; the reference structure does not require copying source values.

| Severity | Location | Evidence | Requirement | Action |
|---|---|---|---|---|
| note | Field/category transfer scope | The supplied specification uses `elapsed_min`, `reported_center`, `axis_quantity`, and `reported_sd`, with `Width variant` and `Length variant` categories. Its caption explicitly describes synthetic new-data reproduction with changed values and x positions. | Preserve the dual-axis reference structure while applying the supplied new meanings. | No repair. Source/data values were not independently inspected by this reviewer. |
| note | Sparse curves and ranges | Two sets of six visible summary-time markers, more angular segment/band boundaries, and the adopted left 0.75–1.45/right 1–7 ranges differ from the source crop. | No smoothing or invented observations; all supplied summaries and SD bounds remain present. | No repair. Treat these as new-data differences rather than reproduction failures. |
| note | Scientific scope | Caption identifies constructed fixtures, independent labelled y scales, supplied SD bands, and no biological experiment, fit, test or sample-count assertion. | Keep synthetic reproduction distinct from Shi source measurements and the separate create exercise. | Retain the explicit synthetic caption. |

**External checks:** direct PNG metadata confirms 1181 × 898 pixels at 300 DPI. Supplied QA measures 17 actual visible text objects as Arial 8 pt with the same no-fallback Arial file/hash as the accepted cases; reports approximately 100 × 76 mm PDF/SVG dimensions and editable SVG text; and reports 12 summaries, 2 curves and 24 band endpoints checked without issues, with unchanged source. These numerical and vector-export records were inspected but not independently recalculated or opened. No PDF-derived small-page preview was supplied for this new fixture; exact font and canvas requirements are nevertheless supported by its supplied measurements.

**Residual differences:** the adopted larger relative plot region, compact fixed typography and right-title rotation match the accepted main adaptation; sparse constructed x positions, new names/units, numerical ranges, and trajectories reflect the supplied synthetic fixture. The candidate's approximate plot bounds are [0.111, 0.026, 0.912, 0.869]. **Status:** `ready_with_notes`; no required repair remains.

## Numerical and export checks

| Candidate | Check | Status | Evidence and limits |
|---|---|---|---|
| Main | PNG dimensions/resolution | passed | Direct PNG inspection: 1181 × 898 pixels, 300 DPI; consistent with the 100 × 76 mm canvas after raster rounding. |
| Transfer | PNG dimensions/resolution | passed | Direct PNG inspection: 1181 × 898 pixels, 300 DPI; consistent with the 100 × 76 mm canvas after raster rounding. |
| Main | PDF/SVG physical canvas | passed | Supplied QA records PDF and SVG dimensions approximately 100 × 76 mm. Those exports were not opened in this review. |
| Transfer | PDF/SVG physical canvas | passed | Supplied QA records PDF and SVG dimensions approximately 100 × 76 mm. Those exports were not opened in this review. |
| Both | Editable SVG text | passed | Supplied QA records `text_preserved: true`. SVG font availability on an assembly system remains the recorded dependency. |
| Main | Numerical source-to-artist audit | passed | Supplied QA: 120 summaries, 2 curves, 240 band endpoints, no issues, source unchanged. Not independently recalculated here. |
| Transfer | Numerical source-to-artist audit | passed | Supplied QA: 18 summaries, 3 curves, 36 band endpoints, no issues, source unchanged. Not independently recalculated here. |
| Both | Clipping/glyph/label overlap | passed | Actual images show complete readable labels; supplied QA lists no clipped text, missing glyphs, or overlapping tick labels. |
| Main | Axis assignments and intervals | passed | Visible colored left/right axes and caption agree with the adopted width/length and mean ± SD meanings. |
| Transfer | Axis/legend assignments and intervals | passed | Visible log x, shared y, literal ordered categories and caption agree with the synthetic supplied-bound specification. |
| Both | Actual Arial 8 pt typography | passed | Updated supplied QA measures all actual visible text objects after final layout as Arial 8 pt, with no-fallback font resolution to `/System/Library/Fonts/Supplemental/Arial.ttf`, SHA-256 `525979822591a3447cfc49d943d6f7683508e25543407871c0ed8fed05fd2bd9`. This reviewer did not inspect the font binary or code. |

## Final-candidate identifiers

- Main PNG SHA-256: `78f5e70686010bccf03787abb0391cb34f5ff7a3689d313bf6957a99216ed343`.
- Synthetic transfer PNG SHA-256: `4c40bbbf7771e8ac2966ba3671db920c1dd60e039ecf07dac7b00ef28ee7bb1e`.
- Synthetic reproduce transfer PNG SHA-256: `105af92702af60bb16c76ff4170140930023911c26d2a48684bcb2507affba56`.

These hashes were calculated directly from the final PNG files actually inspected in pass 2 and its bounded third-view extension.

## Readiness

- **Main:** `ready_with_notes`; no visual or evidence repair remains.
- **Synthetic transfer:** `ready_with_notes`; no visual or evidence repair remains.
- **Synthetic reproduce transfer:** `ready_with_notes`; no visual or evidence repair remains.
- **Overall:** `ready_with_notes`. Required checks pass within the permitted inputs. Residual reference differences are documented and do not change the scientific meanings. Exact source values and statistics were not recalculated by this reviewer; those are supported by the supplied source-to-artist audit. Publication suitability and untested generalization are outside this conclusion.
