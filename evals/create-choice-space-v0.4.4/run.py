"""Replay bounded visual-role probes without choosing a quality winner."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Fresh replay directory')
    parser.add_argument('--freeze', type=Path, default=HERE / 'freeze.json')
    parser.add_argument('--runtime-root', type=Path, default=HERE / 'initial-runtime')
    args = parser.parse_args()
    frozen = json.loads(args.freeze.read_text())
    runtime = args.runtime_root.resolve()
    for name, digest in frozen['runtime'].items():
        assert hashlib.sha256((runtime / name).read_bytes()).hexdigest() == digest, name
    path = runtime / 'skills/easyviz/scripts/create_candidates.py'
    loader = importlib.util.spec_from_file_location('choice_space_engine', path)
    engine = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(engine)
    args.out.mkdir(parents=True, exist_ok=False)
    results = []
    for case in frozen['cases']:
        inputs = HERE / 'inputs' / case['id']
        for name, digest in case['files'].items():
            assert hashlib.sha256((inputs / name).read_bytes()).hexdigest() == digest, name
        manifest = engine.create_candidates(inputs / 'data.csv', inputs / 'spec.json',
                                             args.out / case['id'], new_draft=True, count=3)
        source = json.loads((inputs / 'spec.json').read_text())
        observations, contracts, facets = [], [], []
        for proposal in manifest['candidates']:
            folder = args.out / case['id'] / proposal['id']
            spec = json.loads((folder / 'spec.json').read_text())
            evidence = json.loads((folder / 'geometry-evidence.json').read_text())
            assert evidence['source_to_artist']['status'] == 'pass'
            assert spec['fields'] == source['fields']
            assert spec.get('order', {}) == source.get('order', {})
            for key, value in source['options'].items():
                assert spec['options'][key] == value, (case['id'], key)
            assert all(math.isclose(a, b) for a, b in zip(evidence['canvas_mm'], [80, 70]))
            assert evidence['typography']['tick'] == 8
            facets.append(proposal['visual_facet_evidence'])
            observations.append(evidence['source_to_artist'])
            contracts.append({'candidate': proposal['id'], 'route': proposal['route_id'],
                              'technical': proposal['technical_review']['status'],
                              'changed_facets': proposal['changed_facets_vs_candidate_01']})
        assert len({json.dumps(item, sort_keys=True) for item in facets}) == len(facets)
        assert manifest['inputs_unchanged']
        result = {'case': case['id'], 'rows': manifest['features']['input_rows'],
                  'declared_reading_task': case['reading_task'],
                  'scope': 'Bounded implementation/constraint probe, not a model or aesthetic effectiveness experiment',
                  'status': manifest['status'], 'candidates': contracts,
                  'source_to_artist': observations, 'actual_image_review': 'pending',
                  'aesthetic_winner': None}
        results.append(result)
        (args.out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    assert all(item['status'] == 'visual_review_pending' for item in results)


if __name__ == '__main__':
    main()
