# Reusable chart library

The core renderer produces one panel per invocation from already-prepared CSV data and an explicit JSON plotting specification. It supplies basic chart families; use custom implementations for integrated layouts or scientific layers beyond its supported options. It does not run sequencing analysis, embeddings, clustering, differential expression, or enrichment.

```sh
python /path/to/easyviz/scripts/render.py --data source.csv --spec plot.json --out output
```

Use the interpreter where [requirements.txt](../scripts/requirements.txt) is installed. The specification uses field mappings instead of fixed biological column names. Runnable, explicitly synthetic inputs and specifications are packaged in [assets/fixtures](../assets/fixtures/). These compact fixtures exercise the API; use [Worked cases](examples.md) for more developed scientific panels, provenance, and review evidence.

For several panels in one manuscript figure, use a [shared figure profile](figure-profile.md). It fixes the common font, base size, line width and dpi; retains a complete category-color mapping across missing or reordered groups; and declares each named panel's actual mm dimensions. Optional named continuous scales preserve comparable value ranges. Select it through `profile` and `panel` in the spec, or `--profile` and `--panel` on the command line. Each invocation exports one panel.

## Chart selection and source-data contract

| `chart` | Required `fields` | Input grain | Useful for |
| --- | --- | --- | --- |
| `heatmap` | `row`, `column`, `value` | One numeric value for each row/column pair; complete rectangle | Precomputed scores, expression summaries, or inhibition matrices |
| `composition` | `sample`, `category`, `value` | One nonnegative value per sample/category | Cell or taxon composition with an explicit denominator |
| `dotplot` | `x`, `y`, `size`, `color` | One observation for each displayed categorical pair | Already aggregated expression or enrichment summaries |
| `scatter` | `x`, `y`; optional `group`, `unit` | One numeric pair per observation | Association or already-computed coordinates |
| `distribution` | `group`, `value`; optional `unit` | One measurement per defined independent observation | Group distributions with raw observations |

Prepare reshaped/aggregated plotting data explicitly. The renderer rejects invalid mapped values, duplicate matrix cells, and incomplete heatmaps instead of silently imputing or aggregating. Preserve the unmodified user input and record any excluded missing values before creating a cleaned plotting table. A complete table is not automatically evidence of independent biological replicates.

## Integrated scientific panels

Let the scientific question determine the layers. A panel can contain aligned axes or annotation tracks that explain the same data while remaining a single export at its final physical size. Related layers must retain their meanings and alignment; adding detail is useful only when it improves interpretation.

| Pattern | Data and semantic requirements | Implementation boundary |
| --- | --- | --- |
| Annotated heatmap | Value matrix plus row/column metadata joined by IDs; named selection rule if showing a subset. | Basic heatmap and cell labels are supported. Metadata strips and custom tracks require a custom script. |
| Heatmap with marginal means | Define row/column mean, missing-value handling, and whether the mean uses the displayed cells or full matrix. | Compute and preserve the summary table; align marginal axes to the displayed IDs in a custom script. |
| Count-and-fraction dot plot | Map area to count and color to a fraction with a stated denominator; provide independent size and color legends. | Separate area/color mappings are supported. Aligned total-count summaries or extra tracks require a custom script. |
| Observations with summaries | Define independent units, displayed observation level, summary, and any uncertainty or pairing. | Box/violin plus all raw points is supported. Paired connectors, custom summaries, and uncertainty layers require an explicit implementation. |
| Selective biological annotations | Supply feature IDs and the reason for labeling them; preserve unlabeled observations. | Specialized label placement or annotation geometry may require a custom script. |

For example, an inhibition-matrix view can pair genome annotation strips with marginal means computed over the complete matrix; its caption and saved settings must distinguish that full-data context from the selected view. A cell-atlas panel can use dot area for cell counts, color for within-depot percentages, and an aligned count summary; those quantities need separate labels, and cells must not be treated as replicate donors. These are design patterns, not required layers or universal analysis choices.

Both tracks use the same [Panel layout](panel-layout.md) and [Visual review](visual-review.md) requirements. Inspect track alignment, distinct encoding legends, and annotations at the intended size. Verify derived summaries numerically; keep all adopted layers inside the recorded canvas without shrinking shared text to fit.

## Specification

| Key | Meaning |
| --- | --- |
| `chart`, `fields` | Family and source-column mapping from the table above |
| `layout` | `width_mm`, `height_mm`, `font`, `font_size_pt`, `line_width_pt`, `dpi`, and `margins` |
| `layout.margins` | Fractional axes bounds: `left`, `right`, `bottom`, `top`; allow room for labels, legends and colorbars |
| `typography` | Optional point sizes by role: `axis`, `tick`, `legend`, `annotation`, `title`, `panel` |
| `legends` | Physical categorical/size/colorbar geometry, measured placement and review thresholds; see [Legend layout](legend-layout.md) |
| `colors` / `palette` | Explicit category-to-color mapping, or a categorical preset; the actual mapping is saved |
| `colormap` | Registered continuous map, supported preset, or a list of color values |
| `order` | Explicit lists for `x`, `y`, `group`, `sample`, or `category` as appropriate; heatmap columns use `x` and rows use `y`; list all observed categories exactly once |
| `labels` | `x`, `y`, `color` and `size`; `title` only for an explicitly requested in-image title |
| `formats` | Any supported combination of `pdf`, `png`, `svg`, `tiff` |
| `seed` | Deterministic jitter seed |
| `options` | Family-specific settings below |
| `statistics` | Explicit requested method, comparisons and pairing; never inferred from a reference image |
| `profile`, `panel` | Shared figure-profile path and named panel dimensions; conflicting local settings are rejected |
| `continuous_scale` | Optional named profile scale for a heatmap or dot plot; fixes colormap, limits and optional center |

Use the included specifications as runnable starting points. A panel's dimensions refer to the entire canvas, not only its plotting area. Presets in [presets.json](../assets/layouts/presets.json) are values to copy into `layout`, not a mandatory grid. See [panel-layout.md](panel-layout.md) before changing an agreed panel footprint.

The renderer rejects unknown top-level keys and unknown `layout`, `typography`, `fields`, `labels`, `order`, `statistics` and option keys. Object sections, category lists, boolean switches, numbers and strings must have their documented JSON types. `layout.fontsize_pt`, for example, fails with a `font_size_pt` suggestion. Use numeric mm, pt and dpi values without unit suffixes. This avoids a successful-looking panel that quietly uses defaults after a misspelled setting.

## Frequent options

| Purpose | Setting |
| --- | --- |
| Composition denominator | `normalization: "sample_sum"`, `"denominator"` with `fields.denominator`, or `"none"`; the choice is required |
| Percent ticks for normalized composition | `percent_axis: true` |
| Continuous scale | `color_limits: [low, high]`; `color_center` for a meaningful diverging midpoint |
| Dot area | `size_max`, `max_area_pt2`, `size_legend`; size denotes area, not radius |
| Scatter regression | `regression: true` on linear axes; records a least-squares fit, separate from correlation statistics |
| Labels and marks | `x_rotation`, `point_area_pt2`, `alpha`, `grid`; use per-family support in script help |
| Distribution style | `kind: "box"` or `"violin"`; `orientation: "vertical"` or `"horizontal"`. Violin smoothing parameters are renderer defaults, not recovered author choices. |
| Heatmap labels | `annotate_values`, `value_format`; use only when each cell has enough room |

Do not force a scientific question or complex reference figure into these families. Write a custom script when required layers or geometry are unsupported, reuse the same physical-size/font/export rules, and provide its source, settings, data and review evidence. An unsupported layer should be implemented explicitly or reported as unresolved, not silently dropped.

## Statistical support

| Method | Preconditions |
| --- | --- |
| `pearson`, `spearman` | Scatter with nonconstant numeric pairs; verify independent units and the intended population |
| `welch`, `mannwhitney` | Distribution with exactly two named groups for the comparison; verify independence |
| `wilcoxon` | Paired distribution with an explicit pairing ID and matching IDs across groups |

Tests are two-sided. The built-in helper handles one requested comparison; multiple comparisons, adjusted P values, repeated measures, covariates, and other designs require an explicitly implemented appropriate analysis. Do not label an unadjusted P value as adjusted. Where supported, results include group sample sizes and effect summaries. Request `annotate: true` only when the annotation fits without changing the shared typography.

## Outputs and review

The core renderer's output directory contains panel exports, the plotting table, resolved settings, statistical results, and machine-readable QA. It checks canvas clipping and same-axis horizontal/vertical tick collisions; oblique ticks are recorded as unchecked. Other overlaps and very small marks still need visual inspection. Custom implementations must provide equivalent traceability and export checks, plus any derived metadata or summary tables needed to recreate their layers. A clipping, collision or export-size failure is not a publication-ready result. Numeric/file checks do not establish visual quality; inspect exports and apply the reviewer workflow to both create and reproduce.

The two historical development cases are code-assisted evidence, not proof of image-only reconstruction. Bundled synthetic fixtures exercise reusable code; independent no-author-code cases are identified separately in the example catalog.
