"""Sampled parent/direct-child stop thresholds; no continuous RAM or retention authority."""
import ctypes as C
from ctypes import wintypes as W
import math
import os
from threading import Event,Thread
import time

STDOUT_CAP=327681
STDERR_CAP=131072
PROCESS_BYTES=268435456
PAIR_BYTES=536870912
POLL_SECONDS=0.01
MAX_SAMPLES=4096
METRICS=('working_set_bytes','peak_working_set_bytes','private_bytes')
SIZE_T_MAX=18446744073709551615


def make_sampler(process):
    assert C.sizeof(C.c_size_t)==8
    class Counters(C.Structure):
        _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD)]+[(n,C.c_size_t) for n in (
            'PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
            'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]
    mem=C.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
    mem.argtypes=[W.HANDLE,C.POINTER(Counters),W.DWORD];mem.restype=W.BOOL
    kernel=C.WinDLL('kernel32',use_last_error=True).GetProcessId
    kernel.argtypes=[W.HANDLE];kernel.restype=W.DWORD
    held=process._handle;child_handle=int(held);parent_pid=int(kernel(W.HANDLE(-1)));child_pid=int(kernel(W.HANDLE(child_handle)))
    assert parent_pid==os.getpid()>0 and type(process.pid) is int and child_pid==process.pid>0 and child_handle>0 and child_pid!=parent_pid
    binding=dict(parent_pid=parent_pid,child_pid=child_pid,child_handle=child_handle,struct_bytes=C.sizeof(Counters))
    assert binding['struct_bytes']==80
    handles=(('parent',-1),('child',child_handle))
    def sample():
        assert process._handle is held and int(held)==child_handle and not held.closed
        assert process.pid==child_pid and int(kernel(W.HANDLE(child_handle)))==child_pid
        result={}
        for name,handle in handles:
            value=Counters();value.cb=C.sizeof(value)
            if not mem(W.HANDLE(handle),C.byref(value),value.cb):raise OSError('GetProcessMemoryInfo:'+str(C.get_last_error()))
            result[name]=dict(working_set_bytes=int(value.WorkingSetSize),peak_working_set_bytes=int(value.PeakWorkingSetSize),private_bytes=int(value.PrivateUsage))
        return result
    return sample,binding


def snapshot_valid(value):
    assert type(value) is dict and set(value)=={'parent','child'}
    for row in value.values():
        assert type(row) is dict and set(row)==set(METRICS)
        assert all(type(v) is int and 0<=v<=SIZE_T_MAX for v in row.values())
        assert row['peak_working_set_bytes']>=row['working_set_bytes']


def initial_guard():
    return dict(schema='staged_saved_F_sampled_memory_guard_v1',process_limit_bytes=PROCESS_BYTES,pair_limit_bytes=PAIR_BYTES,
        poll_seconds=POLL_SECONDS,max_samples=MAX_SAMPLES,attempts=0,samples=0,
        maxima={name:{metric:0 for metric in METRICS} for name in ('parent','child')},
        max_sum_peak_working_set_bytes=0,max_sum_private_bytes=0,last=None,error=None,over_limit=False,sample_limit_reached=False,
        continuous_bound_verified=False,combined_retention_verified=False,resource_admission=False,
        sampler_mode='native',native_sampler_bound=False,binding=None,drained_child_pid=None,
        sample_policy='last_live_poll_only',terminal_query_performed=False)


def exceeds(value):
    return (any(row['peak_working_set_bytes']>PROCESS_BYTES or row['private_bytes']>PROCESS_BYTES for row in value['maxima'].values())
        or value['max_sum_peak_working_set_bytes']>PAIR_BYTES or value['max_sum_private_bytes']>PAIR_BYTES)


def observe(value,sampler):
    if value['attempts']==MAX_SAMPLES:
        value['sample_limit_reached']=True;return 'memory_sample_limit'
    value['attempts']+=1
    try:
        current=sampler();snapshot_valid(current)
        value['samples']+=1;value['last']={name:dict(row) for name,row in current.items()}
        for name,row in current.items():
            for metric,number in row.items():value['maxima'][name][metric]=max(value['maxima'][name][metric],number)
        value['max_sum_peak_working_set_bytes']=max(value['max_sum_peak_working_set_bytes'],sum(row['peak_working_set_bytes'] for row in current.values()))
        value['max_sum_private_bytes']=max(value['max_sum_private_bytes'],sum(row['private_bytes'] for row in current.values()))
        value['over_limit']=exceeds(value)
        return 'memory_limit' if value['over_limit'] else None
    except BaseException as error:
        value['error']=(type(error).__name__+':'+str(error))[:160];return 'memory_observation_failed'


def validate_guard(value,healthy=True,require_native=True):
    expected=initial_guard();assert type(value) is dict and set(value)==set(expected) and type(healthy) is bool
    for key in ('schema','process_limit_bytes','pair_limit_bytes','poll_seconds','max_samples'):
        assert type(value[key]) is type(expected[key]) and value[key]==expected[key]
    assert all(type(value[k]) is int for k in ('attempts','samples','max_sum_peak_working_set_bytes','max_sum_private_bytes'))
    assert 0<=value['samples']<=value['attempts']<=MAX_SAMPLES and value['attempts']-value['samples']<=1
    assert 0<=value['max_sum_peak_working_set_bytes']<=2*SIZE_T_MAX and 0<=value['max_sum_private_bytes']<=2*SIZE_T_MAX
    snapshot_valid(value['maxima'])
    if value['samples']:
        snapshot_valid(value['last'])
        for name,row in value['last'].items():assert all(value['maxima'][name][metric]>=number for metric,number in row.items())
        for field,metric in (('max_sum_peak_working_set_bytes','peak_working_set_bytes'),('max_sum_private_bytes','private_bytes')):
            assert sum(row[metric] for row in value['last'].values())<=value[field]<=sum(row[metric] for row in value['maxima'].values())
    else:assert value['last'] is None and value['maxima']==expected['maxima']
    assert value['error'] is None or type(value['error']) is str and 0<len(value['error'])<=160
    if value['error'] is None:assert value['attempts']==value['samples']
    assert type(value['over_limit']) is bool and value['over_limit'] is exceeds(value)
    assert type(value['sample_limit_reached']) is bool
    if value['sample_limit_reached']:assert value['attempts']==MAX_SAMPLES
    for key in ('continuous_bound_verified','combined_retention_verified','resource_admission'):assert value[key] is False
    assert type(value['sampler_mode']) is str and value['sampler_mode'] in ('native','injected_test')
    assert type(value['native_sampler_bound']) is bool and type(value['drained_child_pid']) is int and value['drained_child_pid']>0
    assert value['sample_policy']=='last_live_poll_only' and value['terminal_query_performed'] is False
    if value['native_sampler_bound']:
        binding=value['binding'];assert value['sampler_mode']=='native'
        assert type(binding) is dict and set(binding)=={'parent_pid','child_pid','child_handle','struct_bytes'}
        assert all(type(v) is int and v>0 for v in binding.values()) and binding['struct_bytes']==80
        assert binding['child_pid']==value['drained_child_pid'] and binding['child_handle']<=SIZE_T_MAX
        assert binding['parent_pid']<=4294967295 and binding['child_pid']<=4294967295 and binding['parent_pid']!=binding['child_pid']
    else:assert value['binding'] is None
    assert type(require_native) is bool
    if require_native:assert value['sampler_mode']=='native'
    if healthy:assert value['samples']>0 and value['error'] is None and not value['over_limit'] and not value['sample_limit_reached']
    if healthy and require_native:assert value['native_sampler_bound']
    return value


_ROOTS=tuple((name,fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__,tuple(cell.cell_contents for cell in fn.__closure__ or ()),None if fn.__kwdefaults__ is None else tuple(sorted(fn.__kwdefaults__.items()))) for name,fn in (
    ('make_sampler',make_sampler),('snapshot_valid',snapshot_valid),('initial_guard',initial_guard),
    ('exceeds',exceeds),('observe',observe),('validate_guard',validate_guard)))


_PRIMITIVES=(Event,Thread,math.isfinite,C.WinDLL,C.sizeof,C.byref,C.get_last_error,W.HANDLE,os.getpid)


def check_bindings(roots=_ROOTS,clock=time.perf_counter,limits=(268435456,536870912,0.01,4096,18446744073709551615),primitives=_PRIMITIVES,caps=(327681,131072)):
    for name,fn,code,defaults,kwdefaults,closure,values,kwvalues in roots:
        assert globals()[name] is fn and fn.__code__ is code and fn.__defaults__ is defaults and fn.__kwdefaults__ is kwdefaults and fn.__closure__ is closure
        assert all(cell.cell_contents is expected for cell,expected in zip(closure or (),values))
        if kwvalues is not None:assert set(kwdefaults)=={name for name,value in kwvalues} and all(kwdefaults[name] is value for name,value in kwvalues)
    assert time.perf_counter is clock and (PROCESS_BYTES,PAIR_BYTES,POLL_SECONDS,MAX_SAMPLES,SIZE_T_MAX)==limits
    assert all(type(actual) is type(expected) for actual,expected in zip((PROCESS_BYTES,PAIR_BYTES,POLL_SECONDS,MAX_SAMPLES,SIZE_T_MAX),limits))
    assert all(actual is expected for actual,expected in zip((Event,Thread,math.isfinite,C.WinDLL,C.sizeof,C.byref,C.get_last_error,W.HANDLE,os.getpid),primitives))
    assert (STDOUT_CAP,STDERR_CAP)==caps and type(STDOUT_CAP) is int and type(STDERR_CAP) is int


def _drain(process,timeout,*,prepare,clock,mode,_check=check_bindings,_initial=initial_guard,_observe=observe,_validate=validate_guard):
    _check()
    assert type(timeout) is float and math.isfinite(timeout) and timeout>0
    deadline=clock()+timeout;overflow=Event();state={n:dict(data=bytearray(),observed_bytes=0,truncated=False,error=None) for n in ('stdout','stderr')}
    guard=_initial();guard.update(sampler_mode=mode,drained_child_pid=process.pid);sampler=None
    def sampled():
        nonlocal sampler
        before=guard['attempts']
        try:
            _check()
            if sampler is None:
                sampler,binding=prepare();guard.update(binding=binding,native_sampler_bound=mode=='native')
            reason=_observe(guard,sampler);_check();return reason
        except BaseException as error:
            if guard['attempts']==before and guard['attempts']<MAX_SAMPLES:guard['attempts']+=1
            guard['error']=(type(error).__name__+':'+str(error))[:160];return 'memory_observation_failed'
    def reader(name,stream,limit):
        row=state[name]
        try:
            while True:
                block=stream.read(4096)
                if not block:break
                row['observed_bytes']+=len(block);remaining=limit-len(row['data']);row['data'].extend(block[:remaining])
                if len(block)>remaining:row['truncated']=True;overflow.set()
        except BaseException as caught:row['error']=type(caught).__name__+': '+str(caught)[:256];overflow.set()
    threads=[Thread(target=reader,args=(name,getattr(process,name),cap),daemon=True) for name,cap in (('stdout',STDOUT_CAP),('stderr',STDERR_CAP))]
    for thread in threads:thread.start()
    reason=None;cleanup=[];killed=False
    while reason is None and process.poll() is None:
        if overflow.is_set():reason='output_limit_or_reader_error';break
        if clock()>=deadline:reason='timeout';break
        reason=sampled()
        if reason is None:overflow.wait(POLL_SECONDS)
    if reason is not None and process.poll() is None:
        try:process.kill();killed=True
        except BaseException as caught:cleanup.append('kill:'+type(caught).__name__)
    try:process.wait(timeout=1.)
    except BaseException as caught:cleanup.append('wait:'+type(caught).__name__)
    for thread in threads:thread.join(timeout=.5)
    readers_closed=not any(t.is_alive() for t in threads);pipes_closed=False
    if readers_closed:
        for name in ('stdout','stderr'):
            try:getattr(process,name).close()
            except BaseException as caught:cleanup.append('pipe_close:'+type(caught).__name__)
        pipes_closed=all(getattr(process,n).closed for n in ('stdout','stderr'))
    if guard['samples']==0 and reason is None:guard['error']='no_live_sample';reason='memory_observation_failed'
    try:_check()
    except BaseException as error:
        guard['error']=(type(error).__name__+':'+str(error))[:160];reason=reason or 'memory_observation_failed'
    if any(row['truncated'] or row['error'] is not None for row in state.values()):reason=reason or 'output_limit_or_reader_error'
    if cleanup or not readers_closed or not pipes_closed or process.poll() is None:reason=reason or 'cleanup_unresolved'
    _validate(guard,healthy=reason is None,require_native=mode=='native')
    return process.poll(),bytes(state['stdout']['data']),bytes(state['stderr']['data']),reason,dict(child_created=True,
        stdout_cap=STDOUT_CAP,stderr_cap=STDERR_CAP,chunk_bytes=4096,killed=killed,
        stdout_observed_bytes=state['stdout']['observed_bytes'],stderr_observed_bytes=state['stderr']['observed_bytes'],
        stdout_truncated=state['stdout']['truncated'],stderr_truncated=state['stderr']['truncated'],
        reader_errors=[row['error'] for row in state.values() if row['error'] is not None],
        reader_threads_terminal=readers_closed,pipes_closed=pipes_closed,cleanup=cleanup,direct_child_pid=process.pid,memory_guard=guard)


def _build_actor(test,impl,make,clock,verify):
    if test:
        def test_drain(process,timeout,*,sample,_clock=clock):
            verify();return impl(process,timeout,prepare=lambda:(sample,None),clock=_clock,mode='injected_test')
        return test_drain
    def drain(process,timeout):
        verify();return impl(process,timeout,prepare=lambda:make(process),clock=clock,mode='native')
    return drain


drain=_build_actor(False,_drain,make_sampler,time.perf_counter,check_bindings)
test_drain=_build_actor(True,_drain,make_sampler,time.perf_counter,check_bindings)
_ACTORS=tuple((name,fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__,tuple(cell.cell_contents for cell in fn.__closure__ or ()),None if fn.__kwdefaults__ is None else tuple(sorted(fn.__kwdefaults__.items()))) for name,fn in (
    ('_drain',_drain),('drain',drain),('test_drain',test_drain),('_build_actor',_build_actor)))
check_bindings.__defaults__=((*_ROOTS,*_ACTORS),*check_bindings.__defaults__[1:])
