"""Guard installation and held permission dependency on the real bootstrap path."""
from hashlib import sha256
from pathlib import Path
import ast

ROOT=Path(__file__).absolute().parents[1]
PAIRS=(
    ('construction','experiments/staged_rts24_saved_fresh_producer_bootstrap_v4.py','experiments/staged_rts24_saved_fresh_producer_bootstrap_v5.py'),
    ('loader','experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v2.py','experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v3.py'),
    ('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v41.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v42.py'),
    ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v39.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v40.py'),
    ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v38.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v39.py'),
    ('validation','experiments/staged_rts24_saved_fresh_construction_validation_v1.py','experiments/staged_rts24_saved_fresh_construction_validation_v2.py'))
OLD_OUT='staged_rts24_saved_fresh_project_construction_v2_non_authoritative'
NEW_OUT='staged_rts24_saved_fresh_guarded_project_construction_v1_non_authoritative'


def replace(source,before,after,count=1):
    assert source.count(before)==count,(before,source.count(before),count)
    return source.replace(before,after)


def common(source):
    for before,after in ((OLD_OUT,NEW_OUT),('retained_producer_v3.py','retained_producer_v4.py'),
            ('producer_bootstrap_v4.py','producer_bootstrap_v5.py'),('project_bootstrap_loader_v2.py','project_bootstrap_loader_v3.py'),
            ('staged_saved_F_project_construction_manifest_v2','staged_saved_F_project_construction_manifest_v3')):
        if before in source:source=replace(source,before,after,source.count(before))
    return source


def construction(source):
    source=common(source)
    value=next(node for node in ast.parse(source).body if type(node) is ast.Assign
        and any(type(item) is ast.Name and item.id=='LIFECYCLE_SUCCESSOR_PIN' for item in node.targets))
    old=ast.get_source_segment(source,value);raw=(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v4.py').read_bytes()
    source=replace(source,old,'LIFECYCLE_SUCCESSOR_PIN='+repr((len(raw),sha256(raw).hexdigest())))
    source=replace(source,"def _make_bundle(plan,graph,graph_raw,lifecycle,lifecycle_raw,capture_code,admission):",
        "def _make_bundle(plan,graph,graph_raw,lifecycle,lifecycle_raw,capture_code,admission):")
    source=replace(source,"        _CAPTURE_CODE=capture_code,_GRAPH_MODULE=graph,_PROJECT_SNAPSHOT=snapshot)",
        "        _CAPTURE_CODE=capture_code,_GRAPH_MODULE=graph,_PROJECT_SNAPSHOT=snapshot,\n        _P1_PERMISSION_PROGRAM=_P1_PERMISSION_PROGRAM,_P1_PERMISSION_RAW=_P1_PERMISSION_RAW)")
    source=replace(source,"_RUNTIME_TYPE=globals().get('_RUNTIME_TYPE')",
        "_RUNTIME_TYPE=globals().get('_RUNTIME_TYPE')\n_P1_PERMISSION_PROGRAM=globals().get('_P1_PERMISSION_PROGRAM')\n_P1_PERMISSION_RAW=globals().get('_P1_PERMISSION_RAW')")
    return source.encode('utf8')


def loader(source):
    source=replace(source,"('utilities','lifecycle','project_graph','construction','capture')",
        "('utilities','lifecycle','project_graph','construction','capture','p1_permission')",2)
    source=replace(source,"    program=source_program(held['construction'],dict(_RUNTIME_TYPE=LocalRuntimeInputs),held['utilities'])",
        """    # The fixed permission program has a sticky disabled external root.
    permission_program=FunctionType(function_code('p1_permission','source_program'),vars(modules['p1_permission']))(
        held['p1_permission'],LocalRuntimeInputs,held['utilities'])
    FunctionType(permission_program[0],permission_program[1])(permission_program[2],'bind_owner',(runtime,))
    program=source_program(held['construction'],dict(_RUNTIME_TYPE=LocalRuntimeInputs,
        _P1_PERMISSION_PROGRAM=permission_program,_P1_PERMISSION_RAW=held['p1_permission']),held['utilities'])""")
    return replace(source,'    return bridge','    return bridge,permission_program').encode('utf8')


def refs(source):
    return replace(source,"        construction=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v5.py'),",
        "        p1_permission=str(ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'),\n        construction=str(ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v5.py'),")


def core(source):return refs(common(source)).encode('utf8')


def probe(source):
    source=common(source)
    source=replace(source,'staged_saved_F_project_construction_probe_v2','staged_saved_F_project_construction_probe_v3')
    source=replace(source,'construction_result=None;namespace_terminal=None','construction_result=None;namespace_terminal=None;permission_program=None;permission_observation=None')
    source=replace(source,'            bridge=prepare_project_bridge(runtime,plan,_compile,_exec)',
        '            bridge,permission_program=prepare_project_bridge(runtime,plan,_compile,_exec)')
    source=replace(source,"            runtime.handoff_audit();boundary.admit_paths();phase='IMPORT'",
        "            FunctionType(permission_program[0],permission_program[1])(permission_program[2],'install_guard',(boundary,))\n            runtime.handoff_audit();boundary.admit_paths();phase='IMPORT'")
    source=replace(source,"        if guard is not None:guard['active']=False",
        """        if permission_program is not None:
            try:FunctionType(permission_program[0],permission_program[1])(permission_program[2],'close_guard',())
            except BaseException as error:secondary.append(error)
            try:permission_observation=FunctionType(permission_program[0],permission_program[1])(permission_program[2],'report',())
            except BaseException as error:secondary.append(error)
        if guard is not None:guard['active']=False""")
    source=replace(source,'        construction_result=construction_result,namespace_terminal=namespace_terminal,consumer_state=',
        '        construction_result=construction_result,namespace_terminal=namespace_terminal,permission_observation=permission_observation,consumer_state=')
    return source.encode('utf8')


def parent(source):
    source=refs(common(source))
    source=replace(source,'lease_v41.py','lease_v42.py')
    source=replace(source,'probe_v39.py','probe_v40.py')
    source=replace(source,'construction_validation_v1.py','construction_validation_v2.py')
    return source.encode('utf8')


def validation(source):
    source=replace(source,'staged_saved_F_project_construction_probe_v2','staged_saved_F_project_construction_probe_v3')
    source=replace(source,"PROBE_KEYS=set([","PROBE_KEYS={'permission_observation'}|set([")
    source=replace(source,"'construction_result','namespace_terminal','guard','import_profile'):",
        "'construction_result','namespace_terminal','permission_observation','guard','import_profile'):")
    source=replace(source,"    namespace_shape(record['namespace_terminal'],success=True);construction_shape(record['construction_result'])",
        "    namespace_shape(record['namespace_terminal'],success=True);construction_shape(record['construction_result']);permission_shape(record['permission_observation'],True)")
    source=replace(source,"    if record['namespace_terminal'] is not None:namespace_shape(record['namespace_terminal'])",
        "    if record['namespace_terminal'] is not None:namespace_shape(record['namespace_terminal'])\n    if record['permission_observation'] is not None:permission_shape(record['permission_observation'])")
    return (source+'''


def permission_shape(value,success=False):
    flags=('external_permission_verified','full_P1_content_verified','independent_root_verified','role_bootstrap',
        'permit_issued','run_authority','F_launch_admitted','actual_F','resource_admission','scientific_evidence_adopted','formal_result')
    keys=set(flags)|{'schema','authority','issuer_phase','guard_phase','installed','counters','faults','admission_present'}
    require(type(value) is dict and set(value)==keys and value['schema']=='staged_saved_F_P1_permission_observation_v1'
        and value['authority']=='DRAFT_NONAUTHORITATIVE','closed permission observation required')
    require(all(value[key] is False for key in flags) and value['admission_present'] is False,'no P1 permission is issued')
    require(type(value['installed']) is bool and value['issuer_phase'] in ('DISABLED','RETIRED','UNRESOLVED')
        and value['guard_phase'] in ('NEW','INSTALLED_DENY','DENY','CLOSED'),'disabled permission phases required')
    counts=value['counters'];require(type(counts) is dict and set(counts)=={'selected','protected','allowed','writes','processes','mutations','construction_reads','runtime_reads','outside_reads'}
        and all(type(number) is int and 0<=number<=16384 for number in counts.values()),'bounded permission counters required')
    require(counts['allowed']==0 and type(value['faults']) is list and len(value['faults'])<=4
        and all(type(item) is str and len(item)<=96 for item in value['faults']),'zero authorized P1 reads required')
    if success:
        require(value['issuer_phase']=='DISABLED' and value['guard_phase']=='CLOSED' and value['installed'] is True
            and value['faults']==[] and all(counts[key]==0 for key in ('protected','writes','processes','mutations','outside_reads')),
            'clean continuous deny guard terminal required')
    return value
''').encode('utf8')


def current():
    pins={}
    for name,before,after in PAIRS:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf8'));assert (ROOT/after).read_bytes()==raw,after
        compile(raw,str(ROOT/after),'exec',dont_inherit=True,optimize=0);pins[after]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    return None,dict(schema='staged_saved_F_permission_bootstrap_wiring_v1',authority='DRAFT_NONAUTHORITATIVE',successor_pins=pins,
        external_root=None,guard_installation='after_B_S_hook_before_handoff',issuer_implemented=False,
        P1_reads=0,source49_target_modules_executed=0,actual_F=False,formal_result=False,run_authority=False,resource_admission=False)


if __name__=='__main__':
    for name,before,after in PAIRS:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf8'));compile(raw,str(ROOT/after),'exec',dont_inherit=True,optimize=0)
        with (ROOT/after).open('xb') as stream:stream.write(raw)
