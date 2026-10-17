"""Owned short normal/corrective development execution; no formal publication.

Corrective LPs are independent hourly responses to an event-blind normal plan.
Their assignments do not establish cross-hour outage-state feasibility.
"""
from dataclasses import asdict, dataclass, fields
from importlib.metadata import version
from math import isfinite
from pathlib import Path
from hashlib import sha256

from pyomo.environ import Constraint, Objective, Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense
from pyomo.repn import generate_standard_repn
from pyomo.core.expr.visitor import identify_variables

from ..grid.rts_gmlc_grid_need_successor import _build_corrective_model
from ..grid.rts_gmlc_scuc import _constraint_violation, _integrality_violation
from ..scenarios.rts_gmlc_n1_chronology import N1OutageEvent, event_by_hour
from ..solvers.rq2_solver_adapter import Rq2SolverSpec, solver_spec, solver_options, create_solver, model_scale
from .continuous_grid_normal import (
    TOLERANCE, ContinuousNormalInputs, NormalAssignmentWitness, normal_input_identity,
    build_continuous_normal_model, audit_normal_assignment, _digest, _dependencies,
)

CONTRACT = 'continuous_normal_then_independent_hourly_corrective_short_candidate_v1'
EXTRA_DEPENDENCIES = ('src/grid/rts_gmlc_grid_need.py', 'src/grid/rts_gmlc_grid_need_successor.py',
    'src/scenarios/rts_gmlc_n1_chronology.py', 'src/solvers/rq2_solver_adapter.py',
    'src/rq2_joint_deliverability_boundary_v1/continuous_grid_candidate.py')


@dataclass(frozen=True)
class GridDevelopmentBudget:
    purpose: str
    max_seconds_per_solve: float
    max_threads: int
    max_horizon: int
    max_variables: int
    max_constraints: int
    max_solver_calls: int
    max_total_solver_seconds: float

    def __post_init__(self):
        if type(self.purpose) is not str or not self.purpose.strip():
            raise ValueError('explicit development purpose required')
        for name, cap in (('max_seconds_per_solve', 30), ('max_total_solver_seconds', 60)):
            n = getattr(self, name)
            if type(n) not in (float, int) or not isfinite(n) or not 0 < n <= cap:
                raise ValueError('invalid short solve budget: ' + name)
        for name, cap in (('max_threads', 4), ('max_horizon', 168), ('max_variables', 20000),
                          ('max_constraints', 100000), ('max_solver_calls', 20)):
            n = getattr(self, name)
            if type(n) is not int or not 0 < n <= cap:
                raise ValueError('invalid short solve budget: ' + name)


def _make(cls, **items):
    result = object.__new__(cls)
    for f in fields(cls):
        object.__setattr__(result, f.name, items[f.name])
    return result


@dataclass(frozen=True, init=False)
class GridSolveEvidence:
    purpose: str
    variables: int
    constraints: int
    solver_records: tuple
    problem_records: tuple
    solution_statuses: tuple
    solution_count: int | None
    structures: tuple
    versions: tuple
    options: tuple
    initial_values: tuple
    preload_values: tuple
    native_values: tuple
    canonical_completed_values: tuple
    loaded_values: tuple
    native_objectives: tuple
    objective: float | None
    lower: float | None
    upper: float | None
    maximum_residual: float | None
    maximum_integrality_violation: float | None
    calls: int
    assignment_valid: bool
    optimal: bool
    native_infeasible: bool
    errors: tuple[str, ...]

    def __init__(self, *args, **kwargs):
        raise TypeError('solve evidence requires owned execution')


@dataclass(frozen=True)
class GridCandidateHour:
    source_hour: int
    outage_source_index: int
    timestamp: str
    baseline_generation: tuple
    baseline_commitment: tuple
    event: N1OutageEvent | None
    state: str
    grid_need_mw: float | None
    corrective: GridSolveEvidence | None
    zero_dc_confirmation: GridSolveEvidence | None


@dataclass(frozen=True, init=False)
class ContinuousGridCandidate:
    contract: str
    input_identity: str
    execution_identity: str
    event_identity: str
    event_evidence_role: str
    specification: Rq2SolverSpec
    budget: GridDevelopmentBudget
    normal: GridSolveEvidence
    normal_witness: NormalAssignmentWitness | None
    hours: tuple[GridCandidateHour, ...]
    solver_calls: int
    event_blind_normal_model: bool
    corrective_cross_hour_feasibility: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool

    def __init__(self, *args, **kwargs):
        raise TypeError('grid candidate requires owned execution')

    @property
    def finite_grid_need_trace_available(self):
        return bool(self.hours) and all(h.state == 'finite_grid_need' for h in self.hours)

    @property
    def result_id(self):
        return _digest(self)


def _number(x):
    if type(x) not in (int, float) or not isfinite(x):
        raise ValueError('finite built-in numeric value required')
    return float(x)


def _raw_number(x):
    try:
        n = _number(x)
    except (ValueError, OverflowError):
        n = None
    return (type(x).__module__ + '.' + type(x).__name__, repr(x), n)


def _enum(x):
    return (type(x).__module__ + '.' + type(x).__name__, repr(x))


def _snapshot(model):
    return tuple(sorted((v.name, _raw_number(v.value)) for v in model.component_data_objects(Var)))


def _structure(model):
    def active(component):
        while component is not None:
            if not component.active:
                return False
            component = component.parent_block()
        return True
    def number(x):
        return None if x is None else _number(value(x)).hex()
    def linear(expr):
        repn = generate_standard_repn(expr, compute_values=True)
        if not repn.is_linear():
            raise ValueError('linear canonical model required')
        return (number(repn.constant), tuple(sorted((v.name, number(c))
            for v, c in zip(repn.linear_vars, repn.linear_coefs, strict=True))))
    return _digest(model.active, tuple(sorted((v.name, str(v.domain), number(v.lb), number(v.ub),
        v.fixed, number(v.value) if v.fixed else None) for v in model.component_data_objects(Var))),
        tuple(sorted((c.name, active(c), number(c.lower), number(c.upper), linear(c.body))
            for c in model.component_data_objects(Constraint, active=None))),
        tuple(sorted((o.name, active(o), int(o.sense), linear(o.expr))
            for o in model.component_data_objects(Objective, active=None))))


def _native_values(model, native, kind, component_type):
    solution = native.solution[0]
    symbol_map = native.__dict__.get('_smap')
    if symbol_map is None and native.__dict__.get('_smap_id') is not None:
        symbol_map = model.solutions.symbol_map[native.__dict__['_smap_id']]
    components = {v.name: v for v in model.component_data_objects(component_type)}
    rows = []
    for label, entry in getattr(solution, kind).items():
        if symbol_map is not None:
            component = symbol_map.bySymbol.get(label, symbol_map.aliases.get(label))
        elif solution._cuid:
            component = label.find_component_on(model)
        else:
            component = components.get(label)
        if component is None or components.get(component.name) is not component:
            raise ValueError('unknown native variable/objective label')
        rows.append((component.name, _number(entry.get('Value'))))
    # HiGHS' legacy result omits the solution objective map. Its problem UB
    # must still match the fresh canonical objective before accepting optimality.
    if kind == 'objective' and not rows:
        return ()
    if (len({name for name, _ in rows}) != len(rows)
            or (kind != 'variable' and {name for name, _ in rows} != set(components))):
        raise ValueError('incomplete or duplicate native variable/objective inventory: '
                         + repr(sorted(set(components) - {name for name, _ in rows})))
    return tuple(sorted(rows))


def _canonical_completions(model, native_values):
    """Complete only fixed constants or unused, unbounded continuous variables.

    Never infer a missing dispatch/flow/reserve value from a solver objective.
    These values are explicitly model-derived, not native solver observations.
    """
    reported = dict(native_values)
    used = set()
    for component in model.component_data_objects(Constraint, active=True):
        for expression in (component.body, component.lower, component.upper):
            if expression is not None:
                used.update(v.name for v in identify_variables(expression, include_fixed=True))
    for component in model.component_data_objects(Objective, active=True):
        used.update(v.name for v in identify_variables(component.expr, include_fixed=True))
    completed = []
    for variable in model.component_data_objects(Var):
        if variable.name in reported:
            continue
        if variable.fixed:
            completed.append((variable.name, _number(variable.value), 'canonical_fixed_constant'))
        elif (variable.name not in used and variable.is_continuous()
                and variable.lb is None and variable.ub is None):
            completed.append((variable.name, 0., 'unused_unbounded_continuous_representative'))
        else:
            raise ValueError('missing native decision variable: ' + variable.name)
    return tuple(sorted(completed))


def _execution_identity(spec, budget):
    root = Path(__file__).resolve().parents[2]
    extra = tuple((name, sha256((root / name).read_bytes()).hexdigest()) for name in EXTRA_DEPENDENCIES)
    return _digest(CONTRACT, spec, budget, _dependencies(), extra,
                   version('gurobipy') if spec.name == 'gurobi' else version('highspy'))


def _solve(builder, spec, budget, purpose):
    """Own build/solve/load and independently rebuild the complete assignment."""
    model = builder()
    scale = model_scale(model)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('canonical model exceeds short development scale')
    before = _structure(model)
    initial = _snapshot(model)
    sr = pr = statuses = native_values = loaded = native_objectives = ()
    completed = ()
    preload = ()
    pre_structure = post_structure = None
    before_versions = after_versions = passed = returned = ()
    objective = lower = upper = residual = integer = count = None
    calls, assignment_valid, optimal, native_infeasible = 0, False, False, False
    errors, options = [], None
    status = termination = solution_status = None
    stage = 'create'
    def versions():
        return (version('Pyomo'), version('highspy' if spec.name == 'highs' else 'gurobipy'))
    try:
        before_versions = versions()
        solver, options = create_solver(spec)
        passed = tuple(sorted(options.items()))
        if passed != tuple(sorted(solver_options(spec).items())):
            raise ValueError('solver options differ from declared specification')
        stage = 'solve'
        calls = 1
        native = solver.solve(model, load_solutions=False, tee=spec.tee, options=options)
        stage = 'native_result'
        if not isinstance(native, SolverResults):
            raise ValueError('native SolverResults required')
        sr = tuple((_enum(r.status), _enum(r.termination_condition)) for r in native.solver)
        pr = tuple((_enum(r.sense), _raw_number(r.lower_bound), _raw_number(r.upper_bound),
            _raw_number(r.number_of_variables), _raw_number(r.number_of_constraints),
            _raw_number(r.number_of_objectives)) for r in native.problem)
        statuses = tuple(_enum(s.status) for s in native.solution)
        count = len(native.solution)
        if len(sr) != 1 or len(pr) != 1:
            raise ValueError('one native solver and problem record required')
        status, termination = native.solver[0].status, native.solver[0].termination_condition
        if type(status) is not SolverStatus or type(termination) is not TerminationCondition:
            raise ValueError('typed native status/termination required')
        problem = native.problem[0]
        if problem.sense is not ProblemSense.minimize or _number(problem.number_of_objectives) != 1:
            raise ValueError('one minimization objective required')
        lower, upper = pr[0][1][2], pr[0][2][2]
        pre_structure, preload = _structure(model), _snapshot(model)
        if pre_structure != before or preload != initial:
            raise ValueError('model mutated before explicit load')
        if count == 1:
            solution_status = native.solution[0].status
            if type(solution_status) is not SolutionStatus:
                raise ValueError('typed native solution status required')
            stage = 'native_inventory'
            native_values = _native_values(model, native, 'variable', Var)
            completed = _canonical_completions(model, native_values)
            native_objectives = _native_values(model, native, 'objective', Objective)
            stage = 'load'
            model.solutions.load_from(native, select=0, ignore_invalid_labels=False)
            for name, number, _reason in completed:
                model.find_component(name).set_value(number)
            loaded = tuple((name, item[2]) for name, item in _snapshot(model))
            complete_values = tuple(sorted((*native_values, *((n, x) for n, x, _ in completed))))
            if loaded != complete_values:
                raise ValueError('native and loaded values differ')
            stage = 'canonical_assignment'
            canonical = builder()
            if _structure(canonical) != before:
                raise ValueError('fresh canonical structure changed')
            values = dict(loaded)
            fixed_failed = False
            for variable in canonical.component_data_objects(Var):
                candidate = values[variable.name]
                if variable.fixed and abs(candidate - variable.value) > spec.feasibility_tolerance:
                    fixed_failed = True
                variable.set_value(candidate, skip_validation=True)
            raw_residual = _constraint_violation(canonical)
            raw_integer = _integrality_violation(canonical)
            residual = raw_residual if isfinite(raw_residual) else None
            integer = raw_integer if isfinite(raw_integer) else None
            assignment_valid = (not fixed_failed and residual is not None and integer is not None
                                and residual <= spec.feasibility_tolerance
                                and integer <= spec.integer_feasibility_tolerance)
            objective = _number(value(next(canonical.component_data_objects(Objective)).expr))
            if native_objectives and (len(native_objectives) != 1
                    or abs(native_objectives[0][1] - objective) > min(spec.feasibility_tolerance, 1e-9)):
                raise ValueError('native objective differs from canonical assignment')
            if not assignment_valid:
                errors.append('canonical_assignment_invalid')
        elif count != 0:
            errors.append('multiple_native_solutions_unresolved')
    except Exception as error:
        errors.append(f'{stage}:{type(error).__name__}:{error}')
    try:
        post_structure = _structure(model)
        after_versions = versions()
        returned = () if options is None else tuple(sorted(options.items()))
        if (before != pre_structure or before != post_structure or before_versions != after_versions
                or passed != returned or passed != tuple(sorted(solver_options(spec).items()))):
            errors.append('structure_options_or_version_drift')
    except Exception as error:
        errors.append(f'post_snapshot:{type(error).__name__}:{error}')
    if not errors:
        known_highs_infeasible_status = (spec.name == 'highs' and before_versions == ('6.10.1', '1.15.1')
            and status is SolverStatus.error and purpose.startswith(('corrective_source_', 'zero_dc_source_'))
            and all(v.is_continuous() for v in model.component_data_objects(Var)))
        native_infeasible = ((status in (SolverStatus.ok, SolverStatus.warning) or known_highs_infeasible_status)
                             and termination is TerminationCondition.infeasible and count == 0)
        corrective_bound_domain = (not hasattr(model, 'curtailment') or
            (upper is not None and 0 <= upper <= _number(value(model.curtailment.ub))))
        optimal = (status is SolverStatus.ok and termination in (TerminationCondition.optimal, TerminationCondition.globallyOptimal)
            and solution_status is SolutionStatus.optimal and assignment_valid and objective is not None
            and lower is not None and upper is not None and lower <= upper and lower <= objective
            and corrective_bound_domain
            and abs(upper - objective) <= min(spec.feasibility_tolerance, 1e-9)
            and (upper - lower) / max(abs(objective), 1e-12) <= spec.mip_relative_gap)
    return _make(GridSolveEvidence, purpose=purpose, variables=scale.variables, constraints=scale.constraints,
        solver_records=sr, problem_records=pr, solution_statuses=statuses, solution_count=count,
        structures=(before, pre_structure, post_structure), versions=(before_versions, after_versions),
        options=(passed, returned), initial_values=initial, preload_values=preload, native_values=native_values,
        canonical_completed_values=completed,
        loaded_values=loaded, native_objectives=native_objectives, objective=objective, lower=lower, upper=upper,
        maximum_residual=residual, maximum_integrality_violation=integer, calls=calls,
        assignment_valid=assignment_valid and not errors, optimal=optimal, native_infeasible=native_infeasible,
        errors=tuple(errors))


def _admit(inputs, events, role, spec, budget):
    if type(inputs) is not ContinuousNormalInputs or type(budget) is not GridDevelopmentBudget:
        raise ValueError('typed inputs and development budget required')
    budget.__post_init__()
    if type(spec) is not Rq2SolverSpec:
        raise ValueError('explicit solver specification required')
    canonical_spec = solver_spec(asdict(spec))
    if spec != canonical_spec:
        raise ValueError('canonical solver specification required')
    if any(getattr(spec, field) > TOLERANCE for field in
           ('feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance')):
        raise ValueError('solver tolerances exceed development applicability')
    if (spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_seconds_per_solve
            or spec.threads > budget.max_threads or len(inputs.source_hours) > budget.max_horizon):
        raise ValueError('solver/horizon exceeds development budget')
    if type(role) is not str or role != 'mechanism_assumption':
        raise ValueError('outages require explicit mechanism_assumption role')
    if type(events) is not tuple or any(type(e) is not N1OutageEvent for e in events):
        raise ValueError('immutable typed original event table required')
    if len({e.event_id for e in events}) != len(events):
        raise ValueError('duplicate event ID')
    for e in events:
        if (type(e.seed) is not int or e.seed != inputs.carry.identity.outage_seed
                or type(e.event_id) is not str or not e.event_id.strip()
                or type(e.uid) is not str or not e.uid.strip()
                or type(e.start_hour) is not int or type(e.end_hour_exclusive) is not int):
            raise ValueError('event seed/identity/integer interval mismatch')
        inventory = {b.uid for b in inputs.data.branches} if e.component_type == 'branch' else (
            {g.uid for g in inputs.data.generators if g.enabled} if e.component_type == 'generator' else set())
        if e.uid not in inventory:
            raise ValueError('unknown or disabled outage component')
    timeline = event_by_hour(events, horizon_hours=len(inputs.data.hourly_points))
    selected = tuple(timeline[h - 1] for h in inputs.source_hours)
    worst_calls = 1 + 2 * sum(e is not None for e in selected)
    if (worst_calls > budget.max_solver_calls
            or worst_calls * spec.time_limit_seconds > budget.max_total_solver_seconds):
        raise ValueError('worst-case corrective confirmations exceed development budget')
    return selected


def run_short_grid_candidate(inputs, *, expected_identity, events, event_evidence_role,
                             solver_specification, budget):
    """Validate events, solve an event-blind normal model, then attach responses.

    The normal builder accepts neither the selected events nor their schedule.
    No retry; the distinct zero-DC LP runs only after native primary infeasibility.
    """
    selected = _admit(inputs, events, event_evidence_role, solver_specification, budget)
    execution_id = _execution_identity(solver_specification, budget)
    event_id = _digest(events, event_evidence_role, inputs.carry.identity)
    builder = lambda: build_continuous_normal_model(inputs, expected_identity=expected_identity)
    normal = _solve(builder, solver_specification, budget, 'event_blind_normal')
    witness = None
    if normal.assignment_valid:
        witness = audit_normal_assignment(inputs, dict(normal.loaded_values), expected_identity=expected_identity)
    eligible = normal.optimal and witness is not None and not witness.errors
    normal_values = dict(normal.loaded_values)
    rows, calls = [], normal.calls
    for t, (source_hour, event) in enumerate(zip(inputs.source_hours, selected, strict=True)):
        generation = commitment = ()
        if witness is not None and not witness.errors:
            generation = tuple((g.uid, normal_values[f'generation[normal,{t},{g.uid}]']) for g in inputs.data.generators)
            commitment = tuple((g.uid, bool(round(normal_values[f'commitment[{t},{g.uid}]']))
                if g.dispatch_mode == 'committable' else g.enabled) for g in inputs.data.generators)
        primary = confirmation = None
        state, need = 'unresolved_grid_need', None
        if eligible and event is None:
            state, need = 'finite_grid_need', 0.
        elif eligible:
            point = inputs.data.hourly_points[source_hour - 1]
            def corrective(demand):
                return lambda: _build_corrective_model(inputs.data, point, dict(generation), dict(commitment),
                    event, dc_bus=inputs.request.dc_bus, dc_demand_mw=demand)
            demand = inputs.request.dc_requested_mw[t]
            primary = _solve(corrective(demand), solver_specification, budget, f'corrective_source_{source_hour}')
            calls += primary.calls
            if primary.optimal and primary.objective is not None and 0 <= primary.objective <= demand:
                state, need = 'finite_grid_need', primary.objective
            elif primary.native_infeasible:
                confirmation = _solve(corrective(0.), solver_specification, budget, f'zero_dc_source_{source_hour}')
                calls += confirmation.calls
                if confirmation.native_infeasible:
                    state = 'solver_reported_exogenous_infeasibility'
        rows.append(GridCandidateHour(source_hour, source_hour - 1, inputs.request.timestamps[t].isoformat(),
            generation, commitment, event, state, need, primary, confirmation))
    if normal_input_identity(inputs) != expected_identity or _execution_identity(solver_specification, budget) != execution_id:
        raise ValueError('input or execution identity drifted during candidate execution')
    return _make(ContinuousGridCandidate, contract=CONTRACT, input_identity=expected_identity,
        execution_identity=execution_id, event_identity=event_id, event_evidence_role=event_evidence_role,
        specification=solver_specification, budget=budget, normal=normal, normal_witness=witness,
        hours=tuple(rows), solver_calls=calls, event_blind_normal_model=True,
        corrective_cross_hour_feasibility=None, infeasibility_certificate=None,
        formal_result=False, security_certified=False)
