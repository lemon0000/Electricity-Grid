"""Draft explicit partial-response accounting; no policy or safety certificate."""
from dataclasses import dataclass, replace
from fractions import Fraction as Q

from .boundary import SERVICE_TOLERANCE, _number, _validate_next_identity
from .causal_policy import CurrentObservation, PolicyCursor
from .actual_actions import DeclaredActualAction, _evaluate_actual
from .four_arm_replay import ArmCursor, ArmStep, NETWORK, CFE, JOINT, B6, _effective_call


CONTRACT_ID = 'explicit_partial_response_zero_loss_grid_shortfall_stop_v1'
ORIGIN_STAGES = frozenset({'policy_decision', 'separate_planning', 'physical_execution', 'shared_execution'})


@dataclass(frozen=True)
class DeclaredPartialResponse:
    grid_served: float
    cfe_served: float
    recovery: float
    actual_service_power: float
    allocations: tuple[tuple[int, Q], ...] = ()
    evidence_class: str = 'mechanism_assumption'

    def __post_init__(self):
        for name in ('grid_served','cfe_served','recovery','actual_service_power'):
            if type(getattr(self,name)) not in (int,float):
                raise ValueError('response power fields require built-in int or float')
        _number(self.grid_served, 'grid response')
        _number(self.cfe_served, 'CFE response')
        DeclaredActualAction(self.recovery, self.actual_service_power,
                            self.allocations, self.evidence_class)


def _evaluate_response(before, observation, action):
    stage = 'input_validation'
    sg = sc = None
    try:
        hour = observation.hour
        if (hour.arm_id, hour.track_id) != (JOINT, 'shared'):
            raise ValueError('common JOINT/shared source container required')
        for _, track in before.tracks:
            _validate_next_identity(track.physical.anchor, hour)
        if action is None:
            return stage, 'unassessed', 'missing_partial_response', None, None, None
        stage = 'response_accounting'
        use_grid, use_cfe = before.arm_id != CFE, before.arm_id != NETWORK
        g_raw = hour.grid_request if use_grid else 0.
        c_raw = hour.cfe_request if use_cfe else 0.
        g_req, c_req = _effective_call(g_raw, 0.), _effective_call(0., c_raw)
        if g_req + c_req != _effective_call(g_raw, c_raw):
            raise ValueError('separate and shared effective requests differ')
        if (not use_grid and action.grid_served != 0.) or (not use_cfe and action.cfe_served != 0.):
            raise ValueError('response outside the original arm projection')
        g = _effective_call(action.grid_served, 0.)
        c = _effective_call(0., action.cfe_served)
        if g > g_req or c > c_req:
            raise ValueError('response exceeds original effective request')
        if g + c != _effective_call(action.grid_served, action.cfe_served):
            raise ValueError('separate and shared effective responses differ')
        if _effective_call(float(g),float(c)) != g+c:
            raise ValueError('executed response has no identical decimal-float projection')
        sg, sc = (g_req-g if use_grid else None), (c_req-c if use_cfe else None)
        # This is an executed-obligation projection, never a source observation.
        projected = replace(observation, hour=replace(hour,grid_request=float(g),cfe_request=float(c)),
                            due_hour=observation.due_hour if g+c else None)
        actual = DeclaredActualAction(action.recovery,action.actual_service_power,action.allocations)
        stage = 'business_validation'
        _, error, step = _evaluate_actual(before,projected,actual)
        if error is not None:
            return stage, 'unassessed', error, None, sg, sc
    except (ValueError, OverflowError) as error:
        return stage, 'unassessed', str(error), None, sg, sc
    if sg is not None and sg > Q(str(SERVICE_TOLERANCE)):
        return 'grid_obligation', 'assumed_grid_shortfall_stop', 'declared_grid_response_shortfall', step, sg, sc
    return stage, 'assumed_response_committed', None, step, sg, sc


@dataclass(frozen=True)
class PartialResponseRecord:
    before: ArmCursor
    observation: CurrentObservation
    action: DeclaredPartialResponse | None
    stage: str
    status: str
    error: str | None
    candidate_step: ArmStep | None
    grid_shortfall: Q | None
    cfe_shortfall: Q | None

    def __post_init__(self):
        if (not isinstance(self.before,ArmCursor) or self.before.mode != 'physical_execution'
            or self.before.arm_id not in {NETWORK,CFE,JOINT,B6}):
            raise ValueError('typed shared physical state required')
        if not isinstance(self.observation,CurrentObservation):
            raise ValueError('one current observation required')
        if self.action is not None and not isinstance(self.action,DeclaredPartialResponse):
            raise ValueError('typed explicit partial response required')
        if (self.stage,self.status,self.error,self.candidate_step,self.grid_shortfall,self.cfe_shortfall) != _evaluate_response(
                self.before,self.observation,self.action):
            raise ValueError('partial response differs from deterministic replay')

    @property
    def committed(self):
        return self.status == 'assumed_response_committed'

    @property
    def grid_service_failure(self):
        if self.candidate_step is None or self.grid_shortfall is None:
            return None
        return self.grid_shortfall > Q(str(SERVICE_TOLERANCE))

    @property
    def cfe_service_failure(self):
        if self.candidate_step is None or self.cfe_shortfall is None:
            return None
        return self.cfe_shortfall > Q(str(SERVICE_TOLERANCE))


@dataclass(frozen=True)
class PartialResponseCursor:
    origin: PolicyCursor
    records: tuple[PartialResponseRecord, ...] = ()
    contract_id: str = CONTRACT_ID

    def __post_init__(self):
        if (not isinstance(self.origin,PolicyCursor) or not self.origin.halted
            or self.origin.records[-1].stage not in ORIGIN_STAGES):
            raise ValueError('halted action or planning rejection required; input failures excluded')
        if self.contract_id != CONTRACT_ID or not isinstance(self.records,tuple):
            raise ValueError('fixed partial-response contract and immutable history required')
        previous = self.origin.execution
        for i, record in enumerate(self.records):
            if not isinstance(record,PartialResponseRecord) or record.before != previous:
                raise ValueError('partial-response state chain changed')
            if i == 0 and record.observation != self.origin.records[-1].observation:
                raise ValueError('first response must address the exact original rejection')
            if record.committed:
                previous = record.candidate_step.cursor
            elif i != len(self.records)-1:
                raise ValueError('uncommitted response cannot have a suffix')

    @property
    def execution(self):
        committed = [r for r in self.records if r.committed]
        return committed[-1].candidate_step.cursor if committed else self.origin.execution

    @property
    def stopped(self):
        return bool(self.records and not self.records[-1].committed)


def advance_partial_response(cursor, observation, action):
    if cursor.stopped:
        raise ValueError('uncommitted partial response cannot consume later observations')
    if not isinstance(observation,CurrentObservation):
        raise ValueError('one current observation required')
    if action is not None and not isinstance(action,DeclaredPartialResponse):
        raise ValueError('typed explicit partial response required')
    record = PartialResponseRecord(cursor.execution,observation,action,
                                    *_evaluate_response(cursor.execution,observation,action))
    return PartialResponseCursor(cursor.origin,cursor.records+(record,))


def summarize_partial_response(cursor):
    prefix = sum(r.status == 'accepted' for r in cursor.origin.records)
    committed = sum(r.committed for r in cursor.records)
    return {
        'contract_id': cursor.contract_id, 'evidence_class': 'derived_synthetic_diagnostic',
        'submitted_unique_hours': len(cursor.origin.records)+max(0,len(cursor.records)-1),
        'primary_accepted_hours': prefix, 'response_committed_hours': committed,
        'committed_unique_hours': prefix+committed,
        'business_candidate_hours': sum(r.candidate_step is not None for r in cursor.records),
        'phase': 'unassessed_stop' if cursor.stopped else ('explicit_response' if cursor.records else 'awaiting_response'),
        'original_rejection_source_hour': cursor.origin.records[-1].observation.hour.power_source_hour,
        'original_rejection_submission_index': len(cursor.origin.records),
        'last_committed_source_hour': cursor.execution.tracks[0][1].physical.anchor.power_source_hour,
        'remaining_debt': tuple((name,track.ledger.debt) for name,track in cursor.execution.tracks),
        'formal_result': False, 'security_certified': False, 'completion_claim_allowed': False,
        'causal_policy_implemented': False, 'risk_probability': None,
    }
