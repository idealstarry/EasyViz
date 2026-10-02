# Independent review — original paired-effects panel

Scope: one visual review pass of the original 28-row candidate. The reviewer opened `panel.png` before forming findings, then compared it with the supplied request, source table, saved settings, caption, and export files. No reference image exists or was required. No author or renderer code, other examples, tests, variants, or evaluation outputs were inspected.

## Findings

| severity | location | evidence | requirement | action |
| --- | --- | --- | --- | --- |
| note | Overall panel | The opened candidate visibly contains all 14 source terms in order, two separately aligned estimates per term, and four labeled domains with clear spacing. The shared zero line, effect-axis label, ticks, and cohort legend decode the layers. No clipped text, colliding marks, missing glyphs, or forbidden title, subtitle, panel letter, or prose footnote was visible. | Preserve source order, cohorts, domains, interval display, and the manuscript panel text policy. | No visual revision required for this candidate. |
| note | Points, intervals, legend, and grid | Blue Discovery marks occupy the upper positions and amber Replication the lower positions. Point size is constant; their fill-only styling agrees with the legend. The light grid remains behind the colored intervals and dots, and the zero line is easy to distinguish. The approved colors remain readable against white and distinct from each other. | Use the approved stable colors, borderless fills and matching legend symbols, separate cohort positions, and a common zero reference. | No revision required. |
| note | PNG dimensions | The PNG is 2125 × 1417 px with 299.9994 dpi metadata. Its metadata-derived size is approximately 179.917 × 119.973 mm; the deviation from the nominal 180 × 120 mm is under one pixel in each dimension. The PDF and SVG have the requested exact nominal page dimensions. | Export an individual 180 × 120 mm panel. | Place the PNG at the explicitly requested 180 × 120 mm if used in a layout, or use the dimensionally exact PDF/SVG. This is normal raster quantization, not a required plotting revision. |
| note | SVG portability | SVG text is editable and specifies Arial. The PDF independently contains embedded Arial and Arial Bold fonts. | Arial 8 pt; a recorded fallback only if needed. | Use the PDF for portable fixed typography. SVG viewing/editing on another system requires Arial or an intentional substitute. |

No critical, major, or minor visual conflict was found in the supplied candidate.

## Independent numerical and export checks

| status | check | evidence |
| --- | --- | --- |
| passed | Source identity | SHA-256 calculated directly from the input CSV is `d18da70f4c6c87a17cf2e715cc15924972297e9783e9c75ce32c6ac0b36887d3`, matching the supplied provenance. |
| passed | Complete source-to-exported-row correspondence | Independent CSV parsing found 28 source rows and 28 plotting rows, with 28 unique `(term_id, cohort)` keys in each and no missing or extra key. All `estimate`, `ci_lower`, `ci_upper`, `n`, and `row_order` values compare numerically equal; term/domain/cohort strings, colors, and source-line references also match. |
| passed | Asymmetric supplied intervals | 27 of the 28 source intervals are asymmetric around their supplied estimates; all 56 lower/upper values are preserved in the plotting CSV. The remaining source interval is symmetric and is also preserved. |
| passed | Visible term order and grouping | The PNG and SVG text include the 14 labels in source `row_order`, with Immune, Metabolism, Tissue remodeling, and Cell maintenance in source order. |
| passed | Cohort counts and interpretation | Source counts are 42 for Discovery and 37 for Replication; the visible legend agrees. The caption explicitly states independent participants, constant dot size, descriptive counts, synthetic fixtures, and that interval overlap is not a test between cohorts. It describes supplied endpoints without claiming an upstream analysis. |
| passed | Direct SVG marker styling | The SVG contains 30 colored `<use>` elements: 28 plotted marks plus two legend symbols. Their styles are exclusively `fill: #2581b9` or `fill: #df9a3c`, with no marker stroke; the corresponding marker definitions do not add strokes. |
| passed | PDF page size and page count | `pdfinfo` reports one page. Direct PDF MediaBox extraction gives `[0, 0, 510.2362204724, 340.157480315]` pt, equivalent to 180 × 120 mm to serialization precision. |
| passed | Actual PDF fonts and size | `pdffonts` reports embedded subset CID TrueType `ArialMT` and `Arial-BoldMT`. Independent decompression and inspection of PDF content streams finds only font size `8` in text-font operations. |
| passed | SVG dimensions and text | The actual SVG root is 510.23622 × 340.15748 pt with the same-sized viewBox, equivalent to 180 × 120 mm to serialization precision. All 26 text nodes specify Arial and 8 user units; with this point-sized viewBox, these correspond to 8 pt. Domain labels use bold weight. |
| passed | PNG size and resolution | Direct PNG IHDR/pHYs parsing gives 2125 × 1417 px at 299.9994 dpi. The nominal 300 dpi target entails fractional pixel dimensions; each actual dimension differs by less than one pixel. |
| not_checked | Exported SVG interval coordinate inversion | This reviewer compared source values with the exported plotting table, not every rendered SVG endpoint coordinate. The implementing agent is conducting that distinct check. The `numeric-qa.json` artist-check assertion was read but is not counted as independent evidence here. |
| not_checked | Generalization beyond supplied candidate | Renderer code, alternate mappings/category counts, and variants were outside the delegated review scope. No claim about other inputs is supported by this review. |

## Paths actually read

- `/Users/starry/Desktop/EasyViz/skills/easyviz-figure-reviewer/SKILL.md` — review criteria. It contains no linked review-reference path.
- `/Users/starry/Desktop/EasyViz/evals/transfer-inputs/paired-effects/request.md` — adopted user requirements.
- `/Users/starry/Desktop/EasyViz/evals/transfer-inputs/paired-effects/source.csv` — original source values and independently calculated hash.
- `/Users/starry/Desktop/EasyViz/evals/transfer-inputs/paired-effects/provenance.json` — synthetic-data provenance and expected source hash.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/panel.png` — opened actual candidate image; also parsed PNG dimension/resolution metadata.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/figure-settings.json` — declared mappings and styling.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/actual-settings.json` — saved realized settings.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/caption.md` — separate explanatory artifact and interpretation.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/plotting-data.csv` — independent row-by-row comparison with the input.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/numeric-qa.json` — implementation report, treated as unverified where not independently checked above.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/panel.pdf` — direct page-size, embedded-font, and font-size inspection.
- `/Users/starry/Desktop/EasyViz/examples/create/paired-effects/panel.svg` — direct dimensions, text, and marker-style inspection.

The image tool displayed the 2125 × 1417 px PNG resized to 1919 × 1279 px. Readability was assessed at the panel's intended proportions alongside independently verified 8 pt typography and physical dimensions; this is not a physical print proof. The PDF and SVG were inspected structurally rather than separately rendered for visual comparison. Exact source-to-rendered-coordinate verification and flexible renderer behavior remain outside this review's evidence; the source-to-exported-table correspondence is independently confirmed.

Status: **ready_with_notes** for the original supplied panel within this review scope. No visual correction is required. The raster rounding and editable-SVG font dependency are documented above; completion of the separately assigned SVG endpoint check belongs to the implementing agent's final validation.
