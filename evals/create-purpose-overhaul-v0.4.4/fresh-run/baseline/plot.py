#!/Users/starry/Desktop/EasyViz/.venv/bin/python
"""Reproducible, descriptive plot of the two supplied source files.

Run from the workspace with:
  MPLCONFIGDIR=evals/create-purpose-overhaul-v0.4.4/fresh-run/baseline/mpl-cache \
    .venv/bin/python evals/create-purpose-overhaul-v0.4.4/fresh-run/baseline/plot.py
Each invocation requires a fresh attempt directory and never replaces a render.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parents[1] / 'source-intake'


def spread_points(values: list[float], x_pt_per_unit: float, diameter_pt: float,
                  square: bool = False):
    """Find deterministic collision-avoiding offsets in points, without pairing.

    Values keep their original source order in the returned offsets. Sort only
    for temporary geometric placement; this does not reorder populations/groups.
    """
    offsets = [0.0] * len(values)
    clusters: list[list[int]] = []
    for index in sorted(range(len(values)), key=lambda i: (values[i], i)):
        if not clusters or (values[index] - values[clusters[-1][-1]]) * x_pt_per_unit >= diameter_pt:
            clusters.append([index])
        else:
            clusters[-1].append(index)
    for cluster in clusters:
        placed: list[tuple[float, float]] = []
        for index in cluster:
            x = values[index] * x_pt_per_unit
            candidates = [0.0]
            for prior_x, prior_y in placed:
                dx = abs(x - prior_x)
                if dx < diameter_pt:
                    dy = diameter_pt if square else math.sqrt(diameter_pt ** 2 - dx ** 2)
                    candidates.extend([prior_y + dy, prior_y - dy])
            for y in sorted(candidates, key=lambda z: (abs(z), z)):
                if all((max(abs(x - xx), abs(y - yy)) if square
                        else math.hypot(x - xx, y - yy)) >= diameter_pt - 1e-10
                       for xx, yy in placed):
                    offsets[index] = y
                    placed.append((x, y))
                    break
            else:
                raise RuntimeError('Could not place a source observation')
        midpoint = (min(offsets[i] for i in cluster) + max(offsets[i] for i in cluster)) / 2.0
        for index in cluster:
            offsets[index] -= midpoint
    return offsets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default=None)
    args = parser.parse_args()
    if args.attempt is None:
        args.attempt = next(f'attempt-{i:02d}' for i in range(1, 100)
                            if not (ROOT / f'attempt-{i:02d}').exists())
    if not re.fullmatch(r'attempt-\d{2}', args.attempt):
        raise ValueError('Use a separate attempt-NN directory')
    out = ROOT / args.attempt
    out.mkdir(exist_ok=False)

    contract_path = INPUT / 'input-contract.json'
    observations_path = INPUT / 'observations.csv'
    contract = json.loads(contract_path.read_text())
    with observations_path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    populations = contract['population_order']
    conditions = contract['condition_order']
    assert len(rows) == contract['observation_count'] == 156
    assert set(r['population'] for r in rows) == set(populations)
    assert set(r['condition'] for r in rows) == set(conditions)
    assert len(set((r['source_sheet'], r['source_cell']) for r in rows)) == len(rows)
    assert all(r['source_sheet'] == contract['sheet'] for r in rows)
    assert all(math.isfinite(float(r['normalized_count'])) for r in rows)
    assert all(float(r['normalized_count']) >= 0 for r in rows)
    groups = {(p, c): [r for r in rows if (r['population'], r['condition']) == (p, c)]
              for p in populations for c in conditions}
    expected = {r['population']: r for r in contract['counts']}
    for (p, c), group in groups.items():
        assert len(group) == expected[p][c]

    arial_path = font_manager.findfont(
        font_manager.FontProperties(family='Arial'), fallback_to_default=False)
    mpl.rcParams.update({
        'font.family': 'Arial', 'font.size': 8,
        'axes.labelsize': 8, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
        'legend.fontsize': 8, 'axes.titlesize': 8,
        'axes.linewidth': 0.55, 'xtick.major.width': 0.5,
        'xtick.major.size': 2.5, 'ytick.major.size': 0,
        'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'savefig.transparent': False,
    })
    width_mm, height_mm = 120.0, 60.0
    fig = plt.figure(figsize=(width_mm / 25.4, height_mm / 25.4), dpi=300)
    # Matplotlib 3.11's initial canvas construction snaps the figure to pixels.
    # Restore the requested physical extent for exact SVG/PDF dimensions.
    fig.set_size_inches(width_mm / 25.4, height_mm / 25.4, forward=False)
    # Physical margins allow 8 pt population labels and an uncrowded axis label.
    ax = fig.add_axes([16 / width_mm, 10.8 / height_mm,
                       101 / width_mm, 42.4 / height_mm])
    ax.set_xlim(0, 4)
    ax.set_ylim(8.6, -0.6)
    ax.set_yticks(range(len(populations)), populations)
    ax.tick_params(axis='y', pad=4)
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_xlabel('Normalized cell number', labelpad=3)
    ax.set_axisbelow(True)
    ax.grid(axis='x', color='#dedede', linewidth=0.35, zorder=0)
    for side in ['top', 'right', 'left']:
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#303030')
    colors = {'-DT': '#26738E', '+DT': '#BD542D'}
    markers = {'-DT': 'o', '+DT': 's'}
    point_diameter_pt = 2.5
    collision_diameter_pt = 3.10
    x_pt_per_unit = (101 / 25.4 * 72) / 4
    y_pt_per_unit = (42.4 / 25.4 * 72) / 9.2
    summary_rows = []
    plotting_rows = []
    geometry = []
    for population_index, population in enumerate(populations):
        for condition_index, condition in enumerate(conditions):
            group = groups[(population, condition)]
            values = [float(r['normalized_count']) for r in group]
            mean = statistics.mean(values)
            sem = statistics.stdev(values) / math.sqrt(len(values))
            assert math.isclose(mean, float(np.mean(values)), abs_tol=1e-14)
            assert math.isclose(sem, float(np.std(values, ddof=1) / np.sqrt(len(values))),
                                abs_tol=1e-14)
            base_y = population_index + (-0.25 if condition_index == 0 else 0.25)
            offsets_pt = spread_points(values, x_pt_per_unit, collision_diameter_pt,
                                       square=(markers[condition] == 's'))
            ys = [base_y + offset / y_pt_per_unit for offset in offsets_pt]
            color = colors[condition]
            # Means and SEMs are summary strokes; no observation is connected.
            ax.errorbar(mean, base_y, xerr=sem, fmt='none', ecolor='#242424',
                        elinewidth=0.65, capsize=1.35, capthick=0.65, zorder=2)
            half_mean_bar = 1.85 / y_pt_per_unit
            ax.plot([mean, mean], [base_y - half_mean_bar, base_y + half_mean_bar],
                    color='#242424', linewidth=1.05, solid_capstyle='butt', zorder=2)
            ax.scatter(values, ys, s=point_diameter_pt ** 2, marker=markers[condition],
                       facecolors='white', edgecolors=color, linewidths=0.55, zorder=3)
            summary_rows.append({
                'population': population, 'condition': condition, 'n': len(values),
                'mean': mean, 'sample_sd': statistics.stdev(values), 'sem': sem,
                'min': min(values), 'max': max(values),
            })
            for row, y, offset in zip(group, ys, offsets_pt):
                plotting_rows.append({**row, 'population_order_index': population_index,
                                      'condition_order_index': condition_index,
                                      'plot_x': row['normalized_count'], 'plot_y': y,
                                      'group_center_y': base_y, 'visual_offset_pt': offset})
            geometry.append({'population': population, 'condition': condition,
                             'max_absolute_swarm_offset_pt': max(map(abs, offsets_pt)),
                             'min_plot_y': min(ys), 'max_plot_y': max(ys)})

    # Restore the exact original row sequence in traceable plotting data.
    row_lookup = {(r['source_sheet'], r['source_cell']): r for r in plotting_rows}
    plotting_rows = [row_lookup[(r['source_sheet'], r['source_cell'])] for r in rows]
    original_fields = list(rows[0])
    assert all({k: p[k] for k in original_fields} == r
               for p, r in zip(plotting_rows, rows))
    assert all(p['normalized_count'] == p['plot_x'] for p in plotting_rows)
    display_points = np.array([[float(p['plot_x']) * x_pt_per_unit,
                                float(p['plot_y']) * y_pt_per_unit]
                               for p in plotting_rows])
    min_point_separation_pt = min(
        float(np.linalg.norm(display_points[i] - display_points[j]))
        for i in range(len(display_points)) for j in range(i + 1, len(display_points)))
    # Check complete marker footprints, including square corners and mixed pairs.
    outside_halfwidth_pt = (point_diameter_pt + 0.55) / 2
    intersecting_observation_pairs = []
    for i in range(len(plotting_rows)):
        for j in range(i + 1, len(plotting_rows)):
            dx, dy = map(abs, display_points[i] - display_points[j])
            ci = plotting_rows[i]['condition']
            cj = plotting_rows[j]['condition']
            if ci == cj == '-DT':
                intersects = math.hypot(dx, dy) < 2 * outside_halfwidth_pt - 1e-8
            elif ci == cj == '+DT':
                intersects = max(dx, dy) < 2 * outside_halfwidth_pt - 1e-8
            else:
                distance_to_square = math.hypot(max(dx - outside_halfwidth_pt, 0),
                                                 max(dy - outside_halfwidth_pt, 0))
                intersects = distance_to_square < outside_halfwidth_pt - 1e-8
            if intersects:
                intersecting_observation_pairs.append([
                    plotting_rows[i]['source_cell'], plotting_rows[j]['source_cell']])
    assert not intersecting_observation_pairs
    assert all(0 < float(p['plot_x']) < 4 and -0.6 < float(p['plot_y']) < 8.6
               for p in plotting_rows)

    legend_handles = [Line2D([], [], marker=markers[c], markersize=point_diameter_pt,
                             markerfacecolor='white', markeredgecolor=colors[c],
                             markeredgewidth=0.55, linestyle='none',
                             label='−DT' if c == '-DT' else '+DT') for c in conditions]
    legend = fig.legend(handles=legend_handles, loc='upper left',
                        bbox_to_anchor=(16 / width_mm, 59 / height_mm),
                        frameon=False, ncol=2, borderaxespad=0,
                        handlelength=0.7, handletextpad=0.35, columnspacing=1.1)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    readable_text = [*ax.get_xticklabels(), *ax.get_yticklabels(),
                     ax.xaxis.label, *legend.get_texts()]
    bboxes = [t.get_window_extent(renderer) for t in readable_text]
    inside = all(bb.x0 >= 0 and bb.y0 >= 0 and bb.x1 <= fig.bbox.width
                 and bb.y1 <= fig.bbox.height for bb in bboxes)
    assert inside
    assert all(t.get_fontsize() == 8 for t in readable_text)
    label_overlap_pairs = []
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            if bboxes[i].overlaps(bboxes[j]):
                label_overlap_pairs.append([readable_text[i].get_text(),
                                            readable_text[j].get_text()])
    assert not label_overlap_pairs
    base = out / 'cell-number-comparison'
    fig.savefig(base.with_suffix('.png'), dpi=300)
    fig.savefig(base.with_suffix('.svg'))
    fig.savefig(base.with_suffix('.pdf'), metadata={'Title': '', 'Author': '',
                                                   'Subject': 'Supplied values; descriptive plot'})
    plt.close(fig)

    for filename, output_rows in [('plotting-data.csv', plotting_rows),
                                  ('group-statistics.csv', summary_rows)]:
        with (out / filename).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
            writer.writeheader()
            writer.writerows(output_rows)
    with Image.open(base.with_suffix('.png')) as img:
        png_size = img.size
        png_dpi = img.info.get('dpi')
        corner = img.convert('RGB').getpixel((0, 0))
    svg = ET.parse(base.with_suffix('.svg')).getroot()
    pdf_bytes = base.with_suffix('.pdf').read_bytes()
    pdf_box = re.search(rb'/MediaBox\s*\[([^]]+)\]', pdf_bytes)
    assert pdf_box
    pdf_box_values = [float(x) for x in pdf_box.group(1).split()]
    desired_pt = [width_mm / 25.4 * 72, height_mm / 25.4 * 72]
    assert all(math.isclose(x, y, abs_tol=1e-7)
               for x, y in zip(pdf_box_values[2:], desired_pt))
    validation = {
        'source_csv_sha256': hashlib.sha256(observations_path.read_bytes()).hexdigest(),
        'source_contract_sha256': hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        'input_observation_count': len(rows), 'plotted_observation_count': len(plotting_rows),
        'group_count': len(groups), 'all_supplied_group_counts_match': True,
        'source_sheet_and_cell_unique': True,
        'exact_source_strings_preserved_in_plotting_data': True,
        'source_row_order_preserved': True, 'population_order': populations,
        'condition_order': conditions, 'all_values_finite_and_nonnegative': True,
        'means_checked_statistics_against_numpy': True,
        'sems_checked_statistics_against_numpy_ddof_1': True,
        'normalization_recalculated': False, 'inferred_pairing': False,
        'tests_or_significance_added': False,
        'minimum_observation_center_separation_pt': min_point_separation_pt,
        'nominal_circle_diameter_including_stroke_pt': point_diameter_pt + 0.55,
        'intersecting_observation_marker_footprints': intersecting_observation_pairs,
        'all_observation_centers_within_axes': True,
        'all_readable_text_fontsize_pt': 8, 'font_family': 'Arial', 'arial_file': arial_path,
        'all_text_boxes_within_canvas': inside,
        'overlapping_readable_text_boxes': label_overlap_pairs,
        'nominal_canvas_mm': [width_mm, height_mm], 'png_pixels': png_size,
        'png_dpi_metadata': png_dpi, 'png_corner_rgb': corner,
        'svg_width': svg.attrib['width'], 'svg_height': svg.attrib['height'],
        'svg_viewBox': svg.attrib['viewBox'], 'pdf_mediabox_pt': pdf_box_values,
        'swarm_geometry': geometry,
        'statistics': summary_rows,
        'visual_review_status': 'Requires actual image inspection after this render',
    }
    (out / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    print(json.dumps({k: validation[k] for k in [
        'input_observation_count', 'plotted_observation_count', 'png_pixels',
        'png_dpi_metadata', 'svg_width', 'svg_height', 'pdf_mediabox_pt',
        'overlapping_readable_text_boxes', 'swarm_geometry']}, indent=2))


if __name__ == '__main__':
    main()
