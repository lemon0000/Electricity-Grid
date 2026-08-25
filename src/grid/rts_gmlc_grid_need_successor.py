"""RQ2 grid-need successor with explicit exogenous infeasibility states."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite, radians
from typing import Any

from pyomo.environ import (
    ConcreteModel,
    ConstraintList,
    NonNegativeReals,
    Objective,
    Set,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from src.grid.rts_gmlc_grid_need import (
    RtsGmlcHourlyGridNeed,
    _constraint_violation,
    _finite,
    _generator_bounds,
    _validate,
)
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
from src.solvers.rq2_solver_adapter import (
    Rq2SolverSpec,
    create_solver,
    model_scale,
)

FINITE_GRID_NEED = "finite_grid_need"
EXOGENOUS_GRID_INFEASIBILITY = "exogenous_grid_infeasibility"
UNRESOLVED_GRID_NEED = "unresolved_grid_need"

_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}
_PROVEN_INFEASIBLE = {TerminationCondition.infeasible}


@dataclass(frozen=True)
class RtsGmlcGridNeedAssessment:
    state: str
    resolved_for_pipeline: bool
    primary: RtsGmlcHourlyGridNeed
    primary_certificate: RtsGmlcCorrectiveSolveCertificate
    zero_dc_confirmation: RtsGmlcHourlyGridNeed | None
    zero_dc_confirmation_certificate: RtsGmlcCorrectiveSolveCertificate | None
    solver_name: str
    solver_options: dict[str, float | int]


@dataclass(frozen=True)
class RtsGmlcCorrectiveSolveCertificate:
    objective_incumbent_mw: float | None
    lower_bound_mw: float | None
    upper_bound_mw: float | None
    absolute_gap_mw: float | None
    relative_gap: float | None
    gap_tolerance_mw: float | None
    model_variables: int
    model_constraints: int


def _optional_finite(raw: object | None) -> float | None:
    if raw is None:
        return None
    value_ = float(raw)
    return value_ if isfinite(value_) else None


def _build_corrective_model(
    data: Any,
    point: Any,
    baseline_generation_mw: Mapping[str, float],
    baseline_commitment: Mapping[str, bool],
    event: N1OutageEvent,
    *,
    dc_bus: int,
    dc_demand_mw: float,
) -> ConcreteModel:
    _validate(
        data,
        point,
        baseline_generation_mw,
        baseline_commitment,
        event,
        dc_bus=dc_bus,
        dc_demand_mw=dc_demand_mw,
    )
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

    def generation_bounds(_: object, uid: str) -> tuple[float, float]:
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
    return model


def _solve_corrective_model(
    data: Any,
    point: Any,
    baseline_generation_mw: Mapping[str, float],
    baseline_commitment: Mapping[str, bool],
    event: N1OutageEvent | None,
    *,
    source_hour: int,
    dc_bus: int,
    dc_demand_mw: float,
    solver_specification: Rq2SolverSpec,
    tolerance_mw: float,
) -> tuple[
    RtsGmlcHourlyGridNeed,
    RtsGmlcCorrectiveSolveCertificate,
    dict[str, float | int],
]:
    if event is None:
        return (
            RtsGmlcHourlyGridNeed(
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
            ),
            RtsGmlcCorrectiveSolveCertificate(
                objective_incumbent_mw=0.0,
                lower_bound_mw=0.0,
                upper_bound_mw=0.0,
                absolute_gap_mw=0.0,
                relative_gap=0.0,
                gap_tolerance_mw=0.0,
                model_variables=0,
                model_constraints=0,
            ),
            {},
        )
    model = _build_corrective_model(
        data,
        point,
        baseline_generation_mw,
        baseline_commitment,
        event,
        dc_bus=dc_bus,
        dc_demand_mw=dc_demand_mw,
    )
    scale = model_scale(model)
    solver, options = create_solver(solver_specification)
    result = solver.solve(
        model,
        load_solutions=False,
        tee=solver_specification.tee,
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
            tolerance_mw,
            solver_specification.mip_relative_gap * max(abs(upper), 1.0),
        )
        if upper is not None
        else None
    )
    if termination not in _OPTIMAL:
        return (
            RtsGmlcHourlyGridNeed(
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
            ),
            RtsGmlcCorrectiveSolveCertificate(
                objective_incumbent_mw=None,
                lower_bound_mw=lower,
                upper_bound_mw=upper,
                absolute_gap_mw=gap,
                relative_gap=relative_gap,
                gap_tolerance_mw=gap_tolerance,
                model_variables=scale.variables,
                model_constraints=scale.constraints,
            ),
            options,
        )
    model.solutions.load_from(result)
    violation = _constraint_violation(model)
    curtailment = float(value(model.curtailment))
    resolved = (
        violation <= tolerance_mw
        and -tolerance_mw <= curtailment <= dc_demand_mw + tolerance_mw
        and lower is not None
        and upper is not None
        and gap is not None
        and gap_tolerance is not None
        and gap <= gap_tolerance
        and abs(curtailment - upper) <= gap_tolerance
    )
    return (
        RtsGmlcHourlyGridNeed(
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
        ),
        RtsGmlcCorrectiveSolveCertificate(
            objective_incumbent_mw=curtailment,
            lower_bound_mw=lower,
            upper_bound_mw=upper,
            absolute_gap_mw=gap,
            relative_gap=relative_gap,
            gap_tolerance_mw=gap_tolerance,
            model_variables=scale.variables,
            model_constraints=scale.constraints,
        ),
        options,
    )


def assess_hourly_rts_gmlc_grid_need(
    data: Any,
    point: Any,
    baseline_generation_mw: Mapping[str, float],
    baseline_commitment: Mapping[str, bool],
    event: N1OutageEvent | None,
    *,
    source_hour: int,
    dc_bus: int,
    dc_demand_mw: float,
    solver_specification: Rq2SolverSpec,
    tolerance_mw: float = 1.0e-6,
) -> RtsGmlcGridNeedAssessment:
    """Classify finite grid need, exogenous infeasibility, or unresolved solve."""

    primary, primary_certificate, options = _solve_corrective_model(
        data,
        point,
        baseline_generation_mw,
        baseline_commitment,
        event,
        source_hour=source_hour,
        dc_bus=dc_bus,
        dc_demand_mw=dc_demand_mw,
        solver_specification=solver_specification,
        tolerance_mw=tolerance_mw,
    )
    if primary.resolved:
        return RtsGmlcGridNeedAssessment(
            state=FINITE_GRID_NEED,
            resolved_for_pipeline=True,
            primary=primary,
            primary_certificate=primary_certificate,
            zero_dc_confirmation=None,
            zero_dc_confirmation_certificate=None,
            solver_name=solver_specification.name,
            solver_options=options,
        )
    if not primary.proven_infeasible:
        return RtsGmlcGridNeedAssessment(
            state=UNRESOLVED_GRID_NEED,
            resolved_for_pipeline=False,
            primary=primary,
            primary_certificate=primary_certificate,
            zero_dc_confirmation=None,
            zero_dc_confirmation_certificate=None,
            solver_name=solver_specification.name,
            solver_options=options,
        )
    zero_dc, zero_dc_certificate, zero_options = _solve_corrective_model(
        data,
        point,
        baseline_generation_mw,
        baseline_commitment,
        event,
        source_hour=source_hour,
        dc_bus=dc_bus,
        dc_demand_mw=0.0,
        solver_specification=solver_specification,
        tolerance_mw=tolerance_mw,
    )
    state = (
        EXOGENOUS_GRID_INFEASIBILITY
        if zero_dc.proven_infeasible
        else UNRESOLVED_GRID_NEED
    )
    return RtsGmlcGridNeedAssessment(
        state=state,
        resolved_for_pipeline=state == EXOGENOUS_GRID_INFEASIBILITY,
        primary=primary,
        primary_certificate=primary_certificate,
        zero_dc_confirmation=zero_dc,
        zero_dc_confirmation_certificate=zero_dc_certificate,
        solver_name=solver_specification.name,
        solver_options=zero_options,
    )
