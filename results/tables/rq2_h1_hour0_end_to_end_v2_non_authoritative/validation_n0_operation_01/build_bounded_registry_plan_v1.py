"""Pin a single zero-Job entry diagnostic before its execution."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
base=json.loads((HERE/'fresh_n0_plan_02.json').read_bytes())
code=dict(base['code_lease_sha256'])
scope=HERE/'bounded_stable_read_entry_v1.py';code[str(scope)]=sha256(scope.read_bytes()).hexdigest()
owner_source=HERE.parent/'validation_path_optimization_01/entry_revision_07/code_read_lease.py'
code[str(owner_source)]=sha256(owner_source.read_bytes()).hexdigest()
sources=dict(base['source_sha256']);sources.update(code)
for path in (Path(__file__),HERE/'measure_registry_entry_v1.py',
        HERE/'bounded_entry_unit_06/request.json',HERE/'bounded_entry_unit_06/terminal.json',
        REPO/'tests/test_h1_bounded_stable_read_entry_development_v1.py',
        HERE/'fresh_n0_monitor_02/terminal.json',HERE/'registry_reads_01_non_authoritative/terminal.json',
        HERE/'registry_reads_01_non_authoritative/training_raw.json',
        HERE/'registry_reads_01_non_authoritative/holdout_raw.json'):
    sources[str(path)]=sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in sources.items())
assert json.loads((HERE/'bounded_entry_unit_06/terminal.json').read_bytes())['exit_code']==0
value=dict(status='DRAFT_NONAUTHORITATIVE',question='Does the configured bounded raw-reader entry preserve both complete registry split projections with substantially lower allocation cost?',
    attempts=1,roots=0,hours=0,synthetic_jobs=0,native_calls=0,splits=['training','holdout'],
    predecessor_builds=2,candidate_builds=2,output=str(HERE/'bounded_registry_entry_01_non_authoritative'),
    source_sha256=sources,code_lease_sha256=code,old_chain_sha256=base['old_chain_sha256'],
    limits=dict(wall_seconds=120,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2),
    dag=['fixed inputs and interpreter paths','owned baseline code/METADATA leases','legacy registry two splits',
        'baseline close','owned bounded entry and METADATA leases','same legacy registry two splits',
        'byte equality and execution receipts','close and source/process postcheck'],
    optimization='all original stable-reader calls/observations; cap+1 allocation replaced by observed size+1 for the exact canonical caller',
    boundary='Windows CPython configured entry; additional caller-frame audit events; no audit-hook transparency, no cross-call source/result cache',
    stop='first error or cap; preserve failure; no unchanged retry or resource extension',
    order_effects='one fixed-order observation, no randomized speedup or full-chain runtime inference',
    full_hour0_chain_passed=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
out=HERE/'bounded_registry_plan_01.json'
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(),source_files=len(sources),code_files=len(code))))
