"""Detached real-business/phase assessment tests; no saved N/paired credentials.

The inherited fixture constructs every business hour from genesis with the real
business implementation. Metadata stand-ins below are only phase-body unit
inputs. They are never written to a phase journal or used to admit production.
"""
from dataclasses import asdict
from fractions import Fraction as Q
import json
from types import SimpleNamespace

import pytest

from experiments import h1_phase_boundary_budget_development_v1 as budget
from experiments import h1_phase_owner_development_v1 as phase
from tests.test_h1_finite_followup_assessment_development_v1 import histories
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture(autouse=True)
def no_source_or_job(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('detached phase assessment must not read source or produce a Job')
    monkeypatch.setattr(phase, '_fresh', denied)
    monkeypatch.setattr(phase.source.source.windows, 'load_source_window', denied)


def state(carry, *, disposition='active', outer=None):
    hour = len(carry.history) if outer is None else outer
    return SimpleNamespace(hour=hour, lanes=(('joint', SimpleNamespace(
        business=carry, halted=disposition == 'halted_unresolved',
        completed=disposition == 'completed')),),
        scientific=dict(detached_business_identity=carry.identity, outer_hour=hour))


def body_host():
    # Public owner guards/roots are deliberately absent. This is a pure body test.
    return SimpleNamespace(binding=phase.SourceBinding(
        'synthetic_metadata_only_non_authoritative', '1' * 64, '2' * 64, '3' * 64),
        _heads=lambda rows: ('4' * 64, '5' * 64),
        _branches=lambda: ((1024,) * 4, (1024,) * 2))


def test_count_recurrence_matches_saved_three_hour_observations():
    row = budget.schedule(3, missing_next=True, public_inspect=True)
    assert (row['reader_observations'], row['reader_prefix_hour_weight']) == (32, 64)
    assert (row['parent_inspect_traversals'], row['parent_inspect_prefix_hour_weight']) == (64, 128)
    for h in (1, 2, 3, 168, 192):
        row = budget.schedule(h)
        assert row['reader_observations'] == 8 * h + 4
        assert row['reader_prefix_hour_weight'] == 4 + 4 * h * (h + 1)
        tail = budget.schedule(h, terminal=True, public_inspect=True)
        assert tail['minimum_events'] == 3 * h
        assert tail['reader_observations'] == 8 * h + 10
        assert tail['reader_prefix_hour_weight'] == 4 * h * h + 10 * h + 4


@pytest.mark.parametrize('hours', [168, 192])
def test_business_visit_lower_bound_from_independent_event_enumeration(hours):
    def one_restore(h):
        prepare = sum(range(h))
        paired_assess = sum(range(1, h + 1))
        intent_assess = sum(range(h))
        attempt_assess = sum(range(1, h))
        return prepare + paired_assess + intent_assess + attempt_assess + h
    assert one_restore(hours) == 2 * hours * hours
    independent = 3 * sum(one_restore(h) + one_restore(h + 1) for h in range(hours))
    assert independent == budget.business_history_lower_bound(hours, 3)


def test_original_branch_gate_rejects_small_event_budget_before_next_hour():
    # Real _fits; payload size is intentionally tiny to isolate event count.
    host = SimpleNamespace(manifest=SimpleNamespace(
        max_events=32, max_event_bytes=1024 ** 2, max_archive_bytes=32 * 1024 ** 2))
    row = (0, '', '', b'x', '')
    branches = phase.DevelopmentOwner._branches(host)
    phase.DevelopmentOwner._fits(host, [row] * 26, branches)
    with pytest.raises(ValueError, match='complete branch does not fit'):
        phase.DevelopmentOwner._fits(host, [row] * 29, branches)
    for h in (168, 192):
        host.manifest.max_events = 3 * h
        phase.DevelopmentOwner._fits(host, [row] * (3 * h - 4), branches)


@pytest.mark.parametrize('label,hour,need,next_phase,recovery', [
    ('no_requests', 167, True, 'enrollment', 'U'),
    ('no_requests', 168, False, None, 'S'),
    ('pending', 168, True, 'followup', 'U'),
    ('pending', 169, True, 'followup', 'U'),
    ('recover_primary', 170, False, None, 'S'),
    ('late_recovery', 170, True, 'followup', 'F'),
    ('pending', 191, True, 'followup', 'U'),
    ('pending', 192, False, None, 'F'),
])
def test_original_phase_bodies_consume_complete_business_histories(
        histories, tmp_path, label, hour, need, next_phase, recovery):
    carry = histories[label][hour]
    before = state(carry)
    assessment = phase._assessment(before)
    fact = assessment.lanes[0].business
    assert assessment.needs_next_hour is need
    assert fact.next_phase == next_phase and fact.primary_recovery_status == recovery
    assert not assessment.owner_replay_authenticated and not assessment.actual_paired_commit_verified
    assert not assessment.producer_admitted and not assessment.formal_result
    host = body_host()
    rows = [(1, '', 'intent', phase.encode(dict(terminal='3' * 64)), '')]
    if need:
        with pytest.raises(ValueError, match='episode still needs'):
            phase.DevelopmentOwner._terminal_body(host, before, rows)
        body = phase.DevelopmentOwner._attempt_body(host, before, rows)
        assert body['phase'] == next_phase and body['hour'] == hour
    else:
        with pytest.raises(ValueError, match='positive next-hour need'):
            phase.DevelopmentOwner._attempt_body(host, before, rows)
        body = phase.DevelopmentOwner._terminal_body(host, before, rows)
        assert body['reason'] == 'no_active_lane_needs_next_hour'
    if label == 'recover_primary':
        assert fact.retained_total_debt == Q(17, 200)
        assert fact.primary_cohorts[0].remaining == 0
        assert fact.followup_cohorts[0].remaining == Q(17, 200)
    if label == 'pending' and hour == 192:
        assert fact.primary_cohorts[0].missed_at_deadline == Q(17, 200)
        assert fact.primary_cohorts[0].status == 'failure_at_due'
        assert fact.followup_cohorts[0].due_hour == 193
        assert fact.retained_total_debt == Q(17, 100)
    if label == 'late_recovery':
        assert fact.primary_cohorts[0].remaining == 0
        assert fact.primary_cohorts[0].missed_at_deadline == Q(17, 200)
    artifact = dict(status='DRAFT_NONAUTHORITATIVE', label=label,
        scope='detached_complete_business_history_and_original_phase_body',
        business_hours=hour, source_prefix_authenticated=False,
        paired_owner_authenticated=False, phase_events_written=0,
        jobs=0, real_native_calls=0, formal_result=False,
        assessment=asdict(assessment), body_kind='attempt' if need else 'episode_terminal')
    (tmp_path / 'boundary_fact.json').write_bytes(phase.encode(artifact))


def test_terminal_with_halted_unknown_is_not_a_success(histories):
    before = state(histories['pending'][168], disposition='halted_unresolved', outer=169)
    assessment = phase._assessment(before)
    assert not assessment.needs_next_hour
    assert assessment.lanes[0].business.primary_recovery_status == 'U'
    assert assessment.lanes[0].business.complete_contract_status is None
    body = phase.DevelopmentOwner._terminal_body(body_host(), before, ())
    assert body['assessment']['lanes'][0]['owner_disposition'] == 'halted_unresolved'


def test_missing_needed_followup_is_not_a_business_or_terminal_success(histories):
    # No source is observed here. The existing saved pending-attempt evidence is
    # reused separately; these facts cannot declare availability or right-censoring.
    assessment = phase._assessment(state(histories['pending'][168]))
    fact = assessment.lanes[0].business
    assert assessment.needs_next_hour and fact.next_relative_hour == 168
    assert fact.pending_primary_births == (168,) and fact.last_primary_due == 192
    assert not fact.source_availability_checked and not fact.followup_execution_admitted
    assert fact.complete_contract_status is None
