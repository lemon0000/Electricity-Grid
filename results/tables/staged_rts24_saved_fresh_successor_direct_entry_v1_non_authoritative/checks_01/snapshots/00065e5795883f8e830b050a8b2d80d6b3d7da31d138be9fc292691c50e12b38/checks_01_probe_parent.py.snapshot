"""One bounded ordinary child per case; expected frozen before Popen, no ENTRY import."""
import ctypes as C
from ctypes import wintypes as W
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from common import ROOT,OUT,EXE,selected,pin,canonical,save
from probe_compare import compare,compare_failure
from probe_files import files as bounded_files
from bounded_child import drain_child

case=sys.argv[1] if len(sys.argv)>1 else 'normal'
assert case in ('normal','argv','alias','path','environment','helper','commit','oversize')
entry=ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py'
flag='--ordinary-successor-entry-observe'
argv=[str(EXE),'-B','-s',str(entry),flag]+([] if case=='normal' else ['--fault',case])
spec=json.loads((ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/successor_context_spec_v3.json').read_bytes())
environment={k:v for k,v in os.environ.items() if k.upper() in spec['environment_allowed_keys']}
environment.update(spec['environment_fixed_values'])
source=selected();files=bounded_files(ROOT,tuple(source),EXE)
assert all(files[n]['pin']==source[n] for n in source)
libraries=[p for p in sys.path[1:] if p and Path(p).is_absolute() and Path(p).is_relative_to(EXE.parent)]
assert len(libraries)==len(set(p.casefold() for p in libraries))
expected_raw=canonical(dict(argv=argv,initial_paths=[str(ROOT/'experiments'),*libraries],installed_paths=[str(ROOT),*libraries],
    environment=environment,files=files,cwd=str(ROOT),python=sys.version))
expected_path=OUT/('probe_'+case+'.expected.json');assert not expected_path.exists();expected_path.write_bytes(expected_raw)
api=C.WinDLL('kernel32',use_last_error=True)
for name,args,result in [('GetProcessId',[W.HANDLE],W.DWORD),('GetProcessTimes',[W.HANDLE]+[C.POINTER(W.FILETIME)]*4,W.BOOL),
    ('QueryFullProcessImageNameW',[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)],W.BOOL),
    ('GetHandleInformation',[W.HANDLE,C.POINTER(W.DWORD)],W.BOOL)]:
    fn=getattr(api,name);fn.argtypes,fn.restype=args,result
counts=dict(allowed_Popen=0,unexpected_process_attempts=0,P1_open_attempts=0)
active=True;allowed_command=subprocess.list2cmdline(argv)
def audit(event,args):
    if not active:return
    if event=='subprocess.Popen':
        if not (counts['allowed_Popen']==0 and args[0]==str(EXE) and args[1]==allowed_command and args[2]==str(ROOT) and args[3]==environment):
            counts['unexpected_process_attempts']+=1;raise AssertionError('ordinary parent Popen binding differs')
        counts['allowed_Popen']+=1;return
    if event=='os.system' or event.startswith('os.spawn'):
        counts['unexpected_process_attempts']+=1;raise AssertionError('ordinary parent unexpected process')
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).absolute()
        if p.is_relative_to(ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'):
            counts['P1_open_attempts']+=1;raise AssertionError('ordinary parent attempted P1')
sys.addaudithook(audit)
process=None;stdout=stderr=b'';returncode=None;identity=None;primary=None;cleanup=[];closed=False;result=None;drained=None
started=time.monotonic()
try:
    process=subprocess.Popen(argv,executable=str(EXE),cwd=ROOT,env=environment,creationflags=subprocess.CREATE_NO_WINDOW,
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    handle=process._handle;creation=W.FILETIME();rest=[W.FILETIME() for _ in range(3)]
    assert api.GetProcessId(handle)==process.pid and api.GetProcessTimes(handle,C.byref(creation),*[C.byref(v) for v in rest])
    image=C.create_unicode_buffer(32768);size=W.DWORD(len(image))
    assert api.QueryFullProcessImageNameW(handle,0,image,C.byref(size)) and 0<size.value<len(image)
    assert len(image.value)==size.value and Path(image.value).is_absolute()
    assert str(Path(image.value).absolute()).casefold()==str(EXE).casefold()
    identity=(process.pid,creation.dwLowDateTime | creation.dwHighDateTime<<32,image.value)
    save('probe_'+case+'.started.json',dict(child_identity=identity,expected_pin=pin(expected_raw),terminal=False,ordinary_probe=True))
    drained=drain_child(process,2);stdout,stderr=drained.pop('stdout'),drained.pop('stderr');returncode=process.returncode
    assert drained['cleanup']==[] and drained['pipes_closed'] and drained['reader_threads_terminal']
    assert len(stdout)<=131073 and len(stderr)<=4096
    if case=='oversize':
        assert drained['stop_reason']=='stdout_limit' and drained['kill_requested'] and returncode is not None
        assert len(stdout)==131073 and stderr==b''
        result=dict(bounded_stdout_overflow_rejected=True,ordinary_probe=True,role_binding=False,external_Job_owner=False)
    elif case=='normal':
        assert drained['stop_reason'] is None and stderr==b'' and stdout.endswith(b'\n')
        assert returncode==0;result=compare(stdout[:-1],expected_raw,identity)
    else:
        assert drained['stop_reason'] is None and stderr==b'' and stdout.endswith(b'\n') and returncode==1
        result=compare_failure(stdout[:-1],case)
    assert selected()==source and expected_path.read_bytes()==expected_raw
except BaseException as error:primary=error
finally:
    if process is not None:
        if process.poll() is None:
            try:process.kill();process.wait(timeout=1)
            except BaseException as error:cleanup.append(('kill_wait',repr(error)))
        returncode=process.returncode
        if drained is None:
            try:
                drained=drain_child(process,.1);stdout,stderr=drained.pop('stdout'),drained.pop('stderr')
                cleanup.extend(drained['cleanup'])
            except BaseException as error:cleanup.append(('drain',repr(error)))
        for name in ('stdin','stdout','stderr'):
            stream=getattr(process,name)
            if stream is not None:
                if name in ('stdout','stderr') and drained is not None and not drained['reader_threads_terminal']:
                    cleanup.append(('pending_pipe',name));continue
                try:stream.close()
                except BaseException as error:cleanup.append((name,repr(error)))
        try:
            process._handle.Close();flags=W.DWORD();C.set_last_error(0)
            closed=api.GetHandleInformation(process._handle,C.byref(flags))==0 and C.get_last_error()==6
            assert closed
        except BaseException as error:cleanup.append(('process_handle',repr(error)))
    active=False
for name,raw in [('stdout.log',stdout),('stderr.log',stderr)]:
    path=OUT/('probe_'+case+'.child.'+name);assert not path.exists();path.write_bytes(raw)
save('probe_'+case+'.result.json',dict(authority='DRAFT_NONAUTHORITATIVE',case=case,result=result,
    expected_pin=pin(expected_raw),child_identity=identity,child_exit=returncode,child_process_handle_closed=closed,
    parent_seconds=time.monotonic()-started,audit_counts=counts,primary=None if primary is None else repr(primary),cleanup=cleanup,
    stdout_pin=pin(stdout),stderr_pin=pin(stderr),source_pins=source,ordinary_probe=True,actual_saved_F_execution=False,
    F_launch_admitted=False,Job_quiet_proved=False,bounded_drain=drained))
assert primary is None and cleanup==[] and closed and counts==dict(allowed_Popen=1,unexpected_process_attempts=0,P1_open_attempts=0)
print(json.dumps(dict(case=case,child_exit=returncode,child_process_handle_closed=closed,parent_seconds=time.monotonic()-started)))
