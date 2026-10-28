"""Unit subprocess capture with the unchanged native sampled memory/drain actor."""
import ctypes as C
from ctypes import wintypes as W
import importlib.util
from pathlib import Path
import subprocess

ROOT=Path(__file__).absolute().parents[1]
EXE='D:/Miniconda3/envs/compute/python.exe'


def bounded(argv,timeout):
    path=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py'
    spec=importlib.util.spec_from_file_location('_sampled_unit_drain',path);drain=importlib.util.module_from_spec(spec);spec.loader.exec_module(drain)
    process=None;rc=None;out=err=b'';reason=None;observation=None;closed=False;cleanup=[]
    try:
        if timeout<=0:raise TimeoutError('no unit budget')
        process=subprocess.Popen(argv,executable=EXE,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        rc,out,err,reason,observation=drain.drain(process,float(timeout))
    except BaseException as error:reason=type(error).__name__+':'+str(error)[:160]
    finally:
        if process is not None:
            try:
                if process.poll() is None:process.kill();process.wait(timeout=1.)
            except BaseException as error:cleanup.append('terminal:'+type(error).__name__)
            try:
                handle=int(process._handle);process._handle.Close()
                check=C.WinDLL('kernel32',use_last_error=True).GetHandleInformation
                check.argtypes=[W.HANDLE,C.POINTER(W.DWORD)];check.restype=W.BOOL
                flags=W.DWORD();C.set_last_error(0)
                closed=process._handle.closed and not check(W.HANDLE(handle),C.byref(flags)) and C.get_last_error()==6
            except BaseException as error:cleanup.append('handle:'+type(error).__name__)
    guard=None if observation is None else observation['memory_guard']
    peak=None if guard is None or guard['samples']==0 else guard['maxima']['child']['peak_working_set_bytes']
    return rc,out,err,reason,dict(bounded_drain=observation,handle_closed=closed,peak_working_set_bytes=peak,cleanup=cleanup)
