"""Versioned bootstrap wiring. No target module or Native diagnostic is run."""
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
NATIVE_ROOT='results/tables/staged_rts24_saved_fresh_complete_bootstrap_native_v2_non_authoritative'
GRAPH_CONTRACT=dict(schema='staged_saved_F_bootstrap_graph_stop_contract_v1',graph_call_stop=256,
    graph_image_bytes_stop=4194304,prior_construction_calls=43,observed_complete_calls=None,whole_workflow_admitted=False)


def replace(source,before,after,count=1):
    assert source.count(before)==count,(before,source.count(before),count)
    return source.replace(before,after)


def loader():
    source=(ROOT/'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v3.py').read_text(encoding='utf8')
    source=replace(source,"('utilities','lifecycle','project_graph','construction','capture','p1_permission')",
        "('utilities','lifecycle','project_graph','construction','capture','p1_permission','coordinator','bootstrap_actor')",2)
    source=replace(source,"        extra=dict(_RUNTIME_TYPE=LocalRuntimeInputs) if key=='construction' else {}",
        "        extra=dict(_RUNTIME_TYPE=LocalRuntimeInputs) if key in ('construction','bootstrap_actor') else {}")
    source=replace(source,'    return bridge,permission_program',
        """    actor_context=utility['_private_functions'](vars(modules['bootstrap_actor']))
    actor_context['_GUARD']=(function_code('utilities','_verify_programs'),isolated,
        (witnesses,function_code('utilities','_metadata')))
    actor_context['_COORDINATOR_RAW']=held['coordinator']
    seal_program=FunctionType(function_code('bootstrap_actor','seal_program'),actor_context)
    actor_context['_COORDINATOR_PROGRAM']=seal_program(vars(modules['coordinator']))
    actor=FunctionType(function_code('bootstrap_actor','new_actor'),actor_context)(
        runtime,bridge,permission_program,held['p1_permission'],plan['case'])
    verify(witnesses,function_code('utilities','_metadata'))
    return function_code('bootstrap_actor','actor_dispatch'),dict(isolated,CodeType=CodeType),(seal_program(actor_context),actor,
        function_code('bootstrap_actor','program_context'),function_code('bootstrap_actor','dispatch'))""")
    return source.encode('utf8')


def helper_paths(source):
    source=source.replace('staged_rts24_saved_fresh_project_bootstrap_loader_v3.py','staged_rts24_saved_fresh_project_bootstrap_loader_v5.py')
    source=source.replace('staged_rts24_saved_fresh_producer_bootstrap_v5.py','staged_rts24_saved_fresh_producer_bootstrap_v7.py')
    source=source.replace('staged_rts24_saved_fresh_retained_producer_v4.py','staged_rts24_saved_fresh_retained_producer_v6.py')
    source=replace(source,"        p1_permission=str(ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'),",
        """        p1_permission=str(ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'),
        coordinator=str(ROOT/'experiments/staged_rts24_saved_fresh_complete_producer_v2.py'),
        bootstrap_actor=str(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_actor_v2.py'),""")
    return source


def core():
    source=(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v42.py').read_text(encoding='utf8')
    source=source.replace('results/tables/staged_rts24_saved_fresh_guarded_project_construction_v1_non_authoritative',NATIVE_ROOT)
    source=source.replace('staged_rts24_saved_fresh_entry_namespace_consumer_v3.py','staged_rts24_saved_fresh_entry_namespace_consumer_v4.py')
    source=replace(source,"plan['case'] in ('discovery','import_discovery'), 'closed diagnostic case'",
        "plan['case'] in ('discovery','import_discovery','producer'), 'closed diagnostic case'")
    source=source.replace('staged_saved_F_project_construction_manifest_v3','staged_saved_F_complete_bootstrap_manifest_v1')
    source=replace(source,"    check_producer_helpers(plan);require(canonical(plan['graph_contract'])==canonical(construction_graph_contract()),'exact graph contract required');return plan",
        "    require(plan['case']!='producer' or plan['import_profile']['path']==str(ROOT/'"+NATIVE_ROOT+"/import_profile.json'),'independent complete-bootstrap import profile required');check_producer_helpers(plan);require(canonical(plan['graph_contract'])==canonical(construction_graph_contract()),'exact graph contract required');return plan")
    source=helper_paths(source)
    start=source.index('def construction_graph_contract():')
    source=source[:start]+'def construction_graph_contract():\n    return '+repr(GRAPH_CONTRACT)+'\n'
    return source.encode('utf8')


def namespace():
    source=(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v3.py').read_text(encoding='utf8')
    return replace(source,'not 0 <= count < 43:','not 0 <= count < 256:').encode('utf8')


def probe():
    source=(ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v40.py').read_text(encoding='utf8')
    source=source.replace('results/tables/staged_rts24_saved_fresh_guarded_project_construction_v1_non_authoritative',NATIVE_ROOT)
    source=replace(source,'permission_program=None;permission_observation=None',
        'permission_observation=None;bootstrap_actor=None;actor_observation=None;producer_result=None')
    source=replace(source,'            bridge,permission_program=prepare_project_bridge(runtime,plan,_compile,_exec)',
        """            bootstrap_actor=prepare_project_bridge(runtime,plan,_compile,_exec)
            def actor_call(operation,args=()):
                return FunctionType(bootstrap_actor[0],bootstrap_actor[1])(bootstrap_actor[2],operation,args)
            bridge=actor_call('import_bridge')""")
    source=replace(source,"            FunctionType(permission_program[0],permission_program[1])(permission_program[2],'install_guard',(boundary,))",
        "            actor_call('install_guard',(boundary,))")
    before="""            bs_helper.trace_import_stage(runtime,'before_finish_import');require(runtime.finish_import(adapter,adapter_bindings,retention)==observed_profile,'runtime profile/phase differs')
            runtime.entry();observed=runtime._phase;was_live=observed=='LIVE';bs_helper.trace_import_stage(runtime,'after_finish_import')
            phase='PROJECT_REPORT'
            bundle=FunctionType(bridge[0],bridge[1])(bridge[2],'bundle',runtime,())
            require(bundle[2][3][2][0]['_P1_AUTHORITY'] is None,'construction must remain unadmitted')
            construction_result=FunctionType(bridge[0],bridge[1])(bridge[2],'report',runtime,())"""
    after="""            bs_helper.trace_import_stage(runtime,'before_finish_import')
            construction_result=actor_call('import_returned',(adapter,adapter_bindings,retention,observed_profile))
            observed=runtime._phase;was_live=observed=='LIVE';bs_helper.trace_import_stage(runtime,'after_finish_import')
            if plan['case']=='producer':
                phase='PRODUCER'
                from time import monotonic
                producer_result=actor_call('run',(ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01',monotonic()))
            else:phase='PROJECT_REPORT'"""
    source=replace(source,before,after)
    source=replace(source,"            try:runtime_close[0](runtime_close[1],runtime_close[2],'held_runtime_final_close',runtime_close[3])(runtime,primary)",
        """            try:
                if bootstrap_actor is not None:
                    actor_call('close',(primary,))
                elif not runtime._cleanup_started:
                    runtime_close[0](runtime_close[1],runtime_close[2],'held_runtime_final_close',runtime_close[3])(runtime,primary)""")
    before="""        if permission_program is not None:
            try:FunctionType(permission_program[0],permission_program[1])(permission_program[2],'close_guard',())
            except BaseException as error:secondary.append(error)
            try:permission_observation=FunctionType(permission_program[0],permission_program[1])(permission_program[2],'report',())
            except BaseException as error:secondary.append(error)
"""
    source=replace(source,before,"""        if bootstrap_actor is not None:
            try:
                actor_observation=actor_call('observation')
                permission_observation=actor_observation['permission']
            except BaseException as error:secondary.append(error)
""")
    source=replace(source,"construction_result=construction_result,namespace_terminal=namespace_terminal,permission_observation=permission_observation,consumer_state=",
        "construction_result=construction_result,bootstrap_actor=actor_observation,producer_result=producer_result,namespace_terminal=namespace_terminal,permission_observation=permission_observation,consumer_state=")
    source=source.replace('staged_saved_F_project_construction_probe_v3','staged_saved_F_complete_bootstrap_probe_v1')
    source=replace(source,"require(len(encoded)<=131072,'runtime diagnostic report cap')",
        "require(len(encoded)<=327680,'complete bootstrap canonical report cap')")
    return source.encode('utf8')


def drain():
    source=(ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py').read_text(encoding='utf8')
    source=replace(source,'STDOUT_CAP=131072\nSTDERR_CAP=32768','STDOUT_CAP=327681\nSTDERR_CAP=131072')
    source=replace(source,'caps=(131072,32768)):', 'caps=(327681,131072)):')
    return source.encode('utf8')


def outputs():
    return dict((ROOT/path,raw) for path,raw in (
        ('experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v5.py',loader()),
        ('experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py',core()),
        ('experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py',namespace()),
        ('tests/staged_rts24_saved_fresh_runtime_handoff_probe_v42.py',probe()),
        ('experiments/staged_rts24_saved_fresh_memory_drain_v2.py',drain())))


def current():
    pins={}
    for path,raw in outputs().items():
        assert path.read_bytes()==raw,'bootstrap wiring successor differs: '+str(path)
        compile(raw,str(path),'exec',dont_inherit=True,optimize=0)
        pins[str(path)]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    return None,dict(schema='staged_saved_F_bootstrap_actor_wiring_contract_v1',authority='DRAFT_NONAUTHORITATIVE',
        sources=pins,graph_stop_contract=GRAPH_CONTRACT,native_root=NATIVE_ROOT,stdout_cap=327681,stderr_cap=131072,
        external_permission_verified=False,actual_P1_read=False,native_execution=False,run_authority=False,
        resource_admission=False,formal_result=False,actual_F=False)


if __name__=='__main__':
    for path,raw in outputs().items():
        compile(raw,str(path),'exec',dont_inherit=True,optimize=0)
        if path.exists():assert path.read_bytes()==raw,'existing successor must remain frozen'
        else:
            with path.open('xb') as stream:stream.write(raw)
