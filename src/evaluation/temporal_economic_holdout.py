"""Chronological RQ2 H2 fixed-policy out-of-sample execution.

Training chooses one nonanticipative flexibility provision for the correct
shared-envelope model and one for B6. Holdout execution pins that provision and
always uses the true shared temporal envelope. Solver-unknown outcomes are kept
separate from failures. A hard temporal failure is reported only when an
independent audit of the mandatory network-call trace produces a concrete
envelope violation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from numbers import Real

from ..models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
    solve_temporal_economic_stochastic,
)
from .flexibility_envelope import (
    ChronologicalFlexibilityEnvelope,
    ChronologicalFlexibilityTrace,
    evaluate_chronological_flexibility,
)
from .service_risk import ServiceLossCoefficients

TEMPORAL_HOLDOUT_SCOPE = (
    "synthetic_chronological_fixed_policy_holdout_execution_against_true_shared_"
    "envelope_not_empirical_probability_or_security_certification"
)
_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class TemporalEconomicHoldoutInputs:
    training_scenarios: tuple[TemporalEconomicScenario, ...]
    holdout_scenarios: tuple[TemporalEconomicScenario, ...]
    envelope: ChronologicalFlexibilityEnvelope
    coefficients: ServiceLossCoefficients
    provisioning_cost_per_mw: float
    max_flexibility_budget_mw: float
    lambda_risk: float
    beta: float
    parameter_status: str
    service_shortfall_tolerance_mwh: float


@dataclass(frozen=True)
class TemporalHoldoutLeafOutcome:
    name: str
    probability: float
    committed_flexibility_mw: float
    feasible: bool
    proven_hard_temporal_failure: bool
    solver_unresolved: bool
    service_shortfall_failure: bool
    right_censored: bool
    mw_budget_failure: bool
    minimum_event_power_failure: bool
    response_or_ramp_failure: bool
    duration_failure: bool
    event_count_or_rest_failure: bool
    energy_failure: bool
    recovery_debt_failure: bool
    terminal_boundary_failure: bool
    physical_violations: tuple[str, ...]
    access_shortfall_mwh: float | None
    peak_recovery_debt_mwh: float
    terminal_recovery_debt_mwh: float
    terminal_grid_call_mw: float
    terminal_active_event_duration_hours: float
    terminal_interevent_rest_hours: float | None
    terminal_has_prior_event: bool
    maximum_event_duration_hours: float
    event_count_by_period: dict[str, int]
    curtailment_energy_mwh_by_period: dict[str, float]
    scenario_loss: float | None


@dataclass(frozen=True)
class TemporalHoldoutPolicyEvaluation:
    variant: str
    enforce_joint_budget_in_planning: bool
    training_feasible: bool
    training_solver_unresolved: bool
    committed_flexibility_mw: float | None
    leaf_outcomes: tuple[TemporalHoldoutLeafOutcome, ...]
    hard_temporal_failure_probability: float
    service_failure_probability: float
    total_failure_probability: float
    solver_unresolved_probability: float
    right_censored_probability: float
    mw_budget_failure_probability: float
    minimum_event_power_failure_probability: float
    response_or_ramp_failure_probability: float
    duration_failure_probability: float
    event_count_or_rest_failure_probability: float
    energy_failure_probability: float
    recovery_debt_failure_probability: float
    terminal_boundary_failure_probability: float
    expected_access_shortfall_mwh: float
    expected_terminal_recovery_debt_mwh: float
    expected_peak_recovery_debt_mwh: float
    parameter_status: str


@dataclass(frozen=True)
class TemporalEconomicHoldoutResult:
    correct: TemporalHoldoutPolicyEvaluation
    b6: TemporalHoldoutPolicyEvaluation
    h2_evaluated: bool
    b6_extra_failure_probability: float | None
    b6_extra_expected_shortfall_mwh: float | None
    b6_extra_expected_terminal_debt_mwh: float | None
    h2_b6_underdelivers_out_of_sample: bool
    parameter_status: str
    risk_measure_scope: str
    security_certified: bool


@dataclass(frozen=True)
class TemporalPolicyPlan:
    correct: tuple[bool, bool, float | None]
    b6: tuple[bool, bool, float | None]


def _finite(name: str, raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(raw):
        raise ValueError(f"{name} must be a finite number")
    return float(raw)


def _nonnegative(name: str, raw: object) -> float:
    number = _finite(name, raw)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _validate_inputs(
    inputs: TemporalEconomicHoldoutInputs, *, require_holdout: bool
) -> None:
    if not inputs.parameter_status:
        raise ValueError("parameter_status must be explicit")
    if not inputs.training_scenarios:
        raise ValueError("training scenarios must be nonempty")
    if require_holdout and not inputs.holdout_scenarios:
        raise ValueError("holdout scenarios must be nonempty")
    train_names = {scenario.name for scenario in inputs.training_scenarios}
    holdout_names = {scenario.name for scenario in inputs.holdout_scenarios}
    if train_names & holdout_names:
        raise ValueError("training and holdout scenario names must be disjoint")
    for label, scenarios in (
        ("training", inputs.training_scenarios),
        *((("holdout", inputs.holdout_scenarios),) if require_holdout else ()),
    ):
        if len({scenario.name for scenario in scenarios}) != len(scenarios):
            raise ValueError(f"{label} scenario names must be unique")
        probability = sum(
            _nonnegative(
                f"{label}.probability[{scenario.name}]", scenario.probability
            )
            for scenario in scenarios
        )
        if abs(probability - 1.0) > 1.0e-9:
            raise ValueError(f"{label} probabilities must sum to one")
    _nonnegative("provisioning_cost_per_mw", inputs.provisioning_cost_per_mw)
    _nonnegative(
        "max_flexibility_budget_mw", inputs.max_flexibility_budget_mw
    )
    _nonnegative("lambda_risk", inputs.lambda_risk)
    _nonnegative(
        "service_shortfall_tolerance_mwh",
        inputs.service_shortfall_tolerance_mwh,
    )
    beta = _finite("beta", inputs.beta)
    if not 0.0 <= beta < 1.0:
        raise ValueError("beta must lie in [0, 1)")


def _model_inputs(
    inputs: TemporalEconomicHoldoutInputs,
    scenarios: tuple[TemporalEconomicScenario, ...],
    *,
    joint: bool,
    fixed: float | None,
) -> TemporalEconomicInputs:
    return TemporalEconomicInputs(
        scenarios=scenarios,
        envelope=inputs.envelope,
        coefficients=inputs.coefficients,
        provisioning_cost_per_mw=inputs.provisioning_cost_per_mw,
        max_flexibility_budget_mw=inputs.max_flexibility_budget_mw,
        lambda_risk=inputs.lambda_risk if fixed is None else 0.0,
        beta=inputs.beta,
        enforce_joint_budget=joint,
        fixed_flexibility_mw=fixed,
        parameter_status=inputs.parameter_status,
    )


def _plan(
    inputs: TemporalEconomicHoldoutInputs,
    *,
    joint: bool,
    solver_name: str,
) -> tuple[bool, bool, float | None]:
    result = solve_temporal_economic_stochastic(
        _model_inputs(
            inputs,
            inputs.training_scenarios,
            joint=joint,
            fixed=None,
        ),
        solver_name=solver_name,
    )
    return (
        result.feasible,
        not result.feasible and not result.proven_infeasible,
        result.provisioned_flexibility_mw,
    )


def _single_leaf(
    scenario: TemporalEconomicScenario,
) -> TemporalEconomicScenario:
    return TemporalEconomicScenario(
        name=scenario.name,
        probability=1.0,
        periods=scenario.periods,
        grid_need_mw=scenario.grid_need_mw,
        green_call_mw=scenario.green_call_mw,
        connected_demand_mw=scenario.connected_demand_mw,
        recovery_headroom_mw=scenario.recovery_headroom_mw,
        completed_periods=scenario.completed_periods,
        require_terminal_event_inactive=scenario.require_terminal_event_inactive,
        boundary_state_status=scenario.boundary_state_status,
        available_flexibility_mw=scenario.available_flexibility_mw,
    )


def _mandatory_grid_scenario(
    scenario: TemporalEconomicScenario,
) -> TemporalEconomicScenario:
    return TemporalEconomicScenario(
        name=scenario.name,
        probability=1.0,
        periods=scenario.periods,
        grid_need_mw=scenario.grid_need_mw,
        green_call_mw=(0.0,) * len(scenario.periods),
        connected_demand_mw=scenario.connected_demand_mw,
        recovery_headroom_mw=scenario.recovery_headroom_mw,
        completed_periods=scenario.completed_periods,
        require_terminal_event_inactive=scenario.require_terminal_event_inactive,
        boundary_state_status=scenario.boundary_state_status,
        available_flexibility_mw=scenario.available_flexibility_mw,
    )


def _fixed_call_audit(
    scenario: TemporalEconomicScenario,
    envelope: ChronologicalFlexibilityEnvelope,
    committed: float,
):
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    dt = float(envelope.time_step_hours)
    result = evaluate_chronological_flexibility(
        ChronologicalFlexibilityTrace(
            name=f"{scenario.name}_mandatory_grid_holdout_audit",
            timestamps=tuple(
                start + timedelta(hours=dt * index)
                for index in range(len(scenario.periods))
            ),
            periods=scenario.periods,
            grid_call_mw=scenario.grid_need_mw,
            call_limit_mw=(committed,) * len(scenario.periods),
            recovery_headroom_mw=scenario.recovery_headroom_mw,
            boundary_state_status=scenario.boundary_state_status,
            completed_periods=scenario.completed_periods,
            initial_has_prior_event=False,
            prescribed_recovery_power_mw=None,
            require_terminal_event_inactive=(
                scenario.require_terminal_event_inactive
            ),
        ),
        envelope,
    )
    violations = list(result.violations)
    if (
        scenario.require_terminal_event_inactive
        and result.terminal_has_prior_event
        and (
            result.terminal_interevent_rest_hours is None
            or result.terminal_interevent_rest_hours + _TOLERANCE
            < envelope.minimum_recovery_hours
        )
    ):
        violations.append("terminal_interevent_recovery_incomplete")
    return result, tuple(dict.fromkeys(violations))


def _has(violations: tuple[str, ...], *fragments: str) -> bool:
    return any(
        fragment in violation
        for violation in violations
        for fragment in fragments
    )


def _execute_leaf(
    inputs: TemporalEconomicHoldoutInputs,
    scenario: TemporalEconomicScenario,
    committed: float,
    *,
    solver_name: str,
) -> TemporalHoldoutLeafOutcome:
    audit, violations = _fixed_call_audit(
        scenario, inputs.envelope, committed
    )
    result = solve_temporal_economic_stochastic(
        _model_inputs(
            inputs,
            (_single_leaf(scenario),),
            joint=True,
            fixed=committed,
        ),
        solver_name=solver_name,
    )
    diagnostic = None
    if not result.feasible:
        diagnostic = solve_temporal_economic_stochastic(
            _model_inputs(
                inputs,
                (_mandatory_grid_scenario(scenario),),
                joint=True,
                fixed=committed,
            ),
            solver_name=solver_name,
        )
    hard_failure = bool(
        not result.feasible
        and result.proven_infeasible
        and diagnostic is not None
        and diagnostic.proven_infeasible
    )
    unresolved = bool(not result.feasible and not hard_failure)
    right_censored = (
        scenario.periods[-1] not in scenario.completed_periods
        or not scenario.require_terminal_event_inactive
    )
    dispatch = (
        result.scenario_dispatch.get(scenario.name) if result.feasible else None
    )
    if dispatch is not None:
        physical_audit, physical_violations = _fixed_call_audit(
            TemporalEconomicScenario(
                name=scenario.name,
                probability=scenario.probability,
                periods=scenario.periods,
                grid_need_mw=dispatch.physical_combined_call_mw,
                green_call_mw=(0.0,) * len(scenario.periods),
                connected_demand_mw=scenario.connected_demand_mw,
                recovery_headroom_mw=scenario.recovery_headroom_mw,
                completed_periods=scenario.completed_periods,
                require_terminal_event_inactive=(
                    scenario.require_terminal_event_inactive
                ),
                boundary_state_status=scenario.boundary_state_status,
                available_flexibility_mw=scenario.available_flexibility_mw,
            ),
            inputs.envelope,
            committed,
        )
        shortfall_mwh = (
            sum(dispatch.access_shortfall_mw)
            * inputs.envelope.time_step_hours
        )
    elif hard_failure:
        shortfall_mwh = (
            sum(scenario.green_call_mw) * inputs.envelope.time_step_hours
        )
    else:
        shortfall_mwh = None
    service_failure = (
        dispatch is not None
        and shortfall_mwh is not None
        and shortfall_mwh > inputs.service_shortfall_tolerance_mwh
    )
    if hard_failure:
        reported_violations = tuple(
            dict.fromkeys(
                ("mandatory_grid_temporal_mip_proven_infeasible", *violations)
            )
        )
    elif dispatch is not None:
        reported_violations = physical_violations
    else:
        reported_violations = ()
    if dispatch is not None:
        state_audit = physical_audit
        peak_debt = state_audit.peak_recovery_debt_mwh
        terminal_debt = state_audit.terminal_recovery_debt_mwh
        maximum_duration = state_audit.maximum_event_duration_hours
        event_count = state_audit.event_count_by_period
        energy = state_audit.curtailment_energy_mwh_by_period
    else:
        state_audit = audit
        peak_debt = audit.peak_recovery_debt_mwh
        terminal_debt = audit.terminal_recovery_debt_mwh
        maximum_duration = audit.maximum_event_duration_hours
        event_count = audit.event_count_by_period
        energy = audit.curtailment_energy_mwh_by_period
    return TemporalHoldoutLeafOutcome(
        name=scenario.name,
        probability=scenario.probability,
        committed_flexibility_mw=committed,
        feasible=result.feasible,
        proven_hard_temporal_failure=hard_failure,
        solver_unresolved=unresolved,
        service_shortfall_failure=service_failure,
        right_censored=right_censored,
        mw_budget_failure=hard_failure
        and _has(violations, "call_limit_exceeded"),
        minimum_event_power_failure=hard_failure
        and _has(violations, "minimum_event_power_violated"),
        response_or_ramp_failure=hard_failure
        and _has(violations, "response_deadline", "curtailment_ramp"),
        duration_failure=hard_failure
        and _has(violations, "maximum_event_duration"),
        event_count_or_rest_failure=hard_failure
        and _has(
            violations, "maximum_events", "minimum_interevent_recovery"
        ),
        energy_failure=hard_failure
        and _has(violations, "maximum_curtailment_energy"),
        recovery_debt_failure=hard_failure
        and _has(violations, "maximum_recovery_debt", "terminal_debt"),
        terminal_boundary_failure=hard_failure
        and _has(
            violations,
            "trace_ends_during_active_event",
            "terminal_interevent_recovery_incomplete",
        ),
        physical_violations=reported_violations,
        access_shortfall_mwh=shortfall_mwh,
        peak_recovery_debt_mwh=peak_debt,
        terminal_recovery_debt_mwh=terminal_debt,
        terminal_grid_call_mw=state_audit.terminal_grid_call_mw,
        terminal_active_event_duration_hours=(
            state_audit.terminal_active_event_duration_hours
        ),
        terminal_interevent_rest_hours=(
            state_audit.terminal_interevent_rest_hours
        ),
        terminal_has_prior_event=state_audit.terminal_has_prior_event,
        maximum_event_duration_hours=maximum_duration,
        event_count_by_period=event_count,
        curtailment_energy_mwh_by_period=energy,
        scenario_loss=dispatch.scenario_loss if dispatch is not None else None,
    )


def execute_fixed_temporal_policy(
    inputs: TemporalEconomicHoldoutInputs,
    scenario: TemporalEconomicScenario,
    committed_flexibility_mw: float,
    *,
    solver_name: str = "highs",
) -> TemporalHoldoutLeafOutcome:
    """Execute one fixed capacity under the true shared physical envelope."""

    _validate_inputs(inputs, require_holdout=False)
    committed = _nonnegative(
        "committed_flexibility_mw",
        committed_flexibility_mw,
    )
    if committed > inputs.max_flexibility_budget_mw + _TOLERANCE:
        raise ValueError("committed flexibility exceeds maximum budget")
    return _execute_leaf(
        inputs,
        scenario,
        committed,
        solver_name=solver_name,
    )


def _probability(
    outcomes: tuple[TemporalHoldoutLeafOutcome, ...], field: str
) -> float:
    return sum(
        outcome.probability
        for outcome in outcomes
        if bool(getattr(outcome, field))
    )


def _policy(
    inputs: TemporalEconomicHoldoutInputs,
    *,
    variant: str,
    joint_in_planning: bool,
    plan: tuple[bool, bool, float | None],
    solver_name: str,
) -> TemporalHoldoutPolicyEvaluation:
    training_feasible, training_unresolved, committed = plan
    if not training_feasible or committed is None:
        return TemporalHoldoutPolicyEvaluation(
            variant=variant,
            enforce_joint_budget_in_planning=joint_in_planning,
            training_feasible=False,
            training_solver_unresolved=training_unresolved,
            committed_flexibility_mw=None,
            leaf_outcomes=(),
            hard_temporal_failure_probability=0.0,
            service_failure_probability=0.0,
            total_failure_probability=0.0,
            solver_unresolved_probability=0.0,
            right_censored_probability=0.0,
            mw_budget_failure_probability=0.0,
            minimum_event_power_failure_probability=0.0,
            response_or_ramp_failure_probability=0.0,
            duration_failure_probability=0.0,
            event_count_or_rest_failure_probability=0.0,
            energy_failure_probability=0.0,
            recovery_debt_failure_probability=0.0,
            terminal_boundary_failure_probability=0.0,
            expected_access_shortfall_mwh=0.0,
            expected_terminal_recovery_debt_mwh=0.0,
            expected_peak_recovery_debt_mwh=0.0,
            parameter_status=inputs.parameter_status,
        )
    outcomes = tuple(
        _execute_leaf(
            inputs,
            scenario,
            committed,
            solver_name=solver_name,
        )
        for scenario in inputs.holdout_scenarios
    )
    hard_probability = _probability(
        outcomes, "proven_hard_temporal_failure"
    )
    service_probability = _probability(
        outcomes, "service_shortfall_failure"
    )
    return TemporalHoldoutPolicyEvaluation(
        variant=variant,
        enforce_joint_budget_in_planning=joint_in_planning,
        training_feasible=True,
        training_solver_unresolved=False,
        committed_flexibility_mw=committed,
        leaf_outcomes=outcomes,
        hard_temporal_failure_probability=hard_probability,
        service_failure_probability=service_probability,
        total_failure_probability=sum(
            outcome.probability
            for outcome in outcomes
            if outcome.proven_hard_temporal_failure
            or outcome.service_shortfall_failure
        ),
        solver_unresolved_probability=_probability(
            outcomes, "solver_unresolved"
        ),
        right_censored_probability=_probability(outcomes, "right_censored"),
        mw_budget_failure_probability=_probability(
            outcomes, "mw_budget_failure"
        ),
        minimum_event_power_failure_probability=_probability(
            outcomes, "minimum_event_power_failure"
        ),
        response_or_ramp_failure_probability=_probability(
            outcomes, "response_or_ramp_failure"
        ),
        duration_failure_probability=_probability(
            outcomes, "duration_failure"
        ),
        event_count_or_rest_failure_probability=_probability(
            outcomes, "event_count_or_rest_failure"
        ),
        energy_failure_probability=_probability(outcomes, "energy_failure"),
        recovery_debt_failure_probability=_probability(
            outcomes, "recovery_debt_failure"
        ),
        terminal_boundary_failure_probability=_probability(
            outcomes, "terminal_boundary_failure"
        ),
        expected_access_shortfall_mwh=sum(
            outcome.probability * (outcome.access_shortfall_mwh or 0.0)
            for outcome in outcomes
        ),
        expected_terminal_recovery_debt_mwh=sum(
            outcome.probability * outcome.terminal_recovery_debt_mwh
            for outcome in outcomes
        ),
        expected_peak_recovery_debt_mwh=sum(
            outcome.probability * outcome.peak_recovery_debt_mwh
            for outcome in outcomes
        ),
        parameter_status=inputs.parameter_status,
    )


def plan_temporal_economic_policies(
    inputs: TemporalEconomicHoldoutInputs,
    *,
    solver_name: str = "highs",
) -> TemporalPolicyPlan:
    """Freeze both training policies before any holdout work begins."""

    _validate_inputs(inputs, require_holdout=False)
    return TemporalPolicyPlan(
        correct=_plan(inputs, joint=True, solver_name=solver_name),
        b6=_plan(inputs, joint=False, solver_name=solver_name),
    )


def execute_temporal_economic_holdout(
    inputs: TemporalEconomicHoldoutInputs,
    plans: TemporalPolicyPlan,
    *,
    solver_name: str = "highs",
) -> TemporalEconomicHoldoutResult:
    """Execute already-frozen policies on unseen chronological scenarios."""

    _validate_inputs(inputs, require_holdout=True)
    correct = _policy(
        inputs,
        variant="correct_shared_temporal_envelope",
        joint_in_planning=True,
        plan=plans.correct,
        solver_name=solver_name,
    )
    b6 = _policy(
        inputs,
        variant="b6_error_split_temporal_envelopes",
        joint_in_planning=False,
        plan=plans.b6,
        solver_name=solver_name,
    )
    h2_evaluated = (
        correct.training_feasible
        and b6.training_feasible
        and not correct.training_solver_unresolved
        and not b6.training_solver_unresolved
        and not any(
            outcome.solver_unresolved for outcome in correct.leaf_outcomes
        )
        and not any(
            outcome.solver_unresolved for outcome in b6.leaf_outcomes
        )
    )
    extra_failure = (
        b6.total_failure_probability - correct.total_failure_probability
        if h2_evaluated
        else None
    )
    extra_shortfall = (
        b6.expected_access_shortfall_mwh
        - correct.expected_access_shortfall_mwh
        if h2_evaluated
        else None
    )
    extra_debt = (
        b6.expected_terminal_recovery_debt_mwh
        - correct.expected_terminal_recovery_debt_mwh
        if h2_evaluated
        else None
    )
    # H2 is a service-under-delivery claim. Recovery debt is reported as a
    # physical state, not a welfare offset: a policy can have lower debt only
    # because it failed to serve more load. Letting that lower debt negate
    # higher failure/shortfall would reward non-delivery.
    service_deltas = (extra_failure, extra_shortfall)
    underdelivers = h2_evaluated and bool(
        all(
            delta is not None and delta >= -_TOLERANCE
            for delta in service_deltas
        )
        and any(
            delta is not None and delta > _TOLERANCE
            for delta in service_deltas
        )
    )
    return TemporalEconomicHoldoutResult(
        correct=correct,
        b6=b6,
        h2_evaluated=h2_evaluated,
        b6_extra_failure_probability=extra_failure,
        b6_extra_expected_shortfall_mwh=extra_shortfall,
        b6_extra_expected_terminal_debt_mwh=extra_debt,
        h2_b6_underdelivers_out_of_sample=underdelivers,
        parameter_status=(
            f"{inputs.parameter_status}|{inputs.envelope.parameter_status}|"
            "fixed_policy_temporal_holdout_not_empirical"
        ),
        risk_measure_scope=TEMPORAL_HOLDOUT_SCOPE,
        security_certified=False,
    )


def evaluate_temporal_economic_holdout(
    inputs: TemporalEconomicHoldoutInputs,
    *,
    solver_name: str = "highs",
) -> TemporalEconomicHoldoutResult:
    """Plan both policies, then execute them pinned on holdout."""

    plans = plan_temporal_economic_policies(inputs, solver_name=solver_name)
    return execute_temporal_economic_holdout(
        inputs, plans, solver_name=solver_name
    )
