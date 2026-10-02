#!/usr/bin/env python3
"""Inspect the frozen practical trial independently of its renderer and QA."""
import argparse
import csv
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIBRARY = ROOT / 'evals/reproduce-inputs/new-families-audit/verify.py'
loader = importlib.util.spec_from_file_location('independent_export_audit', LIBRARY)
verifier = importlib.util.module_from_spec(loader)
loader.loader.exec_module(verifier)


def rows(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=HERE, help='Trial record directory containing prepared.csv and agent-result/')
    args = parser.parse_args()
    record = args.run.resolve()
    source = rows(ROOT / 'evals/reproduce-inputs/urschel-paired/source-data.csv')
    supplied = rows(record / 'prepared.csv')
    output = record / 'agent-result/output'
    plotted = rows(output / 'plotting-data.csv')
    rename = {'participant_id': '受试者', 'timepoint': '时间点', 'igg_bau_ml': 'IgG_BAU_ml'}
    mapped = [{rename.get(key, key): value for key, value in row.items()} for row in source]
    verifier.check('Prepared source: header renaming alone, all public values and trace preserved', supplied == mapped, rows=len(supplied), supplied_sha256=digest(record / 'prepared.csv'))
    preserved = len(plotted) == len(supplied) and all(
        float(actual['IgG_BAU_ml']) == float(expected['IgG_BAU_ml'])
        and all(actual[key] == value for key, value in expected.items() if key != 'IgG_BAU_ml')
        for actual, expected in zip(plotted, supplied)
    )
    verifier.check('Exported plotting data: every parsed numeric value, ID, category and source cell preserved', preserved, observations=len(plotted))
    normalized = [{'source_cell': expected['source_cell'], 'source_numeric_text': expected['IgG_BAU_ml'], 'output_numeric_text': actual['IgG_BAU_ml']} for actual, expected in zip(plotted, supplied) if Decimal(actual['IgG_BAU_ml']) != Decimal(expected['IgG_BAU_ml'])]
    raw_column = '_easyviz_source_value_text'
    if any(raw_column in row for row in plotted):
        verifier.check('Exported raw source value text: exact numeric XML lexemes retained', len(plotted) == len(supplied) and all(actual.get(raw_column) == expected['IgG_BAU_ml'] for actual, expected in zip(plotted, supplied)), preserved_observations=len(plotted), raw_column=raw_column)
    units = {}
    for row in supplied:
        units.setdefault(row['受试者'], []).append(row['时间点'])
    verifier.check('Source design: 127 complete distinct Before/After pairs', len(units) == 127 and all(sorted(values) == ['After', 'Before'] for values in units.values()), independent_people=127, repeated_measurements=254)
    verifier.audit_ecdf(output, record / 'prepared.csv', record / 'agent-result/ecdf-spec.json')
    svg = ET.parse(output / 'panel.svg').getroot()
    ns = {'s': 'http://www.w3.org/2000/svg'}
    power_ticks = []
    for index in range(1, 6):
        spans = svg.findall(f".//s:g[@id='xtick_{index}']//s:tspan", ns)
        power_ticks.append([span.text for span in spans])
    verifier.check('Actual SVG: five editable power-of-ten ticks', power_ticks == [['1', '0', str(index)] for index in range(1, 6)], labels=power_ticks)
    if any(raw_column in row for row in plotted):
        legend = svg.find(".//s:g[@id='legend_1']", ns)
        widths = []
        for path in legend.findall('.//s:path', ns):
            style = path.get('style', '')
            if '#5278a8' in style or '#c2764e' in style:
                points = verifier.path_points(path)
                widths.append((max(x for x, y in points) - min(x for x, y in points)) * 25.4 / 72)
        verifier.check('Updated actual SVG: two 6 mm curve legend line keys', len(widths) == 2 and all(abs(width - 6) < .00001 for width in widths), centerline_widths_mm=widths, measured_from='actual SVG line path extrema, not settings metadata')
    from pymupdf import open as open_pdf
    with open_pdf(output / 'panel.pdf') as pdf:
        spans = [span for block in pdf[0].get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for span in line['spans'] if span['text'].strip()]
        fonts = sorted({span['font'] for span in spans})
    verifier.check('Actual PDF: Arial used for base text and mathematical exponents', bool(spans) and all('Arial' in font for font in fonts), fonts=fonts)
    stats = json.loads((output / 'stats.json').read_text())
    verifier.check('Recorded scientific scope: no invented tests or uncertainty', all(stats.get(key) is False for key in ('tests_performed', 'smoothing_applied', 'distributions_fitted', 'confidence_intervals_computed', 'experimental_independence_inferred')), statistics_record=stats)
    report = {'status': 'pass' if all(check['status'] == 'pass' for check in verifier.CHECKS) else 'fail', 'scope': 'One completed practical WorkBuddy ECDF task; source values, real exported paths, canvas, editable ticks and font inspected. No baseline, quality score or generic model conclusion.', 'auditor_sha256': digest(Path(__file__)), 'shared_export_auditor_sha256': digest(LIBRARY), 'input_sha256': digest(record / 'prepared.csv'), 'output_sha256': {path.name: digest(path) for path in output.glob('panel.*')}, 'numeric_serialization_note': {'normalized_source_lexemes': len(normalized), 'parsed_float_values_all_equal': preserved, 'meaning': 'Original prepared.csv retains exact XML text; a plotting numeric column may normalize float lexemes without changing parsed values. A supplied raw source text column is checked separately.', 'examples': normalized[:3]}, 'checks': verifier.CHECKS}
    (record / 'independent-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(report['status'], len(verifier.CHECKS), 'checks')
    for check in verifier.CHECKS:
        if check['status'] != 'pass':
            print(json.dumps(check, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
