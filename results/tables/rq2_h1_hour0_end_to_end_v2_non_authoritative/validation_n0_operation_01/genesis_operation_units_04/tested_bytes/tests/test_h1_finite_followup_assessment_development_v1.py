from dataclasses import replace
from fractions import Fraction as Q
from types import SimpleNamespace

import pytest

from experiments import h1_finite_followup_assessment_development_v1 as m
from tests import test_h1_exact_business_development_v1 as old
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture(scope='module')
def histories():
    result={}
    for label in ('no_requests','pending','recover_primary','late_recovery'):
        c=old.origin(mechanism=m.business.Mechanism(Q(1,2),Q(1,2),Q(1,5)))
        values={0:c}
        end=168 if label=='no_requests' else 170 if label=='recover_primary' else 192
        for hour in range(1,end+1):
            g=Q(0);source=Q(1,2)
            if label in ('pending','recover_primary') and hour in (168,169):g=Q(17,200)
            if label=='late_recovery' and hour in (145,168):g=Q(17,200)
            if label in ('recover_primary','late_recovery') and hour==170:source=Q(0)
            item=old.hour(c,hour-1,g=g,source=source)
            candidate=old.advance(c,item)
            assert candidate.next_candidate is not None,(label,hour,candidate.status)
            c=candidate.next_candidate
            if hour in (144,145,167,168,169,170,191,192):values[hour]=c
        result[label]=values
    return result


def assess(carry):return m.assess_development(carry,expected_carry_identity=carry.identity)


def test_enrollment_needs_remaining_requests_even_with_no_debt(histories):
    for h in (0,144,167):
        a=assess(histories['no_requests'][h])
        assert a.retained_total_debt==0 and not a.pending_primary_births
        assert a.needs_next_hour and a.next_relative_hour==h and a.next_phase=='enrollment'
        assert a.grid_request_status==a.cfe_request_status==a.primary_recovery_status=='U'
    a=assess(histories['no_requests'][168])
    assert not a.needs_next_hour and a.next_relative_hour is None and a.next_phase is None
    assert a.grid_request_status==a.cfe_request_status==a.primary_recovery_status=='S'
    assert a.stop_reason=='primary_resolved' and a.complete_contract_status is None


def test_followup_new_birth_retained_but_does_not_extend_primary_due(histories):
    a=assess(histories['pending'][169])
    assert a.pending_primary_births==(168,) and a.last_primary_due==192
    assert [(c.birth_hour,c.due_hour) for c in a.primary_cohorts]==[(168,192)]
    assert [(c.birth_hour,c.due_hour) for c in a.followup_cohorts]==[(169,193)]
    assert a.needs_next_hour and a.next_phase=='followup' and a.next_relative_hour==169
    assert a.grid_request_status==a.cfe_request_status=='S' and a.primary_recovery_status=='U'
    assert a.complete_contract_status is None and not a.all_component_observations_known


def test_due_endpoint_is_observed_then_stop_with_nonzero_followup_debt(histories):
    before=assess(histories['pending'][191]);after=assess(histories['pending'][192])
    assert before.needs_next_hour and before.next_relative_hour==191
    assert after.primary_cohorts[0].missed_at_deadline==Q(17,200)
    assert after.primary_cohorts[0].status=='failure_at_due'
    assert after.followup_cohorts[0].missed_at_deadline is None
    assert after.followup_cohorts[0].status=='pending_before_due'
    assert after.retained_total_debt==Q(17,100) and not after.needs_next_hour
    assert after.grid_request_status==after.cfe_request_status=='S'
    assert after.primary_recovery_status=='F' and after.any_component_failure_observed


def test_stop_early_after_primary_recovery_without_clearing_followup_debt(histories):
    a=assess(histories['recover_primary'][170])
    assert a.primary_cohorts[0].remaining==0 and a.primary_cohorts[0].status=='success_before_due'
    assert a.followup_cohorts[0].remaining==Q(17,200)
    assert a.retained_total_debt==Q(17,200) and not a.needs_next_hour
    assert a.primary_recovery_status=='S' and a.all_component_observations_known


def test_late_recovery_never_erases_recorded_deadline_failure(histories):
    a=assess(histories['late_recovery'][170]);fact=a.primary_cohorts[0]
    assert fact.remaining==0 and fact.missed_at_deadline==Q(17,200)
    assert fact.status=='failure_at_due' and a.primary_recovery_status=='F'
    assert a.grid_request_status==a.cfe_request_status=='S'
    assert a.needs_next_hour and a.retained_total_debt==Q(17,200)
    assert a.pending_primary_births==(168,)
    assert not a.all_component_observations_known and a.any_component_failure_observed
    end=assess(histories['late_recovery'][192])
    assert not end.needs_next_hour and end.primary_recovery_status=='F'
    assert end.all_component_observations_known and end.any_component_failure_observed


@pytest.mark.parametrize('arm,grid,cfe',[
    (m.business.arms.NETWORK,'U',None),(m.business.arms.CFE,None,'U'),
    (m.business.arms.JOINT,'U','U'),(m.business.arms.B6,'U','U')])
def test_request_applicability_preserves_none(arm,grid,cfe):
    a=assess(old.origin(arm))
    assert (a.grid_request_status,a.cfe_request_status)==(grid,cfe)
    assert a.needs_next_hour and a.complete_contract_status is None


def test_zero_deadline_snapshot_is_known_success_not_missing():
    c=SimpleNamespace(created_hour=1,due_hour=25,incurred=Q(1),remaining=Q(0),missed_at_deadline=Q(0))
    assert m._cohort(c,25).status=='success_by_due'
    c.missed_at_deadline=None
    with pytest.raises(ValueError,match='snapshot missing'):m._cohort(c,25)


@pytest.mark.parametrize('due',[None,24,26,True])
def test_due_contract_drift_cannot_be_repaired_by_more_followup(due):
    c=SimpleNamespace(created_hour=1,due_hour=due,incurred=Q(1),remaining=Q(1),missed_at_deadline=None)
    with pytest.raises(ValueError,match='birth/due'):m._cohort(c,1)


def test_bad_carry_pin_and_forged_history_are_rejected(histories):
    c=histories['pending'][168]
    with pytest.raises(ValueError,match='identity'):m.assess_development(c,expected_carry_identity='0'*64)
    forged=m.business._owned(m.business.BusinessCarry,**(vars(c)|dict(history=c.history[:-1])))
    with pytest.raises(ValueError,match='history'):assess(forged)


def test_roster_freezes_completed_lanes_and_advances_only_pending_primary(histories):
    done=histories['no_requests'][168];pending=histories['pending'][169]
    a=m.assess_roster_development(completed_outer_hours=169,
        lanes=(('done','completed',done),('pending','active',pending)))
    assert a.needs_next_hour and a.next_relative_hour==169
    assert not a.lanes[0].needs_next_hour and a.lanes[1].needs_next_hour
    assert not a.owner_replay_authenticated and not a.producer_admitted
    with pytest.raises(ValueError,match='still has unresolved'):
        m.assess_roster_development(completed_outer_hours=169,lanes=(('pending','completed',pending),))
    with pytest.raises(ValueError,match='outer clock'):
        m.assess_roster_development(completed_outer_hours=169,lanes=(('done','active',done),))


def test_halted_lane_does_not_authorize_more_normal_or_reference(histories):
    c=histories['pending'][168]
    a=m.assess_roster_development(completed_outer_hours=169,lanes=(('failed','halted_unresolved',c),))
    assert not a.needs_next_hour and a.next_relative_hour is None
    assert a.lanes[0].business.primary_recovery_status=='U'
    assert a.lanes[0].disposition_reason=='halted_unresolved'


def test_assessment_reads_no_source_rows(histories,monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import source_window
    def denied(*args,**kwargs):raise AssertionError('assessment read a future/source row')
    monkeypatch.setattr(source_window,'load_source_window',denied)
    a=assess(histories['pending'][168])
    assert a.needs_next_hour
    assert not a.source_availability_checked and not a.followup_execution_admitted and not a.formal_result


def test_contract_or_implementation_drift_rejected(histories,monkeypatch):
    c=histories['pending'][168]
    monkeypatch.setattr(m,'WINDOW',dict(m.WINDOW,enrollment_hours=167))
    with pytest.raises(ValueError,match='declaration differs'):assess(c)
