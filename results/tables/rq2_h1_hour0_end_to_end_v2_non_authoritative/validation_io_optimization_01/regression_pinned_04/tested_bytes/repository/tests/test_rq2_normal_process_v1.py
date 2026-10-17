"""Short real Windows processes, no solver and no repository result writes."""
import ctypes as c
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_process as p


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows ownership contract')
ROOT = Path(__file__).resolve().parents[1]
CAP = 128 * 1024 * 1024


def child(tmp_path, code, cap=CAP):
    return p.DevelopmentNormalChild([sys.executable, '-B', '-c', code],
        cwd=tmp_path, max_process_commit_bytes=cap)


def test_real_suspended_release_and_exit(tmp_path):
    marker = tmp_path/'ran.txt'
    with child(tmp_path, "from pathlib import Path; Path('ran.txt').write_text('ok')") as owner:
        assert owner.creation_filetime > 0
        assert not marker.exists()
        owner.release()
        observed = owner.wait(max_elapsed_seconds=5)
        assert observed.exit_code == 0
        assert observed.reason == 'child_exited'
        assert observed.job_peak_process_commit_bytes > 0
        assert not observed.numerical_evidence_verified and not observed.formal_result
        assert marker.read_text() == 'ok'
        with pytest.raises(RuntimeError, match='already released'):
            owner.release()
    with pytest.raises(RuntimeError):
        owner.release()


def test_deadline_terminates_owned_child_not_bystander(tmp_path):
    bystander = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(20)'],
                                  creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        with child(tmp_path, 'import time; time.sleep(20)') as owner:
            owner.release()
            observed = owner.wait(max_elapsed_seconds=.2)
            assert observed.reason == 'deadline_termination'
            assert observed.exit_code == 0xE001
            assert bystander.poll() is None
    finally:
        bystander.terminate()
        bystander.wait(timeout=5)


def test_nonzero_exit_is_not_success(tmp_path):
    with child(tmp_path, 'raise SystemExit(7)') as owner:
        owner.release()
        assert owner.wait(max_elapsed_seconds=5).exit_code == 7


def test_job_memory_limit_rejects_allocation(tmp_path):
    code = """
from pathlib import Path
try:
    data = bytearray(256 * 1024 * 1024)
except MemoryError:
    Path('limited.txt').write_text('limited')
else:
    raise SystemExit(9)
"""
    with child(tmp_path, code) as owner:
        owner.release()
        result = owner.wait(max_elapsed_seconds=5)
        assert result.exit_code == 0
        assert (tmp_path/'limited.txt').read_text() == 'limited'
        assert result.job_peak_process_commit_bytes <= CAP


@pytest.mark.parametrize('error', [KeyboardInterrupt, SystemExit, RuntimeError])
def test_exception_closes_job_and_kills_child(tmp_path, error):
    # Duplicate only the process handle for observing exit; never duplicate Job.
    import _winapi
    handle = None
    try:
        with pytest.raises(error):
            with child(tmp_path, 'import time; time.sleep(20)') as owner:
                handle = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), owner._process,
                    _winapi.GetCurrentProcess(), 0, False, _winapi.DUPLICATE_SAME_ACCESS)
                owner.release()
                raise error()
        assert _winapi.WaitForSingleObject(handle, 5000) == 0
    finally:
        if handle is not None:
            _winapi.CloseHandle(handle)


@pytest.mark.parametrize('phase', ['inside_create', 'suspended', 'released'])
def test_parent_abrupt_exit_kills_member(tmp_path, phase):
    # Parent waits for our observation handle before os._exit, so PID reuse
    # cannot make this test pass by observing an unrelated process.
    code = f"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, {str(ROOT)!r})
from src.rq2_joint_deliverability_boundary_v1 import normal_process as p
def crash(pid):
    pending = Path({str(tmp_path/'pid.pending')!r})
    pending.write_text(str(pid))
    pending.replace({str(tmp_path/'pid')!r})
    deadline = time.monotonic() + 10
    while not Path({str(tmp_path/'ack')!r}).exists():
        if time.monotonic() > deadline: raise SystemExit(8)
        time.sleep(.01)
    os._exit(17)
if {phase!r} == 'inside_create':
    k = p._api()
    real_create = k.CreateProcessW
    def create(*args):
        result = real_create(*args)
        if result:
            info = p.c.cast(args[-1], p.c.POINTER(p._ProcessInfo)).contents
            crash(info.pid)
        return result
    k.CreateProcessW = create
    p._api = lambda: k
owner = p.DevelopmentNormalChild([sys.executable, '-B', '-c', 'import time; time.sleep(20)'], cwd={str(tmp_path)!r}, max_process_commit_bytes={CAP})
if {phase!r} == 'released': owner.release()
crash(owner.pid)
"""
    parent = subprocess.Popen([sys.executable, '-B', '-c', code], creationflags=subprocess.CREATE_NO_WINDOW)
    handle = None
    k = p._api()
    k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    k.OpenProcess.restype = w.HANDLE
    try:
        deadline = time.monotonic() + 8
        while not (tmp_path/'pid').exists():
            assert parent.poll() is None
            assert time.monotonic() < deadline
            time.sleep(.01)
        pid = int((tmp_path/'pid').read_text())
        handle = p._check(k.OpenProcess(0x100000, False, pid))
        assert k.WaitForSingleObject(handle, 0) == 258
        (tmp_path/'ack').write_text('ok')
        assert parent.wait(timeout=5) == 17
        assert k.WaitForSingleObject(handle, 5000) == 0
    finally:
        if parent.poll() is None:
            parent.terminate()
            parent.wait(timeout=5)
        if handle:
            k.CloseHandle(handle)


def test_64bit_abi_layout_and_handle_signatures():
    assert c.sizeof(c.c_void_p) == 8
    assert c.sizeof(p._Basic) == 64
    assert c.sizeof(p._Limits) == 144
    assert c.sizeof(p._Startup) == 104
    assert c.sizeof(p._StartupEx) == 112
    assert c.sizeof(p._ProcessInfo) == 24
    k = p._api()
    assert k.CreateJobObjectW.restype is w.HANDLE
    for name in ('GetProcessTimes', 'WaitForSingleObject', 'GetExitCodeProcess', 'CloseHandle'):
        assert getattr(k, name).argtypes[0] is w.HANDLE
    # Independent callback proves the selected HANDLE ABI preserves high bits.
    callback = c.WINFUNCTYPE(c.c_size_t, w.HANDLE)(lambda h: h)
    assert callback(0x123456789ABC) == 0x123456789ABC


@pytest.mark.parametrize('cap', [True, 0, -1, 1.5, 2**65])
def test_bad_cap_rejected_before_spawn(tmp_path, cap):
    with pytest.raises(ValueError):
        child(tmp_path, 'raise SystemExit(99)', cap)


def test_bad_executable_rejected(tmp_path):
    with pytest.raises(ValueError):
        p.DevelopmentNormalChild(['python', '-V'], cwd=tmp_path, max_process_commit_bytes=CAP)


def test_failed_create_releases_job(tmp_path):
    invalid = tmp_path/'not-an-executable.exe'
    invalid.write_text('not executable')
    with pytest.raises(OSError):
        p.DevelopmentNormalChild([str(invalid)], cwd=tmp_path, max_process_commit_bytes=CAP)


def test_wait_requires_release_and_valid_deadline(tmp_path):
    with child(tmp_path, 'pass') as owner:
        with pytest.raises(RuntimeError, match='release'):
            owner.wait(max_elapsed_seconds=1)
        owner.release()
        for seconds in (True, 0, -1, float('nan'), float('inf'), 61):
            with pytest.raises(ValueError):
                owner.wait(max_elapsed_seconds=seconds)
        owner.wait(max_elapsed_seconds=5)


def test_close_kills_descendant_even_after_direct_child_exits(tmp_path):
    code = """
import subprocess, sys
from pathlib import Path
p = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(20)'], creationflags=subprocess.CREATE_NO_WINDOW)
Path('descendant').write_text(str(p.pid))
"""
    k = p._api()
    k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    k.OpenProcess.restype = w.HANDLE
    handle = None
    try:
        with child(tmp_path, code) as owner:
            owner.release()
            assert owner.wait(max_elapsed_seconds=5).exit_code == 0
            handle = p._check(k.OpenProcess(0x100000, False, int((tmp_path/'descendant').read_text())))
            assert k.WaitForSingleObject(handle, 0) == 258
        assert k.WaitForSingleObject(handle, 5000) == 0
    finally:
        if handle:
            k.CloseHandle(handle)


def test_failed_membership_check_prevents_execution(tmp_path, monkeypatch):
    import _winapi
    k = p._api()
    handles = []

    def fail_membership(process, job, inside):
        handles.append(_winapi.DuplicateHandle(_winapi.GetCurrentProcess(), process,
            _winapi.GetCurrentProcess(), 0, False, _winapi.DUPLICATE_SAME_ACCESS))
        inside._obj.value = False
        return True

    k.IsProcessInJob = fail_membership
    monkeypatch.setattr(p, '_api', lambda: k)
    try:
        with pytest.raises(OSError, match='membership'):
            child(tmp_path, "from pathlib import Path; Path('bad').write_text('ran')")
        assert len(handles) == 1
        assert _winapi.WaitForSingleObject(handles[0], 5000) == 0
        assert not (tmp_path/'bad').exists()
    finally:
        for handle in handles:
            _winapi.CloseHandle(handle)


def test_interrupt_after_native_create_closes_both_returned_handles(tmp_path, monkeypatch):
    k = p._api()
    real_create = k.CreateProcessW
    created = []

    def interrupted_create(*args):
        result = real_create(*args)
        assert result
        info = c.cast(args[-1], c.POINTER(p._ProcessInfo)).contents
        created.extend([info.process, info.thread])
        raise KeyboardInterrupt()

    k.CreateProcessW = interrupted_create
    monkeypatch.setattr(p, '_api', lambda: k)
    with pytest.raises(KeyboardInterrupt):
        child(tmp_path, 'pass')
    for handle in created:
        flags = w.DWORD()
        assert not k.GetHandleInformation(handle, c.byref(flags))
        assert c.get_last_error() == 6


def test_explicit_environment_and_whole_job_quiescence(tmp_path):
    import json
    env = dict(SYSTEMROOT=os.environ['SYSTEMROOT'], NORMAL_MARKER='explicit-value')
    code = "import os,json; from pathlib import Path; Path('env.json').write_text(json.dumps(dict(os.environ)))"
    with p.DevelopmentNormalChild([sys.executable, '-B', '-c', code], cwd=tmp_path,
            max_process_commit_bytes=CAP, max_job_commit_bytes=2*CAP, environment=env) as owner:
        owner.release()
        assert owner.wait(max_elapsed_seconds=5).exit_code == 0
        owner.quiesce(max_seconds=1)
        assert json.loads((tmp_path/'env.json').read_text()) == env
        limits = p._Limits()
        assert owner._k.QueryInformationJobObject(owner._job, 9, c.byref(limits), c.sizeof(limits), None)
        assert limits.job_memory == 2*CAP
        assert limits.basic.flags & 0x200


def test_quiescence_waits_for_descendant(tmp_path):
    code = """
import subprocess, sys
p = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(20)'], creationflags=subprocess.CREATE_NO_WINDOW)
"""
    with child(tmp_path, code) as owner:
        owner.release()
        assert owner.wait(max_elapsed_seconds=5).exit_code == 0
        owner.quiesce(max_seconds=2)
        a = p._Accounting()
        assert owner._k.QueryInformationJobObject(owner._job, 1, c.byref(a), c.sizeof(a), None)
        assert a.active == 0 and a.total >= 2


def test_cross_thread_operations_rejected(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    with child(tmp_path, 'pass') as owner:
        with ThreadPoolExecutor(1) as pool:
            for operation in (owner.release, owner.close):
                with pytest.raises(RuntimeError):
                    pool.submit(operation).result()
        owner.release()
        owner.wait(max_elapsed_seconds=5)
        owner.quiesce(max_seconds=1)


def test_quiescence_timeout_does_not_claim_quiet(tmp_path, monkeypatch):
    with child(tmp_path, 'pass') as owner:
        real_query = owner._k.QueryInformationJobObject
        def nonquiet(job, kind, payload, size, returned):
            if kind == 1:
                payload._obj.active = 1
                return True
            return real_query(job, kind, payload, size, returned)
        monkeypatch.setattr(owner._k, 'QueryInformationJobObject', nonquiet)
        with pytest.raises(TimeoutError):
            owner.quiesce(max_seconds=.01)


@pytest.mark.parametrize('job_mib, expected_exit', [(160, 0), (256, 9)])
def test_real_aggregate_job_limit_rejects_two_member_allocation(tmp_path, job_mib, expected_exit):
    allocate = """
from pathlib import Path
try:
    data = bytearray(80 * 1024 * 1024)
except MemoryError:
    Path('aggregate_limited').write_text('yes')
else:
    raise SystemExit(9)
"""
    code = ("import subprocess,sys; data=bytearray(80*1024*1024); "
            "result=subprocess.run([sys.executable,'-B','-c',"+repr(allocate)+"], "
            "creationflags=subprocess.CREATE_NO_WINDOW, timeout=5); raise SystemExit(result.returncode)")
    with p.DevelopmentNormalChild([sys.executable, '-B', '-c', code], cwd=tmp_path,
            max_process_commit_bytes=128*1024**2, max_job_commit_bytes=job_mib*1024**2) as owner:
        owner.release()
        result = owner.wait(max_elapsed_seconds=6)
        owner.quiesce(max_seconds=1)
        assert result.exit_code == expected_exit
        assert result.job_peak_process_commit_bytes < 128*1024**2
        assert (tmp_path/'aggregate_limited').exists() is (expected_exit == 0)
