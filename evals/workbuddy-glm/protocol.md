# WorkBuddy unseen interval task

Prepared on 2026-10-02, Asia/Shanghai, before examining either arm's output.
The intended comparison is the same WorkBuddy model on the same unfamiliar
source data, with and without a local EasyViz snapshot. Actual model labels,
completion states and effort must be taken from `launch-observations.json`,
not assumed from this plan.

## Matched inputs

Both arms receive the same 11-row synthetic CSV (SHA-256
`b9d1c0eef736267344770a2f42bf2033eda1073e538ce352829ed93317f98d99`).
The unfamiliar schema maps Readout, Preparation batch, Prepared ratio,
Lower 95 and Upper 95 to seven long labels, two batches and supplied asymmetric
intervals. Three of the fourteen possible label/batch combinations are absent.
They remain absent; neither a missing observation nor an unknown sample size
can be replaced with zero.

The shared request requires a horizontal interval panel, first-occurrence
category order, stable decoded batch colors, a logarithmic x axis and reference
at 1. Supplied intervals containing 1 use hollow circles; the others use filled
circles. This is a reference-overlap encoding without a new significance claim.
Independent n and interval construction are unknown. No estimation, weighting,
imputation, recomputation or new test is permitted.

Both panels use 140 × 100 mm, Arial 8 pt, 300 dpi, full-canvas PDF/SVG/PNG and
editable SVG text. Titles, subtitles and explanatory in-image footnotes are
omitted. An English caption explains the synthetic data, supplied intervals,
unknown n/methods, missing combinations and hollow-circle meaning. Runnable
code, actual settings, plotting data and real checks are requested. Each model
may make at most two evidence-based visual revisions, with no evaluator help
after submission. Exact requests and input/snapshot hashes are preserved when
freezing the completed runs.

The direct-code task is instructed to avoid EasyViz and other test outputs.
The EasyViz task is instructed to use its supplied local skill and necessary
resources, avoiding the baseline and previous evaluation conclusions. Both
receive the same existing scientific Python runtime. These are access
instructions rather than an operating-system sandbox.

## Independent assessment

Freeze original outputs before evaluating them. Audit the actual exported
coordinates, eleven point/interval pairs, three absent combinations, asymmetric
endpoints, logarithmic scale, overlap states, color decoding, source values,
physical canvas, fonts and editable text. Rerun in a relocated temporary copy.
Separate model self-reports from independently checked facts; preserve failures.

Give a fresh visual reviewer only anonymous A/B panels and their captions.
Use the same final-size screen proxy for both and inspect the exported images.
Compare legibility, mark visibility, interval separation, label/guide decoding,
whitespace balance and visual hierarchy. Report specific differences and a
conditional preference, or a tie, rather than treating successful execution
as proof of better aesthetics. A screen proxy does not certify print quality.
Withhold the arm mapping until the review has been saved.

This pair uses a newer EasyViz snapshot and a different chart from the earlier
Deepseek dot task. It supports a within-pair comparison only; it cannot rank
GLM against Deepseek. Shared app memory, hidden prompts, sampling and backend
routing are uncontrolled. One run per arm cannot establish general novice
benefit, a universal model advantage or journal acceptance.
