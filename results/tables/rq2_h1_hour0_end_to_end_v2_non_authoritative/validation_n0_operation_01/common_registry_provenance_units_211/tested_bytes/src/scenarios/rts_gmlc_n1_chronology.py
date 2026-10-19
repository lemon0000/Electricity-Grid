"""System-level RTS-GMLC N-1 outage chronology for public benchmarks."""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class N1ReliabilityComponent:
    component_type: str
    uid: str
    failure_rate_per_hour: float
    mean_down_hours: float


@dataclass(frozen=True)
class N1OutageEvent:
    seed: int
    event_id: str
    component_type: str
    uid: str
    start_hour: int
    end_hour_exclusive: int

    @property
    def duration_hours(self) -> int:
        return self.end_hour_exclusive - self.start_hour


def _positive(raw: Real, label: str) -> float:
    value = float(raw)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be finite and positive")
    return value


def _geometric_duration(rng: random.Random, mean_hours: float) -> int:
    probability = 1.0 - math.exp(-1.0 / mean_hours)
    return max(
        1,
        math.ceil(math.log1p(-rng.random()) / math.log1p(-probability)),
    )


def _weighted_choice(
    rng: random.Random,
    components: tuple[N1ReliabilityComponent, ...],
    weights: tuple[float, ...],
) -> N1ReliabilityComponent:
    threshold = rng.random() * sum(weights)
    cumulative = 0.0
    for component, weight in zip(components, weights, strict=True):
        cumulative += weight
        if threshold <= cumulative:
            return component
    return components[-1]


def simulate_n_minus_one_events(
    components: tuple[N1ReliabilityComponent, ...],
    *,
    seed: int,
    horizon_hours: int,
) -> tuple[N1OutageEvent, ...]:
    """Sample a stationary alternating chronology with at most one outage."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if isinstance(horizon_hours, bool) or horizon_hours <= 0:
        raise ValueError("horizon_hours must be a positive integer")
    if not components:
        raise ValueError("components must be nonempty")
    identities = [(item.component_type, item.uid) for item in components]
    if any(kind not in {"branch", "generator"} or not uid for kind, uid in identities):
        raise ValueError("component identities must be explicit")
    if len(identities) != len(set(identities)):
        raise ValueError("component identities must be unique")

    ordered = tuple(sorted(components, key=lambda item: (item.component_type, item.uid)))
    failure_rates = tuple(
        _positive(item.failure_rate_per_hour, "failure_rate_per_hour")
        for item in ordered
    )
    down_hours = tuple(
        _positive(item.mean_down_hours, "mean_down_hours") for item in ordered
    )
    total_failure_rate = sum(failure_rates)
    mean_up_hours = 1.0 / total_failure_rate
    mean_down_hours = sum(
        rate * duration
        for rate, duration in zip(failure_rates, down_hours, strict=True)
    ) / total_failure_rate
    stationary_down_probability = mean_down_hours / (
        mean_up_hours + mean_down_hours
    )
    down_weights = tuple(
        rate * duration
        for rate, duration in zip(failure_rates, down_hours, strict=True)
    )

    identity = "|".join(
        f"{kind}:{uid}" for kind, uid in ((item.component_type, item.uid) for item in ordered)
    )
    digest = hashlib.sha256(f"{seed}|{identity}".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:16], "big"))
    hour = 0
    event_index = 0
    events: list[N1OutageEvent] = []

    if rng.random() < stationary_down_probability:
        component = _weighted_choice(rng, ordered, down_weights)
        duration = _geometric_duration(rng, component.mean_down_hours)
        events.append(
            N1OutageEvent(
                seed=seed,
                event_id=f"seed_{seed}_event_{event_index:04d}",
                component_type=component.component_type,
                uid=component.uid,
                start_hour=0,
                end_hour_exclusive=min(duration, horizon_hours),
            )
        )
        event_index += 1
        hour = duration

    while hour < horizon_hours:
        hour += _geometric_duration(rng, mean_up_hours)
        if hour >= horizon_hours:
            break
        component = _weighted_choice(rng, ordered, failure_rates)
        duration = _geometric_duration(rng, component.mean_down_hours)
        events.append(
            N1OutageEvent(
                seed=seed,
                event_id=f"seed_{seed}_event_{event_index:04d}",
                component_type=component.component_type,
                uid=component.uid,
                start_hour=hour,
                end_hour_exclusive=min(hour + duration, horizon_hours),
            )
        )
        event_index += 1
        hour += duration

    return tuple(events)


def event_by_hour(
    events: tuple[N1OutageEvent, ...],
    *,
    horizon_hours: int,
) -> tuple[N1OutageEvent | None, ...]:
    """Expand nonoverlapping events to a complete hourly chronology."""

    if isinstance(horizon_hours, bool) or horizon_hours <= 0:
        raise ValueError("horizon_hours must be a positive integer")
    result: list[N1OutageEvent | None] = [None] * horizon_hours
    for event in events:
        if (
            event.start_hour < 0
            or event.end_hour_exclusive <= event.start_hour
            or event.end_hour_exclusive > horizon_hours
        ):
            raise ValueError("event lies outside the chronology")
        for hour in range(event.start_hour, event.end_hour_exclusive):
            if result[hour] is not None:
                raise ValueError("N-1 chronology contains overlapping events")
            result[hour] = event
    return tuple(result)
