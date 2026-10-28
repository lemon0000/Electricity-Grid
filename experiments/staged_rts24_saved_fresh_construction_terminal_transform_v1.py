"""Exact, non-authoritative successors for graph accounting and terminal data."""
import importlib.util
import json
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
OLD_OUT='staged_rts24_saved_fresh_project_construction_v1_non_authoritative'
NEW_OUT='staged_rts24_saved_fresh_project_construction_v2_non_authoritative'
PAIRS=(
    ('namespace','experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v2.py','experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v3.py'),
    ('lifecycle','experiments/staged_rts24_saved_fresh_retained_producer_v2.py','experiments/staged_rts24_saved_fresh_retained_producer_v3.py'),
    ('construction','experiments/staged_rts24_saved_fresh_producer_bootstrap_v3.py','experiments/staged_rts24_saved_fresh_producer_bootstrap_v4.py'),
    ('loader','experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v1.py','experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v2.py'),
    ('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v40.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v41.py'),
    ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v38.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v39.py'),
    ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v37.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v38.py'))

TERMINAL_SOURCE='''

def namespace_terminal_snapshot(owner,expected_namespace):
    """Observe retained ownership data after close; no entry or filesystem read."""
    if owner is None:return None
    namespace=expected_namespace;resource=owner._resource;inputs=namespace._inputs;registry=namespace._modules
    require(type(registry) is dict and len(registry)<=4096 and all(type(key) is str for key in registry),
        'bounded original namespace registry required')
    actual,reference=namespace._aliases
    expected=('experiments.staged_rts24_saved_fresh_adoption_v1','_saved_F_entry_reference_v1')
    require((actual,reference)==expected,'original namespace aliases required')
    return dict(schema='staged_saved_F_namespace_terminal_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        runtime_phase=owner._phase,cleanup_started=owner._cleanup_started,failure_absent=owner._failure is None,
        resource_phase=resource.phase,resource_owner_same=resource.owner is owner,pending=[bool(value) for value in resource.pending],
        namespace_phase=namespace._phase,namespace_same=owner._namespace is namespace,peer_same=namespace._runtime_peer is owner,
        source_same=owner._source is inputs,inputs_phase=inputs._phase,successor_same=inputs._successor is owner,
        resource_same=inputs._resource is resource,registry_same=registry is sys.modules,
        reference_registered=namespace._reference_registered,actual_key_absent=actual not in registry,
        reference_key_absent=reference not in registry,
        actual_aliases=sorted(key for key,value in tuple(registry.items()) if value is namespace.module),
        reference_aliases=sorted(key for key,value in tuple(registry.items()) if value is namespace.reference))


def require_namespace_terminal(value,success):
    require(type(value) is dict and value['schema']=='staged_saved_F_namespace_terminal_observation_v1'
        and value['authority']=='DRAFT_NONAUTHORITATIVE','original namespace terminal observation required')
    require(value['resource_phase']=='CLOSED' and value['namespace_phase']==value['inputs_phase']=='CONSUMED',
        'closed runtime/resource and transferred namespace required')
    if success:require(value['runtime_phase']=='CLOSED' and value['failure_absent'] is True,'successful runtime close required')
    else:require(value['runtime_phase'] in ('CLOSED','UNRESOLVED')
        and value['failure_absent'] is (value['runtime_phase']=='CLOSED'),'retained runtime failure state required')
    for key in ('cleanup_started','resource_owner_same','namespace_same','peer_same','source_same',
            'successor_same','resource_same','registry_same','actual_key_absent','reference_key_absent'):
        require(value[key] is True,'namespace terminal invariant failed: '+key)
    require(value['reference_registered'] is False and value['pending']==[False,False]
        and all(type(item) is bool for item in value['pending'])
        and value['actual_aliases']==value['reference_aliases']==[],'namespace aliases or native handles remain')
    return value
'''


def replace(source,before,after,count=1):
    assert source.count(before)==count,(before,source.count(before),count)
    return source.replace(before,after)


def graph_source():
    spec=importlib.util.spec_from_file_location('_static_terminal_graph_budget',ROOT/'experiments/staged_rts24_saved_fresh_construction_graph_budget_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return '\n\ndef construction_graph_contract():\n    return '+repr(module.contract())+'\n'


def namespace(source):return replace(source,'not 0 <= count < 40:','not 0 <= count < 43:').encode('utf8')


def lifecycle(source):
    source=replace(source,"require(producer._owner._namespace._phase=='CLOSED','ENTRY namespace close incomplete')",
        'require_namespace_terminal(namespace_terminal_snapshot(producer._owner,producer._consumer_plan[2]),primary is None)')
    return (source+TERMINAL_SOURCE).encode('utf8')


def construction(source):
    old="LIFECYCLE_SUCCESSOR_PIN=(41243,'4130f1635d1887f66feea46fe8e8f86537d1d1e4515941367936ac94564f88a8')"
    raw=lifecycle((ROOT/PAIRS[1][1]).read_text(encoding='utf8'))
    return replace(source,old,'LIFECYCLE_SUCCESSOR_PIN='+repr((len(raw),sha256(raw).hexdigest()))).encode('utf8')


def loader(source):return source.encode('utf8')


def common(source):
    source=replace(source,OLD_OUT,NEW_OUT,source.count(OLD_OUT))
    for before,after in (('entry_namespace_consumer_v2.py','entry_namespace_consumer_v3.py'),
            ('producer_bootstrap_v3.py','producer_bootstrap_v4.py'),('retained_producer_v2.py','retained_producer_v3.py'),
            ('project_bootstrap_loader_v1.py','project_bootstrap_loader_v2.py')):
        if before in source:source=replace(source,before,after,source.count(before))
    return source


def core(source):
    source=common(source)
    source=replace(source,"import_profile producer_helpers case'","import_profile producer_helpers graph_contract case'")
    source=replace(source,'staged_saved_F_project_construction_manifest_v1','staged_saved_F_project_construction_manifest_v2')
    source=replace(source,'    check_producer_helpers(plan);return plan',
        "    check_producer_helpers(plan);require(canonical(plan['graph_contract'])==canonical(construction_graph_contract()),'exact graph contract required');return plan")
    return (source+graph_source()).encode('utf8')


def probe(source):
    source=common(source)
    source=replace(source,'staged_saved_F_project_construction_probe_v1','staged_saved_F_project_construction_probe_v2')
    source=replace(source,'construction_result=None','construction_result=None;namespace_terminal=None',1)
    source=replace(source,'    remaining=[48]',
        "    try:namespace_terminal=namespace_terminal_snapshot(runtime,namespace)\n    except BaseException as error:secondary.append(error)\n    remaining=[48]")
    source=replace(source,'        construction_result=construction_result,consumer_state=',
        '        construction_result=construction_result,namespace_terminal=namespace_terminal,consumer_state=')
    source=replace(source,"if __name__=='__main__':_probe_main()",TERMINAL_SOURCE+"\n\nif __name__=='__main__':_probe_main()")
    return source.encode('utf8')


def parent(source):
    source=common(source)
    source=replace(source,'lease_v40.py','lease_v41.py')
    source=replace(source,'probe_v38.py','probe_v39.py')
    source=replace(source,"def save(path,value):\n    with path.open('xb') as stream:stream.write(canonical(value))",
        "def save(path,value):\n    raw=canonical(value);assert len(raw)<=1048576,'diagnostic artifact byte cap'\n    with path.open('xb') as stream:stream.write(raw)")
    source=replace(source,'staged_saved_F_project_construction_manifest_v1','staged_saved_F_project_construction_manifest_v2')
    source=replace(source,'producer_helpers=producer_references(),case=case)',
        'producer_helpers=producer_references(),graph_contract=construction_graph_contract(),case=case)')
    source=replace(source,'staged_rts24_saved_fresh_consumer_binding_validation_v2.py','staged_rts24_saved_fresh_construction_validation_v1.py')
    source=replace(source,"    raise ValueError('construction parent terminal oracle and workflow admission remain open')",
        '    return POST.compare(SimpleNamespace(**globals()),case,code,stdout,stderr,child_code,identity,argv,writer_errors)')
    # Both cases now share the terminal oracle; this closes the old discovery
    # shortcut that could accept rc0 without the full parent/child relation.
    source=replace(source,"    if case in ('import_discovery','normal') and primary is None:",
        "    if case in ('discovery','import_discovery') and primary is None:")
    source=replace(source,"    assert plan['producer_helpers']==producer_references()",
        "    assert plan['producer_helpers']==producer_references() and plan['graph_contract']==construction_graph_contract()")
    source=replace(source,"    reference_before=reference_after=None","    context_before=context_after=None")
    source=replace(source,"        if case=='normal':\n            from types import SimpleNamespace\n            reference_before=REFERENCE.context(SimpleNamespace(**globals()),code,plan,actual)",
        "        from types import SimpleNamespace\n        context_before=POST.context(SimpleNamespace(**globals()),case,code,argv)[2]")
    source=replace(source,"    if case=='normal' and reference_before is not None:\n        try:\n            from types import SimpleNamespace\n            reference_after=REFERENCE.context(SimpleNamespace(**globals()),code,plan,actual)\n            assert reference_after==reference_before",
        "    if context_before is not None:\n        try:\n            from types import SimpleNamespace\n            context_after=POST.context(SimpleNamespace(**globals()),case,code,argv)[2]\n            assert context_after==context_before")
    source=replace(source,"record=dict(reference_before=reference_before,reference_after=reference_after,authority=",
        "record=dict(schema='staged_saved_F_construction_parent_receipt_v1',context_before=context_before,context_after=context_after,profile_publication=None,authority=")
    start=source.index('    started=time.perf_counter(); code=transport();',source.index('def one_case('))
    end=source.index("    context_before=context_after=None\n    try:\n",start)
    preflight=source[start:end]
    preparation=preflight[preflight.index('code=transport();'):preflight.index('    api=process_api();')]
    preparation=preparation.replace('code=transport();','code=transport();',1)
    source=source[:start]+'''    started=time.perf_counter();code=plan=expected=actual=argv=api=None
    process=writer=None;writer_errors=[];released=[False];stdin_closed=[False]
    stdout=stderr=b'';child_code=identity=observation=None;closed=False;primary=None;cleanup=[];result=memory=drain_reason=None
'''+source[end:]
    preparation='\n'.join('        '+line.lstrip() if index==0 else '    '+line
        for index,line in enumerate(preparation.rstrip().splitlines()))
    source=replace(source,'    context_before=context_after=None\n    try:\n',
        '    context_before=context_after=None\n    try:\n'+preparation+'\n        api=process_api()\n')
    source=replace(source,'plan_pin=pin(actual),expected_manifest_pin=pin(expected),transport_pin=pin(code),',
        'plan_pin=None if actual is None else pin(actual),expected_manifest_pin=None if expected is None else pin(expected),transport_pin=None if code is None else pin(code),')
    source=replace(source,"    if case in ('discovery','import_discovery','normal'): save(OUT/('probe_'+case+'.receipt.json'),record)",'''    from types import SimpleNamespace
    POST.finalize_profile(SimpleNamespace(**globals()),record,started,seconds,time.perf_counter)
    if case in ('discovery','import_discovery','normal'): save(OUT/('probe_'+case+'.receipt.json'),record)''')
    return (source+graph_source()).encode('utf8')


def current():
    result={}
    for name,before,after in PAIRS:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf8'))
        assert (ROOT/after).read_bytes()==raw,'terminal successor differs'
        compile(raw,str(ROOT/after),'exec',dont_inherit=True,optimize=0)
        result[after]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    return None,dict(schema='staged_saved_F_construction_terminal_successors_v1',authority='DRAFT_NONAUTHORITATIVE',
        successor_pins=result,namespace_graph_stop=43,Source49_target_execs=0,P1_reads=0,
        issuer_implemented=False,whole_workflow_admitted=False,run_authority=False,formal_result=False,actual_F=False)


def create():
    for name,before,after in PAIRS:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf8'));compile(raw,str(ROOT/after),'exec',dont_inherit=True,optimize=0)
        path=ROOT/after
        if path.exists():assert path.read_bytes()==raw
        else:
            with path.open('xb') as stream:stream.write(raw)


if __name__=='__main__':create()
