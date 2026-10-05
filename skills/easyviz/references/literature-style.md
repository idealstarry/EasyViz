# Literature design mechanisms for Create

Use this reference for a crisp, compact scientific panel when the user has no
adopted reproduction layout. These are transferable design decisions observed
in specific figures, not a single Nature style. Keep the two tracks: a new
arrangement with literature-inspired mark treatment is **create**; an adopted
reference layout/style is **reproduce**.

Apply the mark, color and spacing mechanism to a basic single plot first. The
number of tracks or annotations in a paper is not a quality target. Borrow a
composite arrangement only when its extra layer answers the current reading
task and has supplied data with a declared meaning.
Basic chart families can carry a complete experimental comparison. In scWAT,
repeated groups, relevant outcomes and visible sample/summary layers give
the bars purpose as well as compact geometry. Transfer those relationships
when supplied data support them; colors alone or decorative repetition cannot
give an underspecified demonstration the same scientific completeness.

The actual PDF pages and detail crops were visually inspected. Source anchors
use one-based PDF pages. Images establish appearance; captions and the user's
data establish statistical meaning. Do not copy the papers' tests, significance
marks, transformations, cell labels or filtering into a new dataset.

## What changes the implementation

| Reading problem | Observed mechanism and source | Adaptation to consider | Boundary |
| --- | --- | --- | --- |
| Samples disappear into a pale fill | scWAT Fig. 2c,i,j (p. 4): hollow blue/coral bars, small same-hue observations and readable interval strokes. Vanneste Fig. 2e–h (p. 4): colored open circles over hollow bars. | Set bar, point and interval geometry together: small observations remain distinct, open summaries leave the raw layer visible, and intervals survive at the bar top. | Borrowing blue/coral alone does not reproduce this hierarchy. Bars need an adopted summary and uncertainty definition; a hollow glyph cannot replace quantitative filled-area circles. |
| Two cohorts make an indistinct cloud | Vanneste Fig. 5d (p. 7): repeated aligned plot boxes, shared labels and deliberate class blocks. | Compare neighboring group lanes or aligned facets with shared numeric scales and row order; pack points only along the categorical direction. | Faceting reduces each plot's available width. Check mark capacity at final size, retain every observation and do not erase pairing that the question needs. |
| Distribution layers compete | PROGENy Fig. 4c (p. 6): a fine closed violin contour surrounds a more prominent rectangular summary and median, in compact repeated groups. | For summary-first reading, give the inner box more emphasis than the contour. Choose displayed violin width and group gaps together; a raw-point overlay is another explicit layer, not a requirement inherited from this figure. | Do not infer KDE bandwidth, sample size or interval meaning from an image, or alter bandwidth to copy its silhouette. A box/points view may serve the task without density estimation. |
| A dense point field overwhelms its summary | Vanneste Fig. 5d (p. 7): smooth curves are wider than tiny green points, with a visible white edge separating layers. | Allocate stroke to the summary locally; a narrow contrasting under-stroke can separate a declared curve from points. | A fitted curve requires an adopted method. Adding a smooth line for appearance alone is not justified. |
| Matrix values are difficult to compare | scWAT Fig. 2b (p. 4): a tall narrow expression matrix uses its few columns as compact reading units. PROGENy Fig. 2b,c (p. 4) and Vanneste Fig. 4d (p. 6) use different cell densities and color fields. | Set data-region aspect from matrix shape and label needs before choosing colors. Begin with a reviewed sequential scale for magnitude; use subordinate seams for large cells and a readable guide. | Square cells are not compulsory. Do not stretch a few columns solely to fill width, infer a universal heatmap palette, or introduce an unmotivated neutral threshold. Preserve normalization, ordering and all values. |
| Repeated bars look sparse or disconnected | scWAT Fig. 3g,m (p. 5): tight within-category bars, wider category gaps, compact keys. | Retain relevant supplied outcomes/groupings and repeat their geometry and series order consistently. Show supported observations and uncertainty; use one shared decoding guide. | Retain units and actual experimental grouping. Small data remain a small comparison; density is not a reason to invent annotations, extra outcomes or enlarged marks. |
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
  strokes by role. PROGENy's light contour and stronger inner summary differ
  from a point-first plot. Low alpha may support a density face or uncertainty
  band, but should not erase the primary evidence or its definite boundary.
- PROGENy separates small discrete cells with white boundaries; Vanneste's
  large cell-level heatmaps avoid framing every tiny cell. The separator policy
  depends on cell size, not a universal no-grid rule.

## Apply to another dataset

State the intended lookup or comparison, then select a mechanism above. Record
the actual category mapping, mark treatment, summary meaning, scale and physical
layout. For a basic chart, check the color combination, role of each stroke,
point/summary crossings, category gaps and guide space before adding a layer.
Render the real data; check complete-panel balance and inspect marks at final
size. Compare the accepted candidate and revision with equal dimensions, font
and numeric scales. An omitted-default comparison only tests preference over
that particular baseline. Separately assess whether the target paper's
layer hierarchy, compact grouping and cell proportions have transferred;
different data make this a design comparison, not matched performance evidence.
Disclose intentional normalization changes outside cosmetic comparisons.

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
