"""Bind the tested diagnostic source closure; not a production seal or run grant."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
relative=HERE.relative_to(REPO).as_posix()
names=['experiments/h1_operation_historical_witness_development_v1.py',
    'tests/test_h1_operation_historical_witness_development_v1.py',
    'tests/test_h1_operation_saved_diagnostic_monitor_v1.py',
    *[relative+'/'+n for n in ('launch_saved_v1.py','run_saved_bounded_v1.py','measure_saved_v1.py')]]
required={names[0]:'8b91c8184dc934c90f324705bb05104128245594a677a7fcdf1a13daa04a7e6a',
    names[1]:'d6a0a9413ef43ced30f647be32747147f733a5854ede8b88e332b9c09c159b32',
    relative+'/run_saved_bounded_v1.py':'a8fa8490325b20397e63e1978a3f98cbbb5f0fac565bc1bed69cf7e6cdcc01b0'}
pins={}
for name in names:
    raw=(REPO/name).read_bytes();ast.parse(raw,filename=name)
    pins[name]=sha256(raw).hexdigest()
for name,h in required.items():
    if pins[name]!=h:raise ValueError('tested candidate source differs: '+name)
for label,passes in (('unit_06',68),('monitor_unit_02',3)):
    terminal=json.loads((HERE/label/'terminal.json').read_bytes())
    if terminal['exit_code']!=0 or terminal['stop_reason'] is not None or not terminal['source_unchanged']:
        raise ValueError('required targeted terminal is not closed')
    log=(HERE/label/'stdout.log').read_text(encoding='utf-8')
    if str(passes)+' passed' not in log:raise ValueError('required targeted pass count differs')
    request=json.loads((HERE/label/'request.json').read_bytes())
    required_names=names[:2] if label=='unit_06' else [names[2]]
    if any(request['source_sha256'][str(REPO/n)]!=pins[n] for n in required_names):
        raise ValueError('current diagnostic differs from tested source closure')
    for filename in ('terminal.json','request.json','stdout.log'):
        path=HERE/label/filename;pins[path.relative_to(REPO).as_posix()]=sha256(path.read_bytes()).hexdigest()
value=dict(schema='h1_operation_historical_diagnostic_source_manifest_v1',
    status='DRAFT_NONAUTHORITATIVE',files_sha256=pins,
    helper_tests=68,monitor_helper_tests=3,monitor_helper_test_scope='unmodified AST definitions, fixed full outer SHA',
    configured_package_sha256='e5a7893d2b88812e46c8000463f8e03ba4195ac6ac189b41e68d3af43922d139',
    modes=['full_only','operation'],attempts_per_mode=1,oracle_prepares_per_mode=1,diagnostic_prepares_per_mode=2,
    per_mode_limits=dict(wall_seconds=300,sampled_process_tree_rss_mib=512,new_artifact_mib=64),
    whole_workflow_performance_review_complete=False,production_handoff_integrated=False,
    long_chain_launch_admitted=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
path=HERE/'diagnostic_source_manifest_v1.json'
with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(manifest_sha256=sha256(path.read_bytes()).hexdigest(),members=len(pins))))
