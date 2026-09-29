"""Generate explicitly synthetic input fixtures for the five built-in chart families."""
from pathlib import Path
import csv
import json
import random

ROOT = Path(__file__).resolve().parents[1] / 'skills/easyviz/assets/fixtures'
rng=random.Random(417)
base={'layout':{'width_mm':88,'height_mm':88,'font':'Arial','font_size_pt':8,'line_width_pt':0.6,'dpi':300,'margins':{'left':.20,'right':.77,'bottom':.20,'top':.91}},'formats':['pdf','png','svg','tiff'],'palette':'somerville-bright','seed':417}

def save(name,header,rows,more):
    d=ROOT/name;d.mkdir(parents=True,exist_ok=True)
    with (d/'data.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)
    spec={**base,**more};(d/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    (d/'provenance.json').write_text(json.dumps({'kind':'synthetic','purpose':'Renderer demonstration and validation; not a biological result.','seed':417,'generation':'scripts/generate_demo_inputs.py in development repository','rows':len(rows)},indent=2)+'\n')

save('heatmap',['feature','sample','score'],[[g,s,round(rng.uniform(-2,2),3)] for g in ['Gene A','Gene B','Gene C','Gene D','Gene E'] for s in ['S1','S2','S3','S4']],{'chart':'heatmap','fields':{'row':'feature','column':'sample','value':'score'},'colormap':'somerville-blue-coral','labels':{'x':'Sample','y':'Feature','color':'Score'},'options':{'color_limits':[-2,2],'color_center':0}})
save('composition',['sample','cell_type','count'],[[s,c,rng.randint(20,120)] for s in ['S1','S2','S3','S4'] for c in ['Type A','Type B','Type C']],{'chart':'composition','fields':{'sample':'sample','category':'cell_type','value':'count'},'options':{'normalization':'sample_sum','percent_axis':True},'labels':{'x':'Sample','y':'Composition (%)'},'order':{'category':['Type A','Type B','Type C']}})
save('dotplot',['gene','cluster','fraction','mean_score'],[[g,c,round(rng.uniform(0.05,1),3),round(rng.uniform(0,3),3)] for c in ['Type A','Type B','Type C','Type D'] for g in ['Gene A','Gene B','Gene C','Gene D']],{'chart':'dotplot','fields':{'x':'gene','y':'cluster','size':'fraction','color':'mean_score'},'colormap':'somerville-sky','labels':{'x':'Gene','y':'Cell type','color':'Mean score','size':'Fraction'},'layout':{**base['layout'],'width_mm':110,'height_mm':88},'options':{'size_max':1}})
save('scatter',['sample_id','x_score','y_score'],[[f'S{i+1}',i/3,round(i/4+rng.gauss(0,.9),3)] for i in range(30)],{'chart':'scatter','fields':{'x':'x_score','y':'y_score'},'labels':{'x':'Score X','y':'Score Y'},'statistics':{'method':'pearson','annotate':True},'options':{'regression':True}})
save('distribution',['sample_id','group','value'],[[f'{g}{i+1}',g,round(rng.gauss(mu,1.1),3)] for g,mu in [('Control',4),('Treatment',5.4)] for i in range(12)],{'chart':'distribution','fields':{'group':'group','value':'value','unit':'sample_id'},'labels':{'x':'Group','y':'Measurement'},'statistics':{'method':'welch','groups':['Control','Treatment'],'annotate':True},'options':{'kind':'box'}})
print('Generated five synthetic fixtures.')
