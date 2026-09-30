"""Build a portable EasyViz plugin; keep full paper archives outside the package."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from sync_skill_cases import sync

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
TARGET = DIST / 'easyviz'
sync()
DIST.mkdir(exist_ok=True)
# Only replace this generated build directory, never the source skill tree.
if TARGET.exists():
    if TARGET.is_symlink():
        raise ValueError('Refusing to replace a symlink build directory')
    shutil.rmtree(TARGET)
TARGET.mkdir()
shutil.copytree(ROOT / 'plugins/easyviz/.codex-plugin', TARGET / '.codex-plugin')
shutil.copytree(ROOT / 'plugins/easyviz/assets', TARGET / 'assets')
shutil.copytree(ROOT / 'skills', TARGET / 'skills', ignore=shutil.ignore_patterns('__pycache__','.DS_Store','*.pyc'))
shutil.copy2(ROOT / 'plugins/easyviz/README.md', TARGET / 'README.md')
for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
    if (ROOT / name).exists():
        shutil.copy2(ROOT / name, TARGET / name)
manifest=json.loads((TARGET / '.codex-plugin/plugin.json').read_text())
version=manifest['version']
archive=DIST / f'easyviz-{version}.zip'
content_identity = hashlib.sha256()
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in sorted(TARGET.rglob('*')):
        if path.is_file():
            # Package identity follows file contents, not checkout timestamps.
            info = zipfile.ZipInfo(path.relative_to(DIST).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            content = path.read_bytes()
            z.writestr(info, content)
            content_identity.update(info.filename.encode() + b'\0' + hashlib.sha256(content).digest())
summary={'version':version,'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'content_sha256':content_identity.hexdigest(),'files':sum(p.is_file() for p in TARGET.rglob('*')),'bytes':archive.stat().st_size}
(DIST / 'build.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
