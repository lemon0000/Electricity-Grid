"""Exact LC3 successor requiring a fixed, bootstrap-held permission program."""
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
BEFORE=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v3.py'
AFTER=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v4.py'
PERMISSION=ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'


ADDITION='''

def revoke_window(state,put):
    if state is not None and state.guard_phase!='CLOSED':put(state,'guard_phase','DENY')


def permission_revoke_spec():
    state=None if _P1_PERMISSION_PROGRAM is None else _P1_PERMISSION_PROGRAM[2][2]
    return revoke_window.__code__,{'__builtins__':{}},(state,object.__setattr__)


def retire_permission(producer):
    errors=[]
    # Retained before the first claim, independent of verifier/proof validity.
    try:
        spec=producer._permission_revoke
        FunctionType(spec[0],spec[1])(*spec[2])
    except BaseException as error:errors.append(('permission_revoke',error))
    try:permission_call(producer._owner,producer._authority,producer._consumer_plan,producer._snapshot,'retire')
    except BaseException as error:errors.append(('permission_retirement',error))
    return errors


def cancel_unclaimed(producer,primary):
    errors=retire_permission(producer)
    try:
        row=_LOCKS.get(id(producer))
        if row is not None:
            require(row[0] is producer and row[1] is producer._operation_lock,'original unclaimed lock row required')
            del _LOCKS[id(producer)]
    except BaseException as error:errors.append(('unclaimed_lock_release',error))
    if errors:raise primary from BaseExceptionGroup('permission retirement failures',tuple(error for _,error in errors))
    raise primary


def claim_permission(producer):
    try:permission_call(producer._owner,producer._authority,producer._consumer_plan,producer._snapshot,'claim')
    except BaseException as primary:cancel_unclaimed(producer,primary)


def claim_runtime_slot(producer):
    claim_permission(producer)
    try:
        commit(producer);reserve_state(producer._owner,'RUNNING',producer);commit(producer);entry(producer)
        return producer
    except BaseException as primary:
        if producer._claimed:fail(producer,primary)
        cancel_unclaimed(producer,primary)


def permission_call(owner,admission,plan,snapshot,stage):
    """No consumer-supplied callback/spec can authorize a P1 read."""
    require(stage in ('prepare','entry','claim','retire'),'closed permission verification stage required')
    require(type(_P1_PERMISSION_RAW) is bytes and pin(_P1_PERMISSION_RAW)==P1_PERMISSION_PIN,
        'bootstrap-held fixed permission source required')
    spec=_P1_PERMISSION_PROGRAM
    require(type(spec) is tuple and len(spec)==3 and type(spec[0]) is CodeType
        and type(spec[1]) is dict and type(spec[2]) is tuple and len(spec[2])==3,'held permission program required')
    require(type(_P1_PERMISSION_CODE) is CodeType and spec[0]==_P1_PERMISSION_CODE
        and set(spec[1])=={'FunctionType','__builtins__'} and spec[1]['FunctionType'] is FunctionType,
        'fixed permission dispatcher required')
    native=spec[1]['__builtins__'];expected_native=vars(builtins)
    require(type(native) is dict and set(native)==set(expected_native)
        and all(native[name] is value for name,value in expected_native.items()),'native permission interpreter roots required')
    operation='retire' if stage=='retire' else 'claim' if stage=='claim' else 'verify'
    args=(admission,) if stage=='retire' else (admission,owner,plan,snapshot,stage)
    row=FunctionType(spec[0],spec[1])(spec[2],operation,args)
    if stage!='retire':
        require(type(row) is tuple and len(row)==7 and row[0] is admission and row[1] is owner
            and row[2] is plan and row[3] is snapshot and row[4] is spec[2][2],
            'exact issuer registry row required')
    return row
'''


def replace(source,before,after):
    assert source.count(before)==1,(before,source.count(before))
    return source.replace(before,after)


def derive():
    source=BEFORE.read_text(encoding='utf8');raw=PERMISSION.read_bytes()
    source=replace(source,"_P1_AUTHORITY=globals().get('_P1_AUTHORITY')",
        "_P1_AUTHORITY=globals().get('_P1_AUTHORITY')\n_P1_PERMISSION_PROGRAM=globals().get('_P1_PERMISSION_PROGRAM')\n_P1_PERMISSION_RAW=globals().get('_P1_PERMISSION_RAW')\nP1_PERMISSION_PIN="+repr((len(raw),sha256(raw).hexdigest()))+"\n_P1_PERMISSION_CODE=(next(code for code in compile(_P1_PERMISSION_RAW,str(ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'),'exec',dont_inherit=True,optimize=0).co_consts if type(code) is CodeType and code.co_name=='program_dispatch') if type(_P1_PERMISSION_RAW) is bytes and (len(_P1_PERMISSION_RAW),sha256(_P1_PERMISSION_RAW).hexdigest())==P1_PERMISSION_PIN else None)")
    source=replace(source,"    require(producer._authority is _P1_AUTHORITY and _P1_AUTHORITY is not None,'producer admission was revoked')",
        "    permission_call(producer._owner,producer._authority,producer._consumer_plan,producer._snapshot,'entry')\n    require(producer._authority is _P1_AUTHORITY and _P1_AUTHORITY is not None,'producer admission was revoked')")
    source=replace(source,"    verify_runtime_rows();require(type(owner) is _RUNTIME_TYPE,'exact admitted runtime required')\n    runtime_call(owner,'entry')",
        "    verify_runtime_rows();require(type(owner) is _RUNTIME_TYPE,'exact admitted runtime required')\n    permission_call(owner,admission,owner._consumer_plan,_PROJECT_SNAPSHOT,'prepare')\n    runtime_call(owner,'entry')")
    source=replace(source,"""    _LOCKS[id(producer)]=(producer,producer._operation_lock)
    try:
        # Claim before returning any plan; a second producer cannot take the slot.
        commit(producer);reserve_state(owner,'RUNNING',producer);commit(producer);entry(producer)
        return producer
    except BaseException as primary:
        if producer._claimed:fail(producer,primary)
        raise""","""    _LOCKS[id(producer)]=(producer,producer._operation_lock)
    return claim_runtime_slot(producer)""")
    source=replace(source,"'_operation_lock','_operation_owner','_pending_reentry')",
        "'_operation_lock','_operation_owner','_pending_reentry','_permission_revoke')")
    source=replace(source,"id(producer._operation_lock),producer._operation_owner,id(producer._pending_reentry))",
        "id(producer._operation_lock),producer._operation_owner,id(producer._pending_reentry),id(producer._permission_revoke))")
    source=replace(source,"    for name,value in dict(_operation_lock=Lock(),_operation_owner=None,_pending_reentry=None).items():",
        "    for name,value in dict(_operation_lock=Lock(),_operation_owner=None,_pending_reentry=None,_permission_revoke=permission_revoke_spec()).items():")
    source=replace(source,"    object.__setattr__(producer,'_close_attempted',True);errors=[]",
        "    object.__setattr__(producer,'_close_attempted',True);errors=retire_permission(producer)")
    source=replace(source,"_snapshot=None,_authority=None,_phase='CLOSED'",
        "_snapshot=None,_authority=None,_permission_revoke=None,_phase='CLOSED'")
    source=replace(source,"roots=[item.co_name for item in unit.co_consts if type(item) is CodeType],",
        "roots=[item.co_name for item in unit.co_consts if type(item) is CodeType and not item.co_name.startswith('<')],")
    return (source+ADDITION).encode('utf8')


def current():
    raw=derive();assert AFTER.read_bytes()==raw,'permission lifecycle successor differs'
    compile(raw,str(AFTER),'exec',dont_inherit=True,optimize=0)
    return None,dict(schema='staged_saved_F_permission_lifecycle_successor_v1',authority='DRAFT_NONAUTHORITATIVE',
        pin=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),permission_source_pin=dict(bytes=PERMISSION.stat().st_size,sha256=sha256(PERMISSION.read_bytes()).hexdigest()),
        permission_on_prepare=True,permission_on_entry=True,retirement_before_cleanup=True,
        external_authorization_implemented=False,P1_reads=0,source49_target_modules_executed=0,
        actual_F=False,formal_result=False,run_authority=False,resource_admission=False)


if __name__=='__main__':
    raw=derive();compile(raw,str(AFTER),'exec',dont_inherit=True,optimize=0)
    with AFTER.open('xb') as stream:stream.write(raw)
