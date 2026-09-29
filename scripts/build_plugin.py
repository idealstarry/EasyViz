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
shutil.copytree(ROOT / 'skills', TARGET / 'skills', ignore=shutil.ignore_patterns('__pycache__','.DS_Store','*.pyc'))
shutil.copy2(ROOT / 'plugins/easyviz/README.md', TARGET / 'README.md')
for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
    if (ROOT / name).exists():
        shutil.copy2(ROOT / name, TARGET / name)
manifest=json.loads((TARGET / '.codex-plugin/plugin.json').read_text())
version=manifest['version']
archive=DIST / f'easyviz-{version}.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in sorted(TARGET.rglob('*')):
        if path.is_file():
            z.write(path,path.relative_to(DIST))
summary={'version':version,'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':sum(p.is_file() for p in TARGET.rglob('*')),'bytes':archive.stat().st_size}
(DIST / 'build.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
