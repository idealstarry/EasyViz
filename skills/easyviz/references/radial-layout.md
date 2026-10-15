# Layout helpers for supplied radial graphics

Use `scripts/radial_layout.py` from custom plotting code when a supplied
hierarchy or another circular graphic needs ordered annotation bands or
crowded-label placement. The module uses the standard library. It does not
parse/infer a tree, change its branch lengths, assign colors or export a figure.
Keep the adopted scientific geometry in your plotting implementation.
Declare this imported helper as a consumed code dependency in the custom
[source handoff](figure-workbench.md), alongside the plotting script and inputs,
so a later helper change invalidates the old output's source binding.

```sh
python /absolute/path/to/easyviz/scripts/radial_layout.py --describe-contract
python /absolute/path/to/easyviz/scripts/radial_layout.py \
  --input /absolute/path/to/easyviz/assets/fixtures/radial-layout/runs.json
python /absolute/path/to/easyviz/scripts/radial_layout.py \
  --input /absolute/path/to/easyviz/assets/fixtures/radial-layout/labels.json
```

The two fixtures are synthetic layout inputs, not scientific data. The CLI
prints JSON and accepts `--input -` for stdin. Exit 0 means the operation is
ready, 1 means explicit capacity/review issues, and 2 means invalid input.
Neither a ready layout nor the CLI performs image review.

## Exact category intervals

```python
from radial_layout import merge_category_runs

bands = merge_category_runs(
    ["item-01", "item-02", "item-03", "item-04"],
    ["A", "B", "B", "A"],
    circular=True, start_angle_deg=90,
)
for run in bands["runs"]:
    # Draw a Wedge with these exact degree endpoints and the adopted palette.
    # A seam-spanning run may end beyond the first complete turn.
    print(run["category"], run["start_angle_deg"], run["end_angle_deg"])
```

IDs must be unique literal strings in the adopted order. Join metadata by ID
before calling this helper. It retains every per-item interval and run member;
only adjacent identical categories merge. `circular=True` requires exactly
360 degrees and allows first/last merging. A partial arc, gap or linear track
must use `circular=False`. Equal angular widths are an explicit contract; use
custom boundaries when item intervals have quantitative unequal widths.

Render a continuous run without repeated per-item borders only when this
serves the reading task. Adjacent wedges share computed boundaries; check the
actual vector/raster output for antialias seams. A same-category underlay can
cover raster hairlines when it preserves all class boundaries. Do not expand
every wedge into neighboring categories or add an arbitrary angular overlap.

## Bounded, balanced labels

`pack_labels_in_window(labels, window_deg=[low, high], radius_mm=...,
gap_mm=..., max_shift_deg=...)` minimizes total squared displacement while
preserving label order, occupied extents, the angular window and optional
movement limit. Input angles must already be nondecreasing and unwrapped,
for example 350, 355, 365 rather than silently sorting a circular seam.

Each label has `id`, `angle_deg`, and exactly one of `extent_mm` or `extent_deg`.
The extent is the adopted/measured occupied **tangential arc span**, not the
label's radial length or a character-count estimate. Measure actual rotated
text at the final font/size in the recipe. `extent_mm` is converted at the
specified radius. Inspect leaders and complete glyph bounds after rendering.

An infeasible request returns all IDs with null placed angles and a concrete
issue. Resolve the window, label arrangement or agreed capacity before using
coordinates. Do not fall back to silently clipped, deleted or reordered text.
The helper packs one open sector; it does not check first/last full-circle
collisions, actual text bounding boxes or leader intersections.

## Physical track and guide diagnostics

`radial_geometry(tree_radius_mm, tracks, label_radius_mm=...,
label_depth_mm=..., center_mm=[x,y], canvas_mm=[width,height], guides=...)`
reports each inner-to-outer track's `inner_radius_mm`, `width_mm`, gap, the
label envelope and optional guide rectangles. Guides use `id` and
`bbox_mm: [left,bottom,width,height]` in the same physical coordinate system.
The radial label depth is separate from the tangential label footprint above.

The result reports overlap/canvas issues without repairing coordinates or
declaring a preferred tree-to-ring ratio. A full-circle envelope is conservative
for partial arcs or sparse labels; review actual intersections. It cannot
infer internal-node density from terminal radius. Use
[Evidence before layout](evidence-first-create.md) to judge hierarchy,
continuous bands, focal colors and the branch-length/topology-only boundary.
