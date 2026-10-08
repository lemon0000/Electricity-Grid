from dataclasses import replace
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor,ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.causal_policy import FixedPolicy,HourlyLimits,CurrentObservation
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK,CFE,JOINT,B6
from src.rq2_joint_deliverability_boundary_v1.recovery_controller import (
    CompositePolicy,CompositeCursor,initialize_composite_policy,advance_composite_policy,summarize_composite_policy,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT/'configs/rq2_continuous_recovery_controller_v1.DRAFT.yaml').read_text(encoding='utf-8'))
F = yaml.safe_load((ROOT/CONFIG['fixture']['source_config']).read_text(encoding='utf-8'))['fixture']


def anchor():
    return BoundaryAnchor(JOINT,'shared','holdout',0,100,'synthetic-power','synthetic-work','1'*64,0,'2'*64,'3'*64)


def init(arm=B6,precision=12):
    spec = CompositePolicy.from_config(CONFIG,arm)
    spec = replace(spec,recovery=FixedPolicy(spec.recovery.rule,precision))
    return initialize_composite_policy(spec,anchor=anchor(),envelope=F['envelope'],
        accounting_period_id='synthetic-period',zero_carry_in_assumption=True)


def obs(t,g=None,c=None,due='default',**changes):
    active = t in F['call_hours']
    hour = ContinuationHour(**dict(anchor().__dict__,power_source_hour=t,workload_source_hour=100+t),
        grid_request=(F['grid_request'] if active else 0.) if g is None else g,
        cfe_request=(F['cfe_request'] if active else 0.) if c is None else c,workload_occupancy=1.)
    limits = HourlyLimits(F['call_limit'],F['business_recovery_headroom'],F['cfe_compatible_surplus'],F['maximum_recovery_power'])
    return CurrentObservation(hour,replace(limits,**changes),
        (t+F['deadline_offset_hours'] if active else None) if due=='default' else due)


def through(t,arm=B6,precision=12):
    cursor = init(arm,precision)
    for h in range(1,t+1):
        cursor = advance_composite_policy(cursor,obs(h))
    return cursor


@pytest.mark.parametrize('arm',[NETWORK,CFE,JOINT,B6])
def test_48h_composite_has_unique_exposure_and_preserves_original_rejection(arm):
    cursor = through(48,arm)
    result = summarize_composite_policy(cursor)
    assert result['validated_unique_hours']==result['submitted_unique_hours']==48
    assert result['remaining_debt']==(('shared',Q(0)),)
    assert result['formal_result'] is False and result['risk_probability'] is None
    if arm==B6:
        assert result['original_rejection_hour']==26
        assert result['primary_accepted_hours']==25 and result['recovery_validated_hours']==23
        assert cursor.primary.halted and len(cursor.primary.records)==26
        assert cursor.primary.records[-1].planned_step is not None
        assert cursor.recovery_records[0].after.records[-1].action.recovery==.3125
        assert [r.after.execution.tracks[0][1].ledger.debt for r in cursor.recovery_records[:3]]==[Q('1/2'),Q('1/4'),Q(0)]
    else:
        assert not cursor.recovery_records and result['original_rejection_hour'] is None


def test_future_suffix_perturbations_preserve_past_decisions():
    prefix = through(26)
    a = advance_composite_policy(prefix,obs(27))
    b = advance_composite_policy(prefix,obs(27,business_recovery_headroom=0.))
    assert a.recovery_records[:1]==b.recovery_records[:1]==prefix.recovery_records
    assert a.recovery_records[-1].after.records[-1].action.recovery==.3125
    assert b.recovery_records[-1].after.records[-1].action.recovery==0.
    whole=through(48)
    chunked=init()
    for block in (range(1,24),range(24,27),range(27,49)):
        for t in block:
            chunked=advance_composite_policy(chunked,obs(t))
    assert chunked==whole
    with pytest.raises(ValueError,match='one current observation'):
        advance_composite_policy(prefix,[obs(27),obs(28)])


def test_current_debt_not_archived_planning_drives_recovery_and_new_calls():
    cursor=through(27)
    original=cursor.primary
    cursor=advance_composite_policy(cursor,obs(28,g=.125,c=.125,due=31))
    action=cursor.recovery_records[-1].after.records[-1].action
    assert action.recovery==0. and action.actual_service_power==.75
    assert cursor.primary==original
    assert cursor.actual.execution.tracks[0][1].ledger.debt==Q('1/2')


def test_known_deadline_priority_and_unknown_preservation_after_switch():
    cursor=init()
    for t in range(1,27):
        cursor=advance_composite_policy(cursor,obs(t,due=None if t==23 else ('default' if t!=24 else 40)))
    action=cursor.actual.records[-1].action
    assert action.allocations==((25,Q('1/4')),)
    for t in range(27,49):
        cursor=advance_composite_policy(cursor,obs(t))
    ledger=cursor.actual.execution.tracks[0][1].ledger
    assert ledger.debt==0 and ledger.cohorts[0].due_hour is None


def test_late_recovery_preserves_miss_and_fixed_precision_residual():
    cursor=through(26,precision=2)
    assert cursor.actual.records[-1].action.recovery==.31
    assert cursor.actual.execution.tracks[0][1].ledger.cohorts[0].missed_at_deadline==Q('.002')
    for t in range(27,49):
        cursor=advance_composite_policy(cursor,obs(t))
    assert cursor.actual.execution.tracks[0][1].ledger.debt>0
    assert cursor.actual.execution.tracks[0][1].ledger.cohorts[0].missed_at_deadline==Q('.002')


@pytest.mark.parametrize('arm,g,c',[(NETWORK,.6,0.),(CFE,0.,.6),(JOINT,.3,.3)])
def test_full_call_failure_cannot_be_repaired_or_counted_as_validated(arm,g,c):
    cursor=advance_composite_policy(init(arm),obs(1,g=g,c=c))
    result=summarize_composite_policy(cursor)
    assert cursor.stopped and result['submitted_unique_hours']==1 and result['validated_unique_hours']==0
    assert cursor.recovery_records[-1].after.stopped
    with pytest.raises(ValueError,match='cannot consume'):
        advance_composite_policy(cursor,obs(2))


@pytest.mark.parametrize('field,value',[('split','training'),('power_source_hour',99),('workload_provenance_sha256','4'*64)])
def test_invalid_suffix_identity_stops_before_decision(field,value):
    before=through(26)
    row=obs(27)
    cursor=advance_composite_policy(before,replace(row,hour=replace(row.hour,**{field:value})))
    assert cursor.stopped and cursor.recovery_records[-1].stage=='input_validation'
    assert cursor.recovery_records[-1].after is None
    assert cursor.actual.execution==before.actual.execution
    assert summarize_composite_policy(cursor)['validated_unique_hours']==26


def test_input_or_planning_rejection_does_not_activate_recovery():
    row=obs(1)
    cursor=advance_composite_policy(init(),replace(row,hour=replace(row.hour,split='training')))
    assert cursor.stopped and not cursor.recovery_records
    cursor=advance_composite_policy(through(25),obs(26,g=.125,c=.125))
    assert cursor.stopped and cursor.primary.records[-1].stage=='separate_planning'
    assert not cursor.recovery_records


def test_ex_ante_identity_and_replay_record_cannot_be_relabelled():
    cursor=through(26)
    changed=replace(cursor.spec,recovery=FixedPolicy(recovery_decimal_places=2))
    assert changed.policy_id!=cursor.policy_id
    with pytest.raises(ValueError,match='identity changed'):
        replace(cursor,spec=changed)
    with pytest.raises(ValueError,match='deterministic replay'):
        replace(cursor.recovery_records[0],stage='invented')
    assert init(NETWORK).policy_id!=init(B6).policy_id


def test_recovery_decision_failure_preserves_error_and_last_actual_state():
    before=through(26)
    cursor=advance_composite_policy(before,obs(27,g=.125,c=6e-7))
    record=cursor.recovery_records[-1]
    assert cursor.stopped and record.stage=='recovery_decision' and record.after is None
    assert 'effective obligations differ' in record.error
    assert cursor.actual==before.actual
    result=summarize_composite_policy(cursor)
    assert result['submitted_unique_hours']==27 and result['validated_unique_hours']==26


@pytest.mark.parametrize('limit',['business_recovery_headroom','cfe_compatible_surplus','maximum_recovery_power'])
def test_recovery_obeys_each_current_shared_limit(limit):
    cursor=advance_composite_policy(through(26),obs(27,**{limit:0.}))
    assert not cursor.stopped and cursor.actual.records[-1].action.recovery==0.
    assert cursor.actual.execution.tracks[0][1].ledger.cohorts[1].missed_at_deadline==Q('1/4')


@pytest.mark.parametrize('arm,g,c',[(B6,None,None),(JOINT,.3,.3)])
def test_triggered_primary_cannot_be_reconstructed_without_recovery(arm,g,c):
    cursor=through(26) if arm==B6 else advance_composite_policy(init(arm),obs(1,g=g,c=c))
    with pytest.raises(ValueError,match='same-hour recovery decision'):
        replace(cursor,recovery_records=())
    with pytest.raises(ValueError,match='same-hour recovery decision'):
        CompositeCursor(cursor.spec,cursor.policy_id,cursor.primary)


@pytest.mark.parametrize('key,value',[
    ('trigger_stages',['input_validation']),('transition','resume_old_planning'),
    ('evidence_class','observed'),('failure','continue'),('formal_result',True),
    ('unexpected_rule','silent_override'),
])
def test_config_cannot_silently_drift_from_implemented_policy(key,value):
    with pytest.raises(ValueError,match='draft policy semantics'):
        CompositePolicy.from_config(dict(CONFIG,**{key:value}),B6)
