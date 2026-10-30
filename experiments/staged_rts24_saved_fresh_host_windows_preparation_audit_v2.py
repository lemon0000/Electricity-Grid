"""Strict static replay of frozen Windows preparation; no unit execution."""
import ast
import copy
import sys
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

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


def field_dump(node):
    options = dict(include_attributes=False)
    if sys.version_info >= (3,13):
        options["show_empty"] = True
    return ast.dump(node, **options)


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
            values.append(field_dump(Normalize().visit(assignment.value)))
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
    assert canonical(snapshot())==canonical(report)
    return dict(source_pins=report['source_pins'],acceptance_scope=SCOPE,executed_unit_methods=0,
        actual_F=False,run_authority=False,full_role_entry_connected=False,physical_host_provider_implemented=False)


def verify_reused_unit(report):
    verified=verify_unit(report)
    tree=ast.parse((ROOT/FILES['test']).read_bytes())
    ids=['_windows_resource_unit.'+c.name+'.'+n.name for c in tree.body if type(c) is ast.ClassDef
        for n in c.body if type(n) is ast.FunctionDef and n.name.startswith('test_')]
    assert report['ids']==ids and ids==sorted(ids)
    lines=report['raw_log'].splitlines()
    assert len(lines)==47 and lines[:42]==[i.rsplit('.',1)[1]+' ('+i+') ... ok' for i in ids]
    assert lines[42:]==['','-'*70,'Ran 42 tests in 4.837s','','OK']
    assert report['contracts']['windows']['fault_cases']==sorted(report['contracts']['windows']['fault_cases'])
    return dict(verified,ids_match_frozen_source=True,raw_log_lines=47,reused_unit_methods=42,executed_unit_methods=0)


def static_repair(report,unit_report):
    assert canonical(snapshot())==canonical(report)
    roundtrip=json.loads(canonical(report));assert canonical(roundtrip)==canonical(report)
    assert canonical(replay_saved(roundtrip))==canonical(replay_saved(report))
    tree=ast.parse((ROOT/FILES['provider']).read_bytes()); differences={};all_fields={}
    for name in ('_Basic','_IO','_Limits','_Startup','_StartupEx','_ProcessInfo','_Accounting'):
        cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name==name)
        assignment=next(n for n in cls.body if type(n) is ast.Assign and n.targets[0].id=='_fields_')
        before=pin(ast.dump(assignment.value,include_attributes=False).encode())
        after=pin(field_dump(assignment.value).encode())
        assert after==report['structure_field_ast_equivalence'][name]
        all_fields[name]=after
        if before!=after:differences[name]=dict(default=before,complete=after)
    assert set(differences)=={'_IO','_Startup','_Accounting'}
    assert [(differences[n]['default']['bytes'],differences[n]['complete']['bytes']) for n in
        ('_IO','_Startup','_Accounting')]==[(428,436),(1577,1585),(705,721)]
    node=ast.parse('[value for value in source]',mode='eval').body
    changed=copy.deepcopy(node);changed.generators[0].ifs.append(ast.Constant(value=True))
    assert field_dump(node)!=field_dump(changed)
    probes={}
    for name in ('structure_digest','source_digest','missing_source','execution_gate','boolean_counter','missing_field'):
        altered=copy.deepcopy(report)
        if name=='structure_digest':altered['structure_field_ast_equivalence']['_IO']=differences['_IO']['default']
        elif name=='source_digest':next(iter(altered['source_pins'].values()))['sha256']='0'*64
        elif name=='missing_source':altered['source_pins'].pop(next(iter(altered['source_pins'])))
        elif name=='execution_gate':altered['actual_F']=True
        elif name=='boolean_counter':altered['project_native_calls']=False
        else:del altered['test_methods']
        try:replay_saved(altered)
        except AssertionError:probes[name]=True
        else:raise AssertionError('changed report accepted: '+name)
    return dict(schema='staged_saved_F_windows_replay_repair_v2',original_inspect_exact=True,
        default_dump_differences=differences,complete_field_pins=all_fields,json_roundtrip_exact=True,
        semantic_ast_mutation_rejected=True,report_mutations_rejected=probes,
        unit_reuse=verify_reused_unit(unit_report),executed_unit_methods=0,
        validation_child_processes=0,target_child_processes=0,project_native_calls=0,P1_reads=0,
        source49_modules_executed=0,run_authority=False,actual_F=False,formal_result=False)
