"""Static/source and ordinary fake-DLL validation of prepared Win32 effects."""
import ast
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).absolute().parents[1]
FILES={
    'provider':'experiments/staged_rts24_saved_fresh_host_windows_resources_v1.py',
    'host':'experiments/staged_rts24_saved_fresh_full_role_host_preentry_v2.py',
    'fixture':'tests/saved_fresh_host_windows_fixture_v1.py',
    'test':'tests/test_staged_rts24_saved_fresh_host_windows_resources_v1.py',
    'prior_fixture':'tests/test_staged_rts24_saved_fresh_full_role_host_preentry_v1.py',
    'source_control':'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json',
    'native_baseline':'src/rq2_joint_deliverability_boundary_v1/normal_process.py',
    'guard_baseline':'src/staged_rts24_process_guard_v1.py',
}
METHODS=42
SCOPE='host_win32_resource_source_and_private_protocol_synthetic_only'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def snapshot():
    pins={str(ROOT/path):pin((ROOT/path).read_bytes()) for path in FILES.values()}
    trees={key:ast.parse((ROOT/FILES[key]).read_bytes()) for key in ('provider','host','test','native_baseline')}
    methods=[n.name for c in trees['test'].body if type(c) is ast.ClassDef for n in c.body if type(n) is ast.FunctionDef and n.name.startswith('test_')]
    assert len(methods)==len(set(methods))==METHODS
    for key,names in [('provider',('open_windows_resources','_mechanical_resources')),('host',('open_full_role_host','_mechanical_host'))]:
        for name in names:
            node=next(n for n in trees[key].body if type(n) is ast.FunctionDef and n.name==name)
            assert type(node.body[0]) is ast.Raise
    class Normalize(ast.NodeTransformer):
        def visit_Name(self,node):
            return ast.copy_location(ast.Name(id={'c':'C','w':'W'}.get(node.id,node.id),ctx=node.ctx),node)
    field_rows={}
    for name in ('_Basic','_IO','_Limits','_Startup','_StartupEx','_ProcessInfo','_Accounting'):
        values=[]
        for key in ('provider','native_baseline'):
            cls=next(n for n in trees[key].body if type(n) is ast.ClassDef and n.name==name)
            assignment=next(n for n in cls.body if type(n) is ast.Assign and n.targets[0].id=='_fields_')
            values.append(ast.dump(Normalize().visit(assignment.value),include_attributes=False))
        assert values[0]==values[1],name;field_rows[name]=pin(values[0].encode())
    literal=load(ROOT/'experiments/staged_rts24_saved_fresh_contract_snapshot_v1.py','_windows_original_contract')
    own=literal.extract(ROOT/FILES['host'],('CAPS','STAGES'))
    old=literal.extract(ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py',('CAPS','STAGE_SECONDS'))
    assert own['constants']['CAPS']['value']==old['constants']['CAPS']['value']
    assert own['constants']['STAGES']['value']==old['constants']['STAGE_SECONDS']['value']
    return dict(schema='staged_saved_F_windows_preparation_v1',acceptance_scope=SCOPE,source_pins=pins,test_methods=METHODS,
        structure_field_ast_equivalence=field_rows,original_F_constants_equal=True,
        resource_source_bodies_prepared=True,physical_host_provider_implemented=False,source_authenticated_host_issuer=False,
        full_role_entry_connected=False,native_equivalence_verified=False,native_return_to_publication_window_verified=False,
        new_startup_profile_verified=False,project_native_calls=0,P1_reads=0,source49_modules_executed=0,target_child_processes=0,
        run_authority=False,actual_F=False,formal_result=False)


def unit():
    module=load(ROOT/FILES['test'],'_windows_resource_unit');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    assert suite.countTestCases()==METHODS
    stream=io.StringIO();ids=[]
    class Result(unittest.TextTestResult):
        def startTest(self,test):ids.append(test.id());super().startTest(test)
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    contracts={};errors={}
    try:contracts['windows']=module.contract()
    except BaseException as error:errors['windows']=type(error).__name__+':'+str(error)
    raw=stream.getvalue().encode('utf8');assert len(raw)<=131072
    return dict(success=result.wasSuccessful() and not errors,methods=result.testsRun,ids=ids,raw_log=raw.decode('utf8'),raw_log_pin=pin(raw),
        failures=[(str(test),trace) for test,trace in result.failures],errors=[(str(test),trace) for test,trace in result.errors],skipped=result.skipped,
        contracts=contracts,contract_errors=errors,kernel_leaves_synthetic=True,validation_child_processes=0,target_child_processes=0,
        project_native_calls=0,P1_reads=0,source49_modules_executed=0,run_authority=False,actual_F=False)


def verify_unit(report):
    assert report['success'] is True and report['methods']==METHODS and len(report['ids'])==len(set(report['ids']))==METHODS
    assert report['errors']==report['failures']==report['skipped']==[] and report['contract_errors']=={}
    assert pin(report['raw_log'].encode('utf8'))==report['raw_log_pin'] and report['kernel_leaves_synthetic'] is True
    assert all(type(report[k]) is int and report[k]==0 for k in ('validation_child_processes','target_child_processes','project_native_calls','P1_reads','source49_modules_executed'))
    assert report['run_authority'] is report['actual_F'] is False
    assert set(report['contracts'])=={'windows'};c=report['contracts']['windows']
    assert c['schema']=='staged_saved_F_windows_resources_synthetic_contract_v1' and c['test_methods']==METHODS
    true=('synthetic_only','resource_source_bodies_executed','full_host_protocol_connected_in_private_copy','ctypes_memory_buffers_synthetic','native_return_gap_explicit_unresolved','ephemeral_member_gap_explicit_unresolved')
    false=('native_equivalence_verified','source_authenticated_host_issuer','full_role_entry_connected','physical_host_provider_implemented',
        'actual_entry_authenticated','real_broker_cancel_ack_verified','real_transport_payload_equivalence_verified','core51_full_manifest_validated',
        'new_startup_profile_verified','native_return_to_publication_window_verified','continuous_RSS_measured','native_authorized',
        'public_P2_execution_enabled','resource_admission','run_authority','actual_F','formal_result')
    zero=('project_native_calls','source49_modules_executed','P1_reads','validation_child_processes','target_child_processes')
    assert set(c)==set(true+false+zero+('schema','private_gates_removed','test_methods','fault_cases'))
    assert all(c[k] is True for k in true) and all(c[k] is False for k in false)
    assert all(type(c[k]) is int and c[k]==0 for k in zero)
    assert c['private_gates_removed']==['_mechanical_host','_mechanical_resources'] and len(c['fault_cases'])==len(set(c['fault_cases']))==20
    return dict(methods=METHODS,fault_cases=20,unit_raw_log_pin=report['raw_log_pin'],ordinary_synthetic_only=True)


def replay_saved(report):
    assert snapshot()==report
    return dict(source_pins=report['source_pins'],acceptance_scope=SCOPE,executed_unit_methods=0,
        actual_F=False,run_authority=False,full_role_entry_connected=False,physical_host_provider_implemented=False)
