from dataclasses import replace
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor, ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.multiday import ServiceAction
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import assess_debt_cohorts
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import (
    NETWORK, CFE, JOINT, B6, CohortAction, initialize_arm_replay,
    advance_arm_replay, execute_b6_planned_step,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT/'configs/rq2_continuous_four_arm_replay_v1.DRAFT.yaml').read_text(encoding='utf-8'))['fixture']


def anchor():
    return BoundaryAnchor(JOINT, 'shared', 'training', 0, 100, 'synthetic-power',
                          'synthetic-workload', '1'*64, 0, '2'*64, '3'*64)


def hour(t, g=0., c=0.):
    return ContinuationHour(**dict(anchor().__dict__, power_source_hour=t, workload_source_hour=100+t),
                            grid_request=g, cfe_request=c, workload_occupancy=1.)


def init(arm=JOINT, mode='physical_execution', **kwargs):
    args = dict(mode=mode, anchor=anchor(), envelope=CFG['envelope'],
                accounting_period_id='synthetic-48h', zero_carry_in_assumption=True)
    args.update(kwargs)
    return initialize_arm_replay(arm, **args)


def action(q=0., r=0., allocations=(), **kwargs):
    physical = ServiceAction(r, 1.-q+r, .5, .5, .5, .5)
    return CohortAction(replace(physical, **kwargs), allocations)


@pytest.mark.parametrize('arm,mode', [(NETWORK,'physical_execution'), (CFE,'physical_execution'),
    (JOINT,'physical_execution'), (B6,'physical_execution'), (B6,'separate_planning')])
def test_48h_four_arm_physics_and_cohorts_stay_bound(arm, mode):
    cursor = init(arm, mode)
    history = []
    for t in range(1,49):
        call = t in CFG['call_hours']
        recover = t in CFG['recovery_hours']
        source = hour(t, CFG['grid_request'] if call else 0., CFG['cfe_request'] if call else 0.)
        actions = {}
        for name, _ in cursor.tracks:
            amount = .125 if mode == 'separate_planning' or arm in {NETWORK,CFE} else .25
            allocations = ((t-3,Q(str(amount))),) if recover else ()
            actions[name] = action(amount if call else 0., amount/.8 if recover else 0., allocations)
        cursor = advance_arm_replay(cursor, hour=source, due_hour=t+3 if call else None, actions=actions).cursor
        history.append(cursor)
        for _, track in cursor.tracks:
            assert float(track.ledger.debt) == track.physical.state.recovery_debt
    for _, track in history[23].tracks:
        assert track.physical.state.event_count == 1
        assert track.physical.state.active_duration_hours == 2
        assert track.ledger.debt > 0
    for _, track in cursor.tracks:
        assert track.ledger.debt == 0
        assert all(s == 'recovered_by_deadline' for _,s in assess_debt_cohorts(track.ledger))


def test_b6_plan_replays_shared_with_two_ledgers_merging_into_one():
    plan, shared = init(B6,'separate_planning'), init(B6)
    for t in range(1,49):
        call, recover = t in (23,24,25), t in (26,27,28)
        a = action(.125 if call else 0., .15625 if recover else 0.,
                   ((t-3,Q('0.125')),) if recover else ())
        planned = advance_arm_replay(plan, hour=hour(t,.125 if call else 0.,.125 if call else 0.),
                                    due_hour=t+3 if call else None, actions={'grid':a,'cfe':a})
        p = action(.25 if call else 0., .3125 if recover else 0.).physical
        shared = execute_b6_planned_step(shared, planned=planned, shared_limits=p).cursor
        plan = planned.cursor
        assert dict(shared.tracks)['shared'].ledger.debt == sum((v.ledger.debt for _,v in plan.tracks),Q(0))
    assert dict(shared.tracks)['shared'].physical.state.cumulative_call_energy == .75


def test_b6_individual_capacity_success_does_not_imply_shared_success():
    plan = advance_arm_replay(init(B6,'separate_planning'), hour=hour(1,.3,.3), due_hour=4,
                              actions={'grid':action(.3), 'cfe':action(.3)})
    shared = init(B6)
    with pytest.raises(ValueError, match='call limit'):
        execute_b6_planned_step(shared, planned=plan, shared_limits=action(.6).physical)
    assert dict(shared.tracks)['shared'].ledger.debt == 0


@pytest.mark.parametrize('arm,should_fail', [(NETWORK,False),(CFE,True),(JOINT,True)])
def test_cfe_surplus_applies_only_to_cfe_service_arms(arm, should_fail):
    cursor=init(arm)
    q=.25 if arm==JOINT else .125
    cursor=advance_arm_replay(cursor,hour=hour(1,.125,.125),due_hour=3,actions={'shared':action(q)}).cursor
    a=action(0.,q/.8,((1,Q(str(q))),),cfe_compatible_surplus=0.)
    if should_fail:
        with pytest.raises(ValueError,match='headroom'):
            advance_arm_replay(cursor,hour=hour(2),due_hour=None,actions={'shared':a})
    else:
        result=advance_arm_replay(cursor,hour=hour(2),due_hour=None,actions={'shared':a})
        assert dict(result.cursor.tracks)['shared'].ledger.debt==0


@pytest.mark.parametrize('fault,error', [('missing','allocations do not equal'),
    ('extra','allocations do not equal'), ('headroom','headroom'), ('power','power balance')])
def test_physical_recovery_and_allocation_must_match(fault,error):
    cursor=advance_arm_replay(init(),hour=hour(1,.125,.125),due_hour=3,actions={'shared':action(.25)}).cursor
    a=action(0.,.3125,((1,Q('.25')),))
    if fault=='missing': a=replace(a,allocations=())
    elif fault=='extra': a=replace(a,allocations=((1,Q('.5')),))
    elif fault=='headroom': a=replace(a,physical=replace(a.physical,business_recovery_headroom=0.))
    else: a=replace(a,physical=replace(a.physical,actual_service_power=1.))
    with pytest.raises(ValueError,match=error):
        advance_arm_replay(cursor,hour=hour(2),due_hour=None,actions={'shared':a})
    assert dict(cursor.tracks)['shared'].ledger.debt==Q('.25')


def test_late_recovery_keeps_missed_deadline_after_physical_debt_clears():
    cursor=advance_arm_replay(init(),hour=hour(1,.25),due_hour=2,actions={'shared':action(.25)}).cursor
    cursor=advance_arm_replay(cursor,hour=hour(2),due_hour=None,actions={'shared':action()}).cursor
    cursor=advance_arm_replay(cursor,hour=hour(3),due_hour=None,
        actions={'shared':action(0.,.3125,((1,Q('.25')),))}).cursor
    track=dict(cursor.tracks)['shared']
    assert track.physical.state.recovery_debt==0
    assert assess_debt_cohorts(track.ledger)==((1,'deadline_missed'),)


@pytest.mark.parametrize('field,value', [('split','holdout'),('power_source_hour',3),
    ('workload_source_hour',105),('power_outage_seed',1)])
def test_cross_track_state_rejects_source_drift(field,value):
    with pytest.raises(ValueError):
        advance_arm_replay(init(),hour=replace(hour(1),**{field:value}),due_hour=None,
                           actions={'shared':action()})


def test_b6_cannot_swap_contract_or_reoptimize_recovery_in_execution():
    plan=advance_arm_replay(init(B6,'separate_planning'),hour=hour(1,.125,.125),due_hour=3,
        actions={'grid':action(.125),'cfe':action(.125)})
    with pytest.raises(ValueError,match='exactly replay'):
        execute_b6_planned_step(init(B6),planned=plan,shared_limits=action(.25,.1).physical)
    with pytest.raises(ValueError,match='envelope differ'):
        execute_b6_planned_step(init(B6,envelope=dict(CFG['envelope'],normalized_energy_budget=2.)),
                               planned=plan,shared_limits=action(.25).physical)


def test_nonzero_carry_in_not_silently_initialized_as_zero():
    with pytest.raises(ValueError,match='explicit zero'):
        init(zero_carry_in_assumption=False)


def test_b6_separate_recovery_during_other_service_call_fails_shared_execution():
    planned=advance_arm_replay(init(B6,'separate_planning'),hour=hour(1,.125,0.),due_hour=4,
        actions={'grid':action(.125),'cfe':action()})
    shared=execute_b6_planned_step(init(B6),planned=planned,shared_limits=action(.125).physical).cursor
    next_plan=advance_arm_replay(planned.cursor,hour=hour(2,0.,.125),due_hour=4,
        actions={'grid':action(0.,.15625,((1,Q('.125')),)),'cfe':action(.125)})
    with pytest.raises(ValueError,match='active call'):
        execute_b6_planned_step(shared,planned=next_plan,shared_limits=action(.125,.15625).physical)
    assert dict(shared.tracks)['shared'].ledger.debt==Q('.125')


def test_b6_combined_recovery_cannot_exceed_shared_headroom():
    planned=advance_arm_replay(init(B6,'separate_planning'),hour=hour(1,.125,.125),due_hour=3,
        actions={'grid':action(.125),'cfe':action(.125)})
    shared=execute_b6_planned_step(init(B6),planned=planned,shared_limits=action(.25).physical).cursor
    a=action(0.,.15625,((1,Q('.125')),))
    next_plan=advance_arm_replay(planned.cursor,hour=hour(2),due_hour=None,actions={'grid':a,'cfe':a})
    with pytest.raises(ValueError,match='headroom'):
        execute_b6_planned_step(shared,planned=next_plan,
            shared_limits=action(0.,.3125,business_recovery_headroom=.2).physical)


def test_b6_cannot_splice_another_planning_history():
    p1=advance_arm_replay(init(B6,'separate_planning'),hour=hour(1,.125,.125),due_hour=3,
        actions={'grid':action(.125),'cfe':action(.125)})
    shared=execute_b6_planned_step(init(B6),planned=p1,shared_limits=action(.25).physical).cursor
    alternate=advance_arm_replay(init(B6,'separate_planning'),hour=hour(1,.125,.125),due_hour=4,
        actions={'grid':action(.125),'cfe':action(.125)})
    alternate2=advance_arm_replay(alternate.cursor,hour=hour(2),due_hour=None,
        actions={'grid':action(),'cfe':action()})
    with pytest.raises(ValueError,match='plan history'):
        execute_b6_planned_step(shared,planned=alternate2,shared_limits=action().physical)


def test_cohort_ledger_cannot_be_swapped_between_arms():
    joint=init()
    foreign=dict(init(CFE).tracks)['shared'].ledger
    forged=replace(joint,tracks=(('shared',replace(dict(joint.tracks)['shared'],ledger=foreign)),))
    with pytest.raises(ValueError,match='identity mismatch'):
        advance_arm_replay(forged,hour=hour(1),due_hour=None,actions={'shared':action()})


def test_missing_deadline_remains_unknown_after_bound_recovery():
    state=advance_arm_replay(init(),hour=hour(1,.25),due_hour=None,actions={'shared':action(.25)}).cursor
    state=advance_arm_replay(state,hour=hour(2),due_hour=None,
        actions={'shared':action(0.,.3125,((1,Q('.25')),))}).cursor
    assert assess_debt_cohorts(dict(state.tracks)['shared'].ledger)==((1,'deadline_unidentified'),)


def test_decimal_calls_do_not_create_artificial_deadline_shortfall():
    state=advance_arm_replay(init(),hour=hour(1,.1,.2),due_hour=2,
        actions={'shared':action(.3)}).cursor
    assert dict(state.tracks)['shared'].ledger.debt==Q('.3')
    state=advance_arm_replay(state,hour=hour(2),due_hour=None,
        actions={'shared':action(0.,.375,((1,Q('.3')),))}).cursor
    assert dict(state.tracks)['shared'].ledger.debt==0
    assert assess_debt_cohorts(dict(state.tracks)['shared'].ledger)==((1,'recovered_by_deadline'),)


def test_b6_forged_plan_actions_cannot_keep_a_different_success_state():
    p1=advance_arm_replay(init(B6,'separate_planning'),hour=hour(1,.125,.125),due_hour=4,
        actions={'grid':action(.125),'cfe':action(.125)})
    shared=execute_b6_planned_step(init(B6),planned=p1,shared_limits=action(.25).physical).cursor
    full=action(0.,.15625,((1,Q('.125')),))
    p2=advance_arm_replay(p1.cursor,hour=hour(2),due_hour=None,actions={'grid':full,'cfe':full})
    partial=action(0.,.1,((1,Q('.08')),))
    forged=replace(p2,actions=(('grid',partial),('cfe',partial)))
    with pytest.raises(ValueError,match='replayed actions and state'):
        execute_b6_planned_step(shared,planned=forged,shared_limits=action(0.,.2).physical)
    assert dict(shared.tracks)['shared'].ledger.debt==Q('.25')
    duplicate=replace(p2,actions=p2.actions+(p2.actions[0],))
    with pytest.raises(ValueError,match='inventory'):
        execute_b6_planned_step(shared,planned=duplicate,shared_limits=action(0.,.3125).physical)


@pytest.mark.parametrize('names', [(),('grid',),('shared','shared'),('cfe','grid')])
def test_invalid_cursor_inventory_cannot_skip_service_checks(names):
    cursor=init()
    track=dict(cursor.tracks)['shared']
    with pytest.raises(ValueError,match='inventory'):
        replace(cursor,tracks=tuple((name,track) for name in names))


def test_plan_history_cursor_must_be_b6_separate_planning():
    with pytest.raises(ValueError,match='planning history cursor'):
        replace(init(B6),last_plan_cursor=init(JOINT))
