# Complete empirical distributions from published observations

This create case adds a different reading task to the [paired-observation case](../../no-author-code/urschel-paired/README.md): compare complete marginal distributions without density estimation. It uses all 254 exact source measurements, including their source-cell references, from 127 participants in Urschel et al. (2024), [DOI 10.1038/s41467-024-47429-8](https://doi.org/10.1038/s41467-024-47429-8). The two time points are paired in the study, but a cumulative distribution does not show the correspondence of individual participants. Infection groups are pooled explicitly; this view does not answer a stratified effect question.

The focused generic `ecdf_plot.py` uses mapped columns and exact empirical jump counts. It performs no smoothing or test. Repeated measurements with the same numeric value contribute their full multiplicity when present; this case has 127 unique values in each curve and exercises no tied jump. Separate engineering checks cover ties. Log display transforms only the horizontal axis, not the measurement or cumulative fractions. Narrative belongs in [caption.md](caption.md).

```sh
python /path/to/case/plot.py --runtime /path/to/easyviz/scripts --out output
```

The wrapper also discovers the renderer within a repository or extracted plugin. Copy a packaged case into a writable project before running it. `--font` records an explicit override when the original Arial is unavailable; rerendered figures need a new visual inspection.

The complete 105 × 85 mm canvas uses 8 pt text and exports PDF, editable SVG and PNG. [Source provenance](provenance.json) records the official workbook, exact derivative identity and selected fields. Numerical/export checks and actual-image review apply to their recorded output hashes, rather than every future use of the script.

[Independent visual review](independent-review.md) records the inspected final images, candidate hashes, export checks and remaining adaptation notes.
