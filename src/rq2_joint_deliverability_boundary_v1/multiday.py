"""Non-authoritative replay of prescribed joint-service actions, without a solver."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .boundary import (
    BoundaryAnchor, ContinuationHour, TemporalCarryState, SERVICE_TOLERANCE,
    _number, advance_continuous_state, carry_state_across_boundary,
)


@dataclass(frozen=True)
class ServiceAction:
    recovery: float
    actual_service_power: float
    call_limit: float
    business_recovery_headroom: float
    cfe_compatible_surplus: float
    maximum_recovery_power: float

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _number(getattr(self, name), name)


@dataclass(frozen=True)
class JointReplayCursor:
    """Keep a replay's state, last observation and fixed contract together.

    Constructing the initial cursor is an explicit scenario initialization;
    continuation must use the returned cursor, not reinitialize from its fields.
    """
    state: TemporalCarryState
    anchor: BoundaryAnchor | ContinuationHour
    envelope: tuple[tuple[str, float | int], ...]


def initialize_joint_replay(
    state: TemporalCarryState, *, anchor: BoundaryAnchor,
    envelope: Mapping[str, float | int],
) -> JointReplayCursor:
    if (state.arm_id, state.track_id) != ("joint_correct_shared", "shared"):
        raise ValueError("replay supports only joint_correct_shared")
    if (anchor.arm_id, anchor.track_id) != (state.arm_id, state.track_id):
        raise ValueError("initial state and anchor arm-track identities differ")
    if state.recovery_debt > state.cumulative_call_energy + SERVICE_TOLERANCE:
        raise ValueError("carry-in debt exceeds carried cumulative call energy")
    if state.cumulative_call_energy > SERVICE_TOLERANCE and not state.has_prior_event:
        raise ValueError("carry-in energy requires the prior event history")
    required = {
        "recovery_efficiency", "time_step_hours", "maximum_event_duration_hours",
        "maximum_event_count", "normalized_energy_budget", "normalized_debt_limit",
        "minimum_recovery_hours",
    }
    if set(envelope) != required or envelope["time_step_hours"] != 1:
        raise ValueError("replay requires the explicit hourly envelope")
    for name, value in envelope.items():
        _number(value, name)
    if not 0 < envelope["recovery_efficiency"] <= 1:
        raise ValueError("recovery efficiency must be in (0, 1]")
    if envelope["maximum_event_duration_hours"] <= 0:
        raise ValueError("maximum event duration must be positive")
    count = envelope["maximum_event_count"]
    if not isinstance(count, int):
        raise ValueError("maximum event count must be an integer")
    for value, bound, name in (
        (state.recovery_debt, envelope["normalized_debt_limit"], "debt"),
        (state.cumulative_call_energy, envelope["normalized_energy_budget"], "energy"),
        (state.event_count, count, "event count"),
        (state.active_duration_hours, envelope["maximum_event_duration_hours"], "duration"),
    ):
        if value > bound + SERVICE_TOLERANCE:
            raise ValueError(f"initial {name} limit violated")
    return JointReplayCursor(state, anchor, tuple(sorted(envelope.items())))


@dataclass(frozen=True)
class JointReplayResult:
    states: tuple[TemporalCarryState, ...]
    cursor: JointReplayCursor


def replay_joint_chunk(
    cursor: JointReplayCursor,
    *,
    hours: Sequence[ContinuationHour],
    actions: Sequence[ServiceAction],
) -> JointReplayResult:
    """Audit an additive shared ledger; actions and normalized demand are explicit.

    Fail at the first invalid hour. A raised error is an action/contract violation,
    never a solver infeasibility certificate. No tail or initial state is inferred.
    """
    if len(hours) != len(actions):
        raise ValueError("every observed hour needs an explicit action")
    state = cursor.state
    envelope = dict(cursor.envelope)
    states = []
    previous = cursor.anchor
    for hour, action in zip(hours, actions):
        state = carry_state_across_boundary(state, anchor=previous, next_hour=hour)
        # In this mechanism scenario, workload_occupancy is normalized baseline
        # power, not a measured CPU-to-power mapping.
        call = hour.grid_request + hour.cfe_request
        call = 0.0 if call <= SERVICE_TOLERANCE else call
        recovery = 0.0 if action.recovery <= SERVICE_TOLERANCE else action.recovery
        if call > hour.workload_occupancy + SERVICE_TOLERANCE:
            raise ValueError("call exceeds baseline service power")
        expected_power = hour.workload_occupancy - call + recovery
        if abs(action.actual_service_power - expected_power) > SERVICE_TOLERANCE:
            raise ValueError("service power balance violated")
        state = advance_continuous_state(
            state, call=call, call_limit=action.call_limit,
            recovery=recovery,
            recovery_headroom=min(action.business_recovery_headroom,
                                  action.cfe_compatible_surplus),
            maximum_recovery_power=action.maximum_recovery_power,
            **envelope,
        )
        states.append(state)
        previous = hour
    return JointReplayResult(tuple(states), JointReplayCursor(state, previous, cursor.envelope))
