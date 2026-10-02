# First panel from prepared data

For the five core chart families, create a validated specification from explicit
column roles instead of assembling the full schema. Choose the chart and field
meanings from the scientific question; the helper does not infer them.

```sh
python /absolute/path/to/easyviz/scripts/draft_spec.py \
  --data /absolute/path/to/project/source.csv --chart dotplot \
  --field x=condition --field y=gene \
  --field size=fraction --field color=mean_score \
  --panel-size-mm 120 90 --out /absolute/path/to/project/plot.json
python /absolute/path/to/easyviz/scripts/render.py \
  --data /absolute/path/to/project/source.csv \
  --spec /absolute/path/to/project/plot.json \
  --out /absolute/path/to/project/attempt-01
python /absolute/path/to/easyviz/scripts/render.py --describe-spec
```

Replace `/absolute/path/to/easyviz` with the discovered skill directory and
resolve data/spec/output paths explicitly; Agent shells may reset their working
directory between calls. Use a new attempt directory for each render and keep
accepted outputs intact. Quote a field assignment containing spaces, such as
`--field 'y=Cell type'`. Non-English input
column names are supported; visible text still requires an appropriate font.
Use the [chart library](chart-library.md) for the roles of other families.

The draft contains only the chart, explicit fields, measured layout and supplied
preferences. Without requested dimensions it uses the renderer's adjustable
88 × 88 mm, 8 pt defaults. For a related panel set, use
`--profile /absolute/path/to/project/profile.json --panel panel-name`;
the named panel supplies the dimensions and shared settings.
An explicit local font that conflicts with the profile is rejected. Existing
specifications are never overwritten by this helper; edit a saved spec directly
when refining a plot.

For composition, **supply `--normalization none`, `sample_sum` or `denominator`**.
The last also requires `--field denominator=column_name`. The helper cannot decide
whether the supplied categories represent a whole population. It adds no tests,
pairing, clustering, filtering, titles or missing-data assumptions. Sparse dots
retain the [explicit data-state contract](dot-states.md).

Edit the saved JSON for axis names and units, meaningful ordering, known color
limits, area scales, requested formats, and supported options. Add statistics
only after establishing the experimental unit and design. Unsupported layers
still need an appropriate case or custom implementation.

For paired observations, component/replicate bars, empirical cumulative
distributions or supplied intervals, go directly to the focused recipe in the
[chart library](chart-library.md). The Agent checks the source roles and writes
the small specification described there. Do not force these layers into a core
chart or substitute independent-group statistics for paired measurements.
The core's `--describe-spec` includes `focused_recipes` with absolute script and
documentation paths and required roles. Run the selected recipe's
`--describe-spec` for its full options and scientific checks; these entries do
not expand the five-family draft or core rendering contract.

## Measured layout

New drafts set `layout.auto_fit: true`. The renderer measures actual axis text
and legend envelopes, then fits them inside the unchanged canvas. Automatic
guides are tried as a group on the right, bottom and top, stacking complete
measured envelopes along the chosen side. Explicit nonmanual guide positions
are retained, including when other guides are automatic. Feasible side
candidates are compared by data-region area, a space-allocation choice that
still requires visual judgment. This bounded search does not compare every
possible guide-column or colorbar-length combination.

This mode preserves fonts, text, values and quantitative marker areas. It does
not shorten labels, hide categories, alter units or enlarge the canvas. It is
optional for existing specs. Use explicit margins for an accepted manual layout;
`auto_fit: true` conflicts with margins, manual guide coordinates and a manual
`main_plot_bbox_mm`.

If the contents cannot fit, QA remains `needs_revision`. Resolve the cause by
explicitly enlarging or splitting the panel, wrapping labels in the specification
or choosing a better supported design. Do not shrink an agreed font or discard
data to obtain a pass. Heatmap annotations are checked against their own cells;
unreadable requested values cause a failure even when ticks and exports fit.

Inspect the exported PNG at its final proportions. `settings.json` records the
actual layout and guide geometry; `qa.json` records any clipping, tick collisions,
cell annotation failures and export checks. Technical fit cannot assess scientific
meaning, all mark/label collisions, contrast, aesthetic balance or journal
acceptance. Deliver a separate caption with the data meanings and methods; the
helper does not invent that narrative.

At final size, explicitly inspect the smallest positive dots, the palest end of
the chosen colormap, and measured-zero glyphs. A technically fitting panel can
still make these marks difficult to see. Compare a darker sequential scale or a
clearer decoded state symbol when appropriate; preserve the original numeric
values, zero quantitative area, agreed fonts and canvas. Do not turn small or
zero values into larger positive quantitative circles to improve visibility.
