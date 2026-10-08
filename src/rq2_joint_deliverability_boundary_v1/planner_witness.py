"""Independent effective-action witness for the draft offline prefix planner.

Candidates are explicit exact quantities, never inferred from solver status or
silently rounded. B6 witnesses concern separate planning, not shared execution.
"""
from dataclasses import asdict, dataclass, replace
from fractions import Fraction as Q
import hashlib
import json

from .boundary import ContinuationHour, SERVICE_TOLERANCE
from .capacity_policy import CapacityObservation
from .continuous_planner import ContinuousPlanningInputs, REQUEST_BOUNDED, planner_identity
from .debt_cohorts import assess_debt_cohorts
from .four_arm_replay import (
    NETWORK, CFE, B6, ArmCursor, ArmStep, CohortAction, initialize_arm_replay, advance_arm_replay, _effective_call,
)
from .multiday import ServiceAction

CONTRACT = 'continuous_effective_prefix_witness_v1'
TOL = Q(str(SERVICE_TOLERANCE))


def _exact(value, name):
    if not isinstance(value, Q) or value < 0:
        raise ValueError(f'{name} must be a nonnegative exact Fraction')
    return value


@dataclass(frozen=True)
class PlannerTrackAction:
    recovery: Q
    actual_service_power: Q
    allocations: tuple[tuple[int, Q], ...] = ()

    def __post_init__(self):
        _exact(self.recovery, 'recovery')
        _exact(self.actual_service_power, 'service power')
        if type(self.allocations) is not tuple:
            raise ValueError('immutable allocations required')
        births = []
        for item in self.allocations:
            if type(item) is not tuple or len(item) != 2 or type(item[0]) is not int or item[0] < 0:
                raise ValueError('allocation birth must be a nonnegative source-hour integer')
            _exact(item[1], 'allocation')
            births.append(item[0])
        if births != sorted(set(births)):
            raise ValueError('allocation births must be unique and ordered')


@dataclass(frozen=True)
class PlannerHourAction:
    grid_service: Q
    cfe_service: Q
    tracks: tuple[tuple[str, PlannerTrackAction], ...]

    def __post_init__(self):
        _exact(self.grid_service, 'grid service')
        _exact(self.cfe_service, 'CFE service')
        if (type(self.tracks) is not tuple or any(type(item) is not tuple or len(item) != 2
            or type(item[0]) is not str or not isinstance(item[1], PlannerTrackAction) for item in self.tracks)):
            raise ValueError('immutable named track actions required')
        if len({k for k, _ in self.tracks}) != len(self.tracks):
            raise ValueError('duplicate action track')


@dataclass(frozen=True)
class PlannerWitnessCandidate:
    planner_id: str
    capacity: Q
    scenarios: tuple[tuple[str, tuple[PlannerHourAction, ...]], ...]
    evidence_class: str = 'mechanism_assumption'

    def __post_init__(self):
        _exact(self.capacity, 'capacity')
        if type(self.planner_id) is not str or not self.planner_id or self.evidence_class != 'mechanism_assumption':
            raise ValueError('explicit mechanism planner identity required')
        if type(self.scenarios) is not tuple or any(
            type(item) is not tuple or len(item) != 2 or type(item[0]) is not str
            or type(item[1]) is not tuple or any(not isinstance(a, PlannerHourAction) for a in item[1])
            for item in self.scenarios):
            raise ValueError('immutable scenario action sequences required')


@dataclass(frozen=True)
class PlannerWitnessRecord:
    original_current: CapacityObservation
    action: PlannerHourAction
    before: ArmCursor
    executed_request_projection: ContinuationHour | None
    candidate_step: ArmStep | None
    stage: str
    error: str | None

    @property
    def accepted(self):
        return self.candidate_step is not None and self.error is None

    @property
    def status(self):
        if self.accepted:
            return 'validated_effective_prefix_hour'
        if self.stage == 'physical_cohort_replay' and self.error in (
            'physical and cohort debt diverged', 'physical and cohort carry-in balances mismatch'):
            return 'unassessed_numeric_projection'
        return 'rejected_witness'


@dataclass(frozen=True)
class PlannerScenarioWitness:
    name: str
    records: tuple[PlannerWitnessRecord, ...]
    execution: ArmCursor
    configured_hours: int

    @property
    def accepted(self):
        return len(self.records) == self.configured_hours and all(r.accepted for r in self.records)

    @property
    def cohort_statuses(self):
        return tuple((k, birth, status) for k, track in self.execution.tracks
                     for birth, status in assess_debt_cohorts(track.ledger))


def _envelope(inputs):
    return {k: getattr(inputs, k) for k in ('time_step_hours', 'recovery_efficiency',
        'maximum_event_duration_hours', 'maximum_event_count', 'minimum_recovery_hours',
        'normalized_energy_budget', 'normalized_debt_limit')}


def _audit_hour(inputs, arm, capacity, before, current, action):
    hour, limits = current.observation.hour, current.observation.limits
    projection, candidate, stage = None, None, 'exact_action_validation'
    try:
        names = tuple(k for k, _ in before.tracks)
        if tuple(k for k, _ in action.tracks) != names:
            raise ValueError('action track inventory differs from planner arm')
        raw_g = hour.grid_request if arm != CFE else 0.
        raw_c = hour.cfe_request if arm != NETWORK else 0.
        eg, ec = _effective_call(raw_g, 0.), _effective_call(0., raw_c)
        if inputs.service_action_mode == REQUEST_BOUNDED:
            if eg+ec != _effective_call(raw_g, raw_c):
                raise ValueError('effective source decomposition differs')
            if action.grid_service != eg:
                raise ValueError('bounded grid service must equal effective request')
        elif action.grid_service < eg:
            raise ValueError('grid service is below effective request')
        if arm == CFE and action.grid_service != 0:
            raise ValueError('grid service is inapplicable for CFE-only')
        if action.cfe_service != ec:
            raise ValueError('CFE service must equal effective arm request')
        g, c = action.grid_service, action.cfe_service
        baseline = Q(str(hour.workload_occupancy))
        if g+c > baseline:
            raise ValueError('combined service exceeds connected baseline')
        projection = replace(hour, grid_request=g, cfe_request=c)
        replay_actions = {}
        for k, track in before.tracks:
            declared = dict(action.tracks)[k]
            q = g if k == 'grid' else c if k == 'cfe' else g+c
            r = declared.recovery
            if q and (q <= TOL or q < Q(str(inputs.minimum_event_power))):
                raise ValueError('positive track call violates minimum activity')
            if r and (r <= TOL or float(r) <= SERVICE_TOLERANCE):
                raise ValueError('positive recovery is lost by effective physical threshold')
            if q and r:
                raise ValueError('active track requires exactly zero recovery')
            call_cap = min(capacity, Q(str(current.available_flexibility)), Q(str(limits.call_limit)))
            if q > call_cap:
                raise ValueError('track call exceeds capacity/availability/call limit')
            headroom = min(Q(str(inputs.maximum_recovery_power)), Q(str(limits.maximum_recovery_power)),
                           Q(str(limits.business_recovery_headroom)))
            if arm != NETWORK and k != 'grid':
                headroom = min(headroom, Q(str(limits.cfe_compatible_surplus)))
            if r > headroom:
                raise ValueError('track recovery exceeds applicable headroom')
            if declared.actual_service_power != baseline-q+r:
                raise ValueError('exact service power balance differs')
            state, ledger = track.physical.state, track.ledger
            prior_q = ledger.cohorts[-1].incurred if state.event_active else Q(0)
            if state.event_active and ledger.cohorts[-1].created_hour != ledger.last_hour:
                raise ValueError('active history lacks last-hour exact cohort')
            # Bind the actual precomputed coefficient of the canonical model.
            ramp = Q(str(inputs.curtailment_ramp_per_hour*min(1., inputs.response_time_hours)))
            if q-prior_q > ramp:
                raise ValueError('exact upward ramp/response limit exceeded')
            start = bool(q) and not state.event_active
            if start and state.has_prior_event and (state.interevent_rest_hours is None
                or Q(str(state.interevent_rest_hours)) < Q(str(inputs.minimum_recovery_hours))):
                raise ValueError('exact interevent rest limit violated')
            duration = (Q(str(state.active_duration_hours))+1 if state.event_active else Q(1)) if q else Q(0)
            if duration > Q(str(inputs.maximum_event_duration_hours)) or state.event_count+int(start) > inputs.maximum_event_count:
                raise ValueError('exact event duration/count limit exceeded')
            incurred = sum((cohort.incurred for cohort in ledger.cohorts), Q(0))+q
            eta = Q(str(inputs.recovery_efficiency))
            new_debt = ledger.debt+q-eta*r
            if incurred > Q(str(inputs.normalized_energy_budget)) or not 0 <= new_debt <= Q(str(inputs.normalized_debt_limit)):
                raise ValueError('exact energy/debt limit violated')
            if sum((amount for _, amount in declared.allocations), Q(0)) != eta*r:
                raise ValueError('allocation sum differs from effective recovery work')
            replay_actions[k] = CohortAction(ServiceAction(r, declared.actual_service_power, call_cap,
                limits.business_recovery_headroom, limits.cfe_compatible_surplus,
                min(inputs.maximum_recovery_power, limits.maximum_recovery_power)), declared.allocations)
        due = current.observation.due_hour if g+c else None
        stage = 'physical_cohort_replay'
        candidate = advance_arm_replay(before, hour=projection, due_hour=due, actions=replay_actions)
        stage = 'hard_deadline_validation'
        for k, track in candidate.cursor.tracks:
            if any(status == 'deadline_missed' for _, status in assess_debt_cohorts(track.ledger)):
                raise ValueError('hard known deadline was missed after due-hour recovery')
    except (ValueError, OverflowError) as error:
        return PlannerWitnessRecord(current, action, before, projection, candidate, stage, str(error))
    return PlannerWitnessRecord(current, action, before, projection, candidate, stage, None)


def _evaluate(inputs, arm, candidate):
    if not isinstance(inputs, ContinuousPlanningInputs) or not isinstance(candidate, PlannerWitnessCandidate):
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
class PlannerWitnessAudit:
    inputs: ContinuousPlanningInputs
    arm: str
    candidate: PlannerWitnessCandidate
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
            'prefix_upper_bound': None, 'complete_capacity_lower_bound': None, 'complete_capacity_upper_bound': None,
            'solver_residual_audit_complete': False, 'causal_policy_certificate': None,
            'formal_result': False, 'security_certified': False, 'completion_claim_allowed': False}


def audit_planner_witness(inputs, arm, candidate):
    return PlannerWitnessAudit(inputs, arm, candidate, _evaluate(inputs, arm, candidate))
