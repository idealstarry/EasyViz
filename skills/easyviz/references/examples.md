# Worked cases

Use these cases after resolving the user's data mappings and track. In reproduce, the independent reader must describe the reference before the implementer inspects reusable code. A case is implementation support, not permission to inherit its scientific choices.

## Advanced create

| Resource | Reusable design | Data contract and limit |
| --- | --- | --- |
| [Paired myeloid remodeling](../assets/cases/paired-myeloid-remodeling/README.md) | Compare conventional distributions, a distribution ledger, and a participant matrix for different reading tasks | Real CC BY source scores; 832 paired changes from 52 participants, 16 subtypes, two cohorts. Each candidate is 180 × 125 mm, 8 pt. A same-study Kerr five-year transfer contains 592 different paired changes; it does not establish arbitrary-schema reuse. |
| [Cell atlas dot plot](../assets/cases/cell-atlas-dotplot/README.md) | One aligned matrix with count-area, within-group percentage color, descriptive marker labels, group strips, and pooled-count bars | Real CC BY data, all 16 subtypes × 3 depots. Case-specific implementation; adapt its explicit schema and annotations for new datasets. Markers are labels, not expression measurements. |
| [Annotated heatmap recipe](../assets/recipes/annotated-heatmap/README.md) | Square matrix with binary annotation strips and full-matrix marginal means; deterministic selected views | User-supplied matrix and matching metadata. Configurable selection count, colors, font roles, and millimeter placements. Original development data are excluded from this portable recipe. |
| [Empirical distributions](../assets/cases/urschel-ecdf/README.md) | Exact unsmoothed cumulative steps from all before/after observations | All 254 source values from Urschel; pooled marginal distributions are an explicit new reading task. Ties retain their counts; pairing is not encoded. |
| [Replicate components and ratios](../assets/cases/truong-components/README.md) | Stacked or grouped components with raw replicate layers and explicitly defined SD; supplied ratio observations on a separate panel | 84 Nature Methods values, 7 conditions × 3 biological replicates. Component/total SD differ; two low-event ratios remain marked. These are disclosed create adaptations of the source figure. |

These examples show purposeful scientific layers. They do not require every create chart to be dense. Retain a simpler plot when it answers the question clearly. Recheck denominators and alignment when adding or removing a layer.

The paired case has no single design winner: its reviewed ledger modestly improves cohort-distribution reading, its matrix uniquely retains participant correspondence across subtypes, and its baseline gives individual values more room for precise reading. Use [Design decisions](design-decisions.md) to select the relevant relationship and retain the tradeoff. The combined comparison image is documentation, not an assembled scientific output.

## Custom geometry transfer example

[Cohort effect forest](../assets/cases/paired-effects/README.md) uses explicitly synthetic source data to exercise a chart outside the core renderer. It displays supplied estimates and asymmetric confidence intervals, with two cohorts per term and grouped rows. No model is fitted and participant counts are not treated as weights. The script maps input fields explicitly and records a five-term, three-cohort reuse check with renamed columns. Its caption and review are specific to the recorded input; new data need their own interpretation and visual review.

## No-author-code reproduce

| Case | Evidence and reusable approach | Uncertainty to retain |
| --- | --- | --- |
| [BMI distributions](../assets/cases/massier-bmi-violin/README.md) | Eight horizontal violins, complete source records, transparent KDE calculations, independent reference reading and visual review | Original KDE settings are unknown. Scott bandwidth, observed-range trimming and displayed-area normalization are declared choices. |
| [Integration radar](../assets/cases/massier-integration-radar/README.md) | Five methods × five ordered classes, exact supplied rates, explicit physical geometry and editable output | A zero-centered scale replaces unknown original central padding. Three true zero values remain coincident. |
| [Supplied area scatter](../assets/cases/xiang-bubble-volcano/README.md) | Nature Communications Source Data: 1,457 coordinates/classes, proportional circle area, 37 zeros, explicit reference lines | Grey means small median difference within a prefiltered sheet; two source gene identifiers are Excel dates. A renamed-column synthetic probe is engineering transfer. |
| [Supplied OR forest](../assets/cases/vabistsevits-forest/README.md) | Nature Communications Source Data: 24 OR/asymmetric 95% CI per standalone panel, log axis, exposure blocks and outcome colors | Per-estimate n remains unknown. Panel b tests same-study reuse; physical typography/geometry are declared adaptations. |
| [Paired observations](../assets/cases/urschel-paired/README.md) | Complete source pairs, four median/IQR swarms, log display; optional connected create view | Source-positive infection classifications are pooled according to the caption. Adopted Weibull quartiles are explicit, with a small unresolved published rounding difference; automatic tests are omitted. |

These cases were reconstructed from reference images, source data, and permitted semantic context without author plotting code. Their development evaluations used fresh agents with instruction-based access restrictions, not an enforced filesystem sandbox. Independent reviews accepted the candidates with documented notes; they do not establish pixel identity or unseen statistical equivalence.

Copy a chosen case folder into the user's writable project before running or adapting it; the reproduce scripts write beside their inputs. Keep installed plugin assets unchanged. Each portable case includes a runnable implementation, local inputs, source attribution, actual settings, exports and review evidence. Numerical results belong to the supplied data, not to the visual template. Replace or recalculate them for new inputs. A saved independent review applies to the specific recorded candidate hashes; rerendered or adapted figures need their own review.

## Small API fixtures

[Fixtures](../assets/fixtures/) contain synthetic input tables and specifications for heatmap, composition, dotplot, scatter, and distribution. They demonstrate the core renderer's input format and support deterministic tests. Do not report them as biological findings or treat their minimal layouts as the target level of refinement for all create work.

Use [chart-library.md](chart-library.md) for reusable schema details and [panel-layout.md](panel-layout.md) for physical sizing. Where a custom case contains specialized assumptions, adapt the implementation explicitly instead of forcing the user's data into it.
