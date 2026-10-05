# Design notes · PROGENy signature relationships

## Why these layers

| Reading task | Chosen encoding | Scientific boundary |
| --- | --- | --- |
| Locate overlaps across every pair, including absence | Count-labeled lower triangle with a shared sequential scale | The diagonal would dominate the scale with 100; self-overlaps are omitted explicitly, not silently rescaled. All 48 zero pairs remain visible. |
| Inspect actual weights in the two largest overlaps | Gene-identified paired-coefficient points with zero/equality guides | Selection is strictly >10 shared genes, yielding all 62 + 18 genes. These paired values justify a scatter; no correlation or fitted line is added. |
| Separate overlap amount from signed agreement | Seven aligned same-sign fractions with numerator/denominator labels | Empty pairs have undefined agreement; one shared gene does not establish robust evidence or causal cross-talk. |

The full source and the seven unplotted shared-gene coefficient pairs remain
available. Jaccard is recomputed and saved but is not another redundant in-image
scale: all signature sizes are 100, so its ranking matches shared count.
The current sparse model motivates this arrangement; a denser signature model
or a gene-ranking question can require a different view. This is an adaptable
source/derivation/artist contract, not a mandatory heatmap or scatter recipe.

The first row's isolated EGFR label and empty upper half are intentional
half-matrix geometry. They do not encode missing data: each cross-pathway
comparison appears exactly once below the diagonal, while the complete
coefficient matrix is preserved.

## Literature observations and intentional differences

The [original Figure 2 crop](references/progeny-figure2-reference.png) was
actually inspected. Its compact matrices use shared row/column labels, distinct
seams between discrete cells, local significance marks, and separate guides
for different quantities. Its neutral bar panel uses a clear numerical axis.
Here the count matrix adopts shared decoding and discrete seams, while the
count scale, zero coefficients, pair selection and sign fractions come from
the new scientific question. Original Wald statistics, activation scales,
significance marks and experimental relationships are not transferred.
The new continuous scale is one bright blue family; hue does not imply
pathway identity. Signed coefficients retain zero on their actual axes rather
than acquiring the original paper's activity colorbar.

The source crop is Schubert et al., [Nature Communications 9, 20
(2018)](https://www.nature.com/articles/s41467-017-02391-6), Figure 2,
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It is cropped from
the user-supplied PDF with marks unchanged. This is a comparison of transferable
design mechanisms, not matching numeric outputs or proof of CNS quality.


The adopted 190 × 112 mm canvas and 8 pt text were fixed before the first candidate. Three actual visual passes corrected the lower-label anchors and CXCL8 association without changing numerical coordinates. Dense true near-origin coefficients remain unjittered; the fraction lane keeps every denominator. Historical candidates and full review evidence remain in the [source repository](https://github.com/idealstarry/EasyViz/tree/main/examples/create/pathway-signatures).
