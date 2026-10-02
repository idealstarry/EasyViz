# Independent visual review

Status: **ready_with_notes** for the six supplied views. No critical or major visual failure was found. One minor outline mismatch remains in both Urschel paired guides. This is visual/export readiness only; numerical coverage and statistics were deliberately not checked.

All current original PNGs and both reference crops were opened. Each PDF was rendered at 96 dpi as a final-size screen proxy and opened. No plotting scripts, renderer QA records, numerical source data, earlier candidate images or browsing informed the findings.

| Candidate | Direct export evidence | Visible reading result |
| --- | --- | --- |
| ECDF | 105 × 85 mm; embedded Arial; 8 pt text | Both stepped marginal curves remain clear across the log axis; small two-entry guide keeps the data primary. Time-point colors are explicitly disclosed as a new create mapping. |
| Urschel unconnected | 105 × 96 mm; embedded Arial; 8 pt text | Four swarm distributions and median/IQR overlays are readable. Compact single-row cohort guide uses about 46% of plot width but little height. Adopted omissions of p-value brackets, undefined dotted guides, boxed text and panel letter are respected. |
| Urschel connectors | 105 × 96 mm; embedded Arial; 8 pt text | Low-opacity bands visibly express predominantly upward paired change. Dense crossings limit individual path lookup; summaries and points remain clear. The caption correctly identifies the connector layer as an addition. |
| Truong components | 150 × 100 mm; embedded Arial; 8 pt text | Rose/peach/green segments separate well; dark total points and total-SD strokes remain visible. Near-zero controls remain present but cannot support fine component comparisons on this common scale, as the caption explains. |
| Truong ratios | 150 × 100 mm; embedded Arial; 8 pt text | Current axis reads HDR/mutEJ ratio. Hatched controls, their raw points and the small state guide remain clear. All seven long rotated labels fit at the screen proxy. |
| Truong grouped | 175 × 100 mm; embedded Arial; 8 pt text | Wider spacing supports three components per condition. Small 4 pt² dots remain distinguishable; controls sit close to zero. Legend uses about 28% of plot width and stays secondary. |

Power-of-ten superscripts use 5.6 pt inside otherwise 8 pt labels, verified directly in the PDF. PNG metadata is approximately 300 dpi, with correctly rounded physical-size pixel dimensions.

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| minor | Urschel bottom cohort guides, both views | Plotted points visibly carry thin gray edges; legend circles are solid borderless fills. Cohort association remains clear. | Consistent dot/guide outline policy for the adopted gray-edged point design. | Give both legend circles the same 0.25 pt gray edge; retain the agreed text size and compact guide footprint. |
| note, resolved | Truong grouped point-size brief | Initial adopted wording said 7 pt² for all raw points, while grouped-spec.json said 4 pt². The final brief explicitly adopts 4 pt² for the denser 175 mm grouped view. PNG/PDF hashes remain unchanged. | Specification and physical mark-size policy must agree. | Keep the explicit grouped exception with the example. |
| note | Reference adaptations | Source features were visibly inspected. Dual axes, source comparison stars and uncertain component-boundary intervals are intentionally replaced by single scales and total-SD/component-SD definitions. | Distinguish observed reference features from the disclosed create views. | Retain the supplied separate captions; do not restore omitted source annotations. |

| Check outside visual reading | Result | Limit |
| --- | --- | --- |
| Source coverage and recomputed statistics | not_checked | Excluded to preserve independent image review; a separate numerical audit is needed. |
| Refinement preference over an earlier candidate | not_checked | No baseline comparison was commissioned and earlier candidates were excluded. |
| Print proof / journal acceptance | not_checked | A 96 dpi screen proxy does not establish either. |

The exact PNG/PDF SHA-256 hashes, current adopted-input hashes, PDF font evidence and dimensions are recorded in `review.json` and `independent-export-inspection.json`. The final Urschel unconnected output is independently byte-identical to the inspected first-render PNG/PDF. The review applies only to these bound candidates.
