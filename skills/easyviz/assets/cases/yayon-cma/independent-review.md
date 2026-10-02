# Independent final visual review — Yayon CMA available-layer adaptation

**Status: ready_with_notes.** Reviewed the supplied candidate PNG and actual PDF/SVG exports at 96 dpi, against the adopted 210 × 111 mm, Arial 7.5 pt specification. No plotting code, tests, numerical QA or previous review was read.

- Two aligned 65-column by 10-row matrices appear in Fetal then Paediatric order; shared columns continue through the cosine bars and zero-line P circles.
- Both heatmaps use the visible 0–1 viridis guide; the middle bars and continuous guide cover −1 to +1 with a zero baseline.
- CCL21, CCL19, CXCL12 and CCL25 labels are orange; outlined spans are CCL13–CX3CL1 and IL34–TGFB3. The boxes stop above the upper matrix and do not imply a reconstructed tree.
- The three hollow-circle classes are visibly distinct and agree with the increasing-area legend; bars are filled without incidental dark outlines.
- Row labels, left group dividers, compact P legend and expression guide remain readable and subordinate to the matrix regions. No clipping or collisions were visible in the PDF/PNG views.

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| minor | SVG heatmap cell boundaries at 96 dpi | The librsvg 96 dpi rendering shows faint cell-boundary seams; the matching PDF and PNG renderings do not show this grid. The seams do not alter cell colors, order or layer alignment. | The two matrices should use the adopted filled-cell appearance consistently across exports. | Prefer the inspected PDF/PNG for assembly. If SVG is the delivery format, check the intended application and suppress rasterization seams if they persist. |
| note | Bottom gene labels | All 65 italic gene labels are visible, including the four orange labels. At 210 mm width, each column is approximately 2.6 mm wide; the labels are dense but separately traceable in the final-size PDF/PNG views. | Keep all adopted genes and Arial 7.5 pt at the frozen panel dimensions. | Retain the adopted dimensions/font. Use the vector PDF or 300 dpi PNG for final assembly; do not shrink this panel or its text. |
| note | Reference adaptations | Sub-Capsular is displayed as Subcapsular; Medullar is displayed as Medullary. The dendrogram and source panel letter are intentionally absent. The corrected final caption states that the unpublished tree was not reproduced and full-panel equivalence is not claimed. | Honor the adopted aliases, manuscript text convention and bounded reproduction scope. | Retain these declared adaptations and the separate source-attributed caption. |

The initially incorrect synthetic caption was reported and repaired. The reviewed final caption now identifies the Yayon source and explicit omitted-tree scope.

Actual export checks passed: one 210 × 111 mm PDF page; embedded ArialMT/Arial-ItalicMT; every extracted text span 7.5 pt; no text bounding box outside the page; 2480 × 1311 PNG at approximately 300 dpi. PDF/SVG previews are 794 × 420 pixels at 96 dpi. The JSON records candidate and preview SHA256 hashes and preview paths.

Numerical values and upstream analysis were **not checked**. These visual findings do not establish full-panel equivalence, statistical validation, aesthetic improvement or general effectiveness.

| Reviewed export | SHA256 |
| --- | --- |
| output/panel.png | `bb9ddb50000ae8fae36430d6bc191e368ba19ee950a418ec390915ddbf7898c0` |
| output/panel.pdf | `1e5e990da24678e890a578186580cb92766fdca9909aac08115f58b202b6ae1a` |
| output/panel.svg | `d5cd1b1c5280758728d70c9a739906813f3bd82cc8ef5a39cecf29bb00359f9b` |

Preview evidence: `/private/tmp/easyviz-yayon-review-51hzx9nx`.
