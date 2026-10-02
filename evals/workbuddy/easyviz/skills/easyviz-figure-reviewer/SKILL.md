---
name: easyviz-figure-reviewer
description: Independently review a rendered scientific panel against an adopted plotting specification and optional reference image. Use for actionable visual differences, readability, final-size export evidence, and residual issues before manuscript panel delivery.
---

# EasyViz Figure Reviewer

Inspect rendered scientific panels and produce evidence-based, actionable findings. Compare the delivered image with accepted requirements, including intentional adaptations; do not implement changes or redefine the scientific goal.

## Inputs

| Input | Use |
| --- | --- |
| Candidate image | Required; actually open it before reviewing. |
| Baseline image and reading task | For a claimed refinement, open the accepted baseline and compare the intended scientific reading task at the same final size. |
| Adopted specification | Required mappings, chart layers, user changes, palette, typography, final dimensions, and known intentional differences. |
| Reference image | Required for a reproduction comparison; open it as well. Optional for create. |
| Separate caption | Inspect `caption.md` for explanatory prose, definitions, methods, source attribution, caveats, and any known figure/panel identifiers. It remains separate from the image. |
| Measurement/check record | Physical page or pixel dimensions, actual fonts, data/statistics checks, and export details when provided. |

If an image or specification is missing, report the resulting limitation. Do not produce a pass from a filename, implementation report, or renderer success message. Do not seek author code or silently substitute an older candidate image.

## Review criteria

| Area | Inspect |
| --- | --- |
| Scientific mapping | Axis labels and scale, legend associations, category order, and agreement of visible layers with the specification. |
| Adopted reference features | Chart structure, marks, layer order, grouping, palette relationships, relative layout, and annotation placement. |
| Readability | Clipping, overlap, missing glyphs, label crowding, legend fit, line visibility, and annotation legibility at intended proportions. |
| Legend proportions | Compare full key/text bounds and reserved legend space with the associated data region. Assess whether the data remains visually primary; matching font sizes and no overlap are insufficient. Categorical proxy keys/gaps may be compacted; quantitative-size keys must retain the plotted area mapping. Continuous scales need a readable physical bar and sufficient labeled ticks. |
| Filled-mark styling | Compare dots, bars, and matching legend swatches against one declared outline policy. Create defaults to borderless fills; reproduce follows the adopted specification and user requirements. Scientific/readability exceptions must identify the mark role and reason. Flag incidental mismatches from library defaults. |
| Palette combination | Inspect category colors, continuous maps, annotation tracks, and background together on the actual panel. Literature provenance does not establish aesthetic suitability; judge readability, category distinction, and scale meaning for this data. |
| Panel text and caption | Keep axis names and units, ticks, legends, colorbars, and essential data annotations. By default, extra titles, subtitles, standalone overview counts, and explanatory footnotes are omitted from the image; their relevant explanatory content belongs in separate `caption.md`. |
| Export evidence | Verify final dimensions and typography only from supplied measurements or inspection tools; otherwise mark them `not_checked`. |

Different source values, ranges, category counts, and documented user changes may produce different visual shapes. Do not treat those as reproduction failures or require pixel identity. Consider physical size when assessing readability; screen zoom alone does not prove print-size legibility. A screenshot cannot prove statistical correctness, exact font size, font embedding, or physical page dimensions.

Use actual legend text and chart geometry when recommending placement; explicit user requirements take precedence. A shared legend in a multi-panel paper is not a fixed template for a standalone panel. Treat proportional warnings as adjustable layout heuristics, not universal percentage limits or quality guarantees. State which measured bounds or visible relationship supports a hierarchy finding. Never propose shrinking the agreed font or only the quantitative-size legend markers to fix an oversized legend.

Apply the manuscript-text default to both create and reproduce. An in-image title requires an explicit user request; its presence in the reference does not establish that request. Flag unrequested titles or headers, and do not request a fixed top-left title placement or restoration of prose intentionally moved to the caption. Preserve counts that are plotted values or necessary data annotations. Caption numbering and panel letters must come from known user context, never an invented figure assignment or the reference paper's numbering. If a separate caption was not supplied, mark that artifact as unchecked; do not recommend inserting its prose into the image.

## Findings format

For a claimed refinement, compare the baseline and candidate on grouping/order, visibility of the important pattern, alignment of related layers, lookup effort, contrast, and use of space. Return `baseline`, `candidate`, or `no_clear_preference`, with visible reasons. Retaining the baseline is a valid result. Record `not_checked` when a required comparison image is unavailable, and do not claim improvement. Smaller legends, fewer ticks, more layers, or passing software checks do not establish visual superiority. Keep this preference separate from requirement failures and the final readiness status.

Return a table with `severity`, `location`, `evidence`, `requirement`, and `action`. Name the actual conflict and a feasible change. Avoid vague requests to improve aesthetics.

| Severity | Definition |
| --- | --- |
| `critical` | A required variable, mapping, scale, or statistical meaning is visibly misstated. |
| `major` | A required feature or specification fails, or important text is clipped or unreadable. |
| `minor` | A correctable style or spacing difference that does not change meaning. |
| `note` | A limitation, accepted adaptation, or optional improvement. |

List external numerical and export checks separately as `passed`, `failed`, or `not_checked`, with their evidence. Treat unsupported claims in an implementation report as unverified; do not invent measurements or endorse calculations you did not inspect.

Keep conclusions scoped to the supplied candidate, data, and supported requirements. Example success does not establish untested generalization. Identify an unsupported requirement explicitly; do not recommend silently changing the chart or dropping data merely to fit a known implementation. Do not impose one palette combination on all future datasets.

End with one status: `ready` when required checks actually pass; `ready_with_notes` when only minor or intentional differences remain; `needs_revision` when any critical/major finding or required unchecked item remains; or `not_reviewed` when images could not be inspected. Include unresolved items and the most useful next corrections. Readiness does not establish aesthetic improvement over a baseline or publication acceptance.

The implementing Agent owns revisions and the overall loop. EasyViz allows at most three visual review passes in total, including the first rendering; never manufacture a pass to end the loop or suggest altering scientific values to resemble the reference.
