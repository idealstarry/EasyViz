# EasyViz 0.4.1 validation

Validated on 2026-10-02. [summary.json](summary.json) binds the package identity and check scope. The published source is identified by the `v0.4.1` tag; earlier releases retain their original archives and evidence.

## Changes and checks

| Change/check | Recorded evidence |
| --- | --- |
| Opt-in final-size circle packing, without deleting observations or changing quantitative positions | [Same-data point-spacing comparison](../../crowding-layout/v0.4.1/README.md): 24 observations, 12 intersecting circle pairs under jitter versus zero under beeswarm; same 120 × 90 mm canvas, Arial 8 pt and 3 pt circles |
| Directory intake distinguishes suspected summaries, repeated IDs and unresolved field/unit meanings | [Intake contract](../../../skills/easyviz/references/data-exploration.md), with meaningful numeric/schema tests; declarations exclude unit IDs from measurements |
| Complex reproduce layer adoption, literal joins, encodings, recorded source/artist checks and supported physical SVG alignment | [Complex reproduction contract](../../../skills/easyviz/references/complex-reproduction.md); a passed recorded-check audit does not certify semantics or visual quality |
| Full development suite: 294 tests passed | [Actual log](unit-tests.log), including 59 new numeric/geometry/schema tests |
| Extracted portable bundle | [Package smoke](package-smoke.json): 424 files, five workflow routes, core/draft/measured rendering and selected literature wrappers |
| Reviewed previews reproduced in an isolated runtime | [Pixel/source replay](clean-pixel-replay.json), including historical cases, all three Shi transfers and the annotated-heatmap recipe |
| Fresh local Agent create and reproduce tasks | [Inputs, attempts, code, portable replays and independent reviews](../../workflow-usability/v0.4.1/README.md) |
| All three skill entry points | Skill-creator validators passed; extracted-package resource checks passed |
| Matched WorkBuddy tasks prepared; native UI did not establish a submission | [Kit](../../workbuddy/v0.4.1/README.md), [blocked-attempt status](../../workbuddy/v0.4.1/run-status.json) |

The first full-suite attempt was blocked by sandbox restrictions on local HTTP binding: its [log](sandbox-test-attempt.log) retains all 11 environment errors. The authorized loopback rerun passed all 294 tests. The isolated replay uses the previously created independent Python environment on this same macOS host; no fresh dependency installation or new desktop discovery is claimed for 0.4.1.

[Independent code review and four final reprobes](code-review.json) prompted fixes for nested SVG viewport alignment evidence, exact numeric-string comparison above binary-float integer precision, tiny descriptive order statistics, and explicit numeric unit IDs being selected as measurements. The corresponding tests exercise the concrete failures. Existing random jitter keeps its historical placement; circle spacing is reported as unchecked in that mode rather than certified clear.

The local create trial aggregates technical reads into 36 independent mouse observations, runs two planned Mann–Whitney comparisons with Holm correction, and renders all individual values. The reproduce trial implements a supplied synthetic 8 × 9 reference with aligned annotation and means, three unmeasured cells and one measured zero. Saved final PNG/PDF inspection by a separate reviewer found no required visual repairs. The reproduction's initial reading is by the implementer; its final visual review is independent. Numeric correctness and image readiness remain separate reports.

These bounded tasks support workflow usability and the specific repairs. They do not establish a with/without-skill quality gain, general performance of Chinese models, universal Nature-style aesthetics, physical print proof or journal acceptance. No WorkBuddy v0.4.1 output was verified. Existing negative model-comparison results remain available in their historical records. Install/update follows [INSTALL.md](../../../INSTALL.md).
