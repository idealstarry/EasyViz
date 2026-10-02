# Yayon CMA matrices and supplied summary strip

This is a **source-backed layer adaptation**, not complete equivalence to the
original Fig. 3f. The Source Data supplies both matrices, cosine similarities
and corrected interaction P values, but no dendrogram topology or heights.
The tree layer is therefore omitted explicitly. No author plotting code was
accessed or required.

The case uses the reusable `AlignedFrame` for a lower matrix, an independently
placed upper matrix and a supplied summary strip sharing exactly the same
literal ordered columns. Its wrapper delegates font selection, whole-canvas
export, semantic SVG IDs and guide measurement to the EasyViz runtime. All
field names, orders, display aliases, scales, P-class rules, emphasis and
physical geometry live in `spec.json`; there is no hardcoded gene-selection
or biological analysis in the plotting code.

```sh
python examples/no-author-code/yayon-cma/plot.py \
  --runtime /path/to/easyviz/scripts \
  --out examples/no-author-code/yayon-cma/output
```

`--runtime` explicitly locates the installed helper directory, including when
the case is copied outside this repository. `--data`, `--summary`, `--spec`
and `--provenance` can override bundled inputs. Matrix fields map group, row,
column and value; summary fields separately map column, supplied value and
adjusted P. All joins use exact string IDs. Inputs must contain two complete
matrices and exactly one summary per column. Unknown keys, duplicate cells,
extra/missing summary IDs, nonfinite values, out-of-range values and conflicting
layout settings fail explicitly.

`--font` is an explicit family override for another assembly system; it keeps
the canvas and point sizes fixed and records the override. Different font
metrics can make a dense panel infeasible. The 65-column scientific layout
passes with Arial; DejaVu Sans correctly fails its dense label/guide fit. The
changed-schema transfer below passes with `--font "DejaVu Sans"` and provides
a portable positive smoke input without changing the scientific settings.

The adopted full canvas is 210 × 111 mm with Arial at 7.5 pt and 300 dpi.
The actual available font is recorded. The two matrix rectangles are
`[34,76,169,29]` and `[34,24,169,29]` mm; the summary rectangle is
`[34,55,169,19]` mm. Every rectangle includes its agreed final physical span.
Whole-canvas PNG, SVG and PDF use those dimensions. No title, panel letter,
overview count or explanatory footnote is rendered; scientific explanation
belongs in `caption.md`.

The output includes the panels, source-preserving plotting tables, supplied
summaries, actual artist values/colors, settings, hashes, semantic element map,
statistics-scope record and QA. The audit re-reads source bytes and verifies
all 1,300 cell colors/positions, 65 bar values and baselines, all 65 supplied
P classifications and the 20 visible circle areas/zero positions. It checks
literal label aliases, source emphasis and actual transformed alignment.
Dedicated compound checks protect actual guide/text footprints rather than
the empty corners of one matrix's enclosing label rectangle.

The original workbook and compact prepared tables are bundled in `inputs/`.
`provenance.json` records the workbook hash, numeric source-cell addresses,
extraction scope and licence. The scientific run binds both prepared files
and the workbook hash; no raw-expression analysis is rerun. The independent
image-only reading was produced before case implementation and is retained
in `reference-reading.md` and `.json`.

Both scientific and transfer PNGs were inspected after export. The adopted
labels, legends, outlined ranges and data marks are readable without clipping;
source, transformed alignment, font/glyph and export checks pass. The
dendrogram omission remains a material limitation even when those checks pass.
See `visual-review.md` for the bounded review and `source-audit.md` for scope.

Source and attribution: Yayon, Kedlian, Boehme et al.,
[A spatial human thymus cell atlas mapped to a continuous tissue axis](https://www.nature.com/articles/s41586-024-07944-6),
Nature 635, 708–718 (2024), doi:10.1038/s41586-024-07944-6. Data/reference
adapted under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Changed-schema transfer

`transfer/` contains a synthetic unrelated 5-feature × 4-zone × 2-phase input.
It changes matrix and summary field names, literal IDs, all orders and label
aliases, including `001`, `NA`, `null` and whitespace-bearing IDs. Supplied
summary values include positive, zero and negative bars, and P values exactly
at 0.001, 0.01 and 0.05 test the strict threshold boundaries. The same plotting
code, final canvas and fonts produce the transfer without biology-specific
branches.

```sh
python examples/no-author-code/yayon-cma/plot.py \
  --runtime /path/to/easyviz/scripts \
  --data examples/no-author-code/yayon-cma/transfer/matrix.csv \
  --summary examples/no-author-code/yayon-cma/transfer/summary.csv \
  --spec examples/no-author-code/yayon-cma/transfer/spec.json \
  --out examples/no-author-code/yayon-cma/transfer/output
```

This transfer establishes the tested field/order/dimension contract. It does
not establish arbitrary-data support, upstream statistical validity or a
complete reproduction of the literature image.
