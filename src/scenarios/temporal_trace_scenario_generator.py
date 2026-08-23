"""Split-aware continuous trace scenarios for temporal RQ2 H2.

The Google trace supplies an hourly stress indicator and the Alibaba trace
supplies an hourly green-shift call. They are sampled as independent marginals
because the sources are different clusters with anonymous relative clocks.
Network activation is a frozen threshold sensitivity, not an observed outage.
Recovery headroom and the appended recovery tail are synthetic sensitivities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from numbers import Integral, Real

import numpy as np

from .trace_scenario_generator import TraceShape

TEMPORAL_TRACE_PARAMETER_STATUS = (
    "continuous_hourly_profiles_derived_from_split_aware_trace_shapes_"
    "network_activation_is_a_threshold_stress_indicator_not_observed_outage_"
    "recovery_tail_and_headroom_are_synthetic_not_empirical_or_contract_evidence"
)


@dataclass(frozen=True)
class TemporalNetworkScenario:
    name: str
    probability: float
    periods: tuple[str, ...]
    system_load_multiplier: tuple[float, ...]
    data_center_demand_mw: tuple[float, ...]
    network_call_active: tuple[int, ...]
    green_call_mw: tuple[float, ...]
    connected_demand_mw: tuple[float, ...]
    recovery_headroom_mw: tuple[float, ...]
    completed_periods: frozenset[str]
    require_terminal_event_inactive: bool
    boundary_state_status: str


@dataclass(frozen=True)
class TemporalTraceScenarioConfig:
    grid_stress_shape: TraceShape
    green_workload_shape: TraceShape
    data_center_demand_mw: float
    system_load_multiplier: float
    green_call_scale_mw: float
    network_activation_threshold: float
    recovery_headroom_mw: float
    core_window_hours: int
    recovery_tail_hours: int
    n_train: int
    n_holdout: int
    seed: int
    period: str
    parameter_status: str
    split_fraction: float = 0.5


@dataclass(frozen=True)
class GeneratedTemporalScenarioSet:
    training_scenarios: tuple[TemporalNetworkScenario, ...]
    holdout_scenarios: tuple[TemporalNetworkScenario, ...]
    parameter_status: str
    provenance: dict = field(default_factory=dict)


def _finite(name: str, raw: object, *, minimum: float = 0.0) -> float:
    if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(raw):
        raise ValueError(f"{name} must be a finite number")
    number = float(raw)
    if number < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return number


def _positive_int(name: str, raw: object) -> int:
    if isinstance(raw, bool) or not isinstance(raw, Integral) or raw < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(raw)


def _split_index(length: int, fraction: float) -> int:
    return round(length * fraction)


def _assert_shape_split(name: str, shape: TraceShape, split: float) -> None:
    observed = shape.normalization_split_fraction
    if observed is not None and abs(observed - split) > 1.0e-12:
        raise ValueError(
            f"{name} normalization split_fraction={observed:g} does not "
            f"match sampling split_fraction={split:g}"
        )


def _draw(
    rng: np.random.Generator,
    *,
    low: int,
    high: int,
    hours: int,
    count: int,
    label: str,
) -> list[tuple[int, int]]:
    last = high - hours
    if last < low:
        raise ValueError(f"{label} segment is shorter than core_window_hours")
    starts = rng.integers(low, last + 1, size=count)
    return [(int(start), int(start) + hours) for start in starts]


def _validate(config: TemporalTraceScenarioConfig) -> None:
    if not config.parameter_status:
        raise ValueError("parameter_status must be explicit")
    if not config.period:
        raise ValueError("period must be explicit")
    _finite("data_center_demand_mw", config.data_center_demand_mw)
    _finite("system_load_multiplier", config.system_load_multiplier)
    _finite("green_call_scale_mw", config.green_call_scale_mw)
    _finite(
        "network_activation_threshold", config.network_activation_threshold
    )
    _finite("recovery_headroom_mw", config.recovery_headroom_mw)
    _positive_int("core_window_hours", config.core_window_hours)
    _positive_int("recovery_tail_hours", config.recovery_tail_hours)
    _positive_int("n_train", config.n_train)
    _positive_int("n_holdout", config.n_holdout)
    if isinstance(config.seed, bool) or not isinstance(config.seed, Integral):
        raise TypeError("seed must be an integer")
    split = _finite("split_fraction", config.split_fraction)
    if not 0.0 < split < 1.0:
        raise ValueError("split_fraction must lie strictly in (0, 1)")
    _assert_shape_split("grid_stress_shape", config.grid_stress_shape, split)
    _assert_shape_split(
        "green_workload_shape", config.green_workload_shape, split
    )


def _build(
    *,
    prefix: str,
    grid_windows: list[tuple[int, int]],
    green_windows: list[tuple[int, int]],
    config: TemporalTraceScenarioConfig,
) -> tuple[TemporalNetworkScenario, ...]:
    probability = 1.0 / len(grid_windows)
    tail = config.recovery_tail_hours
    total = config.core_window_hours + tail
    scenarios = []
    for index, (grid_window, green_window) in enumerate(
        zip(grid_windows, green_windows)
    ):
        grid_values = config.grid_stress_shape.values[
            grid_window[0] : grid_window[1]
        ]
        green_values = config.green_workload_shape.values[
            green_window[0] : green_window[1]
        ]
        active = tuple(
            int(value >= config.network_activation_threshold)
            for value in grid_values
        ) + (0,) * tail
        green = tuple(
            config.green_call_scale_mw * value for value in green_values
        ) + (0.0,) * tail
        scenarios.append(
            TemporalNetworkScenario(
                name=f"{prefix}_{index:03d}",
                probability=probability,
                periods=(config.period,) * total,
                system_load_multiplier=(
                    config.system_load_multiplier,
                )
                * total,
                data_center_demand_mw=(
                    config.data_center_demand_mw,
                )
                * total,
                network_call_active=active,
                green_call_mw=green,
                connected_demand_mw=(
                    config.data_center_demand_mw,
                )
                * total,
                recovery_headroom_mw=(
                    config.recovery_headroom_mw,
                )
                * total,
                completed_periods=frozenset({config.period}),
                require_terminal_event_inactive=True,
                boundary_state_status="clean_boundary_with_zero_carry_in",
            )
        )
    return tuple(scenarios)


def generate_temporal_holdout_scenarios(
    config: TemporalTraceScenarioConfig,
) -> GeneratedTemporalScenarioSet:
    """Draw continuous training/holdout windows with a synthetic recovery tail."""

    _validate(config)
    grid_split = _split_index(
        len(config.grid_stress_shape.values), config.split_fraction
    )
    green_split = _split_index(
        len(config.green_workload_shape.values), config.split_fraction
    )
    rng = np.random.default_rng(config.seed)
    grid_train = _draw(
        rng,
        low=0,
        high=grid_split,
        hours=config.core_window_hours,
        count=config.n_train,
        label="grid train",
    )
    green_train = _draw(
        rng,
        low=0,
        high=green_split,
        hours=config.core_window_hours,
        count=config.n_train,
        label="green train",
    )
    grid_holdout = _draw(
        rng,
        low=grid_split,
        high=len(config.grid_stress_shape.values),
        hours=config.core_window_hours,
        count=config.n_holdout,
        label="grid holdout",
    )
    green_holdout = _draw(
        rng,
        low=green_split,
        high=len(config.green_workload_shape.values),
        hours=config.core_window_hours,
        count=config.n_holdout,
        label="green holdout",
    )
    training = _build(
        prefix="temporal_train",
        grid_windows=grid_train,
        green_windows=green_train,
        config=config,
    )
    holdout = _build(
        prefix="temporal_holdout",
        grid_windows=grid_holdout,
        green_windows=green_holdout,
        config=config,
    )
    provenance = {
        "seed": config.seed,
        "split_fraction": config.split_fraction,
        "split_index": {"grid": grid_split, "green": green_split},
        "core_window_hours": config.core_window_hours,
        "recovery_tail_hours": config.recovery_tail_hours,
        "sources": {
            "grid": config.grid_stress_shape.source,
            "green": config.green_workload_shape.source,
        },
        "normalization": {
            "grid": {
                "peak": config.grid_stress_shape.normalization_peak,
                "split_fraction": (
                    config.grid_stress_shape.normalization_split_fraction
                ),
            },
            "green": {
                "peak": config.green_workload_shape.normalization_peak,
                "split_fraction": (
                    config.green_workload_shape.normalization_split_fraction
                ),
            },
        },
        "windows": {
            "train": {
                "grid": [
                    {"start": start, "end": end}
                    for start, end in grid_train
                ],
                "green": [
                    {"start": start, "end": end}
                    for start, end in green_train
                ],
            },
            "holdout": {
                "grid": [
                    {"start": start, "end": end}
                    for start, end in grid_holdout
                ],
                "green": [
                    {"start": start, "end": end}
                    for start, end in green_holdout
                ],
            },
        },
        "network_activation_threshold": config.network_activation_threshold,
        "network_activation_semantics": (
            "trace_threshold_stress_indicator_not_observed_outage_timing"
        ),
        "green_call_scale_mw": config.green_call_scale_mw,
        "recovery_headroom_mw": config.recovery_headroom_mw,
        "recovery_headroom_semantics": (
            "synthetic_constant_sensitivity_not_observed_recovery"
        ),
        "trace_pairing": (
            "independent_marginal_windows_from_different_clusters"
        ),
        "probability_semantics": (
            "uniform_monte_carlo_window_weights_not_empirical_outage_probability"
        ),
    }
    return GeneratedTemporalScenarioSet(
        training_scenarios=training,
        holdout_scenarios=holdout,
        parameter_status=(
            f"{TEMPORAL_TRACE_PARAMETER_STATUS}|{config.parameter_status}"
        ),
        provenance=provenance,
    )
