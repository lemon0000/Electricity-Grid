"""Draft fixed-capacity shared policy with exact continuous response amounts.

Capacity is a mechanism declaration, not a training/solver certificate. No
terminal action or debt reset is introduced at chunk or observation boundaries.
"""
from dataclasses import asdict, dataclass, replace
from fractions import Fraction as Q
import hashlib
import json

from .boundary import SERVICE_TOLERANCE, _number, _validate_next_identity
from .causal_policy import CurrentObservation, FixedPolicy, _choose_actions
from .four_arm_replay import NETWORK, CFE, JOINT, B6, ArmCursor, initialize_arm_replay, _effective_call
from .aggregate_response import DeclaredAggregateResponse, AggregateResponseRecord, _evaluate_aggregate


RULE = 'fixed_capacity_grid_cfe_recovery_open_boundary_v1'


def _scalar(value, name):
    if type(value) not in (int,float):
        raise ValueError(f'{name} requires built-in int or float')
    return _number(value,name)


@dataclass(frozen=True)
class CapacityPolicy:
    arm_id: str
    committed_capacity: float
    capacity_declaration_id: str
    minimum_event_power: float
    curtailment_ramp_per_hour: float
    response_time_hours: float
    maximum_recovery_power: float
    recovery_decimal_places: int = 12
    rule: str = RULE
    evidence_class: str = 'mechanism_assumption'

    @classmethod
    def from_config(cls, config, arm_id):
        expected = {'schema':'rq2_continuous_capacity_policy_v1','status':'DRAFT_NONAUTHORITATIVE',
                    'rule':RULE,'evidence_class':'mechanism_assumption'}
        gates = {'continuous_service_protocol_registered','formal_experiment_authorized',
                 'formal_result','paper_claim','security_certified'}
        if (set(config) != set(expected)|gates|{'training_capacity_certificate','fixture'}
            or any(config[k] != v for k,v in expected.items())
            or any(config[k] is not False for k in gates)
            or config['training_capacity_certificate'] is not None):
            raise ValueError('configuration differs from implemented draft capacity semantics')
        fixture = config['fixture']
        fields = {'committed_capacity','capacity_declaration_id','minimum_event_power',
                  'curtailment_ramp_per_hour','response_time_hours','maximum_recovery_power','recovery_decimal_places'}
        if set(fixture) != fields|{'source_config','available_flexibility'}:
            raise ValueError('draft capacity fixture inventory differs')
        if not isinstance(fixture['source_config'],str) or not fixture['source_config']:
            raise ValueError('explicit fixture source label required')
        if not 0 <= _scalar(fixture['available_flexibility'],'fixture available flexibility') <= 1:
            raise ValueError('normalized fixture available flexibility must be in [0,1]')
        return cls(arm_id,**{k:fixture[k] for k in fields})

    def __post_init__(self):
        if self.arm_id not in {NETWORK,CFE,JOINT,B6} or self.rule != RULE:
            raise ValueError('registered draft shared policy and arm required')
        if self.evidence_class != 'mechanism_assumption':
            raise ValueError('this draft does not certify training capacity')
        if not isinstance(self.capacity_declaration_id,str) or not self.capacity_declaration_id:
            raise ValueError('explicit capacity declaration identity required')
        for name in ('committed_capacity','minimum_event_power','curtailment_ramp_per_hour',
                     'response_time_hours','maximum_recovery_power'):
            _scalar(getattr(self,name),name)
        if not 0 <= self.committed_capacity <= 1:
            raise ValueError('normalized committed capacity must be in [0,1]')
        if min(self.minimum_event_power,self.curtailment_ramp_per_hour,self.response_time_hours) <= 0:
            raise ValueError('minimum event power, ramp and response must be positive')
        if type(self.recovery_decimal_places) is not int or not 0 <= self.recovery_decimal_places <= 12:
            raise ValueError('recovery precision must be an integer from 0 to 12')


@dataclass(frozen=True)
class CapacityObservation:
    observation: CurrentObservation
    available_flexibility: float

    def __post_init__(self):
        if not isinstance(self.observation,CurrentObservation):
            raise ValueError('one typed current observation required')
        if not 0 <= _scalar(self.available_flexibility,'current available flexibility') <= 1:
            raise ValueError('normalized available flexibility must be in [0,1]')


def _continuous_response(g_req, c_req, cap, minimum):
    """Exact grid-first maximum; only aggregate activity has a lower bound."""
    total = min(g_req+c_req,cap)
    if total < minimum or total <= Q(str(SERVICE_TOLERANCE)):
        return Q(0),Q(0)
    grid = min(g_req,total)
    return grid,total-grid


def _select_action(spec, before, current):
    observation = current.observation
    hour = observation.hour
    g_raw = hour.grid_request if spec.arm_id != CFE else 0.
    c_raw = hour.cfe_request if spec.arm_id != NETWORK else 0.
    g_req,c_req = _effective_call(g_raw,0.),_effective_call(0.,c_raw)
    if g_req+c_req != _effective_call(g_raw,c_raw):
        raise ValueError('separate and shared effective requests differ')
    track = before.tracks[0][1]
    state,envelope = track.physical.state,dict(track.physical.envelope)
    dt = Q(str(envelope['time_step_hours']))
    if dt != 1:
        raise ValueError('this draft requires one-hour observations')
    active_permitted = (
        Q(str(state.active_duration_hours))+dt <= Q(str(envelope['maximum_event_duration_hours']))
        if state.event_active else (
            state.event_count < envelope['maximum_event_count'] and
            (not state.has_prior_event or
             (state.interevent_rest_hours is not None and Q(str(state.interevent_rest_hours)) >= Q(str(envelope['minimum_recovery_hours']))))))
    incurred = sum((c.incurred for c in track.ledger.cohorts),Q(0))
    previous_call = Q(0)
    if state.event_active:
        if not track.ledger.cohorts or track.ledger.cohorts[-1].created_hour != track.ledger.last_hour:
            raise ValueError('active previous hour requires its exact incurred cohort')
        previous_call = track.ledger.cohorts[-1].incurred/dt
    ramp = Q(str(spec.curtailment_ramp_per_hour))*min(dt,Q(str(spec.response_time_hours)))
    cap = max(Q(0),min(
        Q(str(spec.committed_capacity)),Q(str(current.available_flexibility)),
        Q(str(observation.limits.call_limit)),Q(str(hour.workload_occupancy)),
        (Q(str(envelope['normalized_energy_budget']))-incurred)/dt,
        (Q(str(envelope['normalized_debt_limit']))-track.ledger.debt)/dt,
        previous_call+ramp,
    ))
    g,c = _continuous_response(g_req,c_req,cap,Q(str(spec.minimum_event_power))) if active_permitted else (Q(0),Q(0))
    if g+c:
        action = DeclaredAggregateResponse(g,c,Q(0),Q(str(hour.workload_occupancy))-g-c)
    else:
        idle = replace(observation,hour=replace(hour,grid_request=0.,cfe_request=0.),due_hour=None,
            limits=replace(observation.limits,maximum_recovery_power=min(
                observation.limits.maximum_recovery_power,spec.maximum_recovery_power)))
        actions,_ = _choose_actions(FixedPolicy(recovery_decimal_places=spec.recovery_decimal_places),before,idle)
        chosen = actions['shared']
        recovery = Q(str(chosen.physical.recovery))
        action = DeclaredAggregateResponse(Q(0),Q(0),recovery,
                                          Q(str(hour.workload_occupancy))+recovery,chosen.allocations)
    return action


def _evaluate_policy(spec, before, current):
    stage = 'input_validation'
    try:
        observation = current.observation
        if (observation.hour.arm_id,observation.hour.track_id) != (JOINT,'shared'):
            raise ValueError('common JOINT/shared source container required')
        for _,track in before.tracks:
            _validate_next_identity(track.physical.anchor,observation.hour)
        stage = 'policy_decision'
        action = _select_action(spec,before,current)
        stage = 'response_validation'
        response = AggregateResponseRecord(before,observation,action,*_evaluate_aggregate(before,observation,action))
    except (ValueError,OverflowError) as error:
        return stage,str(error),None
    return stage,response.error,response


@dataclass(frozen=True)
class CapacityPolicyRecord:
    spec: CapacityPolicy
    before: ArmCursor
    current: CapacityObservation
    stage: str
    error: str | None
    response: AggregateResponseRecord | None

    def __post_init__(self):
        if not isinstance(self.spec,CapacityPolicy) or not isinstance(self.current,CapacityObservation):
            raise ValueError('typed fixed policy and current observation required')
        if (not isinstance(self.before,ArmCursor) or self.before.arm_id != self.spec.arm_id
            or self.before.mode != 'physical_execution'):
            raise ValueError('matching shared execution state required')
        if (self.stage,self.error,self.response) != _evaluate_policy(self.spec,self.before,self.current):
            raise ValueError('capacity-policy record differs from deterministic replay')

    @property
    def committed(self):
        return self.response is not None and self.response.committed


def _policy_id(spec, initial):
    payload = dict(spec=asdict(spec),envelope=initial.tracks[0][1].physical.envelope,
                   initialization='explicit_zero_history',period_rule='single_nonrolling_no_reset',
                   response_contract='exact_components_aggregate_activity_v1',
                   activity_rule='zero_or_strictly_above_service_tolerance',service_tolerance=SERVICE_TOLERANCE,
                   failure='grid_shortfall_or_invalid_stop',boundary='open_no_terminal_action')
    return RULE+':'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class CapacityPolicyCursor:
    spec: CapacityPolicy
    initial: ArmCursor
    policy_id: str
    records: tuple[CapacityPolicyRecord,...] = ()

    def __post_init__(self):
        if not isinstance(self.spec,CapacityPolicy) or not isinstance(self.initial,ArmCursor):
            raise ValueError('typed policy and initial state required')
        track = self.initial.tracks[0][1]
        expected = initialize_arm_replay(self.spec.arm_id,mode='physical_execution',anchor=track.physical.anchor,
            envelope=dict(track.physical.envelope),accounting_period_id=track.ledger.accounting_period_id,
            zero_carry_in_assumption=True)
        if self.initial != expected:
            raise ValueError('explicit canonical zero-history initialization required')
        if self.policy_id != _policy_id(self.spec,self.initial) or not isinstance(self.records,tuple):
            raise ValueError('fixed policy identity and immutable history required')
        previous = self.initial
        for i,record in enumerate(self.records):
            if not isinstance(record,CapacityPolicyRecord) or record.spec != self.spec or record.before != previous:
                raise ValueError('capacity policy or state chain changed')
            if record.committed:
                previous = record.response.candidate_step.cursor
            elif i != len(self.records)-1:
                raise ValueError('uncommitted policy record cannot have a suffix')

    @property
    def execution(self):
        accepted = [r for r in self.records if r.committed]
        return accepted[-1].response.candidate_step.cursor if accepted else self.initial

    @property
    def stopped(self):
        return bool(self.records and not self.records[-1].committed)


def initialize_capacity_policy(spec, *, anchor, envelope, accounting_period_id, zero_carry_in_assumption):
    initial = initialize_arm_replay(spec.arm_id,mode='physical_execution',anchor=anchor,envelope=envelope,
        accounting_period_id=accounting_period_id,zero_carry_in_assumption=zero_carry_in_assumption)
    return CapacityPolicyCursor(spec,initial,_policy_id(spec,initial))


def advance_capacity_policy(cursor, current):
    if cursor.stopped:
        raise ValueError('uncommitted capacity policy cannot consume later observations')
    if not isinstance(current,CapacityObservation):
        raise ValueError('one typed current capacity observation required')
    record = CapacityPolicyRecord(cursor.spec,cursor.execution,current,*_evaluate_policy(cursor.spec,cursor.execution,current))
    return CapacityPolicyCursor(cursor.spec,cursor.initial,cursor.policy_id,cursor.records+(record,))
