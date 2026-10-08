from dataclasses import replace
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor, ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.causal_policy import (
    FixedPolicy, HourlyLimits, CurrentObservation, initialize_causal_policy, advance_causal_policy,
)
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import B6, JOINT, NETWORK, CFE
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import assess_debt_cohorts
from src.rq2_joint_deliverability_boundary_v1.actual_actions import (
    DeclaredActualAction, ActualActionCursor, advance_actual_action,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = yaml.safe_load((ROOT/'configs/rq2_continuous_actual_action_contract_v1.DRAFT.yaml').read_text(encoding='utf-8'))
SOURCE = yaml.safe_load((ROOT/CONTRACT['fixture']['source_config']).read_text(encoding='utf-8'))
F = SOURCE['fixture']


def anchor():
    return BoundaryAnchor(JOINT,'shared','holdout',0,100,'synthetic-power','synthetic-work',
                          '1'*64,0,'2'*64,'3'*64)


def observation(t, *, unknown=False, grid=None, cfe=None):
    active = t in F['call_hours']
    h = ContinuationHour(**dict(anchor().__dict__, power_source_hour=t, workload_source_hour=100+t),
        grid_request=(F['grid_request'] if active else 0.) if grid is None else grid,
        cfe_request=(F['cfe_request'] if active else 0.) if cfe is None else cfe,
        workload_occupancy=1.)
    return CurrentObservation(h, HourlyLimits(F['call_limit'],F['business_recovery_headroom'],
        F['cfe_compatible_surplus'],F['maximum_recovery_power']),
        t+F['deadline_offset_hours'] if active and not unknown else None)


def rejected_prefix(*, unknown=False):
    cursor = initialize_causal_policy(B6, policy=FixedPolicy(), anchor=anchor(), envelope=F['envelope'],
        accounting_period_id='synthetic-period', zero_carry_in_assumption=True)
    for t in range(1, CONTRACT['fixture']['rejection_hour']+1):
        cursor = advance_causal_policy(cursor, observation(t, unknown=unknown))
    assert cursor.halted and cursor.records[-1].stage == 'shared_execution'
    return cursor


def action_for(alternative, t):
    spec = alternative['actions'].get(t, CONTRACT['fixture']['default_idle_action'])
    return DeclaredActualAction(spec['recovery'], spec['power'],
        tuple((hour,Q(amount)) for hour,amount in spec['allocations']))


def ledger(cursor):
    return dict(cursor.execution.tracks)['shared'].ledger


@pytest.mark.parametrize('alternative', CONTRACT['fixture']['alternatives'], ids=lambda a:a['id'])
def test_declared_48h_suffix_balances_and_preserves_rejected_origin(alternative):
    origin = rejected_prefix()
    cursor = ActualActionCursor(origin)
    origin_debt = ledger(cursor).debt
    for t in range(26, 49):
        before = cursor
        action = action_for(alternative,t)
        cursor = advance_actual_action(cursor,observation(t),action)
        assert not cursor.stopped
        assert ledger(cursor).debt == ledger(before).debt-Q('0.8')*Q(str(action.recovery))
        assert cursor.records[-1].step.hour == observation(t).hour
    assert origin.halted and origin.execution == cursor.origin.execution
    assert ledger(ActualActionCursor(origin)).debt == origin_debt == Q('3/4')
    assert len(origin.records) == 26 and len(cursor.records) == 23
    assert ledger(cursor).last_hour == 48
    physical = dict(cursor.execution.tracks)['shared'].physical.state
    assert physical.event_count == 1 and physical.cumulative_call_energy == .75
    assert physical.interevent_rest_hours == 23
    if alternative['id'] == 'bounded_recovery':
        assert ledger(cursor).debt == 0
        assert all(c.missed_at_deadline == 0 for c in ledger(cursor).cohorts)
    else:
        assert ledger(cursor).debt == Q('3/4')
        assert all(status == 'deadline_missed' for _,status in assess_debt_cohorts(ledger(cursor)))


def test_missing_action_leaves_due_hour_unobserved_and_blocks_suffix():
    origin = rejected_prefix()
    cursor = advance_actual_action(ActualActionCursor(origin),observation(26),None)
    assert cursor.stopped and cursor.execution == origin.execution
    assert ledger(cursor).last_hour == 25 and ledger(cursor).cohorts[0].missed_at_deadline is None
    assert cursor.records[-1].error == 'missing_actual_action'
    with pytest.raises(ValueError,match='cannot consume'):
        advance_actual_action(cursor,observation(27),DeclaredActualAction(0.,1.,()))


@pytest.mark.parametrize('action',[
    DeclaredActualAction(.625,1.625,((23,Q('1/4')),(24,Q('1/4')))),
    DeclaredActualAction(.3125,1.,((23,Q('1/4')),)),
    DeclaredActualAction(.3125,1.3125,()),
    DeclaredActualAction(.3125,1.3125,((99,Q('1/4')),)),
])
def test_invalid_recovery_power_or_allocation_cannot_commit(action):
    origin = rejected_prefix()
    cursor = advance_actual_action(ActualActionCursor(origin),observation(26),action)
    assert cursor.stopped and cursor.execution == origin.execution
    assert cursor.records[-1].step is None and cursor.records[-1].action == action


def test_original_rejected_observation_cannot_be_replaced_or_skipped():
    origin = rejected_prefix()
    for obs in [observation(27), replace(observation(26),limits=replace(observation(26).limits,
                business_recovery_headroom=1.))]:
        with pytest.raises(ValueError,match='exact rejected observation'):
            advance_actual_action(ActualActionCursor(origin),obs,DeclaredActualAction(0.,1.,()))


@pytest.mark.parametrize('field,value', [('split','training'),('power_source_hour',29)])
def test_suffix_identity_error_is_unassessed(field,value):
    cursor = advance_actual_action(ActualActionCursor(rejected_prefix()),observation(26),DeclaredActualAction(0.,1.,()))
    obs = observation(27)
    bad = replace(obs,hour=replace(obs.hour,**{field:value}))
    after = advance_actual_action(cursor,bad,DeclaredActualAction(0.,1.,()))
    assert after.stopped and after.execution == cursor.execution


def test_full_new_calls_accrue_debt_and_active_recovery_is_rejected():
    cursor = ActualActionCursor(rejected_prefix())
    for t in (26,27):
        cursor = advance_actual_action(cursor,observation(t),DeclaredActualAction(0.,1.,()))
    obs = observation(28,grid=.125,cfe=.125)
    after = advance_actual_action(cursor,obs,DeclaredActualAction(0.,.75,()))
    assert not after.stopped and ledger(after).debt == 1
    assert dict(after.execution.tracks)['shared'].physical.state.event_count == 2
    bad = advance_actual_action(cursor,obs,DeclaredActualAction(.3125,1.0625,((23,Q('1/4')),)))
    assert bad.stopped and bad.execution == cursor.execution
    clipped = advance_actual_action(cursor,obs,DeclaredActualAction(0.,.875,()))
    assert clipped.stopped


def test_late_recovery_does_not_erase_miss_and_unknown_stays_unknown():
    for unknown in (False,True):
        cursor = ActualActionCursor(rejected_prefix(unknown=unknown))
        cursor = advance_actual_action(cursor,observation(26),DeclaredActualAction(0.,1.,()))
        cursor = advance_actual_action(cursor,observation(27),DeclaredActualAction(.3125,1.3125,((23,Q('1/4')),)))
        first = ledger(cursor).cohorts[0]
        assert first.remaining == 0
        if unknown:
            assert first.due_hour is None and first.missed_at_deadline is None
        else:
            assert first.missed_at_deadline == Q('1/4')


def test_original_halted_policy_cannot_resume_and_record_cannot_be_relabelled():
    origin = rejected_prefix()
    cursor = advance_actual_action(ActualActionCursor(origin),observation(26),DeclaredActualAction(0.,1.,()))
    with pytest.raises(ValueError,match='halted policy'):
        advance_causal_policy(origin,observation(27))
    with pytest.raises(ValueError,match='match replay'):
        replace(cursor.records[0],status='observed_actual')
    with pytest.raises(ValueError,match='assumed actual'):
        DeclaredActualAction(0.,1.,(),evidence_class='observed')


def test_input_rejection_cannot_be_used_as_service_continuation_origin():
    origin = initialize_causal_policy(B6, policy=FixedPolicy(), anchor=anchor(), envelope=F['envelope'],
        accounting_period_id='synthetic-period', zero_carry_in_assumption=True)
    obs = observation(1)
    bad = replace(obs,hour=replace(obs.hour,split='training'))
    rejected = advance_causal_policy(origin,bad)
    with pytest.raises(ValueError,match='separate diagnosis'):
        ActualActionCursor(rejected)


@pytest.mark.parametrize('arm,g,c', [(NETWORK,.6,0.),(CFE,0.,.6),(JOINT,.3,.3)])
def test_other_arms_cannot_repair_full_call_capacity_by_declaring_an_action(arm,g,c):
    origin = initialize_causal_policy(arm,policy=FixedPolicy(),anchor=anchor(),envelope=F['envelope'],
        accounting_period_id='synthetic-period',zero_carry_in_assumption=True)
    obs = observation(1,grid=g,cfe=c)
    rejected = advance_causal_policy(origin,obs)
    assert rejected.records[-1].stage == 'physical_execution'
    actual = advance_actual_action(ActualActionCursor(rejected),obs,DeclaredActualAction(0.,.4,()))
    assert actual.stopped and actual.execution == rejected.execution
    assert ledger(actual).last_hour == 0 and ledger(actual).debt == 0


def test_first_missing_observation_cannot_be_skipped_and_chain_cannot_be_spliced():
    origin = rejected_prefix()
    cursor = ActualActionCursor(origin)
    with pytest.raises(ValueError,match='exact rejected observation'):
        advance_actual_action(cursor,observation(27),None)
    a = advance_actual_action(cursor,observation(26),DeclaredActualAction(0.,1.,()))
    b = advance_actual_action(cursor,observation(26),DeclaredActualAction(.3125,1.3125,((23,Q('1/4')),)))
    a2 = advance_actual_action(a,observation(27),DeclaredActualAction(0.,1.,()))
    with pytest.raises(ValueError,match='state chain'):
        ActualActionCursor(origin,(b.records[0],a2.records[1]))


@pytest.mark.parametrize('field,value', [
    ('power_source_hour',99),('split','training'),('workload_provenance_sha256','4'*64),
    ('arm_id',NETWORK),
])
def test_missing_action_does_not_mask_invalid_observation(field,value):
    cursor = advance_actual_action(ActualActionCursor(rejected_prefix()),observation(26),DeclaredActualAction(0.,1.,()))
    obs = observation(27)
    invalid = replace(obs,hour=replace(obs.hour,**{field:value}))
    after = advance_actual_action(cursor,invalid,None)
    assert after.stopped and after.execution == cursor.execution
    assert after.records[-1].status == 'unassessed'
    assert after.records[-1].error != 'missing_actual_action'
    with pytest.raises(ValueError,match='cannot consume'):
        advance_actual_action(after,observation(28),None)
