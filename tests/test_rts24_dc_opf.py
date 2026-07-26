from dataclasses import replace

import pytest

from src.grid import (
    load_rts24,
    scale_rts24_demand,
    screen_n_minus_one,
    solve_dc_opf,
    validate_ac_power_flow,
)


@pytest.fixture(scope="module")
def rts24():
    return load_rts24()


@pytest.fixture(scope="module")
def base_result(rts24):
    return solve_dc_opf(rts24)


@pytest.fixture(scope="module")
def all_branch_outcomes(rts24):
    return screen_n_minus_one(rts24)


def test_rts24_source_shape_and_demand(rts24):
    assert rts24.source_package == "pypower"
    assert len(rts24.buses) == 24
    assert len(rts24.generators) == 33
    assert len(rts24.branches) == 38
    assert rts24.total_demand_mw == pytest.approx(2850.0)
    assert rts24.branches[0].rate_a_mw == pytest.approx(175.0)
    assert rts24.branches[0].rate_b_mw == pytest.approx(250.0)
    assert rts24.branches[0].rate_c_mw == pytest.approx(200.0)
    assert all(generator.ramp_10_mw is None for generator in rts24.generators)


def test_scale_rts24_demand_returns_scaled_copy(rts24):
    scaled = scale_rts24_demand(rts24, 0.5)

    assert scaled is not rts24
    assert scaled.total_demand_mw == pytest.approx(1425.0)
    assert rts24.total_demand_mw == pytest.approx(2850.0)
    assert scaled.generators is rts24.generators
    assert scaled.branches is rts24.branches
    for original_bus, scaled_bus in zip(rts24.buses, scaled.buses):
        assert scaled_bus.demand_mw == pytest.approx(0.5 * original_bus.demand_mw)


@pytest.mark.parametrize("multiplier", [-0.01, float("nan"), float("inf"), -float("inf")])
def test_scale_rts24_demand_rejects_invalid_multiplier(rts24, multiplier):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        scale_rts24_demand(rts24, multiplier)


def test_base_dc_opf_matches_pypower_reference(rts24, base_result):
    # PYPOWER 5.1.19 rundcopf(case24_ieee_rts()) reference.
    assert base_result.feasible
    assert base_result.termination_condition == "optimal"
    assert base_result.objective == pytest.approx(61001.2403127059, abs=1.0e-3)
    assert sum(base_result.generation_mw.values()) == pytest.approx(
        rts24.total_demand_mw,
        abs=1.0e-6,
    )
    assert max(abs(flow) for flow in base_result.branch_flows_mw.values()) == (
        pytest.approx(366.1228620124, abs=1.0e-3)
    )


def test_base_dc_opf_respects_balance_and_thermal_limits(rts24, base_result):
    assert base_result.max_balance_residual_mw <= 1.0e-6
    for branch in rts24.branches:
        assert abs(base_result.branch_flows_mw[branch.index]) <= (
            branch.rate_a_mw + 1.0e-6
        )


def test_branch_screen_rejects_unplanned_islanding(
    rts24,
    all_branch_outcomes,
):
    assert len(all_branch_outcomes) == 38
    for outcome in all_branch_outcomes:
        if outcome.outaged_branch_index == 10:
            assert not outcome.result.feasible
            assert outcome.result.termination_condition == "islanding"
        else:
            assert outcome.result.feasible
            assert abs(
                outcome.result.branch_flows_mw[outcome.outaged_branch_index]
            ) <= 1.0e-9
            assert outcome.result.max_balance_residual_mw <= 1.0e-6
            assert outcome.max_loading_fraction <= 1.0 + 1.0e-9

    bridge_outage = all_branch_outcomes[10]
    assert bridge_outage.outaged_branch_index == 10
    assert sum(
        len(outcome.result.reference_buses) > 1
        for outcome in all_branch_outcomes
    ) == 1
    assert len(bridge_outage.result.reference_buses) == 2
    assert set(bridge_outage.result.reference_buses) == {7, 13}

    intentional_island = solve_dc_opf(
        rts24,
        outaged_branch_indices=(10,),
        allow_islanding=True,
    )
    assert intentional_island.feasible
    assert intentional_island.branch_flows_mw[10] == pytest.approx(0.0)


def test_explicit_redispatch_limits_are_enforced(rts24, base_result):
    limit_fraction = 0.05
    limits = {
        generator.index: limit_fraction * generator.p_max_mw
        for generator in rts24.generators
    }
    result = solve_dc_opf(
        rts24,
        outaged_branch_indices=(6,),
        reference_generation_mw=base_result.generation_mw,
        redispatch_up_mw=limits,
        redispatch_down_mw=limits,
    )
    assert result.feasible
    for generator in rts24.generators:
        assert abs(
            result.generation_mw[generator.index]
            - base_result.generation_mw[generator.index]
        ) <= limits[generator.index] + 1.0e-6


def test_generator_outage_requires_corrective_capability(rts24, base_result):
    zero_limits = {generator.index: 0.0 for generator in rts24.generators}
    no_response = solve_dc_opf(
        rts24,
        outaged_generator_indices=(22,),
        reference_generation_mw=base_result.generation_mw,
        redispatch_up_mw=zero_limits,
        redispatch_down_mw=zero_limits,
    )
    assert not no_response.feasible

    full_range = {
        generator.index: generator.p_max_mw for generator in rts24.generators
    }
    for generator_index in (22, 32):
        upper_bound = solve_dc_opf(
            rts24,
            outaged_generator_indices=(generator_index,),
            reference_generation_mw=base_result.generation_mw,
            redispatch_up_mw=full_range,
            redispatch_down_mw=full_range,
        )
        assert upper_bound.feasible
        assert upper_bound.generation_mw[generator_index] == pytest.approx(0.0)


def test_base_dc_dispatch_passes_ac_validation(rts24, base_result):
    ac_result = validate_ac_power_flow(rts24, base_result)
    assert ac_result.converged
    assert ac_result.secure
    assert ac_result.max_branch_loading_fraction <= 1.0
    assert ac_result.max_voltage_violation_pu <= 1.0e-6


def test_ac_validation_detects_branch_6_voltage_and_reactive_violations(
    rts24,
    base_result,
):
    zero_limits = {generator.index: 0.0 for generator in rts24.generators}
    immediate_result = solve_dc_opf(
        rts24,
        outaged_branch_indices=(6,),
        branch_rating="rate_c",
        reference_generation_mw=base_result.generation_mw,
        redispatch_up_mw=zero_limits,
        redispatch_down_mw=zero_limits,
    )
    ac_result = validate_ac_power_flow(
        rts24,
        immediate_result,
        branch_rating="rate_c",
    )
    assert ac_result.converged
    assert not ac_result.secure
    assert ac_result.max_voltage_violation_pu > 0.02
    assert ac_result.max_reactive_power_violation_mvar > 20.0


def test_model_is_infeasible_when_all_generation_is_removed(rts24):
    no_generation = replace(
        rts24,
        generators=tuple(
            replace(generator, p_min_mw=0.0, p_max_mw=0.0)
            for generator in rts24.generators
        ),
    )
    result = solve_dc_opf(no_generation)
    assert not result.feasible
    assert result.termination_condition == "infeasible"
