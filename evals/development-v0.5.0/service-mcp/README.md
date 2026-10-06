# Shared figure service and optional MCP validation

Verified on 2026-10-06 with Python 3.12.2 and the official optional
`mcp==2.3.0` SDK. This validates local service operations and protocol behavior;
it does not establish automatic idle-chat activation or figure aesthetics.

| Check | Result | Evidence |
| --- | --- | --- |
| Shared service regression suite | 21 passed, 18.204 s | [Log](service-tests.log) |
| Existing local workbench suite | 37 passed, 15.679 s | [Log](workbench-regression.log) |
| Existing preparation/acceptance/restore suite | 24 passed, 2.216 s | [Log](apply-restore-regression.log) |
| Official SDK stdio negotiation/tool discovery | Protocol `2026-07-28`, 13 tools | [Record](protocol.json) |

The new service suite exercises actual core-rendered SVG/PDF/PNG previews,
unchanged source observations and fixed physical dimensions, immutable accepted
exports, duplicate batch submissions, mixed cosmetic/Agent requests,
cross-process job locking and cancellation, timeout, restarted services,
HTTP Origin/token checks, export downloads, comparison/switching,
acceptance/restore, official in-process and stdio MCP clients and scoped access.
It also checks that the MCP defaults follow the browser's explicit review
selection rather than a stale configured initial attempt.

An adopted adjusted-analysis round trip covers analysis → core figure →
automatic recolor → acceptance → copied restore → explicit portable rerender.
The original analysis directory is deleted before the final render, and the
statistical test is patched to fail if plotting tries to recompute it. Adopted
P values, selected populations, trace and report digests survive; restored
accepted spec/export bytes remain exact, with a derived `rerender-spec.json`
for fresh use of the captured report bundle.

Independent audit regressions cover the publication window after an applied
ledger event but before registry publication, exact committed QA-byte binding
during recovery, cancellation before Agent-only handoff, review-only scopes
that cannot contain sibling attempts, and Ctrl-C reaping the owned renderer.
A lazy analysis helper no longer leaks into the declared inputs of later
ordinary plots in the same Python process.

Primary SDK references: [official Python SDK](https://github.com/modelcontextprotocol/python-sdk),
[SDK clients](https://py.sdk.modelcontextprotocol.io/client/),
[server tools](https://py.sdk.modelcontextprotocol.io/servers/tools/),
[MCP server guide](https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server).
The optional SDK is installed only in the development interpreter. It is not
required by ordinary workbench/CLI use and is not bundled into the plugin.
