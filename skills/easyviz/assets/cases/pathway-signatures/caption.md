Signature overlap and paired model coefficients in the published 11-pathway
PROGENy model. The lower triangle shows all 55 unordered pathway pairs; integer
labels and the sequential color scale encode the number of shared genes with
nonzero coefficients. All 48 zero-overlap pairs are displayed as labeled zero
cells. Self-comparisons and the redundant upper triangle are omitted. Each
signature has exactly 100 nonzero coefficients; a shared count divided by 100
is therefore the fraction of either signature. Jaccard overlap is shared count
divided by the union count (200 minus shared count), and the complete derived
table retains this separate quantity.

The two coefficient plots display every shared gene in the two pairs with more
than 10 shared genes: NFκB–TNFα (62 genes) and EGFR–MAPK (18 genes). Coordinates
are the original unscaled signed model coefficients. The dotted line marks
equal numerical coefficients, rather than a fit; solid internal lines mark
zero. Axis ranges differ between the two pairs and are explicitly labeled.
One gene per plot is labeled by the largest sum of absolute paired
coefficients. The 80 displayed genes are selected from all 87 shared genes,
each of which belongs to exactly two signatures. Coefficients for the remaining
seven shared genes are retained in the full input and shared-gene table.

The aligned fraction plot includes every nonempty pair. A gene has concordant
signs when the product of its two nonzero coefficients is positive; the point
shows concordant count divided by shared count, and the adjacent fraction
states that numerator and denominator. Sign agreement is undefined for empty
pairs; those pairs have blank agreement values in the complete table and are
not plotted as zero agreement.

The full input contains 1,013 genes × 11 pathways (11,143 exact numeric
coordinates), including 10,043 structural zero coefficients set by the
published signature selection. A structural zero denotes an unselected model
coefficient, not an unmeasured expression value. These are descriptive model
properties, not measured pathway activity, biological replicates, or evidence
of causal pathway cross-talk. No pathway score, correlation, hypothesis test,
clustering or normalization is computed.

Source: Schubert et al., *Perturbation-response genes reveal signaling
footprints in cancer gene expression*, Nature Communications 9, 20 (2018),
[Supplementary Data 1](https://www.nature.com/articles/s41467-017-02391-6),
DOI: 10.1038/s41467-017-02391-6. Data are redistributed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The coefficient values
are unchanged; the overlap quantities and graphical arrangement are new
descriptive Create adaptations. The published Figure 2 depicts different
association and perturbation quantities and is not a reproduction target.
