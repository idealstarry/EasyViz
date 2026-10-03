# Synthetic recipe check

These invented 4 × 4 inputs exercise negative, zero, positive, and endpoint colors; leading-zero strain IDs; complete-denominator means; keyed binary strips; and automatic mean-axis limits. No values come from the development dataset and no biological claim is supported.

Run from the recipe folder:

```sh
python plot.py --data synthetic/matrix.csv --genome synthetic/genome-status.csv --settings synthetic/settings.json --out synthetic/output
```

The reviewed full-canvas exports are in `output/`; `caption.md` supplies the separate fixture caption.
