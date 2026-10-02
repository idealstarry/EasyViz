# Urschel Figure 2b source audit

Urschel, R., Bronder, S., Klemis, V. et al. *SARS-CoV-2-specific cellular and humoral immunity after bivalent BA.4/5 COVID-19-vaccination in previously infected and non-infected individuals*. Nature Communications 15, 3077 (2024). [Article and data availability](https://www.nature.com/articles/s41467-024-47429-8), DOI [10.1038/s41467-024-47429-8](https://doi.org/10.1038/s41467-024-47429-8).

## Selected source and trace

The official [Source Data workbook](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-024-47429-8/MediaObjects/41467_2024_47429_MOESM4_ESM.xlsx) is 727,299 bytes, SHA-256 `d902e7608caa56172bac12515bb0e0b79efb075b669424b8b63858ad21d371be`. The downloaded archival copy stays outside the repository at `/private/tmp/easyviz_nature_b/41467_2024_47429_MOESM4_ESM.xlsx`. No author plotting code was read or used.

Select sheet `figure 2`, rows 4–130, columns A (stable public participant ID), B (prior-infection classification), C (Spike IgG before), and D (Spike IgG after). Header labels are at row 3. Each source row provides one complete before/after pair. The long-form derivative has 254 measurements from 127 participants; values are preserved as numeric XML text, avoiding float serialization changes. Each output row records the original sheet, row, and measurement cell. The selected values and classifications also agree exactly with the master sheet `Urschel et al NatCom all data`, columns AE/AF/B, matched by participant ID.

The raw classification has 60 `yes`, four `yes/NCAP+`, and 63 `no` entries. Both positive classifications form the 64-person prior-infection group. This follows the article's grouping by infection history and/or positive nucleocapsid serology. The four `yes/NCAP+` IDs are 031, 091, 102, and 116 in the `NatCom_2024_` ID namespace. They are retained, with the raw classification recorded alongside the display group. Dropping or treating them as a third group would contradict Figure 2b sample sizes.

## Measurement and pairing

Values are spike-specific IgG in BAU/ml (binding antibody units per millilitre), not relative change. Before/after measurements share the participant ID; different participants are independent biological units as stated by the caption. Source Data contain one measurement per participant per time point. The article scheduled the after sample 13–18 days after vaccination; a single nominal time label should not imply every observation was collected on exactly day 14.

All 254 selected measurements are finite and strictly positive. No values are missing or censored in the selected IgG columns. No observations are filtered, no zeros are substituted, and no pseudocount is required for log display. Ranges are 91.76–4675.06 before and 2481.75–21898.09 after for prior infection, and 60.42–4373.12 before and 941.40–33036.34 after for no prior infection.

## Summaries and statistical limits

The source caption identifies medians and interquartile ranges (IQR); these bars must not be labelled SD, SEM, or confidence intervals. Calculate summaries from the original BAU/ml values before transforming only the display axis. The source does not state its quartile estimator. A transparent adopted `weibull` estimator (Hyndman–Fan type 6, NumPy `quantile(method="weibull")`) gives:

| Group | Time | n | Q1 | Median | Q3 | IQR width |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Prior infection | Before | 64 | 800.86 | 1713.845 | 2722.015 | 1921.155 |
| Prior infection | After | 64 | 5428.0775 | 7544.21 | 10994.3475 | 5566.27 |
| No prior infection | Before | 63 | 177.65 | 465.20 | 993.62 | 815.97 |
| No prior infection | After | 63 | 2944.47 | 5045.45 | 7694.53 | 4750.06 |

The first three IQR widths round to the article's reported 1921, 5566, and 816. The last rounds to 4750, whereas the article reports 4751; the difference is about 0.94 BAU/ml. This resemblance does not prove the author's estimator. A reproduction should identify the adopted rule and preserve this small unresolved reporting difference rather than claim exact published quartiles.

The source reports paired t tests for within-person before/after comparisons and Mann–Whitney tests between groups, both two-sided. Neither caption nor methods settles whether paired tests used transformed measurements. The plot implementation should perform no test automatically; reported significance labels, if adopted, must be explicitly supplied and attributed, never inferred from a visible bracket.

## Reference, changes, and reuse

The official article PDF is 4,056,558 bytes, SHA-256 `55df0455ba52ada218f3b0b1302a570fa889c1b07effec8a30a2f113cef703bd`, obtained from [the article PDF](https://www.nature.com/articles/s41467-024-47429-8.pdf). Figure 2b is on PDF page 4 (zero-based page 3), cropped at `[268, 44, 426, 194]` PDF points and rendered at 240 dpi. Crop SHA-256 is `e519b4653620c546dccba9734f0ac821872c0ad7402d31558a0a7dba8b094abb`.

The article is distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), and no separate contrary credit was found for this selected figure or Source Data. This folder redistributes a traced data subset and a cropped reference with attribution; both are derivatives. Proposed manuscript defaults omit the panel letter, boxed in-image label, sample-count prose, and significance narrative in favour of a separate caption. The observed point/summary plot is unconnected. Adding individual before/after connectors is an explicit new view of the paired data, not an exact feature of the published reference. The full measurement methods report assay categories at 25.6 and 35.2 BAU/ml; these are plausible meanings for the two low-concentration dotted guides, although their identification is not explicit in the supplied figure caption. The adopted standalone axis starts at 40 BAU/ml, above both thresholds and below every selected measurement, and omits those guides as a documented display adaptation.

Re-run extraction after downloading the official XLSX:

```sh
python extract_source_data.py --source /path/to/41467_2024_47429_MOESM4_ESM.xlsx
```

`source-checks.json` records the audited workbook and derivative identities, sample counts, complete-pair count, classification mapping, and master-sheet cross-check.
