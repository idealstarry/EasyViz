# Annotated heatmap recipe

A single integrated inhibition panel with a square matrix, row and column means, and binary annotation strips. The original development dataset is excluded from this recipe; provide your own source data.

```sh
python /path/to/annotated-heatmap/plot.py \
  --data matrix.csv --genome genome-status.csv \
  --settings /path/to/annotated-heatmap/settings.json --out output
```

| Input or setting | Contract |
| --- | --- |
| `matrix.csv` | First column `sender`; remaining headers are receiver IDs. Unique row/column IDs with matching sets; finite growth-delay values in minutes, including negative values. |
| `genome-status.csv` | `strain,genome`, one row per strain; `genome` is 0 or 1. All IDs are strings. |
| Selection | Choose `selection_count` from 2 to the number of strains. Rows and columns are ranked separately by full-matrix means, then selected at evenly spaced ranks. This is not random or representative sampling. |
| Mean tracks | Each selected row/column mean uses all partners in the full input matrix, including supplied self-pairs. |
| Layout | Canvas, track rectangles, and text anchors are configured in mm. The supplied geometry is tuned for 20 × 20 at 180 × 160 mm. Adjust placements and inspect if the size or density changes. |
| Typography | Text size and font are configurable; defaults use 8 pt throughout, with no panel title. |
| Scales | Set color limits to cover the complete data range. The supplied `two_slope` normalization requires `color_center=0` strictly inside them; zero is white, negative values blue, positive values gold/orange/coral. Remove optional mean limits/ticks to derive them from data; explicit limits may not clip bars. |
| Output | PDF, editable-text SVG and PNG, plotting data, full summaries, resolved settings and numeric/export QA. `dpi` controls raster resolution. |

Use the runtime dependencies in `../../../scripts/requirements.txt`. The script can reject invalid input or clipped text; inspect the result for overlap and visual balance. Changing the canvas does not automatically adjust every millimeter anchor. Reposition the chart elements while preserving the requested font sizes.

This implementation was written for EasyViz using source data rather than author code. For other measurement semantics or annotations, adapt the field names, units, labels, and calculations explicitly. The recipe's default scale and selection are starting settings, not biological recommendations.

Put narrative and method details in a separate caption, using [caption-template.md](caption-template.md) as a starting structure. Replace every placeholder with the actual input and selection details. The recipe does not draw an overall title, sample-count overview or explanatory footnote.

## Explicit scale and style

The default signed growth-delay scale uses `TwoSlopeNorm(vmin=-400, vcenter=0, vmax=1000)`. For raw minutes `x`, `u=(x+400)/800` at/below zero and `u=0.5+x/2000` at/above zero. Its inverse is `x=-400+800u` at/below normalized 0.5 and `x=2000(u-0.5)` at/above it. This is piecewise linear, with different slopes on the two sign branches; it is not globally value-linear over the asymmetric range. The same norm controls colorbar positions and inverse readout. Every full-input value must fall within the limits, or the recipe fails before rendering. Resolved settings/QA save the actual formulas and ordered inverse checks. `colorbar_ticks` are raw minutes; when a transfer changes limits, in-range configured ticks are retained together with endpoints and the center.

Zero is adopted as a meaningful neutral growth-delay reference in this recipe. For another measurement without that meaning, explicitly choose `color_normalization="linear"` and an appropriate color map; do not borrow a neutral center solely for appearance. For another signed domain, set both bounds and the declared center deliberately. The blue/white/gold/orange/coral colors are newly chosen EasyViz adaptations after inspecting PROGENy Fig. 2b/c, scWAT Fig. 2b, and Vanneste Fig. 4d, rather than exact publication samples.

Explicit `color_stops` take precedence over the plain `colormap` color list and store normalized positions. The defaults are −400/#4B9BDD, −200/#B8DCFA, 0/#FFFFFF, 100/#FFF0B5, 250/#FFD168, 500/#FF995D, and 1000/#F24E55 in original-minute readout. Interpolation is continuous, with no binning or additional data transform. The enabled `check_branch_luminance` validates 1,025 actual color samples: brightness increases toward zero from the negative end and decreases from zero toward the positive end. It rejects a nonordered branch. This does not certify perceptual uniformity. If adopting an explicit linear scale instead, remove this branch-specific check.

Means retain separate quantitative axes and opaque sky-blue bars. Genome metadata uses charcoal filled and white outlined tiles with matching guide keys. White binary tiles have a purposeful 0.45 pt charcoal border; mean bars are borderless. Supporting grids are disabled. The 180 × 160 mm / 8 pt Arial defaults are retained; the bottom-right colorbar is widened to show zero and intermediate positive levels.

A fully synthetic [4 × 4 fixture](synthetic/README.md) and its reviewed full-canvas outputs exercise this contract without the excluded development dataset. It contains invented values, no biological observations, and no scientific claims.
