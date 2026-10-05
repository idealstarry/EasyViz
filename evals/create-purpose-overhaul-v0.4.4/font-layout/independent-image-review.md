# Independent image review: known font/layout regression

Reviewed 2026-10-05 by the independent figure-review agent. This is an engineering check of a known synthetic regression, not an unseen first-draft evaluation, an aesthetic comparison, or evidence that EasyViz improves scientific figures in general. The release draft remains held.

## Scope and identity

Read `diagnosis.md`, `diagnostic-context.json`, the six case manifests, and the eight inspected routes' specifications, geometry evidence and QA records. Opened every PNG listed below as an actual image, in its complete exported aspect ratio. The vertical canvases are 80 × 70 mm and the horizontal canvas is 70 × 80 mm. Most PNGs are 315 × 276 pixels at approximately 100 dpi; the 160 dpi route is 504 × 441 pixels, and the horizontal route is 276 × 315 pixels. These dimensions establish the adopted proportions; the screen display is not a calibrated physical print measurement.

There are only PNG and SVG exports here. Visual findings below come from the PNG pixels. SVG identity, declared physical size, viewBox and preserved-text metadata were checked; the SVGs were not separately rendered for this review. No PDF was available or reviewed, and no PDF export behavior is verified by this record.

Both frozen owner snapshots match the corresponding current files and the SHA256 values in `diagnostic-context.json`:

| File | SHA256 |
| --- | --- |
| `skills/easyviz/scripts/create_candidates.py` | `44f644c95f6ea92d219dd98d1933b78f1dc5ef084e4c14d342a86155a69d4950` |
| `tests/test_create_candidates.py` | `ce423eea849a00179919ac0496848a67b1b4cf25d55c19e8e79f128c8e9d217b` |

This verifies the two named files, not the complete runtime dependency closure. All six source and source-spec snapshot hashes match their manifests. All eight inspected PNG/SVG SHA256 values match their export QA records. No runtime, specification, output or source file was changed by this review.

## Actual image observations

| Inspected case / route | Actual visual finding | Engineering disposition |
| --- | --- | --- |
| `explicit-dejavu/candidate-01` | Four colored box bodies sit at their named category centers; the neutral observations form a distinct adjacent lane to the right. Median strokes, whiskers and caps remain discernible. No raw-point cloud touches the adjacent category or visibly hides its own summary. Axes, category labels and units are complete. | No new visual blocker observed. |
| `explicit-dejavu/candidate-02` | Open neutral boxes remain distinguishable from colored observations. Category identity is readable from position and labels, with the raw lane consistently on the right. No visible clipping or point/summary collision. | No new visual blocker observed. |
| `explicit-dejavu/candidate-03` | Both layers are neutral, but their shape and consistent separation still distinguish the small box from the observation cloud. The four groups stay associated with their labels. | No new visual blocker observed. |
| `arial-present/candidate-01` | Arial changes the text widths and fitted region modestly, without producing a clipped label or a cloud assigned to the wrong box. Box bodies remain narrow but visible at the exported proportions. | No new visual blocker observed. |
| `arial-forced-unavailable/candidate-01` | The actual fallback image is identical to the explicit-DejaVu image by PNG hash. Its displayed summary/raw separation and labels therefore agree with that case. Requested Arial / actual DejaVu is disclosed in the geometry record. | No new visual blocker observed; this is an injected unavailable-font scenario, not proof about every platform fallback. |
| `explicit-dejavu-160/candidate-01` | The higher-resolution raster preserves the four groups, median and whisker strokes, separate raw lanes, and complete labels. It does not introduce a new overlap or clipping defect. | No new visual blocker observed. |
| `horizontal-dejavu/candidate-01` | Categories read top to bottom as Control, Low, Medium, High. Each horizontal box has its own observation lane below it. The numeric x-axis reads 0–10 correctly; no group cloud reaches the next category's box. Axis labels are complete. | No new visual blocker observed. |
| `explicit-locked-margins/candidate-01` | The High cloud has a merged pair near response 6.9. The rest of the panel remains readable, but this pair cannot be treated as two clearly separated circles. Labels and summary/raw separation otherwise remain intact. | **Needs revision as a deliverable panel.** Keep it as the intentional failing regression fixture, not a passed panel. |

All inspected panels omit a legend. Their axis/tick text is readable; there is no legend placement or color-key readability claim to validate here. The three color routes can be read through category position, but this check does not select an aesthetic winner. The narrow summary bodies are still legible in this small synthetic panel; that observation does not establish a broadly suitable summary-width default for other data or final sizes.

## Measurement corroboration and remaining limit

The seven nonlocked inspected routes report all 42 numeric observations preserved at the requested point area, zero point-spacing violations, zero categorical raw/summary envelope crossings, no clipped text and no overlapping tick labels. The minimum center separation is approximately 3.6641 pt for the 3.4641 pt marker diameter and 0.2 pt gap. This agrees with the visible distinct dots and separated layers; it is not itself a beauty score.

The DejaVu case and the injected Arial fallback borrow 0.448964 mm from omitted right-side fit padding. The 160 dpi case borrows 0.316193 mm on that edge, and the horizontal case borrows 0.084465 mm from bottom fit padding. The canvas, 8 pt reading text, numeric limits and quantitative coordinates remain as recorded. Actual image inspection finds no accompanying crop or lost label at these edges. Arial present requires no borrowing.

The explicit locked case borrows nothing and retains `needs_revision`. Its sole measured overlap is between parsed observation rows 33 and 37 (`High-02`, 6.84164; `High-06`, 6.92981). Their 1.3776 pt center separation is smaller than the 3.4641 pt marker diameter. The merged appearance in the High cloud agrees with the measurement. Source-to-artist preservation still passes, which must not be substituted for visual spacing acceptance.

No additional fix is requested from this actual-image pass for the seven inspected valid routes. The locked failure must remain visibly and procedurally failed. This record supports the specific font/layout regression diagnosis and repair only; it supplies no matched-task aesthetic efficacy result, no CNS-level claim and no authorization to release.

## Inspected PNG identities

| Case / route | PNG SHA256 |
| --- | --- |
| `explicit-dejavu/candidate-01` | `16b765cc384b01af7abacba5de190dcba1ebab0518bf0005907ae93666731364` |
| `explicit-dejavu/candidate-02` | `24ea0802382e01c13113e1f645f61b382309d8ade30e9e8df94d43211b028a99` |
| `explicit-dejavu/candidate-03` | `6939d77240d90147efd6e3714240bb09624c707a1fd0a8754947990be4f95138` |
| `arial-present/candidate-01` | `2d024315ec16d141bf7f6f50bb828c89416d5253718d2b71fc3ef4bcf2ecb3c2` |
| `arial-forced-unavailable/candidate-01` | `16b765cc384b01af7abacba5de190dcba1ebab0518bf0005907ae93666731364` |
| `explicit-dejavu-160/candidate-01` | `e20e5394fa1151d29353859448245299a265f95de8193365e32b2359f0a64c5c` |
| `horizontal-dejavu/candidate-01` | `8b29667a01a98b76eb5a88b77904c64d39fc8aec85bebf47c0bcfda931eb32dc` |
| `explicit-locked-margins/candidate-01` | `c704f5f01d3dee0ca62bcd243d1c952502beb8ddd7a8b25d55786112b619b326` |
