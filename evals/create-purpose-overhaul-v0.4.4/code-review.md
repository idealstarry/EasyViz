# Independent code review: purpose intake and measured font layout

Reviewed the current uncommitted runtime and tests on 2026-10-05. No unresolved correctness defect was identified in the reviewed changes. This review does not certify aesthetic quality or approve a stable release.

## Frozen files

| File | SHA-256 |
| --- | --- |
| `skills/easyviz/scripts/inspect_data.py` | `58f90bd127a83ffc94924ff5d74cc23989b4d1350b72f23e7a67def0d4614093` |
| `tests/test_inspect_data.py` | `fb5dc9fa163a66db5d8fef36eb63668238d2d406af493aa9c654db19bff010b3` |
| `skills/easyviz/scripts/create_candidates.py` | `44f644c95f6ea92d219dd98d1933b78f1dc5ef084e4c14d342a86155a69d4950` |
| `tests/test_create_candidates.py` | `ce423eea849a00179919ac0496848a67b1b4cf25d55c19e8e79f128c8e9d217b` |

## Code checks

- **Purpose gating** (`inspect_data.py:418–521`): two numeric columns without both adopted x/y roles produce eligibility only, with no joint chart, proposed coordinates or correlation method. A partial role or free-form question does not complete the mapping. Explicit x/y roles remain unchanged, while useful scientific purpose and inference remain unresolved. Distribution previews still require field-meaning confirmation and retain their row-level descriptive scope.
- **Wide paired intake** (`inspect_data.py:480–502`): requires a confirmed paired design, a declared unit with no missing or duplicate keys in the inspected scope, and at least two numeric measurement candidates. It records a preparation candidate, not verified conditions or computed pairs. Full-source uniqueness is claimed only for a complete inventory. The required schema adoption, missing handling and traceable reshape are explicit; no automatic reshape or inference is introduced.
- **Measured physical layout** (`create_candidates.py:450–637`): point spread uses actual renderer transforms and the existing packing method. Pixel measurements convert to points using the current DPI. The bounded fit trial uses the resolved font and measured text/guide geometry. Vertical trials borrow only from the right category edge; horizontal trials borrow only from the bottom edge and retain reversed category order. Numeric-axis geometry, source values and fixed dimensions/fonts/point areas are preserved.
- **Authority and failure states** (`create_candidates.py:497–550, 713–716, 821–858`): profiles skip lane planning; explicit margins/manual guide geometry and `auto_fit=False` block margin borrowing. Explicit point gap, category offset, maximum spread and summary width remain authoritative. Profile bytes are captured and checked before planning, then exported as that same snapshot. An actual geometry failure cannot become a pass through canvas QA, and an exception after passing renderer QA remains failed.
- **Documentation consistency**: the current `data-exploration.md` describes numeric eligibility and wide paired preparation with the same limits as the runtime. It allows one well-supported proposal and does not require a fixed alternatives quota.

## Independent verification

`PYTHONPATH=tests .venv/bin/python -m unittest test_inspect_data` passed **47 tests** in **1.977 s**. Coverage includes the new purpose/partial-role/explicit-role branches, wide paired preparation and prefix limits, dirty unit keys, plus existing string/source/missing-token preservation and summary intake cases.

After matching the engine owner's frozen hashes, independently reran these **7 tests**, all passing in **9.758 s**:

- `test_measured_margin_handles_explicit_and_fallback_fonts_without_changing_marks_or_numeric_region`
- `test_horizontal_margin_borrowing_keeps_numeric_transform_and_reversed_category_order`
- `test_explicit_margin_lock_retains_cross_font_spacing_failure_and_source_values`
- `test_profile_drift_after_planning_uses_only_original_adopted_snapshot`
- `test_explicit_cosmetics_and_manual_geometry_are_locked_and_deduplicated`
- `test_actual_numeric_artist_violation_cannot_be_masked_by_canvas_qa_pass`
- `test_exception_after_passing_renderer_qa_is_failed_unconditionally`

The cross-font test covers explicit DejaVu Sans at 100/160 DPI and simulated unavailable Arial resolving to the real DejaVu Sans font. Its assertions include actual exports, exact observation coordinates/point areas, adopted statistics/order/numeric bounds, measured summary width floors and positive point spacing. The locked-margin case deliberately remains `needs_revision` rather than silently moving explicit geometry.

## Verified limits

Scientific usefulness is still an Agent/user judgement, not a machine-certified property of x/y mappings or column names. Wide-table preparation still needs an adopted condition schema and a verified reshape. The bounded layout repair is not an optimal-packing guarantee, and technical success still requires actual-image review. The independent tests cover the listed font/orientation/state branches; they do not establish portability to every installed font or performance on arbitrary datasets. Runtime and test files were not modified during this review, and the release remains draft.
