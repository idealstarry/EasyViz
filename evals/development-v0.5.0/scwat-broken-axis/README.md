# Segmented-axis reproduction evidence

This is a real-data learning case for Huang et al., *Nature Communications*
2023, Fig. 2c. It tests a basic bar chart with a nonstandard coordinate
relationship rather than another standard-template gallery plot. The official
Source Data supplies 60 observations and six P entries; no author plotting
code was inspected or executed.

| Evidence | Result and boundary |
| --- | --- |
| `reference-reading.md` | Fresh narrow reader opened only the crop/caption before implementation. Continuous tall-bar side outlines across the axis gap were directly observed; exact unprinted endpoints, physical size and type remain uncertain. |
| `reference-reading-transcription.json` / `reading-transcription-provenance.json` | Later implementing-Agent schema transcription bound to the original reading. It explicitly reports main-Agent provenance and does not claim another independent reading. The implementer knew other parts of the paper, so this is not a held-out benchmark. |
| `source-check.json` | Independent OpenPyXL extraction checks all 60 original workbook numeric strings and six P entries against the stdlib extractor. Source columns do not establish cross-gene mouse identity. |
| `adoption/` / `adoption-check.json` | Real staged image/data packet with preserved/adapted relationships, all read layers, explicit unknown handling and adopted 92 × 66 mm / Arial 8 pt. Record status is `adoption_complete`; `ready_for_delivery` and `visual_review_passed` remain false because a checkpoint is not image approval. |
| `actual-export-check.json` | Actual SVG and PDF contain all 60 source-derived point coordinates; PDF group colors match; source/artist tables contain all 12 independently calculated mean/SEM summaries. PDF/SVG are 92 × 66 mm, PNG is 1087 × 780 at 300 dpi, Arial is embedded and all visible PDF text is 8 pt. This is not an upstream normalization, P calculation or biological-independence audit. |
| `independent-visual-review.md`, canonical pass 2 | `ready_with_notes`, bound to the exact stable exports. Readable at the 96 dpi fixed-size screen proxy. Remaining minor notes: compact low-point overlap, slightly lighter relative strokes and optional Ucp1 guide positioning. No physical paper proof or journal acceptance is claimed. |
| `user-data-transfer/` | Separate simulated engineering inputs: three changed categories, changed group identities, three observations/group/category, 18 points and six summaries. Actual SVG/PDF coordinates/colors and fixed-size/type checks pass. It uses no additional paper Source Data or author code; it does not establish aesthetic quality on unrelated biological data. |
| Focused tests | 34 tests pass across reference-packet, reproduction-checkpoint and scWAT contracts. They cover immutable staging, partial scientific adoption, required unresolved layers, malformed inputs, hidden raw/SEM endpoints, duplicate source identities, invalid P bounds and missing/duplicate summary rows. |

The initially chosen DejaVu Sans 8/7 pt candidate was revised to the explicitly
requested Arial 8 pt throughout; `pass-01-dejavu` is historical. Its review
overlapped that redraw and is not bound approval of the final files. The final
review separately verifies the canonical version. Public portable runs may
adopt `--font "DejaVu Sans"`; they retain 8 pt and record the override rather
than asserting the original Arial specification generated a different font.

Gallery output is frozen documentation. Current maps, QA, settings and handoff
receipts belong to a fresh local redraw and are excluded from the portable
gallery bundle. Exact reference bounds/font, upstream normalization,
multiplicity and cross-gene sample identities remain unrecovered. These limits
are retained in the case caption and adoption record.
