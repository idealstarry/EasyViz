# Current legend audit

This audit is bound to the frozen exports in `current-baseline/`; PNG and PDF hashes are recorded in [current-audit.json](current-audit.json) and match `current-baseline/snapshots.json`. All three baseline PNGs and PDF renders at 96 dpi were visually inspected. Scripts and current layout guidance were read without modification. Earlier checks established no clipping; they did not establish manuscript compactness.

## Diagnosis

The cell-atlas guide section is disproportionately spread out. Its categorical symbols are already modest, and all text is 8 pt. The excess comes from generous horizontal gaps, three vertically separated decoding rows, and an unusually long colorbar. The forest and heatmap do not have the same degree of excess, so a universal font reduction or global legend scale factor would be inappropriate.

Bounding boxes below combine PDF text, vector paths, and images. They are **guide envelopes**, including internal space, not literal ink coverage. “Data field” is declared separately for each panel; ratios are diagnostic and cannot independently accept or reject a design.

| Baseline | Defined data field | Category guide envelope | Other guide envelopes | Main observation |
|---|---|---|---|---|
| Cell atlas, 180 × 120 mm | Full table body: 169 × 74.3 mm, including subtype labels and numeric marks | 81.78 × 3.16 mm; 48.4% of table width | Size: 60.36 × 9.62 mm; color: 73.35 × 13.51 mm | Three guides together occupy a 157.57 × 19.11 mm envelope. The allocated bottom band is 25.7 mm, 21.4% of canvas height and 34.6% of body height. |
| Paired effects, 180 × 120 mm | Numeric forest axes: 120.6 × 94.8 mm; term labels excluded | 64.05 × 3.16 mm; 53.1% of numeric-field width | None | A single shallow guide row. Its actual envelope is only 1.8% of numeric-field area; horizontal packing can improve, but it is not consuming a large vertical block. |
| Annotated inhibition, 180 × 160 mm | Central heatmap: 96 × 96 mm; marginal bars excluded | 53.23 × 3.16 mm; 55.4% of matrix width | Color: 34.32 × 12.22 mm, including title and tick labels | The two guide envelopes sum to 6.4% of matrix area. Their distant placements create a much larger enclosing rectangle; that rectangle must not be mistaken for occupied legend area. |

All inspected PDF text, including axis and legend text, is 8 pt. Equal font size did not produce equal proportional footprint. Summed guide-envelope area is 14.6% of the cell-atlas body, versus 1.8% for the forest and 6.4% for the central heatmap; these use the different declared fields above and are not an aesthetic league table.

### Cell atlas

- Category keys are 1.8 × 1.8 mm, with a sensible 0.9 mm key-to-text gap. The problematic spaces are **between items**: 7.34–9.65 mm, more than twice the approximately 3.16 mm text-box height. Pack items from measured label widths rather than hard-coded increments of 14, 35, and 26 mm.
- Count-guide centers are 21 and 23 mm apart. Three samples and their labels can be packed much more tightly while keeping the plotted areas exactly unchanged. The largest legend circle is approximately 3.18 mm in diameter; this is a quantitative exemplar, not a decorative symbol to shrink independently.
- The colorbar body is 71 × 3.1 mm. The three dot columns span only 51 mm when a half-column interval is included at each end; the bar is 139% of that width. Five short ticks do not require this length.
- “Dot area: object count” and “Color: within-depot share (%)” repeat the mark channels. “Object count” and “Within-depot share (%)” retain their meanings with less visual weight. Keep both numerical guides and the category key unless equivalent direct labels are provided.
- The field headings and subtype labels are essential. They should not be removed to compensate for loose guide placement. No new title or prose footnote is needed.

### Paired effects

The legend circles match the 1.38 mm data dots. However, the right edge of each circle is approximately 3.55 mm from its label, because the default line-handle slot is much wider than a dot. Reduce the handle slot and inter-item gap, rather than reducing the point or text size. The cohort sample counts contain useful information and do not by themselves justify removal. The 9.6 mm top allocation can be inspected after packing, but the one-row legend is already vertically compact.

### Annotated inhibition

The 28 × 3 mm colorbar is not excessively long, although its title and ticks expand the full guide to 12.22 mm high. Its category swatches are 2.82 × 2.16 mm; modestly smaller keys and tighter key-to-label spacing would be sufficient. The category guide sits in a separate bottom band. A measured two-row key in the right-hand guide column could use that column's remaining space, subject to checking label fit. Long rotated strain labels and the receiver-axis label genuinely consume bottom space; do not attribute all of it to the legend.

## Gaps in current reusable guidance and renderer

`panel-layout.md` preserves physical dimensions, text roles, and decoding elements, but has no guide measurement, packing, or footprint review. It therefore permits a panel to pass typography and boundary checks while allocating too much room to legends.

The core renderer fixes the colorbar width to 2.8% of the canvas and its gap to 3.5%. This gives a 2.46 mm bar on an 88 mm panel, but a 5.04 mm bar on a 180 mm panel despite the same 8 pt font. Legend placement, handle slots, and dot-guide row spacing also rely on library defaults or hard-coded fractions. These are not responsive to label lengths, numbers of categories, or the physical size of the main plot. Current clipping checks do not diagnose any of these proportional problems.

## Adaptable rules to implement

1. **Budget actual geometry.** After drawing, measure each guide's full envelope: symbols, labels, title, ticks, and padding. Record width, height, summed guide-envelope area, gap from the data, and any reserved band. Measure categories, size, and color separately. Use the actual data-field bounds, not the entire export canvas. Treat ratios as review signals, not acceptance thresholds.
2. **Pack in physical units.** Use measured label widths and font-relative gaps. At 8 pt, categorical keys around 1.7–2.3 mm, key-to-label gaps around 0.8–1.2 mm, and item gaps around 1.5–3 mm are useful starting candidates. For dot-only keys, the handle slot should follow the dot, not a default line segment. These are EasyViz starting values, not journal standards.
3. **Preserve quantitative mark semantics.** Size-legend circles must use the same area mapping and outline policy as data circles. Use two or three informative reference values and pack them; do not shrink only the legend markers or enlarge tiny data values to meet a style target.
4. **Fit colorbars to decoding needs.** Start around 1.5–2 mm thickness and choose length from tick-label widths, precision, and the relevant data-field size. A 25–40 mm horizontal bar with three to five ticks is a useful candidate in these examples, not a universal requirement. Include the full title/tick envelope when checking available room.
5. **Choose placement from content.** Compare compact one-row, packed multi-row, and side-column arrangements. Use existing free space when it does not cover observations. Avoid reserving an entire footer across the panel for a short guide. Wrap or reposition before changing an agreed font size or canvas.
6. **Keep concise decoding text.** Remove redundant channel prefixes and repeated titles, while retaining units, group identity, size values, zero/center semantics, and missing-value distinctions. Put explanations in the separate caption; do not add a titled card or manuscript footnote.
7. **Review the completed panel at final size.** Confirm both legibility and proportional emphasis after packing. Save measured guide bounds and an actual visual-review result. Passing font-size, clipping, or export checks alone cannot establish balanced composition.

No example, renderer, or skill file was edited for this audit.
