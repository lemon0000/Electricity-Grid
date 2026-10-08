"""Mixed native-prefix/analytic-zero-face selector; development successor.

Keeps full UID order and worst-case reservation. No process or formal authority.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from . import scale_selector as legacy, selector_zero_face as analytic

reference, actual, native = legacy.reference, legacy.actual, legacy.native
_digest, _owned, _Owned = legacy._digest, legacy._owned, legacy._Owned
_module, _admit, model_scale = legacy._module, legacy._admit, legacy.model_scale
_audit = legacy._audit
CONTRACT = 'draft_mixed_zero_face_scale_selector_v1'

@dataclass(frozen=True, init=False)
class MixedSelectionResult(legacy.ScaleSelectionResult):
    pass


def policy_identity(selector, spec, budget):
    return _digest(CONTRACT, sha256(Path(__file__).read_bytes()).hexdigest(),
                   analytic.implementation_identity(), legacy.policy_identity(selector, spec, budget))


def initialize_actual_origin(info, disclosure, *, grid_protocol, generation_mw, base_availability,
                             selector, solver_specification, budget, expected_policy_identity):
    actual._hash(expected_policy_identity)
    module = _admit(selector, solver_specification, budget, len(info.network.units)+1)
    if module is not actual or policy_identity(selector, solver_specification, budget) != expected_policy_identity:
        raise ValueError('declared actual policy identity required')
    physical = actual.initialize_actual_carry(info, disclosure, protocol=grid_protocol,
        generation_mw=generation_mw, base_availability=base_availability, evidence_role='mechanism_assumption')
    return _owned(actual.ActualDispatchOrigin, contract=actual.CONTRACT,
                  selector_policy_identity=expected_policy_identity, physical_origin=physical)


def _select_hour(info, disclosure, before, *, expected_identity, selector, solver_specification,
                budget, expected_policy_identity, power=None, _executor=None):
    """Own one complete numerical selection; incomplete evidence never yields state.

    This synchronous kernel has no wall/commit kill mechanism or durable journal.
    It requires a separately supervised caller before real-scale execution.
    """
    if _executor is None:
        raise ValueError('owned native executor required')
    module = _module(budget)
    is_reference = module is reference
    if is_reference and power is not None or not is_reference and power is None:
        raise ValueError('prescribed power is required only for actual dispatch')
    uids = tuple(g.uid for g in info.network.units)
    if not uids or uids != tuple(sorted(set(uids))) or uids != budget.generator_uids:
        raise ValueError('complete sorted unique UID inventory required')
    labels = (('grid_request', 'l1_normal_deviation') if is_reference else ('l1_normal_deviation',))
    labels += tuple('generation:'+uid for uid in uids)
    spec = solver_specification
    _admit(selector, spec, budget, len(labels))
    actual._hash(expected_identity)
    actual._hash(expected_policy_identity)
    args = (info, disclosure, before) if is_reference else (info, disclosure, before, power)
    identity = reference.reference_input_identity if is_reference else actual.dispatch_input_identity
    policy = policy_identity(selector, spec, budget)
    if identity(*args) != expected_identity or policy != expected_policy_identity:
        raise ValueError('external selector input or policy identity mismatch')
    if hasattr(before, 'selector_policy_identity') and before.selector_policy_identity != policy:
        raise ValueError('selector policy changed within trajectory')
    # source_hour is checked against the actual physical current-hour declaration.
    if info.current.source_hour != budget.source_hour:
        raise ValueError('current source hour differs from reservation')
    def builder(index, frozen):
        if is_reference:
            return reference._stage_model(*args, expected_identity, index, frozen)
        return actual._stage_model(*args, index, frozen)
    largest = builder(len(labels)-1, (0.,)*(len(labels)-1))
    scale = model_scale(largest)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('complete selector exceeds declared model scale')
    stages, frozen, errors, calls, unknown = [], (), [], 0, False
    for index, label in enumerate(labels):
        try:
            if identity(*args) != expected_identity or policy_identity(selector, spec, budget) != policy:
                errors.append(f'{index}:pre_stage_input_or_policy_drift')
                break
        except BaseException as error:
            errors.append(f'{index}:pre_stage_identity_unresolved:{type(error).__name__}')
            break
        if index == (2 if is_reference else 1) and frozen[-1] == 0:
            previous_values = tuple(stages[-1].raw_solve.loaded_values)
            previous_map = dict(previous_values)
            exact_zero = all(analytic.Q(str(previous_map[f'selector_deviation[{uid}]'])) == 0
                and analytic.Q(str(previous_map[f'generation[{uid}]'])) == analytic.Q(str(planned))
                for uid, planned in info.normal.generation_mw)
            if exact_zero:
                try:
                    suffix = analytic.certify_suffix(info, disclosure, before, power=power,
                        budget=budget, selector=selector, specification=spec,
                        expected_identity=expected_identity, policy_identity=policy, frozen=frozen,
                        assignment=previous_values, expected_implementation=analytic.implementation_identity())
                    if identity(*args) != expected_identity or policy_identity(selector, spec, budget) != policy:
                        raise ValueError('analytic input or policy drift')
                    stages.extend(suffix)
                except Exception as error:
                    errors.append('analytic_suffix_unresolved:'+type(error).__name__)
                break
        try:
            raw = _executor(lambda: builder(index, frozen), spec, budget, f'{module.PURPOSE}:{index}:{label}')
        except BaseException as error:
            unknown = True
            errors.append(f'{index}:native_pipeline_unresolved:{type(error).__name__}')
            break
        if type(raw) is not native.GridSolveEvidence or type(raw.calls) is not int or raw.calls not in (0, 1):
            unknown = True
            errors.append(f'{index}:invalid_native_call_evidence')
            break
        calls += raw.calls
        audit_args = (*args, expected_identity) if is_reference else args
        witness, exact, lock, failures = _audit(module, audit_args, index, frozen, raw, selector, spec)
        try:
            if identity(*args) != expected_identity or policy_identity(selector, spec, budget) != policy:
                failures.append('selector_input_or_policy_drift')
        except BaseException as error:
            failures.append('selector_identity_check_unresolved:'+type(error).__name__)
        accepted = not failures and witness is not None and witness.physical_assignment_valid
        cls = reference.ReferenceSelectionStage if is_reference else actual.ActualDispatchStage
        stages.append(_owned(cls, index=index, objective_label=label,
            fixed_previous_objectives=frozen, fixed_previous_objective_hex=tuple(float(x).hex() for x in frozen),
            canonical_objective_hex=None if raw.objective is None else float(raw.objective).hex(),
            raw_solve=raw, assignment_witness=witness,
            maximum_exact_selector_violation=None if exact is None else float(exact),
            maximum_objective_lock_violation=None if lock is None else float(lock),
            accepted=accepted, errors=tuple(failures)))
        if not accepted:
            errors.extend(f'{index}:{failure}' for failure in failures)
            break
        frozen += (raw.objective,)
    next_state, selected = None, None
    if not unknown and len(stages) == len(labels) and all(stage.accepted for stage in stages):
        try:
            witness = stages[-1].assignment_witness
            carry = witness.physical_witness.next_carry if is_reference else witness.next_carry
            values = dict(stages[-1].assignment if type(stages[-1]) is analytic.AnalyticStage else stages[-1].raw_solve.loaded_values)
            if carry.generation_mw != tuple((uid, values[f'generation[{uid}]']) for uid in uids):
                raise ValueError('selected generation differs from audited carry')
            origin_cls = reference.ReferenceGridOrigin if is_reference else actual.ActualDispatchOrigin
            state_cls = reference.ReferenceGridState if is_reference else actual.ActualDispatchState
            state = dict(contract=before.contract, origin_identity=before.identity if type(before) is origin_cls else before.origin_identity,
                previous_state_identity=before.identity, selector_policy_identity=policy,
                selection_identity=_digest(CONTRACT, policy, expected_identity, power, tuple(stages)), physical_carry=carry)
            if is_reference:
                state['protocol'] = before.protocol
                selected = witness.candidate_grid_request_exact
            next_state = _owned(state_cls, **state)
        except BaseException as error:
            next_state, selected = None, None
            errors.append('finalization_unresolved:'+type(error).__name__)
    return _owned(MixedSelectionResult, contract=CONTRACT, input_identity=expected_identity,
        policy_identity=policy, budget=budget, selector=selector, specification=spec, stages=tuple(stages),
        completed_solver_calls=calls, solver_calls=None if unknown else calls, planned_solver_calls=len(labels),
        next_state=next_state, selected_request_exact=selected, status='selected' if next_state is not None else 'unresolved',
        errors=tuple(errors), durable_invocation_tracking=False, hard_resource_limits_enforced=False,
        formal_result=False, security_certified=False)


def select_hour(info, disclosure, before, *, expected_identity, selector, solver_specification,
                budget, expected_policy_identity, power=None):
    return _select_hour(info, disclosure, before, expected_identity=expected_identity,
        selector=selector, solver_specification=solver_specification, budget=budget,
        expected_policy_identity=expected_policy_identity, power=power, _executor=native._solve)
