"""Helper5 -> Helper6: finalize imports first; issue only from prepared LIVE."""
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
BEFORE=ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v5.py'
AFTER=ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v6.py'
LIFECYCLE=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v5.py'


def replace(source,before,after,count=1):
    assert source.count(before)==count,(before,source.count(before),count)
    return source.replace(before,after)


def derive():
    source=BEFORE.read_text(encoding='utf8')
    source=replace(source,'"""Unadmitted source construction and continuity; P1 prepare remains closed.\n\nThe creating bootstrap supplies its authenticated runtime type. This version\nrequires admission=None and issues no P1 token, hook, project import or P1 read.\n"""',
        '"""Deferred creating-bootstrap bundle; the fixed public issuer stays disabled.\n\nImport return finalizes construction. A prepared, profile-matched LIVE owner\nmay request bundle finalization inside the coordinator cleanup boundary.\n"""')
    old="LIFECYCLE_SUCCESSOR_PIN=(48565, '970e5918770c3d09b65447191ae2c68e047ca14551e891772e3548c8dc6f3f53')"
    raw=LIFECYCLE.read_bytes();new='LIFECYCLE_SUCCESSOR_PIN='+repr((len(raw),sha256(raw).hexdigest()))
    source=replace(source,old,new)
    source=replace(source,'"""All-or-fail preparation; no producer claim or P1 call occurs here."""',
        '"""Deferred fixed-issuer request; no producer slot or P1 content call."""')
    source=replace(source,"    require(admission is None and type(capture_code) is CodeType,'unadmitted construction bundle requires no P1 token')",
        """    require(admission is None and type(capture_code) is CodeType,'no caller P1 admission accepted')
    owner=plan._owner
    require(owner._phase=='LIVE' and owner._import_profile_matched is True and owner._consume_state=='PREPARED'
        and owner._consumer_plan is not None,'prepared profile-matched LIVE owner required')
    require(owner._resource.owner is owner and owner._resource.phase=='LIVE','same live resource owner required')""")
    source=replace(source,'    verify_bundle(plan,graph,snapshot,guard)\n    inject=dict(',
        """    verify_bundle(plan,graph,snapshot,guard)
    # No callback, local token, bool or profile data is an external root. The
    # pinned public program below always rejects issue. Future activation must
    # use a separately authorized source successor and a new observation schema.
    admission=permission_operation('issue',(owner,owner._consumer_plan,snapshot,owner._boundary))
    require(admission is not None,'genuine outer-issued diagnostic admission required')
    inject=dict(""")
    source=replace(source,"            state['bundle']=make_project_bootstrap_bundle(plan,state['graph'],state['graph_raw'],\n                state['lifecycle'],state['lifecycle_raw'],state['capture_code'],state['admission'])\n            state['phase']='BUNDLED'",
        "            state['phase']='READY'")
    start=source.index("        elif stage=='bundle':")
    end=source.index("        else:raise ValueError('unknown fixed import bridge stage')",start)
    source=source[:start]+'''        elif stage=='bundle':
            require(state['phase']=='READY' and not args,'single deferred bundle finalization required')
            state['bundle']=make_project_bootstrap_bundle(state['plan'],state['graph'],state['graph_raw'],
                state['lifecycle'],state['lifecycle_raw'],state['capture_code'],None)
            state['phase']='BUNDLED';state['seal']=pin(canonical(bridge_image(state)))
            return state['bundle']
        elif stage=='report':
            require(state['phase']=='READY' and not args,'finalized pre-admission construction required')
            plan=check(state['plan'],final=True)
            result=dict(schema='staged_saved_F_pre_admission_construction_v1',authority='DRAFT_NONAUTHORITATIVE',
                source_modules=len(plan._sources),loader_execs=plan._observed,
                entry_execs=plan._entry_proof[1]._exec_completed,bundle_phase=state['phase'],
                P1_reads=0,admission_present=False,**{name:False for name in FALSE_FIELDS})
            require(len(canonical(result))<=32768,'bounded pre-admission construction report required')
            return result
        elif stage=='release':
            require(state['phase']=='BUNDLED' and not args and runtime._phase=='CLOSED'
                and runtime._consume_state=='CONSUMED' and runtime._resource.phase=='CLOSED'
                and not any(runtime._resource.pending),'closed successful producer required before release')
            held=_P1_PERMISSION_PROGRAM
            require(held[2][2].guard_phase=='CLOSED' and held[2][2].phase=='RETIRED','closed permission required before release')
            for key in ('owner','plan','bundle','graph','graph_raw','lifecycle','lifecycle_raw','capture_code','admission'):
                state[key]=None
            state['phase']='RELEASED'
''' +source[end:]
    source=replace(source,"operation='unadmitted_construction_bundle_only'","operation='deferred_bundle_with_disabled_public_issue'")
    source=replace(source,"staged_saved_F_project_bootstrap_contract_v2","staged_saved_F_project_bootstrap_contract_v3")
    source+='''


P1_PERMISSION_PIN=(18952,'0fa4420f1fb3ccfd70f234d7276de79bd780ce796b708ea58c912ebb9a74f9c7')


def permission_operation(operation,args):
    """Exact fixed permission dispatcher; no injected authorization callback."""
    require(operation=='issue' and type(args) is tuple,'closed deferred permission operation required')
    require(type(_P1_PERMISSION_RAW) is bytes and pin(_P1_PERMISSION_RAW)==P1_PERMISSION_PIN,'fixed permission source required')
    spec=_P1_PERMISSION_PROGRAM
    require(type(spec) is tuple and len(spec)==3 and type(spec[0]) is CodeType and type(spec[1]) is dict
        and type(spec[2]) is tuple and len(spec[2])==3,'held permission program required')
    unit=compile(_P1_PERMISSION_RAW,str(ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'),
        'exec',dont_inherit=True,optimize=0)
    codes=[code for code in unit.co_consts if type(code) is CodeType and code.co_name==code.co_qualname=='program_dispatch']
    require(len(codes)==1 and spec[0]==codes[0] and set(spec[1])=={'__builtins__','FunctionType'}
        and spec[1]['FunctionType'] is FunctionType,'fixed permission dispatch code required')
    native=spec[1]['__builtins__'];expected=vars(builtins)
    require(type(native) is dict and set(native)==set(expected) and all(native[key] is value for key,value in expected.items()),
        'native permission interpreter required')
    return FunctionType(spec[0],spec[1])(spec[2],operation,args)
'''
    return source.encode('utf8')


def current():
    raw=derive();assert AFTER.read_bytes()==raw,'deferred bundle successor differs'
    compile(raw,str(AFTER),'exec',dont_inherit=True,optimize=0)
    return None,dict(schema='staged_saved_F_deferred_bundle_successor_v1',authority='DRAFT_NONAUTHORITATIVE',
        source_pin=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),after_import='READY',
        bundle_requires='profile_matched_LIVE_PREPARED',public_issuer='DISABLED',
        actual_P1_read=False,external_permission_verified=False,formal_result=False,run_authority=False,actual_F=False)


if __name__=='__main__':
    raw=derive();compile(raw,str(AFTER),'exec',dont_inherit=True,optimize=0)
    with AFTER.open('xb') as stream:stream.write(raw)
