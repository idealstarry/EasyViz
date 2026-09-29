# EasyViz 0.1.0

Create and reproduce scientific plots from source data. Export individual manuscript panels at their final physical size so the user can assemble them without resizing text.

## Skills

| Skill | Role |
| --- | --- |
| [EasyViz](skills/easyviz/SKILL.md) | Main create/reproduce workflow, chart selection, statistics, palettes, and exports |
| [Reference Reader](skills/easyviz-reference-reader/SKILL.md) | Independent interpretation of a reference figure without author code |
| [Figure Reviewer](skills/easyviz-figure-reviewer/SKILL.md) | Compare a rendered panel with the adopted requirements and reference |

Keep all three skill directories together when using the plugin. The main skill can also be used alone, with its documented non-independent fallback. This package has no network service or automatic analysis hook.

## Runtime

Use a local Python environment with the dependencies in `skills/easyviz/scripts/requirements.txt`. Python 3.12 was used for validation. The Agent should check available packages and use the user's selected environment.

From this plugin directory:

```sh
python skills/easyviz/scripts/render.py \
  --data skills/easyviz/assets/fixtures/heatmap/data.csv \
  --spec skills/easyviz/assets/fixtures/heatmap/spec.json \
  --out /tmp/easyviz-heatmap
```

The renderer supports heatmaps, composition bars, dot plots, scatter plots, and box/violin distributions. Unsupported geometry can use a custom plotting script under the same size, data, and review rules. Built-in statistical helpers require an explicit method and appropriate experimental units.

## Resources

Copy bundled case folders into your writable project before running or adapting them. The case scripts may write beside their inputs; the installed plugin should remain a reusable source.

- [Chart inputs and settings](skills/easyviz/references/chart-library.md)
- [Design decisions and worked alternatives](skills/easyviz/references/design-decisions.md)
- [Physical dimensions and typography](skills/easyviz/references/panel-layout.md)
- [Legend proportions and measured placement](skills/easyviz/references/legend-layout.md)
- [Palette options](skills/easyviz/references/palettes.md)
- [Example catalog](skills/easyviz/references/examples.md)
- [Source attribution](THIRD_PARTY_NOTICES.md)

PDF and SVG preserve physical dimensions; PNG and TIFF include resolution metadata. SVG text references its font and requires that font on the assembly machine. Always inspect the final output and place it at the recorded size.

This is a locally validated initial release, not a claim of universal figure reproduction or journal acceptance. No author plotting code is required for the reproduce track. Known uncertainties and intentional deviations are recorded with the scientific examples.
