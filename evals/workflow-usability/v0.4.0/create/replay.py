#!/usr/bin/env python3
"""Replay analysis and rendering into a fresh directory with the current skill."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True, help='Fresh output directory')
parser.add_argument('--skill', type=Path, default=ROOT / 'skill-snapshot')
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
env = os.environ.copy()
env['MPLCONFIGDIR'] = str(out / 'runtime' / 'mpl-cache')
env['PYTHONDONTWRITEBYTECODE'] = '1'
commands = []

def run(script, arguments):
    command = [sys.executable, str(args.skill / 'scripts' / script), *map(str, arguments)]
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    commands.append({'argv': command, 'returncode': result.returncode,
                     'stdout': result.stdout, 'stderr': result.stderr})
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(f'{script} failed: {result.stderr}')

run('analyze.py', ['--data', ROOT / 'source/observations.csv', '--plan', ROOT / 'analysis-plan.json', '--out', out / 'analysis'])
run('render.py', ['--data', ROOT / 'source/observations.csv', '--spec', ROOT / 'plot.json', '--out', out / 'panel'])
print(json.dumps({'status': 'replayed', 'out': str(out)}, indent=2))
