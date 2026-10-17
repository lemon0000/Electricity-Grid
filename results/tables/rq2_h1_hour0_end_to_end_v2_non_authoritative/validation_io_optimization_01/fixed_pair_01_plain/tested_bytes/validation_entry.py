"""Pinned-byte entry for bounded, zero-native synthetic validation only."""
from contextlib import ExitStack
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


HERE=Path(__file__).resolve().parent
REPO=Path('D:/CUHKSZ/Research Project/electricity-grid')
E=REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative'
kind,mode,label,*targets=sys.argv[1:]
assert kind in ('arm','phase','unit','pytest') and mode in ('plain','leased','parse')
assert re.fullmatch(r'[a-zA-Z0-9_]+',label)
out=HERE/label;out.mkdir(exist_ok=False)
prefix=out/'empty_pycache';prefix.mkdir()
previous_prefix=sys.pycache_prefix;previous_bytecode=sys.dont_write_bytecode
sys.pycache_prefix=str(prefix);sys.dont_write_bytecode=True
sources=_pinned_sources  # Supplied only by the fixed-hash outer launcher.
code_pins={str(HERE/name):sha256(raw).hexdigest() for name,raw in sources.items()}
tested=out/'tested_bytes';tested.mkdir()
for name,raw in sources.items():(tested/name).write_bytes(raw)


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


package=ModuleType('performance');package.__path__=[str(HERE)]
sys.modules['performance']=package
CodeReadLease=load_module('performance.code_read_lease','code_read_lease.py').CodeReadLease
MetadataParseLease=load_module('performance.metadata_parse_lease','metadata_parse_lease.py').MetadataParseLease
expected=unique_paths(json.loads(sources['code_allowlist_v3.json'])['files_sha256'])
metadata_expected=unique_paths(json.loads(sources['metadata_allowlist_v1.json'])['files_sha256'])
sys.path[:0]=[str(REPO),str(REPO/'tests')]
save('request.json',dict(kind=kind,mode=mode,targets=targets,candidate_sha256=code_pins,
    launcher_sha256=_launcher_sha256,package_manifest_sha256=_manifest_sha256,
    imported_candidate_bytes='compiled from verified tested_bytes, no pyc import',
    pycache_prefix=str(prefix),pycache_prefix_initially_empty=not any(prefix.iterdir()),
    dont_write_bytecode=sys.dont_write_bytecode,formal_result=False))
start=perf_counter();result=dict(kind=kind,mode=mode,formal_result=False,full_chain_passed=False)


def lease_context(stack):
    code=stack.enter_context(CodeReadLease(expected,root=REPO)) if mode!='plain' else None
    parsed=stack.enter_context(MetadataParseLease(metadata_expected)) if mode=='parse' else None
    return code,parsed


def receipts(code,parsed,name=''):
    if code:save(name+'lease_receipt.json',code.receipt())
    if parsed:save(name+'metadata_receipt.json',parsed.receipt())


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
    for filename in ('test_code_read_lease.py','test_metadata_parse_lease.py'):
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
    }
    if not targets or any(t not in allowed for t in targets):
        raise ValueError('explicit zero-native synthetic test allowlist required')
    import pytest
    class Plugin:
        @pytest.hookimpl(hookwrapper=True,tryfirst=True)
        def pytest_runtest_call(self,item):
            name=sha256(item.nodeid.encode()).hexdigest()[:16]+'_'
            with ExitStack() as stack:
                code,parsed=lease_context(stack)
                yield
                receipts(code,parsed,name)
    basetemp=out/'pytest_temp_non_authoritative'
    result['pytest_basetemp']=str(basetemp)
    return int(pytest.main(['-q','-s','-p','no:cacheprovider','--basetemp',str(basetemp),*targets],plugins=[Plugin()]))


previous_cwd=Path.cwd()
try:
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
    after={str(p):sha256(Path(p).read_bytes()).hexdigest() for p in code_pins}
    result['candidate_sha256_after']=after
    result['candidate_bytes_unchanged']=after==code_pins
    result['interpreter_settings_restored']=(sys.pycache_prefix==previous_prefix and sys.dont_write_bytecode==previous_bytecode)
    if after!=code_pins:result.update(exit_code=1,error='candidate code changed during measurement')
    result['elapsed_seconds']=perf_counter()-start
    save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
