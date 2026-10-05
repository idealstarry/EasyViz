# EasyViz v0.4.4 release QA

Validated on 2026-10-05 with Python 3.12.2 on macOS. This release improves the
first reviewed Create delivery and repairs reproduced workflow/code failures.
The two Create/Reproduce tracks remain the public workflow. The archive's
identity is recorded in [build.json](build.json).

| Check | Evidence |
| --- | --- |
| Complete unit suite: 526 tests passed | [Final unit log](unit-tests.log) |
| Installed dependency compatibility: 18 packages compatible | [Dependency check](dependency-check.log) |
| Extracted ZIP resources and actual runtime: passed | [Package check](package-check.log) |
| Local Markdown resources: 405 source targets passed | [Link validation](resource-links.json) |
| Local 0.4.4 installed and enabled; all 848 source/cache files match ZIP | [Installer result](local-install.json), [Independent file comparison](installed-content-check.json) |
| Prospective Create inputs, actual image review and current-file checks | [Evaluation and original failures](../../create-first-delivery-v0.4.4/README.md) |
| Current five selected delivery records | [Readiness evidence](../../create-first-delivery-v0.4.4/delivery-readiness.json) |
| Runtime and workflow failures, fixes and independent verification | [Code audit](../../create-first-delivery-v0.4.4/code-audit.md), [Workbench review](../../create-first-delivery-v0.4.4/workbench-fix-review.md), [Installer/package review](../../create-first-delivery-v0.4.4/install-fix-review.md) |
| Portable documentation: 307 local targets passed | [Reproduced omissions and repairs](../../create-first-delivery-v0.4.4/portable-resource-audit.md) |

The candidate engine was frozen before preparing five new tasks. One new public
Source Data input and four explicitly synthetic stress inputs retain 581
observations/cells. Two proposed tasks passed without a required visual repair;
three needed task-specific internal correction after actual inspection. The
final independent image reviews resolve the inspected defects with stated
density/overlap limits. These corrections are retained separately from the
initial failures and do not count as unseen engine successes. All five current
selected exports have completed, hash-bound review records.

Five original synthetic design-card pairs teach applicability, visible failure
mechanisms and mark/summary geometry. Their 248 observations are unchanged.
The initially faulty recommended violin and its failed packing repair remain in
the evidence; the final ten card exports received actual independent image
inspection, including nominal 96 dpi PDF previews. A complete review record
checks provenance and recorded evidence; it cannot prove that images were opened
or certify aesthetics, statistical validity, accessibility or journal acceptance.
There is no new WorkBuddy/model or causal with/without-Skill effectiveness test.

The scoped code audit reproduced and repaired request loss between cooperating
processes, ordinary two-ledger and acceptance-publication failures, stale QA
publication, restored source bindings, installed-cache rollback, concurrent
catalog preservation, unsafe source/output paths, normalized ZIP aliases and
bounded extraction. Failed runs and intermediate regressions are retained in
[initial](unit-tests-initial.log) and [intermediate](unit-tests-intermediate.log)
logs. macOS/POSIX locks were executed; Windows paths were inspected but not run.
Ordinary exception rollback is not a power-loss transaction. Accepted source
snapshots do not freeze arbitrary imported modules, profiles or external assets.

To repeat the runtime release checks in the selected Python environment:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python scripts/build_plugin.py
python scripts/check_package.py
```

GitHub CI and publication are verified after the source push; the published
asset must match the recorded archive checksum. CLI registration and file
comparison verify the local installed copy. An existing chat may retain its
loaded skills; start a new chat to load the updated version.
