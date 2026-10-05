# Independent Workbench fix review

Reviewed on 2026-10-05. Runtime files were read only. This review independently inspected `figure_workbench.py`, `apply_figure_requests.py`, the new regressions, and the author's `workbench-audit.md`. Controlled probes used disposable test fixtures and patched execution checkpoints; no user/source exports or runtime files were changed.

The shared-lock/CAS and ordinary rollback fixes address the original lost-request and partial-ledger failures in the inspected implementation. This reviewer additionally reproduced a QA publication race and reported it to the owner/root. The subsequent frozen QA-binding repair independently rejects the original reproductions and passes the expanded tests. The earlier finding is resolved for the tested publication windows; legacy QA and external-writer limits remain explicit below.

## Verified fixes

- Request publication acquires the persistent OS file lock before rechecking the expected ledger bytes and figure version. The byte snapshot and parsed ledger come from the same read. Distinct Workbench instances/processes therefore cannot silently replace a cooperating writer's newer queue with an old snapshot. Stable resolved-path ordering avoids opposite-order acquisition for the two-ledger record operation.
- `record_requests()` holds both locks during the final source/target queue checks, both replacements and ordinary failure rollback. The injected failure after target replacement restores the exact previous bytes of both ledgers; retry retains independent target requests and writes the same application event to both histories.
- `accept_attempt()` holds the shared lock while publishing its snapshot/history. Ordinary publication failure attempts to restore the previous queue and removes its own partial snapshot. Recovery failures are explicitly reported instead of returning success.
- Restore rebinds both direct and nested settings source/spec/data paths to the frozen restored files. The focused-render regression checks those declarations through the independent Create provenance reader and verifies that accepted SVG/PDF/PNG, plotting data and statistics remain byte-identical.

## Earlier additional finding: QA changes were not included in publication guards

`record_requests()` initially reads target `qa.json` and requires `status: pass`, but its final locked check only verifies the figure version and source hashes. A concurrent renderer can change QA without changing those version fields yet: the core exporter explicitly invalidates QA as a rerender begins.

Probe A used the existing disposable Apply fixture. Immediately before acquiring the publication locks, the `ledger_serialized()` checkpoint changed target QA to `needs_revision` and `valid_outputs: false`, preserving SVG/source/spec/version and queue bytes. The result was:

```json
{"probe":"record_late_failed_qa","returned_action":"applied","target_qa_at_return":"needs_revision","source_request_status":"applied"}
```

`accept_attempt()` has the same early-only QA check and can additionally capture the invalidated QA inside the accepted bundle. Probe B changed QA to `in_progress` after the initial QA read while the specification was being read; this models the renderer's normal invalidation step, before its exports change. The accepted snapshot was created successfully with its own `qa.json` still `in_progress`:

```json
{"probe":"accept_qa_changed_before_snapshot","returned_acceptance":1,"accepted_snapshot_qa":"in_progress","current_qa":"in_progress"}
```

This was a requirement failure: history claimed application/acceptance after its required technical evidence became invalid. It was separate from queue-writer serialization. The owner/root received both reproductions; this independent reviewer did not edit their code.

## Final QA-binding repair: original finding resolved

The frozen `apply_figure_requests.py` SHA-256 independently checked for this re-review is:

```text
414015c56f6a520e6484c982a28730151b1bd548463a2834ca2a60c35de65435
```

`record_requests()` now binds the target QA bytes before planning, records their hash in the application event/result, and rechecks those exact bytes and declared export hashes before, between and after ledger publication. `accept_attempt()` additionally requires captured and written snapshot QA to match the same passing byte record; it checks the frozen snapshot exports and the current attempt's exports. The rejection and ordinary rollback paths preserve pending instructions.

This reviewer independently reran the **same two original checkpoints**, rather than only accepting the author's new tests:

```json
{"probe":"record_original_window_after_fix","rejected":true,"reason":"QA changed while recording application; retry after the attempt passes QA again","source_ledger_unchanged":true,"target_ledger_unchanged":true,"source_request_status":"pending"}
{"probe":"accept_original_window_after_fix","rejected":true,"reason":"A passing captured snapshot qa.json is required","ledger_unchanged":true,"accepted_snapshot_absent":true}
```

The expanded regressions also exercise changed passing QA bytes, changes after source/target replacement, changes around acceptance capture/publication, a corrupted written snapshot, and successful retry after restoring valid evidence. False, numeric zero, null and the string `"false"` in `valid_outputs` are rejected. The comparison uses identity with the Python boolean `True`; truthy strings/numbers are not accepted as that field's value.

The real-export regression renders distinct core SVG/PDF/PNG/TIFF outputs, substitutes a different actual PDF or TIFF while preserving the target QA and SVG/source/spec version, and verifies both `record` and `accept` reject the recorded-hash mismatch without changing either queue or leaving an accepted snapshot. It also rejects a live PDF replacement after snapshot creation. Restoring matching bytes permits recording/acceptance, and accepted PDF/TIFF hashes match the measured-export records.

One compatibility boundary is retained: `passing_qa()` permits old `status: pass` records that **omit** `valid_outputs`, and declared export byte checks only exist when QA actually records the export hashes. An independent minimal probe confirmed `{"status":"pass"}` is still accepted. Therefore this review's strict-boolean conclusion applies when the field is present; it does not claim all legacy records must contain it. Native current exporters supply `valid_outputs: true` and per-format hashes. The Create pre-delivery gate separately leaves missing PDF/TIFF measurement hashes `not_checked`.

## Independently executed checks

Interpreter: `/Users/starry/Desktop/EasyViz/.venv/bin/python`.

- Final frozen `test_apply_figure_requests.py`: **22 tests passed**, 2.077 s. Includes the expanded QA publication/capture/type checks, real PDF/TIFF substitution rejection, retry, dual-ledger/acceptance ordinary rollback, source tampering/path rejection, actual core rerenders and focused-render restore.
- Initial pre-QA-repair `test_apply_figure_requests.py`: **19 tests passed**, 1.566 s. That earlier passing suite did not establish the QA-window fix; the two diagnostic probes exposed its missing coverage.
- `test_figure_workbench.py`: **36 tests passed**, 14.662 s, including the seven Node client regressions and the real independent-process lock/termination case. Execution was approved for the local `127.0.0.1` test server; no remote listener was used.
- The original controlled QA-window probes exposed successful returns before the final repair. Their independent reruns now reject both operations and preserve the original history bytes/pending state as shown above.

## Limits

The executed OS-lock behavior is macOS/POSIX evidence. Windows locking was inspected but not executed. Queue locks coordinate participating request writers; they do not themselves freeze external renderers or malicious local writers. The final QA/export checks detect changes in the tested windows, not every possible later external mutation after the last check. Ordinary exception rollback is not a crash-atomic transaction across two files: process termination or power loss between replacements still requires recovery. Legacy QA without output-validity/export-hash fields retains the compatibility boundary stated above. This review did not run a real browser session, network fuzzing, arbitrary plotting scripts, or a general security audit. Its conclusions concern the scoped request/history/provenance behavior and the explicit probes above; no further concrete regression was reproduced in that scope after the frozen repair.
