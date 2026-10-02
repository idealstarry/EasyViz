# Planned analysis

Question: Do the mouse-level signal distributions differ for each dose relative to Vehicle?

Design: independent; confirmed: True; unit column: specimen_id; unit meaning: One independently sampled mouse; mean of available measured technical reads
Missing policy: error. Source measurements are preserved.
All inferential tests are two-sided. The helper ran only the supplied methods and comparisons; it did not choose methods by p-values. Predeclaration is the user's responsibility. All reported confidence intervals are pointwise, not adjusted for multiplicity.

Planned family: Two prespecified dose comparisons versus Vehicle; adjustment: holm; members: low_vs_vehicle, high_vs_vehicle.
Holm controls family-wise error under arbitrary dependence. Benjamini-Hochberg controls false discovery rate under independence or appropriate positive dependence; its applicability must be justified for the planned family.

## distribution_overview

Method: descriptive
Counts: {"source_rows": 36, "selected_rows": 36, "included_rows": 36, "excluded_rows": 0, "unselected_rows": 0, "included_units": 36, "independent_unit_count": 36}
Excluded observations: 0
Interval: not computed. No effect confidence interval computed for this method.
Rows are descriptive observations. Independent sample counts are only reported for a confirmed sampling-unit design.

## low_vs_vehicle

Method: mannwhitney
Counts: {"source_rows": 36, "selected_rows": 24, "included_rows": 24, "excluded_rows": 0, "unselected_rows": 12, "included_units": 24, "independent_unit_count": 24}
Excluded observations: 0
Effect: {"name": "cliffs_delta", "estimate": 0.7083333333333333, "direction": "P(Low dose > Vehicle) minus P(Low dose < Vehicle)"}
P-value calculation: Tie-corrected normal approximation with continuity correction
Unadjusted p-value: 0.003549838634913564; adjusted p-value: 0.003549838634913564; adjustment: {'family': 'Two prespecified dose comparisons versus Vehicle', 'method': 'holm', 'family_size': 2}
Interval: not computed. No effect confidence interval computed for this method.
Tests equality of distributions; it is not generally a test of median differences. Cliff's delta has no computed confidence interval.

## high_vs_vehicle

Method: mannwhitney
Counts: {"source_rows": 36, "selected_rows": 24, "included_rows": 24, "excluded_rows": 0, "unselected_rows": 12, "included_units": 24, "independent_unit_count": 24}
Excluded observations: 0
Effect: {"name": "cliffs_delta", "estimate": 0.9722222222222223, "direction": "P(High dose > Vehicle) minus P(High dose < Vehicle)"}
P-value calculation: Tie-corrected normal approximation with continuity correction
Unadjusted p-value: 6.0057602968048996e-05; adjusted p-value: 0.00012011520593609799; adjustment: {'family': 'Two prespecified dose comparisons versus Vehicle', 'method': 'holm', 'family_size': 2}
Interval: not computed. No effect confidence interval computed for this method.
Tests equality of distributions; it is not generally a test of median differences. Cliff's delta has no computed confidence interval.

## Provenance

Data: /private/tmp/easyviz-v041-forward-create/output/attempts/attempt-02/plotting_data.csv
Data SHA-256: 948fed12d6569385eb4d53fa78f12673f441be5a08ede8a5076343ca74156a5b
Helper SHA-256: 180e076ac5c3e28f3c6cafbde721c7ad98958add12b9534ffb3b68ea71e7ab60
Runtime: {"python": "3.12.2", "numpy": "2.5.3", "scipy": "1.18.1"}

The original CSV fields and unit strings (including leading zeros) are copied unchanged into analyzed-data.csv. _easyviz_source_record is a 1-based CSV record number including the header; quoted multi-line fields count as one record.
