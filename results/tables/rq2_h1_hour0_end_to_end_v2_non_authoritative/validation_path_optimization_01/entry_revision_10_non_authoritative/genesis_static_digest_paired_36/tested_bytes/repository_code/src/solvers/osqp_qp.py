"""Direct OSQP adapter for separable convex Pyomo QPs."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

import numpy as np
import osqp
from pyomo.common.collections import ComponentMap
from pyomo.environ import Constraint, Objective, Var, minimize, value
from pyomo.repn.standard_repn import generate_standard_repn
from scipy.sparse import csc_matrix


@dataclass(frozen=True)
class OsqpQpResult:
    solved: bool
    status: str
    status_value: int
    objective_value: float | None
    iterations: int
    primal_residual: float
    dual_residual: float
    max_constraint_violation: float | None
    bound_projection_count: int
    max_bound_projection: float
    variable_count: int
    constraint_row_count: int
    hessian_nonzeros: int
    constraint_nonzeros: int
    objective_scale: float
    extraction_seconds: float
    setup_seconds: float
    solve_seconds: float
    update_seconds: float = 0.0
    settings: dict[str, object] = field(default_factory=dict)
    workspace_reused: bool = False
    warm_started: bool = False


def _finite_bound(bound: object | None) -> float | None:
    if bound is None:
        return None
    number = float(value(bound))
    if not np.isfinite(number):
        raise ValueError("OSQP adapter requires finite explicit bounds")
    return number


def _require_finite(number: object, description: str) -> float:
    converted = float(number)
    if not np.isfinite(converted):
        raise ValueError(f"OSQP adapter requires a finite {description}")
    return converted


def _maximum_violation(
    matrix: csc_matrix,
    lower: np.ndarray,
    upper: np.ndarray,
    solution: np.ndarray,
) -> float:
    activity = matrix @ solution
    lower_violation = np.maximum(lower - activity, 0.0)
    upper_violation = np.maximum(activity - upper, 0.0)
    return float(max(lower_violation.max(initial=0.0), upper_violation.max(initial=0.0)))


def linear_expression_after_fixing_quadratics(expression: object) -> object:
    """Return a linear copy of an expression whose quadratic variables are fixed."""

    representation = generate_standard_repn(
        expression,
        compute_values=True,
        quadratic=True,
    )
    if representation.nonlinear_expr is not None or representation.quadratic_vars:
        raise ValueError("Expression is not linear after fixing quadratic variables")
    constant = _require_finite(
        representation.constant or 0.0,
        "linear-expression constant",
    )
    terms = []
    for variable, coefficient in zip(
        representation.linear_vars,
        representation.linear_coefs,
    ):
        terms.append(
            _require_finite(
                coefficient,
                "linear-expression coefficient",
            )
            * variable
        )
    return constant + sum(terms)


@dataclass(frozen=True)
class _ExtractedQp:
    variables: tuple[object, ...]
    objective: object
    hessian: csc_matrix
    linear: np.ndarray
    constraint_matrix: csc_matrix
    lower: np.ndarray
    upper: np.ndarray
    variable_bounds: tuple[tuple[float | None, float | None], ...]
    objective_scale: float
    extraction_seconds: float


def _extract_qp(model: object) -> _ExtractedQp:
    extraction_started = perf_counter()
    variables = tuple(
        variable
        for variable in model.component_data_objects(
            Var,
            active=True,
            descend_into=True,
        )
        if not variable.fixed
    )
    if any(not variable.is_continuous() for variable in variables):
        raise ValueError("OSQP adapter supports only continuous variables")
    variable_index = ComponentMap(
        (variable, index) for index, variable in enumerate(variables)
    )

    objectives = tuple(
        model.component_data_objects(Objective, active=True, descend_into=True)
    )
    if len(objectives) != 1 or objectives[0].sense != minimize:
        raise ValueError("OSQP adapter requires one active minimization objective")
    objective = objectives[0]
    objective_repn = generate_standard_repn(
        objective.expr,
        compute_values=True,
        quadratic=True,
    )
    if objective_repn.nonlinear_expr is not None:
        raise ValueError("OSQP adapter requires a quadratic objective")
    _require_finite(
        objective_repn.constant or 0.0,
        "objective constant",
    )

    variable_count = len(variables)
    linear = np.zeros(variable_count)
    for variable, coefficient in zip(
        objective_repn.linear_vars,
        objective_repn.linear_coefs,
    ):
        linear[variable_index[variable]] += _require_finite(
            coefficient,
            "linear objective coefficient",
        )
    if not np.isfinite(linear).all():
        raise ValueError("OSQP adapter requires a finite linear objective")

    hessian_rows: list[int] = []
    hessian_columns: list[int] = []
    hessian_values: list[float] = []
    for (first, second), coefficient in zip(
        objective_repn.quadratic_vars,
        objective_repn.quadratic_coefs,
    ):
        if first is not second:
            raise ValueError("OSQP adapter supports only separable quadratic objectives")
        number = _require_finite(
            coefficient,
            "quadratic objective coefficient",
        )
        if number < 0.0:
            raise ValueError("OSQP adapter requires a convex quadratic objective")
        index = variable_index[first]
        hessian_rows.append(index)
        hessian_columns.append(index)
        hessian_values.append(2.0 * number)
    hessian = csc_matrix(
        (hessian_values, (hessian_rows, hessian_columns)),
        shape=(variable_count, variable_count),
    )
    if hessian.nnz and not np.isfinite(hessian.data).all():
        raise ValueError("OSQP adapter requires a finite objective Hessian")

    rows: list[int] = []
    columns: list[int] = []
    coefficients: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    row_index = 0
    for constraint in model.component_data_objects(
        Constraint,
        active=True,
        descend_into=True,
    ):
        representation = generate_standard_repn(
            constraint.body,
            compute_values=True,
            quadratic=True,
        )
        if representation.nonlinear_expr is not None or representation.quadratic_vars:
            raise ValueError(
                f"OSQP adapter requires linear constraints: {constraint.name}"
            )
        for variable, coefficient in zip(
            representation.linear_vars,
            representation.linear_coefs,
        ):
            rows.append(row_index)
            columns.append(variable_index[variable])
            coefficients.append(
                _require_finite(
                    coefficient,
                    f"constraint coefficient in {constraint.name}",
                )
            )
        constant = _require_finite(
            representation.constant or 0.0,
            f"constraint constant in {constraint.name}",
        )
        constraint_lower = _finite_bound(constraint.lower)
        constraint_upper = _finite_bound(constraint.upper)
        lower.append(
            -np.inf if constraint_lower is None else constraint_lower - constant
        )
        upper.append(
            np.inf if constraint_upper is None else constraint_upper - constant
        )
        row_index += 1

    variable_bounds: list[tuple[float | None, float | None]] = []
    for variable in variables:
        variable_lower = _finite_bound(variable.lb)
        variable_upper = _finite_bound(variable.ub)
        variable_bounds.append((variable_lower, variable_upper))
        if variable_lower is None and variable_upper is None:
            continue
        rows.append(row_index)
        columns.append(variable_index[variable])
        coefficients.append(1.0)
        lower.append(-np.inf if variable_lower is None else variable_lower)
        upper.append(np.inf if variable_upper is None else variable_upper)
        row_index += 1

    constraint_matrix = csc_matrix(
        (coefficients, (rows, columns)),
        shape=(row_index, variable_count),
    )
    lower_array = np.asarray(lower)
    upper_array = np.asarray(upper)
    if constraint_matrix.nnz and not np.isfinite(constraint_matrix.data).all():
        raise ValueError("OSQP adapter requires a finite constraint matrix")
    valid_lower = np.isfinite(lower_array) | np.isneginf(lower_array)
    valid_upper = np.isfinite(upper_array) | np.isposinf(upper_array)
    if not valid_lower.all() or not valid_upper.all():
        raise ValueError("OSQP adapter received an invalid bound sentinel")
    if np.any(lower_array > upper_array):
        raise ValueError("OSQP adapter requires lower bounds not above upper bounds")
    nonzero_linear = linear[np.nonzero(linear)]
    objective_scale = max(
        float(np.max(np.abs(hessian.data))) if hessian.nnz else 0.0,
        float(np.max(np.abs(nonzero_linear))) if nonzero_linear.size else 0.0,
        1.0,
    )
    return _ExtractedQp(
        variables=variables,
        objective=objective,
        hessian=hessian,
        linear=linear,
        constraint_matrix=constraint_matrix,
        lower=lower_array,
        upper=upper_array,
        variable_bounds=tuple(variable_bounds),
        objective_scale=objective_scale,
        extraction_seconds=perf_counter() - extraction_started,
    )


def _same_sparse_matrix(first: csc_matrix, second: csc_matrix) -> bool:
    return (
        first.shape == second.shape
        and np.array_equal(first.indptr, second.indptr)
        and np.array_equal(first.indices, second.indices)
        and np.array_equal(first.data, second.data)
    )


class OsqpQpWorkspace:
    """Reusable OSQP workspace for QPs that differ only in row bounds."""

    def __init__(
        self,
        *,
        feasibility_tolerance: float = 1.0e-6,
        eps_abs: float = 1.0e-8,
        eps_rel: float = 1.0e-10,
        max_iter: int = 500_000,
        time_limit_seconds: float = 60.0,
        verbose: bool = False,
    ) -> None:
        self.feasibility_tolerance = feasibility_tolerance
        self.eps_abs = eps_abs
        self.eps_rel = eps_rel
        self.max_iter = max_iter
        self.time_limit_seconds = time_limit_seconds
        self.verbose = verbose
        self.settings = {
            "feasibility_tolerance": feasibility_tolerance,
            "eps_abs": eps_abs,
            "eps_rel": eps_rel,
            "max_iter": max_iter,
            "time_limit_seconds": time_limit_seconds,
            "polishing": True,
            "adaptive_rho": True,
            "scaling": 20,
            "scaled_termination": False,
            "warm_starting": False,
            "verbose": verbose,
        }
        self._solver: osqp.OSQP | None = None
        self._reference: _ExtractedQp | None = None
        self._last_x: np.ndarray | None = None
        self._last_y: np.ndarray | None = None

    def _validate_structure(self, current: _ExtractedQp) -> None:
        reference = self._reference
        if reference is None:
            raise RuntimeError("OSQP workspace has no reference problem")
        if len(reference.variables) != len(current.variables) or any(
            first is not second
            for first, second in zip(reference.variables, current.variables)
        ):
            raise ValueError("OSQP workspace structure changed: variables")
        if reference.objective is not current.objective:
            raise ValueError("OSQP workspace structure changed: objective")
        if not _same_sparse_matrix(reference.hessian, current.hessian):
            raise ValueError("OSQP workspace structure changed: P")
        if not np.array_equal(reference.linear, current.linear):
            raise ValueError("OSQP workspace structure changed: q")
        if not _same_sparse_matrix(
            reference.constraint_matrix,
            current.constraint_matrix,
        ):
            raise ValueError("OSQP workspace structure changed: A")
        if reference.objective_scale != current.objective_scale:
            raise ValueError("OSQP workspace structure changed: objective scale")
        if reference.variable_bounds != current.variable_bounds:
            raise ValueError("OSQP workspace structure changed: variable bounds")

    def solve(self, model: object) -> OsqpQpResult:
        """Solve and load one audited QP, reusing a compatible workspace."""

        problem = _extract_qp(model)
        workspace_reused = self._solver is not None
        setup_seconds = 0.0
        update_seconds = 0.0
        warm_started = False
        if self._solver is None:
            solver = osqp.OSQP()
            setup_started = perf_counter()
            try:
                solver.setup(
                    P=problem.hessian / problem.objective_scale,
                    q=problem.linear / problem.objective_scale,
                    A=problem.constraint_matrix,
                    l=problem.lower,
                    u=problem.upper,
                    eps_abs=self.eps_abs,
                    eps_rel=self.eps_rel,
                    max_iter=self.max_iter,
                    polishing=True,
                    adaptive_rho=True,
                    scaling=20,
                    scaled_termination=False,
                    time_limit=self.time_limit_seconds,
                    warm_starting=False,
                    verbose=self.verbose,
                )
            except osqp.OSQPException as error:
                raise RuntimeError("OSQP workspace setup failed") from error
            self._solver = solver
            self._reference = problem
            setup_seconds = perf_counter() - setup_started
        else:
            self._validate_structure(problem)
            solver = self._solver
            update_started = perf_counter()
            try:
                solver.update(l=problem.lower, u=problem.upper)
                if self._last_x is not None and self._last_y is not None:
                    solver.warm_start(x=self._last_x, y=self._last_y)
                    warm_started = True
            except osqp.OSQPException as error:
                raise RuntimeError("OSQP workspace update failed") from error
            update_seconds = perf_counter() - update_started

        solve_started = perf_counter()
        try:
            raw_result = solver.solve(raise_error=False)
        except osqp.OSQPException as error:
            raise RuntimeError("OSQP workspace solve failed") from error
        solve_seconds = perf_counter() - solve_started
        reusable_status_values = {
            osqp.SolverStatus.OSQP_SOLVED.value,
            osqp.SolverStatus.OSQP_SOLVED_INACCURATE.value,
            osqp.SolverStatus.OSQP_MAX_ITER_REACHED.value,
            osqp.SolverStatus.OSQP_TIME_LIMIT_REACHED.value,
        }
        reusable_iterate = (
            raw_result.info.status_val in reusable_status_values
            and raw_result.x is not None
            and raw_result.y is not None
            and np.isfinite(raw_result.x).all()
            and np.isfinite(raw_result.y).all()
        )
        if reusable_iterate:
            self._last_x = np.asarray(raw_result.x, dtype=float).copy()
            self._last_y = np.asarray(raw_result.y, dtype=float).copy()
        else:
            self._last_x = None
            self._last_y = None

        solved = (
            raw_result.info.status_val == osqp.SolverStatus.OSQP_SOLVED.value
            and np.isfinite(raw_result.info.prim_res)
            and np.isfinite(raw_result.info.dual_res)
        )
        objective_value = None
        max_violation = None
        projection_count = 0
        max_projection = 0.0
        if solved:
            if raw_result.x is None or not np.isfinite(raw_result.x).all():
                solved = False
            else:
                projected = np.asarray(raw_result.x, dtype=float).copy()
                for index, (variable_lower, variable_upper) in enumerate(
                    problem.variable_bounds
                ):
                    original = projected[index]
                    if variable_lower is not None:
                        projected[index] = max(projected[index], variable_lower)
                    if variable_upper is not None:
                        projected[index] = min(projected[index], variable_upper)
                    movement = abs(projected[index] - original)
                    if movement > 0.0:
                        projection_count += 1
                        max_projection = max(max_projection, movement)
                max_violation = _maximum_violation(
                    problem.constraint_matrix,
                    problem.lower,
                    problem.upper,
                    projected,
                )
                if (
                    max_violation > self.feasibility_tolerance
                    or max_projection > self.feasibility_tolerance
                ):
                    solved = False
                else:
                    for variable, variable_value in zip(
                        problem.variables,
                        projected,
                    ):
                        variable.set_value(
                            float(variable_value),
                            skip_validation=True,
                        )
                    candidate_objective = float(value(problem.objective.expr))
                    if np.isfinite(candidate_objective):
                        objective_value = candidate_objective
                    else:
                        solved = False

        return OsqpQpResult(
            solved=solved,
            status=str(raw_result.info.status),
            status_value=int(raw_result.info.status_val),
            objective_value=objective_value,
            iterations=int(raw_result.info.iter),
            primal_residual=float(raw_result.info.prim_res),
            dual_residual=float(raw_result.info.dual_res),
            max_constraint_violation=max_violation,
            bound_projection_count=projection_count,
            max_bound_projection=max_projection,
            variable_count=len(problem.variables),
            constraint_row_count=problem.constraint_matrix.shape[0],
            hessian_nonzeros=problem.hessian.nnz,
            constraint_nonzeros=problem.constraint_matrix.nnz,
            objective_scale=problem.objective_scale,
            extraction_seconds=problem.extraction_seconds,
            setup_seconds=setup_seconds,
            update_seconds=update_seconds,
            solve_seconds=solve_seconds,
            settings=dict(self.settings),
            workspace_reused=workspace_reused,
            warm_started=warm_started,
        )


def solve_separable_convex_qp(
    model: object,
    *,
    feasibility_tolerance: float = 1.0e-6,
    eps_abs: float = 1.0e-8,
    eps_rel: float = 1.0e-10,
    max_iter: int = 500_000,
    time_limit_seconds: float = 60.0,
    verbose: bool = False,
) -> OsqpQpResult:
    """Solve one continuous Pyomo QP with a fresh workspace."""

    return OsqpQpWorkspace(
        feasibility_tolerance=feasibility_tolerance,
        eps_abs=eps_abs,
        eps_rel=eps_rel,
        max_iter=max_iter,
        time_limit_seconds=time_limit_seconds,
        verbose=verbose,
    ).solve(model)
