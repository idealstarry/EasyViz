# Supplied numerical estimates and intervals

Use `scripts/interval_plot.py` when each source row already supplies an estimate,
lower endpoint and upper endpoint. It preserves asymmetric intervals exactly.
The script draws numerical results; it does not compute an interval, infer a
sample size, weight estimates, combine studies, or run a significance test.
The upstream meaning and uncertainty definition belong in the adopted spec and
caption. Do not rename an arbitrary supplied interval as a confidence interval.

```sh
python scripts/interval_plot.py --data source.csv --spec interval-spec.json --out panel-output
python scripts/interval_plot.py --describe-spec
```

## Minimal input and specification

```csv
label,estimate,lower,upper
Group A,1.8,0.9,3.4
Group B,0.7,0.4,1.0
```

```json
{
  "chart": "interval",
  "fields": {
    "label": "label",
    "estimate": "estimate",
    "lower": "lower",
    "upper": "upper"
  },
  "options": {
    "x_scale": "log",
    "reference_value": 1,
    "x_limits": [0.3, 4],
    "x_ticks": [0.5, 1, 2, 4]
  },
  "layout": {
    "width_mm": 88,
    "height_mm": 70,
    "font": "Arial",
    "font_size_pt": 8,
    "auto_fit": true
  },
  "labels": {"x": "Supplied ratio"},
  "formats": ["pdf", "svg", "png", "tiff"]
}
```

Default dimensions are 88 × 88 mm and default typography is 8 pt. Automatic
layout measures label and guide space within those dimensions; it does not
shrink text or enlarge the canvas. Supply explicit `layout.margins` instead of
`auto_fit` for a manual layout. PDF retains the physical page; SVG retains text;
raster dimensions round to whole pixels at the requested dpi.

## Multiple series and color categories

Add `fields.series` for multiple estimates per label. `order.label` and
`order.series`, when supplied, must each list every observed category exactly
once. Every supplied `(label, series)` pair must be unique. Missing pairs remain
absent; no interval, zero or attempted measurement is inferred.

`options.series_layout="aligned"` is the default: each label has one row and
series use stable vertical offsets across all labels. `series_span` defaults
to 0.6 label-row units and must be greater than zero and at most 0.8.

`options.series_layout="blocks"` gives each series a labeled block, traversing
declared series order and then declared label order. Each block contains only
its supplied pairs and a necessary 8 pt series header. Headers directly decode
the series, so the script omits the series legend. `series_span` does not apply
to blocks and cannot be supplied with that layout.

Colors encode series by default. Optional `fields.color` names a categorical
source column and may alias `fields.label` or `fields.series`. For example:

```json
{
  "fields": {
    "label": "outcome",
    "series": "exposure",
    "color": "outcome",
    "estimate": "estimate",
    "lower": "lower",
    "upper": "upper"
  },
  "options": {"series_layout": "blocks"},
  "order": {
    "label": ["Outcome A", "Outcome B"],
    "series": ["Exposure A", "Exposure B"]
  },
  "colors": {"Outcome A": "#0072B2", "Outcome B": "#D55E00"}
}
```

This fragment is merged into a complete interval spec. Headers and row labels
stay neutral when color represents outcomes. Row labels already identify those
outcomes; an independent third color category gets a measured legend. An
independent color role with aligned series is rejected because that layout
would leave the series identity undecoded. Explicit `colors` must cover every
observed color category; colors are never cycled. Optional `order.color` must
include every color category exactly once. Without series or a color mapping,
all estimates use one default color.

## Reference, ticks and marker fill

There is no automatic reference value. `reference_value=0` on a linear axis
and `reference_value=1` on a log axis are explicit choices. Log estimates,
endpoints, reference and limits must all be strictly positive. `x_limits`
must be strictly ascending and contain every supplied endpoint and reference.
`x_ticks` provides strictly ascending numeric positions, displayed as plain
numbers without extra minor tick labels. Ticks must fit the displayed limits;
specify limits explicitly if needed. Neither scale transforms the stored source
coordinates.

`marker_area_pt2` is the geometric area of the circle shape, default 20 pt²,
held equal across every row. Hollow markers use the same circle size; their
outline occupies extra space. Raw Matplotlib `s` is `4/pi * marker_area_pt2`,
and the script records both quantities. `cap_height`, default zero, is an
optional interval-cap height in label-row units, between zero and 0.2.

Default `mark_fill="all_filled"` gives every estimate a filled borderless
circle. A reference overlap does not change that default. Two explicit modes
support hollow marks:

- `mark_fill="input"` requires `fields.mark_state` with literal `filled` or
  `hollow` values on every source row. A mark-state role with another mode is
  rejected so supplied styling cannot be silently ignored.
- `mark_fill="reference_overlap"` explicitly adopts hollow for
  `lower <= reference_value <= upper` and filled otherwise. The reference must
  be supplied. Endpoint equality counts as overlap. This encoding makes no
  statistical significance claim.

`labels.filled` and `labels.hollow` customize the state-key wording. The key
uses the same filled/hollow border policy and the shared measured legend
placement, including `legends.categorical.position="bottom"`. Avoid wording
that claims a statistical interpretation unsupported by the source.

## Outputs and checks

The output directory contains panel exports, `plotting-data.csv`,
`settings.json`, `stats.json`, and `qa.json`. Plotting data retains source rows
and unused source columns, plus explicit source-row IDs, actual vertical
positions, fill states, circle area and Matplotlib `s`. Settings retain the
supplied spec, input/spec hashes, actual font, axes, color mappings, physical
dimensions, runtime versions, and script/helper hashes.

The independent numerical audit rereads the original CSV after drawing. It
compares each actual estimate marker, both interval endpoints, optional caps,
stable row/series positions, color, fill, area, marker shape, reference, and
axis scale against that fresh source. Final checks measure tick collisions,
text clipping, guide placement, circle clipping, and cross-row mark collisions.
They do not certify aesthetic reference fidelity; inspect the exported panel
and obtain an independent visual review when reproducing a reference.

A failed run raises an error and retains `qa.json` with `valid_outputs=false`.
Detailed `needs_revision` records are preserved; a new failed attempt also
invalidates an earlier passing record in the same output directory. Existing
exports after failure may belong to an earlier run and must not be delivered
as passing outputs.

For execution outside the installed skill directory, copy `interval_plot.py`,
`render.py`, `legend_layout.py`, `auto_layout.py`, `figure_profile.py`, and
`annotation_review.py` together. Include `assets/palettes/palettes.json` under
the skill directory layout when using named EasyViz palettes, or supply
explicit category colors. Use the same Python dependencies as the core
renderer. Keep the adopted spec, caption and review beside the output.
