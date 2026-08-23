"""Fast-forward reduction for chronological RQ2 training scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import isfinite
from numbers import Real

import numpy as np

from .temporal_trace_scenario_generator import TemporalNetworkScenario

TEMPORAL_SCENARIO_REDUCTION_PARAMETER_STATUS = (
    "chronological_training_distribution_reduced_by_fast_forward_selection_"
    "representatives_are_input_trajectories_with_redistributed_probability_"
    "mass_not_new_empirical_data"
)
_COMPONENTS = (
    "network_call_active",
    "green_call_mw",
    "data_center_demand_mw",
    "system_load_multiplier",
)
_PROBABILITY_TOLERANCE = 1.0e-9


@dataclass(frozen=True)
class TemporalScenarioReductionResult:
    reduced_scenarios: tuple[TemporalNetworkScenario, ...]
    kantorovich_distance: float
    parameter_status: str
    provenance: dict = field(default_factory=dict)


def _finite(name: str, raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(raw):
        raise ValueError(f"{name} must be a finite number")
    return float(raw)


def _validate(
    scenarios: tuple[TemporalNetworkScenario, ...],
    component_scales: dict[str, float],
) -> tuple[np.ndarray, dict[str, float], int]:
    if not scenarios:
        raise ValueError("scenarios must be a nonempty tuple")
    names = [scenario.name for scenario in scenarios]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("scenario names must be nonempty and unique")
    if set(component_scales) != set(_COMPONENTS):
        raise ValueError(
            f"component_scales must contain exactly {sorted(_COMPONENTS)}"
        )
    scales = {}
    for component in _COMPONENTS:
        scale = _finite(f"component_scales.{component}", component_scales[component])
        if scale <= 0.0:
            raise ValueError("component scales must be strictly positive")
        scales[component] = scale

    horizon = len(scenarios[0].periods)
    if horizon < 1:
        raise ValueError("scenario horizon must be nonempty")
    reference = scenarios[0]
    total_probability = 0.0
    for scenario in scenarios:
        probability = _finite(
            f"probability[{scenario.name}]", scenario.probability
        )
        if probability <= 0.0:
            raise ValueError("scenario probabilities must be strictly positive")
        total_probability += probability
        if len(scenario.periods) != horizon:
            raise ValueError("all scenarios must have the same horizon")
        if any(not period for period in scenario.periods):
            raise ValueError("scenario periods must be nonempty")
        if scenario.periods != reference.periods:
            raise ValueError("all scenarios must have the same period sequence")
        for period in set(scenario.periods):
            indices = [
                index
                for index, observed in enumerate(scenario.periods)
                if observed == period
            ]
            if indices != list(range(indices[0], indices[-1] + 1)):
                raise ValueError("each scenario period must form one contiguous block")
        if not isinstance(scenario.completed_periods, frozenset):
            raise TypeError("completed_periods must be a frozenset")
        if not scenario.completed_periods.issubset(set(scenario.periods)):
            raise ValueError("completed_periods must occur in scenario periods")
        if scenario.completed_periods != reference.completed_periods:
            raise ValueError("all scenarios must have the same completed_periods")
        if not isinstance(scenario.require_terminal_event_inactive, bool):
            raise TypeError("require_terminal_event_inactive must be boolean")
        if (
            scenario.require_terminal_event_inactive
            != reference.require_terminal_event_inactive
        ):
            raise ValueError(
                "all scenarios must have the same terminal event requirement"
            )
        if scenario.boundary_state_status != "clean_boundary_with_zero_carry_in":
            raise ValueError(
                "boundary_state_status must be clean_boundary_with_zero_carry_in"
            )
        if scenario.boundary_state_status != reference.boundary_state_status:
            raise ValueError(
                "all scenarios must have the same boundary_state_status"
            )
        for component in _COMPONENTS:
            values = getattr(scenario, component)
            if len(values) != horizon:
                raise ValueError(f"{component} must match the scenario horizon")
            for index, value in enumerate(values):
                observed = _finite(
                    f"{component}[{scenario.name}][{index}]", value
                )
                if component != "network_call_active" and observed < 0.0:
                    raise ValueError(f"{component} values must be nonnegative")
        for component in ("connected_demand_mw", "recovery_headroom_mw"):
            values = getattr(scenario, component)
            if len(values) != horizon:
                raise ValueError(f"{component} must match the scenario horizon")
            for index, value in enumerate(values):
                if _finite(f"{component}[{scenario.name}][{index}]", value) < 0.0:
                    raise ValueError(f"{component} values must be nonnegative")
        if scenario.recovery_headroom_mw != reference.recovery_headroom_mw:
            raise ValueError(
                "all scenarios must have the same recovery_headroom_mw"
            )
        if any(
            abs(demand - connected) > 1.0e-9
            for demand, connected in zip(
                scenario.data_center_demand_mw,
                scenario.connected_demand_mw,
            )
        ):
            raise ValueError(
                "connected_demand_mw must equal data_center_demand_mw"
            )
        if any(value not in (0, 1) for value in scenario.network_call_active):
            raise ValueError("network_call_active values must be binary")
    if abs(total_probability - 1.0) > _PROBABILITY_TOLERANCE:
        raise ValueError("scenario probabilities must sum to one")
    return (
        np.asarray([scenario.probability for scenario in scenarios], dtype=float),
        scales,
        horizon,
    )


def _feature_matrix(
    scenarios: tuple[TemporalNetworkScenario, ...],
    scales: dict[str, float],
) -> np.ndarray:
    rows = []
    for scenario in scenarios:
        row = []
        for component in _COMPONENTS:
            row.extend(
                float(value) / scales[component]
                for value in getattr(scenario, component)
            )
        rows.append(row)
    return np.asarray(rows, dtype=float)


def reduce_temporal_scenarios_fast_forward(
    scenarios: tuple[TemporalNetworkScenario, ...],
    *,
    target_count: int,
    component_scales: dict[str, float],
    ground_norm_order: float = 2.0,
    parameter_status: str,
) -> TemporalScenarioReductionResult:
    """Reduce training trajectories while preserving retained paths exactly."""

    if isinstance(target_count, bool) or not isinstance(target_count, int):
        raise TypeError("target_count must be an integer")
    if target_count < 1:
        raise ValueError("target_count must be a positive integer")
    if not isinstance(parameter_status, str) or not parameter_status:
        raise ValueError("parameter_status must be a nonempty string")
    order = _finite("ground_norm_order", ground_norm_order)
    if order < 1.0:
        raise ValueError("ground_norm_order must be >= 1 to be a metric")
    probabilities, scales, horizon = _validate(scenarios, component_scales)
    combined_status = (
        f"{parameter_status}|{TEMPORAL_SCENARIO_REDUCTION_PARAMETER_STATUS}"
    )
    count = len(scenarios)
    metric = {
        "norm_order": order,
        "component_order": list(_COMPONENTS),
        "component_scales": scales,
        "flattening": "component_major_then_chronological_hour",
        "horizon_hours": horizon,
    }
    if target_count >= count:
        names = [scenario.name for scenario in scenarios]
        return TemporalScenarioReductionResult(
            reduced_scenarios=scenarios,
            kantorovich_distance=0.0,
            parameter_status=combined_status,
            provenance={
                "algorithm": "fast_forward_selection_no_reduction_needed",
                "ground_metric": metric,
                "original_count": count,
                "target_count": target_count,
                "kept_names": names,
                "selection_order": names,
                "deleted_to_kept": {},
                "kantorovich_distance": 0.0,
            },
        )

    features = _feature_matrix(scenarios, scales)
    difference = features[:, None, :] - features[None, :, :]
    cost = np.linalg.norm(difference, ord=order, axis=2)
    remaining = np.ones(count, dtype=bool)
    nearest_distance = np.full(count, np.inf)
    kept: list[int] = []
    for _ in range(target_count):
        best_index = -1
        best_cost = np.inf
        for candidate_index in np.nonzero(remaining)[0]:
            candidate_distance = np.minimum(
                nearest_distance, cost[:, candidate_index]
            )
            mask = remaining.copy()
            mask[candidate_index] = False
            candidate_cost = float(
                np.sum(probabilities[mask] * candidate_distance[mask])
            )
            if candidate_cost < best_cost - 1.0e-15:
                best_index = int(candidate_index)
                best_cost = candidate_cost
        kept.append(best_index)
        remaining[best_index] = False
        nearest_distance = np.minimum(nearest_distance, cost[:, best_index])

    redistributed = {index: float(probabilities[index]) for index in kept}
    deleted_to_kept = {}
    kantorovich_distance = 0.0
    kept_array = np.asarray(kept, dtype=int)
    for deleted_index in np.nonzero(remaining)[0]:
        distances = cost[deleted_index, kept_array]
        selected_position = int(np.argmin(distances))
        kept_index = int(kept_array[selected_position])
        redistributed[kept_index] += float(probabilities[deleted_index])
        kantorovich_distance += (
            float(probabilities[deleted_index])
            * float(distances[selected_position])
        )
        deleted_to_kept[scenarios[deleted_index].name] = scenarios[kept_index].name

    original_order = sorted(kept)
    reduced = tuple(
        replace(scenarios[index], probability=redistributed[index])
        for index in original_order
    )
    return TemporalScenarioReductionResult(
        reduced_scenarios=reduced,
        kantorovich_distance=kantorovich_distance,
        parameter_status=combined_status,
        provenance={
            "algorithm": (
                "fast_forward_selection_with_optimal_order_1_kantorovich_"
                "redistribution"
            ),
            "ground_metric": metric,
            "original_count": count,
            "target_count": target_count,
            "kept_names": [scenarios[index].name for index in original_order],
            "selection_order": [scenarios[index].name for index in kept],
            "deleted_to_kept": deleted_to_kept,
            "kantorovich_distance": kantorovich_distance,
        },
    )


__all__ = [
    "TEMPORAL_SCENARIO_REDUCTION_PARAMETER_STATUS",
    "TemporalScenarioReductionResult",
    "reduce_temporal_scenarios_fast_forward",
]
