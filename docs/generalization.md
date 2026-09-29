# Generalization evidence and limits

EasyViz does not have evidence for arbitrary data or arbitrary reference figures. A useful claim must identify the input contract, the chart geometry, the changes tested, and what was checked independently. More example images alone do not establish transfer.

## Three distinct layers

| Layer | What can transfer | Current boundary |
| --- | --- | --- |
| Skill decisions | Select create/reproduce, resolve data meanings, preserve physical size and typography, choose encodings, inspect exports, separate captions | These instructions require an agent to apply judgment. Passing script tests does not demonstrate every agent decision. |
| Core renderer | Field-mapped heatmaps, compositions, dot matrices, scatter plots and distributions | Only documented options and validated input contracts. New geometry or scientific layers require a custom implementation. |
| Worked cases | Data validation and layout patterns, source records and review examples | The cell-atlas script explicitly targets 16 subtypes × 3 depots. A caller must adapt its schema and layout for other data; copying it unchanged is not generalization. |

The core maps columns by declared roles instead of fixed biological names. This supports different source-data tables with the same meanings. It does not infer whether a row is a participant, a cell or a technical replicate, or determine an appropriate denominator from a familiar-looking column name.

## Evaluation evidence

| Evaluation | What it exercises | Evidence |
| --- | --- | --- |
| Held-out create and reproduce workflows | New synthetic source schemas, missing follow-up visits, new reference-image categories, measured zeros versus unmeasured coordinates; actual independent output review | [Release QA](../evals/release-qa/README.md) |
| Bounded transfer and stress cases | Larger matrices, long/crowded labels, sparse cells, explicit denominators, more categories, logarithmic axes, unbalanced groups and invalid units/values | [Current report](../evals/generalization/report.md), with the preserved [baseline](../evals/generalization/baseline-report.md) |
| Legend geometry mechanics | Identical-input fit checks across category counts, long labels, canvas sizes, heatmaps, quantitative dot keys and explicit placement; no established aesthetic superiority | [Ten-case evaluation](../evals/legend-transfer/results.md), with later [design reassessment](../evals/design-value/critique.md) |
| Real-data design decisions | Same-input baseline, participant matrix, and distribution view; task-specific preference; unchanged recipe on another time contrast in the same study | [Independent comparison](../evals/design-value/paired-comparison.md), [case and reuse conditions](../examples/create/paired-myeloid-remodeling/README.md) |
| New chart workflow | An agent receives a new source table and request outside the five core families, reads the skill, and writes a custom effect/interval forest implementation | [Input and request](../evals/transfer-inputs/paired-effects/), [implementation and reuse evidence](../examples/create/paired-effects/README.md), [independent SVG geometry check](../evals/transfer-inputs/paired-effects/output-review.json) |
| Existing image-data reproduce cases | Independent reference reading, implementation and comparison without author code | [Case catalog](../examples/README.md) |

Synthetic cases test implementation and workflow behavior. They do not add biological studies or validate scientific inference. The forest task supplies asymmetric confidence intervals; the agent must draw those endpoints rather than fit a model or invent an uncertainty estimate.

## How to interpret a result

A successful transfer retains source values, declared transformations, all required layers and readable final-size output. A clear rejection of invalid data is also useful behavior, but is not a successfully rendered chart. Layout failures require an explicit layout repair with the agreed font size; they must not be counted as passing because a file was created. Unsupported geometry requires a new implementation and review, not silent substitution with an available chart.

Automatic overlap checks cover only the implemented text geometries. Oblique text, annotation-to-mark collisions, very small symbols, crowded legends and physical print reproduction still need visual inspection. Reference reproduction additionally retains uncertainty about original statistical transformations and rendering settings. Two no-author-code cases cannot establish broad reproduction quality.

Legend geometry is shared code across the core families and two custom recipes. This establishes code reuse across the tested contracts. Smaller guides and a geometry pass do not establish better scientific communication. The current helper no longer ranks feasible layouts by smallest occupied area; automatic output is a provisional placement. A design improvement requires a comparison of actual alternatives on the intended reading task, including the option to keep the baseline.

Add future cases to cover a new data or geometry requirement, then vary their inputs. Avoid accumulating many cosmetically different copies of one plot as evidence of generality.


The paired-change case adds a reusable choice between preserving individual correspondence and emphasizing distributions. Its implementation supports a declared tidy score contract, up to 16 annotated subtypes, and one or two cohorts at 180 × 125 mm. It rejects incomplete pairs, unreadably narrow participant columns and clipping scales. Its same-study follow-up reuse does not demonstrate a new domain or arbitrary longitudinal schemas. The transferable contribution is the explicit selection condition and failure mode, supported by competing examples and code; there is no established general quality advantage over a capable agent without EasyViz.
