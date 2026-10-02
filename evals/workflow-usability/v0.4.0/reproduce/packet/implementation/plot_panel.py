#!/usr/bin/env python3
"""User-summary-only two-axis time course; custom implementation from scratch.
Run with /Users/starry/Desktop/EasyViz/.venv/bin/python this_file.py.
"""
from pathlib import Path
import csv, hashlib, importlib.util, json, math, os, sys, warnings
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[2]
os.environ['MPLCONFIGDIR']=str(OUT/'.runtime-cache/matplotlib')
os.environ['XDG_CACHE_HOME']=str(OUT/'.runtime-cache')
SCRIPTS=Path('/Users/starry/Desktop/EasyViz/skills/easyviz/scripts')
loader=importlib.util.spec_from_file_location('easyviz_core',SCRIPTS/'render.py')
core=importlib.util.module_from_spec(loader);loader.loader.exec_module(core)
import numpy as np
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
from PIL import Image
from pypdf import PdfReader
import xml.etree.ElementTree as ET

def save(name,value):
 (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

adopted=json.loads((OUT/'adopted-spec.json').read_text())
DATA=OUT/'packet/data/data-1-user-summaries.csv'
with DATA.open(newline='') as f:rows=list(csv.DictReader(f))
keys=set()
for source_line,r in enumerate(rows,start=2):
 r['source_line']=source_line
 for k in ('t_min','supplied_mean','supplied_sd'):
  r[k]=float(r[k]);assert math.isfinite(r[k]),(source_line,k)
 assert r['channel'] in ('Width','Length') and r['supplied_sd']>=0
 key=(r['channel'],r['t_min']);assert key not in keys;keys.add(key)
assert len(rows)==14
channels={c:sorted([r for r in rows if r['channel']==c],key=lambda r:r['t_min']) for c in ('Width','Length')}
plot_rows=[dict(r,low=r['supplied_mean']-r['supplied_sd'],high=r['supplied_mean']+r['supplied_sd']) for c in channels for r in channels[c]]
with (OUT/'plotting-data.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['source_line','t_min','channel','supplied_mean','supplied_sd','low','high']);w.writeheader();w.writerows(plot_rows)
spec={'chart':'custom-dual-axis-time-course','track':'reproduce','layout':{'width_mm':120,'height_mm':90,'font':'Arial','font_size_pt':8,'line_width_pt':0.6,'dpi':300,'margins':{'left':0.165,'right':0.858,'bottom':0.17,'top':0.89}},'typography':dict.fromkeys(('axis','tick','legend','annotation','title','panel'),8),'formats':['svg','pdf','png'],'colors':{'Width':'#0072B2','Length':'#E76F51'},'labels':{'x':'Time (min)','y':'Width (µm)'},'custom':{'band_alpha':0.28,'line_width_pt':0.8,'no_markers':True,'no_grid':True,'shared_x':True,'independent_y':True}}
save('render-spec.json',spec)
layout,typography,rc=core.setup(spec)
assert layout['actual_font']=='Arial' and not layout['font_substituted']
font_path=font_manager.findfont(font_manager.FontProperties(family='Arial'),fallback_to_default=False)
font=font_manager.get_font(font_path)
missing_chars=sorted({c for text in ['Time (min)','Width (µm)','Length (µm)'] for c in text if ord(c) not in font.get_charmap()});assert not missing_chars
with warnings.catch_warnings(record=True) as caught,core.plt.rc_context(rc):
 warnings.simplefilter('always')
 fig=core.plt.figure(figsize=(120/25.4,90/25.4),dpi=300,facecolor='white')
 ax=fig.add_axes(adopted['layout']['axes_bounds']);right=ax.twinx();right.patch.set_visible(False)
 axes=adopted['axes'];colors=spec['colors']
 ax.set_xlim(axes['x_limits']);right.set_xlim(axes['x_limits']);ax.set_ylim(axes['left_limits']);right.set_ylim(axes['right_limits'])
 ax.set_xticks(axes['x_ticks']);ax.set_yticks(axes['left_ticks']);right.set_yticks(axes['right_ticks'])
 fmt=FuncFormatter(lambda value,pos:f'{value:g}');ax.yaxis.set_major_formatter(fmt);right.yaxis.set_major_formatter(fmt)
 ax.set_xlabel(axes['x_label'],fontsize=8,labelpad=5)
 ax.set_ylabel(axes['left_label'],fontsize=8,color=colors['Width'],labelpad=6)
 right.set_ylabel(axes['right_label'],fontsize=8,color=colors['Length'],rotation=270,labelpad=11)
 for a in (ax,right):
  a.set_axisbelow(True);a.grid(False)
  for spine in a.spines.values():spine.set_linewidth(0.6)
  a.spines['top'].set_visible(False)
 ax.spines['left'].set_color(colors['Width']);ax.spines['right'].set_visible(False);ax.spines['bottom'].set_color('black')
 right.spines['right'].set_color(colors['Length']);right.spines['left'].set_visible(False);right.spines['bottom'].set_visible(False)
 ax.tick_params(axis='x',direction='in',length=2.5,width=0.6,labelsize=8,colors='black',pad=3)
 ax.tick_params(axis='y',direction='in',length=2.5,width=0.6,labelsize=8,colors=colors['Width'],pad=3)
 right.tick_params(axis='y',direction='in',length=2.5,width=0.6,labelsize=8,colors=colors['Length'],pad=3)
 bands={};lines={}
 for c in ('Width','Length'):
  recs=channels[c];x=np.array([r['t_min'] for r in recs]);m=np.array([r['supplied_mean'] for r in recs]);sd=np.array([r['supplied_sd'] for r in recs]);target=ax if c=='Width' else right
  # Both bands draw on the back axis, retaining their proper data transforms.
  # Both means consequently appear in front of both translucent bands.
  band=ax.fill_between(x,m-sd,m+sd,transform=target.transData,color=colors[c],alpha=0.28,edgecolor='none',linewidth=0,zorder=1 if c=='Width' else 2)
  line,=target.plot(x,m,color=colors[c],linewidth=0.8,linestyle='-',marker='None',zorder=4)
  band.set_gid(f'easyviz-{c.lower()}-band');line.set_gid(f'easyviz-{c.lower()}-mean');bands[c]=band;lines[c]=line
  source_keys=[{'source_line':r['source_line'],'channel':c,'t_min':r['t_min']} for r in recs]
  for artist,role,label in ((band,'uncertainty-band',f'{c} supplied mean ± SD'),(line,'mean-trajectory',f'{c} supplied mean')):
   core.figure_elements.register(fig,artist,role,label,key=[role,c],source_keys=source_keys,spec_paths=[core.figure_elements.pointer('colors',c)],editable=['color'])
 fig._easyviz_track='reproduce';fig._easyviz_source_script=Path(__file__).resolve();fig._easyviz_data_file=DATA;fig._easyviz_spec_file=OUT/'render-spec.json'
 fig.canvas.draw();painter=fig.canvas.get_renderer()
 with DATA.open(newline='') as f:originals=list(csv.DictReader(f))
 audit={'status':'passed','scope':'all 14 supplied summary rows, 2 means, 2 SD bands','source_rows':14,'channels':{},'omitted_rows':0}
 for c in ('Width','Length'):
  expected=sorted([r for r in originals if r['channel']==c],key=lambda r:float(r['t_min']))
  ex=np.array([float(r['t_min']) for r in expected]);em=np.array([float(r['supplied_mean']) for r in expected]);es=np.array([float(r['supplied_sd']) for r in expected])
  np.testing.assert_array_equal(lines[c].get_xdata(),ex);np.testing.assert_array_equal(lines[c].get_ydata(),em)
  vertices=bands[c].get_paths()[0].vertices
  for x,m,sd in zip(ex,em,es):
   vy=vertices[np.isclose(vertices[:,0],x),1];assert np.any(np.isclose(vy,m-sd)) and np.any(np.isclose(vy,m+sd)),(c,x)
  target=ax if c=='Width' else right
  assert bands[c].get_transform() is target.transData
  assert ex.min()>=ax.get_xlim()[0] and ex.max()<=ax.get_xlim()[1]
  assert (em-es).min()>=target.get_ylim()[0] and (em+es).max()<=target.get_ylim()[1]
  assert lines[c].get_marker() in ('None','none','') and bands[c].get_linewidths().tolist()==[0]
  audit['channels'][c]={'input_rows':len(expected),'mean_vertices_checked':len(expected),'band_boundary_values_checked':len(expected)*2,'range_low':float((em-es).min()),'range_high':float((em+es).max()),'coordinates':'left y' if c=='Width' else 'right y'}
 np.testing.assert_allclose(ax.get_position().bounds,right.get_position().bounds,atol=1e-12);np.testing.assert_allclose(ax.get_xlim(),right.get_xlim(),atol=1e-12)
 texts=[ax.xaxis.label,ax.yaxis.label,right.yaxis.label,*ax.get_xticklabels(),*ax.get_yticklabels(),*right.get_yticklabels()]
 text_bounds=[];collisions=[]
 for i,t in enumerate(texts):
  b=t.get_window_extent(painter);bmm=[float(v*25.4/fig.dpi) for v in (b.x0,b.y0,b.width,b.height)]
  assert b.x0>=0 and b.y0>=0 and b.x1<=fig.bbox.width and b.y1<=fig.bbox.height,(t.get_text(),bmm)
  assert t.get_fontsize()==8
  text_bounds.append({'text':t.get_text(),'bbox_mm':bmm,'font_size_pt':8})
  for other in texts[i+1:]:
   if b.overlaps(other.get_window_extent(painter)):collisions.append([t.get_text(),other.get_text()])
 assert not collisions
 assert not ax.get_title() and not right.get_title() and not fig.texts
 assert not ax.spines['top'].get_visible() and not right.spines['top'].get_visible()
 assert not any(l.get_visible() for a in (ax,right) for l in a.get_xgridlines()+a.get_ygridlines())
 exports=core.export(fig,OUT,spec,layout);warning_messages=[str(w.message) for w in caught];core.plt.close(fig)
assert not any('Glyph' in message or 'missing' in message for message in warning_messages)
save('source-to-artist-checks.json',audit)
save('layout-checks.json',{'status':'passed','canvas_mm':[120,90],'text_bounds':text_bounds,'collisions':collisions,'axis_alignment':'identical positions and x limits','legend':'none; color-associated y axes','missing_glyphs':missing_chars,'warnings':warning_messages})
save('figure-settings.json',{'track':'reproduce','input_mode':'image-data','layout':layout,'typography_pt':typography,'font_path':font_path,'font_sha256':sha(font_path),'colors':colors,'band_alpha':0.28,'outline_policy':'Borderless fills; markerless 0.8 pt central lines','axes':axes,'formats':spec['formats'],'data':str(DATA)})
save('export-checks.json',exports)
# Reopen exported files and measure independently of the export return values.
pdf=PdfReader(OUT/'panel.pdf');page=pdf.pages[0];pdfmm=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72];np.testing.assert_allclose(pdfmm,[120,90],atol=1e-5)
fonts=[]
for val in page['/Resources']['/Font'].get_object().values():
 f=val.get_object()
 for val2 in f.get('/DescendantFonts',[f]):
  d=val2.get_object();descriptor=d.get('/FontDescriptor');descriptor=descriptor.get_object() if descriptor else {}
  fonts.append({'base_font':str(d.get('/BaseFont',f.get('/BaseFont'))),'embedded':any(k in descriptor for k in ('/FontFile','/FontFile2','/FontFile3'))})
assert fonts and all(f['embedded'] and 'Arial' in f['base_font'] for f in fonts)
root=ET.parse(OUT/'panel.svg').getroot();svgmm=[float(root.attrib[k].removesuffix('pt'))*25.4/72 for k in ('width','height')];np.testing.assert_allclose(svgmm,[120,90],atol=1e-5)
svgtexts=[e for e in root.iter() if e.tag.endswith('}text')];assert len(svgtexts)==len(text_bounds)
assert all('8px' in t.attrib.get('style','') and 'Arial' in t.attrib.get('style','') for t in svgtexts)
with Image.open(OUT/'panel.png') as im:pngsize=list(im.size);pngdpi=list(im.info['dpi'])
assert pngsize==[1417,1063]
manifest=json.loads((OUT/'elements.json').read_text());svgids={e.attrib['id'] for e in root.iter() if 'id' in e.attrib}
assert all(e['id'] in svgids for e in manifest['elements'])
assert all(f'easyviz-{c}-{r}' in svgids for c in ('width','length') for r in ('mean','band'))
save('independent-export-checks.json',{'status':'passed','PDF':{'pages':len(pdf.pages),'canvas_mm':pdfmm,'fonts':fonts},'SVG':{'canvas_mm':svgmm,'editable_text_count':len(svgtexts),'all_text_Arial_8_pt':True,'semantic_ids_match_map':True,'registered_elements':len(manifest['elements'])},'PNG':{'pixels':pngsize,'dpi':pngdpi},'no_crop':True})
save('run-trace.json',{'track':'reproduce','input_mode':'image-data','script':str(Path(__file__).resolve()),'script_sha256':sha(__file__),'inputs':[{'path':str(p),'sha256':sha(p)} for p in (DATA,OUT/'packet/reader-inputs/reference.png',OUT/'packet/reader-inputs/methods-1-user-notes.txt')],'generic_helpers_used':['render.py setup/export','figure_elements.py register/attach_layout/write'],'author_code_accessed':False,'paper_source_data_accessed':False,'no_examples_cases_evals_tests_access':True,'saved_reading_consulted':str(OUT/'prior-independent-reading.md'),'fresh_independent_reading':False,'transforms':['Sort channel and time','Calculate supplied mean ± supplied SD','Straight connections; no aggregation, fitted model or synthetic rows'],'outputs':{f'panel.{ext}':sha(OUT/f'panel.{ext}') for ext in ('svg','pdf','png')},'visual_self_review_pending':True})
print(json.dumps({'status':'rendered; numeric/layout/export checks passed','output':str(OUT),'canvas_mm':[120,90],'font':layout['actual_font'],'rows':14,'registered_elements':len(manifest['elements'])}))
