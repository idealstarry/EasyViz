# Rendered-panel review

The implementing agent inspected the regenerated 300 dpi `panel.png`, then a 680 × 605 px preview of the same complete canvas to assess the overall reading hierarchy near its print-sized screen footprint. This is a self-review, not an independent review. A pixel display is not a calibrated physical print proof.

| Check | Observation |
| --- | --- |
| Main encoding | The bright coral/orange ramp keeps the pale field while giving middle values more definition than the previous pale-coral version. The high end remains coral rather than a brown or dark endpoint. Sender profiles and concentrated high-GII regions remain visible. Linear `Normalize` remains −400 to 1,000 min, including all negative measurements. |
| Supporting color | Mean bars now use muted blue `#6C9FB2`, replacing bright sky blue. Genome strips use subdued blue-gray `#708C94` and light gray `#E8ECEF`. Both layers remain distinguishable while the central matrix carries the main contrast. |
| Strokes | Marginal axes use 0.45 pt gray strokes and 0.35 pt light grid lines behind bars. Mean bars, metadata tiles and corresponding legend keys remain borderless. The continuous colorbar has no surrounding box. |
| Readability | All 40 strain labels remain separately readable at 8 pt, including long numeric identifiers. Programmatic PDF extraction found only 8.0 pt text spans. The display-size preview showed no new collisions. |
| Alignment | Top bars remain centered on receiver columns; side bars remain centered on sender rows. Both metadata strips retain the same cell boundaries. |
| Scope and layout | The same 20 × 20 selection and full 76-partner mean denominators are retained. One 180 × 160 mm integrated panel; no title, explanatory footnote or added panel letter. |
| Export boundaries | Automatic text-boundary and missing-glyph checks pass. PDF/SVG physical dimensions are unchanged; PNG remains 2,126 × 1,890 px at 300 dpi metadata. |

The supplied source CSVs, displayed-measurement table, full summary table, and selected-ID table were compared byte-for-byte with the preceding committed example and are unchanged. `qa.json` records the regenerated numeric and export checks. The visual assessment does not validate a biological mechanism or establish publication acceptance; it evaluates this panel's reading hierarchy and legibility.
