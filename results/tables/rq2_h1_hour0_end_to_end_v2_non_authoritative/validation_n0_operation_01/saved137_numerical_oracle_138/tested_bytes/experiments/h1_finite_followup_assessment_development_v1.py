"""Finite enrollment stopping facts for replayed business carries; no admission.

The persistent successor must rebuild the carry and combine these facts with
paired actual/outer outcomes before consuming them. No source row is read here.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import yaml

from experiments import h1_exact_business_development_v1 as business

SCHEMA='h1_finite_followup_assessment_development_v1'
ROOT=Path(__file__).resolve().parents[1]
PINS={
    'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml':
        '95eb158f0a8e6784d2af401e67164965543c98f42ff02b756c214982601e5430',
    'docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md':
        '09ed8b1a51a27a0bf17de2c18d37a375180a6a294dd5d8714f759f272ade5dfd',
}
WINDOW=dict(enrollment_hours=168,stride_hours=24,maximum_followup_hours=24,due_hours_after_birth=24,
    due_endpoint='recover_then_check_remaining_debt',
    accounting='one_nonrolling_episode_without_followup_reset_or_budget_increment',
    primary_births='enrollment_only',retain_followup_births_and_all_debt=True,
    missing_needed_followup='unresolved',enrollment_input_validation='whole_enrollment_window',
    followup_input_validation='next_hour_only_when_needed_for_enrollment_outcome')


def contract_identity():
    for name,pin in PINS.items():
        if sha256((ROOT/name).read_bytes()).hexdigest()!=pin:raise ValueError('approved finite mechanism bytes changed')
    config=yaml.safe_load((ROOT/next(iter(PINS))).read_bytes())
    if (config['window']!=WINDOW or config['scientific_parameters_approved'] is not True
            or config['formal_execution_ready'] is not False or config['formal_run_authority'] is not False):
        raise ValueError('approved finite mechanism declaration differs')
    return business._digest([SCHEMA,PINS,WINDOW])


def implementation_identity():
    return business._digest([contract_identity(),business.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest(),yaml.__version__])


@dataclass(frozen=True)
class CohortFact:
    birth_hour: int
    due_hour: int
    incurred: business.Q
    remaining: business.Q
    missed_at_deadline: business.Q | None
    status: str


@dataclass(frozen=True)
class Assessment:
    contract_identity: str
    implementation_identity: str
    carry_identity: str
    completed_business_hours: int
    grid_request_status: str | None
    cfe_request_status: str | None
    primary_recovery_status: str
    primary_cohorts: tuple
    followup_cohorts: tuple
    pending_primary_births: tuple
    last_primary_due: int | None
    retained_total_debt: business.Q
    needs_next_hour: bool
    next_relative_hour: int | None
    next_phase: str | None
    stop_reason: str
    all_component_observations_known: bool
    any_component_failure_observed: bool
    complete_contract_status: None = None
    detached_consumer_authenticated: bool = False
    actual_paired_commit_verified: bool = False
    source_availability_checked: bool = False
    followup_execution_admitted: bool = False
    formal_result: bool = False

    @property
    def identity(self):return business._digest(self)


def _cohort(cohort,hour):
    if (type(cohort.created_hour) is not int or not 1<=cohort.created_hour<=hour
            or type(cohort.due_hour) is not int or cohort.due_hour!=cohort.created_hour+24):
        raise ValueError('cohort violates fixed birth/due contract')
    missed=cohort.missed_at_deadline
    if missed is not None:
        if hour<cohort.due_hour:raise ValueError('deadline snapshot precedes due hour')
        status='failure_at_due' if missed>0 else 'success_by_due'
    elif hour>=cohort.due_hour:
        raise ValueError('required deadline snapshot missing')
    elif cohort.remaining==0:status='success_before_due'
    else:status='pending_before_due'
    return CohortFact(cohort.created_hour,cohort.due_hour,cohort.incurred,cohort.remaining,missed,status)


def _request_status(carry,field,applicable):
    flags=[]
    for record in carry.cursor.records[:168]:
        if record.committed is not True or record.response is None:
            raise ValueError('uncommitted candidate is not business history')
        flag=getattr(record.response,field)
        if (applicable and type(flag) is not bool) or (not applicable and flag is not None):
            raise ValueError('request dimension applicability differs')
        flags.append(flag)
    if not applicable:return None
    if any(flag is True for flag in flags):return 'F'
    return 'S' if len(flags)==168 else 'U'


def assess_development(carry,*,expected_carry_identity):
    """Check the complete deterministic business history, never mint a source credential.

Request observations and shared recovery are separate dimensions. The shared
ledger has no grid/CFE debt attribution, so no such attribution is fabricated.
"""
    own=implementation_identity();contract=contract_identity()
    business._validate(carry)
    if carry.identity!=expected_carry_identity:raise ValueError('expected business carry identity differs')
    hour=len(carry.history)
    tracks=carry.cursor.execution.tracks
    if len(tracks)!=1 or tracks[0][0]!='shared':raise ValueError('one shared actual execution ledger required')
    ledger=tracks[0][1].ledger
    if ledger.last_hour!=hour or not 0<=hour<=192:raise ValueError('complete relative business clock required')
    facts=tuple(_cohort(c,hour) for c in ledger.cohorts)
    primary=tuple(c for c in facts if c.birth_hour<=168)
    followup=tuple(c for c in facts if c.birth_hour>168)
    pending=tuple(c.birth_hour for c in primary if c.status=='pending_before_due')
    if hour==192 and pending:raise ValueError('primary remains pending after the absolute episode boundary')
    recovery=('F' if any(c.status=='failure_at_due' for c in primary)
              else 'U' if hour<168 or pending else 'S')
    arm=carry.cursor.spec.arm_id
    grid=_request_status(carry,'grid_service_failure',arm!=business.arms.CFE)
    cfe=_request_status(carry,'cfe_service_failure',arm!=business.arms.NETWORK)
    need=hour<168 or bool(pending)
    reason='enrollment_remaining' if hour<168 else 'primary_deadline_pending' if pending else 'primary_resolved'
    components=tuple(x for x in (grid,cfe,recovery) if x is not None)
    result=Assessment(contract,own,carry.identity,hour,grid,cfe,recovery,primary,followup,pending,
        max((c.due_hour for c in primary),default=None),ledger.debt,need,hour if need else None,
        ('enrollment' if hour<168 else 'followup') if need else None,reason,
        hour>=168 and not pending and all(s!='U' for s in components),any(s=='F' for s in components))
    if implementation_identity()!=own:raise ValueError('followup assessment implementation changed')
    return result


@dataclass(frozen=True)
class LaneAssessment:
    lane_id: str
    owner_disposition: str
    business: Assessment
    needs_next_hour: bool
    disposition_reason: str


@dataclass(frozen=True)
class RosterAssessment:
    implementation_identity: str
    completed_outer_hours: int
    lanes: tuple
    needs_next_hour: bool
    next_relative_hour: int | None
    owner_replay_authenticated: bool = False
    actual_paired_commit_verified: bool = False
    producer_admitted: bool = False
    formal_result: bool = False


def assess_roster_development(*,completed_outer_hours,lanes):
    """Detached roster facts for integration tests and a future live owner.

Each entry is (lane_id, disposition, BusinessCarry); only a persistent owner
may establish disposition from replayed paired outcomes. This function cannot.
"""
    own=implementation_identity()
    if type(completed_outer_hours) is not int or not 0<=completed_outer_hours<=192:
        raise ValueError('bounded outer hour required')
    if type(lanes) is not tuple or not lanes:raise ValueError('nonempty canonical roster required')
    ids=tuple(row[0] for row in lanes)
    if any(type(k) is not str or not k for k in ids) or ids!=tuple(sorted(set(ids))):
        raise ValueError('unique sorted lane identities required')
    result=[]
    for lane_id,disposition,carry in lanes:
        if disposition not in ('active','completed','halted_unresolved'):raise ValueError('explicit lane disposition required')
        item=assess_development(carry,expected_carry_identity=carry.identity)
        if item.completed_business_hours>completed_outer_hours:raise ValueError('lane is ahead of outer progress')
        if disposition=='active' and item.completed_business_hours!=completed_outer_hours:
            raise ValueError('active lane must share the current outer clock')
        if disposition=='completed' and item.needs_next_hour:
            raise ValueError('completed lane still has unresolved primary obligations')
        need=disposition=='active' and item.needs_next_hour
        reason=item.stop_reason if disposition=='active' else disposition
        result.append(LaneAssessment(lane_id,disposition,item,need,reason))
    need=any(v.needs_next_hour for v in result)
    if implementation_identity()!=own or any(v.business.implementation_identity!=own for v in result):
        raise ValueError('roster assessment implementation changed')
    return RosterAssessment(own,completed_outer_hours,tuple(result),need,completed_outer_hours if need else None)
