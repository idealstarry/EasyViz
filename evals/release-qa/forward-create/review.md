# Review of the selected create panel

Status: **ready_with_notes**. Reviewer: implementing agent, self-review. One visual-design review pass; no visual correction was required. A later rerun replaced a deprecated Matplotlib argument without changing the design. No independent reviewer was available: an attempted numerical-auditor spawn failed with the session's agent-thread limit. This is not an independent review claim.

Inspected images: `panel.png`, `baseline_box_points.png`, `panel_pdf_render.png` (PDF rasterized by PyMuPDF at 144 dpi), and `panel_svg_render.png` (SVG rasterized by librsvg at 144 dpi). The full canvas was inspected in each image, not only a crop. The adopted specification is in `settings.json` and resolved values in `figure-settings.json`; `caption.md` was read separately.

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Scientific layers | Two week columns share an x scale; each protein has an upper blue Control row and lower amber Treatment row. Faint circles show spread; stronger diamonds and horizontal intervals show the median and IQR. | Show variation and typical changes across arms and weeks. | Retain. Caption defines every mark and the paired subtraction. |
| note | Individual point overlap | Some close observations overlap each other or the summary marks, as expected at this density; all 252 points are present and their spread is visible. | Preserve observations and participant variation. | Retain modest vertical jitter; exact values and participant IDs are supplied in plotting data. This view does not trace individuals across proteins or visits. |
| note | Facet labels | “Week 4” and “Week 12” identify the two data facets. No overall title, subtitle, footnote or letter is present. | Essential decoding text only. | Retain. |
| note | Legend and hierarchy | One shallow two-item guide sits above the facets. Its measured full bounds are 31.19 × 2.65 mm versus 13,104 mm² of data field. Reserved legend band is 154 × 8 mm. Filled swatches and data marks have no outlines. | Legible guide, preserved 8 pt font and data prominence. | Retain. No clipping or label collision observed. |
| note | SVG portability | SVG retains editable Arial text; the installed Arial font renders consistently with the PDF and PNG on this system. The font is embedded in PDF but not in SVG. | Arial 8 pt and editable vector text. | Keep SVG text; open on a system with Arial installed. |

## Design comparison

Preference: **candidate** (median/IQR with participant points). Both designs were inspected at identical 180 × 125 mm dimensions and the same values, colors, font, group order and horizontal scale. In the box-and-points baseline, whiskers and caps compete with the individual points, particularly for TNF and CCL2. The selected design makes the typical shift easier to locate through one stronger median diamond and removes redundant whisker extent while raw observations still show full spread. This is a task-specific visual preference, not a claim of universal superiority. The comparison exports are retained as review evidence, not additional requested manuscript panels.

## Numerical and export evidence

| Check | Status | Evidence |
| --- | --- | --- |
| Source preservation | passed | Copied input SHA-256 matches original. |
| Pairing and completeness | passed | 396 unique input rows; 24 donors; 252 valid follow-up/baseline pairs. No duplicate keys, arm changes, nulls or nonfinite values. |
| Missingness | passed | Six absent follow-up visits / 36 protein observations recorded explicitly. No imputation. |
| Derived changes and summaries | passed | Separate stdlib dictionary join and quantile implementation recomputed all 252 changes and 24 group summaries. Maximum absolute difference 4.44e-16. This was independent code, not an independent agent. |
| All points within axes | passed | Range −2.2031 to 1.5096 lies within the common −2.5 to 2.0 limits. Drawing counts total 252. |
| Physical vector dimensions | passed | PDF 179.999995 × 125.000004 mm; SVG 180.000000 × 125.000000 mm. |
| PNG | passed | 2126 × 1476 px at approximately 300 dpi; nearest-pixel quantization of the requested canvas. |
| Actual typography | passed | PDF contains embedded ArialMT; every extracted text span is 8 pt. SVG text specifies Arial and equivalent 8 pt in the point-coordinate viewBox. |
| Clipping and ticks | passed | Renderer text extents are within canvas; horizontal tick extents do not collide. Actual PNG, PDF and SVG renderings show no clipping, missing glyphs or unwanted text. |
| Independent human/agent review | not_checked | Attempted delegation hit the thread limit; self-review is disclosed. |
| Generalized reusable-renderer behavior | not_checked | This task used a custom script as allowed by the packaged chart-library boundary; no claim about other chart families or arbitrary data. |

Numerical details and exact missing participant IDs are in `verification.json`; full legend, text and axes measurements are in `layout-checks.json`.
