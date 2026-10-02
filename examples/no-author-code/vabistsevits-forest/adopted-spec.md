# Adopted specification: supplied-interval forest panels

The independent image reading in `inputs/independent-reading.md` preceded selecting the reusable plotting implementation. This reconstruction uses the published figure image, its caption, and the numerical Source Data; no author plotting code was supplied, sought, read, or executed.

## Required scientific mapping

- Render total and direct effects as two separate manuscript panels. Each contains all 24 supplied estimates: three mammographic-density exposure blocks and eight breast-cancer outcomes. The direct-effect table is a same-study transfer check using the same plotting specification, not an independent-study validation.
- Map horizontal position to supplied odds ratio, with a logarithmic axis and explicit reference at 1. Use the separate unrounded lower and upper 95% confidence endpoints. No endpoint is rebuilt from an SD, SEM, standard error, or image pixels.
- Preserve the source hollow-circle states (`effect_direction = overlaps null`) and the original state column. The added `mark_state` is an explicit string mapping to `hollow`/`filled`. The figure does not add tests, p values, stars, weights, or sample sizes.
- Use the reference's exposure and outcome orders, declared in the JSON rather than inferred from the workbook ordering; panel b's input order differs from its display order. All source rows remain traceable.
- `n` stays empty for every record. Caption-level GWAS sample counts do not become per-estimate `n`.

## Adopted layout and style

Both canvases are 105 × 135 mm, Arial 8 pt, 300 dpi, with 0.6 pt interval strokes and equal 20 pt² circle area. These are newly adopted physical settings, not measurements recovered from the reference raster. The original plot's evidence supports a log scale; explicit [0.28, 2.8] limits contain all supplied endpoints in both panels. Original log-base/limits are not stated by the supplied image.

Maintain three separated exposure blocks, consistent outcome-color associations, un-capped horizontal intervals, and hollow versus filled circles. The palette uses dominant solid RGB samples from the supplied PDF raster crop: it approximates the observed appearance and is not evidence of the author's stored palette. Neutral labels preserve readability for the pale yellow, blue, and pink categories.

The standalone panels repeat the eight outcome labels in each block instead of sharing the original two-panel outcome legend. Exposure headers identify the blocks horizontally rather than as rotated labels. The concise fill-state guides are retained as decoding elements; methods and interpretation are in the separate captions. Filled marks have no border; hollow marks have the corresponding color outline because that outline carries the observed state encoding.

Intentional manuscript adaptations: omit source panel lettering, total/direct effect titles, and the original shared outer `Exposure` label; identify the effect in its separate caption. Export one full canvas per panel without cropping. Use a restrained dashed reference and omit the source's enclosing gray frames and its x = 2 guide. Use equal marker areas across both panels instead of their different reference-image diameters. These choices preserve the estimates and their uncertainty while accommodating labels and consistent final typography.

## Evidence and residual questions

The images do not establish exact original fonts, point sizes, physical dimensions, DPI, line widths, or complete uncropped geometry. GWAS analysis, phenotype transformations, and instrument selection are outside this numerical plotting case. The direct-effect panel exercises a second supplied table using the same settings; neither this case nor its provenance establishes universal forest-plot support or publication suitability without inspecting a new dataset.

Actual export, source-to-artist, and layout checks are recorded in each output folder. Independent visual review remains a separate requirement; an automated fit result does not establish reference fidelity or readability.

The first render is retained in `first-render/` with truthful `needs_revision` QA. Its exact source-to-artist mapping and marker geometry passed, but dense automatically formatted log ticks overlapped, and two bottom state-guide requests occupied the same anchor. Correction keeps the canvas and fonts fixed: explicitly label log ticks 0.5, 1, and 2, and combine the two state keys into one measured bottom guide with an explicit border policy per key. The shared helper also calibrates the requested point area as geometric circle area, recording its separate Matplotlib scatter scale. These are formatting/placement corrections, not data changes.

Source: Vabistsevits et al. (2024), *Mammographic density mediates the protective effect of early-life body size on breast cancer risk*, Nature Communications 15, 4021, [DOI](https://doi.org/10.1038/s41467-024-48105-7). Source numerical values and reference crop are adapted under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
