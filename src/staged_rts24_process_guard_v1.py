"""Bounded polling/Job RSS on the existing atomic Windows child owner."""
import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import stat
import time
import math

from src.rq2_joint_deliverability_boundary_v1.normal_process import (
    DevelopmentNormalChild, _check, _Limits, _Accounting,
)


class _Memory(C.Structure):
    _fields_ = [("cb", W.DWORD), ("faults", W.DWORD)] + [(name, C.c_size_t) for name in
        ("peak_working_set", "working_set", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]


class OwnedChild(DevelopmentNormalChild):
    def __init__(self, *a, **kw):
        self._members = {}
        self.quiescence_witness = None
        super().__init__(*a, **kw)
        self._members[(self.pid, self.creation_filetime)] = self._process

    def job_pids(self):
        self._live_owner()
        data = C.create_string_buffer(8+1024*C.sizeof(C.c_size_t))
        _check(self._k.QueryInformationJobObject(self._job, 3, data, len(data), None))
        count = W.DWORD.from_buffer(data, 4).value
        if count > 1024 or W.DWORD.from_buffer(data, 0).value != count: raise OSError("owned process inventory incomplete")
        pids = list((C.c_size_t*count).from_buffer(data, 8))
        if len(set(pids)) != count: raise OSError("duplicate owned process identity")
        return pids

    def open_member(self, pid, access):
        self._k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self._k.OpenProcess.restype = W.HANDLE
        handle = self._k.OpenProcess(access, False, pid)
        if not handle:
            if C.get_last_error() in (87, 1168): return None
            _check(handle)
        try:
            inside = W.BOOL()
            _check(self._k.IsProcessInJob(handle, self._job, C.byref(inside)))
            if inside.value: return handle
        except BaseException:
            _check(self._k.CloseHandle(handle))
            raise
        _check(self._k.CloseHandle(handle))
        return None

    def poll(self):
        self._live_owner()
        state = self._k.WaitForSingleObject(self._process, 0)
        if state == 258: return None
        if state != 0: raise OSError("owned process observation failed")
        code = W.DWORD()
        _check(self._k.GetExitCodeProcess(self._process, C.byref(code)))
        return code.value

    def capture_members(self):
        for pid in self.job_pids():
            if pid == self.pid: continue
            handle = self.open_member(pid, 0x100000 | 0x410)
            if handle is None: continue
            try:
                creation, end, kernel, user = (W.FILETIME() for _ in range(4))
                _check(self._k.GetProcessTimes(handle, C.byref(creation), C.byref(end), C.byref(kernel), C.byref(user)))
                identity = (pid, creation.dwLowDateTime | creation.dwHighDateTime << 32)
                if identity not in self._members:
                    if len(self._members) >= 1024: raise OSError("retained member HANDLE cap")
                    self._members[identity], handle = handle, None
            finally:
                if handle is not None: _check(self._k.CloseHandle(handle))

    def sample(self):
        self._live_owner()
        pids = self.job_pids()
        self.capture_members()
        self._k.K32GetProcessMemoryInfo.argtypes = [W.HANDLE, C.c_void_p, W.DWORD]
        self._k.K32GetProcessMemoryInfo.restype = W.BOOL
        rss = 0
        for handle in self._members.values():
            state = self._k.WaitForSingleObject(handle, 0)
            if state == 0: continue
            if state != 258: raise OSError("member observation failed")
            mem = _Memory()
            mem.cb = C.sizeof(mem)
            if not self._k.K32GetProcessMemoryInfo(handle, C.byref(mem), C.sizeof(mem)):
                if self._k.WaitForSingleObject(handle, 0) == 0: continue
                _check(False)
            rss += mem.working_set
        limits = _Limits()
        _check(self._k.QueryInformationJobObject(self._job, 9, C.byref(limits), C.sizeof(limits), None))
        return dict(rss_bytes=rss, processes=len(pids), pids=pids, peak_job_commit_bytes=limits.peak_job)

    def quiesce(self, *, max_seconds):
        """Job accounting zero plus signaled retained process handles."""
        self._live_owner()
        if type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or not 0 < max_seconds <= 5:
            raise ValueError("explicit quiescence timeout in (0, 5] required")
        deadline = time.monotonic()+max_seconds
        self.capture_members()
        remaining = deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError("ownership snapshot exceeded quiescence deadline")
        super().quiesce(max_seconds=remaining)
        self.quiescence_witness = dict(observed_unique_member_handles=len(self._members), all_handles_signaled=False,
            member_identities=[dict(pid=pid, creation_filetime=creation) for pid, creation in self._members])
        for handle in self._members.values():
            state = self._k.WaitForSingleObject(handle, math.ceil(max(0, deadline-time.monotonic())*1000))
            if state != 0: raise OSError("owned member termination signal not confirmed")
        accounting = _Accounting()
        _check(self._k.QueryInformationJobObject(self._job, 1, C.byref(accounting), C.sizeof(accounting), None))
        final_pids = self.job_pids()
        self.quiescence_witness.update(all_handles_signaled=True, total_processes=accounting.total, final_pids=final_pids,
            active_processes=accounting.active, complete_inventory=accounting.total == len(self._members))
        if time.monotonic() > deadline: raise TimeoutError("quiescence deadline exceeded")
        if accounting.active or final_pids or accounting.total != len(self._members):
            raise OSError("complete member HANDLE inventory unresolved")

    def close(self):
        errors = []
        for identity, handle in tuple(self._members.items()):
            if handle == self._process: continue
            try: _check(self._k.CloseHandle(handle)); del self._members[identity]
            except BaseException as error: errors.append(error)
        try: super().close()
        except BaseException as error: errors.append(error)
        if self._process is None:
            self._members.pop((self.pid, self.creation_filetime), None)
        if errors: raise errors[0]


def controlled_environment():
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "USERPROFILE",
               "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "COMMONPROGRAMFILES",
               "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"}
    result = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    result.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PYTHONHASHSEED="0",
                  OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    return result


def scan_output(root, byte_cap, file_cap):
    total, files = 0, 0
    for directory, names, leaves in os.walk(root, followlinks=False):
        for name in names+leaves:
            path = Path(directory)/name
            try: info = path.lstat()
            except FileNotFoundError: continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0)&0x400:
                raise ValueError("linked output is not allowed")
            if stat.S_ISREG(info.st_mode): total, files = total+info.st_size, files+1
            if total > byte_cap or files > file_cap: return total, files
    return total, files


def supervise(argv, *, cwd, output, progress, limits, owner_factory=OwnedChild):
    """No scientific result inspection until the complete owned Job is quiet."""
    caps = dict(wall_seconds=300, no_progress_seconds=30, rss_bytes=1024**3, output_bytes=64*1024**2, files=5000)
    if type(limits) is not dict or set(limits) != set(caps): raise ValueError("explicit monitor limits required")
    for name, cap in caps.items():
        v = limits[name]
        if type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= cap:
            raise ValueError("monitor limit outside P1 cap")
        if name in ("rss_bytes", "output_bytes", "files") and type(v) is not int:
            raise ValueError("integer monitor byte/file limits required")
    start = last_progress = time.monotonic()
    prior, owner, exit_code, reason, error, cleanup_error = -1, None, None, None, None, None
    peak_rss = peak_commit = samples = 0
    quiet = False
    size = files = 0
    try:
        owner = owner_factory(argv, cwd=cwd, max_process_commit_bytes=1024**3,
            max_job_commit_bytes=2*1024**3, environment=controlled_environment())
        owner.release()
        while owner.poll() is None:
            now = time.monotonic()
            measurement = owner.sample()
            peak_rss, peak_commit = max(peak_rss, measurement["rss_bytes"]), max(peak_commit, measurement["peak_job_commit_bytes"])
            size, files = scan_output(output, limits["output_bytes"], limits["files"])
            try: event_size = Path(progress).stat().st_size
            except FileNotFoundError: event_size = 0
            if event_size < prior: raise ValueError("progress history shrank")
            if event_size != prior: prior, last_progress = event_size, now
            if now-start > limits["wall_seconds"]: reason = "wall_limit"
            elif now-last_progress > limits["no_progress_seconds"]: reason = "no_progress"
            elif peak_rss > limits["rss_bytes"]: reason = "rss_limit"
            elif size > limits["output_bytes"] or files > limits["files"]: reason = "storage_limit"
            samples += 1
            if reason: break
            time.sleep(.2)
        exit_code = owner.poll()
        if exit_code is not None:
            terminal = owner.sample()
            peak_commit = max(peak_commit, terminal["peak_job_commit_bytes"])
            if any(pid != owner.pid for pid in terminal["pids"]): reason = reason or "root_exited_with_descendants"
        if exit_code is not None and exit_code != 0: reason = reason or "child_exit_nonzero"
    except BaseException as exc:
        reason, error = reason or "monitor_exception", f"{type(exc).__name__}: {exc}"
    finally:
        if owner is not None:
            try:
                owner.quiesce(max_seconds=5)
                quiet = True
                exit_code = owner.poll()
            except BaseException as exc:
                cleanup_error, reason = f"{type(exc).__name__}: {exc}", reason or "cleanup_unknown"
            finally:
                try: owner.close()
                except BaseException as exc:
                    cleanup_error, reason = f"{type(exc).__name__}: {exc}", reason or "close_unknown"
                    quiet = False
    # Include output produced just before exit; reserve a terminal record.
    try:
        size, files = scan_output(output, limits["output_bytes"], limits["files"])
        if time.monotonic()-start > limits["wall_seconds"]: reason = reason or "terminal_wall_limit"
        elif time.monotonic()-last_progress > limits["no_progress_seconds"]: reason = reason or "terminal_no_progress"
        elif size+16384 > limits["output_bytes"] or files+1 > limits["files"]: reason = reason or "terminal_storage_limit"
    except BaseException as exc:
        error, reason = f"{type(exc).__name__}: {exc}", reason or "terminal_scan_error"
    return dict(exit_code=exit_code, stop_reason=reason, monitor_error=error, cleanup_error=cleanup_error,
        job_quiet_confirmed=quiet, outer_seconds=time.monotonic()-start,
        sampled_tree_peak_rss_bytes=peak_rss if samples else None, rss_observation_available=bool(samples),
        peak_job_commit_bytes=peak_commit, samples=samples, terminal_bytes=size, terminal_files=files,
        terminal_reserved_bytes=16384, owner_pid=owner.pid if owner else None,
        owner_creation_filetime=owner.creation_filetime if owner else None,
        quiescence_witness=getattr(owner, "quiescence_witness", None))
