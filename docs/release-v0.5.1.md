# EasyViz 0.5.1

Editable figure projects and a clearer workbench-to-Agent review loop.

## Editable projects and an independent workbench

- SVG is the default graphic export. PDF, PNG and TIFF remain available when
  explicitly requested, at the same physical panel dimensions.
- A single `.ev` project carries the current SVG, genuine nonempty element
  mappings, source provenance, plotting code/settings and declared inputs. Import validates
  and stages that project without executing its code.
- The local workbench opens its project library without requiring a selected
  figure. Users can import `.ev`, choose an attempt, add separate numbered
  instructions and compare versions.
- Each numbered annotation takes a plain-text comment. Compact annotation,
  request and history pages keep the inspector aligned with the figure;
  full saved comments remain available to the Agent and in a reading dialog.
- Figure names are editable in the heading. Names are shared with MCP, portable
  `.ev` projects and editing workers while preserving annotations and source
  versions. They do not add titles to the scientific canvas.

## Submit edits to a connected Agent

- The normal review loop is **Save drafts**, then ask the original Agent chat
  to apply the saved comments. The Agent reads them directly, edits the plotting
  code and returns a fresh reviewed attempt for comparison. This loop requires
  no copied comments or host scheduled task.
- **Save drafts** stores instructions; **Submit edits** queues work for the
  connected original authoring session. The active Agent receives that batch
  through a bounded MCP wait, edits the source and renders a fresh attempt in
  the same conversation. The page distinguishes waiting, received, editing,
  rendering, reviewing and completed results from actual task events, with
  cancellation and per-request outcomes.
- The optional MCP adapter exposes `connect_session`, `wait_for_submission`,
  `report_session_progress` and `complete_session_job`, alongside existing
  attempt/request/render tools.
  A connection expires without renewal; session labels alone do not prove
  end-to-end delivery.
- Every edit targets a fresh attempt. Source/data and export checks precede
  applied outcomes; unfulfilled requests remain pending. Acceptance and
  restoration remain explicit review actions.

## Reliability fixes

- Cancelled or closed MCP waits cannot silently claim later submissions.
- Completion preserves the source figure's adopted export formats.
- Fresh attempts inherit custom figure names; renaming refreshes the local `.ev`.
- Open-bar interiors are selectable, and annotation badges avoid nearby points.
- Saved-comment processing and submitted jobs share completion safeguards so
  one batch cannot be applied twice or leave an unfinished job blocking edits.
- Portable packages exclude temporary request locks and local service state.

## Validation

850 tests passed. The full portable-package check also passed, including actual
redraws from extracted resources. The release requires successful GitHub Core
checks on its commit; [the QA record](../evals/release-qa/v0.5.1/README.md)
includes the reviewed scope, actual workbench evidence and applicable limits.

## Boundaries

Live original-session delivery requires an actual session binding and an Agent
active in its bounded submission waits. Optional host scheduled checks require
a successfully created original-conversation task with an explicit interval
and expiration, followed by local registration. Host scheduling availability
and timing are independent of MCP; registration alone does not prove idle
delivery. Saved requests remain available for the original Agent's next turn.
The project's original owner persists across expired connections.
The separate dedicated CLI worker requires an available,
authenticated Codex client and rendering environment; it starts a fresh
headless session and is used only when explicitly requested. It is never a
silent fallback for the original session.

SVG interaction uses actual element mappings. A scatter collection can remain
a group, and raster layers stay raster. Renaming a graphic to `.ev` cannot add
missing code or individual observation identities. Both Create and Reproduce
retain their scientific, reference and final-size review rules.
