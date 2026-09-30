# EasyViz 0.2.0 validation

Validated 2026-09-30, before committing the source update. The source base is `43d8ba3ab1f63e24e6a22716a121954a9d40f699` with the recorded working-tree changes. The package hash identifies the exact locally built and installed candidate independently of that base commit. Source publication is recorded in Git history; a downloadable GitHub Release and public plugin-directory publication are separate actions.

| Check | Result | Evidence |
| --- | --- | --- |
| Core, legend, case, profile, dot-state and installer contracts | 55 tests pass | [Result](unit-tests.json), [log](unit-tests.log) |
| Shared colors and quantitative scales | Category subsets/reorderings retain colors; equal quantities retain actual SVG marker dimensions across different panel dimensions and observed maxima; conflicts and degenerate named ranges reject | `tests/test_figure_profile.py`, [independent audit](audit.md) |
| Dot states | Every supplied row retained; zero, unmeasured and absent states distinguished; tiny positive dots retain exact area | [PNG](dot-states/panel.png), [settings](dot-states/settings.json), [QA](dot-states/qa.json), [caption](dot-states/caption.md), [audit](audit.md) |
| Standalone archive | 176 packaged files, three skill entry points, mandatory helpers and linked skill resources; extracted core render with DejaVu Sans passes | [Package smoke](package-smoke.json) |
| Existing portable cases | Extracted reruns retain the reviewed PNG pixels; transfer checks preserve values and intervals | [Package validation](package-validation.json) |
| Archive repeatability | Changing a source README timestamp leaves the ZIP unchanged under the same Python/compression runtime | [Build check](build-reproducibility.json) |
| Local installation/update | New installer used against the real desktop account; final cache content and enabled state verified; prior source and catalog backed up | [CLI result](local-installation.json) |
| Fresh backend skill discovery | All three 0.2.0 skills enabled from both repository and unrelated temporary working directories | [Discovery](client-discovery.json) |
| Agent-level value | Separate matched two-case pilot with source checks and anonymous review | [Pilot](../../skill-value/README.md) |

The final archive is `easyviz-0.2.0.zip`, SHA-256 `04af11cfa665ce08aa0f1ab120111d99f67ea724be1a7132d9e54ceb94c471d8`. Its path-and-content SHA-256 is `fe248eb970a62e8c09be8ddb85dec0f06d7f43857a43fce76020657f20630d0f`. These values are also in `dist/build.json` and the machine-readable [summary](summary.json).

The final update added source attribution after the first 0.2.0 installation. This changed only THIRD_PARTY_NOTICES.md in the package. The final archive was rebuilt, its extracted checks rerun, and the same version reinstalled with full content verification. Fresh skill-discovery evidence applies to the unchanged skill contents and cache paths. No interactive model turn or application plugin UI was inspected.

Checks ran on the recorded macOS Python 3.12.2 environment; dependency compatibility and all three skill-format validators passed. The Linux workflow now performs unit tests, packaging and an extracted DejaVu Sans core smoke, but this local pass is not a hosted Actions run. Historical 0.1.0 evidence remains unchanged. Neither test success nor a preferred pilot image establishes arbitrary-data quality or broad superiority over a capable Agent.
