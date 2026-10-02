# Manuscript dot plot reproduction

Panel exports are `panel.pdf`, `panel.svg`, and `panel.png`; use the complete 120 × 90 mm canvas in manuscript assembly. PNG is 300 dpi (1417 × 1063 px). `caption.md` contains the separate English caption.

## Reproduce

Use Python 3.11+ with the packages listed in `easyviz/scripts/requirements.txt`, and install Arial on the rendering and SVG assembly system. This run used Python 3.12.2; package versions are recorded in `requirements-used.txt` and `settings.json`.

From this folder:

```sh
python reproduce.py
```

This creates a new `reproduced` folder and does not replace the accepted exports. An optional output directory can be supplied as the first argument. On this machine the verified runtime is `/Users/starry/Desktop/EasyViz/.venv/bin/python`; no network or paid API was needed.

All renderer helpers and the selected palette catalog are included under `easyviz`. The bundle is independent of the original repository at render time. For numerical and export checks, run `python verify.py`. Arial is not redistributed. PDF embeds Arial; SVG retains editable text and references Arial.

## Data and settings

- `prepared.csv`: byte-for-byte copy of the supplied table; all 24 rows retained.
- `plot.json`: adopted create-track specification, explicit input category orders, size maximum 1, maximum area 90 pt², and score limits −0.22 to 1.66.
- `plotting-data.csv`: source fields plus renderer availability states and exact area values.
- `settings.json`: actual font, dimensions, scale, runtime, measured layout, and guide geometry.
- `qa.json`: renderer checks. `checks.json` and `review.md` record independent numerical/export checks and visual findings.
- `provenance.json`: source hashes, resources, choices, and process limitations.

The area formula is `Detected fraction / 1 × 90 pt²` for both plotted dots and size legend keys. A grey tick at each observed zero is a separate nonquantitative state glyph. The selected sequential `notch2-blue` gradient does not assume that score zero is a biological threshold. No rows are aggregated, filtered, imputed, or treated as independent biological replicates; no tests are performed.
