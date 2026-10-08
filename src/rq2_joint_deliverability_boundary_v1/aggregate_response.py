"""Exact aggregate-response accounting for the continuous fixed policy.

Positive service components are retained exactly; activity is defined on their
sum. This is a separate draft contract from the float partial-response API.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as Q

from .boundary import SERVICE_TOLERANCE, _validate_next_identity
from .causal_policy import CurrentObservation
from .actual_actions import DeclaredActualAction, _evaluate_actual
from .four_arm_replay import ArmCursor, ArmStep, NETWORK, CFE, JOINT, _effective_call


@dataclass(frozen=True)
class DeclaredAggregateResponse:
    grid_served: Q
    cfe_served: Q
    recovery: Q
    actual_service_power: Q
    allocations: tuple[tuple[int,Q],...] = ()
    evidence_class: str = 'mechanism_assumption'

    def __post_init__(self):
        for name in ('grid_served','cfe_served','recovery','actual_service_power'):
            value = getattr(self,name)
            if not isinstance(value,Q) or value < 0:
                raise ValueError('aggregate response requires exact nonnegative Fraction quantities')
        DeclaredActualAction(self.recovery,self.actual_service_power,self.allocations,self.evidence_class)


def _evaluate_aggregate(before,observation,action):
    stage,sg,sc = 'input_validation',None,None
    try:
        hour = observation.hour
        if (hour.arm_id,hour.track_id) != (JOINT,'shared'):
            raise ValueError('common JOINT/shared source container required')
        for _,track in before.tracks:
            _validate_next_identity(track.physical.anchor,hour)
        stage = 'response_accounting'
        gr = hour.grid_request if before.arm_id != CFE else 0.
        cr = hour.cfe_request if before.arm_id != NETWORK else 0.
        greq,creq = _effective_call(gr,0.),_effective_call(0.,cr)
        if greq+creq != _effective_call(gr,cr):
            raise ValueError('separate and shared effective requests differ')
        g,c = action.grid_served,action.cfe_served
        if g > greq or c > creq:
            raise ValueError('response exceeds original arm effective request')
        total = g+c
        if total and total <= Q(str(SERVICE_TOLERANCE)):
            raise ValueError('positive aggregate response must exceed the activity threshold')
        if _effective_call(g,c) != total:
            raise ValueError('aggregate activity representation differs')
        if total and action.recovery:
            raise ValueError('active aggregate response requires exactly zero recovery')
        if action.recovery and action.recovery <= Q(str(SERVICE_TOLERANCE)):
            raise ValueError('positive recovery must exceed the effective threshold')
        if action.actual_service_power != Q(str(hour.workload_occupancy))-total+action.recovery:
            raise ValueError('exact aggregate service power balance violated')
        sg = greq-g if before.arm_id != CFE else None
        sc = creq-c if before.arm_id != NETWORK else None
        # Fractions are retained in this derived projection: no lossy float cast.
        projected = replace(observation,hour=replace(hour,grid_request=g,cfe_request=c),
                            due_hour=observation.due_hour if total else None)
        actual = DeclaredActualAction(action.recovery,action.actual_service_power,action.allocations)
        stage = 'business_validation'
        _,error,step = _evaluate_actual(before,projected,actual)
        if error is not None:
            return stage,'unassessed',error,None,sg,sc
    except (ValueError,OverflowError) as error:
        return stage,'unassessed',str(error),None,sg,sc
    if sg is not None and sg > Q(str(SERVICE_TOLERANCE)):
        return 'grid_obligation','assumed_grid_shortfall_stop','declared_grid_response_shortfall',step,sg,sc
    return stage,'assumed_response_committed',None,step,sg,sc


@dataclass(frozen=True)
class AggregateResponseRecord:
    before: ArmCursor
    observation: CurrentObservation
    action: DeclaredAggregateResponse
    stage: str
    status: str
    error: str | None
    candidate_step: ArmStep | None
    grid_shortfall: Q | None
    cfe_shortfall: Q | None

    def __post_init__(self):
        if not isinstance(self.before,ArmCursor) or self.before.mode != 'physical_execution':
            raise ValueError('typed shared physical state required')
        if not isinstance(self.observation,CurrentObservation) or not isinstance(self.action,DeclaredAggregateResponse):
            raise ValueError('typed original observation and exact action required')
        if (self.stage,self.status,self.error,self.candidate_step,self.grid_shortfall,self.cfe_shortfall) != _evaluate_aggregate(
                self.before,self.observation,self.action):
            raise ValueError('aggregate response differs from deterministic replay')

    @property
    def committed(self):
        return self.status == 'assumed_response_committed'

    @property
    def grid_service_failure(self):
        return None if self.candidate_step is None or self.grid_shortfall is None else self.grid_shortfall > Q(str(SERVICE_TOLERANCE))

    @property
    def cfe_service_failure(self):
        return None if self.candidate_step is None or self.cfe_shortfall is None else self.cfe_shortfall > Q(str(SERVICE_TOLERANCE))
