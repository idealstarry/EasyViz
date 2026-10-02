# Recommended scientific views

The strongest first panel is a boxplot with every fluorescence observation. It answers the primary question stated in the study notes and makes the signal difference and sample spread visible without density smoothing.

| Priority | View and reading task | Explicit fields | Descriptive preview |
| --- | --- | --- | --- |
| 1, produced | Boxplot with all raw observations: compare signal across independent conditions | group=condition, value=signal, unit=sample_id | Control: n=12, median=5.47 a.u., IQR=4.89–6.05; Treatment: n=12, median=6.52 a.u., IQR=6.00–7.99. Observed means: 5.21 and 6.94 a.u. |
| 2 | Signal ECDF: compare the full distribution and tails without smoothing | group=condition, value=signal, unit=sample_id | Control spans 2.54–7.09 a.u.; Treatment spans 5.44–8.68 a.u. All 24 measured values can contribute one step each. |
| 3 | Signal versus viability scatter, colored by condition: explore how the two outcomes covary | x=signal, y=viability_pct, group=condition, unit=sample_id | Viability means are 83.14% and 80.33%, with observed ranges 78.75–86.73% and 75.91–86.04%. A scatter can reveal condition-specific patterns; these group summaries alone do not establish an association. |

The study notes establish that the conditions contain different independent specimens. A paired view is therefore inappropriate; the generated paired candidate was rejected. Viability is an exploratory endpoint. No pooled regression or correlation inference was selected. There are no missing values, duplicate sample IDs or excluded specimens. The two descriptive endpoint plans and their complete source-row accounting are retained in analysis-01.

The produced panel is 120 × 90 mm, with English labels, Arial 8 pt text and 300 dpi raster resolution. Color assignments are saved in figure-profile.json. Narrative and sample counts are in caption.md, outside the panel.
