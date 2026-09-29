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
