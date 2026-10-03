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
| Typography and palette | Text size, font, axis line widths/colors, diverging colors, genome colors, and mean-track color are configurable. Mean bars are borderless. White genome tiles and their legend key have a purposeful thin charcoal outline; analyzed tiles are solid charcoal. |
| Data scales | `color_limits` must contain every full-matrix measurement. `color_normalization="two_slope"` requires a declared `color_center` strictly inside the limits; an explicit `linear` option is available for other semantics. Mean-axis limits and ticks are optional; removing them enables data-derived bounds. Explicit limits cannot clip bars. |
| Exports | This recipe always writes PDF, SVG, and 300 dpi PNG by default; `dpi` is adjustable. It is a deliberately scoped recipe rather than a replacement for the five-family renderer. |

Changing the panel footprint or increasing the selection count requires visual review and, when needed, explicit adjustment of the millimeter layout. Text is never automatically shrunk. The code and settings may be distributed as a reusable recipe **without the CC BY-NC data**; users supply their own matching input or an explicitly synthetic fixture.

## Source and calculations

The data are the existing normalized 76 × 76 matrix from Gontijo et al. (2022), *Mining Biosynthetic Gene Clusters in Carnobacterium maltaromaticum by Interference Competition Network and Genome Analysis*, DOI [10.3390/microorganisms10091794](https://doi.org/10.3390/microorganisms10091794). GII is the supplied growth-delay measure in minutes. This example starts from the preserved source table; it does not repeat upstream processing.

For each sender, calculate its arithmetic mean across all 76 receivers. For each receiver, calculate its mean across all 76 senders. Sort each list independently by descending mean, using the strain ID to resolve ties. Select 20 evenly spaced ranks including both extremes, using `round(linspace(0, 75, 20))`. These selected profiles span the observed mean range but are **not a representative random sample** and do not support an inference about prevalence.

The mean tracks use the complete matrix, not only the displayed 400 cells. Self-pairs are retained because they are present in the supplied data. The full-matrix color limits remain −400 and 1,000 min. Zero is explicitly adopted as the neutral reference for the supplied growth-delay measure. The blue–white–gold–orange–coral scale uses `TwoSlopeNorm`: −400 maps to 0, zero to 0.5, and 1,000 to 1. Each sign has its own linear branch, so this is a change from the earlier single globally linear ramp. The negative branch spans 400 min across half the colors; the positive branch spans 1,000 min across the other half. Negative GII values are retained without recoding or clipping. Binary strips map the supplied `genome` column to “Genome analyzed” or “Not analyzed”; the strips do not represent a new genome analysis.

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

The prior palette used Somerville et al. (2024) as historical inspiration. The current design was informed by actual PDF inspection of PROGENy, [Fig. 2b/c](https://doi.org/10.1038/s41467-017-02391-6), scWAT, [Fig. 2b](https://doi.org/10.1038/s41467-023-43021-8), and Vanneste et al., [Fig. 4d](https://doi.org/10.1038/s41590-023-01468-3). Those panels show strong signed colors around a light center, compact metadata, and thin dark axes. They supply visual inspiration only. The chosen blue, white, gold, orange, and coral are EasyViz adaptations, not sampled colors or transferred scientific thresholds. The initial blue–white–red candidate improved sign decoding but still made most positive cells pale pink; it is retained in `evals/create-literature-refresh/alternatives/matrix-blue-white-red.png` with its settings. The adopted multi-hue positive arm makes moderate positive patterns use yellow/gold and stronger values use orange/coral.

For raw GII `x` and normalized color coordinate `u`, the exact forward mapping is `u = (x + 400) / 800` for `x ≤ 0`, and `u = 0.5 + x / 2000` for `x ≥ 0`. Its inverse is `x = -400 + 800u` for `u ≤ 0.5`, and `x = 2000(u - 0.5)` for `u ≥ 0.5`. The colorbar uses the same map and labels original minutes at −400, 0, 250, 500, and 1,000. No clipping, percentile scaling, logarithm, row normalization, or new significance annotation is applied. `render-settings.json` and `qa.json` save these formulas, the scale limits, tick positions, the ordered mapping check, and its inverse check against all unique measurements plus interval probes.

Color stops are explicitly recorded in normalized coordinates and raw-minute readout:

| Raw GII (min) | Normalized coordinate | Chosen color |
| --- | --- | --- |
| −400 | 0 | `#4B9BDD` |
| −200 | 0.25 | `#B8DCFA` |
| 0 | 0.5 | `#FFFFFF` |
| 100 | 0.55 | `#FFF0B5` |
| 250 | 0.625 | `#FFD168` |
| 500 | 0.75 | `#FF995D` |
| 1,000 | 1 | `#F24E55` |

Colors interpolate continuously between these stops; they do not bin values or create scientific thresholds. The normalization and inverse remain unchanged from the first candidate. A 1,025-coordinate sRGB relative-luminance check verifies increasing brightness toward zero on the negative arm and decreasing brightness away from zero on the positive arm. This supports an ordered magnitude reading; it does not claim perceptual uniformity. The check and stop/readout map are saved in QA.

Opaque sky-blue marginal bars (`#49ACDE`) retain their separate nonnegative numeric axes. Charcoal/outlined-white binary strips retain their own genome legend. Thin 0.45 pt charcoal axes remain purposeful; the foggy mean grids and matrix seams are removed. The matrix, all four aligned tracks, and axis labels keep their original millimeter geometry. Only the colorbar is enlarged from 28 to 52 mm and moved within the bottom-right guide area so the added zero and intermediate ticks are readable. Text stays at 8 pt and the 180 × 160 mm footprint is unchanged.

`visual-review.md` records actual before/after inspection, including a separate synthetic portable rendering. The portable code and settings are in `skills/easyviz/assets/recipes/annotated-heatmap`; its `synthetic/` fixture exercises both endpoints, zero, leading-zero IDs, full-denominator means, and binary states without redistributing the restricted development inputs. Palette inspiration does not turn this create design into a reproduction.
