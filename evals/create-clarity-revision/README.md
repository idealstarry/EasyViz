# Create clarity revision

The user rejected the previous paired-panel layout, matrix colors/ranges, and
muted atlas palette. This revision addresses those three specific examples.
The frozen baseline is commit `43662af`; `manifest.json` pins baseline and
candidate PNG identities so later example changes do not overwrite this review.

| Case | Adopted change | Reading limit |
| --- | --- | --- |
| Paired myeloid changes | Adjacent cohort tracks on one axis; filled IQR strips, distinct medians and aligned below-zero percentages. | Dense dots principally convey distributions in small raster previews. |
| Annotated inhibition | Single-hue blue, globally linear −400 to 1000 min; equal 200 min colorbar intervals; both marginal means use 0–700 min. | Common middle values have subtle contrast; differently sized marginal axes still have different physical slopes. |
| Cell atlas | Brighter sky/coral/jade/violet categories and a cyan-to-blue quantitative scale. | True proportional circles remain tiny for very small counts. |

`numeric-verification.json` independently recomputes paired changes/summaries,
matrix matches/means and atlas proportions, and verifies unchanged scientific
tables against the baseline. `matrix-scale-audit.json` records the primary
measurement definition and range rationale. Each case retains its actual-image
review record; candidate preference remains specific to the task and canvas.

The paired case compares two materially different layout revisions before a
second final visual check. The atlas compares two brighter palettes; the matrix
review checks the rendered cell colors and guide geometry. These reviews and
package replays do not establish user acceptance, publication readiness or
generalized improvement across models. Reproduce specifications are unchanged.

The new shared mean-scale option remains reusable with automatic bounds on a
different input; clipping and conflicting range instructions are rejected.
`package-validation.json` records isolated ZIP extraction and replay, using
available fonts on this host rather than a fresh operating-system installation.
