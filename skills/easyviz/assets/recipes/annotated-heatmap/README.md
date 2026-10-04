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
| Scales | Set color limits to cover the complete data range. The default is one globally linear, single-hue ramp. `mean_scale="shared"` uses common numeric limits and ticks for both mean tracks; remove `mean_limits`/`mean_ticks` to derive them over both tracks. Explicit limits must include zero and every bar. Optional `independent` mode retains role-specific bounds. |
| Output | PDF, editable-text SVG and PNG, plotting data, full summaries, resolved settings and numeric/export QA. `dpi` controls raster resolution. |

Use the runtime dependencies in `../../../scripts/requirements.txt`. The script can reject invalid input or clipped text; inspect the result for overlap and visual balance. Changing the canvas does not automatically adjust every millimeter anchor. Reposition the chart elements while preserving the requested font sizes.

This implementation was written for EasyViz using source data rather than author code. For other measurement semantics or annotations, adapt the field names, units, labels, and calculations explicitly. The recipe's default scale and selection are starting settings, not biological recommendations.

Put narrative and method details in a separate caption, using [caption-template.md](caption-template.md) as a starting structure. Replace every placeholder with the actual input and selection details. The recipe does not draw an overall title, sample-count overview or explanatory footnote.

## Explicit scale and style

The supplied single-hue sky-blue scale uses `Normalize(vmin=-400, vmax=1000)`: `u=(x+400)/1400`, with inverse `x=-400+1400u`. Zero is a labeled measurement at `u=2/7`, not the white midpoint. These limits cover the development case's complete range; replace them to cover the complete range of your own input. Every value must fit, or the recipe fails. The mapping is numerically linear; this does not certify perceptual uniformity.

`colorbar_ticks` are original-unit values positioned through the same normalization. Explicit `color_stops`, when supplied, take precedence over `colormap` and must have increasing coordinates from 0 to 1. Do not use arbitrary colorful stops as scientific thresholds. Optional `two_slope` remains available around an explicitly meaningful `color_center`; its asymmetric slopes must be declared rather than described as one common linear scale.

`mean_scale="shared"` is the supplied default. `mean_limits`/`mean_ticks` set one numeric range for both tracks; omit them for automatic shared bounds over all displayed means. Shared mode rejects conflicting role-specific bounds. `mean_scale="independent"` permits the existing `sender_mean_limits`/`receiver_mean_limits` and corresponding ticks. All bounds include zero and all bars, and ticks must increase inside them. The axes have different physical lengths/orientations: equal numeric limits do not imply equal physical bar-length scaling.

For the development GII measurement, positive values mean delayed attainment time and negative values earlier attainment; the original paper calls values >300 min inhibition. Do not infer a significance test or threshold for another measurement from these colors. Adapt units, definitions and supported inference from the actual input.

Opaque sky-blue means and charcoal/outlined-white metadata keep their own guides. Supporting grids are disabled. Text remains 8 pt on the 180 × 160 mm canvas. The full bottom-right guide is checked after rendering; numeric range checks alone do not establish readability.

A fully synthetic [4 × 4 fixture](synthetic/README.md) and its full-canvas outputs exercise this contract without the excluded development data. They contain invented numbers and support no biological claim.
