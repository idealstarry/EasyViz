# Visual review of the independent viscosity trial

Status: reviewed with residual readability observations, not an unqualified visual pass. This is a newly authored synthetic forward trial, not a real viscosity experiment. The declared unit is one independently prepared sample measured once; independence was adopted from the trial definition and not inferred from the table. No inferential statistics were requested or computed.

Reviewed actual PNG exports plus independently rasterized PDF and SVG exports at nominal 96 dpi, corresponding to 110 × 80 mm (about 416 × 303 pixels). This provides a reproducible final-size reading check; the viewing tool does not establish calibrated monitor or printed physical size. Contact-sheet labels are outside the scientific panels.

All axes, group labels, units and ticks are readable in the reviewed rasters. No title, explanatory count text, missing glyph, cut-off label or legend collision was observed. Arial is the recorded actual font without substitution; axis/tick/legend roles remain 8 pt in every alternative. Each PDF is one 110 × 80 mm page. The SVG and PDF rasters match the visible mark layout of the PNGs; their anti-aliasing differs.

## Box and every point

The equal 8.4 mPa·s medians and compact A/C versus broad B spreads can be compared directly. All observations remain visible, including C's isolated high measurements at 10.5, 12, 14.5 and 16 mPa·s. Beeswarm spreads the clustered ties in the categorical direction without changing quantitative x positions or point size. There are 17/19/21 points, zero audited circle overlap/spacing/boundary issues and no packing fallback.

Residual: A/C's thin black median strokes at 8.4 mPa·s are partly covered by the opaque raw-point row. Their upper/lower ends remain visible, but the central stroke is less distinct at the final-size reduction. B's median remains clear. This was reported to the parent and preview author; the original outputs remain intact. This observation motivates a separately reviewed refinement, not a hidden change to this trial.

## ECDF

The unsmoothed steps show B's broad lower and upper spread and C's upper tail clearly, using the same linear 4–17 mPa·s measurement axis and fixed category colors. The lower legend is readable and inside the unchanged canvas. At the shared median and nearby compact values, blue and green steps locally coincide; the tail segments distinguish them, but exact central curve identity requires tracing from the colored segments. No interpolation, confidence band or fitted distribution is implied.

Each group's denominator is its own 17, 19 or 21 observations. The exported tied-value jumps, cumulative fractions, source-row membership and actual SVG step vertices were independently checked against the complete source values. Fractions answer a threshold/tail reading task more directly than the box summaries.

## Explicit opt-in violin and every point

Eligibility was confirmed from the source: A/B/C have 14/19/17 distinct values. The violin shows a compact blue shape, broad orange shape and a thin long green upper tail. The raw points make the sparse green high-value measurements visible. Labels and points fit at the same canvas, font, axis range and colors as the default alternatives.

Scott-bandwidth Gaussian KDE visibly smooths the sparse tail and fills space between observed measurements. Each violin width is independently normalized, so width is neither sample count nor uncertainty. Five distinct values is a guard, not a density-reliability claim. This view is useful for a broad smoothed-shape question, while exact medians and tail fractions are read more directly from the box and ECDF, respectively.

## Choice by reading task

For a median/spread comparison, use the box with every observation, while addressing the recorded median-stroke readability issue in a fresh attempt. For observed tails and fractions at or below a threshold, use the ECDF; it avoids KDE assumptions and shows all tied jumps. The optional violin is a smoothed-shape supplement when that reading task is explicit. There is no universal winner, and this review leaves `selection.chosen_choice=null` and `automatic_winner=false`.

This trial ran no alternative tool, author-code baseline or usability timing comparator. It supports only the reported forward execution, retention, geometry and visual observations for these synthetic inputs.
