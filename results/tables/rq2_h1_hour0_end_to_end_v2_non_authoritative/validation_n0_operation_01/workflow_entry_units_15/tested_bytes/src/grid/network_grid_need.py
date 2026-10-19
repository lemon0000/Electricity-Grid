"""Derive RQ2 network curtailment needs from selected sustained N-1 states.

Two deliberately separate definitions are exposed:

``minimum_curtailment``
    The primary definition. For each selected N-1 state, solve the DC
    corrective-dispatch problem with all branch limits hard and one POI
    curtailment variable. The scenario need is the maximum state-wise minimum
    curtailment.

``overload_sensitivity``
    A diagnostic comparator. Apply the outage-topology POI PTDF to every
    unconstrained corrective-state branch flow and minimize the curtailment
    estimate required to bring all estimated post-curtailment flows within
    rating. A non-relieving sensitivity fails closed.

Both definitions are derived DC benchmark quantities. They are not empirical
outage observations, full-N-1 certification, AC feasibility evidence, or
engineering security certificates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import copysign, isfinite, radians
from numbers import Real

import numpy as np
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

from .dc_opf import solve_dc_opf
from .rts24 import Rts24Data, scale_rts24_demand
from .scopf import SecurityState, non_islanding_branch_indices

METHOD_MINIMUM_CURTAILMENT = "minimum_curtailment"
METHOD_OVERLOAD_SENSITIVITY = "overload_sensitivity"
NETWORK_GRID_NEED_METHODS = (
    METHOD_MINIMUM_CURTAILMENT,
    METHOD_OVERLOAD_SENSITIVITY,
)
NETWORK_GRID_NEED_SCOPE = (
    "derived_selected_sustained_n1_dc_not_empirical_not_ac_"
    "not_engineering_security_certification"
)

_TOLERANCE = 1.0e-8
NETWORK_GRID_NEED_AUDIT_TOLERANCE_MW = 1.0e-6
_OPTIMAL_TERMINATIONS = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
    TerminationCondition.locallyOptimal,
}


@dataclass(frozen=True)
class NetworkGridNeedInputs:
    data: Rts24Data
    poi_bus: int
    balancing_bus: int
    system_load_multiplier: float
    data_center_demand_mw: float
    branch_indices: tuple[int, ...]
    generator_indices: tuple[int, ...]
    redispatch_fraction_of_pmax: float
    sustained_rating: str
    method: str
    parameter_status: str
    solver_name: str = "highs"
    tee: bool = False


@dataclass(frozen=True)
class NetworkGridNeedStateResult:
    state_name: str
    feasible: bool
    physically_deliverable: bool
    proven_infeasible: bool
    termination_condition: str
    solver_status: str
    minimum_curtailment_mw: float | None
    peak_overload_mw: float | None
    critical_branch_index: int | None
    poi_relief_sensitivity: float | None
    estimated_curtailment_mw: float | None
    maximum_balance_residual_mw: float | None
    maximum_thermal_violation_mw: float | None
    maximum_generation_bound_violation_mw: float | None
    maximum_redispatch_violation_mw: float | None
    maximum_outage_generation_mw: float | None
    maximum_flow_equation_residual_mw: float | None
    curtailment_bound_violation_mw: float | None


@dataclass(frozen=True)
class NetworkGridNeedResult:
    feasible: bool
    direct_physical_dispatch_witness: bool
    proven_infeasible: bool
    method: str
    grid_need_mw: float | None
    critical_state: str | None
    state_results: dict[str, NetworkGridNeedStateResult]
    base_dispatch_objective: float | None
    base_termination_condition: str
    base_solver_status: str
    base_maximum_balance_residual_mw: float | None
    base_maximum_thermal_violation_mw: float | None
    base_maximum_generation_bound_violation_mw: float | None
    base_maximum_flow_equation_residual_mw: float | None
    poi_bus: int
    balancing_bus: int
    parameter_status: str
    security_certified: bool
    scope: str


@dataclass(frozen=True)
class _SolvedState:
    feasible: bool
    proven_infeasible: bool
    termination_condition: str
    solver_status: str
    curtailment_mw: float | None
    generation_mw: dict[int, float]
    bus_angles_rad: dict[int, float]
    branch_flows_mw: dict[int, float]
    maximum_balance_residual_mw: float | None
    maximum_generation_bound_violation_mw: float | None
    maximum_redispatch_violation_mw: float | None
    maximum_outage_generation_mw: float | None
    maximum_flow_equation_residual_mw: float | None
    curtailment_bound_violation_mw: float | None


def _finite(name: str, raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(raw):
        raise ValueError(f"{name} must be a finite number")
    return float(raw)


def _nonnegative(name: str, raw: object) -> float:
    number = _finite(name, raw)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _audit_passes(values: tuple[float | None, ...]) -> bool:
    return bool(values) and all(
        value is not None
        and isfinite(value)
        and value >= 0.0
        and value <= NETWORK_GRID_NEED_AUDIT_TOLERANCE_MW
        for value in values
    )


def _audit_max(values) -> float:
    numbers = tuple(float(item) for item in values)
    if not all(isfinite(item) for item in numbers):
        return float("nan")
    return max(numbers, default=0.0)


def _positive_part(raw: float) -> float:
    number = float(raw)
    return max(number, 0.0) if isfinite(number) else float("nan")


def _validate_inputs(inputs: NetworkGridNeedInputs) -> tuple[SecurityState, ...]:
    data = inputs.data
    bus_indices = {bus.index for bus in data.buses}
    branch_by_index = {branch.index: branch for branch in data.branches}
    generator_by_index = {generator.index: generator for generator in data.generators}

    if inputs.poi_bus not in bus_indices:
        raise ValueError(f"Unknown POI bus {inputs.poi_bus}")
    if inputs.balancing_bus not in bus_indices:
        raise ValueError(f"Unknown balancing bus {inputs.balancing_bus}")
    if inputs.poi_bus == inputs.balancing_bus:
        raise ValueError("POI bus and balancing bus must differ")
    if inputs.method not in NETWORK_GRID_NEED_METHODS:
        raise ValueError(f"Unknown network grid-need method '{inputs.method}'")
    if not inputs.parameter_status:
        raise ValueError("parameter_status must be explicit")
    if not inputs.solver_name:
        raise ValueError("solver_name must be explicit")
    _nonnegative("system_load_multiplier", inputs.system_load_multiplier)
    _nonnegative("data_center_demand_mw", inputs.data_center_demand_mw)
    _nonnegative(
        "redispatch_fraction_of_pmax", inputs.redispatch_fraction_of_pmax
    )
    if len(set(inputs.branch_indices)) != len(inputs.branch_indices):
        raise ValueError("branch_indices must not contain duplicates")
    if len(set(inputs.generator_indices)) != len(inputs.generator_indices):
        raise ValueError("generator_indices must not contain duplicates")
    if not inputs.branch_indices and not inputs.generator_indices:
        raise ValueError("At least one selected N-1 state is required")
    unknown_branches = set(inputs.branch_indices) - branch_by_index.keys()
    if unknown_branches:
        raise ValueError(f"Unknown branch indices: {sorted(unknown_branches)}")
    unknown_generators = set(inputs.generator_indices) - generator_by_index.keys()
    if unknown_generators:
        raise ValueError(f"Unknown generator indices: {sorted(unknown_generators)}")
    invalid_generators = sorted(
        index
        for index in inputs.generator_indices
        if not generator_by_index[index].in_service
        or generator_by_index[index].p_max_mw <= 0.0
    )
    if invalid_generators:
        raise ValueError(
            "Selected generator contingencies must be online with positive "
            f"capacity: {invalid_generators}"
        )
    non_islanding = set(non_islanding_branch_indices(data))
    islanding = sorted(set(inputs.branch_indices) - non_islanding)
    if islanding:
        raise ValueError(
            f"Selected N-1 branch set contains islanding branches: {islanding}"
        )
    for branch in data.branches:
        branch.rating_mw(inputs.sustained_rating)

    states = [
        SecurityState(
            name=f"branch_{index}_sustained",
            kind="branch",
            element_index=index,
            branch_rating=inputs.sustained_rating,
            outaged_branch_indices=frozenset((index,)),
            outaged_generator_indices=frozenset(),
            response_mode="bounded",
        )
        for index in inputs.branch_indices
    ]
    states.extend(
        SecurityState(
            name=f"generator_{index}_sustained",
            kind="generator",
            element_index=index,
            branch_rating=inputs.sustained_rating,
            outaged_branch_indices=frozenset(),
            outaged_generator_indices=frozenset((index,)),
            response_mode="bounded",
        )
        for index in inputs.generator_indices
    )
    return tuple(states)


def _operating_data(inputs: NetworkGridNeedInputs) -> Rts24Data:
    scaled = scale_rts24_demand(inputs.data, inputs.system_load_multiplier)
    return replace(
        scaled,
        buses=tuple(
            replace(
                bus,
                demand_mw=(
                    bus.demand_mw + inputs.data_center_demand_mw
                    if bus.index == inputs.poi_bus
                    else bus.demand_mw
                ),
            )
            for bus in scaled.buses
        ),
    )


def _redispatch_limits(
    data: Rts24Data, fraction: float
) -> dict[int, float]:
    return {
        generator.index: fraction * generator.p_max_mw
        for generator in data.generators
    }


def _maximum_flow_equation_residual(
    data: Rts24Data,
    angles_rad: Mapping[int, float],
    flows_mw: Mapping[int, float],
    outaged_branch_indices: frozenset[int],
) -> float:
    residuals = []
    for branch in data.branches:
        if not branch.in_service or branch.index in outaged_branch_indices:
            expected = 0.0
        else:
            susceptance = data.base_mva / (
                branch.reactance_pu * branch.tap_ratio
            )
            expected = susceptance * (
                angles_rad[branch.from_bus]
                - angles_rad[branch.to_bus]
                - branch.phase_shift_rad
            )
        residuals.append(abs(flows_mw[branch.index] - expected))
    return _audit_max(residuals)


def _base_audit(
    data: Rts24Data, base, branch_rating: str
) -> tuple[float, float, float, float]:
    balance = _audit_max(
        abs(residual) for residual in base.power_balance_residuals_mw.values()
    )
    thermal = _audit_max(
        _positive_part(
                abs(base.branch_flows_mw[branch.index])
                - branch.rating_mw(branch_rating)
        )
        for branch in data.branches
        if branch.in_service
    )
    generation = _audit_max(
        
            _positive_part(
                generator.p_min_mw - base.generation_mw[generator.index],
            )
            + _positive_part(
                base.generation_mw[generator.index] - generator.p_max_mw
            )
            if generator.in_service
            else abs(base.generation_mw[generator.index])
            for generator in data.generators
        
    )
    flow = _maximum_flow_equation_residual(
        data,
        base.bus_angles_rad,
        base.branch_flows_mw,
        frozenset(),
    )
    return balance, thermal, generation, flow


def _solve_state(
    data: Rts24Data,
    state: SecurityState,
    *,
    base_generation_mw: Mapping[int, float],
    redispatch_limits_mw: Mapping[int, float],
    poi_bus: int,
    maximum_curtailment_mw: float,
    enforce_thermal_limits: bool,
    sensitivity_by_branch: Mapping[int, float] | None,
    solver_name: str,
    tee: bool,
) -> _SolvedState:
    bus_by_index = {bus.index: bus for bus in data.buses}
    generator_by_index = {generator.index: generator for generator in data.generators}
    branch_by_index = {branch.index: branch for branch in data.branches}
    bus_indices = tuple(bus_by_index)
    generator_indices = tuple(generator_by_index)
    branch_indices = tuple(branch_by_index)
    generators_at_bus = {bus: [] for bus in bus_indices}
    outgoing_at_bus = {bus: [] for bus in bus_indices}
    incoming_at_bus = {bus: [] for bus in bus_indices}
    for generator in data.generators:
        generators_at_bus[generator.bus].append(generator.index)
    for branch in data.branches:
        outgoing_at_bus[branch.from_bus].append(branch.index)
        incoming_at_bus[branch.to_bus].append(branch.index)

    model = ConcreteModel()
    model.BUS = Set(initialize=bus_indices, ordered=True)
    model.GEN = Set(initialize=generator_indices, ordered=True)
    model.BRANCH = Set(initialize=branch_indices, ordered=True)

    def generation_bounds(_model: ConcreteModel, index: int) -> tuple[float, float]:
        generator = generator_by_index[index]
        if not generator.in_service or index in state.outaged_generator_indices:
            return 0.0, 0.0
        limit = redispatch_limits_mw[index]
        lower = max(generator.p_min_mw, base_generation_mw[index] - limit)
        upper = min(generator.p_max_mw, base_generation_mw[index] + limit)
        if lower > upper + _TOLERANCE:
            raise ValueError(f"Inconsistent redispatch bounds for generator {index}")
        return lower, upper

    def flow_bounds(_model: ConcreteModel, index: int):
        if not enforce_thermal_limits:
            return None, None
        rating = branch_by_index[index].rating_mw(state.branch_rating)
        return -rating, rating

    model.generation = Var(model.GEN, bounds=generation_bounds)
    model.angle = Var(model.BUS)
    model.flow = Var(model.BRANCH, bounds=flow_bounds)
    if enforce_thermal_limits:
        model.curtailment = Var(
            domain=NonNegativeReals, bounds=(0.0, maximum_curtailment_mw)
        )
    else:
        model.estimated_curtailment = Var(domain=NonNegativeReals)

    def branch_flow_rule(model: ConcreteModel, index: int):
        branch = branch_by_index[index]
        if not branch.in_service or index in state.outaged_branch_indices:
            return model.flow[index] == 0.0
        susceptance = data.base_mva / (branch.reactance_pu * branch.tap_ratio)
        return model.flow[index] == susceptance * (
            radians(1.0)
            * (model.angle[branch.from_bus] - model.angle[branch.to_bus])
            - branch.phase_shift_rad
        )

    model.branch_flow = Constraint(model.BRANCH, rule=branch_flow_rule)

    def balance_rule(model: ConcreteModel, bus: int):
        generation = sum(model.generation[g] for g in generators_at_bus[bus])
        outgoing = sum(model.flow[b] for b in outgoing_at_bus[bus])
        incoming = sum(model.flow[b] for b in incoming_at_bus[bus])
        curtailment = (
            model.curtailment
            if enforce_thermal_limits and bus == poi_bus
            else 0.0
        )
        return generation - bus_by_index[bus].demand_mw + curtailment == (
            outgoing - incoming
        )

    model.power_balance = Constraint(model.BUS, rule=balance_rule)
    model.angle[data.reference_bus].fix(0.0)

    if enforce_thermal_limits:
        model.objective = Objective(expr=model.curtailment, sense=minimize)
    else:
        if sensitivity_by_branch is None:
            raise ValueError("Sensitivity method requires branch sensitivities")
        model.sensitivity_thermal_limits = ConstraintList()
        for branch in data.branches:
            if (
                not branch.in_service
                or branch.index in state.outaged_branch_indices
            ):
                continue
            rating = branch.rating_mw(state.branch_rating)
            estimated_flow = (
                model.flow[branch.index]
                + sensitivity_by_branch[branch.index]
                * model.estimated_curtailment
            )
            model.sensitivity_thermal_limits.add(estimated_flow <= rating)
            model.sensitivity_thermal_limits.add(-estimated_flow <= rating)
        model.objective = Objective(
            expr=model.estimated_curtailment, sense=minimize
        )

    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    raw = solver.solve(model, load_solutions=False, tee=tee)
    termination = raw.solver.termination_condition
    if termination not in _OPTIMAL_TERMINATIONS:
        return _SolvedState(
            feasible=False,
            proven_infeasible=termination == TerminationCondition.infeasible,
            termination_condition=str(termination),
            solver_status=str(raw.solver.status),
            curtailment_mw=None,
            generation_mw={},
            bus_angles_rad={},
            branch_flows_mw={},
            maximum_balance_residual_mw=None,
            maximum_generation_bound_violation_mw=None,
            maximum_redispatch_violation_mw=None,
            maximum_outage_generation_mw=None,
            maximum_flow_equation_residual_mw=None,
            curtailment_bound_violation_mw=None,
        )

    model.solutions.load_from(raw)
    generation = {
        index: float(value(model.generation[index])) for index in generator_indices
    }
    angles = {
        index: radians(float(value(model.angle[index]))) for index in bus_indices
    }
    flows = {index: float(value(model.flow[index])) for index in branch_indices}
    curtailment_component = (
        model.curtailment
        if enforce_thermal_limits
        else model.estimated_curtailment
    )
    curtailment = max(0.0, float(value(curtailment_component)))
    residuals = []
    for bus in bus_indices:
        generation_at_bus = sum(generation[g] for g in generators_at_bus[bus])
        outgoing = sum(flows[b] for b in outgoing_at_bus[bus])
        incoming = sum(flows[b] for b in incoming_at_bus[bus])
        relief = curtailment if bus == poi_bus and enforce_thermal_limits else 0.0
        residuals.append(
            generation_at_bus
            - bus_by_index[bus].demand_mw
            + relief
            - outgoing
            + incoming
        )
    generation_bound_violations = []
    redispatch_violations = []
    outage_generation = []
    for generator in data.generators:
        output = generation[generator.index]
        if (
            not generator.in_service
            or generator.index in state.outaged_generator_indices
        ):
            generation_bound_violations.append(abs(output))
            if generator.index in state.outaged_generator_indices:
                outage_generation.append(abs(output))
            continue
        generation_bound_violations.append(
            _positive_part(generator.p_min_mw - output)
            + _positive_part(output - generator.p_max_mw)
        )
        redispatch_violations.append(
            _positive_part(
                abs(output - base_generation_mw[generator.index])
                - redispatch_limits_mw[generator.index]
            )
        )
    curtailment_bound_violation = (
        _audit_max(
            (
                _positive_part(-curtailment),
                _positive_part(curtailment - maximum_curtailment_mw),
            )
        )
        if enforce_thermal_limits
        else 0.0
    )
    return _SolvedState(
        feasible=True,
        proven_infeasible=False,
        termination_condition=str(termination),
        solver_status=str(raw.solver.status),
        curtailment_mw=curtailment,
        generation_mw=generation,
        bus_angles_rad=angles,
        branch_flows_mw=flows,
        maximum_balance_residual_mw=_audit_max(abs(item) for item in residuals),
        maximum_generation_bound_violation_mw=_audit_max(
            generation_bound_violations
        ),
        maximum_redispatch_violation_mw=_audit_max(redispatch_violations),
        maximum_outage_generation_mw=_audit_max(outage_generation),
        maximum_flow_equation_residual_mw=_maximum_flow_equation_residual(
            data, angles, flows, state.outaged_branch_indices
        ),
        curtailment_bound_violation_mw=curtailment_bound_violation,
    )


def _poi_transfer_sensitivities(
    data: Rts24Data,
    *,
    outaged_branch_indices: frozenset[int],
    poi_bus: int,
    balancing_bus: int,
) -> dict[int, float]:
    """Return branch-flow change per MW of POI curtailment.

    Curtailment is represented as +1 MW injection at the POI and -1 MW
    withdrawal at the declared balancing bus. The outage set has already been
    checked to keep the network connected.
    """

    buses = tuple(bus.index for bus in data.buses)
    position = {bus: index for index, bus in enumerate(buses)}
    laplacian = np.zeros((len(buses), len(buses)), dtype=float)
    for branch in data.branches:
        if not branch.in_service or branch.index in outaged_branch_indices:
            continue
        susceptance = data.base_mva / (branch.reactance_pu * branch.tap_ratio)
        left = position[branch.from_bus]
        right = position[branch.to_bus]
        laplacian[left, left] += susceptance
        laplacian[right, right] += susceptance
        laplacian[left, right] -= susceptance
        laplacian[right, left] -= susceptance

    injections = np.zeros(len(buses), dtype=float)
    injections[position[poi_bus]] = 1.0
    injections[position[balancing_bus]] = -1.0
    slack = position[balancing_bus]
    retained = [index for index in range(len(buses)) if index != slack]
    try:
        reduced_angles = np.linalg.solve(
            laplacian[np.ix_(retained, retained)], injections[retained]
        )
    except np.linalg.LinAlgError as error:
        raise ValueError("Selected outage topology is singular or islanded") from error
    angles = np.zeros(len(buses), dtype=float)
    angles[retained] = reduced_angles

    sensitivities = {}
    for branch in data.branches:
        if not branch.in_service or branch.index in outaged_branch_indices:
            sensitivities[branch.index] = 0.0
            continue
        susceptance = data.base_mva / (branch.reactance_pu * branch.tap_ratio)
        sensitivities[branch.index] = susceptance * (
            angles[position[branch.from_bus]] - angles[position[branch.to_bus]]
        )
    return sensitivities


def _thermal_violation(
    data: Rts24Data,
    state: SecurityState,
    flows: Mapping[int, float],
) -> float:
    return _audit_max(
        _positive_part(
                abs(flows[branch.index])
                - branch.rating_mw(state.branch_rating)
        )
        for branch in data.branches
        if branch.in_service
        and branch.index not in state.outaged_branch_indices
    )


def _minimum_curtailment_result(
    data: Rts24Data,
    state: SecurityState,
    solved: _SolvedState,
) -> NetworkGridNeedStateResult:
    violation = (
        _thermal_violation(data, state, solved.branch_flows_mw)
        if solved.feasible
        else None
    )
    return NetworkGridNeedStateResult(
        state_name=state.name,
        feasible=solved.feasible,
        physically_deliverable=solved.feasible,
        proven_infeasible=solved.proven_infeasible,
        termination_condition=solved.termination_condition,
        solver_status=solved.solver_status,
        minimum_curtailment_mw=solved.curtailment_mw,
        peak_overload_mw=None,
        critical_branch_index=None,
        poi_relief_sensitivity=None,
        estimated_curtailment_mw=solved.curtailment_mw,
        maximum_balance_residual_mw=solved.maximum_balance_residual_mw,
        maximum_thermal_violation_mw=violation,
        maximum_generation_bound_violation_mw=(
            solved.maximum_generation_bound_violation_mw
        ),
        maximum_redispatch_violation_mw=solved.maximum_redispatch_violation_mw,
        maximum_outage_generation_mw=solved.maximum_outage_generation_mw,
        maximum_flow_equation_residual_mw=(
            solved.maximum_flow_equation_residual_mw
        ),
        curtailment_bound_violation_mw=solved.curtailment_bound_violation_mw,
    )


def _overload_sensitivity_result(
    data: Rts24Data,
    state: SecurityState,
    solved: _SolvedState,
    *,
    poi_bus: int,
    balancing_bus: int,
    maximum_curtailment_mw: float,
) -> NetworkGridNeedStateResult:
    if not solved.feasible:
        return NetworkGridNeedStateResult(
            state_name=state.name,
            feasible=False,
            physically_deliverable=False,
            proven_infeasible=solved.proven_infeasible,
            termination_condition=solved.termination_condition,
            solver_status=solved.solver_status,
            minimum_curtailment_mw=None,
            peak_overload_mw=None,
            critical_branch_index=None,
            poi_relief_sensitivity=None,
            estimated_curtailment_mw=None,
            maximum_balance_residual_mw=None,
            maximum_thermal_violation_mw=None,
            maximum_generation_bound_violation_mw=None,
            maximum_redispatch_violation_mw=None,
            maximum_outage_generation_mw=None,
            maximum_flow_equation_residual_mw=None,
            curtailment_bound_violation_mw=None,
        )

    overloads = {
        branch.index: _positive_part(
            abs(solved.branch_flows_mw[branch.index])
            - branch.rating_mw(state.branch_rating)
        )
        for branch in data.branches
        if branch.in_service and branch.index not in state.outaged_branch_indices
    }
    peak_overload = _audit_max(overloads.values())
    if peak_overload <= _TOLERANCE:
        return NetworkGridNeedStateResult(
            state_name=state.name,
            feasible=True,
            physically_deliverable=True,
            proven_infeasible=False,
            termination_condition=solved.termination_condition,
            solver_status=solved.solver_status,
            minimum_curtailment_mw=None,
            peak_overload_mw=0.0,
            critical_branch_index=None,
            poi_relief_sensitivity=None,
            estimated_curtailment_mw=0.0,
            maximum_balance_residual_mw=solved.maximum_balance_residual_mw,
            maximum_thermal_violation_mw=0.0,
            maximum_generation_bound_violation_mw=(
                solved.maximum_generation_bound_violation_mw
            ),
            maximum_redispatch_violation_mw=solved.maximum_redispatch_violation_mw,
            maximum_outage_generation_mw=solved.maximum_outage_generation_mw,
            maximum_flow_equation_residual_mw=(
                solved.maximum_flow_equation_residual_mw
            ),
            curtailment_bound_violation_mw=0.0,
        )

    sensitivities = _poi_transfer_sensitivities(
        data,
        outaged_branch_indices=state.outaged_branch_indices,
        poi_bus=poi_bus,
        balancing_bus=balancing_bus,
    )
    required_by_branch: dict[int, tuple[float, float]] = {}
    for branch_index, overload in overloads.items():
        if overload <= _TOLERANCE:
            continue
        flow = solved.branch_flows_mw[branch_index]
        relief = -copysign(1.0, flow) * sensitivities[branch_index]
        if relief <= _TOLERANCE:
            return NetworkGridNeedStateResult(
                state_name=state.name,
                feasible=False,
                physically_deliverable=False,
                proven_infeasible=False,
                termination_condition="non_relieving_poi_sensitivity",
                solver_status=solved.solver_status,
                minimum_curtailment_mw=None,
                peak_overload_mw=peak_overload,
                critical_branch_index=branch_index,
                poi_relief_sensitivity=relief,
                estimated_curtailment_mw=None,
                maximum_balance_residual_mw=solved.maximum_balance_residual_mw,
                maximum_thermal_violation_mw=peak_overload,
                maximum_generation_bound_violation_mw=(
                    solved.maximum_generation_bound_violation_mw
                ),
                maximum_redispatch_violation_mw=(
                    solved.maximum_redispatch_violation_mw
                ),
                maximum_outage_generation_mw=solved.maximum_outage_generation_mw,
                maximum_flow_equation_residual_mw=(
                    solved.maximum_flow_equation_residual_mw
                ),
                curtailment_bound_violation_mw=None,
            )
        required_by_branch[branch_index] = (overload / relief, relief)

    critical_branch = max(
        required_by_branch, key=lambda index: required_by_branch[index][0]
    )
    estimated = solved.curtailment_mw
    relief = required_by_branch[critical_branch][1]
    corrected_violation = _audit_max(
        _positive_part(
                abs(
                    solved.branch_flows_mw[branch.index]
                    + sensitivities[branch.index] * estimated
                )
                - branch.rating_mw(state.branch_rating)
        )
        for branch in data.branches
        if branch.in_service
        and branch.index not in state.outaged_branch_indices
    )
    within_poi_load = estimated <= (
        maximum_curtailment_mw + NETWORK_GRID_NEED_AUDIT_TOLERANCE_MW
    )
    return NetworkGridNeedStateResult(
        state_name=state.name,
        feasible=within_poi_load,
        physically_deliverable=within_poi_load and estimated <= _TOLERANCE,
        proven_infeasible=False,
        termination_condition=(
            solved.termination_condition
            if within_poi_load
            else "estimated_curtailment_exceeds_poi_load"
        ),
        solver_status=solved.solver_status,
        minimum_curtailment_mw=None,
        peak_overload_mw=peak_overload,
        critical_branch_index=critical_branch,
        poi_relief_sensitivity=relief,
        estimated_curtailment_mw=estimated,
        maximum_balance_residual_mw=solved.maximum_balance_residual_mw,
        maximum_thermal_violation_mw=corrected_violation,
        maximum_generation_bound_violation_mw=(
            solved.maximum_generation_bound_violation_mw
        ),
        maximum_redispatch_violation_mw=solved.maximum_redispatch_violation_mw,
        maximum_outage_generation_mw=solved.maximum_outage_generation_mw,
        maximum_flow_equation_residual_mw=(
            solved.maximum_flow_equation_residual_mw
        ),
        curtailment_bound_violation_mw=_positive_part(
            estimated - maximum_curtailment_mw
        ),
    )


def derive_network_grid_need(
    inputs: NetworkGridNeedInputs,
) -> NetworkGridNeedResult:
    """Derive one scenario's hard network curtailment need."""

    states = _validate_inputs(inputs)
    data = _operating_data(inputs)
    limits = _redispatch_limits(data, inputs.redispatch_fraction_of_pmax)
    base = solve_dc_opf(
        data,
        branch_rating=inputs.sustained_rating,
        solver_name=inputs.solver_name,
        tee=inputs.tee,
    )
    status = f"{inputs.parameter_status}|{NETWORK_GRID_NEED_SCOPE}"
    if not base.feasible:
        return NetworkGridNeedResult(
            feasible=False,
            direct_physical_dispatch_witness=False,
            proven_infeasible=base.termination_condition == "infeasible",
            method=inputs.method,
            grid_need_mw=None,
            critical_state=None,
            state_results={},
            base_dispatch_objective=None,
            base_termination_condition=base.termination_condition,
            base_solver_status=base.solver_status,
            base_maximum_balance_residual_mw=None,
            base_maximum_thermal_violation_mw=None,
            base_maximum_generation_bound_violation_mw=None,
            base_maximum_flow_equation_residual_mw=None,
            poi_bus=inputs.poi_bus,
            balancing_bus=inputs.balancing_bus,
            parameter_status=status,
            security_certified=False,
            scope=NETWORK_GRID_NEED_SCOPE,
        )
    base_balance, base_thermal, base_generation, base_flow = _base_audit(
        data, base, inputs.sustained_rating
    )
    if not _audit_passes(
        (base_balance, base_thermal, base_generation, base_flow)
    ):
        return NetworkGridNeedResult(
            feasible=False,
            direct_physical_dispatch_witness=False,
            proven_infeasible=False,
            method=inputs.method,
            grid_need_mw=None,
            critical_state=None,
            state_results={},
            base_dispatch_objective=base.objective,
            base_termination_condition="base_solution_audit_failed",
            base_solver_status=base.solver_status,
            base_maximum_balance_residual_mw=base_balance,
            base_maximum_thermal_violation_mw=base_thermal,
            base_maximum_generation_bound_violation_mw=base_generation,
            base_maximum_flow_equation_residual_mw=base_flow,
            poi_bus=inputs.poi_bus,
            balancing_bus=inputs.balancing_bus,
            parameter_status=status,
            security_certified=False,
            scope=NETWORK_GRID_NEED_SCOPE,
        )

    state_results: dict[str, NetworkGridNeedStateResult] = {}
    for state in states:
        sensitivities = (
            None
            if inputs.method == METHOD_MINIMUM_CURTAILMENT
            else _poi_transfer_sensitivities(
                data,
                outaged_branch_indices=state.outaged_branch_indices,
                poi_bus=inputs.poi_bus,
                balancing_bus=inputs.balancing_bus,
            )
        )
        solved = _solve_state(
            data,
            state,
            base_generation_mw=base.generation_mw,
            redispatch_limits_mw=limits,
            poi_bus=inputs.poi_bus,
            maximum_curtailment_mw=inputs.data_center_demand_mw,
            enforce_thermal_limits=inputs.method == METHOD_MINIMUM_CURTAILMENT,
            sensitivity_by_branch=sensitivities,
            solver_name=inputs.solver_name,
            tee=inputs.tee,
        )
        if inputs.method == METHOD_MINIMUM_CURTAILMENT:
            state_result = _minimum_curtailment_result(data, state, solved)
        else:
            state_result = _overload_sensitivity_result(
                data,
                state,
                solved,
                poi_bus=inputs.poi_bus,
                balancing_bus=inputs.balancing_bus,
                maximum_curtailment_mw=inputs.data_center_demand_mw,
            )
        audit_values = (
            state_result.maximum_balance_residual_mw,
            state_result.maximum_thermal_violation_mw,
            state_result.maximum_generation_bound_violation_mw,
            state_result.maximum_redispatch_violation_mw,
            state_result.maximum_outage_generation_mw,
            state_result.maximum_flow_equation_residual_mw,
            state_result.curtailment_bound_violation_mw,
        )
        if state_result.feasible and not _audit_passes(audit_values):
            state_result = replace(
                state_result,
                feasible=False,
                physically_deliverable=False,
                proven_infeasible=False,
                termination_condition="solution_audit_failed",
            )
        state_results[state.name] = state_result

    feasible = all(result.feasible for result in state_results.values())
    proven_infeasible = any(
        result.proven_infeasible for result in state_results.values()
    )
    estimated_results = {
        name: result.estimated_curtailment_mw
        for name, result in state_results.items()
        if result.estimated_curtailment_mw is not None
    }
    if len(estimated_results) == len(state_results):
        critical_state = max(
            estimated_results,
            key=estimated_results.__getitem__,
        )
        grid_need = estimated_results[critical_state]
    else:
        critical_state = None
        grid_need = None

    return NetworkGridNeedResult(
        feasible=feasible,
        direct_physical_dispatch_witness=(
            feasible
            and all(
                result.physically_deliverable
                for result in state_results.values()
            )
        ),
        proven_infeasible=proven_infeasible,
        method=inputs.method,
        grid_need_mw=grid_need,
        critical_state=critical_state,
        state_results=state_results,
        base_dispatch_objective=base.objective,
        base_termination_condition=base.termination_condition,
        base_solver_status=base.solver_status,
        base_maximum_balance_residual_mw=base_balance,
        base_maximum_thermal_violation_mw=base_thermal,
        base_maximum_generation_bound_violation_mw=base_generation,
        base_maximum_flow_equation_residual_mw=base_flow,
        poi_bus=inputs.poi_bus,
        balancing_bus=inputs.balancing_bus,
        parameter_status=status,
        security_certified=False,
        scope=NETWORK_GRID_NEED_SCOPE,
    )
