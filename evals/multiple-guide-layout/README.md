# Multiple-guide layout engineering diagnostic

This is a post-hoc engineering check prompted by the completed GLM comparison.
It is **not another WorkBuddy/model run**, does not replace the frozen model
outputs or their blind review, and provides no estimate of model performance.
The GLM CSV and specification were copied byte for byte; frozen originals were
never edited. `provenance.json` records their original paths and hashes.

The before runtime is the canonical helper/runtime captured before this focused
fix. It includes the earlier circle-area and explicit `statistics.none`
corrections and matches all six helper/runtime files copied by the frozen GLM
task. It differs from the earlier Deepseek snapshot. Both runtime
snapshots are retained with their hashes. Only `auto_layout.py` and
`legend_layout.py` differ between them.

## Change and bounded contract

When at least one guide is automatic, automatic guides are tried together on
the right, bottom and top. Explicit guide sides and supplied columns, colorbar
lengths, orientations and ticks remain fixed. Guides sharing top or bottom stack
outward using the complete measured envelope of prior guides. A chosen size
guide finishes its key-to-label alignment before another guide uses its bounds.
Reserved top/bottom space measures the complete occupied span, and the last
reservation is applied before candidate QA.

The selected arrangement has the largest technically feasible data-axis area
among those three side candidates. Existing guide-column and colorbar-length
variant order is retained; this is not an exhaustive search of combinations or
an aesthetic score. The helper never changes canvas dimensions, fonts, source
values, scientific mappings or quantitative marker sizes. Manual absolute
anchors remain outside automatic fitting and keep their existing behavior.

## Recorded results

All panels remain 140 × 100 mm at 300 dpi. The interval uses Arial; synthetic
probes use DejaVu Sans. Visible axis, tick and legend text remains 8 pt.
Numbers below are rounded to six decimals; `results/comparison.json` contains
the exact recorded floating-point measurements and every side attempt.

| Case | Data width before → after (mm) | Data area before → after (mm²) | Chosen sides after |
| --- | ---: | ---: | --- |
| GLM interval, two categorical guides | 44.127889 → 98.732556 | 3831.283291 → 6933.780827 | bottom, bottom |
| Synthetic grouped size scatter | 103.091347 → 103.091347 | 8804.298604 → 8804.298604 | right, right |
| Synthetic dotplot, explicit right colorbar | 46.034212 → 81.770969 | 3658.889025 → 5025.223866 | right, bottom, bottom |
| Same dotplot, all guides automatic | 46.034212 → 95.095858 | 3658.889025 → 4893.683170 | top, top, top |

The interval retains all 11 source rows, the scatter all 5, and both dot probes
all 8. Every plotting CSV is byte identical before/after. Actual plotted
coordinates and interval endpoints, face/edge colors, linewidths, raw marker
parameters, actual marker path areas and quantitative guide-key areas also
match. Canvas, actual font, typography, axis limits and statistics match. The
circle-area audit integrates the actual Bézier path with its display transform;
edge stroke is separate. The path approximates an ideal circle to about
2.9e-7 relative area error.

Every after candidate in these probes passes the existing technical checks;
all top/bottom stacks have zero overlapping guide-envelope area. Final exports
include PNG, SVG and PDF with physical-size QA, settings, plotting data and
statistics. `artist-measurements.json` records measurements from actual artists
before export, rather than only repeating specification values.

The scatter keeps its larger right-side data area. Its automatic size guide
changes from two columns to one: finalizing the preceding guide's geometry makes
the first declared column variant feasible. Its data field and quantitative
keys remain unchanged; its whole image is not asserted pixel identical.

## Visual evidence and limits

The author inspected the actual interval/dot before/after PNGs, both scatter
PNGs and the all-auto dot after PNG. The wider interval separates endpoints
horizontally while reducing row spacing and allocating a bottom band to both
guides. Mixed dot guides fit below the axes while the explicit colorbar stays
right. The all-auto dot stacks its full-range horizontal colorbar, size guide
and state guide at the top without observed clipping or collisions. This fourth
probe has author inspection and technical QA, not independent blind review.

The [fresh independent review](independent-visual-review.md) compared the first
three cases anonymously and preferred after for the interval and dotplot, with
a slight after preference for the vertically ordered scatter size keys. It
reported no hard visual blocker. These findings apply to these three images;
they do not establish a general aesthetic, journal-readiness or model gain.

The exact small-positive dot remains tiny and uses a separate nonquantitative
state flag. The zero glyph remains the configured gray symbol. No magnitude or
state styling was altered by this layout fix. Numeric locators can change tick
counts when axes move; explicit source labels, values and limits are retained.
Impossible panels still need revision rather than reduced fonts or dropped rows.

`results/legacy-custom-case-pixels.json` records temporary rerenders of the
packaged cell-atlas-dotplot and paired-effects cases after replacing their local
legend helper with each preserved canonical runtime helper. Both before/after
PNGs and saved packaged PNGs match exactly. No package archive, original case
output, preview or frozen model artifact was rewritten for these checks.

## Rerun independently

Use Python 3.11+ with `requirements.txt`. From a compatible environment:

```sh
python /path/to/multiple-guide-layout/run.py --out /tmp/easyviz-multiple-guides-rerun
```

The destination must be new. The runner verifies snapshot and copied-input
hashes, loads each runtime from its own sibling helpers, renders all four cases,
checks preserved semantics/geometry and writes a new comparison. It requires no
network access, model API, WorkBuddy or canonical repository helper. Arial is
used when installed; another system may resolve a fallback and obtain different
text metrics, which remains recorded in settings rather than hidden.

`results/portable-replay-validation.json` confirms that copying this evidence
outside the repository and running from an unrelated temporary directory
reproduced every recorded width and data area exactly on the current environment.

Focused validation: 13 auto-layout tests plus 10 legend tests passed together;
all 12 interval tests passed. A subsequent two-colorbar top/bottom regression
also passed, checking physical exports, full ranges, fixed lengths/ticks and
removal of trial axes. The auto-layout regressions cover grouped categorical
guides, mapped scatter size, mixed explicit/automatic guides and 1200 pt² size
keys whose finalized envelopes previously produced a false clipping failure.

```sh
PYTHONPATH=tests .venv/bin/python -m unittest tests.test_auto_layout tests.test_legend_layout tests.test_interval_plot -v
```
