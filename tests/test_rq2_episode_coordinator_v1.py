from copy import copy, deepcopy
from dataclasses import replace
from fractions import Fraction as Q
import pickle

import pytest

from test_rq2_hourly_transaction_v1 import (
    args, make_origin, arm_origin, source, audit, obs, next_hour,
    REF_SELECTOR, REF_BUDGET, SPEC, SELECTOR, SHORT,
)
from test_rq2_reference_selector_v1 import install as install_reference
from src.rq2_joint_deliverability_boundary_v1 import episode_coordinator as ep
from src.rq2_joint_deliverability_boundary_v1 import hourly_transaction as tx


def origins():
    inputs = args()
    common = make_origin(inputs)
    return inputs, common, tuple(arm_origin(inputs, common, arm) for arm in ep.ARMS)


def session(common, arms, budget=None):
    return ep.EpisodeSession(common, arms, reference_selector=REF_SELECTOR, solver_specification=SPEC,
        reference_budget=REF_BUDGET, budget=budget or ep.EpisodeBudget(3, 40, 40))


def advance(s, info, disclosure, **changes):
    hour = replace(source((info, disclosure, s.snapshot.common.reference_state)),
        power_source_hour=info.current.source_hour, workload_source_hour=100+info.current.source_hour)
    values = dict(limits=obs(1, g=0., c=0., due=None).limits, due_hour=5, available_flexibility=1.)
    values.update(changes)
    return s.advance(info, disclosure, hour, audit(info), **values)


@pytest.fixture(scope='module')
def real_first():
    inputs, common, arms = origins()
    s = session(common, arms)
    result = advance(s, *inputs[:2])
    return inputs, common, arms, s, result


def test_real_common_chain_and_independent_stops(real_first):
    _, common, arms, _, result = real_first
    assert result.status == 'advanced' and not result.halted
    assert result.training_capacity_certificate is result.complete_service_certificate is result.causal_certificate is None
    assert result.formal_result is result.security_certified is False
    assert result.reserved_solver_calls == 11 and result.reserved_solver_seconds == 11
    record = result.attempts[0]
    assert record.solver_calls == record.known_solver_calls == 10
    assert len(record.arm_results) == 4
    assert len({r.exposure_id for r in record.arm_results}) == 1
    assert result.common != common
    for before, after, r in zip(arms, result.arms, record.arm_results):
        if r.arm_id == ep.CFE:
            assert after.halted and r.status == 'physical_network_unresolved'
            assert after.business == before.business and after.grid == before.grid
            assert r.grid_service_failure is None
        else:
            assert r.status == 'committed'
            assert after.business.execution.tracks[0][1].ledger.debt == Q(1, 3)


def test_second_hour_skips_halted_and_preserves_open_debt(real_first):
    _, _, _, s, first = real_first
    info, disclosure = next_hour(first.common)
    second = advance(s, info, disclosure)
    assert second.reserved_solver_calls == 20 and second.reserved_solver_seconds == 20
    record = second.attempts[-1]
    assert record.skipped_halted_arms == (ep.CFE,) and record.unattempted_arms == ()
    assert len(record.arm_results) == 3 and record.solver_calls == 9
    assert second.arms[1] == first.arms[1]
    assert second.arms[0].business.execution.tracks[0][1].ledger.debt == Q(2, 3)
    assert record.common_attempt.publication.previous_publication_identity == first.common.last_publication_identity


@pytest.mark.parametrize('budget', [ep.EpisodeBudget(1, 10, 60), ep.EpisodeBudget(1, 120, 10)])
def test_budget_exhaustion_before_any_solver(budget, monkeypatch):
    inputs, common, arms = origins()
    def forbidden(*a, **kw): raise AssertionError('no solver may run')
    monkeypatch.setattr(tx.reference_selection, 'select_reference_hour', forbidden)
    with pytest.raises(ValueError, match='complete planned episode'):
        session(common, arms, budget)


def test_entire_window_budget_checked_at_initialization():
    _, common, arms = origins()
    with pytest.raises(ValueError, match='complete planned episode'):
        session(common, arms, ep.EpisodeBudget(2, 21, 60))


def cached_first(monkeypatch, real_first):
    record = real_first[-1].attempts[0]
    monkeypatch.setattr(tx.reference_selection, 'select_reference_hour', lambda *a, **kw: record.reference_result)
    monkeypatch.setattr(tx, 'advance_arm_hour', lambda arm, pub: next(
        r for r in record.arm_results if r.arm_id == arm.business.spec.arm_id))
    return record


def test_window_completion_preserves_outstanding_debt(real_first, monkeypatch):
    cached_first(monkeypatch, real_first)
    inputs, common, arms = origins()
    s = session(common, arms, ep.EpisodeBudget(1, 11, 11))
    after = advance(s, *inputs[:2])
    assert after.status == 'observation_window_complete' and after.halted
    assert after.planned_last_hour_attempted and after.input_window_consumed
    assert after.arms[0].business.execution.tracks[0][1].ledger.debt == Q(1, 3)
    assert not after.arms[0].halted
    with pytest.raises(ValueError, match='halted'):
        advance(s, *inputs[:2])


@pytest.mark.parametrize('failure', ['exception', 'drift', 'wrong_arm'])
def test_late_hour_failure_keeps_inner_evidence_but_no_outer_commit(real_first, monkeypatch, failure):
    record = cached_first(monkeypatch, real_first)
    inputs, common, arms = origins()
    s = session(common, arms)
    calls = []
    def changed(arm, publication):
        calls.append(arm.business.spec.arm_id)
        if len(calls) == 2:
            if failure == 'exception': raise RuntimeError('after first arm')
            if failure == 'drift': monkeypatch.setattr(ep, 'CONTRACT', 'changed')
            if failure == 'wrong_arm': return record.arm_results[0]
        return record.arm_results[len(calls)-1]
    monkeypatch.setattr(tx, 'advance_arm_hour', changed)
    with pytest.raises((RuntimeError, ValueError)):
        advance(s, *inputs[:2])
    after = s.snapshot
    assert after.status == 'interrupted' and after.halted
    assert after.common == common and after.arms == arms
    assert after.attempts[0].arm_results[0].published_pair is not None
    assert not after.attempts[0].outer_committed
    assert after.attempts[0].committed_arm_results == ()
    assert after.attempts[0].published_common_hour is None
    assert after.attempts[0].hour_input.info == inputs[0]
    assert after.attempts[0].solver_calls is None
    assert after.reserved_solver_calls == 11


def test_lower_caught_dispatch_error_has_unknown_total_calls(real_first, monkeypatch):
    cached_first(monkeypatch, real_first)
    inputs, common, arms = origins()
    s = session(common, arms, ep.EpisodeBudget(1, 11, 11))
    monkeypatch.undo()
    monkeypatch.setattr(tx.reference_selection, 'select_reference_hour',
        lambda *a, **kw: real_first[-1].attempts[0].reference_result)
    calls = []
    def interrupted(*a, **kw):
        calls.append(1)
        raise ValueError('native call may already have happened')
    monkeypatch.setattr(tx.dispatch, 'select_actual_dispatch', interrupted)
    after = advance(s, *inputs[:2])
    assert len(calls) == 4
    assert after.status == 'all_arms_halted'
    assert after.planned_last_hour_attempted and after.input_window_consumed
    assert after.attempts[0].solver_calls is None
    assert after.attempts[0].known_solver_calls == 3
    assert not after.attempts[0].solver_call_count_complete
    assert after.attempts[0].dispatch_call_count_unresolved_arms == ep.ARMS
    assert {r.status for r in after.attempts[0].arm_results} == {'dispatch_execution_unresolved'}


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'order'])
def test_four_arm_inventory(case):
    _, common, arms = origins()
    bad = arms[:3] if case == 'missing' else (arms[0],)*4 if case == 'duplicate' else arms[::-1]
    with pytest.raises(ValueError, match='four'):
        session(common, bad)


def test_per_arm_capacity_can_differ_but_business_mechanism_cannot():
    inputs, common, arms = origins()
    changed = arm_origin(inputs, common, ep.NETWORK, capacity=.5)
    s = session(common, (changed,)+arms[1:])
    assert s.snapshot.arms[0].business.spec.committed_capacity == .5
    from src.rq2_joint_deliverability_boundary_v1.capacity_policy import initialize_capacity_policy
    track = changed.business.initial.tracks[0][1]
    business = initialize_capacity_policy(replace(changed.business.spec, maximum_recovery_power=.123),
        anchor=common.source_anchor, envelope=dict(track.physical.envelope),
        accounting_period_id=track.ledger.accounting_period_id, zero_carry_in_assumption=True)
    bad = tx.initialize_arm_hours(common, business, changed.grid, selector=SELECTOR,
        solver_specification=SPEC, budget=SHORT)
    with pytest.raises(ValueError, match='business mechanism'):
        session(common, (bad,)+arms[1:])


def test_unequal_actual_generation_rejected():
    inputs, common, arms = origins()
    original = tx.dispatch._physical(arms[0].grid)
    grid = tx.dispatch.initialize_dispatch_origin(inputs[0], original.disclosure,
        grid_protocol=original.protocol, generation_mw=(('G1', 19.),),
        base_availability=original.base_availability, selector=SELECTOR, solver_specification=SPEC, budget=SHORT)
    bad = tx.initialize_arm_hours(common, arms[0].business, grid,
        selector=SELECTOR, solver_specification=SPEC, budget=SHORT)
    with pytest.raises(ValueError, match='physical origin'):
        session(common, (bad,)+arms[1:])


def test_unresolved_reference_is_preserved_and_stops_episode(monkeypatch):
    inputs, common, arms = origins()
    s = session(common, arms, ep.EpisodeBudget(1, 11, 11))
    install_reference(monkeypatch, 'timeout', 0)
    after = advance(s, *inputs[:2])
    assert after.halted and after.status == 'request_unresolved'
    assert after.planned_last_hour_attempted and not after.input_window_consumed
    assert after.common.reference_state == common.reference_state
    assert after.arms == arms
    record = after.attempts[0]
    assert record.solver_calls == 1 and record.reserved_solver_calls == 11
    assert record.common_attempt.publication is None
    assert record.common_attempt.mapping_result.raw_grid_request_mw is None
    assert record.unattempted_arms == ep.ARMS


@pytest.mark.parametrize('exception', [RuntimeError, KeyboardInterrupt])
def test_interruption_keeps_reservation_and_stops_retry(monkeypatch, exception):
    inputs, common, arms = origins()
    s = session(common, arms)
    def interrupt(*a, **kw): raise exception('injected')
    monkeypatch.setattr(tx.reference_selection, 'select_reference_hour', interrupt)
    with pytest.raises(exception):
        advance(s, *inputs[:2])
    after = s.snapshot
    assert after.halted and after.status == 'interrupted'
    assert after.reserved_solver_calls == 11 and after.reserved_solver_seconds == 11
    assert after.common == common and after.arms == arms
    assert after.attempts[0].solver_calls is None and after.attempts[0].known_solver_calls == 0
    with pytest.raises(ValueError, match='halted'):
        advance(s, *inputs[:2])


def test_session_cannot_copy_or_checkpoint():
    _, common, arms = origins()
    s = session(common, arms)
    for operation in (copy, deepcopy, pickle.dumps):
        with pytest.raises(TypeError): operation(s)
    with pytest.raises(AttributeError): s.snapshot = s.snapshot
    with pytest.raises(TypeError): replace(s.snapshot, halted=False)


def test_concurrent_entry_is_rejected_without_reservation():
    inputs, common, arms = origins()
    s = session(common, arms)
    before = s.snapshot
    s._lock.acquire()
    try:
        with pytest.raises(ValueError, match='already in progress'):
            advance(s, *inputs[:2])
    finally:
        s._lock.release()
    assert s.snapshot == before


def test_duplicate_hour_rejected_before_solver(real_first, monkeypatch):
    inputs, _, _, s, _ = real_first
    before = s.snapshot
    def forbidden(*a, **kw): raise AssertionError('no duplicate solve')
    monkeypatch.setattr(tx.reference_selection, 'select_reference_hour', forbidden)
    with pytest.raises(ValueError): advance(s, *inputs[:2])
    assert s.snapshot == before


@pytest.mark.parametrize('phase', ['publication', 'arm_0', 'arm_2', 'arm_3'])
def test_interruption_windows_keep_complete_input_and_no_outer_commit(real_first, monkeypatch, phase):
    record = cached_first(monkeypatch, real_first)
    inputs, common, arms = origins()
    s = session(common, arms)
    def interrupt(*a, **kw): raise KeyboardInterrupt('window injection')
    if phase == 'publication':
        monkeypatch.setattr(tx, 'publish_common_hour', interrupt)
        completed = 0
    else:
        completed = int(phase[-1])
        def arm_step(arm, pub):
            index = ep.ARMS.index(arm.business.spec.arm_id)
            if index == completed: interrupt()
            return record.arm_results[index]
        monkeypatch.setattr(tx, 'advance_arm_hour', arm_step)
    with pytest.raises(KeyboardInterrupt): advance(s, *inputs[:2])
    result = s.snapshot
    attempt = result.attempts[0]
    assert result.common == common and result.arms == arms
    assert result.reserved_solver_calls == 11
    assert len(attempt.arm_results) == completed
    assert attempt.reference_result == record.reference_result
    assert attempt.hour_input.source_audit == audit(inputs[0])
    assert attempt.hour_input.due_hour == 5
    assert attempt.hour_input.available_flexibility == 1.
    begun = completed if phase == 'publication' else completed+1
    assert attempt.unattempted_arms == ep.ARMS[begun:]
    assert attempt.started_arm_ids == ep.ARMS[:begun]
    assert attempt.arms_without_complete_result == (() if phase == 'publication' else (ep.ARMS[completed],))
    assert attempt.committed_arm_results == () and not attempt.outer_committed
    assert not attempt.solver_call_count_complete and attempt.solver_calls is None


def test_reentry_during_solver_is_rejected_without_double_reservation(real_first, monkeypatch):
    record = cached_first(monkeypatch, real_first)
    inputs, common, arms = origins()
    s = session(common, arms, ep.EpisodeBudget(1, 11, 11))
    def reference(*a, **kw):
        assert s.snapshot.status == 'attempt_in_progress'
        assert s.snapshot.reserved_solver_calls == 11
        with pytest.raises(ValueError, match='already in progress'):
            advance(s, *inputs[:2])
        return record.reference_result
    monkeypatch.setattr(tx.reference_selection, 'select_reference_hour', reference)
    result = advance(s, *inputs[:2])
    assert result.reserved_solver_calls == 11 and len(result.attempts) == 1
    assert result.status == 'observation_window_complete'


def test_bad_source_rejected_before_effects(monkeypatch):
    inputs, common, arms = origins()
    s = session(common, arms)
    before = s.snapshot
    def forbidden(*a, **kw): raise AssertionError('no call for bad source')
    monkeypatch.setattr(tx.reference_selection, 'select_reference_hour', forbidden)
    with pytest.raises(ValueError, match='source audit'):
        s.advance(*inputs[:2], source(inputs), None,
            limits=obs(1, g=0., c=0., due=None).limits, due_hour=5, available_flexibility=1.)
    assert s.snapshot == before


def test_final_snapshot_construction_drift_cannot_commit(real_first, monkeypatch):
    cached_first(monkeypatch, real_first)
    inputs, common, arms = origins()
    s = session(common, arms)
    owned = ep._owned
    def changed(cls, **values):
        result = owned(cls, **values)
        if cls is ep.EpisodeSnapshot and values['status'] == 'advanced':
            monkeypatch.setattr(ep, 'CONTRACT', 'changed after final candidate construction')
        return result
    monkeypatch.setattr(ep, '_owned', changed)
    with pytest.raises(ValueError, match='contract drift'):
        advance(s, *inputs[:2])
    after = s.snapshot
    assert after.halted and after.status == 'interrupted'
    assert after.common == common and after.arms == arms
    assert len(after.attempts[0].arm_results) == 4
    assert after.attempts[0].committed_arm_results == ()
    assert not after.attempts[0].outer_committed
    assert after.reserved_solver_calls == 11


@pytest.mark.parametrize('changed', ['limits', 'due_hour', 'available_flexibility'])
def test_foreign_common_business_conditions_rejected(real_first, monkeypatch, changed):
    record = cached_first(monkeypatch, real_first)
    inputs, common, arms = origins()
    s = session(common, arms)
    values = dict(limits=obs(1, g=0., c=0., due=None).limits, due_hour=5, available_flexibility=1.)
    values[changed] = (replace(values['limits'], maximum_recovery_power=.123) if changed == 'limits'
                       else 6 if changed == 'due_hour' else .5)
    foreign = tx.publish_common_hour(common, *inputs[:2], record.reference_result, source(inputs), audit(inputs[0]), **values)
    assert foreign.publication is not None
    monkeypatch.setattr(tx, 'publish_common_hour', lambda *a, **kw: foreign)
    with pytest.raises(ValueError, match='publication differs from saved input'):
        advance(s, *inputs[:2])
    after = s.snapshot
    assert after.common == common and after.arms == arms
    assert after.attempts[0].common_attempt == foreign
    assert not after.attempts[0].outer_committed
    assert after.attempts[0].started_arm_ids == ()
