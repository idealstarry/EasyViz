# EasyViz 0.5.2 release QA

Date: 2026-10-15. This record covers the frozen release sources, first-output
guidance, runtime repairs and portable package. Publication requires the exact
release commit's Core checks to succeed.

## Final source checks

| Check | Result |
| --- | --- |
| Complete runtime/workbench test suite | 893 tests passed in 379.008 seconds |
| Final build/package filter regressions | 42 passed in 0.701 seconds |
| Independent review's final path/default-document/profile/analysis regressions | 55 passed in 13.808 seconds |
| Declared dependency compatibility | 46 installed packages compatible |
| Skill metadata validation | All three skills passed |
| Portable build | 956 files; 19,090,258 bytes |
| Full extracted-package validation | Passed: actual source-data redraws, vector/font/mapping checks, workflow discovery and new radial CLI fixtures without site packages |
| Package/source identity | All 956 packaged files match their corresponding published source blobs |
| Release-document local links | 51 checked; all targets present |
| Patch whitespace | Passed |

The earlier complete run passed 889 tests before independent review added four
path-resolution regressions. The 893-test run includes those fixes and the
final renderer version. The final change only filters local workbench display
metadata while copying package sources; its 42-test build/package check verifies
stateful/clean build equality and keeps legacy archives valid. Core checks
covers the exact final release commit. Counts describe tested engineering
behavior, not an aesthetic score.

## Create guidance and reusable geometry

The [first-output guide](../../../skills/easyviz/references/evidence-first-create.md)
puts the supported comparison before panel organization and supporting layers.
It distinguishes main-figure reading from complete lookup tables, and checks
evidence, track, label and guide footprints separately. Relevant literature
mechanisms remain conditional. No specific tree compression, palette or
physical ratio becomes a universal default. Create and Reproduce stay distinct.

The new [radial helper](../../../skills/easyviz/scripts/radial_layout.py) has
18 targeted tests. They cover exact identity and class boundaries, complete-
circle seam merging, partial arcs, balanced variable-footprint labels,
displacement/capacity failures, finite geometry and CLI execution without site
packages. Independent numerical checks compared feasible placements with
constrained optimization. A synthetic render was actually inspected for band
continuity and local label separation; it does not measure scientific quality
or establish a first-delivery improvement on unfamiliar data.

## Confirmed defects repaired

- Export and metadata paths could replace consumed inputs through ordinary,
  symbolic-link or hard-link aliases. Core and focused exporters now refuse
  these destinations before changing output state, including explicit profile
  overrides and declared auxiliary inputs.
- Create candidate rendering did not load adopted analysis. It now preserves
  adjusted/raw P selection, exact analysis companions and explicitly included
  populations without recomputing inference.
- Focused numeric parsing could turn a nonzero decimal into zero through
  floating-point underflow. All six focused recipes reject that loss while
  retaining real zeros and literal source identities.
- Saving an in-memory specification relocated relative profile/analysis paths.
  Resolution now keeps the caller's original base and saves replayable absolute
  references. Explicit supplied specification bytes remain checked separately.
- Browser acceptance could capture an unseen replacement of the displayed
  attempt. Acceptance now binds the reviewed version; stale submissions fail.
  A historical accepted snapshot no longer marks a different current output as
  accepted, and independent captions survive accepted-version restoration.
- Global active-download links could return a different attempt after another
  window switched the service. Current/history exports now use attempt-scoped,
  version-bound links; ordinary exports also bind their exact bytes. `.ev`
  capture checks the reviewed version before publishing its download.
- Workbench display-name metadata could make a locally built package differ
  from a clean source build. New packages omit that UI state without deleting
  it from the project or rejecting older archives. A stateful/clean rebuild
  regression preserves the actual scientific assets and verifies identical ZIPs.

Actual HTTP regressions show that A's links still return A after B becomes
active, and a replaced A returns 409 for an old viewed version. Browser-client
tests check the rendered link and acceptance payload contracts. These are
automated HTTP/client tests, not a new claim of native browser file-picker or
download interaction coverage.

## Limits

The normal workbench flow remains saved comments followed by a message in the
original Agent chat; MCP can submit directly to that original Agent while it
is active and waiting. Native idle continuation and a new cross-client or
cross-platform efficacy study are not established by this release.

The radial helper packs one explicit angular window using supplied measured
extents. It does not measure text, prove full-circle seam/leader clearance,
infer a tree or transform quantitative branch lengths. Actual-image review is
still required. Known drawing iterations, synthetic geometry and passing
software tests do not establish publication aesthetics or gains for every
Agent, model or unfamiliar dataset.
