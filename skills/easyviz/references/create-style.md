# Create colors and stroke hierarchy

A create panel needs distinct, readable marks as well as a correct chart.
Choose mark treatment, category colors and line roles on the actual data, then
inspect the export at its final physical size. These are adjustable EasyViz
starting values, not journal rules or evidence of publication quality.
Reproduce follows its adopted reference and user settings; do not insert a
create style into an accepted reproduction.

Refine the basic chart before composing extra tracks. A small palette, definite
edges and well-sized data region can improve a single scatter or bar without
adding a statistic, label or annotation. Use additional layers only to answer
an adopted reading task.

For a crisp literature-inspired design, read the specific mechanisms in
[PROGENy, scWAT and Vanneste](literature-style.md). Avoid turning "light" into
low-opacity data, pale structural lines and unused plotting space. Clean
boundaries, visible category identity and organized density can coexist.

## Color decisions

- Use a complete `colors` mapping or an explicit categorical `palette` for
  groups. Give the same group the same color across related panels and guides.
  Two informative hues are often clearer than using every catalog color. Check
  the whole combination, including adjacent fills and legend keys; vivid marks
  can stay bright without turning every layer into a different saturated hue.
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

For example, a two-group panel can adopt the observed scWAT blue/coral pair:

```json
{"colors": {"Discovery": "#55A0FB", "Replication": "#FF8080"}}
```

The PDF vector colors are observed; assigning them to these group labels is an
EasyViz design choice. It is not a required default. Compare the pair with the
actual density, background and guide keys. Preserve
supplied values, marker areas, limits and agreed font sizes while refining
contrast. The [palette catalog](palettes.md) records color provenance; adoption
on one panel does not establish suitability on another. Neutral gray can serve
a background or metadata role; it should not mute every meaningful category.

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
number used only for hollow points. The hollow edge follows the actual group
color. A fixed-size `scatter` can use the same observation treatment. Scatter
with `fields.size` rejects hollow marks/edge-width overrides because its circle
fill area is quantitative. Dot-matrix area encoding is unchanged.

`box_style` accepts `filled` or `outline` for box distributions. An outline box
has an unfilled interior and keeps its whiskers, caps and median. A hollow
sample symbol does not mean an outline bar summarizes those samples correctly;
choose the summary from the data. Point size remains the existing squared
diameter parameter, not circle fill area. Physical point placement includes
the hollow stroke extent and reports unresolved crowding.

Use a hollow alternative with `point_style="hollow"` and
`point_edge_width_pt=0.45` when an unfilled glyph improves separation. Check
summary crossings and the visible edge at final size before adopting it.

For a sparse categorical layout, `box_width` controls box thickness in category
spacing units (`0 < box_width <= 1`, original default 0.5). Inspect its physical
size after layout; a two-group chart can turn 0.5 into an unnecessarily thick
box. New drafts start at 0.18. This changes categorical thickness only; quartile
endpoints, whisker values, median and raw observations stay unchanged.

The shared `scripts/create_style.py` supplies missing cosmetics for new
unprofiled drafts and distribution previews. The default mode is `crisp`:
opaque filled observations, narrow outline boxes and the role widths below.
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

For `kind="violin"`, an explicit `violin_fill_alpha` in `[0, 1]` changes only
the KDE face and keeps its edge opaque. Omission preserves earlier behavior.
`violin_inner="box"` adds a hollow raw-value Q1–Q3 summary, with an optional
median controlled by `violin_median_visible` (default `true`). Its
`violin_inner_width` is category spacing (`0 < width <= 0.7`, default `0.12`),
independent of KDE density and sample count. This is an added statistical
summary layer; adopt it deliberately and define it in the caption.

The separate [replicate-bar recipe](replicate-plot.md) supports explicit
`bar_style="outline"` or optional edges on filled bars. Its bar settings are
not core `line_roles`. Compare fill and edge treatments with the actual raw
layer rather than making every basic chart hollow.

## Basic chart checks

| Chart | Useful design decision | When to choose another treatment |
| --- | --- | --- |
| Scatter | Keep group identity visible in the actual point field; make any adopted fit distinct from points and reference guides. | Dense overlap may need hollow glyphs, modest transparency or facets. Compare actual density; do not fade a sparse cloud by habit. |
| Bar | Set fill/edge treatment, bar thickness and category gaps together. Make an adopted interval visible against the bar and any raw points. | Open bars help when they reveal a raw layer; a filled bar can be clearer when height alone is the evidence. Styling does not define the summary or uncertainty. |
| Box and points | Keep quartile boundaries and median legible; inspect point/whisker crossings and physical box thickness. | Separate the summary and raw layer into neighboring lanes or facets when marks mask each other. An outlined box is a starting choice, not a reason to shrink every point. |
| Violin | Make the density boundary, any adopted box/median and raw points distinct. | Shape adds little for sparse or discrete groups; use box/points when KDE would suggest unsupported detail. |
| Heatmap | Choose a justified scale and readable cell proportions. Subtle cell seams can identify large cells; keep the colorbar interpretable in original units. | Framing every tiny cell can overwhelm a dense matrix. A diverging map needs a declared center, not merely two signs or a desire for more colors. |

Measure the space needed by category labels and legend keys, then give the rest
to the data. Inspect within-group gaps, between-group gaps and outer margins
separately. Reducing a legend should release usable plot space rather than
leave its oversized empty band in place. For repeated categories, adjacent
group lanes and aligned facets are alternatives; preserve unit correspondence
when it is part of the question.

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

The [five runnable basic panels](../assets/cases/basic-panels/README.md) show
these decisions on real data and preserve matched-spec comparison records in
the development repository. Use their contracts and adjustable settings, not
their biological names or scientific assumptions, on a new input.

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
