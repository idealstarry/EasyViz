<div align="center">

<img src="plugins/easyviz/assets/logo.svg" alt="EasyViz logo" width="96" height="96">

# EasyViz

**Scientific plotting guided by data and literature.**

</div>

EasyViz helps a local Agent turn data into editable scientific figures, with
literature-informed design, actual image review and PDF, SVG and PNG exports.

[Latest stable release](https://github.com/idealstarry/EasyViz/releases/latest).

| Track | Start with | The Agent does |
| --- | --- | --- |
| **Create** | A data directory, table or scientific question | Recommends a suitable chart, applies scene-specific design and reviews the result before delivery. |
| **Reproduce** | A reference image and your data | Reads the visual structure, writes or adapts plotting code and checks the result against the reference. |

Set the panel size, typography and scientific choices; EasyViz keeps them
consistent. You receive the figure, a separate caption, runnable code and
traceable plotting data.

## Install

Give your Agent this request:

```text
Install or update https://github.com/idealstarry/EasyViz in my local
ChatGPT Desktop. Follow INSTALL.md and verify the installation for me.
```

For other local Agents, follow [INSTALL.md](INSTALL.md).
[Release packages](https://github.com/idealstarry/EasyViz/releases) are also available.
Start a new chat after installing or updating.

## Use

**Create**

```text
Use EasyViz to inspect /path/to/my-data and recommend useful figures.
Use an 80 × 70 mm panel and 8 pt text. Inspect and refine the actual images
before delivery, export PDF, SVG and PNG, and save a separate caption.
```

**Reproduce**

```text
Use EasyViz to reproduce this reference with my measurements.csv.
Keep its layers and axis structure, use a 100 × 76 mm panel and 8 pt text,
and write plotting code for any unsupported layers. Export PDF, SVG and PNG.
```

The Agent clarifies consequential unknowns about units, pairing or comparisons.
For a new Create panel, it uses applicable literature design rules and
[visual design cards](skills/easyviz/references/design-cards.md), then inspects
and corrects the images before the first finished delivery.

## Examples

### Create

**Treatment comparison** · One repair outcome, with every biological replicate
and sample SD. The case also exports the other outcomes separately.
[Data, code and caption](examples/create/repair-outcomes/README.md).

<p align="center"><a href="examples/create/repair-outcomes/"><img src="examples/create/repair-outcomes/panels/hdr/output/panel.png" alt="HDR treatment comparison with neutral open means, all biological replicates and sample SD" width="440"></a></p>

**Cell-number comparison** · Compare two treatments within nine measured
populations. Separate raw-observation and mean ± SEM lanes keep the summaries
visible. [Fresh workflow exercise, data and limitations](evals/create-purpose-overhaul-v0.4.4/fresh-run/README.md).

<p align="center"><a href="evals/create-purpose-overhaul-v0.4.4/fresh-run/README.md"><img src="evals/create-purpose-overhaul-v0.4.4/fresh-run/with-skill/attempt-02/panel.png" alt="Nine population treatment comparisons with all 156 supplied observations and separate mean and SEM strokes" width="680"></a></p>

**Composition heatmap** · Original percentages, clear cell seams and numeric
values. [Data, code and caption](examples/create/basic-panels/depot-heatmap/).

<p align="center"><a href="examples/create/basic-panels/depot-heatmap/"><img src="examples/create/basic-panels/depot-heatmap/output/panel.png" alt="Subtype percentages across three adipose depots" width="420"></a></p>

### Reproduce

**Time-course means and SD** · Original Figure 1d from
[Shi et al., Nature Communications (2021)](https://doi.org/10.1038/s41467-021-22092-5),
compared with the reconstruction from its 120 supplied summaries.

| Original literature panel | EasyViz reconstruction |
| --- | --- |
| <img src="examples/no-author-code/shi-timecourse/reference.png" alt="Original Shi Figure 1d with two colored axes and mean plus SD bands" width="350"> | <a href="examples/no-author-code/shi-timecourse/"><img src="examples/no-author-code/shi-timecourse/output/panel.png" alt="Reconstructed Figure 1d from all supplied means and SD, with declared axis-bound adaptation" width="350"></a> |

The reproduced panel omits the original panel letter and expands the width-axis
bounds to show the full supplied SD. Source excerpt: Shi et al.,
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
[Data, code and recorded differences](examples/no-author-code/shi-timecourse/README.md).
Other cases include [integration radar](examples/no-author-code/massier-integration-radar/)
and [supplied-effect forest panels](examples/no-author-code/vabistsevits-forest/).

The examples use attributed literature Source Data. Each case records its
transformations and limitations. Your own reproduction needs a reference and
your data; published Source Data or author code is optional.
[Browse all cases](examples/README.md).

## Colors

Choose a palette for the marks and scientific meaning. Defaults are editable.

| Use | Palette | Preview |
| --- | --- | --- |
| Summary areas with dark boundaries | `progeny-summary` | <img src="docs/assets/palettes/progeny-summary.png" alt="Violet, mint, salmon and gray summary fills" width="300" height="24"> |
| Two observation classes | `scwat-blue-pink` | <img src="docs/assets/palettes/scwat-blue-pink.png" alt="Blue and pink observation colors" width="300" height="24"> |
| Increasing magnitude | `somerville-sky` | <img src="docs/assets/palettes/somerville-sky.png" alt="Light-to-strong sky blue sequential scale" width="300" height="24"> |
| Values around an adopted center | `scwat-blue-white-coral` | <img src="docs/assets/palettes/scwat-blue-white-coral.png" alt="Blue-white-coral diverging scale" width="300" height="24"> |

[All palettes, HEX values and literature sources](docs/palettes.md).

## Local figure review

```text
Open the EasyViz local figure workbench for this panel.
Let me select elements or draw numbered regions and save my instructions.
When I say the requests are ready, apply them and show the new attempt
beside the previous one.
```

The Agent shares a `http://127.0.0.1:PORT/` page. Click or draw to add numbered
annotations, write an instruction for each, and use **Save requests** together.
Saving records the requests; tell the Agent when to apply them. It edits the
plotting code and rerenders a new attempt. SVG element selection requires a
matching element map; region notes remain available without one.
[Workbench guide](skills/easyviz/references/figure-workbench.md).

## Guides

[Chart library](skills/easyviz/references/chart-library.md) ·
[Data exploration and analysis](skills/easyviz/references/data-exploration.md) ·
[First Create delivery](skills/easyviz/references/first-draft.md) ·
[Reference to code](skills/easyviz/references/reference-to-code.md) ·
[Development](docs/development.md) ·
[Validation and limits](evals/create-purpose-overhaul-v0.4.4/README.md)

Original code and documentation: [MIT](LICENSE).
Third-party materials retain their own terms; see [source attribution](THIRD_PARTY_NOTICES.md).
