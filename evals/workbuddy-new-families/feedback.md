# Findings from the completed practical trial

This is feedback from one EasyViz-assisted ECDF task, without a control run or model score. The agent discovered the recipe from SKILL.md, mapped Chinese column names correctly, rendered all 254 supplied observations, and completed visibly without a supplemental prompt.

The frozen initial figure passed 10 independent checks, including the actual SVG and PDF curve segments at every source-derived empirical jump, fixed export dimensions, Arial text and editable power ticks. The audit uses an evaluator that imports no extraction code or plotting renderer. The initial image was also opened directly: the curves are clear, the ratio is balanced, and no visible label is clipped. The curve legend uses two vertically stacked entries and short line keys (about 1.78 mm actual stroke envelope); a longer adjustable line key is a reasonable focused aesthetic improvement.

Concrete wording problems remain in the frozen original agent result:

- The caption calls the marginal distribution at a time point an observational unit. The observation is one measurement from each participant at that time point; the distribution summarizes those observations.
- The report says repeated-value jumps are visibly retained. This input contains 127 distinct values per time point and zero multi-observation jumps. Exact empirical jumps were checked, but this real-data trial supplies no evidence about tied values. Separate capability tests are needed for that statement.

A traceability improvement also emerged: 22 original XLSX numeric lexemes are normalized in the plotting-data CSV (for example 5240.4399999999996 to 5240.44), although every parsed floating-point value is unchanged. The offered prepared.csv preserves the exact original text. Retaining a separate raw source-value text column would make export traceability more explicit without changing the curves.

These findings were sent to the repository maintainer. The ECDF documentation now requires true observation units and checking actual tie counts before example-specific claims. Its default curve line key is an adjustable 6 mm, and all three new plotting helpers retain raw numeric text in a separate column. The one updated-snapshot replay is preserved in iteration-2: its source/export audit passed 12 checks, actual SVG key centerlines are each 6 mm, all 254 raw value texts are retained, and caption/report now describe the units and absent ties truthfully. This is an intentional correction check, not independent replication or evidence of causal model improvement. The original frozen outputs and report remain unchanged.

A further operating issue appeared in that replay: shell working-directory reset led to one accidental rerun of the old helper into the old temporary output. The agent detected it and switched to absolute paths. A prior repo freeze allows independent verification that all 11 old runtime files are byte-identical to their original versions. Recipe examples should make the helper, data, spec and output locations explicit in each invocation, rather than rely on shell state persisting across agent calls.
