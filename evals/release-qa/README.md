# Release QA — EasyViz 0.1.0

Latest validation: [0.4.1 point placement, directory intake and complex reference layers](v0.4.1/README.md). The evidence below remains attached to the original 0.1.0 archive.

**Decision: ready for an initial private GitHub release within the tested scope.** Completed 2026-09-29. Three demonstrated scientific input defects were fixed before rebuilding. No unresolved critical or major failure remains in this evaluation. This is a bounded acceptance record, not a claim that every future scientific figure will work or improve.

| Check | Result | Evidence |
| --- | --- | --- |
| Core, legend and custom-case contracts | 33 tests pass in the development environment and in a newly created Python virtual environment | [Audit](audit-report.md), [clean test log](clean-runtime-unit-tests.log) |
| Changed input shapes and data meanings | 21 expected outcomes: 8 valid renders, 10 data rejections, 2 layout rejections, 1 unsupported method; no unexpected result | [Transfer report](renderer-transfer/report.md) |
| Legend geometry | 9 feasible cases and 1 expected impossible-layout rejection | [Legend report](legend-transfer/results.md) |
| Create forward test | New longitudinal protein schema with missing visits; all 252 paired changes and 24 median/IQR groups independently matched, including actual SVG coordinates | [Request](inputs/create/request.md), [output](forward-create/panel.png), [independent review](forward-create/independent-review.md) |
| Reproduce forward test | New category count and missing-value requirement; all 61 supplied values retained, 3 absent pairs distinguished from 2 measured zeros; SVG areas, colors and key scales independently checked | [Request](inputs/reproduce/request.md), [output](forward-reproduce/panel.png), [visual review](forward-reproduce/independent-review.md), [numeric review](reproduce-numeric-review.json) |
| Packaged resource structure | All three skill validators and the plugin manifest validator pass; linked resources resolve | Main skill, reference reader and figure reviewer are bundled together |
| Clean runtime and archive | Declared runtime installed into a new virtual environment without system site packages; extracted ZIP reruns all bundled cases and both transfer variants; PNGs match accepted previews | [Environment, archive checksum and checks](clean-runtime-package.json) |
| Historical/source checks | Existing historical and real-data showcase checks pass; biological provenance remains separate from synthetic stress cases | [Historical checks](../../examples/validation-summary.json), [showcase checks](../showcase-validation.json) |

## Corrections made during this pass

- Scatter correlation previously ignored `statistics.unit`, which could treat repeated participants as independent rows. Both supported unit declarations now resolve consistently; conflicts, missing IDs and repeated units are rejected.
- The paired score recipe previously matched blank participant IDs. Empty or whitespace identifiers are now refused before joining visits.
- The annotated heatmap recipe previously treated a literal `NA` row ID as missing. `NA`, `null` and leading-zero identifiers are preserved, while genuinely empty headers, row IDs and annotation IDs are refused.
- The portable BMI invocation was corrected, and custom cache paths now use the operating system's temporary directory.

The regression tests exercise these actual failure modes. Unchanged valid-case previews were retained and reproduced from the final ZIP. Detailed findings and original failing probes are in [the audit record](audit-report.md).

## Forward-test access and limits

Fresh implementers received only the packaged skills and held-out inputs, with instruction-based access restrictions. They did not read development examples, existing test results or the input generator. This was not a filesystem-enforced sandbox. The create implementer wrote a new script from the design guidance and received an independent source-to-SVG review. The reproduce implementer used the documented main-agent reading fallback when an independent reader was initially unavailable, then received a fresh independent final visual review. The parent separately checked its source table and actual SVG geometry.

Both final panels are 180 × 125 mm with Arial 8 pt and embedded PDF fonts, separate captions, and individual exports. One positive dot in the reproduce test is tiny and pale at the required proportional area and continuous color mapping; it remains a disclosed minor limitation. The input data and reference are explicitly synthetic and carry no biological finding.

The clean environment resolved Matplotlib 3.11.2, pandas 3.0.6 and pypdf 6.19.0, newer than the development pins, and still reproduced the bundled PNGs. This checks a fresh Python environment on the same macOS host with its installed fonts. It is not a new operating-system installation, physical print proof, or exhaustive dependency-version matrix.

Explicit-path Skill use and the standalone runtime were tested. Codex marketplace installation and automatic skill discovery were not performed; building or downloading the ZIP alone does not register it. No claim of universal aesthetics, arbitrary chart support, or superiority over a capable unaided Agent follows from these tests. The GitHub workflow checks core contracts and builds on Linux; actual-image acceptance remains a separate step.

## Reproduction

Run the commands in [the development guide](../../docs/development.md). The held-out inputs are preserved under `inputs/`; `generate_inputs.py` records their deterministic generation. `verify_reproduce.py` independently checks the saved reproduction's actual SVG against its original source. `tests/check_plugin.py --report <path>` allows recording an extracted-package run under another environment. The selected archive identity and exact scope are recorded in [summary.json](summary.json).
