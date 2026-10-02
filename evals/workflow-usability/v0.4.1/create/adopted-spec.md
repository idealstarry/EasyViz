# Adopted create task

Question: How do the two dose arms' mouse-level signals distribute and shift
relative to Vehicle?

Three appropriate directions were considered:

1. **Boxplot with all individual mice (selected):** `group` on the categorical
   axis, `mean_signal` on the signal axis. Shows central distribution, spread,
   overlap, and every experimental unit without density smoothing.
2. **ECDF by group:** same fields; reads tails and proportions at/below a signal
   threshold. It preserves all observations but individual units are less obvious.
3. **Effect plot versus Vehicle:** dose contrasts with effect size and supported
   confidence intervals would emphasize change magnitude, but would need a
   compatible effect/interval estimator and provides less direct distribution
   evidence. No interval is manufactured from the chosen rank method.

The selected single panel uses 36 independent mouse means, with 12 per group,
ordered Vehicle, Low dose, High dose. The ID lookup uses literal `tube_key`.
Numeric values are background-corrected fluorescence in arbitrary units.
Two technical reads are averaged within each mouse using available measured
values; the single failed read is not zero and its mouse is retained. The pilot
and QC tables are not part of the scientific plot or inference.

The complete canvas is 120 × 90 mm, white, Arial 8 pt, 300 dpi. Export PDF, SVG
with editable text, and PNG. No title, panel letter, narrative, or overview count
is inserted. Group names directly decode colors without an extra legend.
Individual circles are borderless, 4 pt diameter (Matplotlib `s=16`); light-filled
boxes have 0.6 pt group-colored boundary lines defining quartiles, with dark
median lines and whiskers to observed values within 1.5 IQR. Summary boundaries
are a separate line encoding, intentionally distinct from individual marks.
The physical beeswarm changes only the categorical coordinate and uses a 0.3 pt
edge gap. Gridlines stay below marks. Planned inference is two-sided
Mann–Whitney, two dose-versus-Vehicle comparisons as one Holm family, with
Cliff's delta in the dose-minus-Vehicle direction; no effect CI is computed.
