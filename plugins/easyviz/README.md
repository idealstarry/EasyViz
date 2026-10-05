# EasyViz

Create and reproduce scientific plots from user data. In create, start with a prepared data directory or a scientific question, choose a basic chart and refine its color, boundaries and proportions. In reproduce, use a reference image and your own data, including references without published Source Data or author code. Export individual panels at their final physical size.

## Skills

| Skill | Role |
| --- | --- |
| [EasyViz](skills/easyviz/SKILL.md) | Main create/reproduce workflow, chart selection, statistics, palettes, and exports |
| [Reference Reader](skills/easyviz-reference-reader/SKILL.md) | Independent interpretation of a reference figure without author code |
| [Figure Reviewer](skills/easyviz-figure-reviewer/SKILL.md) | Compare a rendered panel with the adopted requirements and reference |

Keep all three skill directories together when using the plugin. The main skill can also be used alone, with its documented non-independent fallback. The optional review workbench runs on localhost; analysis runs only from an explicit adopted plan.

## Install or update

Ask a local Agent: “Install or update https://github.com/idealstarry/EasyViz in my local ChatGPT Desktop; read INSTALL.md and complete it for me.” The [repository installation guide](https://github.com/idealstarry/EasyViz/blob/main/INSTALL.md) tells the Agent how to acquire the source, use the standard-library installer, preserve your other plugins, refresh the installed copy, and verify it. A compatible Codex CLI is required for automatic local installation. Downloading this package alone does not register it.

The manifest records this package's version. Start a new chat after installation; refresh or restart the desktop if an update is not visible. This is a local plugin installation, with client support checked on the installed version.

## Runtime

Use a local Python environment with the dependencies in `skills/easyviz/scripts/requirements.txt`. Python 3.12 was used for validation. The Agent should check available packages and use the user's selected environment.

From this plugin directory:

```sh
python skills/easyviz/scripts/render.py \
  --data skills/easyviz/assets/fixtures/heatmap/data.csv \
  --spec skills/easyviz/assets/fixtures/heatmap/spec.json \
  --out /tmp/easyviz-heatmap
```

The core supports heatmaps, composition bars, dot plots, scatter plots, and box/violin distributions. Focused scripts add supplied intervals, paired observations, replicate bars, ECDF and time courses with uncertainty bands. New geometry can use custom plotting code under the same size, data and review rules. Planned statistics require explicit methods and experimental units.

For directory exploration, use `inspect_data.py`; for an adopted analysis, use `analyze.py`. `reference_packet.py` stages reproduce inputs and a layer implementation plan. `figure_workbench.py --figure-dir /absolute/path/to/attempt --port 0` opens a local page where the user selects SVG elements or regions and saves instructions. The Agent reads those requests, edits the plotting code/specification, and rerenders SVG, PDF and PNG together. These helpers serve the same two tracks.

## Resources

Copy bundled case folders into your writable project before running or adapting them. The case scripts may write beside their inputs; the installed plugin should remain a reusable source.

- [Chart inputs and settings](skills/easyviz/references/chart-library.md)
- [Five basic Create panels with runnable Source Data](skills/easyviz/assets/cases/basic-panels/README.md)
- [Create mark colors and line roles](skills/easyviz/references/create-style.md)
- [Directory exploration](skills/easyviz/references/data-exploration.md)
- [Planned analysis](skills/easyviz/references/statistical-analysis.md)
- [Reference to code](skills/easyviz/references/reference-to-code.md)
- [Local figure workbench](skills/easyviz/references/figure-workbench.md)
- [Design decisions and worked alternatives](skills/easyviz/references/design-decisions.md)
- [Physical dimensions and typography](skills/easyviz/references/panel-layout.md)
- [Legend proportions and measured placement](skills/easyviz/references/legend-layout.md)
- [Palette options](skills/easyviz/references/palettes.md)
- [Example catalog](skills/easyviz/references/examples.md)
- [Source attribution](THIRD_PARTY_NOTICES.md)

PDF and SVG preserve physical dimensions; PNG and TIFF include resolution metadata. SVG text references its font and requires that font on the assembly machine. Always inspect the final output and place it at the recorded size.

Each worked case records its tested input scope, review evidence and intentional deviations. Reuse on new data requires a new visual and numerical check. No author plotting code is required for the reproduce track.

Original code and documentation are licensed under MIT; see `LICENSE`. Third-party data and images retain the terms in [Source attribution](THIRD_PARTY_NOTICES.md).
