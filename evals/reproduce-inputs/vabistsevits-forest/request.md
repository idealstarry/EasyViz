# Reproduce request: mammographic-density effect forest

Use `reference.png` as the visual standard for Figure 3a–b. It contains the two forest plots and their shared outcome legend, cropped from PDF page 5 of the official article. Reproduce the 48 published estimates in `source-data.csv` and preserve their exact confidence-interval endpoints.

The source figure compares total and direct effects across three exposures and eight outcomes. Preserve the visible exposure blocks, outcome order, distinct outcome colors, open-circle encoding when a confidence interval overlaps the null, and odds-ratio reference at 1. Retain the statistical column labels and data-reading text. Put narrative, methods, sample-size context, and source attribution in a separate caption. Final canvas and export settings are to be specified by the plotting agent before rendering.

The source values are already prepared for plotting. No genotype, GWAS, instrumental-variable, or Mendelian-randomization analysis is required. The source table provides odds ratios and 95% confidence intervals, but no per-estimate `n`. Do not reconstruct intervals from standard errors, invent sample sizes, or interpret the intervals as SD or SEM.

Use the fresh report in `independent-reading.md` before selecting a template. No author plotting code was used for input preparation or supplied to the reader.

## Caption evidence

Figure 3 reports odds ratios for breast cancer per SD increment in the mammographic-density phenotype. Panel a shows total effect from univariable IVW MR; panel b shows direct effect from multivariable IVW MR accounting for childhood body size. Error bars are 95% confidence intervals. Hollow circles indicate intervals overlapping the null.

The caption reports GWAS-level sample sizes, including 24,158 for mammographic density and 247,173 for overall breast cancer. Breast-cancer subtype sizes are referred to Supplementary Table 1. These contextual counts are not present as per-estimate sizes in the source table.

Attribution: Vabistsevits et al., Nature Communications 15, 4021 (2024), [10.1038/s41467-024-48105-7](https://doi.org/10.1038/s41467-024-48105-7). Article license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The reference image was cropped and the selected source table converted to CSV; the original numerical values were preserved.
