# Panel layout for manuscript assembly

## Physical dimensions

Use millimeters (mm) for width and height, and points (pt) for text and line widths. Canvas dimensions include text, legends, and margins. The aspect ratios and export dimensions below refer to the complete canvas; constraints such as equal coordinate scaling or square heatmap cells apply separately to the plotting area.

Reuse the user's figure width, panel dimensions, fonts, and existing project settings. Fill only missing values. Clarify conflicting width, height, and aspect-ratio requirements instead of silently overriding them.

When no specification exists, use the following internal starting values and identify them to the user as adjustable defaults.

| Setting | Starting value |
| --- | --- |
| Available figure width | 180 mm |
| Columns and gap | 2 columns; 4 mm gap |
| Single-column panel width | 88 mm |
| Default canvas aspect ratio, width:height | 1:1; 88 × 88 mm |
| Alternative canvas aspect ratios | Landscape 4:3; portrait 3:4 |
| Font | Prefer Arial; if unavailable, select an available compatible sans-serif font and record the actual font. |
| Base text size | 8 pt for axis titles, ticks, legends, and statistical annotations |
| Explicitly requested title or panel letter | 9 pt starting size; bold panel letter. Neither is added by default. |
| Base line width | 0.6 pt |
| Raster resolution | 300 dpi when unspecified |
| Export format | PDF with a PNG preview when unspecified |

These values are project defaults, not journal standards. Choose an aspect ratio based on chart type and data density before exporting the panel set, and record each panel's specification.

### Grid calculations

For a regular grid, let W be the available figure width, n the number of columns, g the gap, k the number of columns a panel spans, and r its width-to-height ratio.

| Dimension | Calculation |
| --- | --- |
| Single-column width | `(W - (n - 1) × g) / n` |
| Width spanning k columns | `k × single-column width + (k - 1) × g` |
| Canvas height | `canvas width / r` |

Use explicit dimensions for user-defined irregular layouts instead of forcing a grid. Panels requiring alignment in the same row should share a canvas height; their internal plotting areas and margins may differ. Include legends and long labels within the canvas. Preserve final physical dimensions when adapting the proportions of a reference image.

## Panel text and separate captions

Scientific manuscript panels default to the data display and its essential decoding elements. Keep axis names and units, ticks, legends, colorbars, and essential data annotations. Omit extra titles, subtitles, standalone overview counts, and explanatory footnotes from the image. Counts that are plotted quantities or necessary data annotations remain part of the chart; a decorative summary of the dataset belongs in the caption.

Apply this default to both tracks. Add an in-image title only when explicitly requested by the user; observing one in a reference is not a request to retain it. There is no fixed top-left title or header template. If a title is requested, choose its placement for that panel within the agreed dimensions. Otherwise allocate the available interior to the chart, labels, and legends without reserving an empty title band.

Write `caption.md` separately from the exported panel. Use concise journal-style prose describing the display, necessary abbreviation definitions, data selection or denominators, statistical methods and uncertainty definitions, source attribution, and material caveats. Use known figure and panel identifiers, such as `Figure 1. ... (A) ...`, only when the user has established them; otherwise keep the caption unnumbered. Do not invent identifiers, methods, results, or significance claims. The caption does not occupy the image canvas or become a rendered footnote by default.

## Typography and adjustment

Before plotting, check font availability and coverage for the actual text, including Chinese characters, Greek letters, and mathematical symbols. Select fonts that cover missing glyphs, disclose substitutions, and record the actual font configuration consistently across the panel set. Set text roles explicitly to prevent plotting-library defaults from changing relative sizes.

Within established dimensions, resolve crowding through wrapping, tick density, legend placement, label avoidance, and internal margins. Do not silently remove data, change statistical methods, or reduce text sizes to fit content. If a panel needs more space, propose revised physical dimensions or a split into separate panels. When this would change an agreed assembly layout, obtain the user's choice before rerendering. Retain the shared text sizes in the revised dimensions.

Follow [Legend layout](legend-layout.md) to measure the full key-and-text footprint and its reserved region against the plot. Preserve font sizes while adjusting categorical proxy keys, gaps, columns, colorbar geometry, or placement. Quantitative size keys must retain the same value-to-area mapping as plotted marks. Inspect relative prominence as well as clipping; correct typography alone does not establish correct proportions.

When the user changes a font or text size, update the shared settings and rerender panels within the requested scope. Do not scale exported images to apply the change. Keep text roles consistent across panels; different roles may have different sizes.

## Filled marks and palette combinations

Declare one outline policy for comparable filled dots, bars, and matching legend swatches within an integrated panel. Create defaults to borderless fills: explicitly disable edge strokes rather than relying on plotting-library defaults. In reproduce, resolve the policy from the adopted specification and user requirements. Do not incidentally outline dots while leaving related bars or legend keys borderless. Axes, error bars, and other line encodings are separate roles.

An outline can be intentional when it encodes a distinction or is needed to make marks readable. Record the affected mark role, edge color/width, and scientific or readability reason in the saved settings; apply its legend treatment consistently. Review any effect on the perceived area of quantitative dots. Styling exceptions must not arise solely because different plotting functions have different defaults.

Inspect all categorical palettes, continuous maps, annotations, and background colors together on the actual scientific panel at its intended size. Check category distinction, visual balance, scale meaning, and readability across both large bars and small dots. Literature provenance alone does not establish a good combination. Adapt combinations to the data and panel while preserving agreed category identities; do not impose one combination on every dataset.

## Export and verification

| Area | Requirement |
| --- | --- |
| Canvas boundaries | Preserve the entire canvas. Avoid automatic tight cropping that changes export dimensions; for example, do not use Matplotlib's `bbox_inches='tight'`. Internal layout adjustment is allowed, followed by a boundary check. |
| Vector output | Preserve physical page dimensions and check font embedding or substitution. Preserve text when editability is needed; convert text to paths only when requested. |
| Raster output | Calculate pixels as `round(mm / 25.4 × dpi)`, allowing rounding error. Write resolution metadata where supported and record both mm and dpi for placement at the intended size. |
| Multiple formats | Preserve the same physical dimensions and content extent across formats. Increasing dpi changes pixel count, not text size or physical dimensions. |
| Visual inspection | Check readability, missing glyphs, overlapping annotations, clipping, and agreement between recorded and exported dimensions. Tell the user to place panels at the recorded size because assembly software may rescale imported files. |

## Saved settings

Save shared settings and each panel's actual width and height in a readable configuration in the output directory, such as `figure-settings.json`. Scripts should read that configuration or preserve equivalent parameters completely.

The core renderer can read one [figure-profile.json](figure-profile.md) for a panel set. Store shared font, `font_size_pt`, line width and dpi there, along with each named panel's `width_mm` and `height_mm`; select a panel with `--profile` and `--panel`, or the equivalent spec fields. Panel-specific internal margins remain local. Conflicting explicit font sizes or dimensions are rejected so a panel cannot silently diverge from the assembly settings. Numeric values carry the units in their key names; unknown keys such as `fontsize_pt` produce a correction hint.

Record the track, input paths, color mappings, mark-outline policy and exceptions, actual fonts, sizes by text role, line widths, export formats, and dpi. Update the record when settings change; do not leave these details only in the conversation.

Profile-based outputs additionally save the absolute profile path, profile SHA-256, selected panel and scale, original panel spec, and shared-settings snapshot. Preserve the shared profile with the individual output specs. Updating it does not rescale or assemble previously exported panels; rerender the affected panels at their declared physical sizes.

## Executable support

Copy starting dimensions from [presets.json](../assets/layouts/presets.json) into the renderer's `layout` settings. Use [chart-library.md](chart-library.md) for the supported data mappings and options. Resolved output settings record the actual font and physical dimensions; the renderer also writes export checks. A successful render still requires visual inspection, especially for overlaps between labels that remain inside the canvas.

Keep grids underneath primary marks, labels, and annotations. A fixed canvas should preserve scientific content; it is not a reason to crop observations, reduce the shared font size, or invent a simpler statistical result.
