# Reproduce request: cohort BMI distributions

Use `reference.png` as the visual standard. Reproduce only the cohort-wise BMI distribution column in Figure 8a, the middle column of the left group. Output one standalone panel with all eight cohort labels. The surrounding age, HOMA-IR, subject-count and summary displays are reference context and are outside the requested panel.

Use every available BMI observation in `source-data.csv`. Report missing values and any visualization choices that cannot be recovered from the reference. No author plotting code is available to the implementer. Source data are already prepared: no sequencing or deconvolution analysis is required.

| Output setting | Requirement |
|---|---|
| Track | reproduce |
| Final canvas | 132 mm wide × 99 mm high |
| Typeface | Arial, with a documented available fallback if necessary |
| Text | 8 pt at final size |
| Exports | PDF and SVG, with a 300 dpi PNG preview |
| Assembly | One individual panel; preserve full canvas and physical dimensions |
| Statistics | Density estimation is allowed; state the chosen method and bandwidth rule. No hypothesis test is requested. |

## Caption evidence

The Figure 8a caption on PDF page 14 says that bulk transcriptomic data from eight cohorts were retrieved and that the left panel displays distributions of age, BMI, and HOMA-IR. Summary statistics are shown at right. The caption does not prescribe a density estimator, bandwidth, trimming rule, or violin normalization.

Attribution: Massier et al., Nature Communications 14, 1438 (2023), DOI [10.1038/s41467-023-36983-2](https://doi.org/10.1038/s41467-023-36983-2). Reference image cropped from the article; source data columns selected from the authors' released table. CC BY 4.0.
