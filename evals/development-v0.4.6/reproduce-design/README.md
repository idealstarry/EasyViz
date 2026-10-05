# Reproduce geometry and typography revision

Two actual reference-informed revisions are ready for 0.4.6 integration:

| Case | Original / prior problem | Revised adopted design | Actual evidence |
| --- | --- | --- | --- |
| Vabistsevits Figure 3a,b | Original paired slim lanes and shared outcome key became two wide repeated-label standalone plots. | 100 × 132 mm, two 32 × 92 mm lanes, shared eight-outcome key, three vertical exposure labels, editable Arial 8 pt. | All 48 estimates and 96 asymmetric CI endpoints checked directly against exported PDF vectors; 16 filled and 32 hollow states retained. |
| Massier Figure 1e selected depot kBET radar | Data circle enlarged to 50 mm while nearly original-sized type and points stayed small. | 64 × 66 mm, 34 mm circle, 5.1 pt geometric points, 0.85 pt traces, editable Arial 8 pt; depot title moves to caption. | All 25 supplied vertices and five closed traces checked directly against exported PDF vectors. Three true zeros remain coincident. |

The source circle/point ratio, forest axis aspect and measured text evidence are in [reference-geometry.md](reference-geometry.md). Shi Figure 1d is retained as a measured control; no change is claimed there. Forest source glyphs are outlined, so exact source font point sizes remain unknown. New sizes/fonts were explicitly adopted before rendering; no source values, uncertainty definitions or numerical scales were changed.

[Independent visual review](independent-visual-review.md) opened original reference images, actual article PDF crops, all old/new PNGs and nominal 96 dpi PDF previews. Both revisions are **ready_with_notes**. The preference is scoped to paired forest reading and radar mark-to-circle relationships. It is not evidence of publication acceptance, calibrated printing or general model efficacy. Pale source hues, the forest's adapted lighter frame, unknown outlined type and radar central overlap remain disclosed.

[Physical-scale comparison](physical-scale-comparison.pdf) places every original crop, baseline and revised PDF at its actual recorded dimensions; panels are not normalized to the same thumbnail size. Original crops are attributed CC BY 4.0 excerpts. The exact placements are in [physical-scale-placement.json](physical-scale-placement.json).

The immutable [baseline index](baseline-index.json) covers 54 original asset/check snapshots. All current revision work is isolated under `examples/no-author-code/{vabistsevits-forest,massier-integration-radar}/revision-v0.4.6/`; original top-level plotters and accepted records remain untouched. These revisions were excluded from the 0.4.4 and 0.4.5 package whitelists.

Verification:

- [Actual export audit](export-verification.json): independent reader does not import either plotter or trust its QA flags. It checks real PDF geometry/fonts/sizes, original numeric spellings, SVG element identities and unchanged baseline snapshots.
- [Portable case probes](case-probes.json): 22 real probes, including copied CLI redraws outside the repository, explicit DejaVu Sans adoption with independent PDF/SVG/source checks, missing/duplicate/malformed source identities, out-of-scale values, unknown sample-size semantics, actual timestamp/size-valid stale code caches and actual data/spec/helper changes after capture. These last changes refuse before any export.
- [Production handoff verification](production-handoff-verification.json): source-bound map and consumed-byte handoff are both valid and current for 143 forest / 37 radar mapped elements. Default Arial PNG bytes equal the separately reviewed pre-handoff images. PDF creation metadata and SVG definition IDs can change across repetitions; actual geometry and text are checked rather than claiming those whole files are byte-identical.
- Both plotters use the public `figure_handoff.capture_inputs` before any export, parse those actual captured bytes, compile declared helper bytes, and call `write_receipt` after valid exports. Original and adopted override specifications are separate. No post-export source restamping is used.

The candidate inventory in [portable-revision-files.json](portable-revision-files.json) includes local verification records. Final release curation is narrower: each nested revision ships only README, plotting code, adopted specification, caption and the three frozen PDF/SVG/PNG previews, alongside its parent's inputs. Fresh redraws generate local maps and receipts. Evaluation PDFs, local source papers, baselines, pre-handoff records and archived attempts stay outside the plugin. Package smoke commands are in [package-smoke.md](package-smoke.md).
