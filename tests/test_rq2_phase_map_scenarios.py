"""Tests for phase-map chronology and recovery CFE accounting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.scenarios.rq2_phase_map import (
    PhaseMapScenarioConfig,
    generate_phase_map_scenarios,
)
from src.scenarios.rts_gmlc_cfe_deficit import (
    RtsGmlcCfeDeficitPoint,
    RtsGmlcCfeDeficitProfile,
    derive_cfe_operating_limit,
)
from src.scenarios.trace_scenario_generator import TraceShape


def _point(index: int, share: float) -> RtsGmlcCfeDeficitPoint:
    demand = 100.0
    return RtsGmlcCfeDeficitPoint(
        timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(hours=index),
        system_load_mw=100.0,
        renewable_available_mw=100.0 * share,
        renewable_share=share,
        dc_demand_mw=demand,
        hourly_cfe_target=1.0,
        attributed_cfe_mw=share * demand,
        cfe_deficit_mw=(1.0 - share) * demand,
        green_call_mw=(1.0 - share) * demand,
    )


def _config() -> PhaseMapScenarioConfig:
    values = tuple(index / 20 for index in range(20))
    return PhaseMapScenarioConfig(
        grid_stress_shape=TraceShape(
            name="grid",
            values=values,
            source="synthetic",
            normalization_peak=1.0,
            normalization_split_fraction=0.5,
        ),
        cfe_profile=RtsGmlcCfeDeficitProfile(
            points=tuple(
                _point(index, 0.4 if index % 2 else 0.8) for index in range(20)
            ),
            source="synthetic",
        ),
        hourly_cfe_target=0.5,
        data_center_demand_mw=100.0,
        system_load_multiplier=0.8,
        network_activation_threshold=0.3,
        business_recovery_headroom_mw=80.0,
        core_window_hours=2,
        recovery_tail_hours=2,
        n_train=2,
        n_holdout=2,
        seed=7,
        period="q1",
    )


def test_cfe_operating_limit_closes_recovery_accounting():
    scarce = derive_cfe_operating_limit(
        _point(0, 0.4),
        hourly_cfe_target=0.5,
        business_recovery_headroom_mw=80.0,
    )
    surplus = derive_cfe_operating_limit(
        _point(1, 0.8),
        hourly_cfe_target=0.5,
        business_recovery_headroom_mw=80.0,
    )

    assert scarce.green_call_mw == pytest.approx(20.0)
    assert scarce.effective_recovery_headroom_mw == pytest.approx(0.0)
    assert surplus.green_call_mw == pytest.approx(0.0)
    assert surplus.cfe_compatible_recovery_headroom_mw == pytest.approx(60.0)
    assert surplus.effective_recovery_headroom_mw == pytest.approx(60.0)


def test_phase_scenarios_use_cfe_data_during_recovery_tail():
    generated = generate_phase_map_scenarios(_config())

    assert len(generated.training_scenarios) == 2
    assert len(generated.holdout_scenarios) == 2
    for scenario in (
        *generated.training_scenarios,
        *generated.holdout_scenarios,
    ):
        assert len(scenario.green_call_mw) == 4
        assert len(scenario.recovery_headroom_mw) == 4
        assert scenario.network_call_active[2:] == (0, 0)
        assert all(
            call == pytest.approx(0.0) or headroom == pytest.approx(0.0)
            for call, headroom in zip(
                scenario.green_call_mw,
                scenario.recovery_headroom_mw,
                strict=True,
            )
        )


def test_train_and_holdout_windows_are_source_disjoint():
    provenance = generate_phase_map_scenarios(_config()).provenance
    split = provenance["split_indices"]
    windows = provenance["windows"]

    assert max(end for _, end in windows["training"]["grid"]) <= split["grid"]
    assert min(start for start, _ in windows["holdout"]["grid"]) >= split["grid"]
    assert max(end for _, end in windows["training"]["cfe"]) <= split["cfe"]
    assert min(start for start, _ in windows["holdout"]["cfe"]) >= split["cfe"]
