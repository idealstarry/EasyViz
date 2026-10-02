"""Render palette reference cards and text-free README swatches."""
from pathlib import Path
import argparse
import json
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/easyviz-matplotlib")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'skills/easyviz/assets/palettes'
PALETTES = json.loads((FOLDER / 'palettes.json').read_text())
# Require the requested typeface instead of silently substituting another font.
font_manager.findfont('Arial', fallback_to_default=False)
plt.rcParams.update({'font.family':'Arial','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none'})


def card(entries, filename):
    height = 8 + 21 * len(entries)
    fig = plt.figure(figsize=(210/25.4, height/25.4), facecolor='white')
    def text(x, y, label, **kwargs):
        fig.text(x/210, y/height, label, **kwargs)
    for i, (name, entry) in enumerate(entries):
        y = height-12-i*21
        text(4, y+5, entry.get('display_name',name), fontsize=9, weight='bold', color='#233641')
        text(4, y, name, fontsize=7, color='#536771')
        source = entry.get('source_short',entry.get('type',''))
        text(4, y-4.5, source, fontsize=7, color='#536771')
        ax=fig.add_axes([72/210,(y-1)/height,134/210,8/height]);ax.set_axis_off()
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
    text(4, 5, 'Categorical swatches preserve sampled colors; continuous ramps are labeled adaptations.',fontsize=7,color='#536771')
    fig.savefig(FOLDER / f'{filename}.png',dpi=300,facecolor='white')
    fig.savefig(FOLDER / f'{filename}.pdf',facecolor='white')
    plt.close(fig)


def readme_swatches(entries):
    """Keep names, provenance and HEX labels in Markdown, outside the pixels."""
    output = ROOT / 'docs/assets/palettes'
    output.mkdir(parents=True, exist_ok=True)
    width, height = 640, 40
    for name, entry in entries:
        if entry['type'] == 'categorical':
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            colors = entry['colors']
            gap = 4
            available = width - gap * (len(colors) - 1)
            for index, color in enumerate(colors):
                left = round(index * available / len(colors)) + index * gap
                right = round((index + 1) * available / len(colors)) + index * gap
                draw.rectangle((left, 0, right - 1, height - 1), fill=color)
        else:
            cmap = LinearSegmentedColormap.from_list(name, entry['colors'], N=width)
            pixels = np.rint(cmap(np.linspace(0, 1, width))[:, :3] * 255).astype('uint8')
            image = Image.fromarray(np.repeat(pixels[None, :, :], height, axis=0))
        image.save(output / f'{name}.png', optimize=True)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--readme-only', action='store_true',
                    help='Refresh only text-free documentation assets; retain existing reference cards')
args = parser.parse_args()
featured=[(k,v) for k,v in PALETTES.items() if v.get('collection')=='literature']
readme_swatches(featured)
if not args.readme_only:
    if featured:
        card(featured,'palette-swatches')
    card(list(PALETTES.items()),'all-presets')
print(f'Rendered {len(featured)} text-free README swatches.' if args.readme_only else
      f'Rendered {len(featured)} literature choices and {len(PALETTES)} total presets, plus README swatches.')
