"""Creating-bootstrap orchestration, including the pre-LIVE failure window."""
import builtins
from hashlib import sha256
import json
import os
from threading import get_ident
from types import CodeType,FunctionType

_RUNTIME_TYPE=globals().get('_RUNTIME_TYPE')
_GUARD=globals().get('_GUARD')
_COORDINATOR_PROGRAM=globals().get('_COORDINATOR_PROGRAM')
_COORDINATOR_RAW=globals().get('_COORDINATOR_RAW')
COORDINATOR_PIN=(9264,'0362508e192c116eda5f4428ccbe53969ea23f3e24dc83f132db5e2d53b877f3')
FALSE_FIELDS=('external_permission_verified','parent_independent_P1_verified','role_bootstrap','permit_issued',
    'F_launch_admitted','full_P1_content_verified','independent_root_verified','native_authorized','production_seal',
    'startup_tcb_authenticated','parent_python_graph_attested','full_runtime_binding_verified',
    'run_authority','resource_admission','scientific_evidence_adopted','formal_result','actual_F')


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def pin(raw):return len(raw),sha256(raw).hexdigest()

def creator():return os.getpid(),get_ident()


def guard():
    require(type(_GUARD) is tuple and len(_GUARD)==3,'bootstrap-held original source guard required')
    FunctionType(_GUARD[0],_GUARD[1])(*_GUARD[2])
    require(type(_COORDINATOR_RAW) is bytes and pin(_COORDINATOR_RAW)==COORDINATOR_PIN,
        'fixed producer coordinator predecessor required')


def code_call(row,*args):
    code,context,defaults,kw=row
    function=FunctionType(code,context,'held_bootstrap_actor',defaults);function.__kwdefaults__=kw
    return function(*args)


def method_row(owner,name):
    function=vars(type(owner))[name]
    require(type(function) is FunctionType and function.__closure__ is None,'original runtime method required')
    return type(owner),name,function,(function.__code__,function.__globals__,function.__defaults__,function.__kwdefaults__)


def verify_methods(actor):
    for cls,name,function,row in actor._methods:
        require(vars(cls).get(name) is function and function.__code__ is row[0] and function.__globals__ is row[1]
            and function.__defaults__ is row[2] and function.__kwdefaults__ is row[3] and function.__closure__ is None,
            'original bootstrap runtime method changed')


def seal_program(namespace):
    rows=[];bindings=[]
    for name,value in namespace.items():
        if type(value) is FunctionType and value.__globals__ is namespace:
            require(value.__closure__ is None,'closed source-owned program function required')
            rows.append((name,value.__code__,value.__defaults__,None if value.__kwdefaults__ is None else tuple(value.__kwdefaults__.items())))
        else:bindings.append((name,value))
    return tuple(bindings),tuple(rows)


def program_context(program):
    # Reconstruct fresh functions from held CodeTypes, so replacing a private
    # convenience function cannot become dispatch or recovery authority.
    if type(program) is not tuple or len(program)!=2:raise ValueError('held source program required')
    context=dict(program[0])
    for name,code,defaults,kw in program[1]:
        if type(code) is not CodeType:raise ValueError('held original program CodeType required')
        function=FunctionType(code,context,name,defaults);function.__kwdefaults__=None if kw is None else dict(kw)
        context[name]=function
    return context


def program_call(program,name,*args):
    require(name in ('prepare_coordinator_cleanup','complete_producer','coordinator_revoke','coordinator_terminal'),
        'fixed coordinator operation required')
    context=program_context(program)
    rows=[row for row in program[1] if row[0]==name];require(len(rows)==1,'unique held coordinator operation required')
    _,code,defaults,kw=rows[0]
    function=FunctionType(code,context,'held_bootstrap_'+name,defaults);function.__kwdefaults__=None if kw is None else dict(kw)
    return function(*args)


def coordinator_call(actor,name,*args):return program_call(actor._coordinator_program,name,*args)


def permission_call(actor,operation,args):
    spec=actor._permission
    require(type(spec) is tuple and len(spec)==3 and type(spec[0]) is CodeType and type(spec[1]) is dict,
        'loader-held permission program required')
    return FunctionType(spec[0],spec[1])(spec[2],operation,args)


def bridge_call(actor,stage,args=()):
    spec=actor._bridge
    return FunctionType(spec[0],spec[1])(spec[2],stage,actor._owner,args)


class BootstrapActor:
    __slots__=('_creator','_owner','_bridge','_permission','_cleanup','_coordinator_program','_methods','_mode','_phase','_failure',
        '_secondary','_result','_terminal','_permission_report','_seal')
    def __new__(cls,*args,**kwargs):raise TypeError('use the creating pinned bootstrap')
    def __setattr__(self,name,value):raise AttributeError('bootstrap actor is frozen')
    def __delattr__(self,name):raise AttributeError('bootstrap actor is frozen')
    def __reduce__(self):raise TypeError('bootstrap actor is process-local')


def image(actor,changes=None):
    values={name:getattr(actor,name) for name in BootstrapActor.__slots__ if name!='_seal'}
    if changes:
        require(set(changes)<=set(values),'closed actor state update required');values.update(changes)
    return (values['_creator'],id(values['_owner']),id(values['_bridge']),id(values['_permission']),id(values['_cleanup']),id(values['_coordinator_program']),
        tuple((id(cls),name,id(function),tuple(id(value) for value in row)) for cls,name,function,row in values['_methods']),
        values['_mode'],values['_phase'],id(values['_failure']),tuple(id(error) for error in values['_secondary']),
        None if values['_result'] is None else pin(canonical(values['_result'])),
        None if values['_terminal'] is None else pin(canonical(values['_terminal'])),
        None if values['_permission_report'] is None else pin(canonical(values['_permission_report'])))


def commit(actor,**values):
    seal=pin(canonical(image(actor,values)))
    for name,value in values.items():object.__setattr__(actor,name,value)
    object.__setattr__(actor,'_seal',seal)


def new_actor(owner,bridge,permission,permission_raw,mode):
    guard()
    require(_RUNTIME_TYPE is not None and type(owner) is _RUNTIME_TYPE and owner._phase=='ADOPTED'
        and owner._creator[:2]==creator() and owner._cleanup_started is False,'same pre-import creating owner required')
    require(mode in ('import_discovery','producer'),'closed bootstrap actor mode required')
    require(type(bridge) is tuple and len(bridge)==3 and type(permission) is tuple and len(permission)==3,
        'loader-held original bridge and permission required')
    cleanup=program_call(_COORDINATOR_PROGRAM,'prepare_coordinator_cleanup',owner,permission,permission_raw)
    actor=object.__new__(BootstrapActor)
    values=dict(_creator=creator(),_owner=owner,_bridge=bridge,_permission=permission,_cleanup=cleanup,_coordinator_program=_COORDINATOR_PROGRAM,
        _methods=tuple(method_row(owner,name) for name in ('prepare_consumer','finish_import','close')),
        _mode=mode,_phase='ADOPTED',_failure=None,_secondary=(),_result=None,_terminal=None,_permission_report=None)
    for name,value in values.items():object.__setattr__(actor,name,value)
    commit(actor);return actor


def close_owned(actor,primary):
    """Independent denial and original close; never retry physical cleanup."""
    owner=actor._owner;cleanup=actor._cleanup;errors=[]
    _,_,_,state,revoke,held_close,revoke_code=cleanup
    try:coordinator_call(actor,'coordinator_revoke',revoke,state,revoke_code)
    except BaseException as error:errors.append(error)
    if state.guard_phase!='CLOSED':
        try:permission_call(actor,'retire',(state.admission,))
        except BaseException as error:errors.append(error)
    if owner._cleanup_started is False:
        try:code_call(held_close,owner,primary)
        except BaseException as error:
            expected=held_close[1].get('LocalRuntimeUnresolved')
            if not (primary is not None and expected is not None and type(error) is expected and error.owner is owner
                and error.primary is primary and not error.secondary):errors.append(error)
    try:
        terminal=coordinator_call(actor,'coordinator_terminal',owner)
        require(terminal['close_calls']==[1,1],'exactly one close per original native handle required')
        object.__setattr__(actor,'_terminal',terminal)
    except BaseException as error:errors.append(error)
    try:permission_call(actor,'close_guard',())
    except BaseException as error:errors.append(error)
    try:object.__setattr__(actor,'_permission_report',permission_call(actor,'report',()))
    except BaseException as error:errors.append(error)
    return errors


def fail(actor,primary):
    if actor._failure is not None:raise actor._failure
    try:errors=close_owned(actor,primary)
    except BaseException as error:errors=[error]
    try:commit(actor,_phase='FAILED',_failure=primary,_secondary=tuple(errors))
    except BaseException as error:
        errors.append(error)
        for name,value in dict(_phase='FAILED',_failure=primary,_secondary=tuple(errors)).items():object.__setattr__(actor,name,value)
        try:object.__setattr__(actor,'_seal',pin(canonical(image(actor))))
        except BaseException as secondary:
            errors.append(secondary);object.__setattr__(actor,'_secondary',tuple(errors))
    if errors:
        previous=primary.__cause__
        if previous is not None and all(previous is not error for error in errors):errors.insert(0,previous)
        raise primary from BaseExceptionGroup('bootstrap actor cleanup errors',tuple(errors))
    raise primary


def import_returned(actor,adapter,bindings,retention,observed_profile):
    owner=actor._owner
    require(actor._phase=='IMPORTING' and owner._phase=='IMPORTING' and owner._adapter is None,
        'single pre-LIVE import return required')
    require(owner._boundary._adapter is adapter and owner._boundary._runtime_bindings is bindings
        and owner._boundary._retention is retention and type(observed_profile) is bytes,
        'original returned boundary proof required')
    verify_methods(actor)
    if actor._mode=='producer':
        require(code_call(actor._methods[0][3],owner) is owner,'same IMPORTING consumer owner required')
        require(owner._phase=='IMPORTING' and owner._consume_state=='PREPARED','prepared consumer before LIVE required')
    observed=code_call(actor._methods[1][3],owner,adapter,bindings,retention)
    require(observed==observed_profile,'returned import profile differs')
    if actor._mode=='producer':
        require(owner._phase=='LIVE' and owner._import_profile_matched is True and owner._consume_state=='PREPARED',
            'independent profile-matched LIVE/PREPARED required')
        commit(actor,_phase='LIVE_PREPARED');return None
    require(owner._phase=='OBSERVED' and owner._consume_state is None,'unadmitted observation required')
    result=bridge_call(actor,'report');commit(actor,_phase='OBSERVED',_result=result)
    return json.loads(canonical(result))


def dispatch(actor,operation,args):
    require(type(actor) is BootstrapActor and actor._creator==creator(),'creating exact bootstrap actor required')
    require(type(args) is tuple,'closed actor arguments required')
    if operation=='observation':
        require(actor._phase in ('CLOSED','FAILED') and not args,'terminal actor observation required')
        require(actor._seal==pin(canonical(image(actor))),'terminal actor state differs')
        if actor._mode=='producer' and actor._phase=='CLOSED':
            require(type(actor._result) is dict and actor._result.get('schema')=='staged_saved_F_complete_producer_data_v2',
                'completed detached producer result required')
        value=dict(schema='staged_saved_F_bootstrap_actor_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
            phase=actor._phase,mode=actor._mode,terminal=actor._terminal,permission=actor._permission_report,
            secondary_count=len(actor._secondary),**{name:False for name in FALSE_FIELDS})
        return json.loads(canonical(value))
    if actor._failure is not None:raise actor._failure
    if actor._phase=='CLOSED':
        require(operation=='close' and args==(None,),'bootstrap actor is closed');return
    try:
        require(actor._seal==pin(canonical(image(actor))),'bootstrap actor state differs')
        guard();verify_methods(actor)
        if operation=='import_bridge':
            require(actor._phase=='ADOPTED' and not args,'pre-import held bridge required');return actor._bridge
        if operation=='install_guard':
            require(actor._phase=='ADOPTED' and len(args)==1 and args[0] is actor._owner._boundary,
                'single creating import boundary required')
            permission_call(actor,'install_guard',args);commit(actor,_phase='IMPORTING');return
        if operation=='import_returned':
            require(len(args)==4,'complete original import return required')
            return import_returned(actor,*args)
        if operation=='run':
            require(actor._phase=='LIVE_PREPARED' and actor._mode=='producer' and len(args)==2,
                'single prepared full producer invocation required')
            result=coordinator_call(actor,'complete_producer',actor._owner,actor._bridge,actor._permission,actor._cleanup,*args)
            object.__setattr__(actor,'_result',result)
            detached=json.loads(canonical(result))
            errors=close_owned(actor,None)
            if errors:raise BaseExceptionGroup('producer terminal observation errors',tuple(errors))
            commit(actor,_phase='CLOSED',_owner=None,_bridge=None,_permission=None,_cleanup=None,_coordinator_program=None,_methods=())
            return detached
        if operation=='close':
            require(len(args)==1 and (args[0] is None or isinstance(args[0],BaseException)),'original close reason required')
            if args[0] is not None:fail(actor,args[0])
            require(actor._mode=='import_discovery' and actor._phase=='OBSERVED','incomplete producer/bootstrap cannot close as success')
            errors=close_owned(actor,None)
            if errors:raise BaseExceptionGroup('bootstrap close errors',tuple(errors))
            commit(actor,_phase='CLOSED',_owner=None,_bridge=None,_permission=None,_cleanup=None,_coordinator_program=None,_methods=());return
        raise ValueError('unknown fixed bootstrap actor operation')
    except BaseException as primary:
        if actor._failure is not None:raise actor._failure
        fail(actor,primary)


def actor_dispatch(state,operation,args):
    program,actor,builder_code,dispatch_code=state
    isolated=dict(__builtins__=__builtins__,FunctionType=FunctionType,CodeType=CodeType)
    context=FunctionType(builder_code,isolated)(program)
    return FunctionType(dispatch_code,context)(actor,operation,args)
