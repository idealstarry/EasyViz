# Create-track data exploration

This inventory contains descriptive profiles and candidate reading tasks. No inferential tests were run.

Inspected 1 table(s). Source cells remain strings; type hints do not establish scientific meanings.

## `observations.csv`

Rows inspected: 24; full row coverage: True; duplicate rows: 0.

| Column | Type hint | Missing | Unique nonmissing |
| --- | --- | ---: | ---: |
| `sample_id` | identifier_candidate | 0 | 24 |
| `condition` | categorical_candidate | 0 | 2 |
| `signal` | numeric | 0 | 24 |
| `viability_pct` | numeric | 0 | 24 |

- **Read the spread, skew and raw observations of a measurement**: distribution, ecdf. candidate; confirm field meanings before plotting.
- **Read whether two supplied numeric measurements vary together**: scatter. candidate; confirm field meanings before plotting.
- **Check whether an explicit unit has measurements in multiple conditions**: paired. requires explicit pairing verification.

Confirm the observation unit, field meanings and intended question before inference. See `analysis-options.json` for mappings and consequential questions.
