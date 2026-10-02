# Planned-analysis teaching fixtures

These small tables are **synthetic educational observations**, not paper source
data and not evidence for a scientific claim. IDs intentionally contain leading
zeros. The independent and paired plans differ in experimental structure, not
simply the number or order of spreadsheet rows.

From the installed `easyviz` skill directory:

```sh
python scripts/analyze.py --data assets/fixtures/statistical-analysis/independent.csv --plan assets/fixtures/statistical-analysis/independent-plan.json --out /tmp/easyviz-independent-analysis-01
python scripts/analyze.py --data assets/fixtures/statistical-analysis/paired.csv --plan assets/fixtures/statistical-analysis/paired-plan.json --out /tmp/easyviz-paired-analysis-01
```

Choose fresh output paths on reruns. Inspect `methodology.md`, `results.json` and
`analyzed-data.csv`; group order makes the reported direction treated minus
control, or after minus before. For real data, replace the plan with actual
experimental-unit knowledge and the scientific question before inference.
