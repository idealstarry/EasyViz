# Create design space

A chart family admits several useful designs. Choose a route from the reading
task and actual data, rather than treating one case, palette or "good" card as
the finished template. These are conditional design paths, not a promise that
every path is implemented by the candidate helper. Reproduce retains its adopted
reference; this resource adds no track.

## Make three separate decisions

1. **Reading task:** what should readers compare first—estimates, individual
   observations, distribution shape, an association, or matrix values/patterns?
   Establish units, groups and already adopted statistical layers.
2. **Organization:** overlay or separate related groups, choose orientation,
   category spacing and data-region aspect, and place guides where lookup is
   easiest. Respect adopted order, scales and assembly constraints.
3. **Visual roles:** decide which layer carries category identity and which
   attracts attention. Then choose its fill, contour, point treatment and hues.
   Category count limits decoding capacity; it does not choose the leading layer.

## Conditional routes within basic families

| Family and condition | Organization and visual roles |
| --- | --- |
| Bar: readers mainly compare one supplied quantity | A consistent filled neutral or single-hue bar can emphasize height; use an open summary when raw replicates or intervals need more separation. Neither treatment requires one hue per x label. |
| Bar: one adopted control or contrast is the focus | A deliberate accent with quieter remaining bars can direct that comparison. Decode the focus and retain every group and uncertainty; do not invent a control or ranking. |
| Grouped bar: readers compare real series within categories | Repeat series order and distinguish series on their bounded areas or outlines; balance within-category and between-category gaps. Long labels or different outcomes may justify horizontal/custom or aligned views when the adopted layout permits. |
| Scatter: a single population's relationship is the task | Neutral or one-hue observations can carry the relationship directly. Choose aspect and useful ticks from the numeric ranges; optional fits require an adopted model. |
| Scatter: classes must be identified in a shared point field | Distinguishable point hues, optionally decoded symbols for fixed-size observations, support identity. Check small marks and overlap on white; quantitative filled-area circles retain their shape/area contract. |
| Scatter: comparisons between crowded groups matter more than overlay | Separate aligned views with common adopted scales can reduce lookup and overlap when the layout permits. Retain all observations and the same fits/uncertainty; do not introduce density estimates merely for variety. |
| Box: median and quartiles should lead | Definite summary boundaries with categorical areas or restrained neutral boxes; raw points can occupy a neighboring lane if they obscure the summary. Side placement is conditional, not mandatory. |
| Box: individual observations or extremes should lead | Category-colored raw marks with quieter open summaries can make the observations primary. Keep quartiles/whiskers legible; choose shared or separate lanes from actual crossings. |
| Box: labeled category positions already decode identity | A consistent neutral or single-hue treatment can make numeric comparison easier. Meaningful project/category colors remain authoritative; a larger category count alone does not require this route. |
| Violin: adopted density shape is the main evidence | Let the body/contour communicate shape, with distinguishable but subordinate existing summaries and raw marks. Give density sufficient width without changing KDE or implying sample-size encoding. |
| Violin: adopted quartiles or median should lead | A quieter density body/contour with a definite inner summary can support summary reading. Categorical color may belong to the inner area; add no unadopted summary merely to resemble a card. |
| Violin: raw variation should lead while density remains useful | Distinct raw marks and a restrained silhouette can make observations primary; use an associated lane if crossings obscure values. All adopted layers remain present. |
| Heatmap: readers need direct value lookup | Where cells are large enough, explicit values and visible subordinate seams can support lookup. Set the data rectangle from matrix shape, labels and annotation capacity. |
| Heatmap: readers need the broad pattern | Let a readable ordered scale carry the pattern; use less cell framing for tiny dense cells and a proportionate guide. Eligible single- or multiple-hue sequential maps retain the same adopted bounds/normalization. |
| Heatmap: departures from an adopted meaningful center are the task | A decoded diverging treatment can support direction as well as magnitude. Preserve the center, limits, scale slopes and missing-state meaning; colors never establish a new center or normalization. |

Facets, orientation changes and alternate guides are design possibilities;
check the actual recipe contract or use custom code. Preserve all source rows,
units, statistics, KDE, quantitative mark areas, explicit category mappings,
fonts and dimensions. Do not switch chart family, summary, model, normalization
or selection solely to make variants look different.

## Use materials without becoming anchored

[Cards](design-cards.md) demonstrate local mechanisms such as summary clearance
or small-point contrast; their complete palettes and layouts need not travel
together. [Literature mechanisms](literature-style.md) supply other bounded
observations. Combine only the mechanisms that serve the selected route.

`create_candidates.py` generates a limited set of implementations, not all
allowed Create solutions. Inspect the current contract and each manifest's
actual changed paths. Fill, color or contour choices can test local hierarchy
or decoding; they do not establish exploration of the full reading task or
organization. Width/margin-only variants do not count as distinct helper
candidates. If available materials/proposals miss the needed
route, proactively adapt a spec, focused recipe or custom script within the
same scientific contract, then follow [First reviewed delivery](first-draft.md).

Choose one well-supported route when clear. Render an additional meaningful
alternative only to resolve a concrete uncertainty, not to reach a quota or
produce random colorful variants. All routes share the existing three-pass
actual-image review budget and new-draft eligibility rules.
