"""List a compact, dependency-complete forward QA evidence selection.

This selects files only; it neither stages Git files nor deletes working evidence.
"""
from pathlib import Path
import json, hashlib

BASE=Path(__file__).resolve().parent
REPO=BASE.parents[2]
include={}
def add(path,reason):
    path=Path(path).resolve()
    if path.is_file():include[str(path.relative_to(REPO))]=reason

for name in ['manifest.json','review-summary.md','review-history.json','resource-access.json','independent-create-review.md','palette-rationale.md','prepare_tasks.py','select_release_evidence.py']:
    add(BASE/name,'Consolidated evidence, preparation/release selection code, or independent review')
tasks=json.loads((BASE/'manifest.json').read_text())['tasks']
current_packets=[]
for entry in tasks:
    task=BASE/entry['task'];n=task.name[:2]
    inputs=BASE.parent/'forward-inputs'/task.name
    for name in ['measurements.csv','request.json']:add(inputs/name,'Frozen forwarded runtime input')
    for name in ['run.py','request.json','spec.json','adopted-spec.json','create-intent.json','input-map.json','adopted-settings.json','design-brief.json','source-assertions.json','prepared.csv','label-map.csv','plot.py','caption-correction.json','replay-evidence.json']:
        add(task/name,'Adopted replay/transform code, settings, source assertions or caption correction')
    for relative in entry['final_dirs']:
        final=BASE/relative
        for p in final.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':add(p,'Selected final individual export, data, metadata, caption or bound review')
        gate=json.loads((final/'review-gate.json').read_text())
        current_packets.append(Path(gate['review']).with_name('packet.json'))
    # Preserve first visible results separately without duplicating all vector exports.
    first=task/'first-render'
    for image in first.rglob('panel.png'):
        for name in ['panel.png','qa.json','settings.json','spec.json','plot-source.py']:
            add(image.parent/name,'First-render image and actual technical/source evidence')
    add(first/'manifest.json','First candidate/preview mechanism and selection evidence')
    # Keep representative changed/rejected PNG and QA, not redundant PDF/SVG copies.
    if n=='04':
        for attempt in ['revision-02','revision-03']:
            for name in ['panel.png','qa.json','settings.json']:add(task/attempt/name,'Rejected bounded packing attempt evidence')
        for name in ['revision-spec.json','final-spec.json']:add(task/name,'Actual rejected-attempt source spec')
    if n in ['05','07']:
        for image in (task/'revision-02').rglob('panel.png'):
            for name in ['panel.png','qa.json','settings.json','spec.json','plot-source.py']:add(image.parent/name,'Second-pass geometry/scale evidence')
    if n=='05':
        for name in ['revision-spec.json','final-spec.json']:add(task/name,'Actual alias/precision source specs')

# Include every owned source/spec path bound by current packets, including frozen snapshots.
canonical_dependencies={}
for p in current_packets:
    packet=json.loads(p.read_text())
    for records in packet['snapshot']['source_bindings'].values():
        for record in records:
            source=Path(record['path']).resolve()
            if source.is_relative_to(BASE) or source.is_relative_to(BASE.parent/'forward-inputs'):
                add(source,'Required current review source/spec dependency')
            elif source.is_relative_to(REPO):
                canonical_dependencies[str(source.relative_to(REPO))]=record.get('expected_sha256',record.get('sha256'))

files=[]
for path,reason in sorted(include.items()):
    raw=(REPO/path).read_bytes()
    files.append({'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'reason':reason})
all_paths={str(p.relative_to(REPO)) for directory in [BASE,BASE.parent/'forward-inputs'] for p in directory.rglob('*') if p.is_file()}
excluded=sorted(all_paths-set(include)-{'evals/development-v0.5.0/forward-create/release-evidence-selection.json','evals/development-v0.5.0/forward-create/release-evidence-files.txt'})
manifest={'schema_version':1,'scope':'Forward Create release evidence selection only; production source commits remain the root agent responsibility.','does_not_delete_or_stage':True,'include_file_count':len(files),'include_bytes':sum(p['bytes'] for p in files),'selected_final_panel_sets':10,'inputs':8,'files':files,'also_include_manifest_files':['evals/development-v0.5.0/forward-create/release-evidence-selection.json','evals/development-v0.5.0/forward-create/release-evidence-files.txt'],'canonical_runtime_dependencies':canonical_dependencies,'exclusion_policy':['__pycache__ and *.pyc','replay-check export duplicates; compact replay-evidence.json retained','nonfinal PDF/SVG duplicates','old full source/output duplicates not required by current packet dependencies','one-off finalize/record_delivery utilities and help-contract dumps; direct replay/preparation code retained'],'excluded_paths':excluded,'first_render_policy':'First PNGs plus real QA/settings/spec or custom source evidence retained separately. The selected final sets retain all requested formats.','review_policy':'Task 04 current caption uses pass-03-caption-02. The former pass-03 packet is retained as explicitly historical/stale evidence, linked by caption-correction.json. Current packet source dependencies are included.'}
(BASE/'release-evidence-selection.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(BASE/'release-evidence-files.txt').write_text('\n'.join([record['path'] for record in files]+manifest['also_include_manifest_files'])+'\n')
print(json.dumps({'include_files':len(files)+2,'include_bytes':manifest['include_bytes'],'excluded_files':len(excluded),'canonical_dependencies':len(canonical_dependencies)},indent=2))
