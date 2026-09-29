# Figure-derived categorical palette research

## Selected source: Notch2 lung macrophages

Cruz Tleugabulova, M. et al. **Induction of a distinct macrophage population and protection from lung injury and fibrosis by Notch2 blockade.** *Nature Communications* 15, 9575 (2024). [Article](https://www.nature.com/articles/s41467-024-53700-9) · [DOI: 10.1038/s41467-024-53700-9](https://doi.org/10.1038/s41467-024-53700-9).

The selected set comes from the actual **Figure 2b**, the interstitial macrophage (IM) stacked bars and their I1–I4 legend. Figure 2a uses the same classes. Four colors form a coordinated teal, blue, amber and orange set. These are colors observed in a specific scientific figure, not a palette named after a journal.

| Suggested order | Source class | RGB | HEX | PDF image object |
| --- | --- | --- | --- | --- |
| 1 | I4 | 26, 167, 129 | `#1AA781` | 385 |
| 2 | I2 | 37, 129, 185 | `#2581B9` | 391 |
| 3 | I1 | 223, 154, 60 | `#DF9A3C` | 389 |
| 4 | I3 | 215, 111, 59 | `#D76F3B` | 390 |

The order above is an EasyViz selection. The original legend orders I1, I2, I3, I4. Preserve the original class mapping when reproducing this figure. For new data, assign a stable mapping once and reuse it across panels. The amber and orange are closer than the cool pair; use the first two for a simple two-group comparison, and supplement color with direct labels when all four occur in small marks.

Two optional colors from the same Figure 2b legend are A2 sky blue (`#77B5DA`, RGB 119, 181, 218; object 384) and M1 pink (`#CC86B9`, RGB 204, 134, 185; object 343). Prefer the four-color set unless those extra categories are necessary; adding a second blue does not improve separation automatically.

### Evidence and precision

Inspected the complete PDF page 4 and a rendered crop of Figure 2b. Extracted the embedded **11 × 17 pixel RGB legend swatches** directly with PyMuPDF; all 187 pixels in each selected swatch have exactly the RGB value listed above. No antialiased edge, screenshot color picking, author plotting script or inferred library palette was used. The HEX values are exact for the embedded swatches in this PDF, but are not claimed to be the author's original color constants before PDF production or color management.

- Local source: `/Users/starry/Desktop/Res/Post-MI/ref/singlecell RNA-seq/Mayra. et al., NC, 2024/paper.pdf`.
- PDF SHA-256: `784302ece7c881a11d3260a911a69d4012f957cf535074e8dcb1348f72af7afb`.
- Inspected full-page render: `/private/tmp/easyviz-palette-tleugabulova-p4.png`.
- Inspected Figure 2b crop: `/private/tmp/easyviz-palette-notch2-fig2b.png`.
- Crop rectangle in PDF points (top-left coordinates): `(344, 42, 545, 184)`; scale 4.
- Research images are temporary inspection artifacts. This note distributes color values and attribution, not the paper figure. The article lists CC BY-NC-ND 4.0; do not bundle a modified figure as unrestricted EasyViz artwork.

## Other actual figures inspected

| Publication / figure | Observation | Decision |
| --- | --- | --- |
| Miyake et al., *Nature Communications* (2024), DOI [10.1038/s41467-024-46148-4](https://doi.org/10.1038/s41467-024-46148-4), Figure 1f, PDF page 3 | Four cluster fills are exact PDF vectors: `#FFC000`, `#FF0000`, `#00B0F0`, `#7030A0`. | Very vivid, but pure red and purple make it less balanced for the requested general default. Keep as a possible four-cluster reference, not the preferred set. |
| Sikkema et al., *Nature Medicine* (2023), DOI [10.1038/s41591-023-02327-2](https://doi.org/10.1038/s41591-023-02327-2), Figures 2b and 3a/d, PDF pages 4 and 6 | Figure 2 uses several pale hierarchical shades; Figure 3d uses many closely related fine-cell-type colors. | Useful for hierarchical cell annotation, but does not directly solve the current request for a compact, bright palette. |
| Massier et al., *Nature Communications* (2023), DOI [10.1038/s41467-023-36983-2](https://doi.org/10.1038/s41467-023-36983-2), Figure 2, PDF page 5 | Many pale blue, mint and lavender subtype shades. | Retain for faithful reproduction; do not make it the create-track default. |

Do not assert that any sampled palette is color-vision-deficiency safe without a separate evaluation. None of these categorical sets is a quantitative heatmap gradient.
