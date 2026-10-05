# Developing EasyViz

The canonical runtime sources are in `skills/`. `plugins/easyviz/skills` links to them for local development; the builder materializes a standalone copy in `dist/easyviz/`. Edit the source once, then rebuild. Generated distribution files are ignored by Git.

## Run and validate

For development and full figure checks, use Python 3.12 and the declared development dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python scripts/run_demos.py
.venv/bin/python tests/check_examples.py
.venv/bin/python tests/check_showcase.py
.venv/bin/python tests/check_generalization.py --strict
.venv/bin/python tests/check_legend_layouts.py
.venv/bin/python scripts/build_plugin.py
.venv/bin/python scripts/check_package.py
.venv/bin/python tests/check_plugin.py
```

`run_demos.py` writes synthetic fixture outputs under `evals/fixtures/`. `check_examples.py` validates the two historical code-assisted conversions. The advanced create and image-data reproduce scripts include their own data/export checks; invoke the `plot.py` in the corresponding example directory. Inspect the resulting PNG or rendered PDF in addition to numerical checks.

## Workflow helpers

Create starts with a basic single plot. `create_style.py` fills missing cosmetic
choices in new unprofiled drafts and previews; explicit overrides take
precedence. `crisp` is the default and `legacy` is available for earlier preview
fallbacks. Saved renderer specifications are not rewritten. Run the five
[basic-panel cases](../examples/create/basic-panels/README.md) before accepting
changes to observation boundaries, box widths, bar outlines or violin summaries.

Core and focused renderers write advisory `qa.readability` measurements from
`panel_readability.measure(fig)`. Custom code may call it after final layout.
It records actual physical mark spans, effective contrast against a uniform
background, stroke widths and legend bounds without modifying artists or QA
pass/fail. Thresholds are configurable review cues; inspect actual images for
occlusion, heatmap semantics, text and color accessibility.

Keep two tracks. In create, [inspect_data.py](../skills/easyviz/references/data-exploration.md) inventories prepared CSV/TSV/XLSX data and proposes concrete reading tasks; [analyze.py](../skills/easyviz/references/statistical-analysis.md) executes an adopted descriptive or inferential plan separately from drawing. Preserve literal IDs, source values, experimental-unit declarations, exclusions, effect direction and comparison families. Unknown design supports descriptive previews, not inferred independent sample counts.

In reproduce, stage the supplied reference and user tables with [reference_packet.py](../skills/easyviz/references/reference-to-code.md), obtain a fresh image reading, adopt each layer and map it to code. Implement unfamiliar geometry explicitly. A paper's Source Data or author code is not an entry requirement; published Source Data cases provide auditable learning and numerical validation evidence.

The shared [figure workbench](../skills/easyviz/references/figure-workbench.md) serves either track from `127.0.0.1`. It saves selected-element or millimetre-region instructions in `requests.json` bound to the inspected SVG version. The Agent edits the spec/profile or script, preserves the accepted attempt, and rerenders all requested formats. Custom scripts can register real artists with `figure_elements.py`; an SVG without a matching manifest still supports general and region notes. Keep semantic source keys and quantitative mark geometry tied to the data.

## Extend a chart family

1. State the source-table contract, units, experimental unit, and supported encodings.
2. Add configurable mappings and explicit transformations. Do not turn one paper's selection or denominator into a default for unrelated data.
3. Reuse final-size export rules and save actual fonts, colors, dimensions, and statistics.
4. Exercise meaningful failure cases such as incorrect denominators, missing pairs, invalid values, and clipped content.
5. Inspect real output, then add the implementation and its applicability limits to the chart library.

A custom multi-layer panel can be a useful reusable case without becoming a generic renderer option. Keep a focused implementation when generalization would hide assumptions.

The six focused interval, paired, replicate-bar, ECDF, time-course and annotated-matrix scripts extend the five core
families without enlarging the core schema. They share physical layout,
font/export and legend helpers, and retain their own source/layer audits.
Exercise complete repeated conditions, literal IDs, component completeness,
sample-SD definitions, ties, exact cumulative jumps and supplied band endpoints when changing them.
For annotated matrices, check keyed strip colors, observed/unmeasured/unsupplied
states, omission denominators, supplied tree vertices and actual transformed
alignment. Custom compound panels can reuse `aligned_layers.py` without
introducing automatic clustering.
For step functions, check exported SVG/PDF paths: correct in-memory vertices
do not prevent a backend from simplifying small steps. ECDF export explicitly
disables path simplification and tests the actual vector vertices.

The time-course recipe accepts supplied estimates with nonnegative SD or
explicit containing endpoints. Test irregular x spacing, per-series sorting,
literal categories, log-scale positivity and the actual ordered line/band paths.
Its optional dual-axis contract requires one series per axis and labelled
quantities/units; it does not fit models or derive uncertainty from raw data.

Legend proportions use the shared `skills/easyviz/scripts/legend_layout.py` helper. Development cases link to that source; the case sync and plugin build materialize standalone copies. Edit the canonical helper and rerender dependent cases before packaging. Check actual exported symbol geometry as well as numeric marker settings, especially when interactive and export DPI differ.

## Evaluate transfer

The core's optional measured layout and validated first-panel entry point have
transfer and independent forward-use evidence under
[layout-fit](../evals/layout-fit/README.md). Treat cell annotation fit as part of
candidate feasibility, rather than checking it only after selecting a guide
placement. These checks preserve physical size and fonts; they do not certify
aesthetic superiority or a particular model's performance.

Test changed data shapes, label lengths, category counts, scales and missing-value meanings, not only a second rendering of the same example. Preserve baseline failures and distinguish valid transfer, explicit rejection, a fixable layout problem, and a genuinely unsupported layer. Successful validation covers only the recorded contracts. A new agent using the skill on an unfamiliar chart can test the workflow separately from the core renderer; record its inputs, actual file access, custom implementation and independent output review. Synthetic fixtures are engineering evidence, never additional biological studies.

## Add a no-author-code evaluation

The [Source Data workflow](../skills/easyviz/references/literature-source-data.md)
includes Nature-family cases for scatter, intervals, paired observations,
replicate components and supplied time-course summaries. Source-sheet selection, direction, filtering and uncertainty
definitions remain case metadata rather than defaults in those scripts.
Mapped circle sizes record actual geometric fill area separately from the
Matplotlib parameter; legacy fixed markers/custom recipes retain their older
parameter convention explicitly. Interval geometry checks include actual
line/cap strokes, and source hashes are rechecked after export.

Keep the reference image, request, data dictionary, and source data in `evals/reproduce-inputs/<case>/`. Record image crop coordinates, original source hashes, source terms, and table-to-panel mapping. Do not extract original plotting code.

Give a fresh reader only the image, request, and permitted semantic context. Give a separate implementer its specification and the source data. Preserve the first rendering. Give another reviewer the actual candidate and reference with the adopted requirements. Record real access boundaries; instruction-based isolation is not an operating-system sandbox.

An accepted result may retain documented differences when the original density estimator, normalization, font, radial origin, or editorial changes cannot be established. Match scientific meaning and traceable data before visual details. Never tune data to improve visual similarity.

## Distribution

The plugin includes the main workflow, two helper skills, palettes, layout presets, runtime scripts, synthetic fixtures, and selected CC BY examples. Full paper archives and author scripts are not bundled. Check source terms before adding case data to the package.

The plugin manifest lives at `plugins/easyviz/.codex-plugin/plugin.json`. The build records the ZIP checksum, a path-and-content checksum, and file count in `dist/build.json`. Entries use fixed timestamps and permissions, so identical files produce the same ZIP under the same packaging runtime regardless of checkout timestamps. A build is a packaging result; it does not imply marketplace publication, installation, or end-to-end validation in a fresh Codex session.

The GitHub `Core checks` workflow runs the numerical, source-contract, geometry and export unit tests, builds the plugin on Linux, then validates ZIP paths, manifest resources, all three skill entry points and an extracted core render from a separate working directory. The smoke render explicitly selects bundled DejaVu Sans and checks canvas/export QA. It does not compare Linux font substitutions pixel-for-pixel with the Arial previews produced on macOS or replace actual-image review. Full pixel reproduction remains in `tests/check_plugin.py` on the recorded macOS/font environment.

The package smoke also runs the extracted draft/measured-layout workflow and
selected Source Data case wrappers outside the checkout, with an explicit
DejaVu Sans override and unchanged physical sizes. Their original Arial
candidate images retain separate independent visual/export evidence.

For practical external-agent checks, freeze the skill snapshot and run a new
supported task with changed source-column names or data shape. Inspect the
actual output, repair concrete issues in the reusable tools or instructions,
then record any follow-up run against its own snapshot. The main outcome is
a repo improvement and a usable panel. Preserve the model's original outputs
and the failures that led to a fix.

Matched with/without-skill requests and anonymous comparisons answer the
separate question of skill effectiveness. Earlier [WorkBuddy pilot records](../evals/workbuddy/README.md)
retain that design and its negative results. Report numeric correctness,
visual preference and displayed effort separately; task trials alone do not
establish a gain across models.

The completed [GLM interval comparison](../evals/workbuddy-glm/README.md)
identified narrow data space with multiple automatic guides. The subsequent
[multiple-guide engineering check](../evals/multiple-guide-layout/README.md)
preserves before/after runtimes, changed-field probes, actual export geometry,
legacy pixel checks and a separate anonymous image review. It supports a
specific helper improvement, while retaining the original model comparison.

## Local installation and release records

For an installation request, follow [INSTALL.md](../INSTALL.md). `python scripts/install_plugin.py --build` builds using the standard library and refreshes the personal local plugin through the detected Codex CLI. The installer preserves other catalog entries, copies the package to a stable local source, backs up previous EasyViz files, and checks the installed cache and enabled state. `--home <temporary-directory>` isolates installer verification; it does not change the real OS home or desktop installation.

For each release, set the manifest version before building and record the archive SHA-256, file count, source commit, the checks actually run and any installed-client checks. A published version identifies one archive; changes after publication need a new version. Keep historical QA attached to its original archive rather than changing its hashes to match a later build. A metadata-only change can reuse relevant numerical/visual evidence with an explicit scope statement, while validating the changed manifest, package and installation. Plugin discovery in a fresh client is separate from runtime and image checks.

The historical initial release evidence is under `evals/release-qa/`; it identifies its original 0.1.0 archive. Later releases must identify their own archive and applicable checks. GitHub release publication and public plugin-directory submission are separate from building or local installation.

The [0.4.3 QA record](../evals/release-qa/v0.4.3/README.md) records this version's checks and archive identity. Do not carry an earlier archive's checksum or successful CI status forward to a new build.
