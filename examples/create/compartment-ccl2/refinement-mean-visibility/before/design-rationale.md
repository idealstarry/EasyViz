# Source-informed compartment time comparison

The task is to compare the *timing and magnitude of the group response within
each compartment*. The source has 88 individual observations, two actual
genotypes, four irregularly spaced times, two units, sixteen group summaries,
twenty blank source cells and eight author-adjusted statistical results. A
single shared concentration scale or connecting individual source columns
would change its scientific meaning.

## Adopted first-panel brief

- **Organization:** two independent 82 × 65 mm panels, with exactly aligned
  physical 0/12/24/48 h positions and separately labeled concentration scales.
  The 167 × 65 mm row is an unscaled preview with a 3 mm assembly gap.
- **Leading layer:** definite straight mean trajectories and filled mean
  symbols. The 24-to-48 h interval is twice the 12-to-24 h interval. Lines join
  cross-sectional group means; there is no fitted curve or inferred pairing.
- **Uncertainty:** capless mean ± SEM intervals at the exact source times.
  No large translucent band competes with the mouse observations.
- **Observation layer:** smaller open symbols with color plus shape decoding.
  Explicit physically bounded left/right genotype columns avoid raw symbol
  intersections while retaining every concentration and nominal time.
- **Decoding:** control blue circles and IM-DTR coral squares. The small legend
  describes the mean layer; the caption defines the open observation layer.
- **Geometry:** each data rectangle is 61.50 × 44.85 mm, width/height 1.371.
  Both panels keep Arial 8 pt. No in-image title, count prose or source footer
  is used. Serif-free unit text remains part of the actual reading apparatus.

An initial *planning* message proposed 82 × 63 mm. Before the first actual
export, the adopted height became 65 mm to accommodate the detached legend
and two-line unit label without reducing the font. All saved actual panels
have the same final 82 × 65 mm size; this is not a comparison of different-size
exports.

## What the paper contributes

The inspected Fig. 3c crop has definite blue/red open boundaries, all raw
observations, compact SEM summaries and separate lung/serum units. Its small
raw symbols and clear category identity survive a dense multi-panel context.
Those mechanisms informed this case. It does not supply a universal palette,
an instruction to draw every time comparison as bars, or a license to infer
missing animal IDs.

The present trajectory organization makes the irregularly sampled rise and
return easier to follow than a series of open bar heights. Choosing that
organization is a task-specific Create decision. The paper crop supplies an
observable design comparison; it is not the required target layout, and its
incorrect days label is explicitly corrected from the caption and workbook.

## Iteration and concrete checks

Before any visual pass, actual packing rejected crowded source groups. A
serum cluster contains an exact repeated concentration and four nearby
values; two or three allowed raw columns were insufficient. Four physically
bounded columns retain them individually. The source concentrations were
never changed. The smallest serum value, 0.875427 pg/ml, also required a small
negative *display margin* to avoid cutting its positive glyph at the axis.

1. **Attempt 01:** a complete lung export was inspected; serum construction
   stopped on the raw spacing constraint. The partial export is preserved.
2. **Attempt 02:** both PNGs and the nominal 96 dpi PDF preview were inspected.
   Independent export inspection found that the custom code's SVG/PDF rc
   settings were active only during construction, so old SVG text became
   paths. The earlier files remain evidence of that failed delivery check.
3. **Attempt 03:** serialization keeps the editable SVG text and embedded PDF
   font settings active. Square packing is checked with actual axis-aligned
   footprints, rather than a circular approximation that can miss square
   corner intersections. Actual images and source-to-export validation are
   checked before adoption.

After adopting that appearance, a source-provenance and portability follow-up
added an explicit `--font` override. An actual unchanged-Arial rerender into a
new temporary directory produced byte-identical PNG/PDF/SVG files; current-code
maps and QA were refreshed from that render, while earlier code/maps remain
preserved. A separate DejaVu Sans redraw has its own adopted override spec and
source/artist/font checks. This changes portable execution, not the selected
aesthetic design, and does not add a fabricated fourth aesthetic review.

The standalone validator reads the original workbook XML, independently
computes all sixteen means and SEMs, parses the actual source-bound SVG
markers/SEM/trajectory paths, checks PDF vector marker centers and embedded
Arial 8 pt text, and verifies unscaled assembly positions. This gives concrete
data and geometry evidence; it does not prove a publication-quality verdict.

## Tradeoffs and limits

Physical raw columns are a categorical visibility treatment. Their x
positions are not measurement times; all nominal times and display offsets
are separately retained. A few raw symbols cross a mean trajectory, so the
open symbols may interrupt a small section of that line. Both color and shape
remain decoded, and all observations stay present. Neither a zero-crossing
claim nor a point-free summary is substituted for this real source.

The two independent scales forbid comparing the absolute vertical heights of
lung and serum. The mean trajectory is descriptive interpolation, not a
continuous-time model. Statistical correction-family scope and mouse IDs are
unavailable, so supplied P values remain a separate traceable source table.
This is one known-source Create exercise and a literature design audit, not a
matched model benchmark or a general claim of CNS-level output.
