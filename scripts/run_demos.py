"""Render portable synthetic fixtures with their declared core/focused inputs."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def fixture_command(case, output):
    spec = json.loads((case / 'spec.json').read_text())
    scripts = ROOT / 'skills/easyviz/scripts'
    if spec['chart'] == 'annotated_matrix':
        # This focused fixture declares keyed tracks and supplied trees. The
        # core renderer cannot substitute for that contract.
        return [sys.executable, str(scripts / 'annotated_matrix.py'),
                '--data', str(case / 'input.csv'), '--spec', str(case / 'spec.json'),
                '--row-metadata', str(case / 'row.csv'),
                '--column-metadata', str(case / 'column.csv'),
                '--row-linkage', str(case / 'row.json'),
                '--column-linkage', str(case / 'column.json'), '--out', str(output)]
    return [sys.executable, str(scripts / 'render.py'), '--data', str(case / 'data.csv'),
            '--spec', str(case / 'spec.json'), '--out', str(output)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'evals/fixtures')
    args = parser.parse_args()
    results = []
    for case in sorted((ROOT / 'skills/easyviz/assets/fixtures').iterdir()):
        if not (case / 'spec.json').exists():
            continue
        output = args.out / case.name
        subprocess.run(fixture_command(case, output), check=True)
        shutil.copy2(output / 'panel.png', case / 'preview.png')
        results.append({'case': case.name, 'output': str(output.relative_to(ROOT))
                        if output.is_relative_to(ROOT) else str(output)})
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'index.json').write_text(json.dumps(results, indent=2) + '\n')
    print(f'Rendered {len(results)} synthetic demonstration cases.')


if __name__ == '__main__':
    main()
