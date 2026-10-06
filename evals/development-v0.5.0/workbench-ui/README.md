# Workbench client verification for 0.5.0

The client keeps the existing plain light surfaces, compact scrollable inspector,
anchored menus, numbered independent annotations, Requests / History tabs and
version-bound previous/current comparison. The current logo and versioned SVG
favicon are reused.

New capability-gated controls expose:

- Real mapped object and source identities, declared editable properties and
  current values supplied by the verified service.
- A supported structured property edit can be saved without repeating the same
  change in prose. Its saved instruction is generated from the explicit value.
- Code-rendered cosmetic previews, visible lifecycle status, cancellation and
  honest Agent handoff for unsupported requests.
- Registered attempt selection, acceptance, restoration and matching downloads.
- Per-request outcomes and a separate rendered attempt, preserving current
  exports until the user opens the new version.

A successful preview opens automatically only when its source is still the
visible attempt and there are no newly completed unsaved drafts. Otherwise the
result remains available through **Open rendered attempt**. A disconnect shows
**Status unavailable**, never an invented success or automatic Agent activation.

## Checks

`existing-client-tests.log`: all 7 existing event regressions passed. They cover
painted target picking, property intersection, stale source rejection, atomic
SVG/version loading, independent drafts, batch failure, storage isolation and
annotation numbering.

`client-contract-checks.log`: all 6 added local-service contract scenarios passed:
editable identity / structured save; mixed preview completion preserving new
drafts; automatic result opening / acceptance / restoration; source-bound remaining
requests with new-attempt draft preservation and post-accept action recovery; cancellation /
disconnection; stale source prevention.

A mixed preview also offers **Review remaining requests**. It opens Requests on
the original source attempt, leaving request identities and versions unchanged.
Any unsaved draft on the rendered attempt is preserved for a later return.

The real `workbench.js` is executed through the existing deterministic DOM/event
harness. Run `python3 evals/development-v0.5.0/workbench-ui/check_client.py` to repeat
the additional checks. JavaScript syntax checking also passed.

## Remaining integration QA

These harness checks do not establish browser layout, keyboard behavior in a
real browser, or successful execution of the server renderer. The root agent
records its separate in-app browser and actual renderer checks in
[workbench integration QA](../workbench-integration/README.md). Browser screenshots
and real export comparisons belong to that integration record, not this harness
verification record.
