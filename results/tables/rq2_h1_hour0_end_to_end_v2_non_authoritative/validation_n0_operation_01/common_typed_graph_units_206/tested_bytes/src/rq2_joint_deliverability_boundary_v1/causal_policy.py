"""Draft causal full-request-or-stop policy with immutable prefix audit records."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction as Q
from math import nextafter
from collections.abc import Mapping

from .boundary import BoundaryAnchor, ContinuationHour, SERVICE_TOLERANCE, _number, _validate_next_identity
from .multiday import ServiceAction
from .debt_cohorts import assess_debt_cohorts
from .four_arm_replay import (
    NETWORK, CFE, JOINT, B6, ArmCursor, ArmStep, CohortAction,
    initialize_arm_replay, advance_arm_replay, execute_b6_planned_step, _effective, _effective_call,
)


@dataclass(frozen=True)
class FixedPolicy:
    rule: str = "full_request_edf_known_then_unknown_fifo_v1"
    recovery_decimal_places: int = 12

    def __post_init__(self) -> None:
        if self.rule != "full_request_edf_known_then_unknown_fifo_v1":
            raise ValueError("unimplemented fixed policy")
        if type(self.recovery_decimal_places) is not int or not 0 <= self.recovery_decimal_places <= 12:
            raise ValueError("recovery precision must be an integer from 0 to 12")


@dataclass(frozen=True)
class HourlyLimits:
    call_limit: float
    business_recovery_headroom: float
    cfe_compatible_surplus: float
    maximum_recovery_power: float

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _number(getattr(self, name), name)

    def action(self, recovery: float, power: float) -> ServiceAction:
        return ServiceAction(recovery, power, self.call_limit, self.business_recovery_headroom,
                             self.cfe_compatible_surplus, self.maximum_recovery_power)


@dataclass(frozen=True)
class CurrentObservation:
    hour: ContinuationHour
    limits: HourlyLimits
    due_hour: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.hour, ContinuationHour) or not isinstance(self.limits, HourlyLimits):
            raise ValueError("one typed current observation required")
        if self.due_hour is not None and (
            type(self.due_hour) is not int or self.due_hour < self.hour.power_source_hour
        ):
            raise ValueError("current debt deadline must not precede its birth hour")
        if self.due_hour is not None and self.hour.grid_request+self.hour.cfe_request <= SERVICE_TOLERANCE:
            raise ValueError("deadline without effective source obligations")


@dataclass(frozen=True)
class PolicyRecord:
    policy: FixedPolicy
    before_execution: ArmCursor
    before_planning: ArmCursor | None
    observation: CurrentObservation
    status: str
    stage: str
    error: str | None
    attempted_actions: tuple[tuple[str, CohortAction], ...]
    planned_step: ArmStep | None
    accepted_step: ArmStep | None

    def __post_init__(self) -> None:
        if self.status not in {"accepted", "rejected_uncommitted"}:
            raise ValueError("unknown policy record status")
        if self.status == "accepted" and (self.error is not None or not isinstance(self.accepted_step, ArmStep)):
            raise ValueError("accepted record requires a successful step and no error")
        if self.status == "rejected_uncommitted" and (
            not isinstance(self.error, str) or not self.error or self.accepted_step is not None
        ):
            raise ValueError("rejected record requires error and no accepted step")
        if not isinstance(self.attempted_actions, tuple):
            raise ValueError("immutable attempted actions required")
        expected = _evaluate_current_hour(self.policy, self.before_execution, self.before_planning,
                                          self.observation)
        if expected != (self.status, self.stage, self.error, self.attempted_actions,
                        self.planned_step, self.accepted_step):
            raise ValueError("policy audit record does not match deterministic replay")


@dataclass(frozen=True)
class PolicyCursor:
    policy: FixedPolicy
    execution: ArmCursor
    planning: ArmCursor | None
    records: tuple[PolicyRecord, ...] = ()
    halted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.policy, FixedPolicy) or self.execution.mode != "physical_execution":
            raise ValueError("fixed policy and physical execution cursor required")
        if self.execution.arm_id == B6:
            if not isinstance(self.planning, ArmCursor) or self.planning.arm_id != B6 or self.planning.mode != "separate_planning":
                raise ValueError("B6 requires its separate-planning cursor")
        elif self.planning is not None:
            raise ValueError("only B6 carries a separate-planning cursor")
        if not isinstance(self.records, tuple) or type(self.halted) is not bool:
            raise ValueError("immutable audit records and boolean halt required")
        if any(r.policy != self.policy for r in self.records):
            raise ValueError("policy cannot change within an observed prefix")
        if any(r.status != "accepted" for r in self.records[:-1]):
            raise ValueError("a rejected prefix cannot have subsequent records")
        if self.halted != bool(self.records and self.records[-1].status == "rejected_uncommitted"):
            raise ValueError("halt status and audit record disagree")
        for i, record in enumerate(self.records):
            if i and (record.before_execution != self.records[i-1].accepted_step.cursor or
                      record.before_planning != (self.records[i-1].planned_step.cursor
                          if self.records[i-1].planned_step is not None else None)):
                raise ValueError("policy audit prefix state chain changed")
        if self.records:
            last = self.records[-1]
            execution = last.accepted_step.cursor if last.accepted_step is not None else last.before_execution
            planning = (last.planned_step.cursor if last.planned_step is not None else None) if last.status == "accepted" else last.before_planning
            if self.execution != execution or self.planning != planning:
                raise ValueError("committed state must match the last audit record")


def initialize_causal_policy(
    arm_id: str, *, policy: FixedPolicy, anchor: BoundaryAnchor,
    envelope: Mapping[str, float | int], accounting_period_id: str,
    zero_carry_in_assumption: bool,
) -> PolicyCursor:
    if not isinstance(policy, FixedPolicy):
        raise ValueError("explicit immutable fixed policy required")
    args = dict(anchor=anchor, envelope=envelope, accounting_period_id=accounting_period_id,
                zero_carry_in_assumption=zero_carry_in_assumption)
    execution = initialize_arm_replay(arm_id, mode="physical_execution", **args)
    planning = initialize_arm_replay(B6, mode="separate_planning", **args) if arm_id == B6 else None
    return PolicyCursor(policy, execution, planning)


def _choose_actions(policy: FixedPolicy, cursor: ArmCursor, observation: CurrentObservation):
    """No forecast, future row, horizon length, or callable policy is accepted."""
    hour, limits = observation.hour, observation.limits
    if cursor.arm_id == B6:
        separate = _effective_call(hour.grid_request, 0.)+_effective_call(0., hour.cfe_request)
        shared = _effective_call(hour.grid_request, hour.cfe_request)
        if separate != shared:
            raise ValueError("B6 separate and shared effective obligations differ")
    actions = {}
    any_call = False
    for name, track in cursor.tracks:
        use_grid = name == "grid" or (name == "shared" and cursor.arm_id != CFE)
        use_cfe = name == "cfe" or (name == "shared" and cursor.arm_id != NETWORK)
        raw_call = (hour.grid_request if use_grid else 0.) + (hour.cfe_request if use_cfe else 0.)
        call = float(_effective(raw_call))
        any_call = any_call or call > 0
        recovery = 0.
        allocations = []
        if not call and track.ledger.debt:
            eta = Q(str(dict(track.physical.envelope)["recovery_efficiency"]))
            cap = min(Q(str(limits.business_recovery_headroom)), Q(str(limits.maximum_recovery_power)),
                      track.ledger.debt/eta)
            if use_cfe:
                cap = min(cap, Q(str(limits.cfe_compatible_surplus)))
            scale = 10 ** policy.recovery_decimal_places
            quantized = Q((cap*scale).numerator//(cap*scale).denominator, scale)
            recovery = float(quantized)
            if Q(str(recovery)) > cap:
                recovery = nextafter(recovery, 0.)
            if Q(str(recovery)) > cap:
                raise ValueError("conservative recovery representation failed")
            recovery = float(_effective(recovery))
            work = eta*Q(str(recovery))
            ordered = sorted(track.ledger.cohorts, key=lambda c: (
                c.due_hour is None, c.due_hour if c.due_hour is not None else c.created_hour, c.created_hour))
            for cohort in ordered:
                amount = min(work, cohort.remaining)
                if amount:
                    allocations.append((cohort.created_hour, amount))
                    work -= amount
            if work:
                raise ValueError("policy recovery allocation exceeds existing debt")
        # Negative candidate power means the full obligation cannot be represented
        # by a nonnegative physical action; do not clip the original request.
        power = hour.workload_occupancy-call+recovery
        if power < 0:
            raise ValueError("full service call exceeds baseline power")
        actions[name] = CohortAction(limits.action(recovery, power), tuple(allocations))
    return actions, observation.due_hour if any_call else None


def _evaluate_current_hour(policy, execution, planning, observation):
    """Pure decision/replay result, also used to validate an audit record."""
    stage = "input_validation"
    actions = {}
    planned = None
    try:
        if (observation.hour.arm_id, observation.hour.track_id) != (JOINT, "shared"):
            raise ValueError("common JOINT/shared source container required")
        for _, track in execution.tracks:
            _validate_next_identity(track.physical.anchor, observation.hour)
        if planning is not None:
            for _, track in planning.tracks:
                _validate_next_identity(track.physical.anchor, observation.hour)
        stage = "policy_decision"
        source = planning if planning is not None else execution
        actions, due = _choose_actions(policy, source, observation)
        if planning is None:
            stage = "physical_execution"
            accepted = advance_arm_replay(execution, hour=observation.hour, due_hour=due, actions=actions)
        else:
            stage = "separate_planning"
            planned = advance_arm_replay(planning, hour=observation.hour, due_hour=due, actions=actions)
            stage = "shared_execution"
            recovery = float(sum((_effective(a.physical.recovery) for a in actions.values()), Q(0)))
            call = float(_effective(observation.hour.grid_request+observation.hour.cfe_request))
            power = observation.hour.workload_occupancy-call+float(_effective(recovery))
            if power < 0:
                raise ValueError("full shared call exceeds baseline power")
            accepted = execute_b6_planned_step(execution, planned=planned,
                shared_limits=observation.limits.action(recovery, power))
    except (ValueError, OverflowError) as error:
        return "rejected_uncommitted", stage, str(error), tuple(actions.items()), planned, None
    return "accepted", stage, None, tuple(actions.items()), planned, accepted


def advance_causal_policy(cursor: PolicyCursor, observation: CurrentObservation) -> PolicyCursor:
    """Process one revealed hour; first rejection locks the diagnostic prefix.

    No state is advanced on rejection, including when B6 planning succeeds but
    shared execution fails. A rejected action is not mathematical infeasibility.
    """
    if cursor.halted:
        raise ValueError("halted policy prefix cannot consume later observations")
    if not isinstance(observation, CurrentObservation):
        raise ValueError("one CurrentObservation required")
    outcome = _evaluate_current_hour(cursor.policy, cursor.execution, cursor.planning, observation)
    record = PolicyRecord(cursor.policy, cursor.execution, cursor.planning, observation, *outcome)
    if record.status == "rejected_uncommitted":
        return replace(cursor, records=cursor.records+(record,), halted=True)
    return PolicyCursor(cursor.policy, record.accepted_step.cursor,
                        record.planned_step.cursor if record.planned_step is not None else None,
                        cursor.records+(record,))


def summarize_policy_prefix(cursor: PolicyCursor) -> dict:
    """Report accepted exposure and observed debt statuses; no risk probability."""
    tracks = dict(cursor.execution.tracks)
    statuses = tuple((name, cohort, status) for name, track in tracks.items()
                     for cohort, status in assess_debt_cohorts(track.ledger))
    return {
        "policy_rule": cursor.policy.rule,
        "status": "halted_on_rejection" if cursor.halted else "observed_prefix_only",
        "submitted_hours": len(cursor.records),
        "accepted_hours": sum(r.status == "accepted" for r in cursor.records),
        "last_committed_power_hour": next(iter(tracks.values())).physical.anchor.power_source_hour,
        "rejected_power_hour": cursor.records[-1].observation.hour.power_source_hour if cursor.halted else None,
        "remaining_debt": tuple((name, track.ledger.debt) for name, track in tracks.items()),
        "cohort_statuses": statuses,
        "deadline_missed_count": sum(status == "deadline_missed" for _, _, status in statuses),
        "deadline_unidentified_count": sum(status == "deadline_unidentified" for _, _, status in statuses),
        "right_censored_count": sum(status == "right_censored_before_deadline" for _, _, status in statuses),
        "completion_claim_allowed": False,
        "formal_result": False,
    }
