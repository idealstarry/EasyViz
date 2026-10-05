# Independent visual review — pass 1

Reviewer role: independent figure reviewer. I opened the actual candidate and both whole-canvas nominal final-size previews before assessing it. I did not author the candidate, inspect plotting implementation, or read other trials. This is a Create panel; no reference or baseline comparison is required.

Specification inspected: `adopted-specification.md`, `attempt-01-spec.json`. Caption inspected: `caption.md`. Measurement records inspected: `qa/attempt-01/actual-checks.json`, `attempt-01/qa.json`. Actual exported SVG styles were read only to confirm palette identity.

## Image packet identity

| Opened image | SHA-256 |
| --- | --- |
| `attempt-01/panel.png` | `14b469df0ce756d3458b757f9006fa297a0a47aa180c502490024dde971c6329` |
| `qa/attempt-01/png-96dpi.png` | `2006fbf95b22783464bf6f5f795f0f637b6c8f5f84b02da844bc9831af37c0e0` |
| `qa/attempt-01/pdf-96dpi.png` | `4016b7fa16bc7ae390a4b38284e881e868b96b7910964f41c97aaaad2995fb96` |

Hashes were computed by this reviewer. The 96 dpi images were inspected as whole canvases, not isolated crops. They provide nominal screen proportions; calibrated physical print inspection is unavailable.

## Independent image observations

Vehicle, Dose 1, and Dose 2 appear in the requested order. The linear axis, unit label, colored outline boxes, black medians/whiskers, and opaque borderless specimens match the adopted mapping. Bright blue, coral, and teal remain distinguishable against white; colored box edges and black summaries remain visible in both 96 dpi previews. Labels are legible, unclipped, and well separated; no title, prose, inferential annotation, grid, or duplicate legend appears. The full canvas is retained with room around its extreme points and text.

The visible dots preserve within-arm value variation without suggesting pairing or density. The separate caption explains technical averaging, independent units, group counts, quartiles, whiskers, horizontal displacement, lack of tests, units, and synthetic-fixture provenance. It does not introduce an unsupported biological claim or figure number.

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Point/summary crossings, especially Vehicle quartile edges and median, Dose 1 upper box edge, and endpoint caps | In the full candidate and both 96 dpi views, opaque dots cover short portions of summary lines. Remaining segments identify the quartiles, medians, and caps; no summary becomes unreadable. | Show all specimens together with readable box summaries. | No revision required. Retain this intentional crossing; avoid a change that obscures specimen dots. |
| note | Physical-size inspection | Whole-canvas 96 dpi previews are available, but the display/print scale is not calibrated. | Evaluate intended proportions using available final-size evidence. | No required correction. A calibrated printed proof remains an optional final-production check. |

No critical, major, or minor requirement failure was found in the inspected packet.

## Numerical and export checks

These are supplied measurements, not conclusions established by the screenshots or independently recalculated by this reviewer, except for palette styles and image hashes explicitly identified above.

| Check | Status | Evidence |
| --- | --- | --- |
| Independent-unit preparation and all points | passed | `actual-checks.json`: 66 reads grouped by arm + ID into 33 units, counts 9/13/11, exact unit set, no duplicate units, maximum mean error `7.11e-15`, preserved numeric y. `qa.json` records 33 placed rows. |
| Quartiles, medians, whiskers | passed | Supplied independent recomputation differs from the preparation audit by at most `3.55e-15`; actual saved SVG summary geometry differs by at most `8.89e-8 nmol/min`. |
| Point separation and horizontal bounds | passed | `qa.json`: 0 overlapping-circle pairs, 0 gap violations, minimum center distance 3.3 pt, maximum offsets below 4 mm; the full image visibly separates close dots. |
| Whole-format dimensions | passed | Supplied measurements: PDF approximately 110 × 88 mm, SVG approximately 110 × 88 mm, PNG 1299 × 1039 px at approximately 300 dpi. |
| Actual typography | passed | Supplied PDF spans are 8 pt ArialMT, embedded font bytes are present, SVG text references Arial, and substitution is false. |
| Actual line and point sizes | passed | `qa.json` records summary strokes 0.75 pt, axes/ticks 0.55 pt, and dot spans 1.0583 mm (3 pt). Visual inspection supports their visibility at the provided proportions. |
| Exact palette identity | passed | Reviewer inspection of actual SVG fill/stroke styles finds `#29ACF3`, `#E47751`, and `#007F7F`; independent image observation supports their distinction. |
| Text, inference, and caption consistency | passed | Supplied SVG/PDF text contains only required axes, units, ticks, and categories; saved statistics method is `none`. Image and caption agree. |
| Calibrated physical print | not_checked | Unavailable. Actual mm/font measurements and 96 dpi whole-canvas previews are available. |

Residual issues: short summary segments lie under dots as documented above, and calibrated print inspection remains unavailable. Neither requires changing this panel on the evidence provided. No aesthetic improvement over a baseline or generalization to other datasets is claimed.

Overall status: **ready_with_notes**
