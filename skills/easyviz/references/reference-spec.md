# Reference reading and adopted specification

Keep image evidence separate from implementation decisions. This enables independent interpretation, purposeful adaptation, and a review against explicit requirements rather than an undefined resemblance.

## Reference reading

For each property, record the description, evidence state, evidence source, and any uncertainty. Use short tables or structured JSON; the structure below defines the meaning, not a mandatory serialization format.

| Evidence state | Meaning | Example |
| --- | --- | --- |
| `observed` | Directly visible in the image or explicitly stated in a supplied caption or methods excerpt. Name which source supports it. | “Six tick labels; the axis reads relative abundance.” |
| `inferred` | A plausible interpretation that needs verification before a scientific decision. | “The central mark may be a mean.” |
| `unknown` | Missing, unreadable, or not recoverable from the permitted inputs. | “The error-bar definition is not provided.” |

| Section | Capture |
| --- | --- |
| `reference` | Image identity, selected panel/region, pixel dimensions if available, accessible caption/method sources, and legibility limits. |
| `chart` | Chart family, coordinate system, axes, labels, units, linear or logarithmic scale when established, tick structure. |
| `encodings` | Mappings to position, color, size, shape, facet, and order; name required data meanings without inventing column names. |
| `layers` | Marks, summaries, intervals, fits, labels, annotations, legend, and their visible stacking order. |
| `appearance` | Category-color associations, approximate color values when measurable, line weights, marker types, and typography roles. |
| `geometry` | Approximate plot bounds, complete legend key/text bounds, reserved legend region where discernible, margins, and canvas proportions; preserve uncertainty from crops and image resolution. |
| `legends` | Categorical, quantitative-size, or continuous role; key and visible glyph heights relative to the plot, with estimation confidence; whether a legend serves this panel or several subpanels. |
| `statistics` | Only definitions supported by permitted evidence; separate visible statistical marks from their unknown calculations. |
| `open_items` | Unreadable text, ambiguous encodings, missing data requirements, and issues that affect scientific interpretation. |

Use normalized coordinates for approximate geometry when helpful: `(0, 0)` is the top-left and `(1, 1)` the bottom-right of the supplied image. Record a plot box as `[left, top, right, bottom]`. Distinguish observed pixel dimensions and relative text height from real mm, pt, and dpi. Cropped screenshots rarely establish physical dimensions or an exact font family.

## Adopted specification

The main Agent records the decisions used to render and review a panel. This can be a short `plot-spec.md` beside a machine-readable settings file; avoid duplicating contradictory values in two files.

| Field | Required content |
| --- | --- |
| `track` and `input_mode` | `create`, or `reproduce` with `image-data` / `author-code-assisted`. Record actual author-code access when present. |
| `inputs` | Source data, reference image, optional caption/methods, and any allowed prior plotting files; identify their origin. |
| `data_mapping` | Actual fields, meaning, units, experimental unit, selected data, transformations, aggregation, order, and missing-value treatment. |
| `statistical_layers` | Method, required design information, parameters, correction, sample size definition, uncertainty meaning, or an explicit unresolved/omitted status. |
| `requirements` | Adopted features, evidence basis, implementation decision, and priority. |
| `layout` | Actual width/height in mm, text roles in pt, available font, line widths, margins, format, and dpi where applicable. |
| `legend_layout` | Legend roles, placement, complete measured key/text bounds, reserved region, associated plot bounds, and quantitative mappings under [Legend layout](legend-layout.md). Record intentional adaptations and any adjustable proportion heuristics separately from requirements. |
| `colors` | Palette identity and resolved category-color mapping or continuous scale with its domain and center. |
| `intentional_differences` | User-requested changes and necessary adaptations relative to the reference, each with a reason. |
| `open_items` | Remaining questions and how they limit the current output. |

Use requirement priorities that support review:

| Priority | Examples | Acceptance |
| --- | --- | --- |
| `required` | Correct variables, scale, statistical meaning, agreed panel dimensions and font sizes, requested layer. | Must be satisfied or explicitly reported as unresolved. |
| `preferred` | Adopted palette, legend placement, mark shape, relative spacing. | Correct meaningful avoidable differences; report residual deviations. |
| `flexible` | Minor margin adjustments, tick density, label wrapping. | May change to fit the real data and final canvas. |

Match structure and semantic relationships when data differs. A new range, category count, or distribution does not need to resemble the reference's numbers. Do not change values, omit inconvenient observations, or distort scales to improve apparent similarity.

## Minimal decision example

| Property | Evidence | Adopted decision | Priority |
| --- | --- | --- | --- |
| Marks | Image visibly overlays points and boxes. | Draw both layers from the user's measurement and group fields. | `required` |
| Error bars | Caption and image do not establish their definition. | Leave unresolved; request the definition if this layer is necessary. | `required` if requested |
| Colors | Image appears to use blue and orange. | Use the user's explicit palette and save exact category mappings. | `preferred` |
| Canvas | Screenshot is wider than tall; physical size unknown. | Use the agreed 88 × 66 mm canvas and 8 pt text. | `required` |

This is an illustration of evidence handling, not a default choice of chart, colors, dimensions, or statistics.
