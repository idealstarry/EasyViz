# Independent visual review: scWAT broken-axis reproduction

Latest conclusion: the settled canonical Arial 8 pt candidate received independent pass 2 and is **ready_with_notes**. Its three actual export hashes match the refreshed check record; physical size, typography and fixed-size readability pass. The initial changing-version review below is historical evidence and is superseded by the pass 2 section at the end.

## Historical pass 1

Review date: 2026-10-06. Initial visual pass; a typography redraw was requested while this review was running. This record describes the initially opened DejaVu Sans candidate and must not be used as a review of the subsequent Arial candidate.

## Inspected evidence and version boundary

I opened `inputs/reference.png` and `output/panel.png`, read `spec.json`, `caption.md` and `actual-export-check.json`, then inspected the actual SVG and PDF when root explicitly permitted them. I did not inspect `plot.py`, author code, or an implementer verdict.

The initially supplied specification/caption explicitly adopted a 92 × 66 mm canvas, DejaVu Sans, 8 pt primary text and 7 pt y-axis ticks. Direct PDF font inspection showed an embedded DejaVu Sans subset; PDF text extraction and SVG text styles confirmed those 8/7 pt roles. Root subsequently requested canonical Arial 8 pt for all text roles. That is an updated requirement, not evidence that the initially adopted 7 pt ticks were illegible.

I also opened a direct PDF render at 96 dpi, 349 × 250 px, as a fixed-size screen proxy for the 92 × 66 mm panel. The 7 pt y ticks were small but readable; no tick crowding, glyph loss, clipping or label collision was visible. This is a rendered-size inspection, not a physical print test.

During later hash validation, the live outputs were being regenerated. Their hashes differed from the initially supplied export record, and a later SVG copy already contained Arial. Therefore this initial review has no stable image/vector/check-record hash binding. A final settled export packet must receive a fresh review; geometry observations below do not certify that packet.

## Structural comparison

The initial candidate preserves the reference's six-gene order, blue YT-FF/red YT-AKO order, open white mean bars, colored observations, whiskers, five displayed gene significance classes, and unannotated Prdm16. The high Elovl3 YT-AKO mean and observations occupy the upper segment, while the other groups remain in the lower segment. The y-spine interruption and continuous Elovl3 side outlines across the physical gap reproduce the reference relationship. Horizontal significance guides stay associated with the intended group pair.

The data remain visually primary. The two-entry legend sits in the upper-right open region; its keys match the open bars and do not cover observations. Its overall footprint is modest relative to the 66 mm-wide data region. The 45-degree gene names fit the lower margin without collision, and the y label is readable.

The source panel letter is intentionally omitted, and explanatory prose stays in the separate caption. The declared segment limits, full lower/upper SEM endpoints, fixed physical canvas and chosen typography are accepted adaptations; those differences are not pixel-reproduction failures. The caption explains the unequal numeric scale density, omitted interval, horizontal display offsets and source-reported significance classes.

## Findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| major | Typography/version | Initially opened SVG/PDF use DejaVu Sans 8 pt primary / 7 pt y ticks. The new requested canonical requirement is Arial 8 pt throughout; a later SVG had already changed during inspection. | Review the settled artifact against the latest adopted requirement. | Finish Arial 8 pt regeneration, update spec/caption/export evidence, freeze the packet and request a fresh review. Do not treat this initial review as approval of the redraw. |
| major | Export-check identity | The supplied record and live exports had different hashes during redraw. This prevents endorsing that record's source/SEM checks as checks of the exact inspected image/vector set. | Numerical/export evidence must identify the delivered files. | Refresh the check record after all exports are written; validate all three hashes before the next review. |
| minor | Low-value point clusters | The initial raster has visibly merged/partially overlapping dots in Ucp1 YT-AKO, several blue groups and Prdm16 YT-AKO. The reference separates the two low Ucp1 YT-AKO points more clearly. Retaining point objects does not make all five individually countable. | Observations should be readable while remaining associated with their own bar. | Consider deterministic collision-aware offsets within the adopted bar bounds for near-equal y values, preserving values, group association and marker size. If compact overlap is intentional, retain it as a stated visual limitation. |
| minor | Relative line/annotation weight | Against the reference's plot width and text, the candidate's colored bar outlines and short comparison guides read slightly finer/lighter. The actual initial SVG uses 0.65 pt bar/whisker strokes, 0.55 pt dark-gray comparison guides and 0.6 pt axes. The reference guides/stars appear darker and stronger. | Reproduce the relative hierarchy, allowing declared typography and final-size adaptations. | Optional refinement: modestly strengthen the comparison guides or use black, and assess outlines at the final size. Keep points/SEM endpoints visible; do not broaden everything indiscriminately. |
| note | Significance placement | Ucp1's guide is below the 15 tick in the candidate, while the reference places it near the lower segment's ceiling; Dio2's guide is close to/in the physical gap. They remain attached to the correct gene pair and clear of observations. | Comparison identity and no hidden observation/SEM endpoint; exact annotation coordinates were not fixed. | Keep the current positions if they are the deliberate adopted adaptation. For closer layout fidelity, move only Ucp1's guide toward the lower-segment ceiling after checking clearance. |
| note | Fixed-size readability | At the 96 dpi PDF proxy, the 7 pt y ticks can be read and do not collide. Colored 0.65 pt outlines remain visible; dense low groups require close viewing to distinguish individual dots. | Assess the agreed physical canvas; avoid shrinking agreed type to solve layout. | Retain this readability finding as historical evidence. Recheck the new 8 pt tick version without changing the agreed canvas. |

## External numerical and export checks

| Check | Result | Evidence and scope |
| --- | --- | --- |
| Initial PDF page size | passed | Direct `pdfinfo`: 260.787 × 187.087 pt, corresponding to 92 × 66 mm to the displayed precision. |
| Initial SVG canvas size | passed | Actual SVG header: 260.787402 × 187.086614 pt; viewBox uses the same dimensions. |
| Initial PDF font embedding/family | passed | Direct `pdffonts`: embedded CID TrueType DejaVu Sans subset. This passes the initially supplied adoption, not the later Arial requirement. |
| Initial 8/7 pt text-role measurement | passed | Actual SVG text styles and PDF XML font specs independently show 8 pt primary / 7 pt y ticks. |
| Initial PNG dimensions | passed | Opened candidate was 1087 × 780 px, consistent with the supplied 300 dpi rounded export dimensions. |
| Export-record hash binding | failed | Live files changed during review; later hashes did not match the initially supplied record. A later SVG already used Arial. |
| All 60 observation values/colors/positions and 12 mean/SEM summaries | not_checked for a stable reviewed version | The supplied check record reports these checks passed. This reviewer did not read source data or recalculate summaries, and the record could not be bound to the changing output set. |
| Upstream normalization, biological independence, original significance calculations, multiplicity handling | not_checked | They are outside this visual review; caption identifies the limits without claiming recomputation. |
| Physical printed-page readability | not_checked | Fixed-size screen rendering was inspected; no paper proof was supplied. |

The initial candidate has no visible scientific mapping or structural failure. The next useful step is a stable Arial 8 pt export packet and refreshed actual-export check, followed by inspection of its images. Low-point overlap and slightly lighter relative line weight are the remaining visual refinements. This review does not establish journal acceptance or any CNS-level guarantee.

Historical pass 1 status: **needs_revision** — canonical typography and exact-version binding were still changing at that time. Those two major findings are resolved in pass 2 below.

## Canonical Arial 8 pt candidate — independent pass 2

The reproduction owner explicitly froze the final PNG/SVG/PDF, current specification/caption and refreshed actual-export check before this pass. I reopened the canonical PNG and a fresh direct 96 dpi PDF render (349 × 250 px), inspected actual SVG text styles and header, ran direct PDF font/page inspection and verified all three current hashes. No implementation source or implementer verdict was read.

| Format | Actual SHA256, matching refreshed record |
| --- | --- |
| SVG | `cac601436c2e744373c5cf58e33e73248deed38ab911cdbb836af10433798161` |
| PDF | `b39dc2880e44303c817f461f51740f443ad81ba464321064217c52ffa167ab54` |
| PNG | `131306ab9bca362e508d1bcbb86830c1f60fa0f4bb3bb950c054b544e5dc05cc` |

The actual SVG has only Arial 8 pt text styles. The actual PDF embeds ArialMT, and the bound measurement record reports all selectable PDF text at 8.0 pt. The actual PDF page remains 260.787 × 187.087 pt, and the SVG remains 260.787402 × 187.086614 pt: 92 × 66 mm to reported precision. The previously found font-adoption and record-binding issues are resolved.

The structural matches from pass 1 remain: six ordered genes, blue/red group association, open mean bars, colored raw points, full lower/upper SEM, two linear segments, interrupted y spine, Elovl3's continuous side outlines across the physical gap, and the correct displayed `**`, `***`, `*`, `***`, `***` classes with none for Prdm16. The blank upper region accommodates a compact matching two-entry legend. No observation or SEM endpoint appears in the omitted interval. The separate caption now decodes the literal star keys and states that significance is author-reported rather than recomputed.

The fixed-size PDF proxy shows readable 8 pt ticks, gene names, y label, legend and stars, with no clipping or collision. The canonical Arial text is more compact than the historical DejaVu text; this is the requested typography adoption, not a demonstrated general aesthetic improvement. No physical printed proof was supplied.

### Residual visual findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| minor | Within-bar raw point separation | All 60 circle objects remain present. A direct SVG geometry inspection confirms 2.3 pt disk diameter; for example, the two low Ucp1 YT-AKO point centers are only about 1.336 pt apart, so their disks partially overlap. Several compact blue/Prdm16 clusters similarly appear merged. The reference more clearly separates the two low Ucp1 red points. | Preserve all observations and make individual observations readable while keeping bar association. | Optional: use collision-aware deterministic offsets within the adopted bar bounds for near-equal values. Retain the 2.3 pt marker size and scientific y values. The current partial overlap is a minor limitation, not missing observations. |
| minor | Relative mark/line weight | The candidate's colored bar outlines and dark-gray comparison guides read slightly finer than the reference when compared with each plot's category spacing/text. Actual candidate strokes remain 0.65 pt for bars/SEM, 0.55 pt for guides and 0.6 pt for axes. Bars also occupy a somewhat narrower fraction of the category interval than in the reference, consistent with the explicitly adopted 0.27 width. | Reproduce the mark hierarchy with the adopted final-size/style choices. | Optional refinement: modestly strengthen or darken only the short comparison guides, and assess bar outline prominence at final size. A width change would require updating the adopted style, not silently changing the current specification. |
| note | Significance placement | Ucp1's guide is below the 15 tick, whereas the reference places it closer to the lower-segment ceiling. Dio2's annotation sits near the physical gap. Neither obscures points or changes which pair is compared. | Correct pair association and preserved data/SEM endpoints; exact annotation coordinates were not fixed. | Retain as an accepted placement adaptation. For closer relative fidelity, move only the Ucp1 guide after checking star/point clearance. |
| note | Caption / biological context | The caption carries axis segments, offset semantics, source significance, units/normalization limits and panel-letter omission separately from the image. | Preserve data-reading text in the panel and relevant explanations in the caption. | No caption correction is required for the supplied review scope. Source typeface/size and upstream normalization remain unrecovered; do not turn the adopted typography into a recovered-source claim. |

### Final external and actual export checks

| Check | Result | Evidence and scope |
| --- | --- | --- |
| Exact image/vector identity | passed | Direct SHA256 of all three current exports matches the refreshed record, listed above. |
| 92 × 66 mm canvas / 1087 × 780 px PNG | passed | Direct actual SVG/PDF inspection and reopened PNG; bound check record agrees. |
| Arial 8 pt throughout / PDF font embedding | passed | Actual SVG contains only Arial 8 px text in the pt-based viewBox; direct PDF font inspection shows embedded ArialMT. The hash-bound check records actual PDF text sizes `[8.0]`. |
| 60 selectable observations | passed | Direct actual SVG inspection contains 60 observation circle objects, five for each gene/genotype. Bound check separately validates all 60 SVG/PDF positions/colors against supplied observations. |
| Twelve mean/full-SEM summaries | passed as external numerical check | The refreshed hash-bound record reports 12 independently checked means/SEMs and verifies displayed endpoints. This reviewer did not recalculate these from an unprovided raw table. |
| Fixed-size readability | passed | Canonical full PNG and direct 96 dpi PDF proxy opened; all 8 pt roles are readable without clipping/collision. Low-point partial overlaps remain explicitly listed. |
| Original tests, multiplicity, normalization, biological independence | not_checked | Outside the adopted visual/export review; caption does not fabricate them. They are not required new calculations for this reproduction. |
| Physical paper proof / publication acceptance | not_checked | Neither was supplied or inferred from successful export/review. |

The supplied reference relationship is faithfully retained within the declared adaptations. No critical or major finding remains in the canonical candidate. The useful next refinements are optional near-equal-point spacing and slightly stronger comparison-guide weight; neither requires altering scientific values, statistics, font or canvas. This result does not establish a CNS-level or other journal-quality guarantee.

Status: **ready_with_notes**.
