"""Exact current inputs and detached v2 business replay; no paired-state owner."""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from src.rq2_joint_deliverability_boundary_v1 import capacity_policy_bidirectional as business
from src.rq2_joint_deliverability_boundary_v1 import cfe_preallocation as cfe
from src.rq2_joint_deliverability_boundary_v1 import boundary, causal_policy, four_arm_replay as arms
from src.rq2_joint_deliverability_boundary_v1 import prefix_handoff as encoding
from src.rq2_joint_deliverability_boundary_v1.current_grid_step import _Owned, _owned

SCHEMA = 'h1_exact_business_development_v1'
PERIOD = 'single_nonrolling_enrollment_and_followup_192h'


def _digest(value):
    return sha256(encoding._encoded(value)).hexdigest()


def implementation_identity():
    paths=set(encoding.IMPLEMENTATION)|{
        'src/rq2_joint_deliverability_boundary_v1/capacity_policy_bidirectional.py',
        'src/rq2_joint_deliverability_boundary_v1/cfe_preallocation.py',
        'src/rq2_joint_deliverability_boundary_v1/current_grid_step.py'}
    return _digest([SCHEMA,[(p,sha256((encoding.ROOT/p).read_bytes()).hexdigest()) for p in sorted(paths)],
                    sha256(Path(__file__).read_bytes()).hexdigest()])


def _exact(value):
    if type(value) is not Q or value < 0:
        raise ValueError('nonnegative exact Fraction required')
    return value


def lossless_builtin(value):
    """Only the existing strict scalar field needs a built-in representation."""
    _exact(value)
    if value.denominator == 1:
        return int(value)
    result=float(value)
    if Q(str(result)) != value:
        raise ValueError('exact interface unresolved: no lossless decimal built-in')
    return result


@dataclass(frozen=True)
class Mechanism:
    alpha: Q
    flexible_fraction: Q
    recovery_headroom_fraction: Q
    normalized_unit_mw: Q = Q(250)

    def __post_init__(self):
        for value in vars(self).values():_exact(value)
        if (not 0 < self.alpha <= 1 or not 0 <= self.flexible_fraction <= 1
                or not 0 <= self.recovery_headroom_fraction <= 1 or self.normalized_unit_mw != 250):
            raise ValueError('declared mechanism domain or fixed 250MW scale differs')


@dataclass(frozen=True)
class ExactCurrent:
    relative_hour: int
    mechanism: Mechanism
    allocation: cfe.PreallocatedCFE
    grid_request_mw: Q

    def __post_init__(self):
        if type(self.relative_hour) is not int or not 0 <= self.relative_hour < 192:
            raise ValueError('relative business action hour must be 0..191')
        if type(self.mechanism) is not Mechanism or type(self.allocation) is not cfe.PreallocatedCFE:
            raise ValueError('typed exact mechanism and preallocation required')
        self.mechanism.__post_init__();self.allocation.__post_init__();_exact(self.grid_request_mw)
        if self.allocation.target != self.mechanism.alpha:
            raise ValueError('allocation target differs from fixed mechanism')
        # The caller must bind the current projected workload and Rref elsewhere.
        w=self.allocation.workload;g=self.grid_request
        if self.grid_request_mw > w*self.mechanism.normalized_unit_mw:
            raise ValueError('grid request exceeds exact baseline')
        tau=cfe.activity_threshold()
        if g and g <= tau:
            raise ValueError('positive reference request below business resolution')
        effective=g+self.allocation.effective_request
        raw=g+self.allocation.raw_request
        if effective != (raw if raw > tau else Q(0)):
            raise ValueError('raw component and combined activity mismatch')
        if (arms._effective_call(g,Q(0)) != g
                or arms._effective_call(Q(0),self.allocation.effective_request) != self.allocation.effective_request
                or arms._effective_call(g,self.allocation.effective_request) != effective):
            raise ValueError('legacy binary threshold representation mismatch')
        lossless_builtin(self.available_flexibility)

    @property
    def business_hour(self):return self.relative_hour+1

    @property
    def phase(self):return 'enrollment' if self.relative_hour < 168 else 'followup'

    @property
    def grid_request(self):return self.grid_request_mw/self.mechanism.normalized_unit_mw

    @property
    def available_flexibility(self):return self.mechanism.flexible_fraction*self.allocation.workload

    @property
    def identity(self):return _digest([SCHEMA,self])


def current(*,relative_hour,mechanism,workload,source_cfe_at_alpha_one,grid_request_mw):
    if type(mechanism) is not Mechanism:raise ValueError('typed mechanism required')
    for value in (workload,source_cfe_at_alpha_one,grid_request_mw):_exact(value)
    allocation=cfe.allocate(workload,source_cfe_at_alpha_one,mechanism.alpha)
    return ExactCurrent(relative_hour,mechanism,allocation,grid_request_mw)


def _observation(initial_anchor,current):
    current.__post_init__()
    fields=asdict(initial_anchor)
    fields.update(power_source_hour=current.business_hour,workload_source_hour=current.business_hour,
        grid_request=current.grid_request,cfe_request=current.allocation.effective_request,
        workload_occupancy=current.allocation.workload)
    hour=boundary.ContinuationHour(**fields)
    limits=causal_policy.HourlyLimits(Q(1),current.mechanism.recovery_headroom_fraction*(1-current.allocation.workload),
                                    current.allocation.compatible_surplus,Q(1))
    due=current.business_hour+24 if current.grid_request+current.allocation.effective_request else None
    return business.BidirectionalObservation(causal_policy.CurrentObservation(hour,limits,due),
                                             lossless_builtin(current.available_flexibility))


def _state(cursor):
    if cursor.last_plan_cursor is not None or cursor.mode != 'physical_execution':
        raise ValueError('this adapter handles shared actual business execution only')
    tracks=[]
    for name,track in cursor.tracks:
        state=asdict(track.physical.state);state.pop('accounting_period_id')
        tracks.append(dict(name=name,state=state,envelope=track.physical.envelope,
            business_hour=track.physical.anchor.power_source_hour,
            last_hour=track.ledger.last_hour,cohorts=track.ledger.cohorts))
    return dict(arm=cursor.arm_id,mode=cursor.mode,tracks=tracks,period_rule=PERIOD)


@dataclass(frozen=True,init=False)
class BusinessCarry(_Owned):
    implementation: str
    mechanism: Mechanism
    cursor: business.BidirectionalPolicyCursor
    history: tuple

    @property
    def scientific_payload(self):
        spec=asdict(self.cursor.spec);spec.pop('capacity_declaration_id')
        return encoding._encoded(dict(schema=SCHEMA,implementation=self.implementation,
            mechanism=self.mechanism,policy=spec,initial=_state(self.cursor.initial),
            state=_state(self.cursor.execution),inputs=self.history,completed_actions=len(self.history),
            outcomes=[dict(stage=r.stage,error=r.error,committed=r.committed,
                action=None if r.response is None else r.response.action,
                grid_shortfall=None if r.response is None else r.response.grid_shortfall,
                cfe_shortfall=None if r.response is None else r.response.cfe_shortfall)
                for r in self.cursor.records]))

    @property
    def identity(self):return sha256(self.scientific_payload).hexdigest()

    @property
    def audit_identity(self):return _digest(self)


def initialize_development(spec,*,mechanism,anchor,envelope,accounting_period_id):
    if type(mechanism) is not Mechanism or type(anchor) is not boundary.BoundaryAnchor:
        raise ValueError('typed mechanism and compatibility anchor required')
    mechanism.__post_init__();anchor.__post_init__()
    if (anchor.power_source_hour,anchor.workload_source_hour) != (0,0):
        raise ValueError('relative business clock compatibility genesis must be zero')
    if type(spec) is not business.BidirectionalPolicy:
        raise ValueError('approved bidirectional policy type required')
    cursor=business.initialize_capacity_policy(spec,anchor=anchor,envelope=envelope,
        accounting_period_id=accounting_period_id,zero_carry_in_assumption=True)
    return _owned(BusinessCarry,implementation=implementation_identity(),mechanism=mechanism,cursor=cursor,history=())


def _validate(carry):
    if type(carry) is not BusinessCarry or carry.implementation != implementation_identity():
        raise ValueError('current detached business carry required')
    carry.mechanism.__post_init__();carry.cursor.__post_init__()
    if (type(carry.history) is not tuple or len(carry.history) != len(carry.cursor.records)
            or len(carry.history)>192 or carry.cursor.stopped):
        raise ValueError('complete accepted history required')
    origin=carry.cursor.initial.tracks[0][1].physical.anchor
    if (origin.power_source_hour,origin.workload_source_hour)!=(0,0):
        raise ValueError('relative genesis clock changed')
    for i,(item,record) in enumerate(zip(carry.history,carry.cursor.records)):
        if type(item) is not ExactCurrent or item.relative_hour!=i or item.mechanism!=carry.mechanism:
            raise ValueError('fixed mechanism or relative history drift')
        if record.current != _observation(origin,item):
            raise ValueError('replay observation differs from exact current history')
        record.__post_init__()
    if carry.cursor.execution.tracks[0][1].ledger.last_hour != len(carry.history):
        raise ValueError('business ledger progress differs')


@dataclass(frozen=True,init=False)
class BusinessCandidate(_Owned):
    before: BusinessCarry
    current: ExactCurrent
    replay_cursor: business.BidirectionalPolicyCursor
    next_candidate: BusinessCarry | None
    actual_power_mw: Q | None
    status: str
    source_input_binding_verified: bool
    paired_commit_verified: bool
    formal_result: bool


def prepare_development(carry,current,*,expected_current_identity):
    _validate(carry)
    if type(current) is not ExactCurrent:raise ValueError('typed exact current required')
    current.__post_init__()
    if (current.identity != expected_current_identity or current.mechanism != carry.mechanism
            or current.relative_hour != len(carry.history)):
        raise ValueError('current key, mechanism or progress mismatch')
    observation=_observation(carry.cursor.initial.tracks[0][1].physical.anchor,current)
    candidate=business.advance_capacity_policy(carry.cursor,observation)
    record=candidate.records[-1];next_carry=None;power=None
    if record.committed:
        action=record.response.action
        expected=current.allocation.workload-action.grid_served-action.cfe_served+action.recovery
        if (action.actual_service_power != expected or action.grid_served+action.cfe_served+action.recovery
                > Q(str(carry.cursor.spec.committed_capacity))):
            raise ValueError('exact service balance or bidirectional capacity mismatch')
        power=expected*current.mechanism.normalized_unit_mw
        next_carry=_owned(BusinessCarry,implementation=carry.implementation,mechanism=carry.mechanism,
                          cursor=candidate,history=carry.history+(current,))
    if implementation_identity()!=carry.implementation:raise ValueError('implementation changed')
    return _owned(BusinessCandidate,before=carry,current=current,replay_cursor=candidate,
        next_candidate=next_carry,actual_power_mw=power,
        status='business_numerical_candidate' if next_carry is not None else 'business_unresolved',
        source_input_binding_verified=False,paired_commit_verified=False,formal_result=False)
