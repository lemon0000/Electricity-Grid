from dataclasses import replace
from datetime import timezone
from pathlib import Path

import pytest
from highspy import Highs
from pyomo.environ import ConcreteModel, Objective, Var, value
from pyomo.opt import SolverFactory, TerminationCondition

from src.evaluation import ChronologicalFlexibilityEnvelope, GridIncident
from src.grid.chronological_dispatch import (
    ChronologicalDispatchRequest,
    validate_chronological_dispatch,
)
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data
from src.grid.rts_gmlc_scuc import (
    _build_context,
    _build_model,
    _clean_to_bounds,
    _constraint_violation,
    _security_states,
    build_rts_gmlc_pre_registered_contingencies,
    select_rts_gmlc_critical_contingencies,
    solve_rts_gmlc_scuc,
)

UPSTREAM_ROOT = Path("data/raw/rts_gmlc/v0.2.3/upstream")


def test_solver_constraint_audit_includes_variable_bounds():
    model = ConcreteModel()
    model.x = Var(bounds=(0.0, 1.0))
    model.x.set_value(1.25, skip_validation=True)

    assert _constraint_violation(model) == pytest.approx(0.25)


def test_solver_bound_cleanup_only_clips_within_tolerance():
    assert _clean_to_bounds(1.0 + 1.0e-7, 0.0, 1.0, "candidate") == 1.0
    assert _clean_to_bounds(-1.0e-7, 0.0, 1.0, "candidate") == 0.0

    with pytest.raises(RuntimeError, match="above its variable upper bound"):
        _clean_to_bounds(1.0 + 2.0e-6, 0.0, 1.0, "candidate")


def test_pointwise_unit_order_deletes_valid_crossing_commitment_trajectories():
    first = (1, 1, 0)
    second = (0, 1, 1)

    def starts(schedule):
        return tuple(
            max(value_ - (schedule[index - 1] if index else 0), 0)
            for index, value_ in enumerate(schedule)
        )

    for schedule in (first, second):
        for time, startup in enumerate(starts(schedule)):
            if startup:
                assert schedule[time : time + 2] == (1, 1)

    assert not all(earlier >= later for earlier, later in zip(first, second))
    assert not all(earlier >= later for earlier, later in zip(second, first))


@pytest.fixture(scope="module")
def chronological_data():
    if not UPSTREAM_ROOT.exists():
        pytest.skip("Run scripts/fetch_rts_gmlc.ps1 to enable RTS-GMLC SCUC tests")
    return load_rts_gmlc_chronological_data(UPSTREAM_ROOT)


def _zero_flexibility_envelope() -> ChronologicalFlexibilityEnvelope:
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=1.0,
        minimum_recovery_hours=1.0,
        maximum_events_by_period={"benchmark": 0},
        maximum_curtailment_energy_mwh_by_period={"benchmark": 0.0},
        maximum_recovery_debt_mwh=0.0,
        maximum_recovery_power_mw=0.0,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=1.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={"benchmark": 0.0},
        parameter_status="zero_flexibility_rts_gmlc_benchmark",
    )


def _request(data, hours=1):
    points = data.hourly_points[:hours]
    generator_uids = tuple(generator.uid for generator in data.generators)
    availability = {
        generator.uid: bool(generator.enabled) for generator in data.generators
    }
    initial_commitment = dict(availability)
    initial_generation = {uid: 0.0 for uid in generator_uids}
    initial_duration = {uid: 0.0 for uid in generator_uids}
    return ChronologicalDispatchRequest(
        timestamps=tuple(
            point.timestamp.replace(tzinfo=timezone.utc) for point in points
        ),
        periods=tuple("benchmark" for _ in points),
        time_step_hours=1.0,
        system_demand_by_bus_mw=tuple(dict(point.demand_by_bus_mw) for point in points),
        generator_availability=tuple(dict(availability) for _ in points),
        dc_bus=data.reference_bus,
        dc_requested_mw=tuple(0.0 for _ in points),
        dc_flexible_demand_mw=tuple(0.0 for _ in points),
        dc_recoverable_flexible_mw=tuple(0.0 for _ in points),
        dc_physical_maximum_mw=tuple(0.0 for _ in points),
        dc_connected_capacity_mw=tuple(0.0 for _ in points),
        dc_call_limit_mw=tuple(0.0 for _ in points),
        recovery_headroom_mw=tuple(0.0 for _ in points),
        flexibility_envelope=_zero_flexibility_envelope(),
        flexibility_boundary_state_status="clean_boundary_with_zero_carry_in",
        completed_periods=frozenset({"benchmark"}),
        initial_has_prior_event=False,
        initial_recovery_debt_mwh=0.0,
        initial_grid_call_mw=0.0,
        initial_active_event_duration_hours=0.0,
        initial_interevent_rest_hours=None,
        initial_event_count_by_period={},
        initial_curtailment_energy_mwh_by_period={},
        require_terminal_event_inactive=True,
        incidents=(),
        initial_commitment=initial_commitment,
        initial_generation_mw=initial_generation,
        initial_time_in_state_hours=initial_duration,
    )


def test_selection_uses_maximum_loading_per_area_and_excludes_islanding(
    chronological_data,
):
    data = chronological_data
    flows = {branch.uid: 0.0 for branch in data.branches}
    desired = {"A1", "B1", "C1", "AB1"}
    for branch in data.branches:
        if branch.uid in desired:
            flows[branch.uid] = 0.95 * branch.continuous_rating_mw
        elif branch.uid in {"B11", "C11"}:
            flows[branch.uid] = 10.0 * branch.continuous_rating_mw

    selection = select_rts_gmlc_critical_contingencies(data, (flows,))

    assert set(selection.branch_uids) == desired
    assert selection.excluded_islanding_branch_uids == ("B11", "C11")
    assert selection.generator_uids == (
        "121_NUCLEAR_1",
        "213_CC_3",
        "313_CC_1",
    )
    assert len(selection.states) == 12
    assert selection.states[0].state_id == "normal"


def test_pre_registered_selection_freezes_explicit_nonislanding_states(
    chronological_data,
):
    selection = build_rts_gmlc_pre_registered_contingencies(
        chronological_data,
        branch_uids=("A1", "B1", "C1", "AB1"),
        generator_uids=("121_NUCLEAR_1", "213_CC_3", "313_CC_1"),
    )

    assert selection.branch_uids == ("A1", "B1", "C1", "AB1")
    assert selection.excluded_islanding_branch_uids == ("B11", "C11")
    assert tuple(state.state_id for state in selection.states) == (
        "normal",
        "branch_A1_immediate",
        "branch_A1_sustained",
        "branch_B1_immediate",
        "branch_B1_sustained",
        "branch_C1_immediate",
        "branch_C1_sustained",
        "branch_AB1_immediate",
        "branch_AB1_sustained",
        "generator_121_NUCLEAR_1_sustained",
        "generator_213_CC_3_sustained",
        "generator_313_CC_1_sustained",
    )


def test_pre_registered_selection_rejects_islanding_and_noncommittable_elements(
    chronological_data,
):
    with pytest.raises(ValueError, match="cannot island"):
        build_rts_gmlc_pre_registered_contingencies(
            chronological_data,
            branch_uids=("B11",),
            generator_uids=("121_NUCLEAR_1",),
        )

    with pytest.raises(ValueError, match="must be committable"):
        build_rts_gmlc_pre_registered_contingencies(
            chronological_data,
            branch_uids=("A1",),
            generator_uids=("114_SYNC_COND_1",),
        )


def test_multiperiod_model_has_no_pointwise_commitment_symmetry(chronological_data):
    request = _request(chronological_data, hours=3)
    context = _build_context(
        chronological_data,
        request,
        chronological_data.hourly_points[:3],
        (_security_states((), ())[0],),
    )
    model = _build_model(context, fixed_initial=None)

    assert model.component("SYMMETRY_PAIR") is None
    assert model.component("commitment_symmetry") is None


def test_reserve_commitment_envelope_cuts_fractional_commitment(
    chronological_data,
):
    request = _request(chronological_data)
    context = _build_context(
        chronological_data,
        request,
        chronological_data.hourly_points[:1],
        (_security_states((), ())[0],),
    )
    model = _build_model(context, fixed_initial=None)
    time, uid = next(iter(model.RESERVE_COMMITMENT_PAIR))
    cap = (
        10.0
        * chronological_data.generators[
            next(
                index
                for index, generator in enumerate(chronological_data.generators)
                if generator.uid == uid
            )
        ].ramp_mw_per_minute
    )

    model.reserve_up[time, uid].set_value(cap)
    model.commitment[time, uid].set_value(1.0)
    constraint = model.reserve_commitment_envelope[time, uid]
    assert value(constraint.body) == pytest.approx(0.0)

    model.commitment[time, uid].set_value(0.5)
    assert value(constraint.body) == pytest.approx(0.5 * cap)


def test_two_hour_native_selected_n1_scuc_and_fixed_commitment_sced(
    chronological_data,
):
    Highs.resetGlobalScheduler(True)
    probe = ConcreteModel()
    probe.x = Var(bounds=(0.0, 1.0))
    probe.objective = Objective(expr=probe.x)
    probe_result = SolverFactory("highs").solve(probe, options={"threads": 1})
    assert probe_result.solver.termination_condition == TerminationCondition.optimal

    request = _request(chronological_data, hours=2)

    result = solve_rts_gmlc_scuc(
        chronological_data,
        request,
        solver_threads=4,
        mip_relative_gap=1.0e-6,
    )

    validate_chronological_dispatch(result.dispatch_request, result.dispatch_result)
    assert result.prescreen_audit.accepted
    assert result.scuc_audit.accepted
    assert result.sced_audit.accepted
    assert result.scuc_audit.solver_threads == 4
    assert result.scuc_audit.configured_mip_relative_gap == pytest.approx(1.0e-6)
    constraint_generation = result.constraint_generation_audit
    expected_state_ids = tuple(
        state.state_id for state in result.critical_selection.states
    )
    assert constraint_generation.converged
    assert constraint_generation.maximum_refinement_iterations == 11
    assert constraint_generation.pre_registered_state_ids == expected_state_ids
    assert constraint_generation.verified_state_ids == expected_state_ids
    assert constraint_generation.final_active_state_ids[0] == "normal"
    assert set(constraint_generation.final_active_state_ids) <= set(expected_state_ids)
    assert 1 <= len(constraint_generation.iterations) <= 11
    for iteration in constraint_generation.iterations:
        inactive = set(expected_state_ids) - set(iteration.active_state_ids)
        assert iteration.active_state_ids[0] == "normal"
        assert set(iteration.state_screen_terminations) == inactive
        assert set(iteration.added_state_ids) <= inactive
        assert all(
            iteration.state_screen_terminations[state_id] == "infeasible"
            for state_id in iteration.added_state_ids
        )
        assert iteration.active_mip_audit.accepted
    assert constraint_generation.certified_absolute_gap_usd <= (
        result.scuc_audit.gap_tolerance_usd + 1.0e-6
    )
    assert set(result.security_generation_mw) == set(expected_state_ids) - {"normal"}
    assert set(result.security_branch_flows_mw) == set(expected_state_ids) - {"normal"}
    assert result.initial_state.source_scope == (
        "optimization_derived_free_boundary_not_observed_chronology"
    )
    assert len(result.initial_state.commitment) == 158
    assert result.dispatch_request.initial_commitment == result.initial_state.commitment
    assert (
        result.dispatch_request.initial_generation_mw
        == result.initial_state.generation_mw
    )
    assert result.dispatch_result.grid_call_mw == (0.0, 0.0)
    assert result.dispatch_result.recovery_power_mw == (0.0, 0.0)
    assert result.dispatch_result.security_state_count_by_step == (12, 12)
    assert all(result.dispatch_result.commitment_feasible_by_step)
    assert all(result.dispatch_result.ramp_feasible_by_step)
    assert all(result.dispatch_result.reserve_feasible_by_step)
    assert all(result.dispatch_result.normal_secure_by_step)
    assert all(result.dispatch_result.contingency_secure_by_step)
    assert result.residual_audit.maximum_balance_residual_mw <= 1.0e-6
    assert result.residual_audit.maximum_branch_rating_violation_mw <= 1.0e-6
    assert result.residual_audit.maximum_outage_flow_mw <= 1.0e-6
    assert result.residual_audit.maximum_minimum_time_violation <= 1.0e-6
    assert result.residual_audit.maximum_reserve_shortfall_mw <= 1.0e-6
    assert "constraint_generation_all_pre_registered_states_verified" in (
        result.dispatch_scope
    )
    assert "constraint_generation_all_pre_registered_states_verified" in (
        result.security_scope
    )
    assert "not_full_security_certification" in result.security_scope
    disabled = {
        generator.uid
        for generator in chronological_data.generators
        if generator.dispatch_mode == "disabled"
    }
    assert len(disabled) == 5
    assert all(
        result.dispatch_result.generation_mw[0][uid] == pytest.approx(0.0)
        for uid in disabled
    )
    assert all(len(row) == 1 for row in result.normal_dc_flows_mw)
    assert all(
        abs(flow) <= 100.0 + 1.0e-6
        for row in result.normal_dc_flows_mw
        for flow in row.values()
    )


def test_solver_rejects_nonzero_flexibility_and_incidents(chronological_data):
    request = _request(chronological_data)
    nonzero_flexibility = replace(
        request,
        dc_requested_mw=(1.0,),
        dc_flexible_demand_mw=(1.0,),
        dc_recoverable_flexible_mw=(1.0,),
        dc_physical_maximum_mw=(1.0,),
        dc_connected_capacity_mw=(1.0,),
        dc_call_limit_mw=(1.0,),
    )
    with pytest.raises(ValueError, match="zero flexibility"):
        solve_rts_gmlc_scuc(chronological_data, nonzero_flexibility)

    recovery_enabled = replace(
        request,
        flexibility_envelope=replace(
            request.flexibility_envelope,
            maximum_recovery_power_mw=1.0,
        ),
    )
    with pytest.raises(ValueError, match="zero recovery boundary"):
        solve_rts_gmlc_scuc(chronological_data, recovery_enabled)

    timestamp = request.timestamps[0]
    incident = GridIncident(
        event_id="unsupported-observed-incident",
        start_timestamp=timestamp,
        end_timestamp=timestamp.replace(hour=1),
        kind="branch",
        element_id="A1",
        frequency_semantics="observed_occurrence",
        frequency_value=1.0,
    )
    with pytest.raises(ValueError, match="does not accept incident"):
        solve_rts_gmlc_scuc(
            chronological_data,
            replace(request, incidents=(incident,)),
        )


def test_solver_rejects_demand_drift_and_unavailable_solver(chronological_data):
    request = _request(chronological_data)
    drifted_demand = dict(request.system_demand_by_bus_mw[0])
    drifted_demand[chronological_data.reference_bus] += 1.0
    with pytest.raises(ValueError, match="drifted"):
        solve_rts_gmlc_scuc(
            chronological_data,
            replace(request, system_demand_by_bus_mw=(drifted_demand,)),
        )

    with pytest.raises(RuntimeError, match="not available"):
        solve_rts_gmlc_scuc(
            chronological_data,
            request,
            solver_name="not_a_real_solver",
        )


def test_solver_rejects_negative_transition_costs(chronological_data):
    generators = list(chronological_data.generators)
    index = next(
        index
        for index, generator in enumerate(generators)
        if generator.dispatch_mode == "committable"
    )
    generators[index] = replace(generators[index], cold_start_cost_usd=-1.0)
    invalid_data = replace(chronological_data, generators=tuple(generators))

    with pytest.raises(ValueError, match="nonnegative startup/shutdown costs"):
        solve_rts_gmlc_scuc(invalid_data, _request(invalid_data))
