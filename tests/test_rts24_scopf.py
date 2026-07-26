import pytest

from src.grid import (
    load_rts24,
    non_islanding_branch_indices,
    restore_ac_feasibility,
    scale_rts24_demand,
    solve_security_constrained_dc_opf,
    validate_ac_power_flow,
)


@pytest.fixture(scope="module")
def rts24():
    return load_rts24()


def _limits(data, fraction):
    return {
        generator.index: fraction * generator.p_max_mw
        for generator in data.generators
    }


@pytest.fixture(scope="module")
def minimum_load_unit_selection(rts24):
    data = scale_rts24_demand(rts24, 0.30133597228070175)
    limits = _limits(data, 0.5)
    result = solve_security_constrained_dc_opf(
        data,
        redispatch_up_mw=limits,
        redispatch_down_mw=limits,
        cost_breakpoints=9,
        optimize_unit_selection=True,
    )
    return data, result


def test_contingency_partition_excludes_only_unplanned_island(rts24):
    selected = non_islanding_branch_indices(rts24)
    assert len(selected) == 37
    assert set(range(38)) - set(selected) == {10}


def test_scopf_without_contingencies_matches_base_opf(rts24):
    limits = _limits(rts24, 1.0)
    result = solve_security_constrained_dc_opf(
        rts24,
        redispatch_up_mw=limits,
        redispatch_down_mw=limits,
        branch_indices=(),
        generator_indices=(),
    )
    assert result.feasible
    assert len(result.states) == 1
    assert result.objective == pytest.approx(61001.2403127059, abs=0.1)
    assert result.base_result.max_balance_residual_mw <= 1.0e-6
    assert result.commitment_model == "fixed_online"
    assert result.generator_commitment == {
        generator.index: generator.in_service and generator.p_max_mw > 0.0
        for generator in rts24.generators
    }


def test_scopf_couples_immediate_and_corrective_states(rts24):
    limits = _limits(rts24, 1.0)
    result = solve_security_constrained_dc_opf(
        rts24,
        redispatch_up_mw=limits,
        redispatch_down_mw=limits,
        branch_indices=(6,),
        generator_indices=(22,),
    )
    assert result.feasible
    assert len(result.states) == 4
    base = result.state_results["base"]
    immediate = result.state_results["branch_6_immediate"]
    sustained = result.state_results["branch_6_sustained"]
    generator_outage = result.state_results["generator_22_sustained"]

    assert immediate.branch_rating == "rate_c"
    assert sustained.branch_rating == "rate_a"
    assert immediate.branch_flows_mw[6] == pytest.approx(0.0)
    assert sustained.branch_flows_mw[6] == pytest.approx(0.0)
    assert generator_outage.generation_mw[22] == pytest.approx(0.0)
    for generator in rts24.generators:
        assert immediate.generation_mw[generator.index] == pytest.approx(
            base.generation_mw[generator.index],
            abs=1.0e-6,
        )
        if generator.index != 22:
            assert abs(
                generator_outage.generation_mw[generator.index]
                - base.generation_mw[generator.index]
            ) <= limits[generator.index] + 1.0e-6

    for state in (base, immediate, sustained, generator_outage):
        assert state.max_balance_residual_mw <= 1.0e-6
        for branch in rts24.branches:
            assert abs(state.branch_flows_mw[branch.index]) <= (
                branch.rating_mw(state.branch_rating) + 1.0e-6
            )


def test_scopf_rejects_islanding_branch_from_main_set(rts24):
    limits = _limits(rts24, 1.0)
    with pytest.raises(ValueError, match="islanding branches"):
        solve_security_constrained_dc_opf(
            rts24,
            redispatch_up_mw=limits,
            redispatch_down_mw=limits,
            branch_indices=(10,),
            generator_indices=(),
        )


def test_full_scopf_has_107_states_and_respects_all_outages(rts24):
    limits = _limits(rts24, 1.0)
    result = solve_security_constrained_dc_opf(
        rts24,
        redispatch_up_mw=limits,
        redispatch_down_mw=limits,
    )
    assert result.feasible
    assert len(result.states) == 107
    assert len(result.state_results) == 107
    for state in result.states:
        state_result = result.state_results[state.name]
        assert state_result.max_balance_residual_mw <= 1.0e-6
        for branch_index in state.outaged_branch_indices:
            assert state_result.branch_flows_mw[branch_index] == pytest.approx(0.0)
        for generator_index in state.outaged_generator_indices:
            assert state_result.generation_mw[generator_index] == pytest.approx(0.0)


def test_static_unit_selection_makes_minimum_load_security_feasible(
    minimum_load_unit_selection,
):
    data, result = minimum_load_unit_selection

    assert result.feasible
    assert result.commitment_model == "single_snapshot_static_unit_selection"
    assert len(result.states) == 107
    assert len(result.state_results) == 107
    assert result.excluded_branch_indices == (10,)
    assert result.generator_commitment is not None
    assert set(result.generator_commitment) == {
        generator.index for generator in data.generators
    }
    assert all(
        type(is_committed) is bool
        for is_committed in result.generator_commitment.values()
    )
    assert not result.generator_commitment[14]
    committed = {
        index for index, is_committed in result.generator_commitment.items()
        if is_committed
    }
    assert committed
    assert len(committed) < 32
    assert sum(data.generators[index].p_min_mw for index in committed) <= (
        data.total_demand_mw
    )
    assert sum(data.generators[index].p_max_mw for index in committed) >= (
        data.total_demand_mw
    )

    limits = _limits(data, 0.5)
    base = result.base_result
    for state in result.states:
        state_result = result.state_results[state.name]
        assert sum(state_result.generation_mw.values()) == pytest.approx(
            data.total_demand_mw,
            abs=1.0e-6,
        )
        assert state_result.max_balance_residual_mw <= 1.0e-6
        for generator in data.generators:
            generation = state_result.generation_mw[generator.index]
            if (
                generator.index not in committed
                or generator.index in state.outaged_generator_indices
            ):
                assert generation == pytest.approx(0.0, abs=1.0e-6)
            else:
                assert generation >= generator.p_min_mw - 1.0e-6
                assert generation <= generator.p_max_mw + 1.0e-6
            if state.response_mode == "fixed":
                assert generation == pytest.approx(
                    base.generation_mw[generator.index],
                    abs=1.0e-6,
                )
            elif (
                state.response_mode == "bounded"
                and generator.index not in state.outaged_generator_indices
            ):
                delta = generation - base.generation_mw[generator.index]
                assert delta <= limits[generator.index] + 1.0e-6
                assert -delta <= limits[generator.index] + 1.0e-6

    committed_outage = next(iter(committed))
    assert result.state_results[
        f"generator_{committed_outage}_sustained"
    ].generation_mw[committed_outage] == pytest.approx(0.0)
    uncommitted_outage = next(
        generator.index
        for generator in data.generators
        if generator.p_max_mw > 0.0 and generator.index not in committed
    )
    inactive_outage = result.state_results[
        f"generator_{uncommitted_outage}_sustained"
    ]
    assert inactive_outage.generation_mw == pytest.approx(base.generation_mw)
    assert inactive_outage.objective == pytest.approx(base.objective)
    expected_cost = sum(
        generator.cost_quadratic
        * result.base_result.generation_mw[generator.index] ** 2
        + generator.cost_linear
        * result.base_result.generation_mw[generator.index]
        + generator.cost_constant
        for generator in data.generators
        if generator.index in committed
    )
    assert result.objective == pytest.approx(expected_cost)
    assert result.base_result.objective == pytest.approx(expected_cost)


def test_static_unit_selection_does_not_add_load_shedding(rts24):
    data = scale_rts24_demand(rts24, 3406.0 / rts24.total_demand_mw)
    limits = _limits(data, 1.0)
    result = solve_security_constrained_dc_opf(
        data,
        redispatch_up_mw=limits,
        redispatch_down_mw=limits,
        branch_indices=(),
        generator_indices=(),
        cost_breakpoints=9,
        optimize_unit_selection=True,
    )

    assert not result.feasible
    assert result.objective is None
    assert result.base_result is None
    assert result.state_results == {}
    assert result.generator_commitment is None


def test_minimum_load_commitment_is_mapped_into_ac_models(
    minimum_load_unit_selection,
):
    data, result = minimum_load_unit_selection
    commitment = result.generator_commitment

    power_flow = validate_ac_power_flow(
        data,
        result.base_result,
        generator_commitment=commitment,
    )
    assert power_flow.converged
    assert power_flow.generator_commitment_applied
    assert power_flow.reference_bus != data.reference_bus
    assert 14 in power_flow.active_generator_indices
    assert power_flow.requested_generation_mw == pytest.approx(data.total_demand_mw)
    assert 0.0 < power_flow.slack_and_loss_adjustment_mw < 100.0

    restored = restore_ac_feasibility(
        data,
        result.base_result,
        generator_commitment=commitment,
    )
    assert restored.converged
    assert restored.secure
    assert restored.generator_commitment_applied
    assert restored.reference_bus != data.reference_bus
    assert 14 in restored.active_generator_indices
    assert 0.0 < restored.ac_losses_mw < 100.0
    for generator in data.generators:
        if generator.p_max_mw > 0.0 and not commitment[generator.index]:
            assert restored.generation_mw[generator.index] == pytest.approx(0.0)
            assert restored.reactive_generation_mvar[generator.index] == (
                pytest.approx(0.0)
            )

    committed_large_generator = next(
        generator.index
        for generator in data.generators
        if generator.p_max_mw == 400.0 and commitment[generator.index]
    )
    outage_power_flow = validate_ac_power_flow(
        data,
        result.state_results[
            f"generator_{committed_large_generator}_sustained"
        ],
        generator_commitment=commitment,
    )
    assert outage_power_flow.converged
    assert outage_power_flow.max_active_power_violation_mw <= 1.0e-4
    assert committed_large_generator not in (
        outage_power_flow.active_generator_indices
    )


@pytest.mark.parametrize(
    "ac_function",
    (validate_ac_power_flow, restore_ac_feasibility),
)
def test_ac_models_reject_commitment_without_real_power_generation(
    minimum_load_unit_selection,
    ac_function,
):
    data, result = minimum_load_unit_selection
    no_real_power = {generator.index: False for generator in data.generators}

    with pytest.raises(ValueError, match="active real-power generator"):
        ac_function(
            data,
            result.base_result,
            generator_commitment=no_real_power,
        )
