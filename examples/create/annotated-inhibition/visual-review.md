# Rendered-panel review

The actual 300 dpi `panel.png` was inspected after rendering, then inspected again after spacing refinements. The final panel keeps the heatmap as the dominant element and aligns both mean tracks and both binary strips to the same ordered cells.

| Check | Observation |
| --- | --- |
| Readability | All 40 strain labels remain distinct at the declared 8 pt setting, including the longest numeric IDs and `JIP 05/93 (3)`. Independent PDF text extraction confirmed 8 pt for every text span. |
| Track alignment | Each top bar is centered on its receiver column; each side bar is centered on its sender row. Genome strips share the same boundaries. |
| Color | Light coral cells show the GII range; sky-blue mean bars and teal/gray genome strips remain visually separate from the continuous scale. |
| Hierarchy | Heatmap occupies the main square; mean tracks are subordinate. The full-data denominator is documented in the separate caption. |
| Spacing | The mean-track names remain as axis labels. Standalone panel title, selection overview, denominator prose and color-scale note are now in the separate caption. |
| Boundaries | No label or legend extends outside the canvas. Automatic text-boundary and missing-glyph checks pass. |
| Assembly | One 180 × 160 mm integrated panel, without panel letters or a multi-panel montage. |

This inspection evaluates the rendered design, not statistical or biological validity. Numeric consistency and physical export checks are recorded separately in `qa.json`.

## Palette and caption revision

The actual refreshed PNG was inspected. The panel now uses light coral cells with sky-blue marginal bars and teal metadata strips. All axes, scale ranges, selected data and 8 pt labels remain intact. The title and explanatory prose have been removed; narrative definitions are in caption.md. No clipped labels or new collisions were observed.
