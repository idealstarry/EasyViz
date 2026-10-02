# Source Data quality update, 2026-10-02

## New reviewed cases

- [Xiang area scatter](../../examples/no-author-code/xiang-bubble-volcano/README.md):
  official Nature Communications Figure 3E source data; 1,457 supplied rows,
  including 37 zero-area observations. Preserve supplied coordinates and classes.
  The source workbook already contains two date-converted identifiers; they are
  disclosed, not guessed back into gene names. A separate nine-row synthetic
  probe exercises renamed fields, interleaved categories and automatic layout.
- [Vabistsevits interval panels](../../examples/no-author-code/vabistsevits-forest/README.md):
  official Nature Communications Figure 3a/b source data; 48 supplied estimates
  and asymmetric intervals. Sample sizes are blank and remain unknown. The
  second panel is a same-study transfer, not a second independent study.

Both cases use fresh independent reference readings and recorded adopted
specifications, with captions separate from manuscript panels. Independent
actual-image reviews found no blocking issues. Their notes retain dense overlap,
small/pale marks, source limitations and the limits of a screen-size proxy.
Their independent export audits examine actual coordinates, shapes, colors,
fonts and dimensions. They do not certify aesthetics or upstream analysis.

## Generic tools changed

- Mapped scatter size and dot size now record geometric circle fill area,
  Matplotlib's size parameter and physical diameter separately. Size legends
  use the same conversion. Legacy fixed marker conventions remain explicit.
- The supplied-interval renderer supports renamed fields, sparse label/series
  combinations, linear/log axes, asymmetric intervals, independently decoded
  colors and supplied/reference-overlap fill states. It does not infer n or
  recompute estimates. It checks actual line/cap strokes and verifies source
  bytes again after export.
- Explicit `statistics.method = "none"` supports prepared descriptive inputs.
  First-panel and measured-layout helpers preserve requested dimensions/fonts
  and reject infeasible label fits; image review determines readability.
- Multiple automatic guides now compare right, bottom and top placements.
  Complete guide envelopes stack without collisions, while explicit positions
  stay fixed. [Separate engineering evidence](../multiple-guide-layout/README.md)
  includes preserved before/after runtimes and an independent anonymous review.

## Recorded validation

The final unit suite passed **114 tests** in the recorded local Python environment,
including the updated installer and multiple-guide regressions. Six synthetic
core demonstrations were rerendered, and actual dot
outputs were inspected. Independent reviewers rechecked the identified interval
alpha, stroke and source-change bugs after their fixes.

The final local 0.2.0 build contains 252 files, ZIP SHA-256
`4686550a79030356d95960ac899e60c37fd6968f8eb76d2bd6112a9702d3d0b6`.
The extracted core, specification/layout entry point and both new case wrappers
passed `check_package.py` using an explicit DejaVu Sans override. Additional
[portable regression checks](source-data-package-validation-multiguide.json) passed
on this archive. Both new paper cases, including the second interval panel,
were rerendered from clean extracted copies using the latest runtime and matched
their original reviewed Arial PNG pixels exactly. Independent export auditors
then passed without original workbooks or development history; see
[portable auditor evidence](portable-source-data-auditors-multiguide.json).

The earlier `source-data-package-validation.json` remains evidence for its
different 251-file `dcfdc0e9…` archive. The prior `*-final.json` regression and
`portable-source-data-auditors.json` identify the intermediate 252-file
`57106451…` archive. Their identities were not rewritten. These local packaging checks do not imply
publication, installation, a fresh client discovery check or Linux/Arial pixel
identity. Reviewed paper previews retain their own original hashes and fonts.

## External-agent evidence

[WorkBuddy evaluation](../workbuddy/README.md) addresses the separate question
of whether using EasyViz improves an external model's figure on unfamiliar
data. The completed Deepseek dot pair had correct numeric/export results in
both arms, but the blind visual reviewer preferred the direct-code panel.
Its frozen original results are retained; later tool fixes are not attributed
retroactively to that run. The separate completed [GLM interval pair](../workbuddy-glm/README.md)
also favored the direct-code panel visually, while EasyViz retained the exact
requested canvas and the baseline had a small size drift. Both preserved all
eleven supplied values and endpoints. The GLM comparison identified a multiple-
guide placement limitation, addressed in separate local engineering work;
those later changes do not alter either frozen model result.
