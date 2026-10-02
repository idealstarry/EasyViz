# Bounded visual review

Reviewed actual PNGs:
`output/panel.png` and `transfer/output/panel.png`, both exported at
210 × 111 mm, Arial 7.5 pt, 300 dpi. This review was performed by the plotting
agent; the earlier reference reading was independent and image-only.

The scientific panel preserves both matrix orders, narrow equal-width gene
columns, the aligned cosine bars, visible hollow interaction circles, orange
labels and two outlined ranges. Row labels and italic 90° gene labels are
legible; circle classes and both continuous scales decode without clipping.
All guides sit outside the data rectangles, and their complete text/key
footprints are recorded in `qa.json`. No title, panel letter, count banner or
explanatory image footnote was added. The grey baseline remains below bars
and circles.

The initial machine check flagged the expression key against an empty corner
of the lower axes' enclosing tight rectangle. Inspection showed no actual
label collision; the case now applies actual guide/text and guide/data
checks alongside shared footprint measurement. Data, canvas and fonts stayed
fixed. In the synthetic transfer, the initial long interaction label touched
the summary scale label; wrapping it as “Adjusted P / class” resolved that
actual text collision without changing dimensions, fonts or supplied values.
Both final exports pass the corresponding measured checks.

Residual adaptation: the dendrogram is missing because numerical topology and
heights are not in the source worksheets. Boxes therefore span the available
matrix/summary/label layers rather than an absent tree. Circle sizes and
physical panel size are adopted settings, not recovered source measurements.
This panel is not presented as complete image equivalence.
