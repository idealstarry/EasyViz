# Independent Create refinement review — EasyViz 0.4.3

**Final status: `ready_with_notes`; formal review passes: 2 of at most 3.** Current candidate remains preferred for all three actual published baselines. The only first-pass minor, faint seams between pale heatmap cells, is resolved. Point-size, truthful KDE end shape and claim-scope notes remain.

## Round 2: final images and seam correction

Actually reopened both final heatmap PNGs and their two nominal 96 dpi PDF previews, plus the published old heatmap. The adopted border changed from `#D4E2EA` to `#B7CAD7`, retaining 0.35 pt width. The stronger seams are visible in very pale neighboring cells at nominal preview size and still sit below the numbers and intensity layer. Neither candidate percentages nor transfer integer counts are crowded or masked. There is no added heavy grid texture and no new critical, major or minor visual conflict.

Box/violin visual parameters are unchanged. Independently checked all four PNG and four PDF-preview hashes against round 1: each is byte-identical, so their original actual-image review remains valid. Frozen published baselines are also byte-identical. Exact final hashes and the full first-pass report are preserved in `independent-review.json`.

| First-pass finding | Final outcome |
| --- | --- |
| Pale heatmap seams faint at 96 dpi — minor | Resolved after contrast adjustment and actual inspection of both PNG/PDF previews. |
| Nominal 2 pt observations are fine at reduced size — note | Retained. They are individually visible in these examples, but should not be shrunk further to force future data into the same layout. |
| KDE extrema have flat closures — note | Retained. The specified observed-range trim is truthful; cosmetic tail fabrication is inappropriate. |
| Aliases and 48 cell numbers give an annotated table-like heatmap — note | Retained. They are legible for this exact-lookup task and cannot become a universal large-heatmap default. |
| Literature mechanisms versus CNS/model claims — note | Retained. Improved specific examples do not establish broad journal acceptance or a causal model benefit. |

## Final numerical/export evidence, separate from aesthetics

Read the supplied final `evals/create-refinement-v0.4.3/validation.json`: status pass, 15 runs. Its six relevant candidate/transfer records retain 129/185 distribution observations and reported raw-coordinate/quartile checks, plus all 48 heatmap values/order and global linear 0–40 and 0–2700 scales. The reviewer did not independently recompute those source/statistical assertions.

Independently computed current PNG/PDF/SVG hashes for these six exports; every hash matches its final validation record. These records report the unchanged 110 × 88 mm dimensions, embedded ArialMT, 8 pt text, preserved SVG text and 300 dpi PNG. Round 1 also independently inspected actual PDF dimensions/font embedding. The `/tmp` numeric audit records below remain historical first-pass evidence; the final-state validator supplies the terminal image identities.

Physical print calibration, unseen-agent performance, cross-model causal effects and journal acceptance remain unchecked and outside this readiness claim. No change of aesthetic judgment was inferred from a numerical validator.

**Status: `ready_with_notes`.**

---

## Round 1: preserved historical review

First formal visual review, round 1. **Current candidate preferred in all three comparisons; ready with notes.** This covers these six renderings, not CNS acceptance or a measured causal improvement from using the skill.

## Scope and independence

Actually opened 17 images: the three published, user-criticized candidate PNGs frozen in `before/`, the three current candidates, their three transfer PNGs, six nominal 96 dpi PDF previews, and the supplied scWAT p. 4 Fig. 2 and PROGENy p. 6 Fig. 4c page images. Read all six adopted specs and captions plus the three frozen old specs. No implementation scripts or other agents' visual reports were consulted. The independent preferences were sent to the parent before supplied numeric/export evidence was read. A `visual_review` field embedded in the heatmap audit was ignored; only its numeric/export records are cited below.

All PNG comparisons have the same 1299 × 1039 pixel canvas and approximately 300 dpi metadata. The six current PDFs have the declared 110 × 88 mm page dimensions. The 96 dpi previews expose nominal-size screen reading limits; a physical print proof was not performed.

## Actual baseline comparison

| Panel | Preference | Visible benefit | Remaining limitation |
| --- | --- | --- | --- |
| Cohort box | Candidate | The side observation lane uncovers median, quartile boundaries, whisker stems and caps. Tightened category spacing and smaller opaque bright points avoid the old point/summary collision. | Same-color proximity associates lane and box, but grayscale pairing should be reassessed. Small points are visible at 96 dpi and should not be reduced further. |
| Cohort violin | Candidate | Thin neutral density outlines read behind colored IQR boxes and black medians. The old broad colored envelope and centered raw points competed with the summaries. Four-cohort transfer preserves the new separation. | Trimmed density extrema still have flat closures. The raw-point lane adds another reading column, so this remains more layered than the PROGENy reference. |
| Depot heatmap | Candidate | Compact cells shorten across-depot lookup; SC/OM/PV are separated; 48 numeric labels recover precise small values that hue alone cannot distinguish. Four-digit transfer counts also fit. | Some seams between pale cells are faint in the 96 dpi preview. This is an annotated, table-like heatmap; it is not a universal large-matrix template. |

The side lanes stay closest to their own summary, share category color, and do not visibly form additional labeled cohorts. Their offset is explicitly explained in both captions. In the four-cohort probes, neither the Kerr nor Arner, E lane collides with its summary or the adjacent category. The nominal 2 pt points remain visible at 96 dpi, including sparse extrema; dense regions read as finer point clouds rather than large opaque stacks.

The neutral violin outline is visible, not missing, in the small PDF previews. Its thin gray boundary remains subordinate to the colored IQR and dark median. This now transfers an observable PROGENy design mechanism rather than simply copying a palette. The flat extrema are a truthful consequence of the declared KDE trim and should not be cosmetically extended.

The heatmap's cell numbers are legible and contained. `0.058`, `0.04` and the four-digit count labels do not touch neighboring cell text. The short header aliases are defined in the separate caption. One global linear sequential scale retains quantitative meaning; 48 value labels have a defensible exact-lookup role here. The supplied numeric record gives a 9.53 × 4.45 mm cell size, approximately 2.14:1. A compact rectangle is justified by the label width; square cells are not a universal requirement.

## Literature mechanisms and claim limits

scWAT Fig. 2 provides observable examples of crisp outlines, compact arrangements and distinct raw-point/summary/uncertainty roles. PROGENy Fig. 4c provides thin neutral density boundaries with more prominent categorical summary encodings. These mechanisms are useful; their statistical layers, different data, group counts and panel sizes are not aesthetic or performance targets to copy wholesale.

The current examples visibly learn more than palette and hollow marks. Their source-specific task is still straightforward. Compared with the paper samples, violin closures and generous outer space remain noticeable. Adding complexity to disguise a simple three-cohort task would not establish better scientific design. No unaided-agent, model comparison or journal-level aesthetic benchmark was supplied.

## Actionable findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | cohort-box and cohort-violin; candidate and four-cohort transfer observation lanes | At 96 dpi the nominal 2 pt marks remain individually visible, including separated outliers, but dense portions of Kerr and Arner, E are visually fine. Their matching color and immediate proximity associate them with the neighboring summary; caption explicitly defines the categorical offset. | All observations remain usable while summaries stay visible; point lanes must not imply extra categories. | Keep the present point size as a lower bound for these examples and preserve the explicit lane explanation. Do not shrink points to make future crowded data fit; reconsider the layout instead. For grayscale use, reassess the paired-lane association. |
| note | cohort-violin; neutral KDE outline and observed-range ends | The gray outline is visible in PNG and 96 dpi PDF while the colored IQR and black median read first. The extrema have flat closures, most evident in the Krieg silhouette, unlike several pointed PROGENy shapes. | Density must remain faithful to the adopted Scott KDE and observed-range trimming; aesthetic adaptation cannot fabricate density tails. | Retain these truthful endpoints and state the rendering limitation in design guidance. A future request for smoother tails requires an explicit, scientifically appropriate KDE/support decision, not cosmetic path editing. |
| minor | depot-heatmap; pale neighboring cells in candidate and count transfer | Fine blue-gray seams are visible at full-resolution PNG, but become faint between near-white low-valued cells in the 96 dpi PDF preview. Cell-center numbers and row labels still permit correct tracking; no text overlaps or lost rows were observed. | Clear row/cell boundaries should support crisp, organized reading without dominating the values. | For a further proof, consider slightly increasing seam color contrast at the same 0.35 pt width, then inspect the pale-cell rows at nominal size. Do not introduce a heavy dark grid or reduce the font. |
| note | depot-heatmap; SC/OM/PV headers and 48-value layer | All three aliases are clearly separated and are defined in the caption. Percentage labels include 0.058 and 0.04 without crowding; transfer four-digit counts remain inside their cells. The numbers make the image more table-like than a pattern-only heatmap. | Short display labels must preserve source identity, and value annotations must serve an explicit reading task. | Keep aliases and labels for this small exact-lookup example. Do not generalize 48 annotated cells as a default for large heatmaps; require sufficient physical cell size and an exact-value reading need. |
| note | All examples; claim scope and literature learning | The new renderings visibly apply hierarchy and proportions beyond a palette swap. The source papers have different scientific mappings, category counts, uncertainty layers and physical layouts. A few improved examples cannot measure an agent-level causal benefit. | An improvement claim must remain tied to actual compared images and must not assert CNS acceptance or model generalization. | Describe these as improved basic single-panel examples with explicit layer decisions. Keep paper mechanisms and their applicability limits in Create guidance; do not advertise verified universal CNS quality. |

## Numerical and export evidence, separate from aesthetics

- **Source values, summary definitions and point coordinates: passed.** /tmp/easyviz-distribution-refinement-check.json: four records report unchanged 129/185 raw observations, inclusive quartiles, median/whisker values and KDE evaluation geometry after width normalization; point overlap/spacing records show zero violations. Supplied numeric evidence read after the independent visual preference was already sent to parent; not independently recomputed by this reviewer. Geometry comparison re-renders the frozen prior specs with the current renderer, rather than parsing frozen historical exports.
- **Heatmap source values, order, linear norm and annotations: passed.** /tmp/easyviz-v043-heatmap-refinement-audit.json records: 48 values each, 16 by 3 order, 0–40 and 0–2700 global linear limits, 48 source-derived text labels and 17 vector seam segments. Supplied record values only; not independently recalculated. Its visual_review field was ignored: this review had already recorded its preference before this evidence was read.
- **PDF physical dimensions and embedded font: passed.** Reviewer ran pdfinfo and pdffonts on all six actual PDFs: one page each, 311.811 by 249.449 pt (110 by 88 mm within printed rounding), embedded ArialMT CID TrueType with Unicode. Independently inspected by reviewer.
- **PNG size, DPI and SVG editable typography: passed.** Reviewer inspected image metadata for before/candidate/transfer: 1299 by 1039 pixels, DPI 299.9994; six current SVGs contain Arial and font-size 8px text styles. Supplied export records confirm text retained, 8 pt PDF text and 110 by 88 mm SVG dimensions. PNG metadata and SVG styles independently inspected; exact PDF text size/SVG physical dimensions use supplied export records.
- **Nominal-size PDF reading: passed.** Reviewer actually opened all six 416 by 333 px PDF previews marked 96 dpi, alongside full-resolution PNGs. No clipped label, numeric collision, lost glyph or illegible essential axis text was observed. Visual screen preview inspection only; not a calibrated physical print proof.
- **Cross-model causal effect, broad unseen-data generalization, calibrated print proof or journal acceptance: not_checked.** No such experimental or physical evidence supplied. Outside the narrow visual refinement readiness claim.

The reviewed PNG/PDF hashes match those in the supplied numeric/export records. Exact reviewed image identities are in `independent-review.json`; any later image change requires an actual re-inspection within the three-round review limit.

No critical or major visual conflict was found against the adopted specifications. The remaining seam contrast issue is minor; point-size, trimmed KDE shape and claim scope remain explicit notes. The quantitative checks are accepted only within their documented scope, without pretending the reviewer independently recalculated them.

**Status: `ready_with_notes`.**
