# Independent reference reading

This reading uses only the viewed `reference.png` and `reference-scope.md`. The image was inspected at its original raster resolution. No source data, provenance files, plotting code, templates, or external sources were inspected.

## Supplied scope facts

- The image is the Figure 3E scatter subcomponent, with neighboring pathway tables excluded.
- The scope note describes the horizontal quantity as a difference in medians between C3/C5, the vertical quantity as −log10(FDR), circle size as expression probability, and red/blue as directional groups.
- The 429 × 660 raster is a crop rendered at 216 dpi. It does not establish the original physical panel size or physical font sizes.

## Observed text and encodings

- A large, bold **E** sits at the upper-left edge of the crop, outside the plotting rectangle.
- The horizontal axis reads **Median difference between C5 and C3**.
- The vertical axis reads **Adjusted P-value (-log10)**, rotated counterclockwise along the left side. This wording is retained as printed; it differs in notation from the scope note's caption description.
- The horizontal ticks shown are **−4, −2, 0, 2**. The vertical ticks shown are **0, 2, 10, 20, 30, 40, 50**. The tick at 2 is close to the baseline and a horizontal dashed reference.
- A **Group** legend appears above the upper-right portion of the scatter. Its first row is a blue filled circle followed by **C3 down**; its second row is a red filled circle followed by **C3 up**.
- A separate **Expression probability** legend appears farther down the right side, with its heading broken into two lines. The entries are **0.00**, **0.50**, and **1.00**, in ascending order from top to bottom. The circle for 0.00 is visually negligible at this raster scale; 0.50 has a small filled dark circle, and 1.00 has a larger filled dark circle.
- Scatter marks are filled circles with visibly varying diameters. No clear contrasting marker outlines are visible. Blue and red are dark, somewhat muted colors. A narrow collection of light-gray circles is also visible near the horizontal center, although gray has no entry in the displayed Group legend.

## Observed layers and point arrangement

- The background is white.
- Thin dark left and bottom axes bound the scatter; top and right border lines are absent.
- One thin, light-gray horizontal dashed line crosses the full visible plotting width near the y = 2 tick.
- Two thin, light-gray vertical dashed lines sit close to either side of the x = 0 tick. They are visible from about the level corresponding to the low 40s on the vertical scale down toward the low-value cloud. Their exact numerical horizontal positions are not printed.
- The filled circles appear in front of the dashed references wherever they overlap.
- Blue circles occupy the left side and form the much taller cloud. A dense collection lies close to the bottom, especially between the −2 and 0 ticks. The blue cloud spreads farther left and becomes increasingly sparse at higher vertical positions. Several isolated blue circles extend above 30, with the highest one slightly above 50.
- Red circles occupy the right side. Their densest collection lies near the bottom, between approximately 0 and 2 on the horizontal axis. A sparser red extension rises toward the upper-right, reaching roughly the mid-teens on the vertical scale.
- Light-gray circles occupy a narrow central strip around x = 0, mostly in the low vertical range. They overlap the dense blue/red base near the two vertical dashed lines.
- Circle overlap is substantial in the low-value clouds, so the raster does not permit a reliable point count. Individual points become much easier to distinguish at higher vertical positions and near the outer edges.
- No point labels, connecting lines, error bars, continuous color scale, background grid, or plot title are visible.

## Relative geometry guides

These are approximate positions in this crop, not original manuscript dimensions.

- The plot's left axis is around x = 80 px, its bottom axis around y = 574 px, and its right extent around x = 377 px. The left axis begins around y = 98 px. The plot is a tall, narrow rectangle, approximately 297 px wide by 476 px high.
- The x = 0 tick is around x = 276 px, putting it about two-thirds of the way across the plot. The two vertical references are roughly 15 px apart and bracket that tick.
- The horizontal dashed reference is around y = 554 px, only about 20 px above the bottom axis.
- The Group legend starts around x = 239 px and y = 99 px. Its blue/red rows sit below the heading with fairly close vertical spacing.
- The size legend starts around x = 320 px and y = 303 px. Its example circles align in a vertical column around x = 342 px, with labels immediately to their right.
- The horizontal label sits below the ticks near the bottom of the crop. The rotated vertical label occupies the far-left margin. The panel letter is separated from the plot by a substantial blank upper margin.
- The upper-left blue outliers, the Group legend, and the size legend occupy otherwise open white space. The highest red marks remain well below the size legend.

## Typography observed

- Text is sans serif throughout, with ordinary, upright lettering in the axes and legends.
- Tick labels appear slightly smaller than the axis labels and legend headings.
- **E** is substantially larger and heavier than the other text.
- The Group labels are left aligned beside their markers. The two-line size-legend heading and its three numeric entries are also left aligned.
- The image does not establish a specific font family, font size in points, or original physical sizing.

## Inferred visual reading

- The opposed red and blue clouds, the central gray strip, and the paired vertical references give the scatter a two-sided volcano-like shape. This is a description of visible geometry, not a claim about a statistical procedure.
- Larger circles plausibly correspond to higher expression probability because the supplied scope states that circle size encodes that quantity and the displayed legend increases in size from 0.00 to 1.00. The exact radius/area mapping is not visible.

## Unknown or not established by this reference

- The exact numerical values of the two vertical dashed references, and whether the horizontal line encodes a particular significance cutoff.
- The rule assigning light-gray circles, and the numerical definitions of the red and blue directional groups.
- The exact subtraction convention, transformations, or upstream statistical method beyond the displayed horizontal wording and the supplied caption facts.
- The number of observations, exact coordinates, circle sizes, overlap order, or whether any marks are hidden by other marks.
- Exact colors, alpha values, line widths, dash lengths, font family, point sizes, full axis limits, or any original physical dimensions.
- Whether the 0.00 size-legend entry is deliberately rendered with zero radius or merely too small to resolve in this crop.

No statistical meaning beyond the supplied scope facts is assigned to the visible geometry or reference lines.
