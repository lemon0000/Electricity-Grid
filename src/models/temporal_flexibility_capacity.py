"""Lexicographic minimum flexibility capacity for correct and B6 contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from pyomo.environ import Objective, minimize
from pyomo.opt import SolverFactory, TerminationCondition

from .economic_temporal_stochastic import (
    TemporalEconomicInputs,
    _build_model,
    _clean_nonnegative,
    _constraint_residual,
    _validate_inputs,
)

_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}
_PROVEN_INFEASIBLE = {TerminationCondition.infeasible}
_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class MinimumFlexibilityCapacity:
    enforce_joint_budget: bool
    feasible: bool
    proven_infeasible: bool
    minimum_capacity: float | None
    termination_condition: str
    solver_status: str
    maximum_residual: float | None


@dataclass(frozen=True)
class MinimumFlexibilityPolicyPair:
    correct: MinimumFlexibilityCapacity
    b6: MinimumFlexibilityCapacity


def solve_minimum_temporal_flexibility(
    inputs: TemporalEconomicInputs,
    *,
    enforce_joint_budget: bool,
    solver_name: str = "highs",
    tee: bool = False,
) -> MinimumFlexibilityCapacity:
    """Minimize capacity subject to full grid and CFE service."""

    if inputs.fixed_flexibility_mw is not None:
        raise ValueError("minimum-capacity planning cannot pin flexibility")
    prepared = replace(inputs, enforce_joint_budget=enforce_joint_budget)
    max_duration_steps, minimum_rest_steps = _validate_inputs(prepared)
    model = _build_model(prepared, max_duration_steps, minimum_rest_steps)
    for point in model.points:
        model.access_shortfall[point].fix(0.0)
    model.total_cost.deactivate()
    model.minimum_capacity = Objective(expr=model.flex_budget, sense=minimize)
    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    result = solver.solve(model, tee=tee, load_solutions=False)
    termination = result.solver.termination_condition
    if termination not in _OPTIMAL:
        return MinimumFlexibilityCapacity(
            enforce_joint_budget=enforce_joint_budget,
            feasible=False,
            proven_infeasible=termination in _PROVEN_INFEASIBLE,
            minimum_capacity=None,
            termination_condition=str(termination),
            solver_status=str(result.solver.status),
            maximum_residual=None,
        )
    model.solutions.load_from(result)
    residual = _constraint_residual(model)
    capacity = _clean_nonnegative(model.flex_budget)
    feasible = residual <= _TOLERANCE
    return MinimumFlexibilityCapacity(
        enforce_joint_budget=enforce_joint_budget,
        feasible=feasible,
        proven_infeasible=False,
        minimum_capacity=capacity if feasible else None,
        termination_condition=(
            str(termination) if feasible else "solution_audit_failed"
        ),
        solver_status=str(result.solver.status),
        maximum_residual=residual,
    )


def plan_minimum_flexibility_pair(
    inputs: TemporalEconomicInputs,
    *,
    solver_name: str = "highs",
    tee: bool = False,
) -> MinimumFlexibilityPolicyPair:
    """Freeze correct and B6 minimum-capacity policies on one training set."""

    return MinimumFlexibilityPolicyPair(
        correct=solve_minimum_temporal_flexibility(
            inputs,
            enforce_joint_budget=True,
            solver_name=solver_name,
            tee=tee,
        ),
        b6=solve_minimum_temporal_flexibility(
            inputs,
            enforce_joint_budget=False,
            solver_name=solver_name,
            tee=tee,
        ),
    )
