"""Independent solver-free consistency check of declared normal numerical records.

This does not authenticate source files, historical resource measurements or
native execution, and never returns an executable normal/carry object.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from . import scale_normal as kernel, grid_evidence_replay as native
from . import normal_declared_replay_gurobi_ordered as checks, normal_worker as codec

SCHEMA = 'draft_declared_scale_normal_record_v1'


def _bytes(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False).encode('utf-8')


def export_record(result):
    if type(result) is not kernel.ScaleNormalExecutionResult:
        raise ValueError('owned declared scale normal result required')
    return _bytes(dict(schema=SCHEMA, result_identity=result.identity, result=kernel._encode(result)))


def replay_identity(expected_execution_identity, specification, budget):
    kernel._pin(expected_execution_identity)
    return kernel._digest(SCHEMA, expected_execution_identity, native._identity(specification, budget),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (checks, codec)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def replay_record(data, inputs, *, expected_sha256, expected_result_identity, expected_replay_identity,
                  expected_input_identity, expected_execution_identity, expected_scale, specification,
                  budget, resource_plan, max_record_bytes):
    for pin in (expected_sha256, expected_result_identity, expected_replay_identity,
                expected_input_identity, expected_execution_identity):
        kernel._pin(pin)
    if type(max_record_bytes) is not int or not 0 < max_record_bytes <= 64*1024**2:
        raise ValueError('explicit bounded normal replay size required')
    if type(data) is not bytes or len(data) > max_record_bytes or sha256(data).hexdigest() != expected_sha256:
        raise ValueError('normal record bytes/hash mismatch')
    owned, plan = deepcopy(inputs), deepcopy(resource_plan)
    kernel._validate(specification, budget, expected_scale)

    def check():
        kernel.bind_plan(plan, budget, owned)
        if (kernel.normal_input_identity(owned) != expected_input_identity
                or kernel.normal_execution_identity(expected_input_identity, expected_scale, specification, budget)
                   != expected_execution_identity
                or replay_identity(expected_execution_identity, specification, budget) != expected_replay_identity):
            raise ValueError('normal replay input/execution/implementation drift')

    check()
    record = json.loads(data)
    if (_bytes(record) != data or type(record) is not dict
            or set(record) != {'schema', 'result_identity', 'result'} or record['schema'] != SCHEMA):
        raise ValueError('canonical exact normal record required')
    wire = record['result']
    if (record['result_identity'] != expected_result_identity
            or sha256(_bytes(['tuple', [wire]])).hexdigest() != expected_result_identity):
        raise ValueError('normal result identity mismatch')
    saved = checks._fields(wire, kernel.ScaleNormalExecutionResult)
    pinned = dict(contract=kernel.CONTRACT, input_identity=expected_input_identity,
        execution_identity=expected_execution_identity, specification=specification, budget=budget,
        scale=expected_scale, hard_resource_limits_enforced=False, durable_invocation_tracking=False,
        public_source_binding_verified=False, formal_result=False, security_certified=False,
        causal_certificate=None, infeasibility_certificate=None)
    if any(saved[k] != kernel._encode(v) for k, v in pinned.items()):
        raise ValueError('normal record differs from independently pinned inputs')
    inner = {k: codec._decode(v) for k, v in saved.items() if k not in pinned and k not in ('normal', 'witness')}
    checks._errors(inner['errors'])
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    raw, diagnostic, witness = None, None, None
    if saved['normal'] is not None:
        raw = {k: codec._decode(v) for k, v in checks._fields(saved['normal'], kernel.native.GridSolveEvidence).items()}
        def builder():
            check()
            model = kernel.streaming.build_continuous_normal_model(owned, expected_identity=expected_input_identity,
                expected_implementation_identity=kernel.streaming.implementation_identity())
            if kernel.model_scale(model) != expected_scale:
                raise ValueError('replayed normal model scale differs')
            return model
        diagnostic = native._replay(raw, builder, specification, budget, 'event_blind_normal')
        require(diagnostic['replay_consistent'], 'native_record_not_reproduced')
        require(all(x in inner['errors'] for x in raw['errors']), 'missing_native_errors')
        if raw['assignment_valid']:
            witness = kernel.streaming.audit_normal_assignment(owned, dict(raw['loaded_values']),
                expected_identity=expected_input_identity,
                expected_implementation_identity=kernel.streaming.implementation_identity())
    witness_reproduced = witness is not None and kernel._encode(witness) == saved['witness']
    if saved['witness'] is not None:
        require(witness_reproduced, 'witness_not_reproduced')
        if witness is not None:
            require(all(x in inner['errors'] for x in witness.errors), 'missing_witness_errors')
    elif witness is not None:
        require(any(x.startswith('normal_pipeline:') for x in inner['errors']), 'missing_witness_without_error')
    inherited_errors = (() if raw is None else raw['errors']) + (() if witness is None else witness.errors)
    remaining_errors = list(inner['errors'])
    for error in inherited_errors:
        if error in remaining_errors:
            remaining_errors.remove(error)
        else:
            require(False, 'missing_inherited_error_occurrence')
    checks._error_inventory(tuple(remaining_errors),
        ('unexpected_native_call_count', 'core_evidence_payload_exceeds_budget',
         'process_lifetime_peak_exceeds_budget', 'observed_wall_time_exceeds_budget'),
        ('normal_pipeline', 'post_identity', 'post_memory'))
    require(raw is not None or any(x.startswith('normal_pipeline:') for x in inner['errors']),
            'missing_native_record_without_pipeline_error')
    require(inner['call_count_complete'] is (raw is not None), 'call_completeness_mismatch')
    require(inner['solver_calls'] is None if raw is None else
            type(inner['solver_calls']) is int and inner['solver_calls'] == raw['calls'], 'call_count_mismatch')
    names = ('preflight_seconds', 'solve_load_canonical_pipeline_seconds', 'normal_witness_audit_seconds',
             'builder_seconds_nested', 'observed_total_seconds')
    timings = inner['timings']
    if (type(timings) is not tuple or any(type(x) is not tuple or len(x) != 2 for x in timings)
            or tuple(x[0] for x in timings) != names):
        raise ValueError('exact normal timing inventory required')
    times = dict(timings)
    if (any(not checks._finite_time(times[n]) for n in names if n != 'builder_seconds_nested')
            or type(times['builder_seconds_nested']) is not tuple
            or any(not checks._finite_time(x) for x in times['builder_seconds_nested'])):
        raise ValueError('finite normal timings required')
    builds = times['builder_seconds_nested']
    require(1 <= len(builds) <= 3 and (raw is None or len(builds) >= 2)
            and (raw is None or not raw['assignment_valid'] or len(builds) == 3), 'builder_inventory_mismatch')
    require(times['observed_total_seconds']+1e-6 >= sum(times[n] for n in names[:3])
            and sum(builds) <= times[names[0]]+times[names[1]]+1e-6, 'timing_order_mismatch')
    peaks = inner['process_peak_working_set_bytes']
    if (type(peaks) is not tuple or len(peaks) != 2 or type(peaks[0]) is not int or peaks[0] <= 0
            or peaks[0] > budget.max_process_peak_working_set_bytes
            or peaks[1] is not None and (type(peaks[1]) is not int or peaks[1] < peaks[0])):
        raise ValueError('normal peak memory record invalid')
    payload = ['tuple', [kernel._encode(v) for v in (kernel.CONTRACT, expected_input_identity,
        expected_execution_identity, specification, budget, expected_scale)]+[saved['normal'], saved['witness']]]
    size = len(_bytes(payload))
    require(type(inner['core_evidence_payload_bytes']) is int and inner['core_evidence_payload_bytes'] == size,
            'core_payload_size_mismatch')
    for failed, marker in ((size > budget.max_core_evidence_payload_bytes, 'core_evidence_payload_exceeds_budget'),
            (peaks[1] is not None and peaks[1] > budget.max_process_peak_working_set_bytes, 'process_lifetime_peak_exceeds_budget'),
            (times['observed_total_seconds'] > budget.max_observed_wall_seconds, 'observed_wall_time_exceeds_budget')):
        require(inner['errors'].count(marker) == int(failed), 'resource_error_mismatch:'+marker)
    require(peaks[1] is not None or any(x.startswith('post_memory:') for x in inner['errors']), 'missing_memory_error')
    accepted = bool(not inner['errors'] and raw is not None and raw['calls'] == 1 and raw['optimal']
        and witness_reproduced and not witness.errors and witness.terminal_carry is not None)
    require(inner['normal_accepted'] is accepted, 'normal_acceptance_mismatch')
    require(inner['status'] == 'accepted_normal' if accepted else
            inner['status'] in ('unresolved_normal', 'interrupted_normal'), 'normal_status_mismatch')
    require(not accepted or diagnostic['optimal_flag_reproduced'], 'accepted_normal_not_optimal')
    check()
    return dict(schema=SCHEMA, record_consistent=not errors, errors=tuple(errors),
        numerical_assignment_recomputed=bool(diagnostic and diagnostic['canonical_assignment_valid']),
        witness_reproduced=witness_reproduced, accepted_record_reproduced=accepted and not errors,
        native_replay=diagnostic, solver_calls_by_replay=0, native_execution_authenticated=False,
        resource_measurements_authenticated=False, public_source_binding_verified=False,
        executable_resume_available=False, formal_result=False, security_certified=False)
