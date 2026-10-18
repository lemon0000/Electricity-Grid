"""Draft, zero-solver chronology check for supplied committable-unit witnesses.

This checks unit bounds, ramp and minimum dwell only. It is neither a dispatch
solver nor a network/security certificate. Initial history must be supplied.
"""

from dataclasses import dataclass
from math import ceil, isfinite
from numbers import Real


TOLERANCE_MW = 1e-6


def _nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite nonnegative number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


@dataclass(frozen=True)
class GridIdentity:
    split: str
    trajectory_id: str
    outage_seed: int
    source_sha256: str

    def __post_init__(self):
        if self.split not in {"training", "holdout"}:
            raise ValueError("explicit split required")
        if not isinstance(self.trajectory_id, str) or not self.trajectory_id:
            raise ValueError("explicit trajectory required")
        _integer(self.outage_seed, "outage_seed")
        if (not isinstance(self.source_sha256, str) or len(self.source_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.source_sha256)):
            raise ValueError("source SHA256 identity required")


@dataclass(frozen=True)
class UnitLimits:
    uid: str
    minimum_power_mw: float
    maximum_power_mw: float
    ramp_mw_per_hour: float
    minimum_up_hours: float
    minimum_down_hours: float

    def __post_init__(self):
        if not isinstance(self.uid, str) or not self.uid:
            raise ValueError("unit UID required")
        for name in ("minimum_power_mw", "maximum_power_mw", "ramp_mw_per_hour",
                     "minimum_up_hours", "minimum_down_hours"):
            _nonnegative(getattr(self, name), name)
        if self.minimum_power_mw > self.maximum_power_mw:
            raise ValueError("minimum power exceeds maximum power")


@dataclass(frozen=True)
class UnitPoint:
    uid: str
    committed: bool
    generation_mw: float

    def __post_init__(self):
        if not isinstance(self.uid, str) or not self.uid:
            raise ValueError("unit UID required")
        if type(self.committed) is not bool:
            raise ValueError("commitment must be boolean")
        _nonnegative(self.generation_mw, "generation_mw")


def _inventory(values, kind):
    if not isinstance(values, tuple) or not values or any(type(v) is not kind for v in values):
        raise ValueError("nonempty immutable typed unit inventory required")
    names = tuple(v.uid for v in values)
    if len(set(names)) != len(names) or names != tuple(sorted(names)):
        raise ValueError("unique sorted unit inventory required")
    return names


def _bounds(point, limits):
    lower = limits.minimum_power_mw if point.committed else 0.
    upper = limits.maximum_power_mw if point.committed else 0.
    if point.generation_mw < lower - TOLERANCE_MW or point.generation_mw > upper + TOLERANCE_MW:
        raise ValueError(f"{point.uid}: unit power bound violated")


@dataclass(frozen=True)
class GridCarry:
    identity: GridIdentity
    source_hour: int
    limits: tuple[UnitLimits, ...]
    points: tuple[UnitPoint, ...]
    elapsed_state_hours: tuple[int, ...]
    initial_history_role: str

    def __post_init__(self):
        if type(self.identity) is not GridIdentity:
            raise ValueError("typed grid identity required")
        _integer(self.source_hour, "source_hour")
        if _inventory(self.limits, UnitLimits) != _inventory(self.points, UnitPoint):
            raise ValueError("limits and points must have identical unit inventory")
        if (not isinstance(self.elapsed_state_hours, tuple)
                or len(self.elapsed_state_hours) != len(self.points)):
            raise ValueError("complete immutable initial dwell history required")
        for age, point, limit in zip(self.elapsed_state_hours, self.points, self.limits, strict=True):
            _integer(age, "elapsed_state_hours")
            _bounds(point, limit)
        if self.initial_history_role not in {"mechanism_assumption", "derived_dispatch_witness"}:
            raise ValueError("explicit initial-history evidence role required")


@dataclass(frozen=True)
class GridHour:
    identity: GridIdentity
    source_hour: int
    points: tuple[UnitPoint, ...]

    def __post_init__(self):
        if type(self.identity) is not GridIdentity:
            raise ValueError("typed grid identity required")
        _integer(self.source_hour, "source_hour")
        _inventory(self.points, UnitPoint)


def advance_grid_carry(before: GridCarry, hour: GridHour) -> GridCarry:
    """Check one supplied next hour; rejection leaves the immutable input intact.

    Ramp inequalities follow the existing normal SCUC startup/shutdown Pmax
    allowances. Minimum dwell uses ceil(source minimum hours), with carried
    elapsed hours explicitly checked before switching the unit state.
    """
    if type(before) is not GridCarry or type(hour) is not GridHour:
        raise ValueError("typed carry and one grid hour required")
    if hour.identity != before.identity:
        raise ValueError("grid split/trajectory/seed/source identity changed")
    if hour.source_hour != before.source_hour + 1:
        raise ValueError("grid source-hour gap")
    if tuple(p.uid for p in hour.points) != tuple(p.uid for p in before.points):
        raise ValueError("grid unit inventory changed")
    ages = []
    for prior, current, limit, age in zip(
        before.points, hour.points, before.limits, before.elapsed_state_hours, strict=True
    ):
        _bounds(current, limit)
        startup = not prior.committed and current.committed
        shutdown = prior.committed and not current.committed
        minimum = ceil(limit.minimum_up_hours if prior.committed else limit.minimum_down_hours)
        if (startup or shutdown) and age < minimum:
            raise ValueError(f"{prior.uid}: carried minimum dwell not satisfied")
        upward = limit.ramp_mw_per_hour + limit.maximum_power_mw * startup
        downward = limit.ramp_mw_per_hour + limit.maximum_power_mw * shutdown
        if (current.generation_mw - prior.generation_mw > upward + TOLERANCE_MW
                or prior.generation_mw - current.generation_mw > downward + TOLERANCE_MW):
            raise ValueError(f"{prior.uid}: interhour ramp violated")
        ages.append(1 if startup or shutdown else age + 1)
    return GridCarry(before.identity, hour.source_hour, before.limits, hour.points,
                     tuple(ages), before.initial_history_role)


def replay_grid_chunk(before: GridCarry, hours: tuple[GridHour, ...]) -> GridCarry:
    """Audit all adjacent unit transitions, including the incoming chunk edge."""
    if type(before) is not GridCarry or not isinstance(hours, tuple):
        raise ValueError("typed carry and immutable chunk required")
    state = before
    for hour in hours:
        state = advance_grid_carry(state, hour)
    return state
