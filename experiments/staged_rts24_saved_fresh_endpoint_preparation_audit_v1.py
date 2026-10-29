"""Static thin transport and ordinary synthetic Core51 verification."""
import ast
import base64
from hashlib import sha256
import importlib.util
import io
import json
import lzma
from pathlib import Path
import subprocess
import tokenize
from types import CodeType, FunctionType
import unittest

ROOT=Path(__file__).absolute().parents[1]
FILES={
    'core':'experiments/staged_rts24_saved_fresh_pre_entry_lease_v51.py',
    'entry':'experiments/staged_rts24_saved_fresh_pre_manifest_entry_probe_v1.py',
    'endpoint_fixture':'tests/saved_fresh_endpoint_fixture_v1.py',
    'endpoint_test':'tests/test_staged_rts24_saved_fresh_pre_manifest_endpoint_v1.py',
    'cleanup_test':'tests/test_staged_rts24_saved_fresh_source_cleanup_v7.py',
    'binding_test':'tests/test_staged_rts24_saved_fresh_cleanup_binding_v5.py',
    'role_test':'tests/test_staged_rts24_saved_fresh_full_context_role_runtime_v6.py',
    'role':'experiments/staged_rts24_saved_fresh_full_context_role_runtime_v6.py',
    'core44':'experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py',
    'namespace':'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py',
    'boundary':'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py',
    'transport':'experiments/staged_rts24_saved_fresh_utf16_transport_v1.py',
    'parent40':'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v40.py',
    'oracle':'experiments/staged_rts24_saved_fresh_preentry_route_audit_v2.py',
}
METHODS=99


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def load(key,name):
    path=ROOT/FILES[key];spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def capacity():
    transport=load('transport','_endpoint_static_transport');oracle=load('oracle','_endpoint_independent_decoder')
    raw=(ROOT/FILES['parent40']).read_bytes();node=oracle.node_at(ast.parse(raw),'minify_prefix')
    unit=compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/FILES['parent40']),'exec',dont_inherit=True,optimize=0)
    code=next(item for item in unit.co_consts if type(item) is CodeType and item.co_name=='minify_prefix')
    minify=FunctionType(code,dict(__builtins__=__builtins__,ast=ast,io=io,tokenize=tokenize))
    _,payload=transport.payload(ROOT/FILES['core'],ROOT/FILES['entry'])
    packed=lzma.compress(payload,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,preset=6)
    built=transport.build(ROOT/FILES['core'],ROOT/FILES['entry'],minify)
    independent=oracle.independent_decode_transport(built,payload)
    assert independent['packed_pin']==pin(packed)
    nonce='0'*64;manifest=str(ROOT/'results/tables/staged_rts24_saved_fresh_full_role_entry_native_v1_non_authoritative/transport'/nonce/'controller.plan.json')
    args=['D:\\Miniconda3\\envs\\compute\\python.exe','-P','-B','-s','-S','-c',built.decode('utf8'),
        '--full-role-pre-entry',manifest,'0'*64,'Local\\saved_F_pre_entry_v1_'+nonce,nonce,'controller',
        *(['0'*64]*4),(100.0).hex(),(280.0).hex()]
    units=len(subprocess.list2cmdline(args).encode('utf-16-le'))//2+1
    assert len(args)==19 and units<=30000 and len(payload)<=131072 and len(packed)<=26214
    return dict(payload_pin=pin(payload),packed_pin=pin(packed),transport_pin=pin(built),
        payload_cap=131072,xz_cap=26214,utf16_cap=30000,utf16_units_including_nul=units,
        argv_placeholder_not_runnable=True,transport_base64=base64.b64encode(built).decode('ascii'),
        independent=independent,generated_transport_executed=False)


def snapshot():
    pins={str(ROOT/path):pin((ROOT/path).read_bytes()) for path in FILES.values()}
    count={}
    for key in ('endpoint_test','cleanup_test','role_test','binding_test'):
        tree=ast.parse((ROOT/FILES[key]).read_bytes())
        count[key]=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for c in tree.body
            if isinstance(c,ast.ClassDef) for n in c.body)
    assert count==dict(endpoint_test=30,cleanup_test=32,role_test=26,binding_test=11) and sum(count.values())==METHODS
    return dict(schema='staged_saved_F_endpoint_preparation_v1',source_pins=pins,test_methods=count,
        capacity=capacity(),acceptance_scope='endpoint_core_ownership_synthetic_and_transport_only',
        full_role_entry_connected=False,native_equivalence_verified=False,
        native_return_to_publication_window_verified=False,new_startup_profile_verified=False,
        project_native_calls=0,P1_reads=0,source49_modules_executed=0,target_child_processes=0,
        run_authority=False,actual_F=False,formal_result=False)


def unit():
    modules={key:load(key,'_endpoint_unit_'+key) for key in ('endpoint_test','cleanup_test','role_test','binding_test')}
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules.values())
    assert suite.countTestCases()==METHODS
    stream=io.StringIO();identities=[]
    class Result(unittest.TextTestResult):
        def startTest(self,test):
            identities.append(test.id());super().startTest(test)
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    raw=stream.getvalue().encode('utf8');assert len(raw)<=131072
    contracts={};contract_errors={}
    for key,module in modules.items():
        try:contracts[key]=module.contract()
        except BaseException as error:contract_errors[key]=type(error).__name__+':'+str(error)
    return dict(success=result.wasSuccessful() and not contract_errors,methods=result.testsRun,ids=identities,raw_log=raw.decode('utf8'),
        raw_log_pin=pin(raw),failures=[(str(test),trace) for test,trace in result.failures],
        errors=[(str(test),trace) for test,trace in result.errors],skipped=result.skipped,
        contracts=contracts,contract_errors=contract_errors,
        kernel_leaves_synthetic=True,validation_child_processes=0,target_child_processes=0,
        project_native_calls=0,source49_modules_executed=0,P1_reads=0,run_authority=False,actual_F=False)


def replay_saved(report):
    for path,expected in report['source_pins'].items():assert pin(Path(path).read_bytes())==expected
    saved=report['capacity'];built=base64.b64decode(saved['transport_base64'],validate=True)
    assert pin(built)==saved['transport_pin']
    transport=load('transport','_endpoint_saved_transport');oracle=load('oracle','_endpoint_saved_oracle')
    _,payload=transport.payload(ROOT/FILES['core'],ROOT/FILES['entry'])
    assert pin(payload)==saved['payload_pin']
    independent=oracle.independent_decode_transport(built,payload)
    assert independent==saved['independent'] and independent['packed_pin']==saved['packed_pin']
    assert saved['utf16_units_including_nul']<=30000
    return dict(transport_pin=pin(built),independent=independent,target_executed=False)
