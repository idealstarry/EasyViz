# Create design-choice probe — 0.4.4

This probe checks bounded implementation choices, source preservation and actual
readability. It does not test model effectiveness, causal aesthetic improvement
or publication acceptance. Five explicitly synthetic inputs contain **165
rows/cells**; each adopted panel is **80 × 70 mm with Arial 8 pt text**.

The initial runtime was frozen before preparing the inputs. Its exact
[dependency tree](initial-runtime/manifest.json), [input/runtime freeze](freeze.json)
and [first outputs](outputs/) remain separate from later repairs. The original
first-delivery study uses a different freeze and is not repurposed to validate
this engine.

| Contract | Rows | Initial actual routes | Initial findings |
| --- | ---: | --- | --- |
| Quartile boxes | 42 | Colored summaries; colored observations; neutral positional decoding | All three rejected for raw-point spacing |
| Adopted density and quartiles | 51 | Colored inner summaries; colored observations; neutral positions | All three rejected for raw-point spacing |
| Supplied repeats | 12 | Filled and open bars, same mean/SD/observations | Two candidates; no width-only filler |
| Complete matrix | 24 | Blue/teal ramps; first ramp with a bottom guide | Same cells and global linear 0–50 limits |
| Fixed coordinates | 36 | Two category assignments; first assignment with hollow glyphs | Same coordinates and 14 pt² area; second filled route reassigns the same three hues |

The [initial independent review](initial-visual-review.md) opened all **14 PNGs**
and independently measured the PDFs and their extracted typography. The two
distribution failures are visible and remain recorded. The other three families
have readable, consistent decoders. No aesthetic winner was selected.

`run.py` checks frozen inputs/runtime, source-to-artist records, source
options/order/fields, canvas/typography and painted color/guide facets.
This verifies constrained alternatives rather than counting palette IDs or
spacing changes. An alternate color assignment alone does not establish better
organization or discriminability.

To replay the initial runtime into a fresh directory:

```sh
python evals/create-choice-space-v0.4.4/run.py --out /absolute/fresh/directory
```

This original replay intentionally exits with rejected distribution layouts;
failed QA is a retained finding. Statistical suitability beyond the adopted
captions, physical printing and color-vision accessibility were not checked.

## Retained repairs and final result

The [second freeze](final-freeze.json) and [second outputs](final-outputs/) fix
raw-point crowding within the adopted canvas. The [second actual-image review](final-visual-review.md)
found a remaining narrow-box limitation: approximately 0.912 mm summaries
against 1.222 mm points. These files are retained as pass 2, despite their
original `final-*` names.

The [third freeze](pass-03-freeze.json), [third runtime](pass-03-runtime/manifest.json)
and [third outputs](pass-03-outputs/) retain a minimum omitted summary-body width.
Only when needed, an omitted default positive point gap can be tried once at
0.2 pt instead of 0.3 pt. Explicit geometry and gaps remain locked; layouts that
cannot satisfy the constraints stay invalid. This numerical planning does not
replace actual image inspection or define a universal publication proportion.

The [third and final independent review](pass-03-visual-review.md) opened all
three changed quartile PNGs and nominal PDF previews. The other 11 PNGs were
independently confirmed byte-identical to the already viewed second pass; all
14 current PDFs were measured anew at 80 × 70 mm with Arial 8 pt text. The
revised boxes measure approximately 1.272 mm against 1.222 mm points, retain
visible quartile/median boundaries and preserve readable group association.
Overall status is **ready with notes** for this local readability scope.

All 165 input rows/cells, source order, quantitative coordinates, point areas,
scientific options and statistics remain unchanged. The
[scientific comparison](pass-03-science-comparison.json) and
[unchanged-image comparison](pass-03-byte-comparison.json) record these checks.
This is a same-input repair after initial failures, not an unseen first-draft
success, an aesthetic winner or a demonstration of Skill/model effectiveness.

Replay the final repaired runtime separately:

```sh
python evals/create-choice-space-v0.4.4/run.py --freeze evals/create-choice-space-v0.4.4/pass-03-freeze.json --runtime-root evals/create-choice-space-v0.4.4/pass-03-runtime --out /absolute/fresh/final-directory
```
