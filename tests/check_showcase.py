"""Independently check showcase exports and source-table transformations."""
from pathlib import Path
import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import pymupdf
from PIL import Image
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'annotated-inhibition': ('examples/create/annotated-inhibition/panel', 180, 160),
    'cell-atlas-dotplot': ('examples/create/cell-atlas-dotplot/output/figure', 180, 120),
    'massier-bmi-violin': ('examples/no-author-code/massier-bmi-violin/panel', 160, 100),
    'massier-integration-radar': ('examples/no-author-code/massier-integration-radar/panel', 88, 88),
}
results = {}
for case, (prefix, width, height) in CASES.items():
    path = ROOT / prefix
    with pymupdf.open(path.with_suffix('.pdf')) as doc:
        assert len(doc) == 1
        page = doc[0]
        size = [page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4]
        np.testing.assert_allclose(size, [width, height], atol=1e-4)
        spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b
                 for line in b['lines'] for s in line['spans'] if s['text'].strip()]
        assert spans and all(abs(s['size'] - 8) < .01 for s in spans)
        assert all(page.rect.contains(pymupdf.Rect(s['bbox'])) for s in spans)
        assert all(len(doc.extract_font(item[0])[3]) > 0 for item in page.get_fonts())
    svg = ET.parse(path.with_suffix('.svg')).getroot()
    svg_mm = [float(svg.attrib[key].removesuffix('pt')) / 72 * 25.4 for key in ('width', 'height')]
    np.testing.assert_allclose(svg_mm, [width, height], atol=1e-4)
    assert svg.findall('.//{http://www.w3.org/2000/svg}text')
    with Image.open(path.with_suffix('.png')) as png:
        assert all(abs(a-b) <= 1 for a,b in zip(png.size, [round(width/25.4*300), round(height/25.4*300)]))
        assert all(abs(d-300) < .01 for d in png.info['dpi'])
        pixels = list(png.size)
    results[case] = {'pdf_mm': size, 'svg_mm': svg_mm, 'png_pixels': pixels,
                     'text_pt': 8, 'font_embedded': True, 'editable_svg_text': True}

# Compare against original published tables where locally available, independently
# of the plotting scripts. A missing external archive is recorded as unverified.
for case in ('massier-bmi-violin', 'massier-integration-radar'):
    folder = ROOT / 'evals/reproduce-inputs' / case
    prov = json.loads((folder / 'provenance.json').read_text())
    prepared = folder / 'source-data.csv'
    assert hashlib.sha256(prepared.read_bytes()).hexdigest() == prov['prepared_csv_sha256']
    original = Path(prov['data_origin'])
    results[case]['original_source_verified'] = original.exists()
    if not original.exists():
        continue
    assert hashlib.sha256(original.read_bytes()).hexdigest() == prov['data_sha256']
    rows = list(csv.DictReader(prepared.open()))
    if case.endswith('violin'):
        raw = list(csv.DictReader(original.open(), delimiter='\t'))
        assert len(rows) == len(raw) == 864
        for lineno, (source, target) in enumerate(zip(raw, rows), 2):
            assert target == {'source_row': str(lineno), 'source_id': source['ID'],
                              'cohort': source['Cohort'], 'bmi': '' if source['BMI'] == 'NA' else source['BMI']}
        results[case].update(source_records=864, bmi_available=sum(bool(r['bmi']) for r in rows))
    else:
        wb = openpyxl.load_workbook(original, data_only=True, read_only=True)
        values = list(wb[prov['worksheet']].iter_rows(min_row=1,max_row=6,min_col=1,max_col=6,values_only=True))
        expected = {(str(row[0]), str(c)): float(v) for row in values[1:] for c,v in zip(values[0][1:], row[1:])}
        actual = {(r['integration_method'],r['cell_class']): float(r['acceptance_rate']) for r in rows}
        assert expected == actual and len(actual) == 25
        results[case].update(source_values=25, zeros=sum(v == 0 for v in actual.values()))
        wb.close()

folder = ROOT / 'examples/create/cell-atlas-dotplot'
prov = json.loads((folder / 'provenance.json').read_text())
original = Path(prov['source_origin'])
prepared = folder / 'source-data.csv'
assert hashlib.sha256(prepared.read_bytes()).hexdigest() == prov['prepared_csv_sha256']
results['cell-atlas-dotplot']['original_source_verified'] = original.exists()
if original.exists():
    assert hashlib.sha256(original.read_bytes()).hexdigest() == prov['source_sha256']
    assert list(csv.DictReader(original.open(), delimiter='\t')) == list(csv.DictReader(prepared.open()))
table = pd.read_csv(prepared)
plotted = pd.read_csv(folder / 'output/plotted-data.csv')
assert len(plotted) == len(table) == 48
np.testing.assert_allclose(plotted.within_depot_percent, 100 * table.n / table.tissue.map(table.groupby('tissue').n.sum()))
assert int(table.n.sum()) == 22539
results['cell-atlas-dotplot'].update(source_rows=48, pooled_objects=22539, proportions_verified=True)

folder = ROOT / 'examples/create/annotated-inhibition'
full = pd.read_csv(folder / 'source-data.csv', dtype={'sender':str}).set_index('sender')
shown = pd.read_csv(folder / 'plotting-data.csv', dtype={'sender':str,'receiver':str})
summary = pd.read_csv(folder / 'summary-data.csv', dtype={'strain':str})
assert full.shape == (76,76) and len(shown) == 400 and len(summary) == 152
for row in shown.itertuples():
    assert row.gii_min == full.loc[row.sender, row.receiver]
for row in summary.itertuples():
    values = full.loc[row.strain] if row.role == 'sender' else full[row.strain]
    assert row.denominator == len(values) == 76
    assert math.isclose(row.full_matrix_mean_gii_min, math.fsum(values)/76, rel_tol=1e-12)
results['annotated-inhibition'].update(source_values=5776, displayed_values=400, full_matrix_means_verified=152,
    source_matches_historical_copy=(folder/'source-data.csv').read_bytes() == (ROOT/'examples/reproduce/microbiology/source-data.csv').read_bytes())
assert results['annotated-inhibition']['source_matches_historical_copy']
report = {'status':'pass','cases':results,'visual_review':'Separate actual-image inspections are recorded with each case; these checks do not prove perceptual equivalence.'}
(ROOT / 'evals/showcase-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
