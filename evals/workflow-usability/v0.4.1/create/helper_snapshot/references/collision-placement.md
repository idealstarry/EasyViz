# Keep distribution observations readable

The core `distribution` renderer can place raw observation circles with a
measured beeswarm. Use it in either track when categorical jitter makes tied or
nearby observations hard to distinguish. Inspect the rendered panel before
adopting a layout change in reproduce: the arrangement must preserve the
reference's scientific encodings and the user's data.

```json
{
  "chart": "distribution",
  "fields": {"group": "condition", "value": "measurement"},
  "options": {
    "kind": "box",
    "orientation": "vertical",
    "point_layout": "beeswarm",
    "point_area_pt2": 9,
    "point_max_offset_mm": 4,
    "point_gap_pt": 0.3
  },
  "seed": 23
}
```

Add the agreed canvas, font, labels, colors and formats to this example. The
options apply to both box and violin summaries and both orientations. A violin
still requires nonconstant values and at least two observations per group.

| Option | Meaning |
| --- | --- |
| `point_layout` | `jitter` is the unchanged default; `beeswarm` opts into physical circle packing. |
| `point_max_offset_mm` | Maximum center displacement from the categorical position, in mm; default 4. Must be positive and requires `beeswarm`. The actual lane may be narrower to protect adjacent categories and axes boundaries. |
| `point_gap_pt` | Nonnegative requested edge gap between observation circles, in points; default 0.3. Requires `beeswarm`. |
| `point_area_pt2` | Existing Matplotlib `s` parameter, squared circle diameter; default 9 means a 3 pt diameter. It is not the geometric fill area. |
| `seed` | Replays symmetric choices and placement among equal values. Group labels also contribute to a recorded deterministic seed. |

Packing uses the final plot geometry after margins, optional measured layout,
explicit numeric limits and linear/log scales are resolved. It moves only the
categorical axis: x for a vertical distribution, y for a horizontal one.
Numeric values, all source rows, point sizes, canvas dimensions, typography and
statistical results stay fixed. The quantitative coordinate is never jittered.

The algorithm sorts observations by their displayed numeric position and
greedily selects the nearest available circle center. Each category has a
separate lane; circle edges stay inside its axes region. When the lane cannot
fit another circle, a deterministic 65-center grid selects a less crowded
fallback location. The observation remains in the plot and table. This is a
placement heuristic; it is not a density estimate or a guarantee that every
feasible packing will be found.

## Evidence and repair

`settings.json` and `qa.json` contain `point_layout`, including circle diameter,
gap, physical displacement bounds, each group's actual displacement, fallback
rows, unresolved circle-pair counts and up to 20 example pairs. Pair row numbers
are one-based parsed observations excluding the CSV header. Exact duplicate
centers retain their full pair multiplicity in the count.

`plotting-data.csv` retains source columns and records the categorical drawing
position in `_easyviz_jitter_position`. Beeswarm adds
`_easyviz_point_offset_pt`, the signed displacement in display points: positive
means right for a vertical plot and up for a horizontal plot. A reversed
categorical axis can therefore have a negative categorical-coordinate shift
for a positive display displacement.

Unresolved requested spacing or a categorical marker boundary violation gives
`needs_revision` and a failing render result. The attempted exports and complete
table remain available for review; they are not marked valid. Increase the
allowed displacement only when category separation permits it. Otherwise
explicitly enlarge/split the panel or choose another reading task, such as an
ECDF, retaining the raw-data deliverable. Keep the agreed font and point size.
Any change to mark size needs a separate explicit decision, not an automatic
packing shortcut.

Default `jitter` keeps the original seed-based positions and adds an
`unchecked` point-layout record; it does not claim collision-free output.
Circle spacing checks do not assess point-summary overlap, visual hierarchy,
text placement or reference fidelity. Both policies still require image review
at the agreed manuscript dimensions and a separate caption.

The reusable `pack_distribution_points` function in `render.py` accepts a
one-dimensional array of numeric display positions in points, circle diameter,
maximum categorical displacement, gap and seed. It returns displacements in
the original row order and fallback evidence. Custom scripts must recompute
placement after any axes/layout change and independently audit their rendered
circle centers with `distribution_collision_report`.
