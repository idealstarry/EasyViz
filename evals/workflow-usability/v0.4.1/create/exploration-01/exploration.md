# Create-track data exploration

This inventory contains descriptive profiles and candidate reading tasks. No inferential tests were run.

Inspected 5 table(s). Source cells remain strings; type hints do not establish scientific meanings.

## `A_export__final2.csv`

Rows inspected: 72; full row coverage: True; duplicate rows: 0.

| Column | Type hint | Missing | Unique nonmissing |
| --- | --- | ---: | ---: |
| `read_key` | text | 0 | 72 |
| `tube_key` | identifier_candidate | 0 | 36 |
| `signal_au` | numeric | 1 | 71 |
| `read_state` | categorical_candidate | 0 | 2 |
| `scan_order` | numeric | 0 | 72 |

Profile signal: `tube_key` has 36 repeated identifier(s), with up to 2 source rows per identifier. Identity and dependence are unconfirmed.

- **Read the spread, skew and raw observations of a measurement**: distribution, ecdf. candidate; confirm field meanings before plotting.
- **Read whether two supplied numeric measurements vary together**: scatter. candidate; confirm field meanings before plotting.
- **Check whether an explicit unit has measurements in multiple conditions**: paired. requires explicit pairing verification.

Resolve these points from project context or the user:

- Which identifier is the scientific unit, and do its repeated rows represent the same unit over conditions/time, technical repeats, or reused labels? Explain any repeated unit-condition cells before pairing or inference.
- Which table and measurement answer the intended question, what do their fields mean, and what are the measurement units? Read project notes or a data dictionary before choosing fields; do not join tables merely because IDs or headers look alike.

- Caution: No inferential design has been established. Descriptive previews must identify counts as source rows until scientific units and their dependence are confirmed.
- Caution: Numeric-looking identifiers stay strings and are excluded from automatic measurement candidates. Preserve leading zeros and explicitly declare a measurement role only when source context supports it.
- Caution: Missing-token counts use the recorded exact strings. Verify whether labels such as NA/null are real categories and adopt a missing-value policy explicitly.

See `analysis-options.json` for evidence columns, all cautions and candidate mappings. No inferential method was selected.

## `instrument-log.csv`

Rows inspected: 1; full row coverage: True; duplicate rows: 0.

| Column | Type hint | Missing | Unique nonmissing |
| --- | --- | ---: | ---: |
| `date` | date_time_candidate | 0 | 1 |
| `message` | categorical_candidate | 0 | 1 |

- **Establish table grain and which fields can answer a quantitative question**: clarify quantitative fields first. needs measurement roles or a prepared quantitative table.

Resolve these points from project context or the user:

- What does one row represent, which field identifies the independently sampled unit, and are measurements independent or paired/repeated?
- Which table and measurement answer the intended question, what do their fields mean, and what are the measurement units? Read project notes or a data dictionary before choosing fields; do not join tables merely because IDs or headers look alike.

- Caution: No inferential design has been established. Descriptive previews must identify counts as source rows until scientific units and their dependence are confirmed.

See `analysis-options.json` for evidence columns, all cautions and candidate mappings. No inferential method was selected.

## `old-pilot_DO_NOT_POOL.csv`

Rows inspected: 6; full row coverage: True; duplicate rows: 0.

| Column | Type hint | Missing | Unique nonmissing |
| --- | --- | ---: | ---: |
| `tube_key` | identifier_candidate | 0 | 6 |
| `arm_name` | categorical_candidate | 0 | 1 |
| `signal_au` | numeric | 0 | 6 |

- **Read the spread, skew and raw observations of a measurement**: distribution, ecdf. candidate; confirm field meanings before plotting.

Resolve these points from project context or the user:

- What does one row represent, which field identifies the independently sampled unit, and are measurements independent or paired/repeated?
- Which table and measurement answer the intended question, what do their fields mean, and what are the measurement units? Read project notes or a data dictionary before choosing fields; do not join tables merely because IDs or headers look alike.

- Caution: No inferential design has been established. Descriptive previews must identify counts as source rows until scientific units and their dependence are confirmed.
- Caution: Numeric-looking identifiers stay strings and are excluded from automatic measurement candidates. Preserve leading zeros and explicitly declare a measurement role only when source context supports it.

See `analysis-options.json` for evidence columns, all cautions and candidate mappings. No inferential method was selected.

## `plate-blank_readings.csv`

Rows inspected: 1; full row coverage: True; duplicate rows: 0.

| Column | Type hint | Missing | Unique nonmissing |
| --- | --- | ---: | ---: |
| `tube_key` | categorical_candidate | 0 | 1 |
| `signal_au` | numeric | 0 | 1 |
| `meaning` | categorical_candidate | 0 | 1 |

- **Read the spread, skew and raw observations of a measurement**: distribution, ecdf. candidate; confirm field meanings before plotting.

Resolve these points from project context or the user:

- What does one row represent, which field identifies the independently sampled unit, and are measurements independent or paired/repeated?
- Which table and measurement answer the intended question, what do their fields mean, and what are the measurement units? Read project notes or a data dictionary before choosing fields; do not join tables merely because IDs or headers look alike.

- Caution: No inferential design has been established. Descriptive previews must identify counts as source rows until scientific units and their dependence are confirmed.

See `analysis-options.json` for evidence columns, all cautions and candidate mappings. No inferential method was selected.

## `sample-index__2026.tsv.csv`

Rows inspected: 36; full row coverage: True; duplicate rows: 0.

| Column | Type hint | Missing | Unique nonmissing |
| --- | --- | ---: | ---: |
| `tube_key` | identifier_candidate | 0 | 36 |
| `arm_name` | categorical_candidate | 0 | 3 |
| `rack` | categorical_candidate | 0 | 3 |
| `unit_type` | categorical_candidate | 0 | 1 |

- **Establish table grain and which fields can answer a quantitative question**: clarify quantitative fields first. needs measurement roles or a prepared quantitative table.

Resolve these points from project context or the user:

- What does one row represent, which field identifies the independently sampled unit, and are measurements independent or paired/repeated?
- Which table and measurement answer the intended question, what do their fields mean, and what are the measurement units? Read project notes or a data dictionary before choosing fields; do not join tables merely because IDs or headers look alike.

- Caution: No inferential design has been established. Descriptive previews must identify counts as source rows until scientific units and their dependence are confirmed.
- Caution: Numeric-looking identifiers stay strings and are excluded from automatic measurement candidates. Preserve leading zeros and explicitly declare a measurement role only when source context supports it.

See `analysis-options.json` for evidence columns, all cautions and candidate mappings. No inferential method was selected.

