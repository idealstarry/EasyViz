# First reviewed Create delivery

Use this workflow for a new Create panel or substantial design refinement.
Resolve cosmetic choices and correct visible defects before presenting the
first finished result. Reproduce retains its adopted reference and settings.
Routine corrections need review of the affected result, not compulsory
alternative designs.

## Choose a scene and render

Establish the reading task, fields, units, independent observations and supported
summaries. Consequential unknowns may limit a statistical layer while descriptive
plotting proceeds. Fill cosmetic defaults from the project or task; the user
need not approve a palette or choose a renderer.

Open an applicable image from the [scenario design cards](design-cards.md).
Choose by category/series count, mark density, matrix shape and guide needs,
then inspect its mechanism and limits. A card's data or biological names do
not become assumptions about the user's table.

For supported prepared contracts, generate actual alternatives:

```sh
python /absolute/path/to/easyviz/scripts/create_candidates.py --describe-contract
python /absolute/path/to/easyviz/scripts/create_candidates.py \
  --data /absolute/path/to/project/prepared.csv \
  --spec /absolute/path/to/project/new-draft.json \
  --out /absolute/path/to/project/create-attempt-01 --new-draft --count 2
```

`--new-draft` explicitly declares a new eligible draft; use a fresh output
directory. The helper supports its stated distribution, complete heatmap, fixed-size
scatter and focused replicate contracts. Use a suitable focused recipe or custom
code when those contracts do not fit, with the same image review below. Record
the concrete reason, such as an unsupported layer or an accepted manual layout.
Refine an accepted panel with its original spec/script; declaring it new would
misstate eligibility. Focused replicate candidates require explicit mode and
uncertainty, and use their own layout/font contract rather than core profiles.

Explicit dimensions, fonts, profile settings, mappings and cosmetic choices
remain authoritative. Only omitted dimensions and design options are eligible
for scene suggestions. When using [First panel](quick-start.md) to seed the
spec, choose `--style-mode legacy` so automatically inserted crisp treatments
do not lock the new candidates to that treatment. Write user/project choices
explicitly; preserve accepted sizes during later refinements.

The default requests two rendered candidates, with fewer if explicit choices
lock the design; `--count 1` is appropriate when the
adopted style is clear, and three can resolve a meaningful design uncertainty.
The helper saves source snapshots, candidate specs/exports and `manifest.json`
with changes, rationale, eligible cards and limited technical review. It ensures
a PNG is rendered for inspection. `--no-render` produces proposals, not visual
evidence. Neither the manifest nor technical QA chooses an aesthetic winner.

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
