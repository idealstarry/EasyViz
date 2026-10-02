# Independent panel review

Candidate: `panel.png`, actually opened and inspected. Create track; no baseline or reproduction comparison is required. The original review was limited to the candidate and `plot.json`, `prepared.csv`, `settings.json`, and `qa.json`. A packet-completeness follow-up reviewed the newly supplied `caption.md` and `checks.json`; the unchanged image was not reopened and no earlier check was repeated. No author code, tests, or evaluation history was inspected.

The panel visibly contains the required 3 × 8 grid, with 22 borderless blue circles and two measured-zero dashes. The category order matches the adopted specification. Labels, legends, and the colorbar are readable without visible clipping or collisions. The light grid stays behind the marks. There are no extra titles, overview counts, explanatory footnotes, or inferential annotations.

| severity | location | evidence | requirement | action |
| --- | --- | --- | --- | --- |
| note | Measured-zero coordinates | Resident macrophages / Control and Cycling myeloid cells / Low dose show gray dashes, matching the supplied zero-state policy. These are separate state glyphs; the quantitative circles retain zero area. | Keep both observed zeros and distinguish them from missing coordinates. | Retain this mapping and explain it in the separate caption. |
| note | Separate caption | The completed caption correctly describes both encodings, the shared 0–1 area scale, observed-zero glyphs, retained zero-row scores, descriptive data, absence of inferential calculations, and the unspecified denominator/preparation method. No invented figure number is present. | Explanatory prose and methodological limitations remain outside the image. | Retain the separate caption. |
| note | Export typography verification | Newly supplied actual-PDF measurements report an embedded ArialMT subset (30,084 font bytes) and exclusively 8.0 pt text. | Arial 8 pt; export verification must have evidence. | Retain the verified export settings. The PDF checks are supported by the supplied independent measurement record and were not repeated by this reviewer. |
| note | Editable SVG | SVG QA states that its editable text references Arial. | Preserve editable text and the requested font. | Use an assembly environment with Arial installed. |

## Numerical and export checks

| check | result | evidence and scope |
| --- | --- | --- |
| Descriptive data completeness | passed | Independently counted 24 CSV rows, 24 unique coordinates, and a complete cross-product of the three treatment arms and eight cell types. |
| Observed zeros | passed | Independently found exactly the two zero fractions shown as dashes. All 22 positive fractions have visible circles. |
| Input-record agreement | passed | Independently computed the CSV SHA-256 and matched it to both settings and QA records. |
| Category order | passed | Visible left-to-right treatment and top-to-bottom cell orders match `plot.json`. |
| Shared area mapping | passed | Specification uses size / 1 × 90 pt². Independent anti-alias-weighted raster measurements of all 22 circles yield approximately 1,219–1,225 pixels of filled area per unit fraction. This variation is under 0.5% and is consistent with a single proportional mapping. |
| Size-key agreement | passed | Independent weighted raster measurements yield about 306.2, 612.4, and 1,224.7 pixels for legend values 0.25, 0.5, and 1.0. Thus the keys share the plotted area scale. Supplied key areas are 22.5, 45, and 90 pt². |
| Prepared-score encoding | passed | Visible blue shades follow the score progression. The colorbar is labeled Prepared score with the specified bounds −0.22 and 1.66; supplied mapped-range record agrees. This is a visual/specification check, not an independent reconstruction of the colormap implementation. |
| Final canvas | passed | Supplied QA measurements report PDF 120 × 90 mm and SVG 120 × 90 mm within numerical precision. The new actual-export check record additionally reports PDF 119.9999966 × 89.9999975 mm and SVG 340.15748 × 255.11811 pt, both passing. Independently read PNG IHDR and pHYs in the first review: 1,417 × 1,063 pixels and 299.9994 dpi, consistent with the requested 120 × 90 mm raster after pixel rounding. PDF/SVG measurements were supported by the supplied records, not independently re-read by this reviewer. |
| Arial 8 pt | passed | Settings report actual Arial without substitution; the new actual-PDF measurement record identifies the embedded `FBLWNS+ArialMT` Type0 font with 30,084 embedded bytes, and the complete text-size set is [8.0] pt. No extra title or panel letter appears. |
| Visual fit and hierarchy | passed | No visible overlaps or clipped labels. Supplied combined guide envelopes are 17.7% of plot area; the data region is 56.8 × 79.9 mm, while the guide enclosure is 21.3 × 52.5 mm. The data remains primary and the continuous colorbar has a readable physical length of 27.9 mm. These measurements describe fit and visible hierarchy, not publication acceptance. |
| Inferential annotations | passed | None appear in the image or adopted plotting specification. Caption explicitly states that no inferential tests or uncertainty estimates were calculated, agreeing with `statistics_none: true` in the new check record. Review scope did not include statistics-engine code. |
| Separate caption | passed | Caption was reviewed in the packet-completeness follow-up. Its mapping, zero-state explanation, descriptive-only interpretation, and stated source limitations agree with the adopted specification and data. |
| PDF font embedding | passed | New independent actual-export check record identifies embedded ArialMT and exclusively 8 pt PDF text. This evidence was inspected rather than its underlying checks being rerun. |
| Additional vector geometry and style | passed | New actual-export check record reports 22 positive PDF dots; proportional area, shared plot/legend scale, color mapping, and absent marker strokes all pass. This supports the original visible/raster findings; it was not repeated by this reviewer. |

No critical, major, or minor panel defect was found. The caption and supplied actual-export evidence are complete. There are no unresolved required items and no visual revision is needed.

Status: **ready**.
