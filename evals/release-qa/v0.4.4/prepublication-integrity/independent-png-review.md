# Independent review: PNG scanline integrity

**Decision:** no blocking defect found for the stated PNG scanline/payload/physical-geometry scope. This approves the reviewed PNG helper change, not the full release or aesthetic quality. No authoritative source or original repro evidence was edited by this reviewer.

## Exact reviewed inputs

- `skills/easyviz/scripts/create_review.py`: `f2db9f778830f164a8fd56dcdf7407cddb81e68ba1f6cc7343aca6c8d6cecc33`.
- `tests/test_create_review.py`: `8b8277c0fb00dd811a299aa1592033cab3d52c374f7096eb545b145dff722fe4`.
- **28 focused tests passed**. The earlier task description named 26 tests; the source-continuity owner added two tests while this audit was in progress. The final observed 28-test run and exact hashes are retained in [probes.json](probes.json).
- Independent runtime probes: **150 legal byte streams** spanning all supported PNG color types and bit depths, ordinary/Adam7 interlace, and `1 × 1`, `1 × 7`, `7 × 1`, `5 × 9`, `9 × 5` dimensions. Each was actually decoded with Pillow; every helper dimension matched the decoded image.
- Legacy custom-output compatibility: the full `repair-outcomes/panels/hdr/output` snapshot exactly matches the prior HEAD helper's result, including passed source provenance. A custom output without `source_snapshot` does not acquire a null `captured_source` field. This verifies the additive compatibility fix without rewriting an original successful record.

Whole-file hashes bind this observation. Later source-binding edits require their separate audit; they do not automatically inherit approval. The evidence also records the isolated `png_measurement` function hash.

## Code/specification review

Inspected the actual patch and [W3C PNG Third Edition](https://www.w3.org/TR/png-3/), especially IHDR, PLTE, IDAT, IEND, Adam7 pass extraction and pHYs. The new helper:

- requires one initial, correctly sized IHDR and positive dimensions; accepts only legal color/depth combinations and known encoding methods;
- verifies chunk type plausibility and CRC, rejects unsupported critical chunks and misplaced/duplicate palette or physical metadata, and requires consecutive IDAT chunks;
- requires image data, computes exact filtered row byte counts for each nonempty Adam7 pass, and limits decoded data to 256 MiB before decompression;
- checks a complete first zlib stream, exact expected scanline bytes and valid filter numbers 0–4, followed by a complete IEND and no bytes after it;
- accepts empty consecutive IDAT chunks and unused bytes following the zlib stream in the final IDAT, as required for compatible decoding.

The meaningful focused tests reject header-only PNGs, malformed/truncated zlib streams, missing/extra scanlines, invalid filter bytes, malformed encoding/palette and excessive decoded size. Real mode/bit-depth outputs and actual Adam7 decoding support compatibility. The existing floor/nearest raster geometry and exact vector-canvas tests also passed in the focused run.

## Scope limit

This is **scanline integrity**, not exhaustive PNG conformance or visual content verification. It does not reconstruct filtered colors or validate each resulting palette index. A 1 × 1 indexed fixture with an index beyond its one-entry palette passes these structural checks; PNG 3 treats this as a recoverable color error, and decoder behavior can differ. The probe records that fixture and Pillow's actual recovered color. This does not undermine the repaired absent/corrupt-scanline gate, but documentation must not claim complete PNG validity or verified scientific colors.

The prior raster quantization compatibility band remains unchanged. Dimensions alone do not distinguish every one-pixel content crop near an integer grid; exact vector geometry and actual-image review retain their separate roles.

## Re-run

```sh
.venv/bin/python evals/release-qa/v0.4.4/prepublication-integrity/probe_png.py
```

The probe uses the current checkout, writes only its own `probes.json`, records source/test/script hashes and focused test output, and fails if the helper changes during execution. Original repros remain immutable.
