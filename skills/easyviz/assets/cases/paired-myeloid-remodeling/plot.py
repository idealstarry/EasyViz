#!/usr/bin/env python3
"""Compare three designs of participant-paired, precomputed deconvolution scores.

This custom design recipe accepts tidy source scores and explicit subtype
annotations. Statistical summaries are recomputed from all complete pairs;
upstream deconvolution is deliberately outside this script.
"""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'easyviz-remodeling-mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle
from matplotlib.text import Text
import numpy as np
import pandas as pd
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import linprog

HERE=Path(__file__).resolve().parent
INK='#111111'; MUTED='#111111'; GRID='#D7D7D7'

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)

def pack_points(values_mm, diameter_pt, maximum_mm, *, gap_pt=.1, seed=23):
    """Pack circles at exact x values inside a measured, deterministic y lane.

    Greedy tangent placement provides a vertical ordering. A linear program
    repairs that ordering while minimizing total absolute y displacement.
    Stroke width must already be included in ``diameter_pt`` for hollow marks.
    Failed lanes are reported rather than made transparent or silently dropped.
    """
    x=np.asarray(values_mm,dtype=float)*72/25.4
    n=len(x); maximum=maximum_mm*72/25.4; separation=diameter_pt+gap_pt
    pairs=[(i,j,float(np.sqrt(separation**2-(x[i]-x[j])**2)))
           for i in range(n) for j in range(i+1,n) if abs(x[i]-x[j])<separation]
    last_failure=None
    for attempt in range(24):
        rng=np.random.default_rng(seed+attempt)
        order=np.lexsort((rng.random(n),x)); y=np.zeros(n); placed=[]
        for i in order:
            active=[j for j in placed if abs(x[i]-x[j])<separation]
            candidates=[0.,-maximum,maximum]
            for j in active:
                radius=np.sqrt(separation**2-(x[i]-x[j])**2)
                candidates.extend([y[j]-radius,y[j]+radius])
            valid=[float(v) for v in candidates if -maximum-1e-9<=v<=maximum+1e-9
                   and all((x[i]-x[j])**2+(v-y[j])**2>=separation**2-1e-8 for j in active)]
            preference=bool(rng.integers(2))
            if valid:
                y[i]=min(valid,key=lambda v:(round(abs(v),8),v<0 if preference else v>0))
            else:
                grid=np.linspace(-maximum,maximum,129)
                y[i]=min(grid,key=lambda v:(sum((x[i]-x[j])**2+(v-y[j])**2<separation**2-1e-8 for j in active),abs(v)))
            placed.append(i)
        rows=[]; bounds=[]
        for i,j,radius in pairs:
            high,low=(i,j) if (y[i],i)>(y[j],j) else (j,i)
            row=np.zeros(2*n);row[high]=-1;row[low]=1
            rows.append(row);bounds.append(-radius)
        for i in range(n):
            for sign in (-1,1):
                row=np.zeros(2*n);row[i]=sign;row[n+i]=-1
                rows.append(row);bounds.append(0.)
        solution=linprog(np.r_[np.zeros(n),np.ones(n)],A_ub=np.asarray(rows),b_ub=np.asarray(bounds),
                         bounds=[(-maximum,maximum)]*n+[(0,None)]*n,method='highs')
        if solution.success:
            y=solution.x[:n]
            distances=[float(np.hypot(x[i]-x[j],y[i]-y[j])) for i in range(n) for j in range(i+1,n)]
            violations=sum(v<separation-1e-6 for v in distances)
            require(not violations,'Packed circles failed an independent distance audit')
            return y*25.4/72,{'status':'pass','attempt':attempt,'seed':seed+attempt,
                'circle_outer_diameter_pt':diameter_pt,'requested_gap_pt':gap_pt,
                'maximum_allowed_offset_mm':maximum_mm,'maximum_actual_offset_mm':float(np.max(abs(y))*25.4/72),
                'minimum_center_distance_pt':min(distances) if distances else None,
                'overlapping_circle_pairs':0,'spacing_violation_pairs':0,'participants':n}
        last_failure=solution.message
    return None,{'status':'needs_revision','circle_outer_diameter_pt':diameter_pt,
                'maximum_allowed_offset_mm':maximum_mm,'participants':n,
                'reason':'No feasible lane found across 24 deterministic tangent orderings. '+str(last_failure)}

def pair_data(data, annotations, cohorts, year):
    required={'cohort','participant','year','subtype','score'}
    require(required<=set(data),f'Missing columns: {required-set(data)}')
    for column in ('cohort','participant','subtype'):
        require(not data[column].isna().any() and not data[column].astype(str).str.strip().eq('').any(),
                f'{column} IDs must be nonempty; unnamed records cannot be paired')
    require(not data.duplicated(['cohort','participant','year','subtype']).any(),'Duplicate participant/time/subtype record')
    require(np.isfinite(data.score).all(),'Scores must be finite; missing scores cannot be imputed')
    wanted=[f'myC{a["cluster"]:02}' for a in annotations]
    data=data[data.cohort.isin(cohorts) & data.year.isin([0,year])].copy()
    require(set(data.subtype)==set(wanted),'Subtype annotations must exactly match requested source columns')
    a=data[data.year==0].set_index(['cohort','participant','subtype']).score
    b=data[data.year==year].set_index(['cohort','participant','subtype']).score
    missing=sorted(set(a.index)^set(b.index))
    require(not missing,f'Unmatched baseline/follow-up rows: {missing[:8]}')
    joined=pd.DataFrame({'baseline':a,'followup':b}).reset_index()
    joined['change']=joined.followup-joined.baseline
    require(not joined.isna().any().any(),'Incomplete pairs')
    for (cohort,participant), group in joined.groupby(['cohort','participant']):
        require(set(group.subtype)==set(wanted),f'Incomplete subtype coverage: {cohort}/{participant}')
    require(set(joined.cohort)==set(cohorts),'Requested cohorts must all be present')
    return joined

def rows_geometry(annotations):
    ys={}; groups=[]; y=103.; last=None
    for a in annotations:
        if last is not None and last!=a['display_group']: y-=2.0
        if last!=a['display_group']: groups.append([a['display_group'],y,y])
        else: groups[-1][2]=y
        ys[f'myC{a["cluster"]:02}']=y
        y-=4.6; last=a['display_group']
    return ys,groups

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=HERE/'source-data.csv')
    p.add_argument('--settings',type=Path,default=HERE/'figure-settings.json')
    p.add_argument('--annotations',type=Path,default=HERE/'annotations.json')
    p.add_argument('--out',type=Path,default=HERE/'output')
    p.add_argument('--year',type=int,default=2)
    p.add_argument('--cohorts',nargs='+')
    p.add_argument('--design',choices=['all','baseline','participant-matrix','distribution-ledger'],default='all')
    args=p.parse_args(); cfg=json.loads(args.settings.read_text()); ann=json.loads(args.annotations.read_text())
    cohorts=args.cohorts or cfg['cohort_order']; font=cfg['font_size_pt']
    marks=cfg.get('marks',{})
    require(font==8,'The evaluation fixes every text role at 8 pt')
    require([cfg['width_mm'], cfg['height_mm']]==[180,125],'This recipe fixes the canvas at 180 × 125 mm; revise the physical geometry for another size')
    require(args.year>0,'Follow-up year must be later than baseline')
    require(1<=len(cohorts)<=2,'This recipe supports one or two cohorts; use another layout for more cohorts')
    require(len(set(cohorts))==len(cohorts),'Cohorts must be unique')
    require(1<=len(ann)<=16,'This 125 mm layout needs one to 16 subtypes; do not shrink typography')
    require(len({a['cluster'] for a in ann})==len(ann),'Subtype annotations must be unique')
    require(np.isfinite(cfg['change_xlim']).all() and cfg['change_xlim'][0]<0<cfg['change_xlim'][1], 'The change axis must be finite, ascending and contain zero')
    plt.rcParams.update({'font.family':cfg['font'],'font.size':font,'axes.labelsize':font,
                         'xtick.labelsize':font,'ytick.labelsize':font,'legend.fontsize':font,
                         'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':True,
                         'mathtext.fontset':'custom','mathtext.rm':cfg['font'],
                         'mathtext.it':f"{cfg['font']}:italic",'mathtext.cal':cfg['font']})
    data=pd.read_csv(args.data,keep_default_na=False,dtype={'participant':str})
    paired=pair_data(data,ann,cohorts,args.year)
    require(paired.change.between(*cfg['change_xlim']).all(),'Observed change falls outside fixed comparison axis; explicitly widen the shared axis')
    args.out.mkdir(parents=True,exist_ok=True)
    paired.to_csv(args.out/'paired-changes.csv',index=False,float_format='%.17g')
    ys,groups=rows_geometry(ann)
    ns={c:paired[paired.cohort==c].participant.nunique() for c in cohorts}
    stats={}
    for (cohort,subtype), rows in paired.groupby(['cohort','subtype']):
        v=rows.change.to_numpy()
        stats[(cohort,subtype)]={'median':float(np.median(v)),'q1':float(np.quantile(v,.25)),'q3':float(np.quantile(v,.75)),
                               'min':float(v.min()),'max':float(v.max()),'n':len(v),'negative_percent':float((v<0).mean()*100)}
    statrows=[{'cohort':c,'subtype':s,**v} for (c,s),v in stats.items()]
    pd.DataFrame(statrows).to_csv(args.out/'summary.csv',index=False,float_format='%.17g')
    W,H=cfg['width_mm'],cfg['height_mm']
    plots=[args.design] if args.design!='all' else ['baseline','participant-matrix','distribution-ledger']
    records={}; placement_rows=[]
    for design in plots:
        fig=plt.figure(figsize=(W/25.4,H/25.4),dpi=cfg['dpi'])
        ax=fig.add_axes([0,0,1,1]); ax.set(xlim=(0,W),ylim=(0,H)); ax.axis('off')
        def tx(x,y,s,**kw): return ax.text(x,y,s,fontsize=font,va='center',**{'color':INK,**kw})
        def line(xs,ye,color=GRID,lw=.5,**kw): return ax.plot(xs,ye,color=color,lw=lw,**kw)
        def dot(x,y,color,area=10,**kw): return ax.scatter(x,y,s=area,c=color,edgecolors='none',linewidths=0,alpha=1,**kw)
        def rr(x,y,w,h,c,**kw): ax.add_patch(Rectangle((x,y),w,h,facecolor=c,edgecolor='none',**kw))
        def label_rows(grouped=True):
            for a in ann:
                s=f'myC{a["cluster"]:02}'; label=a['label'].replace('Non-classical Mo','Non-class. Mo').replace('Classical Mo','Class. Mo')
                tx(6,ys[s],f'{s}  {label}')
            if grouped:
                for _,top,bottom in groups[1:]:
                    line([5,176],[top+3.3,top+3.3],color=marks.get('separator_color',GRID),
                         lw=marks.get('separator_line_width_pt',.45))
        def scale(x0,x1): return lambda v:x0+(np.asarray(v)-cfg['change_xlim'][0])/(cfg['change_xlim'][1]-cfg['change_xlim'][0])*(x1-x0)
        def iqr_box(xx,st,y,color,height=.75,width=None):
            left,right=float(xx(st['q1'])),float(xx(st['q3']))
            ax.add_patch(Rectangle((left,y-height/2),right-left,height,facecolor='none',edgecolor=color,
                                  linewidth=width or marks.get('summary_line_width_pt',.65),zorder=4))
            line([xx(st['median']),xx(st['median'])],[y-height/2,y+height/2],color=INK,
                 lw=marks.get('summary_line_width_pt',.65),zorder=5)
        def horizontal_axis(x0,x1,y,label):
            xx=scale(x0,x1)
            line([x0,x1],[y,y],color=marks.get('axis_color','#8A929B'),lw=marks.get('axis_line_width_pt',.5))
            for tick in cfg['change_ticks']:
                line([xx(tick),xx(tick)],[y,y-1],color=marks.get('axis_color','#8A929B'),lw=marks.get('axis_line_width_pt',.5))
                tx(xx(tick),y-3.5,str(tick),ha='center')
            if label:tx((x0+x1)/2,y-8.2,label,ha='center')
            return xx
        offsets=np.linspace(.92,-.92,len(cohorts)) if len(cohorts)>1 else [0]
        point_audits=[]; hollow_audits=[]
        if design=='baseline':
            # A competent conventional baseline, with matched differences rather
            # than misleading unpaired before/after boxes.
            bx=fig.add_axes([43/W,23/H,130/W,84/H]); bx.set_axisbelow(True)
            baseline_offsets=np.linspace(1.15,-1.15,len(cohorts)) if len(cohorts)>1 else [0]
            for ci,c in enumerate(cohorts):
                for a in ann:
                    s=f'myC{a["cluster"]:02}'; values=paired[(paired.cohort==c)&(paired.subtype==s)].change.to_numpy()
                    y=ys[s]+baseline_offsets[ci]
                    bx.boxplot(values,positions=[y],orientation='horizontal',widths=1.55,patch_artist=True,showfliers=False,
                        boxprops={'facecolor':'none','edgecolor':cfg['cohort_colors'][c],'linewidth':.65},
                        medianprops={'color':INK,'linewidth':.7},whiskerprops={'color':cfg['cohort_colors'][c],'linewidth':.7},
                        capprops={'color':cfg['cohort_colors'][c],'linewidth':.7},manage_ticks=False)
                    diameter=marks.get('participant_diameter_pt',1.2)
                    positions,info=pack_points((values-cfg['change_xlim'][0])/(cfg['change_xlim'][1]-cfg['change_xlim'][0])*130,
                                              diameter,.9,gap_pt=marks.get('participant_gap_pt',.1),seed=23)
                    require(positions is not None,f'Baseline participant lane cannot fit {c}/{s}: {info}')
                    point_audits.append({'cohort':c,'subtype':s,**info})
                    bx.scatter(values,y+positions,s=diameter**2,c=cfg['cohort_colors'][c],edgecolors='none',linewidths=0,alpha=1,zorder=3)
            bx.set(ylim=(23,107),xlim=cfg['change_xlim'],xticks=cfg['change_ticks'],yticks=[],xlabel=f'Change in deconvolution score ({args.year} years − baseline)')
            bx.axvline(0,color=marks.get('reference_color','#9EA6AE'),lw=marks.get('reference_line_width_pt',.7),ls='--',zorder=0)
            bx.grid(False)
            bx.spines[['top','right','left']].set_visible(False);bx.spines['bottom'].set_color(INK);bx.spines['bottom'].set_linewidth(.5)
            bx.tick_params(axis='x',length=2,width=.5)
            label_rows(False)
            for i,c in enumerate(cohorts):
                rr(47+i*42,115,2,2,cfg['cohort_colors'][c]);tx(50+i*42,116,f'{c} ($n$ = {ns[c]})')
        elif design=='participant-matrix':
            label_rows(); x0,xend=44.,126.; gap=2.0
            cellw=(xend-x0-gap*(len(cohorts)-1))/sum(ns.values())
            require(cellw>=1.0,'Participant columns would be narrower than 1 mm; choose a wider layout or a distribution view')
            require(paired.change.between(*cfg['matrix_limits']).all(),'Matrix color range would clip observed values; explicitly revise the shared scale')
            require(np.isfinite(cfg['matrix_limits']).all() and cfg['matrix_limits'][0]<0 and cfg['matrix_limits'][1]==-cfg['matrix_limits'][0], 'This diverging recipe requires finite symmetric color limits so neutral means zero')
            cmap=LinearSegmentedColormap.from_list('score_change',cfg['matrix_colors']); norm=Normalize(*cfg['matrix_limits'])
            participant_order={}
            for c in cohorts:
                cp=paired[paired.cohort==c]
                order=cp.groupby('participant').change.median().sort_values(kind='stable').index.tolist()
                participant_order[c]=order
                width=cellw*len(order)
                tx(x0+width/2,114,f'{c} ($n$ = {ns[c]})',ha='center')
                line([x0,x0+width],[110,110],color=cfg['cohort_colors'][c],lw=.65)
                values=cp.pivot(index='subtype',columns='participant',values='change')
                for a in ann:
                    s=f'myC{a["cluster"]:02}'
                    for j,participant in enumerate(order): rr(x0+j*cellw,ys[s]-2.05,cellw,4.1,cmap(norm(values.loc[s,participant])))
                tx(x0+cellw/2,21.8,'1',ha='center');tx(x0+width-cellw/2,21.8,str(len(order)),ha='center')
                x0+=width+gap
            tx(85,16,'Participant order',ha='center')
            pd.DataFrame([{'cohort':c,'rank':i+1,'participant':p} for c,order in participant_order.items() for i,p in enumerate(order)]).to_csv(args.out/'participant-order.csv',index=False)
            xx=scale(134,175)
            line([xx(0),xx(0)],[28,107],color=marks.get('reference_color','#9EA6AE'),lw=marks.get('reference_line_width_pt',.55),ls='--')
            for a in ann:
                s=f'myC{a["cluster"]:02}'
                for ci,c in enumerate(cohorts):
                    st=stats[c,s];yy=ys[s]+offsets[ci]
                    iqr_box(xx,st,yy,cfg['cohort_colors'][c],height=.95,
                            width=marks.get('marginal_summary_line_width_pt',.65))
            tx(154.5,109,'Median / IQR',ha='center')
            for ci,c in enumerate(cohorts): tx(134+ci*23,116,c,color=cfg['cohort_colors'][c])
            # The quantitative color guide shows the entire declared scale; no clipping.
            cbax=fig.add_axes([45/W,4.8/H,38/W,1.8/H])
            cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cbax,orientation='horizontal',ticks=[cfg['matrix_limits'][0],0,cfg['matrix_limits'][1]]);cb.outline.set_visible(False)
            cb.ax.tick_params(length=1.5,width=.4,pad=1)
            tx(45,10.8,'Change in score')
            # Summary axis is intentionally sparse because it is a marginal guide.
            for tick in [cfg['change_xlim'][0],0,cfg['change_xlim'][1]]: tx(xx(tick),21.8,str(tick),ha='center')
            tx(154.5,16,'Change in score',ha='center')
        else:
            label_rows()
            facets=[(35.,93.,100.),(110.,168.,175.)] if len(cohorts)==2 else [(35.,168.,175.)]
            for c,(x0,x1,ledger_x) in zip(cohorts,facets):
                xx=scale(x0,x1); color=cfg['cohort_colors'][c]
                tx((x0+x1)/2,115,f'{c} ($n$ = {ns[c]})',ha='center')
                line([x0,x1],[111,111],color=color,lw=.65)
                tx(ledger_x,113,'<0',ha='center');tx(ledger_x,109,'(%)',ha='center')
                line([xx(0),xx(0)],[26,107],color=INK,lw=marks.get('reference_line_width_pt',.45),
                     ls=(0,tuple(marks.get('reference_dash_pattern_pt',[2,2]))),zorder=0)
                for a in ann:
                    s=f'myC{a["cluster"]:02}'
                    rows=paired[(paired.cohort==c)&(paired.subtype==s)].sort_values('participant')
                    values=rows.change.to_numpy(); st=stats[c,s]
                    # Test the requested hollow-circle policy at the same geometry.
                    _,hollow=pack_points(xx(values),2.0,marks.get('participant_max_offset_mm',1.5),
                                         gap_pt=marks.get('participant_gap_pt',.1),seed=23)
                    hollow_audits.append({'cohort':c,'subtype':s,**hollow})
                    diameter=marks.get('participant_diameter_pt',1.2)
                    packed,info=pack_points(xx(values),diameter,marks.get('participant_max_offset_mm',1.5),
                                            gap_pt=marks.get('participant_gap_pt',.1),seed=23)
                    require(packed is not None,f'Participant lane cannot fit {c}/{s}: {info}')
                    point_audits.append({'cohort':c,'subtype':s,**info})
                    yy=ys[s]+.45+packed
                    dot(xx(values),yy,color,diameter**2,zorder=2)
                    # A dedicated lower strip keeps summary boxes off the raw marks.
                    iqr_box(xx,st,ys[s]-1.7,color,height=.55)
                    tx(ledger_x,ys[s],f'{st["negative_percent"]:.0f}',ha='center')
                    for participant,value,x,y in zip(rows.participant,values,xx(values),yy):
                        placement_rows.append({'design':design,'cohort':c,'subtype':s,'participant':participant,
                                               'change':float(value),'x_mm':float(x),'y_mm':float(y)})
                horizontal_axis(x0,x1,23,None)
            tx(104,14.8,f'Change in deconvolution score ({args.year} years − baseline)',ha='center')
            # Essential layer keys, with the same outline and fill policies as data.
            iqr_box(lambda v:v,{'q1':58,'q3':63,'median':60.5},6.3,INK,height=.9)
            tx(66,6.3,'Median / IQR')
            dot(111,6.3,INK,marks.get('participant_diameter_pt',1.2)**2);tx(114,6.3,'Participant')
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        problems=[];fonts=[]
        for artist in fig.findobj(Text):
            if not artist.get_visible() or not artist.get_text():continue
            box=artist.get_window_extent(renderer);fonts.append(artist.get_fontsize())
            if box.x0<-.5 or box.y0<-.5 or box.x1>fig.bbox.width+.5 or box.y1>fig.bbox.height+.5:
                problems.append({'text':artist.get_text(),'bbox_px':list(box.bounds)})
        require(not problems,f'Text outside physical canvas: {problems}')
        require(set(fonts)=={8.},f'Unapproved font sizes: {set(fonts)}')
        out=args.out/design;out.mkdir(exist_ok=True)
        for suffix in ('png','pdf','svg'):fig.savefig(out/f'panel.{suffix}',dpi=cfg['dpi'],facecolor='white',bbox_inches=None)
        plt.close(fig)
        pdf=PdfReader(out/'panel.pdf').pages[0]
        dims=[float(pdf.mediabox.width)*25.4/72,float(pdf.mediabox.height)*25.4/72]
        require(np.allclose(dims,[W,H],atol=.01),'Physical canvas changed during export')
        records[design]={'formats':{suffix:digest(out/f'panel.{suffix}') for suffix in ('png','pdf','svg')},
                         'width_height_mm':dims,'text_sizes_pt':sorted(set(fonts)),'text_outside_canvas':problems,
                         'all_paired_changes_preserved':len(paired),'points_or_matrix_cells':len(paired),
                         'participant_point_layout':point_audits,
                         'hollow_circle_feasibility_trial':hollow_audits,
                         'comparability':'Same source pairs, canvas, font, selected subtypes, and shared axis/color settings.'}
    if len(plots)==3:
        # A review board outside the manuscript exports; retain the complete
        # individual canvases and use identical display scaling for all three.
        preview_width=1000
        preview_height=round(preview_width*H/W)
        board=Image.new('RGB',(3*preview_width+40,preview_height+58),'white')
        draw=ImageDraw.Draw(board)
        preview_font=ImageFont.truetype(font_manager.findfont(cfg['font']),24)
        names=['Box and observations','Participant correspondence','Magnitude and consistency']
        for index,(design,name) in enumerate(zip(plots,names)):
            x=10+index*(preview_width+10)
            with Image.open(args.out/design/'panel.png') as preview:
                board.paste(preview.convert('RGB').resize((preview_width,preview_height),Image.Resampling.LANCZOS),(x,48))
            draw.text((x+preview_width/2,18),name,font=preview_font,fill=INK,anchor='mm')
        board.save(args.out/'comparison.png')
    if placement_rows:pd.DataFrame(placement_rows).to_csv(args.out/'participant-placement.csv',index=False,float_format='%.17g')
    (args.out/'figure-settings.json').write_text(json.dumps(cfg,indent=2)+'\n')
    audit={'status':'passed','source_sha256':digest(args.data),'settings_sha256':digest(args.settings),
           'actual_font_path':font_manager.findfont(cfg['font'],fallback_to_default=False),
           'actual_cohort_colors':{c:cfg['cohort_colors'][c] for c in cohorts},'mark_roles':marks,
           'followup_year':args.year,'cohorts':ns,
           'paired_participants':sum(ns.values()),'subtypes':len(ann),'paired_changes':len(paired),
           'missing_pairs':0,'imputed_values':0,'change_range':[paired.change.min(),paired.change.max()],
           'score_unit':'Published deconvolution score; differences are score units, not proportions or percentage points.',
           'summary_interval':'Interquartile range of participant differences; not a confidence interval.',
           'designs':records}
    (args.out/'qa.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'output':str(args.out),'status':'passed','paired_changes':len(paired),'designs':plots}))

if __name__=='__main__':main()
