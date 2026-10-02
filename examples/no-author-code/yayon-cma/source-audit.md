# Source and artist audit

The bundled source is Fig. 3 Source Data for Yayon et al.,
doi:10.1038/s41586-024-07944-6, under the recorded CC BY 4.0 licence.
`inputs/provenance.json` records the official article/data URLs, original
workbook SHA-256, both prepared-table hashes, exact worksheet names, ordered
IDs and extraction transformations. Numeric strings and source-cell addresses
were retained in the prepared CSVs; no author plotting code was used.

`3f_cytokine_matrix` provides the two normalized matrices. The supplied
cosine similarities and corrected interaction P values come from
`3f_anova_cosine_sim`. These are prepared source values, not calculations
performed by this case. The official caption describes a two-way ANOVA with
Bonferroni correction; this script does not validate or rerun that study model.

Executed checks bind the original workbook hash and exact parsed matrix and
summary byte snapshots. The source audit re-reads the CSVs independently of
the artist registry and compares source-derived colors with actual patch
colors and transformed corners; supplied cosine values with bar heights,
baselines, centers and colors; and supplied P thresholds with actual circle
presence, areas, hollow style and transformed zero-line positions. All
1,300 cells and 65 summaries are checked. The actual 20 circles comprise
12 with P < .001, 4 with .001 ≤ P < .01 and 4 with .01 ≤ P < .05.

Actual upper/middle/lower column centers and spans match to the runtime's
0.01 mm tolerance. Display aliases do not change joined IDs; orange labels
and outlined endpoint ranges are specification-bound. PNG/PDF/SVG sizes,
fixed fonts, glyph availability and complete guide footprints are checked
separately. Source or spec changes during rendering invalidate QA.

The original tree's topology, merge heights, distances and branch-color rule
are unavailable in these worksheets. The tree is omitted, and no upstream
science or numerical information was inferred from reference pixels. The
recorded audit covers supplied data, artists and declared geometry only;
it does not independently certify expression normalization, experimental
units or the original ANOVA assumptions.
