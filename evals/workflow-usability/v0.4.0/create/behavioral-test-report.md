# Fresh create-track behavioral test

The directory-to-first-panel workflow completed successfully. The accepted boxplot preserves every one of the 24 independent specimens and answers the stated primary fluorescence question. PDF, SVG and PNG exports, the separate caption, adopted specification, planned descriptive analysis, raw source snapshots, replay script, implementation snapshot and actual visual review are retained here. No repository or skill source was edited by this agent; no evals, existing tests or expected outputs were read.

## Deliverables

- `primary-signal.pdf`, `primary-signal.svg`, `primary-signal.png`: accepted individual panel, 120 × 90 mm.
- `caption.md` and `recommendations.md`: separate manuscript caption and three proposed views with explicit fields and numerical previews.
- `source/`: byte-identical observations.csv and study-notes.txt; `source-hashes.json` records hashes.
- `exploration-01/`: unassisted directory inventory and generic recommendations; `exploration-02-design/`: reinspection with scientifically established roles and independent design.
- `analysis-plan.json`, `analysis-01/`: two descriptive endpoint summaries, methods and full source-record accounting. The 48 accounting rows reflect the same 24 specimens in each of two endpoint summaries, not 48 independent specimens.
- `figure-profile.json`, `draft-plot.json`, `plot-attempt-01.json`, `plot.json`, `adopted-specification.json`: stable colors, dimensions, original draft, retained first attempt and accepted seed-37 specification.
- `attempt-01/` and `attempt-02/`: retained exports and their plotting data, settings, renderer QA, element records and statistics.
- `review.json`, `jitter-review.json`, `verification.json`: actual image observations, the one correction and independently measured checks.
- `replay.py`, `skill-snapshot/`, `executed-helper-snapshot.json`, `replay-01/`, `replay-verification.json`: version-bound executable reproduction and its executed comparison.
- `commands.json`: exact workflow command arguments, returns and captured output. Initial schema-discovery and unassisted inspection were run interactively; the inspection records themselves are preserved in exploration-01.

## Changes needed for this input

Study notes supplied every consequential scientific fact: fluorescence in arbitrary units, percentage viability, independent units, unpaired conditions, primary endpoint, complete data and fixed final dimensions. I converted this information into an intake design and analysis plan, rejected the generic paired recommendation, selected a raw-observation boxplot, filled explicit English labels and colors, and wrote the caption. I selected descriptive summaries because the requested initial figure did not require inferential tests; no p-value search, test, confidence interval, upstream biological analysis or data transformation was performed.

The first actual image had an overlap between C005 and C009 at approximately 5.17 a.u. Technical renderer QA nevertheless passed, consistent with its documented scope. I changed only the horizontal jitter seed from 23 to 37. A physical-distance check found that the minimum center separation increased from 0.796 to 1.526 mm; fixed circle diameter is 1.411 mm. Both attempts are preserved. The second actual image was opened and reviewed before acceptance.

## Practical skill shortcomings

| Priority | Observed behavior and exact source | Practical correction used or suggested |
| --- | --- | --- |
| Medium | `skills/easyviz/scripts/inspect_data.py:320` still proposes `paired_candidate` after the design declares independent specimens. In this table all 24 IDs occur once, so there is no within-ID condition coverage. | Manually reject it using study-notes.txt. Suppress a paired recommendation for a confirmed independent design; ID/condition coverage could still be reported as an inventory fact when design is unknown. |
| Medium | Core technical QA reports `pass` for attempt-01 while two raw observation circles visibly overlap. Jitter is uniformly random in `skills/easyviz/scripts/render.py:639` in the current version. This limitation is documented, so the pass is not a false visual-review promise. | Actual image review plus a local mark-separation check; change the seed. A reproducible collision-aware placement option or collision warning would reduce manual corrections. |
| Low | Distribution box fill, edge color, fill alpha and width are hard-coded around `skills/easyviz/scripts/render.py:633`; resolved settings record observation-circle stroke semantics but do not fully state summary-box outlines. | Explicitly record a box-summary boundary exception in the adopted specification. Add summary-outline settings or include their actual resolved policy in settings.json. |
| Low | `skills/easyviz/scripts/analyze.py:465–466` emits paired-exclusion and inferential-interval boilerplate for this independent descriptive-only plan. | Caption and plan explicitly state no exclusions, no paired analysis, no test and no confidence interval. Emit design- and method-specific methodology prose. |
| Low | `render.py` defaults Matplotlib cache to a global temporary location and Python imports may refresh the shared skill __pycache__ during help/schema discovery. | For workflow/replay, set MPLCONFIGDIR under result/runtime and PYTHONDONTWRITEBYTECODE=1. Source files remained unchanged by this agent; shared interpreter caches were not deleted. |

## Checks actually performed

Fifteen checks are saved in verification.json: all 24 exact IDs and both measured values survive plotting; independent Python summaries reproduce each endpoint/group's mean, median, sample SD, linear quartiles and extrema; row accounting contains exactly 24 source rows per endpoint; Arial is used without substitution and active role sizes are 8 pt; PDF MediaBox and SVG width/height measure 120 × 90 mm; the PDF font is embedded; SVG contains editable text; PNG measures 1417 × 1063 pixels at approximately 300 dpi; accepted observation circles do not geometrically overlap; renderer clipping, tick and glyph checks pass; both original sources match their archived copies byte for byte. Actual PNG images from both attempts were opened and inspected.

The supplied source defines synthetic independent specimens; this provenance was used rather than inferring independence from row count. All results are descriptive. Correlation, inferential methods, missing-data handling beyond error-on-missing, paired plots, other chart families, non-English glyphs, large data, and physical print calibration were not tested. The review is self-review. No arbitrary-data generalization is claimed.

The renderer changed during the surrounding development session after helper-hashes.json was captured. Attempt-01 used hash `71bc588e3eab3a706c18cca09ab896f62da7ebab80620906cb6149261a6cd719`; accepted attempt-02 used current hash `931010a7f6bc2098621b7d9e820d3ebf07e369a026b63317a12c77d2bdf047f5`. The accepted implementation and its required helpers are frozen in skill-snapshot and verified against attempt-02. Replay uses that snapshot.

## Replay

Use the project interpreter, which already contains the required plotting libraries. Supply a new output path under this result directory:

```sh
/Users/starry/Desktop/EasyViz/.venv/bin/python /private/tmp/easyviz-forward-create/result/replay.py --out /private/tmp/easyviz-forward-create/result/replay-02
```

The script reads the preserved source, plan, profile and accepted plot spec, and writes a new planned-analysis directory and panel directory. It was executed once into replay-01. Its original-data plotting table, PNG image and descriptive summary are compared to the accepted originals in replay-verification.json.
