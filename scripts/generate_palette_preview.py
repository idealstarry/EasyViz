"""Render the literature palette card and a complete preset reference."""
from pathlib import Path
import json
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/easyviz-matplotlib")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'skills/easyviz/assets/palettes'
PALETTES = json.loads((FOLDER / 'palettes.json').read_text())
# Require the requested typeface instead of silently substituting another font.
font_manager.findfont('Arial', fallback_to_default=False)
plt.rcParams.update({'font.family':'Arial','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none'})


def card(entries, filename, title, subtitle):
    height = 28 + 21 * len(entries)
    fig = plt.figure(figsize=(210/25.4, height/25.4), facecolor='white')
    def text(x, y, label, **kwargs):
        fig.text(x/210, y/height, label, **kwargs)
    text(8, height-9, title, fontsize=13, weight='bold', color='#233641')
    text(8, height-15, subtitle, fontsize=8, color='#536771')
    for i, (name, entry) in enumerate(entries):
        y = height-35-i*21
        text(8, y+5, entry.get('display_name',name), fontsize=9, weight='bold', color='#233641')
        text(8, y, name, fontsize=7, color='#536771')
        source = entry.get('source_short',entry.get('type',''))
        text(8, y-4.5, source, fontsize=7, color='#536771')
        ax=fig.add_axes([76/210,(y-1)/height,126/210,8/height]);ax.set_axis_off()
        if entry['type']=='categorical':
            colors=entry['colors']
            for j,c in enumerate(colors):
                ax.add_patch(plt.Rectangle((j/len(colors)+.003,0),1/len(colors)-.006,1,facecolor=c))
                ax.text((j+.5)/len(colors),-.58,c.upper(),ha='center',va='center',fontsize=6.8,
                        color='#34434C',transform=ax.transAxes,clip_on=False)
        else:
            cmap=entry.get('colormap') or LinearSegmentedColormap.from_list(name,entry['colors'])
            ax.imshow(np.arange(512)[None,:],aspect='auto',cmap=cmap)
            labels=('low','center','high') if entry['type']=='diverging' else ('low','','high')
            for x,label in zip((0,.5,1),labels):
                ax.text(x,-.58,label,ha='center',va='center',fontsize=7,color='#536771',transform=ax.transAxes)
    text(8, 5, 'Categorical swatches preserve sampled colors; continuous ramps are labeled adaptations.',fontsize=7,color='#536771')
    fig.savefig(FOLDER / f'{filename}.png',dpi=180,facecolor='white')
    fig.savefig(FOLDER / f'{filename}.pdf',facecolor='white')
    plt.close(fig)


featured=[(k,v) for k,v in PALETTES.items() if v.get('collection')=='literature']
if featured:
    card(featured,'preview','EasyViz · Literature colors','Brighter coordinated choices, with figure-level provenance. Read palettes.md for source roles and limits.')
card(list(PALETTES.items()),'all-presets','EasyViz · All color presets','Literature-derived choices first; established and legacy options remain available for explicit use.')
print(f'Rendered {len(featured)} literature choices and {len(PALETTES)} total presets.')
