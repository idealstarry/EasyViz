#!/usr/bin/env python3
"""Run the actual directory-intake, planned-summary and first-panel workflow."""
from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SKILL = Path('/Users/starry/Desktop/EasyViz/skills/easyviz')
env = os.environ.copy()
env['MPLCONFIGDIR'] = str(ROOT / 'runtime' / 'mpl-cache')
env['PYTHONDONTWRITEBYTECODE'] = '1'
commands = []

def run(script, arguments):
    command = [sys.executable, str(SKILL / 'scripts' / script), *map(str, arguments)]
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    commands.append({'argv': command, 'returncode': result.returncode,
                     'stdout': result.stdout, 'stderr': result.stderr})
    (ROOT / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(f'{script} failed: {result.stderr}')
    print(result.stdout.strip())

run('inspect_data.py', ['--input', '/private/tmp/easyviz-forward-create/input', '--design', ROOT / 'intake-design.json', '--out', ROOT / 'exploration-02-design'])
run('analyze.py', ['--data', ROOT / 'source/observations.csv', '--plan', ROOT / 'analysis-plan.json', '--out', ROOT / 'analysis-01'])
run('draft_spec.py', ['--data', ROOT / 'source/observations.csv', '--chart', 'distribution', '--field', 'group=condition', '--field', 'value=signal', '--field', 'unit=sample_id', '--profile', ROOT / 'figure-profile.json', '--panel', 'primary_signal', '--out', ROOT / 'draft-plot.json'])
spec = json.loads((ROOT / 'draft-plot.json').read_text())
spec.update({'formats': ['pdf', 'svg', 'png'], 'order': {'group': ['Control', 'Treatment']}, 'seed': 23})
spec['labels'] = {'x': 'Condition', 'y': 'Fluorescence signal (a.u.)'}
spec['options'] = {'kind': 'box', 'orientation': 'vertical', 'point_area_pt2': 16, 'alpha': 0.9, 'grid': True, 'y_limits': [0, 10]}
(ROOT / 'plot.json').write_text(json.dumps(spec, indent=2) + '\n')
run('render.py', ['--data', ROOT / 'source/observations.csv', '--spec', ROOT / 'plot.json', '--out', ROOT / 'attempt-01'])
