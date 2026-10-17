"""Pins for split-aware continuous temporal scenario generation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.scenarios.temporal_trace_scenario_generator import (
    TemporalTraceScenarioConfig,
    generate_temporal_holdout_scenarios,
)
from src.scenarios.trace_scenario_generator import TraceShape

STATUS = "synthetic_temporal_generator_test_not_empirical"


def _shape(name: str, values) -> TraceShape:
    return TraceShape(
        name=name,
        source=f"synthetic::{name}",
        values=tuple(float(value) for value in values),
    )


def _config(**overrides) -> TemporalTraceScenarioConfig:
    values = tuple((index + 1) / 40.0 for index in range(40))
    base = TemporalTraceScenarioConfig(
        grid_stress_shape=_shape("grid", values),
        green_workload_shape=_shape("green", values),
        data_center_demand_mw=80.0,
        system_load_multiplier=1.0,
        green_call_scale_mw=60.0,
        network_activation_threshold=0.35,
        recovery_headroom_mw=100.0,
        core_window_hours=4,
        recovery_tail_hours=2,
        n_train=5,
        n_holdout=4,
        seed=20260823,
        period="q1",
        parameter_status=STATUS,
        split_fraction=0.5,
    )
    return replace(base, **overrides)


def test_generator_preserves_hourly_profiles_and_appends_recovery_tail():
    result = generate_temporal_holdout_scenarios(_config())

    assert len(result.training_scenarios) == 5
    scenario = result.training_scenarios[0]
    assert len(scenario.periods) == 6
    assert scenario.green_call_mw[-2:] == (0.0, 0.0)
    assert scenario.network_call_active[-2:] == (0, 0)
    assert scenario.recovery_headroom_mw[-2:] == (100.0, 100.0)
    assert scenario.completed_periods == frozenset({"q1"})
    assert scenario.require_terminal_event_inactive


def test_hourly_values_equal_the_selected_source_windows():
    config = _config()
    result = generate_temporal_holdout_scenarios(config)
    scenario = result.training_scenarios[0]
    grid_window = result.provenance["windows"]["train"]["grid"][0]
    green_window = result.provenance["windows"]["train"]["green"][0]
    grid_values = config.grid_stress_shape.values[
        grid_window["start"] : grid_window["end"]
    ]
    green_values = config.green_workload_shape.values[
        green_window["start"] : green_window["end"]
    ]

    assert scenario.network_call_active[:4] == tuple(
        int(value >= config.network_activation_threshold)
        for value in grid_values
    )
    assert scenario.green_call_mw[:4] == pytest.approx(
        tuple(config.green_call_scale_mw * value for value in green_values)
    )


def test_train_and_holdout_source_hours_are_disjoint():
    result = generate_temporal_holdout_scenarios(_config())
    for source in ("grid", "green"):
        split = result.provenance["split_index"][source]
        assert all(
            window["end"] <= split
            for window in result.provenance["windows"]["train"][source]
        )
        assert all(
            window["start"] >= split
            for window in result.provenance["windows"]["holdout"][source]
        )


def test_training_trajectories_do_not_depend_on_holdout_values():
    shared_train = tuple((index + 1) / 20.0 for index in range(20))
    calm = shared_train + (0.1,) * 20
    spike = shared_train + (999.0,) * 20
    calm_result = generate_temporal_holdout_scenarios(
        _config(
            grid_stress_shape=_shape("grid", calm),
            green_workload_shape=_shape("green", calm),
        )
    )
    spike_result = generate_temporal_holdout_scenarios(
        _config(
            grid_stress_shape=_shape("grid", spike),
            green_workload_shape=_shape("green", spike),
        )
    )

    def key(result):
        return tuple(
            (scenario.network_call_active, scenario.green_call_mw)
            for scenario in result.training_scenarios
        )

    assert key(calm_result) == key(spike_result)
    assert (
        calm_result.holdout_scenarios[0].green_call_mw
        != spike_result.holdout_scenarios[0].green_call_mw
    )


def test_seed_is_reproducible_and_changes_draw():
    first = generate_temporal_holdout_scenarios(_config(seed=7))
    second = generate_temporal_holdout_scenarios(_config(seed=7))
    third = generate_temporal_holdout_scenarios(_config(seed=8))

    assert first == second
    assert first.provenance["windows"] != third.provenance["windows"]


def test_normalization_split_must_match_sampling_split():
    raw = tuple((index + 1) / 40.0 for index in range(40))
    shape = TraceShape.peak_normalized(
        name="shape",
        source="synthetic",
        raw_values=raw,
        split_fraction=0.5,
    )
    with pytest.raises(ValueError, match="split_fraction"):
        generate_temporal_holdout_scenarios(
            _config(
                grid_stress_shape=shape,
                green_workload_shape=shape,
                split_fraction=0.6,
            )
        )


def test_status_and_provenance_do_not_claim_empirical_outage_or_recovery():
    result = generate_temporal_holdout_scenarios(_config())

    assert "not_empirical" in result.parameter_status
    assert result.provenance["network_activation_semantics"] == (
        "trace_threshold_stress_indicator_not_observed_outage_timing"
    )
    assert result.provenance["recovery_headroom_semantics"] == (
        "synthetic_constant_sensitivity_not_observed_recovery"
    )
    assert result.provenance["trace_pairing"] == (
        "independent_marginal_windows_from_different_clusters"
    )


def test_invalid_threshold_or_tail_fails_closed():
    with pytest.raises(ValueError, match="network_activation_threshold"):
        generate_temporal_holdout_scenarios(
            _config(network_activation_threshold=-0.1)
        )
    with pytest.raises(ValueError, match="recovery_tail_hours"):
        generate_temporal_holdout_scenarios(_config(recovery_tail_hours=0))
