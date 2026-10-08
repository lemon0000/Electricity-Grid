"""Continuous-boundary state and provenance checks for the RQ2 draft."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from math import isfinite
from numbers import Integral, Real

_ARM_TRACKS = {
    "network_only_shared": {"shared"},
    "cfe_only_shared": {"shared"},
    "joint_correct_shared": {"shared"},
    "joint_b6_separate_planning_shared_execution": {"grid", "cfe"},
}
SERVICE_TOLERANCE = 1.0e-6


def _number(raw: object, label: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, Real) or not isfinite(raw):
        raise ValueError(f"{label} must be a finite number")
    value = float(raw)
    if value < 0.0:
        raise ValueError(f"{label} must be nonnegative")
    return value


def _sha256(raw: str, label: str) -> str:
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return raw


@dataclass(frozen=True)
class TemporalCarryState:
    arm_id: str
    track_id: str
    previous_call: float
    event_active: bool
    active_duration_hours: float
    interevent_rest_hours: float | None
    event_count: int
    cumulative_call_energy: float
    recovery_debt: float
    has_prior_event: bool
    accounting_period_id: str
    observed_violations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.arm_id not in _ARM_TRACKS or self.track_id not in _ARM_TRACKS[self.arm_id]:
            raise ValueError("registered arm-track identity is invalid")
        if not isinstance(self.event_active, bool) or not isinstance(
            self.has_prior_event, bool
        ):
            raise TypeError("event state flags must be boolean")
        for field_name in (
            "previous_call",
            "active_duration_hours",
            "cumulative_call_energy",
            "recovery_debt",
        ):
            _number(getattr(self, field_name), field_name)
        if self.interevent_rest_hours is not None:
            _number(self.interevent_rest_hours, "interevent_rest_hours")
        if isinstance(self.event_count, bool) or not isinstance(self.event_count, Integral):
            raise TypeError("event_count must be an integer")
        if self.event_count < 0 or not self.accounting_period_id:
            raise ValueError("event count and accounting period are invalid")
        if self.has_prior_event != (self.event_count > 0):
            raise ValueError("has_prior_event and event_count must agree")
        if self.event_active != (self.previous_call > SERVICE_TOLERANCE):
            raise ValueError("event activity and previous call disagree")
        if self.event_active and (
            self.active_duration_hours <= 0.0 or self.interevent_rest_hours is not None
        ):
            raise ValueError("active carry state is internally inconsistent")
        if not self.event_active and self.active_duration_hours > 0.0:
            raise ValueError("inactive carry state has active duration")
        if not self.event_active and self.has_prior_event and self.interevent_rest_hours is None:
            raise ValueError("inactive prior-event state requires observed rest")
        if not self.event_active and not self.has_prior_event and self.interevent_rest_hours is not None:
            raise ValueError("rest is undefined without a prior event")
        if self.event_count > 0 and not self.has_prior_event:
            raise ValueError("event count requires prior-event state")
        if not all(isinstance(item, str) and item for item in self.observed_violations):
            raise ValueError("observed violations must be nonempty strings")


@dataclass(frozen=True)
class BoundaryAnchor:
    arm_id: str
    track_id: str
    split: str
    power_source_hour: int
    workload_source_hour: int
    power_trajectory_id: str
    workload_trace_id: str
    workload_normalization_sha256: str
    power_outage_seed: int
    power_provenance_sha256: str
    workload_provenance_sha256: str

    def __post_init__(self) -> None:
        _validate_identity(self)


@dataclass(frozen=True)
class ContinuationHour:
    arm_id: str
    track_id: str
    split: str
    power_source_hour: int
    workload_source_hour: int
    power_trajectory_id: str
    workload_trace_id: str
    workload_normalization_sha256: str
    power_outage_seed: int
    grid_request: float
    cfe_request: float
    workload_occupancy: float
    power_provenance_sha256: str
    workload_provenance_sha256: str

    def __post_init__(self) -> None:
        _validate_identity(self)
        _number(self.grid_request, "grid_request")
        _number(self.cfe_request, "cfe_request")
        occupancy = _number(self.workload_occupancy, "workload_occupancy")
        if occupancy > 1.0:
            raise ValueError("workload_occupancy must not exceed one")


@dataclass(frozen=True)
class ContinuationAssessment:
    status: str
    completion_can_be_evaluated: bool
    observed_hours: int
    registered_completion_deadline_hours: int | None
    observed_violations: tuple[str, ...]


def _validate_identity(value: BoundaryAnchor | ContinuationHour) -> None:
    if value.arm_id not in _ARM_TRACKS or value.track_id not in _ARM_TRACKS[value.arm_id]:
        raise ValueError("registered arm-track identity is invalid")
    if value.split not in {"training", "holdout"}:
        raise ValueError("split must be training or holdout")
    for name in ("power_source_hour", "workload_source_hour", "power_outage_seed"):
        item = getattr(value, name)
        if isinstance(item, bool) or not isinstance(item, Integral) or item < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    for name in ("power_trajectory_id", "workload_trace_id"):
        if not isinstance(getattr(value, name), str) or not getattr(value, name):
            raise ValueError(f"{name} must be explicit")
    for name in (
        "workload_normalization_sha256",
        "power_provenance_sha256",
        "workload_provenance_sha256",
    ):
        _sha256(getattr(value, name), name)


def _validate_next_identity(
    previous: BoundaryAnchor | ContinuationHour,
    current: ContinuationHour,
) -> None:
    if current.split != previous.split:
        raise ValueError("cross-split continuation is forbidden")
    if current.power_source_hour != previous.power_source_hour + 1:
        raise ValueError("power continuation has a source-hour gap")
    if current.workload_source_hour != previous.workload_source_hour + 1:
        raise ValueError("workload continuation has a source-hour gap")
    for name in (
        "arm_id",
        "track_id",
        "power_trajectory_id",
        "power_outage_seed",
        "workload_trace_id",
        "workload_normalization_sha256",
        "power_provenance_sha256",
        "workload_provenance_sha256",
    ):
        if getattr(current, name) != getattr(previous, name):
            raise ValueError(f"continuation {name} drifted")


def carry_state_across_boundary(
    state: TemporalCarryState,
    *,
    anchor: BoundaryAnchor,
    next_hour: ContinuationHour,
) -> TemporalCarryState:
    """Validate continuity and return the exact state; the boundary has no dynamics."""

    if state.track_id not in _ARM_TRACKS.get(state.arm_id, set()):
        raise ValueError("registered arm-track identity is invalid")
    if (state.arm_id, state.track_id) != (anchor.arm_id, anchor.track_id):
        raise ValueError("carry state and boundary arm-track identities differ")
    _validate_next_identity(anchor, next_hour)
    return state


def advance_continuous_state(
    state: TemporalCarryState,
    *,
    call: float,
    call_limit: float,
    recovery: float,
    recovery_headroom: float,
    maximum_recovery_power: float,
    recovery_efficiency: float,
    time_step_hours: float,
    maximum_event_duration_hours: float,
    maximum_event_count: int,
    normalized_energy_budget: float,
    normalized_debt_limit: float,
    minimum_recovery_hours: float,
    accounting_period_id: str | None = None,
) -> TemporalCarryState:
    """Audit and advance one observed hour without resetting continuous state."""

    raw_call = _number(call, "call")
    call_limit = _number(call_limit, "call_limit")
    raw_recovery = _number(recovery, "recovery")
    recovery_headroom = _number(recovery_headroom, "recovery_headroom")
    maximum_recovery_power = _number(
        maximum_recovery_power, "maximum_recovery_power"
    )
    call = 0.0 if raw_call <= SERVICE_TOLERANCE else raw_call
    recovery = 0.0 if raw_recovery <= SERVICE_TOLERANCE else raw_recovery
    efficiency = _number(recovery_efficiency, "recovery_efficiency")
    dt = _number(time_step_hours, "time_step_hours")
    max_duration = _number(maximum_event_duration_hours, "maximum_event_duration_hours")
    energy_limit = _number(normalized_energy_budget, "normalized_energy_budget")
    debt_limit = _number(normalized_debt_limit, "normalized_debt_limit")
    min_rest = _number(minimum_recovery_hours, "minimum_recovery_hours")
    tolerance = SERVICE_TOLERANCE
    if not 0.0 < efficiency <= 1.0 or dt <= 0.0 or max_duration <= 0.0:
        raise ValueError("continuous-envelope parameters are invalid")
    if isinstance(maximum_event_count, bool) or not isinstance(maximum_event_count, Integral):
        raise TypeError("maximum_event_count must be an integer")
    if maximum_event_count < 0:
        raise ValueError("maximum_event_count must be nonnegative")
    period = state.accounting_period_id if accounting_period_id is None else accounting_period_id
    if not period:
        raise ValueError("accounting period must be explicit")
    if period != state.accounting_period_id:
        raise ValueError("accounting period cannot change without registered evidence")
    if call > call_limit + tolerance:
        raise ValueError("call limit would be violated")
    if recovery > recovery_headroom + tolerance:
        raise ValueError("recovery headroom would be violated")
    if recovery > maximum_recovery_power + tolerance:
        raise ValueError("maximum recovery power would be violated")
    active = call > tolerance
    start = active and not state.event_active
    if active and recovery > tolerance:
        raise ValueError("recovery cannot occur during an active call")
    if start and state.has_prior_event and (
        state.interevent_rest_hours is None
        or state.interevent_rest_hours + tolerance < min_rest
    ):
        raise ValueError("minimum interevent recovery would be violated")
    duration = (
        state.active_duration_hours + dt
        if active and state.event_active
        else (dt if active else 0.0)
    )
    event_count = state.event_count + int(start)
    energy = state.cumulative_call_energy + call * dt
    debt_before_recovery = state.recovery_debt + call * dt
    if recovery * efficiency * dt > debt_before_recovery + tolerance:
        raise ValueError("recovery exceeds accrued debt")
    debt = max(debt_before_recovery - efficiency * recovery * dt, 0.0)
    violations = list(state.observed_violations)
    if duration > max_duration + tolerance:
        violations.append("maximum_event_duration")
    if event_count > maximum_event_count:
        violations.append("maximum_event_count")
    if energy > energy_limit + tolerance:
        violations.append("energy_budget")
    if debt > debt_limit + tolerance:
        violations.append("recovery_debt_limit")
    if violations != list(state.observed_violations):
        raise ValueError("; ".join(dict.fromkeys(violations)))
    if active:
        rest = None
    elif state.event_active:
        rest = dt
    elif state.has_prior_event:
        rest = (state.interevent_rest_hours or 0.0) + dt
    else:
        rest = None
    return replace(
        state,
        previous_call=call,
        event_active=active,
        active_duration_hours=duration,
        interevent_rest_hours=rest,
        event_count=event_count,
        cumulative_call_energy=energy,
        recovery_debt=debt,
        has_prior_event=state.has_prior_event or start,
    )


def assess_observed_continuation(
    *,
    anchor: BoundaryAnchor,
    continuation: Sequence[ContinuationHour] | None,
    registered_completion_deadline_hours: int | None,
    state: TemporalCarryState | None = None,
) -> ContinuationAssessment:
    """Validate observed continuation inventory without declaring service completion."""

    observed_violations = () if state is None else state.observed_violations
    if state is not None and (state.arm_id, state.track_id) != (
        anchor.arm_id,
        anchor.track_id,
    ):
        raise ValueError("continuation state and anchor arm-track identities differ")
    if continuation is not None:
        previous: BoundaryAnchor | ContinuationHour = anchor
        for hour in continuation:
            _validate_next_identity(previous, hour)
            previous = hour
    if registered_completion_deadline_hours is None:
        return ContinuationAssessment(
            status="blocked_missing_registered_completion_deadline",
            completion_can_be_evaluated=False,
            observed_hours=0 if continuation is None else len(continuation),
            registered_completion_deadline_hours=None,
            observed_violations=observed_violations,
        )
    if (
        isinstance(registered_completion_deadline_hours, bool)
        or not isinstance(registered_completion_deadline_hours, Integral)
        or registered_completion_deadline_hours <= 0
    ):
        raise ValueError("registered completion deadline must be a positive integer")
    if continuation is None:
        return ContinuationAssessment(
            status="blocked_right_censored_unknown_continuation",
            completion_can_be_evaluated=False,
            observed_hours=0,
            registered_completion_deadline_hours=int(registered_completion_deadline_hours),
            observed_violations=observed_violations,
        )
    if len(continuation) < registered_completion_deadline_hours:
        status = "blocked_right_censored_incomplete_continuation"
    else:
        status = "continuation_inputs_complete_not_solved"
    return ContinuationAssessment(
        status=status,
        completion_can_be_evaluated=False,
        observed_hours=len(continuation),
        registered_completion_deadline_hours=int(registered_completion_deadline_hours),
        observed_violations=observed_violations,
    )


__all__ = [
    "SERVICE_TOLERANCE",
    "BoundaryAnchor",
    "ContinuationAssessment",
    "ContinuationHour",
    "TemporalCarryState",
    "advance_continuous_state",
    "assess_observed_continuation",
    "carry_state_across_boundary",
]
