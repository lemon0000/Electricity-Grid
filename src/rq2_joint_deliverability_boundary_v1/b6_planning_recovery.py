"""Draft B6 policy with an explicit shared successor after planning rejection."""
from dataclasses import asdict, dataclass
import hashlib
import json

from .boundary import _validate_next_identity
from .causal_policy import (
    FixedPolicy, CurrentObservation, PolicyCursor, initialize_causal_policy,
    advance_causal_policy, _choose_actions,
)
from .actual_actions import DeclaredActualAction, ActualActionRecord, _evaluate_actual
from .four_arm_replay import ArmCursor, JOINT, B6
from .debt_cohorts import assess_debt_cohorts


TRIGGERS = ('separate_planning', 'shared_execution')
RULE = 'b6_primary_then_permanent_shared_after_planning_or_execution_rejection_v1'


@dataclass(frozen=True)
class B6PlanningRecoveryPolicy:
    primary: FixedPolicy = FixedPolicy()
    recovery: FixedPolicy = FixedPolicy()
    rule: str = RULE

    def __post_init__(self):
        if self.rule != RULE or not all(isinstance(p, FixedPolicy) for p in (self.primary, self.recovery)):
            raise ValueError('fixed B6 primary and shared successor required')

    @classmethod
    def from_config(cls, config):
        expected = {
            'schema': 'rq2_continuous_b6_planning_recovery_v1',
            'status': 'DRAFT_NONAUTHORITATIVE', 'arm_id': B6, 'rule': RULE,
            'trigger_stages': list(TRIGGERS),
            'transition': 'same_rejected_observation_then_permanent_shared_state',
            'failure': 'unassessed_stop', 'evidence_class': 'mechanism_assumption',
        }
        gates = {'continuous_service_protocol_registered', 'formal_experiment_authorized',
                 'formal_result', 'paper_claim', 'security_certified'}
        if (set(config) != set(expected) | gates | {'primary', 'recovery'}
            or any(config[k] != v for k, v in expected.items())
            or any(config[k] is not False for k in gates)):
            raise ValueError('configuration differs from draft policy semantics')
        return cls(FixedPolicy(**config['primary']), FixedPolicy(**config['recovery']))

    @property
    def policy_id(self):
        payload = dict(asdict(self), arm_id=B6, trigger_stages=TRIGGERS,
                       transition='same_rejected_observation_then_permanent_shared_state',
                       failure='unassessed_stop', evidence_class='mechanism_assumption')
        return self.rule + ':' + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _decide_shared(spec, before, observation):
    stage = 'input_validation'
    try:
        if (observation.hour.arm_id, observation.hour.track_id) != (JOINT, 'shared'):
            raise ValueError('common JOINT/shared source container required')
        for _, track in before.tracks:
            _validate_next_identity(track.physical.anchor, observation.hour)
        stage = 'recovery_decision'
        actions, _ = _choose_actions(spec.recovery, before, observation)
        candidate = actions['shared']
        action = DeclaredActualAction(candidate.physical.recovery,
            candidate.physical.actual_service_power, candidate.allocations)
        stage = 'actual_validation'
        record = ActualActionRecord(before, observation, action,
                                     *_evaluate_actual(before, observation, action))
    except (ValueError, OverflowError) as error:
        return stage, str(error), None
    return stage, record.error, record


@dataclass(frozen=True)
class SharedSuccessorDecision:
    spec: B6PlanningRecoveryPolicy
    before: ArmCursor
    observation: CurrentObservation
    stage: str
    error: str | None
    actual_record: ActualActionRecord | None

    def __post_init__(self):
        if not isinstance(self.spec, B6PlanningRecoveryPolicy):
            raise ValueError('typed successor specification required')
        if not isinstance(self.before, ArmCursor) or (self.before.arm_id, self.before.mode) != (B6, 'physical_execution'):
            raise ValueError('B6 shared physical state required')
        if not isinstance(self.observation, CurrentObservation):
            raise ValueError('one current observation required')
        if (self.stage, self.error, self.actual_record) != _decide_shared(self.spec, self.before, self.observation):
            raise ValueError('successor decision differs from deterministic replay')


@dataclass(frozen=True)
class B6PlanningRecoveryCursor:
    spec: B6PlanningRecoveryPolicy
    policy_id: str
    primary: PolicyCursor
    decisions: tuple[SharedSuccessorDecision, ...] = ()

    def __post_init__(self):
        if not isinstance(self.spec, B6PlanningRecoveryPolicy) or self.policy_id != self.spec.policy_id:
            raise ValueError('successor policy identity changed')
        if (not isinstance(self.primary, PolicyCursor) or self.primary.policy != self.spec.primary
            or self.primary.execution.arm_id != B6):
            raise ValueError('original B6 policy required')
        if not isinstance(self.decisions, tuple):
            raise ValueError('immutable successor history required')
        triggered = self.primary.halted and self.primary.records[-1].stage in TRIGGERS
        if triggered and not self.decisions:
            raise ValueError('triggered rejection requires its same-hour decision')
        if self.decisions and not triggered:
            raise ValueError('successor requires a supported original rejection')
        previous = self.primary.execution
        for i, record in enumerate(self.decisions):
            if not isinstance(record, SharedSuccessorDecision) or record.spec != self.spec or record.before != previous:
                raise ValueError('successor policy or state chain changed')
            if i == 0 and record.observation != self.primary.records[-1].observation:
                raise ValueError('successor must address the exact rejected observation')
            if record.error is not None:
                if i != len(self.decisions) - 1:
                    raise ValueError('unassessed decision cannot have a suffix')
            else:
                previous = record.actual_record.step.cursor

    @property
    def execution(self):
        accepted = [r for r in self.decisions if r.error is None]
        return accepted[-1].actual_record.step.cursor if accepted else self.primary.execution

    @property
    def stopped(self):
        return self.decisions[-1].error is not None if self.decisions else self.primary.halted


def initialize_b6_planning_recovery(spec, *, anchor, envelope, accounting_period_id,
                                    zero_carry_in_assumption):
    primary = initialize_causal_policy(B6, policy=spec.primary, anchor=anchor, envelope=envelope,
        accounting_period_id=accounting_period_id, zero_carry_in_assumption=zero_carry_in_assumption)
    return B6PlanningRecoveryCursor(spec, spec.policy_id, primary)


def advance_b6_planning_recovery(cursor, observation):
    if cursor.stopped:
        raise ValueError('unassessed successor cannot consume later observations')
    if not isinstance(observation, CurrentObservation):
        raise ValueError('one current observation required')
    primary = cursor.primary
    if not cursor.decisions:
        primary = advance_causal_policy(primary, observation)
        if not primary.halted or primary.records[-1].stage not in TRIGGERS:
            return B6PlanningRecoveryCursor(cursor.spec, cursor.policy_id, primary)
    before = cursor.execution if cursor.decisions else primary.execution
    decision = SharedSuccessorDecision(cursor.spec, before, observation,
                                       *_decide_shared(cursor.spec, before, observation))
    return B6PlanningRecoveryCursor(cursor.spec, cursor.policy_id, primary, cursor.decisions + (decision,))


def summarize_b6_planning_recovery(cursor):
    execution = cursor.execution
    primary_accepted = sum(r.status == 'accepted' for r in cursor.primary.records)
    successor_accepted = sum(r.error is None for r in cursor.decisions)
    return {
        'policy_id': cursor.policy_id, 'evidence_class': 'derived_synthetic_diagnostic',
        'phase': 'unassessed_stop' if cursor.stopped else ('shared_successor' if cursor.decisions else 'primary'),
        'submitted_unique_hours': len(cursor.primary.records) + max(0, len(cursor.decisions) - 1),
        'primary_accepted_hours': primary_accepted, 'successor_validated_hours': successor_accepted,
        'validated_unique_hours': primary_accepted + successor_accepted,
        'original_rejection_submission_index': len(cursor.primary.records) if cursor.primary.halted else None,
        'original_rejection_source_hour': cursor.primary.records[-1].observation.hour.power_source_hour if cursor.primary.halted else None,
        'last_validated_hour': execution.tracks[0][1].physical.anchor.power_source_hour,
        'remaining_debt': tuple((name, track.ledger.debt) for name, track in execution.tracks),
        'cohort_statuses': tuple((name, c, status) for name, track in execution.tracks
                                 for c, status in assess_debt_cohorts(track.ledger)),
        'completion_claim_allowed': False, 'formal_result': False, 'risk_probability': None,
    }
