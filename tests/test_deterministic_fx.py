from dataclasses import replace

import pytest

from src.grid import Branch, Bus, Generator, Rts24Data
from src.models import (
    ExistingBranchUpgrade,
    FixedFxPlan,
    FixedPoi,
    FxQuarter,
    FxServiceEnvelope,
    evaluate_deterministic_fx_plan,
)


PARAMETER_STATUS = "synthetic_test_only_not_for_engineering"
RESPONSE_MODEL = "mw_only_sustained_states_no_duration_or_energy_limits"


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
                p_max_mw=100.0,
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


@pytest.fixture
def two_generator_grid(two_line_grid):
    primary = replace(two_line_grid.generators[0], p_max_mw=80.0)
    backup = replace(
        primary,
        index=1,
        cost_linear=20.0,
    )
    return replace(two_line_grid, generators=(primary, backup))


def _quarters(demands_mw):
    return tuple(
        FxQuarter(
            name=f"q{index}",
            system_load_multiplier=1.0,
            data_center_demand_mw=float(demand),
            operating_hours=1.0,
            continuous_validation_hours=1.0,
            discount_factor=1.0,
        )
        for index, demand in enumerate(demands_mw)
    )


def _poi():
    return FixedPoi(
        bus=2,
        initial_capacity_mw=80.0,
        application_capacity_mw=80.0,
    )


def _project(*, rate_a_increase_mw=0.0):
    return ExistingBranchUpgrade(
        name="two_line_corridor_upgrade",
        lead_time_quarters=1,
        rate_a_increase_mw={0: rate_a_increase_mw, 1: rate_a_increase_mw},
        rate_c_increase_mw={0: 0.0, 1: 0.0},
        poi_capacity_increase_mw=0.0,
        investment_cost=0.0,
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


def _plan(firm, conditional, *, project_start_quarter=None):
    return FixedFxPlan(
        firm_capacity_mw=firm,
        conditional_capacity_mw=conditional,
        project_start_quarter=project_start_quarter,
        parameter_status=PARAMETER_STATUS,
    )


def _evaluate(
    data,
    *,
    quarters,
    plan,
    project=None,
    poi=None,
    redispatch_mw=None,
    branch_indices=(0, 1),
    generator_indices=(),
):
    redispatch = (
        {
            generator.index: generator.p_max_mw
            for generator in data.generators
        }
        if redispatch_mw is None
        else redispatch_mw
    )
    return evaluate_deterministic_fx_plan(
        data,
        quarters=quarters,
        poi=_poi() if poi is None else poi,
        project=_project() if project is None else project,
        plan=plan,
        service_envelope=_service_envelope(),
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
        access_shortfall_cost_per_mwh=1_000.0,
        branch_indices=branch_indices,
        generator_indices=generator_indices,
        immediate_rating="rate_c",
        sustained_rating="rate_a",
        primary_objective_tolerance=1.0e-7,
        solver_name="highs",
    )


def _assert_layer_is_secure(data, result, layer_results):
    for quarter, state_results in layer_results.items():
        for state_name, state_result in state_results.items():
            assert state_result.max_balance_residual_mw <= 1.0e-6
            ratings = result.effective_branch_ratings_mw[quarter][state_name]
            for branch in data.branches:
                flow = state_result.branch_flows_mw[branch.index]
                if branch.index in state_result.outaged_branch_indices:
                    assert flow == pytest.approx(0.0, abs=1.0e-9)
                else:
                    assert abs(flow) <= ratings[branch.index] + 1.0e-6


def test_fx_calls_only_in_sustained_states_and_preserves_firm(two_line_grid):
    quarters = _quarters((80.0,))
    result = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=_plan({"q0": 40.0}, {"q0": 40.0}),
    )

    assert result.feasible
    assert result.firm_capacity_mw == pytest.approx({"q0": 40.0})
    assert result.conditional_capacity_mw == pytest.approx({"q0": 40.0})
    assert result.total_capacity_mw == pytest.approx({"q0": 80.0})
    assert result.connected_demand_mw == pytest.approx({"q0": 80.0})
    assert result.firm_demand_mw == pytest.approx({"q0": 40.0})
    assert result.active_conditional_demand_mw == pytest.approx({"q0": 40.0})
    assert result.access_shortfall_mw == pytest.approx({"q0": 0.0})

    pre_response = ("base", "branch_0_immediate", "branch_1_immediate")
    sustained = ("branch_0_sustained", "branch_1_sustained")
    for state in pre_response:
        assert result.actual_grid_curtailment_mw["q0"][state] == pytest.approx(0.0)
        assert result.certified_grid_curtailment_mw["q0"][state] == pytest.approx(
            0.0
        )
        assert result.actual_poi_load_mw["q0"][state] == pytest.approx(80.0)
        assert result.certified_poi_load_mw["q0"][state] == pytest.approx(80.0)
    for state in sustained:
        assert result.actual_grid_curtailment_mw["q0"][state] == pytest.approx(40.0)
        assert result.certified_grid_curtailment_mw["q0"][state] == pytest.approx(
            40.0
        )
        assert result.actual_poi_load_mw["q0"][state] == pytest.approx(40.0)
        assert result.certified_poi_load_mw["q0"][state] == pytest.approx(40.0)

    assert all(
        value == pytest.approx(0.0)
        for value in result.firm_breach_mw["q0"].values()
    )
    assert all(
        value == pytest.approx(0.0)
        for value in result.conditional_breach_mw["q0"].values()
    )
    assert result.minimum_call_certificate_mw_sum == pytest.approx(160.0)
    assert result.investment_cost == pytest.approx(0.0)
    assert result.operating_cost == pytest.approx(800.0)
    assert result.access_shortfall_cost == pytest.approx(0.0)
    assert result.objective == pytest.approx(
        result.investment_cost
        + result.operating_cost
        + result.access_shortfall_cost
    )
    assert result.milestones.t100.quarter == "q0"
    _assert_layer_is_secure(two_line_grid, result, result.actual_state_results)
    _assert_layer_is_secure(two_line_grid, result, result.certified_state_results)


def test_generator_outage_uses_sustained_layer_specific_response(
    two_generator_grid,
):
    redispatch = {0: 40.0, 1: 40.0}
    result = _evaluate(
        two_generator_grid,
        quarters=_quarters((80.0,)),
        plan=_plan({"q0": 40.0}, {"q0": 40.0}),
        redispatch_mw=redispatch,
        branch_indices=(),
        generator_indices=(0,),
    )

    assert result.feasible
    assert tuple(state.name for state in result.states) == (
        "base",
        "generator_0_sustained",
    )
    assert "generator_0_immediate" not in {state.name for state in result.states}
    for layer_results in (
        result.actual_state_results,
        result.certified_state_results,
    ):
        base = layer_results["q0"]["base"]
        outage = layer_results["q0"]["generator_0_sustained"]
        assert outage.generation_mw[0] == pytest.approx(0.0, abs=1.0e-9)
        surviving_change = outage.generation_mw[1] - base.generation_mw[1]
        assert abs(surviving_change) <= redispatch[1] + 1.0e-6
        assert base.max_balance_residual_mw <= 1.0e-6
        assert outage.max_balance_residual_mw <= 1.0e-6


def test_quadratic_dispatch_uses_audited_direct_qp_solution(two_line_grid):
    quadratic_generator = replace(
        two_line_grid.generators[0],
        cost_quadratic=1.0,
        cost_linear=0.0,
    )
    quadratic_grid = replace(
        two_line_grid,
        generators=(
            quadratic_generator,
            replace(quadratic_generator, index=1),
        ),
    )

    result = _evaluate(
        quadratic_grid,
        quarters=_quarters((80.0,)),
        plan=_plan({"q0": 80.0}, {"q0": 0.0}),
        branch_indices=(),
    )

    assert result.feasible
    actual_base = result.actual_state_results["q0"]["base"]
    assert actual_base.generation_mw == pytest.approx({0: 40.0, 1: 40.0})
    assert result.base_operating_cost_per_hour == pytest.approx({"q0": 3_200.0})
    assert result.primary_optimization_objective == pytest.approx(3_200.0)
    assert result.canonical_dispatch_primary_objective == pytest.approx(3_200.0)
    assert result.objective == pytest.approx(3_200.0)
    assert result.cost_interpretation == (
        "direct_convex_qp_numerical_solution_then_l1_linear_"
        "feasibility_projection_and_minimum_call"
    )
    assert result.primary_qp_solver == "osqp"
    assert result.primary_qp_status == "solved"
    assert result.primary_qp_max_constraint_violation <= 1.0e-6
    assert abs(result.primary_linear_repair_objective_deviation) <= 1.0e-6
    assert abs(result.primary_linear_repair_objective_deviation) <= (
        result.primary_linear_repair_objective_deviation_tolerance
    )
    assert result.primary_linear_repair_total_generation_movement_mw >= (
        result.primary_linear_repair_max_generation_movement_mw
    )
    assert result.primary_linear_repair_max_generation_movement_mw <= (
        result.primary_linear_repair_generation_movement_tolerance_mw
    )
    assert result.primary_linear_repair_acceptance_interpretation == (
        "numerical_feasibility_projection_envelopes_not_"
        "optimality_gap_or_error_certificate"
    )


def test_low_actual_demand_keeps_full_contract_certification(two_line_grid):
    result = _evaluate(
        two_line_grid,
        quarters=_quarters((20.0,)),
        plan=_plan({"q0": 40.0}, {"q0": 40.0}),
    )

    assert result.feasible
    assert result.connected_demand_mw == pytest.approx({"q0": 20.0})
    assert result.firm_demand_mw == pytest.approx({"q0": 20.0})
    assert result.active_conditional_demand_mw == pytest.approx({"q0": 0.0})
    assert result.access_shortfall_mw == pytest.approx({"q0": 0.0})
    assert all(
        value == pytest.approx(0.0)
        for value in result.actual_grid_curtailment_mw["q0"].values()
    )
    assert all(
        value == pytest.approx(20.0)
        for value in result.actual_poi_load_mw["q0"].values()
    )
    for state in ("base", "branch_0_immediate", "branch_1_immediate"):
        assert result.certified_poi_load_mw["q0"][state] == pytest.approx(80.0)
    for state in ("branch_0_sustained", "branch_1_sustained"):
        assert result.certified_grid_curtailment_mw["q0"][state] == pytest.approx(
            40.0
        )
        assert result.certified_poi_load_mw["q0"][state] == pytest.approx(40.0)
    _assert_layer_is_secure(two_line_grid, result, result.actual_state_results)
    _assert_layer_is_secure(two_line_grid, result, result.certified_state_results)


def test_low_actual_demand_cannot_mask_infeasible_contract(two_line_grid):
    result = _evaluate(
        two_line_grid,
        quarters=_quarters((20.0,)),
        plan=_plan({"q0": 80.0}, {"q0": 0.0}),
    )

    assert not result.feasible
    assert result.actual_state_results == {}
    assert result.certified_state_results == {}


def test_without_x_only_n_minus_one_deliverable_firm_is_feasible(two_line_grid):
    quarters = _quarters((80.0,))
    feasible = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=_plan({"q0": 40.0}, {"q0": 0.0}),
    )

    assert feasible.feasible
    assert feasible.total_capacity_mw == pytest.approx({"q0": 40.0})
    assert feasible.connected_demand_mw == pytest.approx({"q0": 40.0})
    assert feasible.access_shortfall_mw == pytest.approx({"q0": 40.0})
    assert all(
        value == pytest.approx(0.0)
        for value in feasible.actual_grid_curtailment_mw["q0"].values()
    )
    assert all(
        value == pytest.approx(40.0)
        for value in feasible.actual_poi_load_mw["q0"].values()
    )

    infeasible = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=_plan({"q0": 80.0}, {"q0": 0.0}),
    )
    assert not infeasible.feasible


@pytest.mark.parametrize(
    ("firm", "conditional", "message"),
    (
        (
            {"q0": 40.0, "q1": 20.0},
            {"q0": 20.0, "q1": 40.0},
            "Firm capacity cannot decrease",
        ),
        (
            {"q0": 40.0, "q1": 40.0},
            {"q0": 40.0, "q1": 20.0},
            "Total contract capacity cannot decrease",
        ),
        (
            {"q0": 0.0, "q1": 0.0},
            {"q0": 41.0, "q1": 41.0},
            "exceeds the certified MW envelope",
        ),
    ),
)
def test_invalid_fixed_fx_paths_are_rejected(
    two_line_grid,
    firm,
    conditional,
    message,
):
    with pytest.raises(ValueError, match=message):
        _evaluate(
            two_line_grid,
            quarters=_quarters((80.0, 80.0)),
            plan=_plan(firm, conditional),
        )


def test_commissioned_upgrade_can_convert_x_to_f(two_line_grid):
    quarters = _quarters((80.0, 80.0))
    result = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=_plan(
            {"q0": 40.0, "q1": 80.0},
            {"q0": 40.0, "q1": 0.0},
            project_start_quarter="q0",
        ),
        project=_project(rate_a_increase_mw=40.0),
    )

    assert result.feasible
    assert result.total_capacity_mw == pytest.approx({"q0": 80.0, "q1": 80.0})
    assert result.commissioned_by_quarter == {"q0": False, "q1": True}
    for state in ("branch_0_sustained", "branch_1_sustained"):
        assert result.actual_grid_curtailment_mw["q0"][state] == pytest.approx(40.0)
        assert result.certified_grid_curtailment_mw["q0"][state] == pytest.approx(
            40.0
        )
        assert result.actual_grid_curtailment_mw["q1"][state] == pytest.approx(0.0)
        assert result.certified_grid_curtailment_mw["q1"][state] == pytest.approx(
            0.0
        )
        assert result.actual_poi_load_mw["q1"][state] == pytest.approx(80.0)
        assert result.certified_poi_load_mw["q1"][state] == pytest.approx(80.0)
    _assert_layer_is_secure(two_line_grid, result, result.actual_state_results)
    _assert_layer_is_secure(two_line_grid, result, result.certified_state_results)


def test_poi_upgrade_gates_fixed_capacity_path_and_uses_start_discount(
    two_line_grid,
):
    base_quarters = _quarters((40.0, 80.0))
    quarters = (
        replace(base_quarters[0], discount_factor=0.8),
        replace(base_quarters[1], discount_factor=0.6),
    )
    poi = replace(_poi(), initial_capacity_mw=40.0)
    project = replace(
        _project(),
        poi_capacity_increase_mw=40.0,
        investment_cost=125.0,
    )
    firm = {"q0": 40.0, "q1": 40.0}
    conditional = {"q0": 0.0, "q1": 40.0}

    commissioned = _evaluate(
        two_line_grid,
        quarters=quarters,
        poi=poi,
        project=project,
        plan=_plan(
            firm,
            conditional,
            project_start_quarter="q0",
        ),
    )

    assert commissioned.feasible
    assert commissioned.total_capacity_mw == pytest.approx(
        {"q0": 40.0, "q1": 80.0}
    )
    assert commissioned.project_started
    assert commissioned.start_quarter == "q0"
    assert commissioned.commissioned_by_quarter == {"q0": False, "q1": True}
    assert commissioned.investment_cost == pytest.approx(125.0 * 0.8)

    not_started = _evaluate(
        two_line_grid,
        quarters=quarters,
        poi=poi,
        project=project,
        plan=_plan(firm, conditional),
    )
    assert not not_started.feasible


def test_native_system_generation_shortage_is_infeasible(two_line_grid):
    insufficient = replace(
        two_line_grid,
        buses=(
            replace(two_line_grid.buses[0], demand_mw=101.0),
            two_line_grid.buses[1],
        ),
    )
    result = _evaluate(
        insufficient,
        quarters=_quarters((0.0,)),
        plan=_plan({"q0": 0.0}, {"q0": 0.0}),
    )

    assert not result.feasible
    assert result.firm_breach_mw == {}
    assert result.conditional_breach_mw == {}
