# Supplied coordinates with proportional circle area

[Xiang et al., Nature Communications 2024](https://www.nature.com/articles/s41467-024-46480-9), Figure 3E scatter subcomponent, adapted from the official Source Data. This case preserves all 1,457 supplied rows, source coordinates/classes and 37 true zero sizes without author plotting code.

```sh
python plot.py --runtime /path/to/easyviz/scripts --out ./my-output
```

Copy this case into a writable project before running it. In the development repository or packaged skill tree, the wrapper can locate the generic runtime automatically. An explicit `--font 'DejaVu Sans'` override is available when Arial is absent; actual settings record that change. `--data`, `--spec` and `--out` accept independent paths.

Read `adopted-spec.md`, `caption.md`, `provenance.json`, the independent reading/review and numerical verification before reusing scientific labels. The generic scatter renderer accepts renamed numeric x/y/size fields and optional categories/reference positions. It does not select genes, assign differential classes or compute adjusted P. Grey here means a small median difference within an already filtered sheet. This source-specific meaning must not become a universal volcano-plot rule.

Original source values and all twelve columns are retained in `source-data.csv`. Large raw XLSX/PDF archives remain outside the plugin; their official links and hashes are recorded in provenance. The reference is a crop, and all case geometry is an explicit adaptation under CC BY 4.0. A second synthetic renamed-column probe checks engineering transfer separately; it is not another biological study.

`verify_exports.py` independently reads written SVG paths, PDF font resources and PNG metadata; it does not import the renderer. Supply `--source-workbook /path/to/official.xlsx` to repeat the original workbook-to-CSV check. Without that file, the check is explicitly not performed. The two date-typed gene cells in the official workbook are retained as decoded dates, without guessing symbols. Development-only first-render history is excluded from the portable case. Metadata paths are shortened during packaging; saved image hashes retain their original review scope.
