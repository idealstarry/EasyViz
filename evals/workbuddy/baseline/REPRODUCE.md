# Reproduction, settings and check record

Independent dot-plot test. Everything below was run in this directory
(`/private/tmp/easyviz-workbuddy-test/baseline`). No network, no paid API, no other agent,
no EasyViz repository, skill or script was read, and nothing outside this directory was written.

## 1. Files produced

| Path | What it is |
| --- | --- |
| `make_figure.py` | the plotting script (self-contained, deterministic) |
| `verify_figure.py` | independent checks, measured from the written artefacts |
| `output/panel.pdf` | vector, editable text, 120 × 90 mm page box |
| `output/panel.svg` | vector, live `<text>` elements, declared as `120mm × 90mm` |
| `output/panel.png` | 300 dpi raster, 1417 × 1062 px |
| `data/plot_data.csv` | the plotting data: positions, scatter size argument, radius, diameter |
| `settings/figure_settings.json` | the values actually resolved at run time |
| `checks/script_report.txt` | console report of the producing run |
| `checks/verification.txt` | the measured verification output (15 checks) |
| `caption.md` | standalone English caption |

## 2. Environment

```
interpreter : /Users/starry/Desktop/EasyViz/.venv/bin/python   (Python 3, venv, pre-existing)
matplotlib 3.11.1 | numpy 2.5.3 | pandas 3.0.5 | Pillow (used only by verify_figure.py)
font        : Arial -> /System/Library/Fonts/Supplemental/Arial.ttf
```

Nothing was installed.

## 3. How to run

```sh
cd /private/tmp/easyviz-workbuddy-test/baseline
/Users/starry/Desktop/EasyViz/.venv/bin/python make_figure.py     # writes output/, data/, settings/, checks/
/Users/starry/Desktop/EasyViz/.venv/bin/python verify_figure.py   # writes checks/verification.txt
```

Optional extra check with an independent renderer (poppler is not on `PATH` in this shell):

```sh
/opt/homebrew/bin/pdftoppm -r 300 -png -singlefile output/panel.pdf /tmp/pdfcheck
```

`make_figure.py` reads only `prepared.csv`, contains no randomness (so it is byte-stable apart
from matplotlib's embedded timestamps) and never fetches anything.

## 4. Input, as read

* 24 rows, complete 8 × 3 grid. Cell types in first-appearance order: Resident macrophages,
  Activated monocytes, Interferon macrophages, Lipid-associated cells, Antigen-presenting cells,
  Cycling myeloid cells, Inflammatory macrophages, Tissue monocytes. Treatment arms in
  first-appearance order: Control, Low dose, High dose.
* `Detected fraction` spans 0 → 0.85. Exactly two observed zeros:
  **Resident macrophages / Control** and **Cycling myeloid cells / Low dose**.
  The smallest non-zero value is 0.05 (Interferon macrophages / High dose) and is kept as a value.
* `Prepared score` spans −0.22 → 1.66 (the colour limits are those observed extremes).

## 5. Encoding

* **Area → Detected fraction.** Area is linear in the value on a single shared 0–1 scale.
  In matplotlib, `scatter(s=…)` takes the *square of the marker diameter in points*, so the
  mapping is implemented as `s_pt2 = fraction × (5.6 mm → pt)²`, i.e. the drawn diameter is
  `sqrt(fraction) × 5.6 mm` and the drawn geometric area is `π/4 · d²`, linear in `fraction`.
  A value of 1.0 gives a 5.6 mm diameter; 0.85 gives 5.16 mm; 0.05 gives 1.25 mm.
* **Colour → Prepared score.** Linear normalisation over the observed extremes on `viridis`;
  range bar to the right with ticks at 0 / 0.5 / 1.0 / 1.5, plus each dot's own 0.22 pt dark rim
  so that the lightest colours stay legible on white.
* **Zeros.** The two rows with `Detected fraction == 0` get no circle at all: their declared
  marker area is exactly 0, and a grey `×` (a separate, non-quantitative symbol, constant size,
  1.76 mm across) marks that a zero was observed. No zero was turned into a small positive value.

## 6. Resolved figure settings

```
canvas          120 × 90 mm, dpi 300, bbox_inches=None (full canvas preserved)
                PNG 1417 × 1062 px;  PDF MediaBox exactly 120.000 × 90.000 mm
fonts           Arial 8 pt for every string (family, axis labels, tick labels, legend, colour bar)
                pdf.fonttype 42 (embedded TrueType) | svg.fonttype "none" (live text)
marker          diameter(fraction) = sqrt(fraction) × 5.6 mm ; max diameter 5.6 mm
                dot rim #3a3a3a, 0.22 pt
zero symbol     marker "x", 5.0 pt across, linewidth 0.5 pt, colour #8c8c8c
colour          viridis, vmin −0.22, vmax 1.66, ticks 0 / 0.5 / 1.0 / 1.5
axes            x title "Treatment arm", y title "Cell type", no grid,
                spines #4d4d4d 0.5 pt, ticks out 1.8 pt / pad 1.5 pt
layout          main axes 39.96 / 9.26 / 64.47 / 66.54 mm (left/bottom/width/height)
                row pitch 8.32 mm, column pitch 21.49 mm
                colour bar 3.5 mm wide, 1.5 mm gap; size legend strip 10 mm tall
text in image   axis titles, category tick labels, "Detected fraction" size legend,
                "Prepared score" colour bar — and nothing else
```

## 7. What was actually checked

`verify_figure.py` measures the written files rather than the code's intentions.
**15 checks, 15 passed** (`checks/verification.txt`):

* PNG is 1417 × 1062 px = the 120 × 90 mm canvas at 300 dpi.
* All ink lies inside the canvas; measured clear margin left 1.95 / right 2.29 / top 2.63 /
  bottom 2.71 mm — nothing clipped. The declared (text-box based) clearance is also honoured.
* Zero rows declare a marker area of exactly 0 in `data/plot_data.csv`.
* The rendered zero symbol is **not** a disc: ink fills 0.24 of its own bounding box, versus 0.79
  for a filled disc of the same span.
* **The area mapping was verified on the raster**: a least-squares fit of the 22 filled markers
  gives `rendered diameter = 5.624 × sqrt(fraction) + 0.137 mm`, i.e. the slope matches the declared
  5.6 mm maximum to within 0.4 %; the small constant is the 0.22 pt rim plus antialiasing.
* Area ratios 1.000 : 2.000 : 2.9999 : 4.000 for fractions 0.25 : 0.50 : 0.75 : 1.00 — linear in
  the value, which a radius-linear encoding would not be.
* PDF page box is exactly 120.000 × 90.000 mm; text is embedded as TrueType (`FontFile2`, subset
  of Arial), no Type3 outlines.
* **The PDF was rasterised by an independent renderer** (poppler at 300 dpi): 120.06 × 90.00 mm,
  ink inside, and its grey levels agree with the matplotlib PNG to 4.8 / 255 on average.
* SVG declares `width="120mm" height="90mm"` and holds 24 live `<text>` elements with
  `font-family: 'Arial', sans-serif` — the text is editable, not outlined.
* No title, subtitle or explanatory footnote appears anywhere in the image.
* All 24 input rows are present in the plotting data.

## 8. Visual inspection and the two modification rounds

The PNG was opened and viewed after every run, and the PDF was re-rendered through poppler and
viewed as well.

**Round 1 — margins.** The first render had the rotated `Cell type` title glued to (and clipped by)
the left canvas edge: the analytical margin model was short by about 1.9 mm because it estimated
the rotated label's ink height from the point size. Replaced it with a render-measured auto-fit:
the script now draws, reads the real tight ink bbox, and re-positions the axes so the ink keeps a
2 mm clear margin (converges in two iterations; trace in `checks/script_report.txt`).

**Round 2 — marker geometry and the zero symbol.** Measuring the raster exposed a genuine encoding
bug: the dots were 11 % smaller than declared, because `scatter(s=…)` is the square of the marker
*diameter*, not a geometric area, so `s = πr²` had shrunk the radius by √π. Fixed the mapping so
the drawn diameter is `sqrt(fraction) × 5.6 mm`, which the fit above now confirms. In the same
round the zero cross was enlarged from 3.7 pt to 5.0 pt and its stroke thinned from 0.7 pt to
0.5 pt, so that its fill ratio (0.24) is unambiguously that of a cross rather than a small dot.

## 9. Known limitations and what was *not* checked

* **PNG height is 1062 px, not 1063.** `90 mm × 300 dpi = 1062.99 px` and matplotlib truncates the
  fraction, so the PNG is 89.92 mm tall. The PDF and SVG carry the exact 120 × 90 mm size. The
  0.08 mm shortfall was not worked around, because faking the figure size would have made the page
  box inexact instead.
* **Left ink clearance is renderer-dependent.** Matplotlib's own rasteriser puts the leftmost ink
  1.95 mm from the edge; poppler's PDF render puts it at 1.10 mm. Both are inside the canvas, but
  a third renderer could hint the glyphs slightly differently. Not verified in Acrobat or InDesign.
* **No print proof.** The figure was judged on screen at 300 dpi only. How the 0.22 pt dot rims,
  the 0.5 pt spines and the light-grey legend circles survive on paper was not verified.
* **Colour accessibility not tested.** `viridis` is designed to be perceptually uniform and
  colour-vision-deficiency-friendly, but no CVD simulation and no grayscale conversion check was
  run. The magenta-free low end of `viridis` is dark, and the darkest dots (Prepared score near
  −0.1) are close in lightness to the black text; unverified in grayscale print.
* **No reference figure was supplied**, so agreement with any published layout or journal
  template was not assessed, and no target journal's author guidelines were consulted.
* **The colour scale is an assumption.** Mapping `Prepared score` linearly over its observed
  extremes, sequentially rather than diverging, follows from the fact that the score's
  construction — and therefore whether zero is a meaningful midpoint — is undocumented. If the
  score turns out to be a signed, zero-centred quantity, a diverging map would be more
  appropriate; that decision was not resolved from the input.
* **Statistical reading is out of scope by instruction.** No replicates exist in the input, so no
  test, confidence interval or significance marker is shown, and none should be inferred from the
  pattern of the dots.
* **Skill/memory note:** a reusable procedure was identified here (measure the raster to validate
  a size encoding; auto-fit margins from the rendered ink bbox), but writing it to a skill
  directory would have written outside the working directory, which this test forbade — so it was
  left in this document instead.
