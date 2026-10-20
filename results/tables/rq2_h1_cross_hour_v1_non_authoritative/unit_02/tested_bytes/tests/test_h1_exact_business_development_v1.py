from dataclasses import replace
from fractions import Fraction as Q
from copy import copy,deepcopy
import json
import math
import pickle

import pytest

from experiments import h1_exact_business_development_v1 as m
from tests.test_rq2_bidirectional_policy_v1 import init as legacy_init


def origin(arm=m.arms.JOINT,*,labels=0,mechanism=None,**changes):
    old=legacy_init(arm,committed_capacity=.5,minimum_event_power=1e-6,
                    curtailment_ramp_per_hour=1.,maximum_recovery_power=1.,**changes)
    track=old.initial.tracks[0][1]
    anchor=replace(track.physical.anchor,power_source_hour=0,workload_source_hour=0,
        split='training' if labels==0 else 'holdout',power_outage_seed=7+labels,
        power_trajectory_id=f'power-{labels}',workload_trace_id=f'workload-{labels}',
        power_provenance_sha256=str(labels+1)*64,workload_provenance_sha256=str(labels+2)*64,
        workload_normalization_sha256=str(labels+3)*64)
    envelope=dict(track.physical.envelope,recovery_efficiency=.85,normalized_debt_limit=1.,
                  normalized_energy_budget=3.,maximum_event_count=14,maximum_event_duration_hours=4.)
    mechanism=mechanism or m.Mechanism(Q(1,2),Q(1,2),Q(1))
    return m.initialize_development(old.spec,mechanism=mechanism,anchor=anchor,envelope=envelope,
        accounting_period_id=f'audit-period-{labels}')


def hour(carry,t,*,w=Q(1,2),source=Q(1,2),g=Q(0)):
    return m.current(relative_hour=t,mechanism=carry.mechanism,workload=w,
        source_cfe_at_alpha_one=source,grid_request_mw=g*250)


def advance(carry,item):
    return m.prepare_development(carry,item,expected_current_identity=item.identity)


@pytest.mark.parametrize('arm',[m.arms.NETWORK,m.arms.CFE,m.arms.JOINT,m.arms.B6])
def test_exact_current_agrees_with_original_body_and_preserves_roles(arm):
    before=origin(arm);item=hour(before,0,g=Q(1,20),source=Q(3,5))
    result=advance(before,item)
    observation=m._observation(before.cursor.initial.tracks[0][1].physical.anchor,item)
    assert result.replay_cursor==m.business.advance_capacity_policy(before.cursor,observation)
    assert observation.observation.hour.grid_request==Q(1,20)
    assert observation.observation.hour.cfe_request==Q(1,10)
    assert observation.observation.due_hour==25
    action=result.replay_cursor.records[-1].response.action
    assert action.grid_served==(0 if arm==m.arms.CFE else Q(1,20))
    assert action.cfe_served==(0 if arm==m.arms.NETWORK else Q(1,10))
    assert result.actual_power_mw==(Q(1,2)-action.grid_served-action.cfe_served)*250
    assert result.next_candidate.cursor.execution.tracks[0][1].ledger.debt==action.grid_served+action.cfe_served
    assert before.cursor.records==()
    assert not result.source_input_binding_verified and not result.paired_commit_verified and not result.formal_result


def test_one_over_21_surplus_recovery_never_cast_to_float():
    before=origin();first=advance(before,hour(before,0,g=Q(1,20))).next_candidate
    item=hour(first,1,source=Q(19,42))
    assert item.allocation.compatible_surplus==Q(1,21)
    observation=m._observation(before.cursor.initial.tracks[0][1].physical.anchor,item)
    assert type(observation.observation.limits.cfe_compatible_surplus) is Q
    result=advance(first,item);action=result.replay_cursor.records[-1].response.action
    expected=Q((Q(1,21)*10**12).__floor__(),10**12)
    assert action.recovery==expected and expected<=Q(1,21)<expected+Q(1,10**12)
    assert result.next_candidate.cursor.execution.tracks[0][1].ledger.debt==Q(1,20)-Q(85,100)*expected
    assert result.actual_power_mw==(Q(1,2)+expected)*250


def test_audit_labels_change_but_whole_scientific_history_does_not():
    a,b=origin(),origin(labels=1)
    assert a.identity==b.identity and a.audit_identity!=b.audit_identity
    for t in range(4):
        ia=hour(a,t,g=Q(1,20) if t==0 else Q(0),source=Q(19,42) if t else Q(1,2))
        ib=hour(b,t,g=Q(1,20) if t==0 else Q(0),source=Q(19,42) if t else Q(1,2))
        ra,rb=advance(a,ia),advance(b,ib)
        assert ra.actual_power_mw==rb.actual_power_mw
        a,b=ra.next_candidate,rb.next_candidate
        assert a.identity==b.identity and a.audit_identity!=b.audit_identity
    payload=a.scientific_payload
    for forbidden in (b'power_provenance',b'outage_seed',b'trajectory',b'normalization_sha',b'holdout',b'audit-period'):
        assert forbidden not in payload


@pytest.mark.parametrize('value',[Q(1,21),Q(1,3),Q(1,10**30)+Q(1,10)])
def test_strict_scalar_loss_is_unresolved(value):
    with pytest.raises(ValueError,match='no lossless'):m.lossless_builtin(value)


@pytest.mark.parametrize('value',[Q(0),Q(1),Q(1,8),Q('0.123456789012')])
def test_strict_scalar_lossless_decimal_projection(value):
    assert Q(str(m.lossless_builtin(value)))==value


def test_unrepresentable_available_flexibility_not_silently_rounded():
    c=origin(mechanism=m.Mechanism(Q(1,2),Q(1,21),Q(1)))
    with pytest.raises(ValueError,match='no lossless'):hour(c,0)


@pytest.mark.parametrize('g',[Q(1,1000000),Q(1,1000000)-Q(1,10**30),Q.from_float(1e-6),
                             Q.from_float(math.nextafter(1e-6,0.))])
def test_reference_requests_at_or_below_exact_threshold_rejected(g):
    with pytest.raises(ValueError,match='below business resolution'):hour(origin(),0,g=g)


@pytest.mark.parametrize('g',[Q.from_float(math.nextafter(1e-6,math.inf)),Q(1000001,10**12)])
def test_reference_requests_above_exact_threshold_retain_exact_amount(g):
    c=origin();item=hour(c,0,g=g);result=advance(c,item)
    assert result.replay_cursor.records[-1].response.action.grid_served==g


def test_above_threshold_that_collapses_with_legacy_float_zero_is_unresolved():
    c=origin();near=Q(1,1000000)+Q(1,10**30)
    assert near>m.cfe.activity_threshold()
    with pytest.raises(ValueError,match='binary threshold'):
        hour(c,0,g=near)
    with pytest.raises(ValueError,match='binary threshold'):
        hour(c,0,source=Q(1,2)+near)


def test_raw_effective_component_mismatch_rejected_even_when_cfe_is_zero():
    c=origin()
    # w=.5, alpha=.5 -> raw c = source-.5. A subthreshold raw c cannot be hidden by a live g.
    with pytest.raises(ValueError,match='combined activity mismatch'):
        hour(c,0,g=Q(1,20),source=Q(1,2)+Q(1,2000000))
    item=hour(c,0,source=Q(1,2)+Q(1,1000000))
    assert item.allocation.effective_request==0
    assert advance(c,item).replay_cursor.records[-1].response.action.cfe_served==0


def test_business_rejection_has_no_next_candidate_or_actual_power():
    c=origin();item=hour(c,0,g=Q(3,10))
    result=advance(c,item)
    assert result.status=='business_unresolved' and result.next_candidate is None and result.actual_power_mw is None
    assert result.replay_cursor.execution==c.cursor.execution and c.history==()


def test_future_phase_changes_neither_policy_nor_enrollment_debt():
    c=origin();snap=None
    for t in range(192):
        item=hour(c,t,g=Q(1,100) if t in (167,168) else Q(0))
        assert item.phase==('enrollment' if t<168 else 'followup')
        result=advance(c,item)
        assert result.next_candidate is not None
        c=result.next_candidate
        if t==168:snap=c
    ledger=c.cursor.execution.tracks[0][1].ledger
    assert [x.created_hour for x in ledger.cohorts]==[168,169]
    assert [x.due_hour for x in ledger.cohorts]==[192,193]
    assert ledger.cohorts[0].missed_at_deadline==Q(1,100)
    assert ledger.cohorts[1].missed_at_deadline is None
    assert ledger.debt==Q(1,50) and snap.cursor.execution.tracks[0][1].ledger.debt==Q(1,50)
    with pytest.raises(ValueError,match='0..191'):hour(c,192)


def test_mechanism_progress_pin_and_mutated_history_rejected():
    c=origin();item=hour(c,0)
    with pytest.raises(ValueError,match='key'):m.prepare_development(c,item,expected_current_identity='0'*64)
    with pytest.raises(ValueError,match='progress'):advance(c,hour(c,1))
    with pytest.raises(ValueError,match='mechanism'):
        advance(c,replace(item,mechanism=replace(c.mechanism,recovery_headroom_fraction=Q(1,2))))
    nxt=advance(c,item).next_candidate
    fake=m._owned(m.BusinessCarry,**dict(vars(nxt),history=(replace(item,grid_request_mw=Q(1)),)))
    with pytest.raises(ValueError,match='history'):advance(fake,hour(fake,1))
    for copier in (copy,deepcopy,pickle.dumps):
        with pytest.raises(TypeError):copier(c)
