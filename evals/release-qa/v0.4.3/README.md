# EasyViz v0.4.3 release QA

This is the original published v0.4.3 package snapshot. For the subsequent
Create improvements on main, while retaining version 0.4.3, see the
[refinement checks](../../create-refinement-v0.4.3/README.md).

Validated on 2026-10-05 with Python 3.12.2 on macOS. This release concentrates
on basic Create panels while preserving the two Create/Reproduce tracks.
The manifest and release tag identify version 0.4.3; the archive contents are
identified by [build.json](build.json).

| Check | Result | Evidence |
| --- | --- | --- |
| Complete unit suite | 413 tests passed | [Final log](unit-tests-final.log) |
| Installed dependency compatibility | 18 packages checked; compatible | [Dependency check](dependency-check.log) |
| Five saved core specifications | Old and new PNG pixels identical | [Forward compatibility](legacy-core-pixels.json) |
| Bounded core stress/transfer evaluation | 8 successful plots; 2 clear layout rejections, 10 data rejections and 1 unsupported request; no open defects | [Scenario results](generalization-results.json) |
| Existing complex Create cases | Source values and quantities checked | [Showcase check](showcase-check.json) |
| Five basic Create cases and their probes | 15 baseline/candidate/transfer technical checks passed | [Basic-panel validation](../../basic-panels-v0.4.3/validation.json) |
| Independent basic-panel review | No critical/major findings; four candidate preferences and a scatter tie | [Actual image audit](../../basic-panels-v0.4.3/independent-review.md) |
| Explicit font/environment transfer | Five DejaVu Sans panels rerendered and measured in a separate directory | [Standalone validation](../../basic-panels-v0.4.3/standalone-validation.json) |
| Extracted ZIP resources and runtime | Passed, including basic panels and public workflow discovery | [Package check](package-check.log) |
| Extracted Mac replay | Reviewed existing cases and all five basic PNGs/plotting CSVs replay identically | [Pixel replay](clean-pixel-replay.json) |
| Local plugin update | `easyviz@personal` installed as 0.4.3; all 620 cache files match the tested package | [Installer result](local-install.json), [Content verification](installed-content-check.json) |
| Skill metadata and resource links | Three skills validated; changed linked resources exist | [Resource checks](resource-link-check.json) |
| Fresh basic Create workflow | New local Agent retains 33 independent specimens from 66 technical reads; actual saved source/value check passed | [Root audit](../../basic-forward-v0.4.3/root-source-audit.json) |

The first restricted-sandbox unit run could not bind 26 localhost test
servers. Eight installation-fixture errors also exposed omitted new resources
in its mock package. The fixture was updated and the complete final suite was
rerun with loopback access. The original [failed log](unit-tests.log) remains
distinct from the passing result. The additional bar checks accept intentional
zero-baseline contact while still rejecting other clipped outline boundaries.

New task defaults are separate from saved renderer specifications. New draft
and preview requests start with `crisp`; older preview fallback behavior
requires explicit `style_mode: legacy`. Explicit styling and profile choices
remain authoritative. No frozen legacy output was regenerated to manufacture
compatibility.

Image preference is scoped to the inspected data and reading task. The violin
candidate adds a quartile/median layer, so its comparison is not solely
cosmetic. Synthetic probes do not add biological studies. Advisory readability
reports do not alter marks or establish scientific validity, accessibility or
publication acceptance. This release does not add a WorkBuddy effectiveness
comparison.

The fresh basic workflow is a synthetic usability trial with no unaided or
external-model comparison. It prompted a narrower preview instruction for an
already specified reading task. First render, actual SVG/PDF checks and the
technical-read preparation are retained separately from the curated literature
gallery; this trial is outside the portable plugin.

Local content verification and CLI registration do not prove discovery in an
already open conversation. Start a new chat to load the updated skills;
refresh or restart the desktop if its plugin list still shows the old copy.

To repeat the release checks in the selected scientific Python environment:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python tests/check_showcase.py
python tests/check_generalization.py --strict --out /tmp/easyviz-v043-generalization
python scripts/build_plugin.py
python scripts/check_package.py
python tests/check_plugin.py --report /tmp/easyviz-v043-replay.json
```

The independent visual evidence remains attached to the actual reviewed
candidate images. GitHub CI and publication are verified after the source push;
the release asset must match the recorded archive checksum.
