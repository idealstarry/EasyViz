# Bounded generalization evaluation

15 bounded synthetic transfer/stress scenarios; 19 concrete runs including layout repair and data-corruption variants. This does not establish general capability or reference-image reproduction.

All source tables are newly generated synthetic fixtures. Explicit palettes and 8 pt text stabilize this evaluation independently of changing project defaults. No author code or reference image is used.

## Results

| Scenario | Expected | Observed | Evidence |
| --- | --- | --- | --- |
| 01_rectangular_heatmap | success | **success** | All numeric checks pass. |
| 02_long_labels_small | layout_rejection | **clear_layout_rejection** | Canvas QA needs revision: 8 clipped text elements, 0 missing glyph warnings; inspect qa.json and panel.png |
| 02_long_labels_repaired | success | **success** | All numeric checks pass. |
| 03_sparse_denominator_composition | success | **success** | All numeric checks pass. |
| 04_unresolved_composition_missingness | data_rejection | **clear_data_rejection** | Missing sample/category combinations; explicitly set options.missing_categories='zero' only for known zeros |
| 05_zero_sum_composition | data_rejection | **clear_data_rejection** | Every sample sum must be positive |
| 06_sparse_dot_matrix | success | **success** | All numeric checks pass. |
| 07_dot_corruption_duplicate | data_rejection | **clear_data_rejection** | Duplicate ('x', 'y') cells; aggregate explicitly before rendering |
| 07_dot_corruption_negative_size | data_rejection | **clear_data_rejection** | Dot sizes must be nonnegative |
| 07_dot_corruption_nonfinite_color | data_rejection | **clear_data_rejection** | Non-finite values in score |
| 07_dot_corruption_missing_label | data_rejection | **clear_data_rejection** | Missing values in celltype; supply an explicit cleaned input |
| 08_dense_log_scatter | success | **success** | All numeric checks pass. |
| 09_repeated_correlation_unit | data_rejection | **clear_data_rejection** | Correlation requires one observation per supplied independent unit |
| 10_unbalanced_nine_group_distribution | success | **success** | All numeric checks pass. |
| 11_within_group_unit_repetition | data_rejection | **clear_data_rejection** | Repeated observations within a group need explicit aggregation or a repeated-measures model |
| 12_zero_paired_differences | data_rejection | **clear_data_rejection** | All paired differences are zero; Wilcoxon is undefined |
| 13_internal_tick_collisions | quality_guard | **layout_gap** | Renderer returned pass; independent audit found 29 tick-label intersections. |
| 14_literal_category_names | success | **unexpected_rejection** | Missing values in group; supply an explicit cleaned input |
| 15_repeated_three_visit_test | unsupported | **clear_unsupported** | Distribution statistics supports welch, mannwhitney, or paired wilcoxon |

## Interpretation

Successful transfers only support the tested families, schema, data scale, layout and method combinations. Clear rejection prevents a misleading output but is not a successful plot. Unsupported statistics require an appropriate custom implementation. Layout gaps remain failures of publication acceptance even when the renderer's canvas-boundary QA passes.

The repaired long-label run preserves the original data and 8 pt text; it explicitly enlarges the canvas and left margin. The sparse dot run retains supplied zero sizes without imputing absent combinations, but those two situations both look blank and need a custom visual distinction when scientifically relevant.

## Reproduce

```sh
.venv/bin/python tests/check_generalization.py
# Add --strict to fail on any open defect or unflagged layout gap.
```

Every exact input and specification is under `inputs/`; exact per-case commands and quantitative checks are in `report.json`. Outputs are under `renders/`. `contact-sheet.png` is an inspection aid, not a manuscript figure. Actual visual-review findings are documented separately in `visual-review.md`.
