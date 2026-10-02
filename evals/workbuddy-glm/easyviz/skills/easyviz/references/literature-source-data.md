# Learn from literature Source Data

A published panel is useful evidence for a particular visual relationship, not a universal style preset or a guarantee of publication quality. Prefer a small, diverse collection of auditable panels over many unverified screenshots.

## Select and prepare

1. Locate the primary article, exact figure/panel and official Source Data link. Record DOI, workbook/archive name, sheet, header and selected row/column ranges, retrieval date and SHA-256. Keep large raw downloads outside the installed skill.
2. Establish reuse terms and attribution before distributing data or reference crops. Article accessibility alone does not establish permission to redistribute every third-party image. Record crops and transformations as adaptations.
3. Extract a compact CSV with source-row identifiers. Preserve supplied values, asymmetric interval endpoints, classes and measurement states. Explain any display aliases. Do not infer denominators, independent n, error-bar definitions, filtering universe or test design from appearance.
4. Give an independent reader only the selected image and permitted caption/method facts. Adopt explicit requirements before choosing implementation support. Record unfamiliar physical dimensions, colors and fonts as estimates rather than recovered facts.
5. Use a reusable script with explicit field mappings, scales, ordering and reference positions. Draw supplied results directly. A label such as `Not_sig` can be misleading after upstream filtering: verify the source meaning rather than inheriting its name.
6. Audit source rows against actual plotted coordinates, interval endpoints and area encodings, then inspect exported images at final physical size. Technical fit, numerical correctness and visual preference are separate checks.
7. Test another input with different columns, category count/order, sparsity or scale. A second panel from the same study checks reuse within that study; it does not establish transfer to unrelated studies or models. Preserve failures and unresolved differences.

## Curated additions

| Source and selected scope | Reusable relationship | Scientific boundary |
| --- | --- | --- |
| [Xiang et al., Nature Communications 2024, Fig. 3E](https://www.nature.com/articles/s41467-024-46480-9/figures/3), scatter subcomponent | Continuous x/y plus quantitative circle area, supplied classes and supplied reference lines; supported by the core scatter renderer | All 1,457 supplied rows already have FDR below 0.01. Grey rows have small absolute median differences, so grey must not be labeled P-nonsignificant. Source values establish C3 minus C5; do not reverse the sign from ambiguous published wording. |
| [Vabistsevits et al., Nature Communications 2024, Fig. 3a–b](https://www.nature.com/articles/s41467-024-48105-7/figures/3) | Supplied OR and asymmetric 95% CI, log axis/reference 1, filled/hollow states, grouped row blocks; use [interval plotting](interval-plot.md) | 24 supplied estimates per panel. Per-estimate n is not supplied. Global GWAS sample sizes must not be invented as row counts. No estimate is recomputed or reweighted. |

Worked inputs, adopted choices and review evidence are indexed in [worked cases](examples.md). Cases include attribution and transformations; author plotting code is neither required nor bundled.

## Next candidates, not validated cases

The following primary-source candidates were screened but have not been promoted to reusable/reviewed cases. Check their exact Source Data and study design again before use.

- [Urschel et al., Nature Communications 2024, Fig. 2b](https://www.nature.com/articles/s41467-024-47429-8/figures/2): paired observations on a log scale, median and IQR. IQR is not a confidence interval; connecting pairs would be an intentional addition.
- [Truong et al., Nature Methods 2024, Fig. 1b](https://www.nature.com/articles/s41592-023-02162-w/figures/1): stacked components, supplied ratio, raw replicate points and SD. Preserve supplied ratios rather than dividing group averages; first resolve whether a second axis improves the reading task.
- [Cortés-López et al., Nature Communications 2022, Fig. 1b](https://www.nature.com/articles/s41467-022-31818-y/figures/1): a useful future statistical-audit candidate. A scout's exact one-sided signed-rank calculation on the supplied nine pairs did not match the published P value. This unresolved discrepancy excludes it from current validated cases; do not copy the published annotation as a recomputed result.

Do not report these screened candidates as reproduced, packaged, or statistically verified.
