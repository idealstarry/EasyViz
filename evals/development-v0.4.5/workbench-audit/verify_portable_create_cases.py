"""Actual copied and extracted Create redraws, isolated from checkout imports."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_package import CURATED_CREATE_RESOURCES, check_curated_create_cases, extract_package, validate_plugin


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = {'scope': 'Internal 0.4.5 fixture only. Fresh copied/extracted redraws use explicit DejaVu, complete shipped source inputs and real source-bound artist maps; no published package, installation, original exports, release or tag changes.',
                'runtime_sha256': {name: digest(ROOT / 'skills/easyviz/scripts' / name) for name in ('figure_handoff.py', 'figure_workbench.py', 'apply_figure_requests.py', 'render.py', 'observation_clipping.py')},
                'check_package_sha256': digest(ROOT / 'scripts/check_package.py')}
    with tempfile.TemporaryDirectory(prefix='easyviz-future-portable-create-') as temporary:
        scratch = Path(temporary)
        plugin = scratch / 'build/easyviz'
        shutil.copytree(ROOT / 'dist/easyviz', plugin)
        # Use current integrated production helpers, including endpoint checks,
        # loaded fresh by each isolated child process. Do not reuse old modules.
        for source in sorted((ROOT / 'skills/easyviz/scripts').glob('*.py')):
            shutil.copy2(source, plugin / 'skills/easyviz/scripts' / source.name)
        manifest_path = plugin / '.codex-plugin/plugin.json'
        manifest = json.loads(manifest_path.read_text()); manifest['version'] = '0.4.5'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        source_hashes = {}
        for case, resources in CURATED_CREATE_RESOURCES.items():
            # Preserve curated package README/design/preview resources so
            # public guide links are checked alongside the runtime closure.
            source_hashes[case] = {}
            for name in resources:
                src = ROOT / 'examples/create' / case / name
                dst = plugin / 'skills/easyviz/assets/cases' / case / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                source_hashes[case][name] = digest(src)
        assert validate_plugin(plugin)['version'] == '0.4.5'
        evidence['shipped_create_dependency_sha256'] = source_hashes
        unrelated = scratch / 'unrelated-working-directory'; unrelated.mkdir()
        env = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
        env.update(MPLCONFIGDIR=str(scratch / 'matplotlib'), MPLBACKEND='Agg')
        copied = scratch / 'copied-attempts'; copied.mkdir()
        evidence['copied_redraw'] = check_curated_create_cases(plugin / 'skills/easyviz', copied, env)
        archive = scratch / 'future-curated-fixture.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as out:
            for path in sorted(plugin.rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    out.write(path, path.relative_to(plugin.parent))
        extracted = scratch / 'extracted'
        evidence['archive_entries'] = extract_package(archive, extracted)
        package = extracted / 'easyviz'
        assert validate_plugin(package)['version'] == '0.4.5'
        attempts = scratch / 'extracted-attempts'; attempts.mkdir()
        evidence['extracted_redraw'] = check_curated_create_cases(package / 'skills/easyviz', attempts, env)
        # Archive contains only curated inputs/code here; no developer history,
        # source-current assertion stamped onto old canonical QA/handoff packets.
        for case, resources in CURATED_CREATE_RESOURCES.items():
            case_root = package / 'skills/easyviz/assets/cases' / case
            actual = {str(p.relative_to(case_root)) for p in case_root.rglob('*') if p.is_file()}
            assert set(resources) <= actual, actual
            assert not any('history' in part or part in ('qa.json', 'handoff.json', 'packet.json', 'review.json')
                           for name in actual for part in Path(name).parts), actual
            for name, expected in source_hashes[case].items():
                assert digest(ROOT / 'examples/create' / case / name) == expected, 'Original case input/code changed during test'
        evidence['original_case_inputs_and_code_unchanged'] = True
    (HERE / 'portable-create-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'scope': evidence['scope'], 'archive_entries': evidence['archive_entries'],
                      'copied': {name: record['figures'] for name, record in evidence['copied_redraw'].items()},
                      'extracted': {name: record['figures'] for name, record in evidence['extracted_redraw'].items()},
                      'originals_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
