# Adopted image-data reproduction

The fresh reader actually inspected the supplied reference crop and caption
before this case's implementation was selected. Its complete evidence is in
`reference-reading.md`; source numbers were not given to that reader. The main
Agent had inspected shared runtime scaffolding, which is disclosed in the
development access log. No author plotting code was accessed.

Retain the shared linear time axis, blue width on a left y axis, orange length
on a right y axis, thin mean lines, tiny filled sampling markers and pale
mean ± SD bands. Source Data establishes the 60 mean/SD summaries per curve;
the tiny markers represent these supplied summary times, never individual
cells. Use no standalone legend because the matching colored axes decode the
two quantities. Color values `#0072BD` and `#D95319` and band alpha 0.30 are
adopted visual estimates, not recovered author settings.

The fixed output is 100 × 76 mm, with 8 pt Arial axis/tick text. These are
explicit EasyViz settings rather than an inferred journal standard. Measure
both sets of axis text within the full canvas. Keep the top spine hidden,
ticks directed inward, and the bands behind the mean lines. Preserve editable
SVG text and use the same full physical canvas for PDF and raster exports.

Intentional adaptations: omit the source panel letter; keep scientific prose,
sample count, source credit and the dual-axis caveat in `caption.md`. Adopt
width limits 0.88–1.27 µm rather than the approximate lower reference boundary
of 0.9, because the first supplied lower SD bound is 0.89483241975895122 µm.
This displays the entire supplied band. Adopt length limits 1.5–5.5 µm and
time limits 0–60 min. Source coordinates and SD meaning are unchanged.

Implementation choice: a reusable numerical line-and-band recipe with explicit
field roles. It supports supplied SD or explicit lower/upper bounds, one
shared y axis or two explicitly assigned y axes, and complete numeric source
auditing. No smoothing, fit, test, imputation or inferred raw observations are
required. Straight segments and band edges connect adjacent supplied x values;
they do not add measured times or reconstruct missing trajectories.
