# Independent legend-transfer visual review

I opened the contact sheet and all 20 original before/after PNGs for the ten cases in `manifest.json`. The contact sheet was used only for orientation; the findings below come from the individual originals requested with original image detail. I also inspected the saved measurements, original sources/specifications, and actual SVG exports. No renderer implementation was read or edited for this review.

Nine feasible after panels are visually ready. The intentionally impossible 88 × 32 mm panel is **needs_revision** and must not be delivered as aesthetically ready. Its expected rejection is a successful benchmark behavior, not a successful panel layout.

## Case findings

| Case | After panel status | Original-image evidence and before/after comparison |
| --- | --- | --- |
| `categorical-2-short-88` | ready | Both complete labels remain outside the plot. The reduced symbol-to-label gap and row spacing make the key compact without crowding. |
| `categorical-4-long-132` | ready | The before original clips long labels at the right edge. The after original has all four complete labels in a single row above the plot, with clear symbol association and no clipping. |
| `categorical-8-short-180` | ready | All eight entries remain readable in the right margin. The after key is shorter and narrower; it does not intrude on plotted marks or axes. |
| `categorical-8-long-180` | ready | The before original clips the longest right-side labels. The after original has eight complete entries in four columns and two rows above the plot. The columns and rows are distinct, and the legend does not collide with the plot. The measured 132.64 × 6.30 mm occupied box fits this 180 × 108 mm canvas. |
| `colorbar-landscape-132` | ready | The shorter, thinner after colorbar keeps a readable Fraction label and 0, 0.5, 1 scale. The low-to-high color direction and heatmap cells remain unchanged. |
| `colorbar-square-88` | ready | The after colorbar has clear ticks, a complete label, and sufficient separation from the heatmap and canvas edge. Its compactness does not make the scale ambiguous. |
| `dot-small-88` | ready | The Fraction colorbar and Count size key are distinct and nonoverlapping. The Count entries 2, 10, 20 remain individually legible. The size symbols retain the same physical sizes as before; compactness comes from spacing and guide placement. |
| `dot-large-132` | ready | The larger 20, 100, 200 size symbols fit without touching each other, their labels, or the colorbar. The after layout uses less empty guide space while preserving visibly different sizes and the corresponding plot marks. |
| `manual-categorical-132` | ready | The after original uses the requested two-column legend above the left side of the plot. The measured legend lower-left corner is exactly (18, 76) mm. The before original uses a right-side column and does not honor that override, despite its generic renderer pass status. |
| `impossible-8-long-88` | needs_revision | The after original clips the legend above and beyond the canvas and clips the Score X title below it. Moving the guide changes where clipping occurs but does not solve the fixed-footprint conflict. The saved after status correctly remains needs_revision. |

## Actionable findings and limits

| severity | location | evidence | requirement | action |
| --- | --- | --- | --- | --- |
| major | `impossible-8-long-88/after/panel.png`, legend and bottom axis title | Complete category decoding is unavailable in the image: the legend extends beyond the top and both sides; Score X is cut at the bottom. The saved legend box is approximately [-24.08, 30.16, 132.64, 6.30] mm on an 88 × 32 mm canvas. | Do not hide entries, shrink 8 pt type, expand the fixed canvas, or report an impossible footprint as ready. | Retain needs_revision and the diagnostic candidate. A publishable panel requires a separately approved change to the footprint or content/layout constraints. |
| note | Categorical keys | All categorical entries use equal-sized filled symbols; their compact after symbols need not encode the numeric areas of the plotted scatter points because no size variable is mapped. | Compact categorical decoding must not imply a quantitative size scale. | No correction required. Keep this distinction from the exact quantitative dotplot size keys. |
| note | Benchmark scope | The source fixtures, labels, font, and canvases are specific to these ten cases. Image inspection is not a physical print proof or a guarantee for arbitrary inputs. | Report supported transfer behavior and limitations honestly. | Restrict acceptance claims to these cases. |

No critical, major, or minor visual defect was found in the nine feasible after candidates. Their complete labels, scales, keys, and marks are readable in the opened originals; no legend/plot or legend/legend collision was visible. Compactness ratios were treated as descriptive measurements, not universal aesthetic thresholds.

## Numerical and export evidence

| status | check | evidence and independence |
| --- | --- | --- |
| passed | Actual fonts and dimensions | I directly parsed all 20 SVG exports: each retains Arial at 8 user units in point-sized viewBox coordinates, and each before/after pair has identical dimensions matching its manifest canvas. All 20 PNG headers likewise show identical within-case pixel dimensions. |
| passed | Source and data preservation | I independently hashed each source CSV and matched both measurement records. Counts match the manifest. I compared source scatter coordinates by group, heatmap values by row/column, and dotplot count-area/color mappings with the recorded artists; all agree. The complete recorded data-artist structures are identical before and after in every case. This is a check against recorded artist data, not direct recovery of every plotted value from raster pixels. |
| passed | Quantitative size mapping | For dot-small, Count 2, 10, 20 maps to 3.6, 18, 36 pt²; for dot-large, 20, 100, 200 maps to 14.4, 72, 144 pt². I independently read the three gray circular paths in each actual after SVG. Their diameters are approximately 1.897367, 4.242641, 6 pt and 3.794733, 8.485282, 12 pt respectively, matching the supplied mapping to within 0.001 pt. No marker transform rescales them. |
| passed | Raster size-key evidence | The supplied actual-size export checks report matching PNG gray-ink extents within their 2.5 px antialiasing tolerance for both dot cases, before and after. I visually inspected the originals and independently verified SVG diameters; I did not rerun the PNG ink-isolation routine. |
| passed | Plot and guide geometry | Plot rectangles are identical before and after for all cases. I recomputed rectangle intersections from the measured boxes and found no after guide/data-rectangle or guide/guide intersection. The nine feasible cases also report no clipped text or tick overlaps, consistent with the images. |
| passed | Manual position | The supplied explicit lower-left anchor (18, 76) mm and two columns match the after measured box and visible arrangement. The baseline does not honor the override. |
| passed | Honest failure status | The impossible case keeps its 88 × 32 mm canvas, 8 pt SVG text, source values, and needs_revision status. Its visible clipping is not concealed by a benchmark pass label. |
| not_checked | Other inputs and physical print | No arbitrary-input guarantee, color-vision simulation, physical print proof, caption review, or independent renderer-code audit was performed. These are outside this legend-transfer inspection. |

## Actual paths opened

The following top-level files were opened:

- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/contact-sheet.png` — documentation thumbnails only; displayed at reduced resolution.
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/manifest.json`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/results.json`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/results.md`

For **each exact directory below**, I opened `before/panel.png` and `after/panel.png` individually at original detail, and read `before/panel.svg`, `after/panel.svg`, `before/measured-geometry.json`, `after/measured-geometry.json`, `source.csv`, and `spec.json`. This enumerates the original-image and supporting-file paths; the PNG judgments do not rely on the contact sheet.

- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/categorical-2-short-88/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/categorical-4-long-132/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/categorical-8-short-180/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/categorical-8-long-180/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/colorbar-landscape-132/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/colorbar-square-88/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/dot-small-88/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/dot-large-132/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/manual-categorical-132/`
- `/Users/starry/Desktop/EasyViz/evals/legend-transfer/cases/impossible-8-long-88/`

The review criteria were previously read from `/Users/starry/Desktop/EasyViz/skills/easyviz-figure-reviewer/SKILL.md`; that file was not reread for this benchmark. This review changed only `evals/legend-transfer/visual-review.md`.

**Status: needs_revision for the intentionally impossible candidate.** The nine feasible after panels are ready, and the observed outcomes match all ten declared benchmark expectations.
