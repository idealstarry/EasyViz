# Generalization findings and repaired defects

The initial evaluation covered 15 synthetic scenarios in 19 concrete runs. It produced six valid transfers, nine clear data rejections, one layout rejection, one explicitly unsupported method, and two genuine failures. Additional inspection reproduced an invalid logarithmic-bound defect and identified a misleading zero p-value annotation.

After targeted corrections and two added regression variants, the final evaluation contains **21 runs**: **8 valid transfers**, **10 clear data rejections**, **2 clear layout rejections**, and **1 explicitly unsupported method**. Those are different outcomes, not 21 successful figures.

| Defect | Before | Correction and evidence |
| --- | --- | --- |
| Internal tick collisions | The renderer returned `pass` while 29 same-axis tick-label boxes overlapped. | Horizontal/vertical tick-label collisions now produce `needs_revision` and `valid_outputs: false`. A larger/rotated placement of the same input passes at 8 pt. |
| Literal category names | pandas interpreted `NA` and `null` as missing data, rejecting valid categorical input. | CSV loading preserves literal strings; empty fields and nonfinite numeric values are still rejected. The three-category fixture now retains all 12 rows. |
| Zero log-axis bound | A request for a log axis with limits `[0, 100]` returned `pass`, collapsed the point cloud, and piled up ticks. | Explicit logarithmic bounds must now be strictly positive. The new edge-case run rejects the request. |
| Library p-value equal to zero | The dense correlation panel displayed `p = 0`. | Raw library output remains in `stats.json`; display-bound metadata explains possible numerical underflow/limiting correlation. The panel displays the conservative bound `p < 0.001`. |

The original 14 renderer tests still pass, and five new behavioral tests cover literal labels vs genuine blanks, crowded vs repaired text at unchanged font size, oblique-label handling, nonpositive log bounds, and zero-library-p-value formatting. All **19** renderer tests pass.

## Evidence locations

| Artifact | Meaning |
| --- | --- |
| `baseline-report.json`, `baseline-report.md` | Untouched initial results and renderer hash |
| `baseline-contact-sheet.png` | Initial render overview, including the undetected collision |
| `baseline-log-bound/` | Old QA pass, actual invalid scale settings, and visibly collapsed scatter |
| `report.json`, `report.md` | Final outcomes, exact commands, input/renderer identity and numeric checks |
| `inputs/` | Every newly generated synthetic data table and specification |
| `renders/` | All outputs, including deliberately invalid layout examples retained for diagnosis |
| `contact-sheet.png`, `visual-review.md` | Final visual inspection evidence |

## Limits that remain

- The supplied schemas and five chart families are the tested boundary. A three-visit Friedman test is correctly reported as unsupported; clear rejection is not implementation of that method.
- Missing dot combinations and supplied zero-size dots look the same. A custom symbol or layer is required when their distinction matters.
- Overlap detection covers visible same-axis tick labels at horizontal/vertical orientations. Oblique ticks are listed as unchecked instead of being rejected from misleading axis-aligned boxes. Legend/annotation/mark collisions still require visual inspection.
- Repair is explicit: the evaluation modifies dimensions, margins, or label orientation while keeping 8 pt text. It does not establish autonomous layout repair for arbitrary data.
- Synthetic transfer exercises renderer behavior; it does not validate scientific models, the representativeness of biological data, or reference-image reproduction without code.

## Run again

```sh
.venv/bin/python tests/check_generalization.py --strict
.venv/bin/python -m unittest discover -s tests -p test_renderer.py -v
```

The suite's strict flag fails on an unexpected acceptance/rejection, a numerical inconsistency, an unhandled exception, or an independently observed unflagged tick collision. Expected data/layout refusals and declared unsupported functionality remain separately labeled.
