"""Cold fixed-byte route definition probe, without a lease or numeric replay.

Private closure inspection invokes only the pinned loader, never Handoff BEGIN,
Parent completion, session construction, source replay or common preparation.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
PACKAGE=HERE.parent/'validation_path_optimization_01/entry_revision_04'
raw=(PACKAGE/'package_manifest_v1.json').read_bytes()
if sha256(raw).hexdigest()!='d13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43':
    raise ValueError('configured predecessor package differs')
for name,pin in json.loads(raw)['files_sha256'].items():
    if sha256((PACKAGE/name).read_bytes()).hexdigest()!=pin:
        raise ValueError('configured predecessor member differs: '+name)
sys.path[:]=json.loads((PACKAGE/'interpreter_path_policy_v1.json').read_bytes())['configured_paths']
if len(sys.argv)!=2:raise ValueError('one unique output JSON path required')
out=Path(sys.argv[1])
if out.exists():raise ValueError('preserve earlier probe evidence')
start=perf_counter()
from experiments import h1_common_validation_operation_development_v1 as bridge
imported=perf_counter()
def cells(function):
    return dict(zip(function.__code__.co_freevars,(cell.cell_contents for cell in function.__closure__)))
loader=cells(bridge.GuardedCommonOperation.__enter__)['load_routes']
sources=cells(bridge.GuardedCommonOperation.__init__)['sources']
routes=loader(sources)
loaded=perf_counter()
w,s,c=(routes['modules'][name] for name in bridge._ROUTE_NAMES)
bridge._RUNTIME()
w._runtime_check(full=True)
s._FIXED(full=True)
c._FIXED(full=True)
finished=perf_counter()
result=dict(status='COLD_DEFINITION_PROBE_ONLY_NONAUTHORITATIVE',
    bridge_import_seconds=imported-start,fixed_route_load_seconds=loaded-imported,
    final_guard_seconds=finished-loaded,total_seconds=finished-start,
    route_sources=[dict(module=n,path=p,sha256=h) for n,p,h in sources],
    all_final_guards_passed=True,lease_issued=False,handoff_token_issued=False,
    historical_numerical_replay=False,actual_common_slice=False,full_chain_passed=False,
    formal_result=False,resource_admission=False,native_execution_authorized=False)
with out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result),flush=True)
