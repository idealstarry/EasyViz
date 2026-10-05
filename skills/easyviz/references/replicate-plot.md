# Replicate bars and stacked components

Use `scripts/replicate_plot.py` when prepared data contain replicate observations for each condition, with optional components. This recipe adds raw observation layers and explicit sample SD to grouped or stacked means. It also plots supplied scalar values, such as precomputed ratios, without deriving them from other columns.

```bash
python /absolute/path/to/easyviz/scripts/replicate_plot.py \
  --data /absolute/path/to/project/observations.csv \
  --spec /absolute/path/to/project/replicate.json \
  --out /absolute/path/to/project/replicate-output
python /absolute/path/to/easyviz/scripts/replicate_plot.py --describe-spec
```

Resolve the runtime and all input/output paths explicitly. Agent shells can
reset their working directory; a fresh output directory prevents overwriting
an accepted attempt. Check renderer/input hashes in `settings.json` and copy
installed cases into a writable project before use.

Keep `render.py`, `legend_layout.py`, `auto_layout.py`, `figure_profile.py`, `annotation_review.py`, `figure_elements.py` and `panel_readability.py` beside the script. Preserve the skill's `assets/palettes` directory for named palettes, or provide complete explicit colors when copying the runtime alone.

## Choose the quantity first

| Mode | Required roles | Bars | Raw points and SD |
| --- | --- | --- | --- |
| `stacked` | condition, unit, component, value | Mean component values, stacked in the specified component order | **Per-unit total** across all components; one interval per condition |
| `grouped` | condition, unit, component, value | Separate means for each component | Component's own supplied observations and SD |
| `summary` | condition, unit, value | Mean of the supplied scalar values | Those same supplied scalar values and SD |

Stacked totals are computed within each unit before calculating SD. Adding component SDs or using the SD of group means is incorrect for this quantity. The grouped view exposes component-specific variability directly. If the source does not establish which quantity an original stacked error bar represents, record that uncertainty and adopt an explicit quantity; do not claim an exact reproduction of its interval layer.

## Source contract

- Map `fields.condition`, `fields.unit` and `fields.value` to distinct source columns; `fields.component` is required for stacked/grouped and rejected for summary.
- Within each condition, a unit has one value per component. Every supplied unit must have the full same component set. A missing component is rejected rather than treated as zero. Zero values remain observations.
- Component values are never normalized. Stacking requires nonnegative values; grouped/summary support signed numerical observations.
- Unit IDs identify prepared rows. The renderer does not establish biological independence, matched conditions or experimental design. State those in the caption using supplied evidence. A replicate ordinal reused across conditions does not create a paired design.
- `uncertainty: "sample_sd"` computes sample SD with `ddof = 1` and requires at least two units in every condition. `"none"` draws no interval and supports single-unit conditions. No SEM, confidence interval or hypothesis test is inferred.
- For ratios, map `value` to the precomputed per-unit ratio. The recipe does not divide component means or derive ratios from other fields.
- `fields.state` is optional only for summary. Each condition must have one supplied state across its units. Provide a complete `options.state_hatches` map with distinct patterns, for example `{"interpretable": "", "uninterpretable": "///"}`. Optional `labels.states` supplies complete readable guide labels. All values remain plotted.

## Compact specification

```json
{
  "chart": "replicate",
  "fields": {"condition": "condition", "unit": "sample", "component": "component", "value": "percent"},
  "options": {"mode": "stacked", "uncertainty": "sample_sd", "bar_width": 0.6, "marker_area_pt2": 7, "x_rotation": 45},
  "order": {"condition": ["Control", "Treatment"], "component": ["A", "B"]},
  "colors": {"A": "#0072B2", "B": "#D55E00"},
  "labels": {"y": "Cells (%)"},
  "layout": {"width_mm": 130, "height_mm": 90, "font": "Arial", "font_size_pt": 8, "dpi": 300, "auto_fit": true},
  "legends": {"categorical": {"position": "top", "ncol": 2}},
  "formats": ["pdf", "svg", "png", "tiff"]
}
```

`bar_width` is the total occupied fraction of one condition spacing (`0 < width <= 0.85`); grouped components share that width. Raw point offsets depend on sorted unit IDs, so reordering rows does not move observations. `marker_area_pt2` is geometric circle fill area; marks are filled and borderless. The circle's Matplotlib size is `4 / pi × area`.

Optional `point_color`, `bar_color`, `grid`, `y_limits` and `y_ticks` provide explicit styling. Component colors map component names; optional summary colors map condition names. Conditions use their axis labels rather than a redundant color guide. A state guide decodes hatching. Explicit limits must contain every observation, bar baseline and SD endpoint; geometry QA also rejects clipped point glyphs. Do not reduce font sizes to force a crowded panel to fit.

For outlined bars, set `bar_style: "outline"`, optionally
`bar_edge_width_pt` and `bar_edge_color`. The interior is unfilled and raw
observations, means, stacked bases and SD endpoints are unchanged. The edge
color defaults to the original bar/category color. An explicitly bordered
filled bar uses `bar_style: "filled"` with a positive `bar_edge_width_pt`.
Omitted settings retain the earlier borderless filled treatment. Component
legend keys match the selected treatment. These settings support all three
modes; outline bars with state hatching are rejected because removing the fill
would obscure the adopted state encoding. Different component colors should
remain distinguishable when a common edge color is adopted.

The [basic bar case](../assets/cases/basic-panels/README.md) demonstrates an
outlined summary with biological observations and sample SD. This treatment
is optional and does not define which summary or uncertainty is appropriate.

## Review and reuse

The renderer exports a fixed canvas plus `plotting-data.csv`, `summary-data.json`, `settings.json`, `stats.json` and `qa.json`. QA rereads the source independently, checks actual bar means/bases, SD endpoints, raw-point coordinates, categories, colors and declared hatches, and measures font/canvas/guide clipping. Failed runs set `valid_outputs: false`, including when stale exports remain on disk. Numeric QA does not establish aesthetic quality; inspect the actual exported image and use an independent figure review.

The mapped measurement is parsed numerically for means, SD and positions.
`plotting-data.csv` retains the exact original decimal spelling separately
in `_easyviz_source_value_text`; numeric serialization may normalize that
spelling. Keep the original source file and source-cell references as well.

[Truong components case](../assets/cases/truong-components/README.md) uses 84 real numerical values from a Nature Methods Source Data workbook. Its stacked view uses total points/SD, its separate ratio panel retains source-declared uninformative controls, and its grouped alternative shows each component's raw observations/SD. These are disclosed create adaptations of the source figure, rather than additional published panels.
