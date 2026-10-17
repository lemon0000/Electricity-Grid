from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from src.evaluation import ChronologicalFlexibilityEnvelope, GridIncident
from src.grid import (
    ChronologicalDispatchRequest,
    ChronologicalDispatchResult,
    validate_chronological_dispatch,
)


def _timestamps():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return tuple(start + timedelta(hours=index) for index in range(3))


def _request():
    timestamps = _timestamps()
    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=1.0,
        minimum_recovery_hours=1.0,
        maximum_events_by_period={"q1": 1},
        maximum_curtailment_energy_mwh_by_period={"q1": 2.0},
        maximum_recovery_debt_mwh=2.0,
        maximum_recovery_power_mw=2.0,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=10.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={"q1": 0.0},
        parameter_status="synthetic_dispatch_interface_test",
    )
    return ChronologicalDispatchRequest(
        timestamps=timestamps,
        periods=("q1", "q1", "q1"),
        time_step_hours=1.0,
        system_demand_by_bus_mw=({1: 90.0, 8: 0.0},) * 3,
        generator_availability=({"G1": True},) * 3,
        dc_bus=8,
        dc_requested_mw=(10.0, 10.0, 10.0),
        dc_flexible_demand_mw=(3.0, 3.0, 3.0),
        dc_recoverable_flexible_mw=(3.0, 3.0, 3.0),
        dc_physical_maximum_mw=(12.0, 12.0, 12.0),
        dc_connected_capacity_mw=(12.0, 12.0, 12.0),
        dc_call_limit_mw=(3.0, 3.0, 3.0),
        recovery_headroom_mw=(0.0, 0.0, 2.0),
        flexibility_envelope=envelope,
        flexibility_boundary_state_status="clean_boundary_with_zero_carry_in",
        completed_periods=frozenset({"q1"}),
        initial_has_prior_event=False,
        initial_recovery_debt_mwh=0.0,
        initial_grid_call_mw=0.0,
        initial_active_event_duration_hours=0.0,
        initial_interevent_rest_hours=None,
        initial_event_count_by_period={},
        initial_curtailment_energy_mwh_by_period={},
        require_terminal_event_inactive=True,
        incidents=(
            GridIncident(
                event_id="branch-A1-hour-2",
                start_timestamp=timestamps[1],
                end_timestamp=timestamps[2],
                kind="branch",
                element_id="A1",
                frequency_semantics="observed_occurrence",
                frequency_value=1.0,
            ),
        ),
        initial_commitment={"G1": True},
        initial_generation_mw={"G1": 100.0},
        initial_time_in_state_hours={"G1": 12.0},
    )


def _result():
    return ChronologicalDispatchResult(
        feasible=True,
        timestamps=_timestamps(),
        grid_call_mw=(0.0, 2.0, 0.0),
        recovery_power_mw=(0.0, 0.0, 2.0),
        dc_power_mw=(10.0, 8.0, 12.0),
        generation_mw=({"G1": 100.0}, {"G1": 98.0}, {"G1": 102.0}),
        commitment=({"G1": True},) * 3,
        load_shed_mw=(0.0, 0.0, 0.0),
        network_losses_mw=(0.0, 0.0, 0.0),
        commitment_feasible_by_step=(True, True, True),
        ramp_feasible_by_step=(True, True, True),
        reserve_feasible_by_step=(True, True, True),
        normal_secure_by_step=(True, True, True),
        contingency_secure_by_step=(True, True, True),
        security_state_count_by_step=(2, 2, 2),
        checked_security_state_ids_by_step=(
            ("normal", "branch-A1-hour-2"),
            ("normal", "branch-A1-hour-2"),
            ("normal", "branch-A1-hour-2"),
        ),
        termination_condition="optimal",
        dispatch_scope="fake_horizon_scuc_sced_interface_test",
        security_scope="fake_normal_and_n_minus_one_interface_test",
    )


class _FakeHorizonSolver:
    def solve(self, request):
        assert request.timestamps == _timestamps()
        assert request.incidents[0].element_id == "A1"
        return _result()


def test_horizon_solver_boundary_preserves_clock_service_and_security_scope():
    request = _request()
    result = _FakeHorizonSolver().solve(request)

    validate_chronological_dispatch(request, result)

    assert not hasattr(result, "security_certified")
    assert "fake" in result.dispatch_scope


@pytest.mark.parametrize(
    ("result", "message"),
    (
        (replace(_result(), timestamps=_timestamps()[:-1]), "timestamps"),
        (replace(_result(), grid_call_mw=(0.0, 4.0, 0.0)), "call exceeds"),
        (
            replace(_result(), recovery_power_mw=(0.0, 0.0, 3.0)),
            "Recovery exceeds",
        ),
        (replace(_result(), dc_power_mw=(10.0, 9.0, 12.0)), "service balance"),
        (replace(_result(), load_shed_mw=(0.0, 1.0, 0.0)), "load shedding"),
        (
            replace(_result(), generation_mw=({"G1": 100.0}, {}, {"G1": 102.0})),
            "Generator result keys",
        ),
        (
            replace(
                _result(),
                normal_secure_by_step=(True, False, True),
            ),
            "normal security failure",
        ),
    ),
)
def test_dispatch_audit_rejects_inconsistent_results(result, message):
    with pytest.raises(ValueError, match=message):
        validate_chronological_dispatch(_request(), result)


def test_dispatch_audit_rejects_power_imbalance_and_unavailable_generation():
    unbalanced = replace(
        _result(),
        generation_mw=({"G1": 100.0}, {"G1": 97.0}, {"G1": 102.0}),
    )
    with pytest.raises(ValueError, match="power balance"):
        validate_chronological_dispatch(_request(), unbalanced)

    request = replace(
        _request(),
        generator_availability=({"G1": True}, {"G1": False}, {"G1": True}),
    )
    with pytest.raises(ValueError, match="Unavailable generator"):
        validate_chronological_dispatch(request, _result())


def test_dispatch_request_rejects_overlapping_n_minus_one_events():
    request = _request()
    overlapping = replace(
        request.incidents[0],
        event_id="generator-G1-hour-2",
        kind="generator",
        element_id="G1",
    )
    request = replace(request, incidents=request.incidents + (overlapping,))

    with pytest.raises(ValueError, match="overlapping N-1"):
        validate_chronological_dispatch(request, _result())


def test_active_branch_incident_must_appear_in_checked_security_states():
    result = replace(
        _result(),
        checked_security_state_ids_by_step=(
            ("normal", "other-branch"),
            ("normal", "other-branch"),
            ("normal", "other-branch"),
        ),
    )

    with pytest.raises(ValueError, match="missing from security checks"):
        validate_chronological_dispatch(_request(), result)
