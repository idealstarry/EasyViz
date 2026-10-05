#!/usr/bin/env python3
"""Independently probe the exact helper execution boundary in temporary copies."""
from __future__ import annotations

import builtins
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / 'skills/easyviz/scripts'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('helper-execution-after.json')
    initial_sources = {name: sha((SCRIPTS / name).read_bytes())
                       for name in ('render.py', 'figure_elements.py')}
    cases = []
    actual_exec = builtins.exec
    for filename in ('figure_elements.py', 'render.py'):
        with tempfile.TemporaryDirectory(prefix='easyviz-independent-captured-exec-') as tmp:
            temporary = Path(tmp)
            copied = temporary / 'scripts'
            shutil.copytree(SCRIPTS, copied)
            boundary = copied / 'figure_elements.py'
            target = copied / filename
            original = target.read_bytes()
            replacement = original + b'\n# Independent fixture replacement: never executed in this module.\n'
            touched = []

            def replace_after_exec(code, globals=None, locals=None, **kwargs):
                result = actual_exec(code, globals, locals, **kwargs)
                if isinstance(globals, dict) and globals.get('__file__') == str(boundary):
                    target.write_bytes(replacement)
                    touched.append(filename)
                return result

            loader = importlib.util.spec_from_file_location('independent_exact_execution_probe', copied / 'render.py')
            core = importlib.util.module_from_spec(loader)
            with patch.object(builtins, 'exec', replace_after_exec):
                loader.loader.exec_module(core)
            assert touched == [filename], 'Probe must replace source at the actual helper execution boundary.'
            assert target.read_bytes() == replacement
            assert core.RUNTIME_SOURCE_DIGESTS[filename] == sha(original), 'Captured digest must describe consumed bytes.'
            source = temporary / 'source.csv'
            source.write_bytes(b'x,y\n1,2\n2,3\n3,4\n')
            output = temporary / 'figure'
            adopted = {'chart': 'scatter', 'fields': {'x': 'x', 'y': 'y'},
                       'layout': {'width_mm': 88, 'height_mm': 66, 'font': 'DejaVu Sans', 'dpi': 120},
                       'formats': ['png', 'svg']}
            error = None
            try:
                core.render(source, adopted, output)
            except core.SpecError as exc:
                error = str(exc)
            qa = json.loads((output / 'qa.json').read_text())
            assert error and 'changed before rendering' in error
            assert not qa['valid_outputs'] and qa['status'] == 'failed'
            assert not (output / 'panel.png').exists()
            cases.append({'replaced_source': filename, 'hook_reached': True,
                          'consumed_sha256': sha(original), 'replacement_sha256': sha(replacement),
                          'recorded_loaded_sha256': core.RUNTIME_SOURCE_DIGESTS[filename],
                          'race_blocked_before_export': True, 'qa': qa, 'error': error})
    for name, original_hash in initial_sources.items():
        assert sha((SCRIPTS / name).read_bytes()) == original_hash, 'Runtime changed during probe; rerun after freeze.'
    result = {'scope': 'Actual executed-helper bytes and post-execution renderer/helper replacement',
              'source_hashes': initial_sources, 'temporary_copies_only': True,
              'probe_script_sha256': sha(Path(__file__).read_bytes()), 'cases': cases,
              'all_blocked_before_export': True}
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'source_hashes': initial_sources, 'cases': len(cases), 'all_blocked_before_export': True}, indent=2))
    print(f'Evidence: {destination}')


if __name__ == '__main__':
    main()
