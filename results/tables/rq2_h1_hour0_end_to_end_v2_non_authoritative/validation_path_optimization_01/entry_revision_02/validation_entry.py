"""Pinned-byte entry for bounded, zero-native synthetic validation only."""
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from time import perf_counter
import traceback
from types import ModuleType
from collections import Counter


HERE=Path(__file__).resolve().parent
REPO=Path('D:/CUHKSZ/Research Project/electricity-grid')
E=REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative'
kind,mode,label,*targets=sys.argv[1:]
assert kind in ('arm','phase','unit','pytest') and mode in ('plain','leased','parse','parse_path')
if mode=='parse_path' and kind!='pytest':raise ValueError('path successor currently bounded to pytest integration')
assert re.fullmatch(r'[a-zA-Z0-9_]+',label)
out=HERE/label;out.mkdir(exist_ok=False)
prefix=out/'empty_pycache'
previous_prefix=sys.pycache_prefix;previous_bytecode=sys.dont_write_bytecode
sources=_pinned_sources  # Supplied only by the fixed-hash outer launcher.
code_pins={str(HERE/name):sha256(raw).hexdigest() for name,raw in {**sources,**_bootstrap_sources}.items()}


def save(name,value):
    with (out/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)


def load_module(name,filename):
    module=ModuleType(name);module.__file__=str(HERE/filename)
    module.__package__=name.rpartition('.')[0];sys.modules[name]=module
    exec(compile(sources[filename],module.__file__,'exec'),module.__dict__)
    return module


def unique_paths(declaration):
    keys=[os.path.normcase(os.path.normpath(p)) for p in declaration]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate canonical allowlist path')
    return {Path(name):pin for name,pin in declaration.items()}


def no_duplicate_keys(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('duplicate JSON key')
        value[key]=item
    return value


def initialize():
    global CodeReadLease,MetadataParseLease,CanonicalPathLease,path_lease,expected,metadata_expected,repository_pins,repository_code_pins
    prefix.mkdir();sys.pycache_prefix=str(prefix);sys.dont_write_bytecode=True
    tested=out/'tested_bytes';tested.mkdir()
    for name,raw in {**sources,**_bootstrap_sources}.items():(tested/name).write_bytes(raw)
    save('request.json',dict(kind=kind,mode=mode,targets=targets,candidate_sha256=code_pins,
        launcher_sha256=_launcher_sha256,package_manifest_sha256=_manifest_sha256,
        imported_candidate_bytes='compiled from verified tested_bytes, no pyc import',
        pycache_prefix=str(prefix),pycache_prefix_initially_empty=not any(prefix.iterdir()),
        dont_write_bytecode=sys.dont_write_bytecode,formal_result=False))
    package=ModuleType('performance');package.__path__=[str(HERE)]
    sys.modules['performance']=package
    CodeReadLease=load_module('performance.code_read_lease','code_read_lease.py').CodeReadLease
    MetadataParseLease=load_module('performance.metadata_parse_lease','metadata_parse_lease.py').MetadataParseLease
    path_lease=None
    expected=unique_paths(json.loads(sources['code_allowlist_v3.json'],object_pairs_hook=no_duplicate_keys)['files_sha256'])
    metadata_expected=unique_paths(json.loads(sources['metadata_allowlist_v1.json'],object_pairs_hook=no_duplicate_keys)['files_sha256'])
    for path,pin in expected.items():
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=pin:raise ValueError('repository source pin differs: '+str(path))
        relative=path.relative_to(REPO);destination=tested/'repository_code'/relative
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
        repository_code_pins[str(path)]=pin
    declaration=json.loads(sources['test_closure_v1.json'],object_pairs_hook=no_duplicate_keys)['files_sha256']
    unique_paths({str(REPO/Path(name)):pin for name,pin in declaration.items()})
    repository_pins={}
    for name,pin in declaration.items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('relative repository closure required')
        path=REPO/relative;raw=path.read_bytes()
        if sha256(raw).hexdigest()!=pin:raise ValueError('test closure pin differs: '+name)
        destination=tested/'repository'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(raw);repository_pins[str(path)]=pin
    sys.path[:0]=[str(REPO),str(REPO/'tests')]
    # Validate and snapshot the repository closure before importing episode_store.
    CanonicalPathLease=load_module('experiments.h1_canonical_path_lease_development_v1','canonical_path_lease.py').CanonicalPathLease


start=perf_counter();result=dict(kind=kind,mode=mode,formal_result=False,full_chain_passed=False)


def lease_context(stack):
    global path_lease
    code=stack.enter_context(CodeReadLease(expected,root=REPO)) if mode!='plain' else None
    if mode=='parse_path':
        from src.rq2_joint_deliverability_boundary_v1 import episode_store
        path_lease=stack.enter_context(CanonicalPathLease(episode_store,[REPO]))
    parsed=stack.enter_context(MetadataParseLease(metadata_expected)) if mode in ('parse','parse_path') else None
    return code,parsed


def receipts(code,parsed,name='',nodeid=None):
    if code:save(name+'lease_receipt.json',dict(code.receipt(),test_nodeid=nodeid))
    if parsed:save(name+'metadata_receipt.json',dict(parsed.receipt(),test_nodeid=nodeid))
    if path_lease:save(name+'path_receipt.json',dict(path_lease.receipt(),test_nodeid=nodeid))


def saved_arm():
    # Load the fixture before taking the metadata discovery-environment snapshot.
    spec=importlib.util.spec_from_file_location('pair_fixture',E/'replay_saved_with_fixture_v1.py')
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    from experiments import h1_selector_input_snapshot_development_v2 as snapshot
    common=snapshot.common.common;saved=Path('D:/h1_chain_06_non_authoritative')
    header=json.loads(next(saved.glob('nt_non_authoritative/common_owners_non_authoritative/*/header.json')).read_bytes())['declaration']
    base=saved/'test_complete_independent_N0_r0'
    packet=json.loads((base/'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json').read_bytes())
    d=packet['declaration'];manifest,binding,configuration=snapshot._declarations(d['manifest'],d['source_binding'],d['run_configuration'])
    report=header['initial_report'];arm=report['canonical_arm']
    before={str(p):sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
    patch=fixture.complete_fixture(fixture.saved.synthetic_source)(base)
    try:
        with ExitStack() as stack:
            code,parsed=lease_context(stack);begin=perf_counter()
            if kind=='phase':
                fingerprint=common.bootstrap._phase_input_fingerprint(configuration)
                result['phase_seconds']=perf_counter()-begin;save('scientific.json',fingerprint)
                result['validation_scope']='static phase-input fingerprint only; no numerical replay'
            else:
                produced=common._arm(report['arm_audits'][arm]['reference'],binding.registry_identity,manifest)
                result['arm_seconds']=perf_counter()-begin
                assert common.encode(produced[1])==common.encode(report['common_scientific_payload'])
                audit=json.loads(common.encode(produced[2]));prior=json.loads(common.encode(report['arm_audits'][arm]))
                audit.pop('verification_execution',None)
                audit['exact_current_audit'].pop('implementation_identity')
                prior['exact_current_audit'].pop('implementation_identity')
                assert common.encode(audit)==common.encode(prior)
                save('scientific.json',produced[1]);save('audit.json',produced[2])
                result['scientific_payload_and_projected_audit_equal_saved']=True
                result['validation_scope']='original common._arm; original numerical and fresh source checks'
            receipts(code,parsed)
    finally:patch.undo()
    after={str(p):sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
    assert before==after
    result.update(saved_files_unchanged=True,saved_file_count=len(before),real_native_calls=0)


def unit_tests():
    import unittest
    suite=unittest.TestSuite()
    load_module('performance.pytest_lease_plugin','pytest_lease_plugin.py')
    for filename in ('test_code_read_lease.py','test_metadata_parse_lease.py','test_validation_entry.py','test_pytest_lease_plugin.py'):
        module=load_module('performance.'+filename[:-3],filename)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    with (out/'unittest.log').open('x',encoding='utf-8') as log:
        run=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    result.update(tests_run=run.testsRun,skipped=len(run.skipped),failures=len(run.failures),errors=len(run.errors))
    return 0 if run.wasSuccessful() else 1


def pytest_tests():
    allowed={
        'tests/test_h1_phase_exact_source_current_development_v2.py',
        'tests/test_h1_common_source_bundle_v2.py',
        'tests/test_h1_hour0_routing_development_v2.py',
        'tests/test_h1_hour0_end_to_end_development_v2.py',
        'tests/test_h1_hour0_three_actual_preflight_v2.py',
    }
    if not targets or any(t not in allowed for t in targets):
        raise ValueError('explicit zero-native synthetic test allowlist required')
    basetemp=out/'pytest_temp_non_authoritative'
    result['pytest_basetemp']=str(basetemp)
    result['pytest_lease_lifetime']='whole invocation including collection, fixtures, calls and teardown'
    previous_timing=os.environ.get('H1_E2E_TIMING_FILE')
    previous_profile=sys.getprofile()
    if previous_profile is not None:raise ValueError('unambiguous bounded call-counter profile required')
    call_counts=Counter()
    counted_names={'h1_selector_phase_handoff_development_v2.py',
        'h1_selector_parent_controller_development_v2.py',
        'h1_common_owner_genesis_development_v2.py',
        'h1_group_n0_common_input_binding_development_v2.py'}
    counted_files={os.path.normcase(str(REPO/'experiments'/name)) for name in counted_names}
    def count_calls(frame,event,arg):
        if event=='call':
            name=os.path.normcase(frame.f_code.co_filename)
            if name in counted_files:
                call_counts[(name,frame.f_code.co_name,frame.f_code.co_firstlineno)]+=1
    try:
        os.environ['H1_E2E_TIMING_FILE']=str(out/'timing.jsonl')
        with ExitStack() as stack:
            code,parsed=lease_context(stack)
            import pytest
            Plugin=load_module('performance.pytest_lease_plugin','pytest_lease_plugin.py').LeasePlugin
            def window(unused_stack):
                if parsed:parsed.begin_discovery_window()
                return code,parsed
            with (out/'pytest.log').open('x',encoding='utf-8') as log,redirect_stdout(log),redirect_stderr(log):
                try:
                    status=int(pytest.main(['-q','-s','-p','no:cacheprovider','--basetemp',str(basetemp),*targets],
                        plugins=[Plugin(window,receipts,result)]))
                finally:sys.setprofile(previous_profile)
            receipts(code,parsed,'session_')
        return status
    finally:
        sys.setprofile(previous_profile)
        save('call_counts.json',dict(rows=[dict(file=f,function=n,line=l,calls=count)
            for (f,n,l),count in sorted(call_counts.items())],
            scope='counter disabled; per-stage logs retained; parent current thread only if enabled in a successor',
            profiler_restored=sys.getprofile() is previous_profile,formal_result=False))
        if previous_timing is None:os.environ.pop('H1_E2E_TIMING_FILE',None)
        else:os.environ['H1_E2E_TIMING_FILE']=previous_timing


previous_cwd=Path.cwd()
previous_path=list(sys.path)
repository_pins={}
repository_code_pins={}
try:
    initialize()
    os.chdir(REPO)
    for path,pin in expected.items():
        if sha256(path.read_bytes()).hexdigest()!=pin:raise ValueError('repository source pin changed')
    if kind in ('arm','phase'):saved_arm();result['exit_code']=0
    elif kind=='unit':result['exit_code']=unit_tests()
    else:result['exit_code']=pytest_tests()
except BaseException:
    result.update(exit_code=1,error=traceback.format_exc())
finally:
    sys.pycache_prefix=previous_prefix;sys.dont_write_bytecode=previous_bytecode;os.chdir(previous_cwd)
    sys.path[:]=previous_path
    after={};pin_errors={}
    for path in code_pins:
        try:after[path]=sha256(Path(path).read_bytes()).hexdigest()
        except BaseException as error:pin_errors[path]=repr(error)
    result['candidate_sha256_after']=after
    result['candidate_pin_read_errors']=pin_errors
    repository_after={};repository_errors={}
    for path in repository_pins:
        try:repository_after[path]=sha256(Path(path).read_bytes()).hexdigest()
        except BaseException as error:repository_errors[path]=repr(error)
    save('repository_pins_after.json',dict(files_sha256=repository_after,read_errors=repository_errors))
    result['repository_test_closure_file_count']=len(repository_pins)
    result['repository_test_closure_unchanged']=repository_after==repository_pins and not repository_errors
    code_after={};code_errors={}
    for path in repository_code_pins:
        try:code_after[path]=sha256(Path(path).read_bytes()).hexdigest()
        except BaseException as error:code_errors[path]=repr(error)
    save('repository_code_pins_after.json',dict(files_sha256=code_after,read_errors=code_errors))
    result['repository_code_file_count']=len(repository_code_pins)
    result['repository_code_unchanged']=code_after==repository_code_pins and not code_errors
    result['candidate_bytes_unchanged']=after==code_pins
    result['interpreter_settings_restored']=(sys.pycache_prefix==previous_prefix
        and sys.dont_write_bytecode==previous_bytecode and sys.path==previous_path and Path.cwd()==previous_cwd)
    if after!=code_pins:result.update(exit_code=1,error='candidate code changed during measurement')
    if repository_after!=repository_pins or repository_errors:
        result.update(exit_code=1,error='repository test closure changed during measurement')
    if code_after!=repository_code_pins or code_errors:
        result.update(exit_code=1,error='repository code changed during measurement')
    result['elapsed_seconds']=perf_counter()-start
    save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
