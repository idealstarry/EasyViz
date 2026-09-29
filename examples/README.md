# Example catalog

Create and reproduce use the same physical-size, typography, data, and review rules. The catalog records the inputs actually used, so source-data design, image-data reconstruction, and author-code-assisted adaptation remain distinguishable.

## Create showcases

| Case | Design and data | Final size | Implementation |
| --- | --- | --- | --- |
| [Paired myeloid remodeling](create/paired-myeloid-remodeling/README.md) | Three designs for the same 832 paired score changes: 52 participants, 16 subtypes, two cohorts | Each panel 180 × 125 mm; 8 pt | New script using published source scores and semantic annotations; no author code |
| [Annotated inhibition](create/annotated-inhibition/README.md) | 20 × 20 deterministic selection from 5,776 measurements, genome-status strips, and full-matrix mean tracks | 180 × 160 mm; 8 pt | New script using source data; no reference image or author code |
| [Cell atlas dot plot](create/cell-atlas-dotplot/README.md) | All 16 subtypes × 3 depots; count area, within-depot percentage color, published descriptive annotations, pooled-count margin | 180 × 120 mm; 8 pt | New design using source data and semantic annotations from the paper; no author code |

The paired case's [independent comparison](../evals/design-value/paired-comparison.md) has no overall winner. The ledger modestly helps distribution comparison; the participant matrix retains correspondence across subtypes; the baseline preserves more space for individual-value precision. Its unedited script also renders 592 five-year changes from the same study's Kerr cohort. This transfer changes time point and cohort selection, not source schema or study. The [comparison preview](create/paired-myeloid-remodeling/comparison.png) is documentation; all scientific panels are exported individually.

## Synthetic workflow transfer

[Cohort-effect forest](create/paired-effects/README.md) adds a custom interval geometry beyond the core renderer. A fresh agent received an unseen synthetic source table and the EasyViz skill, without reading existing example scripts. The original 14-term × 2-cohort panel and a 5-term × 3-cohort reuse probe retain supplied asymmetric intervals, explicit field mappings and 8 pt typography. The original panel has an independent visual review; the reuse probe has numerical/SVG checks and implementer visual review. This is engineering evidence, not an additional biological study or a guarantee for arbitrary input.

## Reproduce without author code

| Case | Permitted inputs and scientific limits | Final size | Evidence |
| --- | --- | --- | --- |
| [BMI violin](no-author-code/massier-bmi-violin/README.md) | Image, source data, and permitted semantic context; original KDE parameters unknown | 160 × 100 mm; 8 pt | Independent image reader, runnable reconstruction, first render, data checks, independent visual review |
| [Integration radar](no-author-code/massier-integration-radar/README.md) | Image and 25 supplied rates; original radial-origin padding unknown | 88 × 88 mm; 8 pt | Same process; zero rates retained at an explicitly chosen zero origin |

The evaluations withheld author code from the reader and implementer by instruction. The cases preserve access logs; they do not claim operating-system-enforced isolation. Reference crops and their preparation provenance are under [evals/reproduce-inputs](../evals/reproduce-inputs/).

## Historical code-assisted adaptations

| Case | Evidence and transformation | Final size |
| --- | --- | --- |
| [Microbiology](reproduce/microbiology/README.md) | Gontijo source data, image, and author-code evidence; 12 × 12 selected detail | 132 × 120 mm; 8 pt |
| [Single-cell composition](reproduce/singlecell/README.md) | Angarola archived source counts, image, and author-code evidence; replicate-level composition instead of grouped mean/SEM | 88 × 88 mm; 8 pt |

These historical cases are not evidence for image-only reconstruction. [check_examples.py](../tests/check_examples.py) validates their source-table round trips, denominators, fonts, and physical exports. The complete original paper collections remain outside this repository; see the [resource assessment](../docs/resource-assessment.md).

## Reuse

Each case includes inputs, a runnable script, settings, provenance, and exports. Use the project Python environment and the case's own invocation. Always rerender at the intended final dimensions; enlarging an exported panel also enlarges its text.

Selected CC BY cases and the explicitly synthetic forest case are synced into the main skill's portable assets. The Gontijo dataset carries a CC BY-NC notice, and the Angarola historical collection has no verified broad redistribution license; their data stay outside the portable plugin. The independently written annotated-heatmap implementation is available there as a recipe requiring user-supplied inputs.

The small [synthetic fixtures](../evals/README.md) test the reusable renderer. They are not biological findings or flagship create examples. See [acceptance](../docs/acceptance.md) for the scope and limits of completed validation.
