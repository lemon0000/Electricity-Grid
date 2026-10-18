"""Bounded exact-code allowlist comparison; no model or solver execution."""
from contextlib import ExitStack
from hashlib import sha256
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PACKAGE = HERE.parent/'validation_path_optimization_01/entry_revision_06'
VENDOR = Path('D:/Miniconda3/envs/compute/Lib/site-packages/pyomo')
VENDOR_NAMES = ('solvers/plugins/solvers/GUROBI.py','solvers/plugins/solvers/gurobi_direct.py',
    'solvers/plugins/solvers/direct_solver.py','solvers/plugins/solvers/direct_or_persistent_solver.py',
    'opt/results/results_.py','opt/results/solution.py','opt/results/solver.py')


def digest(path): return sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())
def save(path, value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2)


def worker(mode, root):
    assert mode in ('baseline','vendor7') and not root.exists()
    root.mkdir()
    assert digest(PACKAGE/'package_manifest_v1.json') == '6c0db76dd3bbcfb8281e69d7ad70cc18caaf7adef4d120c0aebb30bbcedef03d'
    members = read(PACKAGE/'package_manifest_v1.json')['files_sha256']
    assert all(digest(PACKAGE/name) == pin for name,pin in members.items())
    sys.path[:] = read(PACKAGE/'interpreter_path_policy_v1.json')['configured_paths']
    package = ModuleType('performance');package.__path__=[str(PACKAGE)]
    sys.modules['performance'] = package
    loaded = {}
    for filename in ('code_read_lease.py','metadata_parse_lease.py'):
        name = 'performance.'+filename[:-3]
        module = ModuleType(name);module.__file__=str(PACKAGE/filename)
        sys.modules[name]=module
        exec(compile((PACKAGE/filename).read_bytes(),module.__file__,'exec'),module.__dict__)
        loaded[filename] = module
    from src.solvers import rq2_gurobi_declared_normal as adapter
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_replay as parent
    from experiments import h1_bootstrap_integration_development_v2 as bootstrap
    actual_vendor = (adapter.GUROBI,adapter.gurobi_direct,adapter.direct_solver,
        adapter.direct_or_persistent_solver,adapter.results_,adapter.solution,adapter.solver_results)
    assert {Path(m.__file__) for m in actual_vendor} == {VENDOR/name for name in VENDOR_NAMES}
    repo_pins = {Path(name):pin for name,pin in read(PACKAGE/'code_allowlist_v3.json')['files_sha256'].items()}
    vendor_pins = {VENDOR/name:digest(VENDOR/name) for name in VENDOR_NAMES}
    metadata_pins = {Path(name):pin for name,pin in read(PACKAGE/'metadata_allowlist_v1.json')['files_sha256'].items()}
    assert len(repo_pins) == 149 and len(vendor_pins) == 7 and not (repo_pins.keys() & vendor_pins.keys())
    expected = {**repo_pins,**(vendor_pins if mode == 'vendor7' else {})}
    all_pins = {**repo_pins,**vendor_pins,**metadata_pins,
        Path(__file__).resolve():digest(Path(__file__)),
        **{PACKAGE/name:pin for name,pin in members.items()},
        PACKAGE/'package_manifest_v1.json':digest(PACKAGE/'package_manifest_v1.json')}
    assert all(digest(path) == pin for path,pin in all_pins.items())
    tested = root/'tested_bytes'
    for path in all_pins:
        if path.is_relative_to(REPO):
            target = tested/'repository'/path.relative_to(REPO)
        else:
            assert path.drive in ('C:','D:')
            target = tested/'external'/path.drive[:1]/Path(*path.parts[1:])
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(path.read_bytes())
    save(root/'request.json',dict(mode=mode,cache_files=len(expected),
        cache_scope='exact149 repo' if mode == 'baseline' else 'exact149 repo plus7 vendor; all other read_bytes calls fallback',
        code_root=str(REPO if mode == 'baseline' else Path('D:/')),
        files_sha256={str(path):pin for path,pin in all_pins.items()},
        real_native_calls=0,formal_result=False,resource_admission=False))
    version_fn,distribution_fn = metadata.version,metadata.distribution
    targets = dict(adapter=(adapter.implementation_identity,32),
        parent=(parent.implementation_identity,8),bootstrap=(bootstrap.implementation_identity,1))
    original_functions = {name:(fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__) for name,(fn,_) in targets.items()}
    denied_calls = []
    def denied(*args, **kwargs):
        denied_calls.append(True)
        raise AssertionError('identity-only diagnostic attempted model/solver execution')
    endpoints = ((type(adapter.SolverFactory),'__call__'),(adapter,'create_solver'),
        (parent.native,'run_h1_chain'),(parent.native.capture,'solve_once'),
        (parent.current,'solve_current'))
    originals = [(owner,name,getattr(owner,name)) for owner,name in endpoints]
    results = {}
    setup_start = time.perf_counter()
    with ExitStack() as stack:
        for owner,name,function in originals:
            setattr(owner,name,denied)
            stack.callback(setattr,owner,name,function)
        lease = stack.enter_context(loaded['code_read_lease.py'].CodeReadLease(
            expected,root=REPO if mode == 'baseline' else Path('D:/')))
        parsed = stack.enter_context(loaded['metadata_parse_lease.py'].MetadataParseLease(metadata_pins))
        setup_seconds = time.perf_counter()-setup_start
        assert sys.getprofile() is None
        for name,(function,iterations) in targets.items():
            expected_identity = function()
            counts = dict(version=0,distribution=0,adapter_identity=0)
            codes = {version_fn.__code__:'version',distribution_fn.__code__:'distribution',
                adapter.implementation_identity.__code__:'adapter_identity'}
            def count(frame,event,arg):
                if event == 'call':
                    key = codes.get(frame.f_code)
                    if key is not None:counts[key] += 1
            try:
                sys.setprofile(count)
                assert function() == expected_identity
            finally:
                sys.setprofile(None)
            start = time.perf_counter()
            for _ in range(iterations):
                assert function() == expected_identity
            results[name] = dict(identity=expected_identity,iterations=iterations,
                unprofiled_seconds=time.perf_counter()-start,
                separate_single_call_profile_counts=counts)
        # root=D:/ never turns non-allowlisted reads into cached reads.
        fallback = root/'mutable_unlisted_probe.py'
        fallback.write_bytes(b'first')
        assert fallback.read_bytes() == b'first'
        fallback.write_bytes(b'second')
        assert fallback.read_bytes() == b'second'
        receipt = lease.receipt()
        assert set(receipt['files_sha256']) == {str(path) for path in expected}
        assert receipt['file_count'] == (149 if mode == 'baseline' else 156)
        vendor_hits = {str(path):receipt['hits_by_path'].get(os.path.normcase(str(path)),0) for path in vendor_pins}
        assert all(value > 0 for value in vendor_hits.values()) if mode == 'vendor7' else not any(vendor_hits.values())
        metadata_receipt = parsed.receipt()
    assert not denied_calls and sys.getprofile() is None
    assert metadata.version is version_fn and metadata.distribution is distribution_fn
    for name,(function,code,defaults,keywords) in original_functions.items():
        assert targets[name][0] is function and function.__code__ is code
        assert function.__defaults__ is defaults and function.__kwdefaults__ is keywords
    assert all(digest(path) == pin for path,pin in all_pins.items())
    origins = {m.__name__:str(Path(m.__file__)) for m in actual_vendor}
    result = dict(mode=mode,targets=results,lease_setup_seconds=setup_seconds,
        vendor_hits=vendor_hits,vendor_module_origins=origins,code_lease_receipt=receipt,
        metadata_receipt=metadata_receipt,source_unchanged=True,
        original_identity_functions_unchanged=True,stock_metadata_functions_unchanged=True,
        unlisted_mutable_file_fallback_observed=True,real_native_calls=0,
        full_chain_speedup_measured=False,formal_result=False,resource_admission=False)
    save(root/'result.json',result)


if len(sys.argv) == 4 and sys.argv[1] == '--worker':
    worker(sys.argv[2],Path(sys.argv[3]))
    raise SystemExit(0)
assert len(sys.argv) == 1
import psutil
out = HERE/'vendor_code_identity_pair_01'
out.mkdir(exist_ok=False)
plan = dict(question='Do seven exact immutable vendor code files reduce the observed solver identity fallback cost?',
    modes=['baseline','vendor7','vendor7','baseline'],attempts_per_mode=2,
    targets=dict(adapter=32,parent=8,bootstrap=1),
    per_child_wall_seconds=45,aggregate_sampled_rss_cap_bytes=512*1024**2,
    storage_cap_bytes=64*1024**2,maximum_concurrency=1,
    profiled_counts='one separate untimed call per target; timed loops have no profiler',
    unchanged_core='original CodeReadLease bytes; same stock metadata parsing lease and discovery; only cache file set/root differ',
    stop='first failed/capped worker stops whole pair; preserve all bytes; no retry',
    source_sha256=digest(Path(__file__)),formal_result=False,resource_admission=False,
    real_native_calls=0,full_chain_launch_admitted=False)
save(out/'plan.json',plan)
rows=[];peak=0;status=0
for index,mode in enumerate(plan['modes']):
    root = out/(str(index)+'_'+mode+'_non_authoritative')
    log_path = out/(str(index)+'_'+mode+'.log')
    command=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--worker',mode,str(root)]
    started=time.monotonic();reason=None
    with log_path.open('x',encoding='utf-8') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        observed=psutil.Process(process.pid);creation=observed.create_time()
        try:
            while process.poll() is None:
                try:rss=observed.memory_info().rss+psutil.Process().memory_info().rss
                except psutil.NoSuchProcess:rss=0
                peak=max(peak,rss)
                size=sum(path.stat().st_size for path in out.rglob('*') if path.is_file())
                elapsed=time.monotonic()-started
                if elapsed>45 or rss>512*1024**2 or size>64*1024**2:
                    reason='wall' if elapsed>45 else 'rss' if rss>512*1024**2 else 'storage'
                    process.kill();break
                time.sleep(.05)
        finally:
            if process.poll() is None:process.kill()
            code=process.wait(timeout=3)
    try:
        current=psutil.Process(process.pid)
        assert current.create_time()!=creation or not current.is_running()
    except psutil.NoSuchProcess:pass
    row=dict(mode=mode,pid=process.pid,creation_time=creation,exit_code=code,
        stop_reason=reason,elapsed_seconds=time.monotonic()-started,observed_direct_pid_absent=True,
        result=read(root/'result.json') if (root/'result.json').exists() else None)
    rows.append(row);save(out/(str(index)+'_'+mode+'_terminal.json'),row)
    if code or reason is not None:
        status=1;break
if not status:
    baseline=rows[0]['result']
    for row in rows:
        result=row['result']
        assert result['vendor_module_origins']==baseline['vendor_module_origins']
        for name in baseline['targets']:
            assert result['targets'][name]['identity']==baseline['targets'][name]['identity']
            assert result['targets'][name]['separate_single_call_profile_counts']==baseline['targets'][name]['separate_single_call_profile_counts']
summary=dict(exit_code=status,rows=rows,peak_sampled_rss_including_monitor=peak,
    planned_workers=4,completed_workers=len(rows),full_chain_speedup_measured=False,
    formal_result=False,resource_admission=False,real_native_calls=0)
save(out/'terminal.json',summary)
print(json.dumps(dict(exit_code=status,completed_workers=len(rows),
    modes=[dict(mode=row['mode'],exit_code=row['exit_code'],elapsed_seconds=row['elapsed_seconds'],
        targets=row['result']['targets'] if row['result'] else None) for row in rows])),flush=True)
raise SystemExit(status)
