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

The current user request replaces the rejected multi-hue signed design with one bright blue scale and scientifically interpretable ranges. Use globally linear `Normalize(-400,1000)`, covering every complete-source value. Zero is an explicit tick; it is not a forced white midpoint. Display equally spaced 200-minute ticks in original units.

Both mean tracks use the same numeric limits 0–700 min and ticks 0,350,700, justified by their complete observed mean ranges. Their physical axes differ, so readers should compare numeric tick values. Keep the full-partner denominator, all 5,776 input values, all 400 selected cells, 152 means and rank ordering. Sky-blue means and independent charcoal/outlined-white genome metadata retain their original meanings.

The matrix and keyed metadata remain aligned; guide repositioning and a taller top mean track improve label spacing within 180 × 160 mm. All text remains 8 pt Arial. No data transform, clipping, clustering, classification, significance test or biological inference is added. Explain the source GII definition and its >300-minute inhibition criterion in the separate caption, without interpreting every positive value as classified inhibition.
