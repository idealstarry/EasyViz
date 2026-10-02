# Independent audit of the new plotting families

The evaluator in this folder reads the official XLSX archives as XML, reads the
prepared CSVs independently, and inspects actual SVG/PDF/PNG exports. It imports
neither the source extractors nor the plotting implementation. The reports
record the checked export hashes, so later visual revisions can be audited again.

- `source-verification.json`: 20 source-integrity checks passed. All 254 Urschel
  measurements retain their participant, time point, infection class, worksheet
  coordinate, and decimal value. All selected measurements and classifications
  also agree with the separate master worksheet. All 84 Truong numeric lexemes
  are preserved, including 3 true zeros and 21 supplied ratio values.
- `source-and-exports.json`: 60 checks passed for source integrity and six actual
  exports: paired observations, the explicit connector adaptation, the ECDF
  adaptation, stacked components, supplied ratios, and grouped components.
  Actual SVG/PDF checks cover point coordinates, raw-scale medians/IQRs,
  empirical jumps, component means, sample SD endpoints, declared hatches,
  physical canvas dimensions, and PDF font sizes. Logarithmic superscripts
  retain conventional 70% mathematical typography within an 8 pt base font.
- `transfer-verification.json`: 33 checks passed on synthetic engineering
  inputs with renamed roles, literal `NA`/leading-zero identifiers, repeated
  ECDF values, negative/zero linear measurements, three repeated conditions,
  two blocks, and grouped components. Reversing input rows preserves each PNG.
  Duplicate ECDF units and incomplete paired/component observations are
  rejected, and each failed attempt invalidates previous exports in its QA.

The Truong ratio check confirms the supplied ratios agree with
`(HDR-only + shared)/(mutEJ-only + shared)`; these values are never substituted
with a ratio calculated from group means. Stacked points and intervals describe
per-unit component totals. Total SD is the SD of those sums, not the sum of
component SDs. The display names of the two `-` controls come from the published
figure/caption because the workbook alone does not distinguish them.

The paired summary audit derives quartiles from sorted raw observations using
the adopted Weibull interpolation, separately from the log display transform.
The article does not identify its quartile estimator, so this verifies the
declared adaptation rather than claiming an exact match to undocumented author
software. IQRs remain descriptive observation ranges, not confidence intervals.

## Repaired export issue

`ecdf-first-export-failure.json` preserves the first independent failure.
Matplotlib's default path simplification removed 32 and 42 vertices from the
Before and After curves respectively, changing narrow empirical steps despite
passing the renderer's in-memory artist audit. The ECDF renderer now disables
simplification explicitly. Re-auditing the current SVG and PDF confirms every
one of the 127 observed jumps per group is retained.

## Rerun

The official workbooks remain outside the repo; they are audit inputs and are
not included in the plugin. Supply their local paths explicitly if needed:

```sh
.venv/bin/python evals/reproduce-inputs/new-families-audit/verify.py \
  --urschel-workbook /path/to/41467_2024_47429_MOESM4_ESM.xlsx \
  --truong-workbook /path/to/41592_2023_2162_MOESM6_ESM.xlsx \
  --exports \
  --report evals/reproduce-inputs/new-families-audit/source-and-exports.json

.venv/bin/python evals/reproduce-inputs/new-families-audit/transfer_probes.py
```

The transfer inputs are explicitly synthetic. They test portability and failure
handling; they do not add independent studies or biological replications.
`reviewed-renderer-hashes.json` records the implementation snapshot inspected.
Fresh visual/aesthetic reviews are recorded by the separate figure reviewers.

## Actual package replay

`replay_portable.py` extracts a hash-pinned ZIP to `/private/tmp`, then executes
the six packaged case wrappers with that temporary directory as their working
directory. It supplies no runtime override. A Python audit hook records each
wrapper's actual child command, and recorded renderer/helper hashes are checked
against the extracted scripts. Output directories are separate from case inputs.

`../diversity-portable-replay.json` records a 6/6 pass for the 356-file ZIP with
SHA256 `779c6237bb0294dd03a817140db93466f25b2c63d080a8410c2cf88188609b1f`.
All six PNGs match the reviewed repo exports byte for byte; all six PDFs preserve
their physical dimensions. Arial, the adopted font sizes, source CSV bytes, and
decoded spec objects are preserved. The three Truong spec files have different
byte hashes because packaged JSON writes `µ` as `\u00b5`; their decoded keys and
values are identical. No extracted input or packaged code is changed.

`../diversity-portable-replay-initial.json` preserves the initial audit-criterion
failure, which required byte-identical JSON serialization. Its six wrappers and
images already succeeded. The final audit distinguishes source CSV byte identity
from spec semantic equality and reports both JSON byte hashes transparently.

This evidence is same-environment portability and pixel replay. The evaluator
uses the existing Python/library/font environment and repo reference files; it
does not establish cross-platform compatibility or a new aesthetic assessment.

```sh
.venv/bin/python evals/reproduce-inputs/new-families-audit/replay_portable.py \
  --expected-sha 779c6237bb0294dd03a817140db93466f25b2c63d080a8410c2cf88188609b1f
```
