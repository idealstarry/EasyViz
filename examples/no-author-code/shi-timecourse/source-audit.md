# Source evidence and extraction

Shi et al., *Precise regulation of the relative rates of surface area and
volume synthesis in bacterial cells growing in dynamic environments*,
Nature Communications 12, 1975 (2021).
DOI: [10.1038/s41467-021-22092-5](https://www.nature.com/articles/s41467-021-22092-5).

The article's public licence was checked on 2 October 2026 and is
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The selected figure
and data are attributed to Shi and colleagues. This case selects one panel
and produces an adapted plot; it does not reuse author code.

The public [Source Data workbook](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-021-22092-5/MediaObjects/41467_2021_22092_MOESM5_ESM.xlsx)
contains a worksheet called `Figure 1d`. Row 3 explicitly labels time,
cell width, cell length, and their standard deviations. Rows 4–63 contain
all 60 time points, from 1 to 60 minutes, for both dimensions. Columns B/C/D
hold width time/mean/SD; F/G/H hold length time/mean/SD.

`extract_source_data.py` checks the workbook SHA-256, worksheet name and
headers, then reads original numerical XML text into `source-data.csv`.
Every selected source value retains its worksheet, row and cell address.
The transformation is only wide-to-long reshaping: 120 summary rows and
360 numerical cell strings are preserved without rounding or filtering.
The workbook and worksheet checksums are recorded in `source-checks.json`.

The caption states that lines and bands represent means and SD from
146 single cells followed by time-lapse imaging. The selected source sheet
contains summaries, not those individual cell trajectories. The bands are
not SEM or confidence intervals, and the reported cell count does not
establish 146 independent biological replicates. No test or fitted model
is reconstructed from the image.

The reference crop includes the entire individual panel, including its
letter and both axes; its exact original pixel rectangle and checksum
are recorded in `provenance.json`. Physical output size and typography
are explicit adopted settings, not measurements inferred from pixels.

To repeat the source extraction after downloading the public workbook:

```sh
python extract_source_data.py --source /absolute/path/to/41467_2021_22092_MOESM5_ESM.xlsx
```
