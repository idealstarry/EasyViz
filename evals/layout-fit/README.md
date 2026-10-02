# Measured layout and first-panel exploration

Date: 2026-10-02. These are synthetic engineering inputs and one forward-use
task, not biological evidence, novice-participant research or a Chinese-model
benchmark. The code changes and local build are unreleased. Historical 0.2.0
release QA and installed-plugin evidence remain attached to their original files.

## Fixed versus measured layout

Reproduce the three layout pairs from the repository root:

```sh
.venv/bin/python evals/layout-fit/run.py
```

Both variants use identical source values, category orders, Arial 8 pt and an
88 × 70 mm canvas. The fixed variant retains the core's original margins; the
measured variant opts into `layout.auto_fit`. Both run the current renderer and
its checks. Failed baseline images are retained explicitly as `needs_revision`.
Source CSVs, specifications, actual exports, resolved settings and detailed QA
are saved per case; [summary.json](summary.json) records hashes and results.

| Synthetic case | Fixed | Measured | Independent image comparison |
| --- | --- | --- | --- |
| 17-point scatter | Pass; 37.7% data region | Pass; 67.3% data region | No clear preference; larger area adds denser numeric ticks. |
| 32-observation distribution, four long group labels | Four clipped labels | Full labels retained at the same font and canvas | Measured preferred for complete row identification. |
| 7 × 9 heatmap | Bottom axis name clipped | Complete axis name | Measured preferred; scale remains subordinate. |

[Independent visual review](independent-visual-review.md) opened all six PNGs
without reading implementation or numerical results. It assessed visual layout,
not numerical validity or font embedding. It found no mandatory visual correction
in the measured candidates and explicitly did not equate more area with better
design. Numerical/export tests are separate evidence. Screen inspection is not
a physical print test or journal acceptance.

## Density and failure boundaries

[Auto-layout tests](../../tests/test_auto_layout.py) additionally exercise dot
areas, state glyphs, multiple guides, fixed-size exports and long labels that
cannot fit. A 12 × 14 annotated heatmap retains all 168 values but fails instead
of allowing unreadable annotations. A 4 × 12 annotated heatmap at 88 × 50 mm
tests a consequential choice: a right colorbar leaves cells too narrow, whereas
top/bottom placement fits at the same 8 pt font. Cell annotation checks participate
in automatic candidate selection.

[Annotation tests](../../tests/test_annotation_review.py) measure actual text
against cell boundaries, including unequal cell dimensions and both y-axis
directions. The 0.2 mm text padding is an adjustable engineering aid.
[Draft tests](../../tests/test_draft_spec.py) execute all five chart families,
Unicode column mappings, profiles, explicit dimensions and meaningful invalid
inputs. Composition normalization, missing states, pairing and statistics are
never guessed. Existing specs preserve manual layouts unless opted in.

## Independent forward use

A fresh Agent received only [request.md](forward-use/request.md), its prepared
24-row table, the canonical EasyViz skill path and an isolated output location.
It was not given implementation changes, tests, preferred helpers or prior
conclusions. After its initial runtimes lacked Matplotlib, the parent supplied
the existing scientific Python environment. No network or paid API was used.

The Agent discovered `draft_spec.py` through the skill, produced one plot without
visual repair, and inspected actual PNG/PDF output. Its standalone bundle and
unaltered run records are preserved under [forward-use](forward-use/README.md).
The copied helper files there are an evaluation snapshot, not canonical runtime
sources. Its own independent reviewer found the panel ready within the supplied
requirements; [checks.json](forward-use/checks.json) verifies all rows/two zeros,
PDF dimensions, embedded Arial and 8 pt text, actual proportional plot/legend
geometry, color mapping and identical standalone PNG/SVG reproduction.

The initial missing dependency failures, verifier tolerance correction and
parent runtime assistance are recorded in [provenance](forward-use/provenance.json).
The task used the inherited Codex model. One successful descriptive table does
not establish success rates, cost, novice usability or performance of an external
Chinese model. Unknown source denominator and score construction remain stated
in the separate caption; no inferential tests were added.

## Local checks

The complete unit suite and an extracted-package smoke cover the changed code.
The package smoke invokes the new draft tool and renders its measured layout
outside the repository. Local logs and build metadata accompany this record.
Packaging does not update the installed client or publish a GitHub release.
