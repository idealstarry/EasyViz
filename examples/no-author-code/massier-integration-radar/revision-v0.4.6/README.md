# Compact kBET radar

This revision preserves the selected depot kBET radar's five spokes, five methods and all 25 supplied rates. It brings the data circle, point size and readable type into a compact relationship. The depot heading moves into the caption; class labels, numerical radial ticks, metric label and method key remain in the figure.

![Revised radar](output/panel.png)

The explicitly adopted canvas is **64 × 66 mm**, with a **34 mm** circle, editable **8 pt Arial**, **5.1 pt** geometric point diameter and **0.85 pt** data strokes. The source PDF's selected circle is approximately 23.88 mm across, its text is 7.924 pt, its point geometry is 3.575 pt and its data strokes are 0.847 pt. Direct class labels require more room than the original whole-figure shared class key. All three zero values remain at the genuine origin; no jitter or inferred negative radial padding is introduced.

Copy the whole case to a writable project directory. Keep `revision-v0.4.6` beside the parent `inputs` directory, then run:

```sh
python /path/to/case/revision-v0.4.6/plot.py --runtime /path/to/easyviz/scripts --out /path/to/project/radar
```

Use EasyViz **0.4.6 or later** and its Python dependencies. Default exports require Arial. On another system, explicitly add `--font "DejaVu Sans"` to adopt that installed family; text remains 8 pt and the output records the original/adopted specifications. Use a fresh output folder; `--overwrite` archives an existing attempt before redrawing.

The script exports PDF, editable-text SVG, PNG, literal plotting data, source snapshot, actual settings, source-to-artist checks, an element map and a consumed-byte `handoff.json` for the review workbench. Actual data/specification/script/helper inputs are captured before drawing and rechecked after export. The previous 88 × 88 mm render stays intact in the parent case. See the [adopted specification](adopted-spec.json) and separate [caption](caption.md).

Data and reference excerpt: Massier et al., *An integrated single cell and spatial transcriptomic map of human white adipose tissue*, Nature Communications (2023), [DOI 10.1038/s41467-023-36983-2](https://doi.org/10.1038/s41467-023-36983-2), [source release](https://data.mendeley.com/datasets/y3pxvr4xbf/2), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The reference is cropped and the implementation is newly written without author plotting code. This is a reconstruction of supplied rates, with explicit geometric adaptations; upstream integration is not rerun.
