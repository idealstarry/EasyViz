# EasyViz v0.4.4 draft QA

The user paused publication after Linux Core checks failed. This is a development
draft, not a published stable release. Current local checks use Python 3.12.2 on
macOS. The original published v0.4.3 tag and package remain unchanged.

| Current check | Evidence |
| --- | --- |
| Full runtime suite: **550 tests passed** in 260.900 s | [Unit log](unit-tests.log) |
| Current code review: 47 intake tests and 7 critical layout/state tests independently passed | [Code review](../../create-purpose-overhaul-v0.4.4/code-review.md) |
| Known font regression: 30 focused tests; actual PNG/SVG exports checked | [Diagnosis](../../create-purpose-overhaul-v0.4.4/font-layout/diagnosis.md) |
| Actual new font images independently inspected; explicit locked failure retained | [Image review](../../create-purpose-overhaul-v0.4.4/font-layout/independent-image-review.md) |
| Raster review: 21 focused tests; 9 branches independently rerun; original real spacing failure retained | [Independent review](../../create-purpose-overhaul-v0.4.4/raster-review/independent-review.md) |
| Repair-outcome source values, statistics and five new individual panels reviewed | [Case overhaul](../../create-purpose-overhaul-v0.4.4/repair-outcomes/README.md) |
| New real Source Data first-finished exercise; both outputs independently inspected and numerically verified | [Exercise review](../../create-purpose-overhaul-v0.4.4/fresh-run/independent-review.md) |
| Current source, README image and portable resource links pass | [Resource check](resource-links.json) |
| Portable ZIP: 854 files; extracted runtime and cases passed | [Build metadata](build.json), [package check](package-check.log) |
| Authorized local draft source/cache copies match all 854 package files and remain enabled | [Local installation](local-install.json), [content check](installed-content-check.json) |

## What failed and changed

[GitHub run 37318437850](https://github.com/idealstarry/EasyViz/actions/runs/37318437850)
ran 535 tests with one actual cross-font spacing failure. Arial passed locally;
Linux's fallback DejaVu used enough extra text space to prevent packing at the
retained summary width floor. The measured-margin repair uses only still-safe
omitted default padding, retains all source/science/font/size constraints and
keeps explicit geometry authoritative. Tests exercise real DejaVu, simulated
missing Arial, two DPIs and horizontal layout. The old failure is retained in
the [original CI log](../../create-purpose-overhaul-v0.4.4/ci-failure.log).

The first local full rerun produced 29 workbench setup errors because the
restricted execution environment prohibited temporary loopback servers.
[That log](unit-tests-restricted-sandbox.log) is environment evidence, not 29
code regressions. The current full log above runs all 550 tests with loopback
permission and passes, including the six added raster-review regressions.

A normal Matplotlib PNG also exposed a nearest-integer-only dimension error.
The repair accepts supported floor/nearest conversion, checks saved PNG fields
against actual bytes and keeps PDF/TIFF identity and real point-spacing checks.
[Diagnostic evidence](../../create-purpose-overhaul-v0.4.4/raster-review/owner-forward-diagnostic/diagnostic-summary.json)
records the untouched original exports. The initial trial's real spacing error
still fails; a successful final trial review remains compatible.

The first new build found a development-only relative evidence link in the
portable repair-outcome README. The case now links to its GitHub evidence page,
so the package does not require the development `evals` directory. The original
[package-check failure](package-check-before-case-link-fix.log) is retained;
this was a documentation resource error, not a plotting-runtime change.

## Evidence boundaries

The [original first-delivery evaluation](../../create-first-delivery-v0.4.4/README.md)
and [three-pass choice-space probe](../../create-choice-space-v0.4.4/README.md)
retain their own frozen runtimes, initial failures and subsequent repairs.
They are historical same-input evidence, not validation of the newer engine.
Logs named `*-before-purpose-review` preserve the 535-test pre-overhaul state,
its package and installed copy; they do not describe the current draft.
`unit-tests-before-raster-review.log` preserves the 544-test run before the
six final raster regressions. The current build and extracted-package evidence
are [build metadata](build.json) and [package check](package-check.log).

Actual image review, source/artist checks and export checks establish different
properties. Technical success and current-file identity cannot establish
publication aesthetics, statistical validity on an unknown study, beginner or
domestic-model effectiveness, or universal Skill improvement. The new local
one-input exercise is explicitly exploratory.

The earlier [workflow/code audit](../../create-first-delivery-v0.4.4/code-audit.md)
retains process-lock, ordinary rollback, source binding, installer/cache and
package/path checks. macOS/POSIX behavior was exercised; Windows was inspected
but not run. Ordinary exception rollback is not a power-loss transaction.

## Repeat checks

```sh
python -m unittest discover -s tests -p 'test_*.py'
python scripts/build_plugin.py
python scripts/check_package.py
```

Workbench and extracted-package tests require local loopback-server permission.
The public release, when approved, will contain only the plugin ZIP; there is
no separate checksum download. Starting a new chat is needed to load a newly
installed Skill version. Successful CI is a technical check and does not
remove the user's publication hold.

The local installation above is the reviewed development draft. It does not
change the latest published stable release, v0.4.3. The current chat may retain
its previously loaded Skill; a new chat loads the updated installed files.
