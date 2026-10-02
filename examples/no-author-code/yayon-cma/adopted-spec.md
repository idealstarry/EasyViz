# Adopted source-backed layer specification

Track: reproduce. Inputs: independent image-only reading, original reference
crop, official article caption and Fig. 3 Source Data. No author code.

| Layer | Adopted behavior and evidence | Status |
| --- | --- | --- |
| Two matrices | Fetal then Paediatric; original worksheet gene/region order; all 1,300 supplied normalized values; shared viridis 0–1 scale. | retained |
| Shared columns | Literal gene IDs align through both matrices and the middle summary; 65 source columns. | retained |
| Region names | Source IDs retained for joining; explicit Sub-Capsular→Subcapsular and Medullar→Medullary display aliases only. | adapted spelling |
| Supplied bars | Source cosine values, full −1 to +1 range, coolwarm, zero baseline; no cosine recalculation. | retained |
| Interaction circles | Supplied corrected P; strict P < .05/.01/.001 classes at y=0; hollow circles with geometric areas 4.5/10/18 pt². | retained encoding; adopted physical sizes |
| Orange labels | CCL21, CCL19, CXCL12 and CCL25 from image and source caption. | retained |
| Outlined ranges | CCL13 through CX3CL1 and IL34 through TGFB3 from image; source caption identifies age-divergent clustered genes. | retained; boxes stop at the upper matrix because tree is absent |
| Dendrogram | Source workbook supplies no topology or numerical heights; no clustering or pixel-derived quantitative tree. | omitted; incomplete original layer |
| Panel letter/title | User manuscript-panel convention omits the source letter and narrative text. | intentionally adapted |

Freeze: 210 × 111 mm, Arial 7.5 pt, 300 dpi; fixed physical rectangles in
`spec.json`. The first rendered review corrected only the expression-guide
collision model; it did not change the adopted dimensions, fonts, data or
matrix geometry. Guide/text checks use actual rendered text and key boxes.
The independent reading estimated the reference's relative proportions, but
did not establish original mm, point sizes or numerical tree geometry.

Scope remains source-backed reproduction of available layers with explicit
adaptation. Passing source/export/geometry checks does not make the missing
dendrogram complete or certify the upstream statistical analysis.
