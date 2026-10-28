"""Retained producer program; real bootstrap admission is a separate prerequisite."""
import ast
import builtins
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import get_ident,Lock
from types import CodeType,FunctionType,ModuleType

ROOT=Path(__file__).absolute().parents[1]
ENTRY='experiments/staged_rts24_saved_fresh_adoption_v1.py'
ADAPTER='src/staged_rts24_saved_fresh_adoption_v1.py'
SOURCE_EPOCH='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
_RUNTIME_TYPE=globals().get('_RUNTIME_TYPE')
_P1_AUTHORITY=globals().get('_P1_AUTHORITY')
_ADMITTED_OWNER=globals().get('_ADMITTED_OWNER')
_CAPTURE_CODE=globals().get('_CAPTURE_CODE')
_GRAPH_MODULE=globals().get('_GRAPH_MODULE')
_PROJECT_SNAPSHOT=globals().get('_PROJECT_SNAPSHOT')
_GUARD=globals().get('_GUARD')
_LOCK_TYPE=type(Lock())
_LOCKS=globals().get('_LOCKS')
_TERMINALS=globals().get('_TERMINALS')
_BRAND=object()
_CLAIM_LOCK=Lock()
FALSE_FIELDS=('producer_capability_verified','initial_project_state_authenticated','full_runtime_binding_verified',
    'full_P1_content_verified','role_bootstrap','permit_issued','run_authority','resource_admission',
    'scientific_evidence_adopted','formal_result','actual_F')


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return (len(raw),sha256(raw).hexdigest())


def function_row(namespace,name):
    function=namespace[name]
    require(type(function) is FunctionType and function.__globals__ is namespace,'fixed original function globals required')
    require(function.__closure__ is None,'closed original function required')
    return namespace,name,function,function.__code__,function.__defaults__,function.__kwdefaults__,canonical(function.__kwdefaults__)


def verify_rows(rows):
    for namespace,name,function,code,defaults,kwdefaults,kwraw in rows:
        require(namespace.get(name) is function and type(function) is FunctionType and function.__globals__ is namespace
            and function.__code__ is code and function.__defaults__ is defaults and function.__kwdefaults__ is kwdefaults
            and canonical(function.__kwdefaults__)==kwraw and function.__closure__ is None,'producer function identity or metadata changed')


def _runtime_rows():
    if _RUNTIME_TYPE is None:return ()
    rows=[]
    for name in ('entry','source_bookend','close'):
        function=vars(_RUNTIME_TYPE)[name]
        require(type(function) is FunctionType,'original runtime method required')
        rows.append((_RUNTIME_TYPE,name,function,function.__code__,function.__defaults__,function.__kwdefaults__,canonical(function.__kwdefaults__)))
    entry=rows[0][2];context=entry.__globals__
    require(type(entry.__defaults__) is tuple and len(entry.__defaults__)==7,'fixed runtime entry signature required')
    seal=context.get('runtime_seal')
    require(type(seal) is FunctionType and seal.__code__ is entry.__defaults__[0] and seal.__defaults__ is entry.__defaults__[3],
        'original held runtime seal required')
    rows.append((context,'runtime_seal',seal,seal.__code__,seal.__defaults__,seal.__kwdefaults__,canonical(seal.__kwdefaults__)))
    return tuple(rows)


_RUNTIME_ROWS=_runtime_rows()
_GRAPH_ROW=None if _GRAPH_MODULE is None else function_row(vars(_GRAPH_MODULE),'check')


def verify_runtime_rows():
    require(_RUNTIME_TYPE is not None and len(_RUNTIME_ROWS)==4,'bootstrap runtime bindings are unavailable')
    for namespace,name,function,code,defaults,kwdefaults,kwraw in _RUNTIME_ROWS:
        current=namespace.get(name) if type(namespace) is dict else vars(namespace).get(name)
        require(current is function and function.__code__ is code and function.__defaults__ is defaults
            and function.__kwdefaults__ is kwdefaults and canonical(function.__kwdefaults__)==kwraw,
            'original runtime dispatch changed')


def runtime_call(owner,name,*args):
    verify_runtime_rows();row=next(row for row in _RUNTIME_ROWS if row[1]==name)
    return FunctionType(row[3],row[2].__globals__,'held_producer_'+name,row[4])(owner,*args)


def reserve_state(owner,state,producer=None):
    require(_CLAIM_LOCK.acquire(False),'producer claim is already in progress')
    try:
        verify_runtime_rows();seal=_RUNTIME_ROWS[3]
        require(owner._creator[:2]==(os.getpid(),get_ident()),'creating owner thread required')
        require(runtime_call(owner,'entry') is owner,'exact live producer runtime required')
        if state=='RUNNING':
            require(type(producer) is RetainedProducer and producer._owner is owner and owner._consume_state=='PREPARED','single creating producer claim required')
            commit(producer,_claimed=True)
        object.__setattr__(owner,'_consume_state',state)
        value=FunctionType(seal[3],seal[2].__globals__,'held_producer_runtime_seal',seal[4])(owner)
        object.__setattr__(owner,'_seal',value)
        runtime_call(owner,'entry')
    finally:_CLAIM_LOCK.release()


class RetainedProducerFailure(RuntimeError):
    __slots__=('primary','secondary','producer','runtime_close','_seal')
    def __init__(self,producer,primary,secondary):
        object.__setattr__(self,'primary',primary);object.__setattr__(self,'secondary',tuple(secondary));object.__setattr__(self,'producer',producer)
        object.__setattr__(self,'runtime_close',None);object.__setattr__(self,'_seal',None)
        super().__init__('retained producer failed or cleanup unresolved')
    def __setattr__(self,name,value):
        if name in ('__traceback__','__cause__','__context__','__suppress_context__'):object.__setattr__(self,name,value)
        else:raise AttributeError('producer failure evidence is frozen')
    def __delattr__(self,name):raise AttributeError('producer failure evidence is frozen')
    def __reduce__(self):raise TypeError('producer failures retain process-local objects')


class RetainedProducer:
    __slots__=('_owner','_consumer_plan','_binding','_adapter','_module','_roots','_source','_capture','_creator','_brand','_authority','_claimed',
        '_phase','_busy','_close_attempted','_failure','_expectation','_context','_context_sha','_held','_snapshot','_evidence','_seal',
        '_operation_lock','_operation_owner','_pending_reentry')
    def __new__(cls,*args,**kwargs):raise TypeError('prepare a producer from the creating bootstrap')
    def __setattr__(self,name,value):raise AttributeError('producer ownership fields are frozen')
    def __delattr__(self,name):raise AttributeError('producer ownership fields are frozen')
    def __reduce__(self):raise TypeError('producer capability cannot be serialized')
    def __copy__(self):raise TypeError('producer capability cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('producer capability cannot be copied')

    def run(self,output_root,*,started):raise TypeError('use the bootstrap-held dispatch CodeType')
    def bookend(self,stage):raise TypeError('use the bootstrap-held dispatch CodeType')
    def close(self):raise TypeError('use the bootstrap-held dispatch CodeType')


def image(producer):
    return (tuple(id(getattr(producer,name)) for name in ('_owner','_consumer_plan','_binding','_adapter','_module','_roots','_source','_capture','_snapshot','_brand')),
        producer._creator,producer._phase,producer._busy,producer._close_attempted,id(producer._failure),
        id(producer._expectation),None if producer._context is None else pin(producer._context),producer._context_sha,id(producer._held),
        None if producer._source is None else pin(canonical(producer._source)),id(producer._authority),producer._claimed,pin(canonical(producer._evidence)),
        id(producer._operation_lock),producer._operation_owner,id(producer._pending_reentry))


def failure_image(failure):
    return id(failure.primary),tuple((label,id(error)) for label,error in failure.secondary),id(failure.producer),id(failure.runtime_close)


def verified_failure(producer):
    terminal=None if _TERMINALS is None else _TERMINALS.get(id(producer))
    failure=producer._failure if terminal is None else terminal[1]
    require(type(failure) is RetainedProducerFailure and failure.producer is producer,'original sticky failure required')
    require(failure._seal is not None and failure._seal==failure_image(failure),'sticky failure evidence changed')
    return failure


def commit(producer,*,terminal=False,**changes):
    if producer._failure is not None and not terminal:raise producer._failure
    for name,value in changes.items():object.__setattr__(producer,name,value)
    object.__setattr__(producer,'_seal',pin(canonical(image(producer))))


def entry(producer,*,busy=False):
    require(type(producer) is RetainedProducer and producer._brand is _BRAND and producer._creator==(os.getpid(),get_ident()),'creating exact retained producer required')
    if producer._failure is not None:raise verified_failure(producer)
    if producer._pending_reentry is not None:raise producer._pending_reentry
    check_guard(_GUARD)
    require(producer._seal==pin(canonical(image(producer))),'producer immutable state differs')
    require(producer._authority is _P1_AUTHORITY and _P1_AUTHORITY is not None,'producer admission was revoked')
    require(producer._phase not in ('CLOSED','FAILED','UNRESOLVED') and producer._busy is busy,'producer phase is unavailable or reentrant')
    verify_runtime_rows();verify_rows(producer._roots)
    require(type(producer._capture) is FunctionType and producer._capture.__code__ is _CAPTURE_CODE
        and producer._capture.__globals__ is vars(producer._module) and producer._capture.__defaults__ is None
        and producer._capture.__kwdefaults__ is None and producer._capture.__closure__ is None,'private capture function changed')
    require(type(producer._owner) is _RUNTIME_TYPE and producer._owner._consume_state=='RUNNING'
        and producer._owner is _ADMITTED_OWNER
        and producer._owner._consumer_plan is producer._consumer_plan and producer._consumer_plan[0] is producer._owner
        and producer._consumer_plan[8] is producer._binding and producer._consumer_plan[4] is producer._adapter
        and producer._owner._namespace.module is producer._module,'original producer owner or binding differs')
    require(runtime_call(producer._owner,'entry') is producer._owner,'live retained runtime required')
    require(producer._owner._phase=='LIVE' and producer._owner._import_profile_matched,'profile-matched LIVE producer required')
    require(_GRAPH_ROW is not None and _GRAPH_MODULE is not None and producer._snapshot is _PROJECT_SNAPSHOT,'bootstrap project lease unavailable')
    require(type(producer._snapshot) is _GRAPH_MODULE.ProducerProjectSnapshot and producer._snapshot._registry is sys.modules,
        'actual project snapshot registry required')
    selected={name[:-3].replace('/','.').removesuffix('.__init__'):name for name in producer._source if name.startswith('src/') and name.endswith('.py')}
    selected[ENTRY[:-3].replace('/','.')]=ENTRY
    require(len(selected)==37 and {name for name,_ in producer._snapshot._modules}==set(selected),'complete producer project module set required')
    held_sources=dict(producer._owner._sources)
    require(dict(producer._snapshot._sources)=={name:(relative,held_sources[relative]) for name,relative in selected.items()},'project snapshot source binding differs')
    for name,module in producer._snapshot._modules:require(sys.modules.get(name) is module,'actual producer project module registry changed')
    require(dict(producer._snapshot._modules)[ENTRY[:-3].replace('/','.')] is producer._module
        and dict(producer._snapshot._modules)[ADAPTER[:-3].replace('/','.')] is producer._adapter,'project snapshot producer modules differ')
    verify_rows((_GRAPH_ROW,));report=_GRAPH_ROW[2](producer._snapshot)
    require(report['structure_and_identity_stable'] is True,'project continuity failed')
    require(runtime_call(producer._owner,'source_bookend')==producer._source,'producer source expectation changed')
    return producer


def root(module,name,relative,raw,compiled):
    require(type(module) is ModuleType and vars(module).get('__file__')==str(ROOT/relative),'fixed producer source module required')
    if relative not in compiled:compiled[relative]=compile(raw,str(ROOT/relative),'exec',dont_inherit=True,optimize=0)
    codes=[item for item in compiled[relative].co_consts if type(item) is CodeType and item.co_name==item.co_qualname==name]
    row=function_row(vars(module),name)
    require(len(codes)==1 and row[3]==codes[0],'original compiled producer function required')
    return row


def prepare(owner,admission):
    """No P1 reads; the genuine admission/initial-oracle issuer is not implemented here."""
    require(_P1_AUTHORITY is not None and admission is _P1_AUTHORITY and owner is _ADMITTED_OWNER,'bootstrap-held same-owner P1 diagnostic admission required')
    verify_runtime_rows();require(type(owner) is _RUNTIME_TYPE,'exact admitted runtime required')
    runtime_call(owner,'entry')
    require(owner._phase=='LIVE' and owner._import_profile_matched and owner._consume_state=='PREPARED','single profile-matched producer reservation required')
    plan=owner._consumer_plan
    require(type(plan) is tuple and len(plan)==13 and plan[0] is owner and plan[8][0] is plan[4]
        and owner._adapter is plan[4] and owner._namespace.module is plan[2].module,'original consumer binding required')
    source=dict(owner._sources);require(len(source)==len(owner._sources)==49,'complete held Source49 required')
    expected={name:dict(bytes=len(raw),sha256=sha256(raw).hexdigest()) for name,raw in source.items()}
    require(pin(canonical(expected))[1]==SOURCE_EPOCH,'fixed producer Source49 epoch required')
    require(type(_CAPTURE_CODE) is CodeType and _CAPTURE_CODE.co_name==_CAPTURE_CODE.co_qualname=='capture_saved_expectation_prebound'
        and _CAPTURE_CODE.co_argcount==2 and not _CAPTURE_CODE.co_freevars,'fixed prebound capture code required')
    compiled={};module=owner._namespace.module;adapter=owner._adapter
    rows=tuple(root(module,name,ENTRY,source[ENTRY],compiled) for name in
        ('context_from_saved_expectation','check_expectation_context','_expectation_binding_entry'))
    rows+=tuple(root(adapter,name,ADAPTER,source[ADAPTER],compiled) for name in ('hold','bookend','caller_image'))
    # Capture CodeType must equal the already verified source-derived v3 program.
    builder_path=ROOT/'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v3.py'
    builder_raw=builder_path.read_bytes()
    require(pin(builder_raw)==(10526,'f0fc5fc4c0f45fa6d962593da7b5e752b3568179a4d94213b2db5f02aa1758e6'),'frozen code derivation implementation required')
    context=dict(__file__=str(builder_path),__name__='_held_producer_code_oracle')
    exec(compile(builder_raw,str(builder_path),'exec',dont_inherit=True,optimize=0),context,context)
    code,report=context['current']();require(code==_CAPTURE_CODE and report['source_contract']['source_pins']==expected,'exact v3 prebound producer code differs')
    require(_GRAPH_ROW is not None and _PROJECT_SNAPSHOT is not None,'bootstrap project continuity snapshot required')
    producer=object.__new__(RetainedProducer)
    for name,value in dict(_owner=owner,_consumer_plan=plan,_binding=plan[8],_adapter=adapter,_module=module,_roots=rows,_source=expected,
            _capture=FunctionType(_CAPTURE_CODE,vars(module),'capture_saved_expectation_prebound'),_creator=(os.getpid(),get_ident()),_brand=_BRAND,
            _authority=admission,_claimed=False,
            _phase='PREPARED',_busy=False,_close_attempted=False,_failure=None,_expectation=None,_context=None,_context_sha=None,_held=None,
            _snapshot=_PROJECT_SNAPSHOT,_evidence=[]).items():object.__setattr__(producer,name,value)
    for name,value in dict(_operation_lock=Lock(),_operation_owner=None,_pending_reentry=None).items():object.__setattr__(producer,name,value)
    require(type(_LOCKS) is dict and not _LOCKS,'single bootstrap-held producer lock registry required')
    _LOCKS[id(producer)]=(producer,producer._operation_lock)
    try:
        # Claim before returning any plan; a second producer cannot take the slot.
        commit(producer);reserve_state(owner,'RUNNING',producer);commit(producer);entry(producer)
        return producer
    except BaseException as primary:
        if producer._claimed:fail(producer,primary)
        raise


def identity(producer):
    entry(producer,busy=True)
    expectation=producer._expectation;held=producer._held;module=producer._module;adapter=producer._adapter
    require(type(expectation) is vars(module)['SavedCallerExpectation'],'exact producer expectation required')
    expectation.entry()
    require(type(held) is vars(adapter)['HeldInput'] and type(held.image) is bytes and held.image==expectation.image
        and adapter.caller_image(held)==held.image,'exact HeldInput/caller-image join required')
    require(type(held.files) is dict and len(held.files)==683 and sum(row['bytes'] for row in held.files.values())==2950863
        and type(held.inventory) is dict and type(held.inventory['raw']) is dict
        and set(held.inventory['raw'])==set(held.files),'full retained raw map required')
    for name,raw in held.inventory['raw'].items():
        require(type(raw) is bytes and held.files[name]==dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),'retained raw content changed')
    context=vars(module)['check_expectation_context'](producer._context,producer._context_sha)
    require(context['expectation_sha']==sha256(expectation.raw).hexdigest()
        and canonical(context['caller_expectation_core'])==expectation.image
        and context['source_pins']==producer._source and context['input_files']==held.files,'producer expectation/context/input join differs')
    return held


def invoke(producer,name,*args,**kwargs):
    entry(producer,busy=True)
    matches=[row for row in producer._roots if row[1]==name]
    require(len(matches)==1,'fixed producer dispatch target required')
    return matches[0][2](*args,**kwargs)


def final_checks(producer):
    errors=[]
    for label,operation in (('runtime_final',lambda:entry(producer,busy=True)),
            ('expectation_final',lambda:producer._expectation.entry() if producer._expectation is not None else None),
            ('context_final',lambda:vars(producer._module)['check_expectation_context'](producer._context,producer._context_sha) if producer._context is not None else None),
            ('input_final',lambda:identity(producer) if producer._held is not None else None)):
        try:operation()
        except BaseException as error:errors.append((label,error))
    return errors


def _produce(producer,output_root,*,started):
    try:entry(producer);require(producer._phase=='PREPARED','single prepared producer run required')
    except BaseException as primary:fail(producer,primary)
    commit(producer,_phase='RUNNING',_busy=True);primary=None
    try:
        expectation=producer._capture(producer._source,producer._binding)
        require(type(expectation) is vars(producer._module)['SavedCallerExpectation'],'fixed capture returned foreign expectation')
        commit(producer,_expectation=expectation)
        raw=invoke(producer,'context_from_saved_expectation',expectation,output_root,started=started)
        require(type(raw) is bytes and len(raw)<=2097152,'bounded original expectation context required')
        commit(producer,_context=raw,_context_sha=sha256(raw).hexdigest())
        invoke(producer,'check_expectation_context',raw,producer._context_sha)
        held=invoke(producer,'hold',producer._source,expectation.image);commit(producer,_held=held)
        identity(producer)
    except BaseException as error:primary=error
    errors=final_checks(producer)
    if primary is not None or errors:fail(producer,primary,errors)
    pending_gate(producer)
    producer._evidence.append(dict(stage='G0',expectation_raw_pin=pin(expectation.raw),caller_image_pin=pin(expectation.image),
        context_pin=pin(producer._context),held_image_pin=pin(held.image),local_full_input_verified=True))
    commit(producer,_phase='HELD',_busy=False)
    return producer


def _bookend(producer,stage):
    try:entry(producer);require(type(stage) is str and (producer._phase,stage) in (('HELD','G2'),('G2','G3')),'single ordered G2/G3 bookend required')
    except BaseException as primary:fail(producer,primary)
    commit(producer,_busy=True);primary=None
    try:
        held=identity(producer);invoke(producer,'bookend',held)
        require(identity(producer) is held,'same G0 HeldInput required')
    except BaseException as error:primary=error
    errors=final_checks(producer)
    if primary is not None or errors:fail(producer,primary,errors)
    pending_gate(producer)
    producer._evidence.append(dict(stage=stage,context_pin=pin(producer._context),held_image_pin=pin(producer._held.image),local_full_input_bookend=True))
    commit(producer,_phase=stage,_busy=False)
    return producer


def cleanup(producer,primary,failure=None):
    if producer._close_attempted:return []
    object.__setattr__(producer,'_close_attempted',True);errors=[]
    try:commit(producer,terminal=True)
    except BaseException as error:errors.append(('cleanup_state_seal',error))
    try:reserve_state(producer._owner,'CONSUMED' if primary is None else 'FAILED')
    except BaseException as error:errors.append(('owner_reservation_final',error))
    try:
        # Recovery uses the already held original close CodeType even when its
        # public method binding caused the primary integrity failure.
        row=_RUNTIME_ROWS[2]
        FunctionType(row[3],row[2].__globals__,'held_original_runtime_close',row[4])(producer._owner,primary)
    except BaseException as error:
        expected=_RUNTIME_ROWS[2][2].__globals__.get('LocalRuntimeUnresolved')
        if primary is not None and expected is not None and type(error) is expected and error.owner is producer._owner and error.primary is primary and not error.secondary:
            if failure is not None:object.__setattr__(failure,'runtime_close',error)
        else:errors.append(('runtime_close',error))
    try:
        require(producer._owner._resource.phase=='CLOSED' and not any(producer._owner._resource.pending),'native resource close incomplete')
        spec=producer._owner._boundary_phase
        require(producer._owner._boundary is not None and spec[0](spec[1],spec[2],'held_producer_closed_boundary',spec[3])(producer._owner._boundary)=='CLOSED','import boundary close incomplete')
        require_namespace_terminal(namespace_terminal_snapshot(producer._owner,producer._consumer_plan[2]),primary is None)
    except BaseException as error:errors.append(('terminal_final',error))
    return errors


def fail(producer,primary,secondary=()):
    if producer._failure is not None or id(producer) in _TERMINALS:raise verified_failure(producer)
    errors=list(secondary)
    # Construct with held primitive operations; mutable convenience methods are
    # never recovery dispatch roots.
    failure=RuntimeError.__new__(RetainedProducerFailure)
    for name,value in dict(producer=producer,primary=primary,secondary=(),runtime_close=None,_seal=None).items():
        object.__setattr__(failure,name,value)
    RuntimeError.__init__(failure,'retained producer failed or cleanup unresolved')
    try:commit(producer,terminal=True,_phase='UNRESOLVED',_busy=True)
    except BaseException as error:errors.append(('terminal_begin',error))
    try:errors.extend(cleanup(producer,primary,failure))
    except BaseException as error:errors.append(('cleanup_dispatch',error))
    if producer._pending_reentry is not None and producer._pending_reentry is not primary:
        errors.append(('reentry_during_terminal',producer._pending_reentry))
    try:_terminal_reset(producer)
    except BaseException as error:
        errors.append(('terminal_reset',error));object.__setattr__(producer,'_operation_owner',None)
    object.__setattr__(failure,'secondary',tuple(errors))
    try:_terminal_seal(failure)
    except BaseException as error:errors.append(('failure_seal',error))
    try:_terminal_publish(producer,failure,'UNRESOLVED' if errors else 'FAILED')
    except BaseException as error:errors.append(('failure_publish',error))
    # The bootstrap-held registry is the final, non-retryable record even when
    # an individual terminal helper failed. No callback is invoked here.
    object.__setattr__(failure,'secondary',tuple(errors))
    object.__setattr__(failure,'_seal',failure_image(failure))
    object.__setattr__(producer,'_phase','UNRESOLVED' if errors else 'FAILED')
    object.__setattr__(producer,'_busy',False);object.__setattr__(producer,'_failure',failure)
    _TERMINALS[id(producer)]=(producer,failure)
    raise failure from primary


def _terminal_reset(producer):commit(producer,terminal=True,_operation_owner=None)
def _terminal_seal(failure):object.__setattr__(failure,'_seal',failure_image(failure))
def _terminal_publish(producer,failure,phase):commit(producer,terminal=True,_phase=phase,_busy=False,_failure=failure)


def retained_data_witness(producer):
    """Pure retained data comparison; no live owner entry or filesystem reads."""
    verify_rows(producer._roots)
    row=next(row for row in producer._roots if row[1]=='caller_image')
    projected=FunctionType(row[3],row[0],'held_original_caller_image',row[4])(producer._held)
    require(type(projected) is bytes,'original caller image must be bytes')
    return (id(producer._expectation),_metadata(vars(producer._expectation)),
        id(producer._held),_metadata(vars(producer._held)),pin(projected),
        id(producer._context),pin(producer._context),_metadata(producer._source))


def _close(producer):
    if type(producer) is not RetainedProducer:raise TypeError('exact retained producer required')
    if producer._failure is not None:raise verified_failure(producer)
    if producer._phase=='CLOSED':return report(producer)
    try:entry(producer)
    except BaseException as primary:fail(producer,primary)
    if producer._phase!='G3':fail(producer,ValueError('producer closed before successful G3'))
    commit(producer,_busy=True);errors=final_checks(producer)
    if errors:fail(producer,None,errors)
    pending_gate(producer)
    before=retained_data_witness(producer)
    errors=cleanup(producer,None)
    if errors:fail(producer,None,errors)
    if producer._pending_reentry is not None:
        fail(producer,producer._pending_reentry,(('reentry_during_terminal',producer._pending_reentry),))
    check_guard(_GUARD)
    try:require(retained_data_witness(producer)==before,'retained data changed during close')
    except BaseException as error:fail(producer,error,(('post_close_data',error),))
    try:_terminal_reset(producer)
    except BaseException as error:fail(producer,error,(('close_terminal_reset',error),))
    # Retain only bounded data observations after confirmed cleanup.
    commit(producer,_owner=None,_consumer_plan=None,_binding=None,_adapter=None,_module=None,_roots=(),_source=None,_capture=None,
        _expectation=None,_context=None,_context_sha=None,_held=None,_snapshot=None,_authority=None,_phase='CLOSED',_busy=False)
    return report(producer)


def report(producer):
    require(type(producer) is RetainedProducer and producer._phase=='CLOSED' and producer._failure is None,'successful producer cleanup required for data report')
    require(producer._seal==pin(canonical(image(producer))),'closed producer evidence changed')
    result=dict(schema='staged_saved_F_retained_producer_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        stages=producer._evidence,closed=True,**{name:False for name in FALSE_FIELDS})
    require(len(canonical(result))<=32768,'bounded producer data report required')
    return json.loads(canonical(result))


def operate(producer,operation,*args,**kwargs):
    """Outer operation owner; a bootstrap-held verified dispatcher must call this."""
    require(type(producer) is RetainedProducer and producer._creator==(os.getpid(),get_ident()),'foreign producer thread is rejected without cleanup')
    if producer._failure is not None or id(producer) in _TERMINALS:raise verified_failure(producer)
    held_lock=producer._operation_lock
    expected=_LOCKS.get(id(producer))
    require(expected is not None and expected[0] is producer and expected[1] is held_lock
        and type(held_lock) is _LOCK_TYPE,'original exact bootstrap-held operation lock required')
    if not held_lock.acquire(False):
        if producer._operation_owner==(os.getpid(),get_ident()):
            error=producer._pending_reentry
            if error is None:
                error=ValueError('producer operation reentered')
                commit(producer,_pending_reentry=error)
            raise error
        raise ValueError('another producer operation is active')
    try:
        if operation=='bootstrap_abort':
            require(len(args)==1 and isinstance(args[0],BaseException) and not kwargs
                and producer._owner is _ADMITTED_OWNER,'exact owned bootstrap abort required')
            primary=args[0]
            commit(producer,_operation_owner=(os.getpid(),get_ident()),_busy=True)
            fail(producer,primary,(('bootstrap_bundle',primary),*final_checks(producer)))
        require(producer._seal==pin(canonical(image(producer))),'producer immutable state differs before dispatch')
        check_guard(_GUARD)
        commit(producer,_operation_owner=(os.getpid(),get_ident()))
        if operation=='run':result=_produce(producer,*args,**kwargs)
        elif operation in ('G2','G3'):
            require(not args and not kwargs,'fixed bookend arguments required');result=_bookend(producer,operation)
        elif operation=='close':
            require(not args and not kwargs,'fixed close arguments required');result=_close(producer)
        else:raise ValueError('unknown producer operation')
        if producer._pending_reentry is not None:fail(producer,producer._pending_reentry)
        return result
    except BaseException as primary:
        if producer._failure is not None:raise verified_failure(producer)
        errors=final_checks(producer) if producer._owner is not None else []
        fail(producer,primary,errors)
    finally:
        try:
            if producer._operation_owner is not None:
                try:_terminal_reset(producer)
                except BaseException as error:
                    errors=final_checks(producer) if producer._owner is not None else []
                    fail(producer,error,(('operation_owner_reset',error),*errors))
        finally:held_lock.release()


def pending_gate(producer):
    if producer._pending_reentry is not None:raise producer._pending_reentry


def check_guard(spec):
    require(type(spec) is tuple and len(spec)==3,'bootstrap-held verifier spec required')
    FunctionType(spec[0],spec[1])(*spec[2])


def _metadata(value):
    typ=type(value)
    if value is None or typ in (bool,int,float,str,bytes):return typ,value
    if typ in (tuple,list):return typ,tuple(_metadata(item) for item in value)
    if typ is dict:return typ,tuple(sorted((name,_metadata(item)) for name,item in value.items()))
    return typ,id(value)


def _program_witness(namespace,raw):
    """Source-owned definitions plus their actual direct dependency bindings."""
    filename=namespace['__file__'];unit=compile(raw,filename,'exec',dont_inherit=True,optimize=0)
    codes={}
    def collect(code):
        if type(code) is not CodeType:return
        codes[code.co_qualname]=code
        for child in code.co_consts:collect(child)
    collect(unit);tree=ast.parse(raw);functions=[];classes=[]
    for node in tree.body:
        if type(node) is ast.FunctionDef:functions.append((namespace,node.name,node.name,node))
        elif type(node) is ast.ClassDef:
            cls=namespace[node.name];require(type(cls) is type,'ordinary source-owned helper class required')
            classes.append((cls,tuple(vars(cls).items()),cls.__bases__))
            for child in node.body:
                if type(child) is ast.FunctionDef:functions.append((vars(cls),child.name,node.name+'.'+child.name,child))
    rows=[]
    def default_value(node):
        if type(node) is ast.Name:return namespace[node.id]
        return ast.literal_eval(node)
    for owner,name,qualified,node in functions:
        function=owner[name]
        if type(function) is staticmethod:function=function.__func__
        require(type(function) is FunctionType and function.__globals__ is namespace
            and function.__code__==codes[qualified],'source-derived helper function required')
        expected_defaults=tuple(default_value(value) for value in node.args.defaults) or None
        expected_kwdefaults={name.arg:default_value(value) for name,value in zip(node.args.kwonlyargs,node.args.kw_defaults) if value is not None} or None
        require(_metadata(function.__defaults__)==_metadata(expected_defaults)
            and _metadata(function.__kwdefaults__)==_metadata(expected_kwdefaults)
            and function.__annotations__=={} and function.__dict__=={}
            and function.__name__==name and function.__qualname__==qualified,'source-derived helper metadata required')
        closure=function.__closure__
        cells=() if closure is None else tuple(cell.cell_contents for cell in closure)
        require(not cells or function.__code__.co_freevars==('__class__',) and '.' in qualified
            and cells==(namespace[qualified.split('.')[0]],),'source-owned helper class cell required')
        rows.append((owner,name,function,function.__code__,function.__defaults__,function.__kwdefaults__,
            _metadata((function.__defaults__,function.__kwdefaults__,function.__annotations__,function.__dict__)),closure,cells))
    names={node.id for node in ast.walk(tree) if type(node) is ast.Name};literal_names=set()
    for node in tree.body:
        if type(node) is not ast.Assign:continue
        try:literal=ast.literal_eval(node.value)
        except (ValueError,TypeError):continue
        for target in node.targets:
            if type(target) is ast.Name:
                require(_metadata(namespace[target.id])==_metadata(literal),'source-derived helper constant required: '+target.id)
                literal_names.add(target.id)
    bindings=tuple((name,namespace[name],(_metadata(namespace[name]),) if name in literal_names else None)
        for name in sorted(names&namespace.keys()))
    attributes=[]
    for node in ast.walk(tree):
        if type(node) is not ast.Attribute:continue
        path=[];base=node
        while type(base) is ast.Attribute:path.append(base.attr);base=base.value
        if type(base) is not ast.Name or base.id not in namespace:continue
        value=namespace[base.id]
        # Module/class direct import edges only; never evaluate property getters
        # on injected runtime instances or arbitrary values.
        if type(value) not in (ModuleType,type):continue
        try:
            for name in reversed(path):value=vars(value)[name]
        except (KeyError,TypeError):continue
        attributes.append((namespace[base.id],tuple(reversed(path)),value))
    builtins_ns=namespace['__builtins__']
    if type(builtins_ns) is ModuleType:builtins_ns=vars(builtins_ns)
    builtin_rows=tuple((name,builtins_ns[name]) for name in sorted(names-set(namespace)) if name in builtins_ns)
    return namespace,tuple(rows),tuple(classes),bindings,tuple(attributes),builtins_ns,builtin_rows


def _verify_programs(witnesses,metadata_code):
    # This CodeType runs in isolated bootstrap globals, never the observed helper.
    context={'__builtins__':__builtins__}
    metadata=FunctionType(metadata_code,context);context['_metadata']=metadata
    for namespace,rows,classes,bindings,attributes,builtins_ns,builtin_rows in witnesses:
        current=namespace['__builtins__']
        if type(current) is not dict:current=vars(current)
        if current is not builtins_ns:raise ValueError('helper builtin namespace changed')
        for name,value in builtin_rows:
            if current.get(name) is not value:raise ValueError('helper builtin target changed: '+name)
        for owner,name,function,code,defaults,kwdefaults,expected,closure,cells in rows:
            value=owner[name]
            if type(value) is staticmethod:value=value.__func__
            if value is not function or function.__code__ is not code or function.__globals__ is not namespace \
                    or function.__defaults__ is not defaults or function.__kwdefaults__ is not kwdefaults \
                    or function.__closure__ is not closure \
                    or closure is not None and any(cell.cell_contents is not held for cell,held in zip(closure,cells)) \
                    or metadata((function.__defaults__,function.__kwdefaults__,function.__annotations__,function.__dict__))!=expected:
                raise ValueError('helper function metadata changed: '+name)
        for cls,items,bases in classes:
            values=vars(cls)
            if cls.__bases__!=bases or set(values)!=set(name for name,_ in items) \
                    or any(values[name] is not value for name,value in items):
                raise ValueError('helper class descriptor changed')
        for name,value,expected in bindings:
            if namespace.get(name) is not value or expected is not None and metadata(value)!=expected[0]:
                raise ValueError('helper dependency binding changed: '+name)
        for value,path,expected in attributes:
            for name in path:value=vars(value)[name]
            if value is not expected:raise ValueError('helper imported attribute changed: '+'.'.join(path))


def _private_functions(namespace):
    context=dict(namespace)
    # Direct stdlib attribute targets used during recovery are held before any
    # callback; the interpreter and stdlib remain the stated trust boundary.
    for name,value in tuple(context.items()):
        if type(value) is ModuleType:
            copy=ModuleType(value.__name__);vars(copy).update(vars(value));context[name]=copy
    for name,value in namespace.items():
        if type(value) is FunctionType and value.__globals__ is namespace:
            function=FunctionType(value.__code__,context,value.__name__,value.__defaults__,value.__closure__)
            function.__kwdefaults__=value.__kwdefaults__;context[name]=function
    return context


def _held_dispatch(state,producer,operation,args,kwargs):
    context,guard,operate_code,prepare_code=state
    if operation=='prepare':
        FunctionType(guard[0],guard[1])(*guard[2])
        return FunctionType(prepare_code,context)(*args,**kwargs)
    return FunctionType(operate_code,context)(producer,operation,*args,**kwargs)


def source_dispatch(raw,injected,graph_raw):
    """Build a held dispatch spec; this neither issues admission nor runs P1.

    A creating bootstrap must hold (CodeType, isolated globals, state) and call
    that original CodeType. RetainedProducer convenience methods are not a
    trusted entry point. The caller authenticates these input source bytes.
    """
    require(type(raw) is bytes and type(graph_raw) is bytes and type(injected) is dict,'held source bytes and bootstrap bindings required')
    namespace=dict(__file__=__file__,__name__='_retained_producer_private_source',**injected)
    exec(compile(raw,__file__,'exec',dont_inherit=True,optimize=0),namespace,namespace)
    graph=namespace['_GRAPH_MODULE']
    require(type(graph) is ModuleType,'original graph helper required')
    graph_witness=_program_witness(vars(graph),graph_raw)
    private_graph=_private_functions(vars(graph));graph_copy=ModuleType(graph.__name__);vars(graph_copy).update(private_graph)
    helper_witness=_program_witness(namespace,raw)
    isolated={'__builtins__':dict(vars(builtins)),'FunctionType':FunctionType}
    guard=namespace['_verify_programs'].__code__,isolated,((helper_witness,graph_witness),namespace['_metadata'].__code__)
    context=_private_functions(namespace)
    context['_GRAPH_MODULE']=graph_copy;context['_GRAPH_ROW']=context['function_row'](private_graph,'check')
    context['_GUARD']=guard;context['_LOCKS']={};context['_TERMINALS']={}
    state=context,guard,context['operate'].__code__,context['prepare'].__code__
    return context['_held_dispatch'].__code__,isolated,state


def current():
    """Compile-only development metadata, without runtime/P1 construction."""
    raw=Path(__file__).read_bytes()
    unit=compile(raw,__file__,'exec',dont_inherit=True,optimize=0)
    return None,dict(schema='staged_saved_F_retained_producer_contract_v1',authority='DRAFT_NONAUTHORITATIVE',
        operation='logical_retained_producer_lifecycle_only',source_epoch=SOURCE_EPOCH,
        roots=[item.co_name for item in unit.co_consts if type(item) is CodeType],
        stages=('PREPARED','RUNNING','HELD','G2','G3','CLOSED'),P1_reads=0,source49_target_modules_executed=0,
        **{name:False for name in FALSE_FIELDS})


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
