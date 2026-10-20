"""Source-bound selector archive audit, with no native optimization or resume."""
from dataclasses import dataclass, fields
from hashlib import sha256
import json
from pathlib import Path

from . import reference_selector as reference
from . import actual_dispatch_selector as actual
from . import grid_evidence_replay as native
from . import continuous_grid_candidate as capture
from .current_grid_step import _Owned, _owned
from .prefix_handoff import _encoded, _unique_object, _reject_constant


SCHEMA = 'rq2_source_bound_selector_replay_v1'
DEPENDENCIES = tuple(sorted(set(native.DEPENDENCIES) | {
    'src/rq2_joint_deliverability_boundary_v1/'+name+'.py' for name in (
        'selector_replay', 'reference_grid', 'reference_selector', 'actual_dispatch_selector')}))


def _implementation(spec, budget):
    if SCHEMA != 'rq2_source_bound_selector_replay_v1':
        raise ValueError('selector replay schema drift')
    root = Path(__file__).resolve().parents[2]
    return capture._digest(SCHEMA, tuple((p, sha256((root/p).read_bytes()).hexdigest()) for p in DEPENDENCIES),
        native._identity(spec, budget))


def _api(kind):
    if kind == 'reference':
        return reference, reference.ReferenceSelectionResult, reference.ReferenceSelectionStage
    if kind == 'actual':
        return actual, actual.ActualDispatchResult, actual.ActualDispatchStage
    raise ValueError('explicit reference or actual selector kind required')


def _payload(kind, result):
    return dict(schema=SCHEMA, status='DRAFT_NONAUTHORITATIVE', kind=kind,
        implementation_identity=_implementation(result.specification, result.budget), result=result,
        native_execution_authenticated=False, formal_result=False, security_certified=False,
        resume_authorized=False)


def export_selector_archive(result):
    kind = ('reference' if type(result) is reference.ReferenceSelectionResult else
            'actual' if type(result) is actual.ActualDispatchResult else None)
    api, _, _ = _api(kind)
    if result.selector_policy_identity != api._policy_identity(result.selector, result.specification, result.budget):
        raise ValueError('selector result policy or implementation drift')
    return _encoded(_payload(kind, result))


@dataclass(frozen=True, init=False)
class SelectorReplayDiagnostic(_Owned):
    kind: str
    artifact_sha256: str
    input_identity: str
    selector_policy_identity: str
    implementation_identity: str
    status: str
    archived_outcome: str
    source_input_binding_verified: bool
    policy_binding_verified: bool
    business_power_binding_verified: bool
    call_inventory_verified: bool
    recorded_solver_calls: int
    selector_chain_verified: bool
    selection_accepted: bool
    archive_reproduced: bool
    verified_stage_count: int
    accepted_prefix_length: int
    observed_stage_count: int
    native_diagnostics: tuple
    reproduced_result_identity: str | None
    selected_state_identity: str | None
    selected_request_exact: tuple | None
    solver_calls_by_replay_module: int
    external_builder_accepted: bool
    native_execution_authenticated: bool
    exact_lexicographic_certificate: None
    infeasibility_certificate: None
    capacity_certificate: None
    causal_certificate: None
    formal_result: bool
    security_certified: bool
    resume_authorized: bool


def _input(kind, info, disclosure, before, power):
    return (reference.reference_input_identity(info, disclosure, before) if kind == 'reference'
        else actual.dispatch_input_identity(info, disclosure, before, power))


def _builder(kind, info, disclosure, before, power, identity, index, frozen):
    # No external callable enters either public wrapper.
    if kind == 'reference':
        return reference._stage_model(info, disclosure, before, identity, index, frozen)
    return actual._stage_model(info, disclosure, before, power, index, frozen)


def _raw_archive(raw, identity, purpose, spec, budget):
    return _encoded(dict(schema=native.SCHEMA, status='DRAFT_NONAUTHORITATIVE',
        input_identity=identity, purpose=purpose, specification=spec, budget=budget,
        implementation_identity=native._identity(spec, budget), raw=raw,
        formal_result=False, security_certified=False, native_execution_authenticated=False))


def _verify(kind, data, info, disclosure, before, power, *, expected_sha256, expected_input_identity,
            expected_policy_identity, selector, solver_specification, budget):
    """Private reconstruction is discarded by public diagnostic-only wrappers."""
    api, result_type, stage_type = _api(kind)
    native._hash(expected_sha256)
    native._hash(expected_input_identity)
    native._hash(expected_policy_identity)
    if type(data) is not bytes or sha256(data).hexdigest() != expected_sha256:
        raise ValueError('selector archive digest mismatch')
    identity = _input(kind, info, disclosure, before, power)
    if identity != expected_input_identity:
        raise ValueError('independent selector input identity mismatch')
    uids = tuple(g.uid for g in info.network.units)
    if uids != tuple(sorted(set(uids))):
        raise ValueError('sorted unique generator inventory required')
    labels = (('grid_request',) if kind == 'reference' else ()) + ('l1_normal_deviation',) + tuple('generation:'+u for u in uids)
    spec = solver_specification
    api._admit(selector, spec, budget, len(labels))
    policy = api._policy_identity(selector, spec, budget)
    if policy != expected_policy_identity or (hasattr(before, 'selector_policy_identity') and before.selector_policy_identity != policy):
        raise ValueError('independent selector policy or predecessor mismatch')
    implementation = _implementation(spec, budget)
    largest = _builder(kind, info, disclosure, before, power, identity, len(labels)-1, (0.,)*(len(labels)-1))
    scale = capture.model_scale(largest)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('complete replay selector exceeds declared scale')
    payload = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    expected_envelope = dict(schema=SCHEMA, status='DRAFT_NONAUTHORITATIVE', kind=kind,
        implementation_identity=implementation, result=payload['result'], native_execution_authenticated=False,
        formal_result=False, security_certified=False, resume_authorized=False)
    if _encoded(expected_envelope) != data:
        raise ValueError('selector archive canonical envelope mismatch')
    saved = payload['result']
    if type(saved) is not dict or set(saved) != {f.name for f in fields(result_type)}:
        raise ValueError('selector result field inventory mismatch')
    pinned = dict(contract=api.CONTRACT, input_identity=identity, selector_policy_identity=policy,
        selector=selector, specification=spec, budget=budget, planned_solver_calls=len(labels),
        exact_lexicographic_certificate=None, causal_certificate=None, infeasibility_certificate=None,
        capacity_certificate=None, formal_result=False, security_certified=False)
    if kind == 'actual':
        pinned['prescribed_power'] = power
    if _encoded({k: saved[k] for k in pinned}) != _encoded(pinned):
        raise ValueError('selector result differs from independent input/policy contract')
    saved_stages = saved['stages']
    if type(saved_stages) is not list or not 1 <= len(saved_stages) <= len(labels):
        raise ValueError('nonempty bounded selector stage inventory required')
    stages, diagnostics, frozen, errors, calls = [], [], (), [], 0
    partial = False
    for index, saved_stage in enumerate(saved_stages):
        if type(saved_stage) is not dict or set(saved_stage) != {f.name for f in fields(stage_type)}:
            raise ValueError('selector stage field inventory mismatch')
        stage_header = dict(index=index, objective_label=labels[index], fixed_previous_objectives=frozen,
            fixed_previous_objective_hex=tuple(float(x).hex() for x in frozen))
        if _encoded({k: saved_stage[k] for k in stage_header}) != _encoded(stage_header):
            raise ValueError('selector stage order or prior objective chain mismatch')
        raw_data = _raw_archive(saved_stage['raw_solve'], identity, f'{api.PURPOSE}:{index}:{labels[index]}', spec, budget)
        diagnostic = native.replay_grid_evidence(raw_data, expected_sha256=sha256(raw_data).hexdigest(),
            expected_input_identity=identity, expected_purpose=f'{api.PURPOSE}:{index}:{labels[index]}',
            specification=spec, budget=budget,
            builder=lambda: _builder(kind, info, disclosure, before, power, identity, index, frozen))
        diagnostics.append(diagnostic)
        raw_fields = native._tuples(saved_stage['raw_solve'])
        # _solve sets calls=1 immediately before entering solver.solve. Only
        # an exception in its create block can produce a zero-call record;
        # post_snapshot may fail after either path and does not reset calls.
        create_failed = any(e.startswith('create:') for e in raw_fields['errors'])
        if raw_fields['calls'] != (0 if create_failed else 1):
            raise ValueError('native execution stage and call inventory mismatch')
        if create_failed and (
                any(e.split(':', 1)[0] in ('solve', 'native_result', 'native_inventory',
                    'load', 'canonical_assignment') for e in raw_fields['errors'])
                or any(raw_fields[k] for k in ('solver_records', 'problem_records',
                    'solution_statuses', 'preload_values', 'native_values',
                    'canonical_completed_values', 'loaded_values', 'native_objectives'))
                or any(raw_fields[k] is not None for k in ('solution_count', 'objective',
                    'lower', 'upper', 'maximum_residual', 'maximum_integrality_violation'))
                or raw_fields['structures'][1] is not None):
            raise ValueError('create failure contains post-call evidence')
        calls += raw_fields['calls']
        if calls > budget.max_solver_calls:
            raise ValueError('selector replay call inventory exceeds budget')
        if not diagnostic.replay_consistent:
            if diagnostic.scope != 'partial_execution_evidence':
                raise ValueError('native record failed model-relative replay: '+repr(diagnostic.replay_errors))
            # Preserve incomplete execution evidence, but never reconstruct an
            # accepted stage or successor from it, even with a new digest pin.
            state_key = 'next_reference_state' if kind == 'reference' else 'next_dispatch_state'
            if (index != len(saved_stages)-1 or saved_stage['accepted'] is not False
                    or saved['status'] != 'unresolved' or saved[state_key] is not None
                    or (kind == 'reference' and saved['selected_request_exact'] is not None)):
                raise ValueError('partial native evidence cannot publish selection or consume suffix')
            if (type(saved_stage['errors']) is not list or not saved_stage['errors']
                    or any(type(e) is not str or not e for e in saved_stage['errors'])
                    or _encoded(saved['errors']) != _encoded(tuple(f'{index}:{e}' for e in saved_stage['errors']))):
                raise ValueError('partial selector rejection error inventory mismatch')
            partial = True
            break
        # Only complete re-audited records acquire a private temporary typed
        # representation. No deserialized state or solver result is returned.
        raw_fields.update(objective=diagnostic.recomputed_objective,
            maximum_residual=diagnostic.recomputed_maximum_residual,
            maximum_integrality_violation=diagnostic.recomputed_maximum_integrality_violation,
            assignment_valid=bool(diagnostic.canonical_assignment_valid) and not raw_fields['errors'],
            optimal=diagnostic.optimal_flag_reproduced, native_infeasible=diagnostic.native_infeasible_flag_reproduced)
        raw = capture._make(capture.GridSolveEvidence, **raw_fields)
        if kind == 'reference':
            witness, exact, lock, stage_errors = api._audit_stage(info, disclosure, before, identity, index, frozen, raw, selector)
        else:
            witness, exact, lock, stage_errors = api._audit_stage(info, disclosure, before, power, index, frozen, raw, selector)
        prefix = 'selector' if kind == 'reference' else 'dispatch'
        if raw.lower is None or raw.upper is None or raw.objective is None:
            stage_errors.append(prefix+'_stage_missing_finite_bounds')
        else:
            lower, upper, objective = map(api._finite, (raw.lower, raw.upper, raw.objective))
            gap = upper-lower
            if (lower < 0 or upper < 0 or objective < 0 or gap < 0 or lower > objective
                    or abs(upper-objective) > min(spec.feasibility_tolerance, 1e-9)
                    or gap > selector.absolute_gap_mw or gap/max(abs(upper), 1e-12) > selector.relative_gap):
                stage_errors.append(prefix+'_stage_gap_or_objective_gate')
        accepted = not stage_errors and witness is not None and witness.physical_assignment_valid
        stage = _owned(stage_type, **stage_header,
            canonical_objective_hex=None if raw.objective is None else float(raw.objective).hex(),
            raw_solve=raw, assignment_witness=witness,
            maximum_exact_selector_violation=None if exact is None else float(exact),
            maximum_objective_lock_violation=None if lock is None else float(lock),
            accepted=accepted, errors=tuple(stage_errors))
        if _encoded(stage) != _encoded(saved_stage):
            raise ValueError('selector stage differs from source-bound exact/lock/gap replay')
        stages.append(stage)
        if not accepted:
            if index != len(saved_stages)-1:
                raise ValueError('rejected selector stage cannot have a suffix')
            errors.extend(f'{index}:{error}' for error in stage_errors)
            break
        frozen += (diagnostic.recomputed_objective,)
    reconstructed = next_state = selected = None
    if type(saved['solver_calls']) is not int or saved['solver_calls'] != calls:
        raise ValueError('selector result recorded call inventory mismatch')
    if not partial:
        if all(s.accepted for s in stages) and len(stages) != len(labels):
            raise ValueError('accepted selector prefix lacks a terminal stage')
        if len(stages) == len(labels) and all(s.accepted for s in stages):
            final = stages[-1].assignment_witness
            carry = final.physical_witness.next_carry if kind == 'reference' else final.next_carry
            final_values = dict(stages[-1].raw_solve.loaded_values)
            if carry.generation_mw != tuple((u, final_values[f'generation[{u}]']) for u in uids):
                raise ValueError('replayed final generation differs from fresh physical witness')
            if kind == 'reference':
                selected = final.candidate_grid_request_exact
                selection_id = capture._digest(api.CONTRACT, policy, identity, tuple(stages))
                next_state = _owned(reference.ReferenceGridState, contract=before.contract, protocol=before.protocol,
                    origin_identity=before.identity if type(before) is reference.ReferenceGridOrigin else before.origin_identity,
                    previous_state_identity=before.identity, selector_policy_identity=policy,
                    selection_identity=selection_id, physical_carry=carry)
            else:
                selection_id = capture._digest(api.CONTRACT, policy, identity, power, tuple(stages))
                next_state = _owned(actual.ActualDispatchState, contract=api.CONTRACT,
                    origin_identity=before.identity if type(before) is actual.ActualDispatchOrigin else before.origin_identity,
                    previous_state_identity=before.identity, selector_policy_identity=policy,
                    selection_identity=selection_id, physical_carry=carry)
        result_fields = dict(pinned, stages=tuple(stages), solver_calls=calls, errors=tuple(errors),
            status=('selected_numerical_reference' if kind == 'reference' else 'selected_numerical_dispatch')
                if next_state is not None else 'unresolved')
        if kind == 'reference':
            result_fields.update(selected_request_exact=selected, next_reference_state=next_state)
        else:
            result_fields['next_dispatch_state'] = next_state
        reconstructed = _owned(result_type, **result_fields)
        if _encoded(reconstructed) != _encoded(saved):
            raise ValueError('selector result or selected state differs from full replay')
    report = _owned(SelectorReplayDiagnostic, kind=kind, artifact_sha256=expected_sha256,
        input_identity=identity, selector_policy_identity=policy, implementation_identity=implementation,
        status='partial_native_evidence' if partial else ('reproduced_selected_chain' if next_state is not None else 'reproduced_unresolved_chain'),
        archived_outcome=saved['status'], source_input_binding_verified=True, policy_binding_verified=True,
        business_power_binding_verified=False, call_inventory_verified=True, recorded_solver_calls=calls,
        selector_chain_verified=not partial, selection_accepted=next_state is not None, archive_reproduced=not partial,
        verified_stage_count=len(stages), accepted_prefix_length=sum(s.accepted for s in stages),
        observed_stage_count=len(saved_stages), native_diagnostics=tuple(diagnostics),
        reproduced_result_identity=None if reconstructed is None else reconstructed.identity,
        selected_state_identity=None if next_state is None else next_state.identity, selected_request_exact=selected,
        solver_calls_by_replay_module=0, external_builder_accepted=False, native_execution_authenticated=False,
        exact_lexicographic_certificate=None, infeasibility_certificate=None, capacity_certificate=None,
        causal_certificate=None, formal_result=False, security_certified=False, resume_authorized=False)
    if (_input(kind, info, disclosure, before, power) != identity or api._policy_identity(selector, spec, budget) != policy
            or _implementation(spec, budget) != implementation):
        raise ValueError('selector replay source, policy or implementation changed during audit')
    return report, reconstructed


def _checked_verify(*args, **kwargs):
    try:
        return _verify(*args, **kwargs)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as exc:
        raise ValueError('invalid selector archive structure') from exc


def replay_reference_archive(data, info, disclosure, before, **expectations):
    return _checked_verify('reference', data, info, disclosure, before, None, **expectations)[0]


def replay_actual_archive(data, info, disclosure, before, power, **expectations):
    return _checked_verify('actual', data, info, disclosure, before, power, **expectations)[0]


def write_selector_archive(result, path):
    path = Path(path)
    if not path.name.endswith('_non_authoritative.json'):
        raise ValueError('explicit non_authoritative filename required')
    data = export_selector_archive(result)
    with path.open('xb') as stream:
        stream.write(data)
    return sha256(data).hexdigest()
