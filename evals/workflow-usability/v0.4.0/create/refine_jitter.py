#!/usr/bin/env python3
"""Resolve actual observation-circle overlaps without changing source values."""
from pathlib import Path
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
data = pd.read_csv(ROOT / 'source/observations.csv', dtype={'sample_id': str})
settings = json.loads((ROOT / 'attempt-01/settings.json').read_text())
plot_width = settings['auto_layout']['data_region_mm'][2]
plot_height = settings['auto_layout']['data_region_mm'][3]
diameter = 4 * 25.4 / 72
records = []

def check_seed(seed):
    rng = np.random.default_rng(seed)
    overlaps = []
    minimum = math.inf
    for group in ['Control', 'Treatment']:
        subset = data.loc[data.condition == group]
        xy = np.column_stack([rng.uniform(-.13, .13, len(subset)) * plot_width / 2.2,
                              subset.signal.to_numpy() * plot_height / 10])
        for i, j in itertools.combinations(range(len(xy)), 2):
            distance = float(np.linalg.norm(xy[i] - xy[j]))
            minimum = min(minimum, distance)
            if distance < diameter:
                overlaps.append({'sample_ids': [str(subset.iloc[i].sample_id), str(subset.iloc[j].sample_id)],
                                 'center_distance_mm': distance})
    return {'seed': seed, 'diameter_mm': diameter, 'minimum_center_distance_mm': minimum, 'overlaps': overlaps}

records.append(check_seed(23))
selected = None
for seed in [37, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
    result = check_seed(seed)
    records.append(result)
    if not result['overlaps']:
        selected = seed
        break
assert selected is not None, 'Resolve overlapping raw marks with an explicit implementation.'
report = {'scope': 'Only geometric placement of fixed-diameter raw marks; no statistical tests or source changes',
          'method': 'First non-overlapping seed in the recorded fixed sequence; comparison uses physical center distance',
          'selected_seed': selected, 'attempts': records}
(ROOT / 'jitter-review.json').write_text(json.dumps(report, indent=2) + '\n')
shutil.copyfile(ROOT / 'plot.json', ROOT / 'plot-attempt-01.json')
spec = json.loads((ROOT / 'plot.json').read_text())
spec['seed'] = selected
(ROOT / 'plot.json').write_text(json.dumps(spec, indent=2) + '\n')
env = os.environ.copy()
env['MPLCONFIGDIR'] = str(ROOT / 'runtime/mpl-cache')
env['PYTHONDONTWRITEBYTECODE'] = '1'
command = [sys.executable, '/Users/starry/Desktop/EasyViz/skills/easyviz/scripts/render.py',
           '--data', str(ROOT / 'source/observations.csv'), '--spec', str(ROOT / 'plot.json'),
           '--out', str(ROOT / 'attempt-02')]
result = subprocess.run(command, text=True, capture_output=True, env=env)
commands = json.loads((ROOT / 'commands.json').read_text())
commands.append({'argv': command, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
(ROOT / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
assert result.returncode == 0, result.stderr
print(json.dumps(report, indent=2))
print(result.stdout)
