# Independent color-role review: EasyViz v0.4.3

**Status: ready_with_notes. Formal pass: 1 of at most 3.** Five current basic cases, five transfer probes, and ten nominal 96 dpi PDF previews were actually opened. The visual judgment was sent to the parent before reading numeric validation. No rendering implementation or other review report was consulted. This review is separate from the previous geometry and repair-outcome reviews.

The strongest improvement is in the distribution figures: categorical color now belongs to the IQR region, while observations, summary boundaries and KDE contours have independent dark contrast. This is a clearer observable division of roles than the previous tinted bodies and colored raw lanes. It supports a bounded aesthetic preference for these actual outputs; it does not prove general Create quality or publication acceptance.

## Actual comparison basis

The before files are frozen **published candidates from commit `900dc34dc14f580016c686f696021318a1b6c839`**, recorded in `before/manifest.json`. All ten before PNG/spec hashes match that manifest. They are the adopted gallery candidates the user criticized, not an intentionally weak default.

The numeric validator's `baseline` outputs instead correspond to baseline-spec demonstrations. Their PNG hashes differ from the frozen published candidates. Its statement that the violin candidate adds Q1/median/Q3 applies to that demonstration comparison. **The actual published-before violin already had this layer.** This review does not count it as newly introduced.

Comparing frozen and current specs found changes only in colors, area fill behavior and violin contour color/weight. Declared layout, numeric ranges, marker sizes, category order and lane geometry are unchanged. Box/violin now have filled IQR areas: the change includes mark-role presentation, not just hue substitution. Heatmap spec and main PNG are unchanged; no improvement is attributed to it.

## Whole-panel preference

| Case | Preference over actual published candidate | Visible reason and limit |
| --- | --- | --- |
| Replicate bars | Candidate, modest | Graphite open bars/opaque dots are crisp on white; treatment positions already encode identity. The optional gray-filled variant adds broad gray areas without helping this 15-observation task. The sparse broad canvas is unchanged, so no literature-level proportion claim follows. |
| Paired scatter | Candidate, mild/task-specific | Blue/pink are bright and distinguishable in this actual 127-point cloud and legend. Difference from previous blue/coral is modest. Blue/terra also reads clearly; neither is a universal winning palette. |
| Cohort box | Candidate | Violet/mint/salmon summaries have graphite medians/whiskers and adjacent graphite observations. The 4-cohort gray probe preserves this hierarchy. Position/proximity carries raw-lane association; no extra grouping is inferred. |
| Cohort violin | Candidate | White bodies, 0.5 pt graphite contours and filled colored IQR areas distinguish estimated density, quartiles and measurements. At 96 dpi contours stay subordinate to summaries while less washed out than before. Flat trimmed endpoints remain a visual limitation, not a statistical error. |
| Depot heatmap | No clear preference; unchanged | Main current PNG is byte-identical to before. Positive sequential blue, values/seams remain legible; retained behavior is not palette progress. |

The actual whole-panel alternatives are retained in the repository: [neutral open](candidates/neutral-open/output/panel.png), [neutral filled](candidates/neutral-filled/output/panel.png), [scatter blue/pink](candidates/scatter-blue-pink/output/panel.png), and [scatter blue/terra](candidates/scatter-blue-terra/output/panel.png). All four persisted PNG hashes equal the temporary files actually viewed; the JSON retains both viewing-path history and persistent paths.

All candidate/transfer PNGs and PDF previews were inspected. No major new visible overlap, touching-boundary or clipping defect was identified. In distribution probes, raw lanes associate with their preceding category by position. Darker points improve contrast without establishing that all observations can be visually counted in the small preview.

## What the paper images support

**scWAT, PDF p4, Fig. 2g:** blue/pink fitted lines with matching points/legend distinguish two actual conditions. The exact line hues supplied by the parent are adapted here to infection-class raw dots. This changes the source mark role and biological mapping; no fitted line is added. Exact vector hex extraction was not repeated by this reviewer.

**scWAT, PDF p5, Fig. 3j:** open/white bars use dark or ochre edges, small raw points/squares and dark summary lines. This paper panel has two conditions, so it does not establish a universal neutral palette. The current one-outcome bar adopts open outlines and strong raw-point contrast because position identifies treatments. Page 5 was freshly rendered from the local PDF; page identity and visible roles were checked.

**PROGENy, PDF p6, Fig. 4c:** neutral contours coexist with defined inner boxes. Violet/mint identify mutation-status summaries; salmon, yellow and gray also occupy pathway-quartile density areas. Current cohort plots confine sampled area colors to IQR regions and leave KDE bodies white. Moving salmon from a source KDE-area role to IQR area is an adaptation. Source caption/regions were inspected; exact color extraction was not independently repeated.

Paper panels have different data/reading tasks. Only observable relationships between area, contour, summary and observation layers are transferred; no direct performance score against those panels is claimed.

## Findings and verified corrections

1. **CR-01, minor, resolved:** violin-transfer caption initially called filled inner boxes “open.” It now says **“Inner filled boxes”** and retains the descriptive-quartile definition.
2. **CR-02, minor, resolved:** all three hues were initially called “PDF summary fills.” All four main/transfer box/violin captions now say selected **PDF area fills**, explicitly distinguishing inner summaries from colored density/pathway regions and labeling application to cohort IQR as an EasyViz adaptation.

These wording corrections were verified within pass 1. All rendered/spec files remain unchanged; final export hashes were checked again after the correction, so another full visual iteration was unnecessary.

## Export and numeric evidence

After visual preference had been recorded, `validation.json` was read as supplied evidence: 15 runs passed, with source-to-artist/coordinate and summary checks for five structures and bounded transfer probes. **This reviewer did not independently recompute source statistics, raw coordinates, KDE or all 48 matrix cells.** Numeric success does not establish aesthetic quality. Its default-baseline comparison differs from the published-before comparison above.

The reviewer independently measured ten actual PDF/SVG export sets, checked their text resources and computed all thirty PDF/SVG/PNG hashes. All candidate/transfer hashes match validator records. PDF/SVG are approximately **110 × 88 mm**, ArialMT is embedded in every PDF, ordinary PDF text is **8 pt**, and log superscripts **5.6 pt**. SVG text is retained. PNGs are **1299 × 1039 at approximately 300 dpi**; nominal 96 dpi previews are **416 × 333**. Heatmap before/current main PNG SHA-256 is identical. Exact hashes, all 32 viewed-image paths, SVG text styles and PDF font checks are in the companion JSON.

## Remaining limits

- Distribution dots remain about 2 pt across. Graphite increases contrast without establishing individual countability at 96 dpi; do not shrink them further based on this review.
- The broad fixed canvas, lane spacing and flat KDE trims are inherited. Color changes do not resolve all differences from tightly arranged paper subpanels.
- No color-vision simulation, grayscale proof or print test was performed. Bright pink was judged only in this actual two-class cloud; many-category/large-area suitability remains untested.
- These are known-source examples and transfer probes, not a blind new-agent test. No CNS acceptance, novice benefit or model-level causal claim is supported.

**ready_with_notes**
