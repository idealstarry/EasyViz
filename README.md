<div align="center">

<img src="plugins/easyviz/assets/logo.svg" alt="EasyViz logo" width="96" height="96">

# EasyViz

**Scientific panels, ready for your manuscript.**

</div>

EasyViz helps an Agent turn prepared source data into clear scientific figures. Choose a chart or supply a reference, select a palette and export format, and get a reproducible panel at its final manuscript size.

| Track | Input | Approach |
| --- | --- | --- |
| **Create** | Source data and a chart type or scientific question | Choose useful encodings, grouping and summaries; compare alternatives when the design matters. |
| **Reproduce** | A reference image and source data | Read the visual structure, adapt it to your data, and check the result. Author code is optional. |

Palettes, proportions, dimensions and fonts are configurable. Each panel is exported separately for assembly at its recorded size. General statistics are supported; upstream bioinformatics analysis stays outside the Skill. Explanatory prose belongs in the accompanying caption.

Related panels can share a [figure profile](skills/easyviz/references/figure-profile.md) so category colors, typography and quantitative scales stay consistent. Dot plots distinguish [measured zero, unmeasured and absent data](skills/easyviz/references/dot-states.md) without changing proportional dot areas. Unknown configuration fields fail with a correction hint.

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

<p align="center"><a href="skills/easyviz/references/palettes.md"><img src="skills/easyviz/assets/palettes/palette-swatches.png" alt="Figure-sourced palette choices" width="100%"></a></p>

## Use

```text
Use $easyviz to plot my source data as a dot plot.
Use blue / amber / teal / pink, Arial 8 pt, and a 180 × 120 mm panel.
Export PDF, SVG and PNG, with the caption in a separate file.
```

For reproduction, attach a reference image and state any requested changes. Deliverables include the individual panel, caption, runnable script, settings, plotting data and relevant checks.

The `$easyviz` shorthand requires a discoverable skill. For an uninstalled checkout, ask the Agent to read and use the absolute path to `skills/easyviz/SKILL.md`.

## Setup

Give your local Agent this request:

```text
Install or update https://github.com/idealstarry/EasyViz in my local
ChatGPT Desktop. Read its INSTALL.md and complete the installation for me.
```

The Agent follows [INSTALL.md](INSTALL.md) to download, install or update, and verify EasyViz. It handles the local requirements and preserves your other plugins. Start a new chat for first use; a running desktop may need to refresh or restart before showing an update.

[Release ZIPs](https://github.com/idealstarry/EasyViz/releases) are available for portable use. Building or downloading a package alone does not install it. See the [package guide](plugins/easyviz/README.md) for runtime requirements and [development guide](docs/development.md) for local builds and release checks.

## Inside

- [EasyViz](skills/easyviz/SKILL.md) — the two tracks, data choices and panel delivery.
- [Reference Reader](skills/easyviz-reference-reader/SKILL.md) — independent interpretation of a supplied image.
- [Figure Reviewer](skills/easyviz-figure-reviewer/SKILL.md) — actual-image review against the adopted requirements.

[Development](docs/development.md) · [Release QA](evals/release-qa/README.md) · [Generalization limits](docs/generalization.md)

[Skill value pilot](evals/skill-value/README.md) compares Agent outputs with and without EasyViz on the same two official datasets. Its evidence and limits are recorded separately from renderer tests.

## License

Original code and documentation: [MIT](LICENSE). Third-party data and reference figures retain their own terms; see [source attribution](THIRD_PARTY_NOTICES.md).
