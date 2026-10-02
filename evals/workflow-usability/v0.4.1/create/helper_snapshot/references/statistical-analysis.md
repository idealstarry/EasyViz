# Planned statistical analysis (create track)

Use `scripts/analyze.py` when the **create track** needs a quantitative summary
or a planned comparison on prepared data. It is separate from choosing a chart
and from matching a reference figure in the reproduce track. A reference image
alone cannot establish experimental units, pairing, or statistical significance.

The helper accepts one UTF-8 CSV and an explicit JSON plan. Try the
[synthetic independent and paired teaching fixtures](../assets/fixtures/statistical-analysis/README.md)
for runnable examples. It writes a fresh
attempt directory containing results, source-row accounting, methods and runtime
identity. It preserves source values and unit strings; `001` remains `001`.
It performs no upstream normalization, differential expression, enrichment,
model fitting or automatic search for significant comparisons.

```sh
python scripts/analyze.py --describe-plan
python scripts/analyze.py --data prepared.csv --plan analysis-plan.json --out analysis-attempt-01
```

## Decide meaning and design before inference

1. Identify the actual sampling unit: a person, animal, independent specimen,
   independently assigned experiment or another scientifically justified unit.
   Multiple fields of view, cells from the same specimen and technical repeats
   do not automatically become independent samples.
2. Map the measured outcome and group or `x`/`y` columns explicitly. Establish
   whether subjects are independent or paired by their identities. Do not infer
   this from row count or merely equal group sizes.
3. State the scientific question and select a method that addresses it. A
   normality test alone is not a complete method-selection rule. Confirm the
   design with the user or an explicit data dictionary before inferential tests.
4. Fix comparison names, group order, missing policy and any hypothesis family
   before viewing test results. Record necessary aggregation or transformation
   as a separate, reviewable preparation step.
5. Inspect the recorded exclusions, assumptions, effect direction and intervals.
   Plot descriptive observations and effects alongside uncertainty; a small
   p-value alone is not a figure-design objective.

`design.confirmed=true` records this explicit confirmation; the program cannot
verify that a supplied ID really names an independent experimental unit. It
rejects repeated IDs in an independent comparison and duplicate subject/group
rows in a paired comparison, including rows with missing measurements. It does
not silently average technical repeats or choose a repeated-measures model.

## Minimal independent comparison plan

```json
{
  "schema_version": 1,
  "question": "Does the mean measurement differ between the two independent groups?",
  "design": {
    "unit": "sample_id",
    "unit_definition": "One independently sampled specimen",
    "structure": "independent",
    "confirmed": true
  },
  "missing_policy": "error",
  "comparisons": [
    {
      "name": "planned_group_difference",
      "method": "welch",
      "fields": {"group": "condition", "value": "measurement"},
      "groups": ["control", "treated"],
      "confidence_level": 0.95
    }
  ]
}
```

String group labels are matched exactly. Only the two declared groups enter a
comparison; the number of other source rows is reported as `unselected_rows`.
The effect direction is always first group minus second group, or its stated
rank-probability equivalent. Unknown keys, ambiguous roles and reused columns
are rejected.

| Method | Required roles and design | Effect and interval | Interpretation |
| --- | --- | --- | --- |
| `descriptive` | `value`, optional `group`; confirmed units optional | Mean, median, sample SD, quartiles, minimum and maximum; no confidence interval | Describe observations; unconfirmed unit counts are never presented as independent sample sizes |
| `welch` | `group,value`, two named groups, confirmed independent units | First-group mean minus second-group mean; Welch-Satterthwaite t interval | Mean comparison with potentially unequal variances; justify normal-population or adequate mean-inference assumptions |
| `mannwhitney` | `group,value`, two named groups, confirmed independent units | Cliff's delta; no effect interval computed | Test of equal distributions, not generally a test of equal medians |
| `paired_t` | `group,value`, two conditions, confirmed paired subject IDs | Mean within-subject difference; paired-difference t interval | Independent subjects with justified inference on within-subject differences |
| `wilcoxon` | `group,value`, two conditions, confirmed paired subject IDs | Matched rank-biserial effect; no effect interval computed | Signed-rank test assumes symmetry of within-subject differences |
| `pearson` | `x,y`, confirmed independent units | Pearson correlation; approximate Fisher z interval for n>3 and non-perfect correlation | Linear association; classical inference assumes bivariate normal observations |
| `spearman` | `x,y`, confirmed independent units | Rank correlation; no effect interval computed | Monotonic association; inspect the recorded p-value calculation |

Two-group tests require at least two complete units per independent group or two
complete subject pairs. Correlation requires at least three complete independent
units and nonconstant variables. Zero standard errors and undefined statistics
are rejected. Confidence intervals are **pointwise** even when p-values are
adjusted across a family.

## Descriptions before design confirmation

When the user has provided only a directory and the sampling unit is still
unknown, a descriptive-only plan can proceed. All inferential methods remain
blocked. `n_rows` means rows; `independent_unit_count` is null.

```json
{
  "schema_version": 1,
  "question": "Describe the observed measurement distribution by condition",
  "design": {
    "unit": null,
    "unit_definition": "Unknown; row-level exploratory summaries only",
    "structure": "unknown",
    "confirmed": false
  },
  "missing_policy": "error",
  "comparisons": [
    {
      "name": "measurement_overview",
      "method": "descriptive",
      "fields": {"group": "condition", "value": "measurement"}
    }
  ]
}
```

Choose fields after inspecting the inventory/data dictionary. Running every
numeric column as a separate significance test is not a supported exploration
workflow.

## Pairing and missing values

For `paired_t` or `wilcoxon`, set `design.structure` to `paired`. The unit column
names the same subject in both conditions. Rows are aligned by this string ID,
not their order in the CSV. A subject/group combination can occur only once.

Declare `missing_policy`:

- `error`: missing measured values and incomplete subject pairs stop the attempt.
- `complete_case`: exclude observations missing any required numeric value. For
  paired inference, exclude the whole incomplete subject pair, including its
  valid partner. Record every excluded source row and subject.

Default measurement-only missing tokens are `""`, `"NA"`, `"NaN"`. Customize the
exact strings with `missing_tokens`, always including `""`. Tokens do not convert
unit IDs or group names into missing values: an ID `NA` remains the string `NA`.
A blank unit ID or blank group cannot establish a design and is rejected.
Padded unit IDs are also rejected so `001` and `001 ` do not silently become
different apparent samples; resolve whitespace in a recorded preparation step.
Non-numeric text and undeclared infinity/NaN are errors. Complete-case analysis
can change the target population and requires a justified missingness argument;
counts and exclusions make that decision inspectable.

For Wilcoxon, known measurement precision can be declared with
`"difference_decimals": 3` inside its comparison. This rounds within-subject
differences for rank computation; it never changes source values. Otherwise,
differences are not automatically rounded. Small floating-point differences
can split intended ties, so precision should come from the data definition.

## Planned multiple comparisons

Multiple inferential comparison names require an explicitly named hypothesis
family and an adjustment. The list must include **every inferential comparison
exactly once**, excluding descriptive summaries. A single comparison can also
belong to an explicit family. A larger scientific family spanning other files or
runs must be adjusted together externally; this helper cannot see those tests.

```json
"multiplicity": {
  "family": "Two prespecified endpoints",
  "adjustment": "holm",
  "comparisons": ["endpoint_1", "endpoint_2"]
}
```

- `holm`: sort raw p-values, multiply by the number of remaining hypotheses,
  take the cumulative maximum, clip at one, restore original order. This
  controls family-wise error under arbitrary dependence.
- `benjamini_hochberg`: sort raw p-values, multiply by family size/rank, take the
  reverse cumulative minimum, clip at one, restore original order. False
  discovery rate control requires independence or appropriate positive
  dependence; justify this choice for the scientific family.

Results retain both `pvalue` and `adjusted_pvalue` with family name, method and
size. Without an adjustment, adjusted values and labels are null. The helper
never labels an unadjusted p-value as adjusted. Adjusting p-values does not turn
pointwise confidence intervals into simultaneous intervals.

## Exact calculations and approximations

Mann-Whitney uses the exact no-tie null distribution when one group has at most
eight observations. For tied data with at most 20,000 possible label allocations,
it uses exhaustive label permutations. Larger cases use the tie-corrected normal
approximation with continuity correction; small tied groups receive a recorded
caveat.

Wilcoxon uses the exact signed-rank distribution for up to 50 **nonzero**
differences without tied absolute ranks, exhaustive sign permutations for tied
cases with up to 13 **nonzero** differences, and a normal approximation
otherwise. Under `zero_method='wilcox'`, zero differences are discarded before
routing and calculation, while all complete pairs remain in summaries and
source accounting. For example, five positive differences and 15 zero
differences have an effective sign sample of five, giving an exact two-sided
p-value of 0.0625. Matched rank-biserial effects use average ranks of nonzero
absolute differences.

Spearman uses exhaustive pairing permutations for at most eight units. Larger
samples use SciPy's asymptotic calculation, with an explicit caveat through
500 units. If a modest-sample correlation is a central inference, plan a
separate permutation procedure with a recorded random seed and computation
budget. No interval is manufactured for a rank effect.

## Outputs and replay evidence

- `results.json`: plan, comparison results, unit/row counts, effects, intervals
  or an explicit absence, exclusion reasons, input/helper hashes, Python/NumPy/
  SciPy versions, and artifact hashes.
- `summary.csv`: one descriptive summary per variable/group plus the comparison
  effect, interval and raw/adjusted p-values. Quartiles use linear interpolation; sample SD uses `ddof=1`. A comparison spanning two groups
  appears in both group summary rows; these are not two separate tests.
- `analyzed-data.csv`: all selected rows for each comparison, unchanged original
  fields, comparison name, source CSV record number, inclusion status and reason.
  A row selected in two comparisons appears twice, with distinct comparison IDs.
- `methodology.md`: recorded design, counts, exclusions, assumptions, effect
  direction, interval scope and numerical methods.
- `plan.json`: normalized plan used for the attempt.

The output must be a **new directory**. The helper validates and computes before
reserving it, publishes each complete file atomically, and publishes
`results.json` last. A handled publication failure removes its partial attempt.
A crash before the final manifest can leave an incomplete directory; use a new
attempt path and do not treat that directory as successful. Existing results
and source files are never overwritten.

Tested with Python 3.12.2, NumPy 2.5.3 and SciPy 1.18.1; each actual attempt records
its own runtime and helper hash. Numerical tests cover known test statistics,
analytical intervals, group direction, exact permutations, unit pairing,
leading-zero IDs, missing-pair accounting and hand-calculated Holm/BH values.

Primary implementation references:

- [SciPy independent t test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html)
- [SciPy paired t test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_rel.html)
- [SciPy Mann-Whitney U](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html)
- [SciPy Wilcoxon signed-rank](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)
- [SciPy Pearson correlation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html)
- [SciPy Spearman correlation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html)
- [SciPy permutation test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html)
- [SciPy false discovery control and its BH references](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html)
