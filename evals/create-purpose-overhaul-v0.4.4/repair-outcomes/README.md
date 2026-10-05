# Repair-outcome purpose and geometry overhaul

This is new evidence for the user-directed 2026-10-05 overhaul. The previous
v0.4.3 evaluation folders are frozen. It is a within-case visual comparison and
a bounded numerical/export check, not model-wide effectiveness evidence.

The question remains treatment comparison within each author-supplied outcome.
The five-condition main case retains all 45 original values; the reversed-row,
four-condition/two-outcome input retains all 24 values. Means, sample SD
(ddof = 1), zero baselines, original-percent bounds and Arial 8 pt remain fixed.

| Geometry | Before | New case adoption |
| --- | --- | --- |
| Individual canvas | 60 × 62 mm | 72 × 48 mm |
| Main data rectangle | 45.90 × 51.15 mm | 57.24 × 37.44 mm |
| Data width/height | 0.897 | 1.529 |
| Bar width / category pitch | 0.30 | 0.45 |
| Five-condition physical bar width | 2.70 mm | 5.05 mm |
| Geometric gap / bar width | 2.33 | 1.22 |
| Adjacent raw-mark center spacing | 0.675 mm | 1.263 mm |

The old and new physical sizes intentionally differ. Their visible geometry
can be compared qualitatively, but this is not a scored comparison at matched
dimensions. The two first-pass treatments share the same new size.

The raw circles retain their 3.5 pt² geometric area. At the new pitch their
adjacent horizontal centers exceed the circle diameter, so even nearly equal
repeats are distinct. Extremely short SD intervals can remain covered by a raw
glyph; the numerical endpoints are preserved.

`before/` preserves the old specifications, images and checks with hashes.
`candidates/` contains the first-pass comparison of neutral open means and
subdued slate-blue filled means, rendered with identical science and new
geometry. Neutral open means were selected: x labels decode treatments, y
labels decode outcomes, and graphite raw/SD layers show variation without an
automatic three-outcome palette. `after/` is the frozen current-case snapshot.

`design-decision.json` separates the reading task, organization and mark roles.
The differing literature proportions provided in the task critique are
context for category/series count, not targets copied onto this dataset.
`geometry-evidence.json` measures actual drawn axes and patches.
`change-evidence.json` records before/after geometry and unchanged source hashes.
`frozen-final-manifest.json` binds the selected PNG/PDF/SVG exports.
The existing case `validate.py` checks both known-source inputs, individual
subpanels, grouped alternatives and compositions. Fresh independent review
packets for all five individual subpanels are in `reviews/`.

The HDR single panel is the representative preview; all three manuscript
outcomes remain separately exported. No new example or biological population
is introduced, and the grouped global-scale alternative remains available for
its different reading task.
