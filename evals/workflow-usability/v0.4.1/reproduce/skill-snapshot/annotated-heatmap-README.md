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
| Scales | Set color limits to cover the complete data range. Remove optional mean limits/ticks to derive them from data; explicit limits may not clip bars. |
| Output | PDF, editable-text SVG and PNG, plotting data, full summaries, resolved settings and numeric/export QA. `dpi` controls raster resolution. |

Use the runtime dependencies in `../../../scripts/requirements.txt`. The script can reject invalid input or clipped text; inspect the result for overlap and visual balance. Changing the canvas does not automatically adjust every millimeter anchor. Reposition the chart elements while preserving the requested font sizes.

This implementation was written for EasyViz using source data rather than author code. For other measurement semantics or annotations, adapt the field names, units, labels, and calculations explicitly. The recipe's default scale and selection are starting settings, not biological recommendations.

Put narrative and method details in a separate caption, using [caption-template.md](caption-template.md) as a starting structure. Replace every placeholder with the actual input and selection details. The recipe does not draw an overall title, sample-count overview or explanatory footnote.
