"""Check exported physical sizes, PDF text, and example data provenance."""
from pathlib import Path
import csv
import hashlib
import json
import math
import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
results = {}
for domain in ('microbiology', 'singlecell'):
    folder = ROOT / 'examples' / 'reproduce' / domain
    cfg = json.loads((folder / 'figure-settings.json').read_text())
    with pymupdf.open(folder / 'panel.pdf') as doc:
        assert len(doc) == 1
        page = doc[0]
        dimensions = [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]
        assert all(abs(a - b) < .01 for a, b in zip(dimensions, [cfg['width_mm'], cfg['height_mm']]))
        spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'] if s['text'].strip()]
        assert spans, 'Expected editable PDF text'
        assert all(abs(s['size'] - cfg['font_size_pt']) < .05 for s in spans)
        assert all(page.rect.contains(pymupdf.Rect(s['bbox'])) for s in spans), 'Text outside exported PDF page'
        fonts = sorted({s['font'] for s in spans})
    with Image.open(folder / 'panel.png') as img:
        expected = [round(cfg[k] / 25.4 * cfg['dpi']) for k in ('width_mm', 'height_mm')]
        assert all(abs(a-b) <= 1 for a,b in zip(img.size, expected))
        assert all(abs(d-cfg['dpi']) < .1 for d in img.info['dpi'])
        pixels = list(img.size)
    results[domain] = {'pdf_mm': dimensions, 'png_pixels': pixels, 'pdf_text_sizes_pt': sorted({round(s['size'], 3) for s in spans}), 'pdf_fonts': fonts}

folder = ROOT / 'examples/reproduce/singlecell'
raw = list(csv.reader((folder / 'original-counts.tsv').open(), delimiter='\t'))
expected = {(rep, row[0]): int(value) for row in raw[1:] for rep, value in zip(raw[0], row[1:])}
actual_rows = list(csv.DictReader((folder / 'source-data.csv').open()))
actual = {(r['replicate'], r['cell_type']): int(r['cell_count']) for r in actual_rows}
assert len(actual_rows) == len(actual) == len(expected) == 144 and actual == expected
provenance = json.loads((folder / 'provenance.json').read_text())
assert hashlib.sha256((folder / 'original-counts.tsv').read_bytes()).hexdigest() == provenance['source_sha256']
derived = list(csv.DictReader((folder / 'derived-data.csv').open()))
types = {'Luminal-AV', 'Luminal-HS', 'Myoepithelial'}
for row in derived:
    rep, ct = row['replicate'], row['cell_type']
    total = sum(expected[rep, t] for t in types)
    assert int(row['cell_count']) == expected[rep, ct] and int(row['epithelial_total']) == total
    assert math.isclose(float(row['percent_of_epithelial']), 100 * expected[rep, ct] / total)
assert len(derived) == 36
results['singlecell']['source_counts_verified'] = len(actual)
results['singlecell']['source_cell_total'] = sum(actual.values())

folder = ROOT / 'examples/reproduce/microbiology'
rows = list(csv.reader((folder / 'source-data.csv').open()))
matrix = {(r[0], c): float(v) for r in rows[1:] for c,v in zip(rows[0][1:],r[1:])}
assert len(matrix) == 76*76
selected = list(csv.DictReader((folder / 'selected-data.csv').open()))
assert len(selected) == 144 and len({(r['sender'],r['receiver']) for r in selected}) == 144
assert all(float(r['gii_min']) == matrix[r['sender'],r['receiver']] for r in selected)
provenance = json.loads((folder / 'provenance.json').read_text())
original = Path(provenance['original_files'][0]['path'])
if original.exists():
    assert hashlib.sha256(original.read_bytes()).hexdigest() == provenance['original_files'][0]['sha256']
    raw = list(csv.reader(original.open(), delimiter=';'))
    original_values = {(r[0], c): float(v.replace(',', '.')) for r in raw[1:] for c,v in zip(raw[0][1:],r[1:]) if c != 'EGDe'}
    assert original_values == matrix
results['microbiology']['original_values_compared'] = original.exists()
results['microbiology']['matrix_values_verified'] = len(matrix)
results['microbiology']['selected_values_verified'] = len(selected)
report = {'passed': True, 'checks': results, 'visual_review': 'Separate human/Agent inspection required; this script does not claim perceptual equivalence.'}
(ROOT / 'examples/validation-summary.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
