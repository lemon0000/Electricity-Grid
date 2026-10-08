"""Streaming normal development kernel; synchronous resource checks only.

This owns numerical evidence, not a durable invocation or process supervisor.
Whole-process peak memory includes earlier work in this Python process.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sys
from time import perf_counter

from ..solvers.rq2_solver_adapter import Rq2ModelScale, Rq2SolverSpec, model_scale, solver_spec
from . import continuous_grid_candidate as native
from . import normal_execution as legacy, continuous_grid_normal_stream_numeric as streaming
from .continuous_grid_normal import ContinuousNormalInputs, NormalAssignmentWitness, _encode
from .identity_stream_numeric import normal_input_identity, digest as _digest


CONTRACT = 'draft_numeric_streaming_single_normal_synchronous_resource_checks_v1'


NormalExecutionBudget = legacy.NormalExecutionBudget

class _Owned:
    def __init__(self, *args, **kwargs):
        raise TypeError('normal execution result requires owned execution')


@dataclass(frozen=True, init=False)
class NumericStreamingNormalExecutionResult(_Owned):
    contract: str
    input_identity: str
    execution_identity: str
    specification: Rq2SolverSpec
    budget: NormalExecutionBudget
    scale: Rq2ModelScale
    normal: native.GridSolveEvidence | None
    witness: NormalAssignmentWitness | None
    solver_calls: int | None
    call_count_complete: bool
    normal_accepted: bool
    status: str
    errors: tuple[str, ...]
    timings: tuple
    process_peak_working_set_bytes: tuple[int | None, int | None]
    core_evidence_payload_bytes: int
    hard_resource_limits_enforced: bool
    durable_invocation_tracking: bool
    public_source_binding_verified: bool
    formal_result: bool
    security_certified: bool
    causal_certificate: None
    infeasibility_certificate: None

    @property
    def identity(self):
        return _digest(self)


def _pin(x):
    if type(x) is not str or len(x) != 64 or any(c not in '0123456789abcdef' for c in x):
        raise ValueError('external lowercase SHA256 pin required')


def _validate(spec, budget, scale):
    if CONTRACT != 'draft_numeric_streaming_single_normal_synchronous_resource_checks_v1':
        raise ValueError('normal execution contract drift')
    if type(budget) is not NormalExecutionBudget or type(spec) is not Rq2SolverSpec:
        raise ValueError('typed independent normal budget and solver required')
    budget.__post_init__()
    if spec != solver_spec(asdict(spec)):
        raise ValueError('canonical solver specification required')
    if (spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_seconds_per_solve
            or spec.threads > budget.max_threads or any(getattr(spec, n) > 1e-6 for n in
            ('feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance'))):
        raise ValueError('solver exceeds normal development applicability')
    if (type(scale) is not Rq2ModelScale or any(type(x) is not int or x <= 0
            for x in (scale.variables, scale.constraints))
            or scale.variables > budget.max_variables or scale.constraints > budget.max_constraints):
        raise ValueError('externally declared scale exceeds normal budget')


def normal_execution_identity(input_identity, expected_scale, specification, budget):
    """Derive a candidate pin for independent retention before execution."""
    _pin(input_identity)
    _validate(specification, budget, expected_scale)
    return _digest(CONTRACT, input_identity, expected_scale,
        sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(legacy.__file__).read_bytes()).hexdigest(), streaming.implementation_identity(),
        native._execution_identity(specification, budget))


def _peak_working_set_bytes():
    """Windows lifetime process peak, not an isolated invocation measurement."""
    if sys.platform != 'win32':
        raise ValueError('Windows peak working set measurement required')
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
            *((n, ctypes.c_size_t) for n in ('PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage'))]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    api = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    api.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    api.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError(ctypes.get_last_error(), 'GetProcessMemoryInfo failed')
    return int(counters.PeakWorkingSetSize)


def run_normal_only(inputs, *, expected_input_identity, expected_execution_identity,
                    expected_scale, specification, budget):
    """One native call at most; no retry, publication, recovery or event input.

    Pre-call rejection raises. Once the solve pipeline is entered, missing raw
    evidence is unknown invocation count, including interruption during build.
    Post-return resource gates reject acceptance; they cannot kill a native call.
    """
    start = perf_counter()
    _pin(expected_input_identity)
    _pin(expected_execution_identity)
    model_implementation = streaming.implementation_identity()
    _validate(specification, budget, expected_scale)
    if type(inputs) is not ContinuousNormalInputs:
        raise ValueError('typed complete normal inputs required')
    owned = deepcopy(inputs)
    if len(owned.source_hours) > budget.max_horizon:
        raise ValueError('normal horizon exceeds budget')

    def check():
        if normal_input_identity(owned) != expected_input_identity:
            raise ValueError('normal input identity drift')
        if normal_execution_identity(expected_input_identity, expected_scale, specification, budget) != expected_execution_identity:
            raise ValueError('normal execution identity drift')

    def resources():
        peak = _peak_working_set_bytes()
        if type(peak) is not int or peak <= 0:
            raise ValueError('invalid process peak working set measurement')
        if peak > budget.max_process_peak_working_set_bytes:
            raise ValueError('process lifetime peak working set exceeds budget')
        if perf_counter()-start > budget.max_observed_wall_seconds:
            raise ValueError('observed normal wall time exceeds budget')
        return peak

    check()
    peak_before = resources()
    builds = []
    def builder():
        check()
        resources()
        began = perf_counter()
        model = streaming.build_continuous_normal_model(owned, expected_identity=expected_input_identity,
            expected_implementation_identity=model_implementation)
        actual = model_scale(model)
        builds.append(perf_counter()-began)
        if actual != expected_scale:
            raise ValueError('actual canonical model differs from external scale')
        check()
        resources()
        return model

    # Release the admission model before allocating the solve model.
    admission = builder()
    del admission
    check()
    resources()
    preflight_seconds = perf_counter()-start
    raw = witness = None
    errors = []
    interrupted = False
    pipeline_start = perf_counter()
    audit_seconds = 0.
    try:
        raw = native._solve(builder, specification, budget, 'event_blind_normal')
        pipeline_seconds = perf_counter()-pipeline_start
        if raw.assignment_valid:
            audit_start = perf_counter()
            try:
                witness = streaming.audit_normal_assignment(owned, dict(raw.loaded_values), expected_identity=expected_input_identity,
                    expected_implementation_identity=model_implementation)
            finally:
                audit_seconds = perf_counter()-audit_start
    except BaseException as error:
        pipeline_seconds = perf_counter()-pipeline_start-audit_seconds
        interrupted = not isinstance(error, Exception)
        errors.append('normal_pipeline:'+type(error).__name__+':'+str(error))
    if raw is not None:
        errors.extend(raw.errors)
        if raw.calls not in (0, 1):
            errors.append('unexpected_native_call_count')
    if witness is not None:
        errors.extend(witness.errors)
    try:
        check()
    except Exception as error:
        errors.append('post_identity:'+type(error).__name__+':'+str(error))
    payload = (CONTRACT, expected_input_identity, expected_execution_identity,
        specification, budget, expected_scale, raw, witness)
    payload_bytes = len(json.dumps(_encode(payload), ensure_ascii=True, allow_nan=False).encode('utf-8'))
    if payload_bytes > budget.max_core_evidence_payload_bytes:
        errors.append('core_evidence_payload_exceeds_budget')
    peak_after = None
    try:
        # Retain the measurement even when the post-return gate fails.
        peak_after = _peak_working_set_bytes()
        if type(peak_after) is not int or peak_after <= 0:
            peak_after = None
            raise ValueError('invalid process peak working set measurement')
        if peak_after > budget.max_process_peak_working_set_bytes:
            errors.append('process_lifetime_peak_exceeds_budget')
    except Exception as error:
        errors.append('post_memory:'+type(error).__name__+':'+str(error))
    elapsed = perf_counter()-start
    if elapsed > budget.max_observed_wall_seconds:
        errors.append('observed_wall_time_exceeds_budget')
    accepted = (not errors and raw is not None and raw.calls == 1 and raw.optimal
        and witness is not None and not witness.errors and witness.terminal_carry is not None)
    return native._make(NumericStreamingNormalExecutionResult, contract=CONTRACT,
        input_identity=expected_input_identity, execution_identity=expected_execution_identity,
        specification=specification, budget=budget, scale=expected_scale, normal=raw, witness=witness,
        solver_calls=None if raw is None else raw.calls, call_count_complete=raw is not None,
        normal_accepted=accepted, status='accepted_normal' if accepted else (
            'interrupted_normal' if interrupted else 'unresolved_normal'), errors=tuple(errors),
        timings=(('preflight_seconds', preflight_seconds), ('solve_load_canonical_pipeline_seconds', pipeline_seconds),
            ('normal_witness_audit_seconds', audit_seconds), ('builder_seconds_nested', tuple(builds)),
            ('observed_total_seconds', elapsed)),
        process_peak_working_set_bytes=(peak_before, peak_after), core_evidence_payload_bytes=payload_bytes,
        hard_resource_limits_enforced=False, durable_invocation_tracking=False,
        public_source_binding_verified=False, formal_result=False, security_certified=False,
        causal_certificate=None, infeasibility_certificate=None)
