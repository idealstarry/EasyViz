# Acceptance record

Validated on **2026-09-29**. See the [final release QA](../evals/release-qa/README.md) for fresh forward tests, corrected defects, clean-runtime results and the released archive identity. This record separates numerical checks, actual visual inspection, and packaging evidence. It covers the listed cases and supported behavior; it does not establish universal reproduction quality.

**Design assessment correction:** the earlier legend review established usable decoding and technical fit. It did not establish that each revised panel was better than its baseline. User feedback rejected some revisions, and [comparative reassessment](../evals/design-value/critique.md) identifies dense top legends, unchanged unused margins, and unresolved data-to-color hierarchy. Keep the engineering checks below as correctness evidence; do not use their pass counts as evidence of scientific design quality.

## User requirements

| Requirement | Implementation and observed result |
| --- | --- |
| Source data boundary | All seven real-data cases start from prepared tables. General descriptive statistics and supported tests are performed locally; upstream bioinformatics software is not run. |
| Create and reproduce | Separate track references, with shared scientific, typography, physical export and review requirements. |
| Refined create figures | Three real-data create cases, including a controlled comparison of three designs on matched participant data. Refinement is assessed by the reading task; the baseline may remain preferable. |
| Reproduce without author code | Two fresh-agent image-data implementations, independent image specifications, preserved first renders, access logs and independent final reviews. |
| Final-size individual panels | Each output is a single panel. PDF/SVG dimensions and PNG resolution were measured; all text in the five featured real-data cases is 8 pt. No assembled manuscript figure is produced. |
| Configurable appearance | Fourteen palette presets, including three figure-sourced categorical selections and five explicitly derived continuous scales, physical layout presets, explicit renderer settings and custom-case settings. Cell-atlas uses the user-selected blue/amber/teal/pink set and uniform borderless marks. Its default remains 180 × 120 mm with 8 pt text. |
| Reusable support | Five-family renderer, a matrix/annotation recipe with an independent synthetic reuse test, four portable real-data cases, a custom synthetic forest case with changed-schema reuse evidence, and two focused helper skills. |
| Repository presentation | English README with purpose, a design-comparison preview and create/reproduce showcases, usage, setup and design; separate skill, plugin, example, evaluation and development directories. |

## Real-data showcases

| Case | Numerical evidence | Physical output | Visual review |
| --- | --- | --- | --- |
| Annotated inhibition, create | 5,776 retained source measurements; 400 displayed values exactly matched; 152 full-matrix means independently recomputed; source bytes match the earlier validated conversion | 180 × 160 mm; all text 8 pt; embedded PDF fonts; editable SVG; 300 dpi PNG | Actual preview inspected after the literature-color and external-caption revision; no clipped labels or unresolved overlap |
| Cell atlas dot plot, create | Complete 48-row source table compared with original TSV; 22,539 objects; within-depot percentages and pooled totals verified | 180 × 120 mm; all text 8 pt; same export checks | Actual PNG and rendered PDF inspected; default and resized/font-adjusted variant checked |
| Paired myeloid remodeling, create | All 2,256 prepared scores checked against workbook; 832 two-year paired differences and 32 summaries independently recomputed; same recipe on 592 five-year differences | Three alternative panels, each 180 × 125 mm; 8 pt; separate exports and caption | Independent task-based comparison: ledger modestly preferred for distributions; matrix for within-person correspondence; baseline preferred over matrix for individual magnitude/spread. No overall winner. |
| BMI violin, reproduce | All 864 original records verified; 858 available values used and 6 missing retained; independent review recomputed densities and checked all 8 SVG density bodies | 160 × 100 mm; all text 8 pt; same export checks | Current style adaptation independently reviewed in `qa.json`; original density choices remain unknown |
| Integration radar, reproduce | All 25 rates compared with original workbook; 3 valid zeros; independent review checked all exported data-vertex positions | 88 × 88 mm; all text 8 pt; same export checks | Independent review: `ready_with_notes`; explicit zero origin and standalone labeling are documented adaptations |

[Showcase validation data](../evals/showcase-validation.json) records the independent size/source checks. The two reproduce [review reports](../examples/README.md) include candidate hashes, concrete observations and uncertainties. Review is tied to those files; a new render requires its own assessment.

The historical microbiology and single-cell examples also pass their [numerical/export checks](../examples/validation-summary.json). Their implementations used author-code evidence and are not counted as no-author-code successes.

## Renderer checks

All **22 core renderer tests, 7 focused legend tests and 4 case-contract tests** pass. The release audit added coverage for statistical-unit aliases and literal/empty identifiers in custom recipes. Core checks cover physical PDF/SVG/PNG/TIFF dimensions and metadata, explicit composition denominators, known statistical results, independent and paired units, category capacity and ordering, duplicate/missing/nonfinite data, deterministic jitter, zero-area dots, custom color scales, clipping, missing glyphs, invalid reruns, and rejection of an OLS overlay on logarithmic axes. Five added regressions cover literal `NA`/`null` category names, crowded ticks and an 8 pt layout repair, oblique-label exclusions, invalid logarithmic limits, and a numerical-zero P value displayed as a bound rather than `p = 0`.

All five synthetic fixture specifications render successfully. These test code behavior; their appearance is not evidence for the richer design standard.

## Bounded transfer checks

The [generalization evaluation](../evals/generalization/report.md) ran **21 variants across 15 scenarios**: 8 successful transfers, 10 explicit data rejections, 2 explicit layout rejections, and 1 unsupported repeated-measures method. These are expected outcomes, not 21 successful plots. The [preserved baseline and findings](../evals/generalization/findings.md) show the defects discovered and repaired. The strict run has no unexpected outcomes.

Tested inputs include a 24 × 18 signed matrix, long labels with explicit canvas repair, 12-donor sparse composition with full-sample denominators, a 120-record sparse dot matrix, 5,000 observations on log axes, and nine unbalanced distribution groups. All successful outputs retain source values and 8 pt text. Same-axis horizontal/vertical tick collisions now invalidate QA; oblique text and other visual overlaps still require inspection. Sparse missing combinations and genuine zero-size dots both look blank unless a custom distinction is implemented. See [generalization scope](generalization.md) for how these checks differ from agent workflow or image-reproduction evidence.

A fresh agent using the skill, without reading existing examples/tests, produced the [synthetic cohort-effect forest](../examples/create/paired-effects/README.md) through a custom implementation. Its original 28 estimates and 56 interval endpoints independently match the exported SVG geometry within 0.000001 pt; it preserves 180 × 120 mm and Arial 8 pt. An independent reviewer found no required visual correction. A second 5-term × 3-cohort table changes all nine field names and input row order; all 15 estimates and 30 interval endpoints are retained at 180 × 100 mm and 8 pt. This demonstrates one additional geometry and one reuse variation, not arbitrary-chart competence. Access isolation was instructional, not enforced by the filesystem.

## Skill and plugin checks

The three skills pass the skill-creator validator. The generated `easyviz` plugin passes the plugin-creator manifest validator. Its normalized folder name matches the manifest name.

The ZIP is tested by extraction into a separate temporary directory and execution from a different working directory. The test covers the core renderer, four bundled real-data cases, the synthetic forest and its renamed-field variant, and the matrix recipe. Case PNG rerenders must match bundled previews pixel for pixel in the tested environment. The matrix test uses independent synthetic 4 × 4 inputs, leading-zero IDs, constant binary annotation, negative values and automatically calculated mean-axis bounds. The paired case checks all three previews and the separate five-year variant. The current outcome and archive identity are recorded in the linked report.

See [package validation](../evals/plugin-validation.json) for the archive checksum and exact scope. The archive contains no author plotting scripts, original full-paper archives, Gontijo dataset or unverified Angarola data. It includes source attribution and the permitted Massier crops/data. Copy case folders into a writable workspace before running scripts that write beside their inputs.

## Environment and limits

| Item | Validated version |
| --- | --- |
| Python | 3.12.2 |
| Matplotlib / NumPy / pandas | 3.11.1 / 2.5.3 / 3.0.5 |
| SciPy / Pillow | 1.18.1 / 12.3.0 |
| PyMuPDF / PyYAML | 1.28.2 / 6.0.3 |
| Main font | Locally available Arial; explicit fallback behavior is recorded in scripts |

The packaging test reused this Python environment and available fonts. It was not a fresh operating-system dependency install or a new Codex-session invocation. No marketplace publication or global plugin installation was performed. The final release pass additionally installs the declared runtime into a clean Python virtual environment; its actual result and software versions are recorded in the release QA report. SVG text requires the corresponding font on the assembly machine; PDF fonts are embedded.

No physical print proof was performed. Image-data evaluations used instruction-based isolation, not filesystem-enforced access denial. Unknown original KDE parameters, exact colors and radar padding remain unresolved; visual agreement does not establish equivalence of unseen analysis. The library currently demonstrates five featured real-data designs on two published data sources plus two historical adaptations, so additional scientific domains and figure geometries need their own cases.

## Literature colors and panel prose revision

The annotated-inhibition case uses colors grounded in Somerville et al. (2024) figures. The cell-atlas case now uses the user's selected blue/amber/teal/pink subset from Cruz Tleugabulova et al. (2024), Figure 2b, with borderless dots, bars, strips and matching legend symbols. Source records distinguish published PDF RGB values from EasyViz gradients. Titles, overview text and narrative footnotes are outside the create panels in caption.md. This rule applies to both tracks and overrides generic report-title conventions; titles require an explicit user request. The original reproduce evaluation artifacts retain their historical adopted specifications and reviews.

[Initial revision checks](../evals/palette-refresh.json) preserve the earlier palette/caption revision. [Earlier B style checks](../evals/style-review/report.json) verify the selected palette revision, unchanged data and area scales, physical dimensions, font sizes and borderless marks in that exported SVG. Its [independent review](../evals/style-review/independent-review.md) records that dots for counts such as 1, 2 and 5 are not reliably resolved in the low-resolution final-page preview. Those reports remain tied to their historical hashes; the later legend revision has separate evidence. No print-proof or universal color-vision claim is made.


## Legend proportions and transfer

[Four measured panels from two papers](legend-literature.md) informed the reusable layout rules. Their complete legend footprints, plot-region definitions, PDF coordinates and uncertainties are recorded; observed ratios are not universal targets. Both tracks and their reader/reviewer instructions now require assessing visual hierarchy in addition to fit.

The shared helper measures categorical, quantitative-size and continuous-color guides in physical units, records their complete envelopes and combined occupied area, and distinguishes available space from an explicitly reserved band. It preserves agreed type sizes and quantitative mappings. Seven behavioral tests cover actual PNG/SVG key geometry across display/export DPI, corrupt transforms despite unchanged stored areas, explicit placement, impossible fits, physical colorbars and combined footprint semantics. Export checks caught and corrected displaced symbols and size-dependent key/label misalignment.

The [ten-case legend evaluation](../evals/legend-transfer/results.md) has nine feasible renders and one correct `needs_revision` result for an impossible footprint. Inputs, 8 pt text, canvas and data plot bounds are identical in each before/after pair. It varies 2/4/8 categories, short/long labels, 88/132/180 mm widths, heatmap colorbars, two quantitative-size ranges and explicit placement. Two previously clipped long-label legends now fit without changing their canvas. Independent image findings are recorded in its [visual review](../evals/legend-transfer/visual-review.md).

Two custom recipes also use the canonical helper. In cell atlas, the bottom allocation decreases from 25.7 to 19.5 mm, with the freed space used for rows; the canvas remains 180 × 120 mm and text remains 8 pt. The 48 data-circle diameters, fills, numerical values and count-to-area mapping are preserved. The forest retains its plot geometry and both cohort-count variants. [Independent before/after review](../evals/legend-literature/after-review.md) and the frozen baseline distinguish these current outputs from earlier style reviews. This is bounded evidence for shared layout behavior, not a guarantee for arbitrary scientific panels.


## Design comparison rather than pass-count claims

The [paired-change case](../examples/create/paired-myeloid-remodeling/README.md) presents a competent box-and-points baseline and two substantive alternatives using identical data, canvas and typography. An [independent reviewer](../evals/design-value/paired-comparison.md) opened the final images before reading implementation or design rationale. The participant matrix preserves a person's identity across subtype rows; the distribution view instead prioritizes positional magnitude and summaries. Their relative value changes with the reading task. None of this establishes superiority over a carefully written standalone script.

All 832 changes and 32 summary rows were independently recomputed from the local source CSV, with workbook extraction separately verified. The second-input check uses Kerr five-year follow-up from the same publication, so it is a bounded reuse test, not another study. Actual image hashes, checked formats and remaining review limits are retained in the comparison record.

The [inhibition color experiments](../evals/design-value/inhibition-scale/README.md) preserve all data and compare the existing scale with a zero-anchored linear scale and a disclosed signed asinh scale. Linear zero anchoring clarifies sign but makes common values paler. Asinh reveals moderate-value variation while compressing high-value differences. Neither is installed as a global default, and the canonical inhibition output is retained. The [reusable decision reference](../skills/easyviz/references/design-decisions.md) records when to use or reject each pattern.
