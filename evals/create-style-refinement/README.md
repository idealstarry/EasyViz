# Create color and stroke refinement

This revision addresses four Create panels shown in the main README. It
compares exact prior exports from `3e0a42d` with current exports on the same
data and canvas. It is a scoped design review, not a model comparison or a
claim of universal publication quality.

| Case | Before/after | Main change |
| --- | --- | --- |
| Paired myeloid changes | [Equal-width comparison](comparisons/paired-myeloid-remodeling.png) | Coordinated blue/coral, quieter references, summary strokes distinct from raw participant points. |
| Annotated inhibition | [Equal-width comparison](comparisons/annotated-inhibition.png) | Main coral matrix has priority over quieter marginal means and status strips; lighter axes and no colorbar frame. |
| Cell atlas composition | [Equal-width comparison](comparisons/cell-atlas-dotplot.png) | White data field, less table decoration, unchanged category colors, stronger palest blue tint. |
| Cohort effects | [Equal-width comparison](comparisons/paired-effects.png) | Borderless estimate points, uncapped supplied intervals, blue/coral and a lighter dashed zero guide. |

The main README presents the complete myeloid panel at 720 px, with the
three-design board on the case page. These comparison boards are separate
review aids; manuscript PDF/SVG canvases and 8 pt typography are unchanged.

[Independent image review](independent-review.md) prefers each candidate for
its stated task with residual notes. [Numeric/export verification](numeric-verification.json)
confirms 15 source or derived tables are byte-identical; the forest plotting
table differs only in cosmetic color. All supplied estimates, CI/IQR
definitions, count areas, denominators and declared value scales remain intact.
Very small positive atlas dots and overlapping participant values remain
difficult to distinguish at thumbnail size. Lighter guides may need a physical
print proof; removing grids reduces interpolation aids.

The reusable implementation is [Create colors and stroke roles](../../skills/easyviz/references/create-style.md).
New core Create drafts explicitly record data/summary/reference/axis/grid
weights. Existing specs and shared-profile drafts retain adopted settings.
The workbench uses effective source paths and normalizes core line-style
aliases before rerendering. Focused recipes retain their own documented
contracts.

Rebuild the evidence from this development checkout:

```sh
.venv/bin/python evals/create-style-refinement/build_comparisons.py
.venv/bin/python evals/create-style-refinement/verify_numeric.py
.venv/bin/python tests/check_showcase.py
```

`manifest.json` binds the four exact baseline/current PNG pairs and display
boards to their SHA-256 hashes. The independent review also records its input
identities. Regeneration after a later style change requires a fresh review;
do not relabel this record as validation of a different candidate.
