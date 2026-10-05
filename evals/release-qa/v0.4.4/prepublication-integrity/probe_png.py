#!/usr/bin/env python3
"""Re-run independent PNG decoding/geometry probes and focused review tests.

These synthetic byte streams test legal geometry against Pillow's decoder.
They do not assess aesthetics or exhaust all PNG ancillary/color semantics.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'skills/easyviz/scripts/create_review.py'
TEST_SOURCE = ROOT / 'tests/test_create_review.py'
OUTPUT = Path(__file__).resolve().with_name('probes.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)


def encoded(width, height, depth, color, interlace, data, palette=None):
    result = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, depth, color, 0, 0, interlace))
    if palette is not None:
        result += chunk(b'PLTE', palette)
    return result + chunk(b'IDAT', zlib.compress(data)) + chunk(b'IEND', b'')


def main():
    raw_source = SOURCE.read_bytes()
    spec = importlib.util.spec_from_file_location('independent_png_integrity_probe', SOURCE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    function = next(node for node in ast.parse(raw_source) .body if isinstance(node, ast.FunctionDef) and node.name == 'png_measurement')
    function_source = ast.get_source_segment(raw_source.decode(), function).encode()
    adam7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
             (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))
    cases = []
    for color, depths in {0: [1, 2, 4, 8, 16], 2: [8, 16], 3: [1, 2, 4, 8], 4: [8, 16], 6: [8, 16]}.items():
        for depth in depths:
            for width, height in ((1, 1), (1, 7), (7, 1), (5, 9), (9, 5)):
                for interlace in (0, 1):
                    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
                    data = bytearray()
                    for x, y, dx, dy in (adam7 if interlace else ((0, 0, 1, 1),)):
                        xs = list(range(x, width, dx))
                        ys = list(range(y, height, dy))
                        if xs and ys:
                            row_bytes = (len(xs) * channels * depth + 7) // 8
                            for _ in ys:
                                data.extend(b'\0' * (row_bytes + 1))
                    raw = encoded(width, height, depth, color, interlace, data, b'\0\0\0' if color == 3 else None)
                    measurement = gate.png_measurement(raw)
                    with Image.open(io.BytesIO(raw)) as image:
                        image.load()
                        assert image.size == (width, height)
                    assert measurement['pixels'] == [width, height]
                    cases.append({'color_type': color, 'bit_depth': depth, 'width': width, 'height': height,
                                  'interlace': interlace, 'pillow_decoded': True, 'gate_dimensions_match': True,
                                  'png_sha256': sha(raw)})
    invalid_palette_index = encoded(1, 1, 8, 3, 0, b'\0\xff', b'\xff\0\0')
    # This is intentionally outside the narrower scanline-integrity guarantee.
    # PNG 3 requires decoders to recover an out-of-range palette index as black.
    # The helper checks palette structure, not unfiltered per-pixel index bounds.
    residual = gate.png_measurement(invalid_palette_index)
    with Image.open(io.BytesIO(invalid_palette_index)) as image:
        image.load()
        recovered_pixel = list(image.convert('RGB').getpixel((0, 0)))
    focused = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_create_review.py'],
                             cwd=ROOT, capture_output=True, text=True)
    assert focused.returncode == 0, focused.stdout + focused.stderr
    # Legacy custom recipes do not declare the core CSV snapshot. Their entire
    # review shape must remain unchanged, so old successful attestations are not
    # invalidated solely by adding an irrelevant null evidence field.
    legacy_dir = ROOT / 'examples/create/repair-outcomes/panels/hdr/output'
    legacy_settings = json.loads((legacy_dir / 'settings.json').read_text())
    assert 'source_snapshot' not in legacy_settings
    old_source = subprocess.check_output(['git', 'show', 'HEAD:skills/easyviz/scripts/create_review.py'], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='easyviz-independent-legacy-review-') as temporary:
        old_path = Path(temporary) / 'old_review.py'
        old_path.write_bytes(old_source)
        old_loader = importlib.util.spec_from_file_location('independent_legacy_review', old_path)
        old_gate = importlib.util.module_from_spec(old_loader)
        old_loader.loader.exec_module(old_gate)
        before, after = old_gate.snapshot(legacy_dir), gate.snapshot(legacy_dir)
        assert before == after, 'Legacy custom-output review changed unexpectedly.'
        assert 'captured_source' not in after['measured_checks']['source_provenance']['evidence']
    assert SOURCE.read_bytes() == raw_source, 'Source changed while probes ran; rerun after freeze.'
    result = {'scope': 'PNG scanline/payload/geometry integrity, not appearance or exhaustive PNG conformance',
              'source_sha256': sha(raw_source), 'png_measurement_function_sha256': sha(function_source),
              'test_source_sha256': sha(TEST_SOURCE.read_bytes()),
              'probe_script_sha256': sha(Path(__file__).read_bytes()),
              'independent_legal_cases': len(cases), 'all_actual_pillow_decode': True,
              'all_gate_dimensions_match': True, 'cases': cases,
              'focused_tests': {'command': 'python -m unittest discover -s tests -p test_create_review.py',
                                'returncode': focused.returncode, 'output': focused.stdout + focused.stderr},
              'legacy_custom_output_compatibility': {
                  'fixture': str(legacy_dir.relative_to(ROOT)), 'baseline_git_ref': 'HEAD',
                  'baseline_source_sha256': sha(old_source), 'unchanged_snapshot': before == after,
                  'absent_core_source_snapshot_remains_absent_from_evidence': True,
                  'source_provenance_status': after['measured_checks']['source_provenance']['status']},
              'known_scope_limit': {'description': 'Out-of-range indexed pixel can pass scanline checks; color reconstruction is not performed.',
                                    'png_sha256': sha(invalid_palette_index), 'gate_measurement': residual,
                                    'pillow_recovered_rgb': recovered_pixel,
                                    'blocking_for_stated_scope': False},
              'primary_specification': 'https://www.w3.org/TR/png-3/#11IDAT'}
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(cases)} independently decoded PNG cases passed; focused tests passed. Evidence: {OUTPUT}')


if __name__ == '__main__':
    main()
