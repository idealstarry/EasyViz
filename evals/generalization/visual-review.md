# Visual review of the transfer evaluation

The baseline contact sheet, final contact sheet, invalid-log-bound render, full-size dense-scatter render, and full-size repaired long-label heatmap were inspected. Contact sheets are evaluation aids; their resizing must not be used to judge physical text size. Final panel dimensions and 8 pt text are checked separately in the per-case artifacts.

| Case | Visual finding |
| --- | --- |
| 24 × 18 heatmap | All ordered rows and columns are retained, the signed scale is visible, and the 180 × 160 mm footprint gives distinct 8 pt labels. |
| Long labels at 88 mm | Labels visibly extend beyond the canvas. The run correctly remains invalid, with exports retained for inspection. |
| Repaired long labels | The same 48 values and unabridged labels fit at 180 × 105 mm with a larger left margin. Font size remains 8 pt. |
| Sparse composition | Twelve donor bars remain below 100% because the supplied full-sample denominator includes categories outside the display. The ordering and explicit seven-color mapping are retained. |
| Sparse dot matrix | Color and size legends are separate and visible. Zero-area values and absent combinations both leave blank positions; this display alone cannot communicate that distinction. |
| Dense logarithmic scatter | The 5,000-point cloud spans both log axes after validation. The annotation now displays `p < 0.001`. Small, translucent point symbols make the legend subtle; a final journal-specific design may choose larger legend symbols. |
| Invalid zero log bound, baseline | All points collapse close to a vertical line and tick labels pile up despite the old QA pass. This invalid request is now rejected before export. The baseline image is retained in `baseline-log-bound/`. |
| Nine-group distribution | Unequal sample sizes remain visible as individual points; the singleton stays a descriptive point/degenerate box. No inferential claim is added. |
| Internal tick collisions | The baseline label collision is obvious even though all text fits inside the canvas. The new QA flags the tick intersections and marks the output invalid. |
| Repaired tick placement | A wider 132 mm canvas and vertical tick labels restore separation without changing data or shrinking the 8 pt type. |
| Literal category labels | `NA`, `null`, and `Control` are now rendered as ordinary category names with all observations present. |

These observations support bounded transfer across the tested source shapes and design choices. They do not certify unseen chart families, arbitrary visual standards, automatic layout repair, or all kinds of annotation overlap.
