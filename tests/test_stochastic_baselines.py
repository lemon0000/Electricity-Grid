from dataclasses import replace
from pathlib import Path

import pytest

import src.models.stochastic_baselines as stochastic_model
from src.grid import Branch, Bus, Generator, Rts24Data
from src.models import (
    ExistingBranchUpgrade,
    FixedPoi,
    FxQuarter,
    FxServiceEnvelope,
    StochasticBaselineEndpoint,
    StochasticBaselinePolicy,
    solve_stochastic_baseline,
)
from src.scenarios import (
    FrozenScenarioTree,
    PlanningPolicy,
    QuarterDecisionGroups,
    ScenarioLeaf,
    ScenarioNode,
    load_frozen_scenario_tree,
)


PARAMETER_STATUS = "synthetic_test_only_not_for_engineering"
RESPONSE_MODEL = "mw_only_sustained_states_no_duration_or_energy_limits"
QUARTERS = ("q1", "q2", "q3", "q4")


@pytest.fixture(scope="module")
def frozen_tree():
    return load_frozen_scenario_tree(
        Path(__file__).resolve().parents[1]
        / "configs"
        / "rts24_stochastic_baselines.yaml"
    )


@pytest.fixture(scope="module")
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


def _quarters():
    return tuple(
        FxQuarter(
            name=name,
            system_load_multiplier=1.0,
            data_center_demand_mw=0.0,
            operating_hours=1.0,
            continuous_validation_hours=0.0,
            discount_factor=1.0,
        )
        for name in QUARTERS
    )


def _poi():
    return FixedPoi(
        bus=2,
        initial_capacity_mw=40.0,
        application_capacity_mw=80.0,
    )


def _project():
    return ExistingBranchUpgrade(
        name="two_line_corridor_upgrade",
        lead_time_quarters=2,
        rate_a_increase_mw={0: 40.0, 1: 40.0},
        rate_c_increase_mw={0: 0.0, 1: 0.0},
        poi_capacity_increase_mw=40.0,
        investment_cost=100.0,
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


def _solve(data, tree, policy):
    redispatch = {
        generator.index: generator.p_max_mw for generator in data.generators
    }
    return solve_stochastic_baseline(
        data,
        policy=policy,
        tree=tree,
        quarters=_quarters(),
        poi=_poi(),
        project=_project(),
        service_envelope=_service_envelope(),
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
        branch_indices=(0, 1),
        generator_indices=(),
        immediate_rating="rate_c",
        sustained_rating="rate_a",
        solver_name="highs",
    )


@pytest.fixture(scope="module")
def policy_results(two_line_grid, frozen_tree):
    return {
        policy: _solve(two_line_grid, frozen_tree, policy)
        for policy in StochasticBaselinePolicy
    }


def _endpoint(result):
    assert result.feasible, result.solver_message
    assert isinstance(result.displayed_endpoint, StochasticBaselineEndpoint)
    return result.displayed_endpoint


def test_multistage_information_cannot_worsen_expected_shortfall(policy_results):
    b3 = policy_results[StochasticBaselinePolicy.B3]
    b4 = policy_results[StochasticBaselinePolicy.B4]
    b5 = policy_results[StochasticBaselinePolicy.B5]

    assert b5.primary_access_shortfall_mwh <= (
        b4.primary_access_shortfall_mwh + 1.0e-8
    )
    assert b4.primary_access_shortfall_mwh <= (
        b3.primary_access_shortfall_mwh + 1.0e-8
    )
    assert b4.primary_access_shortfall_mwh < b3.primary_access_shortfall_mwh


@pytest.mark.parametrize("policy", tuple(StochasticBaselinePolicy))
def test_planning_decisions_are_shared_exactly_within_frozen_groups(
    policy_results,
    frozen_tree,
    policy,
):
    endpoint = _endpoint(policy_results[policy])
    for quarter in QUARTERS:
        for group in frozen_tree.decision_groups(policy.value, quarter):
            reference = group[0]
            for leaf in group[1:]:
                assert endpoint.firm_capacity_mw[leaf][quarter] == pytest.approx(
                    endpoint.firm_capacity_mw[reference][quarter]
                )
                assert endpoint.conditional_capacity_mw[leaf][
                    quarter
                ] == pytest.approx(
                    endpoint.conditional_capacity_mw[reference][quarter]
                )
                assert endpoint.project_start_by_quarter[leaf][quarter] is (
                    endpoint.project_start_by_quarter[reference][quarter]
                )


def test_project_availability_is_path_state_not_shared_planning_decision(
    policy_results,
):
    endpoint = _endpoint(policy_results[StochasticBaselinePolicy.B4])
    on_time = "baseline_upper__on_time"
    delayed = "baseline_upper__delayed_one_quarter"

    assert endpoint.project_start_by_quarter[on_time]["q1"]
    assert endpoint.project_start_by_quarter[delayed]["q1"]
    assert endpoint.project_available_by_quarter[on_time]["q3"]
    assert not endpoint.project_available_by_quarter[delayed]["q3"]
    assert endpoint.project_available_by_quarter[delayed]["q4"]


@pytest.mark.parametrize("policy", tuple(StochasticBaselinePolicy))
def test_connected_and_firm_demand_use_exact_minimum_relations(
    policy_results,
    frozen_tree,
    policy,
):
    endpoint = _endpoint(policy_results[policy])
    demand_by_name = {state.name: state for state in frozen_tree.demand_states}
    leaf_by_name = {leaf.name: leaf for leaf in frozen_tree.leaves}
    for leaf in frozen_tree.leaf_names:
        demand_path = demand_by_name[leaf_by_name[leaf].demand_state].demand_mw
        for quarter, demand in zip(QUARTERS, demand_path):
            assert endpoint.connected_demand_mw[leaf][quarter] == pytest.approx(
                min(demand, endpoint.total_capacity_mw[leaf][quarter])
            )
            assert endpoint.firm_demand_mw[leaf][quarter] == pytest.approx(
                min(demand, endpoint.firm_capacity_mw[leaf][quarter])
            )
            assert endpoint.access_shortfall_mw[leaf][quarter] == pytest.approx(
                demand - endpoint.connected_demand_mw[leaf][quarter]
            )


@pytest.mark.parametrize("policy", tuple(StochasticBaselinePolicy))
def test_capacity_and_project_state_are_pathwise_irreversible(
    policy_results,
    frozen_tree,
    policy,
):
    endpoint = _endpoint(policy_results[policy])
    for leaf in frozen_tree.leaf_names:
        firm = [endpoint.firm_capacity_mw[leaf][quarter] for quarter in QUARTERS]
        total = [endpoint.total_capacity_mw[leaf][quarter] for quarter in QUARTERS]
        available = [
            endpoint.project_available_by_quarter[leaf][quarter]
            for quarter in QUARTERS
        ]
        assert firm == sorted(firm)
        assert total == sorted(total)
        assert available == sorted(available)
        assert sum(endpoint.project_start_by_quarter[leaf].values()) <= 1


@pytest.mark.parametrize("policy", tuple(StochasticBaselinePolicy))
def test_total_contract_and_x_exposures_are_reported_as_sets(
    policy_results,
    policy,
):
    result = policy_results[policy]
    assert result.minimum_contract_exposure_mwh <= (
        result.maximum_contract_exposure_mwh + 1.0e-8
    )
    assert result.minimum_x_exposure_mwh <= (
        result.maximum_x_exposure_mwh + 1.0e-8
    )
    assert result.displayed_endpoint is result.minimum_x_endpoint
    assert result.minimum_x_endpoint.contract_capacity_exposure_mwh == (
        pytest.approx(result.minimum_contract_exposure_mwh)
    )
    assert len(result.stage_diagnostics) == 13


def test_unpriced_contract_rights_have_a_nontrivial_exposure_interval(
    two_line_grid,
    frozen_tree,
):
    tree = _single_leaf_tree(frozen_tree)
    low_demand = replace(
        tree.demand_states[0],
        demand_mw=(20.0, 20.0, 20.0, 20.0),
    )
    tree = replace(tree, demand_states=(low_demand,))
    result = _solve(two_line_grid, tree, StochasticBaselinePolicy.B3)

    assert result.maximum_contract_exposure_mwh > (
        result.minimum_contract_exposure_mwh + 1.0e-6
    )


@pytest.mark.parametrize("policy", tuple(StochasticBaselinePolicy))
def test_embedded_actual_and_contract_network_layers_close(policy_results, policy):
    result = policy_results[policy]
    endpoint = _endpoint(result)

    operation_count = (
        12 * 4
        if policy is StochasticBaselinePolicy.B5
        else sum(result.natural_node_counts.values())
    )
    assert result.embedded_state_rows == operation_count * 2 * len(result.states)
    assert endpoint.maximum_original_constraint_violation <= 1.0e-6
    assert endpoint.maximum_integrality_violation <= 1.0e-6
    assert all(stage.accepted for stage in result.stage_diagnostics)


def test_b5_is_retained_only_as_unimplementable_bound(policy_results):
    result = policy_results[StochasticBaselinePolicy.B5]

    assert result.role == "perfect_information_bound"
    assert not result.implementable


def test_b5_leaf_decomposition_matches_monolithic_lexicographic_faces(
    two_line_grid,
    frozen_tree,
    policy_results,
):
    redispatch = {
        generator.index: generator.p_max_mw
        for generator in two_line_grid.generators
    }
    monolithic = stochastic_model._solve_stochastic_baseline_monolithic(
        two_line_grid,
        policy=StochasticBaselinePolicy.B5,
        tree=frozen_tree,
        quarters=_quarters(),
        poi=_poi(),
        project=_project(),
        service_envelope=_service_envelope(),
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
        branch_indices=(0, 1),
        generator_indices=(),
        immediate_rating="rate_c",
        sustained_rating="rate_a",
        solver_name="highs",
    )
    decomposed = policy_results[StochasticBaselinePolicy.B5]

    assert monolithic.feasible
    assert decomposed.feasible
    for field in (
        "primary_access_shortfall_mwh",
        "minimum_contract_exposure_mwh",
        "maximum_contract_exposure_mwh",
        "minimum_x_exposure_mwh",
        "maximum_x_exposure_mwh",
    ):
        assert getattr(decomposed, field) == pytest.approx(
            getattr(monolithic, field), abs=1.0e-6
        )
    assert len(decomposed.stage_diagnostics) == len(
        monolithic.stage_diagnostics
    )
    assert all(stage.accepted for stage in decomposed.stage_diagnostics)


def _single_leaf_tree(tree):
    demand = next(state for state in tree.demand_states if state.name == "baseline_upper")
    project = next(state for state in tree.project_states if state.name == "on_time")
    leaf_name = "only_leaf"
    nodes = tuple(
        ScenarioNode(
            name=f"only_{quarter}",
            quarter=quarter,
            parent=None if position == 0 else f"only_{QUARTERS[position - 1]}",
            probability=1.0,
            leaves=(leaf_name,),
        )
        for position, quarter in enumerate(QUARTERS)
    )
    policies = tuple(
        PlanningPolicy(
            name=policy.value,
            role={
                StochasticBaselinePolicy.B3: "two_stage_root_commitment",
                StochasticBaselinePolicy.B4: "multistage_nonanticipative_policy",
                StochasticBaselinePolicy.B5: "perfect_information_bound",
            }[policy],
            implementable=policy is not StochasticBaselinePolicy.B5,
            decision_variables=("F", "X", "z_start"),
            decision_groups=tuple(
                QuarterDecisionGroups(quarter=quarter, groups=((leaf_name,),))
                for quarter in QUARTERS
            ),
        )
        for policy in StochasticBaselinePolicy
    )
    return FrozenScenarioTree(
        id=tree.id,
        parameter_status=tree.parameter_status,
        probability_basis=tree.probability_basis,
        common_input_config=tree.common_input_config,
        common_input_signature_id=tree.common_input_signature_id,
        common_input_signature_schema=tree.common_input_signature_schema,
        common_input_signature_sha256=tree.common_input_signature_sha256,
        objective_hierarchy=tree.objective_hierarchy,
        security_certified=False,
        project_timing=tree.project_timing,
        quarters=tree.quarters,
        q2_signal_reveal_before=tree.q2_signal_reveal_before,
        project_state_reveal_before=tree.project_state_reveal_before,
        terminal_outcome_reveal_before=tree.terminal_outcome_reveal_before,
        demand_states=(replace(demand, probability=1.0),),
        project_states=(replace(project, probability=1.0),),
        leaves=(
            ScenarioLeaf(
                name=leaf_name,
                demand_state=demand.name,
                project_state=project.name,
                probability=1.0,
            ),
        ),
        nodes=nodes,
        policies=policies,
    )


def test_single_leaf_reduction_makes_b3_b4_b5_identical(
    two_line_grid,
    frozen_tree,
):
    tree = _single_leaf_tree(frozen_tree)
    results = [_solve(two_line_grid, tree, policy) for policy in StochasticBaselinePolicy]
    reference = results[0]
    for result in results[1:]:
        assert result.primary_access_shortfall_mwh == pytest.approx(
            reference.primary_access_shortfall_mwh
        )
        assert result.minimum_contract_exposure_mwh == pytest.approx(
            reference.minimum_contract_exposure_mwh
        )
        assert result.maximum_contract_exposure_mwh == pytest.approx(
            reference.maximum_contract_exposure_mwh
        )
        assert result.minimum_x_exposure_mwh == pytest.approx(
            reference.minimum_x_exposure_mwh
        )
        assert result.maximum_x_exposure_mwh == pytest.approx(
            reference.maximum_x_exposure_mwh
        )


def _rename_leaves(tree):
    mapping = {
        leaf.name: f"permuted_{position}"
        for position, leaf in enumerate(reversed(tree.leaves))
    }
    return replace(
        tree,
        leaves=tuple(replace(leaf, name=mapping[leaf.name]) for leaf in tree.leaves),
        nodes=tuple(
            replace(node, leaves=tuple(mapping[name] for name in node.leaves))
            for node in tree.nodes
        ),
        policies=tuple(
            replace(
                policy,
                decision_groups=tuple(
                    replace(
                        quarter,
                        groups=tuple(
                            tuple(mapping[name] for name in group)
                            for group in quarter.groups
                        ),
                    )
                    for quarter in policy.decision_groups
                ),
            )
            for policy in tree.policies
        ),
    )


def test_leaf_label_permutation_does_not_change_objective(
    two_line_grid,
    frozen_tree,
    policy_results,
):
    permuted = _solve(
        two_line_grid,
        _rename_leaves(frozen_tree),
        StochasticBaselinePolicy.B4,
    )
    reference = policy_results[StochasticBaselinePolicy.B4]

    assert permuted.primary_access_shortfall_mwh == pytest.approx(
        reference.primary_access_shortfall_mwh
    )
    assert permuted.minimum_contract_exposure_mwh == pytest.approx(
        reference.minimum_contract_exposure_mwh
    )
    assert permuted.maximum_x_exposure_mwh == pytest.approx(
        reference.maximum_x_exposure_mwh
    )
