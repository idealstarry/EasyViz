# Integration after v0.4.4 publication

The root agent confirmed publication of v0.4.4 and all passing CI jobs, then
authorized applying the independently reviewed candidate. The production
baseline `05981e…` was checked before copying the staged renderer and new
helper. The original staged source/evidence manifest remains immutable.

## Applied scope

- `render.py` and `observation_clipping.py`: final circular observation
  envelopes at each actual export canvas; confirmed clipping fails core QA.
- `preview_choices.py:_render_distribution` and `replicate_plot.py:render`:
  consume the actual report, save it unchanged in both QA and settings, and
  require no confirmed clipping before declaring outputs valid. The new
  helper's actual executed digest is retained.
- Required helper closure constants in ECDF, paired, interval, timecourse,
  annotated-matrix and replicate consumers, plus the interval/replicate copied
  runtime fixtures: include the new mandatory helper. Preview inherits the
  ECDF closure. No scientific computation or drawing is added to these five
  other recipes.

No source values, point coordinates, ranges, marker sizes, linewidths, bars,
statistics, candidate choice or publication style were changed.

## Actual proof and checks

[`focused-integration/actual-exports/evidence.json`](focused-integration/actual-exports/evidence.json)
retains four real before/after cases. The previous consumer logic runs from
its immutable source copies against the same repaired core used by the new
consumer. All before/after PNG, PDF and SVG files are byte identical:

| Actual case | Before valid | After valid | What the new report measures |
| --- | --- | --- | --- |
| Preview raw values exactly on locked `[1, 3]` endpoints | true | false | 2 clipped raw observation circles |
| Preview raw values inside locked `[0, 4]` | true | true | Safe observation envelopes |
| Replicate vector-safe upper endpoint on a 66.1-mm panel | true | false | 1 circle clipped only by the 66.04-mm rounded PNG canvas |
| Replicate source points inside locked `[0, 4]` | true | true | Safe observation envelopes |

The replicate regression's old nominal `mark_geometry.status` is **pass** in
both versions. SVG and PDF still pass; the actual rounded PNG does not. This
proves the new acceptance condition, rather than merely repeating an old
failure detector. Source CSV bytes and adopted options remain unchanged.

The new observation test module now has **16 passing tests** (14 geometric
tests plus two focused end-to-end tests, each with failing and safe controls).
All **46** core renderer tests passed after integration. All **80** relevant
existing focused tests passed after required helper closure was completed.
The initial copied-runtime failures are retained in logs; both were missing
the new mandatory helper, and no prior real-picture fixture newly failed.
The root agent owns the full suite, package, case replays and release.

## Remaining scope for v0.4.6

1. Register paired raw circular collections with their actual source records,
   then consume the per-format envelope report. Paired currently retains its
   original nominal-canvas circle check; it does not yet receive new raster
   envelope coverage merely by importing the helper.
2. Give custom raw `Line2D` observations (e.g. CCL2 and paired coefficients)
   an explicit physical-marker contract, including their actual filled/hollow
   glyph paths and visible stroke joins. Their independent case validators
   remain authoritative; this circular PathCollection check does not certify
   those artists.
3. Keep summary/estimate markers and uncertainty strokes under a separate
   declared geometry contract. Interval estimates and timecourse means are
   not individual raw observations; matrix cells, bars and ECDF curves are
   also outside this new check.
4. If boundary-valued data must keep a natural zero/min/max axis, consider an
   **explicitly adopted** observation clip policy that displays the full mark
   across the axes edge while retaining figure-page clipping checks. Do not
   silently move data, enlarge a locked range or shrink a quantitative area.

The original staged README describes the pre-integration snapshot. This file
records the subsequent authorized integration; `stage-freeze.json` is retained
unchanged and `integration-freeze.json` records the production source/evidence.
