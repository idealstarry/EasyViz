# Example user request

Create a manuscript-ready overview from the supplied inhibition matrix and genome-status table. There is no reference image. Preserve the complete input data and display a manageable 20 × 20 selection spanning the range of sender and receiver average responses. Make the structure easy to read: show pairwise growth inhibition indices, aligned mean-response tracks calculated across all available partners, and genome-analysis status for both axes.

Use one integrated heatmap panel, an inferno scale, 8 pt Arial labels, and a fixed 180 × 160 mm canvas. Export editable SVG, PDF, and a 300 dpi PNG. Include the exact selected measurements, the full-data summary calculations, settings, and validation record.

## Acceptance criteria

| Area | Requirement |
| --- | --- |
| Data | Retain all 5,776 source measurements unchanged; negative values remain negative. |
| Selection | Select 20 evenly spaced mean ranks separately on each axis. Save every selected ID and rank. |
| Summary | Each sender/receiver mean uses all 76 opposite-axis strains, including self-pairs present in the supplied matrix. |
| Visual encoding | Heatmap color represents GII in minutes; aligned bars represent full-matrix means; binary strips represent supplied genome status. |
| Scientific scope | Descriptive selection and averaging only. No significance or biological mechanism is inferred. |
| Layout | One integrated panel; readable final-size labels; no overlapping labels or clipping; no tight crop. |
| Reproducibility | Script uses only its local data and settings. No reference figure or author plotting code is an input. |

## Adopted design refinement

The original request used inferno; an earlier accepted example used a single linear coral ramp. The current user-requested refinement adopts a crisp blue–white–gold–orange–coral diverging scale with zero as the neutral growth-delay reference. `TwoSlopeNorm` preserves the −400 and 1,000 min limits but changes their normalized proportions explicitly: −400 → 0, 0 → 0.5, 1,000 → 1. Forward and inverse formulas, raw-minute colorbar ticks, and no-clipping checks are recorded. Marginals use clear opaque sky blue; genome status uses charcoal and outlined white. Supporting grids and matrix seams are removed.

All 5,776 source values, 400 selected cells, 152 full-matrix means, rank ordering, 180 × 160 mm canvas, and 8 pt Arial remain unchanged. The only geometry adjustment expands/repositions the bottom-right colorbar for its zero and intermediate positive ticks. No significance, clustering, biological threshold, or transformed measurement table is introduced.

The adopted continuous color stops make moderate positive values gold and stronger values orange/coral. They retain the same piecewise normalization and raw-minute readout; their ordered branch luminance is checked. This replaces the first blue–white–red candidate, which remained overwhelmingly pale pink for this data.
