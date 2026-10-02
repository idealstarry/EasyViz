# v0.4.1 local Codex workflow evidence

This package preserves two forward trials performed by fresh local Codex agents:
one data-first create task and one unfamiliar image-plus-data reproduction task.
Both completed, both replayed from relocated copies, and both received an
independent final visual/export review. This is local-agent usability evidence
for these supplied synthetic tasks. There is no baseline condition and no
WorkBuddy effectiveness comparison.

## Accepted artifacts

| Trial | Accepted output | What the agent did |
|---|---|---|
| Create | [create/output/final/](create/output/final/) | Joined literal mouse IDs, averaged available measured technical reads within each of 36 mice, retained 12 mice per arm, and drew an unsmoothed boxplot with all mouse-level points. Ran two prespecified two-sided Mann–Whitney comparisons against Vehicle with Holm correction. |
| Reproduce | [reproduce/output/](reproduce/output/) | Read the reference in the implementing main agent, then wrote standalone plotting code for the unfamiliar synthetic 8 × 9 matrix, aligned condition strip, measured-only row means, diverging scale and missingness key. |

The reproduction used target source values, rather than estimating values from
reference pixels. Its standalone code adapted physical-font and full-canvas
export primitives from a captured EasyViz renderer; the existing heatmap and
annotated-heatmap contracts did not cover its complete layer/data structure.
No independent reference-reader agent was used. An independent final reviewer
later inspected the reference, rendered candidates and PDF previews.

Both panels export a full 120 × 90 mm canvas, Arial 8 pt, editable SVG text,
embedded PDF fonts and a 1417 × 1063 PNG at approximately 300 dpi. Scientific
narrative and method details are in separate captions. These tasks do not
establish that every v0.4.1 feature was used or validated.

## Preserved evidence

- [copy-manifest.json](copy-manifest.json) records SHA-256, sizes and original
  source roots for all 144 copied non-cache files: 87 create, 50 reproduce and
  7 independent-review files. All copied bytes match the original sources.
  The seven omitted files were a Matplotlib font cache and Python bytecode.
- Whole trial trees preserve inputs, exploratory records, captured helpers or
  instruction snapshots, accepted exports, attempts, self-review records and
  run/provenance documents. The original records were not rewritten.
- [independent-review/](independent-review/) contains the independent final
  JSON/Markdown reviews and the copied 96 dpi PDF preview images. Both statuses
  are `ready_with_notes`, with zero critical, major or minor findings and no
  required visual repairs. The notes reserve numerical correctness for the
  separate numerical checks.
- [reviewed-candidate-mapping.json](verification/reviewed-candidate-mapping.json)
  establishes that the reviewed attempt exports and accepted deliverable exports
  are byte-identical, despite their different historical directory names.

Original absolute source, interpreter, font, helper and output paths in the
trial documents are historical provenance. Use the package replay entry point
below instead of following those old temporary paths. Captured skill/resources
may predate the final v0.4.1 routing edits. The reproduction resource record
explicitly notes changes to the original `SKILL.md`, chart-library reference
and renderer after its snapshot. This package evaluates the captured trial
versions and completed artifacts; it does not silently substitute final runtime
code for those versions.

## Replay and numerical/export checks

[replay_and_verify.py](replay_and_verify.py) copies each archived trial root to a
new temporary project and invokes its root script. All replayed analysis/render
outputs and incidental caches remain in fresh `/private/tmp` directories;
verification reports and captured logs are saved beside the requested report.
It uses the
repository `.venv` Python by default, plus the installed Arial font and the
external libraries already recorded in the trial settings/provenance.

From the repository root, a new verification record can be made with:

```sh
.venv/bin/python evals/workflow-usability/v0.4.1/replay_and_verify.py \
  --report /private/tmp/easyviz-v041-new-verification/portable-replay.json
```

Choose a fresh evidence directory and, when specifying `--work-dir`, a new
nonexistent directory. Existing auxiliary logs/audits are also protected from
overwrite. Copy the complete trial root and invoke its root script;
preserved attempt scripts are evidence snapshots whose adjacent input paths are
not independently replayable. Replay regenerates analysis and render outputs,
but does not regenerate historical captions, reviews, delivery manifests or
the manually augmented create final settings.

The recorded [portable-replay.json](verification/portable-replay.json) passed
all **13/13** comparisons in a fresh relocated run:

- Create: exact plotted and analyzed tables, exact summary table, exact
  statistical results including both tests and Holm family, raw-to-mouse
  accounting, independent arithmetic/export verification, and exact PNG bytes.
- Reproduce: exact 72-coordinate table, means and specimen metadata tables,
  source-to-cell/bar audit values and export checks, and exact PNG bytes.

JSON numerical blocks are compared separately from absolute paths and historical
metadata. PNG byte equality was required; PDF/SVG byte equality across rerenders
was not required because serialization/metadata can differ. The existing trial
verifier independently recomputed mouse means, rank effects, asymptotic P values
and Holm correction from raw input. The create analysis has no effect confidence
intervals; boxes show observed quartiles and whiskers.

The shared [audit utility](../../workbuddy/v0.4.1/scripts/audit_outputs.py) was
also run with explicit artifact names. It alone reads its fixture/expected
resources internally; packaging and replay did not inspect them directly.

| Numerical/export audit | Result | Record |
|---|---:|---|
| Create accepted final | 15/15 checks passed | [create audit](verification/create-numeric-export-audit.json) |
| Reproduce accepted final | 17/17 checks passed | [reproduce audit](verification/reproduce-numeric-export-audit.json) |

The create audit expects `project/output`, while the original accepted files
live in `create/output/final`. A fresh audit-only project copied `create/input`
to `input`, the accepted final directory to `output`, and the root script beside
them. Every staged accepted-output byte matched its source. The original trial
was not renamed or changed; [create-audit-mapping.json](verification/create-audit-mapping.json)
records this temporary mapping. Reproduction was audited with
`output/figure-settings.json`, root `plot_panel.py` and
`reference-reading.json`, preserving those original names.

## Preserved failures and limits

- Create [attempt-01 failure](create/output/attempts/attempt-01/failure.json)
  stopped before rendering because a validation assertion expected the read
  state `failed`, whereas the supplied source used `instrument_failure`.
  The corrected attempt retained mouse `0008` using its one valid reading.
- Reproduce [attempt-01 failure](reproduce/output/attempt-01/failure.json)
  stopped before export because the colorbar label extended 0.0194 mm below
  the canvas. The accepted specification raised that element by 0.5 mm while
  retaining the requested font and canvas size.
- The original [reproduction audit](reproduce/numeric-export-audit.json)
  passed its numerical/export checks but failed three artifact-presence checks
  because canonical filenames differed. It remains byte-identical here.
  [Its original final audit](reproduce/numeric-export-audit-final.json) and the
  new explicit-name audit pass 17/17 checks. No duplicate canonical-name files
  were inserted into the original trial to hide the mismatch.

There are no unresolved numerical, replay, visual or export failures in the
accepted candidates. Input restrictions were instructions, not an operating
system isolation boundary. Successful relocation proves replay in the recorded
runtime and font environment; it does not guarantee arbitrary systems, datasets,
layers, scientific decisions or publication acceptance. Visual review and
numerical/export audit are complementary checks with different scopes.

## Accepted PNG hashes

| Trial | SHA-256 |
|---|---|
| Create | `6d8d7ce01e0c6c341c2a6b2cf39f35c7d36c92ceaa7d5d1a215ffe948941e40d` |
| Reproduce | `3d31b4ebbea4219139e19ab6d1e1776bafd945348feea57cf19c97a204f1e2be` |
