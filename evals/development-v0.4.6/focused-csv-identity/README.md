# Focused CSV identity correction for v0.4.6

The parent agent authorized only four additional recipe CSV readers and
their focused regression tests after the independent paired review passed.
Common `render.py`, `figure_elements.py`, handoff and reviewer modules are
unchanged. This work adds no plotting or statistical algorithm.

## Actual defect

[`before-exports/evidence.json`](before-exports/evidence.json) retains real
PNG/PDF/SVG executions for legal control CSVs and malformed CSVs with one
extra leading field in every record.

| Recipe | Original actual malformed result |
| --- | --- |
| ECDF | `valid_outputs=true`; inferred hidden index shifts literal unit/group columns |
| Interval | `valid_outputs=true`; inferred hidden index shifts literal label/estimate columns |
| Timecourse | `valid_outputs=true`; inferred hidden index shifts literal time/summary columns |
| Replicate | `prepare` shifts columns; separate raw Python-statistics audit refuses before export with a misleading color error |

The fourth case is not described as a false successful export. Its reader
still parsed a malformed table as a different set of named measurements.
The initial probe's overly strong assertion is retained in a separate log.

## Correction and unchanged controls

All four `prepare` functions use the existing core strict UTF-8 CSV reader.
ECDF/interval raw audit rereads use the same structural validation. Replicate
raw audit also uses that reader and then ordinary record dictionaries; its
independent Python `statistics` calculations are unchanged. This also fixes
an inherited legitimate UTF-8 BOM case that otherwise raised `KeyError` for
the first header in replicate's raw audit.

Each recipe's primary digest comes from the exact captured bytes returned by
that reader, and the element manifest and saved settings use the same
consumed primary binding. Existing current-source checks refuse inputs that
change after consumption. No hidden index is inferred, empty record is
skipped, or duplicate header is renamed.

[`after-exports/evidence.json`](after-exports/evidence.json) records the same
four legal cases and four malformed inputs after repair. All malformed
inputs now fail with a CSV structure error before exporting any panel.
All four legal controls' **PNG, PDF and SVG files are byte identical** to
their original exports. Their full prepared numerical tables are identical,
including IDs, values, intervals, summaries and internal source-record
positions; [`legal-parity.json`](legal-parity.json) records the comparisons.

## Focused tests

Three meaningful regression methods cover **28 real scenarios**:

- Four recipes × five malformed header/record variants fail before any
  figure export or mapped-source manifest.
- Four recipes accept actual BOM/quoted-comma/Unicode/leading-zero identity
  CSVs; QA, settings and SVG element manifests bind the exact consumed raw
  byte digest. Existing numeric quantities and available literal source
  spellings are preserved.
- Four actual A→B→A source-consumption races use numerically identical
  measurements with different unused notes. The output must refuse validity
  and bind consumed B bytes, rather than claiming the restored A file.

All three methods pass. The original failed legitimate BOM probe is retained
and the corrected source is independently reviewed before production copy.
The parent agent owns the complete suite, release and package replays.
