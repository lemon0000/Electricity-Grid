"""Draft ex-ante composite policy: primary replay then permanent shared recovery."""
from dataclasses import asdict, dataclass
import hashlib
import json

from .boundary import BoundaryAnchor, _validate_next_identity
from .causal_policy import (
    FixedPolicy, CurrentObservation, PolicyCursor, initialize_causal_policy,
    advance_causal_policy, _choose_actions,
)
from .actual_actions import ActualActionCursor, DeclaredActualAction, advance_actual_action
from .four_arm_replay import NETWORK, CFE, JOINT, B6
from .debt_cohorts import assess_debt_cohorts


@dataclass(frozen=True)
class CompositePolicy:
    arm_id: str
    primary: FixedPolicy = FixedPolicy()
    recovery: FixedPolicy = FixedPolicy()
    rule: str = 'primary_then_permanent_shared_recovery_v1'

    def __post_init__(self):
        if self.arm_id not in {NETWORK,CFE,JOINT,B6} or self.rule != 'primary_then_permanent_shared_recovery_v1':
            raise ValueError('registered composite rule and arm required')
        if not isinstance(self.primary,FixedPolicy) or not isinstance(self.recovery,FixedPolicy):
            raise ValueError('fixed primary and recovery parameters required')

    @classmethod
    def from_config(cls, config, arm_id):
        expected = {
            'schema': 'rq2_continuous_recovery_controller_v1', 'status': 'DRAFT_NONAUTHORITATIVE',
            'rule': 'primary_then_permanent_shared_recovery_v1',
            'trigger_stages': ['physical_execution','shared_execution'],
            'transition': 'same_rejected_observation_then_permanent_shared_state',
            'failure': 'unassessed_stop', 'evidence_class': 'mechanism_assumption',
        }
        gates = {'continuous_service_protocol_registered','formal_experiment_authorized',
                 'formal_result','paper_claim','security_certified'}
        if (set(config) != set(expected)|gates|{'primary','recovery','fixture'}
            or any(config[key] != value for key,value in expected.items())
            or any(config[key] is not False for key in gates)):
            raise ValueError('configuration does not match implemented draft policy semantics')
        return cls(arm_id,FixedPolicy(**config['primary']),FixedPolicy(**config['recovery']),config['rule'])

    @property
    def policy_id(self):
        payload = dict(asdict(self), trigger_stages=['physical_execution','shared_execution'],
                       transition='same_rejected_observation_then_permanent_shared_state',
                       failure='unassessed_stop', evidence='mechanism_assumption')
        return self.rule+':'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()


def _recover(spec, before, observation):
    stage = 'input_validation'
    try:
        if (observation.hour.arm_id,observation.hour.track_id) != (JOINT,'shared'):
            raise ValueError('common JOINT/shared source container required')
        for _,track in before.execution.tracks:
            _validate_next_identity(track.physical.anchor,observation.hour)
        stage = 'recovery_decision'
        actions,_ = _choose_actions(spec.recovery,before.execution,observation)
        candidate = actions['shared']
        action = DeclaredActualAction(candidate.physical.recovery,
            candidate.physical.actual_service_power,candidate.allocations)
        stage = 'actual_validation'
        after = advance_actual_action(before,observation,action)
    except (ValueError,OverflowError) as error:
        return stage,str(error),None
    return stage,after.records[-1].error,after


@dataclass(frozen=True)
class RecoveryDecision:
    spec: CompositePolicy
    before: ActualActionCursor
    observation: CurrentObservation
    stage: str
    error: str | None
    after: ActualActionCursor | None

    def __post_init__(self):
        if not isinstance(self.observation,CurrentObservation):
            raise ValueError('one current observation required')
        if (self.stage,self.error,self.after) != _recover(self.spec,self.before,self.observation):
            raise ValueError('recovery decision differs from deterministic replay')


@dataclass(frozen=True)
class CompositeCursor:
    spec: CompositePolicy
    policy_id: str
    primary: PolicyCursor
    recovery_records: tuple[RecoveryDecision,...] = ()

    def __post_init__(self):
        if self.policy_id != self.spec.policy_id:
            raise ValueError('composite policy identity changed')
        if self.primary.policy != self.spec.primary or self.primary.execution.arm_id != self.spec.arm_id:
            raise ValueError('primary policy does not match composite specification')
        if not isinstance(self.recovery_records,tuple):
            raise ValueError('immutable recovery history required')
        if (self.primary.halted and self.primary.records[-1].stage in {'physical_execution','shared_execution'}
            and not self.recovery_records):
            raise ValueError('triggered rejection requires its same-hour recovery decision')
        if self.recovery_records:
            previous = ActualActionCursor(self.primary)
            for i,record in enumerate(self.recovery_records):
                if record.spec != self.spec or record.before != previous:
                    raise ValueError('recovery policy or state chain changed')
                if i == 0 and record.observation != self.primary.records[-1].observation:
                    raise ValueError('recovery must address the original rejected observation')
                if record.error is not None:
                    if i != len(self.recovery_records)-1:
                        raise ValueError('unassessed decision cannot have a suffix')
                else:
                    previous = record.after

    @property
    def actual(self):
        if not self.recovery_records:
            return None
        last = self.recovery_records[-1]
        return last.after if last.after is not None else last.before

    @property
    def stopped(self):
        if self.recovery_records:
            return self.recovery_records[-1].error is not None
        return self.primary.halted


def initialize_composite_policy(spec: CompositePolicy, *, anchor: BoundaryAnchor,
                                envelope, accounting_period_id: str,
                                zero_carry_in_assumption: bool) -> CompositeCursor:
    primary = initialize_causal_policy(spec.arm_id,policy=spec.primary,anchor=anchor,envelope=envelope,
        accounting_period_id=accounting_period_id,zero_carry_in_assumption=zero_carry_in_assumption)
    return CompositeCursor(spec,spec.policy_id,primary)


def advance_composite_policy(cursor: CompositeCursor, observation: CurrentObservation) -> CompositeCursor:
    if cursor.stopped:
        raise ValueError('unassessed composite policy cannot consume later observations')
    if not isinstance(observation,CurrentObservation):
        raise ValueError('one current observation required')
    primary = cursor.primary
    if not cursor.recovery_records:
        primary = advance_causal_policy(primary,observation)
        if not primary.halted or primary.records[-1].stage not in {'physical_execution','shared_execution'}:
            return CompositeCursor(cursor.spec,cursor.policy_id,primary)
        before = ActualActionCursor(primary)
    else:
        before = cursor.actual
    record = RecoveryDecision(cursor.spec,before,observation,*_recover(cursor.spec,before,observation))
    return CompositeCursor(cursor.spec,cursor.policy_id,primary,cursor.recovery_records+(record,))


def summarize_composite_policy(cursor: CompositeCursor):
    actual = cursor.actual
    execution = actual.execution if actual is not None else cursor.primary.execution
    primary_accepted = sum(r.status == 'accepted' for r in cursor.primary.records)
    recovery_accepted = sum(r.error is None for r in cursor.recovery_records)
    submitted = len(cursor.primary.records)+max(0,len(cursor.recovery_records)-1)
    statuses = tuple((name,c,status) for name,track in execution.tracks
                     for c,status in assess_debt_cohorts(track.ledger))
    return {
        'policy_id': cursor.policy_id, 'evidence_class': 'derived_synthetic_diagnostic',
        'phase': 'unassessed_stop' if cursor.stopped else ('shared_recovery' if actual is not None else 'primary'),
        'submitted_unique_hours': submitted, 'primary_accepted_hours': primary_accepted,
        'recovery_validated_hours': recovery_accepted, 'validated_unique_hours': primary_accepted+recovery_accepted,
        'original_rejection_hour': cursor.primary.records[-1].observation.hour.power_source_hour if cursor.primary.halted else None,
        'last_validated_hour': execution.tracks[0][1].physical.anchor.power_source_hour,
        'remaining_debt': tuple((name,track.ledger.debt) for name,track in execution.tracks),
        'cohort_statuses': statuses,
        'completion_claim_allowed': False, 'formal_result': False, 'risk_probability': None,
    }
