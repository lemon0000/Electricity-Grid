"""Archive exact bounded terminal observations; never creates authority."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
CASES={
    '199':('roster5_callback_frame_units_199','D:/h1_roster5_callback_frame_199_non_authoritative',None,()),
    '200':('roster5_live_header_200','D:/h1_roster5_header_200_non_authoritative','roster5_live_header_plan_200.json',('roster5_live_header_observation.json',)),
    '201':('phase_successor_real_units_201','D:/h1_phase_successor_201_non_authoritative',None,('phase_window_observation.json','shared_phase_observation.json')),
}
number,=sys.argv[1:];label,root,plan_name,names=CASES[number];base=Path(root)
terminal=json.loads((H/label/'terminal.json').read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert not terminal['storage_read_errors'] and terminal['final_storage_observation_complete']
request=json.loads((H/label/'request.json').read_bytes())
assert all(sha256(Path(path).read_bytes()).hexdigest()==pin for path,pin in request['source_sha256'].items())
stdout=(H/label/'stdout.log').read_text(encoding='utf-8')
match=re.search(r'(\d+) passed in ([\d.]+)s',stdout);assert match
closed_path=base/'unit_code_read_lease_closed.json';closed=json.loads(closed_path.read_bytes())
assert closed['all_code_handles_closed'] and closed['original_read_alias_restored']
if number=='200':
    for key in ('all_metadata_handles_closed','original_metadata_version_alias_restored',
            'all_path_handles_closed','canonical_path_alias_restored'):assert closed[key]
    assert closed['canonical_path_state']=='closed' and closed['pending_path_handles']==0
paths=[H/label/name for name in ('request.json','started.json','terminal.json','stdout.log')]+[closed_path]
observations={}
for name in names:
    found=list(base.glob('*/'+name));assert len(found)==1,(name,found)
    paths.extend(found);observations[name]=json.loads(found[0].read_bytes())
plan=json.loads((D/plan_name).read_bytes()) if plan_name else None
if plan:assert all(sha256(Path(path).read_bytes()).hexdigest()==pin for path,pin in plan['files_sha256'].items())
archive=D/('roster_'+number+'_preserved_non_authoritative');archive.mkdir(exist_ok=False)
copies=[]
for source in paths:
    target=archive/source.name;raw=source.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    assert target.read_bytes()==source.read_bytes()==raw
    copies.append(dict(source=str(source),saved=str(target),sha256=sha256(raw).hexdigest()))
value=dict(schema='h1_roster_evidence_'+number,status='VERIFIED_SCOPED_DEVELOPMENT_OBSERVATION',
    terminal=terminal,pytest_cases=int(match[1]),pytest_seconds=float(match[2]),
    request_source_pins=len(request['source_sha256']),current_source_pins_match=True,
    plan_sha256=sha256((D/plan_name).read_bytes()).hexdigest() if plan_name else None,
    planned_pins=len(plan['files_sha256']) if plan else None,pin_drift=[],
    entry_closed={key:item for key,item in closed.items() if key!='files_sha256'},
    observations=observations,archive_files=copies,new_N0_Jobs=0,real_native_calls=0,
    production_seal=False,official_review=False,whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False,formal_execution_ready=False,formal_run_authority=False,
    formal_result=False,resource_admission=False,native_execution_authorized=False)
out=D/('roster_result_'+number+'.json')
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),cases=int(match[1]),
    pytest_seconds=float(match[2]),outer_seconds=terminal['elapsed_seconds'],archives=len(copies))))
