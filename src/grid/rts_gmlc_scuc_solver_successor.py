"""Explicit-solver normal SCUC entry point for the RQ2 successor."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from highspy import Highs
from pyomo.environ import value
from pyomo.opt import TerminationCondition

from src.grid.chronological_dispatch import ChronologicalDispatchRequest
from src.grid.rts_gmlc_scuc import (
    RtsGmlcInitialState,
    RtsGmlcSolverAudit,
    _build_context,
    _build_model,
    _constraint_violation,
    _derive_initial_state,
    _extract_branch_flows,
    _integrality_violation,
    _security_states,
)
from src.solvers.rq2_solver_adapter import Rq2SolverSpec, create_solver


@dataclass(frozen=True)
class RtsGmlcSuccessorSolverAudit(RtsGmlcSolverAudit):
    relative_gap: float | None = None


def _optional_finite(raw: object | None) -> float | None:
    if raw is None:
        return None
    value_ = float(raw)
    return value_ if isfinite(value_) else None


def _relative_gap(
    lower: float | None,
    upper: float | None,
) -> float | None:
    if lower is None or upper is None:
        return None
    return abs(upper - lower) / max(abs(upper), 1.0e-12)


def solve_normal_prescreen_with_spec(
    data: Any,
    request: ChronologicalDispatchRequest,
    points: tuple[Any, ...],
    *,
    solver_specification: Rq2SolverSpec,
    tolerance: float,
) -> tuple[
    Any,
    Any,
    RtsGmlcSuccessorSolverAudit,
    RtsGmlcInitialState,
    tuple[dict[str, float], ...],
]:
    """Build and solve the unchanged normal-state SCUC with explicit options."""

    states = _security_states((), ())
    context = _build_context(data, request, points, states)
    model = _build_model(context, fixed_initial=None)
    if solver_specification.name == "highs":
        Highs.resetGlobalScheduler(True)
    solver, options = create_solver(solver_specification)
    result = solver.solve(
        model,
        load_solutions=False,
        tee=solver_specification.tee,
        options=options,
    )
    termination = result.solver.termination_condition
    optimal = termination in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
    }
    lower = _optional_finite(result.problem.lower_bound)
    upper = _optional_finite(result.problem.upper_bound)
    gap = abs(upper - lower) if lower is not None and upper is not None else None
    relative_gap = _relative_gap(lower, upper)
    scale = max(abs(lower or 0.0), abs(upper or 0.0), 1.0)
    gap_tolerance = max(
        tolerance,
        max(solver_specification.mip_relative_gap, 1.0e-8) * scale,
    )
    objective = None
    constraint_violation = None
    integrality_violation = None
    if optimal:
        model.solutions.load_from(result)
        objective = _optional_finite(value(model.operating_cost, exception=False))
        constraint_violation = _constraint_violation(model)
        integrality_violation = _integrality_violation(model)
    accepted = bool(
        optimal
        and objective is not None
        and gap is not None
        and relative_gap is not None
        and gap <= gap_tolerance
        and constraint_violation is not None
        and constraint_violation <= tolerance
        and integrality_violation is not None
        and integrality_violation
        <= solver_specification.integer_feasibility_tolerance
    )
    audit = RtsGmlcSuccessorSolverAudit(
        accepted=accepted,
        termination_condition=str(termination),
        solver_status=str(result.solver.status),
        solver_message=str(result.solver.message),
        objective_usd=objective,
        lower_bound_usd=lower,
        upper_bound_usd=upper,
        absolute_gap_usd=gap,
        relative_gap=relative_gap,
        gap_tolerance_usd=gap_tolerance,
        maximum_constraint_violation=constraint_violation,
        maximum_integrality_violation=integrality_violation,
        solver_threads=solver_specification.threads,
        configured_mip_relative_gap=solver_specification.mip_relative_gap,
    )
    if not audit.accepted:
        raise RuntimeError(
            "RTS-GMLC normal-state SCUC was not accepted: "
            f"{audit.termination_condition}; status={audit.solver_status}; "
            f"message={audit.solver_message}"
        )
    return (
        context,
        model,
        audit,
        _derive_initial_state(model, context),
        _extract_branch_flows(model, context, "normal"),
    )
