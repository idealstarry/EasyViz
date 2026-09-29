#!/usr/bin/env python3
"""Controlled color-scale experiment. Does not edit the source example."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CASE = ROOT / 'examples/create/annotated-inhibition'

def main():
    source = (CASE / 'plot.py').read_text()
    replacements = {
        'from matplotlib.colors import ListedColormap, LinearSegmentedColormap': 'from matplotlib.colors import ListedColormap, LinearSegmentedColormap, Normalize, AsinhNorm',
        '        cmap = LinearSegmentedColormap.from_list("easyviz_case", palette) if isinstance(palette, list) else palette\n        image = ax.imshow(shown, cmap=cmap, vmin=lo, vmax=hi, aspect="equal", interpolation="nearest")': '''        norm = AsinhNorm(linear_width=100, vmin=lo, vmax=hi) if cfg["experiment_scale"] == "signed-asinh" else Normalize(vmin=lo, vmax=hi)
        # The zero color is fixed by the actual normalization, not its visual midpoint.
        cmap = LinearSegmentedColormap.from_list("signed_gii", [(0, "#2581B9"), (float(norm(0)), "#F8F7F4"), (1, "#E47751")], N=4097)
        image = ax.imshow(shown, cmap=cmap, norm=norm, aspect="equal", interpolation="nearest")''',
        'ticks=np.linspace(lo, hi, 3)': 'ticks=cfg["experiment_ticks"]',
        '        cb.outline.set_linewidth(.4)': '        cb.set_ticks(cfg["experiment_ticks"], labels=[str(v) for v in cfg["experiment_ticks"]])\n        cb.minorticks_off()\n        cb.outline.set_linewidth(.4)',
        'text("colorbar_title", "Pairwise GII (min)", ha="center", va="bottom")': 'text("colorbar_title", cfg["experiment_colorbar_label"], ha="center", va="bottom")',
    }
    for old, new in replacements.items():
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    copied = HERE / 'plot_experiment.py'
    copied.write_text(source)
    spec = importlib.util.spec_from_file_location('inhibition_experiment', copied)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, ticks, label in [
        ('linear-zero', [-400, 0, 1000], 'Pairwise GII (min)'),
        ('signed-asinh', [-400, 0, 100, 1000], 'GII (min; asinh color)'),
    ]:
        cfg = json.loads((CASE / 'settings.json').read_text())
        cfg.update(experiment_scale=name, experiment_ticks=ticks, experiment_colorbar_label=label, mean_color='#6197B8')
        cfg['palette_status'] = 'Proposed signed blue-neutral-coral scale using previously sourced endpoints; not the author palette.'
        cfg['colormap'] = ['#2581B9', '#F8F7F4', '#E47751']
        cfg['colormap_stop_rule'] = 'positions 0, norm(0), 1; neutral is at numeric zero, not midpoint'
        cfg['palette_sources'] = ['https://www.nature.com/articles/s41467-024-53700-9', 'https://www.nature.com/articles/s41467-024-52687-7']
        cfg['palette_family'] = 'experiment-blue-neutral-coral'
        cfg['palette_preset'] = None
        cfg['experiment_source_script_sha256'] = hashlib.sha256((CASE/'plot.py').read_bytes()).hexdigest()
        cfg['experiment_note'] = 'Proposal only. Fixed input/order/axes/font/canvas; no numeric value transformation in source or summaries. Normalization affects color only.'
        if name == 'signed-asinh':
            cfg['normalization_formula'] = '(asinh(x / 100) - asinh(-400 / 100)) / (asinh(1000 / 100) - asinh(-400 / 100))'
            cfg['normalization_inverse'] = '100 * sinh(t * (asinh(1000 / 100) - asinh(-400 / 100)) + asinh(-400 / 100))'
        else:
            cfg['normalization_formula'] = '(x + 400) / 1400'
            cfg['normalization_inverse'] = '1400 * t - 400'
        config_path = HERE / f'{name}.json'
        config_path.write_text(json.dumps(cfg, indent=2) + '\n')
        module.run(HERE / name, CASE/'source-data.csv', CASE/'genome-status.csv', config_path)
        assert (HERE/name/'plotting-data.csv').read_bytes() == (CASE/'plotting-data.csv').read_bytes()
        assert (HERE/name/'summary-data.csv').read_bytes() == (CASE/'summary-data.csv').read_bytes()
        assert (HERE/name/'selection.csv').read_bytes() == (CASE/'selection.csv').read_bytes()
        lo, hi = cfg['color_limits']
        vals=np.array([-400, -100, 0, 100, 300, 1000])
        n=module.AsinhNorm(linear_width=100,vmin=lo,vmax=hi) if name=='signed-asinh' else module.Normalize(vmin=lo,vmax=hi)
        assert np.allclose(n.inverse(n(vals)), vals)
        print(name, 'data exact; positions', dict(zip(vals.tolist(), np.round(n(vals), 6).tolist())))

if __name__ == '__main__':
    main()
