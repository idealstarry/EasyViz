# Proposed inhibition color-scale alternatives

These are two controlled visual experiments, **not replacements or accepted improvements**. Both use the existing source data, selection, ordering, aligned tracks, 180 × 160 mm canvas and 8 pt Arial. The main matrix, its full −400 to 1000 min range, and all 400 selected measurements remain fixed. All 5,776 inputs continue to contribute to the original full-data summaries; no input is capped or modified.

| View | Change | Reading benefit and cost |
| --- | --- | --- |
| [Current original](../../../examples/create/annotated-inhibition/panel.png) | Existing sequential coral scale; summary bars in bright cyan. | Straightforward value-linear encoding. Negative and small positive values share a pale warm hue, and zero has no colorbar tick. Most cells occupy a narrow band of color. |
| [Linear with zero](linear-zero/panel.png) | Value-linear scale; blue below zero, neutral at zero, coral above zero. Colorbar ticks −400, 0, 1000. | The 11 negative cells have a separate hue and zero is explicit. Small positive values become even paler, so this does **not** solve all weak-contrast structure. It is a stronger candidate for a sign-focused task than for finding moderate differences. |
| [Signed asinh](signed-asinh/panel.png) | Same endpoints and colors, with disclosed signed `asinh(x / 100 min)` color normalization. Colorbar ticks −400, 0, 100, 1000 remain in original minutes. | Differences among the numerous low-to-moderate positive cells are more visible, and negative cells remain distinguishable. Large positive differences receive less color distance; viewers must use the nonlinear scale. This is a task-specific alternative, not a default for every heatmap. |

Both alternatives reduce summary-bar chroma from `#29ACF3` to `#6197B8` to test whether the pairwise matrix can take visual priority. This is a deliberate secondary-track choice, not a new global muted-palette preference. The mixed blue/neutral/coral palette uses previously sourced blue and coral endpoints but is a new EasyViz design, not the original author's scale.

For a measurement `x` in minutes, the linear position is `(x + 400) / 1400`. The nonlinear position is:

```
t = (asinh(x / 100) - asinh(-400 / 100))
    / (asinh(1000 / 100) - asinh(-400 / 100))
```

Zero is at `t = 0.285714…` for the linear candidate and `t = 0.411298…` for the nonlinear candidate; that position anchors the neutral color. Zero is **not** moved to the midpoint of a symmetric range. The width of 100 min is an explicit round design parameter on the scale of the dense part of these data (quartiles 79.19, 139.28 and 200.66 min), not an experimentally established threshold. The colorbar names the nonlinear encoding. A manuscript caption would also need to disclose it.

The copies of plotting, summary and selection CSVs match the current example byte for byte. Forward/inverse normalization was checked at −400, −100, 0, 100, 300 and 1000 min. The existing export checks pass for both candidates. I inspected both actual PNGs and corrected Matplotlib's automatic nonlinear tick formatter so the displayed ticks are plain original-unit values. These checks establish unchanged data and valid exports, not aesthetic superiority.

Visual judgment: the nonlinear candidate has clearer within-matrix variation than the original for a pattern-reading task; the linear candidate has clearer sign decoding but weaker moderate-value separation. Neither changes the deeper selection/order decisions, which remain fixed in this experiment. The scientific reading task should decide whether either tradeoff is worthwhile.

Run from the repository root with `.venv/bin/python evals/design-value/inhibition-scale/build.py`. The build script copies the example renderer locally and applies only the recorded scale, colorbar-tick and secondary-bar-color substitutions. No example, core renderer or plugin file is modified.
