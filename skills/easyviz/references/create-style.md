# Create colors and stroke hierarchy

A create panel needs distinct, readable marks as well as a correct chart.
Choose mark treatment, category colors and line roles on the actual data, then
inspect the export at its final physical size. These are adjustable EasyViz
starting values, not journal rules or evidence of publication quality.
Reproduce follows its adopted reference and user settings; do not insert a
create style into an accepted reproduction.

Refine the basic chart before composing extra tracks. Decide whether readers
should see observations, a summary or density shape first, then set their
relative size, contrast and placement. A shared palette or line width cannot
make that decision. Use additional layers only to answer an adopted reading task.
The starting family may be a grouped bar or another genuine repeated comparison.
Compact repeated geometry makes its supplied relationships readable; it should
not remove relevant outcomes to resemble a minimal tutorial.

For a crisp literature-inspired design, read the specific mechanisms in
[PROGENy, scWAT and Vanneste](literature-style.md). Avoid turning "light" into
low-opacity data, pale structural lines and unused plotting space. Clean
boundaries, visible category identity and organized density can coexist.

## Color decisions

Choose which marks need categorical color before selecting hues. Use a complete
`colors` mapping or explicit `palette`, and keep its category assignments stable
across related panels. Raw observations and summary areas can have different
color roles when category positions still decode identity; guides must explain
the actual colored layer.

| Reading task and mark area | Candidate treatment | Check before adopting |
| --- | --- | --- |
| One quantity across x-labeled categories | Neutral filled or open bars, definite intervals and observations. PROGENy Fig. 2d and scWAT Fig. 3j use neutral marks. | Labels already identify categories; color each only if it communicates another adopted meaning. Gray must remain visible on white. |
| Two classes mixed in a scatter field | Distinguishable categorical hues on the actual small points, such as the eligible `scwat-blue-pink` pair. | Both classes remain recognizable in sparse and crowded regions; pale area colors may fail as tiny glyphs. Do not add a fit just because its source example has one. |
| Categories separated by distribution lanes | Category color on bounded box/inner-summary areas, graphite contours and optionally neutral observations; `progeny-summary` is one eligible area palette. | Position/labels and area color still identify groups, the median remains visible, and point keys do not falsely imply colored observations. Use the same map in related box/violin views. |

- Inspect the whole combination, including adjacent fills and legend keys. A
  useful bright pair in one scatter need not color a single-series bar or every
  boundary of a distribution. Neutral marks are an eligible data treatment,
  not solely a background or metadata role.
- Use a sequential `colormap` for magnitude; it may span more than one hue.
  Its palest end must remain visible
  for borderless dots; compare `notch2-blue` on low-value dots when appropriate.
- Use a diverging scale only around a declared meaningful center. A striking
  color range is insufficient justification for a zero-centered scale.
- For direct magnitude reading, begin with one globally linear sequential map
  over justified input bounds. Inspect the actual distribution before adding
  hues, unequal branches or hand-picked color stops. Preserve negative values;
  label zero without forcing it to the white midpoint. Explain any alternative
  normalization in original units, including its different slopes.
- Related mean tracks in the same units can share numeric limits when readers
  compare them. Include the zero baseline and every bar; check the range over
  both tracks. Different physical axis lengths still require reading the ticks.
- Choose one treatment per comparable mark role: borderless filled observations,
  group-colored hollow observations, or outlined distribution summaries.
  Match legend symbols. A stroke does not establish a new categorical mapping;
  a quantitative filled-area circle must not become a hollow ring implicitly.

The [palette catalog](palettes.md) records role eligibility and provenance.
Assigning a paper's colors to new labels or mark types is a design adaptation,
not a required default. Preserve values, marker areas, numeric scales and agreed
fonts when comparing treatments.
`progeny-summary` mixes observed inner-summary and KDE-area fills; applying
all four to cohort box/IQR areas is an adaptation, not that paper's original
four-group summary encoding.

## Crisp observation and summary options

For a fixed-size core `distribution`, the crisp starting treatment is:

```json
{
  "options": {
    "kind": "box", "box_style": "outline",
    "point_style": "filled",
    "alpha": 1, "point_layout": "beeswarm",
    "point_area_pt2": 9, "point_max_offset_mm": 4, "point_gap_pt": 0.3
  }
}
```

`point_style` accepts `filled` or `hollow`; the edge width is a positive finite
number used only for hollow points. By default, the hollow edge follows the
group color; a distribution's explicit `point_color` follows its adopted raw
role instead. A fixed-size `scatter` can use the same filled/hollow treatment. Scatter
with `fields.size` rejects hollow marks/edge-width overrides because its circle
fill area is quantitative. Dot-matrix area encoding is unchanged.

`box_style` accepts `filled` or `outline` for box distributions. An outline box
has an unfilled interior and keeps its whiskers, caps and median. A hollow
sample symbol does not mean an outline bar summarizes those samples correctly;
choose the summary from the data. Point size remains the existing squared
diameter parameter, not circle fill area. Physical point placement includes
the hollow stroke extent and reports unresolved crowding.

For core distributions, explicit `point_color` overrides raw-observation color
only; omission keeps the category colors. Use neutral points when categorical
position and colored summary areas already decode group identity. This does not
override scatter or dot-matrix color semantics. `box_fill_alpha` in `[0, 1]`
controls the face of `kind="box"` with `box_style="filled"` (default `0.22`);
the box edge and summary remain definite. Changing fill strength is independent
of raw-point opacity; an outline box has no face to tint. Observed pastel colors
are already light: an explicit `box_fill_alpha=1` can preserve their visible
area color rather than whitening it again. Compare the actual face on white.

Use a hollow alternative with `point_style="hollow"` and
`point_edge_width_pt=0.45` when an unfilled glyph improves separation. Check
summary crossings and the visible edge at final size before adopting it.

`box_width` controls box thickness in category spacing units
(`0 < box_width <= 1`, original default 0.5). New drafts start at 0.18;
this is a tunable starting value, not a physical-size target. With only a few
categories, filling the available axis can produce wide blank bands even with
narrow boxes. Choose the data-region width, category gaps and physical box
thickness together. This changes categorical geometry only; quartile endpoints,
whisker values, median and raw observations stay unchanged.

The shared `scripts/create_style.py` supplies missing cosmetics for new
unprofiled drafts and distribution previews. The default mode is `crisp`:
opaque filled observations, narrow outline boxes and the role widths below.
Adjust these roles when, for example, a violin outline competes with its
inner summary; the same stroke priority does not suit every family.
Explicit options and category colors remain adopted choices. Profile-based
drafts retain the existing profile without receiving these new defaults.

Use `draft_spec.py --style-mode legacy`, or `"style_mode": "legacy"` in a
preview request, to retain the earlier omitted-option fallbacks. Saved renderer
specifications keep their accepted behavior; opening one is not a style upgrade.
An explicit `layout.line_width_pt` keeps the existing global-width fallback
rather than receiving default role widths; explicit role widths still win.

These choices need image review. If a hollow glyph is weak or exposes a whisker
crossing, compare a filled glyph or separate summary lane. If packing fails,
make an explicit size/layout decision; numeric positions must stay intact.

For a distribution, `point_category_offset` moves the raw-point lane along
the categorical direction (`-0.4` to `0.4` category spacing, default `0`).
Use a nonzero value only when separation improves the adopted reading task;
beeswarm/jitter still needs room within the original category. Inspect the
association between each point lane and its summary. Numeric observations,
statistics and category identity do not move.

For `kind="violin"`, an explicit `violin_fill_alpha` in `[0, 1]` changes only
the KDE face and keeps its edge opaque. Omission preserves earlier behavior.
`violin_inner="box"` adds a hollow raw-value Q1–Q3 summary, with an optional
median controlled by `violin_median_visible` (default `true`). Its
`violin_inner_width` is category spacing (`0 < width <= 0.7`, default `0.12`),
independent of KDE density and sample count. This is an added statistical
summary layer; adopt it deliberately and define it in the caption.
An explicit `violin_inner_fill_alpha` in `[0, 1]` tints that inner box with the
category color; it requires `violin_inner="box"` and defaults to `0` (open).
This changes only its face, not quartiles, median, KDE or the observation layer.
An explicit `violin_inner_fill_alpha=1` is a candidate for an already-pale
summary palette; it does not require an opaque outer violin body.
`violin_width` adjusts displayed categorical width (`0 < width <= 1`, default
`0.7`); it does not alter KDE bandwidth or observed values. A narrow contour,
visible inner summary and optional neighboring raw lane can reduce competing
edges; these are candidate choices, not mandatory layering.

The separate [replicate-bar recipe](replicate-plot.md) supports explicit
`bar_style="outline"` or optional edges on filled bars. Its bar settings are
not core `line_roles`. Compare fill and edge treatments with the actual raw
layer rather than making every basic chart hollow.

For grouped outlined bars, adopt a visible `component_gap` in that recipe.
Neighboring outline strokes must not overwrite each other. Check actual stroke
clearance, within-group spacing, between-group spacing and physical thickness
after layout; a positive center gap by itself is insufficient. When outcomes
have very different ranges and the task is within-outcome treatment comparison,
consider narrow individual panels with repeated order and geometry. Label each
range explicitly and preserve fixed type size when arranging panels together;
different scales do not support absolute-height comparisons across panels.

## Basic chart checks

| Chart | Geometry and layer decision | Check on the actual export |
| --- | --- | --- |
| Scatter | Give the relationship a useful data-region aspect; preserve adopted equal-coordinate constraints. Let small observations carry identity, with an adopted fit stronger than reference guides. | Inspect both sparse and crowded areas, and the guide footprint. Hollow glyphs, modest transparency or facets can help dense overlap; do not fade a sparse cloud by habit. |
| Bar | Set bar thickness, within-group gaps and between-group gaps together. Keep interval endpoints and replicate marks readable at the bar top. | Open bars help reveal raw values; filled bars may serve height alone. Keep the zero baseline and full uncertainty extent. Do not fill spare width by enlarging bars or inventing annotations. |
| Grouped bar | Repeat the adopted series order and widths within each category, with a larger gap between categories and one decoded color assignment per series. Keep small replicate marks and honest uncertainty visible. | Readers should associate each series with its category without repeatedly searching the legend. A common axis requires comparable units and purpose; unrelated scales or unsupported stacking cannot be repaired cosmetically. |
| Box and points | Make median and quartile boundaries continuous. If points hide them, compare a narrow summary lane beside a raw-value lane within the same category. | Inspect numerical values unchanged, lane association clear, and points contained within their category. Choose lane width and group gaps from mark capacity; avoid huge blank bands or miniature boxes. |
| Violin | Use density shape only when it adds a reading task beyond box/points. For summary-first reading, make the KDE outline lighter than the inner box/median and keep its face unobtrusive. | A broad silhouette with points and an equally strong inner box has three competing layers. Adjust displayed width, strokes or categorical placement; never tune KDE bandwidth or remove observations merely for appearance. |
| Heatmap | Set the data-region aspect from row/column count and label needs. Three columns should not automatically fill a wide axis as horizontal ribbons. | Rectangular cells are valid; judge whether adjacent cells and columns remain distinct. Use visible but subordinate seams for large cells, less framing for dense tiny cells, and a readable colorbar in original units. |

Measure label and guide bounds, then choose a data rectangle suited to the
chart; all remaining canvas area need not become plotting width. At fixed
dimensions and fonts, resolve wrapping, label orientation, guide placement,
category spacing and inner-axis bounds before seeking a new canvas. Avoid
using wide gaps to disguise a point/summary collision. Retain every observation,
its numeric coordinate and any adopted pairing.

For core heatmaps, explicit `cell_border_color` and
`cell_border_width_pt` can make large cells distinct (default width `0`).
Choose the width at final size so seams remain subordinate to cell values.
`column_labels` supplies a complete real-category-to-display-label mapping
without changing category order or plotting data. Short aliases can fit a
narrow matrix; define unfamiliar abbreviations in the caption and retain the
original identifiers in the spec and exported table.

## Explicit line roles in core charts

The five-family core renderer accepts an optional `line_roles` object:

```json
{
  "line_roles": {
    "data": {"line_width_pt": 0.85},
    "summary": {"line_width_pt": 0.75},
    "reference": {"line_width_pt": 0.45, "color": "#747474", "linestyle": "--"},
    "axis": {"line_width_pt": 0.55, "color": "#222222"},
    "grid": {"line_width_pt": 0.30, "color": "#E8E8E8", "linestyle": "-"}
  }
}
```

| Role | Actual artists affected |
| --- | --- |
| `data` | Scatter regression stroke and violin outlines. |
| `summary` | Box outlines, whiskers, caps and medians; explicit violin inner boxes and their optional median lines. |
| `reference` | Supplied numeric scatter reference lines; their positions stay unchanged. |
| `axis` | Data-axis spines and tick strokes; text colors and sizes stay unchanged. |
| `grid` | Grid strokes only when `options.grid` is already `true`. |

Every property is optional. Widths must be finite positive JSON numbers. Colors
must be valid color strings. `linestyle` accepts `-`, `--`, `:` or `-.` for all
roles except `axis`. Unknown roles and properties are rejected. Pattern is a
reading cue: usually reserve dashed or dotted lines for a reference or a
scientifically distinct series. Role overrides do not enable a grid, infer a
reference threshold, run a test or add a new layer.

Absent properties retain their previous fallback. Existing specs without
`line_roles` render with their original settings, including their
`layout.line_width_pt` behavior. An explicit `options.regression_color` retains
precedence over `line_roles.data.color`. Category fills and observation colors
always retain `colors`/`palette`; a role color controls the affected strokes.
When summary color is absent, box edges keep category colors, medians keep
their existing dark color, and whiskers/caps keep their prior library fallback.

The [distribution preview helper](preview-choices.md) writes the same starting
hierarchy. Its ECDF uses `data.line_width_pt` for curves unless an explicit
`curve_line_width_pt` is supplied, and supports the `axis` and `grid` roles.
Category colors and solid empirical steps retain their meaning; other role
settings add no ECDF layer. Other focused recipes use their documented curve,
interval, connector and summary options. Do not add core `line_roles` to a
focused spec unless supported. Colorbar frames and legend keys retain their
existing guide contract.

## Review the result

The [runnable basic panels](../assets/cases/basic-panels/README.md) show
these decisions on real data and preserve matched-spec comparison records in
the development repository. Use their contracts and adjustable settings, not
their biological names or scientific assumptions, on a new input.

For an unresolved palette refinement, render two or three materially different
whole-panel candidates: the accepted treatment, a task-suitable area/point
alternative, and another justified option only if useful. Keep source rows,
statistics, numeric scales, canvas and fonts equal. Compare category decoding,
primary evidence, small-point contrast, adjacent areas and guide keys at final
size. Record the preference and tradeoff; neither brighter nor more neutral
automatically wins. Routine edits need no compulsory candidate set.

1. Check the complete palette and that the intended comparison is seen first.
   Use a grid only when it materially improves reading values; a pale grid can
   still create unwanted visual bands in a matrix or categorical panel.
2. Check actual thin strokes, hollow interiors and the palest marks at final
   size. Strengthen the specific layer that disappears; avoid reducing all
   widths/opacity together. A dark thin axis can be clearer than a pale one.
3. Check point/summary crossings, bar or box thickness, category gaps and the
   complete legend footprint. Enlarged inspection alone can hide weak strokes
   or an overlarge guide at the actual manuscript size.
4. Keep line patterns legible and semantically consistent. A solid fitted curve,
   dashed reference and definite axes should remain distinct in export.
5. Verify group-color consistency, intact source rows, statistics, dimensions
   and exports. Technical QA covers those checks only where supported; image
   inspection remains necessary for aesthetics and scientific readability.

For a matrix, inspect the low, middle and high portions of the actual data.
Show an adopted meaningful center on its guide when one exists. An asymmetric
diverging normalization has different scale slopes on its two arms: record
forward and inverse mapping instead of calling it one linear range. For a selected matrix,
metadata and marginals must use the same identifier order and declare whether
their summaries refer to the displayed subset or complete data.

The workbench maps core regression, distribution and supplied reference widths
to their effective spec paths. Saved cosmetic requests still require an Agent
to apply the source/spec change and rerender; they do not edit exported PDF/SVG
bytes in place.
