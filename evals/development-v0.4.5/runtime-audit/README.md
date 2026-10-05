# Current runtime audit before v0.4.5

Five functional issues were reproduced against main commit
`6c3d833b2025613a28e2461b9c8384ca130612c2`, without changing runtime code or
tests. This is a failure investigation, not an aesthetic efficacy benchmark.
The existing cross-font lane repair and PNG floor/nearest quantization repair
were not counted as new issues.

The authoritative machine evidence is [results.json](reproduced/results.json).
[reproduce.py](reproduce.py) creates fresh real exports and exercises actual
source/read/review paths; it refuses to overwrite an existing run directory.
Run it with an unused subdirectory name:

```sh
.venv/bin/python evals/development-v0.4.5/runtime-audit/reproduce.py new-run
```

The complete run is `reproduced/`. Earlier directories at this audit's root
and `reproduce.log` preserve a first harness run that stopped when the focused
replicate audit correctly rejected duplicate column names. The corrected
harness explicitly retains that rejection as a control; it does not relabel
the focused output as successful.

The three P1s below were subsequently repaired for the pending v0.4.4 stable
release. See [frozen after-repair results](repaired-frozen/results.json),
[verification harness](verify-repair.py), and
[runtime freeze](repair-freeze.json). The line references below identify the
audited pre-repair commit, not the new line positions after editing.

## 1. P1: Core renderer binds a new source to an old rendered dataset

Location: [render.py](../../../skills/easyviz/scripts/render.py), lines
1321–1322 and 1364–1368; [figure_elements.py](../../../skills/easyviz/scripts/figure_elements.py),
lines 167–178.

The core reads and draws source data, then hashes the source file after export.
The element map also hashes the then-current source file. There is no final
continuity check against the bytes actually parsed. A source replacement
during export therefore creates internally agreeing provenance records for
data that were never plotted.

Minimal input and actual result:

- [before.csv](reproduced/01-source-race/before.csv): y = 2, 3, 5, 4.
- [after.csv](reproduced/01-source-race/after.csv): y = 200, 300, 500, 400.
- A wrapper replaces the source immediately before the actual exporter runs;
  it does not modify the figure or fabricate successful QA.
- [Actual panel](reproduced/01-source-race/output/panel.png) and
  [plotting-data.csv](reproduced/01-source-race/output/plotting-data.csv) retain
  the original values. `settings.input_sha256` and the element map bind the
  replacement values.
- [qa.json](reproduced/01-source-race/output/qa.json) says `pass`,
  `valid_outputs: true`; the actual
  [Create review snapshot](reproduced/01-source-race/snapshot.json) says
  `source_provenance: passed`.

Required result: fail the attempted run when the source changes; metadata must
bind the precise bytes used to parse/draw. The review gate must not upgrade
the inconsistent render.

Repair scope: parse a captured source snapshot, keep its digest on the figure,
write those captured bindings, and check every adopted file's continuity before
setting valid outputs. Original spec/profile continuity should use the same
principle; the current test demonstrates source data specifically. Focused
replicate/paired/ECDF/matrix scripts already have source-change rejection,
which can inform a common helper without weakening their independent artist
audits.

## 2. P1: Direct CSV parsing changes malformed header/row interpretation

Location: [render.py](../../../skills/easyviz/scripts/render.py), line 558.
The same pandas entry point occurs in focused paired, replicate, ECDF, interval
and time-course preparation. The candidate helper and annotated-matrix recipe
already validate header uniqueness and row width before parsing.

The core accepts this source:

```csv
x,y
1,2,9
2,4,8
3,6,7
```

Pandas implicitly uses 1, 2, 3 as an index, yielding x = 2, 4, 6 and
y = 9, 8, 7. [The actual panel](reproduced/02-ragged-csv/output/panel.png)
therefore uses the shifted interpretation, and
[QA](reproduced/02-ragged-csv/output/qa.json) still reports `pass`, three
input/plotted rows and valid outputs.

Duplicate literal headers also remain ambiguous:
`arm,id,value,value` silently becomes `value` and `value.1`.
[Core output](reproduced/03-duplicate-csv-header/core-output/qa.json) passes
using values 2, 3, 4, 5 while the second literal value column contains
200, 300, 400, 500. In contrast, the
[focused replicate output](reproduced/03-duplicate-csv-header/output/qa.json)
correctly fails its independent source-to-artist audit, because its CSV
dictionary reader uses the other duplicate. That late failure is useful
protection, not proof that its initial parser is correct.

Required result: reject ragged rows, duplicate/empty headers and structurally
empty records before any field mapping. Do not infer an index, silently skip
a record, choose one duplicate column or alter literal IDs. Valid quoted
commas/newlines and a UTF-8 BOM should remain supported.

Repair scope: a shared strict CSV-byte reader used by core and focused input
preparation and by source-to-artist rereads. Existing candidate and matrix
guards provide the intended contract. Test actual malformed inputs and
well-formed quoting rather than merely mirroring a new helper's logic.

## 3. P1: Composition normalization overflows and reports invalid fractions as valid

Location: [render.py](../../../skills/easyviz/scripts/render.py), lines
613–617 and 623–624. Group sums operate on the numeric parser's original
dtype; only individual values are checked for finiteness.

Two actual `normalization: sample_sum` reproductions:

| Supplied finite values | Actual denominator | Actual fractions | QA |
| --- | --- | --- | --- |
| 1e308 and 1e308 | Infinity | 0 and 0; sum 0 | pass, valid |
| 18000000000000000000 and 1000000000000000000 | 553255926290448384 (uint64 wrap) | 32.53467 and 1.80748; sum 34.34215 | pass, valid |

The first export is an
[empty composition](reproduced/04-float-composition-overflow/output/panel.png).
The second is a
[clipped all-blue bar](reproduced/05-integer-composition-overflow/output/panel.png),
because the supposedly normalized bar is far above the fixed 0–1 axis.
No warning was captured in either run. Correct nonnegative proportions would
be 0.5/0.5 and approximately 0.94737/0.05263, respectively.

Required result: compute faithfully representable finite fractions, or reject
an unsupported numerical range explicitly. Never report zeroed or wrapped
normalization as valid. A declared-denominator path must also reject a true
category total that exceeds its denominator even when an integer sum wraps.

Repair scope: avoid fixed-width accumulation, check finite derived totals and
fractions, and enforce a sum-to-one invariant for `sample_sum`. A scaled
nonnegative summation can normalize huge values without overflowing the
total; if recording an unrepresentable denominator, declare that limit
explicitly rather than storing infinity or silently inventing a value.

## 4. P2: Core numeric bounds preserve point centers but clip actual glyphs

Location: [render.py](../../../skills/easyviz/scripts/render.py), lines
1150–1153 and the QA aggregation at 1389–1390. The numeric limits guard
examines values, while core clipping QA examines text only.

Input points (0,0), (0.5,0.5), (1,1), explicit x/y limits [0,1], and
fixed `point_area_pt2: 100` produce two quarter circles at the axes corners:
[actual PNG](reproduced/06-numeric-marker-clipping/output/panel.png).
The actual mark extends 1.763889 mm beyond each affected boundary.
[QA](reproduced/06-numeric-marker-clipping/output/qa.json) still says
`pass`, `valid_outputs: true`, and `clipped_text: []`.

Required result: report clipped observed glyphs separately from intentional
baseline contacts. Preserve explicit numeric bounds and sizes; report a
necessary design adjustment rather than silently expanding a locked axis.

Repair scope: measure transformed outer marker footprints after final layout,
including hollow strokes and mapped sizes, then include genuine clipping in
QA. Focused replicate's explicit mark geometry is a useful precedent. Check
linear/log scales, numeric-axis orientation, visible source rows and both
raster/vector final transforms. This is not a requirement that every data
point be separated from every other point.

## 5. P2: PNG header measurements can pass for a non-decodable export

Location: [create_review.py](../../../skills/easyviz/scripts/create_review.py),
lines 116–139 and 236–241. Header/chunk CRC checks do not establish that
an image payload exists or can be decoded.

The preserved [panel.png](reproduced/07-png-no-image-payload/output/panel.png)
has valid IHDR, pHYs and IEND chunks, but no IDAT image data (66 bytes total).
Pillow opening/loading fails with `OSError: cannot load this image`.
After saving matching current hash/size metadata,
[the actual snapshot](reproduced/07-png-no-image-payload/snapshot.json)
nevertheless reports both `export_dimensions: passed` and
`technical_qa: passed`.

Required result: unreadable current exports must fail an integrity check.
Dimensions may remain a limited header measurement, but must not be the
only current-byte check used to acknowledge a usable raster export.
This finding does not claim the helper can prove image opening or aesthetic
quality; those attestation limits remain valid.

Repair scope: validate payload structure/decode separately, with honest
`not_checked` behavior if a decoder is unavailable. Keep finite file/pixel
limits to avoid decompression exhaustion. Cover missing/corrupt/truncated
image data and ordinary valid floor/nearest-grid outputs without regressing
the v0.4.4 quantization fix.

## Complex Create functions suggested by current contracts

These are functional limits, not additional reproduced bugs:

1. A reusable raw-observations/summary view with explicitly adopted
   mean/median and SD/SEM/supplied interval semantics. The current replicate
   recipe supports sample SD or no uncertainty and requires a unit-ID field;
   the v0.4.4 Vanneste Source Data case has caption-supported mice and SEM
   but no animal IDs, so an Agent had to write custom code. Preserve source-row
   identity without inventing cross-condition subjects. Separate raw and
   summary slots can prevent actual summary occlusion.
2. A common plot/export/review scaffold for focused and custom charts,
   retaining captured source bytes, physical geometry, resolved font,
   source-to-artist evidence, requested formats and workbench region notes.
   Complex cases should not repeatedly invent incompatible metadata formats.
3. Explicit layer adapters for supplied analysis results, such as prespecified
   pairwise effects/uncertainty or multiplicity-adjusted labels. Statistical
   results must retain comparison definitions and source bindings; no automatic
   significance hunting or decorative summary layers are implied.

Keep the two tracks. These functions support Create from a question and data;
Reproduce still starts from an adopted reference structure. No MCP
implementation is needed for these repairs or reusable functions.

## Inspection performed

The audit actually opened the current source-race, ragged-parser, two
composition and boundary-clipping PNGs. They match the concrete numeric
findings above. The invalid PNG's decode failure was tested directly.
The same local pinned runtime was used for all reproductions; this does not
claim Linux/Windows verification or first-output aesthetic efficacy.

Runtime file digests are recorded in `reproduced/results.json`. The main task
owns all later repairs, tests, release decisions and version updates; these
artifacts preserve the pre-repair failures for verification.

## Publication-blocking repairs completed

The repaired runtime parses and hashes one exact strict CSV byte snapshot,
saves its original bytes as `source-data.csv`, and revalidates captured
data/spec/profile/runtime digests before render, before export and after
export. The element map prefers these captured digests; it does not relabel
old artists with source replacements. The preserved
[source replacement result](repaired-frozen/source-race/review-snapshot.json)
now has invalid output QA and failed review source provenance. Ragged rows
and duplicate headers fail before any panel is exported.

Composition uses exact source-decimal sums and finite plotted ratios. Actual
new exports show [0.5/0.5](repaired-frozen/float-sum/output/panel.png) and
[18/19 versus 1/19](repaired-frozen/integer-sum/output/panel.png); both sum to
one and retain literal original CSV bytes. A total above binary64 capacity is
recorded as exact decimal text, never infinity. When inspecting the derived
CSV, read `_easyviz_denominator_text` as a string; a generic pandas inference
can itself reinterpret a text exponent above float capacity as infinity.
The first repair-verification harness made that inference mistake; it is
preserved in `repaired-final/`, and `repaired-frozen/` uses the explicit text
dtype. These are harness revisions, not additional model-quality trials.

Independent root review then identified two further boundaries addressed
before freezing:

- CLI spec loading now uses `render_spec_file`, carrying the same bytes from
  parse to render. Replacing the spec after parsing cannot bind the new hash
  to the old adopted dictionary. A Python dictionary must match an existing
  claimed spec file, or omit that unrelated file claim. Not-yet-saved spec
  paths remain valid relative-profile contexts with an honestly absent hash.
- Zero literals such as `0e-1000000000` contribute neither precision demand
  nor digits to summation. Nonzero numeric underflow fails explicitly. Valid
  zero plus one retains both observations and proportions zero/one.

Targeted evidence at the frozen runtime:

- [43 renderer tests](renderer-repair-tests.log), 6.639 seconds, passed.
- [7 profile tests](profile-binding-repair-tests.log), 3.462 seconds, passed.
- [11 element binding tests](element-binding-repair-tests-final.log),
  12.370 seconds, passed.

The initial computed-denominator test expected one specific Decimal spelling;
it was corrected to test exact numeric equality. The first profile run exposed
the legitimate virtual spec-path compatibility boundary; its failed log is
retained, and the actual API plus regression test were repaired. Historical
logs are not current passing evidence. The root task owns full suite,
cross-environment verification, packaging and release publication.

The endpoint marker-footprint issue remains explicitly deferred to v0.4.5
physical QA; no axis bounds, marker sizes or explicit settings were silently
changed to hide it. PNG decodability is separately repaired by the root owner
in `create_review.py`, outside this agent's runtime ownership.

One final independent publication review reproduced a helper execution race:
the old helper ran, its file was replaced after execution, and a later hash
incorrectly bound the replacement to the old exported artists. The repaired
loader now captures each helper once and compiles/executes those exact bytes,
instead of separately executing a loader or cached bytecode and rereading its
source for a digest. The executing renderer's digest is captured before
third-party/helper imports. Real copied-runtime regression tests replace both
the helper and renderer files immediately after an actual helper executes;
both retain their consumed digest and refuse export, rather than inventing
new-source provenance.

The final helper-capture freeze supersedes the previous frozen runtime while
preserving its evidence:

- [44 renderer tests](renderer-helper-capture-tests.log), 6.534 seconds, passed.
- [7 profile tests](profile-helper-capture-tests.log), 3.542 seconds, passed.
- [11 element binding tests](elements-helper-capture-tests.log), 13.042 seconds,
  passed.
- [Actual repeated repaired exports](repaired-helper-frozen/results.json) retain
  the strict-source, rejected race, and correct large-value composition results.
- [Final source and evidence hashes](repair-helper-freeze.json).

The independent helper race before/after probe belongs to the literature review
owner under `evals/release-qa/v0.4.4/prepublication-integrity/`; this audit does
not modify or overwrite that review evidence.

The final self-loader check closes the equivalent renderer bytecode-cache
boundary. A timestamp/size-valid stale `.pyc` executed area-12 markers while
the replacement source defined area 81; the earlier loader incorrectly claimed
the replacement hash and passing QA. The immutable actual
[before result](self-bytecode-before/evidence.json) includes its old SVG/PNG.
The current loader compiles its captured source with `dont_inherit=True` and
compares the actually executing module code before third-party imports.
Filename/module metadata are not part of that code comparison. The same stale
cache now [refuses import before any export API](self-bytecode-after/evidence.json).

- [46 renderer tests](renderer-self-bytecode-tests.log), 7.220 seconds, passed;
  includes actual portable relative/absolute CLI exports, importlib/API loads,
  exact helper execution and actual stale self-cache refusal.
- [Final repeated scientific repair exports](repaired-bytecode-frozen/results.json)
  still reject source replacement/CSV ambiguity and produce the correct large
  finite composition fractions.
- [Final integrated source/evidence freeze](repair-final-freeze.json).

The workbench owner separately applied only two narrow existing-production
snapshot guards after this reviewer reproduced them: captured spec/script/data
bytes must match the consumed version during acceptance, and restore must
match the accepted QA digest and passing export hashes. Independent real
mapped PNG/PDF/SVG probes reject all three A -> B -> A source-copy cases before
an accepted directory and corrupt QA metadata before a restore target:
`../workbench-audit/reviewer-production-snapshot-after/evidence.json`.
The independent 24-case application regression suite passes in 1.816 seconds.
New custom handoff/auxiliary functionality remains isolated in the v0.4.5 stage.
