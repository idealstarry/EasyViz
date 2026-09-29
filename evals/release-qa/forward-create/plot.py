#!/usr/bin/env python3
"""Recreate the manuscript panel and traceable paired-change tables.

Usage: python plot.py [--settings settings.json] [--out output]
Requires Python 3, pandas, numpy, matplotlib, Pillow.
"""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parent / '.mpl'))
import argparse
import hashlib
import json
import platform
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.text import Text
from PIL import Image


def paired_data(source, s, out):
    data = pd.read_csv(source)
    keys = ['donor_id', 'arm', 'analyte']
    required = keys + ['week', 'log2_abundance']
    if list(data.columns) != ['donor_id','arm','week','analyte','log2_abundance']:
        raise ValueError('Unexpected source columns')
    if data[required].isna().any().any():
        raise ValueError('Source contains explicit nulls; inspect before plotting')
    if not np.isfinite(data.log2_abundance).all():
        raise ValueError('Source contains nonfinite abundances')
    if data.duplicated(keys + ['week']).any():
        raise ValueError('Duplicate donor-arm-analyte-week rows')
    if data.groupby('donor_id').arm.nunique().max() != 1:
        raise ValueError('A donor appears in more than one arm')
    if set(data.arm) != set(s['arm_order']) or set(data.analyte) != set(s['analyte_order']):
        raise ValueError('Settings must list all arms and proteins')
    if set(data.week) != {0, *s['weeks']}:
        raise ValueError('Unexpected weeks')
    base = data[data.week == 0][keys + ['log2_abundance']].rename(columns={'log2_abundance':'baseline_log2'})
    follow = data[data.week.isin(s['weeks'])].rename(columns={'log2_abundance':'followup_log2'})
    donors = data[['donor_id','arm']].drop_duplicates()
    expected = donors.merge(pd.DataFrame({'analyte':s['analyte_order']}), how='cross').merge(pd.DataFrame({'week':s['weeks']}), how='cross')
    audit = expected.merge(base, on=keys, how='left', validate='many_to_one').merge(follow, on=keys+['week'], how='left', validate='one_to_one')
    audit['pair_status'] = np.select([audit.baseline_log2.isna(), audit.followup_log2.isna()], ['missing_baseline','missing_followup'], default='matched')
    audit['change_log2'] = audit.followup_log2 - audit.baseline_log2
    audit.to_csv(out/'pairing_audit.csv', index=False)
    plot_data = audit[audit.pair_status.eq('matched')].copy()
    rng = np.random.default_rng(s['jitter_seed'])
    plot_data['vertical_jitter'] = rng.uniform(-s['jitter_halfwidth'], s['jitter_halfwidth'], len(plot_data))
    plot_data.to_csv(out/'plotting_data.csv', index=False)
    summary = plot_data.groupby(['week','analyte','arm'], sort=False).change_log2.agg(n='size', median='median', q1=lambda x:x.quantile(.25, interpolation='linear'), q3=lambda x:x.quantile(.75, interpolation='linear'), minimum='min', maximum='max').reset_index()
    summary.to_csv(out/'summary.csv', index=False)
    audit.loc[audit.pair_status.ne('matched')].to_csv(out/'missing_pairs.csv', index=False)
    return data, plot_data, summary, audit


def mm_bbox(b, fig):
    return [float(v) for v in [b.x0/fig.dpi*25.4,b.y0/fig.dpi*25.4,b.width/fig.dpi*25.4,b.height/fig.dpi*25.4]]


def draw(s, p, summary, out, style):
    W,H = s['width_mm'],s['height_mm']
    plt.rcParams.update({'font.family':s['font'], 'font.size':s['font_size_pt'], 'axes.labelsize':8, 'xtick.labelsize':8, 'ytick.labelsize':8, 'legend.fontsize':8, 'axes.linewidth':s['line_width_pt'], 'pdf.fonttype':42, 'ps.fonttype':42, 'svg.fonttype':'none', 'axes.unicode_minus':True})
    fig = plt.figure(figsize=(W/25.4,H/25.4), dpi=s['dpi'])
    axes=[]
    raw_count=0
    for week,bounds in zip(s['weeks'],s['axes_bounds_mm']):
        ax=fig.add_axes([bounds[0]/W,bounds[1]/H,bounds[2]/W,bounds[3]/H])
        axes.append(ax)
        ax.set_xlim(s['x_limits'])
        ax.set_xticks(s['x_ticks'])
        ax.set_ylim(5.6,-.6)
        ax.set_yticks(range(len(s['analyte_order'])))
        ax.set_yticklabels(s['analyte_order'] if week==s['weeks'][0] else ['']*len(s['analyte_order']))
        ax.tick_params(axis='y', length=0, pad=6)
        ax.tick_params(axis='x', width=.6, length=2.5, pad=3)
        ax.set_axisbelow(True)
        ax.xaxis.grid(True, color='#E9ECEF',linewidth=.45)
        ax.axvline(0,color='#858B91',linewidth=.8,zorder=1)
        for edge in ['left','top','right']:
            ax.spines[edge].set_visible(False)
        ax.spines['bottom'].set_color('#63686C')
        for row,protein in enumerate(s['analyte_order']):
            if row < len(s['analyte_order'])-1:
                ax.axhline(row+.5,color='#F0F0F0',linewidth=.45,zorder=0)
            for arm in s['arm_order']:
                pos=row+s['arm_offsets'][arm]
                vals=p[(p.week==week)&(p.analyte==protein)&(p.arm==arm)]
                sm=summary[(summary.week==week)&(summary.analyte==protein)&(summary.arm==arm)].iloc[0]
                color=s['colors'][arm]
                if style=='box':
                    bp=ax.boxplot([vals.change_log2], positions=[pos], orientation="horizontal", widths=.19, manage_ticks=False, whis=1.5, showfliers=False, patch_artist=True,
                        boxprops={'facecolor':color,'alpha':.18,'edgecolor':'none','linewidth':0},
                        whiskerprops={'color':color,'linewidth':.7},capprops={'color':color,'linewidth':.7},medianprops={'color':color,'linewidth':1.3})
                ax.scatter(vals.change_log2,pos+vals.vertical_jitter,s=s['raw_point_area_pt2'],alpha=s['raw_point_alpha'],color=color,edgecolors='none',linewidths=0,zorder=3)
                raw_count+=len(vals)
                if style=='median':
                    ax.plot([sm.q1,sm.q3],[pos,pos],color=color,linewidth=s['iqr_line_width_pt'],solid_capstyle='butt',zorder=4)
                    ax.scatter([sm['median']],[pos],s=s['median_area_pt2'],marker='D',facecolor=color,edgecolors='none',linewidths=0,zorder=5)
        ax.text(.5,1.023,f'Week {week}',ha='center',va='bottom',transform=ax.transAxes,fontsize=8)
    fig.text(.55,7.0/H,'Change from baseline (log2 abundance)',ha='center',va='center',fontsize=8)
    handles=[Line2D([],[],linestyle='none',marker='s',markersize=4.2,markerfacecolor=s['colors'][a],markeredgecolor='none',markeredgewidth=0,label=a) for a in s['arm_order']]
    legend=fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.55,122/H),frameon=False,ncol=2,handlelength=.8,handletextpad=.35,columnspacing=1.2,borderpad=0,labelspacing=.3)
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    fig_box=fig.bbox
    text_bboxes=[]
    clipped=[]
    all_text=[]
    for t in fig.findobj(match=Text):
        if t.get_visible() and t.get_text():
            b=t.get_window_extent(renderer)
            all_text.append({'text':t.get_text(),'font_pt':t.get_fontsize(),'font_family':t.get_fontfamily(),'bbox_mm':mm_bbox(b,fig)})
            if b.x0 < -.5 or b.y0 < -.5 or b.x1 > fig_box.x1+.5 or b.y1 > fig_box.y1+.5:
                clipped.append(t.get_text())
    overlaps=[]
    for ax in axes:
        ts=[t for t in ax.get_xticklabels() if t.get_visible() and t.get_text()]
        for i,a in enumerate(ts):
            for b in ts[i+1:]:
                if a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer)):
                    overlaps.append([a.get_text(),b.get_text()])
    lb=legend.get_window_extent(renderer)
    lb_mm=mm_bbox(lb,fig)
    area=sum(a.bbox.width*a.bbox.height for a in axes)
    report={'raw_points_drawn':raw_count,'clipped_text':clipped,'x_tick_collisions':overlaps,'text':all_text,
        'legend':{'bbox_mm':lb_mm,'reserved_region_mm':[22,116,154,8],'reserved_area_mm2':1232,'data_region_area_mm2':2*72*91,'envelope_to_data_area_ratio':lb.width*lb.height/area,'width_to_combined_data_span_ratio':lb_mm[2]/154,'height_to_data_height_ratio':lb_mm[3]/91,'font_pt':8,'categorical_key_side_pt':4.2,'outline':'none'},'plot_bounds_mm':s['axes_bounds_mm']}
    if clipped or overlaps:
        raise RuntimeError(f'Layout clipping or ticks: {clipped}; {overlaps}')
    stem='panel' if style=='median' else 'baseline_box_points'
    targets=s['formats'] if style=='median' else ['png','pdf']
    for fmt in targets:
        if fmt=='png':
            # Quantize the raster canvas to the nearest whole pixel while vectors retain exact mm.
            px=[round(W/25.4*s['dpi']),round(H/25.4*s['dpi'])]
            fig.set_size_inches(px[0]/s['dpi'],px[1]/s['dpi'])
        fig.savefig(out/f'{stem}.{fmt}',dpi=s['dpi'],facecolor='white',bbox_inches=None)
        fig.set_size_inches(W/25.4,H/25.4)
    report['png_pixels']=list(Image.open(out/f'{stem}.png').size)
    report['png_dpi']=list(Image.open(out/f'{stem}.png').info['dpi'])
    plt.close(fig)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings',type=Path,default=Path(__file__).with_name('settings.json'))
    parser.add_argument('--out',type=Path,default=Path(__file__).parent)
    args=parser.parse_args()
    s=json.loads(args.settings.read_text())
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    source=(args.settings.resolve().parent/s['source']).resolve()
    font=font_manager.findfont(s['font'],fallback_to_default=False)
    data,p,summary,audit=paired_data(source,s,out)
    s['actual_font_path']=font
    s['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    s['versions']={'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'matplotlib':matplotlib.__version__}
    s['source_rows']=len(data);s['paired_changes']=len(p)
    s['pair_status_counts']=audit.pair_status.value_counts().to_dict()
    s['unpaired_followup_source_rows']=int(len(data[data.week.ne(0)])-len(p))
    s['data_range']=[float(p.change_log2.min()),float(p.change_log2.max())]
    reports={style:draw(s,p,summary,out,style) for style in ['median','box']}
    (out/'figure-settings.json').write_text(json.dumps(s,indent=2)+'\n')
    (out/'layout-checks.json').write_text(json.dumps(reports,indent=2)+'\n')
    print(json.dumps({'source_rows':len(data),'paired_changes':len(p),'missing_pairs':int(audit.pair_status.ne('matched').sum()),'actual_font':font,'output':str(out)},indent=2))
if __name__=='__main__':
    main()
