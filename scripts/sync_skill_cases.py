"""Refresh curated portable cases from reviewed development examples.

Keep source attribution; omit author code, private archive paths, and full evaluation
histories. Development folders retain the original provenance and access logs.
"""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'skills/easyviz/assets'
GENERATED_CASES = (
    'massier-bmi-violin', 'massier-integration-radar', 'cell-atlas-dotplot',
    'paired-effects', 'paired-myeloid-remodeling', 'xiang-bubble-volcano',
    'vabistsevits-forest', 'urschel-paired', 'truong-components', 'urschel-ecdf', 'shi-timecourse', 'yayon-cma',
)


def check_output_path(target):
    """Check the owned root through the destination without resolving symlinks.

    Production ASSETS belongs to the already resolved repository ROOT. An
    explicit out-of-repository ASSETS used by isolated tests is its own boundary;
    system aliases above that boundary, such as /var, are not owned paths.
    """
    relative = target.relative_to(ASSETS)
    boundary = ROOT if ASSETS.is_relative_to(ROOT) else ASSETS
    asset_parts = ASSETS.relative_to(boundary).parts
    owned_parts = asset_parts + relative.parts
    for path in (boundary, *(boundary.joinpath(*owned_parts[:index])
                            for index in range(1, len(owned_parts) + 1))):
        if path.is_symlink():
            raise ValueError(f'Refusing to write through a symlink assets path: {path}')


def reset_generated_cases():
    """Rebuild owned case directories, retaining hand-maintained recipe files."""
    targets = [ASSETS / 'cases' / case for case in GENERATED_CASES]
    # Check every destination before deleting anything, including recipe files
    # that copy_file will update without owning their whole parent directory.
    for target in targets + [ASSETS / 'recipes/annotated-heatmap' / name
                             for name in ('plot.py', 'settings.json')]:
        check_output_path(target)
    for target in targets:
        if target.exists() and not target.is_dir():
            raise ValueError(f'Generated case destination is not a directory: {target}')
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)


def portable_metadata(value):
    if isinstance(value, dict):
        return {key: portable_metadata(item) for key, item in value.items()
                if key not in ("local_full_workbook", "local_full_pdf")}
    if isinstance(value, list):
        return [portable_metadata(item) for item in value]
    if isinstance(value, str) and value.startswith('/Users/'):
        return Path(value).name
    return value


def copy_file(source, target):
    check_output_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == '.json':
        target.write_text(json.dumps(portable_metadata(json.loads(source.read_text())), indent=2) + '\n')
    else:
        shutil.copy2(source, target)


def sync():
    reset_generated_cases()
    for case in ('massier-bmi-violin', 'massier-integration-radar'):
        source = ROOT / 'examples/no-author-code' / case
        target = ASSETS / 'cases' / case
        target.mkdir(parents=True, exist_ok=True)
        for name in ('plot.py', 'settings.json', 'adopted-spec.md', 'stats.json', 'qa.json',
                     'plotting-data.csv', 'panel.png', 'panel.pdf', 'panel.svg',
                     'independent-review.json', 'independent-review.md', 'README.md'):
            copy_file(source / name, target / name)
        if (source / 'density-data.csv').exists():
            copy_file(source / 'density-data.csv', target / 'density-data.csv')
        for file in (source / 'inputs').iterdir():
            if file.is_file():
                copy_file(file, target / 'inputs' / file.name)
        copy_file(ROOT / 'evals/reproduce-inputs' / case / 'provenance.json', target / 'provenance.json')
        adopted = target / 'adopted-spec.md'
        adopted.write_text(adopted.read_text().replace(f'.venv/bin/python examples/no-author-code/{case}/plot.py', 'python /path/to/case/plot.py'))
        if case == 'massier-bmi-violin':
            adopted.write_text(adopted.read_text() + '\nDevelopment-only access logs and first-render history described above are retained in the development repository, outside this portable case.\n')
    case = 'cell-atlas-dotplot'
    source = ROOT / 'examples/create' / case
    target = ASSETS / 'cases' / case
    for name in ('plot.py', 'legend_layout.py', 'figure-settings.json', 'annotations.json', 'source-data.csv',
                 'data-dictionary.md', 'provenance.json', 'README.md', 'request.md', 'caption.md'):
        copy_file(source / name, target / name)
    for name in ('figure.png', 'figure.pdf', 'figure.svg', 'plotted-data.csv', 'validation.json'):
        copy_file(source / 'output' / name, target / 'output' / name)
    # Reusable implementation only: the CC BY-NC Gontijo tables stay in development.
    source = ROOT / 'examples/create/annotated-inhibition'
    target = ASSETS / 'recipes/annotated-heatmap'
    for name in ('plot.py', 'settings.json'):
        copy_file(source / name, target / name)
    source = ROOT / 'examples/create/paired-effects'
    target = ASSETS / 'cases/paired-effects'
    for name in ('plot.py', 'legend_layout.py', 'figure-settings.json', 'actual-settings.json', 'source.csv',
                 'plotting-data.csv', 'provenance.json', 'README.md', 'request.md', 'caption.md',
                 'numeric-qa.json', 'reuse-validation.json', 'legend-update-review.json', 'review-independent.md',
                 'review-independent.json', 'panel.png', 'panel.pdf', 'panel.svg'):
        copy_file(source / name, target / name)
    for file in (source / 'evaluation').iterdir():
        if file.is_file():
            copy_file(file, target / 'evaluation' / file.name)
    source = ROOT / 'examples/create/paired-myeloid-remodeling'
    target = ASSETS / 'cases/paired-myeloid-remodeling'
    for name in ('plot.py', 'prepare.py', 'figure-settings.json', 'annotations.json',
                 'source-data.csv', 'provenance.json', 'README.md', 'caption.md',
                 'design-rationale.md', 'numeric-verification.json', 'pdf-verification.json',
                 'visual-review.json', 'standalone-verification.json'):
        copy_file(source / name, target / name)
    for folder in ('output', 'transfer-five-year'):
        for file in (source / folder).rglob('*'):
            if file.is_file():
                copy_file(file, target / file.relative_to(source))
    copy_file(ROOT / 'evals/design-value/paired-comparison.md', target / 'independent-comparison.md')
    for track, case in (
            ('no-author-code', 'xiang-bubble-volcano'),
            ('no-author-code', 'vabistsevits-forest'),
            ('no-author-code', 'urschel-paired'),
            ('no-author-code', 'truong-components'),
            ('create', 'urschel-ecdf'),
            ('no-author-code', 'shi-timecourse'),
            ('no-author-code', 'yayon-cma')):
        source = ROOT / 'examples' / track / case
        target = ASSETS / 'cases' / case
        # Retain reviewed evidence and compact inputs; omit development history.
        for file in source.rglob('*'):
            relative = file.relative_to(source)
            if (not file.is_file() or any(part in ('first-render', '__pycache__') for part in relative.parts)
                    or file.name in ('access-log.json', 'first-attempt-evidence.json')
                    or file.suffix == '.pyc'):
                continue
            copy_file(file, target / relative)
    print('Synced eleven CC BY cases, one synthetic forest case, and the annotated-heatmap recipe (without its restricted dataset).')


if __name__ == '__main__':
    sync()
