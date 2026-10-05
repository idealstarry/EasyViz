# Independent visual review — basic panels v0.4.3

**Status: ready_with_notes.** No critical, major, or minor visual requirement failure was found. This status covers the supplied five candidates and five transfer examples at 110 × 88 mm with adopted Arial 8 pt typography. It does not establish numerical correctness, generalization, causal model advantage, or publication acceptance.

I individually opened all 15 baseline/candidate/transfer PNG panels and all 15 corresponding PDF-derived 96 dpi previews. This was one independent visual inspection, with no rerender requested. The previews support intended-size readability judgment; monitor scaling and a physical print were not checked. Candidate specifications, baseline and transfer specifications, settings, QA records, and the five separate candidate captions were read. No implementation code was consulted.

| Panel | Preference | Visible evidence and reading task | Transfer assessment |
| --- | --- | --- | --- |
| replicate-bars | candidate | Mean heights remain easy to compare; unfilled blue bars reduce gray mass and expose raw points and dark intervals. Zero baseline, wrapped labels, and five category gaps read cleanly. | Four mutEJ conditions and the larger range remain clear; no clipping or spacing conflict. |
| paired-scatter | no_clear_preference | Both palettes distinguish groups and retain the same paired coordinates, log ticks, point size, and compact top legend. Candidate blue/coral is clean, but baseline cyan/orange is similarly readable. A color or opacity change alone does not establish a lookup advantage. | Single blue group needs no categorical legend and remains readable. |
| cohort-box | candidate | Narrow unfilled boxes keep median/IQR/whiskers visible while beeswarm rows separate dense Kerr observations. The candidate better balances summaries and raw observations for this task; the baseline gives broader filled summaries more prominence. | The fourth purple cohort fits with readable labels, summaries, and distinct point rows. |
| cohort-violin | candidate | Crisp outlines and light interiors preserve shape and point contrast. Added Q1/median/Q3 boxes make summaries directly readable; this preference partly comes from added information and cannot be assigned solely to cosmetic styling. | Four silhouettes and summary boxes remain separate and readable; the purple cohort fits. |
| depot-heatmap | candidate | Low-to-middle blue differences are easier to see than in the very pale baseline, with the same fixed subtype order and high-cell pattern. All 16 row names and three column names read clearly. | Count ticks and the Source objects label correctly distinguish the transfer scale visibly; wider ticks still fit. |

The panels retain basic chart structures, clear axes, and bright restrained colors without in-panel narrative. Solid points and matching scatter legend dots are borderless. Outline bars and boxes and outlined violin shapes are explicit adopted geometry, rather than accidental filled-mark edges. The low-opacity violin interiors look intentionally light behind crisp lines, not blurred.

Scatter hierarchy is sound: the supplied complete legend bounds are approximately 44.5 × 3.0 mm versus a 95.1 × 69.2 mm data region. Heatmap label space is justified by the long subtype names; the data region is approximately 56.9 × 73.8 mm versus a 9.8 × 32.6 mm complete colorbar envelope. Its 30 × 2 mm bar with five labeled ticks is readable and remains secondary to the matrix. These measured relationships support this layout judgment, not a universal percentage rule.

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Scatter middle and upper-right clusters | Some neighboring marks touch or overlap in both versions. Individual point counting is limited, while coordinate/group reading remains clear. | Preserve scientific coordinates and the adopted paired-data task. | Retain coordinates and the existing separate-caption count; no plot revision is required. |
| note | Violin baseline comparison | Only the candidate contains explicit quartile and median boxes. | Separate information changes from cosmetic claims. | Report the inner summaries as added content; do not credit their gain solely to color/opacity. |
| note | All transfer directories | No separate transfer caption is supplied. Main captions describe HDR with five treatments, 127 participants/two groups, three BMI cohorts, or percentage shares. | A standalone delivered variant needs a matching separate caption. | If transfers become standalone manuscript panels, add variant-specific captions outside the images. This does not block the present visual evaluation. |
| note | Audit scope | Images and renderer QA do not independently prove source values or summary calculations. | State only supported conclusions. | Keep this review separate from numerical verification and model or publication claims. |

| External check | Result | Evidence and limit |
| --- | --- | --- |
| PDF page dimensions | passed | Independently inspected all 15 PDF MediaBoxes: 311.8110 × 249.4488 pt, equivalent to 110 × 88 mm. |
| PNG dimensions | passed | Independently inspected all 15 PNG headers: 1299 × 1039 px. Supplied QA records approximately 300 dpi. |
| PDF font embedding | passed | All 15 PDFs contain subset ArialMT BaseFont references and FontFile2 resources. |
| Agreed 8 pt typography | passed from supplied records | All settings identify actual Arial without substitution and 8 pt axis/tick/legend/annotation text; content-stream type sizes were not independently remeasured. |
| Clipping, tick overlap, glyphs | passed | Empty supplied QA issue arrays agree with the independent visual inspection. |
| Five original candidate captions | passed | Directly read; source, meanings, methods, and caveats remain outside the image. Violin quartile-box meaning is explicit. |
| Transfer captions | not_checked | Not supplied; required only if the transfer variants are independently delivered. |
| Numerical/statistical correctness and counts | not_checked | No independent source-data or statistic recalculation was performed. |
| Source citations/licensing, color-vision simulation, physical print | not_checked | Outside this visual audit. |

No mandatory visual correction or additional render is warranted by this inspection. The useful follow-up is variant-specific captions if transfer outputs become standalone deliverables. Keep the scatter comparison as no_clear_preference and the violin preference qualified as content plus style. **Status: ready_with_notes.**
