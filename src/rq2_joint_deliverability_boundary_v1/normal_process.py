"""Development Windows child ownership primitive, not a normal result verifier.

Create inside a kill-on-close Job, suspended, with no inherited handles.
One retained process HANDLE is used throughout; PID is diagnostic only.
"""
import ctypes as c
from ctypes import wintypes as w
from dataclasses import dataclass
import math
import os
from pathlib import Path
import subprocess
import time
from threading import get_ident


SIZE_T = c.c_size_t
HANDLE = w.HANDLE
DWORD = w.DWORD


class _Basic(c.Structure):
    _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong),
                ('flags', DWORD), ('min_ws', SIZE_T), ('max_ws', SIZE_T),
                ('active_processes', DWORD), ('affinity', SIZE_T),
                ('priority', DWORD), ('scheduling', DWORD)]


class _IO(c.Structure):
    _fields_ = [(name, c.c_ulonglong) for name in
                ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]


class _Limits(c.Structure):
    _fields_ = [('basic', _Basic), ('io', _IO), ('process_memory', SIZE_T),
                ('job_memory', SIZE_T), ('peak_process', SIZE_T), ('peak_job', SIZE_T)]


class _Startup(c.Structure):
    _fields_ = [('cb', DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR),
                ('title', w.LPWSTR)] + [(name, DWORD) for name in
                ('x', 'y', 'x_size', 'y_size', 'x_chars', 'y_chars', 'fill', 'flags')] + [
                ('show', w.WORD), ('reserved_size', w.WORD), ('reserved_ptr', c.c_void_p),
                ('stdin', HANDLE), ('stdout', HANDLE), ('stderr', HANDLE)]


class _StartupEx(c.Structure):
    _fields_ = [('startup', _Startup), ('attributes', c.c_void_p)]


class _ProcessInfo(c.Structure):
    _fields_ = [('process', HANDLE), ('thread', HANDLE), ('pid', DWORD), ('tid', DWORD)]


class _Accounting(c.Structure):
    _fields_ = [(name, c.c_longlong) for name in ('user', 'kernel', 'period_user', 'period_kernel')] + [
        (name, DWORD) for name in ('faults', 'total', 'active', 'terminated')]


def _environment_block(environment):
    if environment is None:
        return None
    if type(environment) is not dict or not environment:
        raise ValueError('nonempty explicit environment mapping required')
    names = set()
    for key, value in environment.items():
        if (type(key) is not str or not key or '=' in key or '\0' in key
                or type(value) is not str or '\0' in value or key.upper() in names):
            raise ValueError('invalid or duplicate Windows environment entry')
        names.add(key.upper())
    return c.create_unicode_buffer('\0'.join(k+'='+environment[k]
        for k in sorted(environment, key=str.upper))+'\0\0')


def _api():
    if os.name != 'nt':
        raise OSError('Windows 10+ Job-list process creation required')
    k = c.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': ([c.c_void_p, w.LPCWSTR], HANDLE),
        'SetInformationJobObject': ([HANDLE, c.c_int, c.c_void_p, DWORD], w.BOOL),
        'QueryInformationJobObject': ([HANDLE, c.c_int, c.c_void_p, DWORD, c.c_void_p], w.BOOL),
        'InitializeProcThreadAttributeList': ([c.c_void_p, DWORD, DWORD, c.POINTER(SIZE_T)], w.BOOL),
        'UpdateProcThreadAttribute': ([c.c_void_p, DWORD, SIZE_T, c.c_void_p, SIZE_T, c.c_void_p, c.c_void_p], w.BOOL),
        'DeleteProcThreadAttributeList': ([c.c_void_p], None),
        'CreateProcessW': ([w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL,
                            DWORD, c.c_void_p, w.LPCWSTR, c.POINTER(_StartupEx), c.POINTER(_ProcessInfo)], w.BOOL),
        'IsProcessInJob': ([HANDLE, HANDLE, c.POINTER(w.BOOL)], w.BOOL),
        'GetProcessTimes': ([HANDLE] + [c.POINTER(w.FILETIME)] * 4, w.BOOL),
        'GetHandleInformation': ([HANDLE, c.POINTER(DWORD)], w.BOOL),
        'ResumeThread': ([HANDLE], DWORD),
        'WaitForSingleObject': ([HANDLE, DWORD], DWORD),
        'GetExitCodeProcess': ([HANDLE, c.POINTER(DWORD)], w.BOOL),
        'TerminateJobObject': ([HANDLE, w.UINT], w.BOOL),
        'CloseHandle': ([HANDLE], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        fn = getattr(k, name)
        fn.argtypes, fn.restype = args, result
    return k


def _check(value):
    if not value:
        raise c.WinError(c.get_last_error())
    return value


@dataclass(frozen=True)
class ProcessObservation:
    pid: int
    creation_filetime: int
    exit_code: int
    reason: str
    elapsed_seconds: float
    job_peak_process_commit_bytes: int
    numerical_evidence_verified: bool = False
    formal_result: bool = False


class DevelopmentNormalChild:
    """Single-threaded context-managed owner of a short development child.

    No shell, stream capture, retry, persisted cursor, or solver status inference.
    A Job commit limit rejects allocations; it is not an RSS or disk limit.
    """
    def __init__(self, argv, *, cwd, max_process_commit_bytes, max_job_commit_bytes=None,
                 environment=None):
        if (not isinstance(argv, (tuple, list)) or not argv or
                any(type(x) is not str or not x or '\0' in x for x in argv)):
            raise ValueError('nonempty explicit string argv required')
        if not Path(argv[0]).is_absolute() or not Path(argv[0]).is_file():
            raise ValueError('absolute existing executable required')
        if type(max_process_commit_bytes) is not int or not 0 < max_process_commit_bytes <= SIZE_T(-1).value:
            raise ValueError('explicit positive process commit limit required')
        if max_job_commit_bytes is not None and (type(max_job_commit_bytes) is not int
                or not max_process_commit_bytes <= max_job_commit_bytes <= SIZE_T(-1).value):
            raise ValueError('job commit limit must cover process limit')
        environment_block = _environment_block(environment)
        directory = str(Path(cwd).resolve(strict=True))
        if not Path(directory).is_dir():
            raise ValueError('working directory required')
        self._k = _api()
        self._job = self._process = self._thread = None
        # CreateProcess writes this before Python regains control. Cleanup can
        # therefore recover both handles even if an interrupt precedes assignment.
        self._info = _ProcessInfo()
        self._released = False
        self._owner = os.getpid()
        self._owner_thread = get_ident()
        self._started = time.monotonic()
        self.pid = self.creation_filetime = None
        try:
            self._job = _check(self._k.CreateJobObjectW(None, None))
            limits = _Limits()
            limits.basic.flags = 0x2000 | 0x100  # KILL_ON_JOB_CLOSE | PROCESS_MEMORY
            limits.process_memory = max_process_commit_bytes
            if max_job_commit_bytes is not None:
                limits.basic.flags |= 0x200  # JOB_MEMORY
                limits.job_memory = max_job_commit_bytes
            _check(self._k.SetInformationJobObject(self._job, 9, c.byref(limits), c.sizeof(limits)))
            size = SIZE_T()
            self._k.InitializeProcThreadAttributeList(None, 1, 0, c.byref(size))
            if c.get_last_error() != 122 or not size.value:
                raise OSError('unexpected attribute size query')
            storage = c.create_string_buffer(size.value)
            _check(self._k.InitializeProcThreadAttributeList(storage, 1, 0, c.byref(size)))
            try:
                jobs = (HANDLE * 1)(self._job)
                _check(self._k.UpdateProcThreadAttribute(storage, 0, 0x2000D,
                    jobs, c.sizeof(jobs), None, None))  # PROC_THREAD_ATTRIBUTE_JOB_LIST
                startup = _StartupEx()
                startup.startup.cb = c.sizeof(startup)
                startup.attributes = c.cast(storage, c.c_void_p)
                info = self._info
                command = c.create_unicode_buffer(subprocess.list2cmdline(argv))
                _check(self._k.CreateProcessW(argv[0], command, None, None, False,
                    0x08000000 | 0x00080000 | 0x4 | 0x400, environment_block, directory,
                    c.byref(startup), c.byref(info)))  # NO_WINDOW | EXTENDED_STARTUP | SUSPENDED
                self._process, self._thread, self.pid = info.process, info.thread, info.pid
            finally:
                self._k.DeleteProcThreadAttributeList(storage)
            inside = w.BOOL()
            _check(self._k.IsProcessInJob(self._process, self._job, c.byref(inside)))
            if not inside.value:
                raise OSError('child missing required Job membership')
            for handle in (self._job, self._process, self._thread):
                flags = DWORD()
                _check(self._k.GetHandleInformation(handle, c.byref(flags)))
                if flags.value & 1:
                    raise OSError('owner handles must not be inheritable')
            creation, end, kernel, user = (w.FILETIME() for _ in range(4))
            _check(self._k.GetProcessTimes(self._process, c.byref(creation), c.byref(end),
                                         c.byref(kernel), c.byref(user)))
            self.creation_filetime = creation.dwLowDateTime | (creation.dwHighDateTime << 32)
        except BaseException:
            self.close()
            raise

    def _live_owner(self):
        if (os.getpid() != self._owner or get_ident() != self._owner_thread
                or self._process is None or self._job is None):
            raise RuntimeError('open creating process ownership required')

    def release(self):
        self._live_owner()
        if self._released:
            raise RuntimeError('child already released')
        previous = self._k.ResumeThread(self._thread)
        if previous != 1:
            raise OSError('unexpected suspended thread count')
        self._released = True

    def wait(self, *, max_elapsed_seconds):
        self._live_owner()
        if (type(max_elapsed_seconds) not in (int, float) or
                not math.isfinite(max_elapsed_seconds) or not 0 < max_elapsed_seconds <= 60):
            raise ValueError('explicit development deadline in (0, 60] seconds required')
        if not self._released:
            raise RuntimeError('release required before wait')
        deadline = self._started + max_elapsed_seconds
        remaining = max(0, deadline - time.monotonic())
        state = self._k.WaitForSingleObject(self._process, math.ceil(remaining * 1000))
        reason = 'child_exited'
        if state == 258:
            reason = 'deadline_termination'
            _check(self._k.TerminateJobObject(self._job, 0xE001))
            state = self._k.WaitForSingleObject(self._process, 5000)
        if state != 0:
            raise OSError('child termination not confirmed')
        code, limits = DWORD(), _Limits()
        _check(self._k.GetExitCodeProcess(self._process, c.byref(code)))
        _check(self._k.QueryInformationJobObject(self._job, 9, c.byref(limits), c.sizeof(limits), None))
        return ProcessObservation(self.pid, self.creation_filetime, code.value, reason,
                                  time.monotonic() - self._started, limits.peak_process)

    def quiesce(self, *, max_seconds):
        """Terminate any remaining members and confirm ActiveProcesses == 0.

        Must precede upper-layer artifact reads. A timeout is unknown, not quiet.
        """
        self._live_owner()
        if type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or not 0 < max_seconds <= 5:
            raise ValueError('explicit quiescence timeout in (0, 5] required')
        _check(self._k.TerminateJobObject(self._job, 0xE002))
        deadline = time.monotonic() + max_seconds
        while True:
            accounting = _Accounting()
            _check(self._k.QueryInformationJobObject(self._job, 1, c.byref(accounting),
                c.sizeof(accounting), None))
            if accounting.active == 0:
                return
            if time.monotonic() >= deadline:
                raise TimeoutError('whole Job quiescence not confirmed')
            time.sleep(min(.01, max(0, deadline-time.monotonic())))

    def close(self):
        if os.getpid() != self._owner or get_ident() != self._owner_thread:
            raise RuntimeError('only creating process may close owner')
        # Closing the non-inherited Job kills live members even on BaseException.
        if self._process is None and self._info.process:
            self._process = self._info.process
        if self._thread is None and self._info.thread:
            self._thread = self._info.thread
        errors = []
        for name in ('_job', '_thread', '_process'):
            handle = getattr(self, name)
            if handle is not None:
                if not self._k.CloseHandle(handle):
                    errors.append(c.WinError(c.get_last_error()))
                else:
                    setattr(self, name, None)
                    if name == '_process':
                        self._info.process = None
                    elif name == '_thread':
                        self._info.thread = None
        if errors:
            raise errors[0]

    def __enter__(self):
        self._live_owner()
        return self

    def __exit__(self, *_):
        self.close()

    def __copy__(self):
        raise TypeError('process owner cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('process owner cannot be copied')

    def __reduce__(self):
        raise TypeError('process owner cannot be serialized')
