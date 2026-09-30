# EasyViz guidance value pilot

**The anonymous reviewer preferred EasyViz for the CO2 task and judged the earthquake task a tie. Both arms preserved the source values and passed the independent export checks. These two cases do not establish a general quality or speed advantage.**

This run, completed 30 September 2026, compares two actual source-data tasks with and without EasyViz guidance. Both authors used the same inherited model configuration, identical data/requests, a 90 × 70 mm canvas, Arial 8 pt, and PNG/PDF/SVG delivery. The baseline author did not read plotting Skills or repository examples/tests/scripts. The EasyViz author read canonical guidance and needed references. Both wrote custom Matplotlib implementations; the evolving packaged renderer was excluded. The [protocol](protocol.md), [identical request](required-spec.md), [source terms and meanings](inputs/SOURCES.md), [provenance](inputs/provenance.json) and [guidance snapshots/hashes](easyviz/guidance-hashes.json) are retained.

## Results and actual panels

The guidance snapshot preserves only files the author actually read; it is not a standalone installed Skill. Internal links to resources outside that partial snapshot retain their original canonical Skill context. The frozen text and hashes remain unchanged.

| Reader task | Baseline result | EasyViz result | Independent result |
| --- | --- | --- | --- |
| Annual NOAA atmospheric CO2, 1980–2024 | [PNG](baseline/noaa-co2/final/noaa-co2.png), [caption](baseline/noaa-co2/final/caption.md), [PDF](baseline/noaa-co2/final/noaa-co2.pdf), [SVG](baseline/noaa-co2/final/noaa-co2.svg) | [PNG](easyviz/noaa-co2/final/panel.png), [caption](easyviz/noaa-co2/final/caption.md), [PDF](easyviz/noaa-co2/final/panel.pdf), [SVG](easyviz/noaa-co2/final/panel.svg) | EasyViz preferred: discrete annual points, clearer axis names, an explicit endpoint leader and zero-based supporting uncertainty axis. |
| USGS January 2024 earthquake depth/magnitude | [PNG](baseline/usgs-earthquakes/final/usgs-earthquakes.png), [caption](baseline/usgs-earthquakes/final/caption.md), [PDF](baseline/usgs-earthquakes/final/usgs-earthquakes.pdf), [SVG](baseline/usgs-earthquakes/final/usgs-earthquakes.svg) | [PNG](easyviz/usgs-earthquakes/final/panel.png), [caption](easyviz/usgs-earthquakes/final/caption.md), [PDF](easyviz/usgs-earthquakes/final/panel.pdf), [SVG](easyviz/usgs-earthquakes/final/panel.svg) | Tie: baseline hollow symbols better distinguish overlapping types; EasyViz's caption better explains measurement methods. |

The reviewer received anonymized A/B final PNGs, identical-size previews and captions, with neither arm identity nor code/source-value audit. CO2 B was EasyViz; earthquake A was EasyViz. The labels reverse between tasks. The [review](blind-review/review.md), [structured findings](blind-review/review.json) and subsequently disclosed [mapping](anonymization-key.json) preserve the assessment. No review feedback was used to revise the frozen figures.

No blocking reading failure was established. Important limitations remained in both arms: primary CO2 error bars are subpixel at the complete concentration range, so the separate uncertainty view and caption are essential; exact coincident earthquake multiplicities cannot be read from either scatterplot. EasyViz's pale filled rare-type markers were less visible than the baseline's hollow symbols at intended size. Baseline retained type codes and documented absent method definitions in its input; EasyViz supplied correct definitions, but the author's record contains no supporting source lookup. A separate [primary-source caption audit](caption-source-audit.md) verified those definitions after freezing. The tie therefore preserves both the visual advantage and the sourcing limitation.

## Independent numerical and export verification

| Check | Baseline | EasyViz |
| --- | --- | --- |
| Frozen source derivation | Exact decimal/identifier strings and declared filters verified against temporary raw downloads: 45 NOAA years and 131 unique USGS events | Same immutable inputs |
| NOAA plotted values | All 45 annual coordinates, supporting uncertainty values and mean ± uncertainty endpoints match input; endpoint change 85.85 ppm | Pass |
| Earthquake plotted values | All 131 coordinates and repeated-coordinate multiplicities drawn; all four type groups retained; raw values unchanged on log depth axis | Pass |
| Export canvas and typography | 90 × 70 mm PDF/SVG; 1063 × 827 PNG at approximately 300 dpi; actual Arial PDF font and 8 pt text | Pass |
| Canvas text bounds | No measured text outside complete canvas | Pass |

Evidence: [source derivation](source-derivation-verification.json), [full artist/trace/PDF-text audit](value-verification.json), [physical export audit](export-verification.json) and [source ground truth](source-ground-truth.json). Artist-array checking confirms that values were drawn; it does not make coincident marks individually visible. Raster dimensions reflect unavoidable integer-pixel rounding. Physical printing and browser substitution of editable SVG fonts were not tested.

## Work and preserved revisions

| Author-recorded observation | Baseline | EasyViz |
| --- | --- | --- |
| Observed wall clock | 945.7 s, approximately 15 min 46 s | 1144.7 s, approximately 19 min 5 s |
| Shell/tool execution calls | 13 | 31 |
| Image inspections | 8 | 10 |
| CO2 visual correction passes | 1 | 2 |
| Earthquake visual correction passes | 0 | 0 |
| Token accounting/control | Unavailable | Unavailable |

Counters are author-reported, not service usage telemetry; orchestration wrappers are recorded separately in the [baseline log](baseline/run-log.json), [EasyViz log](easyviz/run-log.json) and [normalized work summary](author-work-summary.json). Times include input/design work, environment probes, self-review and archive/log creation. These numbers cannot be attributed to Skill use: author variation, uncontrolled sampling, additional guidance/archive work and concurrent machine load remain confounded.

Baseline preserved the initial CO2 missing subscript glyph and endpoint-label collision before correcting them. EasyViz caught the missing glyph before its first complete render, then moved the endpoint label and added a leader in two visual passes. Initial PNG/PDF/SVG, captions, scripts and settings remain under each task's `initial/`; EasyViz's intermediate CO2 revision remains under `review-pass-2/`. Final artifacts are covered by [freeze hashes](artifact-freeze.json). Both earthquake initial/final PNGs are byte-identical.

## Scope and replay

These domains were absent from this repository's examples when selected. They are not necessarily unknown to the pretrained model; NOAA CO2 is a familiar scientific record. Two tasks completed by one author per arm and judged by one reviewer are not independent replicated experiments. Both arms already received strong source/export instructions, and authors knew their assignment. Token budgets and sampling seeds were not controlled. The canonical Skill changed during the authorized repo update; the author's retained snapshots, rather than one release version, identify guidance context. The EasyViz author also consulted the shared memory registry containing the same panel-text conventions already specified to both arms. This is an exploratory guidance comparison, with no population-level performance estimate.

Source input CSVs, captions, plotting scripts, settings and traces are all retained. The raw downloads are intentionally outside the repository; hashes and exact URLs identify them. The input is governmental public-domain source material with required credit/terms documented in `inputs/SOURCES.md`; these figures imply no NOAA or USGS endorsement.

With a Python runtime providing this repo's plotting dependencies and Arial, run from the repository root:

```sh
python evals/skill-value/verify_exports.py
python evals/skill-value/verify_plot_values.py
```

The value audit reruns saved final scripts with export capture and temporary scratch folders, leaving preserved figures untouched. Each author's script also accepts explicit input/output paths for independent rendering. The benchmark is optional evaluation evidence, excluded from plugin installation and runtime. Further effectiveness claims need repeated randomized runs, more source domains and independent reviewers, with controlled budgets where the tools permit them.
