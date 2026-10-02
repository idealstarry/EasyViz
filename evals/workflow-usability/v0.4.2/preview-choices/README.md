# v0.4.2 independent viscosity preview trial

The public preview command produced both default alternatives and the explicitly requested eligible violin from a new 57-row synthetic source. The declared scenario uses independent formulation samples measured once at 25 C, with 17/19/21 observations and literal IDs including `001`, `NA`, `null`, `N/A`, `NaN` and `0007`. These are synthetic measurements for a forward usability trial, not a real experimental dataset.

- Public interface used: `--describe-contract`, `--help`, and `references/preview-choices.md`. The preview implementation, tests and earlier outputs were not consulted.
- Fixed display: 110 × 80 mm, actual Arial 8 pt, category colors `#0072B2` / `#D55E00` / `#009E73`, linear viscosity axis 4–17 mPa·s, real PNG/PDF/SVG exports.
- Retention: all 57 rows, five original columns, literal IDs and exact measurement text were checked in snapshots, traces and every plotted table. Original source bytes remain unchanged. No tests, confidence intervals, aggregation or excluded rows were introduced.
- Actual exported geometry: all three box/violin marker groups preserve the source measurement-coordinate multisets; SVG coordinate rounding errors are below 0.000001 pt. Actual ECDF step vertices preserve full ties/fractions and complete source membership. Digests and check methods are in `verification.json`; no per-observation SVG identity is fabricated.
- Packing: beeswarm placed every point, with zero overlap, spacing violation, boundary issue or fallback; maximum categorical offsets are about 1.955, 0.977 and 2.142 mm. Numeric values and 3 pt point diameter remain unchanged.
- Cross-run invariants: default box and ECDF PNGs and normalized SVG geometry/style digests are byte-identical to their opt-in-run counterparts. Adding the violin did not change the default alternatives.

For medians and descriptive spread, the box/points view is the direct reading task. Its compact A/C median strokes are partly obscured by the opaque raw-point row at the final-size reduction, and that observation was sent to the parent/preview author for a separate refinement. For tails or threshold fractions, ECDF is more direct; its central blue/green steps locally coincide, while tails and the legend remain distinct. The optional violin supplies a smoothed-shape view, with visible dependence on KDE and independently normalized width; it is not an exact tail-fraction or sample-count display. No universal winner or unrun baseline advantage is claimed.

## Evidence

| Artifact | Location |
| --- | --- |
| Source, scenario and requests | `inputs/` |
| Exact public contract | `public-contract.json` |
| Actual commands and return codes | `command-log.json`, `*.stdout.log`, `*.stderr.log` |
| Default two actual choices | `default-two/box-points/`, `default-two/ecdf/` |
| Explicit three-choice output | `with-violin/box-points/`, `with-violin/ecdf/`, `with-violin/violin-points/` |
| Independent retention, physical-size, geometry and hash checks | `verification.json` |
| Final-size PNG/PDF/SVG review rasters | `review/` |
| Honest visual observations and task-specific choice | each attempt's `visual-review.md` |

The original generated manifests and pending review files were preserved before completing review notes. Current manifests update only the review-file binding and add review provenance. Automated `visual_review_required` flags remain their original statements of scope, not substituted proof of inspection. Every `selection.chosen_choice` remains null and every `automatic_winner` remains false.
