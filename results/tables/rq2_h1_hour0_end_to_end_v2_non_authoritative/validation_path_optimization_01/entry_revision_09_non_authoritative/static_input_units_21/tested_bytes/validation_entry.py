"""Pinned-byte entry for bounded, zero-native synthetic validation only."""
from contextlib import ExitStack,redirect_stdout,redirect_stderr
from hashlib import sha256
import importlib.util
import json
import marshal
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
    global StaticScientificInputReadLease,scientific_expected,CodeReadLease,MetadataParseLease,CanonicalPathLease,path_lease,interpreter_policy,expected,metadata_expected,repository_pins,repository_code_pins,vendor_policy,vendor_expected
    prefix.mkdir();sys.pycache_prefix=str(prefix);sys.dont_write_bytecode=True
    tested=out/'tested_bytes';tested.mkdir()
    for name,raw in {**sources,**_bootstrap_sources}.items():(tested/name).write_bytes(raw)
    save('request.json',dict(kind=kind,mode=mode,targets=targets,candidate_sha256=code_pins,
        launcher_sha256=_launcher_sha256,package_manifest_sha256=_manifest_sha256,
        active_validation_identity=dict(schema='h1_static_scientific_input_entry_draft_v2',
            package_manifest_sha256=_manifest_sha256,
            interpreter_policy_sha256=sha256(sources['interpreter_path_policy_v1.json']).hexdigest(),
            interpreter_helper_sha256=sha256(sources['interpreter_path_policy.py']).hexdigest(),
            static_scientific_input_bytes_cached=True,
            repair_cap_table_bytes_cached=True,
            raw_archive_or_source_rows_cached=False,
            static_input_byte_lease_sha256=sha256(sources['static_scientific_input_read_lease_v2.py']).hexdigest(),
            static_input_allowlist_sha256=sha256(sources['scientific_input_allowlist_v1.json']).hexdigest(),
            scientific_inputs=json.loads(sources['scientific_input_allowlist_v1.json'])['files'],
            stock_metadata_finder_unchanged=True,
            repository_code_manifest_sha256=sha256(sources['code_allowlist_v3.json']).hexdigest(),
            vendor_code_manifest_sha256=sha256(sources['vendor_code_allowlist_v1.json']).hexdigest(),
            repository_code_files=249,vendor_code_files=7,code_lease_files=256,
            code_lease_root='D:/',vendor_origin_manifest=sources['vendor_code_allowlist_v1.json'].decode() ),
        imported_candidate_bytes='compiled from verified tested_bytes, no pyc import',
        pycache_prefix=str(prefix),pycache_prefix_initially_empty=not any(prefix.iterdir()),
        dont_write_bytecode=sys.dont_write_bytecode,formal_result=False))
    package=ModuleType('performance');package.__path__=[str(HERE)]
    sys.modules['performance']=package
    CodeReadLease=load_module('performance.code_read_lease','code_read_lease.py').CodeReadLease
    StaticScientificInputReadLease=load_module('performance.static_scientific_input_read_lease_v2',
        'static_scientific_input_read_lease_v2.py').StaticScientificInputReadLease
    scientific_expected=json.loads(sources['scientific_input_allowlist_v1.json'],object_pairs_hook=no_duplicate_keys)['files']
    if scientific_expected!=sys.modules['performance.static_scientific_input_read_lease_v2'].scientific_inputs(REPO):raise ValueError('exact scientific input allowlist required')
    MetadataParseLease=load_module('performance.metadata_parse_lease','metadata_parse_lease.py').MetadataParseLease
    path_lease=None
    expected=unique_paths(json.loads(sources['code_allowlist_v3.json'],object_pairs_hook=no_duplicate_keys)['files_sha256'])
    metadata_expected=unique_paths(json.loads(sources['metadata_allowlist_v1.json'],object_pairs_hook=no_duplicate_keys)['files_sha256'])
    vendor_policy=load_module('performance.vendor_code_policy','vendor_code_policy.py')
    vendor_policy.assert_unloaded(sys.modules)
    vendor_expected=vendor_policy.vendor_files(sources['code_allowlist_v3.json'],sources['vendor_code_allowlist_v1.json'])
    if len(expected)!=249 or len(vendor_expected)!=7 or expected.keys()&vendor_expected.keys():
        raise ValueError('249 repository plus seven disjoint vendor code files required')
    for path,pin in expected.items():
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=pin:raise ValueError('repository source pin differs: '+str(path))
        relative=path.relative_to(REPO);destination=tested/'repository_code'/relative
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
        repository_code_pins[str(path)]=pin
    for path,pin in vendor_expected.items():
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=pin:raise ValueError('vendor source pin differs: '+str(path))
        destination=tested/'vendor_code/pyomo'/path.relative_to(vendor_policy.VENDOR_ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
        vendor_code_pins[str(path)]=pin
    expected={**expected,**vendor_expected}
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
    policy=json.loads(sources['interpreter_path_policy_v1.json'],object_pairs_hook=no_duplicate_keys)
    Policy=load_module('performance.interpreter_path_policy','interpreter_path_policy.py').InterpreterPathPolicy
    interpreter_policy=Policy(policy)
    interpreter_policy.configure()
    # Validate and snapshot the repository closure before importing episode_store.


start=perf_counter();result=dict(kind=kind,mode=mode,formal_result=False,full_chain_passed=False)


normalization_reader=None
byte_lease=None


def lease_context(stack):
    global path_lease,CanonicalPathLease,normalization_reader,byte_lease
    vendor_policy.assert_unloaded(sys.modules)
    byte_lease=StaticScientificInputReadLease(expected,scientific_expected,root=REPO,code_root=Path('D:/')) if mode!='plain' else None
    code=stack.enter_context(byte_lease) if byte_lease is not None else None
    if mode=='parse_path':
        CanonicalPathLease=load_module('experiments.h1_canonical_path_lease_development_v1','canonical_path_lease.py').CanonicalPathLease
        from src.rq2_joint_deliverability_boundary_v1 import episode_store
        path_lease=stack.enter_context(CanonicalPathLease(episode_store,[REPO,Path('D:/h1_wf09_'+label+'_non_authoritative')]))
    parsed=stack.enter_context(MetadataParseLease(metadata_expected)) if mode in ('parse','parse_path') else None
    from experiments import h1_origin_grid_step_development_v1 as physical
    from experiments import h1_repair_cap_normalization_operation_development_v1 as normalization
    expected_physical=REPO/'experiments/h1_origin_grid_step_development_v1.py'
    if (physical.__name__!='experiments.h1_origin_grid_step_development_v1'
            or Path(physical.__file__)!=expected_physical
            or physical.__spec__.origin!=str(expected_physical)
            or physical.repair_mechanism_identity.__code__.co_filename!=str(expected_physical)):
        raise ValueError('fixed physical normalization provenance required')
    registry=physical.registry
    registry_path=REPO/'experiments/h1_outage_registry_development_v1.py'
    original_pin=registry._pin
    original_code=next(c for c in compile(registry_path.read_bytes(),str(registry_path),'exec').co_consts
        if isinstance(c,type(original_pin.__code__)) and c.co_name=='_pin')
    if (registry.__name__!='experiments.h1_outage_registry_development_v1'
            or registry.__file__!=str(registry_path) or registry.__spec__.origin!=str(registry_path)
            or registry.ROOT!=REPO or original_pin.__globals__ is not vars(registry)
            or original_pin.__defaults__ is not None or original_pin.__kwdefaults__ is not None
            or original_pin.__closure__ is not None
            or marshal.dumps(original_pin.__code__)!=marshal.dumps(original_code)):
        raise ValueError('canonical registry and source-authored original _pin required')
    authority_path=REPO/'results/tables/rq2_h1_outage_registry_v1_non_authoritative/scientific_development_authority.json'
    if registry.AUTHORITY!=authority_path:raise ValueError('canonical authority path required')
    authority=json.loads(original_pin(authority_path,registry.AUTHORITY_SHA))
    table_path=REPO/authority['cap_table_path']
    actual_inputs={str(authority_path):dict(sha256=registry.AUTHORITY_SHA,size_bytes=len(authority_path.read_bytes())),
        str(table_path):dict(sha256=authority['cap_table_sha256'],size_bytes=len(original_pin(table_path,authority['cap_table_sha256'])))}
    if actual_inputs!=scientific_expected:raise ValueError('canonical two-input registry cross-link required')
    result['scientific_input_caller_binding']=dict(registry_path=str(registry_path),
        original_pin_code_sha256=sha256(marshal.dumps(original_code)).hexdigest(),
        registry_implementation_identity=registry.implementation_identity(),
        static_input_paths_bound=True,source_authored_pin_hash_body_verified=True)
    normalization_scope,normalization_reader=normalization.operation(physical)
    stack.enter_context(normalization_scope)
    result['normalization_scope_requires_process_exit']=True
    return code,parsed


def receipts(code,parsed,name='',nodeid=None):
    interpreter_policy.admit('after_test_call:'+nodeid if nodeid else 'receipt:'+name)
    if code:
        receipt=code.receipt()
        expected_byte_pins={str(path):pin for path,pin in expected.items()}
        expected_byte_pins.update({p:row['sha256'] for p,row in scientific_expected.items()})
        if receipt['files_sha256']!=expected_byte_pins:
            raise ValueError('exact 256-code plus two scientific input byte lease receipt required')
        if any(receipt['hits_by_path'].get(os.path.normcase(p),0)<=0 for p in scientific_expected):
            raise ValueError('both canonical scientific inputs must actually use held bytes')
        receipt['vendor_module_origins']=vendor_policy.origins(sys.modules,required=kind in ('arm','phase'))
        save(name+'lease_receipt.json',dict(receipt,test_nodeid=nodeid))
    if parsed:save(name+'metadata_receipt.json',dict(parsed.receipt(),test_nodeid=nodeid))
    if path_lease:save(name+'path_receipt.json',dict(path_lease.receipt(),test_nodeid=nodeid))


def saved_arm():
    with ExitStack() as stack:
        vendor_policy.assert_unloaded(sys.modules)
        code=stack.enter_context(CodeReadLease(expected,root=Path('D:/'))) if mode!='plain' else None
        _saved_arm_leased(code)


def _saved_arm_leased(code):
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
        with ExitStack() as metadata_stack:
            parsed=metadata_stack.enter_context(MetadataParseLease(metadata_expected)) if mode in ('parse','parse_path') else None
            begin=perf_counter()
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
                result['validation_scope']='original common._arm and numerical checks; two named immutable scientific inputs use held bytes'
            receipts(code,parsed)
    finally:patch.undo()
    after={str(p):sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
    assert before==after
    result.update(saved_files_unchanged=True,saved_file_count=len(before),real_native_calls=0)


def unit_tests():
    import unittest
    suite=unittest.TestSuite()
    load_module('performance.pytest_lease_plugin','pytest_lease_plugin.py')
    load_module('performance.pytest_admission_plugin','pytest_admission_plugin.py')
    for filename in ('test_code_read_lease.py','test_metadata_parse_lease.py','test_validation_entry.py','test_pytest_lease_plugin.py','test_interpreter_path_policy.py','test_pytest_admission_plugin.py','test_vendor_code_policy.py','test_static_scientific_input_read_lease_v2.py'):
        module=load_module('performance.'+filename[:-3],filename)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    with (out/'unittest.log').open('x',encoding='utf-8') as log:
        run=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    save('static_input_byte_lease_unit_evidence.json',sys.modules['performance.test_static_scientific_input_read_lease_v2'].UNIT_EVIDENCE)
    result.update(tests_run=run.testsRun,skipped=len(run.skipped),failures=len(run.failures),errors=len(run.errors))
    return 0 if run.wasSuccessful() else 1


def pytest_tests():
    allowed=('tests/test_h1_selector_parent_controller_development_v3.py::test_actual_lifecycle_clears_each_external_boundary_and_binds_plain_receipts', 'tests/test_h1_selector_parent_controller_development_v3.py', 'tests/test_h1_selector_source_window_development_v1.py', 'tests/test_h1_selector_parent_validation_operation_development_v3.py', 'tests/test_h1_selector_post_negative_validation_development_v2.py', 'tests/test_h1_common_validation_operation_development_v3.py', 'tests/test_h1_selector_phase_handoff_development_v5.py', 'tests/test_h1_repair_cap_normalization_operation_development_v1.py', 'tests/test_h1_common_genesis_validation_operation_development_v1.py', 'tests/test_h1_genesis_consumer_operation_development_v1.py', 'tests/test_h1_genesis_consumer_operation_development_v1.py::test_three_actual_parents_commit_close_and_reopen_saved_phase')
    if not targets or any(t not in allowed for t in targets):
        raise ValueError('explicit zero-native synthetic test allowlist required')
    basetemp=Path('D:/h1_wf09_'+label+'_non_authoritative')
    if basetemp.exists():raise ValueError('unused short diagnostic root required')
    if targets==['tests/test_h1_guarded_common_slice_development_v2.py']:
        basetemp=Path('D:/h1_cs03_non_authoritative')
        if basetemp.exists():raise ValueError('fresh short diagnostic root required; preserve old attempt')
    result['pytest_basetemp']=str(basetemp)
    result['pytest_lease_lifetime']='whole invocation including collection, fixtures, calls and teardown'
    previous_timing=os.environ.get('H1_E2E_TIMING_FILE')
    previous_pytest_environment={key:os.environ.get(key) for key in (
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTEST_ADDOPTS','PYTEST_PLUGINS')}
    if any(previous_pytest_environment[key] for key in ('PYTEST_ADDOPTS','PYTEST_PLUGINS')):
        raise ValueError('unfixed PYTEST_ADDOPTS/PYTEST_PLUGINS refused')
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
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
        result['pytest_plugin_autoload']=False
        with ExitStack() as stack:
            code,parsed=lease_context(stack)
            import pytest
            Plugin=load_module('performance.pytest_lease_plugin','pytest_lease_plugin.py').LeasePlugin
            def window(unused_stack):
                interpreter_policy.admit('before_test_call')
                if parsed:parsed.begin_discovery_window()
                return code,parsed
            Admission=load_module('performance.pytest_admission_plugin','pytest_admission_plugin.py').AdmissionPlugin
            with (out/'pytest.log').open('x',encoding='utf-8') as log,redirect_stdout(log),redirect_stderr(log):
                try:
                    diagnostic=True
                    selected_plugins=[Plugin(window,receipts,result),Admission(interpreter_policy)]
                    if diagnostic:
                        class DiagnosticFlags:
                            def pytest_configure(self,config):
                                import faulthandler
                                if config.pluginmanager.has_plugin('faulthandler') or faulthandler.is_enabled():
                                    raise ValueError('diagnostic faulthandler plugin/fatal handler must be disabled')
                                result['diagnostic_faulthandler_plugin_absent']=True
                                result['diagnostic_fatal_handler_enabled_at_configure']=False
                        selected_plugins.append(DiagnosticFlags())
                    diagnostic_flags=['-p','no:faulthandler'] if diagnostic else []
                    result['diagnostic_pytest_flags']=diagnostic_flags
                    status=int(pytest.main(['-q','-s','-p','no:cacheprovider',*diagnostic_flags,
                        '--import-mode=importlib','--basetemp',str(basetemp),*targets],plugins=selected_plugins))
                finally:
                    sys.setprofile(previous_profile)
                    interpreter_policy.end_pytest()
            receipts(code,parsed,'session_')
        return status
    finally:
        primary_error=sys.exc_info()[1]
        cleanup_failures=[]
        sys.setprofile(previous_profile)
        if byte_lease is not None:
            closed=byte_lease.closed_receipt()
            save('static_input_byte_lease_closed_receipt.json',closed)
            if (not closed['all_handles_closed'] or not closed['original_alias_restored']
                    or not closed['exit_files_and_ancestors_verified']
                    or closed['first_failure'] is not None or closed['cleanup_errors']):
                cleanup_failures.append(ValueError('static scientific input byte lease did not close cleanly'))
        if normalization_reader is not None:
            normalized=normalization_reader()
            save('repair_normalization_closed_receipt.json',normalized)
            if (not normalized['all_normalization_cache_entries_cleared']
                    or not normalized['original_alias_restored']
                    or normalized['first_failure'] is not None or normalized['cleanup_error'] is not None):
                cleanup_failures.append(ValueError('repair normalization did not close cleanly'))
            if byte_lease is not None:
                closed=byte_lease.closed_receipt()
                oracles=normalized['original_oracle_invocations']
                minimum_pin_reads=normalized['adapter_pin_reads']+(oracles['entry']+oracles['exit'])*normalized['oracle_pin_reads_per_successful_invocation']
                if (minimum_pin_reads%2 or any(closed['hits_by_path'].get(os.path.normcase(p),0)<minimum_pin_reads//2
                        for p in scientific_expected)):
                    cleanup_failures.append(ValueError('held input hits do not cover verified normalizer pin schedule'))
                save('scientific_input_caller_execution.json',dict(
                    **result.get('scientific_input_caller_binding',{}),
                    normalizer_calls=normalized['calls'],normalizer_original_pin_reads=minimum_pin_reads,
                    static_input_hits=closed['scientific_input_read_hits'],
                    scope='normalizer original pin body and minimum counts; other caller counts not attributed',
                    bytes_transport_identity_separate_from_scientific_identity=True,formal_result=False))
            result['post_scope_consumer_reuse_allowed']=False
        save('call_counts.json',dict(rows=[dict(file=f,function=n,line=l,calls=count)
            for (f,n,l),count in sorted(call_counts.items())],
            scope='counter disabled; per-stage logs retained; parent current thread only if enabled in a successor',
            profiler_restored=sys.getprofile() is previous_profile,formal_result=False))
        if previous_timing is None:os.environ.pop('H1_E2E_TIMING_FILE',None)
        else:os.environ['H1_E2E_TIMING_FILE']=previous_timing
        for key,value in previous_pytest_environment.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        result['pytest_environment_restored']=all(os.environ.get(k)==v for k,v in previous_pytest_environment.items())
        if cleanup_failures:
            if primary_error is not None:
                for failure in cleanup_failures:primary_error.add_note(repr(failure))
            else:raise cleanup_failures[0]


previous_cwd=Path.cwd()
previous_path=list(sys.path)
repository_pins={}
repository_code_pins={}
vendor_code_pins={}
interpreter_policy=None
vendor_policy=None
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
    if interpreter_policy is not None:
        try:interpreter_policy.admit('entry_exit')
        except BaseException:result.update(exit_code=1,interpreter_policy_error=traceback.format_exc())
        try:save('interpreter_path_receipt.json',interpreter_policy.receipt())
        except BaseException:result.update(exit_code=1,interpreter_receipt_error=traceback.format_exc())
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
    vendor_after={};vendor_errors={}
    for path in vendor_code_pins:
        try:vendor_after[path]=sha256(Path(path).read_bytes()).hexdigest()
        except BaseException as error:vendor_errors[path]=repr(error)
    save('vendor_code_pins_after.json',dict(files_sha256=vendor_after,read_errors=vendor_errors))
    result['vendor_code_file_count']=len(vendor_code_pins)
    result['vendor_code_unchanged']=vendor_after==vendor_code_pins and not vendor_errors
    if vendor_policy is not None:
        try:result['vendor_module_origins_at_exit']=vendor_policy.origins(sys.modules,required=kind in ('arm','phase'))
        except BaseException:result.update(exit_code=1,vendor_origin_error=traceback.format_exc())
    if vendor_after!=vendor_code_pins or vendor_errors:
        result.update(exit_code=1,error='vendor code changed during measurement')
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
