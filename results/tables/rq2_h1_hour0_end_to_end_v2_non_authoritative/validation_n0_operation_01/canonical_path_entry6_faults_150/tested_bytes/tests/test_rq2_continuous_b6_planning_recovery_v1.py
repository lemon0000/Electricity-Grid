from dataclasses import replace
from fractions import Fraction as Q

import pytest
import yaml

from test_rq2_continuous_recovery_controller_v1 import ROOT, F, anchor, obs
from src.rq2_joint_deliverability_boundary_v1.actual_actions import ActualActionCursor
from src.rq2_joint_deliverability_boundary_v1.causal_policy import FixedPolicy
from src.rq2_joint_deliverability_boundary_v1.b6_planning_recovery import (
    B6PlanningRecoveryPolicy, initialize_b6_planning_recovery,
    advance_b6_planning_recovery as advance, summarize_b6_planning_recovery as summarize,
)

CONFIG = yaml.safe_load((ROOT/'configs/rq2_continuous_b6_planning_recovery_v1.DRAFT.yaml').read_text(encoding='utf-8'))


def init():
    return initialize_b6_planning_recovery(B6PlanningRecoveryPolicy.from_config(CONFIG),
        anchor=anchor(), envelope=F['envelope'], accounting_period_id='synthetic-period',
        zero_carry_in_assumption=True)


def row(t):
    if t == 24:
        return obs(t, g=0., c=.125, business_recovery_headroom=0.,
                   cfe_compatible_surplus=0., maximum_recovery_power=0.)
    return obs(t, g=.125 if t in (23,25) else 0., c=0.)


def through(t):
    cursor = init()
    for h in range(1,t+1):
        cursor = advance(cursor,row(h))
    return cursor


def test_analytic_planning_rejection_shared_successor_and_unique_exposure():
    cursor = through(25)
    original = cursor.primary
    assert original.records[-1].stage == 'separate_planning'
    assert original.execution.tracks[0][1].physical.anchor.power_source_hour == 24
    assert cursor.execution.tracks[0][1].ledger.debt == Q('3/8')
    action = cursor.decisions[0].actual_record.action
    assert (action.recovery,action.actual_service_power) == (0.,.875)
    cursor = advance(cursor,row(26))
    action = cursor.decisions[-1].actual_record.action
    assert action.recovery == .3125
    assert action.allocations == ((23,Q('1/8')),(24,Q('1/8')))
    assert cursor.execution.tracks[0][1].ledger.debt == Q('1/8')
    cursor = advance(cursor,row(27))
    assert cursor.decisions[-1].actual_record.action.recovery == .15625
    assert cursor.execution.tracks[0][1].ledger.debt == 0
    for t in range(28,49):
        cursor = advance(cursor,row(t))
    result = summarize(cursor)
    assert cursor.primary == original
    assert result['submitted_unique_hours'] == result['validated_unique_hours'] == 48
    assert result['primary_accepted_hours'] == result['successor_validated_hours'] == 24
    assert result['original_rejection_source_hour'] == 25
    assert result['risk_probability'] is None and result['formal_result'] is False
    with pytest.raises(ValueError,match='separate diagnosis'):
        ActualActionCursor(original)


def test_full_call_still_fails_without_advancing_or_consuming_suffix():
    cursor = init()
    for t in range(1,26):
        cursor = advance(cursor,obs(t))
    before = cursor.execution
    cursor = advance(cursor,obs(26,g=.125,c=.125))
    assert cursor.primary.records[-1].stage == 'separate_planning'
    assert cursor.stopped and cursor.execution == before
    assert cursor.decisions[-1].actual_record.status == 'unassessed'
    assert summarize(cursor)['validated_unique_hours'] == 25
    assert summarize(cursor)['submitted_unique_hours'] == 26
    with pytest.raises(ValueError,match='cannot consume'):
        advance(cursor,obs(27))


def test_shared_execution_trigger_remains_distinct_from_old_policy():
    cursor = init()
    for t in range(1,49):
        cursor = advance(cursor,obs(t))
    assert cursor.primary.records[-1].stage == 'shared_execution'
    assert summarize(cursor)['validated_unique_hours'] == 48
    assert cursor.execution.tracks[0][1].ledger.debt == 0


def test_future_perturbation_and_chunking():
    prefix = through(25)
    a = advance(prefix,row(26))
    b = advance(prefix,obs(26,business_recovery_headroom=0.))
    assert a.decisions[:1] == b.decisions[:1] == prefix.decisions
    assert b.decisions[-1].actual_record.action.recovery == 0
    assert b.execution.tracks[0][1].ledger.cohorts[0].missed_at_deadline == Q('1/8')
    for t in range(27,49):
        b = advance(b,row(t))
    assert b.execution.tracks[0][1].ledger.cohorts[0].missed_at_deadline == Q('1/8')
    chunked = init()
    for block in (range(1,24),range(24,26),range(26,49)):
        for t in block:
            chunked = advance(chunked,row(t))
    assert chunked == through(48)


@pytest.mark.parametrize('field,value', [('split','training'),('power_source_hour',99),
                                         ('workload_provenance_sha256','4'*64)])
def test_invalid_suffix_preserves_last_physical_hour(field,value):
    prefix = through(25)
    r = row(26)
    cursor = advance(prefix,replace(r,hour=replace(r.hour,**{field:value})))
    assert cursor.stopped and cursor.execution == prefix.execution
    assert cursor.decisions[-1].stage == 'input_validation'
    assert cursor.decisions[-1].actual_record is None
    assert summarize(cursor)['last_validated_hour'] == 25


def test_decision_failure_and_primary_nontriggers():
    prefix = through(25)
    cursor = advance(prefix,obs(26,g=.125,c=6e-7))
    assert cursor.stopped and cursor.execution == prefix.execution
    assert cursor.decisions[-1].stage == 'recovery_decision'
    for r in (obs(1,g=1.1,c=0.),obs(99)):
        cursor = advance(init(),r)
        assert cursor.stopped and not cursor.decisions
        assert summarize(cursor)['validated_unique_hours'] == 0


def test_local_history_consistency_and_policy_identity_guards():
    cursor = through(26)
    with pytest.raises(ValueError,match='same-hour'):
        replace(cursor,decisions=())
    with pytest.raises(ValueError,match='state chain'):
        replace(cursor,decisions=cursor.decisions[1:])
    with pytest.raises(ValueError,match='deterministic replay'):
        replace(cursor.decisions[0],stage='invented')
    spec = replace(cursor.spec,recovery=FixedPolicy(recovery_decimal_places=2))
    assert spec.policy_id != cursor.policy_id
    with pytest.raises(ValueError,match='identity'):
        replace(cursor,spec=spec)


@pytest.mark.parametrize('key,value', [('trigger_stages',['input_validation']),
    ('formal_result',True),('failure','continue'),('arm_id','joint_correct_shared')])
def test_config_drift_rejected(key,value):
    with pytest.raises(ValueError,match='draft policy semantics'):
        B6PlanningRecoveryPolicy.from_config(dict(CONFIG,**{key:value}))


def test_known_edf_precedes_unknown_and_unknown_is_not_completed_claim():
    cursor = init()
    for t in range(1,27):
        r = row(t)
        cursor = advance(cursor,replace(r,due_hour=None) if t == 23 else r)
    action = cursor.decisions[-1].actual_record.action
    assert action.allocations == ((24,Q('1/8')),(25,Q('1/8')))
    cursor = advance(cursor,row(27))
    assert cursor.execution.tracks[0][1].ledger.debt == 0
    assert cursor.execution.tracks[0][1].ledger.cohorts[0].due_hour is None
    assert summarize(cursor)['completion_claim_allowed'] is False


@pytest.mark.parametrize('limit',['business_recovery_headroom','cfe_compatible_surplus','maximum_recovery_power'])
def test_each_shared_limit_and_persistent_deadline_miss(limit):
    cursor = advance(through(25),obs(26,**{limit:0.}))
    assert cursor.decisions[-1].actual_record.action.recovery == 0
    assert cursor.execution.tracks[0][1].ledger.debt == Q('3/8')
    assert cursor.execution.tracks[0][1].ledger.cohorts[0].missed_at_deadline == Q('1/8')
    cursor = advance(cursor,row(27))
    assert cursor.execution.tracks[0][1].ledger.cohorts[0].missed_at_deadline == Q('1/8')


def test_precision_residual_and_illegal_suffix_history():
    spec = replace(B6PlanningRecoveryPolicy.from_config(CONFIG),recovery=FixedPolicy(recovery_decimal_places=2))
    cursor = initialize_b6_planning_recovery(spec,anchor=anchor(),envelope=F['envelope'],
        accounting_period_id='synthetic-period',zero_carry_in_assumption=True)
    for t in range(1,49):
        cursor = advance(cursor,row(t))
    assert cursor.decisions[1].actual_record.action.recovery == .31
    assert cursor.execution.tracks[0][1].ledger.debt > 0
    prefix = through(25)
    bad = advance(prefix,obs(99))
    with pytest.raises(ValueError,match='cannot have a suffix'):
        replace(bad,decisions=bad.decisions+(bad.decisions[-1],))
