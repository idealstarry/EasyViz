# Repeated observations with median and IQR

Use `scripts/paired_plot.py` when the source supplies explicitly identified units
measured in two or more repeated conditions. It keeps every supplied observation,
draws a distribution of raw points with median and interquartile range (IQR), and
can add explicitly adopted within-unit connectors. It does not infer pairing
from row order, run a test, or interpret IQR as a confidence interval.

The plotted value is parsed numerically for summaries and positions. Output
`plotting-data.csv` also retains its exact input spelling in
`_easyviz_source_value_text`, alongside the source-row identity. Keep the
original source file: normalized numeric CSV text and original decimal
spelling are distinct forms of traceability.

```sh
python /absolute/path/to/easyviz/scripts/paired_plot.py \
  --data /absolute/path/to/project/source.csv \
  --spec /absolute/path/to/project/paired-spec.json \
  --out /absolute/path/to/project/paired-output
python /absolute/path/to/easyviz/scripts/paired_plot.py --describe-spec
```

Resolve runtime/data/spec/output paths explicitly; an Agent shell can reset
its working directory between calls. Use a fresh output directory for a new
attempt and verify the renderer/input hashes in `settings.json`. Keep accepted
outputs and installed skill assets intact; copy cases into a writable project.

## Input and minimal specification

```csv
person,visit,measurement
001,Before,12
001,After,21
002,Before,18
002,After,26
003,Before,15
003,After,19
```

```json
{
  "chart": "paired",
  "fields": {"unit": "person", "condition": "visit", "value": "measurement"},
  "order": {"condition": ["Before", "After"]},
  "options": {
    "y_scale": "linear",
    "quantile_method": "linear",
    "point_layout": "swarm",
    "point_area_pt2": 10,
    "connect_pairs": false
  },
  "layout": {
    "width_mm": 88,
    "height_mm": 88,
    "font": "Arial",
    "font_size_pt": 8,
    "auto_fit": true
  },
  "labels": {"y": "Measurement (units)"},
  "formats": ["pdf", "svg", "png", "tiff"]
}
```

Unit IDs are read as strings, retaining IDs such as `001`. Each unit must have
exactly one finite measurement in every declared condition. Duplicate technical
replicates, missing visits, empty IDs, and incomplete trajectories fail with a
specific error. Aggregate technical repeats upstream according to the adopted
scientific definition. For incomplete longitudinal data, choose a recipe that
explicitly represents missing visits; this complete-observation recipe does not
drop a participant or invent a value.

`order.condition` must list all observed conditions exactly once. Without an
explicit order, first appearance in the input defines it. Three or more repeated
conditions are supported and tested; connectors link successive declared
conditions for the same unit. The tool does not infer unequal time intervals:
conditions occupy discrete equally spaced slots. Use an explicit numerical-time
trajectory recipe when elapsed-time distances carry meaning.

## Optional independent groups

Add `fields.block` for mutually exclusive groups, for example prior-infection
classification. Each unit ID must belong to one block. When two separate studies
reuse numeric IDs, namespace them explicitly before combining their rows.
`order.block` lists every observed block once, and each block must contain the
same complete set of repeated conditions.

```json
{
  "fields": {
    "unit": "person", "condition": "visit", "value": "measurement", "block": "cohort"
  },
  "order": {"condition": ["Before", "After"], "block": ["Group A", "Group B"]},
  "colors": {"Group A": "#D55E00", "Group B": "#0072B2"},
  "legends": {"categorical": {"position": "bottom", "ncol": 2}}
}
```

Merge this fragment into a complete spec. Colors encode blocks and their guide
uses the shared measured legend manager. Without blocks, `options.point_color`
controls the single point color and no categorical legend is needed. A mapping
must cover every block with distinct visible colors; colors are never cycled.
`block_gap` is additional space between groups in condition-slot units, default
0.4, allowed 0–2. The source-driven Urschel case uses 0 because its published
reference has four evenly spaced positions.

## Summaries and display scales

Each condition has a black median line, a vertical Q1–Q3 segment, and shorter
quartile caps. `quantile_method` is either `linear` (Hyndman–Fan type 7, default)
or `weibull` (type 6). The method is saved explicitly. Compute Q1, median, and Q3
from raw measurement values even with `y_scale="log"`; the logarithm transforms
only the display axis. This distinction matters for even sample sizes.

Log display requires strictly positive measurements and positive `y_limits` and
`y_ticks`. No pseudocount, zero substitution, or censoring value is introduced.
Linear display permits zero and negative finite measurements. Optional limits
must contain every value; actual marker-edge clipping is checked after drawing.
An interval at the edge can still fail because a point has physical radius.

Source captions often specify IQR without naming a quartile estimator. Adopt and
record one rule; do not claim it is the author's unstated rule. The Urschel case
uses Weibull, notes a small difference from one reported rounded IQR, and performs
no significance tests. Source significance labels require separately adopted
source provenance or a justified upstream analysis.

## Point placement and connectors

`point_layout="swarm"` places equal-area circles in deterministic horizontal
positions using their vertical distance and physical circle size, after the
fixed-size canvas and legend have been fitted. Reordering rows or renaming role
columns does not change placement when category order, IDs, values, and seed
are retained. If every point cannot fit inside `point_spread`, the run fails;
the tool does not shrink markers, drop rows, or silently fall back to jitter.

`point_layout="jitter"` uses a deterministic offset from block, unit ID, and
`seed` (integer 0–2³²−1). That offset is shared across a unit's repeated conditions.
It retains all observations but does not guarantee points are separated.
`point_spread` defaults to 0.7 and must be greater than zero and at most 0.9 slot
units. Review actual dense regions at final size.

`point_area_pt2` is geometric circle fill area, default 10 pt²; the Matplotlib
size parameter is `4/π × area`. Default points have no outline. For an adopted
reference, `point_edge_width_pt` and `point_edge_color` can add a thin explicit
outline. Categorical keys inherit the points' fill opacity, outline color and
stroke width; keep any explicit guide override consistent with that policy.
`point_alpha` must be greater than zero and at most one.

`connect_pairs=true` adds consecutive within-unit segments behind points and
summaries. `pair_line_width_pt` defaults to 0.4 and `pair_alpha` to 0.18. All
segments use the actual point positions and retain each adjacent condition;
path simplification is disabled. A paired study does not automatically imply
that the published plot used connectors. The Urschel `connectors-spec.json`
is an explicitly added data view, while its reference-derived default is
unconnected. Review crossings and summary visibility before adopting a dense
connector view for a manuscript.

Other explicit style settings are `summary_color`, `summary_width` (default
0.7 slot units), `summary_cap_width` (0.22), `summary_line_width_pt` (0.8), and
`grid` (false). Widths must fit inside their condition slot, and quartile caps
cannot be wider than the median line. Grid lines draw below primary marks.
The tool accepts axis labels and data-reading guides; narrative belongs in the
separate caption.

## Outputs and evidence

The same fixed-canvas font/export/layout helpers used by the core renderer
produce PDF, text-preserving SVG, PNG, and TIFF. Default size is 88 × 88 mm and
default typography 8 pt; automatic fitting never reduces font or canvas size.
Manual `layout.margins` remain available. Record any font substitution and adopt
the actual installed font explicitly when needed.

- `plotting-data.csv`: all input rows, source-row indices, actual x positions,
  circle area and Matplotlib size parameter.
- `summary-data.csv`: block, condition, biological-unit count, Q1, median, Q3,
  and IQR width, computed from raw measurements.
- `settings.json`: adopted spec, final dimensions/fonts, category colors,
  placement rule, quantile definition, source/script/helper hashes, and runtime.
- `stats.json`: descriptive rule and complete-unit count, with no test performed,
  no inferred pairing, and no missing measurement filled.
- `qa.json`: source values compared to actual point positions, all rows checked
  once, summary endpoints, connector identities and endpoints, circle size,
  marker clipping, labels, guides, export dimensions, and post-export source
  identity. A failed or unfinished attempt has `valid_outputs=false`, even if
  older exports remain in that directory.

These checks cover numerical and layout integrity; they do not replace viewing
the actual panel. The reference reading and final aesthetic review must still
describe source deviations, dense regions, and readability at the adopted size.
