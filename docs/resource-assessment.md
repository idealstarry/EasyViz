# Supplied research collections

## Local resource assessment

The inventory was taken on 2026-09-08. File counts describe visible local files; they do not establish that all scripts can run. The detailed paths and sizes are in [resource-inventory.json](../examples/resource-inventory.json).

| Collection | Local evidence | Conversion readiness |
| --- | --- | --- |
| Gontijo et al., 2022 | Paper, R Markdown, README, and six cleaned CSV files | First runnable microbiology example selected. Other matrix/network views require separate validation. |
| Somerville et al., 2024 | Paper, R Markdown, rendered HTML, and README | Useful code and rendered visual references. Input tables referenced by the script are absent locally; README points to a Zenodo deposit. A complete runnable case needs the matching data. |
| Damoczi et al., 2024 | Paper and a supplementary Word document containing an R workflow | The inspected code performs motif/ORF/bacteriocin analysis and uses external FASTA/genome paths. Requires upstream results before a source-data plotting example can be isolated. |
| Blanco 2022; Borowska 2025; De Filippis 2024; Pasolli 2020; Sharp 2025; Tang & Leisner 2025 | Six standalone PDFs | Visual-reference candidates. No companion data or scripts found in these local entries. |
| Angarola et al., 2025 | Figure-organized and historical scripts, rendered plots, tabular files, and two RDS objects | First runnable single-cell example selected from a small historical count table with matching code/image. Do not assume historical figure labels match final publication panels. |
| Massier et al., 2023 | Scripts and a dedicated Source Data directory with 18 TXT/XLSX data files | Figure 1e radar, Figure 8a BMI distributions, and Figure 2f myeloid counts now have tested source-data conversions. Other table-to-panel mappings remain unvalidated. Raw FCS files and integration workflows are not direct EasyViz inputs. |
| Kensuke et al., 2024 | Paper and three R scripts | Local scripts include upstream clustering, RNA velocity, and bulk scoring. Matching ready-to-plot data is not established. |
| Mayra et al., 2024 | Paper, notebooks, Python code, and two CSV files | Inspect individual notebook inputs before selection; the presence of CSV files alone does not establish complete plotting data. |
| Single-cell methods | Four PDFs | Method and visual references; no executable example established. |
