"""Exercise the exact monitor helper definitions with owned tiny child processes."""
import ast
from hashlib import sha256
import json
import msvcrt
from pathlib import Path
import subprocess
import sys
import time

import psutil
import pytest

PATH=Path(__file__).resolve().parents[1]/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_operation_witness_01/run_saved_bounded_v1.py'
EXPECTED_OUTER_SHA256='a8fa8490325b20397e63e1978a3f98cbbb5f0fac565bc1bed69cf7e6cdcc01b0'


def helpers(tmp_path):
    # Execute unmodified helper AST nodes only; do not execute the fixed saved
    # experiment's CLI, directory creation or its real input-tree scan.
    raw=PATH.read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_OUTER_SHA256
    parsed=ast.parse(raw,filename=str(PATH))
    definitions=ast.Module(body=[node for node in parsed.body if isinstance(node,ast.FunctionDef)],type_ignores=[])
    namespace=dict(psutil=psutil,time=time,msvcrt=msvcrt,owned={},events=[],errors=[],result={},SAVED=tmp_path)
    exec(compile(definitions,str(PATH),'exec'),namespace)
    return namespace


def test_monitor_kills_and_waits_observed_owned_process_tree(tmp_path):
    ns=helpers(tmp_path);child=tmp_path/'grandchild_pid.json'
    code='import subprocess,sys,time,json; from pathlib import Path; p=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(30)"]); Path(sys.argv[1]).write_text(json.dumps(p.pid)); time.sleep(30)'
    proc=subprocess.Popen([sys.executable,'-B','-c',code,str(child)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    ns['owned'][proc.pid]=psutil.Process(proc.pid).create_time();grand=None
    try:
        deadline=time.monotonic()+5
        while not child.exists() and time.monotonic()<deadline:time.sleep(.02)
        assert child.exists();grand=psutil.Process(json.loads(child.read_text()))
        ns['observe']();assert grand.pid in ns['owned']
        ns['finish_children']()
        assert ns['result']['observed_owned_processes_absent'] and not ns['errors']
        assert proc.wait(timeout=1)!=0
        assert ns['live'](grand.pid,ns['owned'][grand.pid]) is None
    finally:
        for p in (grand,psutil.Process(proc.pid) if proc.poll() is None else None):
            if p is not None:
                try:p.kill()
                except psutil.Error:pass
        proc.wait(timeout=2)


def test_monitor_creation_identity_fence_does_not_claim_ownership_of_wrong_process(tmp_path):
    ns=helpers(tmp_path);proc=psutil.Process()
    ns['owned'][proc.pid]=proc.create_time()-1
    ns['finish_children']()
    assert ns['result']['observed_owned_processes_absent'] and ns['events']==[]
    assert proc.is_running()


def test_monitor_saved_lock_probe_detects_live_owner_and_releases_successful_probe(tmp_path):
    ns=helpers(tmp_path);path=tmp_path/'execution.lock';path.write_bytes(b'0')
    with path.open('r+b',buffering=0) as stream:
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        try:
            with pytest.raises(OSError):ns['lock_postcheck']()
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    assert ns['lock_postcheck']()['all_reacquired_and_released']
    with path.open('r+b',buffering=0) as stream:
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
