"""Chronological RQ2 L5 recourse with a shared flexibility envelope.

The correct model applies one temporal state to the physical aggregate
``grid_curtailment + green_shift``. The B6 error baseline gives the two
contract services independent copies of the same envelope. That baseline is
deliberately physically wrong: it represents separate commitments that can
double-use one workload resource.

All duration, event, energy, recovery-debt and network-need requirements are
hard constraints. CVaR is computed only from service/business loss. Consistent
with the core RQ2 experiment in ``formulation.md`` section 10.2, permanent
drop is fixed to zero rather than used to erase recovery debt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil, floor, isfinite
from numbers import Integral, Real

from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    Expression,
    NonNegativeReals,
    Objective,
    Reals,
    Set,
    SolverFactory,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from ..evaluation.flexibility_envelope import (
    ChronologicalFlexibilityEnvelope,
    ChronologicalFlexibilityTrace,
    evaluate_chronological_flexibility,
)
from ..evaluation.service_risk import (
    ScenarioServiceLoss,
    ServiceLossCoefficients,
    evaluate_service_cvar,
)

TEMPORAL_ECONOMIC_SCOPE = (
    "synthetic_chronological_shared_flexibility_envelope_with_service_cvar_"
    "not_empirical_not_security_certification"
)
_TOLERANCE = 1.0e-6
_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}
_PROVEN_INFEASIBLE = {TerminationCondition.infeasible}


@dataclass(frozen=True)
class TemporalEconomicScenario:
    name: str
    probability: float
    periods: tuple[str, ...]
    grid_need_mw: tuple[float, ...]
    green_call_mw: tuple[float, ...]
    connected_demand_mw: tuple[float, ...]
    recovery_headroom_mw: tuple[float, ...]
    completed_periods: frozenset[str]
    require_terminal_event_inactive: bool
    boundary_state_status: str


@dataclass(frozen=True)
class TemporalEconomicInputs:
    scenarios: tuple[TemporalEconomicScenario, ...]
    envelope: ChronologicalFlexibilityEnvelope
    coefficients: ServiceLossCoefficients
    provisioning_cost_per_mw: float
    max_flexibility_budget_mw: float
    lambda_risk: float
    beta: float
    enforce_joint_budget: bool
    parameter_status: str
    fixed_flexibility_mw: float | None = None


@dataclass(frozen=True)
class TemporalScenarioDispatch:
    grid_curtailment_mw: tuple[float, ...]
    green_shift_mw: tuple[float, ...]
    access_shortfall_mw: tuple[float, ...]
    physical_combined_call_mw: tuple[float, ...]
    modeled_event_count_by_period: dict[str, int]
    curtailment_energy_mwh_by_period: dict[str, float]
    maximum_physical_budget_excess_mw: float
    physical_envelope_feasible: bool
    physical_envelope_violations: tuple[str, ...]
    physical_recovery_power_mw: tuple[float, ...]
    physical_recovery_debt_mwh: tuple[float, ...]
    physical_event_count_by_period: dict[str, int]
    physical_terminal_recovery_debt_mwh: float
    maximum_temporal_residual: float
    scenario_loss: float


@dataclass(frozen=True)
class TemporalEconomicResult:
    feasible: bool
    proven_infeasible: bool
    termination_condition: str
    solver_status: str
    objective: float | None
    expansion_cost: float | None
    expected_operating_cost: float | None
    conditional_value_at_risk: float | None
    value_at_risk: float | None
    provisioned_flexibility_mw: float | None
    scenario_dispatch: dict[str, TemporalScenarioDispatch]
    enforce_joint_budget: bool
    parameter_status: str
    security_certified: bool
    risk_measure_scope: str


def _finite(name: str, raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(raw):
        raise ValueError(f"{name} must be a finite number")
    return float(raw)


def _nonnegative(name: str, raw: object) -> float:
    number = _finite(name, raw)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _positive(name: str, raw: object) -> float:
    number = _finite(name, raw)
    if number <= 0.0:
        raise ValueError(f"{name} must be positive")
    return number


def _validate_period_limits(
    envelope: ChronologicalFlexibilityEnvelope, periods: set[str]
) -> None:
    for name, mapping in (
        ("maximum_events_by_period", envelope.maximum_events_by_period),
        (
            "maximum_curtailment_energy_mwh_by_period",
            envelope.maximum_curtailment_energy_mwh_by_period,
        ),
    ):
        if set(mapping) != periods:
            raise ValueError(f"{name} keys must match all scenario periods")
    if not set(envelope.terminal_debt_limit_mwh_by_period) <= periods:
        raise ValueError("terminal debt limits contain an unknown period")
    for period, limit in envelope.maximum_events_by_period.items():
        if isinstance(limit, bool) or not isinstance(limit, Integral) or limit < 0:
            raise ValueError(
                f"maximum event count for {period} must be a nonnegative integer"
            )
    for period, limit in envelope.maximum_curtailment_energy_mwh_by_period.items():
        _nonnegative(f"maximum energy for {period}", limit)
    for period, limit in envelope.terminal_debt_limit_mwh_by_period.items():
        _nonnegative(f"terminal debt limit for {period}", limit)


def _validate_inputs(inputs: TemporalEconomicInputs) -> tuple[int, int]:
    if not inputs.parameter_status:
        raise ValueError("parameter_status must be explicit")
    if not inputs.envelope.parameter_status:
        raise ValueError("envelope.parameter_status must be explicit")
    if not inputs.coefficients.parameter_status:
        raise ValueError("coefficients.parameter_status must be explicit")
    dt = _positive("time_step_hours", inputs.envelope.time_step_hours)
    maximum_duration = _positive(
        "maximum_event_duration_hours",
        inputs.envelope.maximum_event_duration_hours,
    )
    minimum_rest = _nonnegative(
        "minimum_recovery_hours", inputs.envelope.minimum_recovery_hours
    )
    max_duration_steps = floor(maximum_duration / dt + _TOLERANCE)
    minimum_rest_steps = ceil(minimum_rest / dt - _TOLERANCE)
    if max_duration_steps < 1:
        raise ValueError("maximum event duration must permit at least one step")
    _nonnegative(
        "maximum_recovery_debt_mwh",
        inputs.envelope.maximum_recovery_debt_mwh,
    )
    _nonnegative(
        "maximum_recovery_power_mw",
        inputs.envelope.maximum_recovery_power_mw,
    )
    _positive("minimum_event_power_mw", inputs.envelope.minimum_event_power_mw)
    _positive("response_time_hours", inputs.envelope.response_time_hours)
    _positive(
        "curtailment_ramp_mw_per_hour",
        inputs.envelope.curtailment_ramp_mw_per_hour,
    )
    efficiency = _positive(
        "recovery_efficiency", inputs.envelope.recovery_efficiency
    )
    if efficiency > 1.0:
        raise ValueError("recovery_efficiency cannot exceed one")
    _nonnegative("provisioning_cost_per_mw", inputs.provisioning_cost_per_mw)
    maximum_budget = _nonnegative(
        "max_flexibility_budget_mw", inputs.max_flexibility_budget_mw
    )
    _nonnegative("lambda_risk", inputs.lambda_risk)
    beta = _finite("beta", inputs.beta)
    if not 0.0 <= beta < 1.0:
        raise ValueError("beta must lie in [0, 1)")
    if not isinstance(inputs.enforce_joint_budget, bool):
        raise TypeError("enforce_joint_budget must be boolean")
    if inputs.fixed_flexibility_mw is not None:
        fixed = _nonnegative(
            "fixed_flexibility_mw", inputs.fixed_flexibility_mw
        )
        if fixed > maximum_budget + _TOLERANCE:
            raise ValueError("fixed flexibility exceeds maximum budget")
    for field in (
        "kappa_access",
        "kappa_grid",
        "kappa_green",
        "kappa_drop",
        "kappa_breach_firm",
        "kappa_breach_conditional",
    ):
        _nonnegative(field, getattr(inputs.coefficients, field))
    if not inputs.scenarios:
        raise ValueError("at least one scenario is required")
    names = [scenario.name for scenario in inputs.scenarios]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("scenario names must be nonempty and unique")

    probability_sum = 0.0
    all_periods: set[str] = set()
    reference_periods: tuple[str, ...] | None = None
    for scenario in inputs.scenarios:
        probability = _positive(
            f"probability[{scenario.name}]", scenario.probability
        )
        probability_sum += probability
        lengths = {
            len(scenario.periods),
            len(scenario.grid_need_mw),
            len(scenario.green_call_mw),
            len(scenario.connected_demand_mw),
            len(scenario.recovery_headroom_mw),
        }
        if lengths == {0} or len(lengths) != 1:
            raise ValueError("scenario chronological arrays must be equal and nonempty")
        if any(not period for period in scenario.periods):
            raise ValueError("scenario periods must be nonempty")
        if reference_periods is None:
            reference_periods = scenario.periods
        elif scenario.periods != reference_periods:
            raise ValueError(
                "all temporal scenarios must use the same period sequence"
            )
        for period in set(scenario.periods):
            indices = [
                index
                for index, candidate in enumerate(scenario.periods)
                if candidate == period
            ]
            if indices != list(range(indices[0], indices[-1] + 1)):
                raise ValueError("each scenario period must form one contiguous block")
        if not isinstance(scenario.completed_periods, frozenset):
            raise TypeError("completed_periods must be a frozenset")
        if not scenario.completed_periods <= set(scenario.periods):
            raise ValueError("completed_periods contains an unknown period")
        if not isinstance(scenario.require_terminal_event_inactive, bool):
            raise TypeError("require_terminal_event_inactive must be boolean")
        if scenario.boundary_state_status != "clean_boundary_with_zero_carry_in":
            raise ValueError(
                "temporal L5 currently requires a clean zero carry-in boundary"
            )
        for index in range(len(scenario.periods)):
            grid = _nonnegative(
                f"grid_need_mw[{scenario.name},{index}]",
                scenario.grid_need_mw[index],
            )
            green = _nonnegative(
                f"green_call_mw[{scenario.name},{index}]",
                scenario.green_call_mw[index],
            )
            connected = _nonnegative(
                f"connected_demand_mw[{scenario.name},{index}]",
                scenario.connected_demand_mw[index],
            )
            _nonnegative(
                f"recovery_headroom_mw[{scenario.name},{index}]",
                scenario.recovery_headroom_mw[index],
            )
            if grid > connected + _TOLERANCE:
                raise ValueError("grid need cannot exceed connected demand")
            if green > connected + _TOLERANCE:
                raise ValueError("green call cannot exceed connected demand")
        all_periods.update(scenario.periods)
    if abs(probability_sum - 1.0) > 1.0e-9:
        raise ValueError("scenario probabilities must sum to one")
    _validate_period_limits(inputs.envelope, all_periods)
    return max_duration_steps, minimum_rest_steps


def _build_model(
    inputs: TemporalEconomicInputs,
    max_duration_steps: int,
    minimum_rest_steps: int,
) -> ConcreteModel:
    scenarios = {scenario.name: scenario for scenario in inputs.scenarios}
    names = tuple(scenarios)
    points = tuple(
        (name, index)
        for name in names
        for index in range(len(scenarios[name].periods))
    )
    tracks = ("shared",) if inputs.enforce_joint_budget else ("grid", "green")
    tracked_points = tuple(
        (name, track, index)
        for name in names
        for track in tracks
        for index in range(len(scenarios[name].periods))
    )
    dt = float(inputs.envelope.time_step_hours)
    efficiency = float(inputs.envelope.recovery_efficiency)
    max_budget = float(inputs.max_flexibility_budget_mw)
    max_recovery = float(inputs.envelope.maximum_recovery_power_mw)

    model = ConcreteModel()
    model.scenarios = Set(initialize=names, ordered=True)
    model.points = Set(initialize=points, dimen=2, ordered=True)
    model.tracks = Set(initialize=tracks, ordered=True)
    model.tracked_points = Set(
        initialize=tracked_points, dimen=3, ordered=True
    )
    model.flex_budget = Var(
        domain=NonNegativeReals, bounds=(0.0, max_budget)
    )
    if inputs.fixed_flexibility_mw is not None:
        model.flex_budget.fix(float(inputs.fixed_flexibility_mw))
    model.grid_curtailment = Var(model.points, domain=NonNegativeReals)
    model.green_shift = Var(model.points, domain=NonNegativeReals)
    model.access_shortfall = Var(model.points, domain=NonNegativeReals)
    model.on = Var(model.tracked_points, domain=Binary)
    model.event_start = Var(model.tracked_points, domain=Binary)
    model.event_stop = Var(model.tracked_points, domain=Binary)
    model.recovery = Var(model.tracked_points, domain=NonNegativeReals)
    model.debt = Var(
        model.tracked_points,
        domain=NonNegativeReals,
        bounds=(0.0, float(inputs.envelope.maximum_recovery_debt_mwh)),
    )
    model.var_eta = Var(domain=Reals)
    model.zeta = Var(model.scenarios, domain=NonNegativeReals)

    def call(m, name: str, track: str, index: int):
        if track == "shared":
            return m.grid_curtailment[name, index] + m.green_shift[name, index]
        if track == "grid":
            return m.grid_curtailment[name, index]
        return m.green_shift[name, index]

    model.grid_need = ConstraintList()
    model.green_balance = ConstraintList()
    model.connected_cap = ConstraintList()
    for name, index in points:
        scenario = scenarios[name]
        model.grid_need.add(
            model.grid_curtailment[name, index]
            >= scenario.grid_need_mw[index]
        )
        model.green_balance.add(
            model.green_shift[name, index]
            + model.access_shortfall[name, index]
            == scenario.green_call_mw[index]
        )
        model.connected_cap.add(
            model.grid_curtailment[name, index]
            + model.green_shift[name, index]
            <= scenario.connected_demand_mw[index]
        )

    model.temporal = ConstraintList()
    for name in names:
        scenario = scenarios[name]
        horizon = len(scenario.periods)
        for track in tracks:
            for index in range(horizon):
                current_call = call(model, name, track, index)
                previous_call = (
                    0.0 if index == 0 else call(model, name, track, index - 1)
                )
                previous_on = 0.0 if index == 0 else model.on[name, track, index - 1]
                model.temporal.add(current_call <= model.flex_budget)
                model.temporal.add(
                    current_call <= max_budget * model.on[name, track, index]
                )
                model.temporal.add(
                    current_call
                    >= inputs.envelope.minimum_event_power_mw
                    * model.on[name, track, index]
                )
                model.temporal.add(
                    current_call - previous_call
                    <= inputs.envelope.curtailment_ramp_mw_per_hour * dt
                )
                model.temporal.add(
                    current_call - previous_call
                    <= inputs.envelope.curtailment_ramp_mw_per_hour
                    * inputs.envelope.response_time_hours
                )
                model.temporal.add(
                    model.event_start[name, track, index]
                    >= model.on[name, track, index] - previous_on
                )
                model.temporal.add(
                    model.event_start[name, track, index]
                    <= model.on[name, track, index]
                )
                model.temporal.add(
                    model.event_start[name, track, index] <= 1.0 - previous_on
                )
                model.temporal.add(
                    model.event_stop[name, track, index]
                    >= previous_on - model.on[name, track, index]
                )
                model.temporal.add(
                    model.event_stop[name, track, index] <= previous_on
                )
                model.temporal.add(
                    model.event_stop[name, track, index]
                    <= 1.0 - model.on[name, track, index]
                )
                model.temporal.add(
                    model.recovery[name, track, index] <= max_recovery
                )
                model.temporal.add(
                    model.recovery[name, track, index]
                    <= scenario.recovery_headroom_mw[index]
                )
                model.temporal.add(
                    model.recovery[name, track, index]
                    <= max_recovery * (1.0 - model.on[name, track, index])
                )
                prior_debt = (
                    0.0 if index == 0 else model.debt[name, track, index - 1]
                )
                model.temporal.add(
                    model.debt[name, track, index]
                    == prior_debt
                    + current_call * dt
                    - efficiency * model.recovery[name, track, index] * dt
                )

            for start in range(horizon - max_duration_steps):
                model.temporal.add(
                    sum(
                        model.on[name, track, index]
                        for index in range(
                            start, start + max_duration_steps + 1
                        )
                    )
                    <= max_duration_steps
                )
            for stop_index in range(horizon):
                for future in range(
                    stop_index,
                    min(stop_index + minimum_rest_steps, horizon),
                ):
                    model.temporal.add(
                        model.on[name, track, future]
                        + model.event_stop[name, track, stop_index]
                        <= 1.0
                    )
            for period in dict.fromkeys(scenario.periods):
                period_indices = tuple(
                    index
                    for index, candidate in enumerate(scenario.periods)
                    if candidate == period
                )
                model.temporal.add(
                    sum(
                        model.event_start[name, track, index]
                        for index in period_indices
                    )
                    <= inputs.envelope.maximum_events_by_period[period]
                )
                model.temporal.add(
                    sum(
                        call(model, name, track, index) * dt
                        for index in period_indices
                    )
                    <= inputs.envelope.maximum_curtailment_energy_mwh_by_period[
                        period
                    ]
                )
                period_end = period_indices[-1]
                if (
                    (
                        period_end < horizon - 1
                        or period in scenario.completed_periods
                    )
                    and period in inputs.envelope.terminal_debt_limit_mwh_by_period
                ):
                    model.temporal.add(
                        model.debt[name, track, period_end]
                        <= inputs.envelope.terminal_debt_limit_mwh_by_period[
                            period
                        ]
                    )
            if scenario.require_terminal_event_inactive:
                model.temporal.add(model.on[name, track, horizon - 1] == 0.0)
                for stop_index in range(
                    max(horizon - minimum_rest_steps + 1, 0),
                    horizon,
                ):
                    model.temporal.add(
                        model.event_stop[name, track, stop_index] == 0.0
                    )

    coefficient = inputs.coefficients

    def loss_expression(name: str):
        scenario = scenarios[name]
        return sum(
            dt
            * (
                coefficient.kappa_access
                * model.access_shortfall[name, index]
                + coefficient.kappa_grid
                * model.grid_curtailment[name, index]
                + coefficient.kappa_green * model.green_shift[name, index]
            )
            for index in range(len(scenario.periods))
        )

    model.cvar_epigraph = ConstraintList()
    for name in names:
        model.cvar_epigraph.add(
            model.zeta[name] >= loss_expression(name) - model.var_eta
        )
    model.expansion_cost_expr = Expression(
        expr=inputs.provisioning_cost_per_mw * model.flex_budget
    )
    model.operating_cost_expr = Expression(
        expr=sum(
            scenarios[name].probability * loss_expression(name)
            for name in names
        )
    )
    model.cvar_expr = Expression(
        expr=model.var_eta
        + (1.0 / (1.0 - inputs.beta))
        * sum(
            scenarios[name].probability * model.zeta[name] for name in names
        )
    )
    model.total_cost = Objective(
        expr=model.expansion_cost_expr
        + model.operating_cost_expr
        + inputs.lambda_risk * model.cvar_expr,
        sense=minimize,
    )
    model._temporal_scenarios = scenarios
    model._temporal_tracks = tracks
    return model


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


def _clean_nonnegative(raw: object) -> float:
    number = float(value(raw))
    return 0.0 if -_TOLERANCE <= number < 0.0 else number


def _failed_result(
    inputs: TemporalEconomicInputs,
    termination: str,
    solver_status: str,
    *,
    proven_infeasible: bool,
) -> TemporalEconomicResult:
    return TemporalEconomicResult(
        feasible=False,
        proven_infeasible=proven_infeasible,
        termination_condition=termination,
        solver_status=solver_status,
        objective=None,
        expansion_cost=None,
        expected_operating_cost=None,
        conditional_value_at_risk=None,
        value_at_risk=None,
        provisioned_flexibility_mw=None,
        scenario_dispatch={},
        enforce_joint_budget=inputs.enforce_joint_budget,
        parameter_status=inputs.parameter_status,
        security_certified=False,
        risk_measure_scope=TEMPORAL_ECONOMIC_SCOPE,
    )


def solve_temporal_economic_stochastic(
    inputs: TemporalEconomicInputs,
    *,
    solver_name: str = "highs",
    tee: bool = False,
) -> TemporalEconomicResult:
    """Solve the chronological shared-envelope or B6 recourse model."""

    max_duration_steps, minimum_rest_steps = _validate_inputs(inputs)
    model = _build_model(inputs, max_duration_steps, minimum_rest_steps)
    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    raw = solver.solve(model, tee=tee, load_solutions=False)
    termination = raw.solver.termination_condition
    solver_status = str(raw.solver.status)
    if termination not in _OPTIMAL:
        return _failed_result(
            inputs,
            str(termination),
            solver_status,
            proven_infeasible=termination in _PROVEN_INFEASIBLE,
        )
    model.solutions.load_from(raw)
    maximum_residual = _constraint_residual(model)
    if maximum_residual > _TOLERANCE:
        return _failed_result(
            inputs,
            "solution_audit_failed",
            solver_status,
            proven_infeasible=False,
        )

    dt = float(inputs.envelope.time_step_hours)
    tracks = model._temporal_tracks
    dispatch: dict[str, TemporalScenarioDispatch] = {}
    service_losses: list[ScenarioServiceLoss] = []
    expected_cost = 0.0
    provisioned = _clean_nonnegative(model.flex_budget)
    for scenario in inputs.scenarios:
        horizon = len(scenario.periods)
        grid = tuple(
            _clean_nonnegative(model.grid_curtailment[scenario.name, index])
            for index in range(horizon)
        )
        green = tuple(
            _clean_nonnegative(model.green_shift[scenario.name, index])
            for index in range(horizon)
        )
        shortfall = tuple(
            _clean_nonnegative(model.access_shortfall[scenario.name, index])
            for index in range(horizon)
        )
        physical = tuple(
            grid[index] + green[index] for index in range(horizon)
        )
        event_count = {
            period: round(
                sum(
                    float(
                        value(
                            model.event_start[
                                scenario.name, track, index
                            ]
                        )
                    )
                    for track in tracks
                    for index, candidate in enumerate(scenario.periods)
                    if candidate == period
                )
            )
            for period in dict.fromkeys(scenario.periods)
        }
        energy = {
            period: sum(
                physical[index] * dt
                for index, candidate in enumerate(scenario.periods)
                if candidate == period
            )
            for period in dict.fromkeys(scenario.periods)
        }
        access_mwh = sum(shortfall) * dt
        grid_mwh = sum(grid) * dt
        green_mwh = sum(green) * dt
        loss = (
            inputs.coefficients.kappa_access * access_mwh
            + inputs.coefficients.kappa_grid * grid_mwh
            + inputs.coefficients.kappa_green * green_mwh
        )
        expected_cost += scenario.probability * loss
        service_losses.append(
            ScenarioServiceLoss(
                name=scenario.name,
                probability=scenario.probability,
                access_shortfall_mwh=access_mwh,
                grid_curtailment_mwh=grid_mwh,
                green_shift_mwh=green_mwh,
                permanent_drop_mwh=0.0,
                firm_breach_mwh=0.0,
                conditional_breach_mwh=0.0,
            )
        )
        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        physical_audit = evaluate_chronological_flexibility(
            ChronologicalFlexibilityTrace(
                name=f"{scenario.name}_physical_combined_dispatch",
                timestamps=tuple(
                    start + timedelta(hours=dt * index)
                    for index in range(horizon)
                ),
                periods=scenario.periods,
                grid_call_mw=physical,
                call_limit_mw=(provisioned,) * horizon,
                recovery_headroom_mw=scenario.recovery_headroom_mw,
                boundary_state_status="clean_boundary_with_zero_carry_in",
                completed_periods=scenario.completed_periods,
                initial_has_prior_event=False,
                prescribed_recovery_power_mw=None,
                require_terminal_event_inactive=(
                    scenario.require_terminal_event_inactive
                ),
            ),
            inputs.envelope,
        )
        physical_violations = list(physical_audit.violations)
        if (
            scenario.require_terminal_event_inactive
            and physical_audit.terminal_has_prior_event
            and (
                physical_audit.terminal_interevent_rest_hours is None
                or physical_audit.terminal_interevent_rest_hours + _TOLERANCE
                < inputs.envelope.minimum_recovery_hours
            )
        ):
            physical_violations.append("terminal_interevent_recovery_incomplete")
        dispatch[scenario.name] = TemporalScenarioDispatch(
            grid_curtailment_mw=grid,
            green_shift_mw=green,
            access_shortfall_mw=shortfall,
            physical_combined_call_mw=physical,
            modeled_event_count_by_period=event_count,
            curtailment_energy_mwh_by_period=energy,
            maximum_physical_budget_excess_mw=max(
                max(physical) - provisioned, 0.0
            ),
            physical_envelope_feasible=not physical_violations,
            physical_envelope_violations=tuple(physical_violations),
            physical_recovery_power_mw=(
                physical_audit.effective_recovery_power_mw
            ),
            physical_recovery_debt_mwh=physical_audit.recovery_debt_mwh,
            physical_event_count_by_period=physical_audit.event_count_by_period,
            physical_terminal_recovery_debt_mwh=(
                physical_audit.terminal_recovery_debt_mwh
            ),
            maximum_temporal_residual=maximum_residual,
            scenario_loss=loss,
        )

    if inputs.enforce_joint_budget and any(
        not item.physical_envelope_feasible for item in dispatch.values()
    ):
        return _failed_result(
            inputs,
            "physical_replay_audit_failed",
            solver_status,
            proven_infeasible=False,
        )

    risk = evaluate_service_cvar(
        service_losses, inputs.coefficients, beta=inputs.beta
    )
    expansion = inputs.provisioning_cost_per_mw * provisioned
    objective = (
        expansion
        + expected_cost
        + inputs.lambda_risk * risk.conditional_value_at_risk
    )
    return TemporalEconomicResult(
        feasible=True,
        proven_infeasible=False,
        termination_condition=str(termination),
        solver_status=solver_status,
        objective=objective,
        expansion_cost=expansion,
        expected_operating_cost=expected_cost,
        conditional_value_at_risk=risk.conditional_value_at_risk,
        value_at_risk=risk.value_at_risk,
        provisioned_flexibility_mw=provisioned,
        scenario_dispatch=dispatch,
        enforce_joint_budget=inputs.enforce_joint_budget,
        parameter_status=(
            f"{inputs.parameter_status}|{inputs.envelope.parameter_status}|"
            "derived_temporal_not_empirical"
        ),
        security_certified=False,
        risk_measure_scope=TEMPORAL_ECONOMIC_SCOPE,
    )
