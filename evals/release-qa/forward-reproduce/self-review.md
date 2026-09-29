# Visual review, render pass 1

Reviewer role: main-agent self-review. Opened reference.png, panel.png, pdf-render.png and svg-render.png with the image viewer. The latter two are renders of the serialized vector exports, not re-exports of the in-memory canvas. Considered the declared 180 × 125 mm and 8 pt sizes, then enlarged for glyph and mark details.

| Severity | Location | Evidence | Requirement | Action |
|---|---|---|---|---|
| note | Entire panel | Eight ordered rows and eight marker columns preserve the reference orientation; two original separators remain | Follow source order and retain useful grouping | No repair needed |
| note | Missing cells | Three gray crosses are visually different from the two empty zero-area locations | Distinguish unmeasured from measured zero | Confirmed against source and caption |
| note | Legends | Color guide at right; three proportional area keys below; presence key lower left | Necessary decoding keys with balanced prominence | Individual key footprints remain secondary to matrix |
| note | Text | Long population labels, vertical marker labels, colorbar and keys fit without clipping | Arial 8 pt in fixed canvas | Actual PDF spans are all Arial 8 pt |
| note | Pale dots | Near-zero expression and low fractions naturally yield pale or small dots | Preserve source values and reference style | Retain; do not exaggerate areas or recolor source selectively |
| note | Empty-cell key | Outlined empty swatch explains zero without adding nonzero circle area | Correct zero area | Caption explicitly identifies decoding swatch |

No critical or major visual finding in this inspected candidate. No cosmetic correction was required. Numerical/export checks are independently recorded in export-checks.json. This self-review alone is not independent image-only evaluation evidence; an independent final reviewer has also been requested.
