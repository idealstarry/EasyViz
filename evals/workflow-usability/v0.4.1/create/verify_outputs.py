#!/usr/bin/env python3
"""Independent arithmetic and export audit of this captured, data-specific run."""
import argparse, csv, hashlib, json, math, statistics
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image
from pypdf import PdfReader
import fitz

ROOT = Path(__file__).resolve().parent
GROUPS = ['Vehicle','Low dose','High dose']

def rows(path):
    with path.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def same(a,b):
    return math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True,type=Path)
    run=parser.parse_args().run_dir.resolve()
    data=ROOT/'input/data'
    raw=rows(data/'A_export__final2.csv')
    lookup={r['tube_key']:r['arm_name'] for r in rows(data/'sample-index__2026.tsv.csv')}
    measured=defaultdict(list)
    for r in raw:
        if r['signal_au']!='':
            measured[r['tube_key']].append(Decimal(r['signal_au']))
    expected={ident:sum(values)/len(values) for ident,values in measured.items()}
    plot=rows(run/'plotting_data.csv')
    assert len(plot)==len(expected)==36
    assert len({r['specimen_id'] for r in plot})==36
    assert Counter(r['group'] for r in plot)==Counter({g:12 for g in GROUPS})
    assert all(r['specimen_id'] in lookup and r['group']==lookup[r['specimen_id']]
               and Decimal(r['mean_signal'])==expected[r['specimen_id']] for r in plot)
    assert next(r for r in plot if r['specimen_id']=='0008')['mean_signal']=='105.2146'
    render_rows=rows(run/'panel/plotting-data.csv')
    assert len(render_rows)==36
    assert all(a['specimen_id']==b['specimen_id'] and a['group']==b['group']
               and same(a['mean_signal'],b['mean_signal']) for a,b in zip(plot,render_rows))
    results=json.loads((run/'statistics/results.json').read_text())
    settings=json.loads((run/'panel/settings.json').read_text())
    qa=json.loads((run/'panel/qa.json').read_text())
    assert results['provenance']['data']['sha256']==sha(run/'plotting_data.csv')==settings['input_sha256']
    groups={g:[r['mean_signal'] for r in plot if r['group']==g] for g in GROUPS}
    descriptions={}
    for summary in results['comparisons'][0]['summaries']:
        g=summary['group']
        v=[float(x) for x in groups[g]]
        qs=statistics.quantiles(v,n=4,method='inclusive')
        independently={'n_rows':len(v),'mean':statistics.mean(v),'median':statistics.median(v),
                       'sd':statistics.stdev(v),'q1':qs[0],'q3':qs[2],
                       'minimum':min(v),'maximum':max(v)}
        assert all(same(summary[key],val) for key,val in independently.items())
        descriptions[g]=independently
    inference=[]
    for c in results['comparisons'][1:]:
        dose=c['groups'][0]
        x=[Decimal(v) for v in groups[dose]]
        y=[Decimal(v) for v in groups['Vehicle']]
        greater=sum(a>b for a in x for b in y)
        lower=sum(a<b for a in x for b in y)
        ties=sum(a==b for a in x for b in y)
        u=greater+ties/2
        delta=(greater-lower)/(len(x)*len(y))
        assert same(c['effect']['estimate'],delta)
        ranks=Counter(x+y)
        n=len(x)+len(y)
        tie_term=sum(t**3-t for t in ranks.values())
        var=len(x)*len(y)/12*((n+1)-tie_term/(n*(n-1)))
        z=(abs(u-len(x)*len(y)/2)-0.5)/math.sqrt(var)
        p=math.erfc(abs(z)/math.sqrt(2))
        assert same(c['pvalue'],p)
        assert c['interval'] is None
        inference.append({'comparison':c['name'],'u_first_dose':u,'greater':greater,'lower':lower,
                          'ties':ties,'cliffs_delta':delta,'manual_asymptotic_p':p,
                          'helper_adjusted_p':c['adjusted_pvalue']})
    order=sorted(range(2),key=lambda i:inference[i]['manual_asymptotic_p'])
    prev=0
    for rank,i in enumerate(order):
        adj=min(1,max(prev,(2-rank)*inference[i]['manual_asymptotic_p']))
        prev=adj
        assert same(adj,inference[i]['helper_adjusted_p'])
        inference[i]['manual_holm_p']=adj
    ns={'s':'http://www.w3.org/2000/svg'}
    svg=ET.parse(run/'panel/panel.svg').getroot()
    texts=svg.findall('.//s:text',ns)
    assert len(texts)>0 and all("font-family: 'Arial'" in t.get('style','')
                                and 'font-size: 8px' in t.get('style','') for t in texts)
    svg_mm=[float(svg.attrib[k].removesuffix('pt'))*25.4/72 for k in ['width','height']]
    assert all(math.isclose(a,b,abs_tol=1e-5) for a,b in zip(svg_mm,[120,90]))
    png=Image.open(run/'panel/panel.png')
    assert list(png.size)==[round(120/25.4*300),round(90/25.4*300)]
    assert all(abs(v-300)<.01 for v in png.info['dpi'])
    assert all(png.getpixel((x,y))[:3]==(255,255,255) for x,y in [(0,0),(png.width-1,0),(0,png.height-1),(png.width-1,png.height-1)])
    pdf=PdfReader(str(run/'panel/panel.pdf'))
    assert len(pdf.pages)==1
    page=pdf.pages[0]
    pdf_mm=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72]
    assert all(math.isclose(a,b,abs_tol=1e-5) for a,b in zip(pdf_mm,[120,90]))
    font_records=[]
    for name,ref in page['/Resources']['/Font'].items():
        font=ref.get_object()
        descendants=font.get('/DescendantFonts',[ref])
        for d in descendants:
            child=d.get_object()
            desc=child.get('/FontDescriptor')
            desc=desc.get_object() if desc else {}
            embedded=any(k in desc for k in ['/FontFile','/FontFile2','/FontFile3'])
            font_records.append({'resource':name,'base_font':str(font['/BaseFont']),'embedded':embedded})
    assert font_records and all(f['embedded'] for f in font_records)
    doc=fitz.open(str(run/'panel/panel.pdf'))
    spans=[s for b in doc[0].get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
    assert spans and all(math.isclose(s['size'],8,abs_tol=.001) and 'Arial' in s['font'] for s in spans)
    assert qa['status']=='pass' and qa['point_layout']['placed_rows']==36
    assert qa['point_layout']['spacing_violation_pairs']==0
    report={'status':'passed','scope':'This exact synthetic input, adopted single panel, captured helpers and exported files only',
            'source_unit_checks':{'current_mice':36,'per_group':12,'technical_rows':72,'measured_reads':71,
                                 'failed_read_mouse_retained':'0008','literal_ids_preserved':True,
                                 'raw_to_mean_join_verified':True,'analysis_render_input_hashes_match':True},
            'independent_descriptions':descriptions,'independent_rank_and_holm_calculations':inference,
            'exports':{'pdf_mm':pdf_mm,'pdf_fonts':font_records,'pdf_text_sizes_pt':sorted({s['size'] for s in spans}),
                       'svg_mm':svg_mm,'svg_editable_text_elements':len(texts),'svg_text_font':'Arial 8 pt in SVG pt coordinates',
                       'png_pixels':list(png.size),'png_dpi':png.info['dpi'],'white_canvas_corners':True},
            'limitations':['Visual review is self-review, not independent.',
                           'Mann–Whitney p values use continuity- and tie-corrected normal approximation at n=12 per arm.',
                           'No effect confidence intervals are computed; boxes encode quartiles of observations.',
                           'No claim about arbitrary datasets, unsupported layers, or publication acceptance.'],
            'artifact_hashes':{str(p.relative_to(run)):sha(p) for p in [run/'plotting_data.csv',run/'panel/panel.png',run/'panel/panel.svg',run/'panel/panel.pdf']}}
    (run/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
