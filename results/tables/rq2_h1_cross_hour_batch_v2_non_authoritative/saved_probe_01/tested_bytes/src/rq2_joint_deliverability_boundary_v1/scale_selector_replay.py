"""Solver-free reconstruction of complete scale-selector records.

Incomplete executions retain their archive status and yield no successor here.
"""
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from . import scale_selector_worker as transport, grid_evidence_replay as native

scale, store, codec = transport.scale, transport.store, transport.codec
SCHEMA = 'draft_scale_selector_record_replay_v1'


def implementation_identity(request):
    return codec._digest(SCHEMA, transport.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest(),
        native._identity(request.solver_specification, request.budget))


def _value(wire, depth=0):
    if depth > 32:
        raise ValueError('bounded raw evidence depth exceeded')
    if wire is None or type(wire) in (str, int, bool):
        return wire
    if type(wire) is not list or len(wire) != 2:
        raise ValueError('raw tuple/float wire required')
    if wire[0] == 'tuple' and type(wire[1]) is list:
        return tuple(_value(x, depth+1) for x in wire[1])
    if wire[0] == 'float' and type(wire[1]) is str:
        answer = float.fromhex(wire[1])
        if isfinite(answer) and answer.hex() == wire[1]:
            return answer
    raise ValueError('finite canonical raw wire required')


def _verify(data, request, *, expected_sha256, expected_implementation_identity, max_record_bytes):
    """Returns a private reconstructed result only after full byte reproduction."""
    scale.actual._hash(expected_sha256)
    scale.actual._hash(expected_implementation_identity)
    if type(max_record_bytes) is not int or not 0 < max_record_bytes <= 16*1024**2:
        raise ValueError('bounded replay record limit required')
    if type(data) is not bytes or len(data) > max_record_bytes or sha256(data).hexdigest() != expected_sha256:
        raise ValueError('replay record size/hash mismatch')
    request = transport.decode_request(transport.export_request(request))
    impl = implementation_identity(request)
    if impl != expected_implementation_identity:
        raise ValueError('replay implementation drift')
    module = scale._module(request.budget)
    reference = module is scale.reference
    info, disclosure, before, power = request.info, request.disclosure, request.before, request.power
    args = (info, disclosure, before) if reference else (info, disclosure, before, power)
    identity_function = module.reference_input_identity if reference else module.dispatch_input_identity
    identity = identity_function(*args)
    policy = scale.policy_identity(request.selection_spec, request.solver_specification, request.budget)
    uids = tuple(unit.uid for unit in info.network.units)
    labels = (('grid_request', 'l1_normal_deviation') if reference else ('l1_normal_deviation',))
    labels += tuple('generation:'+uid for uid in uids)
    scale._admit(request.selection_spec, request.solver_specification, request.budget, len(labels))
    if (identity != request.expected_identity or policy != request.expected_policy_identity
            or uids != request.budget.generator_uids or info.current.source_hour != request.budget.source_hour
            or (reference and power is not None) or (not reference and power is None)
            or (hasattr(before, 'selector_policy_identity') and before.selector_policy_identity != policy)):
        raise ValueError('replay input/policy/hour/UID mismatch')
    record = store._decoded(data)
    if type(record) is not dict or set(record) != {'schema', 'binding_identity', 'encoded_result', 'result_identity'}:
        raise ValueError('exact stored result record required')
    if record['schema'] != store.SCHEMA:
        raise ValueError('wrong stored result schema')
    scale.actual._hash(record['binding_identity'])
    saved = store._fields(record['encoded_result'], scale.ScaleSelectionResult)
    # The record digest is an external pin; binding_identity alone does not
    # authenticate its database root, normal source, or preceding execution.
    expected_result_id = sha256(json.dumps(
        ['tuple', [record['encoded_result']]], ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    if record['result_identity'] != expected_result_id:
        raise ValueError('stored result identity mismatch')
    pinned = dict(contract=scale.CONTRACT, input_identity=identity, policy_identity=policy,
        budget=request.budget, selector=request.selection_spec, specification=request.solver_specification,
        planned_solver_calls=len(labels), durable_invocation_tracking=False,
        hard_resource_limits_enforced=False, formal_result=False, security_certified=False)
    if any(store._bytes(saved[k]) != store._bytes(codec._encode(v)) for k, v in pinned.items()):
        raise ValueError('record differs from independently pinned request')
    stages_wire = saved['stages']
    if (type(stages_wire) is not list or len(stages_wire) != 2 or stages_wire[0] != 'tuple'
            or type(stages_wire[1]) is not list or len(stages_wire[1]) > len(labels)):
        raise ValueError('bounded stage tuple required')
    if saved['status'] != 'selected':
        if saved['status'] != 'unresolved' or saved['next_state'] is not None or saved['selected_request_exact'] is not None:
            raise ValueError('unresolved archive cannot publish successor')
        return dict(schema=SCHEMA, status='unresolved_archive_not_replayed', archive_reproduced=False,
            selection_accepted=False, solver_calls_by_replay_module=0, formal_result=False,
            native_execution_authenticated=False, executable_resume_available=False), None
    if len(stages_wire[1]) != len(labels):
        raise ValueError('selected record requires all stages')
    stages, frozen, calls = [], (), 0
    for index, wire in enumerate(stages_wire[1]):
        cls = module.ReferenceSelectionStage if reference else module.ActualDispatchStage
        stage_saved = store._fields(wire, cls)
        raw_fields = {k: _value(v) for k, v in store._fields(
            stage_saved['raw_solve'], scale.native.GridSolveEvidence).items()}
        def builder():
            if reference:
                return module._stage_model(*args, identity, index, frozen)
            return module._stage_model(*args, index, frozen)
        purpose = f'{module.PURPOSE}:{index}:{labels[index]}'
        diagnostic = native._replay(raw_fields, builder, request.solver_specification, request.budget, purpose)
        if (not diagnostic['replay_consistent'] or raw_fields['calls'] != 1
                or not diagnostic['canonical_assignment_valid'] or not diagnostic['optimal_flag_reproduced']):
            raise ValueError('selected stage lacks complete valid native replay')
        raw_fields.update(objective=diagnostic['recomputed_objective'],
            maximum_residual=diagnostic['recomputed_maximum_residual'],
            maximum_integrality_violation=diagnostic['recomputed_maximum_integrality_violation'],
            assignment_valid=bool(diagnostic['canonical_assignment_valid']) and not raw_fields['errors'],
            optimal=diagnostic['optimal_flag_reproduced'],
            native_infeasible=diagnostic['native_infeasible_flag_reproduced'])
        raw = scale.native._make(scale.native.GridSolveEvidence, **raw_fields)
        audit_args = (*args, identity) if reference else args
        witness, exact, lock, failures = scale._audit(module, audit_args, index, frozen, raw,
            request.selection_spec, request.solver_specification)
        if failures or witness is None or not witness.physical_assignment_valid:
            raise ValueError('selected stage physical/lock/gap audit failed')
        stage = scale._owned(cls, index=index, objective_label=labels[index],
            fixed_previous_objectives=frozen, fixed_previous_objective_hex=tuple(float(x).hex() for x in frozen),
            canonical_objective_hex=float(raw.objective).hex(), raw_solve=raw, assignment_witness=witness,
            maximum_exact_selector_violation=float(exact), maximum_objective_lock_violation=float(lock),
            accepted=True, errors=())
        if store._bytes(codec._encode(stage)) != store._bytes(wire):
            raise ValueError('stage differs from independent numerical replay')
        stages.append(stage)
        calls += raw.calls
        frozen += (raw.objective,)
    final = stages[-1].assignment_witness
    carry = final.physical_witness.next_carry if reference else final.next_carry
    values = dict(stages[-1].raw_solve.loaded_values)
    if carry.generation_mw != tuple((uid, values[f'generation[{uid}]']) for uid in uids):
        raise ValueError('selected carry differs from audited generation')
    origin_cls = module.ReferenceGridOrigin if reference else module.ActualDispatchOrigin
    state_cls = module.ReferenceGridState if reference else module.ActualDispatchState
    state_fields = dict(contract=before.contract,
        origin_identity=before.identity if type(before) is origin_cls else before.origin_identity,
        previous_state_identity=before.identity, selector_policy_identity=policy,
        selection_identity=codec._digest(scale.CONTRACT, policy, identity, power, tuple(stages)), physical_carry=carry)
    if reference:
        state_fields['protocol'] = before.protocol
    next_state = scale._owned(state_cls, **state_fields)
    result = scale._owned(scale.ScaleSelectionResult, **pinned, stages=tuple(stages),
        completed_solver_calls=calls, solver_calls=calls, next_state=next_state,
        selected_request_exact=final.candidate_grid_request_exact if reference else None,
        status='selected', errors=())
    if codec._digest(result) != record['result_identity'] or store._bytes(codec._encode(result)) != store._bytes(record['encoded_result']):
        raise ValueError('complete result differs from replay')
    if (implementation_identity(request) != impl or identity_function(*args) != identity
            or scale.policy_identity(request.selection_spec, request.solver_specification, request.budget) != policy):
        raise ValueError('replay implementation/input drift')
    return dict(schema=SCHEMA, status='reproduced_selected_chain', archive_reproduced=True,
        selection_accepted=True, reproduced_result_identity=result.identity,
        selected_state_identity=next_state.identity, verified_stage_count=len(stages),
        solver_calls_by_replay_module=0, formal_result=False, native_execution_authenticated=False,
        executable_resume_available=False), result


def replay_record(data, request, **expectations):
    """Diagnostic only: no deserialized successor is returned to the caller."""
    return _verify(data, request, **expectations)[0]
