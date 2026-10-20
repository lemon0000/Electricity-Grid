"""Sequential forced-outage chronology from pinned RTS-GMLC reliability fields."""

from __future__ import annotations

import csv
import hashlib
import math
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReliabilityComponent:
    component_type: str
    uid: str
    from_bus: int
    to_bus: int | None
    mean_up_hours: float
    mean_down_hours: float
    stated_for: float | None
    source_rate: float
    source_rate_unit: str

    @property
    def implied_unavailability(self) -> float:
        return self.mean_down_hours / (self.mean_up_hours + self.mean_down_hours)


@dataclass(frozen=True)
class OutageEvent:
    seed: int
    component_type: str
    uid: str
    start_hour: int
    end_hour_exclusive: int

    @property
    def duration_hours(self) -> int:
        return self.end_hour_exclusive - self.start_hour


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def load_reliability_components(
    upstream_root: Path,
    *,
    area: int,
) -> tuple[ReliabilityComponent, ...]:
    """Load generator and in-area AC-branch forced-outage parameters."""

    source_root = upstream_root / "RTS_Data" / "SourceData"
    generators = []
    for row in _rows(source_root / "gen.csv"):
        bus = int(row["Bus ID"])
        if bus // 100 != area:
            continue
        mttf = float(row["MTTF Hr"])
        mttr = float(row["MTTR Hr"])
        stated_for = float(row["FOR"])
        if stated_for == 0.0 and mttf == 0.0 and mttr == 0.0:
            continue
        if mttf <= 0.0 or mttr <= 0.0 or not 0.0 <= stated_for < 1.0:
            raise ValueError(f"Invalid generator reliability fields: {row['GEN UID']}")
        generators.append(
            ReliabilityComponent(
                component_type="generator",
                uid=row["GEN UID"],
                from_bus=bus,
                to_bus=None,
                mean_up_hours=mttf,
                mean_down_hours=mttr,
                stated_for=stated_for,
                source_rate=stated_for,
                source_rate_unit="fraction",
            )
        )

    branches = []
    for row in _rows(source_root / "branch.csv"):
        from_bus = int(row["From Bus"])
        to_bus = int(row["To Bus"])
        if from_bus // 100 != area or to_bus // 100 != area:
            continue
        annual_rate = float(row["Perm OutRate"])
        mean_down = float(row["Duration"])
        if annual_rate <= 0.0 or mean_down <= 0.0:
            raise ValueError(f"Invalid branch reliability fields: {row['UID']}")
        branches.append(
            ReliabilityComponent(
                component_type="branch",
                uid=row["UID"],
                from_bus=from_bus,
                to_bus=to_bus,
                mean_up_hours=8760.0 / annual_rate,
                mean_down_hours=mean_down,
                stated_for=None,
                source_rate=annual_rate,
                source_rate_unit="occurrences_per_year",
            )
        )
    components = tuple(
        sorted(
            (*generators, *branches), key=lambda item: (item.component_type, item.uid)
        )
    )
    if not components or len(
        {(item.component_type, item.uid) for item in components}
    ) != len(components):
        raise ValueError(
            "RTS-GMLC reliability component catalog is empty or duplicated"
        )
    return components


def _component_rng(seed: int, component: ReliabilityComponent) -> random.Random:
    identity = f"{seed}|{component.component_type}|{component.uid}".encode()
    component_seed = int.from_bytes(hashlib.sha256(identity).digest()[:16], "big")
    return random.Random(component_seed)


def _geometric_duration(rng: random.Random, mean_hours: float) -> int:
    probability = 1.0 - math.exp(-1.0 / mean_hours)
    return max(1, math.ceil(math.log1p(-rng.random()) / math.log1p(-probability)))


def simulate_outage_events(
    components: tuple[ReliabilityComponent, ...],
    *,
    seed: int,
    horizon_hours: int,
) -> tuple[OutageEvent, ...]:
    """Generate an hourly alternating-renewal benchmark in stationary state."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be positive")
    events = []
    for component in components:
        rng = _component_rng(seed, component)
        is_down = rng.random() < component.implied_unavailability
        hour = 0
        while hour < horizon_hours:
            if is_down:
                duration = _geometric_duration(rng, component.mean_down_hours)
                events.append(
                    OutageEvent(
                        seed=seed,
                        component_type=component.component_type,
                        uid=component.uid,
                        start_hour=hour,
                        end_hour_exclusive=min(hour + duration, horizon_hours),
                    )
                )
            else:
                duration = _geometric_duration(rng, component.mean_up_hours)
            hour += duration
            is_down = not is_down
    return tuple(
        sorted(
            events, key=lambda item: (item.start_hour, item.component_type, item.uid)
        )
    )


def hourly_outage_counts(
    events: tuple[OutageEvent, ...],
    *,
    horizon_hours: int,
) -> tuple[tuple[int, int], ...]:
    generator_delta = [0] * (horizon_hours + 1)
    branch_delta = [0] * (horizon_hours + 1)
    for event in events:
        target = (
            generator_delta if event.component_type == "generator" else branch_delta
        )
        target[event.start_hour] += 1
        target[event.end_hour_exclusive] -= 1
    generator_count = 0
    branch_count = 0
    result = []
    for hour in range(horizon_hours):
        generator_count += generator_delta[hour]
        branch_count += branch_delta[hour]
        result.append((generator_count, branch_count))
    return tuple(result)
