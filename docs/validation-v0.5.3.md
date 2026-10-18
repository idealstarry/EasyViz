# EasyViz 0.5.3 validation

This release changes the default plotting workflow and separates ordinary
graphic delivery from optional editing infrastructure. Validation covers
source-backed graphics, all six focused recipes, explicit `.ev` export,
workbench map validation, package contents and client installers.

Local verification passed 918 tests in the complete Python suite and all 11
npm CLI tests. The final map-free source-review repair additionally passed
all 29 focused Create-review tests. Dependency compatibility was checked
against the 46 installed packages. Release packaging validates the extracted
runtime, the matching renderer version and actual installer delivery.

Runtime regressions exercise missing optional editing modules, failed or
partial maps, stale archive/map cleanup and current explicit document export.
Scientific clipping and graphic write failures remain fatal. A duplicate-ID
regression checks that ambiguous SVG selection is rejected while genuine
source-bound region/general notes remain usable.

Create review also checks the source independently of an optional map. The
regression uses a real render with map writing unavailable, then confirms that
changed inputs and contradictory source declarations are still rejected.

An isolated first-use exercise uses synthetic paired measurements, followed
by user clarification, a reviewed first figure and a chat-based cosmetic edit.
A separate fully specified request checks that first-use guidance includes
the optional workbench without unnecessary questions. These are workflow
checks, not an effectiveness benchmark or evidence of universal publication
aesthetics. Conversation introductions and intake limits are Agent instructions;
their execution depends on the host following the skill.

The paired-data exercise retained all 40 measurements from 20 donors. One
reviewed first rendering was followed by a chat-requested color and marker-size
change; source values, descriptive summaries and point coordinates were
verified unchanged. Independent image review found no required visual or
scientific failure, with normal one-pixel PNG quantization noted; SVG retained
the exact adopted 90 × 75 mm canvas. This task supplies no baseline comparison.

Browser interaction checked opening an ordinary mapped SVG with no prebuilt
`.ev`, saving an element comment and general note together, and downloading a
fresh validated project on demand. No live MCP connection was required.

The workbench remains explicitly requested. MCP submission requires the
connected original Agent to be active and waiting; this release does not
establish automatic idle-session continuation. Skill discovery, a numerical
test pass and a successful export do not replace actual-image review.
