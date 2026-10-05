#!/usr/bin/env python3
"""Independent core-source/Decimal probes; writes only its own evidence file."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / 'skills/easyviz/scripts'
OUTPUT = Path(__file__).with_name('runtime-probes.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    tracked = ['skills/easyviz/scripts/render.py', 'skills/easyviz/scripts/figure_elements.py',
               'tests/test_renderer.py', 'tests/test_figure_elements.py', 'tests/test_figure_profile.py']
    before = {name: sha((ROOT / name).read_bytes()) for name in tracked}
    loader = importlib.util.spec_from_file_location('independent_runtime_probe', SCRIPTS / 'render.py')
    core = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(core)
    cases = []
    base = {'chart': 'scatter', 'fields': {'x': 'x', 'y': 'y'},
            'layout': {'width_mm': 88, 'height_mm': 66, 'font': 'DejaVu Sans', 'dpi': 120},
            'formats': ['png', 'svg']}
    composition = {'chart': 'composition', 'fields': {'sample': 'sample', 'category': 'category', 'value': 'amount'},
                   'options': {'normalization': 'sample_sum'}, 'layout': deepcopy(base['layout']), 'formats': ['png', 'svg']}
    with tempfile.TemporaryDirectory(prefix='easyviz-independent-runtime-') as temporary:
        root = Path(temporary)
        source = root / 'source.csv'

        def rejected(name, body, adopted=base, expected=None, **kwargs):
            source.write_bytes(body)
            output = root / name
            error = None
            try:
                core.render(source, deepcopy(adopted), output, **kwargs)
            except core.SpecError as exc:
                error = str(exc)
            assert error is not None, f'{name} was not explicitly refused.'
            if expected:
                assert expected in error, error
            qa = json.loads((output / 'qa.json').read_text())
            assert not qa['valid_outputs']
            cases.append({'case': name, 'source_sha256': sha(body), 'expected_refusal': True, 'error': error,
                          'qa_status': qa['status'], 'valid_outputs': qa['valid_outputs']})

        malformed = {
            'extra-column': b'x,y\n1,2,3\n', 'missing-column': b'x,y\n1\n',
            'duplicate-header': b'x,y,y\n1,2,3\n', 'whitespace-header': b'x, \n1,2\n',
            'empty-header': b'x,\n1,2\n', 'blank-record': b'x,y\n1,2\n\n2,3\n',
            'empty-record': b'x,y\n,\n', 'unterminated-quote': b'x,y\n1,"2\n',
            'non-utf8': b'x,y\n1,\xff\n', 'missing-header-or-data': b'x,y\n',
        }
        for name, body in malformed.items():
            rejected(name, body)

        raw = b'\xef\xbb\xbfid,x,y,note\r\n0001,1.00,2e0,"a,b"\r\n0002,2,3,"two\r\nlines"\r\n0003,3,4,"say ""yes"""\r\n'
        source.write_bytes(raw)
        adopted = deepcopy(base); adopted['fields']['unit'] = 'id'
        data = core.prepare(source, adopted)
        assert data.id.tolist() == ['0001', '0002', '0003']
        assert data.note.tolist() == ['a,b', 'two\r\nlines', 'say "yes"']
        output = root / 'literal-bytes'
        qa = core.render(source, adopted, output)
        assert qa['valid_outputs'] and (output / 'source-data.csv').read_bytes() == raw
        settings = json.loads((output / 'settings.json').read_text())
        elements = json.loads((output / 'elements.json').read_text())
        assert settings['input_sha256'] == elements['version']['input_sha256'] == sha(raw)
        cases.append({'case': 'bom-crlf-multiline-literal-IDs', 'valid_outputs': True, 'exact_source_snapshot': True,
                      'ids': data.id.tolist(), 'source_sha256': sha(raw)})

        raw = b'x,y\n1,2\n2,3\n3,4\n'
        source.write_bytes(raw)
        actual_reader = core.read_source_csv
        def changed_after_csv(path):
            parsed = actual_reader(path)
            source.write_bytes(b'x,y\n1,200\n2,300\n3,400\n')
            return parsed
        with patch.object(core, 'read_source_csv', side_effect=changed_after_csv):
            rejected('source-after-parse', raw, expected='changed before rendering')
        assert not (root / 'source-after-parse/panel.png').exists()

        actual_export = core.export
        def changed_during_export(fig, destination, adopted, layout):
            source.write_bytes(b'x,y\n1,200\n2,300\n3,400\n')
            return actual_export(fig, destination, adopted, layout)
        with patch.object(core, 'export', side_effect=changed_during_export):
            rejected('source-during-export', raw, expected='changed during export')
        output = root / 'source-during-export'
        assert (output / 'source-data.csv').read_bytes() == raw
        settings = json.loads((output / 'settings.json').read_text())
        elements = json.loads((output / 'elements.json').read_text())
        assert settings['input_sha256'] == elements['version']['input_sha256'] == sha(raw)
        cases[-1].update(retained_consumed_bytes=True, manifest_keeps_consumed_hash=True)

        spec_path = root / 'adopted.json'
        spec_raw = json.dumps(base).encode()
        spec_path.write_bytes(spec_raw); source.write_bytes(raw)
        actual_parse = core.parse_spec_bytes
        parse_calls = []
        def replaced_between_parse_and_render(body):
            parsed = actual_parse(body)
            if not parse_calls:
                spec_path.write_bytes(spec_raw + b'\n')
            parse_calls.append(sha(body))
            return parsed
        output = root / 'cli-spec-byte-race'
        with patch.object(core, 'parse_spec_bytes', side_effect=replaced_between_parse_and_render):
            try:
                core.render_spec_file(source, spec_path, output)
            except core.SpecError as exc:
                error = str(exc)
            else:
                raise AssertionError('CLI captured-spec race passed.')
        qa = json.loads((output / 'qa.json').read_text())
        assert 'changed before rendering' in error and not qa['valid_outputs']
        assert not (output / 'panel.png').exists()
        assert parse_calls and all(value == sha(spec_raw) for value in parse_calls)
        cases.append({'case': 'cli-spec-byte-race', 'error': error, 'captured_spec_sha256': sha(spec_raw),
                      'all_parsed_bytes_are_original': True, 'valid_outputs': False})

        profile_path = root / 'profile.json'
        profile_raw = json.dumps({'version': 1, 'layout': {'font': 'DejaVu Sans', 'font_size_pt': 8,
                                 'line_width_pt': .6, 'dpi': 120},
                                 'panels': {'A': {'width_mm': 88, 'height_mm': 66}}}).encode()
        profile_path.write_bytes(profile_raw)
        actual_resolve = core.resolve_spec
        def profile_replaced_after_resolve(*args, **kwargs):
            resolved, record = actual_resolve(*args, **kwargs)
            profile_path.write_bytes(profile_raw + b'\n')
            return resolved, record
        with patch.object(core, 'resolve_spec', side_effect=profile_replaced_after_resolve):
            rejected('profile-after-resolve', raw, expected='changed before rendering', profile=profile_path, panel='A')

        for name, first, second, exact_total, expected in (
            ('binary64-sum-overflow', '1e308', '1e308', '2e308', [.5, .5]),
            ('unsigned-integer-sum-overflow', '18000000000000000000', '1000000000000000000', '19000000000000000000', [18/19, 1/19]),
        ):
            body = f'sample,category,amount\nA,first,{first}\nA,second,{second}\n'.encode()
            source.write_bytes(body)
            data = core.prepare(source, composition)
            fractions = data['_easyviz_plotted_value'].tolist()
            assert all(math.isclose(a,b,rel_tol=1e-14,abs_tol=0) for a,b in zip(fractions,expected))
            assert all(Decimal(value)==Decimal(exact_total) for value in data['_easyviz_denominator_text'])
            assert math.isclose(math.fsum(fractions),1,rel_tol=1e-14)
            layout, typography, rc = core.setup(composition)
            with core.plt.rc_context(rc):
                fig, _ = core.draw(data,composition,layout,typography,core.statistics(data,composition))
                heights = [bar.get_height() for bar in fig.axes[0].patches]
                core.plt.close(fig)
            assert all(math.isclose(a,b,rel_tol=1e-14,abs_tol=0) for a,b in zip(heights,expected))
            cases.append({'case': name, 'fractions': fractions, 'actual_bar_heights': heights,
                          'exact_total': data['_easyviz_denominator_text'].tolist(), 'passed': True})
            adopted = deepcopy(composition); adopted['fields']['denominator']='denominator'
            adopted['options']['normalization']='denominator'
            bad = f'sample,category,amount,denominator\nA,first,{first},{first}\nA,second,{second},{first}\n'.encode()
            rejected(name+'-supplied-denominator-excess',bad,adopted,expected='sum exceeds')

        for name, token in (('positive-numeric-underflow','1e-400'),('negative-numeric-underflow','-1e-400')):
            rejected(name,f'x,y\n1,{token}\n2,3\n'.encode(),expected='representability')
        rejected('positive-normalized-fraction-underflow',b'sample,category,amount\nA,tiny,1e-308\nA,large,1e308\n',composition,expected='representability')
        for token in ('0e-1000000000','0e1000000000'):
            source.write_bytes(f'sample,category,amount\nA,zero,{token}\nA,one,1\n'.encode())
            data=core.prepare(source,composition)
            assert data['_easyviz_plotted_value'].tolist()==[0,1]
            assert all(Decimal(value)==1 for value in data['_easyviz_denominator_text'])
            cases.append({'case':'extreme-zero-exponent','token':token,'fractions':[0,1],'passed':True})

    tests=[]
    for filename in ('test_renderer.py','test_figure_elements.py','test_figure_profile.py'):
        command=[sys.executable,'-m','unittest','discover','-s','tests','-p',filename]
        completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        assert completed.returncode==0,completed.stdout+completed.stderr
        tests.append({'pattern':filename,'returncode':completed.returncode,'output':completed.stdout+completed.stderr})
    for name,digest in before.items():
        assert sha((ROOT/name).read_bytes())==digest,'Source changed during probe; rerun after freeze.'
    result={'scope':'Strict CSV/source/spec/profile continuity and exact composition normalization; no aesthetic or scientific-design approval',
            'source_hashes':before,'probe_script_sha256':sha(Path(__file__).read_bytes()),
            'independent_cases':len(cases),'cases':cases,'focused_tests':tests,'all_passed':True}
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(cases)} independent runtime cases and focused tests passed. Evidence: {OUTPUT}')


if __name__=='__main__':
    main()
