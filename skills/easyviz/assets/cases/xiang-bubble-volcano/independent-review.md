# Independent visual review

Visual and overall status: **ready with notes**. No critical, major or minor visual failure was observed. The separate independent numerical auditor confirmed 17 paper-only checks passed for the exact reviewed PNG/PDF hashes.

## Inspected inputs and independence

Actually opened `reference.png` (429 × 660), `output/panel.png` (1039 × 1417) at original detail, and a 333 × 454 downsampled candidate proxy corresponding to 88 × 120 mm at nominal 96 screen pixels per inch. The proxy is an uncalibrated screen-size aid, not print proof. Read `adopted-spec.md`, `caption.md`, `output/qa.json`, `output/settings.json` and `independent-reading.md`. Also inspected the candidate PDF page and extracted text metadata. No source-data rows, plotting code, author code or other examples were inspected. The prior independent reading was supplied background; this review opened the actual reference again.

The QA and settings files are implementation reports. Their pass labels and numerical counts were not adopted as independent proof. Numerical conclusions below come from the separate /root/workbuddy_audit messages confirming these exact export hashes and 17 paper-only checks; they are distinguished from direct visual observations.

## Exact inspected hashes

| File | SHA-256 |
| --- | --- |
| `reference.png` | `bac15a228d694dd390b857f4ea55a599b046b319fed13d41d717f0439a919655` |
| `output/panel.png` | `e946688e4832ba46539612ee8d2426415611f762132552e0246eb3095f4aeea5` |
| `output/panel.pdf` | `d90897a7b4446c58b76792d3de18d4744ab3be2ba9241bdeecfa55bfef03910b` |
| `adopted-spec.md` | `c833ae565eceafbec8c5ba804a3b537f8e9faf2bdce5324495dfcb178f97186d` |
| `caption.md` | `1c64f246efb339996435a0aa9f74eba352ae2622f36092c2794b4369303fe28a` |
| `output/qa.json` | `7645ea0b7bd2bf7546d203a0cfa6c6bb7ef915eaf98b8f1d9db7377ee6a6718d` |
| `output/settings.json` | `9daed02371ff458bd4a4beb909424bd8bba3c7eeb62fbbd694f15475c98df57c` |
| `independent-reading.md` | `f71121b83b0e1154142302b2a7b1eb9966e60edc1850ca5e6d9436247e7f808c` |

## Reference and adopted requirements

The candidate retains the actual two-sided scatter structure: a tall, broad blue negative side; a shorter red positive arm; a narrow grey central strip; dense low-y overlap; and sparse isolated high blue marks. The adopted x axis makes C3 − C5 explicit. The visible class guide decodes C3 lower, C3 higher and Small effect. Dashed vertical lines bracket x = 0, and the dashed y reference stays visible outside the central cloud.

The categorical guide sits to the right of both vertical references in upper-right white space. The size-guide heading and keys also clear those lines and remain well above the red arm. No text, key, guide header or point collision was seen. The complete guides stay subordinate to the scatter. Approximate manually inspected pixel bounds are plot `[177,43,998,1220]`, categorical guide `[781,48,978,157]`, and size guide `[813,500,972,681]`; the guides together occupy about 5% of the plot. These are approximate image observations, not copied machine-fit measurements.

The filled quantitative marks and size keys show no contrasting outline. Class keys match their clouds. The size guide visibly increases from 0.25 through 0.5 to 1; exact proportional area was checked by the separate independent numerical auditor. In the 333 × 454 proxy, axis text, short class labels and size labels stay readable. The lower cloud is crowded enough that it cannot support visual row counting, but the main shape, direction and sparse outliers remain visible. Its overlap is consistent with retaining all observations and the declared maximum circle area.

The image omits the source E, pathway tables, titles, count summaries and explanatory footnotes as adopted. The caption correctly carries the grey-class caveat, the 37 zero-area statement, size meaning, attribution and supplied-results-only limitations. No extra statistical test or upstream reconstruction is required by this plotting task.

No accepted earlier candidate baseline was supplied or inspected. Refinement preference is **not checked**; this comparison does not claim improvement over an earlier rendering or publication acceptance.

## Findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| note | Dense base of the blue/red clouds and central grey strip | At original PNG resolution and in the 333 × 454 screen proxy, substantial circle overlap remains around adjusted-P coordinates about 2–8. Individual rows cannot be counted there, but the opposed clouds, grey strip, sparse blue outliers and red arm remain distinguishable. | Preserve every supplied row and the declared 18 pt² maximum geometric circle fill area. No aggregation, filtering, jitter or invented positive area. | Retain this geometry. Treat the panel as a distribution-level view; the accompanying data carries individual-row detail. |
| note | Grey class and separate caption | The candidate legend says Small effect. The caption explicitly says all 1,457 supplied rows already have adjusted P below 0.01 and grey means absolute median difference below 0.2. | Do not imply that grey means P-nonsignificance in this filtered dataset. | Deliver caption.md with the panel; preserve this interpretation caveat in the manuscript caption. |
| note | Zero-probability rows | The caption states that 37 zero-probability rows retain zero area and stay in the accompanying data. Invisible zero-area marks cannot be counted or verified from the raster. | Do not invent visible positive size for a quantitative zero. | Keep the caption statement and retain the separate independent numerical audit confirming 37 zero-size written circle paths. |
| note | Final-size readability evidence | The original 1039 × 1417 PNG and a 333 × 454 proxy corresponding to 88 × 120 mm at nominal 96 ppi were actually opened. Axes, short class labels, size labels and dashed references remain readable in the proxy. The screen is uncalibrated. | Evaluate intended proportions without claiming print proof or journal certification. | No visual correction is required by this inspection. Print legibility and journal acceptance are not established. |
| note | Required numerical correspondence checks | qa.json/settings.json were read as implementation reports, not independent proof. The separate independent numerical auditor confirmed 17 paper-only checks passed on the exact saved PNG/PDF hashes. This visual reviewer did not inspect source rows or plotting code. | Source-to-artist preservation and area semantics require separate evidence for the same candidate hashes. No new statistical test is requested. | Retain the independent audit record with the exported panel and this visual review. No correction is requested. |

## Separate numerical and export checks

| Check | Status | Evidence |
| --- | --- | --- |
| Reference and candidate image access | passed | Both reference.png and output/panel.png were opened with original-detail image inspection. |
| PNG dimensions and density metadata | passed | Pillow independently read 1039 × 1417 pixels, RGB, dpi 299.9994 × 299.9994. |
| PDF page dimensions | passed | pypdf independently read one page with MediaBox 249.4488188976 × 340.157480315 pt, equivalent to 87.99999999998666 × 120.00000000001387 mm. |
| PDF text size and named font | passed | pypdf text visitor returned 21 nonempty text runs, all 8.0 pt, all /CNLMZG+ArialMT. No text-size claim is inferred from raster pixels. |
| Source-to-artist rows, coordinates, source classes, 37 zero areas and quantitative circle/legend mapping | passed | Separate independent /root/workbuddy_audit confirmed the exact PNG/PDF hashes, all 1,457 circle paths including 37 zero-size paths, source order, coordinates, class aliases and counts 471/143/843. Maximum coordinate error 6.35e-7 pt and geometric area error 5.85e-6 pt². Size keys equal probability × 18 pt²; written references match x ±0.2 and y = 2. This is external independent evidence, not a calculation by this visual reviewer. |
| PDF font embedding | passed | pypdf independently found /FontFile2 in the /CNLMZG+ArialMT descendant font descriptor; decoded embedded stream length 29,656 bytes. |
| SVG output details | passed | The independent numerical auditor reported editable Arial 8 pt SVG and matching dimensions. SVG was not directly opened by this visual role; exact reviewed PNG/PDF hashes match the audit. |
| New differential-expression tests or biological validity | not_checked | Outside the plotting-only task. The caption states supplied results were not recomputed and upstream filtering universe, independent units and test are not reconstructed. |
| Print proof and journal acceptance | not_checked | Only an uncalibrated screen proxy was inspected. No publication certification is made. |

The external independent check record is `verification.json`, supplied by /root/workbuddy_audit. Its 17 passing checks apply to the paper candidate and official inputs. Engineering transfer validation is outside this visual pass.

The auditor records: A968 and A1306 are already numeric Excel dates in the official gene column. The prepared CSV preserves decoded date strings; original gene names cannot be recovered from this sheet. Plot coordinates, classes and probabilities are unaffected. This is recorded under `official_workbook_to_CSV.evidence.source_identifier_limitation`. Preserve it in the audit/provenance record; this plotting task does not repair the original identifier intent.

Deliver the panel with its caption and independent audit record. No visual layout correction is requested.

Status: **ready_with_notes**. This status is scoped to the supplied candidate and adopted plotting requirements; it is not print proof or journal certification.
