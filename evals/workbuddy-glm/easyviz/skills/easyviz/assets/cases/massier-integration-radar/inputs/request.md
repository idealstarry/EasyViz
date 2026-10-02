# Reproduce request: depot integration benchmark

Use `reference.png` as the visual standard. Reproduce only the kBET acceptance-rate display under the central “depot” heading in Figure 1e. The other five charts provide context; the bottom method legend and cell-class key apply to the requested chart. Output one standalone chart containing all five integration methods and all five cell classes, with a readable key or direct labels.

Use the 25 already-computed values in `source-data.csv`. No author plotting code is available to the implementer. Do not rerun integration or calculate kBET from expression data.

| Output setting | Requirement |
|---|---|
| Track | reproduce |
| Final canvas | 88 mm wide × 88 mm high |
| Typeface | Arial, with a documented available fallback if necessary |
| Text | 8 pt at final size |
| Exports | PDF and SVG, with a 300 dpi PNG preview |
| Assembly | One individual panel; preserve full canvas and physical dimensions |
| Statistics | Display supplied acceptance rates; no new hypothesis test is requested |

## Caption and methods evidence

The Figure 1e caption on PDF page 4 identifies kBET and adjusted Rand index as benchmarks for raw or integrated data, displayed by method, depot, and cohort. The integration and benchmarking methods on PDF page 14 define kBET acceptance rate as one minus rejection rate. This input is the `KBET_D` worksheet: D denotes the depot comparison.

Attribution: Massier et al., Nature Communications 14, 1438 (2023), DOI [10.1038/s41467-023-36983-2](https://doi.org/10.1038/s41467-023-36983-2). Reference image cropped from the article; source table reshaped from the authors' released workbook. CC BY 4.0.
