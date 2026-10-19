"""Hand-calculated pins for the chronological RQ2 L5 recourse model."""

from __future__ import annotations

from dataclasses import replace

import pytest
from pyomo.opt import TerminationCondition

import src.models.economic_temporal_stochastic as temporal_module
from src.evaluation import ChronologicalFlexibilityEnvelope
from src.evaluation.service_risk import ServiceLossCoefficients
from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
    solve_temporal_economic_stochastic,
)

STATUS = "synthetic_temporal_test_not_contract_or_security_evidence"


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


def _envelope(
    hours: int,
    *,
    maximum_event_duration_hours: float = 2.0,
    maximum_events: int = 2,
    maximum_energy_mwh: float = 200.0,
    maximum_debt_mwh: float = 200.0,
    maximum_recovery_power_mw: float = 20.0,
    terminal_debt_mwh: float = 0.0,
) -> ChronologicalFlexibilityEnvelope:
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=maximum_event_duration_hours,
        minimum_recovery_hours=1.0,
        maximum_events_by_period={"q1": maximum_events},
        maximum_curtailment_energy_mwh_by_period={"q1": maximum_energy_mwh},
        maximum_recovery_debt_mwh=maximum_debt_mwh,
        maximum_recovery_power_mw=maximum_recovery_power_mw,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=100.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={"q1": terminal_debt_mwh},
        parameter_status=f"{STATUS}|hours_{hours}",
    )


def _scenario(
    grid_need,
    green_call=None,
    *,
    recovery_headroom=None,
) -> TemporalEconomicScenario:
    grid_need = tuple(float(value) for value in grid_need)
    hours = len(grid_need)
    return TemporalEconomicScenario(
        name="stress",
        probability=1.0,
        periods=("q1",) * hours,
        grid_need_mw=grid_need,
        green_call_mw=(
            tuple(float(value) for value in green_call)
            if green_call is not None
            else (0.0,) * hours
        ),
        connected_demand_mw=(100.0,) * hours,
        recovery_headroom_mw=(
            tuple(float(value) for value in recovery_headroom)
            if recovery_headroom is not None
            else (100.0,) * hours
        ),
        completed_periods=frozenset({"q1"}),
        require_terminal_event_inactive=True,
        boundary_state_status="clean_boundary_with_zero_carry_in",
    )


def _inputs(
    scenario: TemporalEconomicScenario,
    *,
    envelope: ChronologicalFlexibilityEnvelope | None = None,
    joint: bool = True,
    fixed_flexibility_mw: float = 100.0,
) -> TemporalEconomicInputs:
    return TemporalEconomicInputs(
        scenarios=(scenario,),
        envelope=envelope or _envelope(len(scenario.periods)),
        coefficients=_coefficients(),
        provisioning_cost_per_mw=10.0,
        max_flexibility_budget_mw=100.0,
        lambda_risk=0.0,
        beta=0.5,
        enforce_joint_budget=joint,
        fixed_flexibility_mw=fixed_flexibility_mw,
        parameter_status=STATUS,
    )


def test_shared_temporal_envelope_rejects_b6_same_hour_double_commitment():
    scenario = _scenario(
        (0.0, 40.0, 0.0, 0.0),
        (0.0, 40.0, 0.0, 0.0),
    )
    correct = solve_temporal_economic_stochastic(
        _inputs(scenario, joint=True, fixed_flexibility_mw=40.0)
    )
    b6 = solve_temporal_economic_stochastic(
        _inputs(scenario, joint=False, fixed_flexibility_mw=40.0)
    )

    assert correct.feasible and b6.feasible
    correct_dispatch = correct.scenario_dispatch["stress"]
    assert correct_dispatch.access_shortfall_mw[1] == pytest.approx(40.0)
    dispatch = b6.scenario_dispatch["stress"]
    assert dispatch.grid_curtailment_mw[1] == pytest.approx(40.0)
    assert dispatch.green_shift_mw[1] == pytest.approx(40.0)
    assert dispatch.physical_combined_call_mw[1] == pytest.approx(80.0)
    assert dispatch.maximum_physical_budget_excess_mw == pytest.approx(40.0)
    assert dispatch.physical_envelope_feasible is False
    assert "call_limit_exceeded_at_step_1" in dispatch.physical_envelope_violations
    assert dispatch.physical_terminal_recovery_debt_mwh == pytest.approx(40.0)


def test_time_varying_available_flexibility_is_shared_only_by_correct_model():
    scenario = replace(
        _scenario(
            (0.0, 40.0, 0.0, 0.0),
            (0.0, 40.0, 0.0, 0.0),
        ),
        available_flexibility_mw=(0.0, 40.0, 0.0, 0.0),
    )

    correct = solve_temporal_economic_stochastic(
        _inputs(scenario, joint=True, fixed_flexibility_mw=40.0)
    )
    b6 = solve_temporal_economic_stochastic(
        _inputs(scenario, joint=False, fixed_flexibility_mw=40.0)
    )

    assert correct.feasible and b6.feasible
    assert correct.scenario_dispatch["stress"].access_shortfall_mw[1] == (
        pytest.approx(40.0)
    )
    assert b6.scenario_dispatch["stress"].access_shortfall_mw[1] == (
        pytest.approx(0.0)
    )
    assert b6.scenario_dispatch["stress"].physical_combined_call_mw[1] == (
        pytest.approx(80.0)
    )


def test_grid_need_above_available_flexibility_is_proven_infeasible():
    scenario = replace(
        _scenario((0.0, 40.0, 0.0, 0.0)),
        available_flexibility_mw=(0.0, 30.0, 0.0, 0.0),
    )

    result = solve_temporal_economic_stochastic(
        _inputs(scenario, joint=True, fixed_flexibility_mw=100.0)
    )

    assert not result.feasible
    assert result.proven_infeasible


def test_hard_grid_need_cannot_buy_through_maximum_event_duration():
    scenario = _scenario((40.0, 40.0, 40.0, 0.0, 0.0))
    result = solve_temporal_economic_stochastic(
        _inputs(
            scenario,
            envelope=_envelope(5, maximum_event_duration_hours=2.0),
        )
    )

    assert not result.feasible
    assert result.proven_infeasible


def test_hard_grid_need_cannot_buy_through_event_count_or_energy_limit():
    two_events = _scenario((40.0, 0.0, 40.0, 0.0, 0.0))
    event_limited = solve_temporal_economic_stochastic(
        _inputs(two_events, envelope=_envelope(5, maximum_events=1))
    )
    energy_limited = solve_temporal_economic_stochastic(
        _inputs(
            _scenario((40.0, 40.0, 0.0, 0.0)),
            envelope=_envelope(4, maximum_energy_mwh=79.0),
        )
    )

    assert not event_limited.feasible and event_limited.proven_infeasible
    assert not energy_limited.feasible and energy_limited.proven_infeasible


def test_terminal_recovery_debt_is_hard_not_a_cvar_penalty():
    scenario = _scenario(
        (0.0, 40.0, 0.0, 0.0),
        recovery_headroom=(0.0, 0.0, 0.0, 0.0),
    )
    result = solve_temporal_economic_stochastic(_inputs(scenario))

    assert not result.feasible
    assert result.proven_infeasible


def test_recovery_is_optimized_inside_recourse_and_debt_closes():
    scenario = _scenario(
        (0.0, 40.0, 0.0, 0.0),
        recovery_headroom=(0.0, 0.0, 20.0, 20.0),
    )
    result = solve_temporal_economic_stochastic(_inputs(scenario))

    assert result.feasible
    dispatch = result.scenario_dispatch["stress"]
    assert dispatch.physical_recovery_power_mw == pytest.approx(
        (0.0, 0.0, 20.0, 20.0)
    )
    assert dispatch.physical_recovery_debt_mwh == pytest.approx(
        (0.0, 40.0, 20.0, 0.0)
    )
    assert dispatch.modeled_event_count_by_period == {"q1": 1}
    assert dispatch.physical_event_count_by_period == {"q1": 1}
    assert dispatch.curtailment_energy_mwh_by_period == pytest.approx({"q1": 40.0})
    assert dispatch.physical_envelope_feasible
    assert dispatch.physical_envelope_violations == ()
    assert dispatch.maximum_temporal_residual <= 1.0e-6


def test_incomplete_terminal_period_does_not_falsely_force_debt_to_zero():
    scenario = replace(
        _scenario(
            (0.0, 40.0),
            recovery_headroom=(0.0, 0.0),
        ),
        completed_periods=frozenset(),
        require_terminal_event_inactive=False,
    )
    result = solve_temporal_economic_stochastic(_inputs(scenario))

    assert result.feasible
    dispatch = result.scenario_dispatch["stress"]
    assert dispatch.physical_terminal_recovery_debt_mwh == pytest.approx(40.0)


def test_internal_period_terminal_debt_cannot_be_omitted():
    scenario = replace(
        _scenario(
            (0.0, 40.0, 0.0, 0.0),
            recovery_headroom=(0.0, 0.0, 20.0, 20.0),
        ),
        periods=("q1", "q1", "q2", "q2"),
        completed_periods=frozenset({"q2"}),
    )
    envelope = replace(
        _envelope(4),
        maximum_events_by_period={"q1": 1, "q2": 1},
        maximum_curtailment_energy_mwh_by_period={"q1": 100.0, "q2": 100.0},
        terminal_debt_limit_mwh_by_period={"q1": 0.0, "q2": 0.0},
    )

    result = solve_temporal_economic_stochastic(
        _inputs(scenario, envelope=envelope)
    )

    assert not result.feasible
    assert result.proven_infeasible


def test_unlinked_horizon_requires_full_terminal_recovery_interval():
    scenario = _scenario(
        (0.0, 0.0, 40.0, 0.0),
        recovery_headroom=(0.0, 0.0, 0.0, 40.0),
    )
    envelope = replace(_envelope(4), minimum_recovery_hours=2.0)

    result = solve_temporal_economic_stochastic(
        _inputs(scenario, envelope=envelope)
    )

    assert not result.feasible
    assert result.proven_infeasible


def test_correct_model_physical_replay_failure_blocks_result(monkeypatch):
    real_evaluate = temporal_module.evaluate_chronological_flexibility

    def inject_failure(*args, **kwargs):
        result = real_evaluate(*args, **kwargs)
        return replace(result, feasible=False, violations=("injected",))

    monkeypatch.setattr(
        temporal_module, "evaluate_chronological_flexibility", inject_failure
    )
    result = solve_temporal_economic_stochastic(
        _inputs(_scenario((0.0, 40.0, 0.0, 0.0)))
    )

    assert not result.feasible
    assert not result.proven_infeasible
    assert result.termination_condition == "physical_replay_audit_failed"


def test_mip_does_not_accept_local_optimum_as_global_solution():
    assert TerminationCondition.locallyOptimal not in temporal_module._OPTIMAL


def test_unit_provisioning_cost_does_not_alias_pyomo_variable():
    inputs = replace(
        _inputs(_scenario((0.0, 40.0, 0.0, 0.0))),
        provisioning_cost_per_mw=1.0,
    )

    result = solve_temporal_economic_stochastic(inputs)

    assert result.feasible
    assert result.expansion_cost == pytest.approx(
        result.provisioned_flexibility_mw
    )


def test_temporal_scenarios_require_the_same_period_sequence():
    first = _scenario((0.0, 0.0))
    second = replace(
        first,
        name="other",
        probability=0.5,
        periods=("q1", "q2"),
    )
    first = replace(first, probability=0.5)
    envelope = replace(
        _envelope(2),
        maximum_events_by_period={"q1": 2, "q2": 2},
        maximum_curtailment_energy_mwh_by_period={"q1": 200.0, "q2": 200.0},
        terminal_debt_limit_mwh_by_period={"q2": 0.0},
    )

    with pytest.raises(ValueError, match="same period sequence"):
        solve_temporal_economic_stochastic(
            replace(_inputs(first, envelope=envelope), scenarios=(first, second))
        )


def test_scenario_boundary_fields_are_required():
    with pytest.raises(TypeError):
        TemporalEconomicScenario(
            name="missing_boundary",
            probability=1.0,
            periods=("q1",),
            grid_need_mw=(0.0,),
            green_call_mw=(0.0,),
            connected_demand_mw=(1.0,),
            recovery_headroom_mw=(0.0,),
            completed_periods=frozenset({"q1"}),
        )


def test_temporal_inputs_require_contiguous_period_blocks():
    scenario = replace(
        _scenario((0.0, 0.0, 0.0)),
        periods=("q1", "q2", "q1"),
    )
    envelope = replace(
        _envelope(3),
        maximum_events_by_period={"q1": 2, "q2": 2},
        maximum_curtailment_energy_mwh_by_period={"q1": 200.0, "q2": 200.0},
        terminal_debt_limit_mwh_by_period={"q2": 0.0},
    )

    with pytest.raises(ValueError, match="contiguous block"):
        solve_temporal_economic_stochastic(_inputs(scenario, envelope=envelope))
