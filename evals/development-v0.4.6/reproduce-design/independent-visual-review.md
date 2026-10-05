# Independent visual review of forest and radar revisions

Reviewer: `/root/v045_expression_create`. I opened each original reference image, the adjacent crop from the actual article PDF, the actual previous PNGs and each current revised PNG. I also rendered and opened every old and new PDF at 96 dpi: forest old A/B 105 × 135 mm, revised paired forest 100 × 132 mm, radar old 88 × 88 mm and revised radar 64 × 66 mm. These are explicitly different adopted canvases with unchanged 8 pt text, so this is a disclosed geometry refinement, not a same-size benchmark. The current revision specifications and separate captions were read. A separate read-only rerun of `verify_revisions.py`'s export-check functions checks actual source strings, PDF vectors/fonts/dimensions and SVG identities without importing either plotter.

## Forest: candidate preferred for the paired reading task

The actual original uses narrow, aligned total/direct lanes, three exposure blocks, identical outcome order and one shared color key. The previous single panels repeat every outcome name in each block and allocate much more width to the intervals; reading total versus direct requires comparing two large separate panels. The candidate visibly restores the reference's shared category decoding and vertical block structure. It is easier to see how each aligned direct estimate differs from its total estimate while retaining all eight outcomes. The final nominal PDF has complete labels and a readable shared key, with the estimates visually primary.

The 32 × 92 mm data lanes have a width/height ratio of 0.348, close to the actual source frames' 34.84 × 100.21 mm ratio. This supports the observed slimmer geometry; it is not a recovery of the original unknown font parameters. The source glyphs are outlined. The candidate explicitly adopts editable Arial 8 pt, 5.2 pt geometric circles and 0.8 pt intervals. Essential column names are bold and remain part of the decoding apparatus; adjustment wording belongs in the caption. All 48 estimates and 96 asymmetric endpoints, log odds-ratio axes and supplied hollow/filled states remain unchanged.

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Shared outcome key | The key is reorganized into four rows and two columns, rather than the source's uneven columns; all eight colors retain their identities. | Keep outcome lookup consistent across both lanes. | Accept the explicit adaptation and keep its caption/specification record. |
| note | ER-negative intervals and light subtype colors | Yellow and light cyan/pink remain lower contrast on white in the nominal PDF, as in the source crop. Boundaries and hollow states are still visible, but require closer viewing than the dark outcomes. | Reproduce the source palette relationship without claiming uniform contrast. | Retain this known reference feature; do not make a broad accessibility or print-proof guarantee. |
| note | Frame and exact typography | The candidate's frame is lighter than the source's measured approximately 2.12 pt frame, and source glyph point sizes are unavailable. | Distinguish adopted line/font parameters from recovered original parameters. | Record the difference; no pixel-identical or recovered-author-style claim. |

Current readiness: **ready_with_notes**. Preference: **candidate** for the stated paired total/direct comparison. This supports a visible structure/proportion improvement over the actual previous case, not publication acceptance or matched model efficacy.

## Radar: candidate preferred for reference mark proportions, with true central overlap

The supplied whole-figure reference contains six radars and shared class/method keys; only the depot kBET radar is the adopted numeric target. Both old and revised panels retain the same five-spoke order and method colors. The old 50 mm data circle makes its near-original-sized marks look small and detached. In the candidate, the explicitly adopted 34 mm circle and 5.1 pt marks restore a point-diameter/circle-diameter relationship close to the actual source's approximately 23.88 mm circle and 3.575 pt marks. The 0.85 pt data lines also closely follow the observed source stroke. At nominal 96 dpi, the candidate's data traces and reference rings are definite and class names remain readable.

Removing the unrequested depot title is appropriate; the separate caption now identifies which original radar is represented. Direct class labels around this standalone circle replace the source's whole-figure shared class key. That adaptation and its outside space are explicit, so the candidate does not claim exact whole-figure layout reconstruction. Metric labels, method key, radial ticks and actual zeros remain.

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Zero origin | Three exact zero marks coincide, and additional small rates cluster near the origin. Larger reference-proportion markers inevitably obscure some central boundaries. The actual source radar also has central overlap. | Preserve the true zero-origin radial scale and all values. | Accept this scientific limitation; retain the full source table and do not add fake inner padding, numerical jitter or selective point deletion. |
| note | Class labels and method key | The standalone candidate repeats direct class labels and uses a two-row method key; the source decodes classes/methods once across six radars. | Keep standalone lookup readable while acknowledging a different assembly context. | Retain the explicit adaptation, without claiming equality to the entire source Figure 1e. |
| note | Canvas comparison | Candidate 64 × 66 mm and baseline 88 × 88 mm differ physically. Both actual nominal PDFs were opened and both keep 8 pt text. | Do not attribute differences merely to thumbnail size or a hidden font reduction. | Report the adopted dimensions and mark/circle relationship alongside the visual preference. |

Current readiness: **ready_with_notes**. Preference: **candidate** for reproducing the selected radar's mark-to-data-region relationship. Individual central-value lookup remains limited; the candidate is not universally superior for every reading task.

## External checks

| Check | Status | Evidence |
| --- | --- | --- |
| Actual PDF dimensions and text | passed | Separately measured pages: forest 100.0000 × 132.0000 mm; radar 64.0000 × 66.0000 mm. Export checker rerun finds actual 8 pt embedded Arial and editable SVG text. |
| Literal source preservation | passed | Exact source snapshots and original numeric spellings checked; 48 forest estimates plus 96 interval endpoints and 25 radar vertices checked against actual PDF vectors. No upstream MR, integration, kBET or hypothesis test rerun. |
| Actual vector mapping | passed | Read-only checker rerun verifies 143 forest and 37 radar source-bound SVG IDs, all 5 closed radar traces and 3 unchanged origin zeros. Maximum actual PDF coordinate errors are below 0.000008 pt. |
| Separate current captions | passed | Both revision captions read after addition: model/CI interpretation, unknown per-estimate n, selected depot metric, source aliases, zeros and changed dimensions are stated. |
| Calibrated physical print and general efficacy | not_checked | Nominal PDF previews and actual export measurements support proportion/legibility review; no physical print test or matched model benchmark was conducted. These are outside this readiness claim. |

Final status: **ready_with_notes** for the two adopted revisions. No unresolved critical or major visual requirement was found. The residual differences above are retained and explicit.
