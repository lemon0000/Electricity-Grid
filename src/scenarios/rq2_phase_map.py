"""Chronological scenario construction for the RQ2 three-region phase map."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

import numpy as np

from .rts_gmlc_cfe_deficit import (
    RtsGmlcCfeDeficitProfile,
    derive_cfe_operating_limit,
)
from .temporal_trace_scenario_generator import TemporalNetworkScenario
from .trace_scenario_generator import TraceShape

PHASE_MAP_SCENARIO_STATUS = (
    "split_aware_google_stress_and_rts_gmlc_cfe_scarcity_independent_"
    "marginals_with_cfe_compatible_recovery_headroom_not_empirical"
)


@dataclass(frozen=True)
class PhaseMapScenarioConfig:
    grid_stress_shape: TraceShape
    cfe_profile: RtsGmlcCfeDeficitProfile
    hourly_cfe_target: float
    data_center_demand_mw: float
    system_load_multiplier: float
    network_activation_threshold: float
    business_recovery_headroom_mw: float
    core_window_hours: int
    recovery_tail_hours: int
    n_train: int
    n_holdout: int
    seed: int
    period: str
    split_fraction: float = 0.5


@dataclass(frozen=True)
class PhaseMapScenarioSet:
    training_scenarios: tuple[TemporalNetworkScenario, ...]
    holdout_scenarios: tuple[TemporalNetworkScenario, ...]
    provenance: dict[str, object]


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _draw(
    rng: np.random.Generator,
    *,
    low: int,
    high: int,
    hours: int,
    count: int,
    label: str,
) -> tuple[tuple[int, int], ...]:
    last = high - hours
    if last < low:
        raise ValueError(f"{label} segment is shorter than the requested window")
    starts = rng.integers(low, last + 1, size=count)
    return tuple((int(start), int(start) + hours) for start in starts)


def _build(
    *,
    prefix: str,
    grid_windows: tuple[tuple[int, int], ...],
    cfe_windows: tuple[tuple[int, int], ...],
    config: PhaseMapScenarioConfig,
) -> tuple[TemporalNetworkScenario, ...]:
    horizon = config.core_window_hours + config.recovery_tail_hours
    probability = 1.0 / len(grid_windows)
    scenarios = []
    for index, (grid_window, cfe_window) in enumerate(
        zip(grid_windows, cfe_windows, strict=True)
    ):
        grid_values = config.grid_stress_shape.values[grid_window[0] : grid_window[1]]
        active = (
            tuple(
                int(value >= config.network_activation_threshold)
                for value in grid_values
            )
            + (0,) * config.recovery_tail_hours
        )
        cfe_points = config.cfe_profile.points[cfe_window[0] : cfe_window[1]]
        limits = tuple(
            derive_cfe_operating_limit(
                point,
                hourly_cfe_target=config.hourly_cfe_target,
                business_recovery_headroom_mw=(config.business_recovery_headroom_mw),
            )
            for point in cfe_points
        )
        scenarios.append(
            TemporalNetworkScenario(
                name=f"{prefix}_{index:03d}",
                probability=probability,
                periods=(config.period,) * horizon,
                system_load_multiplier=(config.system_load_multiplier,) * horizon,
                data_center_demand_mw=(config.data_center_demand_mw,) * horizon,
                network_call_active=active,
                green_call_mw=tuple(item.green_call_mw for item in limits),
                connected_demand_mw=(config.data_center_demand_mw,) * horizon,
                recovery_headroom_mw=tuple(
                    item.effective_recovery_headroom_mw for item in limits
                ),
                completed_periods=frozenset({config.period}),
                require_terminal_event_inactive=True,
                boundary_state_status="clean_boundary_with_zero_carry_in",
            )
        )
    return tuple(scenarios)


def _summary_metrics(
    scenarios: tuple[TemporalNetworkScenario, ...],
    *,
    core_hours: int,
) -> dict[str, float]:
    total_core = len(scenarios) * core_hours
    active = 0
    green = 0
    overlap = 0
    calls = []
    headrooms = []
    for scenario in scenarios:
        for index in range(core_hours):
            is_active = bool(scenario.network_call_active[index])
            has_green = scenario.green_call_mw[index] > 1.0e-9
            active += int(is_active)
            green += int(has_green)
            overlap += int(is_active and has_green)
        calls.extend(scenario.green_call_mw)
        headrooms.extend(scenario.recovery_headroom_mw)
    return {
        "network_activation_rate": active / total_core,
        "green_call_rate": green / total_core,
        "joint_overlap_rate": overlap / total_core,
        "mean_green_call_mw": sum(calls) / len(calls),
        "mean_effective_recovery_headroom_mw": (sum(headrooms) / len(headrooms)),
    }


def generate_phase_map_scenarios(
    config: PhaseMapScenarioConfig,
) -> PhaseMapScenarioSet:
    """Draw split-disjoint windows with CFE-accounted recovery hours."""

    if not 0.0 < config.split_fraction < 1.0:
        raise ValueError("split_fraction must lie strictly in (0, 1)")
    if not 0.0 < config.hourly_cfe_target <= 1.0:
        raise ValueError("hourly_cfe_target must lie in (0, 1]")
    if config.data_center_demand_mw <= 0.0:
        raise ValueError("data_center_demand_mw must be positive")
    if config.business_recovery_headroom_mw < 0.0:
        raise ValueError("business_recovery_headroom_mw must be nonnegative")
    for name in (
        "core_window_hours",
        "recovery_tail_hours",
        "n_train",
        "n_holdout",
    ):
        _positive_int(name, getattr(config, name))
    if isinstance(config.seed, bool) or not isinstance(config.seed, Integral):
        raise TypeError("seed must be an integer")
    if not config.period:
        raise ValueError("period must be explicit")
    if any(
        abs(point.dc_demand_mw - config.data_center_demand_mw) > 1.0e-9
        for point in config.cfe_profile.points
    ):
        raise ValueError("CFE profile demand does not match scenario demand")
    observed_split = config.grid_stress_shape.normalization_split_fraction
    if (
        observed_split is not None
        and abs(observed_split - config.split_fraction) > 1.0e-12
    ):
        raise ValueError("grid normalization split does not match sampling split")

    grid_split = round(len(config.grid_stress_shape.values) * config.split_fraction)
    cfe_split = round(len(config.cfe_profile.points) * config.split_fraction)
    horizon = config.core_window_hours + config.recovery_tail_hours
    rng = np.random.default_rng(config.seed)
    grid_train = _draw(
        rng,
        low=0,
        high=grid_split,
        hours=config.core_window_hours,
        count=config.n_train,
        label="grid training",
    )
    cfe_train = _draw(
        rng,
        low=0,
        high=cfe_split,
        hours=horizon,
        count=config.n_train,
        label="CFE training",
    )
    grid_holdout = _draw(
        rng,
        low=grid_split,
        high=len(config.grid_stress_shape.values),
        hours=config.core_window_hours,
        count=config.n_holdout,
        label="grid holdout",
    )
    cfe_holdout = _draw(
        rng,
        low=cfe_split,
        high=len(config.cfe_profile.points),
        hours=horizon,
        count=config.n_holdout,
        label="CFE holdout",
    )
    training = _build(
        prefix="phase_train",
        grid_windows=grid_train,
        cfe_windows=cfe_train,
        config=config,
    )
    holdout = _build(
        prefix="phase_holdout",
        grid_windows=grid_holdout,
        cfe_windows=cfe_holdout,
        config=config,
    )
    return PhaseMapScenarioSet(
        training_scenarios=training,
        holdout_scenarios=holdout,
        provenance={
            "parameter_status": PHASE_MAP_SCENARIO_STATUS,
            "seed": int(config.seed),
            "split_fraction": config.split_fraction,
            "split_indices": {"grid": grid_split, "cfe": cfe_split},
            "core_window_hours": config.core_window_hours,
            "recovery_tail_hours": config.recovery_tail_hours,
            "hourly_cfe_target": config.hourly_cfe_target,
            "business_recovery_headroom_mw": (config.business_recovery_headroom_mw),
            "recovery_accounting": (
                "effective_headroom=min(business_headroom,"
                "max(attributed_cfe/alpha_hr-dc_demand,0))"
            ),
            "trace_pairing": (
                "independent_marginal_windows_between_google_stress_and_rts_gmlc_cfe"
            ),
            "windows": {
                "training": {
                    "grid": grid_train,
                    "cfe": cfe_train,
                },
                "holdout": {
                    "grid": grid_holdout,
                    "cfe": cfe_holdout,
                },
            },
            "training_metrics": _summary_metrics(
                training, core_hours=config.core_window_hours
            ),
            "holdout_metrics": _summary_metrics(
                holdout, core_hours=config.core_window_hours
            ),
        },
    )
