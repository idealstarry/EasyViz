# Create · repair outcomes as individual manuscript panels

The reading task is to compare treatments within each author-supplied repair
outcome. Three **60 × 62 mm** panels use slender outline bars, the same data
rectangle and treatment order, and **Arial 8 pt**. Each is an independently
exported PDF, SVG and PNG. The row below is a preview at the original panel sizes.

![Three individual outcome panels shown side by side](output/panel.png)

| Individual panel | Original-percent range | Source observations |
| --- | --- | --- |
| [HDR](panels/hdr/output/panel.svg) | 0–15% | 15 |
| [HDR and mutEJ](panels/both/output/panel.svg) | 0–6% | 15 |
| [mutEJ](panels/mutej/output/panel.svg) | 0–55% | 15 |

## Decisions and scientific meaning

Open bars show arithmetic means, dark dots retain all three biological repeats
per treatment, and intervals show sample SD. The ranges differ explicitly,
so readers compare treatments **within** each outcome; equal heights in two
panels do not represent equal absolute amounts. No outcome is normalized,
stacked or transformed to manufacture a composition.

The short treatment labels fit a narrow manuscript panel without shrinking
text. DMSO is the vehicle; NU = NU-7441 (1 µM), KU = KU-0060548 (0.25 µM),
L755 = L755507 (5 µM), and SCR7 = SCR7 pyrazine (1 µM). Exact source names,
concentrations, decimal value strings and workbook-cell identities stay in
[source-data.csv](source-data.csv) and each panel's plotting table. The
[caption](caption.md) carries this definition and the scientific limits.

The 45 real values are from Truong et al., Nature Methods, DOI
10.1038/s41592-023-02162-w (CC BY 4.0). The selected rows contain all five drug
conditions, three outcomes and three biological replicates. The
‘No donor/Cas9’ and ‘NTC’ controls are explicitly excluded from this declared
drug-comparison subset. This descriptive plot introduces no hypothesis test,
cross-condition pairing or new biological conclusion.

An optional [grouped alternative](grouped-output/panel.png) answers a different
reading task: compare absolute outcome magnitudes on one global 0–55% scale.
It has explicit within-treatment gaps, verified against actual outline stroke
edges. The individual view remains the main presentation when outcome ranges
would compress smaller responses into short bars. Both layouts are retained;
neither complexity nor more values establishes publication quality by itself.

## Run and adapt

```sh
python /path/to/repair-outcomes/plot.py --out /writable/figure
python /path/to/repair-outcomes/plot.py --transfer --out /writable/probes
python /path/to/repair-outcomes/validate.py --outputs /writable/probes --out /writable/validation.json
```

Supply `--tools /path/to/easyviz/scripts` when copying the case outside the
plugin. `--font "DejaVu Sans"` explicitly chooses an available alternative;
use the same override when validating exports. Copy the case into a writable
project before editing its specifications.

`plot.py` delegates all data drawing to the public `replicate_plot.py`.
`compose.py` joins the already exported vector panels without resizing fonts
or redrawing data; original individual panels remain the manuscript files.
The bounded [transfer](transfer/panel-manifest.json) reverses source rows and
uses four treatments and two outcomes: two narrow panels retain all 24 real
values. It checks the repeated layout and source identity, rather than a new
biological population.

[Provenance](provenance.json) records selection and limits.
[Validation](validation.json) checks every raw value, outcome-specific mean/SD,
source-to-artist coordinates, actual dimensions and fonts. It also checks
unchanged text positions in the assembled PDF and unique SVG identifiers.
Independent image review is recorded separately in the refinement report;
numerical checks do not rank aesthetics or measure model-wide improvement.
