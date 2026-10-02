# Standalone cohort BMI distributions

Origin: **reproduce**, input mode **image-data**. Current output: **user-requested style adaptation** of that reconstruction. Original author plotting code was not supplied, sought, read, or executed. The implementation was written independently using only the permitted blinded inputs and EasyViz instructions.

## Evidence and mapping

The independent `inputs/reference-spec.json` describes the BMI column in Figure 8a. Direct image inspection confirms eight horizontal muted-purple violins, black cohort labels, a linear BMI axis labelled `BMI (kg/m²)`, visible ticks at 20, 40, and 60, faint vertical guides, and no points, summary markers, boxes, or legend in the target column. The surrounding displays and panel letter are outside scope.

Each row of `inputs/source-data.csv` is a participant record. `bmi` is BMI in kg/m². `cohort` maps to the publication labels stored in `settings.json`, in top-to-bottom order: Krieg; Petrus; Arner, E; Kerr; Arner, P#1; Arner, P#2; Armenise; Imbert. `source_row` and `source_id` remain available for traceability. Every one of the 864 input records is preserved in `plotting-data.csv` with its original BMI string, display label, and inclusion status. All 858 available BMI values contribute to their corresponding densities. Six blank BMI fields are excluded only from density estimation: three in Armenise and three in Imbert. There is no imputation, sampling, upstream analysis, transformation of BMI, or hypothesis test.

## Density choices

The caption and image do not establish the original estimator, bandwidth, evaluation grid, trimming, boundary rule, or normalization. The adopted method is an independent **Gaussian KDE**, using `scipy.stats.gaussian_kde` and **Scott's bandwidth rule**. For a cohort of n available BMI records, the bandwidth in BMI units equals its sample standard deviation (ddof = 1) multiplied by n^(-1/5). The KDE is evaluated at 512 equally spaced positions from that cohort's observed minimum to maximum. Each visible density is rescaled to unit area on that interval, and one shared multiplier maps the largest density peak to a full thickness of 0.9 row spacings. This equal displayed-area rule retains variation in relative thickness; width does not encode sample size. No boundary correction or extension beyond the observed range is used. Flat ends at observed extrema can result from this stated trimming choice. All bandwidths, sample sizes, ranges, and retained KDE masses are saved in `stats.json`; evaluated curves are saved in `density-data.csv`.

These choices are not claims about the authors' settings, and the output does not establish an exact statistical replication. No scientific claim beyond the displayed observational distributions is made.

## Adopted requirements

| Priority | Requirement | Decision and evidence |
| --- | --- | --- |
| Required | Correct data and labels | All available BMI observations; eight full publication cohort labels; original cohort order. |
| Required | Standalone structure | One horizontal violin per cohort; no surrounding panels, overall title, prose, panel letters, or extra tests. White IQR segments and median dots aid comparison. |
| Required | BMI mapping | Linear axis, kg/m² units; common limits 18–64 include all observations. |
| Required | Fixed canvas and type | 160 × 100 mm full canvas, all text 8 pt; Arial is available and used. |
| Required | Exports | Full-canvas PDF and SVG, plus 300 dpi PNG; no tight bounding-box cropping. |
| Preferred | Appearance | User-approved blue #2581B9, borderless fills, white background, faint guides behind violins. |
| Preferred | Axes | Major labels 20/40/60 and guides every 10 BMI units; bottom axis only, with no top/left frame or category tick marks. |
| Flexible | Spacing | The wider standalone layout reserves room for all cohort labels and the full density ranges. |

Actual geometry, fonts, line widths, colors, and software versions are in `settings.json` and `stats.json`. Settings are read by `plot.py` for a portable rerun.

## Intentional differences and unresolved choices

The requested refresh changes the original muted-purple reconstruction to a blue manuscript graphic on a 160 × 100 mm canvas. These are style choices, not improved reference fidelity. All density samples, bandwidths, support, common width multiplier, source rows, and cohort order are unchanged. Flat trimmed ends remain visible; no extra smoothing or distribution reshaping was introduced.

White horizontal segments show the interquartile range (25th–75th percentiles), and white dots show medians, computed directly from each cohort's available values using NumPy's `quantile(..., method="linear")`. These descriptive summaries are additions to the original reference and are not confidence intervals. Values and their method are recorded in `stats.json` and `settings.json`.

All text remains Arial 8 pt when available. PDF and SVG retain the full physical canvas; the 300 dpi PNG uses the renderer's integer pixel dimensions (1889 × 1181). Original KDE settings remain unresolved. The immutable `first-render/` and existing `independent-review.*` files describe the historical reproduction only; current export and visual checks are recorded in `qa.json`.

## Reproduction and access limits

Run `python /path/to/copied-case/plot.py` from any working directory using an environment with NumPy, pandas, SciPy, Matplotlib, Pillow, and PyMuPDF. Inputs are included under `inputs/`; no original repository paths are required. Copy the case into a writable project before running it.

`access-log.json` records the actual task inputs and instructional files read. Isolation is **instruction-based**, not an operating-system sandbox or a technical guarantee that other files were inaccessible. No author code, other example implementation, external page, or original provenance path was accessed. The immutable `first-render/` directory preserves the first outputs and implementation if later revisions are required. Numerical export checks and actual-image review findings are recorded separately in `qa.json`.

Attribution supplied with the request: Massier et al., Nature Communications 14, 1438 (2023), DOI 10.1038/s41467-023-36983-2. Reference crop and prepared source table: CC BY 4.0.

Development-only access logs and first-render history described above are retained in the development repository, outside this portable case.
