"""Source-bound, solver-free replay of a complete normal journal record.

Recomputes numerical consistency; never restores an executable solver result.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import json
import math
from pathlib import Path

from . import normal_declared_store_gurobi_direct as journal, normal_worker as codec
from . import grid_evidence_replay as native_replay


execution = journal.execution
prepare = execution.prepare
source = execution.source
kernel = source.kernel
SCHEMA = 'draft_gurobi_direct_declared_normal_record_replay_v1'


def replay_identity(expected_declared_execution_identity, specification, budget):
    kernel._pin(expected_declared_execution_identity)
    if type(budget) is not kernel.NormalExecutionBudget:
        raise ValueError('independent normal replay budget required')
    return kernel._digest(SCHEMA, expected_declared_execution_identity,
        sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(codec.__file__).read_bytes()).hexdigest(),
        sha256(Path(journal.__file__).read_bytes()).hexdigest(),
        native_replay._identity(specification, budget))


def _fields(wire, cls):
    if (type(wire) is not list or len(wire) != 2 or wire[0] != cls.__name__
            or type(wire[1]) is not list or any(type(row) is not list or len(row) != 2 for row in wire[1])
            or [row[0] for row in wire[1]] != [f.name for f in fields(cls)]):
        raise ValueError('exact encoded '+cls.__name__+' field inventory required')
    return dict(wire[1])


def _decode_fields(wire, cls, nested=()):
    return {name: value if name in nested else codec._decode(value)
            for name, value in _fields(wire, cls).items()}


def _errors(value):
    if type(value) is not tuple or any(type(x) is not str for x in value):
        raise ValueError('immutable error strings required')


def _error_inventory(errors, markers, prefixes):
    """Static labels are enumerable; exception text is diagnostic, not authenticated."""
    for error in errors:
        if error in markers:
            continue
        parts = error.split(':', 2)
        if len(parts) != 3 or parts[0] not in prefixes or not parts[1].isidentifier():
            raise ValueError('unknown execution error vocabulary')
    if any(errors.count(marker) > 1 for marker in markers) or any(
            sum(error.startswith(prefix+':') for error in errors) > 1 for prefix in prefixes):
        raise ValueError('duplicate execution error marker')


def _false_flags(record, names):
    if any(record[n] is not False for n in names):
        raise ValueError('normal archive cannot upgrade execution or certification flags')


def _finite_time(x):
    return type(x) is float and math.isfinite(x) and x >= 0


@dataclass(frozen=True, init=False)
class GurobiDirectSourceRecordReplay(kernel._Owned):
    record_sha256: str
    result_identity: str
    replay_identity: str
    source_input_binding_verified: bool
    archive_consistent: bool
    native_record_scope: str
    assignment_recomputed: bool
    normal_witness_reproduced: bool
    recorded_normal_accepted: bool | None
    recorded_source_accepted: bool
    accepted_record_reproduced: bool
    native_replay_json: str | None
    errors: tuple[str, ...]
    status: str
    solver_calls_by_replay: int
    native_execution_authenticated: bool
    resource_measurements_authenticated: bool
    resume_authorized: bool
    optimality_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool


def _replay_source(source_wire, assembly, upstream_root, declaration, *, expected_record_sha256,
        expected_result_identity, expected_store_identity, expected_replay_identity, max_record_bytes,
        expected_assembly_identity, expected_pair_identity, expected_binding_identity, expected_input_identity,
        expected_normal_execution_identity, expected_source_execution_identity,
        expected_declared_execution_identity, expected_source_implementation_identity, expected_binding_implementation_identity,
        expected_scale, specification, budget, config_path=source.source_window.audit.DEFAULT_CONFIG):
    for pin in (expected_record_sha256, expected_result_identity, expected_store_identity,
                expected_replay_identity, expected_assembly_identity, expected_pair_identity,
                expected_binding_identity, expected_input_identity, expected_normal_execution_identity,
                expected_source_execution_identity):
        kernel._pin(pin)
    kernel._validate(specification, budget, expected_scale)
    if type(max_record_bytes) is not int or max_record_bytes <= 0:
        raise ValueError('explicit full record byte budget required')
    if type(assembly) is not source.StreamingSourceNormalAssembly or type(declaration) is not source.PairDeclaration:
        raise ValueError('typed source normal inputs required')
    owned, declared = deepcopy(assembly), deepcopy(declaration)
    if len(owned.inputs.source_hours) > budget.max_horizon:
        raise ValueError('normal replay horizon exceeds budget')
    root, config = Path(upstream_root).resolve(), Path(config_path).resolve()

    def implementation():
        if (replay_identity(expected_declared_execution_identity, specification, budget) != expected_replay_identity
                or kernel.normal_execution_identity(expected_input_identity, expected_scale, specification, budget)
                != expected_normal_execution_identity
                or source.source_execution_identity(expected_binding_identity, expected_normal_execution_identity,
                    declared, expected_assembly_identity=expected_assembly_identity,
                    expected_pair_identity=expected_pair_identity,
                    expected_source_implementation_identity=expected_source_implementation_identity,
                    expected_binding_implementation_identity=expected_binding_implementation_identity) != expected_source_execution_identity):
            raise ValueError('normal replay implementation or execution identity drift')
        if (owned.assembly_identity != expected_assembly_identity or owned.normal_identity != expected_input_identity
                or kernel.normal_input_identity(owned.inputs) != expected_input_identity):
            raise ValueError('normal replay input identity mismatch')

    def binding():
        implementation()
        report = source.binding.bind_pair_normal(owned, root, declared,
            expected_assembly_identity=expected_assembly_identity, expected_pair_identity=expected_pair_identity,
            expected_source_implementation_identity=expected_source_implementation_identity,
            expected_implementation_identity=expected_binding_implementation_identity, config_path=config)
        if (type(report) is not source.binding.StreamingPairBinding
                or report.binding_identity != expected_binding_identity
                or report.source_assembly_identity != expected_assembly_identity
                or report.normal_identity != expected_input_identity or report.pair_identity != expected_pair_identity
                or report.implementation_identity != expected_binding_implementation_identity
                or kernel._digest(source.binding.CONTRACT, report.normal_identity, report.source_assembly_identity,
                    report.pair_identity, report.legacy_content_json, report.implementation_identity) != expected_binding_identity):
            raise ValueError('normal replay source binding mismatch')

        implementation()
        return source._json(asdict(report))

    before = binding()
    outer = _decode_fields(source_wire, source.GurobiDirectSourceNormalExecutionResult, ('normal_result',))
    _errors(outer['errors'])
    _error_inventory(outer['errors'], ('normal_result_binding_mismatch',
        'normal_result_acceptance_inconsistent', 'source_binding_changed'),
        ('normal_return_missing', 'normal_result_validation', 'post_source'))
    _false_flags(outer, ('hard_resource_limits_enforced', 'durable_invocation_tracking', 'registered_coupling',
                         'observed_power_mapping', 'formal_result', 'security_certified'))
    if (outer['contract'] != source.CONTRACT or outer['execution_identity'] != expected_source_execution_identity
            or outer['expected_binding_identity'] != expected_binding_identity or outer['binding_before_json'] != before
            or not _finite_time(outer['observed_wrapper_seconds'])):
        raise ValueError('normal replay outer source or contract mismatch')
    for name in ('source_correspondence_verified', 'source_bound_normal_accepted', 'call_count_complete'):
        if type(outer[name]) is not bool:
            raise ValueError('typed source result flags required')
    errors = []

    def require(condition, error):
        if not condition:
            errors.append(error)

    correspondence = outer['binding_after_json'] is not None and outer['binding_after_json'] == before
    require(outer['errors'].count('source_binding_changed') == int(
        outer['binding_after_json'] is not None and outer['binding_after_json'] != before),
        'source_binding_change_error_projection_mismatch')
    # A lineage/acceptance inconsistency cannot be a consistent replay, even if
    # the archived consumer correctly rejected it. Keep that distinction explicit.
    require(not any(error in outer['errors'] for error in
        ('normal_result_binding_mismatch', 'normal_result_acceptance_inconsistent')),
        'source_recorded_result_mismatch')
    require(outer['source_correspondence_verified'] is correspondence, 'source_correspondence_flag_mismatch')
    require(outer['binding_after_json'] is None or outer['binding_after_json'] == before, 'archived_post_binding_mismatch')
    require(sum(x.startswith('post_source:') for x in outer['errors']) == int(outer['binding_after_json'] is None),
            'post_source_error_phase_mismatch')
    inner_wire = outer['normal_result']
    inner = raw = diagnostic = recomputed_witness = None
    witness_reproduced = False
    if inner_wire is not None:
        inner = _decode_fields(inner_wire, kernel.GurobiDirectNormalExecutionResult, ('normal', 'witness'))
        _errors(inner['errors'])
        _false_flags(inner, ('hard_resource_limits_enforced', 'durable_invocation_tracking',
                            'public_source_binding_verified', 'formal_result', 'security_certified'))
        if (inner['contract'] != kernel.CONTRACT or inner['input_identity'] != expected_input_identity
                or inner['execution_identity'] != expected_normal_execution_identity
                or kernel._digest(inner['specification']) != kernel._digest(specification)
                or kernel._digest(inner['budget']) != kernel._digest(budget)
                or kernel._digest(inner['scale']) != kernel._digest(expected_scale)
                or inner['causal_certificate'] is not None or inner['infeasibility_certificate'] is not None):
            raise ValueError('normal replay inner contract mismatch')
        if type(inner['normal_accepted']) is not bool or type(inner['call_count_complete']) is not bool:
            raise ValueError('typed normal result flags required')
        raw_wire, witness_wire = inner['normal'], inner['witness']
        if raw_wire is None or witness_wire is None:
            # Missing raw always requires a failed pipeline. A missing witness
            # requires it only when the returned raw claims a valid assignment.
            raw_probe = None if raw_wire is None else _decode_fields(raw_wire, kernel.native.GridSolveEvidence)
            if raw_probe is None or raw_probe['assignment_valid'] is True:
                require(any(x.startswith('normal_pipeline:') for x in inner['errors']), 'missing_pipeline_error')
        if raw_wire is not None:
            raw = _decode_fields(raw_wire, kernel.native.GridSolveEvidence)

            def builder():
                implementation()
                model = kernel.streaming.build_continuous_normal_model(owned.inputs, expected_identity=expected_input_identity,
                    expected_implementation_identity=kernel.streaming.implementation_identity())
                if kernel.model_scale(model) != expected_scale:
                    raise ValueError('normal replay actual scale differs from external pin')
                return model

            # Reuse the immutable numerical core, under this module's independent
            # NormalExecutionBudget admission. The old GridDevelopmentBudget API
            # and its smaller scale ceiling remain unchanged.
            diagnostic = native_replay._replay(raw, builder, specification, budget, 'event_blind_normal')
            errors.extend('native:'+x for x in diagnostic['replay_errors'])
            require(all(x in inner['errors'] for x in raw['errors']), 'missing_native_execution_error')
        require(inner['call_count_complete'] is (raw is not None), 'inner_call_completeness_mismatch')
        require((inner['solver_calls'] is None if raw is None else
                 type(inner['solver_calls']) is int and inner['solver_calls'] == raw['calls']), 'inner_call_count_mismatch')
        if witness_wire is not None:
            _fields(witness_wire, kernel.NormalAssignmentWitness)
            if raw is None or raw['assignment_valid'] is not True:
                errors.append('witness_without_valid_raw_assignment')
            else:
                recomputed_witness = kernel.streaming.audit_normal_assignment(owned.inputs, dict(raw['loaded_values']),
                    expected_identity=expected_input_identity,
                    expected_implementation_identity=kernel.streaming.implementation_identity())
                witness_reproduced = kernel._encode(recomputed_witness) == witness_wire
                require(witness_reproduced, 'normal_witness_mismatch')
                require(all(x in inner['errors'] for x in recomputed_witness.errors), 'missing_witness_error')
        timings = inner['timings']
        names = ('preflight_seconds', 'solve_load_canonical_pipeline_seconds', 'normal_witness_audit_seconds',
                 'builder_seconds_nested', 'observed_total_seconds')
        if (type(timings) is not tuple or len(timings) != 5
                or any(type(row) is not tuple or len(row) != 2 for row in timings)
                or tuple(row[0] for row in timings) != names):
            raise ValueError('exact normal timing inventory required')
        times = dict(timings)
        if (any(not _finite_time(times[n]) for n in names if n != 'builder_seconds_nested')
                or type(times['builder_seconds_nested']) is not tuple
                or any(not _finite_time(x) for x in times['builder_seconds_nested'])):
            raise ValueError('finite normal timing records required')
        builds = times['builder_seconds_nested']
        # Admission always completed before an inner result can exist. The
        # native pipeline adds its initial model and, for valid assignments,
        # the independently rebuilt canonical model; no retry path exists.
        require(1 <= len(builds) <= 3, 'builder_inventory_mismatch')
        require(raw is None or len(builds) >= 2, 'native_builder_inventory_mismatch')
        require(raw is None or raw['assignment_valid'] is not True or len(builds) == 3,
                'valid_assignment_builder_inventory_mismatch')
        require(not inner['normal_accepted'] or len(builds) == 3, 'accepted_builder_inventory_mismatch')
        # Clock subtraction/addition roundoff only; this does not relax the
        # original wall-time budget comparison below.
        clock_roundoff = 1e-6
        stages = sum(times[n] for n in names[:3])
        require(times['observed_total_seconds']+clock_roundoff >= stages, 'normal_timing_order_mismatch')
        require(sum(times['builder_seconds_nested']) <= times['preflight_seconds']
                +times['solve_load_canonical_pipeline_seconds']+clock_roundoff, 'nested_builder_timing_mismatch')
        require(outer['observed_wrapper_seconds']+clock_roundoff >= times['observed_total_seconds'],
                'wrapper_timing_order_mismatch')
        peaks = inner['process_peak_working_set_bytes']
        if (type(peaks) is not tuple or len(peaks) != 2 or type(peaks[0]) is not int or peaks[0] <= 0
                or peaks[0] > budget.max_process_peak_working_set_bytes
                or peaks[1] is not None and (type(peaks[1]) is not int or peaks[1] <= 0)):
            raise ValueError('invalid normal peak memory records')
        require(peaks[1] is None or peaks[1] >= peaks[0], 'lifetime_peak_decreased')
        payload_wire = ['tuple', [kernel._encode(x) for x in (kernel.CONTRACT, expected_input_identity,
            expected_normal_execution_identity, specification, budget, expected_scale)] + [raw_wire, witness_wire]]
        size = len(json.dumps(payload_wire, ensure_ascii=True, allow_nan=False).encode('utf-8'))
        require(type(inner['core_evidence_payload_bytes']) is int and inner['core_evidence_payload_bytes'] == size,
                'core_evidence_size_mismatch')
        for failed, error in ((size > budget.max_core_evidence_payload_bytes, 'core_evidence_payload_exceeds_budget'),
                (peaks[1] is not None and peaks[1] > budget.max_process_peak_working_set_bytes, 'process_lifetime_peak_exceeds_budget'),
                (times['observed_total_seconds'] > budget.max_observed_wall_seconds, 'observed_wall_time_exceeds_budget')):
            require(inner['errors'].count(error) == int(failed), 'resource_error_projection_mismatch:'+error)
        require(peaks[1] is not None or any(x.startswith('post_memory:') for x in inner['errors']),
                'missing_post_memory_error')
        accepted = bool(not inner['errors'] and raw is not None and raw['calls'] == 1 and raw['optimal']
            and recomputed_witness is not None and not recomputed_witness.errors and recomputed_witness.terminal_carry is not None)
        require(inner['normal_accepted'] is accepted, 'normal_acceptance_flag_mismatch')
        require(inner['status'] == 'accepted_normal' if accepted else
                inner['status'] in ('unresolved_normal', 'interrupted_normal'), 'normal_status_mismatch')
        if inner['normal_accepted']:
            require(diagnostic is not None and diagnostic['replay_consistent']
                and diagnostic['optimal_flag_reproduced'] is True and witness_reproduced,
                'accepted_normal_missing_complete_replayed_evidence')
    require(outer['call_count_complete'] is (inner is not None and inner['call_count_complete']),
            'outer_call_completeness_mismatch')
    require((outer['solver_calls'] is None if inner is None or inner['solver_calls'] is None else
             type(outer['solver_calls']) is int and outer['solver_calls'] == inner['solver_calls']), 'outer_call_count_mismatch')
    accepted_source = correspondence and not outer['errors'] and inner is not None and inner['normal_accepted'] is True
    require(outer['source_bound_normal_accepted'] is accepted_source, 'source_acceptance_flag_mismatch')
    require(outer['status'] == 'accepted_source_bound_normal' if accepted_source else
            outer['status'] in ('unresolved_source_bound_normal', 'interrupted_source_bound_normal'), 'source_status_mismatch')
    if inner is None:
        require(any(x.startswith('normal_return_missing:') for x in outer['errors']), 'missing_return_error')
        require(not any(x.startswith('normal_result_validation:') for x in outer['errors']),
                'validation_error_without_inner_return')
    else:
        require(not any(x.startswith('normal_return_missing:') for x in outer['errors']),
            'fabricated_missing_return_error')
    require(binding() == before, 'source_changed_during_replay')
    implementation()
    accepted_reproduced = not errors and accepted_source
    return kernel.native._make(GurobiDirectSourceRecordReplay, record_sha256=expected_record_sha256,
        result_identity=expected_result_identity, replay_identity=expected_replay_identity,
        source_input_binding_verified=True, archive_consistent=not errors,
        native_record_scope='no_native_record' if diagnostic is None else diagnostic['scope'],
        assignment_recomputed=diagnostic is not None and diagnostic['assignment_recomputed'],
        normal_witness_reproduced=witness_reproduced,
        recorded_normal_accepted=None if inner is None else inner['normal_accepted'],
        recorded_source_accepted=outer['source_bound_normal_accepted'], accepted_record_reproduced=accepted_reproduced,
        native_replay_json=None if diagnostic is None else source._json(diagnostic), errors=tuple(errors),
        status='inconsistent_normal_record' if errors else ('replayed_accepted_normal_record' if accepted_reproduced
            else 'replayed_unresolved_normal_record'), solver_calls_by_replay=0,
        native_execution_authenticated=False, resource_measurements_authenticated=False,
        resume_authorized=False, optimality_certificate=None, infeasibility_certificate=None,
        formal_result=False, security_certified=False)


@dataclass(frozen=True, init=False)
class DeclaredGurobiDirectNormalRecordReplay(kernel._Owned):
    record_sha256: str
    result_identity: str
    replay_identity: str
    archive_consistent: bool
    accepted_record_reproduced: bool
    source_input_binding_verified: bool
    assignment_recomputed: bool
    normal_witness_reproduced: bool
    recorded_declared_accepted: bool
    source_replay_json: str | None
    errors: tuple[str, ...]
    status: str
    solver_calls_by_replay: int
    native_execution_authenticated: bool
    resource_measurements_authenticated: bool
    resume_authorized: bool
    optimality_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool


def replay_normal_record(data, request, *, expected_record_sha256, expected_result_identity,
        expected_store_identity, expected_replay_identity, max_record_bytes,
        expected_request_identity, expected_declared_execution_identity,
        expected_assembly_identity, expected_binding_identity, expected_source_implementation_identity,
        expected_binding_implementation_identity, expected_normal_execution_identity,
        expected_source_execution_identity, specification, budget):
    """Rebuild pinned inputs and audit wire data; never restore executable results."""
    for pin in (expected_record_sha256, expected_result_identity, expected_store_identity,
            expected_replay_identity, expected_request_identity, expected_declared_execution_identity,
            expected_assembly_identity, expected_binding_identity, expected_source_implementation_identity,
            expected_binding_implementation_identity, expected_normal_execution_identity,
            expected_source_execution_identity):
        kernel._pin(pin)
    if type(max_record_bytes) is not int or max_record_bytes <= 0:
        raise ValueError('explicit full record byte budget required')
    if type(data) is not bytes or len(data) > max_record_bytes or sha256(data).hexdigest() != expected_record_sha256:
        raise ValueError('normal replay record size/hash mismatch')
    request = deepcopy(request)
    prepared = None

    def implementation():
        if (prepare.task_source_identity(request) != expected_request_identity
                or replay_identity(expected_declared_execution_identity, specification, budget) != expected_replay_identity
                or execution.declared_execution_identity(request, expected_request_identity=expected_request_identity,
                    expected_source_execution_identity=expected_source_execution_identity) != expected_declared_execution_identity
                or source.binding.source.implementation_identity() != expected_source_implementation_identity
                or source.binding.implementation_identity() != expected_binding_implementation_identity
                or kernel.normal_execution_identity(request.expected_input_identity, request.expected_scale,
                    specification, budget) != expected_normal_execution_identity):
            raise ValueError('declared replay implementation or execution identity drift')
        if prepared is not None and source.source_execution_identity(expected_binding_identity,
                expected_normal_execution_identity, prepared.declaration,
                expected_assembly_identity=expected_assembly_identity, expected_pair_identity=request.expected_pair_identity,
                expected_source_implementation_identity=expected_source_implementation_identity,
                expected_binding_implementation_identity=expected_binding_implementation_identity) != expected_source_execution_identity:
            raise ValueError('source replay execution identity drift')

    def declarations():
        return tuple(prepare._read_pinned(path, pin, maximum) for path, pin, maximum in (
            (request.normal_record_path, request.expected_normal_record_sha256, request.max_normal_record_bytes),
            (request.pair_declaration_path, request.expected_pair_declaration_sha256, request.max_pair_declaration_bytes),
            (request.config_path, request.expected_config_sha256, request.max_config_bytes)))

    implementation()
    kernel._validate(specification, budget, request.expected_scale)
    record = journal._decoded(data)
    if (set(record) != {'schema', 'store_identity', 'declared_execution_identity', 'result_identity', 'encoded_result'}
            or record['schema'] != journal.SCHEMA or record['store_identity'] != expected_store_identity
            or record['declared_execution_identity'] != expected_declared_execution_identity
            or record['result_identity'] != expected_result_identity
            or journal._result_identity(record['encoded_result']) != expected_result_identity):
        raise ValueError('declared replay independently expected record lineage mismatch')
    declared = _decode_fields(record['encoded_result'], execution.DeclaredGurobiDirectNormalResult, ('source_result',))
    _errors(declared['errors'])
    _error_inventory(declared['errors'], ('source_result_binding_mismatch',
        'normal_result_binding_mismatch', 'source_result_acceptance_inconsistent'),
        ('source_return', 'post_declaration'))
    _false_flags(declared, ('observed_power_mapping', 'hard_resource_limits_enforced',
        'durable_invocation_tracking', 'formal_result'))
    if (declared['contract'] != execution.CONTRACT or declared['execution_identity'] != expected_declared_execution_identity
            or declared['request_identity'] != expected_request_identity or declared['mechanism_initial_state'] is not True
            or type(declared['accepted']) is not bool or type(declared['call_count_complete']) is not bool):
        raise ValueError('declared replay contract or role mismatch')
    timings = declared['preparation_timings']
    names = ('declaration_seconds', 'source_assembly_seconds', 'source_binding_seconds',
        'post_check_seconds', 'observed_total_seconds')
    if (type(timings) is not tuple or len(timings) != len(names)
            or any(type(row) is not tuple or len(row) != 2 for row in timings)
            or tuple(row[0] for row in timings) != names or any(not _finite_time(row[1]) for row in timings)):
        raise ValueError('exact finite preparation timing inventory required')
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    require(abs(sum(row[1] for row in timings[:-1])-timings[-1][1]) <= 1e-6,
        'preparation_timing_sum_mismatch')
    before = declarations()
    prepared = prepare.prepare_task_inputs(request, expected_request_identity=expected_request_identity)
    if (type(prepared) is not prepare.PreparedStreamingNormalTaskInputs
            or prepared.request_identity != expected_request_identity
            or type(prepared.assembly) is not source.StreamingSourceNormalAssembly
            or prepared.assembly.assembly_identity != expected_assembly_identity
            or prepared.assembly.normal_identity != request.expected_input_identity
            or prepared.assembly.implementation_identity != expected_source_implementation_identity
            or type(prepared.binding) is not source.binding.StreamingPairBinding
            or prepared.binding.binding_identity != expected_binding_identity
            or prepared.binding.implementation_identity != expected_binding_implementation_identity
            or type(prepared.solver_calls) is not int or prepared.solver_calls != 0
            or prepared.mechanism_initial_state is not True
            or any(getattr(prepared, name) is not False for name in
                ('observed_power_mapping', 'normal_assignment_verified', 'formal_result'))):
        raise ValueError('replay prepared inputs differ from independent pins')
    implementation()
    source_wire = declared['source_result']
    diagnostic = None
    require(not any(error in declared['errors'] for error in ('source_result_binding_mismatch',
        'normal_result_binding_mismatch', 'source_result_acceptance_inconsistent')),
        'declared_recorded_result_mismatch')
    if source_wire is not None:
        outer = _decode_fields(source_wire, source.GurobiDirectSourceNormalExecutionResult, ('normal_result',))
        diagnostic = _replay_source(source_wire, prepared.assembly, request.upstream_root, prepared.declaration,
            expected_record_sha256=expected_record_sha256, expected_result_identity=expected_result_identity,
            expected_store_identity=expected_store_identity, expected_replay_identity=expected_replay_identity,
            max_record_bytes=max_record_bytes, expected_assembly_identity=expected_assembly_identity,
            expected_pair_identity=request.expected_pair_identity, expected_binding_identity=expected_binding_identity,
            expected_input_identity=request.expected_input_identity,
            expected_normal_execution_identity=expected_normal_execution_identity,
            expected_source_execution_identity=expected_source_execution_identity,
            expected_declared_execution_identity=expected_declared_execution_identity,
            expected_source_implementation_identity=expected_source_implementation_identity,
            expected_binding_implementation_identity=expected_binding_implementation_identity,
            expected_scale=request.expected_scale, specification=specification, budget=budget, config_path=request.config_path)
        errors.extend('source:'+error for error in diagnostic.errors)
        require(declared['call_count_complete'] is outer['call_count_complete'], 'declared_call_completeness_mismatch')
        require(declared['solver_calls'] is None if outer['solver_calls'] is None else
            type(declared['solver_calls']) is int and declared['solver_calls'] == outer['solver_calls'],
            'declared_call_count_mismatch')
        accepted = not declared['errors'] and outer['source_bound_normal_accepted'] is True
        require(not declared['accepted'] or diagnostic.accepted_record_reproduced,
            'declared_accepted_without_replayed_source')
        require(not any(error.startswith('source_return:') for error in declared['errors']),
            'source_return_error_with_complete_source')
    else:
        require(declared['solver_calls'] is None and declared['call_count_complete'] is False,
            'missing_source_return_count_not_unknown')
        require(any(error.startswith('source_return:') for error in declared['errors']), 'missing_source_return_error')
        accepted = False
    require(declared['accepted'] is accepted, 'declared_acceptance_flag_mismatch')
    require(declared['status'] == 'accepted_declared_normal' if accepted else declared['status'] in
        ('unresolved_declared_normal', 'interrupted_declared_normal'), 'declared_status_mismatch')
    if declarations() != before:
        raise ValueError('declarations changed during replay')
    implementation()
    reproduced = not errors and accepted
    return kernel.native._make(DeclaredGurobiDirectNormalRecordReplay, record_sha256=expected_record_sha256,
        result_identity=expected_result_identity, replay_identity=expected_replay_identity,
        archive_consistent=not errors, accepted_record_reproduced=reproduced, source_input_binding_verified=True,
        assignment_recomputed=diagnostic is not None and diagnostic.assignment_recomputed,
        normal_witness_reproduced=diagnostic is not None and diagnostic.normal_witness_reproduced,
        recorded_declared_accepted=declared['accepted'], source_replay_json=None if diagnostic is None else source._json(asdict(diagnostic)),
        errors=tuple(errors), status='inconsistent_declared_normal_record' if errors else
        ('replayed_accepted_declared_normal_record' if reproduced else 'replayed_unresolved_declared_normal_record'),
        solver_calls_by_replay=0, native_execution_authenticated=False, resource_measurements_authenticated=False,
        resume_authorized=False, optimality_certificate=None, infeasibility_certificate=None, formal_result=False,
        security_certified=False)


def replay_normal_store(root, request, *, expected_head, expected_record_sha256, expected_result_identity,
        expected_replay_identity, max_record_bytes, **arguments):
    """Hold the cooperative lease; require independently retained current head."""
    with journal.DevelopmentDeclaredGurobiDirectNormalStore(root, request, create=False, expected_head=expected_head,
            max_record_bytes=max_record_bytes, **arguments) as store:
        inspection = store.inspect()
        if (not inspection.result_present or inspection.head != expected_head or inspection.head == inspection.genesis
                or inspection.result_identity != expected_result_identity
                or inspection.archived_result_sha256 != expected_record_sha256):
            raise ValueError('independently retained complete current normal head/record required')
        connection = store._connect()
        try:
            _, results = store._rows(connection)
            raw = results[0][1]
        finally:
            connection.close()
        result = replay_normal_record(raw, request, expected_record_sha256=expected_record_sha256,
            expected_result_identity=expected_result_identity, expected_store_identity=inspection.store_identity,
            expected_replay_identity=expected_replay_identity, max_record_bytes=max_record_bytes, **arguments)
        if store.inspect() != inspection:
            raise ValueError('normal journal changed during numerical replay')
        return result
