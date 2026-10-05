# Independent repair-outcome review — EasyViz 0.4.3

**Final status: `ready_with_notes`; formal review passes 2 of at most 3.** This separate case loop does not alter the existing three-case report. The round-1 initial `ready_with_notes` judgment was withdrawn for the overlooked touching-outline flaw; that history is retained below and in JSON.

## Round 2: adopted task and proportion change

Primary: three independent 60 × 62 mm panels with slender separated open bars, Arial 8 pt and matching actual data rectangles. Their unscaled 180 × 62 mm composition is a preview. Transfer contains two independent panels and a 120 × 62 mm preview. Corrected global-scale grouped plots remain available at 110 × 82 mm.

Actually opened all five standalone PNGs, two composition PNGs and their 96 dpi PDF previews, both corrected grouped PNGs and their 96 dpi PDF previews, supplied rejected-layout PNG and scWAT p. 4. The visual judgment was sent before reading terminal numerical validation.

Top/baseline/condition rows visibly align across independent panels. Complete bright outlines and clear category gaps replace the rejected continuous touching boundaries. Outcomes are directly named on each y-axis; aliases fit without collision and are defined in captions. The retained grouped variants also have distinct components and visible nominal-size gaps. The control-exclusion sentence is now explicit and quoted, resolving the caption minor.

This applies an observable narrow-panel mechanism from literature. It does not prove that this particular dimension is a universal journal standard.

## Comparison boundaries

Corrected global-scale grouped candidate is preferred to the supplied rejected touching layout: outlines are independent, component/treatment spacing is organized and proportions are more compact. The baseline manifest confirms this is the user-supplied rejected screenshot, not a frozen renderer original or a published release candidate. Its attachment encoding/hash differs from the first-round opened renderer PNG; both actual images depict the rejected touching structure. The manifest records its origin and reconstructed old settings. No exact-byte historical or pixel comparison is claimed.

Primary split versus old grouped is **not checked as a matched cosmetic comparison**. Axes now differ explicitly: HDR 0–15%, HDR and mutEJ 0–6%, mutEJ 0–55%. They improve treatment reading within outcomes while equal physical heights no longer mean equal absolute percentages. The common caption states this, and the global-scale alternative supports between-outcome absolute comparison.

Near-identical triples, e.g. L755 HDR, remain very close in the nominal PDF preview; all observations can be drawn without every triple being separately countable on screen. Do not enlarge SDs or change values to disguise this limitation.

## Remaining findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Near-identical raw values/SD, especially L755 HDR | At nominal 96 dpi the replicate marks lie very close together and tiny SD intervals approach dot height. The reduced image alone does not let every triple be separately counted. | Keep every source observation and original mean/SD; do not overclaim separate-dot visibility. | Keep values, intervals and completeness checks. Do not shrink marks further or cosmetically enlarge small SDs. |
| note | Primary per-outcome scales | HDR uses 0–15%, HDR and mutEJ 0–6%, mutEJ 0–55%; axes visibly differ and the common caption explains that equal physical heights do not represent equal percentages. | The changed within-outcome reading task must remain explicit. | Keep the declared separate scales; use the retained global-scale grouped alternative for absolute between-outcome comparisons. Do not call this a matched purely cosmetic same-scale improvement. |
| note | Short treatment aliases | DMSO/NU/KU/L755/SCR7 fit and remain readable in 60 mm panels and nominal preview; captions define full names/concentrations and common transfer caption explicitly omits SCR7. | Aliases must preserve source treatment identity. | Deliver each individual caption with its panel and retain full source names/IDs in plotting tables. |
| note | Literature mechanism and claim scope | Narrow independent panels, aligned data regions and slender complete outlines reflect an observable literature mechanism. User-preferred 60 × 62 mm geometry alone does not establish publication-grade quality. | Keep case success distinct from universal CNS quality, model benefit or general panel-size rules. | State mechanism/task applicability rather than a publication/model causal guarantee. |

## Numerical/export checks, distinct from aesthetics

- **Source values, arithmetic means, sample SD and raw observations: passed.** Terminal validation.json reports 45 grouped candidate rows and 15 in each of three primary panels; transfer 24 grouped rows and 12 in each of two panels. Source-to-artist records pass with no normalization, derived ratios, inferred independence or issues. Supplied evidence read after round-2 visual judgment; statistics not independently recomputed by reviewer.
- **Unscaled preview composition: passed.** Supplied composition records preserve sizes, PDF text positions, font sizes, embedded fonts and unique SVG IDs, with no redraw. Actual composition PNG/PDF previews inspected. Composition integrity is supplied evidence; page dimensions, embedded fonts and current hashes independently checked.
- **Nine PDF/export sets: passed.** Independently ran pdfinfo/pdffonts: five standalone PDFs 170.079 × 175.748 pt; two grouped PDFs 311.811 × 232.441 pt; compositions 510.236 × 175.748 pt and 340.157 × 175.748 pt. These correspond to 60 × 62, 110 × 82, 180 × 62 and 120 × 62 mm. All fonts embedded ArialMT; SVG Arial/8px; PNG DPI 299.9994; all 27 PNG/PDF/SVG hashes match terminal validation. Actual saved files independently checked; PDF 8 pt text assertion supplied, SVG typography inspected. No calibrated print proof.
- **Actual independent-panel alignment: passed.** Parsed saved SVG clip rectangles are identical in all five primary/transfer panels: x34.015748, y9.666142, width130.110236, height144.992126 pt. Visible composite baselines/top/condition rows align. Independently inspected saved vector artifacts without reading renderer implementation.
- **Actual grouped stroke separation: passed.** Saved SVG rectangles/stroke widths yield within-treatment edge clearance 0.9819742306–0.9819745833 mm main and approximately 1.2817104583 mm transfer after subtracting both half-strokes. Nominal PDF previews visibly retain these gaps. Independently parsed saved SVG geometry; positivity alone does not prove aesthetic spacing.
- **Matched split-panel superiority, publication acceptance or model causal effect: not_checked.** Primary changes scales/reading task; no model or publication experiment supplied. Explicit claim boundary, not an unexplained readiness pass.

Exact inspected image hashes and all nine current export identities are recorded in JSON. Statistics and composition integrity use supplied numerical evidence; saved PDF dimensions/font embedding, SVG typography, hashes, data rectangles and actual stroke clearance were independently checked without implementation access.

No required critical or major visual conflict remains. The remaining point-reading, differing-scale and broader-claim limitations stay as notes. A third pass is unnecessary if current images remain unchanged.

**Status: `ready_with_notes`.**

---

## Round 1: preserved historical review and withdrawal

**Round 1 status: `needs_revision`; formal passes 1 of at most 3.** This is a separate case and review loop from the earlier box/violin/heatmap review.

The reviewer actually opened candidate and transfer PNGs, both 96 dpi PDF previews, and scWAT p. 4 Fig. 2. Specs, separate captions and provenance were read before `validation.json`. The initial visual judgment was `ready_with_notes`, but it overlooked a real visible defect: adjacent component outlines touch and obscure their independent boundaries. That judgment is withdrawn after the user flagged the problem and adopted non-touching separation and better proportions for this case. A numerical validator cannot make this unchanged rendering ready.

The initial strengths remain observations: outcome colors and a matching open-key legend are decodable; dark raw points and SD intervals have distinct roles; treatment labels wrap without collision; one global 0–55% axis retains both high and low outcomes. These do not cancel the layout failure.

This new 45-value grouped-outcome reading task differs from the 15-value single-HDR case. There is no matched same-task aesthetic baseline; preference is therefore `not_checked`, rather than declaring the new image superior merely because it contains more bars. scWAT supplies mechanisms of crisp marks and layered uncertainty, not a universal prohibition on touching bars or a direct performance comparator across different data.

## Findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| major | Within-treatment adjacent open bars; candidate and transfer | The plotted bars directly abut: each outcome's right edge coincides with the next outcome's left edge. Colored outlines merge/cover one another, particularly around the low blue/green bars in the three-outcome candidate. The reviewer initially overlooked this visible defect and withdrew the initial ready_with_notes judgment after the user explicitly flagged it. | The user adopted distinct, non-touching component outlines and better proportions for this grouped-bar case. This is an adopted case requirement, not a claim that every literature bar plot universally needs gaps. | Introduce a real physical gap between component strokes, preserve a larger inter-treatment gap, and inspect actual stroke-to-stroke separation at final size. Adjust bar/panel proportions as a whole rather than relying on thin shared borders. |
| minor | Both separate captions; excluded control names | The sentence “No donor/Cas9 and NTC controls are outside this declared treatment subset” can be read as saying that no controls are excluded. Provenance declares these named controls are excluded. | Caption must unambiguously describe source selection. | Quote control names and state explicitly: “The ‘No donor/Cas9’ and ‘NTC’ controls are excluded from this declared treatment subset.” |
| note | Very short outcome bars and SD intervals in both plots | On the global 0–55% axis, several HDR/combined values lie near 2–4%. Their small SD intervals meet the mean-top region and are much shorter than the high mutEJ bars. Points are visible at 96 dpi but fine. | Retain original units, all replicates and one scientifically meaningful global scale. | Keep the scale and source statistics; do not cosmetically inflate small SDs or add an unrequested broken axis to create apparent detail. |
| note | Task scope and aesthetic claim | Candidate displays 5 treatments × 3 outcomes, whereas the existing single-HDR example displays 5 × 1. More marks answer a different reading question. No same-task accepted baseline was supplied. | Do not use additional values/layers as proof of aesthetic improvement, model benefit or publication acceptance. | Treat this as a new grouped-outcome basic case. Keep its literal source/task limits and avoid a matched before/after superiority claim. |

## Numerical/export evidence, separate from visual readiness

- **Source values, means, sample SD and raw observations: passed.** examples/create/repair-outcomes/validation.json reports 45 candidate and 24 transfer source rows/raw points, original value strings retained, per-outcome mean/sample SD, no composition normalization, no ratios derived or independence inferred. Supplied record read after initial visual judgment; not independently recalculated by reviewer. Does not override the major touching-bar visual defect.
- **Actual PDF size and embedded font: passed.** Reviewer independently ran pdfinfo/pdffonts on both PDFs: one page each, 368.504 × 204.094 pt (130 × 72 mm within printed rounding), embedded Unicode ArialMT CID TrueType. Independently inspected actual saved PDFs.
- **PNG/SVG metadata and export identity: passed.** Reviewer inspected PNG metadata: 1535 × 850 pixels at 299.9994 dpi; nominal PDF previews 492 × 273 pixels. SVGs retain Arial/8px styles. All six PNG/PDF/SVG hashes match supplied validation. Metadata and hashes independently checked; 8 pt PDF text assertion remains supplied evidence.
- **Same-task aesthetic baseline, model causal benefit, physical print proof and publication acceptance: not_checked.** No same-task comparator or such broader evidence supplied. Outside the narrow case review; absence does not justify an improvement or publication-level claim.

Exact inspected image hashes are stored in `grouped-review.json`. Corrected PNG/PDF images must be opened for round 2; fixing metadata or passing tests alone cannot resolve the actual touching-outline defect. The existing three-case review is unchanged.

**Status: `needs_revision`.**
