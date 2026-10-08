from dataclasses import replace, FrozenInstanceError
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor, ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6
from src.rq2_joint_deliverability_boundary_v1.causal_policy import (
    FixedPolicy, HourlyLimits, CurrentObservation, initialize_causal_policy,
    advance_causal_policy, summarize_policy_prefix,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT/'configs/rq2_continuous_causal_policy_v1.DRAFT.yaml').read_text(encoding='utf-8'))
F = CONFIG['fixture']


def anchor():
    return BoundaryAnchor(JOINT,'shared','holdout',0,100,'synthetic-power','synthetic-work',
                          '1'*64,0,'2'*64,'3'*64)


def init(arm=JOINT, **changes):
    args=dict(policy=FixedPolicy(CONFIG['policy']['rule'],CONFIG['policy']['recovery_decimal_places']),
              anchor=anchor(),envelope=F['envelope'],accounting_period_id='synthetic-period',
              zero_carry_in_assumption=True)
    args.update(changes)
    return initialize_causal_policy(arm,**args)


def observation(t,g=0.,c=0.,due=None,**limits):
    h=ContinuationHour(**dict(anchor().__dict__,power_source_hour=t,workload_source_hour=100+t),
                       grid_request=g,cfe_request=c,workload_occupancy=1.)
    cap=HourlyLimits(F['call_limit'],F['business_recovery_headroom'],
                     F['cfe_compatible_surplus'],F['maximum_recovery_power'])
    return CurrentObservation(h,replace(cap,**limits),due)


def fixture_row(t):
    active=t in F['call_hours']
    return observation(t,F['grid_request'] if active else 0.,F['cfe_request'] if active else 0.,
                       t+F['deadline_offset_hours'] if active else None)


@pytest.mark.parametrize('arm',[NETWORK,CFE,JOINT])
def test_48h_causal_policy_carries_events_debt_and_counts_exposure(arm):
    cursor=init(arm)
    history=[]
    for t in range(1,F['hours']+1):
        cursor=advance_causal_policy(cursor,fixture_row(t))
        assert not cursor.halted
        history.append(cursor)
    track=dict(history[23].execution.tracks)['shared']
    assert track.physical.state.event_count==1
    assert track.physical.state.active_duration_hours==2
    assert track.ledger.debt==(Q('.5') if arm==JOINT else Q('.25'))
    result=summarize_policy_prefix(cursor)
    assert result['accepted_hours']==result['submitted_hours']==48
    assert result['remaining_debt']==(('shared',Q(0)),)
    assert result['deadline_missed_count']==0
    assert result['completion_claim_allowed'] is False


@pytest.mark.parametrize('first_due',[None,10])
def test_earliest_known_deadline_precedes_unknown_or_later_deadline(first_due):
    cursor=advance_causal_policy(init(),observation(1,.125,due=first_due))
    cursor=advance_causal_policy(cursor,observation(2,.125,due=4))
    cursor=advance_causal_policy(cursor,observation(3,business_recovery_headroom=.15625))
    assert not cursor.halted
    selected=dict(cursor.records[-1].attempted_actions)['shared']
    assert selected.allocations==((2,Q('.125')),)
    assert dict(cursor.execution.tracks)['shared'].ledger.cohorts[0].remaining==Q('.125')


def test_unknown_deadlines_use_fifo_and_stay_unknown_after_recovery():
    cursor=advance_causal_policy(init(),observation(1,.125))
    cursor=advance_causal_policy(cursor,observation(2,.125))
    cursor=advance_causal_policy(cursor,observation(3,business_recovery_headroom=.15625))
    assert dict(cursor.records[-1].attempted_actions)['shared'].allocations==((1,Q('.125')),)
    assert summarize_policy_prefix(cursor)['deadline_unidentified_count']==2


def test_policy_never_borrows_future_recovery_or_changes_prefix_for_future_inputs():
    left=init()
    for t in range(1,25):
        left=advance_causal_policy(left,fixture_row(t))
    right=init()
    for chunk in [range(1,13),range(13,25)]:
        for t in chunk:
            right=advance_causal_policy(right,fixture_row(t))
    assert left==right
    a=advance_causal_policy(left,observation(25,.125,.125,28))
    b=advance_causal_policy(right,observation(25,business_recovery_headroom=0.))
    assert a.records[:24]==b.records[:24]
    for record in left.records[22:]:
        assert all(action.physical.recovery==0 for _,action in record.attempted_actions)
    with pytest.raises(ValueError,match='one CurrentObservation'):
        advance_causal_policy(left,[fixture_row(25),fixture_row(26)])


def test_capacity_rejection_preserves_prefix_and_stops_without_clipping():
    cursor=advance_causal_policy(init(),observation(1,.25,due=3))
    rejected=advance_causal_policy(cursor,observation(2,.3,.3,4))
    assert rejected.halted and rejected.execution==cursor.execution
    r=rejected.records[-1]
    assert r.stage=='physical_execution' and 'call limit' in r.error
    assert r.observation.hour.grid_request==r.observation.hour.cfe_request==.3
    assert dict(r.attempted_actions)['shared'].physical.actual_service_power==.4
    summary=summarize_policy_prefix(rejected)
    assert summary['accepted_hours']==1 and summary['submitted_hours']==2
    assert summary['last_committed_power_hour']==1 and summary['rejected_power_hour']==2
    assert summary['remaining_debt']==(('shared',Q('.25')),)
    with pytest.raises(ValueError,match='halted policy prefix'):
        advance_causal_policy(rejected,observation(3))


@pytest.mark.parametrize('field,value',[('split','training'),('power_source_hour',3),
                                      ('workload_normalization_sha256','4'*64)])
def test_invalid_observation_is_input_rejection_not_service_failure(field,value):
    obs=observation(1)
    rejected=advance_causal_policy(init(),replace(obs,hour=replace(obs.hour,**{field:value})))
    assert rejected.halted
    assert rejected.records[-1].stage=='input_validation'
    assert rejected.records[-1].attempted_actions==()
    assert summarize_policy_prefix(rejected)['accepted_hours']==0


def test_b6_separate_policy_success_does_not_commit_failed_shared_recovery():
    cursor=init(B6)
    for t in range(1,26):
        cursor=advance_causal_policy(cursor,fixture_row(t))
        assert not cursor.halted
    rejected=advance_causal_policy(cursor,fixture_row(26))
    assert rejected.halted
    assert rejected.execution==cursor.execution and rejected.planning==cursor.planning
    record=rejected.records[-1]
    assert record.stage=='shared_execution'
    assert record.planned_step is not None and record.accepted_step is None
    assert 'headroom' in record.error
    assert summarize_policy_prefix(rejected)['remaining_debt']==(('shared',Q('.75')),)
    assert summarize_policy_prefix(rejected)['accepted_hours']==25


def test_observed_deadline_miss_persists_after_late_policy_recovery():
    cursor=advance_causal_policy(init(),observation(1,.25,due=2))
    cursor=advance_causal_policy(cursor,observation(2,business_recovery_headroom=0.))
    assert summarize_policy_prefix(cursor)['deadline_missed_count']==1
    cursor=advance_causal_policy(cursor,observation(3))
    assert summarize_policy_prefix(cursor)['remaining_debt']==(('shared',Q(0)),)
    assert summarize_policy_prefix(cursor)['deadline_missed_count']==1


def test_fixed_quantization_is_conservative_and_residual_is_not_erased():
    cursor=advance_causal_policy(init(policy=FixedPolicy(recovery_decimal_places=2)),observation(1,.25,due=2))
    cursor=advance_causal_policy(cursor,observation(2))
    assert not cursor.halted
    assert dict(cursor.records[-1].attempted_actions)['shared'].physical.recovery==.31
    assert summarize_policy_prefix(cursor)['remaining_debt']==(('shared',Q('.002')),)
    assert summarize_policy_prefix(cursor)['deadline_missed_count']==1


def test_fixed_policy_cannot_change_after_an_observed_prefix():
    cursor=advance_causal_policy(init(),observation(1))
    with pytest.raises(ValueError,match='policy cannot change'):
        replace(cursor,policy=FixedPolicy(recovery_decimal_places=2))
    with pytest.raises(FrozenInstanceError):
        cursor.policy.recovery_decimal_places=2
    with pytest.raises(ValueError,match='halt status'):
        replace(cursor,halted=True)


def test_unobserved_deadline_reports_censoring_at_last_committed_hour():
    cursor=advance_causal_policy(init(),observation(1,.25,due=5))
    summary=summarize_policy_prefix(cursor)
    assert summary['right_censored_count']==1
    assert summary['completion_claim_allowed'] is False


@pytest.mark.parametrize('arm,expected_recovery',[(NETWORK,.15625),(CFE,0.),(JOINT,0.)])
def test_causal_recovery_obeys_arm_specific_current_surplus(arm,expected_recovery):
    cursor=advance_causal_policy(init(arm),observation(1,.125,.125,3))
    cursor=advance_causal_policy(cursor,observation(2,cfe_compatible_surplus=0.))
    assert dict(cursor.records[-1].attempted_actions)['shared'].physical.recovery==expected_recovery


@pytest.mark.parametrize('g,c',[(6e-7,6e-7),(.125,6e-7)])
def test_b6_threshold_decomposition_rejects_without_losing_deadline(g,c):
    before=init(B6)
    obs=observation(1,g,c,3)
    after=advance_causal_policy(before,obs)
    assert after.halted and after.execution==before.execution and after.planning==before.planning
    record=after.records[-1]
    assert record.stage=='policy_decision' and 'effective obligations differ' in record.error
    assert record.observation==obs and record.observation.due_hour==3
    assert record.planned_step is None and record.attempted_actions==()


@pytest.mark.parametrize('field',['observation','attempted_actions','stage'])
def test_accepted_record_binds_inputs_actions_and_stage(field):
    cursor=advance_causal_policy(init(),observation(1,.125,due=3))
    changes={'observation':observation(1,.25,due=3),
             'attempted_actions':(), 'stage':'input_validation'}
    with pytest.raises(ValueError,match='deterministic replay'):
        replace(cursor.records[-1],**{field:changes[field]})


def test_rejected_record_binds_error_and_prefix_chain():
    first=advance_causal_policy(init(),observation(1,.125,due=3))
    rejected=advance_causal_policy(first,observation(2,.3,.3,4))
    with pytest.raises(ValueError,match='deterministic replay'):
        replace(rejected.records[-1],error='invented rejection')
    other=advance_causal_policy(init(),observation(1,.25,due=3))
    with pytest.raises(ValueError,match='state chain'):
        replace(rejected,records=(other.records[0],rejected.records[1]))


def test_finite_b6_recoveries_with_overflowing_sum_are_audited_rejection():
    before=init(B6,envelope=dict(F['envelope'],recovery_efficiency=5e-324))
    before=advance_causal_policy(before,observation(1,.5,.5,3,call_limit=1.))
    assert not before.halted
    after=advance_causal_policy(before,observation(2,business_recovery_headroom=1e308,
        cfe_compatible_surplus=1e308,maximum_recovery_power=1e308))
    assert after.halted and after.execution==before.execution and after.planning==before.planning
    record=after.records[-1]
    assert record.stage=='shared_execution' and record.planned_step is not None
    assert 'float' in record.error and record.accepted_step is None
