"""Prove all recorded core helpers bind stale refusal and complete restoration."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'skills/easyviz/scripts'))
from figure_workbench import FigureWorkbench
from apply_figure_requests import accept_attempt, restore_attempt

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def build(work, name):
    root=work/name; root.mkdir()
    runtime=root/'runtime';runtime.mkdir()
    for src in (ROOT/'skills/easyviz/scripts').glob('*.py'):shutil.copy2(src,runtime/src.name)
    data=root/'data.csv';data.write_text('x,y\n0.15,0.15\n0.5,0.5\n0.85,0.85\n')
    spec=root/'spec.json';spec.write_text(json.dumps({'chart':'scatter','fields':{'x':'x','y':'y'},'formats':['svg','pdf','png'],'layout':{'width_mm':88,'height_mm':66,'font':'DejaVu Sans','dpi':160},'labels':{'x':'X','y':'Y'},'options':{'point_area_pt2':16,'x_limits':[0,1],'y_limits':[0,1]}}))
    output=root/'attempt'
    p=subprocess.run([sys.executable,'-I','-B',str(runtime/'render.py'),'--data',str(data),'--spec',str(spec),'--out',str(output),'--track','create'],cwd=root,capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    state=FigureWorkbench(output).state()
    assert state['manifest_valid'] and state['provenance_valid'] and state['source_current'] is True,state
    settings=json.loads((output/'settings.json').read_text())
    declared={k:v for k,v in settings['source_bindings'].items() if k not in ('data_file','source_script','spec_file')}
    assert state['input']['auxiliary_inputs']==declared,(state['input'],declared)
    assert all(v['current'] is True for v in state['source_versions'].values()),state
    return root,runtime,data,spec,output,declared

def main():
    evidence={'scope':'Fresh actual isolated mapped core PNG/PDF/SVG; no original sources/outputs modified. QA and accepted validation here establish a functional provenance flow, not visual superiority.',
              'runtime_sha256':{n:digest(ROOT/'skills/easyviz/scripts'/n) for n in ('figure_elements.py','figure_handoff.py','figure_workbench.py','apply_figure_requests.py','render.py')}}
    with tempfile.TemporaryDirectory(prefix='easyviz-core-helper-after-') as tmp:
        work=Path(tmp).resolve()
        root,runtime,data,spec,output,declared=build(work,'stale-helper')
        target=runtime/'legend_layout.py';target.write_bytes(target.read_bytes()+b'\n# isolated late changed dependency\n')
        stale=FigureWorkbench(output).state()
        assert stale['source_current'] is False,stale
        try:accept_attempt(output,validation='Isolated source binding proof only.')
        except Exception as error: evidence['stale_helper']={'source_current':False,'refused':str(error),'snapshot_created':(output/'accepted-snapshot').exists(),'declared_helpers':len(declared)}
        else:raise AssertionError('A changed declared helper was accepted')
        assert not evidence['stale_helper']['snapshot_created']
        root,runtime,data,spec,output,declared=build(work,'valid-restore')
        before=FigureWorkbench(output).state()
        exports={suffix:digest(output/('panel.'+suffix)) for suffix in ('svg','pdf','png')}
        accept_attempt(output,validation='Actual isolated source helper and byte-preserving restoration proof only.')
        accepted=json.loads((output/'accepted-snapshot/acceptance.json').read_text())
        shutil.rmtree(runtime);data.unlink();spec.unlink()
        restored=work/'restored'
        restore_attempt(output,out=restored)
        after=FigureWorkbench(restored).state()
        assert after['source_current'] is True and after['manifest_valid'] and after['provenance_valid'],after
        assert after['version']==before['version'],(after['version'],before['version'])
        assert {suffix:digest(restored/('panel.'+suffix)) for suffix in exports}==exports
        bindings=json.loads((restored/'settings.json').read_text())['source_bindings']
        assert set(bindings)==set(json.loads((output/'settings.json').read_text())['source_bindings'])
        assert all(Path(v['path']).is_file() and Path(v['path']).is_relative_to(restored) for v in bindings.values()),bindings
        evidence['valid_restore']={'accepted':True,'restored_source_current':True,'all_declared_roles':len(after['source_versions']),
                                   'auxiliary_helpers':len(declared),'all_original_runtime_data_spec_deleted':True,
                                   'version_unchanged':True,'svg_pdf_png_unchanged':True,'all_settings_source_bindings_rebased':True,
                                   'captured_files':list(accepted['files'])}
    (HERE/'core-declared-helper-after-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':main()
