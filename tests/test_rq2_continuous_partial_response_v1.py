from dataclasses import replace
from fractions import Fraction as Q

import pytest

from test_rq2_continuous_recovery_controller_v1 import F, anchor, obs
from src.rq2_joint_deliverability_boundary_v1.causal_policy import initialize_causal_policy, advance_causal_policy, FixedPolicy
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import JOINT, B6, NETWORK, CFE
from src.rq2_joint_deliverability_boundary_v1.partial_response import (
    DeclaredPartialResponse as Action, PartialResponseCursor,
    advance_partial_response as advance, summarize_partial_response as summarize,
)


def primary(arm=JOINT):
    return initialize_causal_policy(arm,policy=FixedPolicy(),anchor=anchor(),envelope=F['envelope'],
        accounting_period_id='synthetic-period',zero_carry_in_assumption=True)


def rejected(arm=JOINT,g=.25,c=.5):
    r = obs(1,g=g,c=c,due=4)
    origin = advance_causal_policy(primary(arm),r)
    assert origin.halted
    return PartialResponseCursor(origin),r


def partial():
    cursor,r = rejected()
    return advance(cursor,r,Action(.25,.25,0.,.5))


def test_shortfall_is_not_lost_work_or_debt_and_original_request_stays():
    cursor = partial()
    record = cursor.records[-1]
    assert record.committed and record.grid_shortfall == 0 and record.cfe_shortfall == Q('1/4')
    assert record.grid_service_failure is False and record.cfe_service_failure is True
    assert record.observation.hour.cfe_request == .5
    assert record.candidate_step.hour.cfe_request == .25
    assert cursor.execution.tracks[0][1].ledger.debt == Q('1/2')
    origin = cursor.origin
    for t in (2,3):
        cursor = advance(cursor,obs(t),Action(0.,0.,.3125,1.3125,((1,Q('1/4')),)))
    assert cursor.execution.tracks[0][1].ledger.debt == 0
    assert cursor.origin == origin and cursor.origin.halted
    assert len(cursor.execution.tracks[0][1].ledger.cohorts) == 1
    result = summarize(cursor)
    assert result['submitted_unique_hours'] == result['committed_unique_hours'] == 3
    assert result['risk_probability'] is None and result['security_certified'] is False


@pytest.mark.parametrize('arm',[JOINT,B6])
def test_full_call_above_baseline_preserves_original_and_partial_power_balance(arm):
    cursor,r = rejected(arm,g=.4,c=.8)
    assert cursor.origin.records[-1].stage == ('policy_decision' if arm == JOINT else 'separate_planning')
    cursor = advance(cursor,r,Action(.4,.1,0.,.5))
    assert cursor.records[-1].committed
    assert cursor.records[-1].cfe_shortfall == Q('.7')
    assert cursor.records[-1].observation.hour.grid_request + cursor.records[-1].observation.hour.cfe_request > 1


def test_grid_shortfall_is_candidate_only_and_cannot_consume_suffix():
    cursor,r = rejected(g=.75,c=0.)
    before = cursor.execution
    cursor = advance(cursor,r,Action(.5,0.,0.,.5))
    record = cursor.records[-1]
    assert record.status == 'assumed_grid_shortfall_stop' and record.candidate_step is not None
    assert record.grid_shortfall == Q('1/4') and record.candidate_step.cursor != before
    assert record.grid_service_failure is True
    assert cursor.execution == before and cursor.stopped
    result = summarize(cursor)
    assert result['committed_unique_hours'] == 0 and result['business_candidate_hours'] == 1
    assert result['last_committed_source_hour'] == 0
    with pytest.raises(ValueError,match='cannot consume'):
        advance(cursor,obs(2),Action(0.,0.,0.,1.))
    with pytest.raises(ValueError,match='cannot have a suffix'):
        replace(cursor,records=cursor.records+(record,))


def test_zero_response_has_no_new_cohort_despite_original_deadline():
    cursor,r = rejected(CFE,g=0.,c=.6)
    cursor = advance(cursor,r,Action(0.,0.,0.,1.))
    record = cursor.records[-1]
    assert record.committed and record.grid_shortfall is None
    assert record.grid_service_failure is None and record.cfe_service_failure is True
    assert record.cfe_shortfall == Q('.6')
    assert record.observation.due_hour == 4 and record.candidate_step.due_hour is None
    assert not cursor.execution.tracks[0][1].ledger.cohorts


def test_unserved_cfe_allows_declared_idle_recovery_without_invented_debt():
    cursor = partial()
    cursor = advance(cursor,obs(2,g=0.,c=.2,due=5),Action(0.,0.,.25,1.25,((1,Q('.2')),)))
    assert cursor.records[-1].committed
    assert cursor.records[-1].cfe_shortfall == Q('.2')
    assert cursor.execution.tracks[0][1].ledger.debt == Q('.3')
    assert len(cursor.execution.tracks[0][1].ledger.cohorts) == 1


@pytest.mark.parametrize('action',[
    Action(.3,.2,0.,.5), # overserves grid despite feasible total
    Action(.25,.25,0.,.25), # power incorrectly based on full request
    Action(.25,.3,0.,.45), # shared call cap
    Action(.25,.25,.1,.6,((1,Q('.08')),)), # simultaneous call and recovery
    Action(.25,.25,0.,.5,((999,Q('.1')),)),
])
def test_invalid_declared_actions_do_not_advance(action):
    cursor,r = rejected()
    before = cursor.execution
    after = advance(cursor,r,action)
    assert after.stopped and after.records[-1].candidate_step is None
    assert after.records[-1].grid_service_failure is None and after.records[-1].cfe_service_failure is None
    assert after.execution == before


@pytest.mark.parametrize('field,value',[('split','training'),('power_source_hour',99),('workload_provenance_sha256','4'*64)])
def test_source_fault_precedes_action_and_preserves_last_hour(field,value):
    cursor = partial()
    r = obs(2)
    after = advance(cursor,replace(r,hour=replace(r.hour,**{field:value})),Action(0.,0.,0.,1.))
    assert after.stopped and after.execution == cursor.execution
    assert after.records[-1].stage == 'input_validation'
    assert after.records[-1].grid_shortfall is None


def test_representation_ambiguity_stays_unassessed():
    cursor,r = rejected(B6,g=.125,c=6e-7)
    after = advance(cursor,r,Action(.125,0.,0.,.875))
    assert after.stopped and 'effective requests differ' in after.records[-1].error
    assert after.records[-1].candidate_step is None


def test_missing_action_input_origin_and_foreign_projection():
    cursor,r = rejected()
    assert advance(cursor,r,None).stopped
    with pytest.raises(ValueError,match='typed explicit'):
        advance(cursor,r,{})
    origin = advance_causal_policy(primary(),obs(99))
    with pytest.raises(ValueError,match='input failures excluded'):
        PartialResponseCursor(origin)
    cursor,r = rejected(NETWORK,g=.6,c=.5)
    after = advance(cursor,r,Action(.5,.1,0.,.4))
    assert after.stopped and 'outside' in after.records[-1].error


def test_same_rejection_history_and_future_actions_are_separate():
    prefix = partial()
    a = advance(prefix,obs(2),Action(0.,0.,.3125,1.3125,((1,Q('.25')),)))
    b = advance(prefix,obs(2),Action(0.,0.,0.,1.))
    assert a.records[:1] == b.records[:1] == prefix.records
    with pytest.raises(ValueError,match='deterministic replay'):
        replace(prefix.records[0],cfe_shortfall=Q(0))
    changed = replace(prefix.records[0].observation,due_hour=5)
    other_origin = advance_causal_policy(primary(),changed)
    other = advance(PartialResponseCursor(other_origin),changed,prefix.records[0].action)
    with pytest.raises(ValueError,match='exact original'):
        replace(prefix,records=other.records)


@pytest.mark.parametrize('field,value',[
    ('maximum_event_count',0),('maximum_event_duration_hours',.5),
    ('normalized_energy_budget',.25),('normalized_debt_limit',.25),
])
def test_partial_response_cannot_bypass_original_envelope(field,value):
    origin = initialize_causal_policy(JOINT,policy=FixedPolicy(),anchor=anchor(),
        envelope=dict(F['envelope'],**{field:value}),accounting_period_id='synthetic-period',
        zero_carry_in_assumption=True)
    r = obs(1,g=.25,c=.5,due=4)
    origin = advance_causal_policy(origin,r)
    cursor = advance(PartialResponseCursor(origin),r,Action(.25,.25,0.,.5))
    assert cursor.stopped and cursor.records[-1].candidate_step is None
    assert cursor.execution == origin.execution


def test_rest_limit_and_max_duration_remain_enforced():
    origin = primary()
    for t in (1,2,3):
        origin = advance_causal_policy(origin,obs(t,g=.125,c=0.,due=6))
    r = obs(4,g=.125,c=0.,due=7)
    origin = advance_causal_policy(origin,r)
    cursor = advance(PartialResponseCursor(origin),r,Action(.125,0.,0.,.875))
    assert cursor.stopped and 'duration' in cursor.records[-1].error
    origin = primary()
    origin = advance_causal_policy(origin,obs(1,g=.125,c=0.,due=6))
    origin = advance_causal_policy(origin,obs(2,business_recovery_headroom=0.))
    r = obs(3,g=.125,c=0.,due=6)
    origin = advance_causal_policy(origin,r)
    cursor = advance(PartialResponseCursor(origin),r,Action(.125,0.,0.,.875))
    assert cursor.stopped and 'interevent' in cursor.records[-1].error


@pytest.mark.parametrize('due',[None,1])
def test_unknown_deadline_and_permanent_miss_preserved_after_recovery(due):
    r = obs(1,g=.25,c=.5,due=due)
    origin = advance_causal_policy(primary(),r)
    cursor = advance(PartialResponseCursor(origin),r,Action(.25,.25,0.,.5))
    for t in (2,3):
        cursor = advance(cursor,obs(t),Action(0.,0.,.3125,1.3125,((1,Q('.25')),)))
    cohort = cursor.execution.tracks[0][1].ledger.cohorts[0]
    assert cohort.remaining == 0
    assert cohort.due_hour == due
    assert cohort.missed_at_deadline == (None if due is None else Q('.5'))


def test_unallocated_recovery_and_split_chunks():
    cursor = partial()
    invalid = advance(cursor,obs(2),Action(0.,0.,.25,1.25))
    assert invalid.stopped and invalid.execution == cursor.execution
    actions = [(obs(2),Action(0.,0.,.3125,1.3125,((1,Q('.25')),))),
               (obs(3),Action(0.,0.,.3125,1.3125,((1,Q('.25')),))),
               (obs(4),Action(0.,0.,0.,1.))]
    whole = cursor
    for r,a in actions:
        whole = advance(whole,r,a)
    chunked = cursor
    for chunk in (actions[:1],actions[1:]):
        for r,a in chunk:
            chunked = advance(chunked,r,a)
    assert whole == chunked and summarize(whole)['committed_unique_hours'] == 4


@pytest.mark.parametrize('grid,failed',[(.5000005,False),(.500001,False),(.5000011,True)])
def test_grid_shortfall_uses_original_service_tolerance(grid,failed):
    cursor,r = rejected(g=grid,c=.5)
    cursor = advance(cursor,r,Action(.5,0.,0.,.5))
    record = cursor.records[-1]
    assert record.grid_shortfall == Q(str(grid))-Q('.5')
    assert record.grid_service_failure is failed
    assert record.committed is (not failed)
    assert cursor.stopped is failed


@pytest.mark.parametrize('field',['grid_served','cfe_served','recovery','actual_service_power'])
@pytest.mark.parametrize('value',[Q(1,7),True])
def test_response_power_numeric_domain_prevents_fraction_projection_drift(field,value):
    fields = dict(grid_served=.25,cfe_served=.125,recovery=0.,actual_service_power=.625)
    with pytest.raises(ValueError,match='built-in int or float'):
        Action(**dict(fields,**{field:value}))


def test_decimal_response_matches_exact_debt_and_candidate_cannot_replace_origin():
    cursor,r = rejected()
    c = float(Q(1,7))
    cursor = advance(cursor,r,Action(.25,c,0,1-(.25+c)))
    record = cursor.records[-1]
    assert record.committed
    assert cursor.execution.tracks[0][1].ledger.debt == Q('.25')+Q(str(c))
    assert record.cfe_shortfall == Q('.5')-Q(str(c))
    assert record.observation == r
    with pytest.raises(ValueError,match='halted action or planning'):
        PartialResponseCursor(record.candidate_step.cursor)
