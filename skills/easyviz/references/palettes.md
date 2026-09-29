# Palette selection

Use the [literature color card](../assets/palettes/preview.png) to compare candidates, then inspect them on the actual panel. A publication source establishes provenance, not aesthetic suitability. Prefer coordinated lightness and saturation on white; avoid a dark low-value field or a muted gray-purple scheme as a habitual default. Preserve the user's chosen palette and existing group identities unless a recoloring is requested. In reproduce, use the adopted reference palette or the user's requested override.

The colors live in [palettes.json](../assets/palettes/palettes.json), and compatible combinations in [families.json](../assets/palettes/families.json). Record the preset and actual label-to-color mapping in output settings. A paper's biological labels do not transfer to new data when its colors are reused.

## Literature choices

| Preset | Meaning and preferred use | Provenance |
| --- | --- | --- |
| `notch2-balanced` | Blue, amber, teal, pink. Selected by the user for the cell-atlas example; evaluate again for other contexts. | Four exact embedded legend colors selected from the same Figure 2b, including I2/I1/I4/M1. |
| `notch2-blue` | Blue sequential scale with a visible light endpoint for borderless marks. | EasyViz 20–100% white-to-I2-blue interpolation; not an author gradient. |
| `somerville-bright` | Sky, coral, teal, lavender; optional gold and turquoise. Start with the first four for compact categorical panels. | Selected/reordered PDF colors from Somerville et al. (2024), Figs. 1B and 2B. |
| `notch2-bright` | Teal, blue, amber, orange for four groups. Retain direct labels because the warm pair is closer. | Selected/reordered embedded legend colors from Cruz Tleugabulova et al. (2024), Fig. 2b. |
| `somerville-sky` | Light-to-bright blue for proportions or other ordered values. | EasyViz white-to-blue interpolation from Fig. 2A's observed blue endpoint. |
| `somerville-coral` | Light-to-coral for a warm quantitative matrix; pair with blue marginal bars. | EasyViz interpolation from Fig. 1B's observed coral endpoint. |
| `notch2-teal` | Light-to-jade for ordered values. | EasyViz interpolation from Fig. 2b's observed I4 teal. |
| `somerville-blue-coral` | Blue–white–coral for signed deviations with an explicitly meaningful center. | New EasyViz gradient using Fig. 1B categorical endpoints. |

Families are candidate combinations, not universal defaults. `notch2-balanced` pairs the selected four-category set with a blue scale; `somerville-fresh` and `notch2-fresh` remain alternatives. Check filled areas, small marks and legend keys together under the same outline policy. Do not combine all available hues in one panel or turn a categorical palette into a rainbow heatmap.

The core renderer's technical fallbacks are `somerville-bright` and `somerville-sky` when no explicit choices are supplied. They are not evidence of user approval or suitability; supply the selected palette explicitly. Always review actual marks, not just swatches.

## Source precision

- [Somerville et al., Nature Communications 2024](https://www.nature.com/articles/s41467-024-52687-7): rendered figures were inspected and flat PDF vector-fill RGB values were converted to 8-bit HEX. The six-color selection spans two panels; it is an EasyViz selection, not an author-provided palette product.
- [Cruz Tleugabulova et al., Nature Communications 2024](https://www.nature.com/articles/s41467-024-53700-9): RGB values were extracted from uniform embedded legend swatches and checked against the actual rendered figure. These values are exact for those PDF pixels; pre-publication author constants remain unknown.

[Source records](../assets/palettes/sources.json) retain figure/page locations, file hashes and extraction details. Continuous ramps explicitly mix sampled endpoints with white; they are adaptations, not recovered author colormaps. Full article figures are not bundled with the palette collection.

## Mapping and readability

Categorical colors must not cycle when capacity is exceeded. Supply an explicitly reviewed larger mapping, use redundant encodings, or arrange separate panels. Keep group-color assignments stable across plots. If pale fills need outlines, apply one coherent outline policy to comparable marks and matching legend symbols, or choose stronger fills/direct labels; do not outline only one mark type by accident.

For continuous data, record limits and normalization. Recoloring must preserve the established value scale, zero, missing-value meaning and range unless a scientific change is requested. Do not introduce a diverging center only to obtain a preferred appearance. Sequential scales may include negative numbers when no central threshold is being encoded.

These source palettes have not been certified as color-vision-deficiency safe. Preserve labels, position, shapes or other distinctions where color alone is insufficient. Derived sequential ramps have monotonic relative luminance; this does not establish perceptual uniformity or equal contrast for every data range.

## Established and legacy alternatives

[All presets](../assets/palettes/all-presets.png) also includes `okabe-ito`, `viridis`, `cividis`, `inferno`, `blue-white-red`, and the older `easyviz-muted`. These remain available for explicit choices and existing settings. The [Okabe–Ito guide](https://jfly.uni-koeln.de/color/) and [Matplotlib documentation](https://matplotlib.org/stable/users/explain/colors/colormaps.html) identify those sources. `easyviz-muted` is an earlier project selection, not a literature-derived set.
