# Supplied target data

This synthetic dataset supplies 72 feature/sample coordinates. `z_score` is an already computed upstream standardized score, dimensionless. Do not recompute normalization. Three coordinates are explicitly unmeasured with empty scores; one measured score is exactly zero. There are no absent coordinates.

Join `specimen` to `target-samples.csv`; sort columns by its numeric `display_order` and rows Signal_A through Signal_H. Use the same order in every layer. Group mapping is Baseline (S01–S03), Compound X (S04–S06), Compound Y (S07–S09). For the right marginal summary, use each feature's arithmetic mean across all its measured target samples (do not replace missing with zero). This is a descriptive mean, without an uncertainty interval or inferential test. The main heatmap uses fixed symmetric limits −2 and +2 with zero at the neutral center. Explicitly decode unmeasured cells separately.

The supplied reference is an original synthetic style target created for this evaluation; its numeric values and displayed names are not target data. Read its visible structure, then reproduce the aligned top condition strip, main heatmap, right feature means, diverging colorbar, and compact category guide using the target data. No author code or paper Source Data is available or required.
