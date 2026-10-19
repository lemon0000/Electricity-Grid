"""Minimum POI curtailment for sampled RTS-GMLC N-1 outage hours."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite, radians
from typing import Any

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    ConstraintList,
    NonNegativeReals,
    Objective,
    Set,
    SolverFactory,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent

RTS_GMLC_GRID_NEED_SCOPE = (
    "sampled_N_minus_one_hourly_minimum_POI_curtailment_against_fixed_normal_"
    "commitment_and_dispatch_DC_not_empirical_not_AC_not_security_certification"
)
_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}
_PROVEN_INFEASIBLE = {TerminationCondition.infeasible}
_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class RtsGmlcHourlyGridNeed:
    source_hour: int
    event_id: str | None
    component_type: str | None
    component_uid: str | None
    resolved: bool
    proven_infeasible: bool
    grid_need_mw: float | None
    termination_condition: str
    solver_status: str
    maximum_constraint_violation: float | None


def _finite(raw: object, label: str) -> float:
    try:
        number = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _constraint_violation(model: ConcreteModel) -> float:
    maximum = 0.0
    for constraint in model.component_data_objects(
        Constraint,
        active=True,
        descend_into=True,
    ):
        body = value(constraint.body, exception=False)
        if body is None or not isfinite(float(body)):
            return float("inf")
        body = float(body)
        if constraint.lower is not None:
            maximum = max(maximum, float(value(constraint.lower)) - body)
        if constraint.upper is not None:
            maximum = max(maximum, body - float(value(constraint.upper)))
    for variable in model.component_data_objects(
        Var,
        active=True,
        descend_into=True,
    ):
        candidate = value(variable, exception=False)
        if candidate is None or not isfinite(float(candidate)):
            return float("inf")
        candidate = float(candidate)
        if variable.lb is not None:
            maximum = max(maximum, float(variable.lb) - candidate)
        if variable.ub is not None:
            maximum = max(maximum, candidate - float(variable.ub))
    return max(maximum, 0.0)


def _generator_bounds(point: Any, generator: Any) -> tuple[float, float]:
    lower = _finite(point.generator_min_mw[generator.uid], "generator minimum")
    upper = _finite(point.generator_max_mw[generator.uid], "generator maximum")
    if lower < 0.0 or upper < lower:
        raise ValueError(f"invalid generator bounds for {generator.uid}")
    return lower, upper


def _validate(
    data: Any,
    point: Any,
    baseline_generation_mw: Mapping[str, float],
    baseline_commitment: Mapping[str, bool],
    event: N1OutageEvent,
    *,
    dc_bus: int,
    dc_demand_mw: float,
) -> None:
    generators = {item.uid: item for item in data.generators}
    branches = {item.uid: item for item in data.branches}
    if set(baseline_generation_mw) != set(generators):
        raise ValueError("baseline generation keys must match RTS-GMLC")
    if set(baseline_commitment) != set(generators):
        raise ValueError("baseline commitment keys must match RTS-GMLC")
    if dc_bus not in {int(item.uid) for item in data.buses}:
        raise ValueError("dc_bus is absent from RTS-GMLC")
    if _finite(dc_demand_mw, "dc_demand_mw") < 0.0:
        raise ValueError("dc_demand_mw must be nonnegative")
    if event.component_type == "generator":
        if event.uid not in generators or not generators[event.uid].enabled:
            raise ValueError("generator outage is unknown or disabled")
    elif event.component_type == "branch":
        if event.uid not in branches:
            raise ValueError("branch outage is unknown")
    else:
        raise ValueError("event component_type must be branch or generator")
    for uid, generator in generators.items():
        baseline = _finite(baseline_generation_mw[uid], f"baseline {uid}")
        if baseline < 0.0:
            raise ValueError("baseline generation must be nonnegative")
        if not isinstance(baseline_commitment[uid], bool):
            raise TypeError("baseline commitment values must be boolean")
        _generator_bounds(point, generator)


def derive_hourly_rts_gmlc_grid_need(
    data: Any,
    point: Any,
    baseline_generation_mw: Mapping[str, float],
    baseline_commitment: Mapping[str, bool],
    event: N1OutageEvent | None,
    *,
    source_hour: int,
    dc_bus: int,
    dc_demand_mw: float,
    solver_name: str = "highs",
    tee: bool = False,
    tolerance_mw: float = _TOLERANCE,
) -> RtsGmlcHourlyGridNeed:
    """Minimize required DC curtailment for one sampled sustained outage."""

    if event is None:
        return RtsGmlcHourlyGridNeed(
            source_hour=source_hour,
            event_id=None,
            component_type=None,
            component_uid=None,
            resolved=True,
            proven_infeasible=False,
            grid_need_mw=0.0,
            termination_condition="not_applicable_no_active_outage",
            solver_status="not_applicable",
            maximum_constraint_violation=0.0,
        )
    _validate(
        data,
        point,
        baseline_generation_mw,
        baseline_commitment,
        event,
        dc_bus=dc_bus,
        dc_demand_mw=dc_demand_mw,
    )
    tolerance = _finite(tolerance_mw, "tolerance_mw")
    if tolerance <= 0.0:
        raise ValueError("tolerance_mw must be positive")
    buses = {int(item.uid): item for item in data.buses}
    generators = {item.uid: item for item in data.generators}
    branches = {item.uid: item for item in data.branches}
    dc_branches = {item.uid: item for item in data.dc_branches}
    generators_at_bus = {bus: [] for bus in buses}
    outgoing = {bus: [] for bus in buses}
    incoming = {bus: [] for bus in buses}
    outgoing_dc = {bus: [] for bus in buses}
    incoming_dc = {bus: [] for bus in buses}
    for generator in generators.values():
        generators_at_bus[int(generator.bus)].append(generator.uid)
    for branch in branches.values():
        outgoing[int(branch.from_bus)].append(branch.uid)
        incoming[int(branch.to_bus)].append(branch.uid)
    for branch in dc_branches.values():
        outgoing_dc[int(branch.from_bus)].append(branch.uid)
        incoming_dc[int(branch.to_bus)].append(branch.uid)

    def generation_bounds(_, uid):
        generator = generators[uid]
        if not generator.enabled or (
            event.component_type == "generator" and event.uid == uid
        ):
            return 0.0, 0.0
        lower, upper = _generator_bounds(point, generator)
        if generator.dispatch_mode == "committable":
            return (lower, upper) if baseline_commitment[uid] else (0.0, 0.0)
        if generator.dispatch_mode == "fixed":
            return upper, upper
        if generator.dispatch_mode == "curtailable":
            return lower, upper
        return 0.0, 0.0

    model = ConcreteModel()
    model.BUS = Set(initialize=tuple(buses), ordered=True)
    model.GEN = Set(initialize=tuple(generators), ordered=True)
    model.BRANCH = Set(initialize=tuple(branches), ordered=True)
    model.DC_BRANCH = Set(initialize=tuple(dc_branches), ordered=True)
    model.generation = Var(
        model.GEN,
        domain=NonNegativeReals,
        bounds=generation_bounds,
    )
    model.angle_degrees = Var(model.BUS)
    model.branch_flow = Var(model.BRANCH)
    model.dc_flow = Var(
        model.DC_BRANCH,
        bounds=lambda _, uid: (
            _finite(dc_branches[uid].p_min_mw, "DC branch minimum"),
            _finite(dc_branches[uid].p_max_mw, "DC branch maximum"),
        ),
    )
    model.curtailment = Var(
        domain=NonNegativeReals,
        bounds=(0.0, float(dc_demand_mw)),
    )
    model.flow_equations = ConstraintList()
    for uid, branch in branches.items():
        if event.component_type == "branch" and event.uid == uid:
            model.flow_equations.add(model.branch_flow[uid] == 0.0)
            continue
        rating = _finite(branch.continuous_rating_mw, "branch rating")
        model.branch_flow[uid].setlb(-rating)
        model.branch_flow[uid].setub(rating)
        coefficient = _finite(data.base_mva, "base_mva") / (
            _finite(branch.reactance_pu, "branch reactance")
            * _finite(branch.tap_ratio, "branch tap ratio")
        )
        model.flow_equations.add(
            model.branch_flow[uid]
            == coefficient
            * radians(1.0)
            * (
                model.angle_degrees[int(branch.from_bus)]
                - model.angle_degrees[int(branch.to_bus)]
            )
        )
    model.angle_degrees[int(data.reference_bus)].fix(0.0)
    model.redispatch = ConstraintList()
    for uid, generator in generators.items():
        if not generator.enabled or (
            event.component_type == "generator" and event.uid == uid
        ):
            continue
        if generator.dispatch_mode == "fixed":
            continue
        limit = _finite(generator.ramp_mw_per_hour, "generator hourly ramp")
        baseline = float(baseline_generation_mw[uid])
        model.redispatch.add(model.generation[uid] - baseline <= limit)
        model.redispatch.add(baseline - model.generation[uid] <= limit)
    model.balance = ConstraintList()
    for bus in buses:
        generation = sum(model.generation[uid] for uid in generators_at_bus[bus])
        ac_export = sum(model.branch_flow[uid] for uid in outgoing[bus]) - sum(
            model.branch_flow[uid] for uid in incoming[bus]
        )
        dc_export = sum(model.dc_flow[uid] for uid in outgoing_dc[bus]) - sum(
            model.dc_flow[uid] for uid in incoming_dc[bus]
        )
        demand = _finite(point.demand_by_bus_mw[bus], "bus demand")
        if bus == dc_bus:
            demand += float(dc_demand_mw) - model.curtailment
        model.balance.add(generation - demand == ac_export + dc_export)
    model.objective = Objective(expr=model.curtailment, sense=minimize)

    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    result = solver.solve(model, load_solutions=False, tee=tee)
    termination = result.solver.termination_condition
    if termination not in _OPTIMAL:
        return RtsGmlcHourlyGridNeed(
            source_hour=source_hour,
            event_id=event.event_id,
            component_type=event.component_type,
            component_uid=event.uid,
            resolved=False,
            proven_infeasible=termination in _PROVEN_INFEASIBLE,
            grid_need_mw=None,
            termination_condition=str(termination),
            solver_status=str(result.solver.status),
            maximum_constraint_violation=None,
        )
    model.solutions.load_from(result)
    violation = _constraint_violation(model)
    curtailment = float(value(model.curtailment))
    resolved = violation <= tolerance and -tolerance <= curtailment <= (
        float(dc_demand_mw) + tolerance
    )
    return RtsGmlcHourlyGridNeed(
        source_hour=source_hour,
        event_id=event.event_id,
        component_type=event.component_type,
        component_uid=event.uid,
        resolved=resolved,
        proven_infeasible=False,
        grid_need_mw=max(curtailment, 0.0) if resolved else None,
        termination_condition=(
            str(termination) if resolved else "solution_audit_failed"
        ),
        solver_status=str(result.solver.status),
        maximum_constraint_violation=violation,
    )
