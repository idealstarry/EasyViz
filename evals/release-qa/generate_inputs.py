"""Generate synthetic held-out workflow inputs; not biological evidence."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,TwoSlopeNorm
root=Path(__file__).resolve().parent / 'inputs'; rng=np.random.default_rng(290926)
rows=[]
markers=['IL6','CXCL10','TNF','CCL2','IL1RN','VEGFA']
for arm in ['Control','Treatment']:
 for i in range(12):
  donor=f'{arm[0]}{i+1:02}'
  baseline=rng.normal(5,1,6)
  for week in [0,4,12]:
   if (week==12 and i in [2,9]) or (week==4 and i==7):continue
   effect=np.array([-.7,-1.1,-.35,.1,.8,.3])*(week/8) if arm=='Treatment' else np.array([.1,.25,-.1,.2,.1,-.1])*(week/8)
   noise=np.zeros(6) if week==0 else rng.normal(0,.3,6)
   for marker,value in zip(markers,baseline+effect+noise):rows.append((donor,arm,week,marker,value))
pd.DataFrame(rows,columns=['donor_id','arm','week','analyte','log2_abundance']).to_csv(root/'create/source.csv',index=False)
(root/'create/request.md').write_text('''Use EasyViz to create one manuscript panel showing how the two treatment arms differ in change from baseline at weeks 4 and 12 across these six proteins. Show variation between participants as well as the typical changes. Source values are already normalized log2 protein abundances; do not run upstream analysis. Some visits were not measured; no imputation is authorized. Inferential tests are not required. Choose an informative visual design. Export PDF, SVG and PNG at 180 × 125 mm with Arial 8 pt, using blue/amber where arm colors are needed. No overall title, subtitle, footnote or panel letter in the artwork. Supply a separate caption, executable script, settings and plotting data.\n''')
genes=['LYZ','S100A8','FCGR3A','HLA-DRA','C1QC','APOE','IL1B','CXCL10']
cells=['Classical monocytes','Nonclassical monocytes','Resident macrophages','Inflammatory macrophages','DC2','Activated DC']
palette=LinearSegmentedColormap.from_list('signed',['#2581B9','#F7F8F9','#CC86B9']); norm=TwoSlopeNorm(0,-2,2)
vals=[]
for i,c in enumerate(cells):
 for j,g in enumerate(genes):
  fraction=float(rng.uniform(.04,.98)); expr=float(rng.uniform(-1.9,1.9))
  if (i,j)==(2,3):fraction=0
  vals.append((c,g,fraction,expr))
reference=pd.DataFrame(vals,columns=['population','marker','detected_fraction','mean_scaled_expression'])
plt.rcParams.update({'font.family':'Arial','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(155/25.4,105/25.4),dpi=220)
fig.subplots_adjust(left=.35,right=.85,bottom=.27,top=.95)
for i,c in enumerate(cells):
 for j,g in enumerate(genes):
  r=reference[(reference.population==c)&(reference.marker==g)].iloc[0]
  ax.scatter(j,i,s=r.detected_fraction*80,c=[palette(norm(r.mean_scaled_expression))],edgecolors='none')
ax.set(xticks=range(8),xticklabels=genes,yticks=range(6),yticklabels=cells,xlim=(-.6,7.6),ylim=(5.6,-.6))
ax.tick_params(length=0);ax.tick_params(axis='x',rotation=90)
for sp in ax.spines.values():sp.set_visible(False)
ax.axhline(1.5,color='#DCE2E7',lw=.5);ax.axhline(3.5,color='#DCE2E7',lw=.5)
cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=palette),cax=fig.add_axes([.9,.38,.015,.35]),ticks=[-2,0,2]);cb.set_label('Scaled expression',size=8);cb.outline.set_visible(False)
handles=[ax.scatter([],[],s=v*80,c='#59616B',edgecolors='none') for v in [.25,.5,1]]
fig.legend(handles,['25','50','100'],title='Detected (%)',ncol=3,frameon=False,loc='lower right',bbox_to_anchor=(.88,0),fontsize=8,title_fontsize=8)
fig.savefig(root/'reproduce/reference.png');plt.close(fig)
# New source differs from the reference in row count, labels, zeros and missing coordinates.
newrows=[]
for i,c in enumerate(cells+['Interferon-responsive Mo','Lipid-associated macrophages']):
 for j,g in enumerate(genes):
  if (i,j) in [(1,4),(6,2),(7,6)]:continue
  newrows.append((c,g,0 if (i,j) in [(2,3),(4,2)] else float(rng.uniform(.02,.98)),float(rng.uniform(-1.95,1.95))))
pd.DataFrame(newrows,columns=reference.columns).to_csv(root/'reproduce/source.csv',index=False)
(root/'reproduce/request.md').write_text('''Use EasyViz to reproduce the visual organization of reference.png using source.csv, which has additional cell populations and different values. No author code is available. Dot area encodes detected_fraction (0–1); color encodes mean_scaled_expression (−2 to 2). An absent population–marker row means not measured and must remain distinguishable from a measured detection fraction of zero. Population and marker order should follow their first appearance in the table. Retain the reference's useful grouping and style where applicable without inventing annotations for new populations. Deliver one 180 × 125 mm panel, Arial 8 pt, PDF/SVG/PNG, no overall title or in-image explanatory prose; necessary decoding keys are allowed. Save a separate caption, script, actual settings, plotting data and reference observation record.\n''')
(root/'provenance.json').write_text(json.dumps({'kind':'synthetic forward-test inputs','seed':290926,'biological_claim':False,'reference':'New synthetic reference image, no author or implementation code supplied to evaluated agent','access_boundary':'Instruction-based; not filesystem enforced','create_records':len(rows),'reproduce_records':len(newrows)},indent=2)+'\n')
