"""Budgeted numerical lexicographic reference selection, not exact optimality."""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from pyomo.environ import ConstraintList, NonNegativeReals, Var

from ..solvers.rq2_solver_adapter import Rq2SolverSpec, solver_spec, model_scale
from .continuous_grid_candidate import GridDevelopmentBudget, GridSolveEvidence, _solve, _execution_identity
from .continuous_grid_normal import _digest
from .current_grid_step import _finite, _owned, _Owned
from .reference_grid import (ReferenceGridOrigin, ReferenceGridState, ReferenceAssignmentWitness,
    reference_input_identity, build_reference_grid_model, audit_reference_assignment)


CONTRACT = 'numerical_lexicographic_common_reference_selector_v1'
PURPOSE = 'common_reference_numerical_lexicographic_selection'
TOLERANCE = 1e-6


@dataclass(frozen=True)
class ReferenceSelectorSpec:
    rule: str
    absolute_gap_mw: float
    relative_gap: float
    lock_tolerance_mw: float
    evidence_role: str

    def __post_init__(self):
        if type(self.rule) is not str or self.rule != 'request_l1_normal_deviation_generation_uid_order':
            raise ValueError('explicit reference selector rule required')
        if not 0 <= _finite(self.absolute_gap_mw) <= 1e-6 or not 0 <= _finite(self.relative_gap) <= 1e-3:
            raise ValueError('explicit bounded numerical selector gap gates required')
        if not 0 <= _finite(self.lock_tolerance_mw) <= self.absolute_gap_mw:
            raise ValueError('explicit objective lock tolerance must not exceed absolute gap gate')
        if type(self.evidence_role) is not str or self.evidence_role != 'mechanism_assumption':
            raise ValueError('explicit numerical selector mechanism role required')


@dataclass(frozen=True, init=False)
class ReferenceSelectionStage(_Owned):
    index: int
    objective_label: str
    fixed_previous_objectives: tuple
    fixed_previous_objective_hex: tuple[str, ...]
    canonical_objective_hex: str | None
    raw_solve: GridSolveEvidence
    assignment_witness: ReferenceAssignmentWitness | None
    maximum_exact_selector_violation: float | None
    maximum_objective_lock_violation: float | None
    accepted: bool
    errors: tuple[str, ...]


@dataclass(frozen=True, init=False)
class ReferenceSelectionResult(_Owned):
    contract: str
    input_identity: str
    selector_policy_identity: str
    selector: ReferenceSelectorSpec
    specification: Rq2SolverSpec
    budget: GridDevelopmentBudget
    stages: tuple[ReferenceSelectionStage, ...]
    solver_calls: int
    planned_solver_calls: int
    selected_request_exact: tuple[str, str] | None
    next_reference_state: ReferenceGridState | None
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
    if (type(CONTRACT) is not str or CONTRACT != 'numerical_lexicographic_common_reference_selector_v1'
            or type(PURPOSE) is not str or PURPOSE != 'common_reference_numerical_lexicographic_selection'
            or type(TOLERANCE) is not float or TOLERANCE != 1e-6):
        raise ValueError('reference selector contract drift')


def _policy_identity(selector, spec, budget):
    _contract()
    root = Path(__file__).resolve().parent
    sources = tuple((name, sha256((root/name).read_bytes()).hexdigest()) for name in
        ('reference_selector.py', 'reference_grid.py', 'current_grid_step.py', 'grid_information.py', 'event_disclosure.py'))
    return _digest(CONTRACT, PURPOSE, TOLERANCE, selector, _execution_identity(spec, budget), sources)


def _admit(selector, spec, budget, count):
    _contract()
    if type(selector) is not ReferenceSelectorSpec or type(spec) is not Rq2SolverSpec or type(budget) is not GridDevelopmentBudget:
        raise ValueError('typed selector, solver and shared development budget required')
    selector.__post_init__()
    budget.__post_init__()
    if budget.purpose != PURPOSE or spec != solver_spec(asdict(spec)):
        raise ValueError('canonical solver and explicit selector budget purpose required')
    if any(getattr(spec, name) > TOLERANCE for name in
            ('feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance')):
        raise ValueError('solver tolerance exceeds selector applicability')
    if (spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_seconds_per_solve
            or spec.threads > budget.max_threads or count > budget.max_solver_calls
            or count*spec.time_limit_seconds > budget.max_total_solver_seconds):
        raise ValueError('complete selector exceeds shared short budget')


def _stage_model(info, disclosure, before, expected_identity, index, frozen):
    model = build_reference_grid_model(info, disclosure, before, expected_identity=expected_identity)
    model.selector_deviation = Var(model.GEN, domain=NonNegativeReals)
    model.selector_constraints = ConstraintList()
    for uid, planned in info.normal.generation_mw:
        model.selector_constraints.add(model.selector_deviation[uid] >= model.generation[uid]-planned)
        model.selector_constraints.add(model.selector_deviation[uid] >= planned-model.generation[uid])
    objectives = (info.current.dc_baseline_mw-model.reference_power,
        sum(model.selector_deviation[uid] for uid in model.GEN), *(model.generation[uid] for uid in model.GEN))
    model.selector_fixed = ConstraintList()
    for expression, fixed in zip(objectives, frozen):
        model.selector_fixed.add(expression == fixed)
    model.objective.set_value(objectives[index])
    return model


def _audit_stage(info, disclosure, before, expected_identity, index, frozen, raw, selector):
    errors = list(raw.errors)
    witness = None
    exact = None
    lock = None
    if not raw.optimal or raw.solution_count != 1 or raw.calls != 1 or not raw.assignment_valid:
        errors.append('selector_stage_requires_owned_optimal_assignment')
    if raw.loaded_values:
        try:
            values = dict(raw.loaded_values)
            physical = {name: number for name, number in values.items() if not name.startswith('selector_deviation[')}
            witness = audit_reference_assignment(info, disclosure, before, physical, expected_identity=expected_identity)
            errors.extend(witness.errors)
            exact = Q(0)
            deviations = []
            actual_deviations = []
            for uid, plan in info.normal.generation_mw:
                d = Q(str(values[f'selector_deviation[{uid}]']))
                actual = abs(Q(str(values[f'generation[{uid}]']))-Q(str(plan)))
                deviations.append(d)
                actual_deviations.append(actual)
                exact = max(exact, -d, actual-d)
            objectives = (Q(str(info.current.dc_baseline_mw))-Q(str(values['reference_power'])),
                sum(actual_deviations, Q(0)), *(Q(str(values[f'generation[{g.uid}]'])) for g in info.network.units))
            lock = Q(0)
            for prior, fixed in zip(objectives, frozen):
                lock = max(lock, abs(prior-Q(str(fixed))))
            if index >= 1:
                lock = max(lock, abs(sum(deviations, Q(0))-sum(actual_deviations, Q(0))))
            if raw.objective is not None:
                lock = max(lock, abs(objectives[index]-Q(str(raw.objective))))
            if exact > Q('1e-6') or lock > Q(str(selector.lock_tolerance_mw)):
                errors.append('selector_exact_lock_or_deviation_violation')
            exact = max(exact, lock)
        except (ValueError, KeyError, OverflowError) as error:
            errors.append(f'selector_projection_audit:{type(error).__name__}:{error}')
    else:
        errors.append('selector_stage_missing_loaded_assignment')
    return witness, exact, lock, errors


def select_reference_hour(info, disclosure, before, *, expected_identity, selector, solver_specification, budget):
    if (type(expected_identity) is not str or len(expected_identity) != 64
            or any(c not in '0123456789abcdef' for c in expected_identity)):
        raise ValueError('canonical lowercase SHA256 reference identity required')
    if reference_input_identity(info, disclosure, before) != expected_identity:
        raise ValueError('reference selector input identity mismatch')
    labels = ('grid_request', 'l1_normal_deviation', *(f'generation:{g.uid}' for g in info.network.units))
    uids = tuple(g.uid for g in info.network.units)
    if uids != tuple(sorted(set(uids))):
        raise ValueError('sorted unique complete generator inventory required')
    spec = solver_specification
    _admit(selector, spec, budget, len(labels))
    policy = _policy_identity(selector, spec, budget)
    if type(before) is ReferenceGridState and before.selector_policy_identity != policy:
        raise ValueError('reference selector policy changed within a trajectory')
    # The final stage has the largest row inventory. Check its scale before any
    # native call; placeholder locks are used only for counting, never solving.
    largest = _stage_model(info, disclosure, before, expected_identity, len(labels)-1, (0.,)*(len(labels)-1))
    scale = model_scale(largest)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('complete selector exceeds shared development scale')
    stages, frozen, errors = [], (), []
    calls = 0
    for index, label in enumerate(labels):
        builder = lambda: _stage_model(info, disclosure, before, expected_identity, index, frozen)
        raw = _solve(builder, spec, budget, f'{PURPOSE}:{index}:{label}')
        calls += raw.calls
        if raw.calls not in (0, 1) or calls > budget.max_solver_calls:
            raise ValueError('reference selector solver call budget exceeded')
        witness, exact, lock, stage_errors = _audit_stage(info, disclosure, before, expected_identity, index, frozen, raw, selector)
        if raw.lower is None or raw.upper is None or raw.objective is None:
            stage_errors.append('selector_stage_missing_finite_bounds')
        else:
            lower, upper, objective = map(_finite, (raw.lower, raw.upper, raw.objective))
            gap = upper-lower
            if (lower < 0 or upper < 0 or objective < 0 or gap < 0 or lower > objective
                    or abs(upper-objective) > min(spec.feasibility_tolerance, 1e-9)
                    or gap > selector.absolute_gap_mw or gap/max(abs(upper), 1e-12) > selector.relative_gap):
                stage_errors.append('selector_stage_gap_or_objective_gate')
        if (reference_input_identity(info, disclosure, before) != expected_identity
                or _policy_identity(selector, spec, budget) != policy):
            raise ValueError('reference selector input or execution identity drifted')
        accepted = not stage_errors and witness is not None and witness.physical_assignment_valid
        stages.append(_owned(ReferenceSelectionStage, index=index, objective_label=label,
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
    selected = None
    next_state = None
    if len(stages) == len(labels) and all(s.accepted for s in stages):
        final = stages[-1].assignment_witness
        final_values = dict(stages[-1].raw_solve.loaded_values)
        if final.physical_witness.next_carry.generation_mw != tuple((uid, final_values[f'generation[{uid}]']) for uid in uids):
            raise ValueError('selected reference generation differs from audited carry')
        selected = final.candidate_grid_request_exact
        selection = _digest(CONTRACT, policy, expected_identity, tuple(stages))
        next_state = _owned(ReferenceGridState, contract=before.contract, protocol=before.protocol,
            origin_identity=before.identity if type(before) is ReferenceGridOrigin else before.origin_identity,
            previous_state_identity=before.identity, selector_policy_identity=policy, selection_identity=selection,
            physical_carry=final.physical_witness.next_carry)
    return _owned(ReferenceSelectionResult, contract=CONTRACT, input_identity=expected_identity,
        selector_policy_identity=policy, selector=selector, specification=spec, budget=budget,
        stages=tuple(stages), solver_calls=calls, planned_solver_calls=len(labels),
        selected_request_exact=selected, next_reference_state=next_state,
        status='selected_numerical_reference' if next_state is not None else 'unresolved', errors=tuple(errors),
        exact_lexicographic_certificate=None, causal_certificate=None, infeasibility_certificate=None,
        capacity_certificate=None, formal_result=False, security_certified=False)
