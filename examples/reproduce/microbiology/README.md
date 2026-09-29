# Microbiology: inhibition heatmap adaptation

This runnable `reproduce` example adapts Figure 1 from Gontijo et al. (2022), *Mining Biosynthetic Gene Clusters in Carnobacterium maltaromaticum by Interference Competition Network and Genome Analysis*, DOI [10.3390/microorganisms10091794](https://doi.org/10.3390/microorganisms10091794). It uses real, supplied cleaned measurements. It is a selected 12 × 12 overview, not the full published matrix or a pixel-exact reproduction.

## Run

From the EasyViz project root:

```sh
.venv/bin/python examples/reproduce/microbiology/plot.py
```

Dependencies are NumPy, Matplotlib, Pillow, and pypdf. The script is independent of the author's R environment and reads only files in this example folder. It performs table selection, degree counting for ordering, and plotting; it runs no genome analysis, clustering, or upstream bioinformatics software.

## Files

| File | Purpose |
|---|---|
| `request.md` | Example user request and intended adaptation |
| `reference-analysis.md` | Observed standard, code evidence, and uncertainty |
| `reference-page-4.png` | Rendered article page containing Figure 1 and caption |
| `source-data.csv` | All 76 × 76 intraspecific GII values, with sender IDs |
| `genome-status.csv` | Supplied binary genome-analyzed annotation |
| `figure-settings.json` | Physical dimensions, font, palette, and selection settings |
| `plot.py` | New standalone implementation |
| `selected-data.csv` | Exact 144 measurements displayed, with ordering degrees |
| `panel.pdf`, `panel.png` | Fixed-size final export and preview |
| `validation.json` | Automated source-shape, text-boundary, and export-dimension checks |
| `provenance.json` | Original local paths, hashes, conversion, and license attribution |

## Data and selection

The author-supplied sender matrix has 76 rows and 77 measurement columns. The EGDe column represents another species and is omitted; the remaining 5,776 values are retained unchanged numerically. Only CSV delimiter and decimal formatting are normalized. Negative GII values remain present; no clipping or imputation is performed.

GII is a growth-delay measurement in minutes (article Section 2.2). To order strains, count values **greater than 300 min**, the paper's inhibition threshold, across every one of the 76 receivers for sender degree and across every sender for receiver degree. Sort degrees descending, breaking ties by strain ID. Select 12 evenly spaced ranks, including both ends, separately along each axis: 1, 8, 15, 21, 28, 35, 42, 49, 56, 62, 69, 76. This selection demonstrates adapting density to a readable panel. It is not representative sampling for inference and does not preserve the full network. The full matrix remains available for a different selection.

Color limits use the minimum and maximum of the entire 76 × 76 matrix, not just selected cells. Genome strips are keyed by strain ID. No new significance test is requested or added.

## Layout and review

The export is **132 × 120 mm**, with Arial **8 pt**, a square 78 × 78 mm data area, and a 300 dpi PNG. These are example-specific settings, not a journal standard or an automatically interchangeable 88 mm panel. Reserve this physical footprint before assembly; do not shrink the exported panel to another slot. Labels, annotation strips, and the colorbar are part of the canvas. PDF text is embedded using TrueType support. No tight crop is used.

Initial review: reference article page and resulting PNG were inspected visually; labels, colorbar, and genome strips are legible and contained. Automated checks confirm the full matrix dimensions, finite measurements, unique strain IDs, annotation coverage, text inside the canvas, and matching PDF/PNG physical dimensions. Original-to-normalized numerical equality was independently checked for all 5,776 cells during conversion.

## Attribution and reuse

The supplied repository README names **Creative Commons Attribution-NonCommercial 4.0** for its contents; copied measurement and annotation data retain that provenance. The article states **CC BY 4.0**; `reference-page-4.png` is an unmodified page rendering attributed to its authors. `plot.py` is newly written EasyViz example code, not copied author code. Keep these source-specific notices with the example; no blanket license for all project content is implied.

## Other microbiology resources inspected

| Resource | Local contents | Conversion readiness |
|---|---|---|
| Gontijo et al., 2022 | Paper, Rmd, six cleaned CSVs, README | Ready for data-backed examples; this example is the first conversion |
| Somerville et al., 2024 | Paper, Rmd, rendered HTML, README | Useful script/style reference; no standalone source tables in the supplied folder |
| Damoczi et al., 2024 | Paper and supplementary software DOCX | Code reference candidate; DOCX contents and input availability still require inspection |
| Blanco 2022; Borowska 2025; De Filippis 2024; Pasolli 2020; Sharp 2025; Tang & Leisner 2025 | Standalone papers | Visual-reference candidates; matching source data and code not present locally |
