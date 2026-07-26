from dataclasses import replace
from types import SimpleNamespace

import pytest
from pyomo.environ import Var
from pyomo.opt import TerminationCondition

import src.models.deterministic_baselines as deterministic_baselines_module
from src.grid import Branch, Bus, Generator, Rts24Data
from src.models import (
    BaselineEndpoint,
    BaselinePolicy,
    ExistingBranchUpgrade,
    FixedPoi,
    FxQuarter,
    FxServiceEnvelope,
    solve_deterministic_baseline,
)
from src.solvers import OsqpQpWorkspace


PARAMETER_STATUS = "synthetic_test_only_not_for_engineering"
RESPONSE_MODEL = "mw_only_sustained_states_no_duration_or_energy_limits"
NORMALIZATION_LABEL = (
    "conservative_minimum_x_normalization_not_economic_optimum"
)
PLANNING_INDEXING = "quarter_root_only_no_state_or_scenario"


@pytest.fixture
def two_line_grid():
    return Rts24Data(
        base_mva=100.0,
        buses=(
            Bus(index=1, demand_mw=0.0),
            Bus(index=2, demand_mw=0.0),
        ),
        generators=(
            Generator(
                index=0,
                bus=1,
                p_min_mw=0.0,
                p_max_mw=200.0,
                cost_quadratic=0.0,
                cost_linear=10.0,
                cost_constant=0.0,
                ramp_10_mw=None,
                ramp_30_mw=None,
                in_service=True,
            ),
        ),
        branches=tuple(
            Branch(
                index=index,
                from_bus=1,
                to_bus=2,
                reactance_pu=0.1,
                rate_a_mw=40.0,
                rate_b_mw=40.0,
                rate_c_mw=80.0,
                tap_ratio=1.0,
                phase_shift_rad=0.0,
                in_service=True,
            )
            for index in range(2)
        ),
        reference_bus=1,
        source_package="synthetic_test",
        source_version="1",
    )


def _quarters(demands_mw, *, operating_hours=1.0):
    if isinstance(operating_hours, (int, float)):
        hours = (float(operating_hours),) * len(demands_mw)
    else:
        hours = tuple(float(number) for number in operating_hours)
    return tuple(
        FxQuarter(
            name=f"q{position}",
            system_load_multiplier=1.0,
            data_center_demand_mw=float(demand),
            operating_hours=hours[position],
            continuous_validation_hours=hours[position],
            discount_factor=1.0,
        )
        for position, demand in enumerate(demands_mw)
    )


def _poi():
    return FixedPoi(
        bus=2,
        initial_capacity_mw=80.0,
        application_capacity_mw=80.0,
    )


def _project(*, lead_time_quarters=1, investment_cost=100.0):
    return ExistingBranchUpgrade(
        name="two_line_corridor_upgrade",
        lead_time_quarters=lead_time_quarters,
        rate_a_increase_mw={0: 40.0, 1: 40.0},
        rate_c_increase_mw={0: 0.0, 1: 0.0},
        poi_capacity_increase_mw=0.0,
        investment_cost=investment_cost,
        parameter_status=PARAMETER_STATUS,
    )


def _service_envelope():
    return FxServiceEnvelope(
        max_conditional_capacity_mw=40.0,
        minimum_operational_block_mw=40.0,
        minimum_validation_hours=1.0,
        response_model=RESPONSE_MODEL,
        parameter_status=PARAMETER_STATUS,
    )


def _solve(
    data,
    *,
    policy,
    quarters,
    project=None,
    access_shortfall_cost_per_mwh=1_000.0,
):
    redispatch = {
        generator.index: generator.p_max_mw for generator in data.generators
    }
    return solve_deterministic_baseline(
        data,
        policy=policy,
        quarters=quarters,
        poi=_poi(),
        project=_project() if project is None else project,
        service_envelope=_service_envelope(),
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
        access_shortfall_cost_per_mwh=access_shortfall_cost_per_mwh,
        branch_indices=(0, 1),
        generator_indices=(),
        immediate_rating="rate_c",
        sustained_rating="rate_a",
        solver_name="highs",
    )


def _displayed_endpoint(result):
    assert result.feasible, result.solver_message
    assert isinstance(result.displayed_endpoint, BaselineEndpoint)
    return result.displayed_endpoint


def _assert_nondecreasing(values, quarter_names):
    sequence = [values[name] for name in quarter_names]
    assert sequence == sorted(sequence)


def _assert_same_planning(first, second):
    assert second.primary_access_shortfall_mwh == pytest.approx(
        first.primary_access_shortfall_mwh
    )
    assert second.minimum_x_exposure_mwh == pytest.approx(
        first.minimum_x_exposure_mwh
    )
    assert second.maximum_x_exposure_mwh == pytest.approx(
        first.maximum_x_exposure_mwh
    )
    for first_endpoint, second_endpoint in (
        (first.minimum_x_endpoint, second.minimum_x_endpoint),
        (first.maximum_x_endpoint, second.maximum_x_endpoint),
    ):
        assert second_endpoint.firm_capacity_mw == pytest.approx(
            first_endpoint.firm_capacity_mw
        )
        assert second_endpoint.conditional_capacity_mw == pytest.approx(
            first_endpoint.conditional_capacity_mw
        )
        assert second_endpoint.total_capacity_mw == pytest.approx(
            first_endpoint.total_capacity_mw
        )
        assert second_endpoint.access_shortfall_mw == pytest.approx(
            first_endpoint.access_shortfall_mw
        )
        assert second_endpoint.project_started == first_endpoint.project_started
        assert (
            second_endpoint.project_start_quarter
            == first_endpoint.project_start_quarter
        )
        assert (
            second_endpoint.commissioned_by_quarter
            == first_endpoint.commissioned_by_quarter
        )


def test_b0_releases_zero_capacity_until_the_upgrade_is_commissioned(
    two_line_grid,
):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B0_WAIT,
        quarters=_quarters((80.0, 80.0)),
    )
    endpoint = _displayed_endpoint(result)

    assert result.policy is BaselinePolicy.B0_WAIT
    assert endpoint.project_started
    assert endpoint.project_start_quarter == "q0"
    assert endpoint.commissioned_by_quarter == {"q0": False, "q1": True}
    assert endpoint.firm_capacity_mw == pytest.approx({"q0": 0.0, "q1": 80.0})
    assert endpoint.conditional_capacity_mw == pytest.approx(
        {"q0": 0.0, "q1": 0.0}
    )
    assert endpoint.total_capacity_mw == pytest.approx({"q0": 0.0, "q1": 80.0})


def test_b1_uses_existing_firm_capacity_immediately_and_never_releases_x(
    two_line_grid,
):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B1_FIRM,
        quarters=_quarters((80.0, 80.0)),
    )
    endpoint = _displayed_endpoint(result)

    assert result.policy is BaselinePolicy.B1_FIRM
    assert endpoint.firm_capacity_mw == pytest.approx({"q0": 40.0, "q1": 80.0})
    assert endpoint.total_capacity_mw == pytest.approx({"q0": 40.0, "q1": 80.0})
    assert endpoint.conditional_capacity_mw == pytest.approx(
        {"q0": 0.0, "q1": 0.0}
    )
    assert result.minimum_x_exposure_mwh == pytest.approx(0.0)
    assert result.maximum_x_exposure_mwh == pytest.approx(0.0)


def test_b2_calls_x_only_in_sustained_states_and_preserves_firm_load(
    two_line_grid,
):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )
    endpoint = _displayed_endpoint(result)

    assert result.policy is BaselinePolicy.B2_STATIC_FX
    assert endpoint.firm_capacity_mw["q0"] == pytest.approx(40.0)
    assert endpoint.conditional_capacity_mw["q0"] == pytest.approx(40.0)
    assert endpoint.total_capacity_mw["q0"] == pytest.approx(80.0)

    sustained_calls = []
    for state in result.states:
        call = endpoint.state_call_mw["q0"][state.name]
        poi_load = endpoint.state_poi_load_mw["q0"][state.name]
        if state.response_mode in {"base", "fixed"}:
            assert call == pytest.approx(0.0, abs=1.0e-8)
        else:
            assert 0.0 <= call <= endpoint.conditional_capacity_mw["q0"] + 1.0e-7
            sustained_calls.append(call)
        assert poi_load >= endpoint.firm_capacity_mw["q0"] - 1.0e-7
    assert sustained_calls
    assert max(sustained_calls) > 0.0


@pytest.mark.parametrize(
    "policy",
    (
        BaselinePolicy.B0_WAIT,
        BaselinePolicy.B1_FIRM,
        BaselinePolicy.B2_STATIC_FX,
    ),
)
def test_capacity_balance_and_irreversibility_hold_for_every_baseline(
    two_line_grid,
    policy,
):
    quarters = _quarters((20.0, 60.0, 80.0))
    result = _solve(two_line_grid, policy=policy, quarters=quarters)
    quarter_names = tuple(quarter.name for quarter in quarters)

    assert result.feasible, result.solver_message
    for endpoint in (result.minimum_x_endpoint, result.maximum_x_endpoint):
        for quarter in quarters:
            assert (
                endpoint.total_capacity_mw[quarter.name]
                + endpoint.access_shortfall_mw[quarter.name]
                == pytest.approx(quarter.data_center_demand_mw)
            )
        _assert_nondecreasing(endpoint.firm_capacity_mw, quarter_names)
        _assert_nondecreasing(endpoint.total_capacity_mw, quarter_names)


def test_decreasing_quarterly_demand_is_rejected(two_line_grid):
    with pytest.raises(ValueError, match="nondecreasing"):
        _solve(
            two_line_grid,
            policy=BaselinePolicy.B2_STATIC_FX,
            quarters=_quarters((80.0, 40.0)),
        )


def test_project_lead_time_cannot_release_future_capacity_early(two_line_grid):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B1_FIRM,
        quarters=_quarters((40.0, 80.0, 80.0)),
        project=_project(lead_time_quarters=2),
    )
    endpoint = _displayed_endpoint(result)

    assert endpoint.project_start_quarter == "q0"
    assert endpoint.commissioned_by_quarter == {
        "q0": False,
        "q1": False,
        "q2": True,
    }
    assert endpoint.total_capacity_mw == pytest.approx(
        {"q0": 40.0, "q1": 40.0, "q2": 80.0}
    )
    assert endpoint.access_shortfall_mw == pytest.approx(
        {"q0": 0.0, "q1": 40.0, "q2": 0.0}
    )


def test_b2_reports_both_endpoints_of_a_nonzero_x_exposure_interval(
    two_line_grid,
):
    quarters = _quarters((80.0, 80.0))
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=quarters,
    )

    assert result.feasible, result.solver_message
    assert isinstance(result.minimum_x_endpoint, BaselineEndpoint)
    assert isinstance(result.maximum_x_endpoint, BaselineEndpoint)
    assert result.minimum_x_endpoint.access_shortfall_mwh == pytest.approx(
        result.primary_access_shortfall_mwh
    )
    assert result.maximum_x_endpoint.access_shortfall_mwh == pytest.approx(
        result.primary_access_shortfall_mwh
    )
    assert result.minimum_x_exposure_mwh == pytest.approx(
        result.minimum_x_endpoint.conditional_capacity_exposure_mwh
    )
    assert result.maximum_x_exposure_mwh == pytest.approx(
        result.maximum_x_endpoint.conditional_capacity_exposure_mwh
    )
    assert result.minimum_x_exposure_mwh < result.maximum_x_exposure_mwh
    assert result.minimum_x_exposure_mwh == pytest.approx(40.0)
    assert result.maximum_x_exposure_mwh == pytest.approx(80.0)
    for name in ("q0", "q1"):
        assert result.minimum_x_endpoint.total_capacity_mw[name] == pytest.approx(
            result.maximum_x_endpoint.total_capacity_mw[name]
        )


def test_planning_and_x_interval_do_not_depend_on_unevidenced_costs(
    two_line_grid,
):
    quarters = _quarters((100.0, 100.0))
    project = _project(investment_cost=100.0)
    reference = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=quarters,
        project=project,
        access_shortfall_cost_per_mwh=1_000.0,
    )
    expensive_project = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=quarters,
        project=replace(project, investment_cost=100_000.0),
        access_shortfall_cost_per_mwh=1_000.0,
    )
    expensive_operation = _solve(
        replace(
            two_line_grid,
            generators=(
                replace(two_line_grid.generators[0], cost_linear=100.0),
            ),
        ),
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=quarters,
        project=project,
        access_shortfall_cost_per_mwh=1_000.0,
    )
    expensive_shortfall = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=quarters,
        project=project,
        access_shortfall_cost_per_mwh=10_000.0,
    )

    for changed in (
        expensive_project,
        expensive_operation,
        expensive_shortfall,
    ):
        _assert_same_planning(reference, changed)

    assert expensive_project.dispatch_result.investment_cost > (
        reference.dispatch_result.investment_cost
    )
    assert expensive_operation.dispatch_result.operating_cost > (
        reference.dispatch_result.operating_cost
    )
    assert expensive_shortfall.dispatch_result.access_shortfall_cost > (
        reference.dispatch_result.access_shortfall_cost
    )


def test_displayed_plan_is_the_minimum_x_non_economic_normalization(
    two_line_grid,
):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )

    assert result.displayed_endpoint == result.minimum_x_endpoint
    assert result.displayed_endpoint_name == "minimum_x_endpoint"
    assert result.normalization_label == NORMALIZATION_LABEL
    assert result.displayed_endpoint.normalization_label == NORMALIZATION_LABEL


def test_planning_paths_are_quarter_only_and_state_keys_are_operational(
    two_line_grid,
):
    quarters = _quarters((80.0, 80.0))
    quarter_names = {quarter.name for quarter in quarters}
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=quarters,
    )

    assert result.planning_variable_indexing == PLANNING_INDEXING
    for endpoint in (result.minimum_x_endpoint, result.maximum_x_endpoint):
        assert endpoint.planning_variable_indexing == PLANNING_INDEXING
        for quarter_mapping in (
            endpoint.firm_capacity_mw,
            endpoint.conditional_capacity_mw,
            endpoint.total_capacity_mw,
            endpoint.access_shortfall_mw,
            endpoint.commissioned_by_quarter,
        ):
            assert set(quarter_mapping) == quarter_names
            assert all(not isinstance(key, tuple) for key in quarter_mapping)
        assert set(endpoint.state_call_mw) == quarter_names
        assert set(endpoint.state_poi_load_mw) == quarter_names
        for quarter in quarter_names:
            assert set(endpoint.state_call_mw[quarter]) == {
                state.name for state in result.states
            }
            assert set(endpoint.state_poi_load_mw[quarter]) == {
                state.name for state in result.states
            }


def test_models_with_unfixed_integer_variables_are_never_sent_to_osqp(
    two_line_grid,
    monkeypatch,
):
    original_solve = OsqpQpWorkspace.solve
    observed_continuous_calls = []

    def guarded_solve(workspace, model):
        unfixed_discrete = tuple(
            variable.name
            for variable in model.component_data_objects(
                Var,
                active=True,
                descend_into=True,
            )
            if not variable.fixed and not variable.is_continuous()
        )
        assert not unfixed_discrete, (
            "OSQP received unfixed integer planning variables: "
            f"{unfixed_discrete}"
        )
        observed_continuous_calls.append(True)
        return original_solve(workspace, model)

    monkeypatch.setattr(OsqpQpWorkspace, "solve", guarded_solve)
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )

    assert result.feasible, result.solver_message
    assert observed_continuous_calls


def test_displayed_plan_closes_the_loop_through_feasible_m3_dispatch(
    two_line_grid,
):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )
    endpoint = _displayed_endpoint(result)
    dispatch = result.dispatch_result

    assert dispatch is not None
    assert dispatch.feasible, dispatch.solver_message
    assert dispatch.firm_capacity_mw == pytest.approx(endpoint.firm_capacity_mw)
    assert dispatch.conditional_capacity_mw == pytest.approx(
        endpoint.conditional_capacity_mw
    )
    assert dispatch.total_capacity_mw == pytest.approx(endpoint.total_capacity_mw)
    assert dispatch.project_started == endpoint.project_started
    assert dispatch.start_quarter == endpoint.project_start_quarter
    assert dispatch.commissioned_by_quarter == endpoint.commissioned_by_quarter


def test_m3_infeasibility_is_fail_closed_and_hides_displayed_endpoint(
    two_line_grid,
    monkeypatch,
):
    failed_dispatch = SimpleNamespace(
        feasible=False,
        termination_condition="forced_m3_failure",
        solver_status="warning",
        solver_message="forced M3 failure",
    )
    monkeypatch.setattr(
        deterministic_baselines_module,
        "evaluate_deterministic_fx_plan",
        lambda *args, **kwargs: failed_dispatch,
    )

    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )

    assert not result.feasible
    assert result.dispatch_result is failed_dispatch
    assert result.displayed_endpoint is None
    assert result.displayed_endpoint_name is None
    assert result.normalization_label is None
    assert result.failure_stage == "displayed_dispatch"


def test_m3_solver_exception_is_fail_closed_and_hides_displayed_endpoint(
    two_line_grid,
    monkeypatch,
):
    def raise_solver_exception(*args, **kwargs):
        raise RuntimeError("forced OSQP exception wrapper")

    monkeypatch.setattr(OsqpQpWorkspace, "solve", raise_solver_exception)
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )

    assert not result.feasible
    assert result.failure_stage == "displayed_dispatch"
    assert result.termination_condition == "displayed_dispatch_exception"
    assert result.displayed_endpoint is None
    assert result.displayed_endpoint_name is None
    assert result.normalization_label is None


def test_normalized_endpoints_respect_primary_and_x_bands_with_nonuniform_hours(
    two_line_grid,
):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters(
            (20.0, 60.0, 80.0),
            operating_hours=(1.0, 2.0, 3.0),
        ),
    )

    assert result.feasible, result.solver_message
    assert result.primary_access_shortfall_mwh is not None
    assert result.primary_tolerance_mwh is not None
    assert result.x_exposure_tolerance_mwh is not None
    for endpoint, target_x_exposure in (
        (result.minimum_x_endpoint, result.minimum_x_exposure_mwh),
        (result.maximum_x_endpoint, result.maximum_x_exposure_mwh),
    ):
        assert endpoint is not None
        assert target_x_exposure is not None
        assert endpoint.access_shortfall_mwh <= (
            result.primary_access_shortfall_mwh
            + result.primary_tolerance_mwh
            + 1.0e-8
        )
        assert abs(
            endpoint.conditional_capacity_exposure_mwh - target_x_exposure
        ) <= result.x_exposure_tolerance_mwh + 1.0e-8


def test_second_endpoint_normalization_failure_hides_displayed_endpoint(
    two_line_grid,
    monkeypatch,
):
    real_normalize = deterministic_baselines_module._normalize_endpoint
    call_count = 0

    def fail_second_normalization(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        endpoint = real_normalize(*args, **kwargs)
        return None if call_count == 2 else endpoint

    monkeypatch.setattr(
        deterministic_baselines_module,
        "_normalize_endpoint",
        fail_second_normalization,
    )
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )

    assert call_count == 2
    assert not result.feasible
    assert result.minimum_x_endpoint is not None
    assert result.displayed_endpoint is None
    assert result.displayed_endpoint_name is None
    assert result.normalization_label is None
    assert result.failure_stage == "maximum_x_normalization"
    assert not result.stage_diagnostics[-1].accepted


def test_success_reports_all_lexicographic_and_endpoint_audits(two_line_grid):
    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )

    assert result.feasible, result.solver_message
    assert result.failure_stage is None
    assert all(diagnostic.accepted for diagnostic in result.stage_diagnostics)
    assert {diagnostic.stage for diagnostic in result.stage_diagnostics} == {
        "primary_access_shortfall",
        "minimum_x_exposure",
        "maximum_x_exposure",
        "x_exposure_interval_audit",
        "minimum_x_project_count",
        "minimum_x_commissioning_exposure",
        "minimum_x_endpoint_audit",
        "maximum_x_project_count",
        "maximum_x_commissioning_exposure",
        "maximum_x_endpoint_audit",
    }
    for endpoint in (result.minimum_x_endpoint, result.maximum_x_endpoint):
        assert endpoint.maximum_original_constraint_violation <= 1.0e-6
        assert endpoint.maximum_integrality_violation <= 1.0e-6
        assert endpoint.primary_band_violation_mwh <= 1.0e-8
        assert endpoint.x_band_violation_mwh <= 1.0e-8
        assert endpoint.state_call_interpretation == (
            "feasible_planning_witness_not_canonical_minimum_call_dispatch"
        )


def test_locally_optimal_milp_termination_is_not_accepted():
    assert not deterministic_baselines_module._is_accepted_termination(
        TerminationCondition.locallyOptimal
    )


def test_postsolve_constraint_audit_fails_closed(two_line_grid, monkeypatch):
    monkeypatch.setattr(
        deterministic_baselines_module,
        "_maximum_model_violation",
        lambda *args, **kwargs: 1.0e-3,
    )

    result = _solve(
        two_line_grid,
        policy=BaselinePolicy.B2_STATIC_FX,
        quarters=_quarters((80.0, 80.0)),
    )

    assert not result.feasible
    assert result.failure_stage == "primary_access_shortfall"
    assert result.stage_diagnostics[-1].failure_reason == (
        "model_constraint_violation"
    )
    assert result.displayed_endpoint is None


def test_nonfinite_generator_cost_is_rejected_before_planning(two_line_grid):
    invalid_data = replace(
        two_line_grid,
        generators=(
            replace(two_line_grid.generators[0], cost_constant=float("inf")),
        ),
    )

    with pytest.raises(ValueError, match="finite generator costs"):
        _solve(
            invalid_data,
            policy=BaselinePolicy.B2_STATIC_FX,
            quarters=_quarters((80.0, 80.0)),
        )
