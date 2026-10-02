# Figure diversity and quality update, 2026-10-02

This update adds reusable views for observed distributions, repeated conditions
and replicate components, using two additional public Nature-family Source Data
workbooks. It extends the earlier [source-data update](quality-update-2026-10-02.md).
Alternate views of one workbook are counted as views, not independent studies.

## New capabilities and real examples

| Input and reading task | Reusable capability | Reviewed example |
| --- | --- | --- |
| Identified units measured at multiple conditions | Raw points, median/IQR, optional within-unit connectors, linear/log axis, optional cohort blocks | [Urschel paired observations](../../examples/no-author-code/urschel-paired/README.md): 127 complete before/after pairs, four cohort/condition clouds; a separate connected view |
| Raw distributions | Exact right-continuous ECDF, full repeated-value jumps, optional groups and log/power-of-ten ticks | [Urschel ECDF](../../examples/create/urschel-ecdf/README.md): all 254 observations, two marginal curves |
| Replicate component measurements | Stacked means with raw totals/total SD; grouped means with raw component values/component SD; supplied scalar summaries | [Truong components](../../examples/no-author-code/truong-components/README.md): 7 conditions × 3 biological replicates, 63 component values and 21 supplied ratios, three separate views |

The Urschel paper is [Nature Communications 15, 3077 (2024)](https://www.nature.com/articles/s41467-024-47429-8).
The Truong paper is [Nature Methods 21, 455–464 (2024)](https://www.nature.com/articles/s41592-023-02162-w).
Official workbook identities, extraction scripts, source cells, public license
attribution, reference readings and adopted specifications accompany the cases.
No author plotting code is required. ECDF and the split/grouped component views
are new designs; their captions disclose their relation to the published panels.

## Aesthetic and scientific decisions

All six panels use adopted physical dimensions and Arial 8 pt, editable vector
exports, restrained palettes, explicit raw observation layers and separate
captions. Titles, explanatory footnotes and decorative panel labels are omitted.
Thin paired-point outlines now also appear on the categorical guide keys. ECDF
line keys default to an adjustable 6 mm, retaining the curve's stroke and color.
The independent final-size image review accepts these candidates with disclosed
notes about dense connectors and near-zero control visibility.

The summaries preserve different meanings: raw-scale median/IQR for paired
distributions, empirical fractions for ECDF, sample SD for replicate variability,
and per-replicate supplied ratios. Pairing and independence are never inferred
from row order or repeated replicate numbers. True zeros are retained; unknown
published interval/test definitions are documented rather than reconstructed.

An actual SVG/PDF audit exposed dropped ECDF vertices caused by path
simplification. Exported paths now retain every empirical jump. All three new
renderers additionally retain exact original value text alongside parsed numbers
in `_easyviz_source_value_text`, so decimal serialization cannot erase the
source spelling. Recipes now demonstrate absolute runtime/input/output paths and
a new attempt directory, following a WorkBuddy working-directory reset.

## Validation and package identity

- The completed local unit suite passed **145 tests**. Meaningful regressions
  cover source integrity, ties and dense vector paths, pair completeness,
  missing components, invalid/stale outputs, geometry and literal value trace.
- [Independent source and actual-export audit](new-families-audit/source-and-exports-final.json):
  **60/60 checks passed**, independently parsing raw workbook XML and inspecting
  actual SVG/PDF geometry. [Source-text follow-up](new-families-audit/source-text-trace-final.json)
  separately checks the final six outputs' exact value strings.
- [Independent rendered-image review](new-family-visual-review/final-review.md):
  **ready_with_notes**, no unresolved visual corrections, with hashes for all
  six candidates. Case-specific review records are bundled with the examples.
- [Synthetic transfer checks](new-families-audit/transfer-verification.json):
  **33/33 passed** for renamed fields, literal IDs, ties, repeated conditions,
  row permutation and invalid inputs. This preserved report predates the final
  guide/source-text refinements; it is not additional literature evidence.
- [Extracted package checks](diversity-package-validation.json) exercise package
  structure, the core, draft/measured layout and five real Source Data wrappers,
  using an explicit DejaVu Sans override. [Exact portable replay](diversity-portable-replay.json)
  reruns the six new views from an extracted ZIP with the original Arial specs
  and compares their reviewed PNG identities and PDF dimensions.

The extracted package check passed. All **six portable replays passed**, with
byte-identical reviewed PNGs and matching physical PDF dimensions. Input CSV
bytes were unchanged. Specs retained equal JSON values; Unicode escaping during
packaging changes some spec bytes without changing their meaning. The initial
audit's overly strict byte-equality criterion and its correction are retained.

The local development bundle keeps manifest version **0.2.0**, contains **356
files**, and has ZIP SHA-256
`779c6237bb0294dd03a817140db93466f25b2c63d080a8410c2cf88188609b1f`.
This is a local build, not a new published release or installed client update.
Replay evidence concerns this environment, not identical fonts on every platform.
Numerical/export checks and screen reviews do not establish journal acceptance.

## Practical Agent iteration

[WorkBuddy records](../workbuddy-new-families/README.md) contain one natural
EasyViz-assisted ECDF task and one intentional correction replay using the UI's
GLM-5.3-Flash label. The Agent found the ECDF resource itself and mapped Chinese
column names. Concrete feedback led to the line-key, source-text and caption
guidance improvements above. The updated output passed **12 independent
checks**, retained 254 exact value texts and used accurate observation-unit and
zero-tie wording. Its working-directory mistake was recovered; hashes establish
that the earlier frozen results suffered no content loss.

Both exact skill snapshots and all original outputs are retained. The second
run used the updated helper, but precedes the subsequent absolute-path recipe
examples. It is a correction check in the same conversation, with no baseline
arm or general model-performance claim.
