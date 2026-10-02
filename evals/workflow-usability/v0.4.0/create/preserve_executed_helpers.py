#!/usr/bin/env python3
"""Freeze the accepted implementation for portable, version-bound replay."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/Users/starry/Desktop/EasyViz/skills/easyviz')
files = [f'scripts/{name}.py' for name in ['render', 'analyze', 'legend_layout', 'figure_profile',
          'auto_layout', 'annotation_review', 'figure_elements']]
files.extend(['scripts/requirements.txt', 'assets/palettes/palettes.json'])
snapshot = ROOT / 'skill-snapshot'
records = {}
for relative in files:
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / relative, target)
    records[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
accepted = json.loads((ROOT / 'attempt-02/settings.json').read_text())
assert records['scripts/render.py'] == accepted['renderer']['sha256']
analyzed = json.loads((ROOT / 'analysis-01/results.json').read_text())
report = {'snapshot': str(snapshot), 'files_sha256': records,
          'accepted_renderer_matches_snapshot': True,
          'note': 'The renderer changed after the intake hash capture; attempt-02 uses the current version and this snapshot preserves that version.'}
(ROOT / 'executed-helper-snapshot.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'snapshot_files': len(files), 'renderer_sha256': records['scripts/render.py']}, indent=2))
