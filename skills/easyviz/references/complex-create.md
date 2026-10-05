# Purposeful extra layers in Create

Use this guide when one basic panel cannot show the adopted comparison clearly.
Choose the question and supported quantities first. A richer example is useful
when its layers reduce a particular lookup or reveal a supplied relationship;
it is not the preferred answer merely because it contains more marks.

## Decide what the second layer adds

| Reading task | Useful organization | Check before drawing |
| --- | --- | --- |
| See individual samples and a defined group contrast across many features | A sample-level matrix with an aligned descriptive contrast lane | Preserve literal sample/feature IDs, the exact transform, group membership and the definition of the contrast. A difference of mean logs differs from the log of a ratio of means. |
| Compare response across irregular sampling times and compartments | Separate concentration axes with consistent genotype identity and exact-time summary anchors | Check units per compartment, numeric time spacing, independent versus repeated subjects, and SD/SEM/CI meaning. Do not connect raw individuals across times without a verified longitudinal identity. |
| Compare supplied coefficients for a scientifically relevant shared feature set | A pair-overlap overview plus selected coefficient relationships | Establish the selection rule, structural versus measured zeros, coefficient units and the denominator of every summary. A coefficient correlation does not establish pathway activity or crosstalk. |

Remove a companion that repeats the main view without helping the adopted task.
Separate manuscript panels can be easier to read than a composite. Preserve each
panel's physical size in any documentation preview; assembly remains optional.

## Transfer mechanisms, not a finished template

The [thermogenic expression case](../assets/cases/thermogenic-expression/README.md)
uses scWAT Figure 2b to learn the relationship between few sample columns,
many gene labels, a compact genotype band and a continuous guide. Its new
question uses absolute log2(TPM + 1) values and a separately defined descriptive
group contrast. It therefore retains observed zeros and does not inherit the
reference's row z scores, clustering or significance stars. The adjacent lane
shares the gene order and row centers so readers can relate sample variation to
the mean comparison without searching a second table.

The [compartment Ccl2 case](../assets/cases/compartment-ccl2/README.md)
learns definite raw-mark edges, compact within-group spacing and a readable
summary layer from Vanneste Figure 3c. Its Create task instead emphasizes time:
means and capless SEM remain at exact source hours, while compact raw columns
retain every terminal observation. Those display offsets must be decoded in the
caption; they are not extra time points. Distinct lung and serum units require
their own numeric axes. Near-coincident means need a visible summary treatment
at their true coordinates; a marker can obscure another despite correct values.

These are inspectable design exercises, not universal layouts. The source crop,
adopted specification, source contract, actual exports and checks in each case
explain which mechanism was observed and which choice is a new adaptation.
Use a different color role, summary treatment or organization when it better
answers the current question. Preserve an accepted project palette.

The [pathway-signature case](../assets/cases/pathway-signatures/README.md) starts
from supplied model coefficients. An overlap overview selects two supported
coefficient comparisons; actual denominators decode a descriptive sign summary.
It does not infer pathway activity, biological crosstalk or significance from
coefficient proximity. Structural zeros differ from missing measurements;
undefined empty-pair agreement and tiny denominators remain explicit.

## Plan shared geometry before styling

Record which panels share literal identity, which share a quantitative scale,
and which merely share visual decoding. Matching row centers supports a matrix
and its companion; separate concentration units cannot share numeric height.
Use actual label lengths, sample/category burden and visible mark footprints
to allocate the data rectangle and guide space within the adopted canvas.
Do not make a six-column matrix wide merely to fill available space or force
square cells on a long expression matrix.

Choose strokes by role: observations need recognizable edges, uncertainty must
remain visible beside its estimate, and a seam or reference line must not
dominate the values it helps readers compare. Select colors on the real marks.
A light area color may work with a definite contour but vanish as a tiny dot.
Use a sequential scale for adopted magnitude and a diverging scale only around
a meaningful adopted center. Keep zero, missing and absent states distinct.

After export, open the whole image and a nominal-size view when available.
Inspect near-equal summaries as well as extremes, dense and sparse rows,
endpoint markers, tick labels, guide range and the relationship between panel
body and text. Measurements can identify clipping or source mismatches; they
cannot select an aesthetic winner. Follow [First reviewed delivery](first-draft.md)
for new work and preserve actual later corrections as followups.

## Custom code remains part of the Skill workflow

Write focused code when the public recipes cannot express the chosen task.
Verify actual source-to-artist mappings and physical exports instead of making
a custom figure look like a native renderer's QA record. For local review,
use the [consumed-input handoff](figure-workbench.md) to capture declared input
bytes before plotting and bind the actual exports afterward. Register real
elements for click selection; without an element map, region/general requests
remain valid. Source continuity and complete metadata do not prove scientific
semantics, image inspection or publication quality.
