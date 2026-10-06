"""Prepare held-out Create specifications from forwarded requests only."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT.parent / 'forward-inputs'
REPO = ROOT.parents[2]

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

colors = {'Kerr':'#586BB5', 'Krieg':'#287E71', 'Petrus':'#C15C67'}
for inp in sorted(INPUTS.glob('*/request.json')):
    req=json.loads(inp.read_text()); task=ROOT/req['id']; task.mkdir(exist_ok=True)
    save(task/'request.json',req)
    raw=pd.read_csv(inp.parent/'measurements.csv',dtype=str)
    layout={'width_mm':req['panel_mm'][0], 'height_mm':req['panel_mm'][1], 'font':req['font'], 'font_size_pt':req['font_pt'], 'dpi':300, 'auto_fit':True}
    spec={'layout':layout,'formats':['pdf','svg','png']}
    n=req['id'][:2]
    data=inp.parent/'measurements.csv'
    if n in ['01','02']:
        spec.update(chart='replicate', fields={'condition':'display_condition','unit':'repeat_id','value':'repair_pct'}, order={'condition':raw.display_condition.drop_duplicates().tolist()},labels={'y':'HDR repair (%)'},options={'mode':'summary','uncertainty':'sample_sd','bar_style':'outline','bar_edge_width_pt':.6,'bar_color':'#444444','point_color':'#222222','bar_width':.42,'marker_area_pt2':5,'x_rotation':45,'y_limits':[0,14],'y_ticks':[0,5,10]})
        intent={'schema_version':1,'question':req['question'],'reading_task':'compare_estimates','leading_layer':'summary','organization':'compact','color_role':'labels'}
        if n=='02':
            data=task/'prepared.csv'
            long=raw.melt(id_vars=[c for c in raw if c not in ['repair_pct','joint_pct','endjoining_pct']],value_vars=['repair_pct','joint_pct','endjoining_pct'],var_name='outcome_field',value_name='measurement_pct')
            long['outcome']=long.outcome_field.map({'repair_pct':'HDR','joint_pct':'HDR + mutEJ','endjoining_pct':'mutEJ'})
            long.to_csv(data,index=False)
            spec['fields']={'condition':'display_condition','unit':'repeat_id','component':'outcome','value':'measurement_pct'}
            spec['order']['component']=['HDR','HDR + mutEJ','mutEJ'];spec['labels']={'y':'Repair outcomes (%)'}
            spec['colors']={'HDR':'#347AAF','HDR + mutEJ':'#CE6673','mutEJ':'#5C6B6C'}
            spec['options'].update(mode='grouped',bar_width=.8,component_gap=.055,x_rotation=0,y_limits=[0,55],y_ticks=[0,10,20,30,40,50]);spec['options'].pop('bar_color')
            intent.update(organization='repeated_groups',color_role='series')
    elif n in ['03','04']:
        spec.update(chart='distribution',fields={'group':'cohort_name','value':'body_mass_index','unit':'person_key'},order={'group':['Kerr','Krieg','Petrus']},colors=colors,labels={'x':'Cohort','y':'BMI (kg/m²)'},line_roles={'axis':{'line_width_pt':.55,'color':'#222222'},'summary':{'line_width_pt':.85,'color':'#333333'}},options={'kind':'box','box_style':'filled','box_width':.24,'box_fill_alpha':1,'point_style':'filled','alpha':1,'point_color':'#555555','point_area_pt2':5,'point_layout':'beeswarm','point_category_offset':.24,'point_max_offset_mm':5,'point_gap_pt':.2,'y_limits':[15,60],'grid':False})
        intent={'schema_version':1,'question':req['question'],'reading_task':'compare_distributions','leading_layer':'summary','organization':'separate_lanes','color_role':'summary_areas'}
        if n=='04':
            spec['options'].update(box_style='outline',box_width=.19,point_area_pt2=10,point_category_offset=.22,point_max_offset_mm=5)
            spec['options'].pop('point_color');spec['options'].pop('box_fill_alpha')
            spec['line_roles']['summary']={'line_width_pt':.5,'color':'#666666'}
            intent.update(reading_task='inspect_observations',leading_layer='observations',color_role='observations')
    elif n=='05':
        spec.update(chart='heatmap',fields={'row':'cell_state','column':'tissue_label','value':'within_depot_percent'},order={'y':raw.cell_state.drop_duplicates().tolist(),'x':['Omental','Perivascular','Subcutaneous']},colormap='Blues',labels={'color':'Within depot (%)'},options={'color_limits':[0,40],'annotate_values':True,'value_format':'.1f','cell_aspect':'auto','cell_border_color':'#D1DCE6','cell_border_width_pt':.3,'column_labels':{'Omental':'OM','Perivascular':'PVAT','Subcutaneous':'SC'}},legends={'colorbar':{'position':'right','thickness_mm':2.3}})
        intent={'schema_version':1,'question':req['question'],'reading_task':'read_matrix_values','leading_layer':'values','organization':'compact','color_role':'magnitude'}
    elif n=='06':
        data=task/'prepared.csv'
        assert raw.person_id.is_unique
        rows=[]
        for index,row in raw.iterrows():
            for visit,field,cell in [('Before','baseline_igg','before_source_cell'),('After','followup_igg','after_source_cell')]:
                rows.append({**row.to_dict(),'visit':visit,'igg':row[field],'source_value_field':field,'source_value_cell':row[cell],'source_input_row':index+2})
        pd.DataFrame(rows).to_csv(data,index=False)
        spec.update(chart='paired',fields={'unit':'person_id','condition':'visit','value':'igg','block':'infection_group'},order={'condition':['Before','After'],'block':['No prior infection','Prior infection']},colors={'No prior infection':'#347AAF','Prior infection':'#C05B76'},labels={'y':'IgG (BAU/ml, log scale)'},legends={'categorical':{'position':'top','ncol':2}},options={'y_scale':'log','y_limits':[40,50000],'y_ticks':[100,1000,10000],'quantile_method':'linear','point_layout':'jitter','point_spread':.36,'point_area_pt2':4,'point_alpha':1,'connect_pairs':True,'pair_alpha':.42,'pair_line_width_pt':.32,'summary_color':'#222222','summary_width':.42,'summary_cap_width':.15,'summary_line_width_pt':.8,'block_gap':.65,'seed':42,'grid':False})
        intent={'schema_version':1,'question':req['question'],'reading_task':'compare_within_unit_change','leading_layer':'observations','organization':'repeated_groups','color_role':'observations'}
    elif n=='08':
        # Source rows are descriptive observations; batch is not declared as a unit.
        spec={'row_kind':'observations','fields':{'group':'condition','value':'value'},'design':{'structure':'unknown','confirmed':False,'unit_definition':'One supplied source row; experimental unit is unknown.'},'measurement_units':None,'colors':{'Control':'#445C87','Treated':'#AD5F49'},'order':{'group':['Control','Treated']},'layout':layout,'labels':{'value':'Value','group':'Condition'},'formats':['pdf','svg','png'],'options':{'point_layout':'beeswarm','value_limits':[1.8,3.6]}}
        spec['layout'].pop('auto_fit')
        intent={'schema_version':1,'question':'Compare supplied value records between Control and Treated descriptively','reading_task':'inspect_observations','leading_layer':'observations','organization':'compact','color_role':'observations'}
    else:
        intent={'schema_version':1,'question':req['question'],'reading_task':'compare_trajectories','leading_layer':'summary','organization':'aligned_facets','color_role':'series'}
        spec.update(chart='custom-compartment-timecourse',fields={'compartment':'compartment','group':'condition','time':'hour','value':'ccl2','unit':'unit'},options={'uncertainty':'sample SEM = sample SD / sqrt(source row count)','connect_raw':False,'time_offset_description':'Raw dots within ±1.0 h of condition lane anchors at hour ±1.1 h; means/SEMs remain at true hour.'},colors={'Control':'#347AAF','IM-DTR':'#C5604F'},order={'compartment':['Lung','Serum'],'group':['Control','IM-DTR'],'time':[0,12,24,48]},labels={'x':'Time (h)'})
    save(task/'spec.json',spec); save(task/'create-intent.json',intent)
    save(task/'input-map.json',{'source':str(inp.parent/'measurements.csv'),'plotting_data':str(data),'raw_rows':len(raw),'inference':False,'constraint_input':str(inp)})
    script='''from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
PY=REPO/'.venv/bin/python'
'''
    if n in ['01','02','03','04','05']:
        script+=f"subprocess.run([str(PY),str(REPO/'skills/easyviz/scripts/create_candidates.py'),'--data',{str(data)!r},'--spec',str(ROOT/'spec.json'),'--intent',str(ROOT/'create-intent.json'),'--out',str(ROOT/'first-render'),'--new-draft','--count','1'],check=True)\n"
    elif n=='06':
        script+=f"subprocess.run([str(PY),str(REPO/'skills/easyviz/scripts/paired_plot.py'),'--data',{str(data)!r},'--spec',str(ROOT/'spec.json'),'--out',str(ROOT/'first-render')],check=True)\n"
    elif n=='08':
        script+=f"subprocess.run([str(PY),str(REPO/'skills/easyviz/scripts/preview_choices.py'),'--data',{str(data)!r},'--request',str(ROOT/'spec.json'),'--out',str(ROOT/'first-render')],check=True)\n"
    else:script+="subprocess.run([str(PY),str(ROOT/'plot.py')],check=True)\n"
    (task/'run.py').write_text(script)

