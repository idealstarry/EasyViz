# Real distribution previews

Use `scripts/preview_choices.py` after inspecting the table and establishing
explicit roles in prepared observation data. The helper produces two actual
alternatives at the same final canvas size: a box with every raw observation,
and an unsmoothed empirical cumulative distribution (ECDF). An explicitly
requested violin can add a third alternative when each group contains at least
five distinct values. No alternative is selected automatically.

This request is a comparison of reading tasks, not an execution of candidate
fields from `inspect_data.py`. The Agent should prepare the small request JSON
from confirmed source context and explicit unknowns; the user need not write
JSON or choose a renderer. Use the output manifest and actual images to explain
what each alternative helps the reader compare.

This is a choice between basic single plots. Improve their mark contrast,
summary boundaries and spacing before proposing a composite view. A violin is
useful only when density shape serves the question; it is not an automatic
upgrade over a box or ECDF.

```sh
python /absolute/path/to/easyviz/scripts/preview_choices.py --describe-contract
python /absolute/path/to/easyviz/scripts/preview_choices.py \
  --data /absolute/path/to/project/prepared-observations.csv \
  --request /absolute/path/to/project/preview-request.json \
  --out /absolute/path/to/project/new-preview-attempt
```

Resolve the selected Python runtime and all paths before execution. Keep
accepted/evaluation outputs intact: the helper requires a fresh directory and
rejects an existing directory or symlink. It is portable outside this repo when
copied beside `create_style.py`, `ecdf_plot.py`, `render.py`, `legend_layout.py`,
`auto_layout.py`, `figure_profile.py`, `annotation_review.py`,
`panel_readability.py` and `figure_elements.py`; it uses
the same dependencies as the renderer and requires no palette catalog for
explicit colors.

## Explicit request

```json
{
  "style_mode": "crisp",
  "row_kind": "observations",
  "fields": {"value": "reading", "group": "condition", "unit": "observation_id"},
  "design": {
    "structure": "unknown",
    "confirmed": false,
    "unit_definition": "Sampling unit unknown; each row is one supplied measurement"
  },
  "measurement_units": null,
  "colors": {"Control": "#55A0FB", "Treatment": "#FF8080"},
  "order": {"group": ["Control", "Treatment"]},
  "layout": {"width_mm": 88, "height_mm": 70, "font": "Arial", "font_size_pt": 8, "dpi": 300},
  "labels": {"value": "Reading", "group": "Condition"},
  "formats": ["png", "pdf", "svg"],
  "options": {"value_scale": "linear", "point_layout": "beeswarm", "point_alpha": 1, "point_style": "filled", "box_style": "outline", "box_width": 0.18, "include_violin": false}
}
```

`fields.value` and `fields.group` are required. `fields.unit` is optional and
contains literal IDs; it does not establish independent sampling. Roles must
name distinct columns. Group names and IDs such as `001`, `NA` and `null`
remain literal strings. All mapped cells must be nonempty, every value must be
finite, headers must be unique, and every CSV row must contain all source
columns. The helper does not reinterpret missing tokens, remove rows or invent
values. Unused source columns are retained. Ungrouped data require an explicitly
prepared constant category if this two-view comparison is desired; the ECDF
recipe alone also supports ungrouped data.

`row_kind` must explicitly be `observations`. Summary tables and technical
replicates require appropriate preparation upstream; requesting previews does
not authorize converting technical repeats into independent samples. A mapped
unit can appear only once in this distribution comparison. Duplicate
unit/group measurements are rejected. IDs recurring across groups are also
rejected, because the same ID may define pairing or repeated sampling.

`design` requires `structure`, `confirmed` and a nonempty `unit_definition`.
Structure is `unknown` or `independent`. A confirmed independent design
requires `fields.unit`. Unknown structure must have `confirmed=false` and is
descriptive only. The helper does not infer independence when design is known
or unknown, and computes no test, effect estimate or confidence interval.

Explicit `paired` or `repeated` design is rejected before output. Use
[`paired_plot.py`](paired-plot.md) with explicit `unit`, `condition` and `value`
roles and complete one-observation-per-unit-per-condition data. That recipe
can encode correspondence using connectors. Marginal boxplots and ECDFs alone
do not show within-participant changes. Incomplete pairs must be prepared by a
declared upstream policy; the helper never drops or fills them. Do not rename
participant IDs merely to bypass this check.

`measurement_units` is required: supply the known units or `null` when unknown.
Unknown units are visibly stated in the measurement axis and caption. Supply
`labels.value` without appending invented units; the helper appends the declared
units. Unknown observational units or independence are stated in each caption
and manifest. These previews can describe the supplied values while scientific
facts remain unresolved.

`colors` must map every observed category exactly once, with distinct opaque
colors. The optional `order.group` lists all categories exactly once; otherwise
source first appearance defines the shared order. Layout defaults are 88 × 70
mm, Arial, 8 pt and 300 dpi. Optional layout keys are `width_mm`, `height_mm`,
`font`, `font_size_pt`, `line_width_pt` and `dpi`; optional typography roles are
`axis`, `tick` and `legend`. Automatic margins fit each encoding inside the
identical canvas. The recorded actual font and all three text roles must match
across outputs; font substitution is recorded by the underlying renderer.
Titles, narrative and sample-count prose remain in separate captions.

Optional `value_scale` is `linear` or `log`; log requires strictly positive
values and adds no pseudocount. Optional `value_limits` are ascending bounds
containing every observation. Otherwise complete bounds are computed once and
shared. Boxplots are horizontal, so their numeric x-axis has the same scale
and limits as the ECDF. Box summaries use raw values even on a log display.
Formats are unique `png`, `pdf`, `svg` and/or `tiff`; PNG is required for visual
inspection. PDF, SVG and raster exports keep the whole physical canvas.

## Reading tasks and limitations

| Choice | Helps read | Meaning and limitation |
| --- | --- | --- |
| Box and every point | Group medians, spread, individual measurements | Median, 25th/75th percentiles and whiskers reaching observations within 1.5 IQR. Points include every observation, including values beyond the whiskers. Quartiles and whiskers are descriptive spread, not confidence intervals; summaries can obscure multiple modes. |
| ECDF | Full observed distributions, tails, fraction at or below a value | Unweighted, right-continuous `count(value <= x)/group observation count`, with complete tied-value jumps and no smoothing. Each group's denominator is its own row count. Curves do not encode paired change. |
| Optional violin and every point | Broad distribution shape | Gaussian KDE with Scott bandwidth and 100 evaluation points; each width is independently normalized. Shape depends on smoothing and width is not sample count or uncertainty. Five distinct values is an eligibility guard, not proof of a reliable density. |

`include_violin=true` is explicit opt-in. Sparse or constant groups cause a
clear error before any output rather than a silent chart substitution.
`point_layout=jitter` uses a fixed seed and changes only category position;
points can overlap, which must be inspected at final size. Explicit `beeswarm`
uses the existing physically measured point placement and fails if all points
cannot fit. Both policies retain numeric values, row membership and point size.
`point_style` selects fixed-size `filled` or `hollow` observations.
`point_edge_width_pt` is a positive finite number that requires hollow marks;
the default hollow stroke is 0.45 pt. Hollow points have no face fill, use
category-colored edges, and include stroke extent in physical placement.
`box_style=outline` removes the box interior fill while retaining quartiles,
whiskers and medians; it applies only to the box candidate. Optional violins
retain their own fill and boundary, even when the box is outlined. The helper
audits actual observation edges/faces and box fill as well as values.
`box_width` controls categorical box thickness, with finite `0 < box_width <= 1`;
the legacy default is 0.5. A starting 0.18 reduces oversized summary areas in
sparse layouts without changing their numeric quartiles. Inspect final physical
thickness and point-summary crossings. It is not applied to optional violins.

The default `style_mode=crisp` shares `create_style.py` with new Create drafts:
omitted cosmetics use filled points at alpha 1, outline boxes of width 0.18,
and the starting `line_roles` in [Create colors and strokes](create-style.md).
Use `style_mode=legacy` to replay a pre-0.4.3 request's omitted style options:
filled boxes at .22 fill alpha, point alpha .65 and box width .5. Explicit
options and category colors take precedence in either mode; mode changes no
source row, value, summary or study design.

An optional top-level `line_roles` object supplies core data/summary/reference/
axis/grid styling. It affects box/violin boundaries and axes as documented;
for ECDF, data width controls the curve, axis controls axes, and grid controls
an already-enabled grid. Explicit `options.curve_line_width_pt` takes precedence
over ECDF data width. ECDF category colors and solid step lines remain intact;
summary/reference roles add no curve or threshold. An explicit layout stroke
width retains the existing global-width fallback; per-role overrides still win.

Select another treatment after final-size inspection when useful.
`point_alpha` affects only raw points and must satisfy finite `0 < alpha <= 1`;
it does not change values, point size or group identity. ECDFs and summary
strokes keep their own settings. See [Create colors and strokes](create-style.md)
for role-based decisions rather than universally thinning/fading marks.

## Deliverables and verification

The root `manifest.json` records each reading task, definition, limitation and
relative file path/hash, actual `style_mode`, the complete field/design declaration, the original
source/request paths, and byte hashes for both copied inputs. The source
snapshot `source.csv` is byte-identical to the original; `observation-trace.csv`
retains every literal source field plus one-based source-row IDs and exact
measurement text. `request.json` retains the exact request bytes.

Each alternative saves real panel exports, `spec.json`, `caption.md`,
`plotting-data.csv`, `settings.json`, `stats.json` and `qa.json`. ECDF also saves
`cumulative-data.csv` with ties, denominators and row membership. Its source
audit checks actual empirical vertices. The distribution audit checks actual
rendered point count, group colors and intended alpha, exact numeric coordinates, box quartiles
and medians against the raw snapshot. The original and snapshot hashes are
checked again after all renders. Root `qa.json` checks identical dimensions,
actual font, axis/tick/legend text sizes, colors, measurement-axis limits,
scale and source hash across alternatives. Exports also receive the existing
physical-dimension, text clipping, tick/legend and glyph checks.

A failed child or source/shared-setting audit leaves `valid_outputs=false`
with the failure evidence. Do not deliver a failed attempt's panel files as
passing previews. Automated checks verify the recorded scope and do not score
aesthetics or establish study design. `visual-review.md` begins as pending;
inspect all actual exports at final size, record readability and the tradeoffs
for each reading task, and explain the choice to the user. Do not claim that
automated QA proves a visual review. `selection.chosen_choice` remains null
and `automatic_winner` remains false.
