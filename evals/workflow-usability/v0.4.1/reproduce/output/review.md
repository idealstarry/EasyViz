# Actual review

Status: **ready_with_notes** for this supplied target dataset. Main-agent self-review; independent review was not performed because the task contract prohibits other agents. The reference image and actual attempt-02 PNG were opened and visually inspected. No aesthetic-superiority or arbitrary-data claim is made.

| Severity | Location | Actual evidence | Action/status |
| --- | --- | --- | --- |
| major, resolved | Lower color scale | Attempt-01 canvas check found the Standardized score label 0.0194 mm below the canvas. No export was delivered from that failed attempt. | Raised scale by 0.5 mm; unchanged 120 × 90 mm canvas and Arial 8 pt. Attempt-01 source, settings, data and failure record retained. |
| note | Main matrix and strip | Actual PNG shows a contiguous 8 × 9 matrix, three top condition blocks, and labels in target order. | Accepted; all 72 coordinates retained and nine strip cells aligned to matrix column edges. |
| note | Missing/zero encoding | Signal_B/S05, Signal_G/S01 and Signal_H/S09 appear gray. Measured zero Signal_E/S07 is neutral rather than gray. | Accepted; source/state/color audit and actual PNG agree. |
| note | Right mean track | Gray bars align to all eight matrix rows; negative and positive means share the zero line. Signal_B has a measured mean of −0.002, so its bar is nearly invisible. | Preserve true width; no visual amplification or imputation. |
| note | Guides and labels | Compact three-item condition guide, horizontal diverging scale and gray Unmeasured key are present; no title or narrative text is inside the image. Labels and guide text are readable and uncropped. | Accepted after actual image inspection and measured text bounds. |
| note | Reference fidelity | Relative geometry, layer order and guide roles match the adopted reference reading. Target values, exact names and missing coordinates differ intentionally. | Record intentional changes; no pixel-match claim. |

Numerical/export checks passed: independent source reread compared all coordinates, states, cell colors and mean widths; denominators are 8 for Signal_B/G/H and 9 otherwise. Strip/row alignment was checked in display coordinates. The exported SVG contains 72 heatmap cell groups, 9 strip groups, 8 mean bars and 29 editable text nodes. SVG/PDF canvas measurements are 120 × 90 mm; PDF contains embedded Arial fonts. PNG is 1417 × 1063 pixels with 299.9994 dpi metadata (integer raster rounding of 120 × 90 mm at 300 dpi). All visible text was checked at Arial 8 pt; no clipping or missing glyphs was found. Guide complete bounds and reserved regions are recorded in `figure-settings.json`/`checks.json`.

There was one technical layout correction and one actual rendered-image review pass. Both attempts are preserved. No further correction was justified by the inspected panel. Caption is separate in `caption.md`. Reference typography, exact original colors and original summary denominator remain unknown from the raster; target semantics and requested physical settings establish the implementation. Scientific content is synthetic; no biological claim or inferential test is made.
