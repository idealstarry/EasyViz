# Source-bound workbench and delivery checks

This audit fixes concrete workflow failures in EasyViz. It does not measure
visual quality, verify that a reviewer opened an image, or establish general
Agent effectiveness. The probes use isolated copied sources and actual exports;
original user figures and frozen 0.4.4 trials are unchanged.

- **Custom code:** capture actual declared source/spec/script/auxiliary bytes before
  exports, parse those captured bytes, and publish a bound receipt afterwards.
  A real element map enables selection; receipt-only figures retain region and
  general notes. Verified record/accept/restore preserves every declared input.
  [Independent final nine-case evidence](reviewer-capture-api-final/evidence.json)
  includes replacement-source refusal and actual PNG/PDF/SVG restoration.
- **Accepted snapshots:** copied source bytes must match their expected binding;
  restored passing QA must retain its accepted identity and export hashes.
  [Actual pre-fix probes](reviewer-production-snapshot-before/evidence.json) and
  [post-fix probes](reviewer-production-snapshot-after/evidence.json) cover
  data/spec/script A→B→A replacement and QA-identity tampering.
- **Core helper sources:** the map retains consumed helper roles. A changed helper
  now disables verified acceptance; deleting original code/data/spec after a
  valid acceptance still restores all ten roles and identical exports.
  [Before](core-declared-helper-staleness-evidence.json),
  [after](core-declared-helper-after-evidence.json).
- **Generic Create review:** declared auxiliary claims in maps and saved captured
  settings participate in source continuity. Changed/missing helpers block a
  recorded review; primary-only legacy records remain supported. Followup
  semantics remain separate from bounded first delivery.
  [Before](create-review-auxiliary-before-evidence.json),
  [after](create-review-auxiliary-after-evidence.json),
  [36 focused tests](authoritative-review-source-guard-tests.log).
- **Portable package:** 0.4.5+ requires both new helpers and the complete runtime
  inputs of the thermogenic-expression and compartment-ccl2 cases. Older
  packages retain their prior requirements. Actual copied and extracted fresh
  DejaVu redraws independently check workbook literals, vector marks, physical
  size/font and current real artist/source bindings. Frozen package previews
  carry no repointed historical QA or receipt.
  [Latest portable evidence](portable-create-evidence.json),
  [verification log](portable-create-final-verification.log).

The [84 handoff/application/workbench tests](authoritative-handoff-tests.log)
and [44 installer/build tests](authoritative-portable-closure-tests.log) passed
at their recorded production checks. Parent integration runs the complete suite
again against the final release tree.

`git-evidence-whitelist.json` lists compact evidence and reproducible probes to
retain in Git. Copied package/runtime trees, temporary exported fixtures,
symlink staging adapters and ZIPs are disposable development caches; they are
not part of this evidence set or the plugin package.
