# Forward-use result

Completed the realistic user request with the inherited Codex model for this run. This is not a test of an external Chinese model.

## Deliverables

`panel.pdf`, `panel.svg`, `panel.png`, separate `caption.md`, unchanged `prepared.csv`, adopted `plot.json`, resolved `settings.json`, `plotting-data.csv`, runnable `reproduce.py`, included renderer/helpers/palette, instructions in `README.md`, and verification in `checks.json`, `qa.json`, `review.md`, `provenance.json`. All are under `/tmp/easyviz-forward-output`.

## Resources and helpers used

EasyViz SKILL.md; create, quick-start, chart-library, panel-layout, legend-layout, palettes, dot-states, and visual-review references; literature palette swatch image and palette catalog. Used `draft_spec.py` and core `render.py` with its `legend_layout.py`, `auto_layout.py`, `figure_profile.py` validation, and `annotation_review.py`. The supplied table fits the basic dotplot contract. An independent subagent used the directed EasyViz Figure Reviewer skill and inspected the actual PNG.

## Iterations and failures

The default Python and bundled workspace Python lacked Matplotlib. Used the already installed local EasyViz scientific environment, without installation or network. One plotting specification and one plot render were sufficient; no plot correction was required. A later export verifier falsely rejected grey legend circles under an overly strict neutral-RGB tolerance because PDF conversion gives RGB differences of approximately 0.00009. Relaxing that detector to 0.001 resolved the verifier issue; no visual output or quantitative mapping was changed. Included-bundle reproduction also passed. One image review pass, followed by a caption-completeness check, was performed.

## Final checks

- All 24 source rows and both observed zeros retained; category orders match input.
- All dots use `area = fraction × 90 pt²` with size maximum 1; observed zeros retain quantitative area 0 and use separate grey ticks.
- Actual PDF paths confirm 22 positive dots and size legend keys at 0.25, 0.5 and 1 use the same proportional mapping; borderless fill policy consistent.
- Actual PDF dot colors match the selected sequential blue map over −0.22 to 1.66.
- PDF/SVG are 120 × 90 mm; PNG is 1417 × 1063 px at 300 dpi, with normal pixel-rounding tolerance.
- PDF embeds Arial and all actual text spans are 8 pt. SVG preserves text and references Arial.
- Renderer clipping, glyph, label-collision, and guide checks passed. Inspected actual PNG and rendered PDF; independent reviewer found no panel defect and accepted the caption. Status: `ready` for checked requirements.
- Re-running the self-contained bundle reproduced PNG/SVG byte for byte.
- No inference or replicate-based analysis was introduced.

## Remaining limitations

Source denominator and score construction were not supplied; the caption records this. Zero-area dots cannot communicate their score color, but those scores remain in the accompanying data and this is explained. SVG requires Arial on its assembly system. These do not prevent satisfying the requested plot. The checked scope is this table and its exports, without an arbitrary-data or publication-acceptance claim.
