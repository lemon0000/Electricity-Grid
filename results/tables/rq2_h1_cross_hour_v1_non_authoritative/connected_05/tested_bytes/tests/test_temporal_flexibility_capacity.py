from __future__ import annotations

import pytest

from src.evaluation.flexibility_envelope import ChronologicalFlexibilityEnvelope
from src.evaluation.service_risk import ServiceLossCoefficients
from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
)
from src.models.temporal_flexibility_capacity import (
    plan_minimum_flexibility_pair,
)

STATUS = "synthetic_minimum_capacity_test"


def _inputs(available: float) -> TemporalEconomicInputs:
    scenario = TemporalEconomicScenario(
        name="training",
        probability=1.0,
        periods=("block",) * 4,
        grid_need_mw=(0.0, 40.0, 0.0, 0.0),
        green_call_mw=(0.0, 40.0, 0.0, 0.0),
        connected_demand_mw=(100.0,) * 4,
        recovery_headroom_mw=(0.0, 0.0, 100.0, 100.0),
        completed_periods=frozenset({"block"}),
        require_terminal_event_inactive=True,
        boundary_state_status="clean_boundary_with_zero_carry_in",
        available_flexibility_mw=(0.0, available, 0.0, 0.0),
    )
    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=1.0,
        minimum_recovery_hours=0.0,
        maximum_events_by_period={"block": 1},
        maximum_curtailment_energy_mwh_by_period={"block": 100.0},
        maximum_recovery_debt_mwh=100.0,
        maximum_recovery_power_mw=100.0,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=100.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={"block": 0.0},
        parameter_status=STATUS,
    )
    coefficients = ServiceLossCoefficients(
        kappa_access=0.0,
        kappa_grid=0.0,
        kappa_green=0.0,
        kappa_drop=0.0,
        kappa_breach_firm=0.0,
        kappa_breach_conditional=0.0,
        parameter_status=STATUS,
    )
    return TemporalEconomicInputs(
        scenarios=(scenario,),
        envelope=envelope,
        coefficients=coefficients,
        provisioning_cost_per_mw=0.0,
        max_flexibility_budget_mw=100.0,
        lambda_risk=0.0,
        beta=0.5,
        enforce_joint_budget=True,
        parameter_status=STATUS,
    )


def test_minimum_capacity_identifies_exact_duplicate_commitment_gap():
    result = plan_minimum_flexibility_pair(_inputs(80.0))

    assert result.correct.feasible
    assert result.b6.feasible
    assert result.correct.minimum_capacity == pytest.approx(80.0)
    assert result.b6.minimum_capacity == pytest.approx(40.0)


def test_available_flexibility_can_reject_correct_but_not_b6_contract():
    result = plan_minimum_flexibility_pair(_inputs(40.0))

    assert not result.correct.feasible
    assert result.correct.proven_infeasible
    assert result.b6.feasible
    assert result.b6.minimum_capacity == pytest.approx(40.0)
