# Portable documentation audit

The root's release-time resource scan found two links that worked in development
examples but not in their flattened portable case layout. A subsequent scan of
all packaged Markdown found two attribution links into deliberately excluded
evaluation data. These were reproducible on the original built ZIP, independently
of plotting or Python dependency installation.

| Missing target in the original portable tree | Repair |
| --- | --- |
| ECDF case's `../../no-author-code/urschel-paired/README.md` | At the copy boundary, rewrite to the actually bundled sibling `../urschel-paired/README.md`; retain the correct original development link. |
| BMI violin case's excluded `first-render/panel.png` | At the copy boundary, link the historical image in the public development repository; retain the original example's local history link. |
| Attribution's `evals/skill-value/inputs/SOURCES.md` and `provenance.json` | Link the corresponding public repository files rather than pretend they are distributed in the plugin. |

`validate_plugin()` now validates direct Markdown links and images throughout
the portable tree, beyond the existing entry-point checks. It resolves decoded
local paths relative to the actual containing file, rejects existing resources
outside the package boundary, and ignores URL schemes, fragments and literal
code examples. Missing resources fail before installation. This intentionally
bounded parser does not fetch external URLs, verify named anchors, interpret
every Markdown extension, or act as a general website/link crawler.

Four independently executed resource regressions passed: the original missing
cases, actual sibling/images with escaped spaces and query/fragment components,
external URLs/literal templates, and an existing external local file that cannot
satisfy a portable link. The copy-boundary regression checks both rewritten
destinations while preserving original development README bytes. These tests
are included in the complete **526-test passing suite**.

At the initial release-preparation commit `23da3ca`, the 848-file plugin's full structure validation and
the explicit resource scan passed with **307 direct local Markdown targets**.
The retained [build identity](../release-qa/v0.4.4/build-before-choice-space.json) and
[extracted runtime check](../release-qa/v0.4.4/package-check-before-choice-space.log)
identify that initial tested artifact. Later design changes and the final package
are recorded separately in [release QA](../release-qa/v0.4.4/README.md).
No render/image source was modified by the portable-link repair.
