# Image-only reading of panel f

Inspected input: `/private/tmp/easyviz-v042-yayon-fig3f.png`, a 1200 × 574 pixel raster. The selected region is the entire supplied cropped panel f. I opened the actual image and enlarged crops of that same image to check labels and the middle band. I did not inspect implementation, workbooks, source data, runtime or Git files, author code, templates, previous reproductions, captions, or methods. The local reference-reader skill was the only non-image task input read.

The 65 gene labels and ten row labels are legible. The dendrogram has no visible scale. Small partial black fragments at the upper image boundary are not identifiable. All bounds and height ratios below are approximate raster observations; they do not establish mm, point size, DPI, or the original canvas.

| Property | Description | Evidence state | Source | Uncertainty |
|---|---|---|---|---|
| Arrangement | From top to bottom: dendrogram, Fetal heatmap, cosine-similarity bar strip, Paediatric heatmap, vertical gene labels. Bold **f** at upper left. | observed | Whole panel | No caption or study context supplied. |
| Shared columns | 65 equal-width gene columns align through the two matrices, bar strip, and tree leaves. | observed | Matrices, bars, tree, bottom labels | Selection and ordering rule unknown. |
| Row order | Both matrices use Capsular, Subcapsular, Cortical level 1, Cortical level 2, Cortical level 3, Cortical CMJ, Medullary CMJ, Medullary level 1, Medullary level 2, Medullary level 3. | observed | Left row labels | CMJ is not expanded. |
| Upper heatmap | Bounds approximately `[0.147, 0.136, 0.999, 0.395]`; height about 149 px. | observed | Fetal matrix | Approximate cell-edge locations. |
| Lower heatmap | Bounds approximately `[0.147, 0.599, 0.999, 0.861]`; height about 150 px. | observed | Paediatric matrix | Approximate cell-edge locations. |
| Cell layer | Narrow solid-color cells, subtle internal boundaries, short column ticks below matrices, no cell values printed. | observed | Heatmap bodies | Some fine edges could be raster antialiasing. |
| Relative heights | Heatmaps have equal height; middle strip is about 0.67 of one matrix height; tree about 0.38. About 8 px separates the strip from each matrix. | observed | Layer boundaries | Approximate ratios, not physical dimensions. |
| Expression scale | Dark purple → blue/teal → green → yellow, with numeric key 0, 0.5, 1.0 and heading **Mean expression in group**. | observed | Bottom-left key | Palette name, expression units, and scaling method unknown. |
| Expression legend sharing | One visible expression key appears to apply to both matrices. | inferred | Single key and matched matrix hues | Shared normalization is not explicitly confirmed. |
| Expression legend footprint | Full footprint about `[0.023, 0.878, 0.128, 0.990]`; color rectangle alone about `[0.043, 0.932, 0.113, 0.950]`, roughly 11 px high. | observed | Bottom-left legend | Text extends outside the rectangle; approximate bounds. |
| Cosine strip | Bounds about `[0.147, 0.409, 0.999, 0.587]`, y approximately 235–337 px; baseline about y 286 px. Scale ticks are 1.0, 0.5, 0, −0.5, −1.0. | observed | Middle band | Compared vectors are not defined. |
| Bars | Bars grow upward or downward from zero, align with genes, and leave thin white gaps. Many positive bars nearly reach 1.0. Some bars toward the right are negative. | observed | Middle data marks | Precise values and tiny-versus-zero bars cannot be recovered. |
| Cosine color key | Thin vertical key beside the band: red at +1, pale/white near 0, blue at −1. Its rectangle is about x 161–171, y 235–337 px; the full footprint includes tick text and the rotated label farther left. | observed | Middle-band left scale | Exact palette unknown. Key height is about 0.68 of a matrix height. |
| Significance legend | **Interaction effect (P value)** has three hollow black circles increasing in size for `<0.05`, `<0.01`, `<0.001`. | observed | Far-left middle legend | Exact diameters and statistical calculation unknown. |
| Significance placement | Hollow white-centered circles all lie on the y=0 line at selected genes; they are not at bar tops. Their sizes vary. | observed | Middle zero line | Exact P values, per-gene classes, and relation to cosine similarity unknown. |
| Significance legend footprint | Full footprint about `[0.002, 0.420, 0.091, 0.584]`. Circle glyph heights are roughly 7–12 px. This is a size legend. | observed | Far-left middle legend | No evidence of sharing beyond this cropped panel. |
| Tree | Thin hierarchical branches above the Fetal matrix. Large connecting branches are light blue; small branches have several colors, including orange, green, red, purple, teal, and olive. Bounds about `[0.147, 0.036, 0.999, 0.136]`. | observed | Top dendrogram | Colors do not establish category meaning. |
| Tree heights | Higher branches connect larger leaf sets; no numeric height scale or distance label is shown. | observed | Top dendrogram | Exact merge heights, metric, linkage, clustering input, cut threshold, and leaf-order method unknown. |
| Central outline | Black rectangle around CCL13, CCL3, CCL28, CX3CL1, spanning tree to gene labels; bounds about `[0.527, 0.101, 0.580, 0.981]`. | observed | Center black box | Meaning and selection rule unknown. |
| Right outline | Black rectangle around IL34 through TGFB3, spanning tree to gene labels; bounds about `[0.867, 0.082, 0.999, 0.981]`. | observed | Right black box | Meaning and selection rule unknown. |
| Orange labels | CCL21, CCL19, CXCL12, CCL25 are orange. | observed | Bottom labels | Reason for emphasis unknown. |
| Text | Row labels and legends are regular dark sans-serif; gene labels look italic and rotate roughly 90°, read bottom to top; **f** is bold and larger. | observed | Labels throughout | Exact face and point size unknown. |
| Layer overlap | Significance circles overlay the zero line. Black rectangles overlay tree, matrices, middle strip, and label area. | observed | Overlap regions | Exact rendering order is not available. |

The matrix begins about 15% from the left edge and extends nearly to the right boundary. The left margin contains age labels, row labels, the significance legend, and the cosine key. The bottom margin contains gene labels and the expression key.

## Observable gene order

Left to right, preserving the readable label spelling:

1. CXCL1
2. IL1RAP
3. CXCL6
4. IL1B
5. TNFSF12
6. IL1RN
7. TNFSF9
8. TNFSF11
9. CXCL10
10. IL7R
11. CD70
12. FLT3LG
13. IL23A
14. CCL20
15. CCL1
16. IL6ST
17. EBI3
18. CXCL11
19. CCL21
20. IL15
21. TNF
22. CXCL16
23. LTA
24. TNFSF13B
25. CCL19
26. IL4R
27. CD40LG
28. CXCL9
29. CCL22
30. CCL13
31. CCL3
32. CCL28
33. CX3CL1
34. CSF1
35. CCL4
36. CXCL13
37. IL12B
38. CXCL14
39. TNFSF13
40. IL6R
41. XCL1
42. IL18
43. XCL2
44. TNFSF14
45. CCL17
46. CCL5
47. CCL18
48. TNFSF10
49. IL15RA
50. IL17RE
51. CXCL8
52. CXCL3
53. BMP8A
54. CXCL12
55. CCL25
56. IL34
57. IL33
58. CCL2
59. IL1R1
60. BMP7
61. SPP1
62. CCL14
63. GDF11
64. IL1R2
65. TGFB3

IL7R and IL17RE are separate, readable labels. No source table was used to resolve them.

## Observable significance-circle presence

Hollow circles are visible at CXCL1, CXCL6, TNFSF12, IL1RN, CCL20, CCL1, EBI3, IL4R, CCL22, CCL13, CCL3, CXCL13, TNFSF13, CCL17, TNFSF10, IL1R1, SPP1, CCL14, IL1R2, and TGFB3. This is a reading of visible circle presence only. Individual threshold classes and exact P values are not assigned from the raster.

## Required data meanings and important unknowns

The plot requires gene identity and order; two age groups; the ten named region groups; mean expression per gene, region, and age group; a cosine similarity per gene; interaction-effect P values or categories; and a defensible dendrogram. Scientific interpretation additionally requires the expression normalization scope, compared cosine vectors, interaction model and test, adjustment procedure, sample units, age ranges, and the meaning of the orange labels and black boxes.

The image alone does not supply gene selection rules, tree distance metric or linkage, precise tree heights, clustering input, branch-color thresholds, or leaf-order rules. A visible tree can support approximate visual topology but cannot establish those methods. No exact numerical values or scientific selection criteria have been reconstructed.
