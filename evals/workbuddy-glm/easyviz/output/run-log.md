# Run log — horizontal interval panel (prepared.csv)

Date: 2026-10-02. Track: **create** (chart type specified by user; no reference image).

## Command (rerunnable)

```sh
/Users/starry/Desktop/EasyViz/.venv/bin/python plot_scripts/interval_plot.py \
  --data prepared.csv --spec interval-spec.json --out output
```

Scripts copied from `skills/easyviz/scripts/` into `plot_scripts/` (interval_plot.py, render.py,
legend_layout.py, auto_layout.py, figure_profile.py, annotation_review.py). Spec: `interval-spec.json`.

## Actual settings

- Canvas 140 × 100 mm; Arial 8 pt; 300 dpi; formats pdf / svg / png.
- Log x axis, limits [0.15, 7.0], ticks 0.2 / 0.5 / 1 / 2 / 5; dashed reference at 1.
- Series = "Preparation batch" (aligned layout, span 0.6); Batch A #0072B2, Batch B #D55E00
  (Okabe–Ito, colorblind-safe); legend decodes the colors directly.
- `mark_fill="reference_overlap"`: hollow when lower ≤ 1 ≤ upper (endpoint equality counts as
  overlap), filled otherwise. Legend wording: "Interval excludes 1" / "Interval includes 1".
- Label order = first appearance in CSV (7 readouts, 11 supplied rows). No values imputed,
  no rows dropped; 3 missing readout–batch pairs remain empty positions.

## Checks actually performed

1. QA pass (`qa.json`: valid_outputs=true) — independent numerical audit reread the source CSV and
   verified markers, both interval endpoints, row/series positions, colors, fill states, equal
   marker area (20 pt²), reference value, and log scale; tick-collision, clipping, and
   mark-collision measurements reported no issues.
2. PNG inspected visually at full size and in two zoomed crops (legend region; dense middle region):
   fill states match the data for all 11 rows (verified by hand against the CSV), legend is
   readable, no text clipping, no crowding between intervals and reference line.
3. Exports verified: PDF page exactly 140 × 100 mm; PNG 1654 × 1181 px (= 300 dpi); SVG contains
   17 editable `<text>` elements (text preserved, not outlined).
4. `plotting-data.csv` retains all source columns plus source-row IDs, actual y positions, fill
   states, and marker area; `settings.json` records spec + hashes; `stats.json` records that no
   intervals were recomputed and no tests were run.

## Visual revision rounds

Round 0 of max 2 used. First render accepted with no revisions — justification: no collisions,
clipping, or decoding errors found in the zoomed inspection; the vertical whitespace beside the
three single-series rows is the intended consequence of stable per-series offsets in the aligned
layout and of keeping all 7 labels (rows must not be deleted or merged).

## Remaining issues / unchecked items

- Aesthetic reference fidelity is not certified by the script QA; visual review was performed by
  the generating agent itself, **not** an independent reviewer (helper reviewer skills were not
  used in this run).
- Vertical whitespace next to single-series rows (Background suppression, Temperature
  sensitivity, Storage response) is deliberate; an alternative blocks layout would group by batch
  but was not requested.
- Actual embedded font in PDF/SVG relies on system Arial via Matplotlib; glyph-level font
  substitution inside the PDF was not separately inspected (only that the PDF page size and SVG
  text elements are correct).
- Independent n and interval construction method unknown → no statistical layer added, per task.
