# Review of the adopted create panel

Status: **ready_with_notes**. Reviewer: implementer self-review; no independent
agent was used because the task explicitly disallowed other agents.

Candidate reviewed: `output/attempts/attempt-02/panel/panel.png`, opened with the
image tool after rendering. Adopted requirements are in `adopted-spec.md`.
This was visual review pass 1. No visual correction was required; 0 of the
allowed 2 corrections were used. The earlier `attempt-01` was a preparation
validation failure and produced no rendering; its code and failure record are
preserved.

| Severity | Location | Observed evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Three data groups | Vehicle, Low dose, and High dose are directly labelled in dose order; individual colored circles, quartile boxes, medians, and whiskers are all visible. | Show individual units and group distributions. | Accepted. |
| note | Dense values near Vehicle 82 and Low dose 97 | Physical categorical displacement makes neighboring points distinct; quantitative heights are preserved. | No omitted or obscured individual units. | Accepted; numerical spacing audit reports 0 conflicts and 36 placed points. |
| note | Upper Low dose value near 135 | The observation beyond the whisker remains visible and separated from the highest whisker. | Do not suppress outliers or source observations. | Accepted. |
| note | Axes and margins | Signal axis units and all three group labels fit; ticks from 70 through 140 are legible; no title, count header, or explanatory footnote occupies the canvas. | Arial 8 pt, fixed complete canvas, separate caption. | Accepted. |
| note | Palette and summary layers | Blue, coral, and teal dots remain distinct on white; light boxes provide summary context; low-contrast gridlines lie below the marks. | Clear hierarchy and declared mark outlines. | Accepted. Box boundary strokes define quartiles; individual circles are borderless. |

The actual PNG was viewed at its complete 120:90 proportions. Physical-size text
and mark dimensions were checked from export records; screen zoom alone was not
used to certify physical font size. Observed data occupy a balanced portion of
the canvas without a spare title or legend band. Direct group labels replace
an unnecessary legend. Point/summary overlap is intentional and does not hide
the raw distribution.

## Separate numerical and export evidence

`verification.json` records independent arithmetic and file measurements:

- **Passed:** raw current reads joined by literal IDs, independently recomputed
  available-read means, all 36 unique IDs and 12 mice per arm retained, failed-read
  mouse 0008 retained, historical pilot and QC absent from scientific calculations.
- **Passed:** prepared-table hash agrees between analysis and rendering; rendered
  values and ID strings match the exact prepared table, including leading zeros.
- **Passed:** mean, median, sample SD and inclusive quartiles independently
  recomputed using the standard library; Cliff's delta independently counted
  over all 144 dose/Vehicle pairs per comparison; asymptotic P values and the
  two-test Holm adjustment independently recomputed using the rank variance and
  the normal-tail formula.
- **Passed:** PDF is one complete 120 × 90 mm page with embedded ArialMT;
  extracted text is 8 pt. SVG is 120 × 90 mm within decimal serialization
  tolerance and retains 12 editable text elements in Arial 8 pt. PNG is
  1417 × 1063 pixels with 299.9994 dpi metadata (300 dpi after PNG rounding);
  all four canvas corners are white.
- **Passed:** renderer QA reports no clipped text, overlapping ticks, missing
  glyphs, marker boundary violations, spacing conflicts, or fallback placements.

## Limits and friction

This exact dataset and supported boxplot-with-points contract were checked.
No external biological claim, arbitrary-data generalization, publication
acceptance, or independent visual review is claimed. Rank-effect confidence
intervals are absent; boxes are data quartiles. The n = 12 per-arm Mann–Whitney
P values are asymptotic with continuity and tie correction, not exact
permutation P values. The data dictionary supplies the design; the tool cannot
prove biological independence.

The first preparation script assumed the failed-state literal was `failed`;
inspection revealed `instrument_failure`, and the validation condition was
corrected without changing data. Matplotlib initially could not write its
default home cache; the replay script directs its cache into this working
directory. The PDF verification library emitted a `fitz` API deprecation
warning but completed its text-size measurement. None of these changed the
chosen chart, values, typography, statistics, or output dimensions.
