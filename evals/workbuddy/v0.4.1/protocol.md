# WorkBuddy v0.4.1 external Agent pilot protocol

This evaluates two **synthetic** tasks in the existing create and reproduce
tracks. It is a bounded usability pilot, not proof of general model superiority,
novice usability, journal acceptance, or physical print quality.

## Matched tasks

| Task | Unfamiliar input | Main failure opportunities |
| --- | --- | --- |
| create | 36 independent mice, 72 technical reads (one failed), shuffled literal-ID lookup, historical pilot and QC/log distractors; no selected plot | Wrong joins, pooled historical data, pseudoreplication, missing-as-zero, raw-point crowding, unjustified statistics |
| reproduce | New names and values in an 8 × 9 target matrix; only a synthetic reference PNG and user tables | Premature template choice, layer omission/misalignment, wrong ordering, zero/missing conflation, reference-value substitution, marginal-mean errors |

The reproduction reference was authored specifically for this pilot with
Matplotlib, independently of target values. Its generator and evaluator truth
are not exposed inside the WorkBuddy projects. This is not a literature case.

The two task bodies under `prompts/` are frozen and identical across arms. Only
the scope wrapper and explicitly permitted skill snapshot differ. Every arm
permits the same installed Python runtime and generic libraries. The requested
format, full canvas, font, and visual-correction budget are identical: one initial
render and at most two Agent-directed visual corrections. The Agent can choose
analysis/chart details in create; the reference governs the reproduce layers.

## Arms and staging

- **baseline:** direct local Agent coding; no EasyViz or other run outputs.
- **v040:** frozen `git archive v0.4.0 skills`, retaining exact snapshot hashes.
- **v041:** a copy of the final working-tree skill, frozen before that arm begins.

Stage with `scripts/stage_conditions.py --condition CONDITION`. It refuses to
overwrite a previous project. The default run root is
`/private/tmp/easyviz-v041-workbuddy`. Each arm/task is a separate fresh WorkBuddy
task and working directory. Paste that project's `request.txt` as a single user
request. Keep complete task text and input hashes. Do not add corrective advice
to one arm without recording it and either matching the intervention or treating
that result as a separately assisted run. Retain unfinished, failed, or interrupted
runs and any repeat attempt; do not select only the best run.

These are instructed access boundaries, **not** an OS sandbox. A common app
account/session, global memory, hidden prompts, backend routing, and accidental
prior exposure cannot be fully excluded. Record observed accesses and violations.
The baseline wrapper explicitly forbids even a globally installed EasyViz.

## Actual UI evidence to capture

For every run record start/end timestamps, WorkBuddy app version, exact displayed
model label (including any change), task title or local history identity, complete
submitted prompt hash, output folder, observed skill/code/image reads, any
intervention, displayed consumption with the app's units, and completion state.
The displayed model label identifies the UI selection, not independently verified
backend routing. Preserve available actual task transcript/exports and screenshots
or accessibility snapshots with provenance. Do not manufacture a transcript from
the evaluator's recollection. Native UI failures belong in the limitations; a
command finishing is not proof the Agent actually inspected an image.

If time is limited, prioritize a matched baseline/v041 pair for each task. A v040
arm is useful for isolating the new patch's contribution but is optional. Keep the
same model within each matched comparison; do not rank models across tasks or
different snapshots. Run ordering and any timing gaps must be reported. Repeat
runs after repairs are an iteration demonstration, not untouched first-pass evidence.

## Evaluation and iteration

Run `scripts/audit_outputs.py --project PROJECT --task create|reproduce --report
REPORT` with the shared runtime. It verifies input hashes, exact target tables,
sample counts/technical means, missing states/marginal means, physical PDF/SVG/PNG
dimensions, editable SVG text, direct PDF text fonts/sizes, and required artifacts.
The audit cannot prove marks use the audited tables, method correctness, semantic
layer alignment, or aesthetics. Inspect actual code for joins, analysis units,
uncertainty definitions, correction family, raw point/layer usage, ordering, and
transformations. Numerical/evidence failures are P1; do not offset them with
appearance scores. Rerun portability is a separate actually executed check.

Matched WorkBuddy runs retain the canonical requested artifact names. A separately
identified runner that produces different valid artifact names can declare them
with `--settings output/figure-settings.json --script plot_panel.py --reading
reference-reading.json`. Overrides must be relative paths inside that run's
project, including their resolved symlink targets. The report records requested
and resolved paths and existence; it does not certify settings, code, or reading
semantics. Save this as a new audit report and retain any original naming failure.

For image review run `scripts/prepare_blind.py --destination NEW_PATH` after the
chosen arms finish. Pass a fresh reviewer only one task folder and its
`review-request.txt`, without identity mapping, source code, logs, timings, or
numeric results. The script copies only actual PNG bytes and uses randomized
candidate names. Its sibling identity key is evaluator-only. A reviewer who
already knows identities may still review, but describe that as unblinded.

Score hierarchy, spacing/alignment, label readability, color/guide clarity, and
(reproduce only) visible reference-layer fidelity from 0–4 with concrete image
evidence. Ties are allowed. Keep the original review before revealing identities;
then combine it with scientific/export auditing. This rubric is a reviewer
judgment, not a calibrated aesthetic measurement. Do not call an Agent independent
or blinded solely because files were anonymized; record its actual context.

Use observed failures to improve portable guidance/scripts, then freeze the next
snapshot and run a fresh assisted arm. Preserve all original outputs. Report
repairs and iteration order, limited sample size, and any direct-code visual win.
