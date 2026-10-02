# Adopted Figure 2b point/summary specification

The reference was read by a fresh independent agent from the actual official
PDF crop and permitted caption before selecting plotting code. Its observed
structure is four evenly spaced unconnected point distributions, pastel orange
for prior infection and blue for no prior infection, a logarithmic vertical
axis, and prominent median/Q1/Q3 overlays with shorter quartile caps.

Retain all 127 stable participant IDs and both raw values per ID. Map `yes` and
`yes/NCAP+` to the 64-person prior-infection group and `no` to the 63-person group,
retaining each raw classification. Do not read the supplied fold-change column
into the vertical concentration encoding. Use explicit `unit`, `condition`,
`value`, and `block` roles rather than paper-specific column names.

The adopted standalone panel is 105 × 96 mm with 8 pt Arial throughout. Its
vertical display spans 40–50000 BAU/ml with major power-of-ten ticks at 100,
1000, and 10000; all supplied values and physical point edges fit. Four category
positions remain equally spaced (`block_gap=0`). Circles have 10 pt² geometric
fill area, equivalent to Matplotlib `s=40/π`, and a 0.25 pt gray outline adopted
from the reference. Default generic paired plots remain borderless. Summary
lines are 0.8 pt, with median width 0.72 condition units and cap width 0.25.
Median and IQR calculations use raw values with a stated Weibull quantile rule;
the log display is applied only after those calculations.

The manuscript panel omits the source panel letter, boxed `IgG`, sample-count
prose and reported significance brackets. The source caption does not resolve
the paired-test transformation, so no test is performed. The two source dotted
guides have no meaning specified in the permitted caption. The full methods
report assay thresholds of 25.6 and 35.2 BAU/ml, which plausibly correspond to
the guides. Both lie below the adopted 40 BAU/ml lower display limit and below
every selected measurement, so the guides are omitted as a recorded adaptation. A small bottom
legend decodes the two cohorts for the standalone derivative; its full measured
footprint is kept outside the data region. These are recorded adaptations,
not a claim to have copied every graphical element of Figure 2b.

`connectors-spec.json` is a separately adopted view. It keeps the same data,
colors, summaries, dimensions and typography, changes the point placement to
deterministic shared within-unit jitter, and adds thin low-opacity individual
before/after segments. It is not a reproduction of an observed reference layer.

Automated checks reread the source and compare all actual plotted values,
source-row coverage, median/IQR endpoints, colors, circle geometry, and optional
connector endpoints. Independent final image review and export-level numeric
checks remain separate from the renderer's own QA.
