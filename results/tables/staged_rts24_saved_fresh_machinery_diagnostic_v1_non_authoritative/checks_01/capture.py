"""One bounded diagnostic, separate cost ledger; old failed budgets stay closed."""
import time
STARTED=time.perf_counter()
import ctypes as C
from ctypes import wintypes as W
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def save(name,value):
    with (OUT/name).open('xb') as stream:stream.write(raw(value))
def storage(extra_files,extra_bytes):
    files=[p for p in BASE.rglob('*') if p.is_file()]
    assert len(files)+extra_files<=16 and sum(p.stat().st_size for p in files)+extra_bytes<=512*1024
try:
    admission_raw=(OUT/'admission.json').read_bytes();admission=json.loads(admission_raw)
    assert admission['caps']==dict(registration=2,probe=12,archive=4,total_static=18,pytest=0)
    assert admission['registration_charged_seconds']<=2
    registration_before=pin((OUT/'registration.json').read_bytes());assert registration_before==admission['registration_pin']
    for n in ('probe.exit.json','probe.stdout.log','probe.stderr.log','result.json'):assert not (OUT/n).exists()
    source_before=names(ROOT/n for n in admission['source_pins']);helper_before=names(ROOT/n for n in admission['helper_pins'])
    refs_before=names(ROOT/n for n in admission['reference_pins']);external_before={n:pin(Path(n).read_bytes()) for n in admission['external_pins']}
    assert source_before==admission['source_pins'] and helper_before==admission['helper_pins'] and refs_before==admission['reference_pins'] and external_before==admission['external_pins']
    assert str(Path(sys.executable))==admission['executable'] and sys.version==admission['python'] and sys.dont_write_bytecode
    old=ROOT/admission['drain_helper_path'];assert pin(old.read_bytes())==admission['drain_helper_pin']
    spec=importlib.util.spec_from_file_location('frozen_machinery_drain',old);capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
    argv=[admission['executable'],'-B','-s',str(OUT/'probe.py')];launches=[]
    def audit(event,args):
        if event=='subprocess.Popen':
            assert not launches and args[0]==admission['executable'] and args[1]==subprocess.list2cmdline(argv) and str(args[2])==str(ROOT) and args[3] is None
            launches.append(True)
    sys.addaudithook(audit)
    api=C.WinDLL('kernel32',use_last_error=True);check=api.GetHandleInformation;check.argtypes=[W.HANDLE,C.POINTER(W.DWORD)];check.restype=W.BOOL
    class Counters(C.Structure):
        _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD)]+[(n,C.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    memory_api=C.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo;memory_api.argtypes=[W.HANDLE,C.POINTER(Counters),W.DWORD];memory_api.restype=W.BOOL
    storage(4,350000);preparation=time.perf_counter()-STARTED;timeout=12.-2.5-preparation
    process=None;stdout=stderr=b'';error=None;state=None;code=None;handle_closed=False;peak=None;memory_error=None;cleanup=[]
    started=time.perf_counter()
    try:
        if timeout<=0:raise TimeoutError('preparation exhausted before child')
        process=subprocess.Popen(argv,executable=admission['executable'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        code,stdout,stderr,error,state=capture.drain(process,timeout)
        counters=Counters();counters.cb=C.sizeof(counters)
        if memory_api(W.HANDLE(int(process._handle)),C.byref(counters),counters.cb):peak=int(counters.PeakWorkingSetSize)
        else:memory_error=C.get_last_error()
    except BaseException as caught:error=type(caught).__name__
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    try:process.kill()
                    except BaseException as caught:cleanup.append('kill:'+type(caught).__name__)
                    try:process.wait(timeout=1.)
                    except BaseException as caught:cleanup.append('wait:'+type(caught).__name__)
            except BaseException as caught:cleanup.append('poll:'+type(caught).__name__)
            finally:
                try:
                    handle=int(process._handle)
                    try:process._handle.Close()
                    finally:
                        flags=W.DWORD();C.set_last_error(0)
                        handle_closed=process._handle.closed and not check(W.HANDLE(handle),C.byref(flags)) and C.get_last_error()==6
                except BaseException as caught:cleanup.append('handle_close:'+type(caught).__name__)
    target=time.perf_counter()-started
    child=None
    try:
        if len(stdout)>65536:raise ValueError('diagnostic result byte cap')
        child=json.loads(stdout)
    except (ValueError,TypeError):pass
    source_after=names(ROOT/n for n in source_before);helper_after=names(ROOT/n for n in helper_before);refs_after=names(ROOT/n for n in refs_before)
    external_after={n:pin(Path(n).read_bytes()) for n in external_before};admission_after=pin((OUT/'admission.json').read_bytes())
    registration_after=pin((OUT/'registration.json').read_bytes())
    post_ok=source_before==source_after and helper_before==helper_after and refs_before==refs_after and external_before==external_after and admission_after==pin(admission_raw) and registration_before==registration_after
    charged=time.perf_counter()-STARTED+.5
    accepted=code==0 and error is None and child is not None and child['diagnostic_capture_accepted'] and post_ok and handle_closed and peak is not None and not cleanup and launches==[True] and charged<=12
    if child is not None:save('result.json',child)
    result_pin=None if child is None else pin((OUT/'result.json').read_bytes())
    successor=dict(static=admission['registration_charged_seconds']+charged,pytest=0)
    value=dict(authority='DRAFT_NONAUTHORITATIVE',label='machinery_probe',kind='static',accepted=bool(accepted),diagnostic_capture_accepted=bool(accepted),argv=argv,
        returncode=code,error=error,parent_exact_launch_events=len(launches),source_pins=source_before,after_source_pins=source_after,helper_pins=helper_before,after_helper_pins=helper_after,
        reference_pins=refs_before,after_reference_pins=refs_after,external_pins=external_before,after_external_pins=external_after,
        admission_pin=pin(admission_raw),after_admission_pin=admission_after,postcheck_pins_match=post_ok,
        registration_pin=registration_before,after_registration_pin=registration_after,
        charged_seconds=charged,tail_reserve_seconds=.5,cap_seconds=12,preparation_seconds=preparation,target_seconds=target,target_timeout_seconds=timeout,
        stdout_pin=pin(stdout),stderr_pin=pin(stderr),result_pin=result_pin,bounded_drain=state,handle_closed=handle_closed,process_cleanup_errors=cleanup,
        peak_working_set_bytes=peak,memory_observation_error=memory_error,RAM_hard_cap_enforced=False,
        predecessor_charged_seconds=admission['predecessor_charged_seconds'],successor_charged_seconds=successor,
        all_cumulative_charged_seconds={k:admission['predecessor_charged_seconds'][k]+successor[k] for k in successor},
        predecessor_combined_resource_admission=False,policy_resource_admission=False,cold_acceptance=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False)
    payload=raw(value);storage(3,len(stdout)+len(stderr)+len(payload))
    for suffix,blob in (('stdout.log',stdout),('stderr.log',stderr),('exit.json',payload)):
        with (OUT/('probe.'+suffix)).open('xb') as stream:stream.write(blob)
    print(json.dumps(dict(accepted=bool(accepted),charged_seconds=charged,returncode=code,handle_closed=handle_closed,peak_working_set_bytes=peak),sort_keys=True))
    if not accepted:raise SystemExit(1)
except BaseException as failure:
    if not (OUT/'probe.exit.json').exists():
        charged=time.perf_counter()-STARTED+.5
        fallback=dict(authority='DRAFT_NONAUTHORITATIVE',label='machinery_probe',kind='static',accepted=False,
            diagnostic_capture_accepted=False,error_type=type(failure).__name__,charged_seconds=charged,cap_seconds=12,
            tail_reserve_seconds=.5,child_created=globals().get('process') is not None,partial_capture=True,
            raw_stdout_and_stderr_complete=False,predecessor_combined_resource_admission=False,
            policy_resource_admission=False,cold_acceptance=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False)
        candidate=globals().get('admission')
        if type(candidate) is dict:
            registered=candidate.get('registration_charged_seconds');previous=candidate.get('predecessor_charged_seconds')
            if type(registered) in (int,float) and 0<=registered<=10000 and type(previous) is dict and all(type(previous.get(k)) in (int,float) and 0<=previous[k]<=10000 for k in ('static','pytest')):
                successor=dict(static=registered+charged,pytest=0)
                fallback.update(predecessor_charged_seconds=previous,successor_charged_seconds=successor,
                    all_cumulative_charged_seconds={k:previous[k]+successor[k] for k in successor})
        save('probe.exit.json',fallback)
    raise
