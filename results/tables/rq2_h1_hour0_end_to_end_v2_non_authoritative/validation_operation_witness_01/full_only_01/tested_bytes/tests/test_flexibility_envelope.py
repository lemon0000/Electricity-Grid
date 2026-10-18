from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from experiments.run_rts24_fx_chronology import run
from src.evaluation import (
    ChronologicalFlexibilityEnvelope,
    ChronologicalFlexibilityTrace,
    evaluate_chronological_flexibility,
)


def _timestamps(hours):
    start = datetime(2020, 1, 1)
    return tuple(start + timedelta(hours=index) for index in range(hours))


def _trace(calls, *, periods=None, limits=None, headroom=None, recovery=None):
    calls = tuple(float(value) for value in calls)
    hours = len(calls)
    return ChronologicalFlexibilityTrace(
        name="synthetic_continuous_stress_trace",
        timestamps=_timestamps(hours),
        periods=(tuple(periods) if periods is not None else ("q1",) * hours),
        grid_call_mw=calls,
        call_limit_mw=(
            tuple(float(value) for value in limits)
            if limits is not None
            else (40.0,) * hours
        ),
        recovery_headroom_mw=(
            tuple(float(value) for value in headroom)
            if headroom is not None
            else (20.0,) * hours
        ),
        boundary_state_status="clean_boundary_with_zero_carry_in",
        completed_periods=frozenset(periods or ("q1",)),
        initial_has_prior_event=False,
        prescribed_recovery_power_mw=(
            tuple(float(value) for value in recovery)
            if recovery is not None
            else None
        ),
    )


def _envelope(*, periods=("q1",)):
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=2.0,
        minimum_recovery_hours=2.0,
        maximum_events_by_period={period: 2 for period in periods},
        maximum_curtailment_energy_mwh_by_period={
            period: 160.0 for period in periods
        },
        maximum_recovery_debt_mwh=80.0,
        maximum_recovery_power_mw=20.0,
        minimum_event_power_mw=10.0,
        response_time_hours=0.25,
        curtailment_ramp_mw_per_hour=160.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={periods[-1]: 0.0},
        parameter_status="synthetic_envelope_sensitivity_not_contract_evidence",
    )


def test_continuous_trace_passes_all_temporal_and_recovery_limits():
    result = evaluate_chronological_flexibility(
        _trace((0, 40, 40, 0, 0, 0, 0, 40, 40, 0, 0, 0, 0)),
        _envelope(),
    )

    assert result.feasible
    assert result.violations == ()
    assert result.feasible_by_period == {"q1": True}
    assert result.event_count_by_period == {"q1": 2}
    assert result.curtailment_energy_mwh_by_period == pytest.approx({"q1": 160.0})
    assert result.maximum_event_duration_hours == pytest.approx(2.0)
    assert result.minimum_interevent_recovery_hours == pytest.approx(4.0)
    assert result.peak_recovery_debt_mwh == pytest.approx(80.0)
    assert result.terminal_recovery_debt_mwh == pytest.approx(0.0)
    assert max(result.recovery_power_mw) == pytest.approx(20.0)


def test_event_and_debt_are_linked_across_period_boundary():
    trace = _trace(
        (0, 20, 20, 0, 0, 0),
        periods=("q1", "q1", "q2", "q2", "q2", "q2"),
        headroom=(0, 0, 0, 20, 20, 20),
    )
    envelope = replace(
        _envelope(periods=("q1", "q2")),
        terminal_debt_limit_mwh_by_period={"q2": 0.0},
    )

    result = evaluate_chronological_flexibility(trace, envelope)

    assert result.feasible
    assert result.feasible_by_period == {"q1": True, "q2": True}
    assert result.event_count_by_period == {"q1": 1, "q2": 0}
    assert result.curtailment_energy_mwh_by_period == pytest.approx(
        {"q1": 20.0, "q2": 20.0}
    )
    assert result.recovery_debt_mwh[1] == pytest.approx(20.0)
    assert result.recovery_debt_mwh[2] == pytest.approx(40.0)
    assert result.terminal_recovery_debt_mwh == pytest.approx(0.0)


def test_mw_only_feasibility_does_not_hide_duration_and_energy_failures():
    trace = _trace((0, 40, 40, 40, 0, 0, 0, 0))
    result = evaluate_chronological_flexibility(trace, _envelope())

    assert all(call <= limit for call, limit in zip(trace.grid_call_mw, trace.call_limit_mw))
    assert not result.feasible
    assert "maximum_event_duration_exceeded_at_step_3" in result.violations


def test_full_contract_without_recovery_headroom_fails_terminal_debt():
    trace = _trace((0, 40, 0, 0), headroom=(0, 0, 0, 0))
    result = evaluate_chronological_flexibility(trace, _envelope())

    assert not result.feasible
    assert result.feasible_by_period == {"q1": False}
    assert result.terminal_recovery_debt_mwh == pytest.approx(40.0)
    assert result.terminal_recovery_debt_mwh_by_period == pytest.approx(
        {"q1": 40.0}
    )
    assert "terminal_debt_exceeded_for_period_q1" in result.violations


def test_prescribed_dispatch_recovery_is_audited_instead_of_rescheduled():
    trace = _trace(
        (0, 20, 0, 0),
        recovery=(0, 0, 10, 10),
    )
    result = evaluate_chronological_flexibility(trace, _envelope())

    assert result.feasible
    assert result.recovery_power_mw == pytest.approx((0, 0, 10, 10))
    assert result.recovery_debt_mwh == pytest.approx((0, 20, 10, 0))


def test_invalid_prescribed_recovery_cannot_hide_shared_budget_failure():
    trace = _trace(
        (0, 20, 0, 0),
        headroom=(0, 20, 5, 20),
        recovery=(0, 10, 10, 0),
    )
    result = evaluate_chronological_flexibility(trace, _envelope())

    assert not result.feasible
    assert "recovery_during_active_call_at_step_1" in result.violations
    assert "recovery_headroom_exceeded_at_step_2" in result.violations
    assert result.recovery_power_mw == pytest.approx((0, 10, 10, 0))
    assert result.effective_recovery_power_mw == pytest.approx((0, 0, 0, 0))


def test_linked_windows_match_one_monolithic_business_state_path():
    envelope = _envelope()
    full_trace = _trace(
        (20, 20, 0, 0, 20, 0),
        headroom=(0, 0, 20, 20, 0, 20),
    )
    full = evaluate_chronological_flexibility(full_trace, envelope)

    first_trace = replace(
        _trace((20,), headroom=(0,)),
        completed_periods=frozenset(),
        require_terminal_event_inactive=False,
    )
    first = evaluate_chronological_flexibility(first_trace, envelope)
    second_trace = replace(
        _trace(
            (20, 0, 0, 20, 0),
            headroom=(0, 20, 20, 0, 20),
        ),
        timestamps=_timestamps(6)[1:],
        boundary_state_status="linked_from_previous_window",
        initial_recovery_debt_mwh=first.terminal_recovery_debt_mwh,
        initial_grid_call_mw=first.terminal_grid_call_mw,
        initial_active_event_duration_hours=(
            first.terminal_active_event_duration_hours
        ),
        initial_interevent_rest_hours=first.terminal_interevent_rest_hours,
        initial_has_prior_event=first.terminal_has_prior_event,
        initial_event_count_by_period=first.event_count_by_period,
        initial_curtailment_energy_mwh_by_period=(
            first.curtailment_energy_mwh_by_period
        ),
    )
    second = evaluate_chronological_flexibility(second_trace, envelope)

    assert full.feasible and first.feasible and second.feasible
    assert second.terminal_recovery_debt_mwh == pytest.approx(
        full.terminal_recovery_debt_mwh
    )
    assert second.event_count_by_period == full.event_count_by_period
    assert second.curtailment_energy_mwh_by_period == pytest.approx(
        full.curtailment_energy_mwh_by_period
    )
    assert max(
        first.maximum_event_duration_hours,
        second.maximum_event_duration_hours,
    ) == pytest.approx(full.maximum_event_duration_hours)
    assert second.minimum_interevent_recovery_hours == pytest.approx(
        full.minimum_interevent_recovery_hours
    )


def test_completed_periods_cannot_suppress_an_internal_period_boundary():
    trace = replace(
        _trace(
            (20, 0, 0, 0),
            periods=("q1", "q1", "q2", "q2"),
            headroom=(0, 0, 20, 0),
        ),
        completed_periods=frozenset({"q2"}),
    )
    envelope = replace(
        _envelope(periods=("q1", "q2")),
        terminal_debt_limit_mwh_by_period={"q1": 0.0, "q2": 0.0},
    )

    result = evaluate_chronological_flexibility(trace, envelope)

    assert not result.feasible
    assert "terminal_debt_exceeded_for_period_q1" in result.violations


def test_linked_inactive_boundary_cannot_erase_rest_history():
    trace = replace(
        _trace((20, 0, 0)),
        boundary_state_status="linked_from_previous_window",
        initial_has_prior_event=True,
        initial_event_count_by_period={"q1": 1},
        initial_curtailment_energy_mwh_by_period={"q1": 20.0},
    )

    with pytest.raises(ValueError, match="explicit interevent rest"):
        evaluate_chronological_flexibility(trace, _envelope())


def test_zero_event_windows_round_trip_without_inventing_rest_history():
    first = evaluate_chronological_flexibility(_trace((0, 0)), _envelope())
    second_trace = replace(
        _trace((0, 0)),
        timestamps=_timestamps(4)[2:],
        boundary_state_status="linked_from_previous_window",
        initial_has_prior_event=first.terminal_has_prior_event,
        initial_recovery_debt_mwh=first.terminal_recovery_debt_mwh,
        initial_grid_call_mw=first.terminal_grid_call_mw,
        initial_active_event_duration_hours=(
            first.terminal_active_event_duration_hours
        ),
        initial_interevent_rest_hours=first.terminal_interevent_rest_hours,
        initial_event_count_by_period=first.event_count_by_period,
        initial_curtailment_energy_mwh_by_period=(
            first.curtailment_energy_mwh_by_period
        ),
    )

    second = evaluate_chronological_flexibility(second_trace, _envelope())

    assert second.feasible
    assert not second.terminal_has_prior_event
    assert second.terminal_interevent_rest_hours is None


@pytest.mark.parametrize(
    ("trace", "envelope", "violation"),
    (
        (
            _trace((0, 5, 0)),
            _envelope(),
            "minimum_event_power_violated_at_step_1",
        ),
        (
            _trace((0, 40, 0, 40, 0, 0, 0)),
            _envelope(),
            "minimum_interevent_recovery_violated_at_step_3",
        ),
        (
            _trace((0, 40, 0, 0)),
            replace(
                _envelope(),
                maximum_curtailment_energy_mwh_by_period={"q1": 39.0},
            ),
            "maximum_curtailment_energy_exceeded_for_period_q1",
        ),
        (
            _trace((0, 40, 0, 40, 0, 40, 0, 0, 0, 0)),
            _envelope(),
            "maximum_events_exceeded_for_period_q1",
        ),
        (
            _trace((0, 40, 40, 0, 0, 0)),
            replace(_envelope(), maximum_recovery_debt_mwh=79.0),
            "maximum_recovery_debt_exceeded_at_step_2",
        ),
        (
            _trace((0, 40, 0, 0)),
            replace(_envelope(), curtailment_ramp_mw_per_hour=100.0),
            "response_deadline_exceeded_at_step_1",
        ),
        (
            _trace((0, 41, 0, 0), limits=(40, 40, 40, 40)),
            _envelope(),
            "call_limit_exceeded_at_step_1",
        ),
    ),
)
def test_each_temporal_envelope_boundary_is_a_hard_failure(
    trace,
    envelope,
    violation,
):
    result = evaluate_chronological_flexibility(trace, envelope)
    assert not result.feasible
    assert violation in result.violations


def test_trace_must_be_continuous_and_period_limits_must_be_complete():
    trace = _trace((0, 0, 0))
    discontinuous = replace(
        trace,
        timestamps=(trace.timestamps[0], trace.timestamps[2], trace.timestamps[2]),
    )
    with pytest.raises(ValueError, match="timestamps must be continuous"):
        evaluate_chronological_flexibility(discontinuous, _envelope())

    with pytest.raises(ValueError, match="keys must match trace periods"):
        evaluate_chronological_flexibility(
            replace(trace, periods=("q1", "q2", "q2")),
            _envelope(),
        )


@pytest.mark.skipif(
    not Path("data/raw/rts_gmlc/v0.2.3/upstream").exists(),
    reason="Run scripts/fetch_rts_gmlc.ps1 to enable chronology integration",
)
def test_m3_chronology_withdraws_x_when_flat_contract_has_no_recovery_headroom(
    tmp_path,
):
    config = yaml.safe_load(
        Path("configs/rts24_deterministic_fx.yaml").read_text(encoding="utf-8")
    )
    sensitivity = config["chronological_sensitivity"]
    sensitivity["hourly_output_path"] = str(tmp_path / "hourly.csv")
    sensitivity["summary_output_path"] = str(tmp_path / "summary.json")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    summary = run(config_path)

    assert summary["timeline_hours"] == 8784
    assert summary["timeline_hours_by_quarter"] == {
        "q1": 2184,
        "q2": 2184,
        "q3": 2208,
        "q4": 2208,
    }
    assert summary["full_trace_pass_by_quarter"] == {
        "q1": True,
        "q2": True,
        "q3": False,
        "q4": False,
    }
    assert summary["temporally_qualified_capacity_mw"] == pytest.approx(
        {"q1": 50.0, "q2": 50.0, "q3": 175.0, "q4": 175.0}
    )
    assert summary["T20"]["quarter"] == "q1"
    assert summary["T50"]["quarter"] == "q3"
    assert not summary["T100"]["reached"]
    assert summary["T100"]["display_label"] == "q4+"
    assert "terminal_debt_exceeded_for_period_q3" in summary["layer_results"][
        "actual"
    ]["violations"]
    assert summary["layer_results"]["actual"]["feasible_by_quarter"]["q4"]
    assert not summary["layer_results"]["contract_counterfactual"][
        "feasible_by_quarter"
    ]["q4"]
    assert (tmp_path / "hourly.csv").read_text(encoding="utf-8").count("\n") == (
        2 * 8784 + 1
    )
