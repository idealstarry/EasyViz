"""Cross-sectional time responses; raw rows are never paired across hours."""
from pathlib import Path
import sys, json, hashlib, argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
sys.path.insert(0,str(REPO/'skills/easyviz/scripts'))
import render as core
import panel_readability

SPEC=ROOT/'spec.json'
SOURCE=REPO/'evals/development-v0.5.0/forward-inputs/07-separate-compartments/measurements.csv'
parser=argparse.ArgumentParser();parser.add_argument('--out',default='first-render');args=parser.parse_args()
spec=json.loads(SPEC.read_text())
raw=pd.read_csv(SOURCE,dtype=str,keep_default_na=False)
data=raw.copy()
data['source_input_row']=np.arange(len(data))+2
data['hour']=pd.to_numeric(data.hour)
data['ccl2']=pd.to_numeric(data.ccl2)
assert len(data)==88 and data[['source_sheet','source_cell']].duplicated().sum()==0
source_digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
for compartment in spec['order']['compartment']:
    out=ROOT/args.out/compartment.lower();out.mkdir(parents=True,exist_ok=True)
    (out/'plot-source.py').write_bytes(Path(__file__).read_bytes())
    selected=data[data.compartment==compartment].copy()
    assert selected.unit.nunique()==1
    layout,typography,rc=core.setup(spec)
    with plt.rc_context(rc):
        fig,ax=plt.subplots(figsize=(layout['width_mm']/25.4,layout['height_mm']/25.4),dpi=layout['dpi'])
        # Shared physical axes and typography; each compartment has its own quantity.
        fig.subplots_adjust(left=.195,right=.97,bottom=.19,top=.855)
        points=[];means=[];summary=[];plotrows=[]
        for gi,group in enumerate(spec['order']['group']):
            color=spec['colors'][group]
            for hour in spec['order']['time']:
                subset=selected[(selected.condition==group)&(selected.hour==hour)].copy()
                values=subset.ccl2.to_numpy(float)
                n=len(values);mean=float(np.mean(values));sd=float(np.std(values,ddof=1));sem=sd/np.sqrt(n)
                summary.append({'compartment':compartment,'condition':group,'hour':hour,'mean':mean,'sample_sd':sd,'sem':sem,'source_row_count':n,'unit':selected.unit.iloc[0]})
                offsets=np.linspace(-.85,.85,n)+(gi-.5)*2.4
                x=hour+offsets
                points.append((ax.scatter(x,values,s=9,facecolors='white',edgecolors=color,linewidths=.65,zorder=3),subset,x))
                # Exact-time anchors; marker interiors distinguish near-coincident means.
                ax.vlines(hour,mean-sem,mean+sem,color=color,linewidth=.8,zorder=4)
                means.append((ax.plot([hour],[mean],marker='o' if gi==0 else 's',markersize=3.6,markerfacecolor='white' if gi==0 else color,markeredgewidth=.8,color=color,zorder=5)[0],mean,hour))
                for (_,row),xx in zip(subset.iterrows(),x):plotrows.append({**row.to_dict(),'display_hour':float(xx),'true_hour':hour,'time_offset':float(xx-hour)})
            summaries=[s for s in summary if s['condition']==group]
            ax.plot([s['hour'] for s in summaries],[s['mean'] for s in summaries],color=color,linewidth=.8,zorder=2,clip_on=True)
        ax.set_xlim(-4,52)
        ymax=250 if compartment=='Lung' else 400
        # Limits established from every actual raw value and interval, never clipped.
        envelope=max(selected.ccl2.max(),max(s['mean']+s['sem'] for s in summary))
        ymax=max(ymax,float(np.ceil(envelope/50)*50))
        ax.set_ylim(0,ymax*1.05)
        ax.set_xticks(spec['order']['time'])
        ax.set_yticks(np.arange(0,ymax+1,50 if compartment=='Lung' else 100))
        ax.set_xlabel('Time (h)')
        ylabel='Ccl2 (pg/mg protein)' if compartment=='Lung' else 'Ccl2 (pg/ml)'
        ax.set_ylabel(ylabel)
        ax.spines[['top','right']].set_visible(False)
        ax.set_axisbelow(True)
        from matplotlib.lines import Line2D
        handles=[Line2D([],[],color=spec['colors'][g],marker='o' if i==0 else 's',markerfacecolor='white' if i==0 else spec['colors'][g],markersize=3.6,markeredgewidth=.8,linewidth=.8,label=g) for i,g in enumerate(spec['order']['group'])]
        ax.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,1.03),ncol=2,frameon=False,handlelength=1.4,columnspacing=1.5)
        fig.canvas.draw()
        artist_ok=all(np.array_equal(np.asarray(artist.get_offsets())[:,1],subset.ccl2.to_numpy(float)) and np.array_equal(np.asarray(artist.get_offsets())[:,0],xs) for artist,subset,xs in points)
        assert artist_ok and sum(len(subset) for _,subset,_ in points)==len(selected)
        assert all(np.array_equal(artist.get_xdata(),[hour]) and np.array_equal(artist.get_ydata(),[mean]) for artist,mean,hour in means)
        summary_data=pd.DataFrame(summary)
        # Verify each mean/SEM independently from the input subset.
        for row in summary:
            values=selected[(selected.condition==row['condition'])&(selected.hour==row['hour'])].ccl2.to_numpy(float)
            assert np.isclose(row['mean'],sum(values)/len(values))
            assert np.isclose(row['sem'],np.sqrt(sum((values-row['mean'])**2)/(len(values)-1))/np.sqrt(len(values)))
        from matplotlib.text import Text
        from matplotlib.font_manager import findfont
        from matplotlib.ft2font import FT2Font
        painter=fig.canvas.get_renderer()
        clipped=[]
        missing=[]
        for text in fig.findobj(Text):
            if not text.get_visible() or not text.get_text().strip():continue
            bounds=text.get_window_extent(painter)
            if bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.width+1 or bounds.y1 > fig.bbox.height+1:clipped.append({'text':text.get_text(),'bounds_px':bounds.extents.tolist()})
            cmap=FT2Font(findfont(text.get_fontproperties())).get_charmap()
            for char in text.get_text():
                if not char.isspace() and ord(char) not in cmap:missing.append({'text':text.get_text(),'glyph':char})
        overlap,oblique=core.check_tick_label_overlap(fig,fig.canvas.get_renderer())
        readability=panel_readability.measure(fig)
        exports=core.export(fig,out,spec,layout)
        pd.DataFrame(plotrows).to_csv(out/'plotting-data.csv',index=False)
        summary_data.to_csv(out/'summary-data.csv',index=False)
        (out/'caption.md').write_text(f'{compartment} Ccl2 concentrations at the supplied terminal, cross-sectional time points. Each open circle is one supplied observation; the group-colored line connects arithmetic means at the exact sampling hours, and vertical intervals show sample SEM (sample SD with ddof = 1 divided by the square root of the source-row count). Control means use open circles and IM-DTR means use filled squares to distinguish near-coincident anchors. Raw observations are displayed in compact condition lanes around each true hour, with offsets of at most 2.05 h solely for visibility; they are not additional sampling times. No individual is connected across hours because sample positions do not establish longitudinal identity. The {compartment.lower()} panel retains {len(selected)} observations; each time/group uses the counts saved in summary-data.csv. No test, fitted model or significance annotation is adopted. Units are {selected.unit.iloc[0]}.\n')
        settings={'input':{'data_file':str(SOURCE),'source_script':str(out/'plot-source.py'),'spec_file':str(SPEC),'supplied_spec_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest()},'version':{'input_sha256':source_digest,'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'layout':layout,'typography':typography,'formats':spec['formats'],'spec':spec,'track':'create','caption_file':str(out/'caption.md')}
        issues=clipped+overlap+missing
        qa={'status':'pass' if not issues else 'needs_revision','valid_outputs':not issues,'input_rows':len(data),'plotted_input_rows':len(selected),'input_sha256':source_digest,'exports':exports,'clipped_text':clipped,'overlapping_tick_labels':overlap,'unchecked_oblique_tick_labels':oblique,'missing_glyphs':missing,'source_to_artist_audit':{'status':'pass','all_selected_rows_once':True,'raw_numeric_values_exact':True,'exact_time_mean_anchors':True,'selected_compartment':compartment,'selected_rows':len(selected),'excluded_rows':'other separately exported compartment'},'readability':readability}
        core.write_json(out/'settings.json',settings);core.write_json(out/'qa.json',qa)
        core.write_json(out/'stats.json',{'method':'arithmetic mean and sample SEM','inference':False,'pairing':False,'source_row_count':len(selected),'groups':summary})
        core.write_json(out/'geometry-evidence.json',{'data_region_mm':[layout['width_mm']*.775,layout['height_mm']*.665],'shared_axes_fraction':[.195,.19,.775,.665],'raw_lane_span_hours':1.7,'raw_group_gap_hours':2.4,'summary_x':'literal source hours','independent_unit_limit':'request describes terminal cross-sectional observations; no mouse ID supplied'})
        plt.close(fig)

