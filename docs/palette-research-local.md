# Literature palette research: local figures

## Selected source

Somerville et al. (2024), *Genomic and phenotypic imprints of microbial domestication on cheese starter cultures*, Nature Communications 15, 8642. DOI: [10.1038/s41467-024-52687-7](https://www.nature.com/articles/s41467-024-52687-7). The publisher page confirms the figure identities and their biological encodings. The visually strongest candidate is the paper's combination of vivid sky blue, coral, turquoise, and a white background.

The local PDF was rendered and inspected; no author plotting scripts were read. Source file: `/Users/starry/Desktop/Cm/Viz_ref/Somerville et al., 2024/Somerville et al., 2024.pdf`. SHA-256: `9f2a39db451a63a721ac7c84d77578acdc008e513a293339154d148250a7e7af`.

## Observed colors

Colors below come from flat vector fills in the PDF, extracted with PyMuPDF `Page.get_drawings()`, converted from RGB floats to 8-bit channels with `round(channel * 255)`. These are PDF RGB values, not claims about the authors' original script literals or print profiles. Small differences occur between panels: for example, culture 202 is `#29ACF3` in Figure 1B and `#009CF0` in Figure 2A. Select one version consistently rather than blending values accidentally.

| Color | Hex | Actual source mark | Figure / PDF page |
|---|---|---|---|
| Sky blue | `#29ACF3` | Culture 202 triangular sampling markers | 1B / 3 |
| Coral | `#E47751` | Culture 105 circular sampling markers | 1B / 3 |
| Orange | `#DC732E` | Culture 101 circular sampling markers | 1B / 3 |
| Cyan | `#33CFFA` | Culture 203 triangular sampling markers | 1B / 3 |
| Light sky | `#7FE3FF` | Culture 280 triangular sampling markers | 1B / 3 |
| Teal | `#007F7F` | Culture 302 square sampling markers | 1B / 3 |
| Turquoise | `#00DCDC` | Culture 305 square sampling markers | 1B / 3 |
| Ocean blue | `#007FA6` | *Streptococcus thermophilus* legend swatch and abundance bars | 2A / 4 |
| Pale coral | `#FDC2B5` | *L. delbrueckii* subsp. *lactis* legend swatch and abundance bars | 2A / 4 |
| Saturated sky | `#009CF0` | Culture 202 column header | 2A / 4 |
| Soft gold | `#FFED7F` | Subspecies clade 3 legend circle | 2B / 4 |
| Lavender | `#A37FFF` | Subspecies clade 11 legend circle | 2B / 4 |

Temporary inspection artifacts, outside the distributable plugin:

- `/private/tmp/easyviz-somerville-figure1b.png`: Figure 1B crop, rendered at 3×.
- `/private/tmp/easyviz-somerville-figure2.png`: Figure 2 crop, rendered at 3×.
- `/private/tmp/easyviz-somerville-palette-evidence.json`: 172 matching vector marks, exact PDF float RGB values, fill opacities, bounding boxes, and source hash.

## Suggested EasyViz families

These are **EasyViz selections and adaptations from observed paper colors**, not an official Nature palette and not a ready-made palette claimed to have been provided by the authors. Reassigning the colors to new biological groups does not transfer the original semantic labels.

| Proposed use | Colors / construction | Status |
|---|---|---|
| Bright categorical, four groups | `#29ACF3`, `#E47751`, `#007F7F`, `#A37FFF` | A coordinated selection across Figures 1B and 2B. Blue and coral work especially well as the lead pair. |
| Bright categorical, six groups | Add `#FFED7F` and `#00DCDC` to the four-color selection | Use for sufficiently large marks, with dark outlines for gold. These six are not guaranteed to remain separable in every color-vision condition; use shape or direct labels when needed. |
| Ocean sequential | White or a very pale blue to `#007FA6` | Newly interpolated EasyViz scale based on Figure 2A's blue endpoint; not an author colormap. A light start prevents large low-value areas from becoming a dark field. |
| Sky sequential | White or a very pale blue to `#009CF0` | Brighter alternative based on Figure 2A's culture header; also an EasyViz interpolation. |
| Blue–white–coral diverging | `#29ACF3` → `#FFFFFF` → `#E47751` | Newly interpolated EasyViz scale for signed values with a meaningful center. Both colored endpoints come from Figure 1B. White and interpolation are EasyViz additions. |
| Ocean–white–coral diverging | `#007FA6` → `#FFFFFF` → `#E47751` | Stronger blue contrast; verify perceived balance in the actual heatmap before adopting. |

For the current create showcases, the blue–white–coral family fits a signed interaction heatmap. A sky sequential scale fits nonnegative proportions or prevalence. Continuous colors should reflect numerical meaning; the figure palette must not change zero, missing-value, or normalization semantics. Keep annotation strips in a small, stable categorical family, rather than placing several competing rainbows beside the matrix.

## Other inspected literature

Angarola et al. (2025), *Comprehensive single-cell aging atlas of healthy mammary tissues reveals shared epigenomic and transcriptomic signatures of aging and cancer*, DOI [10.1038/s43587-024-00751-8](https://www.nature.com/articles/s43587-024-00751-8), was also visually inspected. Its extended Figure 10 uses brighter coral, cyan, blue and green tumor-type encodings, but several greens are similar; it is a weaker general categorical default. Its signed heatmaps include dark end colors, so it does not address the user's request as directly as the Somerville pair. No author scripts were consulted.
