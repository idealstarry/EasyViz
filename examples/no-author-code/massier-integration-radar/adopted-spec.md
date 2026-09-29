# Adopted radar specification

This is an `image-data` reproduction of the depot kBET chart, using the supplied independent reference reading and the 25 released acceptance rates. The implementation is newly written. No author code, earlier plotting implementation, original source workbook, original article PDF, or external source was accessed. Input isolation is instruction based, not an operating-system sandbox.

## Evidence and decisions

| Requirement | Evidence | Adopted decision | Priority |
|---|---|---|---|
| One five-spoke radar chart | Reference image and independent reading | Equal angles with all at the top, then FAPs, vascular, immune, adipocytes clockwise | Required |
| All five methods and all 25 values | Request and source table | Preserve every value, including three numerical zeros; no filtering, averaging, or jitter | Required |
| Radius means kBET acceptance rate | Request and dictionary | Linear radius, dimensionless; outer tick 0.5 includes the maximum supplied value, 0.47525 | Required |
| Radial origin | Exact offset is unknown from the reference | Set origin to exactly 0. This explicit scientific scale produces central overlap for zero values; do not reverse-engineer a negative display origin | Required |
| Numeric radial ticks | Reference | Show 0, 0.25, and 0.5 at the left of the upper vertical spoke | Required |
| Method colors and marks | Visible image plus estimated reference palette | Gray raw, gold Harmony, green scVI, dark blue BBKNN, purple rPCA; straight closed line segments and filled round markers; no polygon fills | Preferred |
| Grids and background | Visible image | Pale circular background, thin spokes, dashed teal 0.25 ring and pale gray 0.5 ring, all beneath data | Preferred |
| Standalone identification | Request | Direct labels on all spokes; method key at bottom; depot heading and kBET acceptance-rate caption | Required |
| Final dimensions and typography | Request | Full 88 × 88 mm canvas; Arial, 8 pt throughout; PDF, SVG, and 300 dpi PNG; no tight cropping | Required |

The source unit is one previously computed method–cell-class acceptance rate. The data are not biological replicates. There is no uncertainty or inferential layer, and no kBET or integration computation is repeated. The defined measure domain is [0, 1]; the displayed radial interval [0, 0.5] contains all supplied observations.

`settings.json` is the authoritative record of dimensions, geometry, palette, font, ordering, and exports. The script reads it. `plotting-data.csv` retains the source rows and values, adds publication labels and the explicit angles and drawing positions, and introduces no scientific transformation. `stats.json` records descriptive integrity checks only.

## Intentional differences and limits

The original image contains six charts with shared legends. The delivered chart stands alone, uses direct spoke labels and a compact two-row method key, and omits the frame shared with the depot ARI chart. All typography is fixed at the requested 8 pt. Marker sizes and margins are adapted to this larger standalone chart.

The exact radial origin, author font metrics, method overlap order, and exact colors are not recoverable. The explicit zero origin is a documented adaptation. True coincidences and near-zero measurements remain overlaid; all 25 vertices and five closed traces are drawn. This is a scientific reproduction of the adopted mapping and style, not a claim of pixel-exact reconstruction.

The supplied `reference-spec.json` is the independent reading. The implementer directly inspected the image, performs a self-review, and supplies the candidate for a separate independent review. `qa.json` separates measured export checks from that self-review; `access-log.json` records access and isolation limits.

## Rerun

Run `python plot.py` from any working directory in an environment with Matplotlib, NumPy, pandas, Pillow, and PyMuPDF. The script locates its own settings and input copy. In this repository, `.venv/bin/python examples/no-author-code/massier-integration-radar/plot.py` is the recorded invocation. All five original permitted inputs are copied under `inputs/` so that the candidate is portable. Arial is used when available; a recorded DejaVu Sans fallback supports reruns on other systems.

Attribution supplied with the inputs: Massier et al., Nature Communications 14, 1438 (2023), DOI 10.1038/s41467-023-36983-2, CC BY 4.0. Attribution was not independently browsed.
