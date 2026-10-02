# Mammographic-density supplied-interval forest

Two individually exported panels reproduce 48 published odds ratios and asymmetric 95% confidence intervals. All input records are retained; per-estimate sample sizes remain unknown. The shared generic interval recipe draws three exposure blocks, eight outcome categories, explicit source fill states, and a logarithmic odds-ratio axis.

| Panel | Preview | Data | Specification | Caption |
| --- | --- | --- | --- | --- |
| Total effect | [PNG](output-a/panel.png) | [24 source rows](inputs/source-data-a.csv) | [Spec](panel-a-spec.json) | [Caption](caption-a.md) |
| Direct effect, same-study transfer | [PNG](output-b/panel.png) | [24 source rows](inputs/source-data-b.csv) | [Spec](panel-b-spec.json) | [Caption](caption-b.md) |

The layout repeats outcome labels and uses horizontal exposure headers so that each standalone panel is readable without a shared legend. Source titles and panel letters move out of the image; the adopted specification lists all deliberate changes. Fixed canvases are 105 × 135 mm with Arial 8 pt text. These dimensions are project choices rather than recovered journal settings.

## Run

Copy the case into a writable project directory before running it. The wrapper accepts `--data`, `--spec`, and `--out` and delegates to the shared runtime; it contains no author plotting code. Inside this repository or installed skill tree it locates the runtime automatically. For a separately copied case, provide the EasyViz `scripts` directory explicitly:

```sh
python /path/to/case/plot.py --runtime /path/to/easyviz/scripts --out /path/to/project/total-effect
python /path/to/case/plot.py --runtime /path/to/easyviz/scripts --data /path/to/case/inputs/source-data-b.csv --spec /path/to/case/panel-b-spec.json --out /path/to/project/direct-effect
```

Each run exports a full-canvas PDF, editable-text SVG, PNG, actual settings, plotting data, supplied-statistics record, and automated QA. It does not perform MR, infer independent sample sizes, recompute intervals, or classify significance. Inspect the rendered panel and QA before delivery. The direct-effect table is a transfer within the same study, not independent evidence for another study or arbitrary data.

The supplied renders pass their source-to-artist, layout, and marker checks. The separate [export verification](verification.json), produced by [the export auditor](verify_exports.py), also checks the actual PDF vector endpoints and estimate locations against all 48 source records, the 20 pt² geometric circle areas, source fill states, embedded Arial 8 pt text, physical export sizes, and editable SVG text without importing the renderer. The [independent visual review](independent-review.md) found no blocking revision. Pale yellow remains the weakest source-derived mark color and needs checking in the final production proof; no calibrated print or color-management check was performed.

See [adopted specification](adopted-spec.md), [independent input reading](inputs/independent-reading.md), [dictionary](inputs/data-dictionary.md), and [provenance](provenance.json). The full workbook and article PDF stay outside the case. This case is an image-and-data reconstruction, not an exact recovery of unknown original plotting settings.

Attribution: Vabistsevits et al., *Mammographic density mediates the protective effect of early-life body size on breast cancer risk*, Nature Communications 15, 4021 (2024), [article](https://www.nature.com/articles/s41467-024-48105-7), [official Source Data](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-024-48105-7/MediaObjects/41467_2024_48105_MOESM6_ESM.xlsx), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Adaptations: selected CSV columns and panel partitions, source-state mapping, PDF reference crop, newly written plotting implementation, and standalone layout. All numerical estimate and endpoint values are preserved.
