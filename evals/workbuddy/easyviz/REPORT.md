# Implementation record — cell-type dot panel

Track: **create** (EasyViz `dotplot`). Isolated visual test; no other test output,
repository evaluation, or historical conclusion was read.

## Files

| File | Role |
| --- | --- |
| `prepared.csv` | Input, unmodified (24 rows). |
| `panel-spec.json` | Adoption specification (fields, order, labels, scales, formats). |
| `make_panel.py` | Reproducible driver: input-contract checks → render → output checks. |
| `caption.md` | Standalone English caption (not rendered on the canvas). |
| `output/panel.pdf`, `.svg`, `.png` | Final panel, one panel per file, full canvas. |
| `output/plotting-data.csv` | Rendered values incl. `_easyviz_state`, `_easyviz_area_pt2`. |
| `output/settings.json` | Resolved spec, actual layout, colormap, renderer hashes. |
| `output/qa.json` | Machine-readable render checks. |
| `output/stats.json` | Explicitly no statistics. |
| `output/check-summary.json` | Independently recomputed area/export checks. |
| `output/pdf-render-check.png` | 150 dpi raster of the PDF, used to confirm vector output. |

Reproduce with:
`/Users/starry/Desktop/EasyViz/.venv/bin/python make_panel.py`

## How the panel was built

1. Read `skills/easyviz/SKILL.md`; selected the **create** track and the
   `dotplot` family (one observation per displayed categorical pair).
2. Read `quick-start.md`, `dot-states.md`, `chart-library.md`, `panel-layout.md`,
   `legend-layout.md`, `palettes.md`, `visual-review.md`, the `cell-atlas-dotplot`
   worked case, and the `dot-states` fixture. Inspected the renderer contract with
   `render.py --describe-spec` and the dotplot source before writing a spec.
3. Authored `panel-spec.json` with explicit field roles, category order, canvas,
   font, and scales, then rendered with the bundled core renderer
   (`render.py --data prepared.csv --spec panel-spec.json --out output`).
4. Made one evidence-based visual refinement (see below), re-rendered, re-checked.

## Mapping decisions (recorded, actual)

| Aspect | Actual setting |
| --- | --- |
| x (`Treatment arm`) | Control, Low dose, High dose — first-appearance order |
| y (`Cell type`) | 8 types — first-appearance order (top → bottom) |
| Dot size | `area_pt2 = detected_fraction / 1 × 165` — **area, not radius**; fixed 0–1 scale |
| Size legend | 0.25 / 0.5 / 0.75 / 1, same value→area transform as the dots |
| Dot color | `Prepared score`, sequential `notch2-blue` (light `#D3E6F1` → `#2581B9`) |
| Color limits | `[-0.22, 1.66]` = observed data range; no diverging center |
| Zero handling | Zero area + separate grey `_` ("Measured zero") glyph; no small positive |
| Small-positive flag | Disabled (`small_positive_area_pt2 = 0`) |
| Canvas / font / dpi | 120 × 90 mm / Arial 8 pt / 300 dpi |
| Outline | Borderless dots (create default), no edge stroke |
| Statistics | None — synthetic descriptive quantities, no independent replicates |

Marked dots: 24 observed rows, **2 measured zeros** (Resident macrophages / Control;
Cycling myeloid cells / Low dose), 0 unmeasured, 0 absent coordinates.

## Checks actually performed (evidence)

| Check | Result | Evidence |
| --- | --- | --- |
| Input rows retained | 24 / 24 | `qa.json` `input_rows`; `plotting-data.csv` |
| Category order = first appearance | pass | `make_panel.py` assertion on `dict.fromkeys` order |
| Complete 8 × 3 matrix, no absent cells | pass | `qa.json` `dot_states.missing_coordinates = []` |
| Area ∝ fraction, never radius | pass, max abs err 1.4e-14 | `check-summary.json` `area_max_abs_error` |
| Zero area for measured zeros | pass (both 0.0 pt²) | `check-summary.json` `zero_area_pt2` |
| Zero decoded by a separate glyph | pass | `dot_states.symbols` = `{Measured zero: "_"}` |
| Canvas clipping | 0 clipped text | `qa.json` `clipped_text` |
| Tick-label overlap | 0 collisions | `qa.json` `overlapping_tick_labels` |
| Missing glyphs | none | `qa.json` `missing_glyphs` |
| Legend fit / reserved space | pass, no issues/warnings | `settings.json` `legend_layout`; all blocks inside right band, 2 mm off the data region |
| Export size pdf/svg/png | 120 × 90 mm each; PNG 1417 × 1063 px @ ~300 dpi | `qa.json` `exports`; PDF page box measured 340.157 × 255.118 pt |
| SVG editable text | 23 `<text>` elements, `font-family: 'Arial'`, physical page 120 × 90 mm | `panel.svg` header + tag count |
| Visual inspection of PNG and PDF | done (self-review) | `panel.png`; `output/pdf-render-check.png` |

Legend footprints (canvas fraction): colorbar 3.7 %, size 4.7 %, symbol 0.6 %;
combined right band ≈ 22.3 mm of the 120 mm width; data region 52.7 × 75.8 mm.

## Visual review — self-review, 2 passes

- **Pass 1** (max area 120 pt²): all technical checks passed. Finding (minor): the
  area encoding — the primary quantitative channel — read timid; largest dot ≈ 4.0 mm
  across within a ≈ 9.5 mm row pitch, with visible slack.
- **Pass 2** (max area 165 pt²): largest dot ≈ 4.7 mm, smallest positive ≈ 1.1 mm,
  zeros still zero-area ticks. Still passes every check; dots gain prominence with no
  new collisions. Adopted.

Status: **ready_with_notes**.

## Residual / not checked

- **Reviewer role = self-review.** The task forbade calling other Agents, so the
  independent reader/reviewer helpers were not used; there is no independent review.
- **Print-size legibility** was judged visually at the raster scale, considering the
  intended physical size; it was not verified by physically printing at 100 %.
- **Color-vision-deficiency safety** of `notch2-blue` is not certified; position, size
  and the zero glyph remain as non-color cues.
- **Exact exported dot colors / pixel geometry** were not pixel-sampled; the colormap
  and limits were verified from `settings.json` and the rendered image.
- **Denominator of `Detected fraction` and the construction/units of `Prepared score`
  are unknown** (stated in `caption.md`); the color range is the observed data range,
  not a validated scale.
- **No statistics** — no independent replicates; nothing was imputed, aggregated or
  filtered, so no biological or inferential claim is made.
