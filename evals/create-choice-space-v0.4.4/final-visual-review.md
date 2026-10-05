# Revised independent visual review

This is visual pass 2 of the bounded Create implementation probe. The six revised quartile and density PNGs in `final-outputs/` were opened individually and compared with their previously opened initial versions. The other eight PNGs were independently checked byte-for-byte against their initial versions; every pair is identical, so their documented first-pass observations are carried forward. All 14 current PDFs were independently inspected again for page size and extracted text typography. The adopted input specifications and captions remain those read in pass 1.

The probe concerns 165 synthetic rows and local implementation/constraint behavior. It has no accepted publication reference or no-skill/model comparison. Repairing a visible failure demonstrates this repair on these files; it does not establish aesthetic superiority, generalization, model effectiveness or publication acceptance.

| Case | Review method | Findings | Status |
| --- | --- | --- | --- |
| Quartiles | All three current PNGs actually reopened | The raw observations are now visibly separated, occupy a broader side lane and remain associated with their own labeled categories. Quartile locations and medians remain visible across the three distinct color-role choices. The summaries have become unusually narrow: their vector box width is about 0.912 mm, narrower than the 1.222 mm raw-point diameter. This is a remaining geometry limitation. | `ready_with_notes` |
| Density | All three current PNGs actually reopened | The raw observations now spread into multiple separated columns. Points remain clearly associated with each violin and do not visibly cross its contour. Outer density, inner quartile summary and median remain distinguishable; the expanded category spacing accommodates these layers without squeezing them together. | `ready` |
| Means | Both current PNGs byte-identical to opened pass-1 images | Filled versus open summaries remain distinct, with readable raw repeats and sample-SD intervals. The first-pass findings apply without a new aesthetic comparison. | `ready` |
| Matrix | All three current PNGs byte-identical to opened pass-1 images | Sequential blue/teal decoding and right/bottom guide organization remain readable, with the same cell annotations and global 0–50 limits. | `ready` |
| Coordinates | All three current PNGs byte-identical to opened pass-1 images | Category mapping and filled/open glyph alternatives remain visible and legend-consistent. The second filled route reassigns the same three hues; better category separation has not been demonstrated. | `ready` |

## Remaining findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| minor | Quartiles, all routes, summary geometry | Four filled summary rectangles independently measured in candidate 01's PDF are 0.91182 mm wide, while its raw points are approximately 1.22206 mm across. The outlines and medians are still distinguishable in the reopened PNGs, but the summaries visually read as narrow strips. | The bounded probe requires readable unchanged summaries and observations. This finding does not invalidate their numeric positions, but it limits any claim of refined boxplot proportion. | For future layout improvement, preserve a useful summary width while jointly solving the point-lane anchor and spread. Do not make zero point overlap the only design objective or enforce this narrow box width as a universal Create template. |
| note | Coordinates, route comparison | The same three-hue set is reassigned in route 02 with a matching legend. The current PNGs exactly match the already opened initial PNGs. | Describe the implemented alternative accurately. | Call it an alternative categorical mapping, without claiming improved discriminability or scientific organization. |

## Checked and unchecked evidence

- **Passed independently:** all eight unchanged PNG pairs are byte-identical; all 14 current PDFs have exactly one page and dimensions approximately 79.9999995 × 70.0000016 mm; extracted text spans use `ArialMT` at 8.0 pt. These sub-micrometre dimensional differences reflect numeric representation.
- **Passed by actual second-pass observation:** revised quartile and density raw points are visibly separated and associated with their categories; no new label clipping, raw-to-summary crossing, raw-to-contour crossing or contradictory category decoding was found in the six reopened PNGs.
- **Passed from current supplied technical records:** revised point layouts have zero circle overlaps and spacing violations; source-to-artist records retain numeric values, marker areas, summaries and the adopted scientific settings. These records were inspected but their numerical algorithms were not independently recomputed for this visual review.
- **Carried forward through verified byte identity:** visual judgments of the means, matrix and coordinate PNGs from pass 1. Current PDFs were measured anew rather than assumed identical.
- **Not checked:** physical printing, font-subset embedding, color-vision accessibility, suitability of statistical methods beyond the adopted captions, untested inputs, model or causal effectiveness and publication-level aesthetics.

Compared with the initial failed raw layouts, the revised quartile and density files are preferred **for the specific task of distinguishing every raw observation**. The unusual box-summary width remains an explicit limitation. There is still `no_clear_preference` among the color-role alternatives in each case, and no aesthetic winner is declared.

Overall status: **`ready_with_notes`** within the bounded functional/readability scope. Initial failures remain preserved in `outputs/` and `initial-visual-review.*`; the current box-width note must not be omitted from any claimed result.
