# Cohort effect forest panel

This custom EasyViz create implementation uses synthetic evaluation data, not biological findings. It displays all supplied estimates and asymmetric confidence intervals, preserving the requested 180 × 120 mm canvas, Arial 8 pt type, term order and four domains. `plot.py` implements the grouped geometry explicitly; the separate supplied-interval recipe covers other interval contracts.

Run with a Python environment containing the EasyViz dependencies:

```sh
python /path/to/paired-effects/plot.py \
  --data /path/to/paired-effects/source.csv \
  --settings /path/to/paired-effects/figure-settings.json \
  --out /path/to/paired-effects
```

`source.csv` preserves the supplied bytes. `plotting-data.csv` records every plotted value, its source line, y position, and color. `figure-settings.json` is the editable input; `actual-settings.json` resolves font availability, ordering, offsets, source identity, and software. The script writes PDF, SVG, PNG, and numerical/export checks. `caption.md` contains the separate scientific explanation. `review-independent.md` and `legend-update-review.json` describe earlier candidates and their hashes. Current before/after evidence is recorded in [the create styling review](https://github.com/idealstarry/EasyViz/tree/main/evals/create-style-refinement); earlier reviews are not relabeled as reviews of the current image.

The current styling uses an explicit blue/coral pair chosen by EasyViz, not sampled author colors. Borderless estimates are visually stronger than their uncapped 0.8 pt interval segments. A 0.45 pt light dashed zero guide, a 0.5 pt gray axis and optional 0.3 pt grid have separate roles; the default has no full-height grid. Supplied endpoints, intervals and the common value axis are unchanged. The four domain headings retain the same 8 pt text size with a quieter normal-weight gray treatment. All values are still shown, and no uncertainty is recomputed for this styling change.

Running `python /path/to/paired-effects/plot.py` without arguments uses the bundled source/settings and writes beside the script. `reuse-validation.json` and `evaluation/` document one additional synthetic five-term, three-cohort run with all field names changed; this is a bounded transfer check, not a universal support claim.

The sibling `legend_layout.py` is the shared EasyViz legend helper. In this development folder it links to the canonical skill implementation; keep the helper beside `plot.py` when copying the recipe. The categorical legend retains the top-right anchor from the canvas dimensions and `legend_y_fraction`, with one column per cohort by default. Its compact keys are approximately 1.376 mm, with a 0.7 mm key-to-text gap and 2 mm column gap; text remains 8 pt. Optional `categorical_legend` settings can change `ncol`, key dimensions, and gaps without changing the plotted numeric marks. Complete legend measurements and fit issues are saved in both actual settings and numeric QA; an unfit legend fails explicitly. These category keys do not encode quantitative size.

Field mappings, cohort names/count/order/colors, source term/domain count, x limits/ticks, and physical layout are adjustable. Input requires exactly one estimate and interval per term/cohort, complete cohort coverage, consistent term metadata, unique ordering values, finite numeric inputs, positive integer participant counts, intervals bracketing their estimates, and contiguous domains. It rejects unsupported input explicitly. It does not average duplicate rows or infer statistical meaning. If participant counts vary by term, the legend omits a potentially misleading single count; counts remain in the plotting table and must be described appropriately in the caption.

The supplied 14-term/two-cohort layout is verified. Different label lengths, category counts, and cohort counts may need explicit margin, spacing, or canvas changes. The script checks text bounds, text collisions, marker separation, source-to-artist values, and exported dimensions; these checks do not replace a new visual review. No claim of arbitrary-data or universal chart support is made. SVG keeps editable text and therefore depends on font availability at viewing time; PDF embeds Arial. Raster export permits up to one pixel of integer rounding at 300 dpi. The caption and review are case-specific artifacts and should be revised for a new dataset.
