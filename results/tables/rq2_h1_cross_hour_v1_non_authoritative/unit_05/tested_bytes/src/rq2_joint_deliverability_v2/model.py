"""V5 four-arm planning model for RQ2 joint deliverability.

This module defines the registered feasible sets and solver certificate shape.
It does not load project data, select representatives, or publish results.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from math import ceil, floor, isfinite

from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    NonNegativeReals,
    Objective,
    Set,
    Var,
    minimize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition

from .solver_adapter import (
    Rq2SolverSpec,
    create_solver,
    model_scale,
)

NETWORK_ONLY_SHARED = "network_only_shared"
CFE_ONLY_SHARED = "cfe_only_shared"
JOINT_CORRECT_SHARED = "joint_correct_shared"
JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION = (
    "joint_b6_separate_planning_shared_execution"
)
FOUR_ARM_IDS = (
    NETWORK_ONLY_SHARED,
    CFE_ONLY_SHARED,
    JOINT_CORRECT_SHARED,
    JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
)

_SOLVER_PACKAGE = {"gurobi": "gurobipy", "highs": "highspy"}
_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}
_PROVEN_INFEASIBLE = {TerminationCondition.infeasible}


def _constraint_residual(model: ConcreteModel) -> float:
    residual = 0.0
    for constraint in model.component_data_objects(Constraint, active=True):
        body = float(value(constraint.body))
        if not isfinite(body):
            return float("inf")
        if constraint.lower is not None:
            residual = max(residual, float(value(constraint.lower)) - body)
        if constraint.upper is not None:
            residual = max(residual, body - float(value(constraint.upper)))
    for variable in model.component_data_objects(Var, active=True):
        raw = float(value(variable))
        if not isfinite(raw):
            return float("inf")
        if variable.is_binary():
            residual = max(residual, abs(raw - round(raw)))
        if variable.lb is not None:
            residual = max(residual, float(variable.lb) - raw)
        if variable.ub is not None:
            residual = max(residual, raw - float(variable.ub))
    return max(residual, 0.0)


@dataclass(frozen=True)
class JointDeliverabilityScenario:
    """One finite 24-hour power/workload pair after V5 preprocessing."""

    name: str
    power_block_id: str
    workload_block_id: str
    probability: float
    raw_grid_request: tuple[float, ...]
    raw_cfe_request: tuple[float, ...]
    effective_grid_request: tuple[float, ...]
    effective_cfe_request: tuple[float, ...]
    available_flexibility: tuple[float, ...]
    connected_demand: tuple[float, ...]
    business_recovery_headroom: tuple[float, ...]
    cfe_service_recovery_headroom: tuple[float, ...]


@dataclass(frozen=True)
class JointDeliverabilityPlanningInputs:
    """Frozen cell-level constants shared by every scenario and arm."""

    scenarios: tuple[JointDeliverabilityScenario, ...]
    time_step_hours: float
    maximum_flexibility_budget: float
    minimum_event_power: float
    response_time_hours: float
    curtailment_ramp_per_hour: float
    minimum_recovery_hours: float
    recovery_efficiency: float
    maximum_event_duration_hours: float
    maximum_event_count: int
    normalized_recovery_headroom: float
    normalized_energy_budget: float
    normalized_debt_limit: float
    terminal_recovery_debt_limit: float
    service_shortfall_tolerance: float


@dataclass(frozen=True)
class FixedServiceAudit:
    """Independent analytic audit of the fixed zero-shortfall trajectory."""

    arm_id: str
    feasible: bool
    required_capacity: float
    violations: tuple[str, ...]
    terminal_debt_by_scenario_track: dict[str, float]


@dataclass(frozen=True)
class ArmPlanningCertificate:
    """Fail-closed solver evidence for one arm and one registered cell."""

    arm_id: str
    status: str
    incumbent_capacity: float | None
    objective_lower_bound: float | None
    objective_upper_bound: float | None
    absolute_gap: float | None
    incumbent_relative_gap: float | None
    maximum_constraint_residual: float | None
    termination_condition: str
    solver_status: str
    model_variables: int
    model_constraints: int
    solver_name: str
    solver_version: str
    solver_options: dict[str, float | int]


def effective_request(raw_request: float, tolerance: float) -> float:
    """Apply the registered service-tolerance preprocessing rule."""

    request = _nonnegative(raw_request, "raw request")
    threshold = _nonnegative(tolerance, "service tolerance")
    return 0.0 if request <= threshold else request


def _finite(raw: object, label: str) -> float:
    if isinstance(raw, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        number = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _nonnegative(raw: object, label: str) -> float:
    number = _finite(raw, label)
    if number < 0.0:
        raise ValueError(f"{label} must be nonnegative")
    return number


def _tracks(arm_id: str) -> tuple[str, ...]:
    if arm_id not in FOUR_ARM_IDS:
        raise ValueError(f"unknown RQ2 joint-deliverability arm: {arm_id}")
    if arm_id == JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION:
        return ("grid", "cfe")
    return ("shared",)


def _track_call(
    scenario: JointDeliverabilityScenario,
    arm_id: str,
    track: str,
) -> tuple[float, ...]:
    grid = scenario.effective_grid_request
    cfe = scenario.effective_cfe_request
    if arm_id == NETWORK_ONLY_SHARED:
        return grid
    if arm_id == CFE_ONLY_SHARED:
        return cfe
    if arm_id == JOINT_CORRECT_SHARED:
        return tuple(
            grid_value + cfe_value
            for grid_value, cfe_value in zip(grid, cfe, strict=True)
        )
    if arm_id == JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION:
        return grid if track == "grid" else cfe
    raise ValueError(f"unknown RQ2 joint-deliverability arm: {arm_id}")


def _track_headroom(
    scenario: JointDeliverabilityScenario,
    arm_id: str,
    track: str,
) -> tuple[float, ...]:
    if arm_id == NETWORK_ONLY_SHARED or track == "grid":
        return scenario.business_recovery_headroom
    return scenario.cfe_service_recovery_headroom


def _validate_inputs(inputs: JointDeliverabilityPlanningInputs) -> tuple[int, int]:
    if not inputs.scenarios:
        raise ValueError("planning requires at least one scenario")
    scalar_nonnegative = {
        "maximum_flexibility_budget": inputs.maximum_flexibility_budget,
        "minimum_event_power": inputs.minimum_event_power,
        "response_time_hours": inputs.response_time_hours,
        "curtailment_ramp_per_hour": inputs.curtailment_ramp_per_hour,
        "minimum_recovery_hours": inputs.minimum_recovery_hours,
        "maximum_event_duration_hours": inputs.maximum_event_duration_hours,
        "normalized_recovery_headroom": inputs.normalized_recovery_headroom,
        "normalized_energy_budget": inputs.normalized_energy_budget,
        "normalized_debt_limit": inputs.normalized_debt_limit,
        "terminal_recovery_debt_limit": inputs.terminal_recovery_debt_limit,
        "service_shortfall_tolerance": inputs.service_shortfall_tolerance,
    }
    for label, raw in scalar_nonnegative.items():
        _nonnegative(raw, label)
    dt = _finite(inputs.time_step_hours, "time_step_hours")
    efficiency = _finite(inputs.recovery_efficiency, "recovery_efficiency")
    if dt <= 0.0:
        raise ValueError("time_step_hours must be positive")
    if not 0.0 < efficiency <= 1.0:
        raise ValueError("recovery_efficiency must lie in (0, 1]")
    if inputs.minimum_event_power <= 0.0:
        raise ValueError("minimum_event_power must be positive")
    if inputs.response_time_hours <= 0.0:
        raise ValueError("response_time_hours must be positive")
    if inputs.curtailment_ramp_per_hour <= 0.0:
        raise ValueError("curtailment_ramp_per_hour must be positive")
    if inputs.maximum_event_duration_hours <= 0.0:
        raise ValueError("maximum_event_duration_hours must be positive")
    if (
        isinstance(inputs.maximum_event_count, bool)
        or not isinstance(inputs.maximum_event_count, int)
        or inputs.maximum_event_count < 0
    ):
        raise ValueError("maximum_event_count must be a nonnegative integer")
    max_duration_steps = floor(inputs.maximum_event_duration_hours / dt + 1.0e-6)
    minimum_rest_steps = ceil(inputs.minimum_recovery_hours / dt - 1.0e-6)
    if max_duration_steps < 1:
        raise ValueError("maximum event duration permits no time step")

    names: set[str] = set()
    probability = 0.0
    horizon: int | None = None
    for scenario in inputs.scenarios:
        if (
            not scenario.name
            or not scenario.power_block_id
            or not scenario.workload_block_id
            or scenario.name in names
        ):
            raise ValueError("scenario names must be nonempty and unique")
        names.add(scenario.name)
        probability += _nonnegative(scenario.probability, "scenario probability")
        lengths = {
            len(scenario.raw_grid_request),
            len(scenario.raw_cfe_request),
            len(scenario.effective_grid_request),
            len(scenario.effective_cfe_request),
            len(scenario.available_flexibility),
            len(scenario.connected_demand),
            len(scenario.business_recovery_headroom),
            len(scenario.cfe_service_recovery_headroom),
        }
        if 0 in lengths or len(lengths) != 1:
            raise ValueError("scenario trajectories must have one nonzero length")
        scenario_horizon = lengths.pop()
        if horizon is None:
            horizon = scenario_horizon
        elif horizon != scenario_horizon:
            raise ValueError("all planning scenarios must have equal horizons")
        vectors = (
            scenario.raw_grid_request,
            scenario.raw_cfe_request,
            scenario.effective_grid_request,
            scenario.effective_cfe_request,
            scenario.available_flexibility,
            scenario.connected_demand,
            scenario.business_recovery_headroom,
            scenario.cfe_service_recovery_headroom,
        )
        if any(
            not isfinite(float(item)) or float(item) < 0.0
            for vector in vectors
            for item in vector
        ):
            raise ValueError("scenario trajectories must be finite and nonnegative")
        expected_grid = tuple(
            effective_request(item, inputs.service_shortfall_tolerance)
            for item in scenario.raw_grid_request
        )
        expected_cfe = tuple(
            effective_request(item, inputs.service_shortfall_tolerance)
            for item in scenario.raw_cfe_request
        )
        if (
            scenario.effective_grid_request != expected_grid
            or scenario.effective_cfe_request != expected_cfe
        ):
            raise ValueError("effective service request preprocessing drifted")
        if any(
            cfe > business + 1.0e-12
            for cfe, business in zip(
                scenario.cfe_service_recovery_headroom,
                scenario.business_recovery_headroom,
                strict=True,
            )
        ):
            raise ValueError("CFE recovery headroom exceeds business headroom")
    if abs(probability - 1.0) > 1.0e-9:
        raise ValueError("scenario probabilities must sum to one")
    return max_duration_steps, minimum_rest_steps


def build_arm_planning_model(
    inputs: JointDeliverabilityPlanningInputs,
    arm_id: str,
) -> ConcreteModel:
    """Build the exact V5 MILP for one arm without invoking a solver."""

    max_duration_steps, minimum_rest_steps = _validate_inputs(inputs)
    tracks = _tracks(arm_id)
    scenarios = {scenario.name: scenario for scenario in inputs.scenarios}
    names = tuple(scenarios)
    horizon = len(inputs.scenarios[0].raw_grid_request)
    points = tuple((name, hour) for name in names for hour in range(horizon))
    tracked_points = tuple(
        (name, track, hour)
        for name in names
        for track in tracks
        for hour in range(horizon)
    )
    dt = inputs.time_step_hours
    maximum_capacity = inputs.maximum_flexibility_budget

    model = ConcreteModel()
    model.scenarios = Set(initialize=names, ordered=True)
    model.points = Set(initialize=points, dimen=2, ordered=True)
    model.tracks = Set(initialize=tracks, ordered=True)
    model.tracked_points = Set(
        initialize=tracked_points,
        dimen=3,
        ordered=True,
    )
    model.capacity = Var(
        domain=NonNegativeReals,
        bounds=(0.0, maximum_capacity),
    )
    model.grid_service = Var(model.points, domain=NonNegativeReals)
    model.cfe_service = Var(model.points, domain=NonNegativeReals)
    model.track_call = Var(model.tracked_points, domain=NonNegativeReals)
    model.on = Var(model.tracked_points, domain=Binary)
    model.start = Var(model.tracked_points, domain=Binary)
    model.stop = Var(model.tracked_points, domain=Binary)
    model.recovery = Var(model.tracked_points, domain=NonNegativeReals)
    model.debt = Var(
        model.tracked_points,
        domain=NonNegativeReals,
        bounds=(0.0, inputs.normalized_debt_limit),
    )

    model.service = ConstraintList()
    for name, hour in points:
        scenario = scenarios[name]
        grid_request = scenario.effective_grid_request[hour]
        cfe_request = scenario.effective_cfe_request[hour]
        if arm_id in {
            NETWORK_ONLY_SHARED,
            JOINT_CORRECT_SHARED,
            JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
        }:
            model.service.add(model.grid_service[name, hour] >= grid_request)
        else:
            model.service.add(model.grid_service[name, hour] == 0.0)
        if arm_id in {
            CFE_ONLY_SHARED,
            JOINT_CORRECT_SHARED,
            JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
        }:
            model.service.add(model.cfe_service[name, hour] == cfe_request)
        else:
            model.service.add(model.cfe_service[name, hour] == 0.0)
        model.service.add(
            model.grid_service[name, hour] + model.cfe_service[name, hour]
            <= scenario.connected_demand[hour]
        )
        if arm_id == JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION:
            model.service.add(
                model.grid_service[name, hour] <= scenario.available_flexibility[hour]
            )
            model.service.add(
                model.cfe_service[name, hour] <= scenario.available_flexibility[hour]
            )
        else:
            model.service.add(
                model.grid_service[name, hour] + model.cfe_service[name, hour]
                <= scenario.available_flexibility[hour]
            )

    model.temporal = ConstraintList()
    for name in names:
        scenario = scenarios[name]
        for track in tracks:
            headroom = _track_headroom(scenario, arm_id, track)
            for hour in range(horizon):
                q = model.track_call[name, track, hour]
                if track == "shared":
                    model.temporal.add(
                        q
                        == model.grid_service[name, hour]
                        + model.cfe_service[name, hour]
                    )
                elif track == "grid":
                    model.temporal.add(q == model.grid_service[name, hour])
                else:
                    model.temporal.add(q == model.cfe_service[name, hour])
                previous_q = (
                    0.0 if hour == 0 else model.track_call[name, track, hour - 1]
                )
                previous_on = 0.0 if hour == 0 else model.on[name, track, hour - 1]
                model.temporal.add(q <= model.capacity)
                model.temporal.add(q <= maximum_capacity * model.on[name, track, hour])
                model.temporal.add(
                    q >= inputs.minimum_event_power * model.on[name, track, hour]
                )
                model.temporal.add(
                    q - previous_q <= inputs.curtailment_ramp_per_hour * dt
                )
                model.temporal.add(
                    q - previous_q
                    <= inputs.curtailment_ramp_per_hour * inputs.response_time_hours
                )
                model.temporal.add(
                    model.start[name, track, hour]
                    >= model.on[name, track, hour] - previous_on
                )
                model.temporal.add(
                    model.start[name, track, hour] <= model.on[name, track, hour]
                )
                model.temporal.add(model.start[name, track, hour] <= 1.0 - previous_on)
                model.temporal.add(
                    model.stop[name, track, hour]
                    >= previous_on - model.on[name, track, hour]
                )
                model.temporal.add(model.stop[name, track, hour] <= previous_on)
                model.temporal.add(
                    model.stop[name, track, hour] <= 1.0 - model.on[name, track, hour]
                )
                model.temporal.add(
                    model.recovery[name, track, hour]
                    <= inputs.normalized_recovery_headroom
                )
                model.temporal.add(model.recovery[name, track, hour] <= headroom[hour])
                model.temporal.add(
                    model.recovery[name, track, hour]
                    <= inputs.normalized_recovery_headroom
                    * (1.0 - model.on[name, track, hour])
                )
                prior_debt = 0.0 if hour == 0 else model.debt[name, track, hour - 1]
                model.temporal.add(
                    model.debt[name, track, hour]
                    == prior_debt
                    + q * dt
                    - inputs.recovery_efficiency
                    * model.recovery[name, track, hour]
                    * dt
                )

            for first in range(horizon - max_duration_steps):
                model.temporal.add(
                    sum(
                        model.on[name, track, hour]
                        for hour in range(
                            first,
                            first + max_duration_steps + 1,
                        )
                    )
                    <= max_duration_steps
                )
            for stop_hour in range(horizon):
                for future in range(
                    stop_hour,
                    min(stop_hour + minimum_rest_steps, horizon),
                ):
                    model.temporal.add(
                        model.on[name, track, future]
                        + model.stop[name, track, stop_hour]
                        <= 1.0
                    )
            model.temporal.add(
                sum(model.start[name, track, hour] for hour in range(horizon))
                <= inputs.maximum_event_count
            )
            model.temporal.add(
                sum(model.track_call[name, track, hour] * dt for hour in range(horizon))
                <= inputs.normalized_energy_budget
            )
            model.temporal.add(model.on[name, track, horizon - 1] == 0.0)
            model.temporal.add(
                model.debt[name, track, horizon - 1]
                <= inputs.terminal_recovery_debt_limit
            )

    model.minimum_capacity = Objective(expr=model.capacity, sense=minimize)
    model._joint_deliverability_arm_id = arm_id
    model._joint_deliverability_inputs = inputs
    model._joint_deliverability_track_calls = {
        (name, track): _track_call(scenarios[name], arm_id, track)
        for name in names
        for track in tracks
    }
    return model


def audit_fixed_service_trajectory(
    inputs: JointDeliverabilityPlanningInputs,
    arm_id: str,
) -> FixedServiceAudit:
    """Audit the minimum-request trajectory as a sufficient feasibility witness.

    CFE service is fixed, while grid service is only lower-bounded. A failed
    minimum-request trajectory is therefore not an infeasibility certificate
    for grid-active arms; callers must use the exact model fallback.
    """

    max_duration_steps, minimum_rest_steps = _validate_inputs(inputs)
    tracks = _tracks(arm_id)
    dt = inputs.time_step_hours
    violations: list[str] = []
    terminal_debt: dict[str, float] = {}
    required_capacity = 0.0

    for scenario in inputs.scenarios:
        grid = (
            scenario.effective_grid_request
            if arm_id
            in {
                NETWORK_ONLY_SHARED,
                JOINT_CORRECT_SHARED,
                JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
            }
            else (0.0,) * len(scenario.effective_grid_request)
        )
        cfe = (
            scenario.effective_cfe_request
            if arm_id
            in {
                CFE_ONLY_SHARED,
                JOINT_CORRECT_SHARED,
                JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
            }
            else (0.0,) * len(scenario.effective_cfe_request)
        )
        for hour, (grid_value, cfe_value) in enumerate(zip(grid, cfe, strict=True)):
            if grid_value + cfe_value > scenario.connected_demand[hour] + 1.0e-12:
                violations.append(f"{scenario.name}:connected_cap:{hour}")
            if arm_id == JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION:
                if grid_value > scenario.available_flexibility[hour] + 1.0e-12:
                    violations.append(f"{scenario.name}:grid_available:{hour}")
                if cfe_value > scenario.available_flexibility[hour] + 1.0e-12:
                    violations.append(f"{scenario.name}:cfe_available:{hour}")
            elif (
                grid_value + cfe_value > scenario.available_flexibility[hour] + 1.0e-12
            ):
                violations.append(f"{scenario.name}:shared_available:{hour}")

        for track in tracks:
            calls = _track_call(scenario, arm_id, track)
            headroom = _track_headroom(scenario, arm_id, track)
            required_capacity = max(required_capacity, max(calls))
            active = [call >= inputs.minimum_event_power for call in calls]
            previous_call = 0.0
            previous_active = False
            active_duration = 0
            rest_steps: int | None = None
            event_count = 0
            energy = 0.0
            debt = 0.0
            peak_debt = 0.0
            for hour, call in enumerate(calls):
                label = f"{scenario.name}:{track}:{hour}"
                if call > inputs.maximum_flexibility_budget + 1.0e-12:
                    violations.append(f"{label}:capacity_domain")
                if active[hour] != (call > inputs.service_shortfall_tolerance):
                    violations.append(f"{label}:activity_threshold")
                if (
                    call - previous_call
                    > inputs.curtailment_ramp_per_hour * dt + 1.0e-12
                    or call - previous_call
                    > inputs.curtailment_ramp_per_hour * inputs.response_time_hours
                    + 1.0e-12
                ):
                    violations.append(f"{label}:upward_ramp")
                starts = active[hour] and not previous_active
                stops = previous_active and not active[hour]
                if starts:
                    event_count += 1
                    if rest_steps is not None and rest_steps < minimum_rest_steps:
                        violations.append(f"{label}:minimum_rest")
                    rest_steps = None
                if active[hour]:
                    active_duration = active_duration + 1 if previous_active else 1
                    if active_duration > max_duration_steps:
                        violations.append(f"{label}:maximum_duration")
                else:
                    active_duration = 0
                    if stops:
                        rest_steps = 1
                    elif rest_steps is not None:
                        rest_steps += 1
                energy += call * dt
                debt += call * dt
                if not active[hour]:
                    recovery = min(
                        inputs.normalized_recovery_headroom,
                        headroom[hour],
                        debt / (inputs.recovery_efficiency * dt),
                    )
                    debt = max(
                        debt - inputs.recovery_efficiency * recovery * dt,
                        0.0,
                    )
                peak_debt = max(peak_debt, debt)
                if debt > inputs.normalized_debt_limit + 1.0e-12:
                    violations.append(f"{label}:debt_limit")
                previous_call = call
                previous_active = active[hour]
            if event_count > inputs.maximum_event_count:
                violations.append(f"{scenario.name}:{track}:event_count")
            if energy > inputs.normalized_energy_budget + 1.0e-12:
                violations.append(f"{scenario.name}:{track}:energy")
            if active[-1]:
                violations.append(f"{scenario.name}:{track}:terminal_on")
            if debt > inputs.terminal_recovery_debt_limit + 1.0e-12:
                violations.append(f"{scenario.name}:{track}:terminal_debt")
            terminal_debt[f"{scenario.name}::{track}"] = debt
            if peak_debt > inputs.normalized_debt_limit + 1.0e-12:
                violations.append(f"{scenario.name}:{track}:peak_debt")
    return FixedServiceAudit(
        arm_id=arm_id,
        feasible=not violations,
        required_capacity=required_capacity,
        violations=tuple(dict.fromkeys(violations)),
        terminal_debt_by_scenario_track=terminal_debt,
    )


def solve_arm_minimum_capacity(
    inputs: JointDeliverabilityPlanningInputs,
    arm_id: str,
    *,
    solver_specification: Rq2SolverSpec,
) -> ArmPlanningCertificate:
    """Solve one arm and retain the complete registered bound certificate."""

    model = build_arm_planning_model(inputs, arm_id)
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
    package = _SOLVER_PACKAGE[solver_specification.name]
    observed_version = version(package)

    if termination not in _OPTIMAL:
        proven_infeasible = bool(
            termination in _PROVEN_INFEASIBLE
            and result.solver.status in {SolverStatus.ok, SolverStatus.warning}
        )
        return ArmPlanningCertificate(
            arm_id=arm_id,
            status=(
                "proven_infeasible_at_registered_cap_estimand_undefined"
                if proven_infeasible
                else "unresolved"
            ),
            incumbent_capacity=None,
            objective_lower_bound=None if proven_infeasible else lower,
            objective_upper_bound=None if proven_infeasible else upper,
            absolute_gap=(
                None
                if proven_infeasible
                else (
                    abs(upper - lower)
                    if lower is not None and upper is not None
                    else None
                )
            ),
            incumbent_relative_gap=None,
            maximum_constraint_residual=None,
            termination_condition=str(termination),
            solver_status=str(result.solver.status),
            model_variables=scale.variables,
            model_constraints=scale.constraints,
            solver_name=solver_specification.name,
            solver_version=observed_version,
            solver_options=options,
        )

    model.solutions.load_from(result)
    incumbent = _optional_finite(value(model.capacity))
    residual = _constraint_residual(model)
    absolute_gap = upper - lower if upper is not None and lower is not None else None
    relative_gap = (
        absolute_gap / max(abs(incumbent), 1.0e-12)
        if absolute_gap is not None and incumbent is not None
        else None
    )
    valid = bool(
        incumbent is not None
        and lower is not None
        and upper is not None
        and result.solver.status == SolverStatus.ok
        and lower <= upper
        and lower <= incumbent
        and abs(upper - incumbent) <= solver_specification.feasibility_tolerance
        and incumbent
        <= inputs.maximum_flexibility_budget
        + solver_specification.feasibility_tolerance
        and absolute_gap is not None
        and absolute_gap >= 0.0
        and relative_gap is not None
        and relative_gap <= solver_specification.mip_relative_gap + 1.0e-12
        and residual <= solver_specification.feasibility_tolerance
    )
    return ArmPlanningCertificate(
        arm_id=arm_id,
        status="candidate_resolved" if valid else "unresolved",
        incumbent_capacity=incumbent if valid else None,
        objective_lower_bound=lower,
        objective_upper_bound=upper,
        absolute_gap=absolute_gap,
        incumbent_relative_gap=relative_gap,
        maximum_constraint_residual=residual,
        termination_condition=(str(termination) if valid else "solution_audit_failed"),
        solver_status=str(result.solver.status),
        model_variables=scale.variables,
        model_constraints=scale.constraints,
        solver_name=solver_specification.name,
        solver_version=observed_version,
        solver_options=options,
    )


def _optional_finite(raw: object | None) -> float | None:
    if raw is None:
        return None
    number = float(raw)
    return number if isfinite(number) else None


__all__ = [
    "CFE_ONLY_SHARED",
    "FOUR_ARM_IDS",
    "JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION",
    "JOINT_CORRECT_SHARED",
    "NETWORK_ONLY_SHARED",
    "ArmPlanningCertificate",
    "FixedServiceAudit",
    "JointDeliverabilityPlanningInputs",
    "JointDeliverabilityScenario",
    "audit_fixed_service_trajectory",
    "build_arm_planning_model",
    "effective_request",
    "solve_arm_minimum_capacity",
]
