# Supplied summary lines and uncertainty bands

Use `scripts/timecourse_plot.py` for numerical time courses or dose-response
summaries when a reference has mean lines and shaded uncertainty. This focused
recipe preserves supplied estimates and supplied SD or lower/upper endpoints.
It does not aggregate raw replicates, infer independence, calculate SEM or a
confidence interval, fit a pharmacological model, smooth trajectories, or test
differences. In reproduce, obtain the independent image reading and adopted
specification before selecting this implementation.

```sh
python /absolute/path/to/easyviz/scripts/timecourse_plot.py \
  --data /absolute/path/to/project/summaries.csv \
  --spec /absolute/path/to/project/timecourse-spec.json \
  --out /absolute/path/to/project/output
python /absolute/path/to/easyviz/scripts/timecourse_plot.py --describe-spec
```

Copy example inputs to the user's writable project and resolve all paths.
Keep this script and the shared runtime helpers together. A published example
demonstrates a specific contract, not automatic support for every reference.

## Establish the numerical meaning

Each row must be a supplied summary at one numeric x position for one series.
Use `fields.x` and `fields.estimate`. Optional `fields.series` is a literal
category, preserving strings such as `001`, `NA`, and `null`; an ungrouped
input instead uses `colors.all`. Define uncertainty explicitly:

- `uncertainty.kind="sd"` requires `fields.sd` only. Draw the supplied estimate
  minus/plus the supplied nonnegative SD; never divide it by a guessed n.
- `uncertainty.kind="supplied_bounds"` requires `fields.lower` and `.upper`
  only. Both endpoints must be finite and contain the central estimate.
  Bounds may be asymmetric. They are not called a confidence interval unless
  the supplied study evidence establishes that definition.

`uncertainty.label` is mandatory and records the actual definition in settings.
Keep its prose in the separate caption. The script does not add an uncertainty
label inside the panel or create fictitious raw measurements from a summary.
An n supplied by a caption is not automatically a count of independent
biological replicates, especially for cells measured repeatedly.

```json
{
  "chart": "timecourse",
  "fields": {"x": "minute", "estimate": "mean", "sd": "sd", "series": "condition"},
  "uncertainty": {"kind": "sd", "label": "Supplied standard deviation"},
  "order": {"series": ["Control", "Treatment"]},
  "colors": {"Control": "#2581B9", "Treatment": "#D76F3B"},
  "options": {"curve_line_width_pt": 0.8, "band_alpha": 0.25, "marker_diameter_pt": 2},
  "labels": {"x": "Time (min)", "y": "Response (a.u.)"},
  "layout": {"width_mm": 100, "height_mm": 76, "font": "Arial", "font_size_pt": 8},
  "legends": {"categorical": {"position": "bottom"}},
  "formats": ["pdf", "svg", "png", "tiff"]
}
```

All mapped roles need distinct, nonempty columns. Nonfinite values, missing
summaries and duplicate x within a series fail explicitly instead of being
removed or averaged. Every series requires at least two distinct positions.
Each series is stably sorted by x for plotting; original row order and exact
numeric input text remain in `plotting-data.csv`. An irregular x grid retains
its true spacing. Different series need not share a complete x grid.

Straight line segments and band edges connect adjacent supplied coordinates.
They are a visual connection, not a fitted model, continuous mechanistic
claim, or new measured time point. The recipe cannot reconstruct missing
author-model curves; implement a documented model separately if required.

## Scales and axis assignments

`x_scale`, `y_scale` and `right_y_scale` accept `linear` or `log`. Every source
x must be positive for log x; the entire band must be positive for log y.
Limits must include all summaries and all band endpoints. Tick lists are
unique, strictly ascending finite numbers within the displayed limits.
Unknown configuration keys are rejected. Both vector line and band path
simplification are disabled to retain the supplied geometry in SVG and PDF.

The default is one y axis with a categorical line legend for multiple series.
Supply colors for every category and retain those mappings when data reorder.
Fixed marker diameters are optional sampling markers; they represent summary
positions, not individual replicates or quantitative sample sizes.

For an adopted dual-axis reference, `options.axis_by_series` must assign
exactly one series to `left` and one to `right`. Both `labels.y` and
`labels.right_y` must explicitly identify their quantities and units. Matching
colored axes decode the curves; the dual-axis recipe has no separate legend.
`right_y_limits`, `.right_y_ticks` and `.right_y_scale` configure the second
axis. For example, the Shi case uses width on the left and length on the right.
Its different y ranges are preserved. Vertical proximity across those axes
does not establish equal numerical dimensions, correlation, or an effect size.

Both fills are drawn behind both mean lines while each quantity retains its
own y transform. Manual margins remain available. Otherwise the dual-axis
layout measures both complete axis-text extents inside the fixed canvas;
single-axis layouts use the shared measured legend helper. Agreed canvas
dimensions and font sizes remain unchanged. Manual margins and `auto_fit=true`
conflict. The optional horizontal grid stays below the data layers.

## Review and transferable evidence

The main [Shi time-course case](../assets/cases/shi-timecourse/README.md)
uses all 120 supplied summaries and SD values from a CC BY Nature
Communications figure, without author plotting code. It explicitly expands
the width-axis lower range to retain a band that the reference appears to
touch at the plot bottom. Its caption and adopted spec record this adaptation.
An independent fresh reader interpreted the image before implementation.

The reproduction transfer changes all column roles, categories, times and
values while retaining the reference's dual-axis, mean/SD-band geometry.
It stays in reproduce. A separate synthetic create fixture changes every mapped field name,
uses three literal series, a logarithmic dose axis, irregular x spacing, and
asymmetric supplied endpoints. This establishes those bounded input cases;
it does not prove successful fitting, arbitrary-reference reproduction, or
universal manuscript aesthetics. The caller selects `--track create` or
`--track reproduce`; the recipe's geometry does not invent another track.

Inspect `qa.json` for checks against actual line coordinates and complete
ordered band path vertices, source row membership, axis transforms, scales,
ticks, colors, strokes, marker diameters, band opacity, clipping, and export
dimensions. `stats.json` records the absent inference/fitting steps.
`settings.json` records input, spec, actual runtime/helper hashes, font and
resolved axes. `elements.json` associates selectable curves/bands and axis
labels with their configuration paths for agent-led edits when the shared
export helper supports it.

A failed run records `valid_outputs=false`, even if old panel files remain.
Numeric and technical checks are separate from aesthetic review: inspect the
complete exported image at final size, especially overlapping bands, colored
axis correspondence, visible sample positions and the total legend footprint.
Keep sources, unit definitions, repeated-measurement limitations and fitting
caveats in the separate `caption.md`.
