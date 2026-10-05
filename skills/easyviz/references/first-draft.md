# First reviewed Create delivery

Use this workflow for a new Create panel or substantial design refinement.
Resolve cosmetic choices and correct visible defects before presenting the
first finished result. Reproduce retains its adopted reference and settings.
Routine corrections need review of the affected result, not compulsory
alternative designs.

## Choose a design route and render

Establish the reading task, fields, units, independent observations and supported
summaries. Consequential unknowns may limit a statistical layer while descriptive
plotting proceeds. Fill cosmetic defaults from the project or task; the user
need not approve a palette or choose a renderer.

Decide reading task, organization and visual roles separately using
[Create design paths](design-space.md). Before the first render, use its short
[panel planning brief](design-space.md#plan-the-first-panel) to choose the
data-region shape and layer relationships from this task and a relevant
literature mechanism. A passed generic render does not establish that benefit. Then open relevant
[card mechanisms](design-cards.md), checking their feature conditions and limits.
A card's whole palette/layout is not a mandatory solution, and its data or
biological names do not become assumptions about the user's table.

For supported prepared contracts, the helper can render limited proposals:

```sh
python /absolute/path/to/easyviz/scripts/create_candidates.py --describe-contract
python /absolute/path/to/easyviz/scripts/create_candidates.py \
  --data /absolute/path/to/project/prepared.csv \
  --spec /absolute/path/to/project/new-draft.json \
  --out /absolute/path/to/project/create-attempt-01 --new-draft --count 1
```

`--new-draft` explicitly declares a new eligible draft; use a fresh output
directory. The helper supports its stated distribution, complete heatmap, fixed-size
scatter and focused replicate contracts. Use a suitable focused recipe or custom
code when contracts or available design routes do not fit, with the same image
review below. This includes a supported family whose proposals miss the chosen
role/organization. Record the concrete reason, not a generic desire for variety.
Encode chosen roles in supported spec options when necessary; a first candidate
index or `--count 1` does not mean the helper chose the best design for the task.
Refine an accepted panel with its original spec/script; declaring it new would
misstate eligibility. Focused replicate candidates require explicit mode and
uncertainty, and use their own layout/font contract rather than core profiles.

Explicit dimensions, fonts, profile settings, mappings and cosmetic choices
remain authoritative. Only omitted dimensions and design options are eligible
for scene suggestions. When using [First panel](quick-start.md) to seed the
spec, choose `--style-mode legacy` so automatically inserted crisp treatments
do not lock the new candidates to that treatment. Write user/project choices
explicitly; preserve accepted sizes during later refinements. If an existing
key's provenance is uncertain, do not guess that it was inserted by a helper
and remove it. Only known new seeds leave design choices deliberately omitted.

The default requests two rendered candidates, with fewer if explicit choices
lock or duplicate routes; fewer than the requested count is normal.
`--count 1` is appropriate when the
adopted style is clear, and three can resolve a meaningful design uncertainty.
The helper saves source snapshots, candidate specs/exports and `manifest.json`
with per-candidate `route_id`, `visual_role`, `changed_paths`,
`changed_facets_vs_candidate_01`, eligible cards and limited technical review;
`design_space.excluded_routes` records exclusion reasons. It ensures a PNG
is rendered for inspection. `--no-render` produces proposals, not visual
evidence. Neither the manifest nor technical QA chooses an aesthetic winner.
Inspect the proposals' actual differences and locks. Small width/fill/gap
changes can fix a specific defect but do not exhaust the design space; if they
miss the task, actively design an adapted spec or focused/custom solution.
Do not render extra outputs just to fill a quota or change scientific methods,
data selection, explicit settings or category identity for variety.

## Inspect, correct and record

Actually open the candidate images at their intended proportions, plus detail
views when needed. Compare the same reading task: category decoding, point/
summary crossings, contour hierarchy, category gaps, cell proportions, pale
marks and guide footprint. Prefer the treatment that makes the required
comparison clearer; state a visible tradeoff when neither wins clearly.

For crowded distributions, read the actual physical category lanes, mark outer
diameter and unresolved pairs in `qa.json`/`settings.json` `point_layout`.
For beeswarm, increase `point_max_offset_mm` only where neighboring groups and
axes leave room; a larger requested bound cannot enlarge a physically narrow lane.
Rebalance categorical spacing, summary thickness and `point_category_offset`
inside the adopted canvas, then check group association and point/summary
crossings in the new image. Preserve explicit marker area, fonts, canvas and
every source row; never jitter the numeric axis or relabel failed QA as passed.

For eligible omitted beeswarm geometry, the helper uses actual point outer
diameter, summary envelopes and available category pitch in at most three
bounded numerical stages: compact lane, available categorical region within
the same canvas, then adjust omitted summary width if necessary. Its body
cannot become narrower than the actual point outer diameter and must retain
the interior/stroke floor. The available-region stage can borrow a measured
spread deficit from omitted default fit padding, retaining at least 1.5 mm
canvas padding after text/guide measurement; it leaves numeric-axis geometry
unchanged. Actual font resolution is recorded because fallback glyph metrics
can alter available category space. Explicit margins and profiles skip this
automatic lane planning. Only when the body floor needs it, the third stage may
try the omitted default positive gap once at 0.2 pt instead of 0.3 pt. Explicit
geometry and gap remain fixed; `manifest.candidates[].distribution_lane_planning`
records trials. Infeasible packing remains invalid, and numerical fit does
not replace actual image review.

Use [Visual review](visual-review.md) and an independent
[Figure Reviewer](../../easyviz-figure-reviewer/SKILL.md) when available. Supply
current images, specification, caption and measurement evidence without priming
a desired verdict. If independence is unavailable, actually inspect the images
and label the review as self-review.

Correct concrete findings internally and render all affected formats. Allow
at most **three visual passes in total**, including the initial candidate
comparison; generating another alternative does not restart that budget.
Keep source observations, scientific meanings, agreed fonts and dimensions.
After the third pass, report unresolved findings rather than fabricate a pass.
If safe packing still fails, state the capacity limit; a split panel or another
reading task is a proposal, not a silent replacement of the requested plot.

Later feedback or an explicitly continued correction uses the accepted settings
and a separate followup record. Preserve the earlier artifacts and cumulative
pass count; do not relabel a fourth inspection as pass 3 or reset the first
delivery budget. Stage the current output with `--phase followup`, the cumulative
`--pass-number`, a concrete `--followup-reason` and an existing `--prior-review`
evidence path. The prior bytes are bound alongside current sources and exports.
The result explicitly sets `first_delivery_claim: false`; it validates recorded
history and current files, not the truth of a claimed count or image opening.

Stage a review for the selected current export directory:

```sh
python /absolute/path/to/easyviz/scripts/create_review.py --describe-spec
python /absolute/path/to/easyviz/scripts/create_review.py stage \
  --figure-dir /absolute/path/to/project/create-attempt-01/candidate-02 \
  --reading-task 'Compare the supplied measurements across the adopted groups' \
  --caption /absolute/path/to/project/caption.md \
  --pass-number 1
```

The default review folder is `create-review/pass-01` within that figure directory.
`packet.json` binds available sources and artifacts; `review.json` begins pending.
Complete the generated review using the actual `--describe-spec` contract:
current image path/hash, opening method, full-canvas/final-proportions views,
six design criteria and supplied external checks. One opening can cover both
views; do not claim an unavailable nominal-size preview or fabricate measurements.
Record real findings and corrections. Select the real chosen candidate;
`candidate-02` above is an example, not a preferred design. `--caption` is
optional when `caption.md` is already inside the figure directory.

```sh
python /absolute/path/to/easyviz/scripts/create_review.py check \
  --packet /absolute/path/to/project/create-attempt-01/candidate-02/create-review/pass-01/packet.json
```

A valid `ready` or `ready_with_notes` review with current artifact/source hashes
can yield `gate_status: recorded`. This verifies record completeness and version
binding. It cannot prove that images were opened, that review was independent,
or that a panel is beautiful. Changed exports require review of the new images;
do not reuse a stale record. An unresolved required check remains explicit.
Custom code can save real source paths/hashes, layout/typography and measured
exports in the metadata contract exposed by `--describe-spec`, alongside its
caption. Saved PDF/TIFF measurements must include the SHA-256 of the same
exported bytes; missing hashes remain `not_checked`. If supported evidence is
absent, retain the actual visual review and available measurements, mark those
checks `not_checked`, and report that
boundary. Do not invent metadata or native-renderer QA to obtain `recorded`.

Deliver the selected current exports, separate caption, runnable settings/code,
traceable data and review findings. A first-output quality claim needs held-out
tasks and the first finished delivery frozen before human aesthetic feedback;
an attractive known showcase or preference over weak defaults is insufficient.
