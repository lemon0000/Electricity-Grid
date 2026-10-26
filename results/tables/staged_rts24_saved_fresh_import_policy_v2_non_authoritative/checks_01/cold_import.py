"""Bounded ordinary cold-import children; no OwnedChild/Job or scientific calls."""
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2]
ENTRY=ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py';EXE=Path('D:/Miniconda3/envs/compute/python.exe')
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def child(case):
    assert case in ('normal','caught_effect','blocked_installation')
    counts=dict(P1_open=0,actual_F_open=0,write_attempts=0,unexpected_process=0,optional_seen=0,lifecycle_injections=0)
    p1=os.path.normcase(str(ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'))
    actual=os.path.normcase(str(ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'))
    source=raw(json.loads((OUT/('admission_revision.json' if (OUT/'admission_revision.json').exists() else 'admission.json')).read_bytes())['source_pins']);injected=False
    def audit(event,args):
        nonlocal injected
        if case=='blocked_installation' and event=='sys.addaudithook':raise RuntimeError('fixed installation rejection')
        if event=='electricity_grid.saved_import.after_dependency_import' and case=='caught_effect' and not injected:
            injected=True;counts['lifecycle_injections']+=1
            try:sys.audit('os.system',b'PRIVATE_TEST_EVENT_NOT_EXECUTED')
            except BaseException:pass
        if event=='subprocess.Popen':
            if tuple(args)==(None,'lscpu',None,None):counts['optional_seen']+=1
            else:counts['unexpected_process']+=1;raise AssertionError('cold import attempted an unlisted process')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])));mode,flags=args[1:3]
            if path==p1 or path.startswith(p1+os.sep):counts['P1_open']+=1;raise AssertionError('cold import attempted P1 read')
            if path==actual or path.startswith(actual+os.sep):counts['actual_F_open']+=1;raise AssertionError('cold import attempted actual-F read')
            if type(mode) is str and any(c in mode for c in 'wax+') or type(flags) is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                counts['write_attempts']+=1;raise AssertionError('cold import attempted file write')
    sys.addaudithook(audit);sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('_successor_import_entry',ENTRY);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    result=None;error=None;boundary=None;returned=False
    try:
        adapter,boundary=module.load_saved_successor_dependencies(json.loads(source),(OUT/'import_policy.json').read_bytes());returned=True
        result=json.loads(boundary.report_raw)
    except BaseException as caught:
        error=type(caught).__name__
        boundary=getattr(caught,'boundary',None)
        if boundary is not None:result=json.loads(boundary.report_raw)
    record=dict(authority='DRAFT_NONAUTHORITATIVE',case=case,loader_returned=returned,error_type=error,boundary=result,
        counts=counts,scientific_API_calls_instrumented=False,manual_fault_event_only=case=='caught_effect',actual_F=False,run_authority=False,formal_result=False)
    if case=='normal':
        assert returned and result['phase']=='CLOSED' and result['optional_Popen_attempts']==result['blocked_optional_attempts']==1
        assert result['internal_introspection_events']==6 and result['source49_bookend_equal'] and not result['hook_active']
    else:
        assert not returned and error=='SavedSuccessorImportUnresolved' and result is not None and result['phase']=='FAULTED' and not result['hook_active']
        if case=='caught_effect':assert result['violations']==1 and counts['lifecycle_injections']==1
        else:assert result['installation_sentinel_observed']==0 and result['optional_Popen_attempts']==0
    assert all(counts[n]==0 for n in ('P1_open','actual_F_open','write_attempts','unexpected_process'))
    print(json.dumps(record,sort_keys=True));raise SystemExit(0 if case=='normal' else 1)
def parent():
    import ctypes as C
    from ctypes import wintypes as W
    api=C.WinDLL('kernel32',use_last_error=True);check=api.GetHandleInformation
    check.argtypes=[W.HANDLE,C.POINTER(W.DWORD)];check.restype=W.BOOL
    start=time.perf_counter();deadline=start+7.5
    baseline=json.loads((OUT/'baseline.json').read_bytes());old=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative/checks_01/run.py'
    assert pin(old.read_bytes())==baseline['preserved'][old.relative_to(ROOT).as_posix()]
    spec=importlib.util.spec_from_file_location('frozen_cold_drain',old);capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
    allowed=[[str(EXE),'-B','-s',str(Path(__file__).resolve()),'--child',case] for case in baseline['cold_cases']];launches=[]
    def audit(event,args):
        if event=='subprocess.Popen':
            assert len(launches)<len(allowed) and list(args[1])==allowed[len(launches)] and str(args[2])==str(ROOT)
            launches.append(list(args[1]))
    sys.addaudithook(audit)
    for argv,case in zip(allowed,baseline['cold_cases']):
        remaining=min(3.,deadline-time.perf_counter()-.4);assert remaining>.5
        process=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        code,stdout,stderr,error,state=capture.drain(process,remaining)
        handle=int(process._handle);process._handle.Close();flags=W.DWORD();C.set_last_error(0)
        handle_closed=process._handle.closed and not check(W.HANDLE(handle),C.byref(flags)) and C.get_last_error()==6
        row=dict(authority='DRAFT_NONAUTHORITATIVE',case=case,argv=argv,returncode=code,error=error,stdout_pin=pin(stdout),stderr_pin=pin(stderr),bounded_drain=state,
            handle_closed=handle_closed,actual_F=False,run_authority=False,formal_result=False)
        if code==(0 if case=='normal' else 1) and error is None and not stderr:
            row['child_record']=json.loads(stdout);row['accepted']=row['child_record']['case']==case
        else:row['accepted']=False
        for suffix,data in (('stdout.log',stdout),('stderr.log',stderr),('json',raw(row))):
            with (OUT/('cold_'+case+'.'+suffix)).open('xb') as stream:stream.write(data)
        print(json.dumps(dict(case=case,accepted=row['accepted'],returncode=code,error=error,handle_closed=handle_closed),sort_keys=True))
        assert row['accepted'] and handle_closed
    assert launches==allowed
if __name__=='__main__':
    if sys.argv[1:2]==['--child']:child(sys.argv[2])
    else:parent()
