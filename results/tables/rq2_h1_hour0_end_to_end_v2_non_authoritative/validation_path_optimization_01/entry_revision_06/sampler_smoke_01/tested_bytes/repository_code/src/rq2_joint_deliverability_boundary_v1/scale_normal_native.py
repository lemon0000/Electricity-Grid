"""Owned direct-Gurobi solve using the unchanged native audit algorithm."""
from hashlib import sha256
from pathlib import Path
from importlib.metadata import version
from .continuous_grid_candidate import _enum, _raw_number
from ..solvers import rq2_gurobi_declared_normal as adapter
from ..solvers.rq2_gurobi_declared_normal import create_solver
from . import continuous_grid_candidate as legacy
from . import grid_structure_fast as structure
from .grid_structure_fast import structure as _structure
from .continuous_grid_candidate import (
    GridDevelopmentBudget,
    GridSolveEvidence,
    Objective,
    ProblemSense,
    SolutionStatus,
    SolverResults,
    SolverStatus,
    TerminationCondition,
    Var,
    _canonical_completions,
    _constraint_violation,
    _dependencies,
    _integrality_violation,
    _make,
    _native_values,
    _number,
    _snapshot,
    isfinite,
    model_scale,
    solver_options,
    value
)

CONTRACT = 'draft_declared_scale_normal_native_v1'
EXTRA_DEPENDENCIES = legacy.EXTRA_DEPENDENCIES + (
    'src/solvers/rq2_gurobi_declared_normal.py',
    'src/rq2_joint_deliverability_boundary_v1/scale_normal_native.py',
    'src/rq2_joint_deliverability_boundary_v1/grid_structure_fast.py')


def _execution_identity(spec, budget):
    adapter.validate_spec(spec)
    return legacy._digest(CONTRACT, legacy._execution_identity(spec, budget),
        adapter.implementation_identity(), structure.implementation_identity(), sha256(Path(__file__).read_bytes()).hexdigest())


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
