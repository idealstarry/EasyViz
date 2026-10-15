# Make the first Create result answer the question

Read this before a new multi-layer/custom panel, a related panel set, or a
substantial redesign. For a simple established chart, use the same decisions
briefly in the existing specification or working notes. No extra planning
document or compulsory alternatives are needed.

## Choose the evidence before the layout

State what the reader should compare, which source fields establish it, and
which detail is needed to interpret that comparison. A list of input columns
is not a figure plan. Choose a graphical view only when position, shape,
alignment or color exposes a comparison more directly than reading a table.

| Reading need | Useful design decision | Boundary |
| --- | --- | --- |
| Compare two supplied estimates across many named categories | Aligned points/intervals or paired marks can expose direction and size; use a shared key and baseline where meaningful. | Preserve adopted uncertainty, all categories and the exact comparison. Do not connect unpaired observations or invent intervals. |
| Inspect a large source list or full membership set | Retain the full table; let a main panel show the supported pattern, with an explicit selection or aggregation contract if needed. | Do not silently drop records. A requested complete matrix stays complete; propose a separate overview only when it helps the task. |
| Read a hierarchy with several annotation tracks | Allocate the hierarchy, tracks, labels and guides separately; measure their combined footprint before fine styling. | A tree's topology, rooting and quantitative branch lengths are scientific inputs, not cosmetic defaults. |
| Compare outcomes in related panels | Group panels by the scientific question and keep repeated category identity, type and decoding consistent. | Different units or ranges need explicit axes; a common visual style does not authorize a shared numerical scale. |

When a manuscript figure is requested, decide which panels support the same
question and which tables provide the complete lookup detail. Export the
agreed individual panels; assemble only when requested. Avoid building a main
figure from one panel per available file or adding a plot family for variety.
Keep narrative, interpretation and provenance in the separate caption.

## Allocate space to the primary comparison

In the existing brief/spec rationale, identify the primary mark region, the
supporting tracks, the longest labels and the guide footprint. Check both the
data region and the entire canvas at the agreed text size. A successful
collision check can still leave the primary evidence tiny beside a broad
annotation band or a large legend.

Choose dimensions for a new unspecified panel from its reading burden. Within
an adopted canvas, change margins, local gaps or guide placement before
requesting a size change. Keep observed values, adopted scales and text sizes.
Do not treat any literature ratio as a universal target. When the comparison
still requires excessive lookup, revisit its graphical organization before
trying another palette.

For an unfamiliar custom organization, inspect one relevant published figure
or an accessible local reference before the first finished output. Match the
reading burden, not just the subject: number of layers, label density,
quantitative encodings and required comparisons. Record what is observed,
what is an adaptation, and what is unknown. A Create design reference informs
decisions; it does not change the track to Reproduce or authorize copying data,
biological assumptions, axis breaks or scientific methods.
An already inspected, applicable example can supply this reference. If no
suitable reference is accessible, proceed with an explicit task-based design
and record that limitation; do not invent a source or block descriptive plotting.

## Circular hierarchies and annotation bands

Treat internal-node footprint, terminal extent, annotation radius/width,
label envelope and guide space as separate choices. Shrinking the whole tree
does not necessarily improve an overcrowded interior. Conversely, bringing
every branch close to the ring can erase the separation between layers.

- Preserve quantitative branch lengths through one declared scale when they
  encode distance. A topology-only view needs an explicit adopted display
  contract and caption; retain the distance view separately when required.
  Never apply nonlinear node compression as a cosmetic repair to a metric tree.
- Join track values by exact leaf IDs in the adopted order. Where adjacent
  intervals have the same category, a continuous run can remove repeated
  white seams. Retain exact class boundaries and every member's interval.
  Keep per-item boundaries when individual lookup requires them. Merge across
  the first/last boundary only for a true complete circle, never across a gap.
- Place crowded labels in balanced, order-preserving lanes rather than
  repeatedly pushing later labels in one direction. Use measured glyph
  envelopes and explicit movement limits; keep short identity leaders outside
  encoded tracks where feasible. A minimum angle alone does not prove that
  text, leaders or the circular seam are collision-free.
- Distinguish a focal mark from annotation categories. Test the whole palette
  on its actual thin bands and small points, with matching keys. Bright colors
  can help narrow tracks; brightness alone does not establish accessibility or
  justify coloring all background branches.

Use [radial layout tools](radial-layout.md) for exact interval runs, bounded
label separation and physical geometry diagnostics in custom code. They do
not infer a tree, choose scientific branch coordinates or certify aesthetics.

## Review before showing the first finished result

Use the existing three-pass [first-delivery review](first-draft.md); these are
decisions to make inside that budget, not another review loop. Open the actual
whole image before magnified details, and ask:

1. Is the intended comparison visible before reading the caption? Can the
   reader trace a mark to its category without repeatedly scanning a table?
2. Do supporting tracks, keys or whitespace dominate the main evidence? Check
   local label clusters and leader crossings, not just average spacing.
3. Does color explain the variable it claims to explain? Are class boundaries,
   summaries and uncertainty endpoints still clear at final proportions?

Correct the most important visible defect, then re-render and inspect the
affected formats. Do not present a known structural imbalance as a finished
first version merely because the user called it an initial draft. A draft may
have provisional assembly or an explicitly unresolved scientific input while
still meeting the adopted visual contract.

Later human feedback remains a followup in the cumulative history. Learning
from an improved known example supports these conditional decisions; it is
not evidence that unfamiliar first outputs or every Agent now improve.
