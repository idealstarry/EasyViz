"""Actual copied core exports prove generic review auxiliary source continuity."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tests'))
import test_create_review as base

fixture=base.CreateReviewTests('test_source_data_and_saved_spec_changes_are_stale_before_another_render')
fixture.setUp()
try:
    runtime=fixture.root/'copied-runtime';runtime.mkdir()
    for source in (ROOT/'skills/easyviz/scripts').glob('*.py'):shutil.copy2(source,runtime/source.name)
    output=fixture.root/'actual-copied-output'
    run=subprocess.run([sys.executable,'-I','-B',str(runtime/'render.py'),'--data',str(fixture.data),'--spec',str(fixture.spec_path),'--out',str(output),'--track','create'],cwd=fixture.root,capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    fixture.figure=output
    staged=fixture.stage()
    fixture.recorded_fixture(staged)
    before=base.gate.check(staged['packet'])
    assert before['gate_status']=='recorded',before
    helper=runtime/'legend_layout.py';helper.write_bytes(helper.read_bytes()+b'\n# isolated actual helper replacement after output\n')
    after=base.gate.check(staged['packet'])
    sources=base.gate.snapshot(output,caption=fixture.caption)
    evidence={'scope':'Actual copied core outputs and isolated recorded attestation fixture. No production source/export modified, no claim that an image was viewed.',
              'create_review_sha256':hashlib.sha256((ROOT/'skills/easyviz/scripts/create_review.py').read_bytes()).hexdigest(),
              'before_gate_status':before['gate_status'],'after_gate_status':after['gate_status'],'after_errors':after['errors'],
              'after_source_provenance':sources['measured_checks']['source_provenance']['status'],
              'checked_source_roles':list(sources['source_bindings'])}
    destination=HERE/(sys.argv[1] if len(sys.argv)>1 else 'create-review-auxiliary-before-evidence.json')
    destination.write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))
finally:fixture.tearDown()
