# Generalization evidence and limits

EasyViz does not have evidence for arbitrary data or arbitrary reference figures. A useful claim must identify the input contract, the chart geometry, the changes tested, and what was checked independently. More example images alone do not establish transfer.

## Transfer boundaries

| Layer | What can transfer | Current boundary |
| --- | --- | --- |
| Skill decisions | Select create/reproduce, resolve data meanings, preserve physical size and typography, choose encodings, inspect exports, separate captions | These instructions require an agent to apply judgment. Passing script tests does not demonstrate every agent decision. |
| Core renderer | Field-mapped heatmaps, compositions, dot matrices, scatter plots and distributions | Only documented options and validated input contracts. New geometry or scientific layers require a custom implementation. |
| Supplied-interval tool | Field-mapped estimates and asymmetric endpoints, sparse series combinations, log/linear axes and explicitly adopted fill states | Preserves prepared quantities; does not infer n, compute intervals or fit models. Independent source/color meanings remain case requirements. |
| Paired-observation tool | Explicit complete units across two or more conditions, optional exclusive blocks, median/IQR, deterministic point placement and adopted connectors | Rejects missing or duplicate repeated measurements. Quantiles use the stated raw-scale rule; no test or pairing is inferred. |
| Replicate-bar tool | Stacked/grouped components and supplied-value summary bars, raw replicate layers, optional sample SD and explicit state hatches | Components must be complete for every condition/unit. Stacked SD describes per-unit totals, grouped SD each component. Biological independence and ratio formulas remain source facts. |
| ECDF tool | Grouped or ungrouped empirical distributions, complete ties and linear/log x axes | Unweighted raw observations only, without smoothing or inference. Marginal curves do not preserve pairing. Actual vector paths retain every empirical jump. |
| Worked cases | Data validation and layout patterns, source records and review examples | The cell-atlas script explicitly targets 16 subtypes × 3 depots. A caller must adapt its schema and layout for other data; copying it unchanged is not generalization. |

The core maps columns by declared roles instead of fixed biological names. This supports different source-data tables with the same meanings. It does not infer whether a row is a participant, a cell or a technical replicate, or determine an appropriate denominator from a familiar-looking column name.

## Evaluation evidence

| Evaluation | What it exercises | Evidence |
| --- | --- | --- |
| Held-out create and reproduce workflows | New synthetic source schemas, missing follow-up visits, new reference-image categories, measured zeros versus unmeasured coordinates; actual independent output review | [Release QA](../evals/release-qa/README.md) |
| Bounded transfer and stress cases | Larger matrices, long/crowded labels, sparse cells, explicit denominators, more categories, logarithmic axes, unbalanced groups and invalid units/values | [Current report](../evals/generalization/report.md), with the preserved [baseline](../evals/generalization/baseline-report.md) |
| Legend geometry mechanics | Identical-input fit checks across category counts, long labels, canvas sizes, heatmaps, quantitative dot keys and explicit placement; no established aesthetic superiority | [Ten-case evaluation](../evals/legend-transfer/results.md), with later [design reassessment](../evals/design-value/critique.md) |
| Skill use versus capable baseline | Two real NOAA/USGS source-data tasks, identical model configuration and requests, preserved first/final outputs, anonymous independent comparison and separate source-value/export audit | [Actual value pilot](../evals/skill-value/README.md): EasyViz preferred for CO2, earthquake tie; two cases do not establish a general advantage |
| Real-data design decisions | Same-input baseline, participant matrix, and distribution view; task-specific preference; unchanged recipe on another time contrast in the same study | [Independent comparison](../evals/design-value/paired-comparison.md), [case and reuse conditions](../examples/create/paired-myeloid-remodeling/README.md) |
| New chart workflow | An agent receives a new source table and request outside the five core families, reads the skill, and writes a custom effect/interval forest implementation | [Input and request](../evals/transfer-inputs/paired-effects/), [implementation and reuse evidence](../examples/create/paired-effects/README.md), [independent SVG geometry check](../evals/transfer-inputs/paired-effects/output-review.json) |
| Existing image-data reproduce cases | Independent reference reading, implementation and comparison without author code | [Case catalog](../examples/README.md) |
| New Nature Communications Source Data | 1,457 supplied area-scatter rows including 37 zeros; 48 supplied estimates/asymmetric intervals with unknown n; fresh reference readings and independent actual export/image review | [Quality update](../evals/reproduce-inputs/quality-update-2026-10-02.md), including a nine-row synthetic scatter probe and a same-study second interval panel |
| New observations/components and plot diversity | Two further Source Data papers, 127 complete pairs/254 measurements and 84 component/ratio values; three focused generic tools; exact source and vector audits, plus changed-schema checks | [Diversity update](../evals/reproduce-inputs/diversity-update-2026-10-02.md), [independent source/export audit](../evals/reproduce-inputs/new-families-audit/source-and-exports-final.json), and [new case catalog](../examples/README.md) |
| Practical external-agent iteration | One natural ECDF task and a correction replay in WorkBuddy, with renamed Chinese fields and exact skill snapshots; feedback changed line keys, source-text trace and caption guidance | [New-family trial](../evals/workbuddy-new-families/README.md): updated output passes 12 independent checks; same-conversation correction check, without a baseline arm or effectiveness estimate |
| External domestic-model comparison | WorkBuddy Deepseek matched unseen dot task with/without a frozen skill, independent numeric/export/reuse checks and anonymous visual review | [Recorded pilot](../evals/workbuddy/README.md): direct-code panel preferred; no demonstrated visual gain in that task |
| Second external model/task pair | WorkBuddy GLM matched unfamiliar renamed interval fields, long labels and absent combinations | [GLM evidence](../evals/workbuddy-glm/README.md): direct-code panel preferred visually, EasyViz canvas more accurate; later engineering fixes remain separate from this frozen result |
| Physical distribution-point spacing | Same 24 observations and final-size styling, default jitter versus opt-in beeswarm | [0.4.1 geometric comparison](../evals/crowding-layout/v0.4.1/README.md): 12 overlapping circle pairs reduced to zero; a software/layout result, without a model or general aesthetic-effect estimate |
| Noisy-directory and aligned-layer workflows | Fresh local Agents use mixed technical-read tables or a synthetic reference with heatmap, condition strip and marginal means | [0.4.1 trials](../evals/workflow-usability/v0.4.1/README.md): source/export audit and independent actual-image review; bounded tasks, without an unaided baseline |
| Prepared external-model follow-up | Frozen matching requests, multi-table inputs, unfamiliar reference and independent verification kit | [WorkBuddy 0.4.1 status](../evals/workbuddy/v0.4.1/README.md): UI input was blocked before a verified submission; no new model-quality result |

Synthetic cases test implementation and workflow behavior. They do not add biological studies or validate scientific inference. The forest task supplies asymmetric confidence intervals; the agent must draw those endpoints rather than fit a model or invent an uncertainty estimate.

## How to interpret a result

A successful transfer retains source values, declared transformations, all required layers and readable final-size output. A clear rejection of invalid data is also useful behavior, but is not a successfully rendered chart. Layout failures require an explicit layout repair with the agreed font size; they must not be counted as passing because a file was created. Unsupported geometry requires a new implementation and review, not silent substitution with an available chart.

Automatic overlap checks cover only the implemented geometries. The supplied-interval tool also checks line/cap strokes and cross-row marks. Oblique text, annotation-to-mark collisions, very small symbols, crowded legends and physical print reproduction still need visual inspection. Reference reproduction additionally retains uncertainty about original statistical transformations and rendering settings. A small set of no-author-code cases cannot establish broad reproduction quality.

Legend geometry is shared code across the core families and two custom recipes. This establishes code reuse across the tested contracts. Smaller guides and a geometry pass do not establish better scientific communication. The current helper no longer ranks feasible layouts by smallest occupied area; automatic output is a provisional placement. A design improvement requires a comparison of actual alternatives on the intended reading task, including the option to keep the baseline.

Add future cases to cover a new data or geometry requirement, then vary their inputs. Avoid accumulating many cosmetically different copies of one plot as evidence of generality.


The paired-change case adds a reusable choice between preserving individual correspondence and emphasizing distributions. Its implementation supports a declared tidy score contract, up to 16 annotated subtypes, and one or two cohorts at 180 × 125 mm. It rejects incomplete pairs, unreadably narrow participant columns and clipping scales. Its same-study follow-up reuse does not demonstrate a new domain or arbitrary longitudinal schemas. The transferable contribution is the explicit selection condition and failure mode, supported by competing examples and code; there is no established general quality advantage over a capable agent without EasyViz.

## First guidance value pilot

The [source-backed value comparison](../evals/skill-value/README.md) includes actual PNG/PDF/SVG panels from two authors using the same inherited model configuration and the same source data, requested size/font and deliverables. The baseline did not read EasyViz or repo plotting examples; the guidance arm read canonical EasyViz and needed references. Both used custom scripts rather than the changing core renderer. An independent reviewer saw anonymous final images and captions without origin or code; no reviewer feedback changed the frozen outputs. Separate artist-array, trace, PDF-text and export checks retained all 45 NOAA annual means/uncertainty endpoints and 131 USGS event coordinates and multiplicities.

The reviewer preferred the EasyViz CO2 panel for discrete annual marks, complete labels, an endpoint leader and an uncertainty scale including zero. The earthquake task tied: hollow baseline marks exposed overlapping categories more clearly, while the EasyViz caption explained magnitude methods more fully. Primary CO2 uncertainties remain subpixel; supporting uncertainty axes retain readable values. Neither earthquake rendering makes exact coincident multiplicities visible. These are task-specific tradeoffs, and provide no basis for a universal filled/borderless-mark preference.

This is new evidence of guidance applied to real domains absent from this repository, with inspectable comparison artifacts. It is not an effectiveness estimate. There was one author per arm completing both tasks, one reviewer, no controlled token budget or seed, and a canonical guidance update during the run. The retained guidance snapshots identify exposure; the extra memory/context reads and author variation remain confounders. Observed work times and corrections cannot establish a speed or error-rate benefit. Both arms already received strong source/export instructions, so these cases do not establish broad gain over a capable agent or demonstrate the new packaged renderer features.

## v0.4.2 evidence

- An independent public-contract matrix trial used an unrelated shuffled 7 × 6 assay, 41 source rows, both missing states, literal IDs, keyed strips, seven means and a supplied tree. Actual 100 × 85 mm Arial 8 pt PNG/PDF/SVG inspection passed; relatively large necessary guide area and faint SVG cell seams remain recorded limitations.
- A separate public-contract preview trial used 57 synthetic independent observations in three groups. Same-source box/ECDF/optional-violin candidates preserve IDs, coordinates, fonts and scales. Independent before/after review found a modest median-readability gain from point opacity 0.65, with lower point contrast as the tradeoff. This is one task-specific refinement, not a general aesthetic score.
- The Yayon Nature layer adaptation preserves all 1,430 numeric source strings, verifies actual cell/bar/circle artists, and has independent original/changed-schema PNG/PDF/SVG reviews. The unpublished dendrogram is omitted. A distinct 250 × 111 mm DejaVu Sans layout preserves 7.5 pt text; it does not establish unchanged-layout equivalence to the original Arial case.
- The parent operated the real in-app-browser workbench: mapped category and key selection, saved request, hash-checked core rerender, previous/current preview and byte-identical accepted restoration of source/spec/data and all requested exports. Independent review prompted concrete containment and palette-binding repairs. Imported plotting dependencies remain the Agent’s preservation responsibility.

Inputs, actual commands, first attempts, refinements and their scope are in
[workflow evidence](../evals/workflow-usability/v0.4.2/README.md).
No MCP, external-model effectiveness comparison or fresh desktop plugin
installation/discovery is claimed for this release.
