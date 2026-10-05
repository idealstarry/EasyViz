"""Exercise an actual timestamp/size-valid stale renderer cache in a fresh copy."""
import hashlib, importlib.util, json, os, py_compile, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAMES = ('render.py', 'legend_layout.py', 'figure_profile.py', 'auto_layout.py', 'annotation_review.py', 'figure_elements.py', 'panel_readability.py')


def main():
    out = HERE / (sys.argv[1] if len(sys.argv) > 1 else 'self-bytecode-after')
    out.mkdir()
    runtime = out / 'runtime'
    runtime.mkdir()
    for name in NAMES:
        shutil.copy2(ROOT / 'skills/easyviz/scripts' / name, runtime / name)
    script = runtime / 'render.py'
    raw = script.read_bytes()
    replacement = raw.replace(b'options.get("point_area_pt2", 12)', b'options.get("point_area_pt2", 81)')
    assert raw != replacement and len(raw) == len(replacement)
    stat = script.stat()
    py_compile.compile(str(script), doraise=True)
    script.write_bytes(replacement)
    os.utime(script, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    record = {'captured_cached_source_hash': hashlib.sha256(raw).hexdigest(), 'replacement_file_hash': hashlib.sha256(replacement).hexdigest(), 'same_length': len(raw) == len(replacement), 'same_integer_mtime': int(script.stat().st_mtime) == int(stat.st_mtime)}
    loader = importlib.util.spec_from_file_location('reviewer_stale_self', script)
    module = importlib.util.module_from_spec(loader)
    try:
        loader.loader.exec_module(module)
    except RuntimeError as exc:
        record.update(import_refused=True, refusal=str(exc), export_api_loaded=hasattr(module, 'render'), export_files=list(str(p) for p in runtime.glob('panel.*')))
    else:
        record.update(import_refused=False, export_api_loaded=hasattr(module, 'render'))
    (out / 'evidence.json').write_text(json.dumps(record, indent=2) + '\n')
    assert record['import_refused'] and not record['export_api_loaded'] and not record['export_files']
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
