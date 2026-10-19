"""Opaque stream capture and the existing independent numerical replayer."""
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from test_rq2_normal_declared_store_stream_v1 import supplied, prepared_source, bound_source, source_supplied, open_store, LIMIT
from test_rq2_normal_declared_replay_stream_v1 import no_solver, arguments as replay_arguments
from src.rq2_joint_deliverability_boundary_v1 import normal_archive_capture_stream as api
from src.rq2_joint_deliverability_boundary_v1 import normal_declared_replay_stream as replay


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='local NTFS archive')


def test_capture_never_prepares_or_builds_annual_inputs(tmp_path,supplied,monkeypatch):
    root,observed,intent=empty(tmp_path,supplied)
    insert(root,intent,b'opaque result')
    arguments=request(root,supplied,observed,claimed_result_identity='a'*64)
    def forbidden(*a,**k):raise AssertionError('capture entered source/model/solver')
    monkeypatch.setattr(api.journal.execution.prepare,'prepare_task_inputs',forbidden)
    monkeypatch.setattr(api.journal.execution.kernel,'normal_input_identity',forbidden)
    monkeypatch.setattr(api.journal.execution.kernel.streaming,'build_continuous_normal_model',forbidden)
    monkeypatch.setattr(api.journal.execution.kernel.native,'create_solver',forbidden)
    result=api.capture_normal_archive(root,**arguments)
    assert result.status=='opaque_record_captured' and not result.result_identity_verified


def test_old_capture_cannot_read_new_schema(tmp_path,supplied):
    root,observed,_=empty(tmp_path,supplied)
    old=api.legacy
    args=dict(budget=old.ArchiveCaptureBudget(32*1024**2,LIMIT,10.),
        expected_store_identity=observed.store_identity,
        expected_source_execution_identity=supplied[1]['expected_source_execution_identity'],
        claimed_result_identity=None)
    with pytest.raises(ValueError,match='schema mismatch'):
        old.capture_normal_archive(root,expected_capture_identity=old.capture_identity(root,**args),**args)


@pytest.mark.parametrize('pending',[False,True])
def test_wrong_declared_intent_pin_is_rejected(tmp_path,supplied,pending):
    root,observed,intent=empty(tmp_path,supplied)
    if pending:insert(root,intent)
    with pytest.raises(ValueError):
        api.capture_normal_archive(root,**request(root,supplied,observed,expected_declared_execution_identity='0'*64))


def test_new_capture_cannot_read_old_schema(tmp_path,supplied,monkeypatch):
    from test_rq2_source_normal_execution_v1 import supplied as old_supplied
    from test_rq2_normal_store_v1 import open_store as old_open
    old_case=old_supplied.__wrapped__(monkeypatch)
    root=tmp_path/'old_journal_non_authoritative'
    with old_open(root,old_case) as store:observed=store.inspect()
    with pytest.raises(ValueError,match='schema mismatch'):
        api.capture_normal_archive(root,**request(root,supplied,observed))


def request(root, supplied, observed, **changes):
    kw = dict(budget=api.ArchiveCaptureBudget(32*1024**2, LIMIT, 10.),
        expected_store_identity=observed.store_identity,
        expected_declared_execution_identity=supplied[1]['expected_declared_execution_identity'],
        claimed_result_identity=observed.result_identity)
    kw.update(changes)
    return dict(**kw, expected_capture_identity=api.capture_identity(root, **kw))


def empty(tmp_path, supplied):
    root = tmp_path/'capture_non_authoritative'
    with open_store(root, supplied) as store:
        observed = store.inspect()
        intent = store._intent
    return root, observed, intent


def insert(root, intent, raw=None):
    with sqlite3.connect(root/'normal.sqlite3') as con:
        con.execute('INSERT INTO intent VALUES(1, ?)', (intent,))
        if raw is not None:
            con.execute('INSERT INTO result VALUES(1, ?, ?)', (raw, sha256(raw).hexdigest()))


def test_capture_then_original_replay_verifies_claim(tmp_path, supplied, monkeypatch):
    root = tmp_path/'real_record_non_authoritative'
    with open_store(root, supplied) as store:
        _, observed = store.execute()
    no_solver(monkeypatch)
    before = (root/'normal.sqlite3').read_bytes()
    before_mtime = (root/'normal.sqlite3').stat().st_mtime_ns
    captured = api.capture_normal_archive(root, **request(root, supplied, observed))
    assert captured.status == 'opaque_record_captured'
    assert captured.head == observed.head
    assert captured.record_sha256 == observed.archived_result_sha256
    assert captured.claimed_result_identity == observed.result_identity
    assert not any((captured.result_identity_verified, captured.numerical_evidence_replayed,
        captured.native_execution_authenticated, captured.whole_job_quiescence_verified, captured.formal_result))
    kw = replay_arguments(supplied, observed)
    kw.pop('expected_store_identity')
    kw.update(expected_record_sha256=captured.record_sha256,
        expected_result_identity=captured.claimed_result_identity)
    result = replay.replay_normal_store(root, supplied[0],
        expected_head=captured.head, **kw)
    assert result.accepted_record_reproduced and result.solver_calls_by_replay == 0
    assert (root/'normal.sqlite3').read_bytes() == before
    assert (root/'normal.sqlite3').stat().st_mtime_ns == before_mtime
    wrong_claim = api.capture_normal_archive(root, **request(root, supplied, observed,
        claimed_result_identity='a'*64))
    assert not wrong_claim.result_identity_verified
    kw['expected_result_identity'] = wrong_claim.claimed_result_identity
    with pytest.raises(ValueError, match='current normal head'):
        replay.replay_normal_store(root, supplied[0],
            expected_head=wrong_claim.head, **kw)


@pytest.mark.parametrize('pending', [False, True])
def test_empty_and_pending_preserve_unknown_state(tmp_path, supplied, pending):
    root, observed, intent = empty(tmp_path, supplied)
    if pending: insert(root, intent)
    captured = api.capture_normal_archive(root, **request(root, supplied, observed))
    assert captured.status == ('unresolved_intent' if pending else 'unused')
    assert captured.head == observed.genesis and captured.record_sha256 is None
    assert captured.record_bytes == 0 and captured.intent_present == pending


def test_streaming_does_not_decode_opaque_payload_or_validate_claim(tmp_path, supplied, monkeypatch):
    root, observed, intent = empty(tmp_path, supplied)
    raw = b'x'*(2*1024**2+7)  # Deliberately not a valid normal numerical record.
    insert(root, intent, raw)
    kw = request(root, supplied, observed, claimed_result_identity='a'*64)
    original = api.sqlite3.connect
    reads = []
    class Blob:
        def __init__(self, inner): self.inner = inner
        def __len__(self): return len(self.inner)
        def __enter__(self): return self
        def __exit__(self, *args): self.inner.close()
        def read(self, size):
            reads.append(size)
            assert 0 < size <= api.CHUNK_BYTES
            return self.inner.read(size)
    class Connection(sqlite3.Connection):
        def execute(self, sql, *args):
            assert sql != 'SELECT payload FROM result'
            return super().execute(sql, *args)
        def blobopen(self, *args, **kwargs): return Blob(super().blobopen(*args, **kwargs))
    monkeypatch.setattr(api.sqlite3, 'connect', lambda *a, **k: original(*a, **k, factory=Connection))
    result = api.capture_normal_archive(root, **kw)
    assert len(reads) > 32 and result.record_bytes == len(raw)
    assert result.record_sha256 == sha256(raw).hexdigest()
    assert result.claimed_result_identity == 'a'*64 and not result.result_identity_verified
    kw_replay = replay_arguments(supplied, observed)
    kw_replay.update(expected_record_sha256=result.record_sha256, expected_result_identity='a'*64)
    with pytest.raises(ValueError):
        replay.replay_normal_record(raw, supplied[0], **kw_replay)


@pytest.mark.parametrize('fault', ['digest', 'intent', 'extra_table', 'header', 'oversize_record',
    'missing_claim', 'claim_without_record', 'oversize_database', 'sidecar', 'wal', 'shm',
    'index', 'trigger', 'hardlink', 'copied_root'])
def test_corrupt_or_unbounded_archive_refused(tmp_path, supplied, fault):
    root, observed, intent = empty(tmp_path, supplied)
    has_record = fault != 'claim_without_record'
    insert(root, intent, b'opaque' if has_record else None)
    kw = request(root, supplied, observed, claimed_result_identity='a'*64)
    with sqlite3.connect(root/'normal.sqlite3') as con:
        if fault == 'digest': con.execute("UPDATE result SET digest=?", ('0'*64,))
        if fault == 'intent': con.execute("UPDATE intent SET payload=?", (b'wrong',))
        if fault == 'extra_table': con.execute('CREATE TABLE extra(x)')
        if fault == 'index': con.execute('CREATE INDEX extra ON result(digest)')
        if fault == 'trigger': con.execute('CREATE TRIGGER extra AFTER INSERT ON result BEGIN SELECT 1; END')
        if fault == 'header': con.execute('UPDATE metadata SET header=?', (b'{}',))
        if fault == 'oversize_record':
            con.execute('UPDATE result SET payload=zeroblob(?)', (LIMIT+1,))
    if fault == 'missing_claim': kw = request(root, supplied, observed)
    if fault == 'oversize_database':
        kw = request(root, supplied, observed, claimed_result_identity='a'*64,
            budget=api.ArchiveCaptureBudget(1, 1, 10.))
    if fault == 'sidecar': Path(str(root/'normal.sqlite3')+'-journal').write_bytes(b'pending')
    if fault in ('wal', 'shm'): Path(str(root/'normal.sqlite3')+'-'+fault).write_bytes(b'pending')
    if fault == 'hardlink': os.link(root/'normal.sqlite3', tmp_path/'linked.sqlite3')
    if fault == 'copied_root':
        target = tmp_path/'copied_non_authoritative'
        shutil.copytree(root, target)
        root = target
        kw = request(root, supplied, observed, claimed_result_identity='a'*64)
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        api.capture_normal_archive(root, **kw)


def test_existing_lease_refused_and_capture_releases_on_interrupt(tmp_path, supplied, monkeypatch):
    root, observed, _ = empty(tmp_path, supplied)
    kw = request(root, supplied, observed)
    with open_store(root, supplied, create=False, expected_head=observed.head):
        with pytest.raises(ValueError, match='already held'):
            api.capture_normal_archive(root, **kw)
    original = api.journal._decoded
    def fail(raw): raise KeyboardInterrupt('during capture')
    monkeypatch.setattr(api.journal, '_decoded', fail)
    with pytest.raises(KeyboardInterrupt): api.capture_normal_archive(root, **kw)
    monkeypatch.setattr(api.journal, '_decoded', original)
    assert api.capture_normal_archive(root, **kw).status == 'unused'


def test_deadline_and_implementation_drift_refused(tmp_path, supplied, monkeypatch):
    root, observed, _ = empty(tmp_path, supplied)
    kw = request(root, supplied, observed)
    ticks = iter([0., 11.])
    monkeypatch.setattr(api.time, 'monotonic', lambda: next(ticks))
    with pytest.raises(TimeoutError): api.capture_normal_archive(root, **kw)
    monkeypatch.undo()
    original = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda p:
        original(p)+(b'drift' if p.resolve() == Path(api.journal.__file__).resolve() else b''))
    with pytest.raises(ValueError, match='implementation mismatch'):
        api.capture_normal_archive(root, **kw)


@pytest.mark.parametrize('changes', [dict(max_database_bytes=True), dict(max_record_bytes=0),
    dict(max_elapsed_seconds=float('nan')), dict(max_elapsed_seconds=61)])
def test_invalid_budgets(changes):
    with pytest.raises(ValueError): replace(api.ArchiveCaptureBudget(LIMIT, LIMIT, 5.), **changes)


@pytest.mark.parametrize('fault', ['stream_deadline', 'sql_deadline', 'file_changed', 'source_changed'])
def test_mid_capture_failures_release_lease_without_pins(tmp_path, supplied, monkeypatch, fault):
    root, observed, intent = empty(tmp_path, supplied)
    insert(root, intent, b'x'*(2*api.CHUNK_BYTES+1))
    kw = request(root, supplied, observed, claimed_result_identity='a'*64)
    original = api.sqlite3.connect
    clock = [0.]
    monkeypatch.setattr(api.time, 'monotonic', lambda: clock[0])
    class Blob:
        def __init__(self, inner): self.inner = inner
        def __len__(self): return len(self.inner)
        def __enter__(self): return self
        def __exit__(self, *args): self.inner.close()
        def read(self, size):
            result = self.inner.read(size)
            if fault == 'stream_deadline': clock[0] = 11.
            if fault == 'file_changed':
                st = (root/'normal.sqlite3').stat()
                os.utime(root/'normal.sqlite3', ns=(st.st_atime_ns, st.st_mtime_ns+1000000))
            if fault == 'source_changed':
                old = Path.read_bytes
                monkeypatch.setattr(Path, 'read_bytes', lambda path:
                    old(path)+(b'drift' if path.resolve() == Path(api.__file__).resolve() else b''))
            return result
    class Connection(sqlite3.Connection):
        def execute(self, sql, *args):
            if fault == 'sql_deadline' and sql == 'PRAGMA integrity_check(1)':
                clock[0] = 11.
                # Deterministic long SQL scan exercises the actual progress callback.
                return super().execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL '
                    'SELECT x+1 FROM n WHERE x<100000) SELECT sum(x) FROM n')
            return super().execute(sql, *args)
        def blobopen(self, table, *args, **kwargs):
            inner = super().blobopen(table, *args, **kwargs)
            return Blob(inner) if table == 'result' else inner
    monkeypatch.setattr(api.sqlite3, 'connect', lambda *a, **k: original(*a, **k, factory=Connection))
    if fault == 'sql_deadline':
        with pytest.raises(sqlite3.OperationalError, match='interrupted'):
            api.capture_normal_archive(root, **kw)
    else:
        with pytest.raises((ValueError, TimeoutError)):
            api.capture_normal_archive(root, **kw)
    monkeypatch.undo()
    # Even after the exceptional read, a fresh cooperative reader can acquire the root.
    assert api.capture_normal_archive(root, **kw).status == 'opaque_record_captured'


def test_oversize_lock_refused_before_old_lease_read(tmp_path, supplied, monkeypatch):
    root, observed, _ = empty(tmp_path, supplied)
    kw = request(root, supplied, observed)
    (root/'execution.lock').write_bytes(b'0'*100)
    def forbidden(*args, **kwargs): raise AssertionError('unbounded lease read reached')
    monkeypatch.setattr(api.journal.local._Lease, '__init__', forbidden)
    with pytest.raises(ValueError, match='one-byte'):
        api.capture_normal_archive(root, **kw)


def test_broken_sidecar_path_checked_by_local_path_layer(tmp_path, supplied, monkeypatch):
    root, observed, _ = empty(tmp_path, supplied)
    kw = request(root, supplied, observed)
    original = api.journal.local._path
    target = str(root/'normal.sqlite3')+'-journal'
    def broken(path):
        if str(path) == target:
            raise ValueError('reparse paths are not supported by the local store')
        return original(path)
    monkeypatch.setattr(api.journal.local, '_path', broken)
    with pytest.raises(ValueError, match='reparse'):
        api.capture_normal_archive(root, **kw)
