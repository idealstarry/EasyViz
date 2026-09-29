# Independent EasyViz create forward test

Completed the user request in this folder. Selected manuscript outputs: `panel.pdf`, `panel.svg`, `panel.png`. Supporting files: `caption.md`, executable `plot.py`, `settings.json`, resolved `figure-settings.json`, untouched `source.csv`, `plotting_data.csv`, `summary.csv`, `pairing_audit.csv`, and `missing_pairs.csv`. Review evidence: `review.md`, `verification.json`, `layout-checks.json`, PDF/SVG raster renders, and a same-size box-and-points design comparison.

## Inputs and resource use

Task information was limited to the assigned `request.md` and `source.csv`, applicable repository `AGENTS.md`, and packaged EasyViz resources. No repository tests, existing evaluation outputs, development examples, earlier agent records, author code, GitHub or external websites were consulted. No repository files were changed and no plugins were installed.

Read and used these packaged resources under `/Users/starry/Desktop/EasyViz/dist/easyviz/skills/`:

- `easyviz/SKILL.md`: select create track, source integrity, fixed-size exports, separate caption and reproducible deliverables.
- `easyviz/references/create.md`: visual mapping, statistics, candidate comparison and equivalent traceability for custom implementation.
- `easyviz/references/panel-layout.md`: 180 × 125 mm full canvas, 8 pt typography, actual font checking, vector/raster export and grid placement.
- `easyviz/references/legend-layout.md`: complete key/text bounds, reserved region, data-region proportions and explicit borderless keys.
- `easyviz/references/palettes.md`, `easyviz/assets/palettes/palettes.json`, and visually inspected `easyviz/assets/palettes/preview.png`: choose the requested blue/amber combination, Control #2581B9 and Treatment #DF9A3C.
- `easyviz/references/chart-library.md`: core distribution chart supports basic box/violin with points, but the required paired derivation, week facets and custom median/IQR composition require an explicit custom implementation.
- `easyviz/references/design-decisions.md`: the paired-change pattern informed individual points plus median/IQR; it did not provide data, executable code or an answer for this source.
- `easyviz/references/visual-review.md` and `easyviz-figure-reviewer/SKILL.md`: actual-render inspection, evidence-separated checks and recorded self-review.
- Also opened `easyviz-reference-reader/SKILL.md` while checking helper roles; no reference image was supplied, so that skill was not applied.

No bundled case scripts or examples were opened. The implementation was written for the observed source schema, per the packaged custom-script option.

## Consequential choices

The independent unit is the participant. Change is follow-up minus the same donor's week-0 value for the same protein and arm. All baseline records exist. Available pairs were retained independently by visit: 11 donors per arm/protein at week 4 and 10 at week 12. Missing visits were recorded, not fabricated and not used to exclude otherwise valid pairs at another visit. There are 252 plotted changes and 36 explicitly absent expected follow-up protein measurements.

The chosen design has two aligned week facets, six protein rows in source order, two consistent arm subrows, a shared linear horizontal axis with meaningful zero, faint individual points and prominent median/IQR. IQR represents participant spread; no inferential claim or confidence interval was added. No upstream normalization, model fitting or hypothesis tests were performed. A conventional box-and-points design at the same size was rendered and inspected as a comparison; selected design reduces whisker clutter while retaining raw spread. Week labels are necessary facet labels, not an overall title.

All typography uses actual installed Arial 8 pt. All filled marks and categorical keys are borderless. The selected PDF and SVG have exact physical canvas dimensions; PNG has nearest-pixel dimensions at 300 dpi. The SVG preserves editable text and references Arial rather than embedding it; PDF embeds ArialMT.

## Checks and limitations

Actual PNGs and PDF/SVG rasterizations were opened and inspected. Dimensions, PDF font embedding, extracted PDF text sizes, SVG text styles, PNG resolution metadata, clipping, tick collisions and legend geometry were checked. All pair changes and all median/Q1/Q3 summaries were recomputed through a separate standard-library code path; maximum absolute discrepancy was 4.44e-16. See `verification.json` and `review.md` for exact scope.

No unresolved blocker. Independent reviewer delegation was attempted but unavailable because the session reached its agent-thread limit; visual and numerical checks are explicitly self-review. Startup font-cache warnings were addressed by using a local Matplotlib cache. An initial custom-script use of Matplotlib's deprecated `vert` argument was replaced with `orientation` and rerun. These are environment/custom-code issues, not observed packaged-renderer failures. This trial exercises EasyViz's guidance and custom-script route; it does not validate the core renderer or unrelated chart families. Missingness means the contributing participant set differs between visits; that limitation is disclosed in the caption. Close points can overlap, and this distribution view does not preserve visible individual trajectories.

## Re-run

From this directory, run:

```sh
/Users/starry/Desktop/EasyViz/.venv/bin/python plot.py
```

Alternatively, use Python with pandas, NumPy, Matplotlib and Pillow installed. Arial must be available. `plot.py --out /path/to/output` writes a new output folder without changing the source. Package code is not needed to rerun the delivered script. Exact installed versions are saved in `figure-settings.json`.
