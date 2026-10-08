"""Draft fixed-power numerical dispatch selection with an owned policy chain."""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from pyomo.environ import ConstraintList, NonNegativeReals, Var

from ..solvers.rq2_solver_adapter import Rq2SolverSpec, solver_spec, model_scale
from .continuous_grid_candidate import GridDevelopmentBudget, GridSolveEvidence, _solve, _execution_identity
from .continuous_grid_normal import _digest
from .current_grid_step import (ActualStepCarry, CurrentGridWitness, PrescribedDcPower, initialize_actual_carry,
    current_step_identity, build_current_grid_model, audit_current_grid_assignment, _finite, _owned, _Owned)


CONTRACT = 'numerical_lexicographic_fixed_power_actual_dispatch_v1'
PURPOSE = 'actual_fixed_power_numerical_lexicographic_selection'
TOLERANCE = 1e-6


def _hash(item):
    if type(item) is not str or len(item) != 64 or any(c not in '0123456789abcdef' for c in item):
        raise ValueError('canonical lowercase SHA256 dispatch identity required')


@dataclass(frozen=True)
class ActualDispatchSpec:
    rule: str
    absolute_gap_mw: float
    relative_gap: float
    lock_tolerance_mw: float
    evidence_role: str

    def __post_init__(self):
        if type(self.rule) is not str or self.rule != 'l1_normal_deviation_generation_uid_order':
            raise ValueError('explicit actual dispatch selector rule required')
        if not 0 <= _finite(self.absolute_gap_mw) <= 1e-6 or not 0 <= _finite(self.relative_gap) <= 1e-3:
            raise ValueError('explicit bounded numerical dispatch gap gates required')
        if not 0 <= _finite(self.lock_tolerance_mw) <= self.absolute_gap_mw:
            raise ValueError('explicit objective lock tolerance must not exceed absolute gap gate')
        if type(self.evidence_role) is not str or self.evidence_role != 'mechanism_assumption':
            raise ValueError('explicit numerical dispatch mechanism role required')


@dataclass(frozen=True, init=False)
class ActualDispatchOrigin(_Owned):
    contract: str
    selector_policy_identity: str
    physical_origin: ActualStepCarry

    @property
    def identity(self):
        return _digest(self)


@dataclass(frozen=True, init=False)
class ActualDispatchState(_Owned):
    contract: str
    origin_identity: str
    previous_state_identity: str
    selector_policy_identity: str
    selection_identity: str
    physical_carry: ActualStepCarry

    @property
    def identity(self):
        return _digest(self)


@dataclass(frozen=True, init=False)
class ActualDispatchStage(_Owned):
    index: int
    objective_label: str
    fixed_previous_objectives: tuple
    fixed_previous_objective_hex: tuple[str, ...]
    canonical_objective_hex: str | None
    raw_solve: GridSolveEvidence
    assignment_witness: CurrentGridWitness | None
    maximum_exact_selector_violation: float | None
    maximum_objective_lock_violation: float | None
    accepted: bool
    errors: tuple[str, ...]


@dataclass(frozen=True, init=False)
class ActualDispatchResult(_Owned):
    contract: str
    input_identity: str
    selector_policy_identity: str
    selector: ActualDispatchSpec
    specification: Rq2SolverSpec
    budget: GridDevelopmentBudget
    prescribed_power: PrescribedDcPower
    stages: tuple[ActualDispatchStage, ...]
    solver_calls: int
    planned_solver_calls: int
    next_dispatch_state: ActualDispatchState | None
    status: str
    errors: tuple[str, ...]
    exact_lexicographic_certificate: None
    causal_certificate: None
    infeasibility_certificate: None
    capacity_certificate: None
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return _digest(self)


def _contract():
    if (type(CONTRACT) is not str or CONTRACT != 'numerical_lexicographic_fixed_power_actual_dispatch_v1'
            or type(PURPOSE) is not str or PURPOSE != 'actual_fixed_power_numerical_lexicographic_selection'
            or type(TOLERANCE) is not float or TOLERANCE != 1e-6):
        raise ValueError('actual dispatch contract drift')


def initialize_dispatch_origin(info, disclosure, *, grid_protocol, generation_mw, base_availability,
                               selector, solver_specification, budget):
    _contract()
    _admit(selector, solver_specification, budget, len(info.network.units)+1)
    policy = _policy_identity(selector, solver_specification, budget)
    physical = initialize_actual_carry(info, disclosure, protocol=grid_protocol,
        generation_mw=generation_mw, base_availability=base_availability, evidence_role='mechanism_assumption')
    return _owned(ActualDispatchOrigin, contract=CONTRACT, selector_policy_identity=policy, physical_origin=physical)


def _physical(before):
    if type(before) not in (ActualDispatchOrigin, ActualDispatchState) or before.contract != CONTRACT:
        raise ValueError('owned actual dispatch origin/state required, not a raw or reference carry')
    _hash(before.selector_policy_identity)
    if type(before) is ActualDispatchOrigin:
        physical = before.physical_origin
        if physical.predecessor_identity is not None or physical.evidence_role != 'mechanism_assumption':
            raise ValueError('declared actual dispatch origin required')
    else:
        for name in ('origin_identity', 'previous_state_identity', 'selector_policy_identity', 'selection_identity'):
            _hash(getattr(before, name))
        physical = before.physical_carry
        if physical.predecessor_identity is None or physical.evidence_role != 'derived_current_network_assignment':
            raise ValueError('selected actual dispatch requires audited physical carry')
    return physical


def dispatch_input_identity(info, disclosure, before, power):
    _contract()
    physical = _physical(before)
    source = sha256(Path(__file__).read_bytes()).hexdigest()
    return _digest(CONTRACT, before, source, current_step_identity(info, disclosure, physical, power))


def _policy_identity(selector, spec, budget):
    _contract()
    root = Path(__file__).resolve().parent
    sources = tuple((name, sha256((root/name).read_bytes()).hexdigest()) for name in
        ('actual_dispatch_selector.py', 'current_grid_step.py', 'grid_information.py', 'event_disclosure.py'))
    return _digest(CONTRACT, PURPOSE, TOLERANCE, selector, _execution_identity(spec, budget), sources)


def _admit(selector, spec, budget, count):
    _contract()
    if type(selector) is not ActualDispatchSpec or type(spec) is not Rq2SolverSpec or type(budget) is not GridDevelopmentBudget:
        raise ValueError('typed dispatch selector, solver and shared development budget required')
    selector.__post_init__()
    budget.__post_init__()
    if budget.purpose != PURPOSE or spec != solver_spec(asdict(spec)):
        raise ValueError('canonical solver and explicit actual dispatch budget purpose required')
    if any(getattr(spec, name) > TOLERANCE for name in
            ('feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance')):
        raise ValueError('solver tolerance exceeds actual dispatch applicability')
    if (spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_seconds_per_solve
            or spec.threads > budget.max_threads or count > budget.max_solver_calls
            or count*spec.time_limit_seconds > budget.max_total_solver_seconds):
        raise ValueError('complete actual dispatch exceeds shared short budget')


def _stage_model(info, disclosure, before, power, index, frozen):
    physical = _physical(before)
    model = build_current_grid_model(info, disclosure, physical, power,
        expected_identity=current_step_identity(info, disclosure, physical, power))
    model.selector_deviation = Var(model.GEN, domain=NonNegativeReals)
    model.selector_constraints = ConstraintList()
    for uid, planned in info.normal.generation_mw:
        model.selector_constraints.add(model.selector_deviation[uid] >= model.generation[uid]-planned)
        model.selector_constraints.add(model.selector_deviation[uid] >= planned-model.generation[uid])
    objectives = (sum(model.selector_deviation[uid] for uid in model.GEN), *(model.generation[uid] for uid in model.GEN))
    model.selector_fixed = ConstraintList()
    for expression, fixed in zip(objectives, frozen):
        model.selector_fixed.add(expression == fixed)
    model.objective.set_value(objectives[index])
    return model


def _audit_stage(info, disclosure, before, power, index, frozen, raw, selector):
    errors = list(raw.errors)
    witness = exact = lock = None
    if not raw.optimal or raw.solution_count != 1 or raw.calls != 1 or not raw.assignment_valid:
        errors.append('dispatch_stage_requires_owned_optimal_assignment')
    if raw.loaded_values:
        try:
            values = dict(raw.loaded_values)
            assignment = {name: number for name, number in values.items() if not name.startswith('selector_deviation[')}
            physical = _physical(before)
            witness = audit_current_grid_assignment(info, disclosure, physical, power, assignment,
                expected_identity=current_step_identity(info, disclosure, physical, power))
            errors.extend(witness.errors)
            exact = Q(0)
            deviations, actual_deviations = [], []
            for uid, plan in info.normal.generation_mw:
                d = Q(str(values[f'selector_deviation[{uid}]']))
                actual = abs(Q(str(values[f'generation[{uid}]']))-Q(str(plan)))
                deviations.append(d)
                actual_deviations.append(actual)
                exact = max(exact, -d, actual-d)
            actual_l1 = sum(actual_deviations, Q(0))
            objectives = (actual_l1, *(Q(str(values[f'generation[{g.uid}]'])) for g in info.network.units))
            lock = abs(sum(deviations, Q(0))-actual_l1)
            for prior, fixed in zip(objectives, frozen):
                lock = max(lock, abs(prior-Q(str(fixed))))
            if raw.objective is not None:
                lock = max(lock, abs(objectives[index]-Q(str(raw.objective))))
            if exact > Q('1e-6') or lock > Q(str(selector.lock_tolerance_mw)):
                errors.append('dispatch_exact_lock_or_deviation_violation')
            exact = max(exact, lock)
        except (ValueError, KeyError, OverflowError) as error:
            errors.append(f'dispatch_projection_audit:{type(error).__name__}:{error}')
    else:
        errors.append('dispatch_stage_missing_loaded_assignment')
    return witness, exact, lock, errors


def select_actual_dispatch(info, disclosure, before, power, *, expected_identity, selector, solver_specification, budget):
    _hash(expected_identity)
    if dispatch_input_identity(info, disclosure, before, power) != expected_identity:
        raise ValueError('actual dispatch input identity mismatch')
    uids = tuple(g.uid for g in info.network.units)
    if uids != tuple(sorted(set(uids))):
        raise ValueError('sorted unique complete generator inventory required')
    labels = ('l1_normal_deviation', *(f'generation:{uid}' for uid in uids))
    spec = solver_specification
    _admit(selector, spec, budget, len(labels))
    policy = _policy_identity(selector, spec, budget)
    if before.selector_policy_identity != policy:
        raise ValueError('actual dispatch policy changed within a trajectory')
    largest = _stage_model(info, disclosure, before, power, len(labels)-1, (0.,)*(len(labels)-1))
    scale = model_scale(largest)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('complete actual dispatch exceeds shared development scale')
    stages, frozen, errors = [], (), []
    calls = 0
    for index, label in enumerate(labels):
        builder = lambda: _stage_model(info, disclosure, before, power, index, frozen)
        raw = _solve(builder, spec, budget, f'{PURPOSE}:{index}:{label}')
        calls += raw.calls
        if raw.calls not in (0, 1) or calls > budget.max_solver_calls:
            raise ValueError('actual dispatch solver call budget exceeded')
        witness, exact, lock, stage_errors = _audit_stage(info, disclosure, before, power, index, frozen, raw, selector)
        if raw.lower is None or raw.upper is None or raw.objective is None:
            stage_errors.append('dispatch_stage_missing_finite_bounds')
        else:
            lower, upper, objective = map(_finite, (raw.lower, raw.upper, raw.objective))
            gap = upper-lower
            if (lower < 0 or upper < 0 or objective < 0 or gap < 0 or lower > objective
                    or abs(upper-objective) > min(spec.feasibility_tolerance, 1e-9)
                    or gap > selector.absolute_gap_mw or gap/max(abs(upper), 1e-12) > selector.relative_gap):
                stage_errors.append('dispatch_stage_gap_or_objective_gate')
        if (dispatch_input_identity(info, disclosure, before, power) != expected_identity
                or _policy_identity(selector, spec, budget) != policy):
            raise ValueError('actual dispatch input or execution identity drifted')
        accepted = not stage_errors and witness is not None and witness.physical_assignment_valid
        stages.append(_owned(ActualDispatchStage, index=index, objective_label=label,
            fixed_previous_objectives=frozen, fixed_previous_objective_hex=tuple(float(x).hex() for x in frozen),
            canonical_objective_hex=None if raw.objective is None else float(raw.objective).hex(),
            raw_solve=raw, assignment_witness=witness,
            maximum_exact_selector_violation=None if exact is None else float(exact),
            maximum_objective_lock_violation=None if lock is None else float(lock),
            accepted=accepted, errors=tuple(stage_errors)))
        if not accepted:
            errors.extend(f'{index}:{error}' for error in stage_errors)
            break
        frozen += (raw.objective,)
    next_state = None
    if len(stages) == len(labels) and all(s.accepted for s in stages):
        final = stages[-1].assignment_witness
        final_values = dict(stages[-1].raw_solve.loaded_values)
        if final.next_carry.generation_mw != tuple((uid, final_values[f'generation[{uid}]']) for uid in uids):
            raise ValueError('selected actual generation differs from audited carry')
        selection = _digest(CONTRACT, policy, expected_identity, power, tuple(stages))
        next_state = _owned(ActualDispatchState, contract=CONTRACT,
            origin_identity=before.identity if type(before) is ActualDispatchOrigin else before.origin_identity,
            previous_state_identity=before.identity, selector_policy_identity=policy, selection_identity=selection,
            physical_carry=final.next_carry)
    return _owned(ActualDispatchResult, contract=CONTRACT, input_identity=expected_identity,
        selector_policy_identity=policy, selector=selector, specification=spec, budget=budget,
        prescribed_power=power, stages=tuple(stages), solver_calls=calls, planned_solver_calls=len(labels), next_dispatch_state=next_state,
        status='selected_numerical_dispatch' if next_state is not None else 'unresolved', errors=tuple(errors),
        exact_lexicographic_certificate=None, causal_certificate=None, infeasibility_certificate=None,
        capacity_certificate=None, formal_result=False, security_certified=False)
