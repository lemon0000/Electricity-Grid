"""Source-bound declared normal execution and solver-free record replay.

Preparation reconstructs mechanism inputs from pinned declarations and source
files. It does not authenticate empirical business parameters or coupling.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from time import perf_counter

from . import normal_task_inputs_stream as prepare
from . import scale_normal as kernel, scale_normal_budget as budgets, scale_normal_replay as replay

SCHEMA = 'draft_source_bound_scale_normal_v1'


@dataclass(frozen=True)
class ScaleNormalSourceRequest:
    source: prepare.legacy.NormalTaskSourceRequest
    expected_source_request_identity: str
    expected_assembly_identity: str
    expected_binding_identity: str
    expected_source_implementation_identity: str
    expected_binding_implementation_identity: str
    expected_normal_execution_identity: str
    specification: kernel.Rq2SolverSpec
    budget: budgets.ScaleNormalBudget
    resource_plan: budgets.NormalResourcePlan | budgets.SingleNormalResourcePlan


def request_identity(request):
    if type(request) is not ScaleNormalSourceRequest or type(request.source) is not prepare.legacy.NormalTaskSourceRequest:
        raise ValueError('typed source-bound scale normal request required')
    request.source.__post_init__()
    for name in ('expected_source_request_identity', 'expected_assembly_identity', 'expected_binding_identity',
                 'expected_source_implementation_identity', 'expected_binding_implementation_identity',
                 'expected_normal_execution_identity'):
        kernel._pin(getattr(request, name))
    kernel._validate(request.specification, request.budget, request.source.expected_scale)
    expected = budgets.budget_for_task(request.resource_plan, task_id=request.budget.normal.task_id,
        max_observed_wall_seconds=request.budget.max_observed_wall_seconds,
        max_process_peak_working_set_bytes=request.budget.max_process_peak_working_set_bytes,
        max_core_evidence_payload_bytes=request.budget.max_core_evidence_payload_bytes)
    if (expected != request.budget or request.budget.normal.input_identity != request.source.expected_input_identity
            or prepare.task_source_identity(request.source) != request.expected_source_request_identity
            or prepare.source_normal.implementation_identity() != request.expected_source_implementation_identity
            or prepare.stream_binding.implementation_identity() != request.expected_binding_implementation_identity
            or kernel.normal_execution_identity(request.source.expected_input_identity, request.source.expected_scale,
                request.specification, request.budget) != request.expected_normal_execution_identity):
        raise ValueError('source-bound normal request lineage differs')
    return kernel._digest(SCHEMA, request, sha256(Path(__file__).read_bytes()).hexdigest(),
        replay.replay_identity(request.expected_normal_execution_identity, request.specification, request.budget))


def _prepare(request, identity):
    if request_identity(request) != identity:
        raise ValueError('source-bound normal request drift')
    prepared = prepare.prepare_task_inputs(request.source,
        expected_request_identity=request.expected_source_request_identity)
    if (type(prepared) is not prepare.PreparedStreamingNormalTaskInputs
            or prepared.request_identity != request.expected_source_request_identity
            or type(prepared.assembly) is not prepare.source_normal.StreamingSourceNormalAssembly
            or type(prepared.binding) is not prepare.stream_binding.StreamingPairBinding
            or prepared.assembly.assembly_identity != request.expected_assembly_identity
            or prepared.assembly.implementation_identity != request.expected_source_implementation_identity
            or prepared.assembly.normal_identity != request.source.expected_input_identity
            or prepared.assembly.legacy_content_assembly_identity != request.source.expected_assembly_identity
            or prepared.binding.binding_identity != request.expected_binding_identity
            or prepared.binding.implementation_identity != request.expected_binding_implementation_identity
            or prepared.binding.legacy_content_binding_identity != request.source.expected_binding_identity
            or prepared.binding.source_assembly_identity != request.expected_assembly_identity
            or prepared.binding.pair_identity != request.source.expected_pair_identity
            or prepared.binding.normal_identity != request.source.expected_input_identity
            or type(prepared.solver_calls) is not int or prepared.solver_calls != 0
            or prepared.mechanism_initial_state is not True
            or any(getattr(prepared, n) is not False for n in
                   ('observed_power_mapping', 'normal_assignment_verified', 'formal_result'))):
        raise ValueError('prepared normal source identity or mechanism role differs')
    budgets.bind_plan(request.resource_plan, request.budget, prepared.assembly.inputs)
    snapshot = dict(assembly_identity=prepared.assembly.assembly_identity,
        source_implementation_identity=prepared.assembly.implementation_identity,
        normal_identity=prepared.assembly.normal_identity, binding=asdict(prepared.binding),
        declaration=asdict(prepared.declaration), mechanism_initial_state=True, observed_power_mapping=False)
    if request_identity(request) != identity:
        raise ValueError('source-bound normal implementation changed during preparation')
    return prepared.assembly.inputs, snapshot


def _arguments(request):
    return dict(expected_input_identity=request.source.expected_input_identity,
        expected_execution_identity=request.expected_normal_execution_identity,
        expected_scale=request.source.expected_scale, specification=request.specification,
        budget=request.budget, resource_plan=request.resource_plan)


def _declarations(request):
    r = request.source
    return tuple(prepare._read_pinned(path, pin, size) for path, pin, size in (
        (r.normal_record_path, r.expected_normal_record_sha256, r.max_normal_record_bytes),
        (r.pair_declaration_path, r.expected_pair_declaration_sha256, r.max_pair_declaration_bytes),
        (r.config_path, r.expected_config_sha256, r.max_config_bytes)))


def _consistent_normal(result):
    raw, witness = result.normal, result.witness
    return (result.normal_accepted is True and result.status == 'accepted_normal' and result.errors == ()
        and type(result.solver_calls) is int and result.solver_calls == 1 and result.call_count_complete is True
        and type(raw) is kernel.native.GridSolveEvidence and raw.calls == 1
        and raw.optimal is True and raw.assignment_valid is True and raw.errors == ()
        and type(witness) is kernel.NormalAssignmentWitness and witness.errors == ()
        and witness.input_identity == result.input_identity and witness.terminal_carry is not None
        and witness.assignment_identity == kernel._digest(dict(raw.loaded_values))
        and all(getattr(result, n) is False for n in ('hard_resource_limits_enforced','durable_invocation_tracking',
            'public_source_binding_verified','formal_result','security_certified'))
        and result.causal_certificate is None and result.infeasibility_certificate is None)


def run_source(request, *, expected_request_identity, before_kernel=None):
    """At most one kernel call; caller owns durable intent and process limits."""
    if before_kernel is not None and not callable(before_kernel):
        raise TypeError('callable pre-kernel runtime check required')
    kernel._pin(expected_request_identity)
    started = perf_counter()
    owned = deepcopy(request)
    inputs, before = _prepare(owned, expected_request_identity)
    declarations = _declarations(owned)
    if before_kernel is not None:
        before_kernel()
    if request_identity(owned) != expected_request_identity or _declarations(owned) != declarations:
        raise ValueError('source declarations or implementation changed before kernel')
    normal, errors, interrupted = None, [], False
    try:
        returned = kernel.run_normal_only(inputs, **_arguments(owned))
        if type(returned) is not kernel.ScaleNormalExecutionResult:
            raise ValueError('owned scale normal return required')
        normal = returned
        if (normal.input_identity != owned.source.expected_input_identity
                or normal.execution_identity != owned.expected_normal_execution_identity
                or normal.specification != owned.specification or normal.budget != owned.budget
                or normal.scale != owned.source.expected_scale or normal.contract != kernel.CONTRACT):
            errors.append('normal_return_binding_mismatch')
        if normal.normal_accepted is not False and not _consistent_normal(normal):
            errors.append('normal_return_acceptance_inconsistent')
    except BaseException as error:
        interrupted = not isinstance(error, Exception)
        errors.append('normal_return_missing:'+type(error).__name__+':'+str(error))
    after = None
    try:
        _, after = _prepare(owned, expected_request_identity)
        if after != before:
            errors.append('source_binding_changed')
    except BaseException as error:
        interrupted = interrupted or not isinstance(error, Exception)
        errors.append('post_source:'+type(error).__name__+':'+str(error))
    correspondence = after is not None and before == after
    accepted = bool(correspondence and not errors and normal is not None and normal.normal_accepted is True)
    return dict(schema=SCHEMA, request_identity=expected_request_identity, source_before=before, source_after=after,
        normal_record=None if normal is None else json.loads(replay.export_record(normal)),
        solver_calls=None if normal is None else normal.solver_calls,
        call_count_complete=normal is not None and normal.call_count_complete,
        source_correspondence_verified=correspondence, accepted=accepted,
        status='accepted_source_bound_normal' if accepted else ('interrupted_source_bound_normal'
            if interrupted or normal is not None and normal.status == 'interrupted_normal'
            else 'unresolved_source_bound_normal'), errors=errors, observed_wall_seconds=perf_counter()-started,
        mechanism_initial_state=True, observed_power_mapping=False, registered_coupling=False,
        hard_resource_limits_enforced=False, durable_invocation_tracking=False, formal_result=False, security_certified=False)


def audit_source(data, request, *, expected_sha256, expected_request_identity, max_record_bytes):
    kernel._pin(expected_sha256)
    kernel._pin(expected_request_identity)
    if type(max_record_bytes) is not int or not 0 < max_record_bytes <= 64*1024**2:
        raise ValueError('explicit bounded source record size required')
    if type(data) is not bytes or len(data) > max_record_bytes or sha256(data).hexdigest() != expected_sha256:
        raise ValueError('source normal record size/hash mismatch')
    owned = deepcopy(request)
    inputs, snapshot = _prepare(owned, expected_request_identity)
    record = json.loads(data)
    keys = {'schema','request_identity','source_before','source_after','normal_record','solver_calls',
        'call_count_complete','source_correspondence_verified','accepted','status','errors','observed_wall_seconds',
        'mechanism_initial_state','observed_power_mapping','registered_coupling','hard_resource_limits_enforced',
        'durable_invocation_tracking','formal_result','security_certified'}
    if type(record) is not dict or set(record) != keys or replay._bytes(record) != data:
        raise ValueError('canonical exact source normal record required')
    if (record['schema'] != SCHEMA or record['request_identity'] != expected_request_identity
            or replay._bytes(record['source_before']) != replay._bytes(snapshot) or record['mechanism_initial_state'] is not True
            or any(record[k] is not False for k in ('observed_power_mapping','registered_coupling',
                'hard_resource_limits_enforced','durable_invocation_tracking','formal_result','security_certified'))):
        raise ValueError('source normal record lineage or authority differs')
    elapsed = record['observed_wall_seconds']
    if type(elapsed) is not float or not isfinite(elapsed) or elapsed < 0:
        raise ValueError('finite source wrapper time required')
    errors = record['errors']
    if type(errors) is not list or any(type(e) is not str for e in errors):
        raise ValueError('source wrapper error strings required')
    replay.checks._error_inventory(tuple(errors), ('normal_return_binding_mismatch','normal_return_acceptance_inconsistent','source_binding_changed'),
                                  ('normal_return_missing','post_source'))
    numerical, inner = None, None
    if record['normal_record'] is not None:
        inner_data = replay._bytes(record['normal_record'])
        inner = replay.checks._fields(record['normal_record']['result'], kernel.ScaleNormalExecutionResult)
        numerical = replay.replay_record(inner_data, inputs, expected_sha256=sha256(inner_data).hexdigest(),
            expected_result_identity=record['normal_record']['result_identity'],
            expected_replay_identity=replay.replay_identity(owned.expected_normal_execution_identity,
                owned.specification, owned.budget), max_record_bytes=max_record_bytes, **_arguments(owned))
        timings = dict(replay.codec._decode(inner['timings']))
        if elapsed+1e-6 < timings['observed_total_seconds']:
            raise ValueError('source wrapper shorter than normal execution')
        if any(e.startswith('normal_return_missing:') for e in errors):
            raise ValueError('complete normal return conflicts with missing-return error')
    elif not any(e.startswith('normal_return_missing:') for e in errors):
        raise ValueError('unknown native invocation needs a missing-return error')
    correspondence = record['source_after'] is not None and replay._bytes(record['source_after']) == replay._bytes(snapshot)
    if record['source_after'] is not None and not correspondence:
        raise ValueError('source-after record differs from independently rebuilt source')
    # A rebuilt, pinned inner record cannot justify a binding/acceptance error;
    # a missing return cannot justify an error about a returned object's fields.
    # Likewise an independently equal source snapshot cannot justify a change.
    if any(e in errors for e in ('normal_return_binding_mismatch',
                                 'normal_return_acceptance_inconsistent', 'source_binding_changed')):
        raise ValueError('source wrapper error not reproduced by pinned replay')
    if (record['source_after'] is None) != any(e.startswith('post_source:') for e in errors):
        raise ValueError('post-source phase record mismatch')
    calls = None if inner is None else inner['solver_calls']
    complete = inner is not None and inner['call_count_complete'] is True
    accepted = bool(correspondence and not errors and numerical is not None and numerical['accepted_record_reproduced'])
    if (record['source_correspondence_verified'] is not correspondence
            or record['call_count_complete'] is not complete or record['accepted'] is not accepted
            or (record['solver_calls'] is not None if calls is None else
                type(record['solver_calls']) is not int or record['solver_calls'] != calls)
            or (record['status'] != 'accepted_source_bound_normal' if accepted else
                record['status'] not in ('unresolved_source_bound_normal','interrupted_source_bound_normal'))):
        raise ValueError('source wrapper acceptance/call projection differs')
    _, after = _prepare(owned, expected_request_identity)
    if after != snapshot:
        raise ValueError('source changed during independent replay')
    return dict(schema=SCHEMA, record_consistent=numerical is None or numerical['record_consistent'],
        accepted_record_reproduced=accepted, numerical=numerical, solver_calls_by_replay=0,
        source_correspondence_rechecked=True, mechanism_initial_state=True, observed_power_mapping=False,
        registered_coupling=False, native_execution_authenticated=False, resource_measurements_authenticated=False,
        executable_resume_available=False, formal_result=False, security_certified=False)
