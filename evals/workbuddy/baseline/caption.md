# Figure caption

**Detected-cell fraction and prepared score for eight myeloid cell types across three treatment
arms.**

Every marker is one cell type × treatment arm combination from a supplied descriptive table (24
combinations, 8 cell types × 3 arms). Rows and columns follow the order in which the cell types and
the treatment arms first appear in the input; no combination was dropped, merged or reordered.
Marker **area** encodes *Detected fraction* on one shared 0–1 scale, drawn so that the geometric
area of a marker is proportional to the value (a value of 1.0 corresponds to a 5.6 mm diameter;
the radius is not the mapping variable). Marker **colour** encodes *Prepared score* through a
linear map from the smallest to the largest observed value (−0.22 to 1.66) on the viridis
colormap. Filled circles are proportional-value markers. The two combinations with an observed
*Detected fraction* of 0 — Resident macrophages in the Control arm and Cycling myeloid cells in the
Low dose arm — are drawn with a grey cross: a separate non-quantitative symbol whose area is
exactly zero, used instead of an artificially small positive value. The marker for Interferon
macrophages in the High dose arm represents a genuine near-zero value of 0.05 and is not a zero
annotation.

These are synthetic engineering test data. The two supplied quantities are descriptive values
rather than independent replicate measurements, so no statistical inference was performed and no
value was imputed, filled in, pooled, filtered or summarised. The quantity underlying *Detected
fraction* — which cells were counted and against which denominator — is not documented in the
input, and neither is the construction of *Prepared score* (its scale, its normalisation, and
whether a score of zero is meaningful). Both are therefore unknown; because no meaningful midpoint
can be assumed for *Prepared score*, the colour map is sequential rather than diverging.
