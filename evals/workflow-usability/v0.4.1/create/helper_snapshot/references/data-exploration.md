# Explore a data directory in create

Use this entry point when the user supplies a local directory or table and has
not selected a chart or reading task. Keep the two tracks separate: a reference
image that defines the requested structure belongs to **reproduce**. Use
`--inventory-only` to inspect its supplied directory without generating create
recommendations. Inventory does not choose or change the active track; retain
the reference-driven geometry and adopted reproduction specification.

## Inspect without changing sources

```bash
python "$EASYVIZ_SKILL/scripts/inspect_data.py" \
  --input /path/to/project-data --out /path/to/project/exploration-01
```

`--input` accepts a directory, UTF-8 CSV/TSV, or XLSX workbook. Set
`EASYVIZ_SKILL` to the installed `skills/easyviz` directory; the script works from
an unrelated working directory. XLSX requires `openpyxl` from the runtime
requirements. Use a fresh output directory for each inspection.

The command creates:

| File | Agent action |
| --- | --- |
| `manifest.json` | Read file hashes, worksheets, column hints, row coverage, missing tokens, duplicates, small source samples and skipped/error files. `intake_signals` records generic headers, repeated identifier patterns and suspected summary columns; these are observed clues, not established scientific roles. |
| `analysis-options.json` | Compare up to three reading tasks per table and read its `intake.priority_questions` and `intake.cautions`. Resolve consequential uncertainties from available project context first, then select two or three meaningful options across the relevant tables, rather than presenting every table's options. |
| `exploration.md` | Give the user a compact inventory and candidate directions. Keep detailed source profiles in the JSON files. |

For common source inventory in an already selected track, run:

```bash
python "$EASYVIZ_SKILL/scripts/inspect_data.py" \
  --input /path/to/project-data --out /path/to/project/inventory-01 \
  --inventory-only
```

This mode writes only `manifest.json` and `exploration.md`, sets
`mode: "inventory"` and `track: null`, and produces no chart, analysis-method or
field-mapping recommendations. The manifest's `track: null` means the inventory
does not select a track; it does not reset an existing create/reproduce choice.
Use the inventory to understand the supplied tables, then continue the already
adopted track. The bounded scan, descriptive profiles and source-preservation
rules are identical in both modes.

CSV/TSV values remain strings, including `001` identifiers. Numeric summaries
are separate hints; no source value is replaced. XLSX retains stored values as
strings, ISO date values and formula text; Excel number formats are not applied,
so a numeric cell formatted `000` still has its stored numeric value. Formulas
are never executed. Empty worksheet rows are skipped. Default profile missing
tokens are exact strings and are recorded explicitly; whitespace is not removed
when matching missing tokens. `NA` may be a real category in a particular
study, so adopt a different token list when needed.

Numeric summaries use original finite values. Median and inclusive quartiles
use overflow-safe interpolation that preserves tiny values beside large
outliers. An unrepresentable sample SD is recorded as `null`; source values are
not rescaled or replaced.

Inspection is bounded to 100 tables, 20 MiB per file, 100 MiB total input bytes,
100,000 observations per table, 200 columns, 10,000 directory entries and eight
directory levels. A row limit makes summaries describe the inspected prefix,
not the complete source. Hidden/dependency/generated-output directories and
all symlinks are skipped; the requested output directory is excluded. Oversized
inputs should be inspected as narrower prepared tables. Unsupported files are
not read. Errors in a mixed directory are recorded while other usable tables
are inspected; no usable table yields an actionable nonzero exit without a
partial report. No table is joined merely because its field names look similar.

## Recognize uncertain row grain before recommending analysis

Read each table independently. A measurement table, a sample metadata table and
a supplied-summary table can share an ID field while requiring different next
steps. Repeated values do not establish a join key, technical-replicate relation
or pairing. The source files and inspected rows are retained without joining,
deduplicating or aggregating them.

The profile includes these bounded signals:

- Generic names such as `v1`, `x` and `value` remain unresolved without a data
  dictionary or project context. Numeric strings become numeric *candidates*;
  numeric-looking IDs, including leading zeros, remain string identifiers.
- Identifier profiles record how many IDs repeat, their minimum/maximum source
  rows, whether they span candidate groups and whether an ID/group combination
  occurs more than once. These patterns expose possible repeated measurements
  and technical repeats. They do not establish the scientific unit. Unique
  identifiers alone do not trigger a paired-chart suggestion. Pattern profiling
  covers the first six identifier candidates against at most six group fields;
  `identifier_pattern_scope` records this limit. Every column still retains its
  individual duplicate/nonmissing profile.
- Bracketed column labels such as `time (h)` or `signal [AU]` are preserved as
  literal `unit_label_hint` text; the tool does not adopt or convert units.
- Numeric estimate columns beside names resembling SD, SEM, bounds or `n`
  yield `summary_data.status: "suspected"`. This is a name-based clue and can be
  wrong. A mean measured separately for each independent specimen can still be
  an observation-level value; resolve the row meaning from source context.

For suspected summaries, the create candidates propose reading supplied
estimates and uncertainty. They emit **no raw-observation analysis plan** and
do not propose tests on the summary rows. A bounds table can use the interval
recipe after adopting the literal bounds and their meaning; a numeric
time/dose table can use the timecourse recipe with explicit SD or supplied
bounds. A column called `SEM` does not meet the SD contract. A named `n` column
does not establish an inferential sample size, and SD/SEM/CI are never
interconverted from names alone. Read the selected recipe's required fields
before proposing executable mappings.

Each create table has at most three `intake.priority_questions`, prioritized
around uncertainty meaning, row grain/repeated units and field meaning/units.
Use project notes to answer them where possible. Ask the user only about the
remaining uncertainty that changes the next analysis or figure. Do not present
every question and every table as a long questionnaire. Descriptive previews
can proceed with explicitly unknown units when they identify their counts as
source rows and preserve all observations.

`--inventory-only` retains these descriptive signals in `manifest.json`, but
does not invoke create guidance or emit intake questions, chart recommendations
or analysis plans. Continue the selected track with its existing specification.

## Turn candidates into a meaningful proposal

1. Read existing project context, the inventory and source samples. Treat names
   and type hints as clues, not established biological or clinical meanings.
2. Select a plausible reading task: measurement distribution, association, or
   verified within-unit change. Explain which question each proposed figure
   answers and which fields it uses. Keep raw observations visible where useful.
3. Offer two or three relevant directions. A table with no quantitative field
   needs role clarification or a prepared quantitative table; identifier counts
   are not a substitute for the missing measurement.
4. Record the selected question, fields, units and design. Candidate mappings
   are illustrative choices; confirm them from the source context before
   drawing. Descriptive previews can proceed with an unknown experimental unit
   if their counts are explicitly row counts.
5. Run an adopted descriptive plan with `analyze.py`, create a spec with
   `draft_spec.py` or a focused recipe, then render and inspect the output. XLSX
   needs an explicit, traceable export of the chosen sheet to CSV before these
   CSV-based tools. Preserve string identifiers during that export.

An option's `descriptive_analysis_plan` uses the analysis tool's plan schema.
Without declared design it sets `unit: null`, `structure: "unknown"`,
`confirmed: false` and an explicit row-level unit definition. It runs no
inferential method. The default `missing_policy: "error"` asks for an explicit
missing-value decision instead of silently discarding observations. A
recommended family may have additional required roles: read the advertised
recipe contract before generating a plot spec. A distribution without a group
can use the ECDF recipe's single-distribution contract, or an explicitly added
constant category for a distribution plot.

## Supply established field roles and study design

To guide the recommendations from known source context, save a JSON file and
pass `--design /path/to/intake-design.json`:

```json
{
  "table": "observations.csv",
  "row_kind": "observations",
  "question": "How does the supplied measurement differ between conditions?",
  "fields": {"group": "condition", "value": "measurement"},
  "design": {
    "unit": "sample_id",
    "unit_definition": "one independently sampled biological specimen",
    "structure": "independent",
    "confirmed": true
  },
  "missing_tokens": ["", "NA"],
  "missing_policy": "error"
}
```

`table` is a relative source path or exact `table_id` from the manifest. Add
`sheet` when a workbook contains multiple tables. `fields` accepts `group`,
`value`, `x` and `y`; the unit column belongs in `design.unit`. Structures are
`independent`, `paired` or `unknown`; a confirmed design requires a known unit,
a unit definition and a known structure. A declaration records scientific
evidence supplied to the tool; it does not prove independence or automatically
run tests. Columns must exist and the declared value must be numeric under the
adopted missing tokens.

The declared `design.unit` is excluded from automatic measurement, group and
association candidates even when its column name does not resemble an ID.
It cannot simultaneously be declared as a measurement or grouping field.

Optional `row_kind` is `observations`, `summaries` or `unknown` (default). Set it
from source evidence. `observations` resolves a false name-based summary hint,
while `summaries` prevents a raw-observation analysis plan even when the columns
have generic names. Declaring row kind does not declare independent units or
uncertainty semantics. The original name/value signals remain in the manifest
for review. These are additive schema-version-1 fields; existing declarations
remain valid.

Before choosing inference, establish the scientific question, experimental
unit, pairing or repeated measurements, intended comparisons and missing-data
handling. Cells, repeated measurements and technical replicates are not
automatically independent specimens. Paired-looking IDs must be verified and
duplicate unit-condition values resolved explicitly. Read the statistics plan
contract before selecting a method or multiplicity family; do not run a menu
of tests and keep the most favorable p value.

Deliver the selected plan, source references, transformations, computed results,
runnable plotting script, individual panel exports, separate `caption.md`, and
actual review evidence. Keep the inventory and unused candidates available for
inspection without treating them as scientific conclusions.
