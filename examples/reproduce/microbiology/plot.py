"""Render a documented Figure 1 adaptation from supplied, cleaned GII values."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
cfg = json.loads((ROOT / 'figure-settings.json').read_text())
with (ROOT / 'source-data.csv').open() as f:
    rows = list(csv.reader(f))
receivers = rows[0][1:]
senders = [r[0] for r in rows[1:]]
values = np.array([[float(x) for x in r[1:]] for r in rows[1:]])
assert values.shape == (76, 76) and np.isfinite(values).all()
assert len(set(senders)) == 76 and set(senders) == set(receivers)
with (ROOT / 'genome-status.csv').open() as f:
    genome = {r['strain']: int(r['genome']) for r in csv.DictReader(f)}
assert all(x in genome for x in senders) and set(genome.values()) <= {0, 1}
# Counts use all 76 receivers/senders, then select evenly spaced sorted ranks.
# This is a documented adaptation, not literal reuse of the Rmd's column slice.
inhibited = values > cfg['degree_threshold_min']
sender_degree = inhibited.sum(axis=1)
receiver_degree = inhibited.sum(axis=0)
row_order = sorted(range(76), key=lambda i: (-int(sender_degree[i]), senders[i]))
col_order = sorted(range(76), key=lambda i: (-int(receiver_degree[i]), receivers[i]))
n = cfg['selection_count']
assert 2 <= n <= 76
ranks = np.rint(np.linspace(0, 75, n)).astype(int)
ri = [row_order[i] for i in ranks]
ci = [col_order[i] for i in ranks]
subset = values[np.ix_(ri, ci)]
with (ROOT / 'selected-data.csv').open('w') as f:
    writer = csv.writer(f)
    writer.writerow(['sender', 'receiver', 'gii_min', 'sender_degree', 'receiver_degree'])
    writer.writerows([senders[r], receivers[c], values[r,c], int(sender_degree[r]), int(receiver_degree[c])]
                     for r in ri for c in ci)

font_file = font_manager.findfont(cfg['font_family'], fallback_to_default=True)
actual_font = font_manager.FontProperties(fname=font_file).get_name()
plt.rcParams.update({'font.family': actual_font, 'font.size': cfg['font_size_pt'],
                     'axes.labelsize': cfg['font_size_pt'], 'xtick.labelsize': cfg['font_size_pt'],
                     'ytick.labelsize': cfg['font_size_pt'], 'legend.fontsize': cfg['font_size_pt'],
                     'axes.linewidth': cfg['line_width_pt'], 'pdf.fonttype':42,'ps.fonttype':42})
w, h = cfg['width_mm'], cfg['height_mm']
fig = plt.figure(figsize=(w/25.4, h/25.4), dpi=cfg['dpi'])
def axes_mm(x, y, aw, ah):
    return fig.add_axes([x/w, y/h, aw/w, ah/h])
# Explicit physical layout: labels, strips, and colorbar stay within the canvas.
ax = axes_mm(32, 16, 78, 78)
im = ax.imshow(subset, cmap=cfg['cmap'], vmin=float(values.min()), vmax=float(values.max()), interpolation='nearest', aspect='equal')
ax.set_xticks(range(n), [receivers[i] for i in ci], rotation=90)
ax.set_yticks(range(n), [senders[i] for i in ri])
ax.tick_params(axis='both', length=0, pad=3)
# Labels are at the top as in the reference, with room for genome annotation.
ax.xaxis.tick_top()
ax.tick_params(axis='x', pad=10)
ax.tick_params(axis='y', pad=10)
for spine in ax.spines.values():
    spine.set_visible(False)
strip_cmap = ListedColormap(['white', '#404040'])
left = axes_mm(29.5, 16, 2, 78)
left.imshow(np.array([genome[senders[i]] for i in ri])[:,None], cmap=strip_cmap, vmin=0, vmax=1, aspect='auto', interpolation='nearest')
top = axes_mm(32, 94.5, 78, 2)
top.imshow(np.array([genome[receivers[i]] for i in ci])[None,:], cmap=strip_cmap, vmin=0, vmax=1, aspect='auto', interpolation='nearest')
for a in (left, top):
    a.set_xticks([]); a.set_yticks([])
    for spine in a.spines.values():
        spine.set_linewidth(0.4)
cax = axes_mm(113, 34, 3, 42)
cb = fig.colorbar(im, cax=cax)
cb.set_label('GII (min)', labelpad=4)
cb.ax.tick_params(length=2, width=0.6)
fig.text(71/w, 117/h, 'Receiver', ha='center', va='center')
fig.text(3/w, 55/h, 'Sender', rotation=90, ha='center', va='center')
fig.legend(handles=[Patch(facecolor='#404040', label='Genome analyzed')],
           loc='lower center', bbox_to_anchor=(71/w, 1/h), frameon=False, handlelength=1, borderaxespad=0)
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
# Visible text may touch neither edge of the final physical canvas.
from matplotlib.text import Text
clipped = []
for obj in fig.findobj(Text):
    if not obj.get_visible() or not obj.get_text():
        continue
    box = obj.get_window_extent(renderer)
    if box.x0 < 0 or box.y0 < 0 or box.x1 > fig.bbox.width or box.y1 > fig.bbox.height:
        clipped.append(obj.get_text())
assert not clipped, f'Text extends outside canvas: {clipped}'
for ext in cfg['formats']:
    fig.savefig(ROOT / f'panel.{ext}', dpi=cfg['dpi'], facecolor='white')
plt.close(fig)
page = PdfReader(ROOT/'panel.pdf').pages[0]
actual_mm = [float(page.mediabox.width)*25.4/72, float(page.mediabox.height)*25.4/72]
assert np.allclose(actual_mm, [w,h], atol=0.01)
with Image.open(ROOT/'panel.png') as img:
    pixels = list(img.size)
assert all(abs(a-b/25.4*cfg['dpi']) <= 1 for a,b in zip(pixels,[w,h]))
report = {'passed':True,'source_shape':list(values.shape),'source_cells':int(values.size),
          'selected_shape':list(subset.shape),'selected_source_ranks_1_based':(ranks+1).tolist(),
          'color_limits_full_matrix_min_max':[float(values.min()),float(values.max())],
          'pdf_mm':actual_mm,'png_pixels':pixels,'font_family_requested':cfg['font_family'],
          'font_family_used':actual_font,'font_file':font_file,'font_size_pt':cfg['font_size_pt'],
          'text_outside_canvas':clipped,'note':'Automated checks cover values and dimensions; visual inspection is additionally required.'}
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
