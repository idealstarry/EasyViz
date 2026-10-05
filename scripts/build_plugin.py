"""Build a portable EasyViz plugin; keep full paper archives outside the package."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from check_package import validate_resource_tree
from sync_skill_cases import sync

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'


def check_output_path(path: Path, dist: Path) -> None:
    """Check owned paths without following symlinks or parent traversal.

    A repository-local output belongs to ROOT. An explicitly selected external
    output directory is its own boundary; system aliases above it are not owned.
    """
    if '..' in dist.parts or '..' in path.parts:
        raise ValueError(f'Refusing a parent traversal build path: {path}')
    relative = path.relative_to(dist)
    boundary = ROOT if dist.is_relative_to(ROOT) else dist
    parts = dist.relative_to(boundary).parts + relative.parts
    for candidate in (boundary, *(boundary.joinpath(*parts[:index])
                                  for index in range(1, len(parts) + 1))):
        if candidate.is_symlink():
            raise ValueError(f'Refusing to write through a symlink build path: {candidate}')


def validate_sources() -> None:
    """Reject external links and nonportable resources before copying them."""
    directories = (ROOT / 'plugins/easyviz/.codex-plugin', ROOT / 'plugins/easyviz/assets', ROOT / 'skills')
    files = [ROOT / 'plugins/easyviz/README.md']
    files.extend(path for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md')
                 if (path := ROOT / name).exists() or path.is_symlink())
    for path in (*directories, *files):
        relative = path.relative_to(ROOT)
        for candidate in (ROOT, *(ROOT.joinpath(*relative.parts[:index])
                                  for index in range(1, len(relative.parts) + 1))):
            if candidate.is_symlink() or not (candidate.is_file() or candidate.is_dir()):
                raise ValueError(f'Symlink or special build source: {candidate}')
    for path in directories:
        validate_resource_tree(path)
    for path in files:
        if not path.is_file():
            raise ValueError(f'Build source is not a regular file: {path}')


def build(dist: Path | None = None) -> dict:
    """Build into the default dist folder or a caller-selected output folder."""
    dist = Path(dist if dist is not None else DIST).absolute()
    target = dist / 'easyviz'
    for source in (ROOT / 'plugins/easyviz', ROOT / 'skills'):
        physical_target, physical_source = target.resolve(), source.resolve()
        if (target.is_relative_to(source) or source.is_relative_to(target)
                or physical_target.is_relative_to(physical_source) or physical_source.is_relative_to(physical_target)):
            raise ValueError(f'Build destination overlaps the source tree: {target}')
    validate_sources()
    manifest = json.loads((ROOT / 'plugins/easyviz/.codex-plugin/plugin.json').read_text())
    version = manifest['version']
    if not isinstance(version, str) or not version or '/' in version or '\\' in version:
        raise ValueError('Plugin version must be usable in a single archive filename')
    archive = dist / f'easyviz-{version}.zip'
    summary_path = dist / 'build.json'

    # Check every owned destination before syncing or replacing any directory.
    for path in (target, target / '.codex-plugin/plugin.json', archive, summary_path):
        check_output_path(path, dist)
    if dist.exists() and not dist.is_dir():
        raise ValueError(f'Build destination is not a directory: {dist}')
    for path in (archive, summary_path):
        if path.exists() and not path.is_file():
            raise ValueError(f'Build output is not a file: {path}')
    if target.exists():
        try:
            previous = json.loads((target / '.codex-plugin/plugin.json').read_text())
            if not target.is_dir() or not isinstance(previous, dict) or previous.get('name') != 'easyviz':
                raise ValueError('manifest name is not easyviz')
        except (OSError, ValueError) as error:
            raise ValueError(f'Existing build directory is not identified as EasyViz; left untouched: {target}') from error

    sync()
    # Sync refreshes generated skill assets; validate that authoritative tree too.
    validate_sources()
    dist.mkdir(parents=True, exist_ok=True)
    # Only replace the identified generated build directory, never the source.
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    shutil.copytree(ROOT / 'plugins/easyviz/.codex-plugin', target / '.codex-plugin')
    shutil.copytree(ROOT / 'plugins/easyviz/assets', target / 'assets')
    shutil.copytree(ROOT / 'skills', target / 'skills', ignore=shutil.ignore_patterns('__pycache__', '.DS_Store', '*.pyc'))
    shutil.copy2(ROOT / 'plugins/easyviz/README.md', target / 'README.md')
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, target / name)
    content_identity = hashlib.sha256()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for path in sorted(target.rglob('*')):
            if path.is_file():
                # Package identity follows file contents, not checkout timestamps.
                info = zipfile.ZipInfo(path.relative_to(dist).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                content = path.read_bytes()
                package.writestr(info, content)
                content_identity.update(info.filename.encode() + b'\0' + hashlib.sha256(content).digest())
    summary = {'version': version, 'archive': archive.name,
               'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
               'content_sha256': content_identity.hexdigest(),
               'files': sum(path.is_file() for path in target.rglob('*')),
               'bytes': archive.stat().st_size}
    summary_path.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
