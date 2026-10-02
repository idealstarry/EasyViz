# Independent numerical and export audit: unseen interval task

Both arms preserve and correctly render all eleven supplied estimates and asymmetric interval endpoints. Actual written SVG geometry confirms the log axis, reference at 1, first-appearance readout order, stable decoded batch colors, six hollow reference-overlap circles and five filled circles. Both safely rerun from a relocated directory and reproduce the same PNG pixels. The baseline has a small physical-size drift in all export formats; EasyViz preserves the requested physical canvas.

36 checks passed and 2 failed. The two failures concern baseline vector/raster dimensions, not incorrect data or missing observations. All 208 frozen-file hashes matched before the audit and remained unchanged.

| Actual artifact measurement | Baseline | With EasyViz |
|---|---|---|
| Matched source estimates and intervals | 11 | 11 |
| Hollow / filled circles | 6 / 5 | 6 / 5 |
| Unprovided readout/batch pairs | 3 left unpainted | 3 left unpainted |
| PDF page | 139.954000 × 99.822000 mm | 140.000000 × 100.000000 mm |
| SVG physical canvas | 139.954000 × 99.822000 mm | 140.000000 × 100.000000 mm |
| PNG raster | 1653 × 1179 px, 299.9994 dpi | 1654 × 1181 px, 299.9994 dpi |
| Actual fonts / SVG text | Embedded Arial 8 pt; editable text | Embedded Arial 8 pt; editable text |
| Clean relocated rerun | Exit 0; identical PNG pixels | Exit 0; identical PNG pixels |

The requested vector dimensions were 140 × 100 mm. Baseline PDF and SVG measure 139.954 × 99.822 mm, a difference of −0.046 and −0.178 mm. Its PNG height is 1179 pixels against an ideal 1181.102 pixels, beyond the protocol's one-pixel integer-rounding allowance. The frozen baseline check record calls the size equivalent; that statement is inaccurate. These are small deviations. The audit does not attribute their cause or repair the originals.

The baseline export table uses renamed columns and includes fourteen coordinate records: eleven supplied observations plus three explicit blank records for unprovided combinations. The audit decodes the five roles and confirms the blank records have no numeric estimate or endpoints; it does not falsely count them as imputed observations. EasyViz exports eleven source rows plus traceability fields. Every supplied value is compared by its unique readout/batch identity, while actual axis order is checked independently.

Measurements come from the exported paths, not model self-QA: a log transform is fitted from actual numeric SVG tick positions; all point centers, interval endpoints, fill states and colors are matched to supplied values; complete circle/interval geometry is checked against the written axes viewport. The baseline suppresses y tick marks and wraps labels. Its actual text baselines are used only as label-block proxies; exact paired-series separation is recovered from the actual marker centers. A coincident grid line at 1 is permitted alongside the explicit reference line. Native `<use>` marker paths and the explicit closing line on hollow-circle paths are decoded without changing model outputs.

Both entry paths were inspected before execution. The baseline writes relative to its own script; the EasyViz arm uses the documented copied CLI and sibling helpers. Temporary copies had their output directories and plotting tables removed before rerunning. No script was patched, no helper was added, and no frozen output was touched. Both programs use supplied endpoints directly and neither introduces a statistical test, fitting, numerical weighting, inferred n, or recomputed interval. Both captions describe the synthetic source, unknown n/interval construction, missing combinations and reference-overlap semantics. Model self-reported QA remains separate from this audit.

No anonymous visual-review findings were read before these conclusions. Physical-size compliance does not establish an aesthetic preference. This is one unfamiliar synthetic task and one run per arm, using one app-reported model and an explicitly detailed request. It does not certify actual backend identity, cross-machine installation, cost in money, journal suitability, novice benefit in general, or GLM versus Deepseek performance.

The companion JSON records per-observation written geometry, fonts, dimensions, rerun logs and all frozen-file checks. Reproduce the audit with:

```sh
python independent-numeric-audit.py --baseline-entry plot_panel.py --baseline-table output/plot_data.csv --easyviz-entry plot_scripts/interval_plot.py --easyviz-table output/plotting-data.csv --easyviz-render-spec interval-spec.json
```

Exit status 1 is deliberate while the two original dimension failures remain. It reports the frozen result faithfully rather than repairing it.
