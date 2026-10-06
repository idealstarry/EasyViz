# EasyViz 0.5.1 validation

This release uses the normal review loop: **Save drafts → ask the original
Agent chat to apply the comments → compare the fresh result in the workbench**.
The optional MCP submission route was also exercised with the original Agent
active and receiving work. Automatic continuation after an idle chat remains
host-dependent and is not required for the normal loop.

The [release QA record](../evals/release-qa/v0.5.1/README.md) records the final
checks, actual browser evidence, repairs and applicable limits. It distinguishes
runtime tests, reviewed output and host integration rather than treating a
connected-session label as proof of delivery.

Review covered the renderers and declared export contracts, editable `.ev`
packing/import, shared figure service, source-bound requests, original-session
queue and cancellation, manual comment processing, workbench interactions,
installation safeguards and portable packaging. Regressions exercise actual
renders, source changes, concurrent completion and task ownership.

Native host scheduling was not verified. Browser file-picker upload and browser
download were not established in the final workflow check; module, HTTP and
extracted-runtime document checks and local generated exports are separate
validation evidence. SVG interaction uses genuine mappings; a collection may
remain a group and a raster layer remains raster.

These checks establish engineering behavior for the tested inputs. They do not
establish publication aesthetics for every dataset or gains across every Agent
or model. Both Create and Reproduce retain their own scientific and visual
review requirements.
