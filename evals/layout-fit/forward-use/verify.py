"""Check the recorded source and actual PDF/SVG/PNG exports."""
from pathlib import Path
import json, hashlib, math, csv, xml.etree.ElementTree as ET
import pymupdf
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap, Normalize

root=Path(__file__).resolve().parent
source=list(csv.DictReader((root/'prepared.csv').open()))
plotted=list(csv.DictReader((root/'plotting-data.csv').open()))
spec=json.loads((root/'plot.json').read_text())
palette=json.loads((root/'easyviz/assets/palettes/palettes.json').read_text())['notch2-blue']['colors']
checks={}
checks['source_sha256']=hashlib.sha256((root/'prepared.csv').read_bytes()).hexdigest()
checks['rows_retained']=len(source)==len(plotted)==24 and all(all(p[k]==s[k] or (k in ['Detected fraction','Prepared score'] and float(p[k])==float(s[k])) for k in s) for s,p in zip(source,plotted))
checks['all_states_observed']=all(p['_easyviz_state']=='observed' for p in plotted)
checks['zero_rows_retained']=sum(float(p['Detected fraction'])==0 for p in plotted)==2
checks['areas_match_0_to_1_scale']=all(abs(float(p['_easyviz_area_pt2'])-90*float(s['Detected fraction']))<1e-9 for s,p in zip(source,plotted))
checks['orders_match_input']=spec['order']=={'x':list(dict.fromkeys(s['Treatment arm'] for s in source)),'y':list(dict.fromkeys(s['Cell type'] for s in source))}

pdf=pymupdf.open(root/'panel.pdf'); page=pdf[0]
checks['pdf_size_mm']=[page.rect.width*25.4/72,page.rect.height*25.4/72]
checks['pdf_dimensions_pass']=len(pdf)==1 and all(abs(a-b)<0.001 for a,b in zip(checks['pdf_size_mm'],[120,90]))
fonts=page.get_fonts(full=True)
checks['pdf_fonts']=[{'font':f[3],'type':f[2],'embedded_bytes':len(pdf.extract_font(f[0])[3])} for f in fonts]
checks['pdf_arial_embedded']=all('Arial' in f[3] and len(pdf.extract_font(f[0])[3])>0 for f in fonts)
spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
checks['pdf_all_text_8pt']=all(abs(s['size']-8)<1e-6 for s in spans)
checks['pdf_text_sizes_pt']=sorted(set(s['size'] for s in spans))
curves=[d for d in page.get_drawings() if d['fill'] and len(d['items'])==8 and all(i[0]=='c' for i in d['items'])]
dots=[d for d in curves if d['fill'][2]>d['fill'][0]+0.01]
positive=[s for s in source if float(s['Detected fraction'])>0]
checks['pdf_positive_dot_count']=len(dots)
checks['pdf_dot_area_ratios_pass']=len(dots)==22 and all(abs(d['rect'].width**2-90*float(s['Detected fraction']))<0.001 for d,s in zip(dots,positive))
cmap=LinearSegmentedColormap.from_list('check',palette); norm=Normalize(-0.22,1.66)
checks['pdf_color_mapping_pass']=all(max(abs(a-b) for a,b in zip(d['fill'],cmap(norm(float(s['Prepared score'])))[:3]))<1e-6 for d,s in zip(dots,positive))
keys=[d for d in curves if max(d['fill'])-min(d['fill'])<0.001]
checks['pdf_size_legend_key_areas_pass']=len(keys)==3 and all(abs(d['rect'].width**2-90*v)<0.001 for d,v in zip(keys,[0.25,0.5,1.0]))
checks['pdf_marker_strokes_absent']=all(d['type']=='f' for d in dots+keys)
svg=ET.parse(root/'panel.svg').getroot()
checks['svg_dimensions_pt']=[float(svg.attrib[k].removesuffix('pt')) for k in ['width','height']]
checks['svg_dimensions_pass']=all(abs(a*25.4/72-b)<0.001 for a,b in zip(checks['svg_dimensions_pt'],[120,90]))
checks['svg_editable_text_present']=len(svg.findall('.//{http://www.w3.org/2000/svg}text'))>0
with Image.open(root/'panel.png') as im:
    checks['png_pixels']=list(im.size); checks['png_dpi']=list(im.info['dpi'])
checks['png_dimensions_pass']=all(abs(a-b)<=1 for a,b in zip(checks['png_pixels'],[round(120/25.4*300),round(90/25.4*300)])) and all(abs(d-300)<0.01 for d in checks['png_dpi'])
checks['statistics_none']=json.loads((root/'stats.json').read_text())['method']=='none'
if (root/'reproduced/panel.png').exists():
    checks['bundle_reproduction_png_byte_identical']=(root/'panel.png').read_bytes()==(root/'reproduced/panel.png').read_bytes()
    checks['bundle_reproduction_svg_byte_identical']=(root/'panel.svg').read_bytes()==(root/'reproduced/panel.svg').read_bytes()
checks['status']='pass' if all(v for k,v in checks.items() if isinstance(v,bool)) else 'failed'
checks['scope']='One supplied 24-row descriptive table and these actual exports; no generalization claim. Circle bounding width squared verifies proportional area and equality of plot/legend scales.'
(root/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
assert checks['status']=='pass'
