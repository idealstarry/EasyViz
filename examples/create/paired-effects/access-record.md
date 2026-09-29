# Transfer evaluation access record

The implementation followed EasyViz's create track and its explicit custom-renderer boundary. No existing example case, test, fixture, core renderer source, author code, or reference image was inspected to produce this case. The only example directory accessed was this newly created `examples/create/paired-effects` output directory. The source and request arrived before implementation; the supplied table is synthetic.

## Guidance and inputs actually read by the implementer

- `AGENTS.md`
- `skills/easyviz/SKILL.md`
- `skills/easyviz/references/create.md`
- `skills/easyviz/references/panel-layout.md`
- `skills/easyviz/references/palettes.md`
- `skills/easyviz/references/chart-library.md`
- `skills/easyviz/references/visual-review.md`
- `skills/easyviz/assets/palettes/palettes.json`
- `skills/easyviz/scripts/requirements.txt`
- `evals/transfer-inputs/paired-effects/request.md`
- `evals/transfer-inputs/paired-effects/source.csv`
- `evals/transfer-inputs/paired-effects/provenance.json`

The approved colors in the request determined the mapping. The palette JSON confirmed their identities; its linked literature, palette preview, other references, and worked cases were not opened. Environment checks queried the project `.venv` and confirmed Arial availability; system Python and the app runtime lacked Matplotlib. The project environment ran the script without installing dependencies. Python imported its required numerical/plotting/file-format libraries and the font manager accessed the installed Arial font; these environment assets were not examples or author implementations.

## Newly authored outputs inspected

The implementer opened both `panel.png` and `evaluation/panel.png` with the image viewer. The renderer directly read the local source/settings and measured its PDF, SVG, and PNG outputs. Follow-up numerical inspection read `actual-settings.json`, `numeric-qa.json`, and the evaluation source, settings, plotting table, SVG, and numeric QA. The original independent review was read after it was saved. Its exact independent access scope is listed in `review-independent.md`; that reviewer did not read the renderer or the evaluation variant.

## Findings and limits

The skill's chart library explicitly states that unsupported geometry should be implemented in a custom script and preserve the same dimension, type, data, and review requirements. This was sufficient guidance to implement direct horizontal confidence-interval segments rather than substituting a basic scatter plot. The main case has 28 records, 14 terms, two independent cohorts, and four domain groups. Its 27 asymmetric intervals and one symmetric interval are all retained exactly. Independent review found no required visual correction.

One separately generated reuse probe has five terms, three cohorts, two domains, all nine field names changed, reversed physical row order, and 15 supplied asymmetric intervals. Its first pre-export bounds check caught an automatic tick outside the view; filtering automatic ticks to the retained axis range corrected that issue. It then passed source-to-table, artist, direct SVG-coordinate, export, and self-review checks. This code change did not affect the original case's explicitly supplied ticks or original reviewed exports.

This evidence supports these two specified inputs. Complete cohort coverage, intervals bracketing estimates, and contiguous domain groups are current input requirements. Labels and category density can require explicit layout changes and a new visual review. There is no claim that the five core renderer families now support forest plots, or that this case validates arbitrary scientific plots.
