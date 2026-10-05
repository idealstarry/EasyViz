# Literature design mechanisms for Create

Use this reference for a crisp, compact scientific panel when the user has no
adopted reproduction layout. Create can use these observed mechanisms without
a user-supplied reference at runtime; they are not a single Nature style.
Keep the two tracks: a new arrangement with literature-inspired treatment is
**create**; adopting a supplied reference's layout/style is **reproduce**.

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
| A single quantity has unnecessary categorical colors | PROGENy Fig. 2d (p. 4): uniform gray bars. scWAT Fig. 3j (p. 5): deep-gray open control bar/observations beside a colored comparison. | When x labels already decode categories, compare neutral bars/points with the accepted colored design. | A neutral treatment is optional; multiple series need another visible decoding channel. Do not remove a supplied comparison group to simplify the panel. |
| Two classes need identity in a small-point field | scWAT Fig. 2g (p. 4): blue and pink observations with matching fitted-line strokes, unlike the blue/coral bars on the same page. | Compare a distinct pair on the actual small points; color requirements differ from large summary areas. | The fitted line requires an adopted model. A source's pair can inspire a new scatter without copying its analysis or all mark colors. |
| Samples disappear into a pale fill | scWAT Fig. 2c,i,j (p. 4): hollow blue/coral bars, small same-hue observations and readable interval strokes. Vanneste Fig. 2e–h (p. 4): colored open circles over hollow bars. | Set bar, point and interval geometry together: small observations remain distinct, open summaries leave the raw layer visible, and intervals survive at the bar top. | Borrowing blue/coral alone does not reproduce this hierarchy. Bars need an adopted summary and uncertainty definition; a hollow glyph cannot replace quantitative filled-area circles. |
| Two cohorts make an indistinct cloud | Vanneste Fig. 5d (p. 7): repeated aligned plot boxes, shared labels and deliberate class blocks. | Compare neighboring group lanes or aligned facets with shared numeric scales and row order; pack points only along the categorical direction. | Faceting reduces each plot's available width. Check mark capacity at final size, retain every observation and do not erase pairing that the question needs. |
| Distribution layers compete | PROGENy Fig. 4c (p. 6): fine neutral violin boundaries, categorical fills on summary/body areas, clear inner boxes and medians in compact groups. | For summary-first reading, compare categorical areas with neutral contours/raw points. Give the inner box more emphasis than the contour; choose displayed width and group gaps together. | Neutral raw points are a proposed adaptation, not an observed PROGENy layer. Do not infer KDE bandwidth or interval meaning, change bandwidth for silhouette, or inherit the paper's mutation/pathway categories. |
| A dense point field overwhelms its summary | Vanneste Fig. 5d (p. 7): smooth curves are wider than tiny green points, with a visible white edge separating layers. | Allocate stroke to the summary locally; a narrow contrasting under-stroke can separate a declared curve from points. | A fitted curve requires an adopted method. Adding a smooth line for appearance alone is not justified. |
| Matrix values are difficult to compare | scWAT Fig. 2b (p. 4): a tall narrow expression matrix uses its few columns as compact reading units. PROGENy Fig. 2b,c (p. 4) and Vanneste Fig. 4d (p. 6) use different cell densities and color fields. | Set data-region aspect from matrix shape and label needs before choosing colors. Begin with a reviewed sequential scale for magnitude; use subordinate seams for large cells and a readable guide. | Square cells are not compulsory. Do not stretch a few columns solely to fill width, infer a universal heatmap palette, or introduce an unmotivated neutral threshold. Preserve normalization, ordering and all values. |
| Repeated bars look sparse or disconnected | scWAT Fig. 3g,m (p. 5): tight within-category bars, wider category gaps, compact keys. | Retain relevant supplied outcomes/groupings and repeat their geometry and series order consistently. Show supported observations and uncertainty; use one shared decoding guide. | Retain units and actual experimental grouping. Small data remain a small comparison; density is not a reason to invent annotations, extra outcomes or enlarged marks. |
| Two grouping variables become a long legend | scWAT Fig. 3g (p. 5): hue/edge and open/filled interiors distinguish separate variables; Fig. 5b,c (p. 9) uses hatching. | Use a second decoded visual channel when both groupings matter. | Do not introduce shape, hatch or stroke differences without a meaning; quantify their legend footprint. |

## Geometry observations

The following approximate width:height ratios were measured from the data
regions on rendered PDF pages, including 300 dpi detail views. They exclude
axis titles, tick text and legends; they are not complete-canvas ratios or
recovered author settings. The contrasting examples show conditional geometry,
not universal thresholds.

| Observed source | Local geometry and hierarchy | Conditional adaptation |
| --- | --- | --- |
| PROGENy Fig. 4c (p. 6) | Each panel has eight distributions in a data region about 2.4–2.5 times as wide as high. Fine neutral density contours remain distinct from definite inner boxes/medians; categorical color occupies different summary/body roles. | When several distribution groups must be compared, test whether a wider, shallower data rectangle and compact category rhythm improve lookup. Plan any new raw-point lane separately; it is not a layer observed here. Preserve the adopted KDE and summary definitions. |
| Vanneste Fig. 2g,h (p. 4) | Eight and nine categories respectively, each with two treatment bars, in data regions about 3.3–3.5 times as wide as high. Closely associated bar pairs, visible raw observation edges and interval strokes repeat across the row; black axes and a decoded reference line remain readable. | For a comparable repeated two-series comparison, plan pair width, within-pair gap and between-category gap together. Test horizontal extent and useful numeric-axis height rather than placing narrow bars in a tall default region. Retain the actual units and uncertainty; source comparisons and reference values are not defaults. |
| scWAT Fig. 2c (p. 4) | Six categories with two treatment bars use a data-region ratio around 1.5. Hollow summaries, same-hue observations and visible interval endpoints remain associated. The numeric axis has a break. | A smaller repeated comparison can need more vertical space than the Vanneste example. Match its mark/interval relationship where relevant, while keeping the current adopted scale; an axis break, source limits or significance layer requires separate scientific justification. |
| scWAT Fig. 2j (p. 4) | A single treatment pair occupies a narrow data region with readable summary, observations and uncertainty. | A one-pair comparison need not occupy the same broad region as six or nine categories. Set width from actual bar/point capacity and label/guide needs, then check complete-canvas balance. |

For a new dataset, use category/series count, actual raw-point density, labels,
range and adopted layers to select an analogue. Measure the new data region in
mm and distinguish body width from category pitch and within/between-group gaps.
The mechanism may suggest a geometry change; only the actual final-size view
can establish whether it helps this panel. Copying an observed ratio or palette
does not establish successful transfer.

## Color and stroke observations

- PROGENy Fig. 2d uses uniform gray **`#595959`** bars. In Fig. 4c, selected
  purple **`#8787DE`** and mint **`#BFE8C5`** fills occur in inner mutation
  summaries; selected salmon **`#FF9695`** and gray **`#CACACA`** occur in
  KDE/pathway-stratum areas. Boundaries are neutral **`#333333`**.
  `progeny-summary` selects observed area colors from these different roles;
  it is not a recovered four-color inner-box palette. Reassigning all four to
  new cohort IQR areas and adding graphite raw points are adaptations, without
  inheriting the source's mutation/pathway meaning.
- scWAT Fig. 2c,i,j uses vector blue **`#55A0FB`** and coral **`#FF8080`**.
  Fig. 2g instead has blue/pink fitted-line strokes **`#3795D3`** / **`#FF5FBD`**;
  its point fills/edges are not uniformly those two colors. `scwat-blue-pink`
  selects the line strokes; applying the pair to all new scatter observations
  is an adaptation. These HEX values round observed PDF RGB, not author code.
- Vanneste Fig. 3e,g (p. 5) uses black/white/gray compositions with definite
  black outlines; Fig. 3g gray fill is **`#9E9E9E`**. The source demonstrates
  neutral data marks, not a requirement to remove informative hues from every
  categorical panel.
- Vanneste Fig. 2e–h uses saturated blue/red observation edges. Black axes and
  comparison strokes remain clear. A guide can be dark and thin; all supporting
  strokes do not need to be pale or weaker than every data stroke.
- The source figures mix hollow/filled marks, vivid/pale fills and narrow/wide
  strokes by role. Large light-colored areas can remain legible with boundaries,
  while the same pale color may disappear as a tiny point. PROGENy's fine
  contour and stronger inner summary differ from a point-first plot. Low alpha
  may support a density face or uncertainty band, but should not erase the
  primary evidence or its definite boundary. Already-pale observed fills do not
  require an additional low-opacity treatment.
- PROGENy separates small discrete cells with white boundaries; Vanneste's
  large cell-level heatmaps avoid framing every tiny cell. The separator policy
  depends on cell size, not a universal no-grid rule.

## Apply to another dataset

Use the [internal design brief](design-space.md#plan-the-first-panel) to connect
the intended comparison and actual data burden to a mechanism above. Distinguish
what was observed in the source from what is being adapted and name the expected
geometry or hierarchy benefit. Record the actual category mapping, mark
treatment, summary meaning, scale and physical layout. For a basic chart, check
the color combination, role of each stroke, point/summary crossings, category
gaps and guide space before adding a layer.
Render the real data; check complete-panel balance and inspect marks at final
size. Compare the accepted candidate and revision with equal dimensions, font
and numeric scales. An omitted-default comparison only tests preference over
that particular baseline. Separately assess whether the target paper's
layer hierarchy, compact grouping and cell proportions have transferred;
different data make this a design comparison, not matched performance evidence.
Disclose intentional normalization changes outside cosmetic comparisons.

Do not call the result better merely because it has more colors, thinner lines,
less grid, more empty space or no technical failures. If the main evidence
becomes a faint cloud, summary endpoints cannot be distinguished, or a colorbar
hides zero, revise the
specific encoding or layout. Also revise a tall/slender categorical region or
disconnected spacing when it impairs the intended comparison. Technical checks
support row/scale/export fidelity; visual inspection and user judgment assess
whether the design succeeds. A preference over a weak default, a known showcase
revision and a successful held-out first delivery support different claims;
none alone establishes publication-level quality or a causal Skill benefit.

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
