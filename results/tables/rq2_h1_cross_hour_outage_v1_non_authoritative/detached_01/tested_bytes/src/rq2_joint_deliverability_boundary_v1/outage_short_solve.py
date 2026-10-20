"""Owned, bounded development solve of the complete offline outage LP."""
from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib.metadata import version
from math import fsum, isfinite
from pathlib import Path

from pyomo.environ import Objective, Var
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from ..solvers.rq2_solver_adapter import (
    Rq2SolverSpec, solver_spec, solver_options, create_solver, model_scale)
from .continuous_grid_candidate import (
    GridDevelopmentBudget, GridSolveEvidence, _make, _number, _raw_number, _enum,
    _snapshot, _structure, _native_values, _canonical_completions, _execution_identity)
from .continuous_grid_normal import _digest
from .outage_trajectory import OutageTrajectoryInputs, build_outage_trajectory_model, outage_trajectory_identity
from .outage_assignment import OutageAssignmentWitness, audit_outage_assignment


CONTRACT = 'owned_complete_offline_outage_lp_short_solve_v1'


@dataclass(frozen=True, init=False)
class OutageShortResult:
    contract: str
    input_identity: str
    execution_identity: str
    specification: Rq2SolverSpec
    budget: GridDevelopmentBudget
    objective_mode: str
    solve: GridSolveEvidence
    assignment_witness: OutageAssignmentWitness | None
    solver_lineage_checked: bool
    offline_feasible_trajectory_witness_available: bool
    fixed_vector_feasibility_witness_available: bool
    hourly_curtailment_mw: tuple
    weighted_objective_contributions: tuple
    development_objective_interval: tuple[float, float] | None
    information_mode: str
    external_grid_need_trace: None
    causal_policy_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool

    def __init__(self, *args, **kwargs):
        raise TypeError('outage result requires owned short execution')

    @property
    def result_id(self):
        return _digest(self)


def _execution(spec, budget):
    if type(CONTRACT) is not str or CONTRACT != 'owned_complete_offline_outage_lp_short_solve_v1':
        raise ValueError('outage short execution contract drift')
    root = Path(__file__).resolve().parent
    sources = tuple((name, sha256((root / name).read_bytes()).hexdigest()) for name in
        ('outage_trajectory.py', 'outage_assignment.py', 'outage_short_solve.py'))
    return _digest(CONTRACT, _execution_identity(spec, budget), sources)


def _admit(inputs, spec, budget):
    if (type(inputs) is not OutageTrajectoryInputs or type(budget) is not GridDevelopmentBudget
            or type(spec) is not Rq2SolverSpec):
        raise ValueError('explicit typed solver and development budget required')
    budget.__post_init__()
    if spec != solver_spec(asdict(spec)):
        raise ValueError('canonical solver specification required')
    if any(getattr(spec, name) > 1e-6 for name in (
            'feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance')):
        raise ValueError('solver tolerance exceeds outage audit applicability')
    if (spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_seconds_per_solve
            or spec.time_limit_seconds > budget.max_total_solver_seconds
            or spec.threads > budget.max_threads
            or len(inputs.normal_inputs.source_hours) > budget.max_horizon):
        raise ValueError('outage execution exceeds short development budget')


def run_short_outage(inputs, *, expected_identity, solver_specification, budget):
    """One native LP call, explicit load, then independent full assignment audit.

    Weighted-objective evidence belongs only to this offline scalarized problem.
    A fixed-vector model has a zero objective and yields feasibility evidence.
    No fallback, zero-demand replacement, suffix optimization or formal output.
    """
    spec = solver_specification
    _admit(inputs, spec, budget)
    execution = _execution(spec, budget)
    builder = lambda: build_outage_trajectory_model(inputs, expected_identity=expected_identity)
    model = builder()
    scale = model_scale(model)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('outage model exceeds short development scale')
    maximum_objective = (fsum(w * d for w, d in zip(inputs.curtailment_weights,
        inputs.normal_inputs.request.dc_requested_mw, strict=True))
        if inputs.objective_mode == 'weighted_total_curtailment' else 0.)
    if not isfinite(maximum_objective):
        raise ValueError('finite weighted objective domain required')
    before, initial = _structure(model), _snapshot(model)
    solver_records = problem_records = statuses = native_values = completed = loaded = native_objectives = ()
    preload = passed = returned = before_versions = after_versions = ()
    pre_structure = post_structure = None
    objective = lower = upper = residual = integer = count = None
    witness = None
    calls = 0
    errors = []
    options = None
    status = termination = solution_status = None
    assignment_valid = optimal = native_infeasible = False
    def versions():
        return (version('Pyomo'), version('highspy' if spec.name == 'highs' else 'gurobipy'))
    stage = 'create'
    try:
        before_versions = versions()
        solver, options = create_solver(spec)
        passed = tuple(sorted(options.items()))
        if passed != tuple(sorted(solver_options(spec).items())):
            raise ValueError('solver options differ from declaration')
        stage = 'solve'
        calls = 1
        native = solver.solve(model, load_solutions=False, tee=spec.tee, options=options)
        stage = 'native_result'
        if not isinstance(native, SolverResults):
            raise ValueError('native SolverResults required')
        solver_records = tuple((_enum(r.status), _enum(r.termination_condition)) for r in native.solver)
        problem_records = tuple((_enum(r.sense), _raw_number(r.lower_bound), _raw_number(r.upper_bound),
            _raw_number(r.number_of_variables), _raw_number(r.number_of_constraints),
            _raw_number(r.number_of_objectives)) for r in native.problem)
        statuses = tuple(_enum(s.status) for s in native.solution)
        count = len(native.solution)
        if len(solver_records) != 1 or len(problem_records) != 1:
            raise ValueError('one native solver and problem record required')
        status, termination = native.solver[0].status, native.solver[0].termination_condition
        if type(status) is not SolverStatus or type(termination) is not TerminationCondition:
            raise ValueError('typed native status and termination required')
        problem = native.problem[0]
        if problem.sense is not ProblemSense.minimize or _number(problem.number_of_objectives) != 1:
            raise ValueError('one native minimization objective required')
        lower, upper = problem_records[0][1][2], problem_records[0][2][2]
        pre_structure, preload = _structure(model), _snapshot(model)
        if before != pre_structure or initial != preload:
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
            if loaded != tuple(sorted((*native_values, *((n, x) for n, x, _ in completed)))):
                raise ValueError('native and loaded assignment differ')
            stage = 'canonical_audit'
            canonical = builder()
            if _structure(canonical) != before:
                raise ValueError('fresh canonical structure differs')
            witness = audit_outage_assignment(inputs, dict(loaded), expected_identity=expected_identity)
            objective = witness.objective_value
            checks = (witness.maximum_fixed_violation, witness.maximum_bound_violation,
                      witness.maximum_constraint_violation)
            residual = max(checks) if all(x is not None for x in checks) else None
            integer = 0.  # The canonical outage model is a continuous LP.
            assignment_valid = not witness.errors
            if not assignment_valid:
                errors.append('canonical_outage_assignment_invalid')
            if native_objectives and (len(native_objectives) != 1 or objective is None
                    or abs(native_objectives[0][1] - objective) > min(spec.feasibility_tolerance, 1e-9)):
                raise ValueError('native objective differs from canonical objective')
            if solution_status not in (SolutionStatus.optimal, SolutionStatus.feasible):
                errors.append('native_solution_status_not_feasible')
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
        optimal = (status is SolverStatus.ok
            and termination in (TerminationCondition.optimal, TerminationCondition.globallyOptimal)
            and solution_status is SolutionStatus.optimal and assignment_valid and objective is not None
            and residual is not None and residual <= spec.feasibility_tolerance
            and lower is not None and upper is not None and 0 <= lower <= upper and lower <= objective
            and 0 <= objective <= maximum_objective and 0 <= upper <= maximum_objective
            and abs(upper - objective) <= min(spec.feasibility_tolerance, 1e-9)
            and (upper - lower) / max(abs(objective), 1e-12) <= spec.mip_relative_gap)
    if (outage_trajectory_identity(inputs) != expected_identity or _execution(spec, budget) != execution):
        raise ValueError('outage input or execution identity drifted')
    evidence = _make(GridSolveEvidence, purpose='complete_offline_outage_lp',
        variables=scale.variables, constraints=scale.constraints, solver_records=solver_records,
        problem_records=problem_records, solution_statuses=statuses, solution_count=count,
        structures=(before, pre_structure, post_structure), versions=(before_versions, after_versions),
        options=(passed, returned), initial_values=initial, preload_values=preload,
        native_values=native_values, canonical_completed_values=completed, loaded_values=loaded,
        native_objectives=native_objectives, objective=objective, lower=lower, upper=upper,
        maximum_residual=residual, maximum_integrality_violation=integer, calls=calls,
        assignment_valid=assignment_valid and not errors, optimal=optimal,
        native_infeasible=native_infeasible, errors=tuple(errors))
    interval = ((lower, upper) if optimal and inputs.objective_mode == 'weighted_total_curtailment' else None)
    feasible = witness is not None and not witness.errors
    values = {} if not feasible else dict(witness.assignment)
    hourly = tuple((hour, values[f'curtailment[{t}]'])
        for t, hour in enumerate(inputs.normal_inputs.source_hours)) if feasible else ()
    contributions = (tuple((hour, inputs.curtailment_weights[t] * q) for t, (hour, q) in enumerate(hourly))
        if inputs.objective_mode == 'weighted_total_curtailment' else ())
    return _make(OutageShortResult, contract=CONTRACT, input_identity=expected_identity,
        execution_identity=execution, specification=spec, budget=budget, objective_mode=inputs.objective_mode,
        solve=evidence, assignment_witness=witness, solver_lineage_checked=not errors,
        offline_feasible_trajectory_witness_available=feasible,
        fixed_vector_feasibility_witness_available=feasible and inputs.objective_mode == 'fixed_curtailment_vector',
        hourly_curtailment_mw=hourly, weighted_objective_contributions=contributions,
        development_objective_interval=interval, information_mode=inputs.information_mode,
        external_grid_need_trace=None, causal_policy_certificate=None,
        infeasibility_certificate=None, formal_result=False, security_certified=False)
