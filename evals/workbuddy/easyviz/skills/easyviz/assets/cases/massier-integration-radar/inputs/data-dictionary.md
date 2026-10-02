# Source data dictionary

Each row is one already-computed kBET acceptance rate for an integration method and cell class. The source is worksheet `KBET_D` of `Figure_1e.xlsx`, cells A1:F6.

| Column | Meaning |
|---|---|
| `integration_method` | Original `group` row label from the source worksheet |
| `cell_class` | Original column label in the source worksheet |
| `acceptance_rate` | Published kBET acceptance rate (1 minus rejection rate), dimensionless on [0, 1] |

| Source method | Publication label |
|---|---|
| raw | raw |
| harmony | Harmony |
| scVI | scVI |
| bbknn | BBKNN |
| rPCA | rPCA |

| Source cell-class label | Publication label |
|---|---|
| ALL | all |
| FAP | FAPs |
| ENDO | vascular |
| IMMUNE | immune |
| ADIPOCYTES | adipocytes |

All 25 supplied values are present. Zero values are valid numeric source values, not missingness. The table has only been reshaped from wide to long form; values are neither rescaled nor recomputed. These are visualization inputs and must not be treated as instructions to run the biological analysis packages.
