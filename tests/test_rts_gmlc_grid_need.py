from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.grid.rts_gmlc_grid_need import derive_hourly_rts_gmlc_grid_need
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent


def _generator(uid: str, maximum: float):
    return SimpleNamespace(
        uid=uid,
        bus=1,
        enabled=True,
        dispatch_mode="committable",
        ramp_mw_per_hour=100.0,
        p_max_mw=maximum,
    )


def _branch(uid: str):
    return SimpleNamespace(
        uid=uid,
        from_bus=1,
        to_bus=2,
        reactance_pu=0.1,
        tap_ratio=1.0,
        continuous_rating_mw=40.0,
    )


def _data(generators):
    return SimpleNamespace(
        base_mva=100.0,
        reference_bus=1,
        buses=(SimpleNamespace(uid=1), SimpleNamespace(uid=2)),
        generators=tuple(generators),
        branches=(_branch("L1"), _branch("L2")),
        dc_branches=(),
    )


def _point(generators, *, native_bus_2_load: float = 0.0):
    return SimpleNamespace(
        demand_by_bus_mw={1: 0.0, 2: native_bus_2_load},
        generator_min_mw={generator.uid: 0.0 for generator in generators},
        generator_max_mw={
            generator.uid: generator.p_max_mw for generator in generators
        },
    )


def test_parallel_line_outage_requires_exact_minimum_curtailment():
    generators = (_generator("G1", 100.0),)
    result = derive_hourly_rts_gmlc_grid_need(
        _data(generators),
        _point(generators),
        {"G1": 80.0},
        {"G1": True},
        N1OutageEvent(1, "line", "branch", "L1", 0, 1),
        source_hour=0,
        dc_bus=2,
        dc_demand_mw=80.0,
    )

    assert result.resolved
    assert not result.proven_infeasible
    assert result.grid_need_mw == pytest.approx(40.0, abs=1.0e-7)
    assert result.maximum_constraint_violation <= 1.0e-7


def test_generator_outage_uses_fixed_commitment_and_capacity():
    generators = (_generator("G1", 60.0), _generator("G2", 50.0))
    result = derive_hourly_rts_gmlc_grid_need(
        _data(generators),
        _point(generators),
        {"G1": 40.0, "G2": 40.0},
        {"G1": True, "G2": True},
        N1OutageEvent(1, "generator", "generator", "G1", 0, 1),
        source_hour=0,
        dc_bus=2,
        dc_demand_mw=80.0,
    )

    assert result.resolved
    assert result.grid_need_mw == pytest.approx(30.0, abs=1.0e-7)


def test_no_outage_has_zero_need_without_solver_call():
    generators = (_generator("G1", 100.0),)
    result = derive_hourly_rts_gmlc_grid_need(
        _data(generators),
        _point(generators),
        {"G1": 80.0},
        {"G1": True},
        None,
        source_hour=0,
        dc_bus=2,
        dc_demand_mw=80.0,
        solver_name="solver_does_not_exist",
    )

    assert result.resolved
    assert result.grid_need_mw == 0.0
    assert result.termination_condition == "not_applicable_no_active_outage"


def test_infeasible_even_after_full_dc_curtailment_is_not_a_grid_need():
    generators = (_generator("G1", 100.0),)
    result = derive_hourly_rts_gmlc_grid_need(
        _data(generators),
        _point(generators, native_bus_2_load=10.0),
        {"G1": 90.0},
        {"G1": True},
        N1OutageEvent(1, "generator", "generator", "G1", 0, 1),
        source_hour=0,
        dc_bus=2,
        dc_demand_mw=80.0,
    )

    assert not result.resolved
    assert result.proven_infeasible
    assert result.grid_need_mw is None
