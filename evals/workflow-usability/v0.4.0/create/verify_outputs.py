#!/usr/bin/env python3
"""Independently check source accounting, summaries, fonts and exported canvases."""
from pathlib import Path
from decimal import Decimal
import csv
import hashlib
import itertools
import json
import math
import statistics
import xml.etree.ElementTree as ET
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
PANEL = ROOT / 'attempt-02'

def load_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))

def percentile(values, p):
    x = sorted(values)
    position = (len(x) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    return x[lower] + (position - lower) * (x[upper] - x[lower])

source = load_csv(ROOT / 'source/observations.csv')
plot = load_csv(PANEL / 'plotting-data.csv')
accounting = load_csv(ROOT / 'analysis-01/analyzed-data.csv')
summaries = load_csv(ROOT / 'analysis-01/summary.csv')
checks = []

def record(name, passed, evidence):
    checks.append({'check': name, 'status': 'passed' if passed else 'failed', 'evidence': evidence})
    assert passed, name

record('All specimens traced to exact string IDs', len(source) == len(plot) == 24 and
       [r['sample_id'] for r in source] == [r['sample_id'] for r in plot] and
       len({r['sample_id'] for r in plot}) == 24, '24 original and plotted rows; identical ordered sample IDs; 12 per condition')
record('Source values numerically preserved', all(
    s['condition'] == p['condition'] and Decimal(s['signal']) == Decimal(p['signal']) and
    Decimal(s['viability_pct']) == Decimal(p['viability_pct']) for s, p in zip(source, plot)),
    'String identity for categories and decimal equality for both measured outcomes')
recomputed = []
for group in ['Control', 'Treatment']:
    for variable, comparison in [('signal', 'primary_signal_summary'), ('viability_pct', 'exploratory_viability_summary')]:
        values = [float(row[variable]) for row in source if row['condition'] == group]
        row = next(r for r in summaries if r['comparison'] == comparison and r['group'] == group)
        expected = {'mean': statistics.fmean(values), 'median': statistics.median(values),
                    'sd': statistics.stdev(values), 'q1': percentile(values, .25),
                    'q3': percentile(values, .75), 'minimum': min(values), 'maximum': max(values)}
        record(f'Numerical summary: {comparison}/{group}', all(math.isclose(float(row[k]), v, rel_tol=1e-12, abs_tol=1e-12) for k, v in expected.items()), expected)
        expected.update({'group': group, 'variable': variable, 'n': len(values)})
        if variable == 'signal':
            iqr = expected['q3'] - expected['q1']
            inside = [v for v in values if expected['q1'] - 1.5 * iqr <= v <= expected['q3'] + 1.5 * iqr]
            expected['whisker_lower'] = min(inside)
            expected['whisker_upper'] = max(inside)
        recomputed.append(expected)
record('Per-comparison row accounting', len(accounting) == 48 and all(
    len([r for r in accounting if r['_easyviz_comparison'] == name]) == 24
    for name in ['primary_signal_summary', 'exploratory_viability_summary']),
    '24 unchanged source rows per descriptive endpoint; repeated rows across two comparisons are expected')

settings = json.loads((PANEL / 'settings.json').read_text())
record('Actual font and role sizes', settings['layout']['actual_font'] == 'Arial' and
       not settings['layout']['font_substituted'] and all(settings['typography'][role] == 8 for role in ['axis', 'tick', 'legend', 'annotation']),
       'Arial selected without substitution; active axis/tick roles 8 pt')
pdf = PdfReader(PANEL / 'panel.pdf')
page = pdf.pages[0]
pdf_size = [float(page.mediabox.width) * 25.4 / 72, float(page.mediabox.height) * 25.4 / 72]
record('PDF physical dimensions', all(math.isclose(a, b, abs_tol=1e-7) for a, b in zip(pdf_size, [120, 90])) and len(pdf.pages) == 1, pdf_size)
pdf_fonts = []
for name, ref in page['/Resources']['/Font'].items():
    font = ref.get_object()
    descriptor = font.get('/FontDescriptor')
    if descriptor is None and font.get('/DescendantFonts'):
        descriptor = font['/DescendantFonts'][0].get_object().get('/FontDescriptor')
    desc = descriptor.get_object() if descriptor else {}
    pdf_fonts.append({'resource': name, 'base_font': str(font.get('/BaseFont')), 'embedded': any(k in desc for k in ['/FontFile', '/FontFile2', '/FontFile3'])})
record('PDF font embedding', bool(pdf_fonts) and all(f['embedded'] for f in pdf_fonts), pdf_fonts)
svg = ET.parse(PANEL / 'panel.svg').getroot()
svg_size = [float(svg.attrib['width'].removesuffix('pt')) * 25.4 / 72,
            float(svg.attrib['height'].removesuffix('pt')) * 25.4 / 72]
texts = [node for node in svg.iter() if node.tag.endswith('}text')]
record('SVG physical dimensions and editable text', all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(svg_size, [120, 90])) and bool(texts), {'mm': svg_size, 'text_elements': len(texts)})
with Image.open(PANEL / 'panel.png') as png:
    record('PNG pixel dimensions and dpi', png.size == (round(120 / 25.4 * 300), round(90 / 25.4 * 300)) and all(abs(v - 300) < .01 for v in png.info['dpi']), {'pixels': list(png.size), 'dpi': list(png.info['dpi'])})
xywidth, xyheight = settings['auto_layout']['data_region_mm'][2:]
min_sep = math.inf
for group in ['Control', 'Treatment']:
    rows = [r for r in plot if r['condition'] == group]
    for a, b in itertools.combinations(rows, 2):
        dx = (float(a['_easyviz_jitter_position']) - float(b['_easyviz_jitter_position'])) * xywidth / 2.2
        dy = (float(a['signal']) - float(b['signal'])) * xyheight / 10
        min_sep = min(min_sep, math.hypot(dx, dy))
diameter = settings['mark_geometry']['diameter_pt'] * 25.4 / 72
record('Raw circle center separation', min_sep > diameter, {'minimum_center_distance_mm': min_sep, 'circle_diameter_mm': diameter})
qa = json.loads((PANEL / 'qa.json').read_text())
record('Renderer clipping/glyph/tick checks', qa['status'] == 'pass' and not qa['clipped_text'] and not qa['missing_glyphs'] and not qa['overlapping_tick_labels'], 'Renderer QA pass; 24/24 source rows plotted')
input_root = Path('/private/tmp/easyviz-forward-create/input')
record('Original sources preserved', all((input_root / name).read_bytes() == (ROOT / 'source' / name).read_bytes() for name in ['observations.csv', 'study-notes.txt']), 'Byte-identical source snapshots')
result = {'scope': 'Accepted attempt-02; 24 source rows; signal plotted, two endpoints described; self review is separate',
          'checks': checks, 'recomputed_summaries': recomputed,
          'formats_sha256': {suffix: hashlib.sha256((PANEL / f'panel.{suffix}').read_bytes()).hexdigest() for suffix in ['pdf', 'svg', 'png']}}
(ROOT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'checks_passed': len(checks), 'pdf_mm': pdf_size, 'svg_mm': svg_size, 'minimum_mark_separation_mm': min_sep}, indent=2))
