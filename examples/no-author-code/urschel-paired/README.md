# Raw observations, median/IQR, and optional paired connectors

This case uses all 254 measurements from 127 explicitly paired participants in
[Urschel et al., Nature Communications (2024), Figure 2b](https://www.nature.com/articles/s41467-024-47429-8).
The generic `paired_plot.py` recipe supports two or more repeated conditions,
optional mutually exclusive groups, deterministic swarm or jitter placement,
raw-scale median/IQR summaries, and explicitly adopted individual connectors.
No author plotting code or hypothesis-test reconstruction is used.

![Reference-derived raw observations and median/IQR](output/panel.png)

```sh
python plot.py
python plot.py --spec connectors-spec.json --out output-connectors
```

The first command reproduces the reference's point/summary encodings with four
unconnected clouds. The second adds a new within-person view: its connectors are
not present in the reference. Default exports are PDF, SVG, PNG, and TIFF at
105 × 96 mm with 8 pt Arial. On another host, explicitly adopt an installed
font with `--font "DejaVu Sans"`; the resulting settings record the choice.
Keep the runtime's sibling helpers together, and pass
`--runtime /path/to/easyviz/scripts` when using a copied case outside the plugin.

`source-data.csv` preserves every selected source measurement and its original
sheet, row, cell, ID, and raw infection classification. The 64-person prior-
infection group includes 60 `yes` and four `yes/NCAP+` entries; the other group
has 63 participants. Both measurements are positive and complete for every ID.
There is no filtering, imputation, pseudo-count, or inferred pair ordering.

The reference contains a boxed in-image label, panel letter, counts, reported
significance brackets and two dotted horizontal lines. Their removal and the
added cohort legend are recorded in `adopted-spec.md`; the numerical measurement
and uncertainty definitions are retained in `caption.md`. Quartiles use a
transparent Weibull rule, which is not claimed as the author's unstated rule.

See `output/qa.json` for source-to-artist, pairing, summary, circle-geometry,
canvas and guide checks, and `output/summary-data.csv` for exact descriptive
values. `first-render/` preserves the initial author rendering. A fresh
independent reference reading was completed before any implementation template
was selected; its source evidence is in
`evals/reproduce-inputs/urschel-paired/` in the development checkout.

The source article, selected Source Data and cropped reference are attributed
to Urschel and colleagues under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
This is a data subset and adapted plot. It demonstrates source integrity and
the new plot family; it does not establish journal acceptance or model-wide
aesthetic improvement.

[Independent visual review](independent-review.md) records the inspected final images, candidate hashes, export checks and remaining adaptation notes.
