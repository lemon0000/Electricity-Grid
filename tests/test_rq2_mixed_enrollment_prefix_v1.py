from dataclasses import replace
from fractions import Fraction as Q
from types import SimpleNamespace

import pytest

from experiments import summarize_rq2_mixed_enrollment_prefix_v1 as d
from experiments import summarize_rq2_scale_committed_prefix_v1 as old
from test_rq2_hourly_zero_face_transaction_v1 import common, arm, execute, ACT, SPEC, tx, source, audit
from test_rq2_hourly_transaction_v1 import next_hour


def summarize(cursor, enrolled=(1,), window=(1, 2, 3)):
    return d.summarize_cursor(cursor, window, enrollment_source_hours=enrolled,
                              expected_cursor_identity=cursor.identity)


@pytest.fixture(scope='module')
def trajectories(tmp_path_factory):
    root = tmp_path_factory.mktemp('mixed_enrollment')
    req, first = common(root)
    results, origins = {}, {}
    for name in tx.ARMS:
        before, budget = arm(req, first, name)
        origins[name] = before
        proposal = tx.prepare_arm(before, first, selector=ACT, solver_specification=SPEC, budget=budget)
        raw, pins = execute(root/('actual_'+str(tx.ARMS.index(name))+'_non_authoritative'), proposal.dispatch_request)
        results[name] = tx.finish_arm(proposal, raw, **pins)['cursor']
    before, budget = arm(req, first, tx.JOINT, capacity=.125)
    proposal = tx.prepare_arm(before, first, selector=ACT, solver_specification=SPEC, budget=budget)
    rejected = tx.finish_arm(proposal)
    info, disclosure = next_hour(SimpleNamespace(reference_state=first.reference_result.next_state), demand=20., cap=25.)
    inputs = (info, disclosure, first.reference_result.next_state)
    second_request = replace(req, info=info, disclosure=disclosure, before=inputs[2],
        budget=replace(req.budget, source_hour=2), expected_identity=tx.scale.reference.reference_input_identity(*inputs))
    raw, pins = execute(root/'second_reference_non_authoritative', second_request)
    hour = replace(source(inputs, '45'), power_source_hour=2, workload_source_hour=102)
    second = tx.publish_common_record(raw, second_request, hour, first.mapping, audit(info), previous=first,
        limits=first.current.observation.limits, due_hour=5, available_flexibility=1., **pins)
    _, budget = arm(req, first, tx.JOINT)
    proposal = tx.prepare_arm(results[tx.JOINT], second, selector=ACT, solver_specification=SPEC,
        budget=replace(budget, source_hour=2))
    raw, pins = execute(root/'second_actual_non_authoritative', proposal.dispatch_request)
    two = tx.finish_arm(proposal, raw, **pins)['cursor']
    return origins, results, rejected, two


@pytest.mark.parametrize('name', tx.ARMS)
def test_only_paired_commits_and_applicable_services_count(trajectories, name):
    _, results, _, _ = trajectories
    result = summarize(results[name])
    count = 0 if name == tx.CFE else 1
    assert result['committed_hours'] == count
    assert result['enrollment']['committed_source_hours'] == (() if count == 0 else (1,))
    assert result['enrollment_uncommitted_source_hours'] == ((1,) if count == 0 else ())
    assert result['enrolled_remaining_debt'] == (0 if count == 0 else Q(1, 3))
    assert result['followup_remaining_debt'] == 0
    if name == tx.CFE:
        assert result['enrollment']['grid_shortfall_energy'] is None
    if name == tx.NETWORK:
        assert result['enrollment']['cfe_shortfall_energy'] is None
    assert result['enrollment_service_result'] is result['complete_service_result'] is result['risk_probability'] is None
    assert not result['enrollment_declaration_registered'] and not result['historical_grid_archives_replayed']


def test_followup_debt_preserved_and_partition_changes_no_state(trajectories):
    _, _, _, cursor = trajectories
    identity = cursor.identity
    report = summarize(cursor)
    assert report['remaining_debt'] == Q(2, 3)
    assert report['enrolled_remaining_debt'] == report['followup_remaining_debt'] == Q(1, 3)
    assert [(r['birth'], r['scope']) for r in report['cohorts']] == [(1, 'enrolled'), (2, 'followup')]
    assert all(r['status'] == 'right_censored_before_deadline' for r in report['cohorts'])
    assert report['followup']['committed_source_hours'] == (2,)
    longer = summarize(cursor, enrolled=(1, 2))
    assert longer['enrolled_remaining_debt'] == Q(2, 3) and longer['followup_remaining_debt'] == 0
    assert cursor.identity == identity  # This is a declared partition, not a new state or registered estimand.


def test_rejected_candidate_creates_no_committed_cohort_or_service_failure(trajectories):
    _, _, rejected, _ = trajectories
    report = summarize(rejected['cursor'])
    assert report['committed_hours'] == 0 and not report['cohorts']
    assert report['enrollment_uncommitted_source_hours'] == (1,)
    assert report['committed_grid_failure_hours'] == 0
    with pytest.raises(ValueError, match='not a business candidate'):
        d.summarize_cursor(rejected['business_candidate'], (1, 2, 3), enrollment_source_hours=(1,),
                           expected_cursor_identity='0'*64)


@pytest.mark.parametrize('enrolled', [(), (2,), (1, 3), (True,), (1, 2, 3, 4), [1]])
def test_declared_enrollment_must_be_nonempty_prefix(trajectories, enrolled):
    with pytest.raises(ValueError, match='enrollment'):
        summarize(trajectories[1][tx.JOINT], enrolled=enrolled)


def test_identity_grid_endpoint_and_legacy_type_guard(trajectories):
    origins, results, _, _ = trajectories
    cursor = results[tx.JOINT]
    with pytest.raises(ValueError, match='identity'):
        d.summarize_cursor(cursor, (1, 2), enrollment_source_hours=(1,), expected_cursor_identity='0'*64)
    bad = tx._owned(tx.ArmCursor, **dict(vars(cursor), grid=origins[tx.JOINT].grid))
    with pytest.raises(ValueError, match='endpoint'):
        summarize(bad)
    with pytest.raises(ValueError, match='owned paired'):
        old.summarize_cursor(cursor, (1, 2), expected_cursor_identity=cursor.identity)
