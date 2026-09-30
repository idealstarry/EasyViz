# Frozen source data

Retrieved 2026-09-30. This evaluation is a third-party presentation, with no NOAA or USGS endorsement. Government source material in these tables is public-domain material; EasyViz does not claim copyright over it. Sources may be revised after retrieval, so the saved CSV and hashes identify this run.

## NOAA annual CO2

- Product: [NOAA GML Mauna Loa annual means](https://gml.noaa.gov/ccgg/trends/data.html).
- Raw file: https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt
- Distribution terms: [NOAA GML Disclaimer and Terms of Reference](https://gml.noaa.gov/about/disclaimer.html), public domain unless individually annotated, free use with acknowledgment and no false endorsement or official presentation. The file itself states that the data are freely available for public and scientific use.
- Credit: Data provided by NOAA Global Monitoring Laboratory, Boulder, Colorado, USA; Dr. Xin Lan, NOAA/GML, and Dr. Ralph Keeling, Scripps Institution of Oceanography. Only 1980–2024 rows are included, after the Scripps-only period described by the raw header.
- Grain: one annual mean per calendar year. `mean_ppm` is dry-air mole fraction in micromol/mol (ppm). `uncertainty_ppm` is NOAA's supplied uncertainty: standard deviation of differences between annual means determined independently by NOAA/ESRL and Scripps, not a confidence interval or temporal spread.
- Site note: Mauna Loa observations paused after 2022-11-29 and resumed in July 2023. Observations from December 2022 through 2023-07-04 were obtained at Maunakea. Both arms receive this source note.
- Transform: retain 1980–2024 inclusive, preserve decimal strings, rename raw `mean`/`unc` fields. No fitting, interpolation or recomputation of annual means.

## USGS earthquake events

- Product: [USGS ComCat/FDSN earthquake catalog API](https://earthquake.usgs.gov/fdsnws/event/1/).
- Full exact query and SHA256 are in `provenance.json`.
- Distribution terms: [USGS Copyrights and Credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits): USGS-authored or produced data are in the U.S. public domain; credit is requested. Only rows with USGS preferred `net`, `locationSource`, and `magSource` equal to `us` are retained, avoiding a third-party preferred-origin row.
- Credit: U.S. Geological Survey, Department of the Interior/USGS.
- Grain: one reviewed catalog earthquake event, identified by `id`, UTC time, preferred hypocentral `depth` in km, preferred catalog `mag` and its `magType`. Magnitude types may differ; these are not replicated experiments or uniformly measured energy/intensity. No event uncertainty fields are supplied in this minimal input.
- Scope: 2024-01-01T00:00:00Z inclusive to 2024-02-01T00:00:00Z exclusive, global, queried `minmagnitude=5`, `eventtype=earthquake`, `contributor=us`; then restrict preferred network, location and magnitude source to USGS as above. This is a catalog sample, not all earthquakes or a catalog-completeness study.
- Transform: retain identifiers and these plotting/source fields only; remove February endpoint if present; restrict source as declared. No rounding, weighting, aggregation or random sampling.

`provenance.json` records full-download hashes and derived CSV hashes. Raw downloaded bodies remain outside the repository in a temporary folder. The CSVs are the minimal immutable source inputs for replaying this run. No source figures, logos or website text are redistributed here.
