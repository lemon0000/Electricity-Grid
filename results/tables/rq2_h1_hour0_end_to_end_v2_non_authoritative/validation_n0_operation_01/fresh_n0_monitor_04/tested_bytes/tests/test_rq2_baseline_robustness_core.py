from __future__ import annotations

from dataclasses import fields, replace
from importlib.metadata import version
from types import SimpleNamespace

import pytest

from src.evaluation.flexibility_envelope import ChronologicalFlexibilityEnvelope
from src.evaluation.service_risk import ServiceLossCoefficients
from src.grid.rts_gmlc_grid_need_successor import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
)
from src.models import rq2_baseline_robustness as model_core
from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
)
from src.models.rq2_baseline_robustness import (
    CFE_ONLY_SHARED,
    FOUR_ARM_IDS,
    FOUR_ARM_SPECS,
    JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    JOINT_CORRECT_SHARED,
    NETWORK_ONLY_SHARED,
    plan_four_arm_minimum_flexibility_with_spec,
    project_training_inputs_for_arm,
)
from src.scenarios import rq2_baseline_robustness as scenario_core
from src.scenarios.rq2_baseline_robustness import (
    REGISTERED_SERVICE_RISK_SCHEMA,
    audit_four_arm_training_support,
    evaluate_training_trace_support,
    execute_four_arm_causal_policy,
    project_finite_scenario_for_arm,
    registered_service_risk_outcome,
)
from src.scenarios.rq2_public_replay import (
    CausalPolicyOutcome,
    ParameterCell,
    TemporalBlock,
    execute_causal_grid_first_policy,
)
from src.solvers.rq2_solver_adapter import Rq2SolverSpec

STATUS = "nonformal_four_arm_synthetic_test"


def _envelope() -> ChronologicalFlexibilityEnvelope:
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=1.0,
        minimum_recovery_hours=0.0,
        maximum_events_by_period={"block": 1},
        maximum_curtailment_energy_mwh_by_period={"block": 2.0},
        maximum_recovery_debt_mwh=2.0,
        maximum_recovery_power_mw=1.0,
        minimum_event_power_mw=1.0e-8,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=1.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={"block": 0.0},
        parameter_status=STATUS,
    )


def _scenario(
    *,
    grid: tuple[float, ...] = (0.0, 0.3, 0.0, 0.0),
    green: tuple[float, ...] = (0.0, 0.2, 0.0, 0.0),
    completed: frozenset[str] = frozenset({"block"}),
    require_terminal_inactive: bool = True,
) -> TemporalEconomicScenario:
    size = len(grid)
    return TemporalEconomicScenario(
        name="synthetic",
        probability=1.0,
        periods=("block",) * size,
        grid_need_mw=grid,
        green_call_mw=green,
        connected_demand_mw=(1.0,) * size,
        recovery_headroom_mw=(0.0, 0.0, 1.0, 1.0)[:size],
        completed_periods=completed,
        require_terminal_event_inactive=require_terminal_inactive,
        boundary_state_status="clean_boundary_with_zero_carry_in",
        available_flexibility_mw=(0.0, 1.0, 0.0, 0.0)[:size],
    )


def _inputs() -> TemporalEconomicInputs:
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
        scenarios=(_scenario(),),
        envelope=_envelope(),
        coefficients=coefficients,
        provisioning_cost_per_mw=0.0,
        max_flexibility_budget_mw=1.0,
        lambda_risk=0.0,
        beta=0.5,
        enforce_joint_budget=True,
        parameter_status=STATUS,
    )


def _one_hour_coincident_inputs() -> TemporalEconomicInputs:
    scenario = replace(
        _scenario(
            grid=(0.3,),
            green=(0.2,),
            completed=frozenset(),
            require_terminal_inactive=False,
        ),
        available_flexibility_mw=(1.0,),
        recovery_headroom_mw=(0.0,),
    )
    return replace(_inputs(), scenarios=(scenario,))


def _solver_spec() -> Rq2SolverSpec:
    return Rq2SolverSpec(
        name="highs",
        expected_package_version=version("highspy"),
        threads=1,
        mip_relative_gap=0.0,
        feasibility_tolerance=1.0e-7,
        optimality_tolerance=1.0e-7,
        integer_feasibility_tolerance=1.0e-7,
        random_seed=0,
        time_limit_seconds=None,
        tee=False,
    )


def _capacities(value: float = 0.5) -> dict[str, float]:
    return {arm_id: value for arm_id in FOUR_ARM_IDS}


def _cell() -> ParameterCell:
    return ParameterCell(
        cell_id="base",
        varied_dimension="base",
        flexible_fraction=1.0,
        recovery_efficiency=1.0,
        normalized_recovery_headroom=1.0,
        maximum_event_duration_hours=1.0,
        maximum_event_count=1,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
    )


def _fixed_policy() -> dict[str, object]:
    return {
        "minimum_recovery_hours": 0.0,
        "minimum_event_power": 1.0e-8,
        "response_time_hours": 1.0,
        "curtailment_ramp_per_hour": 1.0,
    }


def _block(
    block_id: str,
    *,
    grid: tuple[float, ...] = (),
    cfe: tuple[float, ...] = (),
    workload: tuple[float, ...] = (),
) -> TemporalBlock:
    return TemporalBlock(
        block_id=block_id,
        split="training",
        probability=1.0,
        first_source_hour=0,
        grid_need=grid,
        cfe_call=cfe,
        workload=workload,
    )


def _outcome(scenario: TemporalEconomicScenario, capacity: float):
    return CausalPolicyOutcome(
        name=scenario.name,
        committed_flexibility=capacity,
        resolved=True,
        hard_grid_failure=False,
        physical_policy_failure=False,
        service_shortfall_failure=False,
        access_shortfall=0.0,
        peak_recovery_debt=3.0,
        terminal_recovery_debt=2.0,
        combined_call=tuple(
            grid + green
            for grid, green in zip(
                scenario.grid_need_mw,
                scenario.green_call_mw,
                strict=True,
            )
        ),
        green_served=scenario.green_call_mw,
        physical_violations=(),
    )


def test_exact_arm_inventory_and_projection_preserve_noncall_semantics():
    assert FOUR_ARM_IDS == (
        NETWORK_ONLY_SHARED,
        CFE_ONLY_SHARED,
        JOINT_CORRECT_SHARED,
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    )
    assert tuple(spec.execution_envelope for spec in FOUR_ARM_SPECS) == (
        "shared",
    ) * 4
    source = _inputs()
    source_scenario = source.scenarios[0]
    scenario_exclusions = {"grid_need_mw", "green_call_mw"}
    input_exclusions = {"scenarios", "enforce_joint_budget"}

    for spec in FOUR_ARM_SPECS:
        projection = project_training_inputs_for_arm(source, spec.arm_id)
        projected_scenario = projection.inputs.scenarios[0]
        assert all(
            getattr(projected_scenario, field.name)
            == getattr(source_scenario, field.name)
            for field in fields(source_scenario)
            if field.name not in scenario_exclusions
        )
        assert all(
            getattr(projection.inputs, field.name) == getattr(source, field.name)
            for field in fields(source)
            if field.name not in input_exclusions
        )
        assert projection.inputs.enforce_joint_budget is spec.enforce_joint_budget
        assert projection.audit.non_call_scenario_fields_preserved
        assert projection.audit.non_scenario_input_fields_preserved
        assert projection.audit.idempotent
        repeated = project_training_inputs_for_arm(
            projection.inputs, spec.arm_id
        )
        assert repeated.inputs == projection.inputs

    assert source == _inputs()
    assert project_training_inputs_for_arm(
        source, NETWORK_ONLY_SHARED
    ).inputs.scenarios[0].green_call_mw == (0.0,) * 4
    assert project_training_inputs_for_arm(
        source, CFE_ONLY_SHARED
    ).inputs.scenarios[0].grid_need_mw == (0.0,) * 4
    for arm_id in (
        JOINT_CORRECT_SHARED,
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    ):
        projected = project_training_inputs_for_arm(source, arm_id).inputs
        assert projected.scenarios[0].grid_need_mw == source_scenario.grid_need_mw
        assert projected.scenarios[0].green_call_mw == source_scenario.green_call_mw


def test_four_arm_planner_calls_one_solver_per_registered_projection(monkeypatch):
    calls = []

    def fake_solve(inputs, *, enforce_joint_budget, solver_specification):
        calls.append((inputs, enforce_joint_budget, solver_specification))
        return SimpleNamespace(
            feasible=True,
            minimum_capacity=0.5,
            enforce_joint_budget=enforce_joint_budget,
        )

    monkeypatch.setattr(
        model_core,
        "solve_minimum_temporal_flexibility_with_spec",
        fake_solve,
    )
    spec = _solver_spec()
    planned = plan_four_arm_minimum_flexibility_with_spec(
        _inputs(), solver_specification=spec
    )

    assert tuple(arm.arm_id for arm in planned.arms) == FOUR_ARM_IDS
    assert len(calls) == 4
    assert all(call[2] is spec for call in calls)
    assert tuple(call[1] for call in calls) == (True, True, True, False)
    assert calls[0][0].scenarios[0].green_call_mw == (0.0,) * 4
    assert calls[1][0].scenarios[0].grid_need_mw == (0.0,) * 4
    assert calls[2][0].scenarios[0] == _inputs().scenarios[0]
    assert calls[3][0].scenarios[0] == _inputs().scenarios[0]


def test_nonformal_one_hour_coincident_highs_identifies_four_capacities():
    planned = plan_four_arm_minimum_flexibility_with_spec(
        _one_hour_coincident_inputs(), solver_specification=_solver_spec()
    )
    expected = {
        NETWORK_ONLY_SHARED: 0.3,
        CFE_ONLY_SHARED: 0.2,
        JOINT_CORRECT_SHARED: 0.5,
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION: 0.3,
    }

    for arm_id, expected_capacity in expected.items():
        arm = planned.by_arm[arm_id]
        assert arm.result.feasible
        assert not arm.result.proven_infeasible
        assert arm.result.minimum_capacity == pytest.approx(expected_capacity)
        assert arm.result.termination_condition == "optimal"
        assert arm.result.solver_status == "ok"
        assert arm.result.maximum_residual <= 1.0e-7
        assert arm.result.absolute_gap == pytest.approx(0.0)
        assert arm.result.solver_name == "highs"
        assert arm.input_projection_audit.idempotent


def test_offset_calls_have_zero_instantaneous_mw_only_gap():
    scenario = _scenario(
        grid=(0.4, 0.0, 0.0, 0.0),
        green=(0.0, 0.3, 0.0, 0.0),
    )
    shared = max(
        grid + green
        for grid, green in zip(
            scenario.grid_need_mw,
            scenario.green_call_mw,
            strict=True,
        )
    )
    separate = max(max(scenario.grid_need_mw), max(scenario.green_call_mw))

    assert shared == pytest.approx(0.4)
    assert shared - separate == pytest.approx(0.0)


def test_projection_preserves_right_censor_and_boundary_fields():
    scenario = _scenario(
        completed=frozenset(),
        require_terminal_inactive=False,
    )
    for arm_id in FOUR_ARM_IDS:
        projected = project_finite_scenario_for_arm(
            scenario,
            arm_id,
            grid_state=FINITE_GRID_NEED,
        ).scenario
        assert projected.completed_periods == frozenset()
        assert not projected.require_terminal_event_inactive
        assert projected.boundary_state_status == scenario.boundary_state_status
        assert projected.recovery_headroom_mw == scenario.recovery_headroom_mw


def test_holdout_replay_projects_calls_and_uses_one_shared_envelope(monkeypatch):
    calls = []

    def fake_execute(
        scenario,
        envelope,
        committed,
        *,
        service_shortfall_tolerance,
    ):
        calls.append(
            (
                scenario,
                envelope,
                committed,
                service_shortfall_tolerance,
            )
        )
        return _outcome(scenario, committed)

    monkeypatch.setattr(
        scenario_core,
        "execute_causal_grid_first_policy",
        fake_execute,
    )
    envelope = _envelope()
    expected_capacities = {
        NETWORK_ONLY_SHARED: 0.3,
        CFE_ONLY_SHARED: 0.2,
        JOINT_CORRECT_SHARED: 0.5,
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION: 0.3,
    }
    capacities = dict(reversed(tuple(expected_capacities.items())))
    result = execute_four_arm_causal_policy(
        _scenario(),
        envelope,
        capacities,
        grid_state=FINITE_GRID_NEED,
        service_shortfall_tolerance=1.0e-6,
    )

    assert tuple(arm.arm_id for arm in result.arms) == FOUR_ARM_IDS
    assert len(calls) == 4
    assert all(call[1] is envelope for call in calls)
    assert tuple(call[2] for call in calls) == tuple(
        expected_capacities[arm_id] for arm_id in FOUR_ARM_IDS
    )
    assert calls[0][0].green_call_mw == (0.0,) * 4
    assert calls[1][0].grid_need_mw == (0.0,) * 4
    assert calls[2][0] == _scenario()
    assert calls[3][0] == _scenario()
    assert all(
        arm.debt_metrics_role == "descriptive_only_not_category_deciding"
        for arm in result.arms
    )
    assert all(arm.outcome.peak_recovery_debt == 3.0 for arm in result.arms)
    assert all(
        arm.registered_service_risk.schema == REGISTERED_SERVICE_RISK_SCHEMA
        and arm.registered_service_risk.resolved
        and arm.registered_service_risk.registered_failure is False
        and arm.registered_service_risk.raw_outcome is arm.outcome
        for arm in result.arms
    )
    assert not any(hasattr(arm, "classification") for arm in result.arms)


@pytest.mark.parametrize(
    "capacities",
    [
        {arm_id: 0.5 for arm_id in FOUR_ARM_IDS[:-1]},
        {**_capacities(), "unknown_arm": 0.5},
        {**_capacities(), JOINT_CORRECT_SHARED: float("nan")},
        {**_capacities(), JOINT_CORRECT_SHARED: float("inf")},
        {**_capacities(), JOINT_CORRECT_SHARED: None},
    ],
)
def test_holdout_capacity_inventory_and_values_fail_closed(capacities):
    with pytest.raises(ValueError, match="capacity"):
        execute_four_arm_causal_policy(
            _scenario(),
            _envelope(),
            capacities,
            grid_state=FINITE_GRID_NEED,
            service_shortfall_tolerance=1.0e-6,
        )


def test_arm_drift_and_nonfinite_grid_states_fail_before_replay(monkeypatch):
    replay_calls = 0

    def unexpected_replay(*_args, **_kwargs):
        nonlocal replay_calls
        replay_calls += 1
        raise AssertionError("non-finite state must not create an outcome")

    monkeypatch.setattr(
        scenario_core,
        "execute_causal_grid_first_policy",
        unexpected_replay,
    )
    with pytest.raises(ValueError, match="finite_grid_need"):
        execute_four_arm_causal_policy(
            _scenario(),
            _envelope(),
            _capacities(),
            grid_state=EXOGENOUS_GRID_INFEASIBILITY,
            service_shortfall_tolerance=1.0e-6,
        )
    with pytest.raises(ValueError, match="unknown RQ2"):
        project_finite_scenario_for_arm(
            _scenario(),
            "drifted_arm",
            grid_state=FINITE_GRID_NEED,
        )
    assert replay_calls == 0


def test_training_support_audits_all_arms_and_b6_separately():
    power = (
        _block("p0", grid=(0.0, 0.0), cfe=(0.0, 0.0)),
        _block("p1", grid=(0.1, 0.0), cfe=(0.1, 0.0)),
    )
    workload = (
        _block("w0", workload=(1.0, 0.0)),
        _block("w1", workload=(1.0, 0.0)),
    )
    capacities = {
        NETWORK_ONLY_SHARED: 0.1,
        CFE_ONLY_SHARED: 0.05,
        JOINT_CORRECT_SHARED: 0.1,
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION: 0.1,
    }
    audit = audit_four_arm_training_support(
        power,
        workload,
        _cell(),
        capacity_by_arm=capacities,
        fixed_policy=_fixed_policy(),
        grid_state_by_power_block={
            "p0": FINITE_GRID_NEED,
            "p1": FINITE_GRID_NEED,
        },
    )

    assert tuple(arm.arm_id for arm in audit.arms) == FOUR_ARM_IDS
    assert all(arm.pair_count == 4 for arm in audit.arms)
    assert audit.by_arm[NETWORK_ONLY_SHARED].passed
    assert audit.by_arm[CFE_ONLY_SHARED].failed_pair_ids == (
        "p1__w0",
        "p1__w1",
    )
    assert audit.by_arm[JOINT_CORRECT_SHARED].failed_pair_ids == (
        "p1__w0",
        "p1__w1",
    )
    assert audit.by_arm[
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION
    ].passed
    assert all(not arm.unresolved_pair_ids for arm in audit.arms)


def test_b6_training_audit_evaluates_both_separate_traces(monkeypatch):
    calls = []

    def trace_spy(_scenario, _envelope, call, _capacity):
        calls.append(call)
        return SimpleNamespace(feasible=False)

    monkeypatch.setattr(
        scenario_core,
        "evaluate_training_trace_support",
        trace_spy,
    )
    audit_four_arm_training_support(
        (_block("p0", grid=(0.1, 0.0), cfe=(0.1, 0.0)),),
        (_block("w0", workload=(1.0, 0.0)),),
        _cell(),
        capacity_by_arm=_capacities(),
        fixed_policy=_fixed_policy(),
        grid_state_by_power_block={"p0": FINITE_GRID_NEED},
    )

    assert len(calls) == 5
    assert calls[-2] == (0.1, 0.0)
    assert calls[-1] == (0.1, 0.0)


def test_training_audit_rejects_e0_and_propagates_unresolved(monkeypatch):
    power = (_block("p0", grid=(0.1, 0.0), cfe=(0.1, 0.0)),)
    workload = (_block("w0", workload=(1.0, 0.0)),)
    with pytest.raises(ValueError, match="finite_grid_need only"):
        audit_four_arm_training_support(
            power,
            workload,
            _cell(),
            capacity_by_arm=_capacities(),
            fixed_policy=_fixed_policy(),
            grid_state_by_power_block={
                "p0": EXOGENOUS_GRID_INFEASIBILITY
            },
        )

    monkeypatch.setattr(
        scenario_core,
        "evaluate_training_trace_support",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TimeoutError("synthetic unresolved evaluator")
        ),
    )
    with pytest.raises(TimeoutError, match="unresolved"):
        audit_four_arm_training_support(
            power,
            workload,
            _cell(),
            capacity_by_arm=_capacities(),
            fixed_policy=_fixed_policy(),
            grid_state_by_power_block={"p0": FINITE_GRID_NEED},
        )


def test_training_audit_rejects_holdout_support():
    power = (_block("p0", grid=(0.1, 0.0), cfe=(0.1, 0.0)),)
    holdout_workload = (
        TemporalBlock(
            block_id="w0",
            split="holdout",
            probability=1.0,
            first_source_hour=0,
            grid_need=(),
            cfe_call=(),
            workload=(1.0, 0.0),
        ),
    )
    with pytest.raises(ValueError, match="cannot contain holdout"):
        audit_four_arm_training_support(
            power,
            holdout_workload,
            _cell(),
            capacity_by_arm=_capacities(),
            fixed_policy=_fixed_policy(),
            grid_state_by_power_block={"p0": FINITE_GRID_NEED},
        )


def test_registered_service_risk_excludes_debt_only_right_censored_failure():
    scenario = replace(
        _scenario(
            grid=(0.2,),
            green=(0.0,),
            completed=frozenset(),
            require_terminal_inactive=False,
        ),
        available_flexibility_mw=(1.0,),
        recovery_headroom_mw=(0.0,),
    )
    envelope = replace(_envelope(), maximum_recovery_debt_mwh=0.1)
    raw = execute_causal_grid_first_policy(
        scenario,
        envelope,
        0.5,
        service_shortfall_tolerance=1.0e-6,
    )
    registered = registered_service_risk_outcome(scenario, raw)

    assert raw.hard_grid_failure
    assert raw.physical_policy_failure
    assert not raw.service_shortfall_failure
    assert raw.access_shortfall == pytest.approx(0.0)
    assert raw.peak_recovery_debt == pytest.approx(0.2)
    assert raw.terminal_recovery_debt == pytest.approx(0.2)
    assert raw.physical_violations == (
        "maximum_recovery_debt_exceeded_at_step_0",
    )
    assert registered.resolved
    assert registered.right_censored
    assert registered.registered_failure is False
    assert registered.registered_physical_failure is False
    assert registered.service_shortfall_amount == pytest.approx(0.0)
    assert registered.registered_physical_violations == ()
    assert registered.excluded_debt_violations == raw.physical_violations
    assert registered.raw_outcome is raw


@pytest.mark.parametrize("failure_channel", ["call_limit", "shortfall"])
def test_registered_service_risk_keeps_real_service_channels(failure_channel):
    if failure_channel == "call_limit":
        scenario = replace(
            _scenario(
                grid=(0.3,),
                green=(0.0,),
                completed=frozenset(),
                require_terminal_inactive=False,
            ),
            available_flexibility_mw=(1.0,),
            recovery_headroom_mw=(0.0,),
        )
        capacity = 0.2
    else:
        scenario = replace(
            _scenario(
                grid=(0.0,),
                green=(0.3,),
                completed=frozenset(),
                require_terminal_inactive=False,
            ),
            available_flexibility_mw=(1.0,),
            recovery_headroom_mw=(0.0,),
        )
        capacity = 0.1
    raw = execute_causal_grid_first_policy(
        scenario,
        _envelope(),
        capacity,
        service_shortfall_tolerance=1.0e-6,
    )
    registered = registered_service_risk_outcome(scenario, raw)

    assert registered.resolved
    assert registered.registered_failure is True
    if failure_channel == "call_limit":
        assert registered.registered_physical_failure is True
        assert any(
            code.startswith("call_limit_exceeded_at_step_")
            for code in registered.registered_physical_violations
        )
        assert registered.service_shortfall_failure is False
    else:
        assert registered.registered_physical_failure is False
        assert registered.service_shortfall_failure is True
        assert registered.service_shortfall_amount == pytest.approx(0.2)


def test_unbound_terminal_condition_and_unknown_violation_are_fail_closed():
    scenario = _scenario()
    terminal_only = replace(
        _outcome(scenario, 0.5),
        physical_policy_failure=True,
        physical_violations=("policy_terminal_recovery_incomplete",),
    )
    registered_terminal = registered_service_risk_outcome(
        scenario,
        terminal_only,
    )
    assert registered_terminal.resolved
    assert registered_terminal.registered_failure is False
    assert registered_terminal.excluded_terminal_condition_violations == (
        "policy_terminal_recovery_incomplete",
    )

    unknown = replace(
        _outcome(scenario, 0.5),
        physical_policy_failure=True,
        physical_violations=("future_unknown_physical_violation",),
    )
    registered_unknown = registered_service_risk_outcome(scenario, unknown)
    assert registered_unknown.resolved
    assert registered_unknown.registered_failure is True
    assert registered_unknown.registered_physical_violations == (
        "future_unknown_physical_violation",
    )

    inconsistent = replace(
        _outcome(scenario, 0.5),
        physical_policy_failure=True,
    )
    registered_inconsistent = registered_service_risk_outcome(
        scenario,
        inconsistent,
    )
    assert not registered_inconsistent.resolved
    assert registered_inconsistent.registered_failure is None
    assert registered_inconsistent.unresolved_reason is not None


def test_public_training_support_adapter_locks_physical_boundary_semantics():
    recovering = replace(
        _scenario(grid=(0.2, 0.0), green=(0.0, 0.0)),
        available_flexibility_mw=(1.0, 1.0),
        recovery_headroom_mw=(0.0, 1.0),
    )
    recovered = evaluate_training_trace_support(
        recovering,
        _envelope(),
        recovering.grid_need_mw,
        0.2,
    )
    assert recovered.feasible
    assert recovered.terminal_recovery_debt_mwh == pytest.approx(0.0)

    call_limited = evaluate_training_trace_support(
        recovering,
        _envelope(),
        recovering.grid_need_mw,
        0.1,
    )
    assert not call_limited.feasible
    assert "call_limit_exceeded_at_step_0" in call_limited.violations

    censored = replace(
        _scenario(
            grid=(0.2,),
            green=(0.0,),
            completed=frozenset(),
            require_terminal_inactive=False,
        ),
        available_flexibility_mw=(1.0,),
        recovery_headroom_mw=(0.0,),
    )
    censored_audit = evaluate_training_trace_support(
        censored,
        _envelope(),
        censored.grid_need_mw,
        0.2,
    )
    assert censored_audit.terminal_recovery_debt_mwh == pytest.approx(0.2)
    assert not any(
        code.startswith("terminal_debt_exceeded_for_period_")
        for code in censored_audit.violations
    )
    completed = replace(censored, completed_periods=frozenset({"block"}))
    completed_audit = evaluate_training_trace_support(
        completed,
        _envelope(),
        completed.grid_need_mw,
        0.2,
    )
    assert "terminal_debt_exceeded_for_period_block" in completed_audit.violations
