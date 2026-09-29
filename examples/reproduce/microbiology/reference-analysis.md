# Reference reader output

## Observed standard

Reference: article page 4, Figure 1, inspected as a rendered page.

| Feature | Observation |
|---|---|
| Chart | Dense rectangular matrix heatmap |
| Rows and columns | Sender strains in rows; receiver strains in columns |
| Color | Dark purple/black through orange to yellow for increasing GII |
| Labels | Row labels on the left, vertical column labels at the top |
| Annotations | Narrow gray/white genome-status strips beside both axes |
| Colorbar | Small vertical GII (min) scale on the right |
| Clustering | No visible dendrogram |
| Composition | One matrix with annotation strips and colorbar |

## Supporting author code

The supplied `09_R_C.malt_Graph_pub.rmd` section `NESTEDNESS STRUCTURE` constructs a ComplexHeatmap plot with `inferno(100)`, disabled row/column clustering, sender rows, receiver columns, and genome-availability annotations. The exported original canvas is 17 × 17 inches; its text sizes are therefore unsuitable for direct reuse at the final physical size here.

## Adaptation decisions and uncertainty

- Adopt the chart structure, orientation, palette family, annotation semantics, and top/left label positions.
- Select a documented 12 × 12 view spanning sorted ranks, rather than squeeze 76 labels into a small panel. This is not an exact crop of Figure 1 because ordering is recomputed with the convention below.
- Recompute sender degree over **all 76 receiver columns**. The supplied Rmd's sender-degree loop sums columns `2:ncol(mat_df_bin)` after the identifier has already been removed, excluding the first receiver. This implementation deliberately uses the stated degree meaning instead of preserving that slice. Therefore ordering and selected strains may differ from the publication.
- The caption describes sender rows/receiver columns clearly but later associates the two axis degree names inconsistently. This adaptation explicitly orders rows by outgoing sender count and columns by incoming receiver count; it does not infer exact author ordering from the image.
- The Rmd disables its heatmap legend whereas the published figure has a small colorbar. A visible colorbar is deliberately included here; the script-to-final-image match is not exact.
- Exact reference typography, color normalization, and post-export edits cannot be determined from appearance alone. This example sets its own documented 8 pt typography and full-matrix minimum/maximum color limits.
