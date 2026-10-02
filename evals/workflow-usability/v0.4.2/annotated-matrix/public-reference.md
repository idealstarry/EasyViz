# Annotated matrices and aligned layers

Use this focused recipe when a scientific panel combines a continuous matrix,
keyed categorical strips, marginal summaries or a **supplied** dendrogram.
It accepts prepared data and preserves explicit ordering. It performs no
clustering, normalization, model fitting or upstream bioinformatics analysis.

```sh
python /path/to/easyviz/scripts/annotated_matrix.py --describe-spec
python /path/to/easyviz/scripts/annotated_matrix.py \
  --data matrix-long.csv --spec panel.json --out output \
  --row-metadata rows.csv --column-metadata columns.csv \
  --row-linkage row-linkage.json --column-linkage column-linkage.json \
  --track reproduce
```

The metadata and linkage flags are optional and must be paired with their
corresponding specification entries. The track records provenance; it does
not infer a chart from the data. CSV files have unique, nonempty headers and
exact-width rows. IDs and categorical values remain literal strings: `001`,
`NA`, `null`, and whitespace-bearing IDs are preserved. Duplicate row/column
pairs fail; aggregate explicitly before calling the renderer.

## Input contract

```json
{
  "chart": "annotated_matrix",
  "fields": {
    "row": "sender", "column": "receiver",
    "value": "signal", "state": "measurement_state"
  },
  "order": {"row": ["001", "NA"], "column": ["B", "A"]},
  "options": {"missing_cells": "unsupplied", "color_limits": [-2, 5]},
  "metadata": {
    "row": {"id": "strain_id", "tracks": [
      {"field": "group", "label": "Group",
       "colors": {"Control": "#0072B2", "Treatment": "#D55E00"}}
    ]}
  },
  "marginals": {
    "row": {"statistic": "mean", "missing": "omit", "label": "Mean signal"}
  },
  "dendrograms": {"column": {"label": "Supplied distance"}},
  "tracks": {"strip_mm": 2, "marginal_mm": 14, "dendrogram_mm": 14, "gap_mm": 2},
  "labels": {"x": "Receiver", "y": "Sender", "color": "Signal (a.u.)"},
  "layout": {"width_mm": 120, "height_mm": 100, "font": "Arial", "font_size_pt": 8, "dpi": 300},
  "formats": ["pdf", "svg", "png"]
}
```

`order.row` and `order.column` are required lists of literal strings. Each
lists every ID present in its source dimension exactly once, without extras.
The long matrix may be rectangular. Row zero is at the top, column zero at
the left; integer centers and half-integer cell boundaries are shared by all
tracks. Source field names, ID spelling, record order and category counts can
change without changing the plotting implementation.

`fields.state` is optional. Without it, every supplied row is observed. With
it, values must be `observed` or `unmeasured`. Observed cells require finite
numeric values, including zero. Unmeasured cells require an **exactly empty**
value. `NA`, spaces and zero cannot stand in for an unmeasured value. Absent
coordinates fail by default; `options.missing_cells="unsupplied"` retains them
as a distinct nonnumeric state. Cross/plus hatches and decoded guide keys
distinguish the two missing states from quantitative colors. A missing source
row never establishes an attempted measurement. At least one observation is
required to establish the continuous scale.

Metadata files join one-to-one on their configured ID field and must cover
the displayed axis exactly. No source-order joining, dropped extra IDs or
missing annotation fills occur. Each strip has a field, decoding label and
explicit stable category-to-color mapping; colors never cycle. Unused
categories in a supplied color mapping remain in its guide. Each axis can
have several metadata tracks; their fields must be distinct. Track-qualified
semantic keys and color pointers avoid confusing the same category name in
two different annotations.

Marginals support `mean` and `sum` across the **displayed grid**, with an
explicit `missing="error"` or `missing="omit"`. Omit excludes unmeasured and
unsupplied cells, records both omission counts and observed denominators,
and fails for an all-missing group. Sum does not treat missing values as
measured zero. `marginal-data.csv` records each value, statistic, rule,
observed count and full displayed-grid count. Optional limits must include
every bar and its zero baseline; negative values remain negative.

## Supplied linkage

```json
{"leaf_ids": ["A", "B"], "linkage": [[1, 0, 2.5, 2]]}
```

Leaves are indexed by `leaf_ids`. Merge row `i` receives index `n+i` and is
`[left_child, right_child, height, recursive_leaf_count]`. Child indices and
counts are JSON integers, excluding booleans. There are exactly `n-1`
merges, children precede parents, each non-root node is used exactly once,
and recursive counts must match. Heights are finite and nonnegative;
parents cannot be lower than their children. Independent merges need not be
globally height-sorted. Inversion-bearing trees are outside this contract and
fail explicitly. Leaf IDs have exact coverage, and the complete left-to-right
traversal must equal the displayed order. The example therefore requires
displayed columns `["B", "A"]`. No automatic child swaps or reordered axes
occur. Singleton trees use empty linkage, and zero-height trees retain zero
geometry with a deterministic 0–1 display axis. The height label declares the
meaning/units supplied upstream.

## Reusable alignment API

The CLI is a convenience entry point. Custom scripts can import
`aligned_layers.py` independently and draw new scientific primitives on the
returned axes:

```python
frame = AlignedFrame(fig, row_ids, column_ids, [20, 20, 60, 50], gap_mm=2)
top = frame.add_track("column-summary", "column", 12)
right = frame.add_track("row-annotation", "row", 3)
# Draw on frame.main, top and right in their own value dimensions.
frame.reshape([22, 24, 56, 46])  # all categorical spans move together
report = frame.audit()           # inspect actual rendered centers and spans
```

`add_aligned(key, dimension, rect_mm)` also supports a custom manually placed
track whose shared span exactly equals the matrix span. `supplied_linkage()`
validates and returns reusable branch vertices without plotting or clustering.
The focused recipe also exposes `prepare()`, `draw()` and
`audit_source_artists()` for reviewed custom scripts. Additional custom layers
need their own source-to-artist checks and must participate in the custom
layout envelope; calling the helper does not certify unregistered artists.

## Final layout, exports and evidence

Automatic layout measures the union of matrix, track and label envelopes,
moves all aligned axes together, and uses the existing measured guide checks.
It preserves final width, height and every font size. `tracks.matrix_mm` gives
explicit matrix geometry and requires `layout.auto_fit=false`; explicit
`layout.margins` is an alternative. Manual guide coordinates also require an
explicit layout. Conflicting or unknown settings fail before plotting.
Unsupported or infeasible content fails with `valid_outputs=false`, retaining
the preview when one could be rendered. It never shrinks fonts, crops exports,
drops IDs or recomputes the supplied tree to fit.

The current per-cell SVG/semantic implementation supports at most 10,000
cells. Larger raster matrices require an explicitly reviewed custom script.
Cell aspect follows the allocated rectangle; square cells are not inferred.
Optional value annotations are checked against their actual cell bounds.
The recipe omits in-image titles and narrative; it writes a separate
`caption.md` describing the declared measurements, missing states, joins,
marginal population and supplied-tree scope.

Outputs include full-canvas panels, `plotting-data.csv` retaining source rows
and unused fields, complete `matrix-cells.csv`, `marginal-data.csv` when used,
`artist-values.csv`, `settings.json`, `stats.json`, `elements.json` and
`qa.json`. Settings and the element map record paths and hashes for the
matrix, metadata and linkage inputs. Stable semantic IDs identify cells,
strip cells, marginal bars, tree branches, axes and guide keys across a
source record reorder. IDs follow literal keys rather than numeric positions.

The executed audit re-reads all sources and checks encoded cell colors,
missing-state patterns and cell bounds; keyed strip colors/bounds; marginal
bar values, baselines and centers; supplied branch vertices; and actual
transformed track alignment within 0.01 mm. A passed check establishes those
relationships, not upstream scientific validity or visual quality. Inspect
the final PNG/PDF, the complete guide footprint and font readability at the
recorded size before delivery. A machine pass still records
`visual_review_required=true`.
