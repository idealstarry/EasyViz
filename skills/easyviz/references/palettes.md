# Palette selection

Use the [literature color card](../assets/palettes/palette-swatches.png) to compare candidates, then inspect them on the actual panel. A publication source establishes provenance, not aesthetic suitability. Choose lightness and saturation by mark area and reading task: pale summary areas with clear edges differ from tiny observations on white. A single quantity may use neutral marks; mixed categorical points need visible decoding. Preserve accepted palettes and group identities unless recoloring is requested. In reproduce, use the adopted reference palette or the user's requested override.

The colors live in [palettes.json](../assets/palettes/palettes.json), and compatible combinations in [families.json](../assets/palettes/families.json). Record the preset and actual label-to-color mapping in output settings. A paper's biological labels do not transfer to new data when its colors are reused.

## Literature choices

| Preset | Meaning and preferred use | Provenance |
| --- | --- | --- |
| `scwat-blue-coral` | Clear blue/coral for two groups; inspect opaque filled or hollow observations and matching outlines. | Selected PDF vector colors from Huang et al. (2023), Fig. 2. Reassigning colors to new groups is an explicit choice. |
| `scwat-blue-pink` | Candidate blue/pink pair for two-class scatter; inspect actual small points and overlap. | Selected vector fitted-line strokes from scWAT Fig. 2g, PDF p. 4. Reusing them as observation colors is an adaptation; source point paints vary. |
| `progeny-summary` | Purple, mint, salmon and gray area colors for bounded distribution summaries, with eligible graphite contours and neutral raw points. | PROGENy Fig. 4c, PDF p. 6: selected purple/mint inner-summary fills and salmon/gray KDE-area fills. Reassigning all four to cohort IQR areas and adding neutral raw points are adaptations. Pale area colors are not automatically suitable for tiny glyphs. |
| `scwat-blue-white-coral` | Blue–white–coral for signed deviations with a meaningful center. | New EasyViz interpolation from Fig. 2 categorical endpoints; not the author's Fig. 2b heatmap palette. |
| `notch2-balanced` | Blue, amber, teal, pink. Selected by the user for the cell-atlas example; evaluate again for other contexts. | Four exact embedded legend colors selected from the same Figure 2b, including I2/I1/I4/M1. |
| `notch2-blue` | Blue sequential scale with a visible light endpoint for borderless marks. | EasyViz 20–100% white-to-I2-blue interpolation; not an author gradient. |
| `somerville-bright` | Sky, coral, teal, lavender; optional gold and turquoise. Start with the first four for compact categorical panels. | Selected/reordered PDF colors from Somerville et al. (2024), Figs. 1B and 2B. |
| `notch2-bright` | Teal, blue, amber, orange for four groups. Retain direct labels because the warm pair is closer. | Selected/reordered embedded legend colors from Cruz Tleugabulova et al. (2024), Fig. 2b. |
| `somerville-sky` | Light-to-bright blue for proportions or other ordered values. | EasyViz white-to-blue interpolation from Fig. 2A's observed blue endpoint. |
| `somerville-coral` | Light-to-coral for a warm quantitative matrix; pair with blue marginal bars. | EasyViz interpolation from Fig. 1B's observed coral endpoint. |
| `notch2-teal` | Light-to-jade for ordered values. | EasyViz interpolation from Fig. 2b's observed I4 teal. |
| `somerville-blue-coral` | Blue–white–coral for signed deviations with an explicitly meaningful center. | New EasyViz gradient using Fig. 1B categorical endpoints. |

Families are candidate combinations, not universal defaults. `notch2-balanced` pairs the selected four-category set with a blue scale; `somerville-fresh` and `notch2-fresh` remain alternatives. Judge areas, small marks, outlines and keys by their roles. A distribution can use category-colored areas with neutral raw points, while a two-class scatter needs point identity. Do not apply the same vivid trio to every example, combine all available hues, or turn a categorical palette into a rainbow heatmap.

The core renderer's technical fallbacks are `somerville-bright` and `somerville-sky` when no explicit choices are supplied. They are not evidence of user approval or suitability; supply the selected palette explicitly. Always review actual marks, not just swatches.

## Source precision

- [Huang et al., Nature Communications 2023](https://www.nature.com/articles/s41467-023-43021-8): the actual Figure 2 page was inspected. Blue/coral vector strokes and fills are `#55A0FB` / `#FF8080` after rounding PDF RGB to 8-bit HEX. The categorical pair is observed; the white-centered continuous ramp is an adaptation. Original author-code constants remain unknown. [Literature design mechanisms](literature-style.md) connects this pair to mark treatment and layout rather than treating hue alone as a design solution.
- scWAT Fig. 2g's actual vector fitted-line strokes round to `#3795D3` / `#FF5FBD`; its blue observation fill/edge round to `#25A7E0` / `#3698D5`, while pink observations have multiple paint layers. `scwat-blue-pink` selects the line pair and does not claim a uniform author scatter palette.
- [Schubert et al., Nature Communications 2018](https://www.nature.com/articles/s41467-017-02391-6): PROGENy Fig. 2d uses gray `#595959` bars. Fig. 4c supplies selected purple/mint inner-summary and salmon/gray KDE-area fills with neutral `#333333` boundaries; `progeny-summary` combines these observed roles into an adapted area palette. Values are rounded PDF vector RGB, not author-code constants or an original four-color IQR palette. The source's mutation/pathway encodings do not transfer to new labels.
- [Somerville et al., Nature Communications 2024](https://www.nature.com/articles/s41467-024-52687-7): rendered figures were inspected and flat PDF vector-fill RGB values were converted to 8-bit HEX. The six-color selection spans two panels; it is an EasyViz selection, not an author-provided palette product.
- [Cruz Tleugabulova et al., Nature Communications 2024](https://www.nature.com/articles/s41467-024-53700-9): RGB values were extracted from uniform embedded legend swatches and checked against the actual rendered figure. These values are exact for those PDF pixels; pre-publication author constants remain unknown.

[Source records](../assets/palettes/sources.json) retain figure/page locations, file hashes and extraction details. Continuous ramps explicitly mix sampled endpoints with white; they are adaptations, not recovered author colormaps. Full article figures are not bundled with the palette collection.

## Mapping and readability

Categorical colors must not cycle when capacity is exceeded. Supply an explicitly reviewed larger mapping, use redundant encodings, or arrange separate panels. Keep group-color assignments stable across related box/violin views as well as other panels. If pale areas need outlines, use deliberate role settings and matching legend symbols. Neutral point overrides are valid when categorical position/labels and summary colors still decode identity; a colored point key must not imply those neutral observations carry hue.

For a panel set, save the complete category-to-color mapping in a [shared figure profile](figure-profile.md). A palette name assigns colors from the current panel's categories; if a group is absent or the order changes, its position in that palette can change. A profile's explicit mapping retains category identity. Omit local `palette` when using shared `colors`; conflicting explicit colors fail instead of overriding the map. New categories must be added to the shared mapping.

For continuous data, record limits and normalization. Recoloring must preserve the established value scale, zero, missing-value meaning and range unless a scientific change is requested. Do not introduce a diverging center only to obtain a preferred appearance. Sequential scales may include negative numbers when no central threshold is being encoded.

A sequential scale may span several hues when its ordered values remain
decodable. A signed scale can have cold and warm arms around a justified center.
Neither case requires a muddy low end or an arbitrary rainbow. If the adopted
reading task changes to sign-aware decoding, explicitly record the center and
any normalization change; keep source values unchanged and show zero on the
colorbar. Asymmetric zero-centered branches do not share one slope in raw units.

When comparing the same quantity across panels, define a named profile `continuous_scales` entry with `colormap`, `color_limits`, and optional `color_center`, then select it using `continuous_scale`. The fixed scale is checked against each panel's actual values; out-of-range values fail rather than being clipped. Use separate scales when units, quantities or the intended comparisons differ.

These source palettes have not been certified as color-vision-deficiency safe. Preserve labels, position, shapes or other distinctions where color alone is insufficient. Derived sequential ramps have monotonic relative luminance; this does not establish perceptual uniformity or equal contrast for every data range.

## Established and legacy alternatives

[All presets](../assets/palettes/all-presets.png) also includes `okabe-ito`, `viridis`, `cividis`, `inferno`, `blue-white-red`, and the older `easyviz-muted`. These remain available for explicit choices and existing settings. The [Okabe–Ito guide](https://jfly.uni-koeln.de/color/) and [Matplotlib documentation](https://matplotlib.org/stable/users/explain/colors/colormaps.html) identify those sources. `easyviz-muted` is an earlier project selection, not a literature-derived set.
