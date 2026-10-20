"""One numerical normal invocation bound to sources and an issued plan.

Durable intent and OS supervision belong to the worker/controller. An exception
from the owned collector leaves the invocation count unknown; it never retries.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from time import perf_counter

from . import normal_numerical_source as projection

legacy = projection.source
prepare, kernel, budgets, replay = legacy.prepare, legacy.kernel, legacy.budgets, legacy.replay
SCHEMA = 'draft_source_bound_numerical_normal_execution_v1'


@dataclass(frozen=True)
class NumericalNormalRequest:
    normal: legacy.ScaleNormalSourceRequest
    declaration: projection.information.PlanInformationDeclaration
    numerical_byte_limit: int

    @property
    def source(self): return self.normal.source

    @property
    def budget(self): return self.normal.budget

    @property
    def resource_plan(self): return self.normal.resource_plan


def implementation_identity():
    return kernel._digest(SCHEMA, projection.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest())


def request_identity(request):
    if type(request) is not NumericalNormalRequest:
        raise ValueError('typed numerical normal request required')
    normal_pin = legacy.request_identity(request.normal)
    projection.capture.provenance.adapter.validate_spec(request.normal.specification)
    if type(request.declaration) is not projection.information.PlanInformationDeclaration:
        raise ValueError('explicit typed information declaration required')
    request.declaration.__post_init__()
    if (type(request.numerical_byte_limit) is not int
            or not 0 < request.numerical_byte_limit <= min(projection.LIMIT,
                request.budget.max_core_evidence_payload_bytes)):
        raise ValueError('numerical payload exceeds declared allocation')
    return kernel._digest(SCHEMA, normal_pin, request.declaration,
        request.numerical_byte_limit, implementation_identity())


def execution_targets():
    import sys
    return ((sys.modules[__name__], 'run_source'),
        (projection.capture, 'solve_once'), (projection.capture.provenance.adapter, 'create_solver'),
        (legacy, 'run_source'), (kernel, 'run_normal_only'),
        (kernel.native, '_solve'), (kernel.native, 'create_solver'))


@contextmanager
def solver_free():
    originals = [(obj, name, getattr(obj, name)) for obj, name in execution_targets()]
    def forbidden(*a, **k): raise RuntimeError('numerical normal audit execution forbidden')
    try:
        for obj, name, _ in originals: setattr(obj, name, forbidden)
        yield
    finally:
        for obj, name, original in originals: setattr(obj, name, original)


def _project(request, numerical):
    raw = projection.capture.encode(numerical)
    args = dict(expected_record_sha256=sha256(raw).hexdigest(),
        max_record_bytes=request.numerical_byte_limit)
    args['expected_binding_identity'] = projection.binding_identity(request.normal, request.declaration, **args)
    return projection.prepare_information(raw, request.normal, request.declaration, **args)


def _snapshot(request, expected):
    if request_identity(request) != expected:
        raise ValueError('numerical normal request drift')
    inputs, snapshot = legacy._prepare(request.normal, legacy.request_identity(request.normal))
    if request.declaration.issued_at_source_hour > inputs.carry.source_hour:
        raise ValueError('normal declaration follows incoming boundary')
    return inputs, snapshot


def _record(request, identity, before, numerical, projected, prepared, error, elapsed):
    complete = numerical is not None
    if complete:
        if projected['numerical_plan_accepted'] is not (prepared is not None):
            raise ValueError('projection acceptance differs from complete plan')
        if prepared is not None and (
                type(prepared) is not projection.information.PreparedNormalInformation
                or prepared.audit_identity != projected['prepared_information_identity']
                or prepared.allowed_plan_identity != projected['allowed_plan_identity']):
            raise ValueError('prepared plan differs from projection identities')
    elif projected is not None or prepared is not None:
        raise ValueError('unknown invocation cannot publish a plan')
    accepted = complete and projected['numerical_plan_accepted']
    return dict(schema=SCHEMA, request_identity=identity, source_before=before, source_after=before,
        numerical=numerical, projection=projected, prepared_information=kernel._encode(prepared),
        solver_calls=1 if complete else None,
        call_count_complete=complete, source_correspondence_verified=True, accepted=bool(accepted),
        status=('accepted_numerical_source_normal' if accepted else
            'unresolved_numerical_source_normal' if complete else 'numerical_invocation_unknown'),
        invocation_error=error, observed_wall_seconds=elapsed, mechanism_initial_state=True,
        observed_power_mapping=False, registered_coupling=False, native_execution_authenticated=False,
        whole_task_resources_verified=False, rigorous_exact_optimality_certified=False,
        security_certified=False, formal_result=False, executable_resume_available=False)


def run_source(request, *, expected_request_identity, before_kernel=None):
    started = perf_counter()
    request = deepcopy(request)
    inputs, before = _snapshot(request, expected_request_identity)
    declarations = legacy._declarations(request.normal)
    def builder():
        return projection.acceptance.stream.build_continuous_normal_model(inputs,
            expected_identity=request.source.expected_input_identity,
            expected_implementation_identity=projection.acceptance.stream.implementation_identity())
    model = builder()
    structure = projection.capture.audit._structure(model)
    del model
    if before_kernel is not None: before_kernel()
    if (request_identity(request) != expected_request_identity
            or declarations != legacy._declarations(request.normal)):
        raise ValueError('normal request or declarations changed before invocation')
    numerical = projected = prepared = error = None
    try:
        raw = projection.capture.solve_once(builder, request.normal.specification,
            expected_structure=structure, max_variables=request.source.expected_scale.variables,
            max_constraints=request.source.expected_scale.constraints,
            max_payload_bytes=request.numerical_byte_limit,
            expected_implementation=projection.capture.implementation_identity())
    except Exception as exc:
        error = type(exc).__name__
    else:
        numerical = json.loads(raw)
        if projection.capture.encode(numerical) != raw:
            raise ValueError('collector returned noncanonical record')
        with solver_free(): projected, prepared = _project(request, numerical)
    _, after = _snapshot(request, expected_request_identity)
    if before != after or declarations != legacy._declarations(request.normal):
        raise ValueError('normal source changed during invocation')
    elapsed = float(perf_counter()-started)
    if elapsed > request.budget.max_observed_wall_seconds:
        raise TimeoutError('normal invocation exceeded allocated wall time')
    return _record(request, expected_request_identity, before, numerical, projected, prepared, error, elapsed)


def replay_information(data, request, *, expected_sha256, expected_request_identity, max_record_bytes):
    """Reproduce the archive and return (audit report, typed plan or None)."""
    request = deepcopy(request)
    kernel._pin(expected_sha256)
    if (type(max_record_bytes) is not int or not 0 < max_record_bytes <= 64*1024**2
            or type(data) is not bytes or len(data) > max_record_bytes
            or sha256(data).hexdigest() != expected_sha256):
        raise ValueError('bounded externally pinned normal archive required')
    _, before = _snapshot(request, expected_request_identity)
    declarations = legacy._declarations(request.normal)
    record = json.loads(data)
    if type(record) is not dict or replay._bytes(record) != data:
        raise ValueError('canonical numerical normal archive required')
    numerical = record.get('numerical')
    error, elapsed = record.get('invocation_error'), record.get('observed_wall_seconds')
    if type(elapsed) is not float or not isfinite(elapsed) or not 0 <= elapsed <= request.budget.max_observed_wall_seconds:
        raise ValueError('normal observed wall time outside allocation')
    projected = prepared = None
    if numerical is None:
        if type(error) is not str or not error.isidentifier() or len(error) > 128:
            raise ValueError('unknown invocation requires bounded exception class')
    else:
        if error is not None: raise ValueError('returned numerical record conflicts with invocation error')
        with solver_free(): projected, prepared = _project(request, numerical)
    expected = _record(request, expected_request_identity, before, numerical, projected, prepared, error, elapsed)
    if replay._bytes(expected) != data:
        raise ValueError('normal archive differs from independently replayed projection')
    _, after = _snapshot(request, expected_request_identity)
    if after != before or declarations != legacy._declarations(request.normal):
        raise ValueError('normal source changed during archive audit')
    report = dict(schema=SCHEMA, record_consistent=True, accepted_record_reproduced=expected['accepted'],
        prepared_information=expected['prepared_information'],
        numerical=projected, solver_calls_by_replay=0, source_correspondence_rechecked=True,
        mechanism_initial_state=True, observed_power_mapping=False, registered_coupling=False,
        native_execution_authenticated=False, resource_measurements_authenticated=False,
        executable_resume_available=False, formal_result=False, security_certified=False)
    return report, prepared


def audit_source(data, request, *, expected_sha256, expected_request_identity, max_record_bytes):
    return replay_information(data, request, expected_sha256=expected_sha256,
        expected_request_identity=expected_request_identity, max_record_bytes=max_record_bytes)[0]
