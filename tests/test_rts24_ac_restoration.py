import pytest

from src.grid import load_rts24, restore_ac_feasibility, solve_dc_opf


@pytest.fixture(scope="module")
def rts24():
    return load_rts24()


@pytest.fixture(scope="module")
def base_dc(rts24):
    return solve_dc_opf(rts24)


@pytest.fixture(scope="module")
def base_ac(rts24, base_dc):
    return restore_ac_feasibility(rts24, base_dc)


def test_base_ac_restoration_accounts_for_losses(rts24, base_ac):
    assert base_ac.converged
    assert base_ac.secure
    assert base_ac.ac_losses_mw > 40.0
    assert base_ac.max_target_deviation_mw < 5.0
    assert min(base_ac.bus_voltage_pu.values()) >= 0.95


def test_branch_6_is_ac_feasible_after_minimum_deviation_restoration(
    rts24,
    base_dc,
    base_ac,
):
    zero_limits = {generator.index: 0.0 for generator in rts24.generators}
    immediate_dc = solve_dc_opf(
        rts24,
        outaged_branch_indices=(6,),
        branch_rating="rate_c",
        reference_generation_mw=base_dc.generation_mw,
        redispatch_up_mw=zero_limits,
        redispatch_down_mw=zero_limits,
    )
    limits = {
        generator.index: 0.10 * generator.p_max_mw
        for generator in rts24.generators
    }
    restored = restore_ac_feasibility(
        rts24,
        immediate_dc,
        reference_generation_mw=base_ac.generation_mw,
        redispatch_up_mw=limits,
        redispatch_down_mw=limits,
    )
    assert restored.converged
    assert restored.secure
    assert min(restored.bus_voltage_pu.values()) >= 0.95
    assert restored.max_reactive_power_violation_mvar <= 1.0e-5
    for generator in rts24.generators:
        assert abs(
            restored.generation_mw[generator.index]
            - base_ac.generation_mw[generator.index]
        ) <= limits[generator.index] + 1.0e-4


@pytest.mark.parametrize(
    ("outaged_branch", "action"),
    (
        (4, {"branch_rating_overrides_mva": {9: 255.0}}),
        (9, {"shunt_injections_mvar": {6: 140.0}}),
        (26, {"corrective_open_branch_indices": (6,)}),
    ),
)
def test_provisional_branch_remedies_restore_ac_feasibility(
    rts24,
    outaged_branch,
    action,
):
    dc_result = solve_dc_opf(rts24, outaged_branch_indices=(outaged_branch,))
    restored = restore_ac_feasibility(rts24, dc_result, **action)
    assert restored.converged
    assert restored.secure
    assert min(restored.bus_voltage_pu.values()) >= 0.95
