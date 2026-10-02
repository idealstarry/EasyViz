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
| `manifest.json` | Read file hashes, worksheets, column hints, row coverage, missing tokens, duplicates, small source samples and skipped/error files. Establish field meaning and scientific unit from user context. |
| `analysis-options.json` | Compare up to three reading tasks per table, suggested chart families, candidate fields and questions that affect inference. Select two or three meaningful options across the relevant tables, rather than presenting every table's options. |
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

Inspection is bounded to 100 tables, 20 MiB per file, 100 MiB total input bytes,
100,000 observations per table, 200 columns, 10,000 directory entries and eight
directory levels. A row limit makes summaries describe the inspected prefix,
not the complete source. Hidden/dependency/generated-output directories and
all symlinks are skipped; the requested output directory is excluded. Oversized
inputs should be inspected as narrower prepared tables. Unsupported files are
not read. Errors in a mixed directory are recorded while other usable tables
are inspected; no usable table yields an actionable nonzero exit without a
partial report. No table is joined merely because its field names look similar.

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
