# Identical plotting request for both arms

Create two individual scientific manuscript panels from the supplied CSVs. The intended reader should be able to answer the reading tasks below from the panel and its separate caption.

1. **NOAA CO2**: Show how annual mean atmospheric CO2 at the monitored site changes over 1980–2024, while retaining the supplied uncertainty and its correct meaning. Which years bound the record, and how large is the overall change?
2. **USGS earthquakes**: Show how preferred hypocentral depth and catalog magnitude vary across the supplied January 2024 events. Can the reader compare shallow and deep events and recognize relevant differences in measurement type? The catalog sample and variables must be described correctly.

Per panel, deliver PNG at 300 dpi, PDF, SVG, a separate journal-style `caption.md`, a runnable plotting script, actual settings and traceable plotted values. Deliver all requested observations; record transformations, filtering, statistics and any unavailable checks. No fitted or significance layer is required.

The complete canvas must be **90 × 70 mm** in every format, including axes, legends and margins. Use **Arial, 8 pt** for all panel text. If Arial is unavailable, report the actual substituted font; do not shrink type. Keep data-reading text in the image and explanatory prose in the caption. Do not add an in-image title, panel letter or explanatory footnote. Choose an honest and readable encoding; no specific chart or palette is prescribed. Gridlines should remain beneath marks. Inspect the exported image at its intended size, and correct visible clipping or overlap without changing the agreed size or font.

Source files: `inputs/noaa-co2-1980-2024.csv`, `inputs/usgs-earthquakes-2024-01.csv`. Read `inputs/SOURCES.md` for field meanings, sampling scope, uncertainty and source caveats, and `inputs/provenance.json` for traceability. Work only in your assigned output folder. Keep the first complete render in `initial/` before making visual corrections, and put the delivered result in `final/`. Save a `run-log.json` with UTC start/end, available token data (use null when unavailable), tool call counts from your actual work, attempted repairs, files read, and your own inspection findings. Do not invent controlled token budgets or times.
