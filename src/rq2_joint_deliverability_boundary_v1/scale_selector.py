"""Full-UID numerical selector kernel; no process supervision or formal authority."""
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path

from . import reference_selector as reference, actual_dispatch_selector as actual
from . import continuous_grid_candidate as native
from . import execution_resource_contract, execution_workload
from .continuous_grid_normal import _digest
from .current_grid_step import _owned, _Owned
from ..solvers.rq2_solver_adapter import Rq2SolverSpec, solver_spec, model_scale

CONTRACT = 'draft_full_uid_scale_selector_v1'


def _resource_implementation():
    return tuple((module.__name__, sha256(Path(module.__file__).read_bytes()).hexdigest())
                 for module in (execution_resource_contract, execution_workload))


@dataclass(frozen=True)
class ScaleSelectorBudget:
    resource_contract_identity: str
    task_id: str
    source_hour: int
    role: str
    generator_uids: tuple[str, ...]
    max_seconds_per_solve: int
    max_threads: int
    max_variables: int
    max_constraints: int
    max_solver_calls: int
    max_total_solver_seconds: int

    def __post_init__(self):
        actual._hash(self.resource_contract_identity)
        if type(self.task_id) is not str or not self.task_id.strip():
            raise ValueError('explicit episode task required')
        if type(self.source_hour) is not int or self.source_hour < 0:
            raise ValueError('explicit source hour required')
        if self.role not in ('reference', 'actual:0', 'actual:1', 'actual:2', 'actual:3'):
            raise ValueError('explicit reference or canonical arm role required')
        uids = self.generator_uids
        if (type(uids) is not tuple or not uids or any(type(x) is not str or not x for x in uids)
                or uids != tuple(sorted(set(uids)))):
            raise ValueError('complete declared sorted UID inventory required')
        for name in ('max_seconds_per_solve', 'max_threads', 'max_variables',
                     'max_constraints', 'max_solver_calls', 'max_total_solver_seconds'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError('positive declared scale budget required: '+name)


def budget_for_hour(normals, episodes, envelopes, resource_budget, *, task_id, source_hour, role):
    from .execution_resource_contract import check_resource_contract
    report = check_resource_contract(normals, episodes, envelopes, resource_budget)
    if not report['declaration_consistent']:
        raise ValueError('inconsistent resource declaration')
    episode = next((task for task in episodes if task.task_id == task_id), None)
    if episode is None or type(source_hour) is not int or source_hour not in episode.source_hours:
        raise ValueError('declared episode and source hour required')
    if role not in ('reference', 'actual:0', 'actual:1', 'actual:2', 'actual:3'):
        raise ValueError('explicit selector role required')
    envelope = next(item for item in envelopes if item.task_id == task_id)
    reference_role = role == 'reference'
    seconds = episode.reference_seconds if reference_role else episode.actual_seconds[int(role[-1])]
    count = len(episode.generator_uids)+(2 if reference_role else 1)
    return ScaleSelectorBudget(_digest(report, _resource_implementation()), task_id, source_hour, role, episode.generator_uids, seconds,
        envelope.max_threads, envelope.max_variables, envelope.max_constraints, count, count*seconds)


@dataclass(frozen=True, init=False)
class ScaleSelectionResult(_Owned):
    contract: str
    input_identity: str
    policy_identity: str
    budget: ScaleSelectorBudget
    selector: object
    specification: Rq2SolverSpec
    stages: tuple
    completed_solver_calls: int
    solver_calls: int | None
    planned_solver_calls: int
    next_state: object
    selected_request_exact: tuple | None
    status: str
    errors: tuple
    durable_invocation_tracking: bool
    hard_resource_limits_enforced: bool
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return _digest(self)


def _module(budget):
    if type(budget) is not ScaleSelectorBudget:
        raise ValueError('independent scale selector budget required')
    budget.__post_init__()
    return reference if budget.role == 'reference' else actual


def policy_identity(selector, spec, budget):
    module = _module(budget)
    return _digest(CONTRACT, sha256(Path(__file__).read_bytes()).hexdigest(),
                   _resource_implementation(), module._policy_identity(selector, spec, replace(budget, source_hour=0)))


def _admit(selector, spec, budget, count):
    module = _module(budget)
    expected = reference.ReferenceSelectorSpec if module is reference else actual.ActualDispatchSpec
    if type(selector) is not expected or type(spec) is not Rq2SolverSpec:
        raise ValueError('typed selector and solver required')
    selector.__post_init__()
    if spec != solver_spec(asdict(spec)):
        raise ValueError('canonical solver specification required')
    if any(getattr(spec, name) > module.TOLERANCE for name in (
            'feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance')):
        raise ValueError('solver tolerance exceeds selector applicability')
    if (spec.time_limit_seconds != budget.max_seconds_per_solve
            or spec.threads > budget.max_threads or count != budget.max_solver_calls
            or count*budget.max_seconds_per_solve != budget.max_total_solver_seconds):
        raise ValueError('complete selector differs from declared stage reservation')
    return module


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


def _audit(module, args, index, frozen, raw, selector, spec):
    witness = exact = lock = None
    failures = []
    try:
        witness, exact, lock, failures = module._audit_stage(*args, index, frozen, raw, selector)
        if raw.lower is None or raw.upper is None or raw.objective is None:
            failures.append('stage_missing_finite_bounds')
        else:
            lower, upper, objective = map(actual._finite, (raw.lower, raw.upper, raw.objective))
            gap = upper-lower
            if (lower < 0 or upper < 0 or objective < 0 or gap < 0 or lower > objective
                    or abs(upper-objective) > min(spec.feasibility_tolerance, 1e-9)
                    or gap > selector.absolute_gap_mw or gap/max(abs(upper), 1e-12) > selector.relative_gap):
                failures.append('stage_gap_or_objective_gate')
    except BaseException as error:
        failures.append('stage_audit_unresolved:'+type(error).__name__)
    return witness, exact, lock, failures


def select_hour(info, disclosure, before, *, expected_identity, selector, solver_specification,
                budget, expected_policy_identity, power=None):
    """Own one complete numerical selection; incomplete evidence never yields state.

    This synchronous kernel has no wall/commit kill mechanism or durable journal.
    It requires a separately supervised caller before real-scale execution.
    """
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
        try:
            raw = native._solve(lambda: builder(index, frozen), spec, budget, f'{module.PURPOSE}:{index}:{label}')
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
            values = dict(stages[-1].raw_solve.loaded_values)
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
    return _owned(ScaleSelectionResult, contract=CONTRACT, input_identity=expected_identity,
        policy_identity=policy, budget=budget, selector=selector, specification=spec, stages=tuple(stages),
        completed_solver_calls=calls, solver_calls=None if unknown else calls, planned_solver_calls=len(labels),
        next_state=next_state, selected_request_exact=selected, status='selected' if next_state is not None else 'unresolved',
        errors=tuple(errors), durable_invocation_tracking=False, hard_resource_limits_enforced=False,
        formal_result=False, security_certified=False)
