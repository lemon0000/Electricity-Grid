"""Fixed cold synthetic N0 entry; no native solver or formal authority."""
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
plan_name,plan_pin=sys.argv[1:]
if Path(plan_name).name!=plan_name or not plan_name.endswith('.json'):raise ValueError('one local plan filename required')
plan_path=HERE/plan_name;plan_raw=plan_path.read_bytes()
if sha256(plan_raw).hexdigest()!=plan_pin:raise ValueError('fixed cold diagnostic plan differs')
plan=json.loads(plan_raw);OUT=Path(plan['inner_output']);OUT.mkdir(exist_ok=False)
sources=plan['source_sha256']
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
def load(name,path):
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=sources[str(path)]:raise ValueError('fixed entry member differs')
    module=ModuleType(name);module.__file__=str(path);module.__package__=name.rpartition('.')[0]
    sys.modules[name]=module;exec(compile(raw,str(path),'exec'),vars(module));return module
if not sys.flags.isolated or not sys.dont_write_bytecode:raise ValueError('fixed -I -B required')
sys.pycache_prefix=str(OUT/'empty_pycache');Path(sys.pycache_prefix).mkdir()
result=dict(formal_result=False,resource_admission=False,full_hour0_chain_passed=False,
    native_execution_authorized=False,source_identity_shortcut=False);start=perf_counter();policy=None
try:
    for path,pin in sources.items():
        if sha256(Path(path).read_bytes()).hexdigest()!=pin:raise ValueError('input closure differs: '+path)
    save('request.json',plan)
    package=ModuleType('performance');package.__path__=[str(ENTRY)];sys.modules['performance']=package
    code=load('performance.code_read_lease',ENTRY/'code_read_lease.py')
    metadata=load('performance.metadata_parse_lease',ENTRY/'metadata_parse_lease.py')
    policy=load('performance.interpreter_path_policy',ENTRY/'interpreter_path_policy.py').InterpreterPathPolicy(
        json.loads((ENTRY/'interpreter_path_policy_v1.json').read_bytes()))
    policy.configure()
    vendor=load('performance.vendor_code_policy',ENTRY/'vendor_code_policy.py');vendor.assert_unloaded(sys.modules)
    bounded=load('performance.bounded_stable_read_entry',HERE/'bounded_stable_read_entry_v2.py')
    expected={Path(k):v for k,v in plan['code_lease_sha256'].items()}
    metadata_expected={Path(k):v for k,v in json.loads((ENTRY/'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}
    with ExitStack() as stack:
        lease=stack.enter_context(bounded.BoundedStableReadLease(expected,root=Path('D:/')))
        assert 'experiments.h1_canonical_path_lease_development_v1' not in sys.modules
        assert 'src.rq2_joint_deliverability_boundary_v1.episode_store' not in sys.modules
        paths=load('experiments.h1_canonical_path_lease_development_v1',ENTRY/'canonical_path_lease.py')
        from src.rq2_joint_deliverability_boundary_v1 import episode_store
        original_path=episode_store._path
        roots=[REPO,Path(plan['basetemp'])]
        assert [str(p) for p in roots]==plan['path_roots']
        path_lease=stack.enter_context(paths.CanonicalPathLease(episode_store,roots))
        parsed=stack.enter_context(metadata.MetadataParseLease(metadata_expected))
        import pytest
        admission=load('performance.pytest_admission_plugin',ENTRY/'pytest_admission_plugin.py').AdmissionPlugin(policy)
        class Windows:
            @pytest.hookimpl(tryfirst=True)
            def pytest_runtest_setup(self,item):parsed.begin_discovery_window()
            @pytest.hookimpl(tryfirst=True)
            def pytest_runtest_call(self,item):parsed.begin_discovery_window()
        previous=os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD');os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
        try:
            observer=load('performance.gil_stack_observer',REPO/'tests/h1_gil_stack_observer_development_v1.py')
            with observer.observe_owner_stack(OUT/'dense_stack_samples.jsonl',interval_seconds=1.,
                    max_samples=1024,max_frames=128,max_bytes=16*1024**2) as observed:
                status=pytest.main(['-q','-s','-p','no:cacheprovider','-p','no:faulthandler',
                    '--import-mode=importlib','--basetemp',plan['basetemp'],plan['target']],plugins=[admission,Windows()])
            save('dense_stack_observer_receipt.json',observed)
        finally:
            if previous is None:os.environ.pop('PYTEST_DISABLE_PLUGIN_AUTOLOAD',None)
            else:os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']=previous
            policy.end_pytest()
        save('path_receipt.json',path_lease.receipt())
        execution=lease.receipt();save('bounded_read_receipt.json',execution)
        save('code_receipt.json',execution['code_lease']);save('metadata_receipt.json',parsed.receipt())
        result['exit_code']=int(status)
    path_closed=dict(dispatch_restored=episode_store._path is original_path,
        remaining_directory_handles=len(path_lease._directories),remaining_paths=len(path_lease._paths),state=path_lease._state)
    save('path_closed_receipt.json',path_closed)
    assert path_closed==dict(dispatch_restored=True,remaining_directory_handles=0,remaining_paths=0,state='closed')
    closed=lease.closed_receipt()
    assert closed['code_owner_closed'] and closed['path_open_restored'] and closed['path_read_bytes_restored']
    assert closed['remaining_code_handles']==closed['remaining_streams']==closed['remaining_proxies']==0
    assert not closed['cleanup_errors'] and closed['first_failure'] is None
    save('bounded_closed_receipt.json',closed)
    for source in expected:
        with source.open('r+b'):pass
    result['code_paths_reopened_for_write_without_writing']=len(expected)
    save('interpreter_receipt.json',policy.receipt())
    result['vendor_module_origins']=vendor.origins(sys.modules,required=True)
except BaseException:result.update(exit_code=1,error=traceback.format_exc())
finally:
    drift=[p for p,h in sources.items() if not Path(p).is_file() or sha256(Path(p).read_bytes()).hexdigest()!=h]
    result.update(source_unchanged=not drift,source_drift=drift,elapsed_seconds=perf_counter()-start)
    if drift:result['exit_code']=1
    save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
