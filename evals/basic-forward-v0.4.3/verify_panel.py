#!/usr/bin/env python3
"""Independent checks of the saved source, plotted rows and actual exports.

This does not redraw the manuscript panel. It saves inspection rasters and
measurements outside the immutable attempt directory.
"""
from pathlib import Path
from collections import defaultdict, Counter
import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET

import pymupdf as fitz
from PIL import Image

ROOT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    attempt = ROOT / args.attempt
    out = ROOT / 'qa' / args.attempt
    out.mkdir(parents=True, exist_ok=True)
    source = read_csv(ROOT/'data/source/assays.csv')
    plotted = read_csv(attempt/'plotting-data.csv')
    source_values = defaultdict(list)
    for row in source:
        source_values[(row['arm'], row['biospecimen_key'])].append(float(row['enzyme_velocity']))
    means = {key: statistics.mean(values) for key, values in source_values.items()}
    plotted_keys = [(row['arm'], row['biospecimen_key']) for row in plotted]
    row_counts = Counter(plotted_keys)
    errors = [abs(float(row['activity_nmol_min']) - means[(row['arm'],row['biospecimen_key'])]) for row in plotted]
    data_check = {
        'status': 'passed' if set(plotted_keys) == set(means) and all(n == 1 for n in row_counts.values())
                 and len(plotted) == 33 and max(errors) < 1e-10 else 'failed',
        'method': 'Independent csv grouping by arm + ID, Python statistics.mean; direct saved-row comparison.',
        'source_rows': len(source), 'expected_units': len(means), 'plotted_rows': len(plotted),
        'unit_set_exact': set(plotted_keys) == set(means), 'duplicate_unit_rows': sum(n-1 for n in row_counts.values()),
        'maximum_mean_absolute_error': max(errors), 'counts_by_arm': dict(Counter(row['arm'] for row in plotted)),
        'numeric_y_values_preserved': True,
    }
    summaries = {}
    for arm in ['Vehicle','Dose 1','Dose 2']:
        values = [value for (group, unit), value in means.items() if group == arm]
        q1, median, q3 = statistics.quantiles(values, n=4, method='inclusive')
        inside = [value for value in values if q1-1.5*(q3-q1) <= value <= q3+1.5*(q3-q1)]
        summaries[arm] = {'n':len(values), 'q1':q1,'median':median,'q3':q3,
                          'whisker_low':min(inside), 'whisker_high':max(inside)}
    audit = json.loads((ROOT/'data/data-audit.json').read_text())
    summary_error = max(abs(value-audit['descriptive_summaries'][arm][key])
                        for arm, summary in summaries.items() for key, value in summary.items() if key != 'n')
    settings = json.loads((attempt/'settings.json').read_text())
    svg = ET.parse(attempt/'panel.svg').getroot()
    svg_dimensions_mm = [float(svg.attrib[key].removesuffix('pt'))*25.4/72 for key in ['width','height']]
    svg_text = [element for element in svg.iter() if element.tag.endswith('text')]
    text_content = [''.join(element.itertext()) for element in svg_text]
    svg_font_styles = sorted(set(element.attrib.get('style','') for element in svg_text))
    # Check the saved vector geometry itself, rather than trusting a renderer
    # settings record to prove that the summaries were drawn at correct values.
    height_pt = float(svg.attrib['height'].removesuffix('pt'))
    margins = settings['layout']['margins']
    y_low, y_high = settings['options']['y_limits']
    svg_bottom = height_pt * (1 - margins['bottom'])
    svg_span = height_pt * (margins['top'] - margins['bottom'])
    def y_value(y_svg):
        return y_low + (svg_bottom-y_svg)/svg_span*(y_high-y_low)
    paths = []
    for element in svg.iter():
        if not element.tag.endswith('path') or 'stroke-width: 0.75' not in element.attrib.get('style',''):
            continue
        numbers = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?',element.attrib.get('d',''))]
        if len(numbers) == 4:
            paths.append(numbers)
    box_groups = [element for element in svg.iter()
                  if element.attrib.get('id','').startswith('easyviz-distribution-')]
    drawn = {}
    for arm, group in zip(['Vehicle','Dose 1','Dose 2'],box_groups):
        box_path = next(element for element in group.iter() if element.tag.endswith('path'))
        numbers = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?',box_path.attrib['d'])]
        xs, ys = numbers[::2], numbers[1::2]
        x_left, x_right = min(xs), max(xs)
        x_center = (x_left+x_right)/2
        median_segments = [p for p in paths if abs(p[0]-x_left)<1e-4 and abs(p[2]-x_right)<1e-4
                           and abs(p[1]-p[3])<1e-5]
        caps = [p for p in paths if abs((p[0]+p[2])/2-x_center)<1e-4 and abs(p[1]-p[3])<1e-5
                and abs(abs(p[2]-p[0])-(x_right-x_left)/2)<1e-4]
        if len(median_segments)!=1 or len(caps)!=2:
            raise ValueError(f'Actual SVG summaries could not be identified unambiguously: {arm}')
        endpoints = sorted(y_value(p[1]) for p in caps)
        drawn[arm] = {'q1':y_value(max(ys)), 'q3':y_value(min(ys)),
                      'median':y_value(median_segments[0][1]),
                      'whisker_low':endpoints[0], 'whisker_high':endpoints[1]}
    drawn_error = max(abs(value-summaries[arm][key]) for arm,summary in drawn.items()
                      for key,value in summary.items())
    doc = fitz.open(attempt/'panel.pdf')
    page = doc[0]
    pdf_dimensions_mm = [page.rect.width*25.4/72, page.rect.height*25.4/72]
    spans = [span for block in page.get_text('dict')['blocks'] if 'lines' in block
             for line in block['lines'] for span in line['spans']]
    font_sizes = sorted(set(span['size'] for span in spans))
    font_names = sorted(set(span['font'] for span in spans))
    embedded = [{'base_font':font[3], 'type':font[2], 'bytes':len(doc.extract_font(font[0])[3])}
                for font in page.get_fonts(full=True)]
    page.get_pixmap(dpi=96, alpha=False).save(out/'pdf-96dpi.png')
    page.get_pixmap(dpi=150, alpha=False).save(out/'pdf-150dpi.png')
    image = Image.open(attempt/'panel.png')
    png_dimensions = list(image.size)
    png_dpi = list(image.info.get('dpi',[]))
    preview_pixels = [round(mm/25.4*96) for mm in [110,88]]
    image.resize(preview_pixels, Image.Resampling.LANCZOS).save(out/'png-96dpi.png')
    dim_ok = all(abs(actual-target)<0.001 for pair in [pdf_dimensions_mm,svg_dimensions_mm]
                 for actual,target in zip(pair,[110,88]))
    pixels_ok = png_dimensions == [round(mm/25.4*300) for mm in [110,88]]
    font_ok = font_sizes == [8.0] and font_names == ['ArialMT'] and all(font['bytes']>0 for font in embedded)
    stats = json.loads((attempt/'stats.json').read_text())
    freeze = json.loads((ROOT/f'{args.attempt}-freeze.json').read_text())
    frozen_unchanged = all(sha(ROOT/path)==expected for path,expected in freeze['files'].items())
    report = {
        'scope': str(attempt), 'source_grain_and_points': data_check,
        'descriptive_summaries': {'status':'passed' if summary_error<1e-10 else 'failed',
            'method':'Python statistics.quantiles inclusive, independently recomputed from original reads.',
            'maximum_difference_from_preparation_audit':summary_error,'values':summaries},
        'actual_drawn_summary_geometry': {'status':'passed' if drawn_error<1e-6 else 'failed',
            'tool':'Actual SVG box patch extrema, median segments and whisker-cap segments; invert documented physical axis mapping.',
            'maximum_error_nmol_min':drawn_error,'values':drawn},
        'actual_export_dimensions': {'status':'passed' if dim_ok and pixels_ok else 'failed',
            'tool':'PyMuPDF page.rect; XML SVG width/height; Pillow PNG size/info',
            'pdf_mm':pdf_dimensions_mm,'svg_mm':svg_dimensions_mm,
            'png_pixels':png_dimensions,'png_dpi':png_dpi},
        'actual_typography': {'status':'passed' if font_ok else 'failed',
            'tool':'PyMuPDF actual text spans and extract_font; SVG text style inspection',
            'pdf_span_sizes_pt':font_sizes,'pdf_span_fonts':font_names,'pdf_embedded_fonts':embedded,
            'svg_font_styles':svg_font_styles,'actual_font_record':settings['layout']['actual_font'],
            'font_substituted':settings['layout']['font_substituted']},
        'panel_text': {'status':'passed' if 'Treatment arm' in text_content and 'Activity (nmol/min)' in text_content
                      and not settings['labels'].get('title') and not settings['labels'].get('panel') else 'failed',
                      'svg_text':text_content,'pdf_text':page.get_text()},
        'inference': {'status':'passed' if settings['statistics']['method']=='none' else 'failed',
                      'requested_method':settings['statistics']['method'],'saved_stats':stats},
        'first_render_freeze': {'status':'passed' if frozen_unchanged else 'failed',
                               'files_compared':len(freeze['files'])},
        'inspection_rasters': ['pdf-96dpi.png','png-96dpi.png','pdf-150dpi.png'],
        'inspection_note': '96 dpi whole-canvas rasters model a nominal screen size; calibrated physical print viewing is unavailable. Actual mm/page and 8 pt font measurements accompany visual inspection.',
        'visual_review': 'pending; these numeric checks do not establish palette distinction or point/summary occlusion.'
    }
    (out/'actual-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value.get('status') for key,value in report.items() if isinstance(value,dict)},indent=2))

if __name__=='__main__':
    main()
