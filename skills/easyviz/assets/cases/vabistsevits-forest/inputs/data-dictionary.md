# Source data dictionary

Every row is one published Mendelian-randomization effect estimate for a mammographic-density exposure and a breast-cancer outcome. These are model estimates, not independent participant measurements or matched raw observations.

The input contains all 48 rows from sheet `fig3` of the official Source Data workbook. Excel row 1 is the header. Figure 3a uses rows 2–25; Figure 3b uses rows 26–49. Each panel contains three exposures × eight outcomes. No numeric value was imputed, averaged, sampled, transformed, or recomputed during preparation.

| CSV column | Meaning and source |
|---|---|
| `source_row` | Original 1-based Excel row in sheet `fig3`, including the header as row 1 |
| `source_sheet` | Original sheet name, `fig3` |
| `panel` | `a` for total effect; `b` for direct effect |
| `effect` | Normalized display label derived from original column H |
| `exposure` | Original column A: Dense area, Non-dense area, or Percent density |
| `outcome` | Original column B: overall breast cancer, ER+ or ER− breast cancer, or one of five molecular subtypes |
| `estimate` | Original column C, `or`: odds ratio for breast cancer per SD increment in the exposure |
| `ci_low` | Original column D, `or_lci95`: lower endpoint of the 95% confidence interval |
| `ci_high` | Original column E, `or_uci95`: upper endpoint of the 95% confidence interval |
| `ci_level` | `0.95`, explicitly identified in the Figure 3 caption |
| `effect_measure` | `odds ratio`, explicitly identified in the caption |
| `null_value` | `1`, the no-effect reference for an odds ratio |
| `effect_direction` | Original column G: `ok` or `overlaps null`; the latter maps to the hollow-circle encoding |
| `n` | Empty for all rows. The figure source table does not give per-estimate sample sizes. |

The original column F, `OR_CI`, is a rounded display string and is absent for panel b. It is intentionally omitted: plotting must use the unrounded numeric endpoints in columns C–E. Original effect labels in H contain line breaks; the CSV replaces those with readable `Total effect` and `Direct effect` labels while retaining panel and Excel-row provenance.

The caption defines total effect as univariable IVW MR and direct effect as IVW multivariable MR accounting for childhood body size. All intervals are 95% confidence intervals. They are asymmetric on the odds-ratio scale; the supplied endpoints must be used separately. An SD or SEM cannot be substituted.

The caption reports GWAS dataset sizes of 24,158 for mammographic density and 247,173 for overall breast cancer (133,384 cases, 113,789 controls), while referring subtype sample sizes to Supplementary Table 1. These counts are dataset-level context and are not inserted into `n` for each estimate.

There are 48 complete positive estimates and intervals: every record satisfies `0 < ci_low < estimate < ci_high`. There are 16 `ok` records and 32 `overlaps null` records. Panel a contains 6 solid and 18 hollow marks; panel b contains 10 solid and 14 hollow marks.

The input order follows the workbook and differs between panels. The reference's visible outcome order is Overall breast cancer, ER+ breast cancer, ER− breast cancer, Luminal A subtype, Luminal B1 subtype, Luminal B2 subtype, HER2-enriched subtype, Triple-negative subtype. Reproduction should use explicit category order, not workbook row order or alphabetical sorting.

Attribution: Vabistsevits et al., Nature Communications 15, 4021 (2024), [10.1038/s41467-024-48105-7](https://doi.org/10.1038/s41467-024-48105-7). Article license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Full asset provenance and retrieval details are in `provenance.json`.
