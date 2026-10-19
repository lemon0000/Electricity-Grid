"""Owned task child with polled deadlines and host reserve observations.

Reuses the old atomic Job/HANDLE primitive without extending its short wait API.
This is not a task runner, a durable phase log, or a numerical verifier.
"""
from copy import deepcopy
from contextlib import contextmanager
import ctypes as c
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time

from . import normal_process as process, normal_resources as resources


SCHEMA = 'draft_normal_task_polled_process_v1'


@dataclass(frozen=True)
class TaskProcessBudget:
    max_elapsed_seconds: float
    sample_interval_seconds: float
    max_process_commit_bytes: int
    max_job_commit_bytes: int
    max_quiescence_seconds: float

    def __post_init__(self):
        for name in ('max_elapsed_seconds', 'sample_interval_seconds', 'max_quiescence_seconds'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('finite positive task timing budget required')
        if (self.max_elapsed_seconds > 3600 or self.sample_interval_seconds > 1
                or self.max_quiescence_seconds > 5):
            raise ValueError('task elapsed/sample/quiescence interval exceeds development ceiling')
        for name in ('max_process_commit_bytes', 'max_job_commit_bytes'):
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= process.SIZE_T(-1).value:
                raise ValueError('explicit task commit byte budget required')
        if self.max_process_commit_bytes > self.max_job_commit_bytes:
            raise ValueError('task Job limit must cover process limit')


def task_process_identity(argv, *, cwd, environment, budget, host_budget, expected_host_identity):
    if type(budget) is not TaskProcessBudget:
        raise ValueError('typed task process budget required')
    budget.__post_init__()
    if type(environment) is not dict:
        raise ValueError('explicit task environment required')
    process._environment_block(environment)
    directory = resources.local._path(cwd)
    if (not directory.is_dir() or any(type(environment.get(name)) is not str
            or os.path.normcase(environment[name]) != os.path.normcase(str(directory)) for name in ('TEMP', 'TMP'))):
        raise ValueError('task cwd/TEMP/TMP must share an explicit existing scratch directory')
    if resources.resource_identity(host_budget) != expected_host_identity:
        raise ValueError('external host resource identity mismatch')
    if (host_budget.additional_commit_bytes < budget.max_job_commit_bytes
            or not any(os.path.normcase(str(resources.local._path(item.directory))) == os.path.normcase(str(directory))
                       for item in host_budget.directories)):
        raise ValueError('host demand must cover task Job and scratch')
    if (type(argv) not in (tuple, list) or not argv
            or any(type(x) is not str or not x or '\0' in x for x in argv)
            or not Path(argv[0]).is_absolute() or not Path(argv[0]).is_file()):
        raise ValueError('explicit task command and executable required')
    payload = (SCHEMA, list(argv), str(directory), environment, asdict(budget), expected_host_identity,
        sha256(Path(argv[0]).read_bytes()).hexdigest(),
        tuple((str(Path(module.__file__).resolve()), sha256(Path(module.__file__).read_bytes()).hexdigest())
              for module in (process, resources, resources.local)), sha256(Path(__file__).read_bytes()).hexdigest())
    return sha256(json.dumps(payload, ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class TaskProcessObservation:
    process_identity: str
    pid: int
    creation_filetime: int
    exit_code: int
    reason: str
    elapsed_seconds: float
    runtime_samples: int
    minimum_runtime_commit_available_bytes: int | None
    minimum_runtime_disk_available_bytes: tuple[tuple[str, int], ...]
    last_resource_errors: tuple[str, ...]
    observation_error_type: str | None
    stop_markers: tuple[str, ...]
    job_peak_process_commit_bytes: int
    job_peak_total_commit_bytes: int
    whole_job_quiescent: bool
    job_commit_limits_configured: bool = True
    hard_disk_quota_enforced: bool = False
    whole_task_resources_verified: bool = False
    numerical_evidence_verified: bool = False
    formal_result: bool = False


def _reserve_errors(observation, budget):
    reasons = []
    if observation.commit.available_bytes < budget.commit_reserve_bytes:
        reasons.append('system_commit_reserve_breached')
    for volume, _demand, reserve, free in observation.volume_requirements:
        if free < reserve:
            reasons.append('caller_disk_reserve_breached:'+volume)
    return tuple(reasons)


class NormalTaskChild:
    """Single creating-thread owner; enter a context and release/wait at most once.

The controller must persist its phase intent and launch identity before release.
    Result-artifact reads belong after wait returns with whole_job_quiescent=True.
"""
    def __init__(self, *args, **kwargs):
        raise TypeError('use normal_task_child context manager')

    def _initialize(self, argv, *, cwd, environment, budget, host_budget, expected_host_identity,
                 expected_process_identity):
        self._child = None
        self._started = time.monotonic()
        self._argv, self._environment, self._budget, self._host_budget = deepcopy((
            argv, environment, budget, host_budget))
        self._cwd = str(resources.local._path(cwd))
        self._host_identity, self._identity = expected_host_identity, expected_process_identity
        self._released = self._waited = False
        self._identity_check()
        self.initial_observation = resources.observe_headroom(self._host_budget,
            expected_request_identity=self._host_identity)
        if not self.initial_observation.observed_headroom_sufficient:
            raise ValueError('insufficient initial task headroom')
        if self._expired():
            raise TimeoutError('task deadline reached before child creation')
        try:
            # Retain the owner before its constructor can acquire handles. An
            # interrupt after native creation but before a normal RHS assignment
            # would otherwise leave those handles unreachable by this wrapper.
            self._child = object.__new__(process.DevelopmentNormalChild)
            process.DevelopmentNormalChild.__init__(self._child, self._argv, cwd=self._cwd,
                environment=self._environment, max_process_commit_bytes=self._budget.max_process_commit_bytes,
                max_job_commit_bytes=self._budget.max_job_commit_bytes)
            self.pid, self.creation_filetime = self._child.pid, self._child.creation_filetime
        except BaseException:
            self.close()
            raise

    def _identity_check(self):
        if task_process_identity(self._argv, cwd=self._cwd, environment=self._environment, budget=self._budget,
                host_budget=self._host_budget, expected_host_identity=self._host_identity) != self._identity:
            raise ValueError('task process implementation/request drift')

    def _expired(self):
        return time.monotonic()-self._started >= self._budget.max_elapsed_seconds

    def _live(self):
        if self._child is None:
            raise RuntimeError('open task owner required')
        self._child._live_owner()

    def release(self):
        self._live()
        if self._released:
            raise RuntimeError('task child already released')
        try:
            self._identity_check()
            # Creation has already allocated some task memory. From here on,
            # allocated bytes must not be counted again as future demand.
            observed = resources.observe_headroom(self._host_budget, expected_request_identity=self._host_identity)
            if _reserve_errors(observed, self._host_budget):
                raise ValueError('task resource reserve breached before release')
            if self._expired():
                raise TimeoutError('task deadline reached before release')
            self._child.release()
            self._released = True
        except BaseException:
            self.close()
            raise

    def wait(self):
        self._live()
        if not self._released or self._waited:
            raise RuntimeError('single wait requires a released task child')
        self._waited = True
        child = self._child
        samples, minimum_commit, minimum_disks = 0, None, {}
        errors, error_type = (), None
        markers = ()
        reason = None
        try:
            while reason is None:
                if self._expired():
                    reason = 'task_deadline_stop'
                    markers = (reason,)
                    break
                state = child._k.WaitForSingleObject(child._process, 0)
                if state not in (0, 258):
                    raise OSError('task process wait state unavailable')
                try:
                    self._identity_check()
                    observation = resources.observe_headroom(self._host_budget,
                        expected_request_identity=self._host_identity)
                    samples += 1
                    available = observation.commit.available_bytes
                    minimum_commit = available if minimum_commit is None else min(minimum_commit, available)
                    for volume, _demand, reserve, free in observation.volume_requirements:
                        minimum_disks[volume] = min(minimum_disks.get(volume, free), free)
                    errors = _reserve_errors(observation, self._host_budget)
                except Exception as error:
                    error_type = type(error).__name__[:128]
                    reason = 'resource_observation_failed'
                markers = errors + (('resource_observation_failed',) if error_type else ())
                if state == 0:
                    markers += ('direct_child_exit_observed',)
                # A completed observation can cross the deadline. Deadline has
                # precedence; resource errors remain recorded as diagnostics.
                if self._expired():
                    reason = 'task_deadline_stop'
                    markers += (reason,)
                elif reason is None and errors:
                    reason = 'host_resource_reserve_stop'
                elif reason is None and state == 0:
                    reason = 'child_exited'
                if reason is not None:
                    break
                remaining = self._budget.max_elapsed_seconds-(time.monotonic()-self._started)
                milliseconds = math.ceil(max(0., min(self._budget.sample_interval_seconds, remaining))*1000)
                state = child._k.WaitForSingleObject(child._process, milliseconds)
                if state not in (0, 258):
                    raise OSError('task process polling failed')
            # Terminate all remaining descendants and confirm inactivity even
            # after a natural direct-child exit, before any upper-layer reads.
            quiet_deadline = time.monotonic()+self._budget.max_quiescence_seconds
            child.quiesce(max_seconds=self._budget.max_quiescence_seconds)
            remaining = max(0., quiet_deadline-time.monotonic())
            if child._k.WaitForSingleObject(child._process, math.ceil(remaining*1000)) != 0:
                raise OSError('task direct-child exit not confirmed')
            code, limits = process.DWORD(), process._Limits()
            process._check(child._k.GetExitCodeProcess(child._process, c.byref(code)))
            process._check(child._k.QueryInformationJobObject(child._job, 9, c.byref(limits), c.sizeof(limits), None))
            try:
                self._identity_check()
            except Exception as error:
                error_type = type(error).__name__[:128]
                markers += ('post_process_identity_failed',)
                if reason == 'child_exited':
                    reason = 'post_process_identity_failed'
            return TaskProcessObservation(self._identity, self.pid, self.creation_filetime, code.value, reason,
                time.monotonic()-self._started, samples, minimum_commit, tuple(sorted(minimum_disks.items())),
                errors, error_type, markers, limits.peak_process, limits.peak_job, True)
        except BaseException:
            self.close()
            raise

    def close(self):
        if getattr(self, '_child', None) is not None:
            # In the pinned base constructor _owner precedes all native handle
            # acquisition. Earlier validation failures therefore own no handles.
            if hasattr(self._child, '_owner'):
                self._child.close()
            self._child = None

    def __enter__(self):
        self._live()
        return self

    def __exit__(self, *_):
        self.close()

    def __copy__(self):
        raise TypeError('task owner cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('task owner cannot be copied')

    def __reduce__(self):
        raise TypeError('task owner cannot be serialized')


@contextmanager
def normal_task_child(argv, *, cwd, environment, budget, host_budget, expected_host_identity,
                      expected_process_identity):
    """Acquire only on context entry, with cleanup covering initialization too."""
    owner = object.__new__(NormalTaskChild)
    try:
        owner._initialize(argv, cwd=cwd, environment=environment, budget=budget,
            host_budget=host_budget, expected_host_identity=expected_host_identity,
            expected_process_identity=expected_process_identity)
        yield owner
    finally:
        owner.close()
