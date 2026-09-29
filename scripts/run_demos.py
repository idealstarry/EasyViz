"""Render all portable synthetic fixtures using the reusable EasyViz renderer."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--out', type=Path, default=ROOT/'evals/fixtures')
args=p.parse_args()
results=[]
for case in sorted((ROOT/'skills/easyviz/assets/fixtures').iterdir()):
    if not (case/'spec.json').exists():
        continue
    out=args.out/case.name
    subprocess.run([sys.executable,str(ROOT/'skills/easyviz/scripts/render.py'),'--data',str(case/'data.csv'),'--spec',str(case/'spec.json'),'--out',str(out)],check=True)
    shutil.copy2(out/'panel.png', case/'preview.png')
    results.append({'case':case.name,'output':str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)})
args.out.mkdir(parents=True,exist_ok=True)
(args.out/'index.json').write_text(json.dumps(results,indent=2)+'\n')
print(f'Rendered {len(results)} synthetic demonstration cases.')
