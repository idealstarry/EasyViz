# EasyViz 0.4.5 validation

This release adds two distinct, literature-informed Create tasks and repairs
custom-code handoff and observation-boundary checks. The release retains the
Create and Reproduce tracks. New Reproduce revisions belong to 0.4.6.

## Actual figures and source checks

- [Thermogenic expression](../../../examples/create/thermogenic-expression/README.md):
  all 174 literal TPM observations, including measured zeros, with an absolute
  log2(TPM + 1) matrix and an aligned, explicitly descriptive genotype contrast.
  The case distinguishes a difference of mean logs from other contrasts.
- [Compartment Ccl2](../../../examples/create/compartment-ccl2/README.md):
  all 88 observations, exact-hour means and SEM, separate concentration units,
  and decoded display offsets. Terminal groups are not linked as individuals.
  Three initial visual passes and a fourth, separate feedback correction remain
  recorded; the fourth is not claimed as bounded first-delivery success.
- Both cases were inspected as actual PNG and nominal-size PDF images and
  independently reviewed. Exact source-to-artist checks, editable vectors,
  supplied font adoption and fresh copied/extracted redraws accompany them.
  These are bounded case results, not evidence of universal publication quality
  or a controlled model/Skill effectiveness comparison.

## Runtime and workflow scope

Custom plotting can capture declared input bytes before plotting, then bind
actual exports. Verified region/general requests work without a selectable
element map; actual registered IDs enable click selection. Accepted snapshots
preserve the declared dependency closure. Unknown post-export consumption is
explicitly unverified.

Registered circular observation envelopes are checked at final transforms,
actual axes clipping and each export page, including PNG rounding. Confirmed
clipping invalidates delivery while preserving explicit ranges and mark areas.
Unsupported marker/clip geometry stays advisory. The focused preview and
replicate consumers use the same report; custom code must explicitly consume
applicable geometry checks.

See [endpoint evidence](../../development-v0.4.5/endpoint-clipping/INTEGRATION.md),
[followup review evidence](../../development-v0.4.5/followup-review/README.md),
and the case source contracts and independent reviews for exact limits.

The [complete local suite](unit-tests.log) passed **625 tests**. The
[fresh extracted package checks](package-check.log) passed, and
[package contents](package.json) and [installed copies](installed-content-check.json)
record the 892-file build and local enabled-plugin verification.
Disposable copied package trees and caches
are omitted. Development history stays outside the portable plugin.

The preceding [0.4.4 release](https://github.com/idealstarry/EasyViz/releases/tag/v0.4.4)
is published; its matching Linux CI completed successfully, as recorded in
[the retained log](v0.4.4-final-linux-ci.log).
