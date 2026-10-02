# Empirical cumulative distributions

Use `scripts/ecdf_plot.py` for unsmoothed, unweighted raw numeric observations.
Each group gets a right-continuous empirical step function:
`F(x) = count(value <= x) / observation_count`. Repeated values produce a jump
equal to their complete count. This recipe supports comparison of the full
observed distribution without choosing histogram bins or a density bandwidth.

The script performs no statistical test, fit, smoothing, weighting or confidence
interval calculation. Describe the observational unit and sampling design in
the adopted spec and separate caption. Pooling paired observations into before
and after ECDFs shows marginal distributions and removes participant pairing
from the visual encoding; do not use it to imply a paired effect estimate.

The observational unit is an individual measurement from the stated sample or
participant. A distribution, curve, group or timepoint category is a label for
pooling observations; it is not the observational unit. If the participant is
the sampling unit, state that separately and describe repeated measurements
without treating their group labels as independent units.

```sh
python /absolute/path/to/easyviz/scripts/ecdf_plot.py \
  --data /absolute/path/to/project/source.csv \
  --spec /absolute/path/to/project/ecdf-spec.json \
  --out /absolute/path/to/project/ecdf-output
python /absolute/path/to/easyviz/scripts/ecdf_plot.py --describe-spec
```

Resolve the selected runtime and all three data/spec/output paths before running.
Agent shells may reset their working directory between calls. Use a new output
directory for a new attempt, keep accepted or evaluation outputs intact, and
check the actual renderer/input hashes in `settings.json` before delivery.
Copy cases to a writable project; keep installed skill assets unchanged.

## Explicit input roles

```csv
participant,condition,reading
001,Before,10
002,Before,10
003,Before,40
001,After,30
002,After,50
003,After,90
```

```json
{
  "chart": "ecdf",
  "fields": {"value": "reading", "group": "condition", "unit": "participant"},
  "order": {"group": ["Before", "After"]},
  "colors": {"Before": "#5278A8", "After": "#C2764E"},
  "options": {
    "x_scale": "log",
    "x_limits": [1, 100],
    "x_ticks": [1, 10, 100],
    "curve_line_width_pt": 0.8
  },
  "layout": {"width_mm": 88, "height_mm": 70, "font": "Arial", "font_size_pt": 8},
  "labels": {"x": "Measurement (a.u.)", "y": "Cumulative fraction"},
  "formats": ["pdf", "svg", "png", "tiff"]
}
```

Only `fields.value` is required. It must contain finite raw numbers in every
supplied row. `fields.group` and `fields.unit` are optional literal string
roles, preserving IDs such as `001`, `NA` and `null`. Empty mapped cells are
rejected; rows are never dropped silently. Mapped roles must name distinct
source columns. Unused source columns are retained in plotting data.

If `unit` is mapped, `(unit, group)` must be unique; without a group, each
unit must be unique. A participant can appear once in each group. This check
protects an explicitly declared one-observation-per-unit input contract;
it does not establish independence or calculate a paired test. Without a
unit role, every supplied row contributes one equal-weight observation.

`order.group`, when supplied, must list every observed category exactly once.
Otherwise curves and keys follow the first occurrence of each group in the
source. Always supply `colors` with exactly the observed group labels, keeping
category colors stable across reordered inputs. Ungrouped input instead uses
`"colors": {"all": "#5278A8"}` and gets one curve without a legend. Transparent
colors are rejected. Distinct groups must have distinct colors.

## Scale, geometry and typography

`x_scale` is `linear` by default or explicitly `log`. Log observations, limits
and tick positions must all be strictly positive. Explicit `x_limits` must be
strictly ascending and include every observation, including the smallest and
largest values. Explicit `x_ticks` must be a nonempty, unique, strictly ascending
numeric list inside the displayed limits. Unknown keys are rejected.

`x_tick_format="plain"` is the default for supplied `x_ticks`.
`x_tick_format="power10"` uses compact MathText labels such as 10³, retaining
the supplied positions and font size. This mode requires `x_scale="log"` and
ticks that are exact integer powers of ten. Both explicit formats require
`x_ticks`; a format without supplied positions is rejected.

The cumulative data stay in the range 0–1. Y ticks are 0, 0.25, 0.5, 0.75 and
1, with a 0.02 display-only vertical pad to preserve the full endpoint stroke.
Horizontal tails extend to the displayed x limits at 0 and 1; these are display
extensions and do not add observations. `curve_line_width_pt` is an explicit
positive stroke width, default 0.8 pt; legend line keys use the same width and
color. Curves have no markers. `grid=true` adds a restrained horizontal grid
behind the curves; the default has no grid.

Vector path simplification is explicitly disabled: narrow empirical steps must
remain in the exported SVG/PDF rather than being replaced by simplified lines.

Use the shared physical layout fields and optional `typography.axis`, `.tick`
and `.legend`. The script measures automatic margins and legend space inside
the unchanged canvas when margins are absent. Explicit `layout.margins` retains
a manual layout; `auto_fit=true` and explicit margins conflict. The caption is
a separate file. Axis labels and units belong on the panel; narrative, titles,
sample-size prose and statistical caveats belong in the caption.

Grouped curves use the shared categorical legend placement, with actual line
keys rather than filled swatches. For example,
`"legends": {"categorical": {"position": "bottom"}}`. Manual guide anchors
require manual margins. Legend color, stroke and title overrides are rejected:
the keys decode the curves, and explanatory prose belongs in the caption.
Ungrouped input rejects unused legend settings.

The ECDF-specific default `legends.categorical.key_width_mm` is 6 mm so the
curve key remains a readable line segment. An explicit user width is retained,
as are manual anchors. `settings.json` records `resolved_legends` and measured
guide settings, including this default and the chosen position.

## Outputs and evidence

Exports retain the complete canvas: PDF has the declared physical page, SVG
preserves editable text, and PNG/TIFF round dimensions to whole pixels at the
declared dpi. The output directory also contains:

- `plotting-data.csv`: all observations and unused columns, plus source-row IDs.
  The mapped value is parsed numerically for calculations; its exact input
  text is retained separately in `_easyviz_source_value_text`. Numeric CSV
  serialization can shorten a decimal spelling without changing its parsed
  value. Preserve the original source file and this text column for literal
  source tracing.
- `cumulative-data.csv`: sorted unique values within each group, full tie jump
  counts, cumulative counts, denominators, fractions and source-row membership.
- `stats.json`: explicitly records no tests, smoothing, fitted distributions,
  confidence intervals or inferred experimental independence.
- `settings.json`: supplied spec, actual font, colors, axes, tail/padding policy,
  input/spec/script/helper hashes and runtime versions.
- `qa.json`: fixed dimensions, source-to-actual-step audit, clipping, tick and
  legend measurements, and whether the exports passed this run.

The source audit rereads the original CSV and independently counts values and
ties. It checks actual line path vertices, group order, colors, stroke widths,
line keys, axis limits, ticks and scale. Source integrity is checked again after
export. Technical checks are not an aesthetic score: inspect the complete
render at final size, including whether curves can be distinguished and keys
leave adequate room for the data.

Before describing visible tied-value jumps, inspect the input and
`cumulative-data.csv`: a `jump_count` greater than one establishes a tied jump
within that group. Support for ties in the script does not establish ties in
the particular dataset. The Urschel example has 127 unique measurements in
each timepoint curve, so it does not demonstrate a tied-value jump. Distinguish
that real-source result from the synthetic tied-value export regression when
reporting validation or writing its caption.

A failed attempt sets `valid_outputs=false`, even if an earlier run left panel
files in the same directory. Those older files must not be delivered as a
passing result. Detailed `needs_revision` records remain available for repair.

For portable execution, copy `ecdf_plot.py`, `render.py`, `legend_layout.py`,
`auto_layout.py`, `figure_profile.py`, `annotation_review.py` and `figure_elements.py` together.
Explicit colors require no palette catalog. Use the same Python dependencies
as the core renderer and keep the adopted spec, caption and visual review
beside the output.
