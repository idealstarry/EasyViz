# Synthetic preview regression fixture

This small table is synthetic. It checks literal observation IDs (`001`, `NA`,
`null`), tied values, exact source value text, unused columns, and two or three
actual descriptive distribution previews. It supports no biological inference.
Every group has five distinct values, so the request explicitly includes the
optional KDE violin. The density eligibility guard does not validate density
interpretation for scientific use.

Copy this directory to a writable project and run `preview_choices.py` with
`--data source.csv --request request.json --out NEW_DIRECTORY`, using absolute
paths. Installed fixtures remain unchanged. The output includes actual panel
exports, separate captions, source and request snapshots, all observations,
the ECDF tie audit, fixed-size QA and a choice manifest with no automatic winner.
