"""Real 192-hour business ledger at the exact deadline; detached, zero Job."""
from fractions import Fraction as Q
import time
from types import SimpleNamespace

from experiments import h1_phase_owner_development_v1 as phase
from tests import test_h1_exact_business_development_v1 as fixture
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def test_deadline_hour_recovers_before_snapshot_without_requesting_hour_193(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('detached deadline test must not observe a source')
    monkeypatch.setattr(phase, '_fresh', denied)
    monkeypatch.setattr(phase.source.source.windows, 'load_source_window', denied)
    carry = fixture.origin(mechanism=phase.business.Mechanism(Q(1, 2), Q(1, 2), Q(1, 5)))
    original = phase.business._validate
    validations = []
    def measured(value):
        validations.append(len(value.history))
        return original(value)
    monkeypatch.setattr(phase.business, '_validate', measured)
    started = time.perf_counter()
    for hour in range(1, 193):
        item = fixture.hour(carry, hour - 1,
            g=Q(17, 200) if hour == 168 else Q(0),
            source=Q(0) if hour == 192 else Q(1, 2))
        result = fixture.advance(carry, item)
        assert result.next_candidate is not None
        carry = result.next_candidate
        if hour == 191:
            prior = carry.cursor.execution.tracks[0][1].ledger
            assert prior.debt == Q(17, 200)
            assert prior.cohorts[0].missed_at_deadline is None
    ledger = carry.cursor.execution.tracks[0][1].ledger
    action = carry.cursor.records[-1].response.action
    assert action.recovery == Q(1, 10) and action.grid_served + action.cfe_served == 0
    assert ledger.debt == 0 and ledger.cohorts[0].missed_at_deadline == 0
    assert ledger.cohorts[0].due_hour == 192 and ledger.cohorts[0].remaining == 0
    state = SimpleNamespace(hour=192, lanes=(('joint', SimpleNamespace(
        business=carry, halted=False, completed=True)),),
        scientific=dict(detached_business_identity=carry.identity))
    assessment = phase._assessment(state)
    fact = assessment.lanes[0].business
    assert fact.primary_recovery_status == 'S' and not assessment.needs_next_hour
    assert assessment.lanes[0].owner_disposition == 'completed'
    assert fact.primary_cohorts[0].status == 'success_by_due'
    assert fact.next_relative_hour is None and fact.last_primary_due == 192
    assert len(validations) == 193 and sum(validations) == 18528
    host = SimpleNamespace(_heads=lambda rows: ('4' * 64, '5' * 64))
    terminal = phase.DevelopmentOwner._terminal_body(host, state, ())
    assert terminal['hour'] == 192 and terminal['reason'] == 'no_active_lane_needs_next_hour'
    assert len(validations) == 194 and sum(validations) == 18720
    artifact = dict(status='DRAFT_NONAUTHORITATIVE',
        scope='detached_exact_due_hour_business_and_original_phase_body',
        completed_business_hours=192, birth_hour=168, due_hour=192,
        final_recovery=action.recovery, debt=ledger.debt,
        deadline_snapshot=ledger.cohorts[0].missed_at_deadline,
        assessment=terminal['assessment'],
        original_validate_calls=len(validations), validate_history_length_sum=sum(validations),
        business_path_wall_seconds=time.perf_counter() - started,
        source_prefix_authenticated=False, paired_owner_authenticated=False,
        phase_events_written=0, new_normal_jobs=0, real_native_calls=0,
        full_192_hour_execution_verified=False, formal_result=False)
    (tmp_path / 'due_endpoint_fact.json').write_bytes(phase.encode(artifact))
