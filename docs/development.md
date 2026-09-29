# Developing EasyViz

The canonical runtime sources are in `skills/`. `plugins/easyviz/skills` links to them for local development; the builder materializes a standalone copy in `dist/easyviz/`. Edit the source once, then rebuild. Generated distribution files are ignored by Git.

## Run and validate

Use the environment described in the root README.

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python scripts/run_demos.py
.venv/bin/python tests/check_examples.py
.venv/bin/python tests/check_showcase.py
.venv/bin/python tests/check_generalization.py --strict
.venv/bin/python tests/check_legend_layouts.py
.venv/bin/python scripts/build_plugin.py
.venv/bin/python tests/check_plugin.py
```

`run_demos.py` writes synthetic fixture outputs under `evals/fixtures/`. `check_examples.py` validates the two historical code-assisted conversions. The advanced create and image-data reproduce scripts include their own data/export checks; invoke the `plot.py` in the corresponding example directory. Inspect the resulting PNG or rendered PDF in addition to numerical checks.

## Extend a chart family

1. State the source-table contract, units, experimental unit, and supported encodings.
2. Add configurable mappings and explicit transformations. Do not turn one paper's selection or denominator into a default for unrelated data.
3. Reuse final-size export rules and save actual fonts, colors, dimensions, and statistics.
4. Exercise meaningful failure cases such as incorrect denominators, missing pairs, invalid values, and clipped content.
5. Inspect real output, then add the implementation and its applicability limits to the chart library.

A custom multi-layer panel can be a useful reusable case without becoming a generic renderer option. Keep a focused implementation when generalization would hide assumptions.

Legend proportions use the shared `skills/easyviz/scripts/legend_layout.py` helper. Development cases link to that source; the case sync and plugin build materialize standalone copies. Edit the canonical helper and rerender dependent cases before packaging. Check actual exported symbol geometry as well as numeric marker settings, especially when interactive and export DPI differ.

## Evaluate transfer

Test changed data shapes, label lengths, category counts, scales and missing-value meanings, not only a second rendering of the same example. Preserve baseline failures and distinguish valid transfer, explicit rejection, a fixable layout problem, and a genuinely unsupported layer. Successful validation covers only the recorded contracts. A new agent using the skill on an unfamiliar chart can test the workflow separately from the core renderer; record its inputs, actual file access, custom implementation and independent output review. Synthetic fixtures are engineering evidence, never additional biological studies.

## Add a no-author-code evaluation

Keep the reference image, request, data dictionary, and source data in `evals/reproduce-inputs/<case>/`. Record image crop coordinates, original source hashes, source terms, and table-to-panel mapping. Do not extract original plotting code.

Give a fresh reader only the image, request, and permitted semantic context. Give a separate implementer its specification and the source data. Preserve the first rendering. Give another reviewer the actual candidate and reference with the adopted requirements. Record real access boundaries; instruction-based isolation is not an operating-system sandbox.

An accepted result may retain documented differences when the original density estimator, normalization, font, radial origin, or editorial changes cannot be established. Match scientific meaning and traceable data before visual details. Never tune data to improve visual similarity.

## Distribution

The plugin includes the main workflow, two helper skills, palettes, layout presets, runtime scripts, synthetic fixtures, and selected CC BY examples. Full paper archives and author scripts are not bundled. Check source terms before adding case data to the package.

The plugin manifest lives at `plugins/easyviz/.codex-plugin/plugin.json`. The build records the ZIP checksum and file count in `dist/build.json`. A build is a packaging result; it does not imply marketplace publication, installation, or end-to-end validation in a fresh Codex session.

The GitHub `Core checks` workflow runs the numerical, source-contract, geometry and export unit tests and builds the plugin on Linux. It does not replace actual-image review or compare Linux font substitutions pixel-for-pixel with the Arial previews produced on macOS. Full release evidence and the exact archive checksum are recorded under `evals/release-qa/`.
