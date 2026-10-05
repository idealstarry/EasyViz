# EasyViz v0.4.4 release QA

The original publication hold after Linux Core checks failed was superseded by
the user's authorization to finish and release 0.4.4, 0.4.5 and 0.4.6. Current
local checks use Python 3.12.2 on macOS; publication also requires successful
GitHub Core checks for the release commit. See the
[release](https://github.com/idealstarry/EasyViz/releases/tag/v0.4.4) and its
commit checks for the authoritative publication state. The original published
v0.4.3 tag and package remain unchanged.

| Current check | Evidence |
| --- | --- |
| Full runtime suite: **575 tests passed** in 269.866 s | [Unit log](unit-tests.log) |
| Consumed-source/spec/helper/code checks, strict CSV and exact large-value normalization independently reviewed | [Runtime review](prepublication-integrity/independent-runtime-review.md) |
| PNG scanlines: 150 independent real-decode probes; 28 regression tests; unchanged successful custom review retained | [PNG review](prepublication-integrity/independent-png-review.md), [forward check](prepublication-integrity/png-forward-check.json) |
| Snapshot capture and restore QA guards: 24 application tests and actual unchanged PNG/PDF/SVG probes | [Actual after-repair evidence](../../development-v0.4.5/workbench-audit/reviewer-production-snapshot-after/evidence.json) |
| Current code review: 47 intake tests and 7 critical layout/state tests independently passed | [Code review](../../create-purpose-overhaul-v0.4.4/code-review.md) |
| Known font regression: 30 focused tests; actual PNG/SVG exports checked | [Diagnosis](../../create-purpose-overhaul-v0.4.4/font-layout/diagnosis.md) |
| Actual new font images independently inspected; explicit locked failure retained | [Image review](../../create-purpose-overhaul-v0.4.4/font-layout/independent-image-review.md) |
| Raster review: 21 focused tests; 9 branches independently rerun; original real spacing failure retained | [Independent review](../../create-purpose-overhaul-v0.4.4/raster-review/independent-review.md) |
| Repair-outcome source values, statistics and five new individual panels reviewed | [Case overhaul](../../create-purpose-overhaul-v0.4.4/repair-outcomes/README.md) |
| New real Source Data first-finished exercise; both outputs independently inspected and numerically verified | [Exercise review](../../create-purpose-overhaul-v0.4.4/fresh-run/independent-review.md) |
| Current source, README image and portable resource links pass | [Resource check](resource-links.json) |
| Portable ZIP: 854 files; extracted runtime and cases passed | [Build metadata](build.json), [package check](package-check.log) |
| Authorized local source/cache copies match all 854 package files and remain enabled | [Local installation](local-install.json), [content check](installed-content-check.json) |
| Future unreviewed development revisions are omitted from the archive | [Curation check](prepublication-integrity/package-curation-check.json) |

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
code regressions. The current full log above runs all 575 tests with loopback
permission and passes. The 550-test prepublication state is retained separately;
the current 575-test run also covers the source, PNG and snapshot repairs below.

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

## Prepublication reliability repairs

An independent forward audit reproduced source replacement, malformed CSV
index inference, unsigned and floating-point composition-sum overflow, and a
PNG with dimensions but no image data. The
[original evidence and actual repaired exports](../../development-v0.4.5/runtime-audit/README.md)
retain both outcomes. The core now parses/hashes the same captured source and
spec bytes, compiles the same captured helper bytes, rejects stale self bytecode,
checks continuity before and after export, and preserves literal source CSV
separately from plotting data. Exact decimal totals produce correct proportions
for the large valid inputs; unrepresentable positive fractions fail explicitly.

The PNG helper checks bounded filtered scanlines and physical geometry, without
claiming exhaustive PNG conformance or appearance inspection. Captured source
snapshots are bound when declared; legacy custom review records retain their
unchanged shape. Existing-source snapshot acceptance also verifies the bytes
actually copied, and restoration verifies the accepted QA digest and declared
exports before creating output. Custom no-map handoff and full auxiliary-input
support remain separately developed 0.4.5 work; they are not claimed here.

The extracted-package check caught a legitimate explicit font override being
bound to the unchanged case specification. The wrapper now saves the adopted
specification and original-font override provenance. A concurrent new 0.4.6
development revision also exposed an overbroad recursive case copy; named
development revisions are omitted until separately reviewed and curated.
The final 854-file archive is checked directly, with no such entries.

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
Files named `*-before-prepublication-integrity` preserve the 550-test state and
its installed archive. The [prepublication folder](prepublication-integrity/)
also retains intermediate successful checks and actual failed package evidence;
they describe their own frozen source scope, not the final release.

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
The authorized public release contains only the plugin ZIP; there is
no separate checksum download. Starting a new chat is needed to load a newly
installed Skill version. Successful CI is a technical check; it does not prove
aesthetic superiority or statistical validity on an unknown study.
