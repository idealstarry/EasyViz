# Independent review of raster quantization compatibility

Reviewed the uncommitted `create_review.py` and `test_create_review.py` diff, and the saved `owner-forward-diagnostic` evidence, on 2026-10-05. No unresolved correctness defect was found within this narrow change. No runtime, test, trial or prior evidence file was modified, and no new visual review is claimed.

Verified frozen SHA-256 values:

- `skills/easyviz/scripts/create_review.py`: `f487a2b14a7a41c90c0c8cae64f3590a402d5dc47696629089da8a825f1bd314`
- `tests/test_create_review.py`: `674467770347321ab641fefd37711ff8e37c0a4674db9930d8177ff315b53d8e`

## Code conclusion and limits

`raster_pixels_match` accepts only two positive integer pixel dimensions. For each axis it accepts the adopted millimetres/DPI converted to its floor or nearest grid. An additional `nearest - 1` pixel is accepted only when the ideal value lies within `1e-8` pixel of an integer, accounting for the documented legacy Agg truncation boundary. No blanket plus/minus-one-pixel tolerance is introduced. Dimensions cannot distinguish a deliberately cropped image that lands inside this expressly compatible grid; the near-integer test records that limitation rather than claiming crop detection there.

PNG dimensions and DPI are measured from the current file bytes. If saved QA claims pixel dimensions, they must equal the actual dimensions, even when another claimed size would also belong to the compatible grid. If saved QA claims DPI, both pairs must be positive/finite and agree within `1e-6`; the current file must independently agree with adopted DPI within `0.1`. Missing optional legacy PNG claims still permit direct measurement, while null/malformed claimed values cannot pass. The code retains optional PNG hash validation.

PDF/TIFF continue to use saved actual-export measurements only when their export hashes match current bytes. Missing hashes remain unchecked and mismatches fail. TIFF pixel/DPI claims must meet the same compatible grid and adopted DPI contract. These are hash-bound exporter records, not newly parsed TIFF/PDF measurements. SVG still uses current-byte canvas measurements, and valid rasters do not override an invalid vector canvas. A failed or unchecked required measurement cannot be upgraded by a review attestation.

## Independent checks

Independently ran **9 focused tests**, all passing in **2.719 s**, covering:

- Actual Matplotlib floor and nearest PNG/TIFF exports, both orientations, with exact vector canvas.
- The narrow integer-boundary compatibility and rejection outside it.
- Current PNG crops, extra pixels, larger deviations, and missing/wrong DPI.
- PNG QA/file identity when both claimed grids would otherwise be permitted.
- Invalid TIFF grid/DPI claims, replaced TIFF bytes with unchanged dimensions, corrupt PDF bytes, and missing PDF/TIFF hashes.
- Invalid current SVG canvas despite valid floor rasters.

Test names:

```text
test_actual_matplotlib_floor_and_nearest_raster_grids_keep_exact_vector_canvas
test_actual_near_integer_canvas_accepts_only_numerical_boundary_tolerance
test_current_png_crop_extra_pixel_large_size_and_missing_or_wrong_dpi_are_rejected
test_png_record_must_match_actual_bytes_even_when_both_sizes_quantize_legally
test_hash_bound_tiff_quantization_still_rejects_invalid_size_and_dpi
test_pre_stage_corrupt_pdf_cannot_reuse_old_page_measurements
test_pre_stage_replaced_tiff_fails_even_when_pixel_dimensions_still_match
test_pdf_and_tiff_measurements_without_export_hashes_remain_unchecked
test_current_vector_canvas_remains_decisive_when_floor_rasters_are_valid
```

Independently recomputed all three diagnostic snapshots with the frozen helper. Each equals its saved `after` snapshot, and each saved `before`/`after` pair has identical artifact paths, byte sizes and hashes:

| Diagnostic | Current raster | Export dimensions | Technical QA |
| --- | --- | --- | --- |
| `real-matplotlib-floor` | 1417 × 708, DPI 299.9994 each axis | passed | passed |
| `trial-attempt-01` | 1417 × 708, DPI 299.9994 each axis | passed | failed |
| `trial-attempt-02` | 1417 × 709, DPI 299.9994 each axis | passed | passed |

The first trial still records **15 unresolved point-spacing pairs**, with minimum centre separation `1.736249957905528 pt` against marker diameter `2.5 pt` plus gap `0.22 pt`; its saved `needs_revision` technical QA remains failed in the current review snapshot. Rechecking the existing second-trial packet returns `gate_status: recorded` with no errors. This confirms that the compatible export grid removes the dimension false failure without erasing the saved real spacing failure or rewriting trial outcomes.
