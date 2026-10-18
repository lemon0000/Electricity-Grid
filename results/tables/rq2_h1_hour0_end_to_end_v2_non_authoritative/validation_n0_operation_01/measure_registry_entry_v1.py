"""Fixed two-split allocation comparison through the genuine configured entry."""
from contextlib import ExitStack
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import traceback
from types import ModuleType
from time import perf_counter

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
ENTRY=HERE.parent/'validation_path_optimization_01/entry_revision_07'
plan_pin,*unused=sys.argv[1:];raw_plan=(HERE/'bounded_registry_plan_01.json').read_bytes()
if sha256(raw_plan).hexdigest()!=plan_pin:raise ValueError('fixed bounded registry diagnostic plan differs')
plan=json.loads(raw_plan);OUT=Path(plan['output']);OUT.mkdir(exist_ok=False)
sys.pycache_prefix=str(OUT/'empty_pycache');Path(sys.pycache_prefix).mkdir()
sources=plan['source_sha256'];policy=None;start=perf_counter()
result=dict(exit_code=1,formal_result=False,resource_admission=False,full_hour0_chain_passed=False,
    native_execution_authorized=False)
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
def load(name,path):
    value=path.read_bytes()
    if sha256(value).hexdigest()!=sources[str(path)]:raise ValueError('fixed entry member differs')
    module=ModuleType(name);module.__file__=str(path);module.__package__=name.rpartition('.')[0]
    sys.modules[name]=module;exec(compile(value,str(path),'exec'),vars(module));return module
try:
    if not sys.flags.isolated or not sys.dont_write_bytecode:raise ValueError('fixed -I -B required')
    for path,pin in {**sources,**plan['old_chain_sha256']}.items():
        if sha256(Path(path).read_bytes()).hexdigest()!=pin:raise ValueError('fixed diagnostic source differs')
    save('request.json',plan)
    package=ModuleType('performance');package.__path__=[str(ENTRY)];sys.modules['performance']=package
    code=load('performance.code_read_lease',ENTRY/'code_read_lease.py')
    metadata=load('performance.metadata_parse_lease',ENTRY/'metadata_parse_lease.py')
    policy=load('performance.interpreter_path_policy',ENTRY/'interpreter_path_policy.py').InterpreterPathPolicy(
        json.loads((ENTRY/'interpreter_path_policy_v1.json').read_bytes()))
    policy.configure()
    vendor=load('performance.vendor_code_policy',ENTRY/'vendor_code_policy.py');vendor.assert_unloaded(sys.modules)
    bounded=load('performance.bounded_stable_read_entry',HERE/'bounded_stable_read_entry_v1.py')
    expected={Path(k):v for k,v in plan['code_lease_sha256'].items()}
    metadata_expected={Path(k):v for k,v in json.loads((ENTRY/'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}
    rows=[];basis={}
    for mode in ('predecessor_entry','bounded_entry'):
        with ExitStack() as stack:
            lease=stack.enter_context(code.CodeReadLease(expected,root=Path('D:/')) if mode=='predecessor_entry'
                else bounded.BoundedStableReadLease(expected,root=Path('D:/')))
            parsed=stack.enter_context(metadata.MetadataParseLease(metadata_expected))
            from experiments import h1_registry_declaration_development_v1 as registry
            for split in ('training','holdout'):
                parsed.begin_discovery_window();policy.admit(mode+'_'+split)
                previous=perf_counter();projection=registry.build(split);elapsed=perf_counter()-previous
                if mode=='predecessor_entry':basis[split]=projection
                assert projection==basis[split]==(HERE/'registry_reads_01_non_authoritative'/(split+'_raw.json')).read_bytes()
                (OUT/(mode+'_'+split+'.json')).write_bytes(projection)
                rows.append(dict(mode=mode,split=split,seconds=elapsed,raw_sha256=sha256(projection).hexdigest()))
            save(mode+'_receipt.json',lease.receipt());save(mode+'_metadata.json',parsed.receipt())
        policy.admit(mode+'_closed')
    save('interpreter_receipt.json',policy.receipt())
    result.update(exit_code=0,measurements=rows,all_compatibility_bytes_equal=True,
        vendor_module_origins=vendor.origins(sys.modules,required=False),synthetic_jobs=0,real_native_calls=0)
except BaseException:result.update(error=traceback.format_exc())
finally:
    for name,pins in (('source',sources),('old_chain',plan['old_chain_sha256'])):
        drift=[p for p,h in pins.items() if not Path(p).is_file() or sha256(Path(p).read_bytes()).hexdigest()!=h]
        result[name+'_unchanged']=not drift;result[name+'_drift']=drift
        if drift:result['exit_code']=1
    result['elapsed_seconds']=perf_counter()-start;save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
