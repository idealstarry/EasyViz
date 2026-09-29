# Legend geometry observed in scientific figures

EasyViz should allocate space from the actual keys and labels that a chart needs. The inspected papers use shallow categorical rows, shared keys and short colorbars. Their geometry supports compact legends, but does not establish a universal size ratio or a journal standard. The user's agreed 8 pt typography remains an EasyViz constraint; a compact source legend is not permission to shrink it.

## Sources and method

| Source | Panels inspected | Primary publication | Local PDF SHA-256 |
| --- | --- | --- | --- |
| Cruz Tleugabulova et al. (2024), *Induction of a distinct macrophage population and protection from lung injury and fibrosis by Notch2 blockade* | Figure 2b, 2c and 2d; PDF page 4 | [Nature Communications, DOI 10.1038/s41467-024-53700-9](https://www.nature.com/articles/s41467-024-53700-9) | `784302ece7c881a11d3260a911a69d4012f957cf535074e8dcb1348f72af7afb` |
| Somerville et al. (2024), *Genomic and phenotypic imprints of microbial domestication on cheese starter cultures* | Figure 2A; PDF page 4 | [Nature Communications, DOI 10.1038/s41467-024-52687-7](https://www.nature.com/articles/s41467-024-52687-7) | `9f2a39db451a63a721ac7c84d77578acdc008e513a293339154d148250a7e7af` |

Both complete pages were rendered with Poppler and visually inspected. Individual panels were inspected as higher-resolution PyMuPDF crops. Vector paths, embedded-image rectangles and remaining text spans supplied coordinate evidence. Manual selection defines which marks belong to each plot or legend. Typical boundary uncertainty is approximately 0.5 PDF pt, or 1 pt for the heatmap's raster-composited colorbar. Coordinates use the top-left PDF origin. One PDF pt is 1/72 inch in the source page; an enlarged raster crop does not establish another physical scale.

The complete legend includes every key, title, label and tick. A plot field includes the area where data marks are drawn and excludes axis labels, tick labels, dendrograms, titles and legend. Where a key is shared by three independent fields, the denominator is the sum of those fields' areas, excluding intervening whitespace. The Somerville plot is treated as one composition field containing deliberate gaps between culture groups. These definitions matter: a ratio against the whole multi-panel page would be misleading.

Exact record structure, source paths, primitive dimensions and caveats are in [measurements.json](../evals/legend-literature/measurements.json). The numbers below are rounded observations of four panels, not population estimates.

## Measured examples

| Panel and legend | Plot-field bounds, PDF pt | Complete legend bounds, PDF pt | Legend area / plot-field area | Geometry that makes it compact |
| --- | --- | --- | --- | --- |
| Notch2 Figure 2b: 11 categorical items shared by three composition axes | Three fields: `(364.88, 79.40, 414.64, 154.90)`; `(425.09, 79.40, 474.85, 154.90)`; `(484.32, 79.40, 534.08, 154.90)` | `(364.48, 173.00, 540.47, 178.43)` | 8.5% | One 5.43 pt-high row. Outer key approximately 4.32 × 5.43 pt; key-to-text gap approximately 2.45 pt. Legend width is approximately 1.04 times the enclosing field width, so it uses the surrounding panel margin. |
| Notch2 Figure 2c: shared size and continuous-color keys for three dotplot blocks | Three fields: `(73.08, 232.38, 320.32, 267.80)`; `(73.42, 311.26, 312.80, 345.55)`; `(74.05, 387.84, 220.72, 422.26)` | `(233.02, 391.16, 314.26, 420.63)` | 10.9% | Both keys occupy the vacant area beside the shortest block. Horizontal colorbar is approximately 34.80 × 2.43 pt, only 14.1% of the widest field's width. Five size keys use approximately 7 pt center spacing. |
| Notch2 Figure 2d: continuous colorbar beside a similarity heatmap | Matrix: `(383.42, 261.50, 502.24, 378.20)` | `(510.28, 229.41, 540.47, 271.00)` | 9.1% | Colorbar body approximately 39.17 × 8.52 pt; its length is 33.6% of the matrix height. It sits above much of the row-label area instead of spanning the entire matrix. |
| Somerville Figure 2A: three species labels above grouped composition bars | `(87.94, 79.60, 358.73, 152.45)` | `(82.44, 48.77, 356.28, 59.81)` | 15.3% | One row accommodates long scientific names. Keys are 11.04 pt squares with approximately 2.3-3.1 pt key-to-text gaps. The full legend is approximately as wide as the plot field. |

The Somerville example is a useful counterexample to a universal small-key rule: its colored squares are much taller than the letter ink. Likewise, the Notch2 heatmap colorbar is relatively thick, while the dotplot colorbar is thin. The common pattern is controlled use of space and a clear relationship to the data field, not identical geometry across chart types.

### Typography and symbol scale

Most figure text in these PDFs has been converted to vector outlines. An outlined letter's ink height is not its font size, and punctuation, capitals and descenders change that height. Those font sizes are recorded as unavailable.

| Panel | Recoverable font metadata | Other directly measured evidence |
| --- | --- | --- |
| Notch2 2b | X-axis category labels: ArialMT, approximately 6.412 pt in the PDF | Legend letter ink approximately 4.49-4.59 pt high; y-axis numeral ink approximately 4.82-4.98 pt. This is an ink-height comparison, not a font-size ratio. |
| Notch2 2c | Two legend titles: Helvetica, approximately 5.610 pt | Size-key numeral ink approximately 2.98-3.03 pt; colorbar numerals approximately 4.06-4.13 pt; row-tick numeral ink approximately 4.11-4.20 pt. Size-key circle diameters are approximately 1.82, 3.07, 4.17, 5.17 and 6.10 pt for the five displayed values. |
| Notch2 2d | Colorbar title: ArialMT, approximately 6.412 pt | Colorbar numeral ink approximately 4.51-4.57 pt, comparable to the 4.49-4.59 pt cross-axis ink extent of rotated matrix labels. |
| Somerville 2A | Unavailable; text is outlined | Typical legend letter ink approximately 4.41-4.61 pt; tick numerals approximately 4.67-4.77 pt. Species names with descenders span more height. |

The small size-key numerals in Notch2 2c are an observation, not a recommendation to reproduce them in EasyViz. Preserve the same quantitative size transform in plot and key: a reference figure's circle diameters do not establish a valid transform for new data.

## Transferable rules for EasyViz

These are proposed EasyViz design rules informed by the inspected figures. Their numerical defaults, if implemented, must be labeled as EasyViz choices and validated on new charts.

1. **Measure the complete legend after rendering.** Count its title, numeric labels, long names, and keys. Check the occupied width and height against the available panel space, along with overlap and clipping. A compact colorbar body can still have a large overall legend because of text.
2. **Preserve agreed text size and meaning.** Try shorter titles without losing units or normalization, remove redundant titles, reduce key lengths and unnecessary padding, and arrange items into a shallow row before enlarging the panel. Wrap or move the legend if it does not fit. Do not reduce an 8 pt font to force a target percentage.
3. **Choose geometry by encoding.** A category swatch only needs to identify a fill. A line key may need enough length to show dash patterns. A point key must retain meaningful shape and outline. A continuous colorbar rarely needs to span the whole data field. A size key must be generated by the same numeric-to-area mapping as the data marks.
4. **Share only genuinely identical mappings.** Several blocks of one chart can use one key when their categorical mapping, color normalization or size transform is identical. Separately exported EasyViz panels should each remain interpretable unless the user explicitly requests a separate legend asset.
5. **Use representative quantitative ticks.** Enough reference values to explain the scale are more useful than a long stack of nearly redundant keys. Preserve scientifically meaningful thresholds and endpoints. Avoid adding a category legend when direct labels already identify every class clearly.
6. **Treat area ratios as a review signal.** The four measurements span approximately 8.5-15.3% under the stated denominator. This small, selected sample does not justify a hard maximum for every chart. Long species names, unusual scales and multiple independent encodings may need more space; record the reason and review the actual panel at its final size.

## Inspection artifacts

Research crops remain outside the repository and distributable skill:

- `/private/tmp/easyviz-legend-research/notch2-2b.png`
- `/private/tmp/easyviz-legend-research/notch2-2c.png`
- `/private/tmp/easyviz-legend-research/notch2-2d.png`
- `/private/tmp/easyviz-legend-research/somerville-2a.png`

The research does not consult author plotting code and does not redistribute article figures. The evidence supports layout choices; it does not establish a publication rule, test color-vision accessibility or validate the statistics of the papers.
