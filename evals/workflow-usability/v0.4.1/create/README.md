# Finished create task

Final exports and supporting records are in `output/final/`.
The selected panel is an unsmoothed boxplot with all 36 mouse-level points.
All source inputs were copied only from the specified raw-data directory into
`input/data/`. No neighboring requests, outputs, conditions, expected results,
old conversations, network resources, or repository files were used.

The reusable EasyViz helpers were copied and SHA-256 recorded in
`helper_snapshot/snapshot-manifest.json` before execution. The used renderer
identifies itself as v0.4.1. The recorded Python is 3.12.2, NumPy 2.5.3 and SciPy
1.18.1. Replay uses the supplied project runtime and captured helpers:

```sh
/Users/starry/Desktop/EasyViz/.venv/bin/python /private/tmp/easyviz-v041-forward-create/run_analysis_plot.py --run-dir /private/tmp/easyviz-v041-forward-create/output/replay-01
/Users/starry/Desktop/EasyViz/.venv/bin/python /private/tmp/easyviz-v041-forward-create/verify_outputs.py --run-dir /private/tmp/easyviz-v041-forward-create/output/replay-01
```

Choose a fresh `--run-dir`; existing attempts are preserved. The copied final
`plotting_data.csv` is byte-identical to the table actually passed to both the
analysis and renderer (SHA-256
`948fed12d6569385eb4d53fa78f12673f441be5a08ede8a5076343ca74156a5b`).
The canonical executed source remains in `output/attempts/attempt-02/`.
The complete initial inspection and its unused generic proposals are retained
in `exploration-01/`; the data dictionary resolved their scientific ambiguities.
Only the three question-specific directions in `adopted-spec.md` were proposed.

Used resources: current `skills/easyviz/SKILL.md`; linked create,
data-exploration, quick-start, statistical-analysis, panel-layout, palettes,
visual-review, collision-placement, and chart-library references; corresponding
captured inspect, analyze, draft and render helpers and render dependencies.
The supporting standard runtime libraries used for verification were Python
CSV/Decimal/statistics/math/XML, Pillow, pypdf, and PyMuPDF. No fixtures,
examples, evaluation targets, expected answers, or test suites were consulted.
