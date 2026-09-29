#!/usr/bin/env python3
"""Reproduce the supplied dot-matrix organization using new source values.
Run: /Users/starry/Desktop/EasyViz/.venv/bin/python plot.py
Dependencies: matplotlib, numpy, pandas, Pillow, pypdf, PyMuPDF.
All scientific inputs are local. No author code, remote source or example data.
"""
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR'] = str(ROOT / '.mpl-cache')
os.environ['XDG_CACHE_HOME'] = str(ROOT / '.cache')
import json, hashlib, math, xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox
from PIL import Image
from pypdf import PdfReader
import fitz

CFG = {
 'track':'reproduce', 'input_mode':'image-data', 'author_code_accessed':False,
 'inputs':{'data':'source.csv','reference':'reference.png','request':'request.md'},
 'layout':{'width_mm':180,'height_mm':125,'font':'Arial','font_size_pt':8,'line_width_pt':0.6,'dpi':300,
           'plot_bbox_mm':[62,33,90,85]},
 'data_mapping':{'x':'marker','y':'population','size':'detected_fraction','color':'mean_scaled_expression',
  'order':'first appearance for each dimension','aggregation':'none',
  'missing':'absent source row => gray x; measured zero => zero-area blank',
  'transformation':'complete population-marker grid without imputing measurements'},
 'statistics':{'computed':False,'reason':'No statistical layer requested; upstream summaries supplied.'},
 'colors':{'type':'linear blue-neutral-pink','stops':['#2581b9','#f7f8f9','#cc86b9'],
           'limits':[-2,2],'center':0,'source':'estimated from supplied reference colorbar pixels'},
 'marks':{'shape':'circle','max_scatter_area_pt2':64,'area_formula':'s = 64 * detected_fraction',
          'geometric_disk_area_formula_pt2':'pi / 4 * s; strictly proportional to detected_fraction',
          'outline':'none','missing_shape':'x','missing_area_pt2':12,'missing_stroke_pt':0.6,'missing_color':'#70777e',
          'zero':'no visible mark; source expression preserved'},
 'group_lines':{'after_populations':['Nonclassical monocytes','Inflammatory macrophages'],
                'color':'#d9e0e8','width_pt':0.6,'new_population_annotations':[]},
 'guides':{'colorbar_rect_mm':[161.5,49.5,2.7,42],'colorbar_ticks':[-2,0,2],
           'colorbar_label':'Scaled expression','size_values':[0.25,0.5,1.0],
           'size_label':'Detected (%)','size_area_formula':'same s = 64 * value',
           'zero_swatch':'outlined empty cell, separate from quantitative circle scale',
           'zero_label':'0 (measured)','missing_label':'Not measured'},
 'formats':['pdf','svg','png'],'intentional_differences':[
  'Eight population rows follow source first appearance; new rows have no invented biological annotations.',
  'Retain only the two original separators after named populations.',
  'Add gray x for absent combinations and an empty-cell key for measured zeros.',
  'Legend and margins adapted for final physical size and longer population labels.',
  'Palette sampled approximately; source numeric values replace reference values.'],
 'review':{'reading_role':'main-agent fallback','independent_reader_attempt':'failed: agent thread limit reached'}
}

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

df = pd.read_csv(ROOT / 'source.csv')
assert list(df.columns) == ['population','marker','detected_fraction','mean_scaled_expression']
assert not df[['population','marker']].duplicated().any(), 'Duplicate source pair'
assert not df.isna().any().any(), 'Unexpected incomplete source row'
assert df.detected_fraction.between(0,1).all()
assert df.mean_scaled_expression.between(-2,2).all()
populations = df.population.drop_duplicates().tolist()
markers = df.marker.drop_duplicates().tolist()
df['source_row'] = np.arange(1,len(df)+1)
full = pd.MultiIndex.from_product([populations,markers],names=['population','marker'])
grid = df.set_index(['population','marker']).reindex(full).reset_index()
grid['measured'] = grid.source_row.notna()
grid['source_row'] = grid.source_row.astype('Int64')
grid['population_order'] = grid.population.map({p:i for i,p in enumerate(populations)})
grid['marker_order'] = grid.marker.map({m:i for i,m in enumerate(markers)})
grid['state'] = np.where(~grid.measured,'not_measured',np.where(grid.detected_fraction.eq(0),'measured_zero','measured_nonzero'))
grid['scatter_area_pt2'] = grid.detected_fraction * CFG['marks']['max_scatter_area_pt2']
grid.to_csv(ROOT / 'plotting-data.csv',index=False)
font_path = font_manager.findfont(font_manager.FontProperties(family='Arial'), fallback_to_default=False)
CFG['layout']['actual_font_path'] = font_path
CFG['layout']['actual_font_name'] = font_manager.FontProperties(fname=font_path).get_name()
CFG['order'] = {'populations':populations,'markers':markers}
CFG['inputs']['sha256'] = {n:digest(ROOT/n) for n in ['source.csv','reference.png','request.md']}
plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,
 'legend.fontsize':8,'figure.titlesize':8,'axes.titlesize':8,'pdf.fonttype':42,'ps.fonttype':42,
 'svg.fonttype':'none','axes.linewidth':0.6,'savefig.facecolor':'white'})
W,H=180,125
fig = plt.figure(figsize=(W/25.4,H/25.4),dpi=300,facecolor='white')
def mmrect(vals): return [vals[0]/W,vals[1]/H,vals[2]/W,vals[3]/H]
ax = fig.add_axes(mmrect(CFG['layout']['plot_bbox_mm']))
ax.set_axisbelow(True)
ax.set_xlim(-0.6,len(markers)-0.4)
ax.set_ylim(len(populations)-0.5,-0.5)
ax.set_xticks(range(len(markers)),markers,rotation=90)
ax.set_yticks(range(len(populations)),populations)
ax.tick_params(axis='both',length=0,pad=5)
for spine in ax.spines.values(): spine.set_visible(False)
cmap = LinearSegmentedColormap.from_list('reference_blue_neutral_pink',CFG['colors']['stops'],N=256)
norm = Normalize(-2,2)
positive = grid[grid.state.eq('measured_nonzero')]
sc = ax.scatter(positive.marker_order,positive.population_order,s=positive.scatter_area_pt2,
 c=positive.mean_scaled_expression,cmap=cmap,norm=norm,edgecolors='none',linewidths=0,zorder=3)
absent = grid[~grid.measured]
missing_mark = ax.scatter(absent.marker_order,absent.population_order,s=12,marker='x',c='#70777e',linewidths=0.6,zorder=3)
for p in CFG['group_lines']['after_populations']:
 ax.axhline(populations.index(p)+0.5,color=CFG['group_lines']['color'],lw=0.6,zorder=1)
# Compact continuous guide at right, preserving fixed endpoints and midpoint.
cax=fig.add_axes(mmrect(CFG['guides']['colorbar_rect_mm']))
cbar=fig.colorbar(sc,cax=cax,ticks=[-2,0,2])
cbar.set_label('Scaled expression',size=8,labelpad=4)
cbar.outline.set_visible(False)
cbar.ax.tick_params(labelsize=8,length=3,width=0.6,pad=3)
# Quantitative size guide uses the exact same scatter transform and no outlines.
sizeax=fig.add_axes([0,0,1,1],frameon=False)
sizeax.set_xlim(0,W); sizeax.set_ylim(0,H); sizeax.set_axis_off()
size_title=sizeax.text(121,12,'Detected (%)',ha='center',va='center',size=8)
size_artists=[size_title]
for x,v in zip([98,117,137],CFG['guides']['size_values']):
 sizeax.scatter([x],[6.5],s=[64*v],c=['#59616c'],edgecolors='none',linewidths=0,zorder=3)
 size_artists.append(sizeax.text(x+4,6.5,f'{v*100:g}',ha='left',va='center',size=8))
# Presence/zero key, positioned in otherwise unoccupied lower-left area.
keyax=sizeax
missingkey=keyax.scatter([22],[13],s=12,marker='x',c='#70777e',linewidths=0.6)
missinglabel=keyax.text(26,13,'Not measured',va='center',ha='left',size=8)
zeroswatch=Rectangle((20.5,4.8),3,3,facecolor='white',edgecolor='#a2a7ad',lw=0.5)
keyax.add_patch(zeroswatch)
zerolabel=keyax.text(26,6.3,'0 (measured)',va='center',ha='left',size=8)
# Measure actual complete guide footprints from the raster renderer at export dpi.
fig.canvas.draw()
renderer=fig.canvas.get_renderer()
canvas_bbox=fig.bbox
mm_per_px=25.4/fig.dpi

def bbox_mm(b): return [round(v*mm_per_px,4) for v in [b.x0,b.y0,b.width,b.height]]
def union(artists): return Bbox.union([a.get_window_extent(renderer) for a in artists if a.get_visible()])
def disk_bbox(xmm,ymm,s):
 r=math.sqrt(s)*fig.dpi/72/2
 x=xmm/25.4*fig.dpi;y=ymm/25.4*fig.dpi
 return Bbox.from_extents(x-r,y-r,x+r,y+r)
size_bbox=Bbox.union([union(size_artists)]+[disk_bbox(x,6.5,64*v) for x,v in zip([98,117,137],[.25,.5,1])])
color_bbox=cax.get_tightbbox(renderer)
missing_bbox=Bbox.union([missinglabel.get_window_extent(renderer),disk_bbox(22,13,12)])
zero_bbox=union([zeroswatch,zerolabel])
state_bbox=Bbox.union([missing_bbox,zero_bbox])
combined=Bbox.union([size_bbox,color_bbox,state_bbox])
plot_bbox=ax.bbox
CFG['legend_layout'] = {'plot_bbox_mm':bbox_mm(plot_bbox),
 'complete_bounds_mm':{'color':bbox_mm(color_bbox),'size':bbox_mm(size_bbox),'presence':bbox_mm(state_bbox),
                       'combined_envelope':bbox_mm(combined)},
 'reserved_regions_mm':{'color':[159,45,20,53],'size':[94,2,61,14],'presence':[18,2,35,14]},
 'relative_to_plot':{name:{'width_ratio':b.width/plot_bbox.width,'height_ratio':b.height/plot_bbox.height,
                         'envelope_area_ratio':b.width*b.height/(plot_bbox.width*plot_bbox.height)}
                     for name,b in [('color',color_bbox),('size',size_bbox),('presence',state_bbox),('combined',combined)]},
 'text_pt':8,'size_areas_pt2':[16,32,64],
 'combined_envelope_note':'Envelope spans separated guides and includes empty space; judge individual guides and actual visual weight.'}
texts=[t for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()]
clipped=[]
for t in texts:
 b=t.get_window_extent(renderer)
 if b.x0<canvas_bbox.x0-.5 or b.y0<canvas_bbox.y0-.5 or b.x1>canvas_bbox.x1+.5 or b.y1>canvas_bbox.y1+.5:
  clipped.append(t.get_text())
collisions=[]
for axis_name,labels in [('x',ax.get_xticklabels()),('y',ax.get_yticklabels())]:
 boxes=[(t.get_text(),t.get_window_extent(renderer)) for t in labels]
 for i,(a,ba) in enumerate(boxes):
  for b,bb in boxes[i+1:]:
   if ba.overlaps(bb):collisions.append([axis_name,a,b])
assert not clipped, f'Clipped text: {clipped}'
assert not collisions, f'Tick collision: {collisions}'
assert all(t.get_fontsize()==8 for t in texts), 'Text not 8 pt'
for fmt in CFG['formats']: fig.savefig(ROOT/f'panel.{fmt}',dpi=300,bbox_inches=None,pad_inches=0)
plt.close(fig)
# Inspect serialized exports, rather than only in-memory canvas dimensions.
image=Image.open(ROOT/'panel.png')
pdf=PdfReader(ROOT/'panel.pdf')
page=pdf.pages[0]
pdf_size=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72]
svgroot=ET.parse(ROOT/'panel.svg').getroot()
svg_pt=[float(svgroot.attrib[k].replace('pt','')) for k in ['width','height']]
svg_mm=[v*25.4/72 for v in svg_pt]
pdf_fonts=[]
for f in page['/Resources']['/Font'].get_object().values():
 f=f.get_object(); descendants=f.get('/DescendantFonts',[])
 fd=descendants[0].get_object().get('/FontDescriptor').get_object() if descendants else f.get('/FontDescriptor',{})
 pdf_fonts.append({'basefont':str(f.get('/BaseFont')),'subtype':str(f.get('/Subtype')),
                   'embedded':any(k in fd for k in ['/FontFile','/FontFile2','/FontFile3'])})
# Render the actual PDF into a separate QA image.
pdfdoc=fitz.open(ROOT/'panel.pdf');pdfdoc[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(ROOT/'pdf-render.png')
svg_render_status='not_checked'
try:
 svgdoc=fitz.open(ROOT/'panel.svg')
 svgdoc[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(ROOT/'svg-render.png')
 svg_render_status='rendered via PyMuPDF; inspect independently of editable SVG text metadata'
except Exception as exc: svg_render_status=f'failed: {exc}'
checks={
 'data':{'input_rows':len(df),'plotted_nonzero_dots':len(positive),'zero_cells':int(grid.state.eq('measured_zero').sum()),
         'unmeasured_cells':len(absent),'grid_rows':len(grid),'duplicates':False,
         'values_unchanged':True,'populations':populations,'markers':markers},
 'geometry':{'requested_mm':[W,H],'pdf_mm':pdf_size,'svg_mm':svg_mm,'png_pixels':list(image.size),
             'expected_png_pixels':[round(W/25.4*300),round(H/25.4*300)],'png_dpi':image.info.get('dpi'),
             'raster_rounding_tolerance_px':1},
 'font':{'family':'Arial','path':font_path,'all_text_pt':8,'pdf_fonts':pdf_fonts,'svg_text_preserved':True},
 'layout':{'clipped_text':clipped,'same_axis_tick_collisions':collisions,'guide_bounds_saved':True},
 'actual_export_renders':{'pdf':'pdf-render.png','svg':svg_render_status},
 'artifacts_sha256':{f'panel.{fmt}':digest(ROOT/f'panel.{fmt}') for fmt in CFG['formats']}}
assert all(abs(a-b)<.01 for a,b in zip(pdf_size,[W,H]))
assert all(abs(a-b)<.01 for a,b in zip(svg_mm,[W,H]))
assert all(abs(a-b)<=1 for a,b in zip(image.size,checks['geometry']['expected_png_pixels']))
assert all(f['embedded'] for f in pdf_fonts)
(ROOT/'figure-settings.json').write_text(json.dumps(CFG,indent=2)+'\n')
(ROOT/'export-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
