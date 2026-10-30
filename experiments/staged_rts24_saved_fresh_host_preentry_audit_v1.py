"""Bounded static and ordinary synthetic host protocol validation."""
import ast
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).absolute().parents[1]
FILES={
    'host':'experiments/staged_rts24_saved_fresh_full_role_host_preentry_v1.py',
    'test':'tests/test_staged_rts24_saved_fresh_full_role_host_preentry_v1.py',
    'core':'experiments/staged_rts24_saved_fresh_pre_entry_lease_v51.py',
    'endpoint_fixture':'tests/saved_fresh_endpoint_fixture_v1.py',
    'source_control':'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json',
}
METHODS=46
SCOPE='outer_host_protocol_and_suspended_order_synthetic_only'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def snapshot():
    pins={str(ROOT/path):pin((ROOT/path).read_bytes()) for path in FILES.values()}
    tree=ast.parse((ROOT/FILES['host']).read_bytes());test=ast.parse((ROOT/FILES['test']).read_bytes())
    methods=[n.name for c in test.body if type(c) is ast.ClassDef for n in c.body if type(n) is ast.FunctionDef and n.name.startswith('test_')]
    assert len(methods)==len(set(methods))==METHODS
    gates=[]
    for node in tree.body:
        if type(node) is ast.FunctionDef and node.name in ('open_full_role_host','_mechanical_host'):
            assert type(node.body[0]) is ast.Raise and node.body[0].exc.func.id=='FullHostUnavailable';gates.append(node.name)
    assert gates==['open_full_role_host','_mechanical_host']
    literal=load(ROOT/'experiments/staged_rts24_saved_fresh_contract_snapshot_v1.py','_host_source_constants')
    own=literal.extract(ROOT/FILES['host'],('CAPS','STAGES'))
    old=literal.extract(ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py',('CAPS','STAGE_SECONDS'))
    assert own['constants']['CAPS']['value']==old['constants']['CAPS']['value']
    assert own['constants']['STAGES']['value']==old['constants']['STAGE_SECONDS']['value']
    return dict(schema='staged_saved_F_host_preentry_preparation_v1',acceptance_scope=SCOPE,source_pins=pins,
        test_methods=METHODS,closed_issuers=gates,original_budget_constants_equal=True,
        physical_host_provider_implemented=False,source_authenticated_host_issuer=False,
        full_role_entry_connected=False,native_equivalence_verified=False,
        native_return_to_publication_window_verified=False,new_startup_profile_verified=False,
        project_native_calls=0,P1_reads=0,source49_modules_executed=0,target_child_processes=0,
        run_authority=False,actual_F=False,formal_result=False)


def unit():
    module=load(ROOT/FILES['test'],'_host_ordinary_unit');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    assert suite.countTestCases()==METHODS
    stream=io.StringIO();ids=[]
    class Result(unittest.TextTestResult):
        def startTest(self,test):ids.append(test.id());super().startTest(test)
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    contracts={};errors={}
    try:contracts['host']=module.contract()
    except BaseException as error:errors['host']=type(error).__name__+':'+str(error)
    raw=stream.getvalue().encode('utf8');assert len(raw)<=131072
    return dict(success=result.wasSuccessful() and not errors,methods=result.testsRun,ids=ids,raw_log=raw.decode('utf8'),raw_log_pin=pin(raw),
        failures=[(str(test),trace) for test,trace in result.failures],errors=[(str(test),trace) for test,trace in result.errors],
        skipped=result.skipped,contracts=contracts,contract_errors=errors,
        kernel_leaves_synthetic=True,validation_child_processes=0,target_child_processes=0,project_native_calls=0,
        P1_reads=0,source49_modules_executed=0,run_authority=False,actual_F=False)


def verify_unit(report):
    assert report['success'] is True and report['methods']==METHODS and len(report['ids'])==len(set(report['ids']))==METHODS
    assert report['errors']==report['failures']==report['skipped']==[] and report['contract_errors']=={}
    assert pin(report['raw_log'].encode('utf8'))==report['raw_log_pin'] and report['kernel_leaves_synthetic'] is True
    assert all(type(report[k]) is int and report[k]==0 for k in ('validation_child_processes','target_child_processes','project_native_calls','P1_reads','source49_modules_executed'))
    assert report['run_authority'] is report['actual_F'] is False
    assert set(report['contracts'])=={'host'};contract=report['contracts']['host']
    assert contract['schema']=='staged_saved_F_host_preentry_synthetic_contract_v1'
    assert set(contract)==set(('schema synthetic_only private_gate_removed fault_cases physical_host_provider_implemented '
        'full_context_bytes_synthetic source_authenticated_host_issuer native_return_to_publication_window_verified '
        'new_startup_profile_verified native_authorized public_P2_execution_enabled real_broker_cancel_ack_verified '
        'real_transport_payload_equivalence_verified core51_full_manifest_validated core51_header_only_interop '
        'source49_pin_map_from_saved_record source49_modules_executed P1_reads project_native_calls target_child_processes '
        'validation_child_processes actual_entry_authenticated full_role_entry_connected native_equivalence_verified '
        'run_authority actual_F formal_result').split())
    assert contract['synthetic_only'] is contract['full_context_bytes_synthetic'] is contract['source49_pin_map_from_saved_record'] is True
    assert contract['private_gate_removed']==['_mechanical_host'] and len(contract['fault_cases'])==len(set(contract['fault_cases']))==23
    assert all(contract[k] is False for k in ('physical_host_provider_implemented','actual_entry_authenticated','full_role_entry_connected',
        'native_equivalence_verified','real_broker_cancel_ack_verified','real_transport_payload_equivalence_verified',
        'core51_full_manifest_validated','source_authenticated_host_issuer','native_return_to_publication_window_verified',
        'new_startup_profile_verified','native_authorized','public_P2_execution_enabled','run_authority','actual_F','formal_result'))
    assert contract['core51_header_only_interop'] is True
    assert all(type(contract[k]) is int and contract[k]==0 for k in ('source49_modules_executed','P1_reads','project_native_calls',
        'target_child_processes','validation_child_processes'))
    return dict(methods=METHODS,fault_cases=23,unit_raw_log_pin=report['raw_log_pin'],ordinary_synthetic_only=True)


def replay_saved(report):
    assert snapshot()==report
    return dict(source_pins=report['source_pins'],acceptance_scope=SCOPE,executed_unit_methods=0,
        actual_F=False,run_authority=False,full_role_entry_connected=False,physical_host_provider_implemented=False)
