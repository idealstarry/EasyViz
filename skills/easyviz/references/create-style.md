# Create colors and stroke hierarchy

A create panel needs an explicit visual hierarchy as well as a correct chart.
Choose category colors and line roles on the actual data, then inspect the
export at its final physical size. These are adjustable EasyViz starting values,
not journal rules or evidence that a figure has reached publication quality.
Reproduce follows its adopted reference and user settings; do not insert a
create style into an accepted reproduction.

## Color decisions

- Use a complete `colors` mapping or an explicit categorical `palette` for
  groups. Give the same group the same color across related panels and guides.
  Two informative hues are often clearer than using every catalog color.
- Use a sequential `colormap` for magnitude. Its palest end must remain visible
  for borderless dots; compare `notch2-blue` on low-value dots when appropriate.
- Use a diverging scale only around a declared meaningful center. A striking
  color range is insufficient justification for a zero-centered scale.
- Keep raw filled circles and bars borderless. Use line color for curves,
  intervals, outlines of distribution summaries or declared reference lines;
  a stroke does not establish a new categorical mapping.

For example, the revised cohort-effect case explicitly adopts blue and coral:

```json
{"colors": {"Discovery": "#287A9E", "Replication": "#CC7358"}}
```

This pair is an EasyViz design choice, not recovered author colors or a
required default. Compare it with the actual density, background and guide keys. Preserve
supplied values, marker areas, limits and agreed font sizes while refining
contrast. The [palette catalog](palettes.md) records color provenance; adoption
on one panel does not establish suitability on another.

## Explicit line roles in core charts

The five-family core renderer accepts an optional `line_roles` object:

```json
{
  "line_roles": {
    "data": {"line_width_pt": 0.85},
    "summary": {"line_width_pt": 0.75},
    "reference": {"line_width_pt": 0.45, "color": "#A1A1A1", "linestyle": "--"},
    "axis": {"line_width_pt": 0.55, "color": "#555555"},
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

1. Check that the intended comparison is seen before axes and auxiliary guides.
   Use a grid only when it materially improves reading values; a pale grid can
   still create unwanted visual bands in a matrix or categorical panel.
2. Check actual thin strokes and the palest marks at final size. Strengthen an
   essential reference if it disappears; do not compensate with extra outlines
   around every filled point.
3. Keep line patterns legible and semantically consistent. A solid fitted curve,
   lighter reference and quiet axes should remain distinct in export.
4. Verify group-color consistency, intact source rows, statistics, dimensions
   and exports. Technical QA covers those checks only where supported; image
   inspection remains necessary for aesthetics and scientific readability.

The workbench maps core regression, distribution and supplied reference widths
to their effective spec paths. Saved cosmetic requests still require an Agent
to apply the source/spec change and rerender; they do not edit exported PDF/SVG
bytes in place.
