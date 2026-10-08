from fractions import Fraction as Q
from dataclasses import replace
from copy import deepcopy

import pytest

from experiments import summarize_rq2_scale_committed_prefix_v1 as diagnostics
from test_rq2_scale_rejection_action_semantics_v1 import first_publication, timeout_archive
from test_rq2_scale_hourly_transaction_v1 import arm, execute, ACT, SPEC, tx


def summary(cursor, hours=(1, 2)):
    return diagnostics.summarize_cursor(cursor, hours, expected_cursor_identity=cursor.identity)


@pytest.fixture(scope='module')
def publication(tmp_path_factory):
    return first_publication(tmp_path_factory.mktemp('paired_diagnostic'), cfe=.25, due=2)


@pytest.mark.parametrize('arm_id', [tx.JOINT, tx.B6])
@pytest.mark.parametrize('timeout', [False, True])
def test_only_paired_commit_contributes_cfe_shortfall_and_cohorts(publication, tmp_path, monkeypatch, arm_id, timeout):
    req, pub = publication
    before, budget = arm(req, pub, arm_id, capacity=.4)
    proposal = tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=budget)
    assert proposal.business_candidate.records[-1].response.cfe_shortfall == Q(11, 60)
    if timeout:
        data, pins = timeout_archive(tmp_path/'actual_non_authoritative', proposal.dispatch_request, monkeypatch)
    else:
        data, pins = execute(tmp_path/'actual_non_authoritative', proposal.dispatch_request)
    result = tx.finish_arm(proposal, data, **pins)
    report = summary(result['cursor'])
    assert report['committed_hours'] == (0 if timeout else 1)
    assert report['uncommitted_hours'] == (2 if timeout else 1)
    assert report['uncommitted_source_hours'] == ((1, 2) if timeout else (2,))
    assert report['committed_cfe_shortfall_energy'] == (0 if timeout else Q(11, 60))
    assert report['committed_cfe_failure_hours'] == (0 if timeout else 1)
    assert report['remaining_debt'] == (0 if timeout else Q(2, 5))
    assert report['cohort_assessment'] == (() if timeout else ((1, 'right_censored_before_deadline'),))
    assert report['risk_probability'] is report['complete_service_result'] is None
    assert not report['historical_grid_archives_replayed'] and not report['formal_result']
    with pytest.raises(ValueError, match='not a business candidate'):
        diagnostics.summarize_cursor(proposal.business_candidate, (1, 2), expected_cursor_identity='0'*64)
    if not timeout:
        # Even a fully consumed declared window cannot certify complete recovery.
        complete_window = summary(result['cursor'], (1,))
        assert complete_window['uncommitted_hours'] == 0
        assert complete_window['complete_service_result'] is None
        mismatched = tx._owned(tx.ArmCursor, **dict(vars(result['cursor']), grid=before.grid))
        with pytest.raises(ValueError, match='endpoint'):
            summary(mismatched)


@pytest.mark.parametrize('arm_id', tx.ARMS)
def test_empty_prefix_preserves_not_applicable_vs_zero(publication, arm_id):
    req, pub = publication
    cursor, _ = arm(req, pub, arm_id)
    report = summary(cursor)
    assert report['committed_hours'] == 0 and report['uncommitted_hours'] == 2
    assert report['committed_grid_shortfall_energy'] == (None if arm_id == tx.CFE else 0)
    assert report['committed_cfe_shortfall_energy'] == (None if arm_id == tx.NETWORK else 0)
    assert report['committed_grid_failure_hours'] == (None if arm_id == tx.CFE else 0)
    assert report['committed_cfe_failure_hours'] == (None if arm_id == tx.NETWORK else 0)
    assert report['complete_service_result'] is None


@pytest.mark.parametrize('hours', [(), (2, 3), (1, 3), (True, 2), [1, 2]])
def test_window_cannot_relabel_or_skip_source_hours(publication, hours):
    cursor, _ = arm(*publication, tx.JOINT)
    with pytest.raises(ValueError): summary(cursor, hours)


def test_cursor_pin_policy_and_endpoint_are_checked(publication):
    cursor, _ = arm(*publication, tx.JOINT)
    with pytest.raises(ValueError, match='identity'):
        diagnostics.summarize_cursor(cursor, (1, 2), expected_cursor_identity='0'*64)
    for changes in ({'business_policy_identity':'0'*64}, {'last_publication_identity':'0'*64}):
        forged = tx._owned(tx.ArmCursor, **dict(vars(cursor), **changes))
        with pytest.raises(ValueError): summary(forged)


def test_halted_flag_does_not_invent_attempts_or_change_prefix(publication):
    cursor, _ = arm(*publication, tx.JOINT)
    halted = tx._owned(tx.ArmCursor, **dict(vars(cursor), halted=True))
    before, after = summary(cursor), summary(halted)
    for report in (before, after):
        assert report['uncommitted_source_hours'] == (1, 2)
        assert 'attempted_hours' not in report and 'failed_hours' not in report
    for key in before:
        if key not in ('cursor_identity', 'halted'): assert before[key] == after[key]


def test_business_rejection_record_cannot_be_inserted_into_paired_state(publication):
    req, pub = publication
    before, budget = arm(req, pub, tx.JOINT, capacity=.125)
    proposal = tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=budget)
    assert not proposal.business_candidate.records[-1].committed
    forged = tx._owned(tx.ArmCursor, **dict(vars(before), business=proposal.business_candidate))
    with pytest.raises(ValueError, match='uncommitted business record'): summary(forged)


@pytest.mark.parametrize('fault', ['implementation', 'cursor'])
def test_post_summary_drift_is_rejected(publication, monkeypatch, fault):
    cursor, _ = arm(*publication, tx.JOINT)
    original = diagnostics.business_diagnostics.summarize
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        if fault == 'implementation':
            monkeypatch.setattr(diagnostics, 'implementation_identity', lambda: '0'*64)
        else:
            object.__setattr__(cursor, 'halted', True)
        return result
    monkeypatch.setattr(diagnostics.business_diagnostics, 'summarize', changed)
    with pytest.raises(ValueError, match='changed during summary'): summary(cursor)


def test_record_subclass_cannot_disable_replay_and_erase_shortfall(publication):
    req, pub = publication
    before, budget = arm(req, pub, tx.JOINT, capacity=.4)
    proposal = tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=budget)
    original = proposal.business_candidate.records[-1]
    class UncheckedRecord(diagnostics.capacity_policy.CapacityPolicyRecord):
        def __post_init__(self): pass
    response = deepcopy(original.response)
    object.__setattr__(response, 'cfe_shortfall', Q(0))
    record = UncheckedRecord(**dict(vars(original), response=response))
    assert original.response.cfe_service_failure and not record.response.cfe_service_failure
    business = replace(proposal.business_candidate, records=(record,))
    forged = tx._owned(tx.ArmCursor, **dict(vars(before), business=business))
    with pytest.raises(ValueError, match='exact capacity policy record'): summary(forged)


def test_policy_subclass_is_not_a_canonical_policy(publication):
    before, _ = arm(*publication, tx.JOINT)
    class UncheckedPolicy(diagnostics.capacity_policy.CapacityPolicy):
        def __post_init__(self): pass
    business = replace(before.business, spec=UncheckedPolicy(**vars(before.business.spec)))
    forged = tx._owned(tx.ArmCursor, **dict(vars(before), business=business))
    with pytest.raises(ValueError, match='exact canonical business'): summary(forged)
