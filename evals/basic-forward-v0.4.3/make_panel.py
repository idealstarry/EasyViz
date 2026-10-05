#!/usr/bin/env python3
"""Prepare specimen means and invoke the public EasyViz draft/render workflow.

Run with the ready environment:
/Users/starry/Desktop/EasyViz/.venv/bin/python make_panel.py --attempt attempt-01
Use a fresh --attempt for any repair; first exports are never overwritten.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SKILL = Path('/Users/starry/Desktop/EasyViz/skills/easyviz')
ARMS = ['Vehicle', 'Dose 1', 'Dose 2']
COLORS = {'Vehicle': '#29ACF3', 'Dose 1': '#E47751', 'Dose 2': '#007F7F'}

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command, log_path, env):
    completed = subprocess.run(command, env=env, text=True, capture_output=True)
    write_json(log_path, {'command': command, 'returncode': completed.returncode,
                          'stdout': completed.stdout, 'stderr': completed.stderr})
    return completed

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--spec', type=Path, help='Optional accepted/repaired full spec; no drafting')
    args = parser.parse_args()
    attempt = ROOT / args.attempt
    if attempt.exists():
        raise SystemExit(f'Refusing to overwrite actual render: {attempt}')
    trace = ROOT / 'trace'
    data = ROOT / 'data'
    source = data / 'source'
    for directory in [trace, source, ROOT / '.cache' / 'matplotlib', ROOT / '.cache' / 'xdg']:
        directory.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MPLCONFIGDIR=str(ROOT / '.cache' / 'matplotlib'),
               XDG_CACHE_HOME=str(ROOT / '.cache' / 'xdg'))
    os.environ.update({k: env[k] for k in ['MPLCONFIGDIR', 'XDG_CACHE_HOME']})

    for name in ['assays.csv', 'study-notes.md', 'provenance.json']:
        destination = source / name
        original = ROOT / 'inputs' / name
        if destination.exists() and destination.read_bytes() != original.read_bytes():
            raise ValueError(f'Source archive changed: {name}')
        shutil.copy2(original, destination)
    with (source / 'assays.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    grouped = {}
    seen = set()
    for row in rows:
        key = (row['arm'], row['biospecimen_key'])
        repeat = int(row['readout_repeat'])
        if (*key, repeat) in seen:
            raise ValueError('Duplicate technical read key')
        seen.add((*key, repeat))
        value = Decimal(row['enzyme_velocity'])
        if not value.is_finite():
            raise ValueError('Nonfinite read; no silent filtering is allowed')
        grouped.setdefault(key, []).append((repeat, value))
    if set(arm for arm, _ in grouped) != set(ARMS):
        raise ValueError('Unexpected treatment arms')
    prepared = data / 'specimen-means.csv'
    with prepared.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['arm', 'biospecimen_key',
                                'independent_specimen', 'technical_reads', 'activity_nmol_min'])
        writer.writeheader()
        for (arm, unit), reads in sorted(grouped.items(), key=lambda item: (ARMS.index(item[0][0]), item[0][1])):
            if sorted(repeat for repeat, _ in reads) != [1, 2]:
                raise ValueError(f'Expected two explicit technical reads: {arm}, {unit}')
            mean = sum((value for _, value in reads), Decimal(0)) / 2
            writer.writerow({'arm': arm, 'biospecimen_key': unit,
                             'independent_specimen': f'{arm}|{unit}', 'technical_reads': 2,
                             'activity_nmol_min': str(mean)})
    from matplotlib import font_manager
    import numpy as np
    font_path = font_manager.findfont(font_manager.FontProperties(family='Arial'), fallback_to_default=False)
    summaries = {}
    for arm in ARMS:
        values = np.array([float(sum((value for _, value in reads), Decimal(0)) / 2)
                           for (group, _), reads in grouped.items() if group == arm])
        q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75], method='linear')
        inside = values[(values >= q1 - 1.5*(q3-q1)) & (values <= q3 + 1.5*(q3-q1))]
        summaries[arm] = {'n': len(values), 'minimum': float(values.min()), 'q1': float(q1),
                          'median': float(median), 'q3': float(q3), 'maximum': float(values.max()),
                          'whisker_low': float(inside.min()), 'whisker_high': float(inside.max())}
    write_json(data / 'data-audit.json', {
        'source_rows': len(rows), 'independent_specimens': len(grouped),
        'source_key': ['arm', 'biospecimen_key', 'readout_repeat'],
        'experimental_unit': ['arm', 'biospecimen_key'],
        'transformation': 'Arithmetic mean of the two technical reads within each arm + biospecimen_key.',
        'design': 'Independent specimens; arms are unpaired.', 'excluded_rows': 0,
        'missing_values': 0, 'units': 'nmol/min', 'inferential_tests': 'none',
        'summary_convention': 'Linear-interpolated quartiles; median; whiskers at observed extrema within 1.5 IQR.',
        'descriptive_summaries': summaries,
        'source_sha256': {name: sha(source/name) for name in ['assays.csv', 'study-notes.md', 'provenance.json']},
        'prepared_sha256': sha(prepared), 'actual_font_path_preflight': font_path
    })
    schema = run([sys.executable, str(SKILL/'scripts/render.py'), '--describe-spec'],
                 trace/'public-describe-spec-command.json', env)
    if schema.returncode:
        raise SystemExit('Public schema failed; see trace')
    (trace/'public-describe-spec.json').write_text(schema.stdout)
    spec_path = ROOT / f'{args.attempt}-spec.json'
    if args.spec:
        spec = json.loads(args.spec.read_text())
    else:
        draft_path = ROOT / f'{args.attempt}-draft.json'
        drafted = run([sys.executable, str(SKILL/'scripts/draft_spec.py'), '--data', str(prepared),
                       '--chart', 'distribution', '--field', 'group=arm',
                       '--field', 'value=activity_nmol_min', '--field', 'unit=independent_specimen',
                       '--panel-size-mm', '110', '88', '--font', 'Arial', '--out', str(draft_path)],
                      trace/f'{args.attempt}-draft-command.json', env)
        if drafted.returncode:
            raise SystemExit('Public draft failed; see trace')
        spec = json.loads(draft_path.read_text())
        spec.pop('palette', None)
        spec.update({'colors': COLORS, 'order': {'group': ARMS},
                     'labels': {'x': 'Treatment arm', 'y': 'Activity (nmol/min)'},
                     'formats': ['svg', 'pdf', 'png'], 'seed': 43017,
                     'statistics': {'method': 'none', 'annotate': False}})
        spec['layout'].update({'font': 'Arial', 'font_size_pt': 8, 'width_mm': 110,
                               'height_mm': 88, 'dpi': 300, 'auto_fit': True})
        spec['typography'] = {role: 8 for role in ['axis','tick','legend','annotation','title','panel']}
        spec['options'].update({'kind': 'box', 'orientation': 'vertical',
                                'box_style': 'outline', 'box_width': 0.18,
                                'point_style': 'filled', 'point_area_pt2': 9,
                                'alpha': 1, 'point_layout': 'beeswarm',
                                'point_max_offset_mm': 4, 'point_gap_pt': 0.3,
                                'grid': False, 'y_limits': [8,44]})
    write_json(spec_path, spec)
    rendered = run([sys.executable, str(SKILL/'scripts/render.py'), '--data', str(prepared),
                    '--spec', str(spec_path), '--out', str(attempt), '--track', 'create'],
                   trace/f'{args.attempt}-render-command.json', env)
    # Freeze the first actual exported canvas immediately, before review/repair.
    freeze = {'attempt': args.attempt, 'render_returncode': rendered.returncode,
              'spec_sha256': sha(spec_path), 'files': {str(p.relative_to(ROOT)): sha(p)
                   for p in sorted(attempt.rglob('*')) if p.is_file()}}
    write_json(ROOT/f'{args.attempt}-freeze.json', freeze)
    print(json.dumps({'attempt': str(attempt), 'returncode': rendered.returncode,
                      'independent_specimens': len(grouped), 'font': font_path,
                      'files_frozen': len(freeze['files'])}, indent=2))
    if rendered.returncode:
        print(rendered.stdout)
        print(rendered.stderr)
        raise SystemExit(rendered.returncode)

if __name__ == '__main__':
    main()
