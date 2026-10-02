#!/usr/bin/env python3
"""Preserve intake evidence and make explicitly adopted analysis settings."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
INPUT = Path('/private/tmp/easyviz-forward-create/input')
SKILL = Path('/Users/starry/Desktop/EasyViz/skills/easyviz')

def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2) + '\n')

(ROOT / 'source').mkdir(exist_ok=True)
for name in ['observations.csv', 'study-notes.txt']:
    shutil.copyfile(INPUT / name, ROOT / 'source' / name)

design = {
    'unit': 'sample_id',
    'unit_definition': 'One independent specimen, explicitly established by study-notes.txt',
    'structure': 'independent',
    'confirmed': True,
}
save('intake-design.json', {
    'table': 'observations.csv',
    'question': 'How does fluorescence signal differ between Control and Treatment?',
    'fields': {'group': 'condition', 'value': 'signal'},
    'design': design,
    'missing_tokens': [''],
    'missing_policy': 'error',
})
save('analysis-plan.json', {
    'schema_version': 1,
    'question': 'Describe the primary fluorescence signal and exploratory viability by independent condition',
    'design': design,
    'missing_tokens': [''],
    'missing_policy': 'error',
    'comparisons': [
        {'name': 'primary_signal_summary', 'method': 'descriptive',
         'fields': {'group': 'condition', 'value': 'signal'}},
        {'name': 'exploratory_viability_summary', 'method': 'descriptive',
         'fields': {'group': 'condition', 'value': 'viability_pct'}},
    ],
})
save('figure-profile.json', {
    'version': 1,
    'layout': {'font': 'Arial', 'font_size_pt': 8, 'line_width_pt': 0.6, 'dpi': 300},
    'colors': {'Control': '#29ACF3', 'Treatment': '#E47751'},
    'panels': {'primary_signal': {'width_mm': 120, 'height_mm': 90}},
})
save('adopted-specification.json', {
    'track': 'create',
    'source_paths': [str(INPUT / 'observations.csv'), str(INPUT / 'study-notes.txt')],
    'evidence': 'study-notes.txt establishes independent specimens, units, primary endpoint and final size',
    'primary_question': 'How does fluorescence signal differ between independent conditions?',
    'chart': 'distribution',
    'fields': {'group': 'condition', 'value': 'signal', 'unit': 'sample_id'},
    'order': ['Control', 'Treatment'],
    'transformation': 'None; all source values and all 24 specimens retained',
    'layers': ['All 24 raw observations', 'Median and interquartile box', 'Whiskers to observations within 1.5 IQR'],
    'analysis_plan': 'analysis-plan.json; descriptive only; no inferential method selected',
    'analysis_rationale': 'The user asks for useful scientific views and an initial panel. Raw distributions answer the primary question; synthetic teaching data do not warrant a biological significance claim. Independent design is retained for possible explicitly requested inference.',
    'uncertainty': 'Box and whiskers describe observed spread, not confidence intervals',
    'text': 'English; Arial 8 pt; no in-image title, subtitle, panel letter or narrative',
    'canvas_mm': [120, 90],
    'formats': ['pdf', 'svg', 'png'],
    'dpi': 300,
    'palette': 'Somerville bright sky/coral, explicit stable category mapping in figure-profile.json',
    'outline_policy': {
        'raw_points': 'Borderless filled circles, linewidth 0',
        'box_summary_exception': 'Colored 0.6 pt box boundary to make Q1/Q3 readable against white; box is a statistical summary, not another raw-observation mark',
        'statistical_lines': '0.6 pt median, whiskers and caps; line encodings',
    },
    'legend': 'No categorical legend: conditions directly identified by the x axis',
    'review_role': 'Self review; no independent reviewer requested',
    'candidate_views': [
        {'priority': 1, 'view': 'Boxplot with all raw signal observations', 'fields': ['condition', 'signal', 'sample_id'], 'purpose': 'Compare central signal and within-group spread; selected first panel'},
        {'priority': 2, 'view': 'Signal ECDF', 'fields': ['condition', 'signal', 'sample_id'], 'purpose': 'Compare the full signal distribution and tails without kernel smoothing'},
        {'priority': 3, 'view': 'Signal versus viability scatter, colored by condition', 'fields': ['signal', 'viability_pct', 'condition', 'sample_id'], 'purpose': 'Explore whether signal covaries with viable fraction; no pooled fit or causal claim'},
    ],
    'rejected_candidate': 'Paired chart: notes explicitly define independent groups, and each sample ID appears once',
})
save('source-hashes.json', {
    name: {'original': str(INPUT / name), 'snapshot': str(ROOT / 'source' / name),
           'sha256': hashlib.sha256((INPUT / name).read_bytes()).hexdigest(),
           'byte_identical': (INPUT / name).read_bytes() == (ROOT / 'source' / name).read_bytes()}
    for name in ['observations.csv', 'study-notes.txt']
})
save('helper-hashes.json', {
    str(path.relative_to(SKILL)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (SKILL / 'scripts').glob('*.py')
})
print('Preserved 2 sources and adopted descriptive analysis, primary mapping and 120 x 90 mm profile.')
