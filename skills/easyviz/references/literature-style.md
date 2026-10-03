# Literature design mechanisms for Create

Use this reference for a crisp, compact scientific panel when the user has no
adopted reproduction layout. These are transferable design decisions observed
in specific figures, not a single Nature style. Keep the two tracks: a new
arrangement with literature-inspired mark treatment is **create**; an adopted
reference layout/style is **reproduce**.

The actual PDF pages and detail crops were visually inspected. Source anchors
use one-based PDF pages. Images establish appearance; captions and the user's
data establish statistical meaning. Do not copy the papers' tests, significance
marks, transformations, cell labels or filtering into a new dataset.

## What changes the implementation

| Reading problem | Observed mechanism and source | Adaptation to consider | Boundary |
| --- | --- | --- | --- |
| Samples disappear into a pale fill | scWAT Fig. 2c,i,j (p. 4): hollow blue/coral bars plus small same-hue observations. Vanneste Fig. 2e–h (p. 4): colored open circles over hollow bars. | Opaque observation marks; open summaries leave the raw layer readable. Match hollow/filled legend symbols to actual marks. | A hollow glyph is a fixed-size observation symbol. It cannot silently replace a circle whose filled area encodes a number. Bars still need an adopted summary and uncertainty definition. |
| Two cohorts make an indistinct cloud | Vanneste Fig. 5d (p. 7): repeated aligned plot boxes, shared labels and deliberate class blocks. | Compare aligned facets with shared numeric scales and row order; pack points only along the categorical direction. | Faceting reduces each plot's available width. Check mark capacity at final size and retain every source observation. |
| Distribution shape looks washed out | PROGENy Fig. 4c (p. 6): closed violin boundary, inner rectangular box and median stroke are separately visible. | Give the shape and its summary explicit outlines; use color for identity rather than fading the whole layer. | Do not infer KDE bandwidth, sample size or interval meaning from an image. A plain box/points view may be more appropriate. |
| A dense point field overwhelms its summary | Vanneste Fig. 5d (p. 7): smooth curves are wider than tiny green points, with a visible white edge separating layers. | Allocate stroke to the summary locally; a narrow contrasting under-stroke can separate a declared curve from points. | A fitted curve requires an adopted method. Adding a smooth line for appearance alone is not justified. |
| Signed matrix values blur together | scWAT Fig. 2b (p. 4), Vanneste Fig. 4d (p. 6): cold/neutral/warm expression fields; PROGENy Fig. 2b,c (p. 4) uses green/yellow/red fields. | Choose a reviewed multihue scale; a meaningful zero can anchor a diverging scale and a labeled zero tick. Make category strips distinct from the numeric color scale. | Signed normalization and endpoints must be explicit. A nonnegative magnitude can use a multihue sequential scale; it does not acquire a neutral threshold just because diverging colors are attractive. |
| Repeated bars look sparse or disconnected | scWAT Fig. 3g,m (p. 5): tight within-category bars, wider category gaps, compact keys. | Use repeated geometry, consistent gaps and shared decoding. Reserve only the space needed by data and annotations. | Retain units and actual experimental grouping. Density is not a reason to invent annotations or enlarge bars independently of values. |
| Two grouping variables become a long legend | scWAT Fig. 3g (p. 5): hue/edge and open/filled interiors distinguish separate variables; Fig. 5b,c (p. 9) uses hatching. | Use a second decoded visual channel when both groupings matter. | Do not introduce shape, hatch or stroke differences without a meaning; quantify their legend footprint. |

## Color and stroke observations

- scWAT Fig. 2 uses PDF vector blue **`#55A0FB`** and coral **`#FF8080`**
  in strokes and filled marks. These values are rounded from inspected PDF RGB,
  not recovered author-code constants. `scwat-blue-coral` offers the pair;
  its assignment to new cohort labels is an explicit design choice.
- Vanneste Fig. 2e–h uses saturated blue/red observation edges. Black axes and
  comparison strokes remain clear. A guide can be dark and thin; all supporting
  strokes do not need to be pale or weaker than every data stroke.
- The source figures mix hollow/filled marks, vivid/pale fills and narrow/wide
  strokes by role. Low alpha is useful for a declared dense background or
  uncertainty band, but should not erase the layer the reader must inspect.
- PROGENy separates small discrete cells with white boundaries; Vanneste's
  large cell-level heatmaps avoid framing every tiny cell. The separator policy
  depends on cell size, not a universal no-grid rule.

## Apply to another dataset

State the intended lookup or comparison, then select a mechanism above. Record
the actual category mapping, mark treatment, summary meaning, scale and physical
layout. Render the real data; check complete-panel balance and inspect marks at
final size. Compare a baseline and candidate with equal dimensions, font and
numeric scales. Where a normalization change is intentional, disclose it
separately from a cosmetic comparison.

Do not call the result better merely because it has more colors, thinner lines,
less grid or more empty space. If the main evidence becomes a faint cloud,
summary endpoints cannot be distinguished, or a colorbar hides zero, revise the
specific encoding or layout. Technical checks support row/scale/export fidelity;
visual inspection and user judgment assess whether the design succeeds.

## Sources

- Schubert et al. (2018), [Perturbation-response genes reveal signaling
  footprints in cancer gene expression](https://www.nature.com/articles/s41467-017-02391-6),
  Nature Communications 9:20; supplied `PROGENy.pdf`.
- Huang et al. (2023), [Transcriptional repression of beige fat innervation via
  a YAP/TAZ-S100B axis](https://www.nature.com/articles/s41467-023-43021-8),
  Nature Communications 14:7102; supplied `scWAT.pdf`.
- Vanneste et al. (2023), [MafB-restricted local monocyte proliferation precedes
  lung interstitial macrophage differentiation](https://www.nature.com/articles/s41590-023-01468-3),
  Nature Immunology 24:827–840.

Original PDF files and full figure images are not bundled with this reference.
Palette records retain PDF hashes and vector locations. These sources do not
establish accessibility, publication acceptance or model-performance improvement.
