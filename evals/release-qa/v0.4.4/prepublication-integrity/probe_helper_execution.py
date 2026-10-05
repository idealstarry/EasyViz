#!/usr/bin/env python3
"""Probe loaded-helper/source digest continuity in an isolated script copy.

This never modifies authoritative runtime sources or original trial records.
The first observed failure is preserved in helper-execution-before.json.
"""
from __future__ import annotations

import hashlib
import importlib.machinery
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
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('helper-execution-current.json')
    initial_sources = {name: sha((SCRIPTS / name).read_bytes())
                       for name in ('render.py', 'figure_elements.py')}
    with tempfile.TemporaryDirectory(prefix='easyviz-independent-import-race-') as tmp:
        temporary = Path(tmp)
        copied = temporary / 'scripts'
        shutil.copytree(SCRIPTS, copied)
        target = copied / 'figure_elements.py'
        original = target.read_bytes()
        replacement = original.replace(b'Registered artists and shared guides only.',
                                       b'NEWLY_REPLACED_GUIDES_SOURCE_UNEXECUTED.')
        assert replacement != original, 'The copied fixture must change the manifest scope string.'
        actual_loader = importlib.machinery.SourceFileLoader.exec_module
        touched = []

        def replace_after_loaded(self, module):
            result = actual_loader(self, module)
            if Path(self.path).resolve() == target.resolve():
                target.write_bytes(replacement)
                touched.append(module.__name__)
            return result

        loader = importlib.util.spec_from_file_location('independent_helper_execution_probe', copied / 'render.py')
        core = importlib.util.module_from_spec(loader)
        with patch.object(importlib.machinery.SourceFileLoader, 'exec_module', replace_after_loaded):
            loader.loader.exec_module(core)
        source = temporary / 'source.csv'
        source.write_bytes(b'x,y\n1,2\n2,3\n3,4\n')
        output = temporary / 'figure'
        adopted = {'chart': 'scatter', 'fields': {'x': 'x', 'y': 'y'},
                   'layout': {'width_mm': 88, 'height_mm': 66, 'font': 'DejaVu Sans', 'dpi': 120},
                   'formats': ['png', 'svg']}
        error = None
        try:
            core.render(source, adopted, output)
        except Exception as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)}
        qa = json.loads((output / 'qa.json').read_text())
        settings_path, elements_path = output / 'settings.json', output / 'elements.json'
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        elements = json.loads(elements_path.read_text()) if elements_path.exists() else {}
        record = settings.get('source_bindings', {}).get('helper:figure_elements.py', {})
        result = {'source_hashes': initial_sources, 'probe_script_sha256': sha(Path(__file__).read_bytes()),
                  'hook': 'SourceFileLoader.exec_module returns after loading figure_elements.py; replace its on-disk manifest scope before render.py records helper digests',
                  'temporary_copies_only': True, 'touched_modules': touched,
                  'captured_loaded_helper_sha256': sha(original),
                  'replaced_unexecuted_helper_sha256': sha(replacement),
                  'qa': qa, 'error': error, 'recorded_helper_sha256': record.get('sha256'),
                  'actual_helper_sha256': sha(target.read_bytes()), 'manifest_scope': elements.get('scope'),
                  'race_blocked': not qa.get('valid_outputs') or not touched}
    for name, original_hash in initial_sources.items():
        assert sha((SCRIPTS / name).read_bytes()) == original_hash, 'Runtime changed during probe; rerun after freeze.'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('source_hashes', 'touched_modules', 'race_blocked', 'error')}, indent=2))
    print(f'Evidence: {destination}')


if __name__ == '__main__':
    main()
