# Annotated inhibition profiles — create showcase

This example designs a richer panel directly from supplied data, without a structural reference image or author plotting code. A central 20 × 20 inhibition heatmap is integrated with receiver and sender mean-response tracks and two genome-status strips. All tracks share the same strain ordering. The physical size is **180 × 160 mm**, with **8 pt Arial throughout**, with narrative text supplied separately in `caption.md`.

```sh
.venv/bin/python examples/create/annotated-inhibition/plot.py
```

The script is portable with this folder and requires NumPy, pandas, Matplotlib, Pillow, and pypdf. Optional `--out /path/to/output` keeps generated files outside the example folder.

## Reusable recipe contract

The script can also run on another square inhibition matrix without copying this dataset:

```sh
python plot.py --data matrix.csv --genome genome-status.csv --settings settings.json --out output
```

| Input or setting | Contract |
| --- | --- |
| Matrix CSV | First column named `sender`; remaining column headers are receiver strain IDs. Row and column ID sets must match. All values are finite GII in minutes. Negative values are allowed. |
| Genome CSV | Columns `strain,genome`; exactly one row for every strain; `genome` is 0 or 1. Leading-zero IDs are preserved as strings. |
| `selection_count` | Integer from 2 through the number of strains. The same mean-rank algorithm is used; the number of strains and denominator are inferred from the input. |
| Physical layout | Canvas width/height, every track rectangle `[left, bottom, width, height]`, and every text anchor are in mm in the settings file. This supplied layout is visually tuned for 20 × 20 at 180 × 160 mm. |
| Typography and palette | Text size, font, axis and grid line widths/colors, sequential colors, genome colors, and mean-track color are configurable. The supplied mean bars, metadata tiles, and legend swatches are borderless. |
| Data scales | `color_limits` must contain every full-matrix measurement. Mean-axis limits and ticks are optional; removing them enables data-derived bounds. Explicit limits cannot clip bars. |
| Exports | This recipe always writes PDF, SVG, and 300 dpi PNG by default; `dpi` is adjustable. It is a deliberately scoped recipe rather than a replacement for the five-family renderer. |

Changing the panel footprint or increasing the selection count requires visual review and, when needed, explicit adjustment of the millimeter layout. Text is never automatically shrunk. The code and settings may be distributed as a reusable recipe **without the CC BY-NC data**; users supply their own matching input or an explicitly synthetic fixture.

## Source and calculations

The data are the existing normalized 76 × 76 matrix from Gontijo et al. (2022), *Mining Biosynthetic Gene Clusters in Carnobacterium maltaromaticum by Interference Competition Network and Genome Analysis*, DOI [10.3390/microorganisms10091794](https://doi.org/10.3390/microorganisms10091794). GII is the supplied growth-delay measure in minutes. This example starts from the preserved source table; it does not repeat upstream processing.

For each sender, calculate its arithmetic mean across all 76 receivers. For each receiver, calculate its mean across all 76 senders. Sort each list independently by descending mean, using the strain ID to resolve ties. Select 20 evenly spaced ranks including both extremes, using `round(linspace(0, 75, 20))`. These selected profiles span the observed mean range but are **not a representative random sample** and do not support an inference about prevalence.

The mean tracks use the complete matrix, not only the displayed 400 cells. Self-pairs are retained because they are present in the supplied data. The full-matrix color limits are rounded outward to −400 and 1,000 min; this fixed light-to-coral sequential scale retains negative values without clipping. Negative GII values are not recoded as zero. Binary strips map the supplied `genome` column to “Genome analyzed” or “Not analyzed”; the strips do not represent a new genome analysis.

| File | Purpose |
| --- | --- |
| `source-data.csv`, `genome-status.csv` | Complete copied source inputs; unchanged bytes from the established dataset example |
| `caption.md` | Manuscript prose, selection details, denominator definitions, and source notes; kept outside the image |
| `settings.json` | Editable physical layout, font, color scale, and selection settings |
| `plot.py` | New standalone create implementation |
| `plotting-data.csv` | Exact 400 displayed measurements and their full-matrix ranks |
| `summary-data.csv` | All 152 sender/receiver means, genome status, selection flags, and denominator |
| `selection.csv` | The 40 axis-specific selected IDs with ranks and means |
| `render-settings.json` | Resolved font, selected IDs, dimensions, and input/script hashes |
| `panel.pdf`, `panel.svg`, `panel.png` | Final-size panel and preview |
| `qa.json` | Numeric invariants, export dimensions, glyph and text-boundary checks |
| `visual-review.md` | Actual rendered-panel inspection |

The PNG uses 300 dpi metadata. PDF preserves the physical canvas and embeds the selected font. SVG preserves editable text and requires the recorded font on the assembly system. Place the panel at 180 × 160 mm during manuscript assembly; changing its scale also changes the effective text size.

## Reuse and attribution

The copied matrix and genome table inherit the supplied repository’s **CC BY-NC 4.0** notice. Retain author attribution and the data’s noncommercial restriction when redistributing them. The article is separately described as CC BY 4.0 in the earlier provenance record; no article image is included here. `plot.py` was written for EasyViz using only the supplied data, metadata needed to identify units and license, and this create brief. It does not load or copy an author plotting script. This is a new visualization of existing data, not an independent biological finding.

The earlier palette used Somerville et al. (2024), [Figures 1B and 2B](https://www.nature.com/articles/s41467-024-52687-7), as color inspiration. The current refinement uses an EasyViz-designed coral/orange ramp (`#FFFAF7` to `#E36F50`), muted blue mean bars (`#6C9FB2`), and subdued blue-gray metadata (`#708C94` / `#E8ECEF`). These current values are explicit design choices, not colors sampled from that publication. The clear light-to-coral range makes the central matrix the primary quantitative layer, while the lower-saturation marginals support the reading task. The scale still uses linear normalization over −400 to 1,000 min; there is no zero-centered, thresholded, nonlinear, or percentile remapping.

Supporting axes use 0.45 pt gray strokes; 0.35 pt grid lines sit below bars. The colorbar has no outer box. Every bar, binary tile, and matching legend key is borderless. Text stays at 8 pt and the 180 × 160 mm panel footprint is unchanged. `visual-review.md` records the actual refreshed-panel inspection, and `qa.json` records the numeric and export checks. Palette inspiration does not turn this create design into a reproduction of a paper.
