"""Independent read-only audit of the two frozen exports, without renderer imports."""
from pathlib import Path
import csv
import hashlib
import json
import math
import statistics
import xml.etree.ElementTree as ET
from collections import Counter

import pymupdf
from PIL import Image

REPO = Path('/Users/starry/Desktop/EasyViz')
CASE = REPO / 'evals/create-purpose-overhaul-v0.4.4'
RUN = CASE / 'fresh-run'
OUT = RUN / 'independent-artifacts'
OUT.mkdir(exist_ok=True)
PT_MM = 72 / 25.4
SOURCE_FIELDS = ['population', 'condition', 'normalized_count', 'source_sheet', 'source_cell']

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rows(path):
    with Path(path).open(newline='') as f:
        return list(csv.DictReader(f))

def match_freeze(path, key):
    data = json.loads(path.read_text())
    return [{'path': r['path'], 'expected': r['sha256'],
             'actual': sha(r['path']), 'matches': sha(r['path']) == r['sha256']}
            for r in data[key]]

source = rows(CASE / 'source-intake/observations.csv')
contract = json.loads((CASE / 'source-intake/input-contract.json').read_text())
groups = {(p, c): [r for r in source if (r['population'], r['condition']) == (p, c)]
          for p in contract['population_order'] for c in contract['condition_order']}
stats = {}
for key, rr in groups.items():
    values = [float(r['normalized_count']) for r in rr]
    stats[key] = {'n': len(values), 'mean': statistics.mean(values),
                  'sample_sd': statistics.stdev(values),
                  'sem': statistics.stdev(values) / math.sqrt(len(values)),
                  'min': min(values), 'max': max(values)}

freeze_checks = {
    'baseline': match_freeze(RUN / 'baseline/final-manifest.json', 'files'),
    'with_skill': match_freeze(RUN / 'with-skill/first-finished-delivery-freeze.json', 'artifacts'),
}
task_freeze = json.loads((RUN / 'inputs-and-workflow-freeze.json').read_text())
input_checks = []
for p in ['fresh-task.md', 'source-intake/observations.csv', 'source-intake/input-contract.json']:
    path = CASE / p
    expected = task_freeze['task_and_current_workflow_sha256'][str(path.relative_to(REPO))]
    input_checks.append({'path': str(path), 'expected': expected, 'actual': sha(path),
                         'matches': expected == sha(path)})

evidence = {
    'method': 'Direct source CSV recomputation and PDF drawing/text extraction; no plotting code executed and no helper QA used as evidence.',
    'scope': 'Two non-blinded frozen first finished deliveries from one real-source task; no causal or general effectiveness inference.',
    'input_freeze': input_checks,
    'artifact_freeze': freeze_checks,
    'source': {'observations': len(source), 'unique_source_cells': len({(r['source_sheet'], r['source_cell']) for r in source}),
               'groups': [{'population': p, 'condition': c, **s} for (p, c), s in stats.items()]},
    'outputs': {},
}

configs = {
    'baseline': {'directory': RUN / 'baseline/attempt-05', 'stem': 'cell-number-comparison',
                 'summary_file': 'group-statistics.csv', 'orientation': 'horizontal'},
    'with_skill': {'directory': RUN / 'with-skill/attempt-02', 'stem': 'panel',
                   'summary_file': 'summary-data.json', 'orientation': 'vertical'},
}

def distance_segment(pt, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    denom = dx*dx+dy*dy
    t = max(0., min(1., ((pt[0]-a[0])*dx+(pt[1]-a[1])*dy)/denom)) if denom else 0.
    return math.dist(pt, (a[0]+t*dx, a[1]+t*dy))

for label, cfg in configs.items():
    directory, stem = cfg['directory'], cfg['stem']
    plotted = rows(directory / 'plotting-data.csv')
    source_lookup = {(r['source_sheet'], r['source_cell']): r for r in source}
    plot_lookup = {(r['source_sheet'], r['source_cell']): r for r in plotted}
    lexical_ok = len(plot_lookup) == len(plotted) == 156 and set(plot_lookup) == set(source_lookup)
    lexical_ok = lexical_ok and all(all(plot_lookup[k][f] == r[f] for f in SOURCE_FIELDS) for k, r in source_lookup.items())
    metadata = (rows(directory / cfg['summary_file']) if label == 'baseline'
                else json.loads((directory / cfg['summary_file']).read_text()))
    errors = []
    for s in metadata:
        key = (s['population'], s['condition'])
        expected = stats[key]
        errors.append({'population': key[0], 'condition': key[1],
                       'n_matches': int(s['n']) == expected['n'],
                       **{f'{k}_absolute_error': abs(float(s[k])-expected[k]) for k in ['mean', 'sample_sd', 'sem']}})

    doc = pymupdf.open(directory / f'{stem}.pdf')
    page = doc[0]
    drawings = page.get_drawings()
    white_rects = [d['rect'] for d in drawings if d['fill'] == (1., 1., 1.) and d['rect'].width > 200]
    axes = min(white_rects, key=lambda r:r.width*r.height)
    markers = [d for d in drawings if abs(d['rect'].width-2.5)<.0001 and abs(d['rect'].height-2.5)<.0001
               and axes.contains(d['rect'])]
    summary_strokes = [d for d in drawings if d['width'] is not None
                       and (abs(d['width']-.65)<1e-6 or abs(d['width']-1.05)<1e-6)
                       and len(d['items'])==1 and d['items'][0][0]=='l' and axes.contains(d['rect'])]
    def transform(x, y):
        if label == 'baseline':
            return (axes.x0+x/4*axes.width, axes.y0+(y+.6)/9.2*axes.height)
        return (axes.x0+(x+.5)/9*axes.width, axes.y1-y/4*axes.height)
    unmatched = list(markers)
    marker_matches = []
    for r in plotted:
        value = float(r['normalized_count'])
        xy = transform(value, float(r['plot_y'])) if label == 'baseline' else transform(float(r['_raw_x']), value)
        d = min(unmatched, key=lambda d:math.dist(xy, tuple(d['rect'].tl+(d['rect'].br-d['rect'].tl)/2)))
        center = tuple(d['rect'].tl+(d['rect'].br-d['rect'].tl)/2)
        error = math.dist(xy, center)
        unmatched.remove(d)
        marker_matches.append({'source_cell': r['source_cell'], 'population': r['population'], 'condition': r['condition'],
                               'expected_center_pt': list(xy), 'actual_center_pt': list(center),
                               'position_error_pt': error, 'pdf_sequence': d['seqno'],
                               'marker_shape': 'circle' if all(it[0]=='c' for it in d['items']) else 'square',
                               'stroke_rgb': list(d['color']) if d['color'] else None,
                               'fill_rgb': list(d['fill']) if d['fill'] else None})
    intervals = [d for d in summary_strokes if abs(d['width']-.65)<1e-6
                 and ((d['rect'].height<1e-5 and d['rect'].width>5) if label=='baseline'
                      else (d['rect'].width<1e-5 and d['rect'].height>1e-5))]
    interval_matches = []
    remaining = list(intervals)
    for p_i, p in enumerate(contract['population_order']):
        for c_i, c in enumerate(contract['condition_order']):
            ss = stats[(p,c)]
            cat = (p_i+(-.25 if c_i==0 else .25)) if label=='baseline' else float(next(r['_summary_x'] for r in plotted if (r['population'],r['condition'])==(p,c)))
            aa, bb = ((transform(ss['mean']-ss['sem'],cat), transform(ss['mean']+ss['sem'],cat)) if label=='baseline'
                      else (transform(cat,ss['mean']-ss['sem']), transform(cat,ss['mean']+ss['sem'])))
            expected = sorted([aa,bb])
            def endpoint_error(d):
                actual = sorted([tuple(d['items'][0][1]), tuple(d['items'][0][2])])
                return max(math.dist(e,a) for e,a in zip(expected,actual))
            d = min(remaining, key=endpoint_error)
            remaining.remove(d)
            interval_matches.append({'population':p,'condition':c,'endpoint_error_pt':endpoint_error(d),
                                      'expected_endpoints_pt':expected,
                                      'actual_endpoints_pt':[list(d['items'][0][1]),list(d['items'][0][2])]})
    # Direct exported path geometry confirms whether summaries meet observation glyph footprints.
    overlaps=[]
    for marker in marker_matches:
        d = next(d for d in markers if d['seqno']==marker['pdf_sequence'])
        center = marker['actual_center_pt']
        for line in summary_strokes:
            aa,bb=tuple(line['items'][0][1]),tuple(line['items'][0][2])
            radius = 1.25 + ((d['width'] or 0)/2 if label=='baseline' else 0)
            if marker['marker_shape']=='square':
                rect = pymupdf.Rect(d['rect'])
                rect += (-((d['width'] or 0)+line['width'])/2, -((d['width'] or 0)+line['width'])/2,
                          ((d['width'] or 0)+line['width'])/2, ((d['width'] or 0)+line['width'])/2)
                crossing = rect.contains(pymupdf.Point(aa)) or rect.contains(pymupdf.Point(bb)) or (
                    abs(aa[1]-bb[1])<1e-6 and rect.y0 <= aa[1] <= rect.y1 and max(aa[0],bb[0])>=rect.x0 and min(aa[0],bb[0])<=rect.x1) or (
                    abs(aa[0]-bb[0])<1e-6 and rect.x0 <= aa[0] <= rect.x1 and max(aa[1],bb[1])>=rect.y0 and min(aa[1],bb[1])<=rect.y1)
            else:
                crossing = distance_segment(center,aa,bb) < radius+line['width']/2
            if crossing:
                overlaps.append({'source_cell':marker['source_cell'],'population':marker['population'],'condition':marker['condition'],
                                 'marker_sequence':marker['pdf_sequence'],'summary_sequence':line['seqno'],
                                 'raw_drawn_after_summary':marker['pdf_sequence']>line['seqno']})
    spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for s in line['spans']]
    texts = [{'text':s['text'],'size_pt':s['size'],'font':s['font'],'bbox_pt':list(s['bbox'])} for s in spans]
    fonts=[]
    for font in page.get_fonts(full=True):
        base,name,typ,buf=doc.extract_font(font[0])
        fonts.append({'base':base,'type':typ,'embedded_bytes':len(buf)})
    svg=ET.parse(directory/f'{stem}.svg').getroot()
    svg_texts=[{'text':''.join(el.itertext()),'style':el.attrib.get('style','')} for el in svg.iter() if el.tag.endswith('text')]
    png=Image.open(directory/f'{stem}.png')
    raw_intersections=[]
    min_center_distance=float('inf')
    for i,a in enumerate(markers):
        ac=tuple(a['rect'].tl+(a['rect'].br-a['rect'].tl)/2)
        ashape='circle' if all(it[0]=='c' for it in a['items']) else 'square'
        ahalf=1.25+(a['width'] or 0)/2
        for b in markers[i+1:]:
            bc=tuple(b['rect'].tl+(b['rect'].br-b['rect'].tl)/2)
            bshape='circle' if all(it[0]=='c' for it in b['items']) else 'square'
            bhalf=1.25+(b['width'] or 0)/2
            dx,dy=abs(ac[0]-bc[0]),abs(ac[1]-bc[1])
            min_center_distance=min(min_center_distance,math.hypot(dx,dy))
            if ashape==bshape=='circle':
                collides=math.hypot(dx,dy)<ahalf+bhalf-1e-4
            elif ashape==bshape=='square':
                collides=max(dx,dy)<ahalf+bhalf-1e-4
            else:
                sqhalf=ahalf if ashape=='square' else bhalf
                circhalf=bhalf if ashape=='square' else ahalf
                collides=math.hypot(max(dx-sqhalf,0),max(dy-sqhalf,0))<circhalf-1e-4
            if collides:
                raw_intersections.append([a['seqno'],b['seqno']])
    preview=OUT/f'{label}-pdf-96dpi.png'
    page.get_pixmap(dpi=96,alpha=False).save(preview)
    result={
        'export_hashes':{fmt:sha(directory/f'{stem}.{fmt}') for fmt in ['png','pdf','svg']},
        'source_rows_lexically_preserved':lexical_ok,'plotting_row_count':len(plotted),'summary_group_count':len(metadata),
        'summary_errors':errors,
        'pdf':{'page_count':len(doc),'dimensions_mm':[page.rect.width/PT_MM,page.rect.height/PT_MM],
               'axes_rectangle_mm':[x/PT_MM for x in axes],'data_width_mm':axes.width/PT_MM,'data_height_mm':axes.height/PT_MM,
               'marker_count':len(markers),'marker_matches':marker_matches,
               'raw_raw_footprint_intersections':raw_intersections,
               'minimum_raw_center_distance_pt':min_center_distance,
               'full_raw_glyphs_within_axes':all(axes.contains(d['rect']+(-((d['width'] or 0)/2),-((d['width'] or 0)/2),((d['width'] or 0)/2),((d['width'] or 0)/2))) for d in markers),
               'max_marker_position_error_pt':max(r['position_error_pt'] for r in marker_matches),
               'interval_count':len(intervals),'interval_matches':interval_matches,
               'max_interval_endpoint_error_pt':max(r['endpoint_error_pt'] for r in interval_matches),
               'mean_stroke_count':sum(abs(d['width']-1.05)<1e-6 for d in summary_strokes),
               'summary_stroke_widths_pt':sorted(set(round(d['width'],6) for d in summary_strokes)),
               'raw_summary_footprint_intersections':overlaps,'intersection_pair_count':len(overlaps),
               'observations_touching_summary_count':len(set(r['source_cell'] for r in overlaps)),
               'text_spans':texts,'all_text_exactly_8pt':all(abs(s['size_pt']-8)<1e-6 for s in texts),
               'all_text_within_page':all(page.rect.contains(pymupdf.Rect(s['bbox_pt'])) for s in texts),
               'fonts':fonts},
        'svg':{'width':svg.attrib['width'],'height':svg.attrib['height'],'viewBox':svg.attrib['viewBox'],'text':svg_texts},
        'png':{'pixels':list(png.size),'dpi':list(png.info.get('dpi',[]))},
        'nominal_96dpi_pdf_preview':{'path':str(preview),'pixels':list(Image.open(preview).size),'sha256':sha(preview)},
    }
    evidence['outputs'][label]=result

evidence['freeze_recheck_after_audit']={
    'baseline':match_freeze(RUN/'baseline/final-manifest.json','files'),
    'with_skill':match_freeze(RUN/'with-skill/first-finished-delivery-freeze.json','artifacts'),
}
(OUT/'numeric-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps({'input_hashes_match':all(r['matches'] for r in input_checks),
    'freeze_hashes_match':{k:all(r['matches'] for r in v) for k,v in freeze_checks.items()},
    'outputs':{k:{'source_rows_preserved':r['source_rows_lexically_preserved'],
                  'summary_max_error':max(e[f'{f}_absolute_error'] for e in r['summary_errors'] for f in ['mean','sample_sd','sem']),
                  'pdf_dimensions_mm':r['pdf']['dimensions_mm'],'pdf_markers':r['pdf']['marker_count'],
                  'pdf_intervals':r['pdf']['interval_count'],'max_pdf_marker_error_pt':r['pdf']['max_marker_position_error_pt'],
                  'max_pdf_interval_error_pt':r['pdf']['max_interval_endpoint_error_pt'],
                  'summary_touched_observations':r['pdf']['observations_touching_summary_count'],
                  'all_text_8pt':r['pdf']['all_text_exactly_8pt'],'text_within_page':r['pdf']['all_text_within_page'],
                  'png_pixels':r['png']['pixels'],'preview_pixels':r['nominal_96dpi_pdf_preview']['pixels']}
               for k,r in evidence['outputs'].items()}},indent=2))
