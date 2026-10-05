# EasyViz 0.4.6 validation

This release strengthens reference proportions and adds a distinct, purposeful
Create task. Create and Reproduce remain the two tracks. The 0.5.0 work is a
[research proposal](../../../docs/roadmap-v0.5.0.md), with no new MCP runtime.

## Actual design and numerical evidence

- [PROGENy signatures](../../../examples/create/pathway-signatures/README.md)
  retain all 11,143 literal coefficients. A 55-pair overview selects two complete
  coefficient comparisons; seven sign summaries state their real denominators.
  All 80 selected points, matrix quantities, PDF fonts and physical exports were
  independently checked. Three visual passes are retained, including a concrete
  annotation correction. Near-origin crowding and tiny denominators remain
  documented; no biological activity, fitted correlation or crosstalk is inferred.
- [Paired forest lanes](../../../examples/no-author-code/vabistsevits-forest/revision-v0.4.6/README.md)
  preserve 48 estimates, 96 CI endpoints and supplied fill states. The adopted
  32 × 92 mm data lanes retain the source width/height relationship, with one
  shared outcome key and explicitly adopted editable 8 pt text.
- [Integration radar](../../../examples/no-author-code/massier-integration-radar/revision-v0.4.6/README.md)
  preserves all 25 rates. A 34 mm circle and 5.1 pt marks restore the observed
  point/circle relationship; three true zeros stay coincident.

The Reproduce cases have [original/baseline/revision inspection](../../development-v0.4.6/reproduce-design/independent-visual-review.md),
[current independent confirmation](../../development-v0.4.6/reproduce-design/independent-readiness-rebind.md),
and [real-size comparison](../../development-v0.4.6/reproduce-design/physical-scale-comparison.pdf).
Source outlined fonts and pale colors, adapted frames/keys and actual overlaps
remain explicit limits. Measured geometry supports, but does not replace,
inspection of the actual images at their adopted physical size.

## Workflow and package scope

Paired raw circles now register real source groups and consume the per-format
observation-boundary report. A genuine PNG-only rounding case is rejected even
when its PDF/SVG and earlier nominal geometry check pass. Legal values, areas,
statistics, adopted ranges and PNG/PDF pixels remain unchanged. The independent
[paired review](../../development-v0.4.6/paired-observation-clipping/reviewer-review-after.md)
also confirms refusal of a malformed table that previously acquired a hidden
index and false unit identities.

The [independent focused CSV review](../../development-v0.4.6/focused-csv-identity/reviewer-final-review.json)
reproduced false-passing exports in ECDF, interval and summary time-course
renderers. Replicate preparation shifted fields too, but its existing later
audit already refused export. All four now reject malformed widths before
drawing and bind actual consumed bytes. Twelve fresh CLI flows and 28 regression
scenarios preserve legal PNG/PDF/SVG bytes, BOM, quoted Unicode and literal
identifiers such as `001` and `NA`. The five changed modules pass 64 focused
tests; shared drawing helpers remain unchanged.

New package resources contain executable source, attribution and frozen
previews. Current-path QA, maps and receipts stay in development; fresh copied
and extracted redraws create honest local records. Package verification reads
actual source/vector/font exports and checks real element and receipt bindings.
The prior versions' package requirements remain supported.

These case reviews and runtime regressions do not establish universal CNS
aesthetics, publication acceptance or controlled model/Skill efficacy.
Release test, package, local-installation and GitHub CI evidence accompanies
this record.

## Release verification

- [Full test record](unit-tests.json): 635 tests pass in 281.123 seconds.
  The [initial run](initial-unit-tests.log) found one old restoration expectation
  that omitted the newly explicit consumed-source path. The restored source was
  correct; the test now checks both rebound pointers and frozen byte identity.
  [All 24 request/restoration tests](restore-tests.log) and the
  [final complete suite](unit-tests.log) pass.
- [Archive identity](package.json) and [fresh extracted-package verification](package-check.log)
  cover all 921 files and real redraws. The new three-case check also has a
  [separate execution record](new-cases-package-check.log).
- [Installed-content verification](installed-content-check.json) compares the
  actual local plugin and cache with the archive and confirms enabled 0.4.6.
- [Documentation and image resources](resource-links.json) resolve current
  local links and all README/palette images. Frozen partial history capsules are
  excluded explicitly.
- The immediately preceding 0.4.5 release passed its matching
  [GitHub Core checks](https://github.com/idealstarry/EasyViz/actions/runs/37350679728)
  before publication; [public asset evidence](previous-release-v0.4.5.json) records
  the exact target and single ZIP. For 0.4.6, publication requires successful
  Core checks on its pushed release commit.
