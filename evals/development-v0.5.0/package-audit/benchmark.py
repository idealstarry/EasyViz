"""Measure current hashing and isolated sync against the checked-in baseline."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from package_io import file_sha256
import sync_skill_cases


def measure(function, repeats):
    times, peaks, values = [], [], []
    for _ in range(repeats):
        tracemalloc.start()
        started = time.perf_counter()
        values.append(function())
        times.append(time.perf_counter() - started)
        peaks.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
    return {'median_seconds': statistics.median(times), 'max_python_peak_bytes': max(peaks),
            'trials': repeats, 'all_results_equal': len(set(values)) == 1}, values[0]


def tree_identity(folder, cases=None):
    files = {path.relative_to(folder).as_posix(): file_sha256(path)
             for path in folder.rglob('*') if path.is_file()
             and (cases is None or path.relative_to(folder).parts[0] != 'cases'
                  or path.relative_to(folder).parts[1] in cases)}
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return identity, len(files)


def main():
    baseline_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    baseline_source = subprocess.check_output(['git', 'show', f'{baseline_commit}:scripts/sync_skill_cases.py'], cwd=ROOT)
    baseline = {'__name__': 'isolated_sync_baseline', '__file__': str(ROOT / 'scripts/sync_skill_cases.py')}
    exec(compile(baseline_source, 'checked-in-sync-baseline', 'exec'), baseline)
    common_cases = set(baseline['GENERATED_CASES']) & set(sync_skill_cases.GENERATED_CASES)
    added_cases = sorted(set(sync_skill_cases.GENERATED_CASES) - set(baseline['GENERATED_CASES']))
    archive = ROOT / 'dist/easyviz-0.4.6.zip'
    whole, whole_digest = measure(lambda: hashlib.sha256(archive.read_bytes()).hexdigest(), 7)
    bounded, bounded_digest = measure(lambda: file_sha256(archive), 7)
    previous_assets = sync_skill_cases.ASSETS
    with tempfile.TemporaryDirectory(prefix='easyviz-package-benchmark-') as temporary:
        folder = Path(temporary).resolve()
        baseline['ASSETS'] = folder / 'baseline'
        sync_skill_cases.ASSETS = folder / 'current'
        def old_sync():
            with redirect_stdout(io.StringIO()):
                baseline['sync']()
            return tree_identity(baseline['ASSETS'], common_cases)[0]
        def new_sync():
            with redirect_stdout(io.StringIO()):
                sync_skill_cases.sync()
            return tree_identity(sync_skill_cases.ASSETS, common_cases)[0]
        try:
            # Refresh already populated assets, matching build()'s use.
            old_sync()
            new_sync()
            old_result, old_identity = measure(old_sync, 3)
            new_result, new_identity = measure(new_sync, 3)
            _, files = tree_identity(sync_skill_cases.ASSETS, common_cases)
        finally:
            sync_skill_cases.ASSETS = previous_assets
    report = {
        'python': platform.python_version(), 'platform': platform.platform(),
        'baseline_commit': baseline_commit,
        'archive_hashing': {'archive': archive.relative_to(ROOT).as_posix(),
                            'bytes': archive.stat().st_size, 'whole_read': whole, 'chunked_read': bounded,
                            'same_digest': whole_digest == bounded_digest},
        'isolated_asset_refresh': {'baseline': old_result, 'transactional': new_result,
                                  'same_common_file_bytes': old_identity == new_identity, 'common_generated_files': files,
                                  'common_cases': sorted(common_cases), 'added_current_cases': added_cases,
                                  'scope': 'Full baseline/current refresh timings; identical common-case bytes checked separately. Added current cases, if any, add work to current timing.'},
        'limits': ['Python traced allocation excludes OS/cache memory.',
                   'Local cached disk timing is descriptive, not a cross-machine speed guarantee.',
                   'Peak allocations include copied metadata and tree-identity comparison.',
                   'Temporary staging adds one candidate copy on disk; old leaves move by rename.']}
    out = Path(__file__).with_name('benchmark.json')
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
