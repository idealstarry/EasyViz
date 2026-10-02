#!/usr/bin/env python3
"""Replay this data-specific create task from raw reads using captured helpers.

Run with the project Python: run_analysis_plot.py --run-dir /path/to/new-run
The run directory must not exist. The raw input and helper snapshot remain intact.
"""
import argparse
import csv
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'input' / 'data'
HELPERS = ROOT / 'helper_snapshot'
GROUPS = ['Vehicle', 'Low dose', 'High dose']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def execute(helper, *arguments):
    env = dict(os.environ)
    env['MPLCONFIGDIR'] = str(ROOT / '.matplotlib-cache')
    subprocess.run([sys.executable, str(HELPERS / 'scripts' / helper), *map(str, arguments)],
                   check=True, cwd=ROOT, env=env)

def prepare(run):
    with (DATA / 'sample-index__2026.tsv.csv').open(newline='', encoding='utf-8') as f:
        index_rows = list(csv.DictReader(f))
    with (DATA / 'A_export__final2.csv').open(newline='', encoding='utf-8') as f:
        raw = list(csv.DictReader(f))
    lookup = {r['tube_key']:r for r in index_rows}
    assert len(lookup) == len(index_rows) == 36, 'One unique lookup row per mouse required'
    assert all(len(k) == 4 and k.startswith('0') for k in lookup), 'Literal padded IDs required'
    assert all(r['unit_type'] == 'individual_mouse' for r in index_rows)
    assert Counter(r['arm_name'] for r in index_rows) == Counter({g:12 for g in GROUPS})
    assert len(raw) == 72 and len({r['read_key'] for r in raw}) == 72
    assert {r['tube_key'] for r in raw} == set(lookup)
    by_unit = defaultdict(list)
    for row_number, r in enumerate(raw, start=2):
        assert r['tube_key'] == r['tube_key'].strip()
        r['_source_csv_row'] = row_number
        by_unit[r['tube_key']].append(r)
    output = []
    accounting = []
    failures = []
    for group in GROUPS:
        for ident in sorted(k for k,v in lookup.items() if v['arm_name'] == group):
            reads = by_unit[ident]
            assert len(reads) == 2, f'{ident}: exactly two scheduled reads required'
            values = []
            for r in reads:
                if r['signal_au'] == '':
                    assert r['read_state'] == 'failed'
                    failures.append({'specimen_id':ident,'read_key':r['read_key'],
                                     'source_csv_row':r['_source_csv_row'],'reason':'failed technical read'})
                else:
                    assert r['read_state'] == 'measured'
                    value = Decimal(r['signal_au'])
                    assert value.is_finite()
                    values.append(value)
            assert values, f'{ident}: no measured read available'
            mean = sum(values) / Decimal(len(values))
            output.append({'specimen_id':ident,'group':group,'mean_signal':str(mean)})
            accounting.append({'specimen_id':ident,'group':group,'technical_rows':len(reads),
                               'measured_reads':len(values),'mean_signal':str(mean),
                               'read_keys':[r['read_key'] for r in reads],
                               'raw_source_rows':[r['_source_csv_row'] for r in reads]})
    assert len(output) == 36 and len(failures) == 1
    with (run / 'plotting_data.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['specimen_id','group','mean_signal'])
        w.writeheader()
        w.writerows(output)
    save_json(run / 'preparation.json', {
        'evidence':'input/data/DATA_DICTIONARY.md',
        'unit':'one independently sampled mouse',
        'operation':'literal-ID join current reads to lookup; arithmetic mean of available measured reads per mouse',
        'source_rows':72, 'measured_reads':71, 'failed_technical_reads':failures,
        'final_rows':36, 'group_counts':{g:12 for g in GROUPS},
        'exclusions_from_scientific_analysis':['old-pilot_DO_NOT_POOL.csv: separate historical study',
                                              'plate-blank_readings.csv: QC; signal already corrected',
                                              'instrument-log.csv: contextual notes'],
        'missing_policy':'failed technical read omitted from its within-mouse mean; mouse retained; no specimen excluded',
        'source_files':[{ 'path':str(p),'sha256':sha(p)} for p in sorted(DATA.iterdir()) if p.is_file()],
        'plotting_data_sha256':sha(run/'plotting_data.csv'), 'unit_accounting':accounting})

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if run.exists():
        raise SystemExit('Choose a new run directory; preserved attempts are not overwritten.')
    for entry in json.loads((HELPERS / 'snapshot-manifest.json').read_text()):
        assert sha(HELPERS / entry['relative_path']) == entry['sha256'], 'Captured helper changed'
    run.mkdir(parents=True)
    prepare(run)
    plan = {
        'schema_version':1,
        'question':'Do the mouse-level signal distributions differ for each dose relative to Vehicle?',
        'design':{'unit':'specimen_id','unit_definition':'One independently sampled mouse; mean of available measured technical reads',
                  'structure':'independent','confirmed':True},
        'missing_policy':'error','missing_tokens':[''],
        'comparisons':[
            {'name':'distribution_overview','method':'descriptive','fields':{'group':'group','value':'mean_signal'}},
            {'name':'low_vs_vehicle','method':'mannwhitney','fields':{'group':'group','value':'mean_signal'},
             'groups':['Low dose','Vehicle']},
            {'name':'high_vs_vehicle','method':'mannwhitney','fields':{'group':'group','value':'mean_signal'},
             'groups':['High dose','Vehicle']}],
        'multiplicity':{'family':'Two prespecified dose comparisons versus Vehicle','adjustment':'holm',
                        'comparisons':['low_vs_vehicle','high_vs_vehicle']}}
    save_json(run / 'analysis-plan.json', plan)
    (run/'analysis-rationale.md').write_text('''# Analysis fixed before inference

The data dictionary establishes 36 independent mice in three independent arms.
Technical reads are averaged within each mouse; neither reads nor handling racks
are independent units. This question concerns distribution shifts rather than a
specific parametric mean model. Two-sided Mann–Whitney comparisons are planned
for each dose versus Vehicle, with Holm family-wise adjustment across both tests.
No normality screening or test-selection search is used.

The null is equality of the two distributions under independent sampling and
exchangeability under that null. It is not generally a test of equal medians.
Cliff's delta is first-dose minus Vehicle in probability terms:
P(dose > Vehicle) − P(dose < Vehicle). Positive values indicate higher dose-arm
signals. The helper supplies no effect confidence interval for this method.
Boxes display observed quartiles and whiskers, not confidence intervals.
The two comparisons form one family; no Low-versus-High test is run.
''')
    execute('analyze.py', '--data', run/'plotting_data.csv', '--plan', run/'analysis-plan.json', '--out', run/'statistics')
    execute('draft_spec.py', '--data', run/'plotting_data.csv', '--chart', 'distribution',
            '--field', 'group=group', '--field', 'value=mean_signal', '--field', 'unit=specimen_id',
            '--panel-size-mm', 120, 90, '--font', 'Arial', '--out', run/'draft-spec.json')
    spec = json.loads((run/'draft-spec.json').read_text())
    spec['layout'].update(font_size_pt=8, line_width_pt=0.6, dpi=300)
    spec.update(typography={k:8 for k in ['axis','tick','legend','annotation','title','panel']},
                colors={'Vehicle':'#29ACF3','Low dose':'#E47751','High dose':'#007F7F'},
                palette='somerville-bright', order={'group':GROUPS},
                labels={'x':'','y':'Signal (a.u.)'}, formats=['pdf','svg','png'], seed=23,
                options={'kind':'box','orientation':'vertical','point_layout':'beeswarm',
                         'point_area_pt2':16,'point_max_offset_mm':4,'point_gap_pt':0.3,'alpha':1,'grid':True},
                statistics={'method':'none','annotate':False})
    save_json(run/'plot-spec.json', spec)
    execute('render.py','--data',run/'plotting_data.csv','--spec',run/'plot-spec.json',
            '--out',run/'panel','--track','create')
    save_json(run/'run-provenance.json', {'run_dir':str(run),'script':str(Path(__file__).resolve()),
         'script_sha256':sha(Path(__file__)), 'python':sys.executable,
         'helper_snapshot':str(HELPERS),'helper_manifest_sha256':sha(HELPERS/'snapshot-manifest.json'),
         'plotting_data_used_for':'Both analyze.py and render.py receive this exact plotting_data.csv',
         'plotting_data_sha256':sha(run/'plotting_data.csv')})
    print(json.dumps({'status':'rendered','run_dir':str(run)}))

if __name__ == '__main__':
    main()
