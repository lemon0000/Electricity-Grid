"""Strict effective-action witness bound to the open-activity draft identity.

Check exact bidirectional capacity before reusing the existing hour/cohort audit.
An assignment on the closed boundary is not an effective physical witness.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
import hashlib
import json

from .continuous_planner_bidirectional import BidirectionalPlanningInputs, planner_identity
from .four_arm_replay import B6, initialize_arm_replay
from .planner_witness import (
    PlannerWitnessCandidate as LegacyCandidate, PlannerScenarioWitness, PlannerWitnessRecord,
    TOL, _envelope, _audit_hour as _legacy_audit_hour, PlannerHourAction,
)

CONTRACT = 'continuous_bidirectional_effective_prefix_witness_v1'


@dataclass(frozen=True)
class BidirectionalWitnessCandidate:
    planner_id: str
    capacity: Q
    scenarios: tuple[tuple[str, tuple[PlannerHourAction, ...]], ...]
    evidence_class: str = 'mechanism_assumption'

    def __post_init__(self):
        # Reuse quantity/schema validation, not the legacy candidate type.
        LegacyCandidate(self.planner_id, self.capacity, self.scenarios, self.evidence_class)


def _audit_hour(inputs, arm, capacity, before, current, action):
    # Exact physical power check precedes any replay or state progression.
    for k, declared in action.tracks:
        q = action.grid_service if k == 'grid' else action.cfe_service if k == 'cfe' else action.grid_service+action.cfe_service
        if q+declared.recovery > capacity:
            return PlannerWitnessRecord(current, action, before, None, None,
                'exact_bidirectional_capacity_validation', 'track call plus recovery exceeds physical capacity')
    return _legacy_audit_hour(inputs, arm, capacity, before, current, action)


def _evaluate(inputs, arm, candidate):
    if type(inputs) is not BidirectionalPlanningInputs or type(candidate) is not BidirectionalWitnessCandidate:
        raise ValueError('typed planner inputs and witness candidate required')
    if candidate.planner_id != planner_identity(inputs, arm):
        raise ValueError('candidate planner identity differs')
    if candidate.capacity > Q(str(inputs.maximum_capacity)):
        raise ValueError('candidate capacity exceeds declared domain')
    if tuple(name for name, _ in candidate.scenarios) != tuple(s.name for s in inputs.scenarios):
        raise ValueError('candidate must cover the complete ordered scenario support')
    results = []
    for scenario, (_, actions) in zip(inputs.scenarios, candidate.scenarios, strict=True):
        if len(actions) != len(scenario.observations):
            raise ValueError('candidate must declare every configured hour')
        cursor = initialize_arm_replay(arm, mode='separate_planning' if arm == B6 else 'physical_execution',
            anchor=scenario.anchor, envelope=_envelope(inputs), accounting_period_id=inputs.accounting_period_id,
            zero_carry_in_assumption=True)
        records = []
        for current, action in zip(scenario.observations, actions, strict=True):
            record = _audit_hour(inputs, arm, candidate.capacity, cursor, current, action)
            records.append(record)
            if not record.accepted:
                break
            cursor = record.candidate_step.cursor
        results.append(PlannerScenarioWitness(scenario.name, tuple(records), cursor, len(actions)))
    return tuple(results)


@dataclass(frozen=True)
class BidirectionalWitnessAudit:
    inputs: BidirectionalPlanningInputs
    arm: str
    candidate: BidirectionalWitnessCandidate
    scenarios: tuple[PlannerScenarioWitness, ...]

    def __post_init__(self):
        if self.scenarios != _evaluate(self.inputs, self.arm, self.candidate):
            raise ValueError('witness audit differs from independent replay')

    @property
    def accepted(self):
        return all(s.accepted for s in self.scenarios)

    @property
    def witness_capacity(self):
        return self.candidate.capacity if self.accepted else None

    @property
    def witness_id(self):
        def fraction(value):
            if isinstance(value, Q):
                return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}
            raise TypeError('unsupported candidate encoding')
        payload = json.dumps({'contract': CONTRACT, 'service_tolerance': TOL, 'candidate': asdict(self.candidate)},
                             default=fraction, sort_keys=True, allow_nan=False)
        return CONTRACT+':'+hashlib.sha256(payload.encode()).hexdigest()

    def evidence(self):
        return {'status': 'DRAFT_NONAUTHORITATIVE', 'evidence_class': 'derived_mechanism_witness',
            'witness_id': self.witness_id, 'planner_id': self.candidate.planner_id,
            'scope': 'b6_separate_planning' if self.arm == B6 else 'shared_business_prefix',
            'accepted': self.accepted, 'declared_capacity': self.candidate.capacity,
            'activity_representation': self.inputs.activity_representation,
            'prefix_upper_bound': None, 'complete_capacity_lower_bound': None, 'complete_capacity_upper_bound': None,
            'solver_residual_audit_complete': False, 'causal_policy_certificate': None,
            'formal_result': False, 'security_certified': False, 'completion_claim_allowed': False}


def audit_planner_witness(inputs, arm, candidate):
    return BidirectionalWitnessAudit(inputs, arm, candidate, _evaluate(inputs, arm, candidate))
