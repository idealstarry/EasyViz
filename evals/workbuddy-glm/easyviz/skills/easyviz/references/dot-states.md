# Dot-matrix data states

Dot area represents a quantity. A missing coordinate, a measured zero and a small positive value must retain different meanings even when their quantitative dots look blank at the final panel size.

| Source state | Representation | Meaning |
| --- | --- | --- |
| Observed positive | Exact proportional dot | Area remains `size / size_max × max_area_pt2`. |
| Observed zero | Zero-area dot with a grey horizontal tick | A real zero, not an absent measurement. |
| Explicitly unmeasured | Grey cross; empty size and color fields | The source explicitly says no measurement exists. |
| Coordinate absent from the table | Grey plus by default | Not supplied; absence alone does not establish that it was unmeasured. |
| Very small observed positive | Exact dot with an optional grey side tick | A presence flag, independent of the unchanged quantitative dot area. |

For a table with an explicit availability column, map `fields.state` to it. Its values are `observed` and `unmeasured`. Observed rows require finite numeric size/color values; unmeasured rows require genuinely empty size/color cells. Do not label a supplied numeric zero as unmeasured. The exported plotting table retains every supplied row, availability state and quantitative area; absent coordinates are listed separately in QA.

`options.missing_cells` is `unsupplied` by default. Use `unmeasured` only when the scientific source or user establishes that all absent combinations were unmeasured. Use `error` to require a complete declared matrix. Existing x/y category ordering still includes every supplied category exactly once.

`options.state_markers` defaults to `true`. The separate state-symbol legend decodes the glyphs; it does not redefine the size legend or color scale. A caller that explicitly disables markers must provide another readable distinction and review the resulting panel.

`options.small_positive_area_pt2` is an optional nonnegative area threshold, with `0` disabling the presence flag. For example, `1` flags positive dots below 1 pt² with a side tick. This threshold is a display decision, not a detection limit or biological cutoff. Inspect it at the agreed final size and record it in settings and the separate caption. State-only matrices omit quantitative guides rather than invent measurements or a scale.

Copy the [state fixture](../assets/fixtures/dot-states/) to a writable directory and render its `data.csv` with `spec.json`. This is synthetic engineering data, not a biological study. The shared [figure profile](figure-profile.md) can fix size/color limits across related panels.
