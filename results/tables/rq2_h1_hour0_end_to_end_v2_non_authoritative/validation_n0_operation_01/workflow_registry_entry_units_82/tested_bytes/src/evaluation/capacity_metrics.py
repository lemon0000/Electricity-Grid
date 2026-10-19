"""Evidence-scoped capacity milestone calculations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from numbers import Real


STATIC_ASSUMPTION_METRIC_SCOPE = (
    "released_capacity_threshold_in_static_dc_state_set_with_declared_window_assumption"
)
CHRONOLOGICAL_SENSITIVITY_METRIC_SCOPE = (
    "released_capacity_model_validated_over_explicit_chronological_sensitivity_trace"
)


@dataclass(frozen=True)
class CapacityMilestone:
    threshold_mw: float
    reached: bool
    quarter: str | None
    right_censored: bool
    censor_quarter: str | None
    display_label: str


@dataclass(frozen=True)
class CapacityMilestones:
    t_module: CapacityMilestone
    t20: CapacityMilestone
    t50: CapacityMilestone
    t100: CapacityMilestone
    metric_scope: str


def _positive_finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if number <= 0.0:
        raise ValueError(f"{name} must be positive")
    return number


def _nonnegative_finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _validate_keys(
    name: str,
    values: Mapping[str, object],
    quarter_names: tuple[str, ...],
) -> None:
    expected = set(quarter_names)
    actual = set(values)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{name} keys must match quarter_names; missing={missing}, extra={extra}"
        )


def calculate_capacity_milestones(
    quarter_names: Iterable[str],
    total_capacity_mw: Mapping[str, float],
    model_validated_by_quarter: Mapping[str, bool],
    continuous_validation_hours: Mapping[str, float],
    application_capacity_mw: float,
    minimum_operational_block_mw: float,
    minimum_validation_hours: float,
    tolerance_mw: float = 1.0e-6,
    metric_scope: str = STATIC_ASSUMPTION_METRIC_SCOPE,
) -> CapacityMilestones:
    """Return evidence-scoped capacity milestones on one ordered path."""

    if isinstance(quarter_names, str):
        raise ValueError("quarter_names must be an ordered iterable of names")
    names = tuple(quarter_names)
    if not names:
        raise ValueError("quarter_names must be nonempty")
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("quarter names must be nonempty strings")
    if len(set(names)) != len(names):
        raise ValueError("quarter names must be unique")

    application_capacity = _positive_finite(
        "application_capacity_mw", application_capacity_mw
    )
    minimum_block = _positive_finite(
        "minimum_operational_block_mw", minimum_operational_block_mw
    )
    minimum_hours = _positive_finite(
        "minimum_validation_hours", minimum_validation_hours
    )
    tolerance = _nonnegative_finite("tolerance_mw", tolerance_mw)
    if not isinstance(metric_scope, str) or not metric_scope:
        raise ValueError("metric_scope must be a nonempty string")
    if minimum_block > application_capacity + tolerance:
        raise ValueError(
            "minimum_operational_block_mw cannot exceed application_capacity_mw"
        )

    _validate_keys("total_capacity_mw", total_capacity_mw, names)
    _validate_keys("model_validated_by_quarter", model_validated_by_quarter, names)
    _validate_keys(
        "continuous_validation_hours", continuous_validation_hours, names
    )

    capacities = {}
    validation_hours = {}
    previous_capacity = None
    for name in names:
        capacity = _nonnegative_finite(
            f"total_capacity_mw[{name}]", total_capacity_mw[name]
        )
        if capacity > application_capacity + tolerance:
            raise ValueError(
                f"total_capacity_mw[{name}] cannot exceed application_capacity_mw"
            )
        if previous_capacity is not None and capacity + tolerance < previous_capacity:
            raise ValueError("total_capacity_mw must be nondecreasing")
        previous_capacity = capacity
        capacities[name] = capacity
        validation_hours[name] = _nonnegative_finite(
            f"continuous_validation_hours[{name}]",
            continuous_validation_hours[name],
        )
        if type(model_validated_by_quarter[name]) is not bool:
            raise ValueError(f"model_validated_by_quarter[{name}] must be bool")

    def milestone(threshold_mw: float) -> CapacityMilestone:
        for name in names:
            if (
                capacities[name] + tolerance >= threshold_mw
                and model_validated_by_quarter[name]
                and validation_hours[name] >= minimum_hours
            ):
                return CapacityMilestone(
                    threshold_mw=threshold_mw,
                    reached=True,
                    quarter=name,
                    right_censored=False,
                    censor_quarter=None,
                    display_label=name,
                )
        censor_quarter = names[-1]
        return CapacityMilestone(
            threshold_mw=threshold_mw,
            reached=False,
            quarter=None,
            right_censored=True,
            censor_quarter=censor_quarter,
            display_label=f"{censor_quarter}+",
        )

    return CapacityMilestones(
        t_module=milestone(minimum_block),
        t20=milestone(max(0.20 * application_capacity, minimum_block)),
        t50=milestone(max(0.50 * application_capacity, minimum_block)),
        t100=milestone(max(application_capacity, minimum_block)),
        metric_scope=metric_scope,
    )
