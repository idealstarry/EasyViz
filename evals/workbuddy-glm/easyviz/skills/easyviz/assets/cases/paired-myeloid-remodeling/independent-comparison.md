# Paired myeloid design comparison

Independent review, 2026-09-29. Opened all three final PNGs; no plotting/preparation code or author rationale was read. The two reading tasks have equal weight. The comparisons below concern these data and this 180 × 125 mm panel only.

## Preferences from the actual images

| Reading task | Ledger versus baseline | Matrix versus baseline | Visible basis and cost |
| --- | --- | --- | --- |
| Cross-cohort direction, magnitude, participant variability | **candidate**, modest preference | **baseline** | Ledger's strong median dots and IQR lines make cohort offsets easier to find among pale participant dots. Its aligned Below 0 columns distinguish myC04 (27% / 51%) and myC09 (80% / 65%) without counting dots. Baseline gives individual values more horizontal space and has familiar distribution geometry. Matrix compresses magnitude comparison into the narrow right strip; color is less precise for individual spread and extremes. |
| Several subtypes changing together within individuals | **no_clear_preference** | **candidate**, clear preference | Matrix keeps each participant in one column across all 16 rows. Broad blue columns and exceptions in myC04 and the monocyte rows can be followed vertically. Baseline and ledger show distributions but neither preserves visible participant identity between rows. Matrix's fine columns, pale near-zero cells, and absence of participant IDs still limit exact lookup. |

All three preserve the same subtype order and biological gaps; ledger and matrix add light horizontal separators that make groups easier to scan. Ledger's extra numeric column helps the first task but consumes plotting width. It provides no new evidence for the second task. Matrix adds a usable relationship between rows, not just another summary layer.

There is **no single winner across both equally weighted tasks**. The ledger is a modest distribution-reading improvement; the matrix supplies a reading operation the baseline cannot support, while sacrificing individual-value precision. Neither result establishes that EasyViz is better than a carefully written standalone plotting script.

## Findings and limits

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Matrix ordering | Dark-to-light progression is visible across many rows; participant-order.csv matches sorting by each participant's median change within cohort. | Distinguish visible paired patterns from an effect of sorting. | State the sort rule in the separate caption; do not claim covariance or a shared biological program from this gradient alone. |
| note | Matrix scale | Several near-zero cells are almost white; the shared range is −12 to +12 although observed positive changes stop near +7.23. | Interpret signed score differences without implying missing cells. | Explain that all cells contain observed differences; retain the common scale when comparing rows. |
| note | Matrix lookup | Endpoint ranks are now separated, but columns have no participant IDs and are narrow. | Support within-person pattern exploration. | Use participant-order.csv for named-person lookup; exact numerical comparison still needs the source table. |
| note | Separate caption | The supplied caption now defines two-year-minus-baseline changes, original score units, ordering, counts, IQR, and the separate five-year transfer. | Retain essential interpretation with the exported figure. | Distribute caption.md with the chosen panel; matrix alone does not name its time contrast. |

## Numerical and export checks

- **passed:** Independently recomputed all 832 year-2-minus-baseline changes from source-data.csv and all 32 cohort/subtype medians, linear quartiles, and strictly-below-zero percentages; no mismatch. This checks local tables, not the original publication's data extraction.
- **passed:** 52 unique participants (Petrus 15, Kerr 37), 16 subtypes; matrix order agrees with within-cohort median-change sorting. Differences range from −10.7388842461 to +7.2262132672, inside both display scales.
- **passed:** Each PNG is 2125 × 1476 pixels. Each PDF MediaBox and SVG page is 510.236220 × 354.330709 pt, corresponding to 180 × 125 mm. SVG text is Arial, size 8 in a viewBox numerically matched to page points.
- **not_checked:** Physical print legibility, PDF font embedding, perceptual color accessibility, and whether every plotted mark corresponds to its table value. Opened PNGs support the visual comparison; correct table calculations do not prove every mark.
- **passed:** Read the final separate caption; it agrees with the inspected local data and figure semantics. IQR is participant spread, not a confidence interval; score differences are not percentages. “Below 0 (%)” describes the proportion of participants. Publication provenance and licensing claims were not independently checked.

## Exact reviewed image hashes (SHA-256)

Paths are relative to `examples/create/paired-myeloid-remodeling/output/`.

- `baseline/panel.png`: `e1e508f7a2231487ecaae75f385137d5010df87f751ddd170e8988d805f7cd75`
- `distribution-ledger/panel.png`: `5ddd3007ca6ca888581dfd30bf511dc503c6d9af248a3dcdd8dcb7ac9e27e3a5`
- `participant-matrix/panel.png`: `74017d6a6ccf3776272734b940c802db2a8c5be63b2ebd8ebf77b476aa1f2fb4`

**Status: ready_with_notes** for this scoped panel comparison. Retain the caption and the matrix ordering/lookup limits above. This status is separate from the task-specific preferences and does not establish publication acceptance, covariance, general design superiority, or a full audit of every rendered mark.
