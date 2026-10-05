# 0.5.0 ecosystem research

Observed **2026-10-05 UTC**. This is preparation for a future major release;
no comparison repository was installed or executed and no 0.5.0 runtime was
implemented. The [proposal](../../docs/roadmap-v0.5.0.md) turns these observations
into three bounded release themes. Sources are primary repository files and
official documentation, not search summaries or popularity rankings.

[GitHub snapshot](github-snapshot.json) records canonical repositories, default
branches, exact observed commits, commit dates, license paths and whether a tree
query was truncated. [File records](inspected-files.json) identify 51 retrieved
source/license files by commit, path, byte count and content binding. Source
files were cached temporarily outside the checkout for bounded source reading;
their implementations are not vendored here. Downloading a file is not a full
code audit. [Architecture snapshot](architecture-snapshot.json) records the
EasyViz baseline inspected while this research ran alongside the minor-release
work.
[Official-page observations](official-pages.json) separately record the
protocol, SDK, composition and figure-design pages read during the survey.

## Repository comparison

The first four projects concern scientific Agent workflows, the next three
provide styling/composition/selection mechanisms, and the last two inform a
future transport adapter. Dates below are **observed HEAD commit dates**, not
claims about when a particular feature first appeared.

| Project and pinned observation | License inspected | Implemented fact and useful design | Adaptation for EasyViz; evidence limit |
| --- | --- | --- | --- |
| [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/92ace75ac21efe19a620434e0ca4e356081fe807), HEAD 2026-10-05 | [MIT](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/LICENSE.md) | Scientific visualization has scoped styles, lazily loaded helpers, metadata inspection and dated publisher profiles. | Learn progressive package/API guidance and separate export screening from aesthetic review. Its breadth or self-reported adoption does not demonstrate better first Create panels. |
| [cnsplots](https://github.com/faridrashidi/cnsplots/tree/626baf754b0e0289113fd66eade43828db130b63), HEAD 2026-09-28 | [BSD-3-Clause](https://github.com/faridrashidi/cnsplots/blob/626baf754b0e0289113fd66eade43828db130b63/LICENSE.md) | Unit-aware canvas/axes sizing, temporary settings contexts, explicit `ax` composition and bundled Agent Skill. | Learn physical-unit clarity and settings scoping. Its base dependencies include Scanpy, survival and complex-heatmap packages; wholesale adoption expands EasyViz's footprint. Its name is not evidence of journal acceptance. |
| [AgentFigureGallery](https://github.com/Dsadd4/AgentFigureGallery/tree/0b55f26fd575a00b5ebacb619d953b0a008e0126), HEAD 2026-09-05 | [MIT](https://github.com/Dsadd4/AgentFigureGallery/blob/0b55f26fd575a00b5ebacb619d953b0a008e0126/LICENSE) | A dependency-free Python controller queries external reference packs, serves a local gallery, persists task/global preferences and exports selected reference metadata. | A small mechanism index and optional preference scope are relevant. Mandatory human selection would delay the autonomous first delivery. Corpus claims were not independently recounted; repository licensing does not establish every image's reuse terms. |
| [SciVisAgentSkills](https://github.com/KuangshiAi/SciVisAgentSkills/tree/5c9ce7d28905af949dc4192b8984a44a7a5d9402), HEAD 2026-06-02 | No root license file observed in the complete 15-file tree; GitHub license field null | Four tool-specific workflows cover ParaView, napari, VMD and TTK, including headless operation, setup and API/error guidance. | Learn bounded tool contracts and environment checks. These are microscopy/3D workflows, not evidence for manuscript barplot quality. Do not vendor its material without permission. Some host installation notes are dated. |
| [SciencePlots](https://github.com/garrettj403/SciencePlots/tree/b9b16959570bd2fbc9ff5118bacc423c3bddd592), HEAD 2026-06-23 | [MIT](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/LICENSE) | Small composable Matplotlib style files; the package depends on Matplotlib. | Learn explicit stroke/palette override composition. Its base style selects serif/LaTeX, inward ticks on four sides and tight export, so direct adoption changes EasyViz's canvas/font conventions. A style cannot select a scientific reading task. |
| [Vega-Lite](https://github.com/vega/vega-lite/tree/213faf313cd2e8b1f94b61d24e90cac2e77b576e), HEAD 2026-10-01 | [BSD-3-Clause](https://github.com/vega/vega-lite/blob/213faf313cd2e8b1f94b61d24e90cac2e77b576e/LICENSE) | Explicit layered/concatenated view specs, shared encodings, scale resolution and point/interval selection compilation. | Learn relationships between views, scales and selections. Keep Matplotlib as the scientific drawing core; adopting a second JavaScript renderer would require a separate fidelity/export evaluation. |
| [mplcursors](https://github.com/anntzer/mplcursors/tree/566963caa0c527825e735c9146c9fae129ac898c), HEAD 2026-03-18 | [Zlib](https://github.com/anntzer/mplcursors/blob/566963caa0c527825e735c9146c9fae129ac898c/LICENSE.txt) | Artist-specific picking returns an artist, data-coordinate target, index and pixel distance; implementation handles collections and containers differently. | Learn explicit capability/granularity and source-record binding for custom SVG maps. Its interactive Matplotlib events are not a drop-in browser editor; not every artist is supported. |
| [AntV chart MCP](https://github.com/antvis/mcp-server-chart/tree/e2a8fb7c185e17c75c067817ff1a2acfddf49aa1), HEAD 2026-08-27 | [MIT](https://github.com/antvis/mcp-server-chart/blob/e2a8fb7c185e17c75c067817ff1a2acfddf49aa1/LICENSE) | Chart tools use schemas, filtering and stdio/HTTP transport; chart generation posts options to a configurable service, whose default endpoint is remote. | Learn small tool descriptions and filtering. Do not infer local processing, statistical fidelity or scientific aesthetics from MCP support or chart count. EasyViz should retain local files/code and its adopted uncertainty/source contracts. |
| [Official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk/tree/91941ed4d3985d59def99e090baa3f880c626cc8), HEAD 2026-10-05 | [MIT](https://github.com/modelcontextprotocol/python-sdk/blob/91941ed4d3985d59def99e090baa3f880c626cc8/LICENSE) | Tools/resources, typed inputs, transports, progress, cancellation and HTTP security configuration are present. | A future optional adapter can wrap stable local operations. A protocol library does not define EasyViz source identity, reliable render transactions or automatic host Agent dispatch. Pin a released SDK and test actual hosts. |

## Features checked beyond repository descriptions

**Scientific Agent Skills:** its
[visualization Skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/skills/scientific-visualization/SKILL.md)
distinguishes data semantics, physical export and manual inspection. The
[style helper](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/skills/scientific-visualization/scripts/style_presets.py)
uses scoped starting points and keeps optional imports lazy. The
[export-plan code](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/skills/scientific-visualization/scripts/export_plan.py)
records profile date/phase and emits review states for mismatches. These are
useful architecture patterns, not proof of a visual-quality gain.

**cnsplots:** the
[Skill](https://github.com/faridrashidi/cnsplots/blob/626baf754b0e0289113fd66eade43828db130b63/src/cnsplots/_agent_skill/cnsplots/SKILL.md)
requires checking the installed public API and distinguishes whole-canvas sizes
from multipanel axes areas. It also documents that tight cropping changes saved
bounds. Its
[settings context](https://github.com/faridrashidi/cnsplots/blob/626baf754b0e0289113fd66eade43828db130b63/src/cnsplots/_settings.py)
temporarily scopes settings and Matplotlib state. The
[heatmap helper](https://github.com/faridrashidi/cnsplots/blob/626baf754b0e0289113fd66eade43828db130b63/src/cnsplots/helpers/_heatmap.py)
has explicit legend/layout synchronization and clustering-memory checks. These
specific mechanisms are more informative than the package's promotional label.

**AgentFigureGallery:** the
[Skill](https://github.com/Dsadd4/AgentFigureGallery/blob/0b55f26fd575a00b5ebacb619d953b0a008e0126/skills/agent-figure-gallery/SKILL.md)
keeps its corpus external. The
[controller](https://github.com/Dsadd4/AgentFigureGallery/blob/0b55f26fd575a00b5ebacb619d953b0a008e0126/agentfiguregallery/server.py)
filters by plot type/global rejection and exports selected or liked candidates;
that metadata handoff does not itself draw or scientifically validate a new
panel. The observed
[dependency declaration](https://github.com/Dsadd4/AgentFigureGallery/blob/0b55f26fd575a00b5ebacb619d953b0a008e0126/pyproject.toml)
is empty. External packs can still be large and separately licensed.

**SciVisAgentSkills:**
[README](https://github.com/KuangshiAi/SciVisAgentSkills/blob/5c9ce7d28905af949dc4192b8984a44a7a5d9402/README.md)
and napari/ParaView workflow files were inspected. Its ParaView MCP reference
documents another project's interface; the inspected repository contains no
server implementation. The README assertion that Codex lacks a native skill
loader is not applicable to the inspected EasyViz plugin setup. Recheck host
guidance instead of copying that installation statement.

**SciencePlots:** the
[base style](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/src/scienceplots/styles/science.mplstyle)
and [bright palette](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/src/scienceplots/styles/color/bright.mplstyle)
were read directly. The precise defaults above come from those files. A
palette file does not account for small-mark contrast, category decoding,
uncertainty hierarchy or the ratio of body width to group spacing.

**Vega-Lite and mplcursors:**
[layer](https://github.com/vega/vega-lite/blob/213faf313cd2e8b1f94b61d24e90cac2e77b576e/src/spec/layer.ts),
[concatenation](https://github.com/vega/vega-lite/blob/213faf313cd2e8b1f94b61d24e90cac2e77b576e/src/spec/concat.ts)
and [selection compilation](https://github.com/vega/vega-lite/blob/213faf313cd2e8b1f94b61d24e90cac2e77b576e/src/compile/selection/index.ts)
establish actual composition primitives. mplcursors'
[picking code](https://github.com/anntzer/mplcursors/blob/566963caa0c527825e735c9146c9fae129ac898c/src/mplcursors/_pick_info.py)
explicitly distinguishes scatter indices, line segments and bar/errorbar
containers. An index describes a rendered artist's input; EasyViz still needs
a documented mapping to retained source records.

**AntV:**
[tool registration](https://github.com/antvis/mcp-server-chart/blob/e2a8fb7c185e17c75c067817ff1a2acfddf49aa1/src/server.ts)
and [boxplot schema](https://github.com/antvis/mcp-server-chart/blob/e2a8fb7c185e17c75c067817ff1a2acfddf49aa1/src/charts/boxplot.ts)
were read. The
[generation implementation](https://github.com/antvis/mcp-server-chart/blob/e2a8fb7c185e17c75c067817ff1a2acfddf49aa1/src/utils/generate.ts)
posts chart options using Axios, and
[environment code](https://github.com/antvis/mcp-server-chart/blob/e2a8fb7c185e17c75c067817ff1a2acfddf49aa1/src/utils/env.ts)
sets the remote default. The schema supports categories/values/group/style;
it does not establish EasyViz's experimental-unit, SEM/SD or source-to-artist
invariants. No remote data was submitted during this research.

## Current protocol observations

The official `latest` specification resolved to
[2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28).
The SDK's separate
[stable-release observation](sdk-release-snapshot.json) records **v2.3.0**, published
2026-10-02; it is distinct from the moving HEAD used for source inspection.

The current core uses per-request capabilities; the
[transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
documents compatibility with earlier connection-scoped versions. Durable
[Tasks](https://modelcontextprotocol.io/extensions/tasks/overview) and
[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) are optional
extensions, requiring explicit counterpart support. Older 2025 task examples
must not be presented as universal current behavior. EasyViz should start with
explicit local job handles and verify each target host's actual extension and
legacy-protocol behavior.

The SDK
[cancellation documentation](https://py.sdk.modelcontextprotocol.io/handlers/cancellation/)
distinguishes cooperative synchronous-worker cancellation from async handler
cancellation and identifies HTTP options that suppress cancellation propagation.
This motivates tests of owned renderer termination and output publication,
rather than merely testing that a tool call returns a cancelled response.
[Progress](https://py.sdk.modelcontextprotocol.io/handlers/progress/) is useful
only when a client requests it; phase/job status must remain available through
the portable local interface.

Tool annotations and the MCP transport do not enforce project filesystem scope.
Source/job/attempt identity, authorization and diagnostic redaction remain
EasyViz design work. Resource change notification is not proof that a host will
wake an Agent or automatically act on a saved batch.

The [current SDK roots/sampling guide](https://py.sdk.modelcontextprotocol.io/handlers/sampling-and-roots/)
also marks those features deprecated for the 2026-07-28 protocol and states
that roots are informational. A new adapter should take explicit project/artifact
handles from its configuration and authorized calls, with separately tested
legacy compatibility.

## What remains unproven

This research establishes implemented interfaces and relevant design patterns.
It does not rank render quality, measure speed, verify complete third-party
corpora, test Chinese-model performance or demonstrate successful MCP handoff
in a desktop client. Those require actual runs with frozen inputs and inspected
outputs. No code or image reuse is authorized merely by a repository badge;
verify file-specific terms before any future vendoring.

For first-output evaluation, use an already competent generic Agent baseline,
not a deliberately weak default plot. Record numerical correctness, visual
reading benefit and human intervention separately. Retain negative outcomes
as bounded evaluation evidence while keeping the main user-facing examples
focused on useful outputs.

The broader design guidance is consistent with
[Rougier et al.'s figure rules](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003833):
select the message, adapt visual organization to the audience and inspect the
finished figure. EasyViz's first delivery needs those decisions in addition to
a correct file export.

## Refresh procedure

`snapshot_sources.py` uses public GitHub metadata to refresh exact commits and
license-path observations. `inspect_sources.py` reads the explicitly listed
files at those commits; it never executes their code. Both require an
authenticated GitHub CLI/network connection and write only research metadata
here, with source content in a temporary cache. Refreshing changes the research
snapshot; preserve the old record when later decisions need its exact context.

Before implementation, refresh the SDK/protocol/host observations and recheck
the completed EasyViz 0.4.6 contracts. Review the proposal's acceptance criteria
against that actual baseline, then adopt the justified scope for 0.5.0.
