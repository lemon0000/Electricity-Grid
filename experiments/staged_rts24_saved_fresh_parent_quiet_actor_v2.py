"""Retained parent/process/drain facts. This actor issues no read permission."""
import ctypes as C
from ctypes import wintypes as W
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from threading import Thread,get_ident
from types import FunctionType

ROOT=Path(__file__).absolute().parents[1]
DRAIN_PATH=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v2.py'
DRAIN_PIN=(14255, 'b73a9b552a08a5e995e23dd73e3d468f05b9d52703c0f73e179791dc34eeffb3')
STDOUT_CAP=327681
STDERR_CAP=131072
_ACTORS={}


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())

def creator():return os.getpid(),get_ident()


def checked_pin(value):
    require(type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and 0<value['bytes']<=1048576
        and type(value['sha256']) is str and len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256']),
        'exact bounded parent pin required')
    return json.loads(canonical(value))


def function_spec(function):
    require(type(function) is FunctionType,'original parent drain callable required')
    closure=function.__closure__
    return function,function.__code__,function.__globals__,function.__defaults__,function.__kwdefaults__,closure,tuple(c.cell_contents for c in closure or ())


def verify_function(row):
    function,code,context,defaults,kw,closure,cells=row
    require(function.__code__ is code and function.__globals__ is context and function.__defaults__ is defaults
        and function.__kwdefaults__ is kw and function.__closure__ is closure
        and all(c.cell_contents is value for c,value in zip(closure or (),cells)),'original parent drain changed')


def kernel_identity(process):
    kernel=C.WinDLL('kernel32',use_last_error=True)
    pid=kernel.GetProcessId;pid.argtypes=[W.HANDLE];pid.restype=W.DWORD
    times=kernel.GetProcessTimes;times.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;times.restype=W.BOOL
    image=kernel.QueryFullProcessImageNameW;image.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];image.restype=W.BOOL
    created,ended,kernel_time,user=(W.FILETIME() for _ in range(4));path=C.create_unicode_buffer(32768);size=W.DWORD(len(path))
    require(pid(process._handle)==process.pid and times(process._handle,*[C.byref(value) for value in (created,ended,kernel_time,user)])
        and image(process._handle,0,path,C.byref(size)),'live child kernel identity unavailable')
    return dict(pid=process.pid,creation=created.dwLowDateTime|created.dwHighDateTime<<32,image_path=path.value)


class ParentQuietActor:
    __slots__=('_creator','_process','_pid','_handle','_handle_value','_pipes','_argv','_identity','_plan_pin','_transport_pin',
        '_drain','_writer','_writer_errors','_release_raw','_released','_raws','_observation','_reason','_exit',
        '_close_attempted','_closed','_phase','_failure','_result','_retired_evidence')
    def __new__(cls,*args,**kwargs):raise TypeError('capture the retained parent actor')
    def __setattr__(self,name,value):raise AttributeError('parent actor is frozen')
    def __delattr__(self,name):raise AttributeError('parent actor is frozen')
    def __reduce__(self):raise TypeError('parent process actor cannot be serialized')


def entry(actor):
    require(type(actor) is ParentQuietActor and actor._creator==creator() and _ACTORS.get(id(actor)) is actor,
        'original creating parent actor required')
    if actor._failure is not None:raise actor._failure
    return actor


def capture(process,identity,argv,plan_pin,transport_pin,drain_raw,
        _identity_code=kernel_identity.__code__,_identity_context=globals(),_factory=FunctionType):
    require(type(process) is subprocess.Popen and type(process.pid) is int and process.pid>0 and process.returncode is None,
        'exact live direct-child Popen required')
    require(type(argv) is list and 1<=len(argv)<=16 and all(type(value) is str for value in argv)
        and process.args==argv,'exact original child argv required')
    require(type(identity) is dict and set(identity)=={'pid','creation','image_path'} and type(identity['pid']) is int
        and identity['pid']==process.pid and type(identity['creation']) is int and identity['creation']>0
        and type(identity['image_path']) is str and Path(identity['image_path'])==Path(argv[0]),'held child kernel identity required')
    require(identity==_factory(_identity_code,_identity_context,'held_parent_kernel_identity')(process),
        'independent live child kernel identity differs')
    require(type(drain_raw) is bytes and DRAIN_PIN is not None and (len(drain_raw),sha256(drain_raw).hexdigest())==DRAIN_PIN,
        'fixed parent drain source required')
    unit=compile(drain_raw,str(DRAIN_PATH),'exec',dont_inherit=True,optimize=0)
    namespace=dict(__file__=str(DRAIN_PATH),__name__='_held_parent_native_drain')
    exec(unit,namespace,namespace);drain=namespace['drain']
    require(type(drain) is FunctionType,'fixed source-owned native drain required')
    pipes=(process.stdin,process.stdout,process.stderr)
    require(all(pipe is not None and not pipe.closed for pipe in pipes) and not process._handle.closed,'live original pipes/handle required')
    actor=object.__new__(ParentQuietActor)
    values=dict(_creator=creator(),_process=process,_pid=process.pid,_handle=process._handle,_handle_value=int(process._handle),
        _pipes=pipes,_argv=canonical(argv),_identity=canonical(identity),_plan_pin=checked_pin(plan_pin),_transport_pin=checked_pin(transport_pin),
        _drain=function_spec(drain),_writer=None,_writer_errors=(),
        _release_raw=b'SAVED_PRE_ENTRY_V1:'+plan_pin['sha256'].encode('ascii')+b'\n',_released=False,
        _raws=None,_observation=None,_reason=None,_exit=None,
        _close_attempted=False,_closed=False,_phase='CAPTURED',_failure=None,_result=None,_retired_evidence=None)
    for name,value in values.items():object.__setattr__(actor,name,value)
    _ACTORS[id(actor)]=actor;return actor


def write_release(actor):
    stream=actor._pipes[0]
    try:
        stream.write(actor._release_raw);stream.flush();object.__setattr__(actor,'_released',True)
    except BaseException as error:
        object.__setattr__(actor,'_writer_errors',actor._writer_errors+((type(error).__name__+':'+str(error))[:160],))
    finally:
        try:stream.close()
        except BaseException as error:
            object.__setattr__(actor,'_writer_errors',actor._writer_errors+((type(error).__name__+':'+str(error))[:160],))


def release(actor,_code=write_release.__code__,_context=globals(),_factory=FunctionType):
    entry(actor);require(actor._phase=='CAPTURED' and actor._writer is None,'single original release writer required')
    held=_factory(_code,_context,'held_parent_release')
    writer=Thread(target=held,args=(actor,),daemon=True);object.__setattr__(actor,'_writer',writer)
    writer.start()


def drain_child(actor,seconds):
    entry(actor)
    require(actor._phase=='CAPTURED' and type(actor._writer) is Thread,'original actor-owned release writer required')
    process=actor._process
    require(process.pid==actor._pid and process._handle is actor._handle and canonical(process.args)==actor._argv,
        'retained child instance changed before drain')
    verify_function(actor._drain)
    function,code,context,defaults,kw,closure,_=actor._drain
    held=FunctionType(code,context,'held_parent_native_drain',defaults,closure);held.__kwdefaults__=kw
    result=held(process,seconds);verify_function(actor._drain)
    require(type(result) is tuple and len(result)==5,'closed drain result required')
    exit_code,stdout,stderr,reason,observation=result
    require(type(stdout) is type(stderr) is bytes and len(stdout)<=STDOUT_CAP and len(stderr)<=STDERR_CAP,
        'bounded original child bytes required')
    # Retain canonical independent copies, so caller-side dict mutation cannot
    # turn the actual drain result into a successful terminal observation.
    observation_raw=canonical(observation);require(len(observation_raw)<=32768,'bounded original drain observation required')
    for name,value in dict(_exit=exit_code,_raws=(stdout,stderr),_reason=reason,
            _observation=observation_raw,_phase='DRAINED').items():object.__setattr__(actor,name,value)
    return exit_code,stdout,stderr,reason,json.loads(actor._observation)


def close_handle(actor):
    # Cleanup must remain possible after a failed quiet check.
    require(type(actor) is ParentQuietActor and actor._creator==creator() and _ACTORS.get(id(actor)) is actor,
        'original creating parent cleanup actor required')
    if actor._close_attempted:
        require(actor._closed,'prior child process-handle close unresolved');return True
    process=actor._process
    require(process is not None and process.pid==actor._pid and process._handle is actor._handle
        and process.returncode is not None,'terminal original child required before handle close')
    object.__setattr__(actor,'_close_attempted',True)
    kernel=C.WinDLL('kernel32',use_last_error=True);observe=kernel.GetHandleInformation
    observe.argtypes=[W.HANDLE,C.POINTER(W.DWORD)];observe.restype=W.BOOL
    actor._handle.Close();flags=W.DWORD();C.set_last_error(0)
    closed=actor._handle.closed and not observe(W.HANDLE(actor._handle_value),C.byref(flags)) and C.get_last_error()==6
    object.__setattr__(actor,'_closed',bool(closed));require(closed,'original child process HANDLE close unverified')
    return True


def finish(actor):
    entry(actor)
    if actor._phase=='CLOSED':return json.loads(actor._result)
    try:
        require(actor._phase=='DRAINED' and actor._closed and actor._close_attempted,'drain and closed process HANDLE required')
        process=actor._process;writer=actor._writer
        if type(writer) is Thread:writer.join(.5)
        require(process.pid==actor._pid and process._handle is actor._handle and process._handle.closed
            and process.args is not None and canonical(process.args)==actor._argv,'same closed child identity required')
        require(process.stdin is actor._pipes[0] and process.stdout is actor._pipes[1] and process.stderr is actor._pipes[2]
            and all(pipe.closed for pipe in actor._pipes),'all original child pipes must be closed')
        require(type(writer) is Thread and writer.ident is not None and not writer.is_alive(),'original writer must be terminal')
        require(type(actor._exit) is int and actor._exit==process.returncode and actor._reason is None,
            'actual child exit and clean drain reason required')
        observation=json.loads(actor._observation)
        require(observation['direct_child_pid']==actor._pid and observation['pipes_closed'] is True
            and observation['reader_threads_terminal'] is True and observation['killed'] is False
            and observation['stdout_truncated'] is False and observation['stderr_truncated'] is False
            and observation['reader_errors']==observation['cleanup']==[],'actual retained drain was not quiet')
        verify_function(actor._drain)
        stdout,stderr=actor._raws
        quiet=dict(child_exit=actor._exit,process_handle_closed=True,pipes_closed=True,reader_threads_terminal=True,writer_thread_terminal=True,
            killed=False,stdout_truncated=False,stderr_truncated=False,reader_errors=[],cleanup=[])
        value=dict(schema='staged_saved_F_retained_parent_quiet_v1',authority='DRAFT_NONAUTHORITATIVE',
            kernel_identity=json.loads(actor._identity),argv_pin=pin(actor._argv),plan_pin=actor._plan_pin,transport_pin=actor._transport_pin,
            stdout_pin=pin(stdout),stderr_pin=pin(stderr),release_pin=pin(actor._release_raw),release_sent=actor._released,
            writer_errors=list(actor._writer_errors),child_success=actor._exit==0,
            transport_success=actor._released and not actor._writer_errors,
            drain_observation=json.loads(actor._observation),drain_observation_pin=pin(actor._observation),quiet=quiet,
            parent_independent_P1_verified=False,
            external_permission_verified=False,resource_admission=False,formal_result=False,run_authority=False,actual_F=False)
        raw=canonical(value);require(len(raw)<=40960,'bounded retained quiet receipt required')
        for name,item in dict(_phase='CLOSED',_result=raw,_process=None,_handle=None,_pipes=(),_drain=None,_writer=None,
                _writer_errors=None,_raws=None,_observation=None).items():object.__setattr__(actor,name,item)
        return json.loads(raw)
    except BaseException as error:
        object.__setattr__(actor,'_failure',error);object.__setattr__(actor,'_phase','FAILED');raise


def _predecessor_contract():
    """Static source/cap binding only; no Popen, kernel query or drain call."""
    raw=DRAIN_PATH.read_bytes()
    require((len(raw),sha256(raw).hexdigest())==DRAIN_PIN,'fixed private drain bytes changed')
    compile(raw,str(DRAIN_PATH),'exec',dont_inherit=True,optimize=0)
    return None,dict(schema='staged_saved_F_parent_quiet_actor_contract_v1',authority='DRAFT_NONAUTHORITATIVE',
        drain_pin=pin(raw),stdout_cap=STDOUT_CAP,stderr_cap=STDERR_CAP,writer='actor_owned_fixed_manifest_frame',
        child_nonzero_can_be_physically_quiet=True,caller_drain_callable=False,parent_P1_reads=0,
        external_permission_verified=False,continuous_bound_verified=False,combined_retention_verified=False,
        resource_admission=False,formal_result=False,run_authority=False,actual_F=False)


def abort(actor,primary):
    """Stop only this retained direct child; preserve primary and cleanup facts."""
    require(type(actor) is ParentQuietActor and actor._creator==creator() and _ACTORS.get(id(actor)) is actor,
        'original creating parent cleanup actor required')
    require(isinstance(primary,BaseException) and actor._phase!='RETIRED','original parent failure required')
    if actor._phase=='CLOSED':return []
    errors=[];process=actor._process
    require(process is not None and process.pid==actor._pid and process._handle is actor._handle,
        'same retained direct child required for failure cleanup')
    if actor._raws is None:
        try:
            function,code,context,defaults,kw,closure,_=actor._drain
            verify_function(actor._drain)
            held=FunctionType(code,context,'held_parent_failure_drain',defaults,closure);held.__kwdefaults__=kw
            rc,out,err,reason,observation=held(process,1.)
            require(type(out) is type(err) is bytes and len(out)<=STDOUT_CAP and len(err)<=STDERR_CAP,
                'bounded original failure drain bytes required')
            raw=canonical(observation);require(len(raw)<=32768,'bounded original failure drain observation required')
            for name,value in dict(_exit=rc,_raws=(out,err),_reason=reason,_observation=raw).items():
                object.__setattr__(actor,name,value)
        except BaseException as error:errors.append('failure_drain:'+type(error).__name__+':'+str(error)[:160])
    if process.poll() is None:
        try:process.kill();process.wait(timeout=1.)
        except BaseException as error:errors.append('kill_wait:'+type(error).__name__+':'+str(error)[:160])
    writer=actor._writer
    if type(writer) is Thread and writer.ident is not None:
        try:writer.join(.5)
        except BaseException as error:errors.append('writer_join:'+type(error).__name__+':'+str(error)[:160])
    if type(writer) is Thread and writer.is_alive():errors.append('writer_thread_pending')
    else:
        for index,pipe in enumerate(actor._pipes):
            try:
                if not pipe.closed:pipe.close()
            except BaseException as error:errors.append('pipe_'+str(index)+':'+type(error).__name__+':'+str(error)[:160])
    try:close_handle(actor)
    except BaseException as error:errors.append('process_handle:'+type(error).__name__+':'+str(error)[:160])
    if actor._failure is None:object.__setattr__(actor,'_failure',primary)
    object.__setattr__(actor,'_phase','FAILED')
    return errors


def terminal_snapshot(actor):
    """Immutable observations before exact registry retirement; grants no authority."""
    require(type(actor) is ParentQuietActor and actor._creator==creator() and _ACTORS.get(id(actor)) is actor,
        'original creating terminal actor required')
    if actor._phase=='CLOSED':return json.loads(actor._result)
    require(actor._phase=='FAILED' and actor._failure is not None and actor._observation is not None,
        'failed actor needs its retained drain observation')
    process=actor._process;writer=actor._writer
    require(process is not None and process.pid==actor._pid and process._handle is actor._handle
        and process.returncode is not None and process._handle.closed and actor._closed
        and actor._close_attempted and canonical(process.args)==actor._argv,
        'failed direct child HANDLE/identity unresolved')
    require(all(pipe.closed for pipe in actor._pipes) and process.stdin is actor._pipes[0]
        and process.stdout is actor._pipes[1] and process.stderr is actor._pipes[2],
        'failed original pipes unresolved')
    require(writer is None or type(writer) is Thread and not writer.is_alive(),'failed original writer unresolved')
    observation=json.loads(actor._observation)
    require(observation['direct_child_pid']==actor._pid and observation['pipes_closed'] is True
        and observation['reader_threads_terminal'] is True,
        'failed original drain readers unresolved')
    stdout,stderr=actor._raws
    value=dict(schema='staged_saved_F_retained_parent_failure_v1',authority='DRAFT_NONAUTHORITATIVE',
        kernel_identity=json.loads(actor._identity),argv_pin=pin(actor._argv),plan_pin=actor._plan_pin,transport_pin=actor._transport_pin,
        stdout_pin=pin(stdout),stderr_pin=pin(stderr),release_pin=pin(actor._release_raw),release_sent=actor._released,
        writer_errors=list(actor._writer_errors),child_exit=process.returncode,drain_reason=actor._reason,
        drain_observation=observation,drain_observation_pin=pin(actor._observation),process_handle_closed=True,
        writer_thread_terminal=True,primary=dict(type=type(actor._failure).__name__,message=str(actor._failure)[:180]),
        parent_independent_P1_verified=False,external_permission_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)
    raw=canonical(value);require(len(raw)<=40960,'bounded failed parent snapshot required')
    return json.loads(raw)


def retire(actor,evidence_raw):
    """Retire the exact actor only after terminal evidence is held as canonical bytes."""
    snapshot=terminal_snapshot(actor)
    require(type(evidence_raw) is bytes and len(evidence_raw)<=1048576,'bounded held retirement evidence required')
    value=json.loads(evidence_raw)
    flags=('parent_independent_P1_verified','external_permission_verified','resource_admission','formal_result','run_authority','actual_F')
    require(canonical(value)==evidence_raw and type(value) is dict
        and set(value)=={'schema','authority','quiet_snapshot_pin','parent_result_pin','accepted',*flags}
        and value['schema']=='staged_saved_F_parent_retirement_record_v1' and value['authority']=='DRAFT_NONAUTHORITATIVE'
        and type(value['accepted']) is bool and all(value[key] is False for key in flags)
        and value['quiet_snapshot_pin']==pin(canonical(snapshot)),'same terminal snapshot retirement required')
    checked_pin(value['parent_result_pin'])
    require(actor._phase=='CLOSED' or value['accepted'] is False,'failed actor cannot retire as accepted')
    # Form all retained bytes before changing the registry or any live slot.
    raw=canonical(snapshot)
    require(_ACTORS.get(id(actor)) is actor,'exact parent registry row changed')
    del _ACTORS[id(actor)]
    for name,item in dict(_phase='RETIRED',_result=raw,_retired_evidence=evidence_raw,_process=None,_handle=None,_pipes=(),
            _drain=None,_writer=None,_writer_errors=None,_raws=None,_observation=None,_failure=None).items():
        object.__setattr__(actor,name,item)
    return dict(schema='staged_saved_F_parent_actor_retirement_v1',authority='DRAFT_NONAUTHORITATIVE',
        exact_registry_row_retired=True,terminal_snapshot_pin=pin(raw),evidence_pin=pin(evidence_raw),
        parent_independent_P1_verified=False,external_permission_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)


def current():
    _,contract=_predecessor_contract()
    contract.update(schema='staged_saved_F_parent_quiet_actor_contract_v2',
        exact_registry_retirement=True,failed_retirement_requires_terminal_readers=True,
        retained_primary_before_retirement=True)
    return None,contract


def program_memory_guard(value):
    raw=DRAIN_PATH.read_bytes()
    require((len(raw),sha256(raw).hexdigest())==DRAIN_PIN,'same fixed memory guard source required')
    namespace=dict(__file__=str(DRAIN_PATH),__name__='_held_parent_saved_guard')
    exec(compile(raw,str(DRAIN_PATH),'exec',dont_inherit=True,optimize=0),namespace,namespace)
    return namespace['validate_guard'](value)


def retired_observation(actor,evidence_raw):
    require(type(actor) is ParentQuietActor and actor._creator==creator() and actor._phase=='RETIRED'
        and id(actor) not in _ACTORS and actor._retired_evidence==evidence_raw,
        'same actually retired parent actor required')
    require(actor._process is actor._handle is actor._drain is actor._writer is actor._writer_errors is actor._raws is actor._observation is actor._failure is None
        and actor._pipes==(),'retired actor still holds live references')
    return dict(schema='staged_saved_F_parent_actor_retirement_v1',authority='DRAFT_NONAUTHORITATIVE',
        exact_registry_row_retired=True,terminal_snapshot_pin=pin(actor._result),evidence_pin=pin(evidence_raw),
        parent_independent_P1_verified=False,external_permission_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)
