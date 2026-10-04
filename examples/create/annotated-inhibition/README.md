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
| Typography and palette | Text size, font, axis line widths/colors, continuous colors, genome colors, and mean-track color are configurable. The adopted user-requested styling uses white 0.5 pt internal heatmap boundaries and charcoal 0.45 pt mean-bar outlines; `heatmap_grid_color`/`heatmap_grid_width_pt` and `mean_edge_color`/`mean_edge_width_pt` control them independently. Omitted widths default to zero for older settings. White genome tiles and their legend key have a purposeful thin charcoal outline; analyzed tiles are solid charcoal. |
| Data scales | `color_limits` must contain every full-matrix measurement. `color_normalization="linear"` is the default. Optional `two_slope` requires a meaningful `color_center` strictly inside the limits. `mean_scale="shared"` uses common `mean_limits`/`mean_ticks`, or automatically derives one range over both tracks. Explicit bounds must include zero and all bars. Role-specific limits are supported only with `mean_scale="independent"`. |
| Exports | This recipe always writes PDF, SVG, and 300 dpi PNG by default; `dpi` is adjustable. It is a deliberately scoped recipe rather than a replacement for the five-family renderer. |

Changing the panel footprint or increasing the selection count requires visual review and, when needed, explicit adjustment of the millimeter layout. Text is never automatically shrunk. The code and settings may be distributed as a reusable recipe **without the CC BY-NC data**; users supply their own matching input or an explicitly synthetic fixture.

## Source and calculations

The data are the existing normalized 76 × 76 matrix from Gontijo et al. (2022), *Mining Biosynthetic Gene Clusters in Carnobacterium maltaromaticum by Interference Competition Network and Genome Analysis*, DOI [10.3390/microorganisms10091794](https://doi.org/10.3390/microorganisms10091794). GII is the supplied growth-delay measure in minutes. This example starts from the preserved source table; it does not repeat upstream processing.

For each sender, calculate its arithmetic mean across all 76 receivers. For each receiver, calculate its mean across all 76 senders. Sort each list independently by descending mean, using the strain ID to resolve ties. Select 20 evenly spaced ranks including both extremes, using `round(linspace(0, 75, 20))`. These selected profiles span the observed mean range but are **not a representative random sample** and do not support an inference about prevalence.

The mean tracks use the complete matrix, not only the displayed 400 cells. Self-pairs and all negative GII values are retained. The complete measurements range from −398.9071599 to 981.4179003 min; outward-rounded color limits of −400 to 1,000 therefore cover every measurement. The single-hue light-to-sky-blue ramp uses one linear mapping, `u = (x + 400) / 1400`, throughout. Zero remains a labeled value at `u = 2/7`, without a special white center or changed slope. No clipping, row normalization, logarithm, quantile remapping, or additional measurement transformation is applied.

The paper's Section 2.2 defines GII as the difference in time to reach OD595 = 0.2 with cell-free supernatant versus fresh medium alone. Positive values indicate delay, negative values earlier attainment. The publication calls GII > 300 min inhibition; positivity alone does not meet that criterion, and negative values do not establish statistically significant growth promotion. This panel preserves the supplied continuous measurements and makes no new classification or significance claim.

Both mean tracks use the same numeric range, **0–700 min**, covering sender means up to 664.2455 min and receiver means up to 370.7236 min. All means use 76 partners. Read the axis ticks when comparing them: the top and side value axes have different physical lengths and orientations, so equal minutes need not occupy equal physical bar lengths. Genome strips decode the supplied binary metadata independently.

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
| `boundary-review.json` | Independent inspection of the adopted cell boundaries and bar outlines |

The PNG uses 300 dpi metadata. PDF preserves the physical canvas and embeds the selected font. SVG preserves editable text and requires the recorded font on the assembly system. Place the panel at 180 × 160 mm during manuscript assembly; changing its scale also changes the effective text size.

## Reuse and attribution

The copied matrix and genome table inherit the supplied repository’s **CC BY-NC 4.0** notice. Retain author attribution and the data’s noncommercial restriction when redistributing them. The article is separately described as CC BY 4.0 in the earlier provenance record; no article image is included here. `plot.py` was written for EasyViz using only the supplied data, metadata needed to identify units and license, and this create brief. It does not load or copy an author plotting script. This is a new visualization of existing data, not an independent biological finding.

The current palette is an EasyViz choice in response to the user's request for simpler, brighter quantitative colors. It is not sampled from a publication. Earlier signed multi-hue candidates and their reviews are historical evidence; their independent positive review did not establish user acceptance. The prior candidate is retained in `evals/create-clarity-revision/baseline/matrix.png`.

White 0.5 pt internal boundaries distinguish the matrix cells. Opaque sky-blue means (`#29ACF3`) have thin charcoal 0.45 pt outlines, matching the axis weight and the outlined-white genome tiles. These mark boundaries follow the user’s explicit request; mean-axis grids remain disabled. The colorbar gives equally spaced 200-minute ticks; the larger mean-track height and repositioned guide keep labels readable within 180 × 160 mm at 8 pt. The matrix and metadata remain keyed to exactly the same selected IDs.

The portable code and settings are in `skills/easyviz/assets/recipes/annotated-heatmap`; its synthetic fixture exercises negative, zero and positive values, leading-zero IDs, full-denominator means and both binary states without redistributing the restricted development inputs. Inspect `visual-review.md` for the actual rendered-panel findings; numeric checks alone do not establish visual quality.
