<div align="center">

<img src="plugins/easyviz/assets/logo.svg" alt="EasyViz logo" width="96" height="96">

# EasyViz

**Scientific panels, ready for your manuscript.**

</div>

EasyViz helps a local Agent turn data into editable scientific figures, with
literature-informed design, actual image review and PDF, SVG and PNG exports.

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

**Replicate bars** · Three compact outcome panels, with every replicate and
sample SD. [Data, code and caption](examples/create/repair-outcomes/README.md).

<p align="center"><a href="examples/create/repair-outcomes/"><img src="examples/create/repair-outcomes/output/panel.png" alt="Three individual repair-outcome bar panels with raw replicates and sample SD" width="680"></a></p>

| Cohort distributions | Before/after coordinates |
| --- | --- |
| <a href="examples/create/basic-panels/cohort-box/"><img src="examples/create/basic-panels/cohort-box/output/panel.png" alt="Cohort quartile boxes with all observations" width="350"></a> | <a href="examples/create/basic-panels/paired-scatter/"><img src="examples/create/basic-panels/paired-scatter/output/panel.png" alt="Participant before-after coordinates, colored by infection class" width="350"></a> |

**Composition heatmap** · Original percentages, clear cell seams and numeric
values. [Data, code and caption](examples/create/basic-panels/depot-heatmap/).

<p align="center"><a href="examples/create/basic-panels/depot-heatmap/"><img src="examples/create/basic-panels/depot-heatmap/output/panel.png" alt="Subtype percentages across three adipose depots" width="420"></a></p>

### Reproduce

| Integration radar | Supplied effects and intervals |
| --- | --- |
| <a href="examples/no-author-code/massier-integration-radar/"><img src="examples/no-author-code/massier-integration-radar/panel.png" alt="Reference-led reconstruction of five integration methods" width="320"></a> | <a href="examples/no-author-code/vabistsevits-forest/"><img src="examples/no-author-code/vabistsevits-forest/output-a/panel.png" alt="Supplied odds ratios and asymmetric confidence intervals on a log axis" width="420"></a> |

**Time-course summaries** · Supplied means, SD bands and two labeled axes;
recorded adaptations retain the full uncertainty bounds.
[Reference, data and code](examples/no-author-code/shi-timecourse/README.md).

<p align="center"><a href="examples/no-author-code/shi-timecourse/"><img src="examples/no-author-code/shi-timecourse/output/panel.png" alt="Supplied cell-width and cell-length time-course summaries" width="460"></a></p>

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
[Validation and limits](evals/create-first-delivery-v0.4.4/README.md)

Original code and documentation: [MIT](LICENSE).
Third-party materials retain their own terms; see [source attribution](THIRD_PARTY_NOTICES.md).
