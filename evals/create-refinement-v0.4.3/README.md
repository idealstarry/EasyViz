# Create refinement within EasyViz 0.4.3

The version stays **0.4.3**. These are subsequent source changes on `main`;
the published `v0.4.3` tag and its original release ZIP remain historical
snapshots. Follow the repository's [INSTALL.md](../../INSTALL.md) to install
the current maintained checkout, rather than assuming equal version strings
identify equal package contents. Build and installed-content hashes record the
actual update.

## Design decisions

| Panel | Problem in the published candidate | Adopted revision |
| --- | --- | --- |
| [Box](../../examples/create/basic-panels/cohort-box/output/panel.png) | Points cover summary lines; three narrow point groups occupy a widely spaced region. | Open quartile boxes, clear median/whiskers and a same-color neighboring raw-point lane. Explicit 4 pt² points retain every observation; final-size review checks their visibility. |
| [Violin](../../examples/create/basic-panels/cohort-violin/output/panel.png) | Wide saturated density contours compete with points and inner summaries. | Narrow thin neutral contours, colored quartile boxes, dark medians and neighboring raw points. The Gaussian Scott KDE, 100 evaluation values and observed-range trim stay unchanged. |
| [Heatmap](../../examples/create/basic-panels/depot-heatmap/output/panel.png) | Three columns stretch across the available width, while full column names crowd together and low shares are hard to read from hue. | A 28.6 × 71.28 mm matrix; 9.53 × 4.455 mm cells, short defined headers, 0.35 pt vector seams and 48 source-derived labels. The original linear 0–40% scale and full-precision color mapping stay unchanged. |

The main README presents three new narrow repair-outcome bar panels, then the
box example and other basic families. The same-data violin remains an
alternative view. The original single-HDR bar and paired scatter retain their
prior designs; no improvement is claimed for those two existing cases.

scWAT Fig. 2c/i/j (PDF p. 4) provides an observed mechanism for distinct
observations, summary edges and intervals. PROGENy Fig. 4c (PDF p. 6) provides
an observed contour/inner-summary hierarchy. Their different data and panel
contexts are not direct performance comparators. The references identify
specific design mechanisms and limitations in
[literature-style.md](../../skills/easyviz/references/literature-style.md).
Full paper pages are not bundled or republished.

## Comparison and validation

`before/` freezes three **actual published candidates**, including their specs
and PNG hashes from commit `5acbb5b36166b99097f2a0fffad321a4abf7c315`. These
are a stronger refinement comparator than the original omitted-option defaults;
they still do not represent a without-Skill agent experiment.

- [Independent visual review](independent-review.md): the reviewer opened the
  three actual predecessors, three new candidates, three real-source transfer
  probes, their six nominal-size PDF previews and two supplied paper pages.
  It preferred all three current candidates. A second formal pass checked
  strengthened heatmap seams; box/violin image hashes stayed unchanged.
  Status is `ready_with_notes`, with two of the three allowed formal passes used.
- [Numerical and export validation](validation.json): all 15 historical-default,
  current-candidate and changed-input probe runs pass. Source values and numeric
  artist coordinates, quartiles, matrix order, scales, actual PDF/SVG size,
  embedded font and PNG DPI are checked separately from aesthetic preference.
- [Distribution check](distribution-check.json): first-pass source fields and
  summary/KDE invariants are retained. Historical-spec geometry uses a replay
  through the same current renderer; it is not a parse of historical SVG geometry.
- [Heatmap check](heatmap-check.json): first-pass source/order/norm and annotation
  measurements. The final seam-color change is reflected in `validation.json`
  and the final review hashes, rather than silently overwriting that snapshot.
- [Legacy pixels](legacy-pixels.json): the tagged v0.4.3 and current runtimes
  produce identical RGBA pixels for all five saved core-chart fixtures plus
  the real grouped/stacked replicate examples when new options are omitted.
  [Eight additional replicate cases](legacy-grouped-pixels.json) test two/three
  components and filled/outline styles against the actual old tag, separately
  from aesthetic evidence. These are same-environment checks.
- [Unit checks](unit-tests.log): 429 tests passed, including shifted-layer
  capacity failures that preserve every row, both orientations, unchanged KDE
  numeric geometry, display aliases, true cell seams and omitted-option pixels.

The box/violin use 129 main observations and 185 in the four-cohort probe.
The heatmap retains 48 percentages; its probe uses 48 actual object counts with
a separately justified 0–2700 scale. Every panel remains 110 × 88 mm, Arial
8 pt, with a separate caption. New heatmap numeric text is a deliberately added
reading layer, so that comparison is not purely cosmetic.

## Portable behavior

New optional public settings are `point_category_offset`, `violin_width`,
`cell_border_color`, `cell_border_width_pt`, `column_labels` and the replicate
recipe’s `component_gap`. They preserve
old omitted-option geometry. Point shifts stay in the original category lane;
packing failures remain visible in QA rather than being repaired by dropping
observations. Display aliases retain actual column keys in selectable SVG
element metadata. The heatmap intensity image uses the existing raster layer;
its seams and text are editable vectors.

Review notes remain explicit: 2 pt observation diameters should not be reduced
further in these panels; trimmed KDE endpoints should not be cosmetically
invented; adding a value to every matrix cell is appropriate for this adopted
reading task, rather than a universal heatmap default. This evidence does not
establish model-wide aesthetic improvement, calibrated print quality,
color-vision accessibility or journal acceptance.

## Narrow manuscript subpanels and grouped-edge correction

The user rejected the first grouped-bar candidate for touching hollow edges
and poor proportions, then clarified a preference for slender individual
figure subpanels shown in parallel. That correction changed the design task.
The [new repair-outcome case](../../examples/create/repair-outcomes/README.md)
retains the 45 real values as three separate **60 × 62 mm** bar panels, all
Arial 8 pt, repeated source order and identical data rectangles. Their original
percent ranges are explicitly different: 0–15, 0–6 and 0–55. Compare treatment
responses within each outcome, rather than equal heights between outcomes.
The row preview joins existing vector panels without changing their size or
text. Two independent source-transfer panels retain 24 real values.

A corrected global-scale grouped alternative remains for absolute-outcome
comparisons. Public `component_gap` separates bars within an unchanged block
span; QA measures actual path clearance minus visible half-strokes after
layout. A positive requested gap can still fail if the strokes touch.
[Nine focused tests](grouped-spacing-tests.log) check source meanings, geometry,
invalid settings and the previously missed border-collision failure.

The [separate case review](grouped-review.md) preserves the first withdrawn
readiness judgment and the user-identified defect, then records actual
inspection of the corrected layouts. This is not a same-scale cosmetic
comparison between grouped and split views. The numerical
[case validation](../../examples/create/repair-outcomes/validation.json) checks
all means/SD/raw values, individual exports, embedded fonts and unchanged PDF
text positions in composition. Distinct SVG IDs keep panel clips independent.
Close repeated values can still make dots hard to count at nominal size; the
case does not establish journal acceptance or cross-model improvement.

## Package and local update

[Build identity](build.json) records a new 726-file 0.4.3 package. The original
release archive is unchanged. [Extracted package checks](package-check.log)
pass for documented APIs, analysis workflows, seven Source Data wrappers and
basic panels. A separate [same-environment replay](package-replay.json) renders
all ten basic candidates/probes plus the nine new individual, composed and
grouped repair-outcome outputs from a fresh ZIP. PNG, PDF, SVG and available
plotting CSV bytes match the reviewed checkout outputs.

[Installation](local-install.json) refreshed and enabled `easyviz@personal`.
[Installed-content verification](installed-content.json) independently checks
both the marketplace source and installed cache against every build file;
the version is still 0.4.3, so the content digest identifies this refinement.
Start a new chat to load refreshed skill instructions.
