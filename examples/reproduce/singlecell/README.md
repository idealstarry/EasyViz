# Epithelial composition: reference-guided adaptation

This runnable local example uses real archived cell counts and an inspected reference PNG from the user's Angarola collection. It demonstrates a reproduce request with an explicit change: preserve the reference's epithelial composition and green palette while displaying individual replicates. It does not claim to reproduce an exact published figure panel.

## Example request

Use the supplied epithelial composition reference as a visual standard. Keep its three cell types, color mapping, and 0–100% composition scale. Show a separate bar for each replicate, grouped by M3 and M18, instead of the original group means and SEM. Export one 88 × 88 mm panel in PDF and PNG with 8 pt text. Preserve all supplied counts in the source data.

This request was constructed for the EasyViz example; it is not a historical user request or an author instruction.

## Files

| File | Purpose |
| --- | --- |
| `reference.png` | Archived reference inspected visually; unchanged copy. |
| `original-counts.tsv` | Unchanged count table, 12 clusters × 12 replicates. Its first header cell is implicitly the row name. |
| `source-data.csv` | Lossless long-format version, 144 count observations. |
| `provenance.json` | Absolute original paths, source checksum, and conversion details. |
| `figure-settings.json` | Editable panel dimensions, text size, colors, and group/stack order. |
| `plot.py` | Independently written plotting implementation; no Seurat or upstream analysis. |
| `derived-data.csv` | Computed percentages with original counts and explicit denominators. |
| `panel.pdf`, `panel.png` | One manuscript panel and raster preview. |
| `render-settings.json`, `validation.json` | Actual font/render settings and numerical/layout checks. |

## Data and computation

| Field | Meaning |
| --- | --- |
| `replicate` | Original identifier, such as `M3_rep1`. |
| `group` | Prefix extracted from the original replicate identifier; M3 or M18. |
| `cell_type` | Original cluster name, preserved verbatim. |
| `cell_count` | Non-negative integer cell count in this replicate and cluster. |

For each replicate, the epithelial denominator is **Luminal-AV + Luminal-HS + Myoepithelial**. Compute `100 × cell_count / epithelial_total`. Other clusters remain in the source CSV but are excluded from this explicitly defined denominator, matching the archived author's script. These are percentages within captured epithelial cells, not percentages of all captured cells or tissue abundance. Every bar sums to 100%. No inferential test is performed and no biological pairing is assumed.

## Reference interpretation and decisions

| Evidence | Decision |
| --- | --- |
| PNG shows two stacked bars, M3 then M18, dark to light to bright green from bottom to top. | Retain groups, stack order, and the exact color mapping verified in the R script. |
| Script computes each replicate's epithelial percentages before averaging by group. | Retain per-replicate denominator computation; display those values directly. |
| PNG includes one-sided error bars; script calculates SEM and adds component SEM values at some stack boundaries. | Omit these under the explicit per-replicate adaptation request. This convention is not a general formula for uncertainty of cumulative composition. |
| PNG has a right legend with variable-name labels and large bold axis text. | Use readable cell-type names, a bottom legend, and fixed 8 pt Arial text within 88 mm. Record a fallback if Arial is unavailable. |
| Collection README describes `Old_Scripts` as unorganized analyses. | Treat this as an archived plotting example. The current manuscript figure/panel correspondence is unverified. |

The author R script requires a Seurat object only to create the existing count table. EasyViz begins at that table and does not execute or copy the upstream analysis. Exact historical object provenance and the meaning of the M3/M18 group codes have not been independently verified; labels remain unchanged.

## Run

From the EasyViz repository root, using its environment with Matplotlib installed:

```sh
.venv/bin/python examples/reproduce/singlecell/plot.py
```

The script resolves inputs relative to itself and recreates derived data, output panels, settings, and numerical/layout checks. It retains the full canvas without tight cropping. Place the PDF at 88 × 88 mm in manuscript assembly; do not rescale if uniform 8 pt text is required.

## Scope of verification

The run checks non-negative counts, duplicate keys, group labels, positive denominators, 100% sums, and visible text boundaries. The converted table was compared cell by cell with the original TSV. PDF page size and PNG dimensions were checked separately, and the rendered PNG was visually inspected. `validation.json` contains run-specific values; the local reference files are preserved without changing the original collection.
