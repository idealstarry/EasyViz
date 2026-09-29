# Massier Bmi Violin

Eight cohort BMI distributions, using all 858 available observations and retaining six missing-value records. This reproduce case used a reference image and source data, with author plotting code withheld by instruction.

![Final panel](panel.png)

## Rerun

Copy this entire case folder into a writable project directory before running or adapting it. The script writes outputs beside its inputs; keep installed plugin assets unchanged.

```sh
python /path/to/case/plot.py
```

Use the EasyViz runtime dependencies. The script locates its inputs relative to itself. It records the actual font, with a declared fallback if Arial is unavailable.

| Resource | Purpose |
| --- | --- |
| [Adopted specification](adopted-spec.md) | Required features, design decisions, and unknown original choices |
| [Source data](inputs/source-data.csv) | Traceable numeric inputs, never inferred from reference pixels |
| [Reference image](inputs/reference.png) | Target crop from the published figure |
| [Settings](settings.json) | Physical dimensions, typography, palette, and visual/statistical parameters |
| [Independent review](independent-review.md) | Actual reference/candidate comparison with disclosed limits |
| [QA](qa.json) | Numeric and physical-export checks |

PDF, SVG, and PNG are individual panels. Place them at their recorded physical size. This is a documented reconstruction, not a claim that unknown original parameters or editorial adjustments were recovered.

Data and reference excerpt: Massier et al. (2023), *An integrated single cell and spatial transcriptomic map of human white adipose tissue*, [DOI 10.1038/s41467-023-36983-2](https://doi.org/10.1038/s41467-023-36983-2), [source release](https://data.mendeley.com/datasets/y3pxvr4xbf/2), CC BY 4.0. The reference is cropped and the plotting implementation is newly written. Development provenance records exact extraction and transformation steps.
