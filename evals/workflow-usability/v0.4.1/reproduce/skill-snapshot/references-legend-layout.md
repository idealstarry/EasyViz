# Legend proportions and placement

Legends support accurate, low-effort decoding inside the fixed manuscript canvas. Preserve the agreed type and quantitative mappings, then choose guide size and placement in relation to the data, label lengths, and reading task. Compactness is one possible improvement, not the optimization target. Equal font sizes do not guarantee balanced proportions: oversized keys, loose gaps, or a large reserved legend band can still dominate a panel.

## Identify the encoding

| Legend role | Preserve | Compact safely |
| --- | --- | --- |
| Categorical color, shape, or line | Category identity, legible labels, and the declared mark-outline policy. | Use compact proxy keys; adjust key dimensions, key-to-text gap, row spacing, and columns. Their key size need not equal a plotted mark when size carries no information. |
| Quantitative size | The exact plotted value-to-area mapping and matching outline treatment. | Choose a small sufficient set of labeled values and adjust spacing or placement. **Never shrink legend markers relative to plotted areas** to make the legend fit. Reconsider the shared plot-and-legend area scale only as a declared encoding change. |
| Continuous color scale | Value range, direction, meaningful center, and enough labeled ticks to interpret the scale. | Adjust physical colorbar length/thickness, label offset, orientation, and tick count. Retain endpoints and any necessary center or threshold; do not change the data normalization to save space. |

Give separate roles clear labels, such as count for area and proportion for color. A short encoding label or unit belongs with its legend; explanations, abbreviation definitions, methods, and caveats belong in `caption.md`. User-specified placement and typography take precedence over inferred preferences.

## Measure the whole layout

Render with the actual font and text before accepting a placement. For each legend block, record the following in the layout/review evidence.

| Measurement | Meaning |
| --- | --- |
| Complete legend bounds | Bounding box of keys, labels, legend role label, ticks, and colorbar as applicable; measure each block and their combined envelope. A colorbar rectangle alone is not its full footprint. |
| Reserved legend region | Space allocated to the legend, including padding. Record it separately: unused reserved space can shrink the plot even when the actual legend is compact. |
| Plot bounds | Bounds of the primary data region. In integrated panels, identify the main matrix/plot and aligned summary axes separately. |
| Relative proportions | Legend width, height, and envelope area relative to the stated plot region; also inspect the gaps and visual weight rather than treating area alone as the verdict. |
| Physical text and keys | Actual text size in pt and key geometry in mm or pt², including whether size is quantitative. |

Use measured text extents to compare plausible placements: alongside a plot, below it in columns, or in a genuinely unoccupied interior region. Keep labels, keys, and related data visibly associated. An interior legend must not hide observations or annotations. Avoid a fixed side band that remains excessively large for a short legend, and avoid squeezing the data region merely because one default anchor fits without clipping.

A legend that fits the canvas can still be too prominent. Review data-region dominance, legend footprint, reserved whitespace, and the hierarchy of marks and text separately from overlap/clipping. Any automated proportional warning is an adjustable project heuristic tied to a particular layout; it is not a universal percentage limit, a journal requirement, or proof of aesthetic quality.

Inspect key-to-label alignment as well as spacing. Large quantitative keys need sufficient row height and a stable relationship to their numeric labels; increasing marker area must not make symbols float above the corresponding text. Verify the actual exported SVG/PDF or raster output when display and export resolutions differ. Stored marker areas alone do not prove correct exported geometry.

## Learn from references without copying their constraints

In reproduce, measure approximate relative legend/plot bounds and visible key/glyph heights from the selected reference panel. Keep uncertainty from image resolution, cropping, and ambiguous panel boundaries. Raster glyph height is not an absolute font size. A legend shared by several published subpanels may occupy a different proportion than a legend serving one standalone output; do not transfer that geometry blindly.

Adopt the useful relationship—such as compact categorical keys beside a tall matrix—then fit it to the user's data, label lengths, agreed font size, and final canvas. Preserve quantitative size mappings and continuous-scale semantics even when the reference's implementation is unknown. State intentional deviations in the adopted specification.

### Measured literature examples

The following are approximate observations from source PDF page 4 of each paper, not author instructions or journal standards. Complete legend bounds include keys, labels, ticks, and role labels. The area denominator is the sum of the specified data-field rectangles, excluding axis labels and inter-axis gaps; the Somerville field includes its internal group gaps. A shared legend is counted once. Boundary estimates have approximately 0.5 PDF pt uncertainty, or 1 pt for the heatmap colorbar.

| Inspected source and panel | Observed geometry | Transferable decision |
| --- | --- | --- |
| [Cruz Tleugabulova et al., 2024, Figure 2b](https://www.nature.com/articles/s41467-024-53700-9) | Eleven categorical keys in one shallow row shared by three composition axes; complete legend area approximately 8.5% of their combined fields. | Consider compact categorical rows when labels fit; do not charge a shared legend to each field separately. |
| [Same paper, Figure 2c](https://www.nature.com/articles/s41467-024-53700-9) | Size and color keys occupy spare space beside the shortest of three dotplot blocks; complete legend area approximately 10.9% of combined fields. Colorbar body 34.80 × 2.43 PDF pt. | Use available geometry and separate encoding roles; preserve the new data's quantitative size mapping. |
| [Same paper, Figure 2d](https://www.nature.com/articles/s41467-024-53700-9) | Complete legend area approximately 9.1% of the heatmap field; vertical colorbar body length approximately 33.6% of matrix height. | A colorbar can occupy a compact physical region instead of matching the entire matrix height. |
| [Somerville et al., 2024, Figure 2A](https://www.nature.com/articles/s41467-024-52687-7) | Three long species labels form one row; complete legend area approximately 15.3% of the composition field. Keys are approximately 11.04 PDF pt squares. | Long labels and large keys can still form a shallow layout; the literature does not support a universal tiny-key rule. |

Most text in these panels is outlined, so visible glyph height does not establish font size. The selected observations cannot justify a universal 8.5–15.3% target range. Retain EasyViz's agreed typography and assess the actual key/text footprint, reserved space, and data hierarchy for each new panel.

## Correction and verification

Correct the relevant cause: key geometry, excessive gaps, column arrangement, reserved band, or placement. Protect the agreed typography. Re-render and inspect the actual panel under [Visual review](visual-review.md); do not declare success solely because no objects overlap.

When a correction changes reusable EasyViz styling or layout code, verify the affected chart families with representative variations in category count, label length, and physical panel size. Include quantitative-size or continuous legends when that shared code serves them. Record the cases actually exercised and remaining limits; avoid unrelated changes or claims that one corrected example establishes generalization. An ordinary case-specific adjustment does not require a library-wide benchmark.

## Shared implementation

The core renderer uses `scripts/legend_layout.py`. A custom Matplotlib recipe can use the same helper; include a copy beside the recipe when distributing a standalone folder. Register the required guides, call `layout()`, and save its report with the actual plotting settings. `validate()` remeasures existing guides. The helper tries a bounded set of placements and columns; a failed fit is `needs_revision`, requiring an explicit layout repair. It does not resize the data axes or canvas automatically, and custom annotations still require visual review.

```python
from legend_layout import LegendLayout

guides = LegendLayout(fig, ax, {"legend": 8}, config.get("legends", {}))
guides.add_categorical(labels, colors, shape="patch")
guides.add_size(values, [area_for_value(v) for v in values], title="Count")
guides.add_colorbar(mappable, "Proportion (%)")
report = guides.layout()
```

Register only guides that explain the actual encodings. For a custom chart drawn on a full-canvas, axes-off coordinate system, pass `main_plot_bbox_mm=[left, bottom, width, height]` to identify its actual data region. An ordinary chart uses its axes field and measures surrounding tick and axis labels for collision checks.

| Setting under `legends` | Use |
| --- | --- |
| `categorical` | `position`, `ncol`, `key_width_mm`, `key_height_mm`, `handletext_gap_mm`, `row_gap_mm`, `column_gap_mm`, and `borderpad_mm`; proxy keys can compact without changing data marks. |
| `size` | Placement, columns and gaps; numerical areas must come from the same transform as plotted observations. Independent size scaling is unsupported. |
| `colorbar` | `position`, `orientation`, `length_mm`, `thickness_mm`, `ticks`, `label`, and `label_position`; the mappable retains the normalization. |
| `review_thresholds` | Adjustable diagnostic thresholds; warnings prompt review and do not constitute journal requirements or aesthetic acceptance. |

Positions are `auto`, `right`, `top`, `bottom`, or `manual`. Automatic placement preserves explicit options. A manual categorical or size guide uses `anchor_mm: [x, y]` and a Matplotlib `loc`; a manual colorbar uses `rect_mm: [x, y, width, height]`. Physical coordinates start at the lower-left canvas corner. Set the manual rectangle and label position together so the complete guide, including ticks, fits.

Starting choices are 1.5 mm categorical keys, 0.7 mm key-to-text spacing, 0.6 mm row spacing, 2 mm column spacing, and 2 mm colorbar thickness. Automatic colorbar length candidates are 18–28 mm, informed by the relevant plot side. These are EasyViz engineering defaults, **not measurements prescribed by the cited papers**. The actual selected geometry is recorded in the layout report.

Treat these values as fallbacks. Preserve an existing acceptable guide unless a full-panel comparison shows a benefit from changing it. Fit measurements can reject unusable placements; they cannot rank the remaining placements by visual quality. Do not transfer a short paper colorbar into every chart or replace a useful five-tick scale with three ticks solely to make it smaller. Reclaiming space, retaining a longer scale, or leaving the baseline unchanged can each be the appropriate decision.
