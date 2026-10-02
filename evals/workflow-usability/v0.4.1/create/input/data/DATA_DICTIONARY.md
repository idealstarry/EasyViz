# Study and field meanings

This is a synthetic teaching dataset. Current experiment: 36 independently sampled mice, 12 mice in each of Vehicle, Low dose, High dose. Each mouse belongs to exactly one arm. There is no pairing or longitudinal design. Each mouse has two technical instrument reads; one read failed.

- `A_export__final2.csv`: current technical reads. `tube_key` is a literal identifier, including leading zeros; `signal_au` is background-corrected fluorescence in arbitrary units. Empty failed read is missing, never zero. `scan_order` is instrument order, not time.
- `sample-index__2026.tsv.csv`: current sample-to-arm lookup. Join on literal `tube_key`; row order differs. `rack` is a handling batch balanced across arms, not another experimental unit.
- `old-pilot_DO_NOT_POOL.csv`: separate historical pilot, with reused identifiers; do not combine.
- `plate-blank_readings.csv`: instrument QC only; do not subtract again or count as specimens.
- `instrument-log.csv`: notes only.

The analysis unit is one mouse. Average its available measured technical reads first; retain all 36 mice, including the mouse with one measured read. The main question is whether the distributions shift with dose relative to Vehicle. Describe all arms and, if doing inference, justify the independent-unit method, state effect direction, and correct the two comparisons to Vehicle as one family. No other covariate analysis is required.
