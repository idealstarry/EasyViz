"""Verify the generated ZIP runs without the development tree or source archives."""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tempfile
import zipfile
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', type=Path, default=ROOT / 'evals/plugin-validation.json')
args = parser.parse_args()
build = json.loads((ROOT / 'dist/build.json').read_text())
archive = ROOT / 'dist' / build['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == build['sha256']
checks = {}
with tempfile.TemporaryDirectory(prefix='easyviz-package-') as temporary:
    sandbox = Path(temporary)
    with zipfile.ZipFile(archive) as zip_file:
        names = zip_file.namelist()
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
        assert not any('/.venv/' in n or '/__pycache__/' in n or 'original-counts.tsv' in n for n in names)
        assert not any(n.endswith('.R') or n.endswith('.Rmd') for n in names)
        assert not any('/recipes/annotated-heatmap/source-data.csv' in n for n in names)
        zip_file.extractall(sandbox)
    plugin = sandbox / 'easyviz'
    skill = plugin / 'skills/easyviz'
    manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text())
    assert manifest['name'] == plugin.name == 'easyviz'
    assert all((plugin / 'skills' / n / 'SKILL.md').exists() for n in ('easyviz','easyviz-reference-reader','easyviz-figure-reviewer'))

    def run(*args):
        result = subprocess.run([sys.executable, *map(str, args)], cwd=sandbox, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr

    fixture = skill / 'assets/fixtures/heatmap'
    run(skill / 'scripts/render.py', '--data', fixture / 'data.csv', '--spec', fixture / 'spec.json', '--out', sandbox / 'core-output')
    assert json.loads((sandbox / 'core-output/qa.json').read_text())['status'] == 'pass'
    checks['core_renderer'] = 'pass'
    for case in ('cell-atlas-dotplot','massier-bmi-violin','massier-integration-radar','paired-effects'):
        folder = skill / 'assets/cases' / case
        image_file = folder / ('output/figure.png' if case == 'cell-atlas-dotplot' else 'panel.png')
        with Image.open(image_file) as image:
            before = image.convert('RGBA').copy()
        run(folder / 'plot.py')
        with Image.open(image_file) as image:
            after = image.convert('RGBA')
            assert before.size == after.size
            assert ImageChops.difference(before, after).getbbox(alpha_only=False) is None, f'Portable render pixels differ: {case}'
        checks[case] = 'pass; rerendered PNG pixels match the reviewed bundled preview'
    paired = skill / 'assets/cases/paired-myeloid-remodeling'
    run(paired / 'plot.py', '--out', sandbox / 'paired-output')
    paired_qa = json.loads((sandbox / 'paired-output/qa.json').read_text())
    assert paired_qa['status'] == 'passed' and paired_qa['paired_changes'] == 832
    assert paired_qa['paired_participants'] == 52 and paired_qa['missing_pairs'] == 0
    for design in ('baseline', 'participant-matrix', 'distribution-ledger'):
        with Image.open(paired / 'output' / design / 'panel.png') as bundled, Image.open(sandbox / 'paired-output' / design / 'panel.png') as rerendered:
            assert bundled.size == rerendered.size
            assert ImageChops.difference(bundled.convert('RGBA'), rerendered.convert('RGBA')).getbbox(alpha_only=False) is None, design
    checks['paired_myeloid_alternatives'] = 'pass; all three PNGs match reviewed previews; 832 matched changes from prepared CSV'
    run(paired / 'plot.py', '--year', '5', '--cohorts', 'Kerr', '--design', 'participant-matrix', '--out', sandbox / 'paired-transfer')
    paired_transfer = json.loads((sandbox / 'paired-transfer/qa.json').read_text())
    assert paired_transfer['status'] == 'passed' and paired_transfer['paired_changes'] == 592
    assert paired_transfer['paired_participants'] == 37 and paired_transfer['cohorts'] == {'Kerr': 37}
    with Image.open(paired / 'transfer-five-year/participant-matrix/panel.png') as bundled, Image.open(sandbox / 'paired-transfer/participant-matrix/panel.png') as rerendered:
        assert bundled.size == rerendered.size
        assert ImageChops.difference(bundled.convert('RGBA'), rerendered.convert('RGBA')).getbbox(alpha_only=False) is None
    checks['paired_myeloid_same_study_transfer'] = 'pass; same recipe on 592 five-year changes, without original workbook or author code'
    forest = skill / 'assets/cases/paired-effects'
    run(forest / 'plot.py', '--data', forest / 'evaluation/source.csv',
        '--settings', forest / 'evaluation/figure-settings.json', '--out', sandbox / 'forest-transfer')
    forest_qa = json.loads((sandbox / 'forest-transfer/numeric-qa.json').read_text())
    assert forest_qa['status'] == 'passed' and forest_qa['terms'] == 5 and forest_qa['cohorts'] == 3
    assert forest_qa['displayed_points'] == forest_qa['displayed_intervals'] == 15
    checks['forest_renamed_field_transfer'] = 'pass; five terms, three cohorts and renamed field mappings preserve all 15 supplied asymmetric intervals'
    recipe = skill / 'assets/recipes/annotated-heatmap'
    ids = ['001','002','003','004']
    with (sandbox / 'matrix.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['sender',*ids])
        for i, strain in enumerate(ids):
            w.writerow([strain,*[i*4+j-3 for j in range(4)]])
    with (sandbox / 'genome.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['strain','genome']); w.writerows((strain,0) for strain in ids)
    config = json.loads((recipe / 'settings.json').read_text())
    config.update(selection_count=4, color_limits=[-5,15])
    for key in ('receiver_mean_limits','receiver_mean_ticks','sender_mean_limits','sender_mean_ticks'):
        config.pop(key, None)
    (sandbox / 'recipe.json').write_text(json.dumps(config))
    run(recipe / 'plot.py', '--data', sandbox / 'matrix.csv', '--genome', sandbox / 'genome.csv',
        '--settings', sandbox / 'recipe.json', '--out', sandbox / 'recipe-output')
    qa = json.loads((sandbox / 'recipe-output/qa.json').read_text())
    assert qa['status'] == 'pass' and qa['selected_measurements'] == 16 and qa['summary_denominator'] == 4
    selected = list(csv.DictReader((sandbox / 'recipe-output/plotting-data.csv').open()))
    assert {r['sender'] for r in selected} == set(ids)
    checks['annotated_heatmap_recipe'] = 'pass; separate synthetic 4×4 matrix, leading-zero IDs, constant binary annotation, negative values and automatic means'
report = {'status':'pass','archive':build['archive'],'archive_sha256':build['sha256'],
          'extracted_file_count':len(names),'checks':checks,
          'environment': {'python': platform.python_version(), 'platform': platform.system(),
                          'packages': {name: importlib.metadata.version(name) for name in ('matplotlib','numpy','pandas','scipy','Pillow','pypdf','PyMuPDF')}},
          'scope':'Isolated extracted files and different working directory in the recorded Python environment, using fonts available on this host. No original paper archives or author code are required. Not a fresh operating-system installation or Codex automatic-discovery test.'}
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
