"""Draft four-arm prescribed-action replay with bound physical/cohort states."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction as Q
import hashlib
import json
from collections.abc import Mapping

from .boundary import BoundaryAnchor, ContinuationHour, TemporalCarryState, SERVICE_TOLERANCE
from .multiday import JointReplayCursor, ServiceAction, initialize_joint_replay, replay_joint_chunk
from .debt_cohorts import DebtLedger, advance_debt_ledger

NETWORK = "network_only_shared"
CFE = "cfe_only_shared"
JOINT = "joint_correct_shared"
B6 = "joint_b6_separate_planning_shared_execution"


@dataclass(frozen=True)
class BoundTrack:
    physical: JointReplayCursor
    ledger: DebtLedger


@dataclass(frozen=True)
class ArmCursor:
    arm_id: str
    mode: str
    tracks: tuple[tuple[str, BoundTrack], ...]
    last_plan_cursor: ArmCursor | None = None

    def __post_init__(self) -> None:
        if self.arm_id not in {NETWORK, CFE, JOINT, B6}:
            raise ValueError("unknown arm")
        if self.mode not in {"physical_execution", "separate_planning"}:
            raise ValueError("unknown replay mode")
        if self.mode == "separate_planning" and self.arm_id != B6:
            raise ValueError("separate planning is B6 only")
        expected = ("grid", "cfe") if self.mode == "separate_planning" else ("shared",)
        if not isinstance(self.tracks, tuple) or tuple(name for name, _ in self.tracks) != expected:
            raise ValueError("cursor track inventory mismatch")
        if self.last_plan_cursor is not None and (self.arm_id != B6 or self.mode != "physical_execution"):
            raise ValueError("plan history is only valid for B6 execution")
        if self.last_plan_cursor is not None and (
            not isinstance(self.last_plan_cursor, ArmCursor)
            or self.last_plan_cursor.arm_id != B6 or self.last_plan_cursor.mode != "separate_planning"
        ):
            raise ValueError("invalid B6 planning history cursor")


@dataclass(frozen=True)
class CohortAction:
    physical: ServiceAction
    allocations: tuple[tuple[int, Q], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.physical, ServiceAction):
            raise ValueError("physical ServiceAction required")
        if not isinstance(self.allocations, tuple) or any(
            not isinstance(pair, tuple) or len(pair) != 2 for pair in self.allocations
        ):
            raise ValueError("allocations must contain immutable pairs")


@dataclass(frozen=True)
class ArmStep:
    before: ArmCursor
    cursor: ArmCursor
    hour: ContinuationHour
    due_hour: int | None
    actions: tuple[tuple[str, CohortAction], ...]


def _identity(arm_id, mode, name, physical):
    anchor = physical.anchor
    identity = {key: getattr(anchor, key) for key in BoundaryAnchor.__dataclass_fields__
                if key not in {"power_source_hour", "workload_source_hour"}}
    identity["source_hour_offset"] = anchor.workload_source_hour-anchor.power_source_hour
    return hashlib.sha256(json.dumps(
        [arm_id, mode, name, identity, list(physical.envelope), physical.state.accounting_period_id],
        sort_keys=True, allow_nan=False,
    ).encode()).hexdigest()


def initialize_arm_replay(
    arm_id: str, *, mode: str, anchor: BoundaryAnchor, envelope: Mapping[str, float | int],
    accounting_period_id: str, zero_carry_in_assumption: bool,
) -> ArmCursor:
    """Initialize a synthetic zero-history scenario, never infer empirical carry-in.

    Shared source anchors use JOINT/shared as a common four-arm input container.
    Arm identity is bound separately in this cursor and its ledger identity.
    """
    if arm_id not in {NETWORK, CFE, JOINT, B6}:
        raise ValueError("unknown arm")
    if mode not in {"physical_execution", "separate_planning"}:
        raise ValueError("unknown replay mode")
    if mode == "separate_planning" and arm_id != B6:
        raise ValueError("separate planning is B6 only")
    if zero_carry_in_assumption is not True:
        raise ValueError("explicit zero carry-in assumption required; nonzero adapter not implemented")
    state = TemporalCarryState(JOINT, "shared", 0., False, 0., None, 0, 0., 0., False,
                               accounting_period_id)
    physical = initialize_joint_replay(state, anchor=anchor, envelope=envelope)
    names = ("grid", "cfe") if mode == "separate_planning" else ("shared",)
    tracks = []
    for name in names:
        identity = _identity(arm_id, mode, name, physical)
        ledger = DebtLedger(identity, accounting_period_id, anchor.power_source_hour)
        tracks.append((name, BoundTrack(physical, ledger)))
    return ArmCursor(arm_id, mode, tuple(tracks))


def _effective(value: float) -> Q:
    return Q(0) if value <= SERVICE_TOLERANCE else Q(str(value))


def _effective_call(grid: float, cfe: float) -> Q:
    # Use the existing float cutoff, then add decimal source values exactly.
    # Fraction(str(grid + cfe)) would invent a debt of 4e-17 for 0.1 + 0.2.
    return Q(0) if grid+cfe <= SERVICE_TOLERANCE else Q(str(grid))+Q(str(cfe))


def advance_arm_replay(
    cursor: ArmCursor, *, hour: ContinuationHour, due_hour: int | None,
    actions: Mapping[str, CohortAction],
) -> ArmStep:
    """Advance all tracks atomically; deadlines apply to this hour's new debt.

    This adapter uses one common deadline per birth hour. It neither chooses
    recovery allocations nor certifies an optimal or causal policy.
    """
    if (hour.arm_id, hour.track_id) != (JOINT, "shared"):
        raise ValueError("four-arm input requires the common JOINT/shared source container")
    if set(actions) != {name for name, _ in cursor.tracks}:
        raise ValueError("action tracks do not match replay mode")
    updated = []
    any_call = False
    for name, track in cursor.tracks:
        if (track.ledger.trajectory_identity != _identity(cursor.arm_id, cursor.mode, name, track.physical)
            or track.ledger.last_hour != track.physical.anchor.power_source_hour
            or track.ledger.accounting_period_id != track.physical.state.accounting_period_id):
            raise ValueError("physical and cohort state identity mismatch")
        if (abs(float(track.ledger.debt)-track.physical.state.recovery_debt) > 1e-12
            or abs(float(sum((c.incurred for c in track.ledger.cohorts), Q(0)))
                   - track.physical.state.cumulative_call_energy) > 1e-12):
            raise ValueError("physical and cohort carry-in balances mismatch")
        use_grid = name == "grid" or (name == "shared" and cursor.arm_id != CFE)
        use_cfe = name == "cfe" or (name == "shared" and cursor.arm_id != NETWORK)
        projected = replace(hour, grid_request=hour.grid_request if use_grid else 0.,
                            cfe_request=hour.cfe_request if use_cfe else 0.)
        action = actions[name]
        if not isinstance(action.allocations, tuple):
            raise ValueError("cohort allocations must be immutable")
        physical_action = action.physical
        if not use_cfe:
            physical_action = replace(physical_action,
                cfe_compatible_surplus=physical_action.business_recovery_headroom)
        call = _effective_call(projected.grid_request, projected.cfe_request)
        recovery = _effective(physical_action.recovery)
        any_call = any_call or bool(call)
        # Validate power/headroom and chronology before accepting debt accounting.
        advanced = replay_joint_chunk(track.physical, hours=(projected,), actions=(physical_action,))
        eta = Q(str(dict(track.physical.envelope)["recovery_efficiency"]))
        for _, amount in action.allocations:
            if not isinstance(amount, Q) or amount < 0:
                raise ValueError("allocation must be nonnegative exact work-energy")
        if sum((amount for _, amount in action.allocations), Q(0)) != eta * recovery:
            raise ValueError("allocations do not equal effective physical recovery work")
        ledger = advance_debt_ledger(track.ledger, hour=hour.power_source_hour,
            trajectory_identity=track.ledger.trajectory_identity,
            accounting_period_id=track.physical.state.accounting_period_id,
            incurred=call, due_hour=due_hour if call else None,
            deadline_evidence="mechanism_assumption" if call and due_hour is not None else "unidentified",
            allocations=action.allocations)
        # Float physical state and exact decimal-input ledger must agree.
        if abs(float(ledger.debt) - advanced.cursor.state.recovery_debt) > 1e-12:
            raise ValueError("physical and cohort debt diverged")
        updated.append((name, BoundTrack(advanced.cursor, ledger)))
    if due_hour is not None and not any_call:
        raise ValueError("deadline supplied without effective new debt")
    return ArmStep(cursor, ArmCursor(cursor.arm_id, cursor.mode, tuple(updated), cursor.last_plan_cursor), hour, due_hour,
                   tuple((name, actions[name]) for name, _ in cursor.tracks))


def execute_b6_planned_step(
    execution: ArmCursor, *, planned: ArmStep, shared_limits: ServiceAction,
) -> ArmStep:
    """Replay a successful separate-planning step in a shared physical envelope.

    Recovery and actual power are derived from the prescribed plan; only common
    physical limits are provided by the caller. No shared feasibility is inferred
    from separate-track success.
    """
    if execution.arm_id != B6 or execution.mode != "physical_execution":
        raise ValueError("B6 shared execution cursor required")
    if planned.cursor.arm_id != B6 or planned.cursor.mode != "separate_planning":
        raise ValueError("successful B6 separate-planning step required")
    if tuple(name for name, _ in planned.actions) != ("grid", "cfe"):
        raise ValueError("B6 planned action inventory mismatch")
    verified = advance_arm_replay(planned.before, hour=planned.hour, due_hour=planned.due_hour,
                                  actions=dict(planned.actions))
    if verified != planned:
        raise ValueError("B6 planned step does not match its replayed actions and state")
    physical = dict(execution.tracks)["shared"].physical
    if any(track.physical.envelope != physical.envelope or
           track.physical.state.accounting_period_id != physical.state.accounting_period_id
           for _, track in planned.before.tracks):
        raise ValueError("planning and execution envelope differ")
    if execution.last_plan_cursor is not None:
        if planned.before != execution.last_plan_cursor:
            raise ValueError("B6 plan history changed")
    else:
        if any(track.physical.anchor != physical.anchor or track.ledger.cohorts
               for _, track in planned.before.tracks) or physical.state.cumulative_call_energy != 0:
            raise ValueError("B6 execution must start from the same zero-history plan anchor")
    actions = dict(planned.actions)
    recovery = float(sum((_effective(a.physical.recovery) for a in actions.values()), Q(0)))
    call = float(_effective(planned.hour.grid_request + planned.hour.cfe_request))
    power = planned.hour.workload_occupancy - call + float(_effective(recovery))
    # Input recovery/power fields are checked, never silently overridden.
    if shared_limits.recovery != recovery or shared_limits.actual_service_power != power:
        raise ValueError("shared action must exactly replay planned recovery and power")
    allocations = {}
    for a in actions.values():
        for cohort_id, amount in a.allocations:
            allocations[cohort_id] = allocations.get(cohort_id, Q(0)) + amount
    result = advance_arm_replay(execution, hour=planned.hour, due_hour=planned.due_hour,
        actions={"shared": CohortAction(shared_limits, tuple(sorted(allocations.items())))})
    return replace(result, cursor=replace(result.cursor, last_plan_cursor=planned.cursor))
