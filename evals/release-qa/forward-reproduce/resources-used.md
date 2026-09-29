# Resources used

Task input directory: `/Users/starry/Desktop/EasyViz/evals/release-qa/inputs/reproduce/` — only `request.md`, `source.csv`, and `reference.png`. Local copies are beside the deliverables.

Project instructions: `/Users/starry/Desktop/EasyViz/AGENTS.md`.

Packaged skill resources read under `/Users/starry/Desktop/EasyViz/dist/easyviz/skills/`:
- `easyviz/SKILL.md`
- `easyviz/references/reproduce.md`
- `easyviz/references/reference-spec.md`
- `easyviz/references/panel-layout.md`
- `easyviz/references/legend-layout.md`
- `easyviz/references/visual-review.md`
- `easyviz/references/design-decisions.md`
- `easyviz/references/palettes.md`
- `easyviz/references/chart-library.md`
- `easyviz/references/examples.md`
- `easyviz-reference-reader/SKILL.md`
- `easyviz-figure-reviewer/SKILL.md` (actually read and confirmed by the fresh independent reviewer)

The chart-library and examples catalogs were read only after the reference observations and adopted specification had been written. No bundled case, fixture, source generation script, repository test, existing evaluation output or earlier agent record was opened. A custom Matplotlib script was selected because the requested absent-versus-zero encoding and two named reference separators require explicit additional layers beyond the documented basic dotplot contract. No source data from bundled examples were reused. No browser, GitHub, remote service, publication or installation was used.

Execution used the existing `/Users/starry/Desktop/EasyViz/.venv/bin/python`, plus installed Matplotlib, pandas, NumPy, Pillow, pypdf and PyMuPDF. Arial resolved to `/System/Library/Fonts/Supplemental/Arial.ttf`. All deliverables and rendering caches were written under `/private/tmp/easyviz-forward-reproduce`. The initial font-discovery probe used Matplotlib defaults and automatically created a temporary cache under macOS `/var/folders/.../T/`; the final script explicitly redirects both Matplotlib and XDG caches to the output folder. No canonical repository file was modified.
