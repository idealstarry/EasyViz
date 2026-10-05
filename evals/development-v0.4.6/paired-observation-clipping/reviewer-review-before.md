# Independent paired raw-observation review — initial frozen candidate

Reviewer: `/root/v045_literature_cases`. Candidate `staged-runtime/paired_plot.py` SHA256: `2ab35e1dc65592cbabb82dda6903dcd95d144a5603c123129d148444fa0e6d42`. All frozen sources and original evidence remain unchanged. This record is the initial assessment and must remain intact if a later candidate fixes the finding.

## Finding requiring repair

The existing `prepare()` uses `pd.read_csv(... dtype=object, keep_default_na=False)` without validating literal CSV row widths. A source with three headers and four cells per record is silently accepted through Pandas' inferred index. With headers `id,condition,value` and records `extra,u1,A,1`, `extra,u1,B,2`, `extra,u2,A,3`, `extra,u2,B,2.5`, the candidate exports a panel and records `valid_outputs: true`. Its new raw-group metadata claims units `u1` and `u2`; the literal named `id` source column contains `extra`. This is an inherited parsing defect exposed by the stronger source-record/unit mapping promise, not a newly introduced glyph or geometry change.

The real false acceptance is preserved under `reviewer-malformed-row/`: source CSV, adopted specification, actual exports, QA/settings/map and `evidence.json`. Before approving the input mapping claim, reject inconsistent CSV row widths and ambiguous headers before Pandas parsing and add a real malformed-row regression. No scientific values or condition identities should be inferred from shifted cells.

## Checks that passed

All 15 focused staged tests passed independently in 3.741 s; their log is `reviewer-focused-tests.log`. Seven additional actual probes in `reviewer-probe.py` passed: unsorted source rows and tied values with three explicitly reordered conditions/two blocks, both swarm and jitter; source ordinals and literal unit identities matched actual `PathCollection` offsets; `/` and `~` group labels produced escaped real JSON pointers; absent declared block/condition refused before an empty collection; omitted point color/alpha exposed no fabricated editable pointers; explicit unblocked color exposed only its real option path. The complete probe result is `reviewer-probes.json`.

The actual PNG-only case was checked against its image pixel dimensions, the report's actual millimetre canvas, source record 3, identical QA/settings reports, vector pass and raster `needs_revision`; it correctly rejects `valid_outputs` although the nominal mark/source audits pass. The linear and logarithmic endpoint tests also passed with true source record identities.

I independently compared all four preserved before/after pairs. PNG, PDF, plotting-data, summary-data and stats bytes are identical; SVG XML is identical after removing only the two raw group ID attributes. Normal-input numerical science, locked ranges, glyphs and appearance therefore remain unchanged in these actual fixtures. The actual group registrations and report integration are suitable once the malformed source entrance is repaired.

Current verdict: **needs revision for the CSV source mapping finding**. The checks certify raw circular observation registration and confirmed per-format clipping acceptance only. Summary/connector envelopes, aesthetics, statistical appropriateness and undeclared dependencies remain outside this review.
