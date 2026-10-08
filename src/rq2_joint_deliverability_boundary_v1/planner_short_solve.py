"""One bounded development solve with native-result and assignment evidence.

No formal publication, retry, fallback, lease, or complete-service certificate.
The solver time limit is not a process-level wall-clock termination guarantee.
"""
from dataclasses import asdict, dataclass, fields
from importlib.metadata import version
from math import isfinite
from time import perf_counter
import hashlib
import json

from pyomo.environ import Objective, Var
from pyomo.opt import SolverStatus, TerminationCondition, SolutionStatus, SolverResults
from pyomo.opt.results.problem import ProblemSense

from ..rq2_joint_deliverability_v2.solver_adapter import (
    Rq2SolverSpec, create_solver, model_scale, solver_options, solver_spec,
)
from .continuous_planner import ContinuousPlanningInputs, build_continuous_planning_model, planner_identity
from .four_arm_replay import B6
from .planner_assignment import AssignmentAudit, NumericSnapshot, _numeric, _structure, audit_planner_assignment

CONTRACT = 'continuous_planner_short_solve_v1'
NUMERICAL_LIMITS = (('feasibility_tolerance', 1e-6), ('optimality_tolerance', 1e-6),
                    ('integer_feasibility_tolerance', 1e-6), ('objective_consistency_tolerance', 1e-9))


@dataclass(frozen=True)
class DevelopmentSolveBudget:
    purpose: str
    max_time_limit_seconds: float
    max_threads: int
    max_variables: int
    max_constraints: int
    max_scenarios: int
    max_horizon_hours: int

    def __post_init__(self):
        if type(self.purpose) is not str or not self.purpose.strip():
            raise ValueError('explicit development purpose required')
        if (type(self.max_time_limit_seconds) not in (int, float)
            or not isfinite(self.max_time_limit_seconds) or not 0 < self.max_time_limit_seconds <= 30):
            raise ValueError('short development time budget must be in (0,30] seconds')
        for name, ceiling in (('max_threads', 4), ('max_variables', 20000), ('max_constraints', 100000),
                              ('max_scenarios', 16), ('max_horizon_hours', 168)):
            if type(getattr(self, name)) is not int or not 0 < getattr(self, name) <= ceiling:
                raise ValueError('invalid short development budget: '+name)


def _admit(inputs, arm, spec, budget):
    planner_identity(inputs, arm)
    if not isinstance(budget, DevelopmentSolveBudget):
        raise ValueError('explicit development solve budget required')
    if not isinstance(spec, Rq2SolverSpec):
        raise ValueError('explicit solver specification required')
    spec = solver_spec(asdict(spec))
    for name, maximum in NUMERICAL_LIMITS[:3]:
        if getattr(spec, name) > maximum:
            raise ValueError('solver tolerance exceeds short development applicability: '+name)
    if spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_time_limit_seconds:
        raise ValueError('solver time limit exceeds development budget or is absent')
    if spec.threads > budget.max_threads:
        raise ValueError('solver threads exceed development budget')
    n, h = len(inputs.scenarios), len(inputs.scenarios[0].observations)
    if n > budget.max_scenarios or h > budget.max_horizon_hours:
        raise ValueError('scenario support/horizon exceeds development budget')
    k = 2 if arm == B6 else 1
    if 1+2*n*h+6*n*k*h+n*k*h*(h+1) > budget.max_variables:
        raise ValueError('predicted variable count exceeds development budget')
    return spec


def _values(model):
    return tuple(sorted((v.name, _numeric(v.value))
        for v in model.component_data_objects(Var, active=None, descend_into=True)))


def _native_entries(model, native, component_type, kind):
    """Resolve reported entries explicitly; legacy loaders can ignore unknown symbols."""
    solution = native.solution[0]
    smap = native.__dict__.get('_smap')
    if smap is None:
        key = native.__dict__.get('_smap_id')
        if key is not None:
            smap = model.solutions.symbol_map[key]
    components = {v.name: v for v in model.component_data_objects(component_type, active=None, descend_into=True)}
    resolved = []
    for label, item in getattr(solution, kind).items():
        if smap is not None:
            component = smap.bySymbol.get(label, smap.aliases.get(label))
        elif solution._cuid:
            component = label.find_component_on(model)
        else:
            component = components.get(label)
        if component is None or components.get(component.name) is not component:
            raise ValueError('unknown or wrong-component native solution label: '+str(label))
        resolved.append((component.name, _numeric(item.get('Value'))))
    names = tuple(name for name, _ in resolved)
    if len(names) != len(set(names)):
        raise ValueError('multiple native labels refer to one component')
    return tuple(sorted(resolved))


@dataclass(frozen=True)
class NativeEnumSnapshot:
    type_name: str
    raw_repr: str
    member_name: str | None


def _enum(raw, expected):
    return NativeEnumSnapshot(type(raw).__module__+'.'+type(raw).__qualname__, repr(raw),
                              raw.name if type(raw) is expected else None)


def _native(item, expected):
    if item is None or item.member_name is None:
        return None
    try:
        member = expected[item.member_name]
    except KeyError:
        return None
    return member if _enum(member, expected) == item else None


@dataclass(frozen=True)
class NativeProblemSnapshot:
    sense: NativeEnumSnapshot
    lower: NumericSnapshot
    upper: NumericSnapshot
    variables: NumericSnapshot
    constraints: NumericSnapshot
    objectives: NumericSnapshot


@dataclass(frozen=True, init=False)
class ShortSolveAudit:
    contract: str
    numerical_limits: tuple[tuple[str, float], ...]
    inputs: ContinuousPlanningInputs
    arm: str
    specification: Rq2SolverSpec
    budget: DevelopmentSolveBudget
    variables: int
    constraints: int
    versions_before: tuple[tuple[str, str], ...]
    versions_after: tuple[tuple[str, str], ...]
    passed_options: tuple[tuple[str, float | int], ...]
    returned_options: tuple[tuple[str, float | int], ...]
    pre_structure: str
    preload_structure: str | None
    post_structure: str | None
    initial_values: tuple[tuple[str, NumericSnapshot], ...]
    preload_values: tuple[tuple[str, NumericSnapshot], ...]
    native_values: tuple[tuple[str, NumericSnapshot], ...]
    native_objectives: tuple[tuple[str, NumericSnapshot], ...]
    solver_records: tuple[tuple[NativeEnumSnapshot, NativeEnumSnapshot], ...]
    problem_records: tuple[NativeProblemSnapshot, ...]
    solver_status: NativeEnumSnapshot | None
    termination: NativeEnumSnapshot | None
    solution_statuses: tuple[NativeEnumSnapshot, ...]
    solution_count: int | None
    lower: NumericSnapshot
    upper: NumericSnapshot
    assignment: AssignmentAudit | None
    loaded: bool
    solve_calls: int
    errors: tuple[str, ...]
    elapsed_seconds: float

    def __init__(self, *args, **kwargs):
        raise TypeError('short solve evidence is created only by the owned solver flow')

    def __post_init__(self):
        _admit(self.inputs, self.arm, self.specification, self.budget)
        if self.assignment is not None:
            if (self.assignment.inputs != self.inputs or self.assignment.arm != self.arm
                or self.assignment.feasibility_tolerance != self.specification.feasibility_tolerance
                or self.assignment.integer_tolerance != self.specification.integer_feasibility_tolerance):
                raise ValueError('assignment differs from solve contract')
        if self.solve_calls not in (0, 1) or self.elapsed_seconds < 0 or not isfinite(self.elapsed_seconds):
            raise ValueError('invalid solve accounting')

    @property
    def planner_id(self):
        return planner_identity(self.inputs, self.arm)

    @property
    def lineage_checked(self):
        return (not self.errors and self.solve_calls == 1 and self.loaded
            and self.solution_count == 1 and len(self.solution_statuses) == 1
            and len(self.solver_records) == len(self.problem_records) == 1
            and _native(self.problem_records[0].sense, type(ProblemSense.minimize)) == ProblemSense.minimize
            and self.problem_records[0].objectives.error is None and self.problem_records[0].objectives.number == 1
            and self.assignment is not None and self.assignment.structure_matches
            and self.pre_structure == self.preload_structure == self.post_structure == self.assignment.canonical_structure
            and self.initial_values == self.preload_values
            and self.native_values == self.assignment.snapshot
            and all(item.error is None and self.assignment.objective is not None
                    and abs(item.number-self.assignment.objective) <= min(self.specification.feasibility_tolerance,
                        dict(self.numerical_limits)['objective_consistency_tolerance']) for _, item in self.native_objectives)
            and self.passed_options == self.returned_options == tuple(sorted(solver_options(self.specification).items()))
            and self.versions_before == self.versions_after
            and dict(self.versions_before).get('solver') == self.specification.expected_package_version
            and _native(self.solver_status, SolverStatus) in (SolverStatus.ok, SolverStatus.warning, SolverStatus.aborted)
            and _native(self.solution_statuses[0], SolutionStatus) in
                (SolutionStatus.optimal, SolutionStatus.feasible, SolutionStatus.bestSoFar))

    @property
    def relaxed_prefix_assignment_audited(self):
        return self.lineage_checked and self.assignment.numerical_assignment_accepted

    @property
    def effective_prefix_witness_available(self):
        return self.loaded and self.assignment is not None and self.assignment.exact_witness_accepted

    @property
    def interval_issues(self):
        issues = list(self.errors)
        if not self.lineage_checked: issues.append('solve_lineage_unverified')
        if not self.relaxed_prefix_assignment_audited: issues.append('canonical_assignment_unaccepted')
        if _native(self.solver_status, SolverStatus) != SolverStatus.ok: issues.append('solver_status_not_ok')
        if _native(self.termination, TerminationCondition) not in (TerminationCondition.optimal, TerminationCondition.globallyOptimal):
            issues.append('termination_not_optimal')
        if len(self.solution_statuses) != 1 or _native(self.solution_statuses[0], SolutionStatus) != SolutionStatus.optimal:
            issues.append('solution_status_not_optimal')
        for name, item in (('lower', self.lower), ('upper', self.upper)):
            if item.error is not None: issues.append(name+'_'+item.error)
        if self.lower.number is not None and self.upper.number is not None:
            lower, upper = self.lower.number, self.upper.number
            objective = self.assignment.objective if self.assignment is not None else None
            if lower > upper: issues.append('inverted_bounds')
            if upper < 0 or upper > self.inputs.maximum_capacity:
                issues.append('upper_outside_declared_capacity_domain')
            if lower > self.inputs.maximum_capacity:
                issues.append('lower_above_declared_capacity_domain')
            if objective is not None:
                if lower > objective: issues.append('lower_exceeds_assignment_objective')
                objective_tolerance = min(self.specification.feasibility_tolerance,
                                          dict(self.numerical_limits)['objective_consistency_tolerance'])
                if abs(upper-objective) > objective_tolerance:
                    issues.append('upper_differs_from_assignment_objective')
                gap = upper-lower
                relative = gap/max(abs(objective), 1e-12)
                if not isfinite(relative) or relative < 0 or relative > self.specification.mip_relative_gap:
                    issues.append('relative_gap_unaccepted')
        return tuple(issues)

    @property
    def relaxed_prefix_interval(self):
        return None if self.interval_issues else (self.lower.number, self.upper.number)

    @property
    def result_id(self):
        payload = {k: v for k, v in self.__dict__.items() if k not in ('inputs', 'assignment')}
        payload['planner_id'] = self.planner_id
        payload['assignment_id'] = None if self.assignment is None else self.assignment.assignment_id
        def encode(item):
            return asdict(item)
        return hashlib.sha256(json.dumps(payload, default=encode, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def evidence(self):
        return {'status': 'DRAFT_NONAUTHORITATIVE', 'contract': self.contract,
            'result_id': self.result_id, 'planner_id': self.planner_id,
            'assessment': 'development_relaxed_prefix_interval' if self.relaxed_prefix_interval is not None else 'unresolved',
            'relaxed_prefix_solver_interval': self.relaxed_prefix_interval,
            'interval_interpretation': 'native_mip_bounds_under_declared_numerical_tolerances',
            'relaxed_prefix_assignment_audited': self.relaxed_prefix_assignment_audited,
            'effective_prefix_witness_available': self.effective_prefix_witness_available,
            'prefix_capacity_interval': None, 'complete_capacity_lower_bound': None,
            'complete_capacity_upper_bound': None, 'causal_policy_certificate': None,
            'formal_result': False, 'security_certified': False, 'infeasibility_certificate': None}


def run_short_continuous_solve(inputs, arm, *, solver_specification, budget):
    """Fresh build and one solver call; callers cannot inject models or results."""
    started = perf_counter()
    spec = _admit(inputs, arm, solver_specification, budget)
    model = build_continuous_planning_model(inputs, arm)
    scale = model_scale(model)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('canonical model scale exceeds development budget')
    pre, initial = _structure(model), _values(model)
    before_versions = after_versions = passed = returned = ()
    preload = post = status = termination = count = assignment = None
    preload_values, native_values, native_objectives, solution_statuses, solver_records, problem_records = (), (), (), (), (), ()
    lower = upper = _numeric(None)
    loaded, calls, errors = False, 0, []
    stage = 'create_solver'
    options = None
    def versions():
        return (('pyomo', version('pyomo')), ('solver', version({'highs': 'highspy', 'gurobi': 'gurobipy'}[spec.name])))
    try:
        before_versions = versions()
        solver, options = create_solver(spec)
        passed = tuple(sorted(options.items()))
        if passed != tuple(sorted(solver_options(spec).items())):
            raise ValueError('created solver options differ from specification')
        stage = 'solve'
        calls = 1
        native = solver.solve(model, load_solutions=False, tee=spec.tee, options=options)
        stage = 'native_result'
        if not isinstance(native, SolverResults):
            raise ValueError('native Pyomo SolverResults required')
        solver_records = tuple((_enum(item.status, SolverStatus), _enum(item.termination_condition, TerminationCondition))
                               for item in native.solver)
        problem_records = tuple(NativeProblemSnapshot(_enum(item.sense, type(ProblemSense.minimize)),
            _numeric(item.lower_bound), _numeric(item.upper_bound), _numeric(item.number_of_variables),
            _numeric(item.number_of_constraints), _numeric(item.number_of_objectives)) for item in native.problem)
        count = len(native.solution)
        solution_statuses = tuple(_enum(solution.status, SolutionStatus) for solution in native.solution)
        if len(solver_records) != 1 or len(problem_records) != 1:
            raise ValueError('exactly one native solver and problem record required')
        status, termination = solver_records[0]
        lower, upper = problem_records[0].lower, problem_records[0].upper
        preload, preload_values = _structure(model), _values(model)
        if preload != pre or preload_values != initial:
            raise ValueError('model changed before explicit solution loading')
        if count == 1:
            stage = 'native_variable_inventory'
            native_values = _native_entries(model, native, Var, 'variable')
            native_objectives = _native_entries(model, native, Objective, 'objective')
            if tuple(name for name, _ in native_values) != tuple(name for name, _ in initial):
                raise ValueError('native solution variable inventory is incomplete')
            if any(item.error is not None for _, item in native_values):
                raise ValueError('native solution contains invalid variable values')
            stage = 'load_solution'
            model.solutions.load_from(native, select=0, ignore_invalid_labels=False)
            loaded = True
            stage = 'assignment_audit'
            assignment = audit_planner_assignment(inputs, arm, model, spec)
        elif count == 0:
            errors.append('no_native_solution')
        else:
            errors.append('multiple_native_solutions_unresolved')
    except Exception as error:
        errors.append(stage+':'+type(error).__name__+':'+str(error))
    try:
        post = _structure(model)
        after_versions = versions()
        returned = () if options is None else tuple(sorted(options.items()))
    except Exception as error:
        errors.append('post_snapshot:'+type(error).__name__+':'+str(error))
    return _solve_audit(CONTRACT, NUMERICAL_LIMITS, inputs, arm, spec, budget, scale.variables, scale.constraints,
        before_versions, after_versions, passed, returned, pre, preload, post, initial, preload_values,
        native_values, native_objectives, solver_records, problem_records, status, termination, solution_statuses, count,
        lower, upper, assignment, loaded, calls, tuple(errors), perf_counter()-started)


def _solve_audit(*values):
    # Runtime facts cannot be re-derived by a public dataclass constructor.
    # Keep ordinary construction/replace out of the evidence API; this is not a signature.
    result = object.__new__(ShortSolveAudit)
    for field, item in zip(fields(ShortSolveAudit), values, strict=True):
        object.__setattr__(result, field.name, item)
    result.__post_init__()
    return result
