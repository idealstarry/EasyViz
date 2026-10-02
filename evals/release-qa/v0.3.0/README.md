# EasyViz 0.3.0 stable release validation

Validated on 2026-10-02 against the local working-tree candidate based on
`719ffdd5e9d72c7c38a4c811999ff4ca928215aa`. The published source is identified by
the `v0.3.0` tag. Package and source hashes in [summary.json](summary.json) bind
the checks below; earlier 0.2.0 development records retain their original hashes.

## Improvements included

- Four focused plotting tools: supplied intervals, paired observations,
  replicate components/supplied scalar values and exact empirical cumulative
  distributions. The five core chart families remain separate contracts.
- Real Source Data cases from four additional Nature-family papers, with fresh
  reference readings, declared adaptations, traceable inputs and captions.
- Physical circle-area mapping, measured layout, multiple-guide placement,
  exact vector steps and original numeric-text preservation.
- Machine-readable recipe discovery and actionable wrong-entry errors, plus
  absolute-path examples for Agent shells with changing working directories.
- Fresh generated-case synchronization prevents deleted/history files leaking
  into later packages; symlink checks cover the repository-to-target ancestry,
  while hand-maintained assets remain intact.

## Recorded checks

| Check | Evidence and scope |
| --- | --- |
| Full data/statistics/geometry/export/installer/discovery/sync unit suite | [Result](unit-tests.json), [raw log](unit-tests.log) |
| Extracted package resources and runtime | [Package smoke](package-smoke.json): four focused discovery routes execute, core and draft/measured-layout render, five real Source Data wrappers pass with explicit DejaVu Sans |
| Existing reviewed cases and changed-schema transfers | [Portable regressions](portable-regressions.json): isolated reruns, exact reviewed PNG pixels and retained quantities |
| Six newly reviewed views | [Portable new views](portable-new-views.json): wrapper-discovered extracted runtime, byte-identical reviewed PNGs, adopted Arial and PDF dimensions, unchanged CSV and equivalent JSON specs |
| Real compatible CLI installation | [Isolated installation](isolated-installation.json): 0.3.0 cache content and enabled state verified in a temporary home |
| Repeat build | [Build repeatability](build-reproducibility.json): fresh case regeneration produces the identical ZIP |
| Independent source and actual vector geometry | [New family audit](../../reproduce-inputs/new-families-audit/source-and-exports-final.json): 60/60 checks on original traced candidate exports |
| Independent actual-image review | [Final review](../../reproduce-inputs/new-family-visual-review/final-review.md): six candidates ready with disclosed notes |

The bundle is `easyviz-0.3.0.zip`, **356 files**, **7,180,125 bytes**, ZIP SHA-256
`10e211c1981ddb6a7b610b34687ca0d8a83f88fc7aeebbdf2084f6120662aaa0`.
Its path/content identity is
`b84d1570ad07682b1f7403c0704ac2d8d6020fe32a536f912d7223be0429b7f6`.
The release assets contain the bundle, build metadata and SHA256SUMS.

Checks run in the recorded macOS Python 3.12.2 environment. The published commit
also triggers the hosted Linux workflow; its live status is available in GitHub
Actions. Pixel identity on macOS does not promise cross-platform font identity.
The isolated installation does not update the user's desktop installation or
establish fresh application UI discovery. An installation request remains one
repository-link instruction following [INSTALL.md](../../../INSTALL.md).

Source numerical and independent image evidence retains its original candidate
scope. The final discovery/version changes do not alter plotting geometry, and
the current extracted bundle reproduces those inspected PNGs exactly. Screen
proxies and source correctness do not establish print proof, journal acceptance
or a universal model-quality gain. Practical Agent feedback and historical
negative comparisons are preserved in the repository.

The first 154-test log precedes a follow-up ancestor-symlink regression; the
final suite log supersedes it for source validation. An initial smoke criterion
compared macOS `/var` and `/private/var` aliases without resolving the checker
root; [the initial record](initial-discovery-check.json) and corrected passing
smoke are retained. This checker correction did not change the ZIP.
