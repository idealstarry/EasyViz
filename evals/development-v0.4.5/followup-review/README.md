# Later Create corrections retain their history

The Ccl2 case completed three initial visual passes. Independent inspection
then identified partially hidden same-hour group means. The continued task
explicitly authorized a focused fourth correction. Recording that output as
pass 3 would misstate its first-delivery history.

The isolated helper adds an explicit `followup` phase with a cumulative pass
number, a concrete correction reason and byte-bound prior review evidence.
Followup packets use a separate directory and state
`first_delivery_claim: false`. They retain current source/export/QA checks;
changing prior evidence also invalidates the recorded correction.

Default first-delivery packets retain their existing shape and 1–3 limit.
A later-feedback record does not establish bounded first-delivery success,
prove an image was opened or independently verify a claimed pass count.

The 28 existing review tests and four new actual-export checks passed against
the isolated helper. Test attestations are fixtures, not image inspection.
Independent review and production integration are recorded separately.
