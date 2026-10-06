# Create design space

A chart family admits several useful designs. Choose a route from the reading
task and actual data, rather than treating one case, palette or "good" card as
the finished template. These are conditional design paths, not a promise that
every path is implemented by the candidate helper. Reproduce retains its adopted
reference; this resource adds no track.

## Make three separate decisions

1. **Reading task:** what should readers compare first—estimates, individual
   observations, distribution shape, an association, or matrix values/patterns?
   State the scientific question, the comparison this panel enables and why it is needed;
   establish units, groups and already adopted statistical layers. A numeric
   pair supplies coordinates, not a reason to draw an association panel.
2. **Organization:** overlay or separate related groups, choose orientation,
   category spacing and data-region aspect, and place guides where lookup is
   easiest. Respect adopted order, scales and assembly constraints.
3. **Visual roles:** decide which layer carries category identity and which
   attracts attention. Then choose its fill, contour, point treatment and hues.
   Category count limits decoding capacity; it does not choose the leading layer.

## Plan the first panel

Write a short internal design brief before rendering; a few lines in working
notes or the spec rationale suffice. Resolve supported cosmetic choices without
asking the user to approve a layout. Use source context to settle the question;
clarify only scientific ambiguity that would change its meaning.

| Brief item | Concrete decision |
| --- | --- |
| Purpose | State the comparison readers need to make and why this panel is needed. Identify the adopted measurement, experimental unit and summaries. |
| Reading burden | Count actual categories, series within each category, observations per group and long labels. Inspect value ranges, uncertainty extent and adopted density layers. Keep these planning counts outside the image unless needed for decoding. |
| Geometry | Plan the data-region width and height, category pitch, summary/body width, raw-point span and guide footprint at the adopted font size. Distinguish within-group, between-group and exterior gaps. Canvas aspect alone does not describe this geometry. |
| Hierarchy | Decide which of raw observations, summary or density should lead. Give the other adopted layers distinct, readable boundaries; state where crossings or overly tall/slender marks are likely. |
| Comparable mechanism | Choose a literature/card mechanism with a similar reading burden. Record the observed feature and the proposed adaptation separately; sharing a palette does not establish comparable grouping or proportions. |
| Expected benefit | Name an observable gain, such as less disconnected category spacing, easier interval lookup or a clearer median. Check that gain on actual final-size exports before accepting it. |

For vertical categorical plots, relate the measured data width to the category
pitch and the visible summary width. A narrow body separated by several body
widths can make a small comparison look disconnected; extending the numeric
axis vertically can make bars look slender without adding evidence. For grouped
bars, distinguish the series gap within a group from the gap between groups,
including the visible strokes. For box/violin, choose summary and raw-lane
capacity together, rather than shrinking summaries until points fit.

The [observed literature geometry](literature-style.md#geometry-observations)
offers conditional analogues for one pair, repeated double bars and multiple
distributions. Use its mechanism to propose a data rectangle; do not assign its
ratio to every chart. Preserve adopted dimensions, fonts, scale, statistics and
all observations. An unadopted new-canvas default can be chosen for this task;
an explicit canvas stays fixed. Check resulting exterior whitespace as well as
the data rectangle.

### Retrieve a local mechanism from actual burden

`scripts/design_mechanisms.py --describe-contract` exposes a small stdlib-only
catalog keyed by reading task, leading layer and observed chart burden. To
inspect applicability for a custom/focused route, pass `--features` with actual
counts and `--intent` with the adopted purpose. Unknown burden remains unresolved;
a selected `mechanism_id` must actually apply. Results retain source-panel
observations separately from proposed adaptations and counterexamples.

The new-draft candidate helper runs this retrieval automatically. Use its
applicable mechanisms as local evidence for planning, not a requirement to
copy a paper's complete geometry, palette or analysis. A strong mechanism may
lead to custom code when the helper cannot express its organization. Inspect
the excluded routes and concrete reasons rather than accepting the first index.

## Conditional routes within basic families

| Family and condition | Organization and visual roles |
| --- | --- |
| Bar: readers mainly compare one supplied quantity | A consistent filled neutral or single-hue bar can emphasize height; use an open summary when raw replicates or intervals need more separation. Neither treatment requires one hue per x label. |
| Bar: one adopted control or contrast is the focus | A deliberate accent with quieter remaining bars can direct that comparison. Decode the focus and retain every group and uncertainty; do not invent a control or ranking. |
| Grouped bar: readers compare real series within categories | Repeat series order and distinguish series on their bounded areas or outlines; balance within-category and between-category gaps. Long labels or different outcomes may justify horizontal/custom or aligned views when the adopted layout permits. |
| Scatter: a scientifically relevant relationship is the task | Neutral or one-hue observations can carry the relationship directly. Establish why reading that relationship matters before choosing aspect and useful ticks; optional fits require an adopted model. |
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

For before/after data, decide whether the task concerns the relationship across
occasions or verified within-unit change. Use the [Create mapping guidance](create.md)
to choose a scatter, connected paired view or explicit change view accordingly;
do not add a family to a panel set merely to make it varied.

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
