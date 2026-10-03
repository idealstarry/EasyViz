The selected panel is panel.pdf / panel.svg / panel.png, at 110 × 85 mm with Arial 8 pt. caption.md is separate; the PNG is 1299 × 1004 pixels at 300 dpi. Place vector outputs at their recorded physical size. PDF embeds Arial; SVG keeps editable text and references Arial.

Use the existing project plotting interpreter to rerender into a fresh subdirectory:

    /Users/starry/Desktop/EasyViz/.venv/bin/python -B /Users/starry/Desktop/EasyViz/evals/create-literature-refresh/forward-test/output/make_figure.py --out rerun-01

The wrapper uses the preserved source.csv and preview-request.json, then calls the specified skill helper. The initial exact helper and implementation hashes remain in previews/manifest.json and first-use-selection.json; if the skill changes, a new run may differ and needs fresh image review. The launcher is deliberately dependent on the existing skill/runtime, rather than a vendored library.

first-use-interpretation-review-log.md and independent-review.md preserve actual first-use reasoning and image findings. independent-numeric-export-checks.json contains independently recomputed descriptions and measured export dimensions/font records. Descriptive quantities are in descriptive-summary.json. No test was requested or run.
