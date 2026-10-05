# Create · thermogenic expression and genotype contrasts

A real **29-gene × 6-mouse** source matrix: retain the sample-level expression
and add a separately defined descriptive genotype-mean comparison.

![Absolute expression matrix and aligned descriptive mean contrasts](output/panel.png)

This is a Create design exercise. scWAT Figure 2b supplies a literature analogue
for crisp seams, sample groups, gene-label geometry and guide proportions. Its
original z scores, dendrogram and stars are not the target of this panel.
The inspected [matrix crop](literature/figure2b-reference.png) and
[original color scale](literature/figure2b-colorbar-reference.png) are retained
with the paper attribution below; they inform design, not numeric calculations.

| Read | Inspect |
| --- | --- |
| All 174 source TPM values | [Copied observations](inputs/observations.csv), [official workbook](inputs/41467_2023_43021_MOESM8_ESM.xlsx), [input contract](inputs/input-contract.json) |
| Display and descriptive comparison | [Specification](spec.json), [caption](caption.md), [design decisions and limits](design-notes.md) |
| Runnable custom code | [plot.py](plot.py), [independent source/export validator](validate.py) |
| Full exports and trace | [PDF](output/panel.pdf), [SVG](output/panel.svg), [cell transformation](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/output/transformed-cells.csv), [genotype summaries](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/output/genotype-contrasts.csv), [selectable source-bound elements](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/output/elements.json), [validation](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/output/validation.json) |
| Actual internal review | [First render](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/attempts/attempt-01/panel.png), [corrected second pass](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/attempts/attempt-02/panel.png), [final physical-size PDF preview](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/output/pdf-preview-96dpi.png) |

From a repository checkout or a copied bundled case, run:

```sh
python plot.py --out /absolute/path/to/new-thermogenic-panel
python validate.py --output /absolute/path/to/new-thermogenic-panel
```

If the scripts are stored elsewhere, pass
`--tools /absolute/path/to/easyviz/scripts`. Choose a fresh output directory;
attempts are preserved. Arial is the recorded manuscript font. An explicit
`--font "DejaVu Sans"` override is supported and recorded for systems without
Arial; it is a different adopted font, not a claim of matching Arial glyphs.

The heatmap scale is **0–12 log2(TPM + 1)**, including the six literal observed
Atp5o zeros. The **0–5** comparison scale contains the complete nonnegative
differences of genotype means of those log-transformed values. Neither scale
is silently clipped. The panel is **112 × 128 mm** with **8 pt** text across
PNG, PDF and SVG. All cells, contrast bars, data labels and sample bands are
selectable vector groups mapped to actual source cells for workbench notes.

Data and reference crops: Huang et al., Nature Communications 14, 7102 (2023),
[article and Source Data](https://doi.org/10.1038/s41467-023-43021-8),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The [separate caption](caption.md) states the adaptations and inferential limits.

The custom renderer requires EasyViz's consumed-byte `figure_handoff` helper
(v0.4.5 runtime). It captures the data, adopted specification and declared
inputs before drawing, then binds the actual final exports in `handoff.json`.
Source snapshots preserve those exact bytes. A late source change rejects the
attempt and leaves failed QA; [receipt checks](https://github.com/idealstarry/EasyViz/blob/main/examples/create/thermogenic-expression/receipt-validation.json) exercise
this after numerical validation, using disposable input copies.

The bundled exports are frozen previews. Redraw this copied case into a fresh writable directory to create current source bindings, QA, selectable elements and a handoff receipt. Development review/history links refer to the original repository records.
