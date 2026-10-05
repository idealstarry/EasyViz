# Reproduce track

Recreate the adopted visual structure and styling of a reference using the user's source data. Differences caused by new data are expected. Establish what should match before judging similarity.

The default task is **a reference image plus the user's real data**, including
references whose papers publish no Source Data or author code. Literature
Source Data cases are useful numerical/visual validation examples, not required
runtime inputs. A reference can use layers or geometry outside the current chart
library; implement them from scratch when needed. Follow
[Reference to code](reference-to-code.md) for a staged input packet, progressive
pattern search, a layer-to-code plan and the custom-script route.

## Input modes and evidence

| Mode | Available inputs | Record and limitation |
| --- | --- | --- |
| `image-data` — default | Reference image, user data, requested changes; optional caption and methods excerpts. | Record any caption or method evidence separately from what is visible. Author code is not required or sought for this workflow. |
| `author-code-assisted` — optional | The same inputs plus author plotting code explicitly supplied or requested by the user. | Record which code was read or executed and what it established. This cannot serve as evidence of image-only reproduction capability. |

Use only the selected mode's permitted inputs. If the user supplies or requests author code for this task, update the mode before using it; an unresolved image detail alone does not justify switching modes. Prior familiarity with an image or script must be disclosed in a reproduction benchmark; a fresh agent must not receive prior implementations or their conclusions.

The workflow always needs user data for a scientific output. With only an image, produce a visual specification or an explicitly labeled synthetic demonstration; do not reconstruct trustworthy measurements from pixels. A low-resolution image may support structure without supporting exact colors or text.

## 1. Obtain an independent reading

Delegate image interpretation to a fresh subagent using the [Reference Reader](../../easyviz-reference-reader/SKILL.md). Give it only accessible reference images, the selected panel or region, and any supplied caption or methods excerpt. Do not provide plotting templates, previous reproductions, author code, or the main Agent's interpretation. In parallel, the main Agent inspects user data and requirements.

Example delegation:

> Read the EasyViz Reference Reader skill at the supplied path. Inspect the attached reference panel and supplied caption excerpt. Return a structured description with observed, inferred, and unknown evidence states, required data meanings, and approximate relative geometry. Do not inspect other project files, search for author code, or choose an implementation. Report unreadable elements explicitly.

Use a fresh context without inherited implementation history when the collaboration tool supports it. The reader must actually view the image. For a multi-panel reference, select the relevant panel and describe its individual visual elements; the surrounding figure is context, not an instruction to assemble panels.

If independent delegation is unavailable, perform the reading in the main Agent with the same evidence rules and disclose that limitation. If a file cannot be viewed, report that rather than claiming a reading.

Optionally stage explicit files with
[reference_packet.py](../scripts/reference_packet.py) before delegation. Its
`reader-inputs/` contains only the reference and supplied caption/methods;
`data/` stays with the main Agent. Pass the reader only the permitted inputs and
reading contract. The tool copies bytes and validates evidence structure; it
does not read image semantics, infer measurements or verify independence.

## 2. Adopt a specification

Use [Reference specification](reference-spec.md) to combine the reading, user request, and real data into implementation requirements. The reader records observations; the main Agent owns the decisions.

| Decision | Apply |
| --- | --- |
| Scientific mapping | Confirm variables, units, transformation, aggregation, group order, and uncertainty meaning. A visible error bar does not distinguish SD, SEM, or a confidence interval. |
| User changes | Adopt additions and removals explicitly. User requirements take precedence over reference styling. |
| Panel text and caption | Retain axis names and units, ticks, legends, colorbars, and essential data annotations. The independent reader may observe reference titles or prose, but adoption follows the manuscript default: omit extra titles, subtitles, standalone overview counts, and explanatory footnotes; move explanatory material to separate `caption.md`. Copy an in-image title only when the user explicitly requests it. |
| Geometry | Use relative plot and legend placement as visual guidance. Set physical dimensions and point sizes from [Panel layout](panel-layout.md), never from screenshot pixels alone. |
| Legends | Apply [Legend layout](legend-layout.md): distinguish categorical, quantitative-size, and continuous roles; inspect complete bounds and reserved space relative to the plot. Adapt shared multi-panel reference legends to the standalone panel while preserving fonts and quantitative mappings. |
| Palette | Preserve adopted group-color relationships or apply the requested preset. Record estimated colors as estimates. Evaluate all palettes together on the actual panel; publication provenance alone does not establish a suitable combination. |
| Mark outlines | Resolve one policy for comparable filled dots, bars, and matching legend swatches from the adopted specification and user requirements. Apply it explicitly; record scientific/readability exceptions by role instead of inheriting conflicting library defaults. |
| Statistical uncertainty | Use the caption or methods when supplied. Ask for missing design information before computing an unsupported statistic; keep the rest of the plot moving. |
| Intentional differences | Record data-driven changes, layout adaptations, font substitutions, and omitted unsupported layers so the reviewer does not treat them as defects. |

Only after adoption, inspect reusable implementations. Search progressively by
layers and visual relationships, check recipe/data contracts, then choose a
supported recipe or an explicit custom script. In the layer-to-code plan, map
each layer to its real data, transform, artist, backend and verification; record
intentional omissions rather than silently dropping unsupported content.
For integrated references, resolve
[shared coordinates, literal ID joins, marginal summaries and guide mappings](complex-reproduction.md)
before drawing. Bind every adopted material layer to actual exported artists;
use the optional recorded-plan auditor when these dependencies need a repeatable
check. It does not certify image interpretation or visual quality.
Reproduce visual relationships before tuning small styling details: chart
geometry and scales, data-to-layer mappings, grouping and colors, then
typography and spacing. Reuse library components without inheriting their sample
filtering or scientific assumptions. Do not impose a fixed top-left title
template or retain an empty header band after moving prose to the caption.
Record omitted reference titles and explanatory text as intentional manuscript
adaptations, not missing features.

For related manuscript panels, carry accepted category colors, typography, continuous scales, and each panel's dimensions in a [Figure profile](figure-profile.md). Resolve conflicts before rendering; a category missing from one panel must keep its established color. For dot plots, use the [Dot data states](dot-states.md) contract: an empty position in a reference does not establish whether a measurement was zero, unmeasured, or omitted from the supplied data. Preserve the user's explicit measurement states and the quantitative area mapping.

Examples support specific input contracts and visual patterns. Check the current data, required layers, and layout against those boundaries before reuse; adapt and verify, or write a custom implementation when needed. Report unresolved support explicitly without substituting a different chart or dropping observations to fit a template. Existing example checks do not validate a new dataset or geometry.

For structural adaptations, use [Design decisions](design-decisions.md) to compare the reference's useful relationships with the new data's grouping, density, and label lengths. When claiming a refinement, compare the accepted baseline and candidate at the same final size under [Visual review](visual-review.md); retain the baseline if it better supports the intended reading task. A fitting layout or closer superficial resemblance alone does not establish improvement.

## 3. Implement and compare

Use [Reference geometry and typography](reference-geometry.md) before finalizing
the canvas. Measure the data region apart from keys and labels; relate marker
diameter and stroke to that region. Record the source scale when known and
explicitly adopt physical sizes when it is unknown. Shared decoding, narrow
data lanes and relative type hierarchy can matter more than matching a palette.

Render individual panels using the adopted specification and final-size layout. Save the script, settings, data transformations, and evidence sources. Write a separate `caption.md` with explanatory prose, abbreviation definitions, methods, attribution, and caveats under the [Panel layout](panel-layout.md) caption rules. Use known figure/panel identifiers only; do not inherit the reference's numbering for a new manuscript. The reproducibility record must identify the actual inputs accessed, including optional author code.

Custom implementations reuse the physical-size/font/export helpers and provide
their own source-to-artist, layer and alignment checks. Save a baseline before
structural adaptations and compare at the same final size. Review the
[implementation gap checklist](reference-to-code.md) so an unfamiliar visual
grammar remains a reproduction task rather than an excuse to switch tracks or
force a familiar template.

Delegate comparison to the [Figure Reviewer](../../easyviz-figure-reviewer/SKILL.md) with the reference image, rendered candidate, separate caption, adopted specification, and export measurements. The reviewer compares observable output and accepted requirements; it does not infer statistical correctness from appearance or request restoration of reference prose intentionally moved to the caption. Follow [Visual review](visual-review.md) for actionable findings, correction limits, and final status.

Deliver the result even when minor documented differences remain. Do not label it an exact replication, a passed visual review, or a validated image-only benchmark unless the corresponding evidence supports that claim.
