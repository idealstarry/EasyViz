# Create colors and stroke hierarchy

A create panel needs distinct, readable marks as well as a correct chart.
Choose mark treatment, category colors and line roles on the actual data, then
inspect the export at its final physical size. These are adjustable EasyViz
starting values, not journal rules or evidence of publication quality.
Reproduce follows its adopted reference and user settings; do not insert a
create style into an accepted reproduction.

For a crisp literature-inspired design, read the specific mechanisms in
[PROGENy, scWAT and Vanneste](literature-style.md). Avoid turning "light" into
low-opacity data, pale structural lines and unused plotting space. Clean
boundaries, visible category identity and organized density can coexist.

## Color decisions

- Use a complete `colors` mapping or an explicit categorical `palette` for
  groups. Give the same group the same color across related panels and guides.
  Two informative hues are often clearer than using every catalog color.
- Use a sequential `colormap` for magnitude; it may span more than one hue.
  Its palest end must remain visible
  for borderless dots; compare `notch2-blue` on low-value dots when appropriate.
- Use a diverging scale only around a declared meaningful center. A striking
  color range is insufficient justification for a zero-centered scale.
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

For a fixed-size core `distribution`, an explicit open treatment is:

```json
{
  "options": {
    "kind": "box", "box_style": "outline",
    "point_style": "hollow", "point_edge_width_pt": 0.45,
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

For a sparse categorical layout, `box_width` controls box thickness in category
spacing units (`0 < box_width <= 1`, original default 0.5). Inspect its physical
size after layout; a two-group chart can turn 0.5 into an unnecessarily thick
box. New drafts start at 0.18. This changes categorical thickness only; quartile
endpoints, whisker values, median and raw observations stay unchanged.

New drafts without an adopted profile use opaque filled observations and
narrow outline boxes for distribution. Hollow points remain an explicit option,
not a required aesthetic. Existing
specifications keep their old fallbacks. These starting choices need image
review. When an open mark cannot fit or is too weak at final size, compare a
clear filled treatment or aligned facets before fading it. Any size/layout
change must be explicit; packing must not jitter the numeric coordinate.
When a whisker crosses a hollow observation, consider an opaque filled glyph
or a separate summary lane; exposing the crossing is not automatically cleaner.

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
| `summary` | Box outlines, whiskers, caps and medians. |
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

New drafts without a shared profile write the example starting hierarchy.
Profile-based drafts preserve the adopted shared strokes. Focused recipes use
their own declared curve, interval, paired-connector and summary options; do
not add core `line_roles` to a focused spec unless that recipe documents it.
Colorbar frames and legend keys retain their existing guide contract.

## Review the result

1. Check that the intended comparison is seen before auxiliary decoration.
   Use a grid only when it materially improves reading values; a pale grid can
   still create unwanted visual bands in a matrix or categorical panel.
2. Check actual thin strokes, hollow interiors and the palest marks at final
   size. Strengthen the specific layer that disappears; avoid reducing all
   widths/opacity together. A dark thin axis can be clearer than a pale one.
3. Keep line patterns legible and semantically consistent. A solid fitted curve,
   dashed reference and definite axes should remain distinct in export.
4. Verify group-color consistency, intact source rows, statistics, dimensions
   and exports. Technical QA covers those checks only where supported; image
   inspection remains necessary for aesthetics and scientific readability.

For a signed matrix, show the meaningful center on its guide and inspect
negative, near-zero and positive regions separately. An asymmetric diverging
normalization has different scale slopes on its two arms: record forward and
inverse mapping instead of calling it one linear range. For a selected matrix,
metadata and marginals must use the same identifier order and declare whether
their summaries refer to the displayed subset or complete data.

The workbench maps core regression, distribution and supplied reference widths
to their effective spec paths. Saved cosmetic requests still require an Agent
to apply the source/spec change and rerender; they do not edit exported PDF/SVG
bytes in place.
