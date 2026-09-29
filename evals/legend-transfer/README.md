# Legend transfer evaluation

This benchmark uses ten fresh synthetic fixtures to evaluate the reusable legend layout on core chart families. All panels retain Arial 8 pt and the explicitly specified canvas. Each historical/current comparison receives identical source bytes and JSON settings. The benchmark does not infer statistical results or claim that smaller legends always improve a figure.

Run from the repository root with the EasyViz dependencies installed:

```sh
python tests/check_legend_layouts.py
```

`--generate-only` regenerates the deterministic source/spec files. `--only CASE_ID ...` limits a debugging run; such a run's report covers only the selected cases. `--skip-before` reuses historical measurements after the baseline has already been rendered. The baseline renderer and its palette catalog are a verbatim snapshot of the code before the new layout implementation, copied from the implementation agent's `/private/tmp/easyviz-legend-baseline` snapshot. The renderer hash is recorded in each run's evidence.

The cases cover 2, 4, and 8 categorical entries; short and long labels; 88, 132, and 180 mm widths; square and landscape continuous scales; two quantitative dot ranges and maximum areas; one manual placement; and a deliberately impossible 88 × 32 mm footprint. `manifest.json` records intent and constraints per case.

Each case preserves its source CSV and specification plus `before/` and `after/` SVG/PNG outputs, plotting tables, renderer settings/QA, and independently captured `measured-geometry.json`. Geometry uses millimeters from the lower-left canvas origin and `[x0,y0,width,height]` boxes. The data rectangle and the plot footprint including axes/ticks/labels are recorded separately. Canvas-margin bands are labeled as geometric available space; the helper's actual candidate regions and occupied envelopes are recorded separately. These fractions and colorbar-length ratios are diagnostics, not universal thresholds.

Hard checks concern complete decoding, clipping/collisions, source and mapping preservation, exact quantitative legend areas, final dimensions and type, manual-placement obedience, and refusal of the impossible footprint. Quantitative SVG path diameters and centers are checked from actual exports; PNG symbol ink is checked independently with a small raster tolerance. Correct in-memory marker sizes alone do not establish correct export rendering.

`results.json` and `results.md` summarize only executed cases. `contact-sheet.png` uses a common physical scale for documentation; it is not evidence of print-size legibility. Actual image findings belong in `visual-review.md`, separate from numerical checks. No result supports arbitrary legends, labels, data, canvases, or custom artist implementations.
