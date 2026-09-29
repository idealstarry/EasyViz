<div align="center">

# EasyViz

**Scientific panels, ready for your manuscript.**

Source data · Create & reproduce · Consistent typography · Individual exports

[Examples](#examples) · [Use](#use) · [Setup](#setup) · [QA](evals/release-qa/README.md)

</div>

EasyViz helps an Agent turn prepared source data into clear scientific figures. Choose a chart or supply a reference, select a palette and export format, and get a reproducible panel at its final manuscript size.

| Track | Input | Approach |
| --- | --- | --- |
| **Create** | Source data and a chart type or scientific question | Choose useful encodings, grouping and summaries; compare alternatives when the design matters. |
| **Reproduce** | A reference image and source data | Read the visual structure, adapt it to your data, and check the result. Author code is optional. |

Palettes, proportions, dimensions and fonts are configurable. Each panel is exported separately for assembly at its recorded size. General statistics are supported; upstream bioinformatics analysis stays outside the Skill. Explanatory prose belongs in the accompanying caption.

## Examples

**Create · paired myeloid changes**

Three designs for the same 832 paired changes: individual values, cohort distributions, and participant correspondence.

<p align="center"><a href="examples/create/paired-myeloid-remodeling/"><img src="examples/create/paired-myeloid-remodeling/comparison.png" alt="Three designs compared on the same paired myeloid data" width="960"></a></p>

**Create · annotated inhibition matrix**

Genome-status annotations and full-matrix summaries accompany a selected 20 × 20 view.

<p align="center"><a href="examples/create/annotated-inhibition/"><img src="examples/create/annotated-inhibition/panel.png" alt="Microbial inhibition heatmap with annotations and marginal means" width="640"></a></p>

**Create · cell atlas composition**

Counts, within-depot proportions, and aligned totals for 16 myeloid subtypes across three depots.

<p align="center"><a href="examples/create/cell-atlas-dotplot/"><img src="examples/create/cell-atlas-dotplot/output/figure.png" alt="Myeloid subtype composition across three adipose depots" width="720"></a></p>

**Create · cohort effects**

Supplied estimates and asymmetric confidence intervals; synthetic data demonstrate custom geometry and field mapping.

<p align="center"><a href="examples/create/paired-effects/"><img src="examples/create/paired-effects/panel.png" alt="Cohort effects and asymmetric confidence intervals" width="720"></a></p>

**Reproduce · integration comparison**

Five methods across five cell classes, reconstructed from a reference image and source data without author code. All 25 rates, including three zeros, are retained.

<p align="center"><a href="examples/no-author-code/massier-integration-radar/"><img src="examples/no-author-code/massier-integration-radar/panel.png" alt="Integration radar comparing five methods across five cell classes" width="440"></a></p>

[Browse all examples](examples/README.md) · [Design decisions](skills/easyviz/references/design-decisions.md)

**Palette choices**

<p align="center"><a href="skills/easyviz/references/palettes.md"><img src="skills/easyviz/assets/palettes/preview.png?v=arial-300dpi" alt="Figure-sourced palette choices" width="720"></a></p>

## Use

```text
Use $easyviz to plot my source data as a dot plot.
Use blue / amber / teal / pink, Arial 8 pt, and a 180 × 120 mm panel.
Export PDF, SVG and PNG, with the caption in a separate file.
```

For reproduction, attach a reference image and state any requested changes. Deliverables include the individual panel, caption, runnable script, settings, plotting data and relevant checks.

The `$easyviz` shorthand requires a discoverable skill. For an uninstalled checkout, ask the Agent to read and use the absolute path to `skills/easyviz/SKILL.md`.

## Setup

Download the plugin ZIP from [Releases](https://github.com/idealstarry/EasyViz/releases), or build it locally with Python 3.12:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/build_plugin.py
```

The portable package is written to `dist/easyviz/`; building it does not register it in Codex. See the [package guide](plugins/easyviz/README.md) for runtime requirements and resource entry points.

## Inside

- [EasyViz](skills/easyviz/SKILL.md) — the two tracks, data choices and panel delivery.
- [Reference Reader](skills/easyviz-reference-reader/SKILL.md) — independent interpretation of a supplied image.
- [Figure Reviewer](skills/easyviz-figure-reviewer/SKILL.md) — actual-image review against the adopted requirements.

[Development](docs/development.md) · [Release QA](evals/release-qa/README.md) · [Generalization limits](docs/generalization.md)

## License

Original code and documentation: [MIT](LICENSE). Third-party data and reference figures retain their own terms; see [source attribution](THIRD_PARTY_NOTICES.md).
