# Paired raw observation export check — staged for v0.4.6

This candidate is isolated from production. The parent agent authorized
preparing it while the v0.4.5 source is frozen for release testing. Only
`staged-runtime/paired_plot.py` differs from its recorded baseline; the copied
core and helper sources are unchanged adapters.

## What changes

The actual circular raw-observation `PathCollection` in every block and
condition receives a semantic `point-group` registration. It retains its
actual sorted source-record ordinals and biological unit identities. Editable
color and alpha paths are advertised only when those properties actually
exist in the adopted specification.

After core export, paired QA and settings receive the same per-format
`observation_clipping` report. Confirmed clipped observation envelopes refuse
`valid_outputs`, including clipping on the actual pixel-rounded PNG canvas.
The helper digest is the captured digest of the executed core dependency.

An independent review then reproduced an inherited CSV parsing defect:
`pandas.read_csv` accepted four cells under three headers by inferring a hidden
index. The resulting marks and unit identities no longer matched the literal
named source columns. The candidate now reuses the existing strict core CSV
reader: header and rectangular-record validation happens before any figure
is drawn, and the input digest and primary element binding come from the exact
same bytes that produced the parsed table. Literal unit IDs, quoted commas,
UTF-8 BOM and original numeric spellings are retained.

Source measurements, condition/block ordering, swarm positions, circle area,
outline width, connectors, median/IQR summaries, axes, locked ranges, physical
dimensions, font size and image appearance are preserved. Summary and
connector footprints are not certified by this raw circular observation
check. General statistical appropriateness and aesthetics still require
review.

## Actual export evidence

[`actual-exports/evidence.json`](actual-exports/evidence.json) preserves four
real PNG/PDF/SVG before/after cases. The old paired code runs against the same
copied core and helper dependencies as the candidate.

| Case | Old valid | Candidate valid | Actual result |
| --- | --- | --- | --- |
| Observations inside locked `[0, 4]` | true | true | All four raw circles safe |
| Vector-safe upper range on a 66.1-mm panel | true | false | Source record 3 clipped only by the 66.04-mm actual PNG canvas |
| Locked linear `[1, 3]` endpoints | false | false | Existing refusal retained; raw source records 1 and 3 now mapped in every format |
| Locked logarithmic `[1, 100]` endpoints | false | false | Final transformed raw source records 1 and 3 mapped in every format |

The raster-only case's old nominal `mark_geometry` and numerical
`source_to_artist_audit` still pass. SVG and PDF pass the new circle-envelope
measurement; PNG reports a **0.0005084-mm** actual upper-envelope excess. The
range, area and source are unchanged; this deliberately tight case establishes
the missing export acceptance condition.

All four before/after **PNG and PDF files are byte identical**. The SVG changes
only the raw collection group identifiers to their registered semantic IDs:
after removing only those two raw collection `id` attributes, the XML tree is
identical, including all paths and transforms. Actual `plotting-data.csv`,
`summary-data.csv` and `stats.json` files are byte identical. The input CSV
bytes and adopted options are unchanged.

## Verification and integration boundary

- **17 tests pass**: seven new real-export regressions and ten existing paired
  tests, including copied-runtime portability, source mutation refusal,
  connector/summary numerical audit, overflow and renamed fields.
- New tests cover safe observations, actual PNG-only clipping, locked linear
  and log endpoints, visible marker outline, block colors and exact source
  identities. They also reject five malformed header/record variants before
  any export and verify exact quoted/numeric sample identity and consumed-byte
  digests on valid real exports.
- [`reviewer-malformed-row/evidence.json`](reviewer-malformed-row/evidence.json)
  preserves the independent original false-pass proof; the same probe now
  refuses it before drawing in
  [`malformed-row-after/evidence.json`](malformed-row-after/evidence.json).
- The initial registration-only candidate and its original manifest and
  exports are retained in `initial-registration-runtime`,
  `stage-freeze-initial-registration.json` and
  `actual-exports-initial-registration`. The final evidence incorporates the
  strict CSV correction without replacing those earlier records.
- The initial verification adapter incorrectly expected a `source-data.csv`
  artifact that this recipe does not produce. Its traceback and partial
  output are retained separately; the corrected proof compares the actual
  numerical artifacts and leaves the runtime unchanged.
- `stage-freeze.json` records this candidate and its evidence. The parent
  agent authorized applying only the paired recipe and its focused test file
  after strict parsing and the final independent review pass. Common core,
  helpers, handoff and reviewer sources remain outside this integration scope.

Focused recipe reproduction:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_paired*.py' -v
```

`verify_actual_exports.py` intentionally refuses to overwrite preserved
evidence. To rerun that immutable proof, use a fresh copied proof directory.
When local staging adapters are absent, it uses the repository production
runtime and the retained original paired source copy. Full temporary runtime
copies and initial adapter failures are preserved locally and omitted from
the recommended compact commit record.
