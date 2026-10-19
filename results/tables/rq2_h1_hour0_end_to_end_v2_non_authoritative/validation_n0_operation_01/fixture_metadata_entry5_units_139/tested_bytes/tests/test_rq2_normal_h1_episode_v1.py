from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
import json
import sqlite3

import pytest

from tests.test_rq2_continuous_grid_normal_v1 import fixture
from tests.test_rq2_normal_h1_source_v1 import packet, run
from tests.test_rq2_normal_h1_short_solve_v1 import budget
from tests.test_rq2_objective_provenance_run_v1 import spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_episode as api


def episode(root, *, create=True, expected_head=None, plan=None):
    return api.DevelopmentH1NormalEpisode(root, api.source.static_network(fixture(2).data), spec(), budget(),
        plan or api.H1EpisodeBudget(2, 6, 6.), dc_bus=1, create=create, expected_head=expected_head)


def step(owner, hour=0, workload='0'):
    return owner.step(fixture(2).data.hourly_points[hour], workload,
        source_time_basis='naive_source_labelled_utc', expected_head=owner.head)


def events(root):
    connection = sqlite3.connect(root/'h1_normal_episode.sqlite3')
    try:
        return [(head, api._decode_event(raw)) for raw, head in connection.execute('SELECT archive,head FROM events ORDER BY seq')]
    finally:
        connection.close()


@pytest.fixture(scope='module')
def first_result():
    result = run(packet())
    assert result.current_decision_accepted
    return result


def test_two_hours_reopen_uses_exact_prefix_without_solver(tmp_path, monkeypatch):
    root = tmp_path/'normal_non_authoritative'
    owner = episode(root)
    try:
        initial = owner.inspect()
        assert initial.completed_hours == 0 and initial.planned_solver_calls == 6
        first, one = step(owner)
        assert one.completed_hours == 1 and one.status == 'ready'
        assert first.decision.candidate_boundary.units == (('G1', True, 20., 1),)
        second, two = step(owner, 1)
        assert second.decision.candidate_boundary.units == (('G1', True, 20., 2),)
        assert two.completed_hours == 2 and two.status == 'complete'
        assert two.reserved_solver_calls == 6
        head = owner.head
    finally:
        owner.close()
    def forbidden(*args, **kwargs):
        pytest.fail('restoring normal prefix called solver')
    monkeypatch.setattr(api.current, 'solve_current', forbidden)
    monkeypatch.setattr(api.replay.native.capture, 'solve_once', forbidden)
    monkeypatch.setattr(api.replay.native.capture.provenance.adapter, 'create_solver', forbidden)
    owner = episode(root, create=False, expected_head=head)
    try:
        restored = owner.inspect()
        assert restored == two
        assert not any((restored.source_authenticated, restored.native_execution_authenticated,
            restored.formal_result, restored.published, restored.complete_service_certificate, restored.hard_wall_time_verified))
        assert not hasattr(restored, 'candidate_boundary')
        with pytest.raises(ValueError):
            owner.step(object(), 'bad', source_time_basis='bad', expected_head=owner.head)
    finally:
        owner.close()
    records = events(root)
    assert [r['kind'] for _, r in records] == ['intent','accepted','intent','accepted']
    assert records[3][1]['intent_head'] == records[2][0]


@pytest.mark.parametrize('plan', [api.H1EpisodeBudget(2, 5, 6.), api.H1EpisodeBudget(2, 6, 5.),
                                   api.H1EpisodeBudget(7, 20, 60.)])
def test_total_plan_budget_rejected_before_directory_or_native(tmp_path, monkeypatch, plan):
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: pytest.fail('budget called native'))
    root = tmp_path/'budget_non_authoritative'
    with pytest.raises(ValueError, match='reservation budget'):
        episode(root, plan=plan)
    assert not root.exists()


def test_intent_precedes_native_and_pending_never_retries(tmp_path, monkeypatch):
    root = tmp_path/'pending_non_authoritative'
    owner = episode(root)
    class ProcessStopped(BaseException):
        pass
    def stop(*args, **kwargs):
        records = events(root)
        assert len(records) == 1 and records[0][1]['kind'] == 'intent'
        raise ProcessStopped()
    monkeypatch.setattr(api.current, 'solve_current', stop)
    with pytest.raises(ProcessStopped):
        step(owner)
    head = owner.head
    assert owner.inspect().status == 'unresolved_intent'
    owner.close()
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: pytest.fail('pending intent retried'))
    owner = episode(root, create=False, expected_head=head)
    try:
        state = owner.inspect()
        assert state.completed_hours == 0 and state.reserved_solver_calls == 3
        with pytest.raises(ValueError, match='cannot retry'):
            step(owner)
    finally:
        owner.close()


def test_partial_native_failure_persists_diagnostics_and_halts(tmp_path, monkeypatch, first_result):
    root = tmp_path/'partial_non_authoritative'
    owner = episode(root)
    calls = []
    def collector(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return first_result.evidence.stages[0].native_payload
        raise RuntimeError('injected second-stage failure')
    monkeypatch.setattr(api.replay.native.capture, 'solve_once', collector)
    try:
        result, state = step(owner)
        assert state.status == 'halted' and state.completed_hours == 0
        assert result is None and len(calls) == 2
        with pytest.raises(ValueError, match='cannot retry'):
            step(owner)
        head = owner.head
    finally:
        owner.close()
    outcome = events(root)[-1][1]
    assert outcome['kind'] == 'rejected'
    assert outcome['diagnostic']['solver_calls'] is None
    assert outcome['diagnostic']['stages'][0]['accepted']
    assert outcome['diagnostic']['stages'][0]['native_payload'] == first_result.evidence.stages[0].native_payload
    owner = episode(root, create=False, expected_head=head)
    try:
        assert owner.inspect() == state
    finally:
        owner.close()


@pytest.mark.parametrize('after_commit', [False, True])
def test_outcome_commit_ambiguity_never_advances_before_readback(tmp_path, monkeypatch, first_result, after_commit):
    root = tmp_path/'outcome_non_authoritative'
    owner = episode(root)
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: first_result)
    original, calls = owner._commit, []
    def commit(connection):
        calls.append(1)
        if len(calls) == 2:
            if after_commit:
                original(connection)
            raise RuntimeError('injected outcome commit window')
        original(connection)
    monkeypatch.setattr(owner, '_commit', commit)
    with pytest.raises(RuntimeError):
        step(owner)
    with pytest.raises(ValueError, match='unresolved'):
        step(owner)
    owner.close()
    records = events(root)
    head = records[-1][0]  # Explicit read-only recovery inspection; not automatic retry.
    owner = episode(root, create=False, expected_head=head)
    try:
        status = owner.inspect()
        assert status.completed_hours == int(after_commit)
        assert status.status == ('ready' if after_commit else 'unresolved_intent')
    finally:
        owner.close()


def test_current_row_admission_and_head_failure_do_not_reserve(tmp_path, monkeypatch):
    owner = episode(tmp_path/'input_non_authoritative')
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: pytest.fail('invalid input invoked native'))
    initial = owner.inspect()
    try:
        with pytest.raises(ValueError, match='mapping'):
            step(owner, workload='1.0001')
        with pytest.raises(ValueError, match='predecessor'):
            owner.step(fixture(2).data.hourly_points[0], '0', source_time_basis='naive_source_labelled_utc', expected_head='0'*64)
        assert owner.inspect() == initial
    finally:
        owner.close()


def test_clock_gap_refused_and_next_input_never_resets_initial(tmp_path, monkeypatch, first_result):
    owner = episode(tmp_path/'clock_non_authoritative')
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: first_result)
    try:
        _, prior = step(owner)
        wrong = replace(fixture(2).data.hourly_points[1], timestamp=fixture(2).data.hourly_points[1].timestamp+timedelta(hours=1))
        with pytest.raises(ValueError, match='clock gap'):
            owner.step(wrong, '0', source_time_basis='naive_source_labelled_utc', expected_head=owner.head)
        assert owner.inspect() == prior
    finally:
        owner.close()


def test_distinct_store_types_cannot_open_or_advance_each_other(tmp_path):
    root = tmp_path/'episode_non_authoritative'
    owner = episode(root)
    head = owner.head
    with pytest.raises(TypeError):
        owner.append(None)
    assert not isinstance(owner, api.journal.DevelopmentH1ProjectionStore)
    owner.close()
    with pytest.raises((ValueError, FileNotFoundError)):
        api.journal.DevelopmentH1ProjectionStore(root, expected_head=head)
    other = tmp_path/'projection_non_authoritative'
    store = api.journal.DevelopmentH1ProjectionStore(other, create=True)
    old_head = store.head
    store.close()
    with pytest.raises((ValueError, FileNotFoundError)):
        episode(other, create=False, expected_head=old_head)


def test_numeric_observation_types_roundtrip_and_future_rows_ignored(tmp_path):
    class FuturePoison:
        def __deepcopy__(self, memo):
            raise AssertionError('future rows copied')
        def __iter__(self):
            raise AssertionError('future rows read')
    data = fixture(2).data
    network = api.source.static_network(replace(data, hourly_points=FuturePoison()))
    row = replace(data.hourly_points[0], demand_by_bus_mw={1: 20, 2: 0.})
    observation = api._observation(row, '0', 'naive_source_labelled_utc')
    restored = api._row(json.loads(api.journal._bytes(observation)))
    assert type(restored.demand_by_bus_mw[1]) is int
    assert type(restored.demand_by_bus_mw[2]) is float
    owner = api.DevelopmentH1NormalEpisode(tmp_path/'future_non_authoritative', network, spec(), budget(),
        api.H1EpisodeBudget(1, 3, 3.), dc_bus=1, create=True)
    try:
        assert owner.inspect().status == 'ready'
    finally:
        owner.close()


@pytest.mark.parametrize('phase', ['intent_noop', 'outcome_noop', 'outcome_readback'])
def test_episode_fresh_readback_is_required_before_advancement(tmp_path, monkeypatch, first_result, phase):
    root = tmp_path/'readback_non_authoritative'
    owner = episode(root)
    genesis = owner.head
    invokes, commits = [], []
    def solve(*args, **kwargs):
        invokes.append(1)
        return first_result
    monkeypatch.setattr(api.current, 'solve_current', solve)
    original_commit, original_rows = owner._commit, owner._rows
    def commit(connection):
        commits.append(1)
        if phase == 'intent_noop' and len(commits) == 1:
            return
        if phase == 'outcome_noop' and len(commits) == 2:
            return
        original_commit(connection)
    def rows(connection):
        if phase == 'outcome_readback' and len(commits) == 2:
            raise RuntimeError('injected fresh readback failure')
        return original_rows(connection)
    monkeypatch.setattr(owner, '_commit', commit)
    monkeypatch.setattr(owner, '_rows', rows)
    with pytest.raises((ValueError, RuntimeError)):
        step(owner)
    assert len(invokes) == (0 if phase == 'intent_noop' else 1)
    with pytest.raises(ValueError, match='unresolved'):
        step(owner)
    owner.close()
    records = events(root)
    expected_count = {'intent_noop':0,'outcome_noop':1,'outcome_readback':2}[phase]
    assert len(records) == expected_count
    head = records[-1][0] if records else genesis
    reopened = episode(root, create=False, expected_head=head)
    try:
        status = reopened.inspect()
        assert status.completed_hours == int(phase == 'outcome_readback')
        assert status.status == ('unresolved_intent' if phase == 'outcome_noop' else 'ready')
    finally:
        reopened.close()


def test_self_consistent_hashes_cannot_replace_exact_predecessor_semantics(tmp_path, monkeypatch, first_result):
    root = tmp_path/'semantic_non_authoritative'
    owner = episode(root)
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: first_result)
    step(owner)
    owner.close()
    db = sqlite3.connect(root/'h1_normal_episode.sqlite3')
    try:
        rows = db.execute('SELECT seq,predecessor,request_key,archive_sha256,archive,head FROM events ORDER BY seq').fetchall()
        previous = rows[0][1]
        for seq, _, key, _, raw, _ in rows:
            item = api._decode_event(raw)
            if seq == 1:
                item['before_identity'] = '0'*64
            else:
                item['intent_head'] = previous
            raw = api._encode_event(item)
            pin = sha256(raw).hexdigest()
            head = api._head(seq, previous, key, pin)
            db.execute('UPDATE events SET predecessor=?, archive_sha256=?, archive=?, head=? WHERE seq=?',
                       (previous, pin, raw, head, seq))
            previous = head
        db.commit()
    finally:
        db.close()
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: pytest.fail('tampered prefix invoked native'))
    with pytest.raises(ValueError, match='predecessor/source/request'):
        episode(root, create=False, expected_head=previous)


def test_archive_failure_never_returns_accepted_decision(tmp_path, monkeypatch, first_result):
    root = tmp_path/'archive_failure_non_authoritative'
    owner = episode(root)
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: first_result)
    def fail(*a, **k):
        raise ValueError('archive refused')
    monkeypatch.setattr(api.replay, 'archive_current', fail)
    result, state = step(owner)
    assert result is None and state.status == 'halted' and state.completed_hours == 0
    record = events(root)[-1][1]
    assert record['kind'] == 'exception'
    assert record['diagnostic']['returned_result']['stages'][0]['native_payload'] == first_result.evidence.stages[0].native_payload
    head = owner.head
    owner.close()
    owner = episode(root, create=False, expected_head=head)
    try:
        assert owner.inspect() == state
    finally:
        owner.close()


@pytest.mark.parametrize('mode', ['long', 'surrogate', 'unprintable', 'wrong_result'])
def test_exception_channel_is_bounded_and_cannot_return_decision(tmp_path, monkeypatch, mode):
    root = tmp_path/'exception_non_authoritative'
    owner = episode(root)
    class Unprintable(Exception):
        def __str__(self):
            raise RuntimeError('cannot stringify')
    def fail(*a, **k):
        if mode == 'wrong_result':
            return object()
        if mode == 'unprintable':
            raise Unprintable()
        raise RuntimeError('x'*1000000 if mode == 'long' else '\ud800')
    monkeypatch.setattr(api.current, 'solve_current', fail)
    result, state = step(owner)
    assert result is None and state.completed_hours == 0 and state.status == 'halted'
    record = events(root)[-1][1]
    description = record['diagnostic']['exception']
    assert len(bytes.fromhex(description['message']['prefix_hex'])) <= api.TEXT_PREFIX_BYTES
    assert description['rendered'] is (mode != 'unprintable')
    assert description['message']['complete'] is (mode != 'long')
    head = owner.head
    owner.close()
    owner = episode(root, create=False, expected_head=head)
    owner.close()


def test_restore_checks_drift_after_semantic_replay(tmp_path, monkeypatch, first_result):
    owner = episode(tmp_path/'drift_non_authoritative')
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: first_result)
    step(owner)
    original = api.replay.replay_archive
    def drift(*a, **k):
        result = original(*a, **k)
        monkeypatch.setattr(owner, '_header_bytes', lambda: b'drift')
        return result
    monkeypatch.setattr(api.replay, 'replay_archive', drift)
    try:
        with pytest.raises(ValueError):
            owner.inspect()
    finally:
        owner.close()


def test_binary_frame_capacity_and_tamper_boundaries(tmp_path):
    owner = episode(tmp_path/'bytes_non_authoritative')
    try:
        # Native reports containing quotes/backslashes do not expand in framing.
        raw = b'\\"'*(api.replay.native.MAX_PAYLOAD_BYTES//2)
        item = dict(z=[raw]*owner._stages, a=b'first')
        encoded = api._encode_event(item)
        assert len(encoded) <= owner._event_bytes
        assert api._decode_event(encoded) == item
        assert owner._journal_bytes >= (owner._episode_budget.planned_hours*api.replay.MAX_ARCHIVE_BYTES
            + owner._episode_budget.max_reserved_solver_calls*api.replay.native.MAX_PAYLOAD_BYTES
            + owner._limit*owner._frame_overhead)
        for corrupt in (encoded[:-1], encoded+b'extra', encoded[:-1]+b'!'):
            with pytest.raises(ValueError):
                api._decode_event(corrupt)
        with pytest.raises(ValueError, match='metadata'):
            api._encode_event(dict(value='x'*api.MAX_METADATA_BYTES))
        assert api._head(1, 'a', 'b', 'c') != api.journal._head(1, 'a', 'b', 'c')
    finally:
        owner.close()


@pytest.mark.parametrize('field', ['request_key','chain_identity','formal_result','stages'])
def test_failure_summary_binding_rejects_structural_tamper(first_result, field):
    result = api._failure(first_result, first_result.request_key, first_result.evidence.chain_identity, 3)
    result[field] = [] if field == 'stages' else True if field == 'formal_result' else '0'*64
    if field == 'stages':
        result[field] = [dict(index=1)]
    with pytest.raises(ValueError):
        api._validate_failure(result, first_result.request_key, first_result.evidence.chain_identity, 3)


def test_final_restore_failure_poison_requires_explicit_reopen(tmp_path, monkeypatch, first_result):
    root = tmp_path/'final_restore_non_authoritative'
    owner = episode(root)
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: first_result)
    original = owner._restore
    restores = []
    def restore():
        restores.append(1)
        if len(restores) == 3:
            raise RuntimeError('final restore failed after commit')
        return original()
    monkeypatch.setattr(owner, '_restore', restore)
    with pytest.raises(RuntimeError):
        step(owner)
    assert events(root)[-1][1]['kind'] == 'accepted'
    for retry in (owner.inspect, lambda: step(owner, 1)):
        with pytest.raises(ValueError, match='unresolved'):
            retry()
    owner.close()
    head = events(root)[-1][0]
    owner = episode(root, create=False, expected_head=head)
    try:
        assert owner.inspect().completed_hours == 1
    finally:
        owner.close()


def test_inspection_failure_poison_is_sticky(tmp_path, monkeypatch):
    owner = episode(tmp_path/'inspect_failure_non_authoritative')
    original = owner._restore
    def fail():
        raise ValueError('injected read failure')
    monkeypatch.setattr(owner, '_restore', fail)
    with pytest.raises(ValueError):
        owner.inspect()
    monkeypatch.setattr(owner, '_restore', original)
    try:
        with pytest.raises(ValueError, match='unresolved'):
            owner.inspect()
    finally:
        owner.close()


@pytest.mark.parametrize('change', ['missing','index','length','hash'])
def test_binary_descriptors_reject_missing_order_length_and_hash(change):
    raw = api._encode_event(dict(a=b'first', b=b'second'))
    start = len(api.FRAME)+8
    size = int.from_bytes(raw[len(api.FRAME):start], 'big')
    metadata = json.loads(raw[start:start+size])
    if change == 'missing':
        del metadata['a']
    elif change == 'index':
        metadata['a']['blob'] = 1
    elif change == 'length':
        metadata['a']['length'] += 1
    else:
        metadata['a']['sha256'] = '0'*64
    encoded = api.journal._bytes(metadata)
    corrupt = api.FRAME+len(encoded).to_bytes(8,'big')+encoded+raw[start+size:]
    with pytest.raises(ValueError):
        api._decode_event(corrupt)


def test_rejected_cannot_claim_accepted_decision(tmp_path, monkeypatch, first_result):
    root = tmp_path/'rejected_tamper_non_authoritative'
    owner = episode(root)
    monkeypatch.setattr(api.current, 'solve_current', lambda *a, **k: first_result)
    step(owner)
    owner.close()
    db = sqlite3.connect(root/'h1_normal_episode.sqlite3')
    try:
        seq, previous, key, _, raw, _ = db.execute('SELECT * FROM events WHERE seq=2').fetchone()
        item = api._decode_event(raw)
        item.pop('archive')
        item.pop('archive_sha256')
        item['kind'] = 'rejected'
        item['diagnostic'] = api._failure(first_result, key, first_result.evidence.chain_identity, 3)
        payload = api._encode_event(item)
        pin = sha256(payload).hexdigest()
        head = api._head(seq, previous, key, pin)
        db.execute('UPDATE events SET archive_sha256=?,archive=?,head=? WHERE seq=2', (pin,payload,head))
        db.commit()
    finally:
        db.close()
    with pytest.raises(ValueError, match='claims accepted'):
        episode(root, create=False, expected_head=head)
