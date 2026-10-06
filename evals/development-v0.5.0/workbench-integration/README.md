# Actual workbench and client checks

Verified by the main Agent through the Codex in-app browser on 2026-10-06.
The local fixture is synthetic: six observations, two groups, a 110 × 80 mm
scatter panel and Arial 8 pt. This is service/UI evidence, not a scientific
design or skill-effectiveness comparison.

## Actual browser operations

1. Select the mapped Control group; inspect its source records, editable spec
   paths and current color. Save a structured color change and a separate
   free-form legend instruction in one numbered batch.
2. Render the supported color request from the plotting code. The service
   produces fresh SVG/PDF/PNG and leaves the legend instruction pending on
   its original source attempt.
3. Inspect the matched previous/current views, accept the result and restore
   accepted source/spec/export bytes as another registered attempt.
4. Write an unsaved draft on a preview. **Review remaining requests** returns
   to the original request ledger; returning to the preview retains the draft.
5. Clear unsaved drafts and add a note: numbering starts at 1 when that attempt
   has no saved annotations. Saved annotations keep their own existing numbers.
6. Repeat a code-backed preview and verify its readable version name. An actual
   post-Accept disabled-button defect was fixed; after the fix, accept a restored
   attempt and successfully open the original pending instructions.
7. Use Home/Enter on the real version menu to switch to the original attempt.
   Inspect 1280 × 900 desktop and 390 × 844 narrow layouts. The narrow document's
   scroll width is exactly 390 px: no horizontal overflow. The comparison stacks
   vertically. Reset the viewport, close the owned tab and stop the test server.

[Desktop result](preview-proof.jpg) · [Narrow layout](narrow-proof.jpg) ·
[Recorded service outcomes](integration-record.json).

The deterministic [client checks](../workbench-ui/README.md) additionally cover
late jobs, cancellation, disconnection, stale source, drafts and operation-state
controls. Browser inspection and that event harness are separate evidence.

## Protocol scope

The [official SDK protocol checks](../service-mcp/README.md) and
[extracted-package SDK round trip](../package-audit/extracted-mcp.json) did
negotiate a session, discover tools and inspect scoped resources. These prove
adapter behavior. Automatic host activation and cross-client Agent execution
remain separate compatibility targets.
