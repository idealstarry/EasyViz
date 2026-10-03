#!/usr/bin/env python3
"""Rerender both audited same-data views into a fresh directory under this package."""
from pathlib import Path
import argparse, os, subprocess, sys
import datetime
HERE = Path(__file__).resolve().parent
SKILL = Path('/Users/starry/Desktop/EasyViz/skills/easyviz')
parser = argparse.ArgumentParser()
parser.add_argument('--out', default='rerun-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
args = parser.parse_args()
destination = (HERE / args.out).resolve()
if HERE not in destination.parents:
    parser.error('Output must be a fresh child of this output package.')
env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['MPLCONFIGDIR'] = str(HERE / '.mplconfig')
subprocess.run([sys.executable, '-B', str(SKILL / 'scripts/preview_choices.py'),
                '--data', str(HERE / 'source.csv'),
                '--request', str(HERE / 'preview-request.json'),
                '--out', str(destination)], check=True, env=env)
print('Chosen view: box-points. Inspect the new exports before adopting them.')
