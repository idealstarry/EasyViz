#!/usr/bin/env python3
"""Reproduce the supplied aligned panel using target data only.

Custom data/artist code; physical font and full-canvas export behavior adapted
from the inspected EasyViz render.py snapshot in skill-snapshot/scripts-render.py.
Run with the supplied Python runtime, or any Python with matplotlib, numpy,
pandas, pillow, pypdf and fonttools installed.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import warnings
import xml.etree.ElementTree as ET

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/easyviz-forward-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors, font_manager
from matplotlib.patches import Rectangle
from matplotlib.colorbar import ColorbarBase
from matplotlib.text import Text
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader
from fontTools.ttLib import TTFont


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def bbox_mm(fig, box):
    scale = np.array([120 / fig.bbox.width, 90 / fig.bbox.height,
                      120 / fig.bbox.width, 90 / fig.bbox.height])
    return (np.array([box.x0, box.y0, box.x1, box.y1]) * scale).tolist()


def envelope(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def axes_mm(fig, rect, width, height):
    x, y, w, h = rect
    return fig.add_axes([x / width, y / height, w / width, h / height])


def prepare(input_dir, spec, out):
    # Main plotting path uses pandas; audit below rereads source with csv module.
    values = pd.read_csv(input_dir / 'target-values.csv')
    samples = pd.read_csv(input_dir / 'target-samples.csv')
    required = ['analyte', 'specimen', 'z_score', 'measurement_state']
    assert values.columns.tolist() == required
    assert not values.duplicated(['analyte', 'specimen']).any()
    assert not samples['specimen'].duplicated().any()
    assert not samples['display_order'].duplicated().any()
    samples = samples.sort_values('display_order')
    rows = spec['data_mapping']['row_order']
    cols = samples['specimen'].tolist()
    assert set(values['analyte']) == set(rows)
    assert set(values['specimen']) == set(cols)
    assert set(values['measurement_state']) == {'measured', 'unmeasured'}
    measured = values['measurement_state'].eq('measured')
    assert values.loc[measured, 'z_score'].notna().all()
    assert np.isfinite(values.loc[measured, 'z_score']).all()
    assert values.loc[~measured, 'z_score'].isna().all()
    assert (values.loc[measured, 'z_score'].abs() <= 2).all()
    expected = pd.MultiIndex.from_product([rows, cols], names=['analyte', 'specimen'])
    long = values.set_index(['analyte', 'specimen']).reindex(expected).reset_index()
    assert len(long) == 72 and long['measurement_state'].notna().all()
    assert long['measurement_state'].eq('unmeasured').sum() == 3
    assert (long['measurement_state'].eq('measured') & long['z_score'].eq(0)).sum() == 1
    matrix = long.pivot(index='analyte', columns='specimen', values='z_score').loc[rows, cols]
    states = long.pivot(index='analyte', columns='specimen', values='measurement_state').loc[rows, cols]
    summary = (long[long['measurement_state'].eq('measured')]
               .groupby('analyte')['z_score'].agg(['mean', 'count']).reindex(rows)
               .rename(columns={'mean': 'mean_z_score', 'count': 'measured_count'}).reset_index())
    long[required].to_csv(out / 'plotting_data.csv', index=False, float_format='%.3f')
    summary.to_csv(out / 'feature-means.csv', index=False, float_format='%.12g')
    samples.to_csv(out / 'specimen-metadata.csv', index=False)
    return rows, cols, samples, long, matrix, states, summary


def export_full_canvas(fig, out, width_mm, height_mm, dpi):
    # Adapted EasyViz export primitive: explicit full canvas, rounded raster grid,
    # editable SVG text and embedded TrueType PDF font; no automatic cropping.
    sizes = {}
    for extension in ['svg', 'pdf', 'png']:
        path = out / f'panel.{extension}'
        if extension == 'png':
            pixels = [round(width_mm / 25.4 * dpi), round(height_mm / 25.4 * dpi)]
            old_size = fig.get_size_inches().copy()
            fig.set_size_inches(pixels[0] / dpi, pixels[1] / dpi)
            fig.canvas.draw()
            Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert('RGB').save(path, dpi=(dpi, dpi))
            fig.set_size_inches(old_size)
            with Image.open(path) as image:
                assert list(image.size) == pixels
                sizes[extension] = {'pixels': list(image.size), 'dpi': image.info['dpi']}
        else:
            metadata = ({'Creator': 'EasyViz custom image-data reproduction', 'CreationDate': None, 'ModDate': None}
                        if extension == 'pdf' else {'Creator': 'EasyViz custom image-data reproduction', 'Date': None})
            fig.savefig(path, format=extension, dpi=dpi, bbox_inches=None, metadata=metadata)
            if extension == 'pdf':
                page = PdfReader(path).pages[0]
                mm = [float(page.mediabox.width) / 72 * 25.4, float(page.mediabox.height) / 72 * 25.4]
                embedded = []
                for f in page['/Resources']['/Font'].values():
                    font = f.get_object()
                    descendants = font.get('/DescendantFonts', [font])
                    for d in descendants:
                        d = d.get_object()
                        descriptor = d.get('/FontDescriptor')
                        if descriptor:
                            descriptor = descriptor.get_object()
                            embedded.append({'name': str(descriptor.get('/FontName')),
                                             'embedded': any(k in descriptor for k in ['/FontFile', '/FontFile2', '/FontFile3'])})
                assert embedded and all(f['embedded'] for f in embedded)
                sizes[extension] = {'width_mm': mm[0], 'height_mm': mm[1], 'fonts': embedded}
            else:
                root = ET.parse(path).getroot()
                mm = [float(root.attrib[k].removesuffix('pt')) / 72 * 25.4 for k in ['width', 'height']]
                texts = list(root.iter('{http://www.w3.org/2000/svg}text'))
                assert texts
                sizes[extension] = {'width_mm': mm[0], 'height_mm': mm[1],
                                    'editable_text_nodes': len(texts), 'text_preserved': True}
            assert np.allclose(mm, [width_mm, height_mm], atol=1e-5)
    return sizes


def source_audit(input_dir, rows, cols, samples, long, summary, cells, bars, strip, cmap, norm):
    with (input_dir / 'target-values.csv').open(newline='') as f:
        source = list(csv.DictReader(f))
    with (input_dir / 'target-samples.csv').open(newline='') as f:
        metadata = sorted(csv.DictReader(f), key=lambda r: int(r['display_order']))
    keyed = {(r['analyte'], r['specimen']): r for r in source}
    assert len(source) == len(keyed) == 72
    assert set(keyed) == {(r, c) for r in rows for c in cols}
    assert cols == [r['specimen'] for r in metadata]
    independent_means = {}
    independent_counts = {}
    for row in rows:
        scores = [float(r['z_score']) for r in source if r['analyte'] == row and r['measurement_state'] == 'measured']
        independent_means[row] = math.fsum(scores) / len(scores)
        independent_counts[row] = len(scores)
    for rec in long.to_dict('records'):
        raw = keyed[(rec['analyte'], rec['specimen'])]
        assert rec['measurement_state'] == raw['measurement_state']
        if raw['measurement_state'] == 'measured':
            assert rec['z_score'] == float(raw['z_score'])
        else:
            assert pd.isna(rec['z_score'])
    for record, bar in zip(summary.to_dict('records'), bars):
        name = record['analyte']
        assert abs(record['mean_z_score'] - independent_means[name]) < 1e-12
        assert record['measured_count'] == independent_counts[name]
        assert abs(bar.get_width() - independent_means[name]) < 1e-12
    missing_keys = []
    zero_keys = []
    for (i, j), cell in cells.items():
        raw = keyed[(rows[i], cols[j])]
        assert cell.get_xy() == (j, i) and cell.get_width() == cell.get_height() == 1
        if raw['measurement_state'] == 'unmeasured':
            assert np.allclose(cell.get_facecolor(), colors.to_rgba('#d5d9df'))
            missing_keys.append([rows[i], cols[j]])
        else:
            assert np.allclose(cell.get_facecolor(), cmap(norm(float(raw['z_score']))))
            if float(raw['z_score']) == 0:
                assert not np.allclose(cell.get_facecolor(), colors.to_rgba('#d5d9df'))
                zero_keys.append([rows[i], cols[j]])
    for j, cell in enumerate(strip):
        assert cell.get_xy() == (j, 0) and cell.get_width() == 1
        assert samples.iloc[j]['condition'] == metadata[j]['condition']
    return {'method': 'independent csv.DictReader + math.fsum source reread compared to saved table and artists',
            'input_coordinates': len(source), 'plotted_cells': len(cells), 'missing_coordinates': missing_keys,
            'measured_zero_coordinates': zero_keys, 'per_feature_means': independent_means,
            'measured_counts': independent_counts, 'value_state_cell_and_bar_checks': 'passed'}


def draw(root, input_dir, spec_path, out):
    spec = json.loads(spec_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    rows, cols, samples, long, matrix, states, summary = prepare(input_dir, spec, out)
    layout = spec['layout']
    width, height, dpi = layout['width_mm'], layout['height_mm'], layout['dpi']
    font_path = font_manager.findfont(layout['font'], fallback_to_default=False)
    actual_font = font_manager.FontProperties(fname=font_path).get_name()
    assert actual_font == 'Arial'
    rc = {'font.family': actual_font, 'font.size': 8, 'axes.labelsize': 8, 'xtick.labelsize': 8,
          'ytick.labelsize': 8, 'legend.fontsize': 8, 'axes.linewidth': .6,
          'xtick.major.width': .6, 'ytick.major.width': .6,
          'pdf.fonttype': 42, 'svg.fonttype': 'none', 'svg.hashsalt': 'easyviz-forward', 'savefig.bbox': None}
    with plt.rc_context(rc), warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        fig = plt.figure(figsize=(width / 25.4, height / 25.4), dpi=dpi, facecolor='white')
        base = axes_mm(fig, [0, 0, width, height], width, height)
        base.set(xlim=(0, width), ylim=(0, height)); base.set_axis_off()
        heat = axes_mm(fig, spec['axes_mm']['heatmap'], width, height)
        top = axes_mm(fig, spec['axes_mm']['condition_strip'], width, height)
        means = axes_mm(fig, spec['axes_mm']['means'], width, height)
        cbax = axes_mm(fig, spec['axes_mm']['colorbar'], width, height)
        cmap = matplotlib.colormaps[spec['colors']['continuous']].resampled(256)
        norm = colors.Normalize(-2, 2)
        cells = {}
        for i, row in enumerate(rows):
            for j, col in enumerate(cols):
                value = matrix.loc[row, col]
                color = spec['colors']['unmeasured'] if states.loc[row, col] == 'unmeasured' else cmap(norm(value))
                cell = Rectangle((j, i), 1, 1, facecolor=color, edgecolor='none', linewidth=0, zorder=2)
                cell.set_gid(f'cell-{row}-{col}')
                heat.add_patch(cell); cells[i, j] = cell
        heat.set(xlim=(0, 9), ylim=(8, 0))
        heat.set_xticks(np.arange(9) + .5, cols, rotation=90)
        heat.set_yticks(np.arange(8) + .5, rows)
        heat.tick_params(axis='both', length=0, pad=3)
        for spine in heat.spines.values(): spine.set_visible(False)
        heat.set_axisbelow(True)
        strip = []
        for j, condition in enumerate(samples['condition']):
            cell = Rectangle((j, 0), 1, 1, facecolor=spec['colors']['condition_colors'][condition], edgecolor='none', linewidth=0)
            cell.set_gid(f'condition-{cols[j]}'); top.add_patch(cell); strip.append(cell)
        top.set(xlim=(0, 9), ylim=(0, 1)); top.set_axis_off()
        means.set(xlim=(-1, 1), ylim=(8, 0))
        means.set_axisbelow(True)
        zero_line = means.axvline(0, color=spec['colors']['zero_line'], linewidth=.6, zorder=1)
        zero_line.set_gid('mean-zero-reference')
        bars = means.barh(np.arange(8) + .5, summary['mean_z_score'], height=.56,
                          color=spec['colors']['mean_bars'], edgecolor='none', linewidth=0, zorder=2)
        for row, bar in zip(rows, bars): bar.set_gid(f'mean-{row}')
        means.set_yticks([]); means.set_xticks([-1, 0, 1]); means.set_xlabel('Mean score', labelpad=3)
        means.tick_params(axis='x', length=2, pad=3)
        for name in ['left', 'top', 'right']: means.spines[name].set_visible(False)
        assert (summary['mean_z_score'].abs() < 1).all()
        colorbar = ColorbarBase(cbax, cmap=cmap, norm=norm, orientation='horizontal', ticks=[-2, 0, 2])
        colorbar.outline.set_visible(False)
        colorbar.set_label('Standardized score', labelpad=3, fontsize=8)
        cbax.tick_params(axis='x', length=2, pad=3)
        # Compact condition guide: key/text spacing measured with the actual font.
        fig.canvas.draw(); painter = fig.canvas.get_renderer()
        guide_artists = []
        guide_y = 85.3; cursor = 25.8
        for condition in spec['data_mapping']['conditions']:
            patch = Rectangle((cursor, guide_y - .85), 2.8, 1.8,
                              facecolor=spec['colors']['condition_colors'][condition], edgecolor='none', linewidth=0)
            patch.set_gid('guide-' + condition.replace(' ', '-')); base.add_patch(patch)
            text = base.text(cursor + 4.0, guide_y, condition, va='center', fontsize=8)
            text.set_gid('guide-label-' + condition.replace(' ', '-'))
            fig.canvas.draw(); painter = fig.canvas.get_renderer()
            text_width_mm = text.get_window_extent(painter).width / fig.bbox.width * width
            guide_artists.extend([patch, text]); cursor += 4.0 + text_width_mm + 3.0
        missing_key = Rectangle((75.5, 9.5), 2.8, 1.8, facecolor=spec['colors']['unmeasured'], edgecolor='none', linewidth=0)
        missing_key.set_gid('unmeasured-guide-key'); base.add_patch(missing_key)
        missing_text = base.text(79.5, 10.3, 'Unmeasured', va='center', fontsize=8)
        missing_text.set_gid('unmeasured-guide-label')
        fig.canvas.draw(); painter = fig.canvas.get_renderer()
        # Shared-axis alignment checked in display coordinates, rather than guessed from axes rectangles.
        assert np.allclose([heat.transData.transform((j, 0))[0] for j in range(10)],
                           [top.transData.transform((j, 0))[0] for j in range(10)], atol=1e-8)
        assert np.allclose([heat.transData.transform((0, i + .5))[1] for i in range(8)],
                           [means.transData.transform((0, i + .5))[1] for i in range(8)], atol=1e-8)
        source_checks = source_audit(input_dir, rows, cols, samples, long, summary, cells, bars, strip, cmap, norm)
        texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
        clipped = []
        for text in texts:
            assert text.get_fontsize() == 8
            box = text.get_window_extent(painter)
            if box.x0 < -.1 or box.y0 < -.1 or box.x1 > fig.bbox.width + .1 or box.y1 > fig.bbox.height + .1:
                clipped.append({'text': text.get_text(), 'bbox_mm': bbox_mm(fig, box)})
        assert not clipped, clipped
        cmap_chars = TTFont(font_path).getBestCmap()
        missing_glyphs = sorted(set(c for text in texts for c in text.get_text() if ord(c) not in cmap_chars))
        assert not missing_glyphs
        guide_boxes = [bbox_mm(fig, a.get_window_extent(painter)) for a in guide_artists]
        missing_boxes = [bbox_mm(fig, a.get_window_extent(painter)) for a in [missing_key, missing_text]]
        scale_boxes = [bbox_mm(fig, cbax.get_window_extent(painter))] + [bbox_mm(fig, t.get_window_extent(painter)) for t in cbax.findobj(Text) if t.get_visible() and t.get_text()]
        footprints = {'main_matrix': bbox_mm(fig, heat.get_window_extent(painter)),
                      'means_field': bbox_mm(fig, means.get_window_extent(painter)),
                      'condition_strip': bbox_mm(fig, top.get_window_extent(painter)),
                      'condition_guide_complete': envelope(guide_boxes),
                      'missing_guide_complete': envelope(missing_boxes),
                      'continuous_scale_complete': envelope(scale_boxes),
                      'condition_guide_reserved': [25.8, 82.5, 105, 88.0],
                      'continuous_scale_reserved': [24, .5, 63, 11.5],
                      'missing_guide_reserved': [74.5, 8.0, 111, 12.5]}
        area = spec['axes_mm']['heatmap'][2] * spec['axes_mm']['heatmap'][3]
        for name in ['condition_guide_complete', 'missing_guide_complete', 'continuous_scale_complete']:
            b = footprints[name]
            footprints[name + '_area_fraction_of_matrix'] = (b[2] - b[0]) * (b[3] - b[1]) / area
        exports = export_full_canvas(fig, out, width, height, dpi)
        warning_messages = sorted(set(str(w.message) for w in captured))
        assert not any('Glyph' in w or 'findfont' in w for w in warning_messages)
        settings = dict(spec)
        settings['actual_font'] = {'family': actual_font, 'path': font_path, 'sha256': sha256(font_path), 'substituted': False,
                                   'all_visible_text_size_pt': 8, 'svg_text':'editable, font referenced', 'pdf_font':'embedded TrueType'}
        settings['guide_measurements'] = footprints
        settings['source_hashes'] = {str(p.relative_to(root)): sha256(p) for p in sorted((root / 'input').rglob('*')) if p.is_file()}
        settings['code_sha256'] = sha256(__file__)
        settings['executed_settings_sha256'] = sha256(spec_path)
        settings['runtime'] = {'matplotlib': matplotlib.__version__, 'numpy': np.__version__, 'pandas': pd.__version__}
        write_json(out / 'figure-settings.json', settings)
        qa = {'numeric_and_export_status': 'passed', 'source_artist_audit': source_checks,
              'column_strip_alignment':'passed', 'row_mean_alignment':'passed', 'text_canvas_clipping': clipped,
              'all_visible_text_Arial_8pt':'passed', 'missing_glyphs': missing_glyphs,
              'exports': exports, 'layout_footprints_mm': footprints, 'warnings': warning_messages,
              'visual_review':'pending actual PNG inspection', 'scope':'this supplied 8x9 target dataset only'}
        write_json(out / 'checks.json', qa)
        plt.close(fig)
    print(json.dumps({'output':str(out), 'rows':len(rows),'columns':len(cols),'exports':exports}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=Path(__file__).resolve().parent / 'input/data')
    parser.add_argument('--settings', type=Path, default=Path(__file__).resolve().parent / 'adopted-spec.json')
    parser.add_argument('--out', type=Path, required=True, help='New output directory; existing attempts are preserved.')
    args = parser.parse_args()
    draw(Path(__file__).resolve().parent, args.input_dir, args.settings, args.out)
