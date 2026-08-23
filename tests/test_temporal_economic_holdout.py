"""TDD pins for chronological RQ2 H2 fixed-policy holdout execution."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.evaluation.flexibility_envelope import ChronologicalFlexibilityEnvelope
from src.evaluation.service_risk import ServiceLossCoefficients
from src.evaluation.temporal_economic_holdout import (
    TemporalEconomicHoldoutInputs,
    TemporalPolicyPlan,
    evaluate_temporal_economic_holdout,
    execute_temporal_economic_holdout,
)
from src.models.economic_temporal_stochastic import TemporalEconomicScenario

STATUS = "synthetic_temporal_h2_test_not_empirical_or_security_evidence"


def _coefficients() -> ServiceLossCoefficients:
    return ServiceLossCoefficients(
        kappa_access=1000.0,
        kappa_grid=10.0,
        kappa_green=5.0,
        kappa_drop=2000.0,
        kappa_breach_firm=0.0,
        kappa_breach_conditional=0.0,
        parameter_status=STATUS,
    )


def _envelope() -> ChronologicalFlexibilityEnvelope:
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=2.0,
        minimum_recovery_hours=1.0,
        maximum_events_by_period={"q1": 2},
        maximum_curtailment_energy_mwh_by_period={"q1": 200.0},
        maximum_recovery_debt_mwh=200.0,
        maximum_recovery_power_mw=80.0,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=100.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={"q1": 0.0},
        parameter_status=STATUS,
    )


def _scenario(
    name: str,
    probability: float,
    grid,
    green,
    *,
    recovery=None,
    completed: bool = True,
    require_terminal_inactive: bool = True,
) -> TemporalEconomicScenario:
    grid = tuple(float(item) for item in grid)
    green = tuple(float(item) for item in green)
    hours = len(grid)
    return TemporalEconomicScenario(
        name=name,
        probability=probability,
        periods=("q1",) * hours,
        grid_need_mw=grid,
        green_call_mw=green,
        connected_demand_mw=(100.0,) * hours,
        recovery_headroom_mw=(
            tuple(float(item) for item in recovery)
            if recovery is not None
            else (100.0,) * hours
        ),
        completed_periods=frozenset({"q1"}) if completed else frozenset(),
        require_terminal_event_inactive=require_terminal_inactive,
        boundary_state_status="clean_boundary_with_zero_carry_in",
    )


def _inputs(training, holdout, **overrides) -> TemporalEconomicHoldoutInputs:
    values = {
        "training_scenarios": tuple(training),
        "holdout_scenarios": tuple(holdout),
        "envelope": _envelope(),
        "coefficients": _coefficients(),
        "provisioning_cost_per_mw": 100.0,
        "max_flexibility_budget_mw": 100.0,
        "lambda_risk": 0.0,
        "beta": 0.5,
        "parameter_status": STATUS,
        "service_shortfall_tolerance_mwh": 1.0e-6,
    }
    values.update(overrides)
    return TemporalEconomicHoldoutInputs(**values)


def test_temporal_h2_plans_once_and_pins_provision_on_holdout():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "holdout",
            1.0,
            (0.0, 30.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )

    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))

    assert result.h2_evaluated
    assert result.correct.committed_flexibility_mw == pytest.approx(80.0)
    assert result.b6.committed_flexibility_mw == pytest.approx(40.0)
    assert result.correct.leaf_outcomes[0].committed_flexibility_mw == (
        pytest.approx(80.0)
    )
    assert result.b6.leaf_outcomes[0].committed_flexibility_mw == (
        pytest.approx(40.0)
    )
    assert result.b6.leaf_outcomes[0].access_shortfall_mwh == pytest.approx(30.0)
    assert result.b6_extra_expected_shortfall_mwh == pytest.approx(30.0)


def test_mandatory_grid_duration_failure_is_classified_not_relaxed():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "duration_stress",
            1.0,
            (40.0, 40.0, 40.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 0.0, 80.0, 80.0),
        ),
    )

    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))
    leaf = result.b6.leaf_outcomes[0]

    assert not leaf.feasible
    assert leaf.proven_hard_temporal_failure
    assert not leaf.solver_unresolved
    assert leaf.duration_failure
    assert not leaf.mw_budget_failure
    assert result.b6.duration_failure_probability == pytest.approx(1.0)


def test_subminimum_mandatory_call_is_not_a_hard_failure_when_mip_can_raise_it():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "subminimum",
            1.0,
            (0.0, 0.5, 0.0, 0.0),
            (0.0, 0.5, 0.0, 0.0),
        ),
    )

    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))
    leaf = result.b6.leaf_outcomes[0]

    assert leaf.feasible
    assert not leaf.proven_hard_temporal_failure
    assert leaf.service_shortfall_failure is False
    assert result.b6.hard_temporal_failure_probability == pytest.approx(0.0)


def test_hard_failure_books_full_unserved_green_energy_without_soft_double_count():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "hard",
            1.0,
            (0.0, 50.0, 0.0, 0.0),
            (0.0, 20.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )

    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))
    leaf = result.b6.leaf_outcomes[0]

    assert leaf.proven_hard_temporal_failure
    assert not leaf.service_shortfall_failure
    assert leaf.access_shortfall_mwh == pytest.approx(20.0)
    assert result.b6.hard_temporal_failure_probability == pytest.approx(1.0)
    assert result.b6.service_failure_probability == pytest.approx(0.0)
    assert result.b6.expected_access_shortfall_mwh == pytest.approx(20.0)
    assert result.h2_b6_underdelivers_out_of_sample


def test_right_censored_terminal_event_is_reported_not_failed():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "censored",
            1.0,
            (0.0, 40.0),
            (0.0, 0.0),
            recovery=(0.0, 0.0),
            completed=False,
            require_terminal_inactive=False,
        ),
    )

    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))
    leaf = result.b6.leaf_outcomes[0]

    assert leaf.feasible
    assert leaf.right_censored
    assert not leaf.proven_hard_temporal_failure
    assert leaf.terminal_recovery_debt_mwh == pytest.approx(40.0)
    assert leaf.terminal_grid_call_mw == pytest.approx(40.0)
    assert leaf.terminal_active_event_duration_hours == pytest.approx(1.0)
    assert leaf.terminal_interevent_rest_hours is None
    assert leaf.terminal_has_prior_event
    assert result.b6.right_censored_probability == pytest.approx(1.0)
    assert result.b6.total_failure_probability == pytest.approx(0.0)


def test_unlinked_complete_window_requires_full_terminal_rest():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "short_rest",
            1.0,
            (0.0, 0.0, 40.0, 0.0),
            (0.0, 0.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 0.0, 40.0),
        ),
    )
    envelope = replace(_envelope(), minimum_recovery_hours=2.0)

    result = evaluate_temporal_economic_holdout(
        _inputs(training, holdout, envelope=envelope)
    )
    leaf = result.b6.leaf_outcomes[0]

    assert leaf.proven_hard_temporal_failure
    assert leaf.terminal_boundary_failure
    assert "terminal_interevent_recovery_incomplete" in (
        leaf.physical_violations
    )


def test_holdout_changes_do_not_change_training_commitment():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    mild = (
        _scenario(
            "mild",
            1.0,
            (0.0, 10.0, 0.0),
            (0.0, 10.0, 0.0),
        ),
    )
    severe = (
        _scenario(
            "severe",
            1.0,
            (80.0, 80.0, 80.0, 0.0),
            (0.0, 0.0, 0.0, 0.0),
        ),
    )

    first = evaluate_temporal_economic_holdout(_inputs(training, mild))
    second = evaluate_temporal_economic_holdout(_inputs(training, severe))

    assert first.correct.committed_flexibility_mw == pytest.approx(
        second.correct.committed_flexibility_mw
    )
    assert first.b6.committed_flexibility_mw == pytest.approx(
        second.b6.committed_flexibility_mw
    )


def test_unresolved_solver_result_is_not_counted_as_failure(monkeypatch):
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario("holdout", 1.0, (0.0, 10.0, 0.0), (0.0, 0.0, 0.0)),
    )

    import src.evaluation.temporal_economic_holdout as module

    real_solve = module.solve_temporal_economic_stochastic
    calls = 0

    def unresolved_after_training(*args, **kwargs):
        nonlocal calls
        calls += 1
        result = real_solve(*args, **kwargs)
        if calls > 2:
            return replace(
                result,
                feasible=False,
                proven_infeasible=False,
                termination_condition="maxTimeLimit",
                scenario_dispatch={},
            )
        return result

    monkeypatch.setattr(
        module, "solve_temporal_economic_stochastic", unresolved_after_training
    )
    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))

    assert result.correct.solver_unresolved_probability == pytest.approx(1.0)
    assert result.correct.total_failure_probability == pytest.approx(0.0)
    assert not result.h2_evaluated


def test_any_positive_unresolved_probability_closes_h2(monkeypatch):
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "tiny_unresolved",
            5.0e-7,
            (0.0, 10.0, 0.0),
            (0.0, 0.0, 0.0),
        ),
        _scenario(
            "resolved",
            1.0 - 5.0e-7,
            (0.0, 10.0, 0.0),
            (0.0, 0.0, 0.0),
        ),
    )

    import src.evaluation.temporal_economic_holdout as module

    real_solve = module.solve_temporal_economic_stochastic

    def inject_tiny_unresolved(inputs, **kwargs):
        result = real_solve(inputs, **kwargs)
        if (
            inputs.fixed_flexibility_mw is not None
            and inputs.scenarios[0].name == "tiny_unresolved"
        ):
            return replace(
                result,
                feasible=False,
                proven_infeasible=False,
                termination_condition="maxTimeLimit",
                scenario_dispatch={},
            )
        return result

    monkeypatch.setattr(
        module,
        "solve_temporal_economic_stochastic",
        inject_tiny_unresolved,
    )
    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))

    assert result.correct.solver_unresolved_probability == pytest.approx(
        5.0e-7
    )
    assert not result.h2_evaluated
    assert not result.h2_b6_underdelivers_out_of_sample


def test_unresolved_main_recourse_cannot_borrow_diagnostic_infeasibility(
    monkeypatch,
):
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "hard",
            1.0,
            (0.0, 50.0, 0.0, 0.0),
            (0.0, 20.0, 0.0, 0.0),
            recovery=(0.0, 0.0, 80.0, 0.0),
        ),
    )
    import src.evaluation.temporal_economic_holdout as module

    real_solve = module.solve_temporal_economic_stochastic

    def inject_main_unresolved(inputs, **kwargs):
        result = real_solve(inputs, **kwargs)
        if (
            inputs.fixed_flexibility_mw == pytest.approx(40.0)
            and any(inputs.scenarios[0].green_call_mw)
        ):
            return replace(
                result,
                feasible=False,
                proven_infeasible=False,
                termination_condition="maxTimeLimit",
                scenario_dispatch={},
            )
        return result

    monkeypatch.setattr(
        module,
        "solve_temporal_economic_stochastic",
        inject_main_unresolved,
    )
    result = evaluate_temporal_economic_holdout(_inputs(training, holdout))
    leaf = result.b6.leaf_outcomes[0]

    assert leaf.solver_unresolved
    assert not leaf.proven_hard_temporal_failure
    assert result.b6.hard_temporal_failure_probability == pytest.approx(0.0)
    assert not result.h2_evaluated


def test_minimum_event_power_hard_failure_has_closed_classification():
    training = (
        _scenario(
            "train",
            1.0,
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0),
        ),
    )
    holdout = (
        _scenario(
            "subminimum",
            1.0,
            (0.0, 0.5, 0.0),
            (0.0, 0.0, 0.0),
        ),
    )
    inputs = _inputs(training, holdout)
    plans = TemporalPolicyPlan(
        correct=(True, False, 0.5),
        b6=(True, False, 0.5),
    )

    result = execute_temporal_economic_holdout(inputs, plans)
    leaf = result.correct.leaf_outcomes[0]

    assert leaf.proven_hard_temporal_failure
    assert leaf.minimum_event_power_failure
    assert result.correct.minimum_event_power_failure_probability == (
        pytest.approx(1.0)
    )
