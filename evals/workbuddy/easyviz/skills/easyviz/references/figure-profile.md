# Shared figure settings for separate panels

Use one `figure-profile.json` for panels that belong to the same manuscript figure. It declares shared typography, the complete category-to-color mapping, named continuous and dot-size scales when values must be comparable, and each panel's actual physical dimensions. Each invocation still exports one independent panel.

```json
{
  "version": 1,
  "layout": {
    "font": "Arial",
    "font_size_pt": 8,
    "line_width_pt": 0.6,
    "dpi": 300
  },
  "typography": {"title": 9, "panel": 9},
  "colors": {
    "Control": "#29ACF3",
    "Treatment": "#E47751"
  },
  "continuous_scales": {
    "expression": {
      "colormap": "blue-white-red",
      "color_limits": [-2, 2],
      "color_center": 0
    }
  },
  "size_scales": {
    "count": {
      "size_max": 100,
      "max_area_pt2": 90,
      "size_legend": [25, 50, 100]
    }
  },
  "panels": {
    "A": {"width_mm": 88, "height_mm": 66},
    "B": {"width_mm": 132, "height_mm": 88}
  }
}
```

`layout` must declare `font`, `font_size_pt`, `line_width_pt`, and integer `dpi`. Dimensions use millimeters, typography and line widths use points, and dpi changes raster resolution. Use JSON numbers without unit suffixes. Panel dimensions are the complete canvas, including legends and margins. Shared typography roles are optional; axis, tick, legend and annotation sizes otherwise use the shared base size. Named panels require both `width_mm` and `height_mm`. Their names select dimensions; they do not add lettering to the artwork.

`colors` is optional for figures with no categorical encoding. When supplied, declare every category used anywhere in the figure. A panel containing only Treatment retains Treatment's color even when Control is absent, input rows are reordered, or plot order changes. A palette name alone assigns colors from the categories in the current panel and cannot provide this guarantee. Omit local `palette` when the profile supplies `colors`.

Continuous scales are optional. Select a named scale only when the same measurement, units and normalization justify comparing values between panels. Each scale declares a colormap and fixed, strictly increasing `color_limits`, with optional scientifically meaningful `color_center`. Equal endpoints are rejected for a shared scale rather than silently expanded. Values outside those limits are rejected rather than clipped. Changing local data ranges does not change a selected scale. A panel can leave `continuous_scale` unset and choose its own documented scale when cross-panel comparability is inappropriate.

Dot-size scales are also optional. A named `size_scales` entry must declare positive `size_max` and `max_area_pt2`; it may also fix `size_legend` values. Select it with `"size_scale": "count"` in a dot-plot spec. The scatter area parameter remains `value / size_max × max_area_pt2`, so an equal supplied quantity has the same physical mark size across panels with different observed maxima or canvas dimensions. Source values exceeding `size_max` fail rather than being clipped. Use the same size scale only for quantities with comparable meanings and units. Leaving `size_scale` unset retains the existing local/default behavior, even when the profile contains size scales.

## Use the profile

Add the profile path and panel name to an ordinary plotting spec:

```json
{
  "profile": "figure-profile.json",
  "panel": "A",
  "chart": "scatter",
  "fields": {"x": "dose", "y": "response", "group": "arm"},
  "labels": {"x": "Dose (µM)", "y": "Response (%)"},
  "formats": ["pdf", "svg", "png"]
}
```

For a heatmap or dot plot using the shared expression scale, also add `"continuous_scale": "expression"`. For a dot plot using the shared count-to-area mapping, add `"size_scale": "count"`; both can be selected together. Keep data mappings, order, labels, statistics, and panel-specific internal margins in each plotting spec. Relative profile paths in a spec resolve from that spec's directory.

```sh
python /path/to/easyviz/scripts/render.py \
  --data source.csv --spec panel-a.json --out output/a
```

Alternatively, pass the profile and panel on the command line without adding them to the spec:

```sh
python /path/to/easyviz/scripts/render.py \
  --data source.csv --spec panel-b.json --out output/b \
  --profile figure-profile.json --panel B
```

Command-line profile paths resolve from the working directory. If a spec also declares a profile or panel, both declarations must agree. Python callers can use `render(data_path, spec, out, profile=profile_path, panel="B")`; pass `spec_path` when resolving a relative path stored inside the spec.

## Conflicts and saved evidence

Conflicting explicit settings fail with an explanation. A local font size, category color, selected color or size scale, or canvas size cannot silently override the profile. In particular, local `size_max` and `max_area_pt2` cannot change a selected size scale. Matching repeated values are allowed. A partial local color mapping must match the shared mapping; additional categories belong in the shared profile. To revise a common setting, update the profile and rerender the affected panels. To use an independent setting, use a separate profile or an ordinary spec without one, and record the change in the adopted specification.

Unknown keys and wrong value types fail before data are loaded. For example, `layout.fontsize_pt` gives a `font_size_pt` suggestion instead of quietly retaining 8 pt. Known keys remain available to standalone specs; no profile is required for a single panel.

Each output's `settings.json` saves the resolved settings, full shared category mapping, actual colors used, selected panel, continuous scale and size scale, absolute profile path, SHA-256 of the profile bytes, original plotting specification, and shared settings snapshot. The renderer also records the profile helper's code hash. Export dimensions, actual fonts, source values and visual review still require their existing checks. Preserve the profile and all panel-specific specs with the delivered scripts and data.
