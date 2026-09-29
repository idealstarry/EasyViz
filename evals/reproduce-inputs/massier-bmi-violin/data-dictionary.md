# Source data dictionary

Each row is a participant record in the authors' released Figure 8a source table. This is an observational cohort distribution, with no pairing implied between rows or studies.

| Column | Meaning |
|---|---|
| `source_row` | 1-based line number in `Figure_8a.txt`, including its header as line 1 |
| `source_id` | Original `ID` value, retained as text for traceability |
| `cohort` | Original `Cohort` label |
| `bmi` | Original BMI value in kg/m²; empty field preserves a source `NA` |

| Original cohort value | Publication label | Rows | Available BMI |
|---|---|---:|---:|
| Krieg | Krieg, L et al. | 23 | 23 |
| Petrus | Petrus, P. et al. | 29 | 29 |
| Arner, E | Arner, E. et al. | 56 | 56 |
| Kerr | Kerr, A. et al. | 77 | 77 |
| Arner, P#1 | Arner, P. et al. (#1) | 78 | 78 |
| Arner, P#2 | Arner, P. et al. (#2) | 80 | 80 |
| Armenise | Armenise, C. et al. | 189 | 186 |
| Imbert | Imbert, A. et al. | 332 | 329 |

There are 864 original records, 858 nonmissing BMI values, and 6 missing BMI values. The original numeric strings are preserved; no normalization, imputation, aggregation, sampling, or density estimation was performed during input preparation. Publication labels were transcribed from the PDF.
