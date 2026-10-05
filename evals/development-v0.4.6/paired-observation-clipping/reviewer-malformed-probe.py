"""Replay the literal extra-cell false acceptance against a chosen script."""
import argparse, hashlib, importlib.util, json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--script',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--expect-refusal',action='store_true')
args=parser.parse_args()
assert not args.out.exists(), 'Preserve previous evidence; choose a fresh folder.'
args.out.mkdir(parents=True)
source=args.out/'source.csv'
source.write_text('id,condition,value\nextra,u1,A,1\nextra,u1,B,2\nextra,u2,A,3\nextra,u2,B,2.5\n')
spec={'chart':'paired','fields':{'unit':'id','condition':'condition','value':'value'},'options':{'y_limits':[0,4],'point_area_pt2':10},'layout':{'width_mm':88,'height_mm':66.1,'font':'DejaVu Sans','dpi':160,'auto_fit':False,'margins':{'left':.19,'right':.77,'bottom':.23,'top':.88}},'formats':['png','pdf','svg'],'labels':{'y':'Value'}}
spec_path=args.out/'spec.json';spec_path.write_text(json.dumps(spec,indent=2)+'\n')
loader=importlib.util.spec_from_file_location('independent_paired_malformed',args.script.resolve())
paired=importlib.util.module_from_spec(loader);loader.loader.exec_module(paired)
error=None
try: paired.render(source,spec,args.out/'output',spec_path=spec_path)
except paired.SpecError as exc: error=str(exc)
qa=json.loads((args.out/'output/qa.json').read_text())
report={'candidate_sha256':hashlib.sha256(args.script.read_bytes()).hexdigest(),'error':error,'valid_outputs':qa['valid_outputs'],'exports_present':bool(list((args.out/'output').glob('panel.*'))),'literal_headers':3,'literal_cells_per_record':4}
(args.out/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
if args.expect_refusal:
    assert error is not None and not report['valid_outputs'] and not report['exports_present'],report
print(json.dumps(report))
