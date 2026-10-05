"""Actual mapped core source helper staleness, isolated from production code."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'skills/easyviz/scripts'))
from figure_workbench import FigureWorkbench
from apply_figure_requests import accept_attempt

def main():
    evidence={'scope':'Copied current core runtime and actual new SVG/PDF/PNG; original source/runtime/outputs unchanged.'}
    with tempfile.TemporaryDirectory(prefix='easyviz-core-declared-helper-') as tmp:
        work=Path(tmp); runtime=work/'runtime'; runtime.mkdir()
        for src in (ROOT/'skills/easyviz/scripts').glob('*.py'): shutil.copy2(src,runtime/src.name)
        data=work/'data.csv';data.write_text('x,y\n0.15,0.15\n0.5,0.5\n0.85,0.85\n')
        spec=work/'spec.json';spec.write_text(json.dumps({'chart':'scatter','fields':{'x':'x','y':'y'},'formats':['svg','pdf','png'],'layout':{'width_mm':88,'height_mm':66,'font':'DejaVu Sans','dpi':160},'labels':{'x':'X','y':'Y'},'options':{'point_area_pt2':16,'x_limits':[0,1],'y_limits':[0,1]}}))
        output=work/'attempt'
        result=subprocess.run([sys.executable,'-I','-B',str(runtime/'render.py'),'--data',str(data),'--spec',str(spec),'--out',str(output),'--track','create'],cwd=work,capture_output=True,text=True)
        assert result.returncode==0,result.stdout+result.stderr
        before=FigureWorkbench(output).state()
        settings=json.loads((output/'settings.json').read_text())
        declared=settings['source_bindings']['helper:legend_layout.py']
        target=runtime/'legend_layout.py'; target.write_bytes(target.read_bytes()+b'\n# isolated late replacement\n')
        after=FigureWorkbench(output).state()
        try:
            accepted=accept_attempt(output,validation='Actual isolated source/helper binding reproduction only; no aesthetic claim.')
            acceptance=json.loads((output/'accepted-snapshot/acceptance.json').read_text())
            evidence['accepted']=True
            evidence['snapshot_inputs']=acceptance.get('files',acceptance.get('source'))
        except Exception as exc:
            evidence['accepted']=False;evidence['refused']=str(exc)
        evidence.update(before_source_current=before['source_current'], after_source_current=after['source_current'],
                        checked_source_roles=list(after['source_versions']), declared_consumed_helper=declared,
                        replacement_helper_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                        settings_declared_helper_hash_matches_current=declared['sha256']==hashlib.sha256(target.read_bytes()).hexdigest(),
                        exported_files={suffix:hashlib.sha256((output/('panel.'+suffix)).read_bytes()).hexdigest() for suffix in ('svg','pdf','png')})
    (HERE/(sys.argv[1] if len(sys.argv)>1 else 'core-declared-helper-staleness-evidence.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':main()
