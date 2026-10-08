from copy import deepcopy
from hashlib import sha256
import sqlite3

import pytest

from tests.test_rq2_normal_h1_source_v1 import packet, run
from tests.test_rq2_normal_h1_short_solve_v1 import budget
from tests.test_rq2_objective_provenance_run_v1 import spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_projection_store as api


@pytest.fixture(scope='module')
def case():
    p = packet()
    result = run(p)
    raw = api.replay.archive_current(p, spec(), budget(), result)
    return p, result.request_key, raw, sha256(raw).hexdigest()


@pytest.fixture(autouse=True)
def no_solver(monkeypatch, case):
    def forbidden(*args, **kwargs):
        pytest.fail('projection journal entered native solver')
    monkeypatch.setattr(api.replay.native.capture, 'solve_once', forbidden)
    monkeypatch.setattr(api.replay.native.capture.provenance.adapter, 'create_solver', forbidden)


def append(store, case):
    p, key, raw, pin = case
    return store.append(p, spec(), budget(), raw, expected_key=key, expected_archive_sha256=pin)


def inspect(store, case):
    p, key, _, _ = case
    return store.inspect(p, spec(), budget(), expected_key=key)


def test_append_reopen_idempotence_and_no_executable_cursor(tmp_path, case):
    root = tmp_path/'store_non_authoritative'
    store = api.DevelopmentH1ProjectionStore(root, create=True)
    genesis = store.head
    try:
        assert inspect(store, case).status == 'absent'
        first = append(store, case)
        assert first.status == 'available' and first.witness_count == 1
        assert first.head != genesis
        assert not first.native_execution_authenticated and not first.formal_result
        assert not first.executable_boundary_restored
        assert append(store, case) == first
        head = store.head
    finally:
        store.close()

    store = api.DevelopmentH1ProjectionStore(root, expected_head=head)
    try:
        assert inspect(store, case) == first
    finally:
        store.close()
    with pytest.raises(ValueError, match='retained'):
        api.DevelopmentH1ProjectionStore(root, expected_head=genesis)


def test_root_exclusion_and_old_types_rejected(tmp_path, case):
    root = tmp_path/'held_non_authoritative'
    store = api.DevelopmentH1ProjectionStore(root, create=True)
    try:
        with pytest.raises(ValueError, match='already held'):
            api.DevelopmentH1ProjectionStore(root, expected_head=store.head)
        with pytest.raises(TypeError):
            deepcopy(store)
        with pytest.raises(ValueError):
            store.inspect(object(), spec(), budget(), expected_key=case[1])
        assert inspect(store, case).status == 'absent'
    finally:
        store.close()


@pytest.mark.parametrize('after_commit', [False, True])
def test_commit_failure_preserves_atomic_record_and_blocks_retry(tmp_path, monkeypatch, case, after_commit):
    root = tmp_path/'fault_non_authoritative'
    store = api.DevelopmentH1ProjectionStore(root, create=True)
    before = store.head
    expected_after = api._head(1, before, case[1], case[3])
    original = store._commit
    def fail(connection):
        if after_commit:
            original(connection)
        raise RuntimeError('injected commit window')
    monkeypatch.setattr(store, '_commit', fail)
    with pytest.raises(RuntimeError, match='commit window'):
        append(store, case)
    with pytest.raises(ValueError, match='unresolved'):
        append(store, case)
    store.close()
    if after_commit:
        with pytest.raises(ValueError, match='retained'):
            api.DevelopmentH1ProjectionStore(root, expected_head=before)
    # The caller independently computes the exact attempted append head.
    resumed = api.DevelopmentH1ProjectionStore(root, expected_head=expected_after if after_commit else before)
    try:
        assert inspect(resumed, case).status == ('available' if after_commit else 'absent')
    finally:
        resumed.close()


def test_corrupted_archive_or_truncated_history_cannot_resume(tmp_path, case):
    root = tmp_path/'corrupt_non_authoritative'
    store = api.DevelopmentH1ProjectionStore(root, create=True)
    append(store, case)
    head = store.head
    store.close()
    db = sqlite3.connect(root/'h1_projections.sqlite3')
    try:
        db.execute('UPDATE records SET archive=? WHERE seq=1', (b'{}',))
        db.commit()
    finally:
        db.close()
    with pytest.raises(ValueError, match='hash mismatch'):
        api.DevelopmentH1ProjectionStore(root, expected_head=head)


def test_conflict_is_sticky_and_never_overwrites_prior_projection(tmp_path, monkeypatch, case):
    # Isolate the journal's conflict rule with a second independently-approved
    # validator output. Full numerical archive tamper rejection is tested in
    # test_rq2_normal_h1_replay_v1, not bypassed in the production store.
    p, key, _, _ = case
    original = api.replay.replay_archive
    projection = original(p, spec(), budget(), case[2], expected_key=key, expected_archive_sha256=case[3])
    alternate = deepcopy(projection)
    object.__setattr__(alternate, 'projection_identity', 'f'*64)
    object.__setattr__(alternate, 'projection_payload', b'{"fault_injected_projection":true}')
    raw = b'fault_injected_validator_input'
    def validator(packet, specification, bound, archive, **kwargs):
        return alternate if archive == raw else original(packet, specification, bound, archive, **kwargs)
    monkeypatch.setattr(api.replay, 'replay_archive', validator)
    root = tmp_path/'conflict_non_authoritative'
    store = api.DevelopmentH1ProjectionStore(root, create=True)
    try:
        first = append(store, case)
        conflict = store.append(p, spec(), budget(), raw, expected_key=key,
                                expected_archive_sha256=sha256(raw).hexdigest())
        assert conflict.status == 'unresolved_conflict' and conflict.witness_count == 2
        assert conflict.projection_payload is None and conflict.projection_identity is None
        assert append(store, case).status == 'unresolved_conflict'
        assert inspect(store, case).status == 'unresolved_conflict'
        db = sqlite3.connect(root/'h1_projections.sqlite3')
        try:
            assert db.execute('SELECT archive FROM records WHERE seq=1').fetchone()[0] == case[2]
        finally:
            db.close()
        assert store.head != first.head
        head = store.head
    finally:
        store.close()
    store = api.DevelopmentH1ProjectionStore(root, expected_head=head)
    try:
        assert inspect(store, case).status == 'unresolved_conflict'
    finally:
        store.close()


@pytest.mark.parametrize('flag', ['published', 'native_execution_authenticated', 'formal_result'])
def test_validator_authority_drift_rejected_before_append(tmp_path, monkeypatch, case, flag):
    p, key, raw, pin = case
    value = api.replay.replay_archive(p, spec(), budget(), raw, expected_key=key, expected_archive_sha256=pin)
    object.__setattr__(value, flag, True)
    store = api.DevelopmentH1ProjectionStore(tmp_path/'authority_non_authoritative', create=True)
    before = store.head
    monkeypatch.setattr(api.replay, 'replay_archive', lambda *a, **k: value)
    try:
        with pytest.raises(ValueError, match='authority drift'):
            append(store, case)
        assert store.head == before
        assert inspect(store, case).status == 'absent'
    finally:
        store.close()


@pytest.mark.parametrize('kind', ['commit_noop', 'readback_failure'])
def test_commit_readback_required_before_success(tmp_path, monkeypatch, case, kind):
    root = tmp_path/'readback_non_authoritative'
    store = api.DevelopmentH1ProjectionStore(root, create=True)
    before = store.head
    expected_after = api._head(1, before, case[1], case[3])
    if kind == 'commit_noop':
        monkeypatch.setattr(store, '_commit', lambda connection: None)
    else:
        original, calls = store._rows, []
        def fail(connection):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('injected readback failure')
            return original(connection)
        monkeypatch.setattr(store, '_rows', fail)
    with pytest.raises((ValueError, RuntimeError)):
        append(store, case)
    with pytest.raises(ValueError, match='unresolved'):
        append(store, case)
    store.close()
    reopened = api.DevelopmentH1ProjectionStore(root,
        expected_head=before if kind == 'commit_noop' else expected_after)
    try:
        assert inspect(reopened, case).status == ('absent' if kind == 'commit_noop' else 'available')
    finally:
        reopened.close()
