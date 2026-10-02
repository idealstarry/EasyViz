# Independent anonymous visual review

Preferences were frozen while A/B identities remained unknown: **interval B; scatter B (small preference); dot B**.

Only the six anonymous PNGs and six anonymous PDFs under `blind/{interval,scatter,dot}/{A,B}/` were inspected, plus the figure-review and PDF skills. No identities, author code, source tables, QA, history, or prior reviews were inspected. Same-program metadata was not used to infer identity or phase.

All original PNGs are **1654 × 1181 px**. All PDFs have **one page at 396.85 × 283.465 pt**, approximately **140 × 100 mm**. Original PNGs were resampled and PDFs independently rendered to equal nominal **96 dpi** screen proxies of **530 × 378 px**. PNG and PDF agreed on the material layout and all three preferences. This is a screen comparison, not a physical print proof.

| Case | Preference | Visible basis | Hard visual blockers |
| --- | --- | --- | --- |
| Interval | B | Its much wider horizontal data region makes endpoints and their relation to the dashed reference at 1 easier to read. Seven row labels remain distinct; bottom color and hollow/filled keys remain separate and fully visible. A compresses the intervals beside a broad guide reservation and blank right-hand area. | None observed |
| Scatter | B, small preference | Both have materially the same axes and marks. B lists size samples 5, 10, 20 in a direct vertical sequence. A wraps 5 and 20 onto one row with 10 below. B's slightly taller key remains in unused right-hand space. | None observed |
| Dot | B | Its wider matrix gives the three columns more separation while the three row labels stay clear. Continuous color remains beside the matrix; area and special-state keys remain below, separately decodable. A is tall and narrow beside a broad guide reservation. | None observed |

## Concrete findings

| Severity | Location | Evidence | Requirement | Action |
| --- | --- | --- | --- | --- |
| Minor | Interval A: data region and upper-right guides | Near-reference endpoints occupy a short horizontal span; guides and blank right-hand space dominate the horizontal allocation. | Preserve endpoint reading and data priority. | Use B's wider data region for this case, retaining fixed fonts and quantitative mappings. |
| Note | Interval B: bottom guides | Bottom guides reduce row spacing, but all labels and visible marks remain separated. | Preserve label lookup and independent color / fill decoding. | Retain the distinct keys; no further correction follows from this comparison. |
| Minor | Scatter A: observed-cells key | First row reads 5 and 20; second row reads 10. | Make size decoding quick without changing area mapping. | Use B's ordered 5, 10, 20 arrangement with true-size samples. |
| Note | Scatter: smallest orange point in both | It is discernible as a tiny speck at this proxy size. | Preserve visibility in the intended output medium. | Verify the required proof medium if that smallest mark must draw attention; this is a shared limitation. |
| Minor | Dot A: matrix and right-side guides | Rows are much more separated than columns, beside a large guide reservation. | Balance categorical lookup and guide visibility. | Use B's wider matrix and guide placement for this case while holding fonts and mappings fixed. |
| Note | Dot: special states in both | Small gray symbols require attention, particularly the short vertical line for small positive. Their labeled keys remain visible. | Decode special states independently of area and continuous color. | Keep the separate state key and verify the symbols in the intended proof medium. |

The interval preference is conditional on endpoint reading and comparison to 1 being central. The scatter preference is modest and reflects guide sequence, because the plotted region is materially the same. The dot preference follows the supplied need to keep the matrix primary while decoding color, area, and special states independently.

Exact fonts, font embedding, numeric and statistical correctness, and authored geometry were **not checked**. Separate author/QA records must verify those claims. No journal readiness or acceptance is asserted.

Scoped visual status: **ready with notes**. These are findings about the supplied actual outputs at fixed fonts and canvas, not model runs or evidence of model performance.
