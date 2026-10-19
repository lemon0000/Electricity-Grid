from dataclasses import replace

import pytest

import src.models.deterministic_expansion as deterministic_expansion_module
from src.grid import Branch, Bus, Generator, Rts24Data, solve_dc_opf
from src.models.deterministic_expansion import (
    ExistingBranchUpgrade,
    FixedPoi,
    PlanningQuarter,
    solve_deterministic_expansion,
)


ACCESS_SHORTFALL_COST = 1_000.0


@pytest.fixture
def two_bus_grid():
    return Rts24Data(
        base_mva=100.0,
        buses=(
            Bus(index=1, demand_mw=20.0),
            Bus(index=2, demand_mw=0.0),
        ),
        generators=(
            Generator(
                index=0,
                bus=1,
                p_min_mw=0.0,
                p_max_mw=120.0,
                cost_quadratic=0.0,
                cost_linear=10.0,
                cost_constant=0.0,
                ramp_10_mw=None,
                ramp_30_mw=None,
                in_service=True,
            ),
        ),
        branches=(
            Branch(
                index=0,
                from_bus=1,
                to_bus=2,
                reactance_pu=0.1,
                rate_a_mw=40.0,
                rate_b_mw=40.0,
                rate_c_mw=40.0,
                tap_ratio=1.0,
                phase_shift_rad=0.0,
                in_service=True,
            ),
            Branch(
                index=1,
                from_bus=1,
                to_bus=2,
                reactance_pu=0.1,
                rate_a_mw=40.0,
                rate_b_mw=40.0,
                rate_c_mw=40.0,
                tap_ratio=1.0,
                phase_shift_rad=0.0,
                in_service=True,
            ),
        ),
        reference_bus=1,
        source_package="synthetic_test",
        source_version="1",
    )


def _quarters(
    demands_mw,
    *,
    system_load_multiplier=1.0,
    operating_hours=1.0,
):
    return tuple(
        PlanningQuarter(
            name=f"q{index}",
            system_load_multiplier=system_load_multiplier,
            data_center_demand_mw=float(demand),
            operating_hours=operating_hours,
            discount_factor=1.0,
        )
        for index, demand in enumerate(demands_mw)
    )


def _upgrade(*, lead_time_quarters=1, investment_cost=0.0):
    return ExistingBranchUpgrade(
        name="parallel_corridor_uprating",
        lead_time_quarters=lead_time_quarters,
        rate_a_increase_mw={0: 40.0, 1: 40.0},
        rate_c_increase_mw={0: 40.0, 1: 40.0},
        poi_capacity_increase_mw=40.0,
        investment_cost=investment_cost,
        parameter_status="synthetic_test_only_not_for_engineering",
    )


def _quadratic_cost_grid(data):
    return replace(
        data,
        buses=(
            replace(data.buses[0], demand_mw=0.0),
            data.buses[1],
        ),
        generators=(
            replace(
                data.generators[0],
                p_max_mw=100.0,
                cost_quadratic=1.0,
                cost_linear=0.0,
            ),
        ),
        branches=tuple(
            replace(
                branch,
                rate_a_mw=200.0,
                rate_b_mw=200.0,
                rate_c_mw=200.0,
            )
            for branch in data.branches
        ),
    )


def _solve(
    data,
    *,
    quarters,
    poi,
    project,
    branch_indices=(),
    generator_indices=(),
    redispatch_up_mw=None,
    redispatch_down_mw=None,
    access_shortfall_cost_per_mwh=ACCESS_SHORTFALL_COST,
):
    default_redispatch = {
        generator.index: generator.p_max_mw for generator in data.generators
    }
    return solve_deterministic_expansion(
        data,
        quarters=quarters,
        poi=poi,
        project=project,
        redispatch_up_mw=(
            default_redispatch if redispatch_up_mw is None else redispatch_up_mw
        ),
        redispatch_down_mw=(
            default_redispatch if redispatch_down_mw is None else redispatch_down_mw
        ),
        branch_indices=tuple(branch_indices),
        generator_indices=tuple(generator_indices),
        immediate_rating="rate_c",
        sustained_rating="rate_a",
        access_shortfall_cost_per_mwh=access_shortfall_cost_per_mwh,
        solver_name="highs",
    )


def _shift_first_qp_objective(monkeypatch, shift):
    real_workspace = deterministic_expansion_module.OsqpQpWorkspace
    workspaces = []

    class ShiftedObjectiveWorkspace:
        def __init__(self, *args, **kwargs):
            self.workspace = real_workspace(*args, **kwargs)
            self.solve_count = 0
            workspaces.append(self)

        def solve(self, model):
            result = self.workspace.solve(model)
            self.solve_count += 1
            if self.solve_count == 1 and result.objective_value is not None:
                return replace(
                    result,
                    objective_value=result.objective_value - shift,
                )
            return result

    monkeypatch.setattr(
        deterministic_expansion_module,
        "OsqpQpWorkspace",
        ShiftedObjectiveWorkspace,
    )
    return workspaces


def test_zero_data_center_demand_reduces_to_base_grid(two_bus_grid):
    quarters = _quarters((0.0,))
    poi = FixedPoi(bus=2, initial_capacity_mw=0.0, application_capacity_mw=0.0)

    result = _solve(
        two_bus_grid,
        quarters=quarters,
        poi=poi,
        project=_upgrade(investment_cost=100.0),
    )
    baseline = solve_dc_opf(two_bus_grid)

    assert result.feasible
    assert not result.project_started
    assert result.start_quarter is None
    assert result.connected_capacity_mw == pytest.approx({"q0": 0.0})
    assert result.access_shortfall_mw == pytest.approx({"q0": 0.0})
    state = result.state_results["q0"]["base"]
    assert state.generation_mw == pytest.approx(baseline.generation_mw)
    assert state.branch_flows_mw == pytest.approx(baseline.branch_flows_mw)
    assert result.objective == pytest.approx(baseline.objective)


def test_equal_objectives_prefer_canonical_no_start_when_it_is_solved_second(
    two_bus_grid,
):
    result = _solve(
        two_bus_grid,
        quarters=_quarters((0.0,)),
        poi=FixedPoi(bus=2, initial_capacity_mw=0.0, application_capacity_mw=0.0),
        project=_upgrade(lead_time_quarters=0, investment_cost=0.0),
    )

    assert result.feasible
    assert not result.project_started
    assert [row["start_quarter"] for row in result.candidate_diagnostics] == [
        None,
        "q0",
    ]
    assert result.candidate_diagnostics[0]["selected"]
    assert not result.candidate_diagnostics[1]["selected"]
    assert result.candidate_diagnostics[1]["commissioned_by_quarter"] == {
        "q0": True
    }
    assert [row["solve_order"] for row in result.candidate_diagnostics] == [1, 0]
    assert result.candidate_diagnostics[0]["objective"] == pytest.approx(
        result.candidate_diagnostics[1]["objective"]
    )


def test_a_strictly_lower_later_objective_is_not_hidden_by_a_tolerance(
    two_bus_grid,
):
    result = _solve(
        two_bus_grid,
        quarters=_quarters((0.0,)),
        poi=FixedPoi(bus=2, initial_capacity_mw=0.0, application_capacity_mw=0.0),
        project=_upgrade(lead_time_quarters=0, investment_cost=5.0e-7),
    )

    no_start, start = result.candidate_diagnostics
    objective_gap = start["objective"] - no_start["objective"]
    assert result.feasible
    assert [no_start["solve_order"], start["solve_order"]] == [1, 0]
    assert 0.0 < objective_gap < 1.0e-6
    assert no_start["selected"]
    assert not start["selected"]
    assert no_start["objective"] == min(
        row["objective"] for row in result.candidate_diagnostics if row["feasible"]
    )


def test_k_plus_one_diagnostics_keep_canonical_order_and_a_separate_solve_order(
    two_bus_grid,
    monkeypatch,
):
    real_workspace = deterministic_expansion_module.OsqpQpWorkspace
    workspaces = []

    class CountingWorkspace:
        def __init__(self, *args, **kwargs):
            self.workspace = real_workspace(*args, **kwargs)
            self.solve_count = 0
            workspaces.append(self)

        def solve(self, model):
            self.solve_count += 1
            return self.workspace.solve(model)

    monkeypatch.setattr(
        deterministic_expansion_module,
        "OsqpQpWorkspace",
        CountingWorkspace,
    )
    quarters = tuple(
        PlanningQuarter(
            name=f"q{index}",
            system_load_multiplier=1.0,
            data_center_demand_mw=0.0,
            operating_hours=1.0,
            discount_factor=1.0,
        )
        for index in range(1, 5)
    )
    result = _solve(
        two_bus_grid,
        quarters=quarters,
        poi=FixedPoi(bus=2, initial_capacity_mw=0.0, application_capacity_mw=0.0),
        project=_upgrade(lead_time_quarters=2, investment_cost=0.0),
    )

    diagnostics = result.candidate_diagnostics
    assert result.feasible
    assert len(workspaces) == 1
    assert workspaces[0].solve_count == len(quarters) + 1
    assert len(diagnostics) == len(quarters) + 1
    assert [row["candidate_index"] for row in diagnostics] == list(range(5))
    assert [row["start_quarter"] for row in diagnostics] == [
        None,
        "q1",
        "q2",
        "q3",
        "q4",
    ]
    assert [row["solve_order"] for row in diagnostics] == [2, 1, 0, 3, 4]
    first_solved = diagnostics[2]
    assert not first_solved["qp_workspace_reused"]
    assert not first_solved["qp_warm_started"]
    assert all(
        row["qp_workspace_reused"] and row["qp_warm_started"]
        for row in diagnostics
        if row is not first_solved
    )
    assert all(row["resolved"] and row["feasible"] for row in diagnostics)
    assert diagnostics[0]["selected"]
    assert sum(bool(row["selected"]) for row in diagnostics) == 1
    for row in diagnostics:
        assert row["qp_settings"]["eps_abs"] == 1.0e-6
        assert row["qp_settings"]["eps_rel"] == 1.0e-8
        assert row["qp_settings"]["time_limit_seconds"] == 120.0
        assert row["qp_settings"]["warm_starting"] is False
        assert row["qp_variable_count"] > 0
        assert row["qp_constraint_row_count"] > 0
        assert row["qp_constraint_nonzeros"] > 0
        assert row["qp_hessian_nonzeros"] == 0
        assert not row["repair_objective_deviation_applicable"]
        assert row["repair_objective_deviation_assessment"] == (
            "not_applicable_original_problem_is_linear"
        )
        assert row["repair_objective_deviation_threshold"] is None
        assert row["repair_objective_deviation_passed"]


def test_direct_quadratic_enumeration_avoids_pwl_discrete_choice_error(
    two_bus_grid,
):
    quadratic_grid = _quadratic_cost_grid(two_bus_grid)
    project = replace(
        _upgrade(lead_time_quarters=0, investment_cost=4_250.0),
        poi_capacity_increase_mw=50.0,
    )
    result = _solve(
        quadratic_grid,
        quarters=_quarters((80.0,)),
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=30.0,
            application_capacity_mw=80.0,
        ),
        project=project,
        access_shortfall_cost_per_mwh=200.0,
    )

    # With two endpoint tangents, the former PWL objectives were 10000 and
    # 10250, so it preferred no-start. True costs are 10900 and 10650.
    assert result.feasible
    assert result.start_quarter == "q0"
    assert result.connected_capacity_mw == pytest.approx({"q0": 80.0})
    assert result.objective == pytest.approx(10_650.0)
    assert [
        row["objective"] for row in result.candidate_diagnostics
    ] == pytest.approx([10_900.0, 10_650.0])
    assert not result.candidate_diagnostics[0]["selected"]
    assert result.candidate_diagnostics[1]["selected"]
    feasible_objectives = [
        row["objective"]
        for row in result.candidate_diagnostics
        if row["feasible"]
    ]
    selected = [row for row in result.candidate_diagnostics if row["selected"]]
    assert len(selected) == 1
    assert selected[0]["objective"] == min(feasible_objectives)
    for row in result.candidate_diagnostics:
        assert row["candidate_solver_seconds"] == pytest.approx(
            row["qp_extraction_seconds"]
            + row["qp_setup_seconds"]
            + row["qp_update_seconds"]
            + row["qp_solve_seconds"]
            + row["repair_solve_seconds"]
        )
    assert result.enumeration_method == (
        "exhaustive_fixed_start_direct_numerical_qp_with_linear_repair"
    )


def test_quadratic_repair_objective_deviation_above_threshold_is_unresolved(
    two_bus_grid,
    monkeypatch,
):
    workspaces = _shift_first_qp_objective(monkeypatch, 100.0)
    result = _solve(
        _quadratic_cost_grid(two_bus_grid),
        quarters=_quarters((80.0,)),
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=30.0,
            application_capacity_mw=80.0,
        ),
        project=replace(
            _upgrade(lead_time_quarters=0, investment_cost=4_250.0),
            poi_capacity_increase_mw=50.0,
        ),
        access_shortfall_cost_per_mwh=200.0,
    )

    assert not result.feasible
    assert result.termination_condition == "enumeration_incomplete"
    assert not any(row["selected"] for row in result.candidate_diagnostics)
    perturbed = result.candidate_diagnostics[1]
    assert len(workspaces) == 1
    assert workspaces[0].solve_count == 2
    assert perturbed["qp_hessian_nonzeros"] > 0
    assert perturbed["repair_objective_deviation_applicable"]
    assert perturbed["repair_objective_deviation_assessment"] == (
        "exceeds_threshold"
    )
    assert not perturbed["repair_objective_deviation_passed"]
    absolute_deviation = abs(perturbed["repair_objective_deviation"])
    assert absolute_deviation > perturbed[
        "repair_objective_deviation_absolute_threshold"
    ]
    assert absolute_deviation > perturbed[
        "repair_objective_deviation_relative_threshold"
    ]
    assert absolute_deviation > perturbed[
        "repair_objective_deviation_scaled_numerical_repair_envelope"
    ]
    assert absolute_deviation > perturbed["repair_objective_deviation_threshold"]
    assert perturbed["resolution_reason"] == "linear_repair_objective_deviation"
    assert perturbed["candidate_solver_seconds"] == pytest.approx(
        perturbed["qp_extraction_seconds"]
        + perturbed["qp_setup_seconds"]
        + perturbed["qp_update_seconds"]
        + perturbed["qp_solve_seconds"]
        + perturbed["repair_solve_seconds"]
    )


def test_scaled_numerical_repair_envelope_accepts_a_small_quadratic_deviation(
    two_bus_grid,
    monkeypatch,
):
    workspaces = _shift_first_qp_objective(monkeypatch, 1.0e-3)
    result = _solve(
        _quadratic_cost_grid(two_bus_grid),
        quarters=_quarters((80.0,)),
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=30.0,
            application_capacity_mw=80.0,
        ),
        project=replace(
            _upgrade(lead_time_quarters=0, investment_cost=4_250.0),
            poi_capacity_increase_mw=50.0,
        ),
        access_shortfall_cost_per_mwh=200.0,
    )

    accepted = result.candidate_diagnostics[1]
    absolute_deviation = abs(accepted["repair_objective_deviation"])
    assert result.feasible
    assert len(workspaces) == 1
    assert workspaces[0].solve_count == 2
    assert accepted["resolved"]
    assert accepted["feasible"]
    assert accepted["repair_objective_deviation_passed"]
    assert absolute_deviation > accepted[
        "repair_objective_deviation_relative_threshold"
    ]
    assert absolute_deviation < accepted[
        "repair_objective_deviation_scaled_numerical_repair_envelope"
    ]
    assert accepted["repair_objective_deviation_assessment"] == (
        "within_scaled_numerical_repair_envelope"
    )
    assert accepted["repair_objective_deviation_threshold"] == accepted[
        "repair_objective_deviation_scaled_numerical_repair_envelope"
    ]
    assert accepted["repair_objective_deviation_threshold_interpretation"] == (
        "numerical_acceptance_envelope_not_optimality_gap_or_error_certificate"
    )


def test_sufficient_network_and_poi_capacity_serve_all_demand_without_building(
    two_bus_grid,
):
    unconstrained_grid = replace(
        two_bus_grid,
        branches=tuple(
            replace(
                branch,
                rate_a_mw=200.0,
                rate_b_mw=200.0,
                rate_c_mw=200.0,
            )
            for branch in two_bus_grid.branches
        ),
    )
    result = _solve(
        unconstrained_grid,
        quarters=_quarters((80.0,)),
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=80.0,
            application_capacity_mw=80.0,
        ),
        project=_upgrade(investment_cost=100.0),
    )

    assert result.feasible
    assert not result.project_started
    assert result.connected_capacity_mw == pytest.approx({"q0": 80.0})
    assert result.access_shortfall_mw == pytest.approx({"q0": 0.0})
    state = result.state_results["q0"]["base"]
    assert sum(state.generation_mw.values()) == pytest.approx(100.0)
    assert max(abs(flow) for flow in state.branch_flows_mw.values()) < 200.0


def test_low_cost_upgrade_starts_in_earliest_quarter(two_bus_grid):
    quarters = _quarters((80.0, 80.0, 80.0, 80.0))
    result = _solve(
        two_bus_grid,
        quarters=quarters,
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=40.0,
            application_capacity_mw=80.0,
        ),
        project=_upgrade(lead_time_quarters=1, investment_cost=0.0),
    )

    assert result.feasible
    assert result.project_started
    assert result.start_quarter == "q0"
    assert result.commissioned_by_quarter == {
        "q0": False,
        "q1": True,
        "q2": True,
        "q3": True,
    }
    assert result.connected_capacity_mw == pytest.approx(
        {"q0": 40.0, "q1": 80.0, "q2": 80.0, "q3": 80.0}
    )
    assert result.access_shortfall_mw == pytest.approx(
        {"q0": 40.0, "q1": 0.0, "q2": 0.0, "q3": 0.0}
    )


def test_upgrade_cost_above_no_build_objective_prevents_building(two_bus_grid):
    quarters = _quarters((80.0, 80.0, 80.0, 80.0))
    # Without an upgrade each quarter costs 60 MW * 10 + 40 MW * 1000.
    no_build_objective = 4.0 * (60.0 * 10.0 + 40.0 * ACCESS_SHORTFALL_COST)
    result = _solve(
        two_bus_grid,
        quarters=quarters,
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=40.0,
            application_capacity_mw=80.0,
        ),
        project=_upgrade(investment_cost=no_build_objective + 1.0),
    )

    assert result.feasible
    assert not result.project_started
    assert result.start_quarter is None
    assert not any(result.commissioned_by_quarter.values())
    assert result.connected_capacity_mw == pytest.approx(
        {quarter.name: 40.0 for quarter in quarters}
    )
    assert result.access_shortfall_mw == pytest.approx(
        {quarter.name: 40.0 for quarter in quarters}
    )
    assert result.objective == pytest.approx(no_build_objective)


def test_lead_time_blocks_capacity_until_commissioning_quarter(two_bus_grid):
    quarters = _quarters((80.0, 80.0, 80.0, 80.0))
    result = _solve(
        two_bus_grid,
        quarters=quarters,
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=40.0,
            application_capacity_mw=80.0,
        ),
        project=_upgrade(lead_time_quarters=2, investment_cost=0.0),
    )

    assert result.feasible
    assert result.start_quarter == "q0"
    assert result.commissioned_by_quarter == {
        "q0": False,
        "q1": False,
        "q2": True,
        "q3": True,
    }
    assert result.connected_capacity_mw == pytest.approx(
        {"q0": 40.0, "q1": 40.0, "q2": 80.0, "q3": 80.0}
    )
    assert result.access_shortfall_mw == pytest.approx(
        {"q0": 40.0, "q1": 40.0, "q2": 0.0, "q3": 0.0}
    )
    for quarter in ("q0", "q1"):
        assert result.state_results[quarter]["base"].branch_flows_mw == (
            pytest.approx({0: 20.0, 1: 20.0})
        )
    for quarter in ("q2", "q3"):
        assert result.state_results[quarter]["base"].branch_flows_mw == (
            pytest.approx({0: 40.0, 1: 40.0})
        )


def test_parallel_line_upgrade_is_secure_for_selected_n_minus_one_states(
    two_bus_grid,
):
    quarters = _quarters((80.0, 80.0))
    project = _upgrade(lead_time_quarters=1, investment_cost=0.0)
    result = _solve(
        two_bus_grid,
        quarters=quarters,
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=40.0,
            application_capacity_mw=80.0,
        ),
        project=project,
        branch_indices=(0, 1),
    )

    assert result.feasible
    assert result.connected_capacity_mw == pytest.approx(
        {"q0": 40.0, "q1": 80.0}
    )
    assert {state.name for state in result.states} == {
        "base",
        "branch_0_immediate",
        "branch_0_sustained",
        "branch_1_immediate",
        "branch_1_sustained",
    }
    states_by_name = {state.name: state for state in result.states}
    for quarter in quarters:
        commissioned = result.commissioned_by_quarter[quarter.name]
        for state_name, state in states_by_name.items():
            state_result = result.state_results[quarter.name][state_name]
            assert state_result.max_balance_residual_mw <= 1.0e-6
            for branch in two_bus_grid.branches:
                flow = state_result.branch_flows_mw[branch.index]
                if branch.index in state.outaged_branch_indices:
                    assert flow == pytest.approx(0.0, abs=1.0e-9)
                    continue
                rating = branch.rating_mw(state.branch_rating)
                if commissioned:
                    rating += {
                        "rate_a": project.rate_a_increase_mw,
                        "rate_c": project.rate_c_increase_mw,
                    }[state.branch_rating][branch.index]
                assert abs(flow) <= rating + 1.0e-6

    assert abs(
        result.state_results["q1"]["branch_0_sustained"].branch_flows_mw[1]
    ) == pytest.approx(80.0)
    assert abs(
        result.state_results["q1"]["branch_1_sustained"].branch_flows_mw[0]
    ) == pytest.approx(80.0)


def test_connected_capacity_does_not_retreat_when_future_headroom_falls(
    two_bus_grid,
):
    poi_loaded_grid = replace(
        two_bus_grid,
        buses=(
            replace(two_bus_grid.buses[0], demand_mw=0.0),
            replace(two_bus_grid.buses[1], demand_mw=20.0),
        ),
    )
    quarters = (
        PlanningQuarter(
            name="q0",
            system_load_multiplier=0.0,
            data_center_demand_mw=80.0,
            operating_hours=1.0,
            discount_factor=1.0,
        ),
        PlanningQuarter(
            name="q1",
            system_load_multiplier=1.0,
            data_center_demand_mw=80.0,
            operating_hours=1.0,
            discount_factor=1.0,
        ),
    )
    result = _solve(
        poi_loaded_grid,
        quarters=quarters,
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=80.0,
            application_capacity_mw=80.0,
        ),
        project=_upgrade(investment_cost=100_000.0),
    )

    assert result.feasible
    assert not result.project_started
    assert result.connected_capacity_mw == pytest.approx(
        {"q0": 60.0, "q1": 60.0}
    )
    assert result.access_shortfall_mw == pytest.approx(
        {"q0": 20.0, "q1": 20.0}
    )
    assert sum(result.state_results["q0"]["base"].generation_mw.values()) == (
        pytest.approx(60.0)
    )
    assert sum(result.state_results["q1"]["base"].generation_mw.values()) == (
        pytest.approx(80.0)
    )


def test_native_system_load_shortage_is_infeasible(two_bus_grid):
    insufficient_grid = replace(
        two_bus_grid,
        generators=(replace(two_bus_grid.generators[0], p_max_mw=10.0),),
    )
    result = _solve(
        insufficient_grid,
        quarters=_quarters((0.0,)),
        poi=FixedPoi(bus=2, initial_capacity_mw=0.0, application_capacity_mw=0.0),
        project=_upgrade(investment_cost=100.0),
    )

    assert not result.feasible
    assert result.objective is None
    assert result.termination_condition == "all_enumerated_candidates_infeasible"
    assert len(result.candidate_diagnostics) == 2
    assert all(row["resolved"] for row in result.candidate_diagnostics)
    assert all(not row["feasible"] for row in result.candidate_diagnostics)


def test_investment_cost_is_discounted_in_the_project_start_quarter(two_bus_grid):
    quarters = (
        PlanningQuarter(
            name="q0",
            system_load_multiplier=1.0,
            data_center_demand_mw=0.0,
            operating_hours=1.0,
            discount_factor=1.0,
        ),
        PlanningQuarter(
            name="q1",
            system_load_multiplier=1.0,
            data_center_demand_mw=0.0,
            operating_hours=1.0,
            discount_factor=0.5,
        ),
        PlanningQuarter(
            name="q2",
            system_load_multiplier=1.0,
            data_center_demand_mw=80.0,
            operating_hours=1.0,
            discount_factor=0.25,
        ),
    )
    result = _solve(
        two_bus_grid,
        quarters=quarters,
        poi=FixedPoi(
            bus=2,
            initial_capacity_mw=40.0,
            application_capacity_mw=80.0,
        ),
        project=_upgrade(lead_time_quarters=1, investment_cost=1_000.0),
    )

    assert result.feasible
    assert result.project_started
    assert result.start_quarter == "q1"
    assert result.commissioned_by_quarter == {
        "q0": False,
        "q1": False,
        "q2": True,
    }
    assert result.investment_cost == pytest.approx(500.0)
    assert result.connected_capacity_mw == pytest.approx(
        {"q0": 0.0, "q1": 0.0, "q2": 80.0}
    )
    # Discounted operating cost is 200 + 100 + 250; access shortfall is zero.
    assert result.objective == pytest.approx(1_050.0)
    assert [row["start_quarter"] for row in result.candidate_diagnostics] == [
        None,
        "q0",
        "q1",
        "q2",
    ]
    assert result.candidate_diagnostics[2]["selected"]
    late_start = result.candidate_diagnostics[3]
    assert late_start["commissioned_by_quarter"] == {
        "q0": False,
        "q1": False,
        "q2": False,
    }
    assert late_start["objective"] == pytest.approx(10_700.0)


def test_security_states_enforce_fixed_and_bounded_generator_response():
    data = Rts24Data(
        base_mva=100.0,
        buses=(
            Bus(index=1, demand_mw=0.0),
            Bus(index=2, demand_mw=100.0),
        ),
        generators=(
            Generator(
                index=0,
                bus=1,
                p_min_mw=0.0,
                p_max_mw=20.0,
                cost_quadratic=0.0,
                cost_linear=10.0,
                cost_constant=0.0,
                ramp_10_mw=None,
                ramp_30_mw=None,
                in_service=True,
            ),
            Generator(
                index=1,
                bus=1,
                p_min_mw=0.0,
                p_max_mw=100.0,
                cost_quadratic=0.0,
                cost_linear=20.0,
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
                rate_a_mw=100.0,
                rate_b_mw=100.0,
                rate_c_mw=100.0,
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
    redispatch = {0: 20.0, 1: 20.0}
    result = _solve(
        data,
        quarters=_quarters((0.0,)),
        poi=FixedPoi(bus=2, initial_capacity_mw=0.0, application_capacity_mw=0.0),
        project=_upgrade(investment_cost=100.0),
        branch_indices=(0,),
        generator_indices=(0,),
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
    )

    assert result.feasible
    assert {state.name for state in result.states} == {
        "base",
        "branch_0_immediate",
        "branch_0_sustained",
        "generator_0_sustained",
    }
    states = result.state_results["q0"]
    base = states["base"]
    immediate = states["branch_0_immediate"]
    sustained = states["branch_0_sustained"]
    generator_outage = states["generator_0_sustained"]

    assert base.generation_mw == pytest.approx({0: 20.0, 1: 80.0})
    for generator_index in base.generation_mw:
        assert immediate.generation_mw[generator_index] == pytest.approx(
            base.generation_mw[generator_index]
        )
        assert abs(
            sustained.generation_mw[generator_index]
            - base.generation_mw[generator_index]
        ) <= redispatch[generator_index] + 1.0e-6

    assert generator_outage.generation_mw[0] == pytest.approx(0.0)
    assert abs(
        generator_outage.generation_mw[1] - base.generation_mw[1]
    ) <= redispatch[1] + 1.0e-6
    assert generator_outage.generation_mw[1] == pytest.approx(100.0)
    for state in states.values():
        assert state.max_balance_residual_mw <= 1.0e-6
    assert immediate.branch_flows_mw[0] == pytest.approx(0.0, abs=1.0e-9)
    assert sustained.branch_flows_mw[0] == pytest.approx(0.0, abs=1.0e-9)
    assert abs(immediate.branch_flows_mw[1]) <= 100.0 + 1.0e-6
    assert abs(sustained.branch_flows_mw[1]) <= 100.0 + 1.0e-6
