"""Explicit-solver minimum flexibility planning for the RQ2 successor."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite

from pyomo.environ import Objective, minimize, value
from pyomo.opt import TerminationCondition

from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    _build_model,
    _clean_nonnegative,
    _constraint_residual,
    _validate_inputs,
)
from src.solvers.rq2_solver_adapter import (
    Rq2SolverSpec,
    create_solver,
    model_scale,
)

_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}
_PROVEN_INFEASIBLE = {TerminationCondition.infeasible}


@dataclass(frozen=True)
class MinimumFlexibilityCapacitySuccessor:
    enforce_joint_budget: bool
    feasible: bool
    proven_infeasible: bool
    minimum_capacity: float | None
    termination_condition: str
    solver_status: str
    maximum_residual: float | None
    lower_bound: float | None
    upper_bound: float | None
    absolute_gap: float | None
    relative_gap: float | None
    gap_tolerance: float | None
    model_variables: int
    model_constraints: int
    solver_name: str
    solver_options: dict[str, float | int]


@dataclass(frozen=True)
class MinimumFlexibilityPolicyPairSuccessor:
    correct: MinimumFlexibilityCapacitySuccessor
    b6: MinimumFlexibilityCapacitySuccessor


def _optional_finite(raw: object | None) -> float | None:
    if raw is None:
        return None
    value_ = float(raw)
    return value_ if isfinite(value_) else None


def solve_minimum_temporal_flexibility_with_spec(
    inputs: TemporalEconomicInputs,
    *,
    enforce_joint_budget: bool,
    solver_specification: Rq2SolverSpec,
) -> MinimumFlexibilityCapacitySuccessor:
    """Minimize normalized flexibility using the frozen explicit solver spec."""

    if inputs.fixed_flexibility_mw is not None:
        raise ValueError("minimum-capacity planning cannot pin flexibility")
    prepared = replace(inputs, enforce_joint_budget=enforce_joint_budget)
    max_duration_steps, minimum_rest_steps = _validate_inputs(prepared)
    model = _build_model(prepared, max_duration_steps, minimum_rest_steps)
    for point in model.points:
        model.access_shortfall[point].fix(0.0)
    model.total_cost.deactivate()
    model.minimum_capacity = Objective(expr=model.flex_budget, sense=minimize)
    scale = model_scale(model)
    solver, options = create_solver(solver_specification)
    result = solver.solve(
        model,
        tee=solver_specification.tee,
        load_solutions=False,
        options=options,
    )
    termination = result.solver.termination_condition
    lower = _optional_finite(result.problem.lower_bound)
    upper = _optional_finite(result.problem.upper_bound)
    gap = abs(upper - lower) if lower is not None and upper is not None else None
    relative_gap = (
        gap / max(abs(upper), 1.0e-12)
        if gap is not None and upper is not None
        else None
    )
    gap_tolerance = (
        max(
            solver_specification.feasibility_tolerance,
            solver_specification.mip_relative_gap * max(abs(upper), 1.0),
        )
        if upper is not None
        else None
    )
    if termination not in _OPTIMAL:
        return MinimumFlexibilityCapacitySuccessor(
            enforce_joint_budget=enforce_joint_budget,
            feasible=False,
            proven_infeasible=termination in _PROVEN_INFEASIBLE,
            minimum_capacity=None,
            termination_condition=str(termination),
            solver_status=str(result.solver.status),
            maximum_residual=None,
            lower_bound=lower,
            upper_bound=upper,
            absolute_gap=gap,
            relative_gap=relative_gap,
            gap_tolerance=gap_tolerance,
            model_variables=scale.variables,
            model_constraints=scale.constraints,
            solver_name=solver_specification.name,
            solver_options=options,
        )
    model.solutions.load_from(result)
    residual = _constraint_residual(model)
    capacity = _clean_nonnegative(model.flex_budget)
    feasible = bool(
        residual <= solver_specification.feasibility_tolerance
        and lower is not None
        and upper is not None
        and gap is not None
        and gap_tolerance is not None
        and gap <= gap_tolerance
        and abs(float(value(model.flex_budget)) - upper) <= gap_tolerance
    )
    return MinimumFlexibilityCapacitySuccessor(
        enforce_joint_budget=enforce_joint_budget,
        feasible=feasible,
        proven_infeasible=False,
        minimum_capacity=capacity if feasible else None,
        termination_condition=(
            str(termination) if feasible else "solution_audit_failed"
        ),
        solver_status=str(result.solver.status),
        maximum_residual=residual,
        lower_bound=lower,
        upper_bound=upper,
        absolute_gap=gap,
        relative_gap=relative_gap,
        gap_tolerance=gap_tolerance,
        model_variables=scale.variables,
        model_constraints=scale.constraints,
        solver_name=solver_specification.name,
        solver_options=options,
    )


def plan_minimum_flexibility_pair_with_spec(
    inputs: TemporalEconomicInputs,
    *,
    solver_specification: Rq2SolverSpec,
) -> MinimumFlexibilityPolicyPairSuccessor:
    """Freeze correct and B6 policies with one explicit solver contract."""

    return MinimumFlexibilityPolicyPairSuccessor(
        correct=solve_minimum_temporal_flexibility_with_spec(
            inputs,
            enforce_joint_budget=True,
            solver_specification=solver_specification,
        ),
        b6=solve_minimum_temporal_flexibility_with_spec(
            inputs,
            enforce_joint_budget=False,
            solver_specification=solver_specification,
        ),
    )
