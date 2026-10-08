"""Draft prescribed actual-action continuation, separate from the halted policy.

Actions are mechanism assumptions. This validates actions, not a causal fallback
controller, observed operation, or the feasibility of an alternative policy.
"""
from dataclasses import dataclass
from fractions import Fraction as Q

from .boundary import _number, _validate_next_identity
from .causal_policy import CurrentObservation, PolicyCursor
from .four_arm_replay import (
    ArmCursor, ArmStep, CohortAction, NETWORK, CFE, JOINT, advance_arm_replay, _effective_call,
)


@dataclass(frozen=True)
class DeclaredActualAction:
    recovery: float
    actual_service_power: float
    allocations: tuple[tuple[int, Q], ...]
    evidence_class: str = 'mechanism_assumption'

    def __post_init__(self):
        _number(self.recovery, 'actual recovery')
        _number(self.actual_service_power, 'actual service power')
        if self.evidence_class != 'mechanism_assumption':
            raise ValueError('this draft only supports assumed actual actions')
        if not isinstance(self.allocations, tuple):
            raise ValueError('immutable allocations required')
        for item in self.allocations:
            if (not isinstance(item, tuple) or len(item) != 2 or type(item[0]) is not int
                or item[0] < 0 or not isinstance(item[1], Q) or item[1] < 0):
                raise ValueError('allocation requires birth hour and exact nonnegative work')


def _evaluate_actual(before, observation, action):
    try:
        hour = observation.hour
        if (hour.arm_id, hour.track_id) != (JOINT, 'shared'):
            raise ValueError('common JOINT/shared source container required')
        for _, track in before.tracks:
            _validate_next_identity(track.physical.anchor, hour)
        if action is None:
            return 'unassessed', 'missing_actual_action', None
        call = _effective_call(hour.grid_request if before.arm_id != CFE else 0.,
                               hour.cfe_request if before.arm_id != NETWORK else 0.)
        physical = observation.limits.action(action.recovery, action.actual_service_power)
        step = advance_arm_replay(before, hour=hour, due_hour=observation.due_hour if call else None,
            actions={'shared': CohortAction(physical, action.allocations)})
    except (ValueError, OverflowError) as error:
        return 'unassessed', str(error), None
    return 'assumed_action_validated', None, step


@dataclass(frozen=True)
class ActualActionRecord:
    before: ArmCursor
    observation: CurrentObservation
    action: DeclaredActualAction | None
    status: str
    error: str | None
    step: ArmStep | None

    def __post_init__(self):
        if not isinstance(self.observation, CurrentObservation):
            raise ValueError('one current observation required')
        if self.action is not None and not isinstance(self.action, DeclaredActualAction):
            raise ValueError('typed declared actual action required')
        if self.before.mode != 'physical_execution':
            raise ValueError('shared physical state required')
        if (self.status, self.error, self.step) != _evaluate_actual(self.before, self.observation, self.action):
            raise ValueError('actual-action record does not match replay')


@dataclass(frozen=True)
class ActualActionCursor:
    origin: PolicyCursor
    records: tuple[ActualActionRecord, ...] = ()

    def __post_init__(self):
        if not isinstance(self.origin, PolicyCursor) or not self.origin.halted:
            raise ValueError('halted original policy prefix required')
        rejection = self.origin.records[-1]
        if rejection.stage not in {'physical_execution', 'shared_execution'}:
            raise ValueError('input, decision, or planning rejection requires separate diagnosis')
        if not isinstance(self.records, tuple):
            raise ValueError('immutable actual-action records required')
        previous = self.origin.execution
        for i, record in enumerate(self.records):
            if not isinstance(record, ActualActionRecord) or record.before != previous:
                raise ValueError('actual-action state chain mismatch')
            if i == 0 and record.observation != rejection.observation:
                raise ValueError('first actual action must address the exact rejected observation')
            if record.step is None:
                if i != len(self.records)-1:
                    raise ValueError('unassessed hour cannot have a simulated suffix')
            else:
                previous = record.step.cursor

    @property
    def execution(self):
        accepted = [r for r in self.records if r.step is not None]
        return accepted[-1].step.cursor if accepted else self.origin.execution

    @property
    def stopped(self):
        return bool(self.records and self.records[-1].step is None)


def advance_actual_action(cursor: ActualActionCursor, observation: CurrentObservation,
                          action: DeclaredActualAction | None) -> ActualActionCursor:
    """Validate one explicit assumed actual action; never choose or repair it."""
    if cursor.stopped:
        raise ValueError('unassessed actual hour cannot consume a later observation')
    if not isinstance(observation, CurrentObservation):
        raise ValueError('one current observation required')
    if action is not None and not isinstance(action, DeclaredActualAction):
        raise ValueError('typed declared actual action required')
    record = ActualActionRecord(cursor.execution, observation, action,
                                 *_evaluate_actual(cursor.execution, observation, action))
    return ActualActionCursor(cursor.origin, cursor.records+(record,))
