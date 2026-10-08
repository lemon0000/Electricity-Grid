from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

from test_rq2_episode_replay_v1 import CONFIG, origins, hour
from test_rq2_hourly_transaction_v1 import normal_source, view, current
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import disclose_current, CurrentOutageReport
from src.rq2_joint_deliverability_boundary_v1 import episode_store as store
from src.rq2_joint_deliverability_boundary_v1 import episode_coordinator as ep


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='local NTFS contract')


def supplied():
    inputs, common, arms = origins()
    first = hour(*inputs[:2], common)
    _, prepared = normal_source()
    info = view(prepared, replace(current(2, demand=20.), dc_baseline_mw=25.,
        dc_connected_capacity_mw=25., dc_physical_maximum_mw=30.))
    disclosure = disclose_current(inputs[1].after, CurrentOutageReport(2, None, None))
    return common, arms, (first, hour(info, disclosure, common))


@pytest.fixture(scope='module')
def snapshots():
    common, arms, hours = supplied()
    session = ep.EpisodeSession(common, arms, **CONFIG)
    rows = []
    for h in hours:
        rows.append(session.advance(h.info, h.disclosure, h.source_hour, h.source_audit,
            limits=h.limits, due_hour=h.due_hour, available_flexibility=h.available_flexibility))
    return tuple(rows)


def cached(monkeypatch, snapshots):
    calls = []
    def advance(session, info, disclosure, source_hour, source_audit, **kw):
        index = len(session.snapshot.attempts)
        expected = snapshots[index].attempts[-1]
        assert expected.before_identity == session.snapshot.identity
        assert expected.hour_input.info == info and expected.hour_input.source_hour == source_hour
        calls.append(index)
        session._snapshot = snapshots[index]
        return session.snapshot
    monkeypatch.setattr(ep.EpisodeSession, 'advance', advance)
    return calls


def test_real_create_then_reopen_and_advance(tmp_path):
    root = tmp_path/'real_non_authoritative'
    inputs = supplied()
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        first = owner.advance()
        assert first.completed_attempts == 1 and first.development_continuation_available
    with store.DevelopmentEpisodeStore(root, *inputs, expected_head=first.head, **CONFIG) as resumed:
        final = resumed.advance()
        assert final.status == 'observation_window_complete'
        assert final.archive_reproduced and not final.development_continuation_available
        assert not final.formal_run_authorized
        with pytest.raises(ValueError): resumed.advance()


def test_duplicate_owner_and_stale_head_are_rejected(tmp_path, monkeypatch, snapshots):
    calls = cached(monkeypatch, snapshots)
    root = tmp_path/'single_non_authoritative'
    inputs = supplied()
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        initial = owner.inspection.head
        with pytest.raises(ValueError, match='already held'):
            store.DevelopmentEpisodeStore(root, *inputs, expected_head=initial, **CONFIG)
        latest = owner.advance()
    with pytest.raises(ValueError, match='head mismatch'):
        store.DevelopmentEpisodeStore(root, *inputs, expected_head=initial, **CONFIG)
    assert calls == [0]
    assert store.inspect_episode_store(root, *inputs, **CONFIG).head == latest.head


@pytest.mark.parametrize('window', ['intent_before', 'intent_after', 'result_before', 'result_after'])
def test_commit_exception_never_retries_invocation(tmp_path, monkeypatch, snapshots, window):
    calls = cached(monkeypatch, snapshots)
    root = tmp_path/(window+'_non_authoritative')
    inputs = supplied()
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        original = owner._append
        def failed(intent, seq, head, archive=None):
            relevant = (archive is None) == window.startswith('intent')
            if relevant and window.endswith('before'): raise OSError('commit failed before write')
            original(intent, seq, head, archive)
            if relevant: raise OSError('commit response lost')
        monkeypatch.setattr(owner, '_append', failed)
        with pytest.raises(OSError): owner.advance()
        with pytest.raises(ValueError, match='indeterminate'): owner.advance()
    report = store.inspect_episode_store(root, *inputs, **CONFIG)
    assert len(calls) == (1 if window.startswith('result') else 0)
    assert report.pending_intent == (window in ('intent_after', 'result_before'))
    if report.pending_intent:
        with pytest.raises(ValueError, match='unresolved'):
            store.DevelopmentEpisodeStore(root, *inputs, expected_head=report.head, **CONFIG)
    else:
        with store.DevelopmentEpisodeStore(root, *inputs, expected_head=report.head, **CONFIG) as recovered:
            assert recovered.inspection.development_continuation_available


@pytest.mark.parametrize('mutation', ['schema', 'input', 'root', 'head', 'intent', 'archive', 'gap'])
def test_journal_tampering_and_wrong_sources(tmp_path, monkeypatch, snapshots, mutation):
    cached(monkeypatch, snapshots)
    root = tmp_path/'original_non_authoritative'
    inputs = supplied()
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        receipt = owner.advance()
    if mutation == 'input':
        h = inputs[2][0]
        changed = store.tx._owned(ep.EpisodeHourInput, **dict(vars(h), due_hour=6))
        inputs = inputs[:2]+((changed, inputs[2][1]),)
    elif mutation == 'root':
        destination = tmp_path/'copied_non_authoritative'
        shutil.copytree(root, destination)
        root = destination
    else:
        with sqlite3.connect(root/'journal.sqlite3') as db:
            if mutation == 'schema': db.execute('CREATE TABLE extra (x TEXT)')
            elif mutation == 'head': db.execute('UPDATE results SET head=?', ('0'*64,))
            elif mutation == 'intent': db.execute('UPDATE intents SET payload=?', (b'{}\n',))
            elif mutation == 'archive': db.execute('UPDATE results SET archive=?', (b'{}\n',))
            elif mutation == 'gap': db.execute('UPDATE intents SET seq=3')
    with pytest.raises(ValueError):
        store.DevelopmentEpisodeStore(root, *inputs, expected_head=receipt.head, **CONFIG)


def test_invalid_input_is_rejected_before_intent(tmp_path, monkeypatch):
    common, arms, hours = supplied()
    bad = store.tx._owned(ep.EpisodeHourInput, **dict(vars(hours[0]), due_hour=0))
    root = tmp_path/'invalid_non_authoritative'
    with store.DevelopmentEpisodeStore(root, common, arms, (bad, hours[1]), create=True, **CONFIG) as owner:
        def forbidden(*a, **kw): raise AssertionError('no advance for invalid input')
        monkeypatch.setattr(ep.EpisodeSession, 'advance', forbidden)
        with pytest.raises(ValueError, match='deadline'): owner.advance()
        with sqlite3.connect(root/'journal.sqlite3') as db:
            assert db.execute('SELECT count(*) FROM intents').fetchone()[0] == 0


CHILD = '''
import os,sys
from pathlib import Path
from test_rq2_episode_store_v1 import supplied,CONFIG,store,ep
root=Path(sys.argv[1]); mode=sys.argv[2]
inputs=supplied()
with store.DevelopmentEpisodeStore(root,*inputs,create=True,**CONFIG) as owner:
    if mode=='before_intent': os._exit(17)
    original=owner._append
    def append(intent,seq,head,archive=None):
        original(intent,seq,head,archive)
        if archive is None and mode in ('after_intent','compete'):
            if mode=='compete':
                print('intent committed',flush=True)
                sys.stdin.readline()
            os._exit(17)
        if archive is not None and mode=='after_result': os._exit(17)
    owner._append=append
    if mode=='during_advance': ep.EpisodeSession.advance=lambda *a,**kw: os._exit(17)
    if mode=='before_result': owner._publish_result=lambda *a,**kw: os._exit(17)
    owner.advance()
raise AssertionError('crash window not reached')
'''


def child_args(root, mode):
    repo = Path(__file__).resolve().parents[1]
    return dict(args=[sys.executable, '-B', '-c', CHILD, str(root), mode], cwd=repo,
        env=dict(os.environ, PYTHONPATH=str(repo/'tests')+os.pathsep+str(repo)),
        creationflags=subprocess.CREATE_NO_WINDOW, text=True)


@pytest.mark.parametrize('window', ['before_intent', 'after_intent', 'during_advance', 'before_result', 'after_result'])
def test_subprocess_crash_windows(tmp_path, window):
    root = tmp_path/(window+'_non_authoritative')
    result = subprocess.run(**child_args(root, window), capture_output=True, timeout=90)
    assert result.returncode == 17, result.stdout+result.stderr
    inputs = supplied()
    report = store.inspect_episode_store(root, *inputs, **CONFIG)
    assert report.pending_intent == (window in ('after_intent', 'during_advance', 'before_result'))
    assert report.completed_attempts == (1 if window == 'after_result' else 0)
    if report.pending_intent:
        with pytest.raises(ValueError, match='unresolved'):
            store.DevelopmentEpisodeStore(root, *inputs, expected_head=report.head, **CONFIG)
    else:
        with store.DevelopmentEpisodeStore(root, *inputs, expected_head=report.head, **CONFIG) as owner:
            assert owner.inspection.development_continuation_available


def test_real_cross_process_exclusion_after_intent(tmp_path, monkeypatch):
    root = tmp_path/'competing_non_authoritative'
    process = subprocess.Popen(**child_args(root, 'compete'), stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert process.stdout.readline().strip() == 'intent committed'
        def forbidden(*a, **kw): raise AssertionError('competing process must not invoke')
        monkeypatch.setattr(ep.EpisodeSession, 'advance', forbidden)
        with pytest.raises((ValueError, OSError)):
            store.DevelopmentEpisodeStore(root, *supplied(), expected_head='0'*64, **CONFIG)
        process.communicate('exit\n', timeout=20)
        assert process.returncode == 17
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=20)
    assert store.inspect_episode_store(root, *supplied(), **CONFIG).pending_intent


def test_independently_valid_archive_cannot_rewrite_committed_history(tmp_path, monkeypatch, snapshots):
    cached(monkeypatch, snapshots)
    inputs = supplied()
    root = tmp_path/'history_non_authoritative'
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        first = owner.advance()
        final = owner.advance()
    with sqlite3.connect(root/'journal.sqlite3') as db:
        original1 = json.loads(db.execute('SELECT archive FROM results WHERE seq=1').fetchone()[0])
        original2 = json.loads(db.execute('SELECT archive FROM results WHERE seq=2').fetchone()[0])
        intent_digest = db.execute('SELECT digest FROM intents WHERE seq=2').fetchone()[0]
        # Two unknown native bound descriptors can both replay as unknown.
        # This preserves physical choices but changes the saved evidence prefix.
        for payload in (original1, original2):
            raw = payload['snapshot']['attempts'][0]['arm_results'][1]['dispatch_result']['stages'][0]['raw_solve']
            assert raw['lower'] is None
            raw['problem_records'][0][1] = ['builtins.float', 'nan', None]
        original2['snapshot']['attempts'][1]['before_identity'] = store.tx._identity(original1['snapshot'])
        forged = store._encoded(original2)
        digest = sha256(forged).hexdigest()
        # Prove the rejection is about committed history, not an invalid model.
        report = store.replay.replay_episode_archive(forged, *inputs,
            expected_sha256=digest,
            expected_input_identity=store.replay.episode_replay_input_identity(*inputs, **CONFIG), **CONFIG)
        assert report.archive_reproduced
        changed_head = store.tx._identity(final.store_identity, first.head, intent_digest, digest)
        db.execute('UPDATE results SET archive=?, archive_digest=?, head=? WHERE seq=2', (forged, digest, changed_head))
    with pytest.raises(ValueError, match='committed history'):
        store.DevelopmentEpisodeStore(root, *inputs, expected_head=changed_head, **CONFIG)


def test_advance_without_attempt_leaves_only_intent(tmp_path, monkeypatch):
    root = tmp_path/'no_return_non_authoritative'
    inputs = supplied()
    def failed(*a, **kw): raise RuntimeError('failed before coordinator record')
    monkeypatch.setattr(ep.EpisodeSession, 'advance', failed)
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        with pytest.raises(ValueError, match='attempt record'): owner.advance()
    with sqlite3.connect(root/'journal.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM intents').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM results').fetchone()[0] == 0
    assert store.inspect_episode_store(root, *inputs, **CONFIG).pending_intent


def test_close_releases_handle_even_when_unlock_raises(tmp_path, monkeypatch):
    import msvcrt
    root = tmp_path/'unlock_non_authoritative'
    inputs = supplied()
    owner = store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG)
    head = owner.inspection.head
    original = msvcrt.locking
    def fail_unlock(fd, mode, count):
        if mode == msvcrt.LK_UNLCK: raise OSError('unlock failed')
        return original(fd, mode, count)
    monkeypatch.setattr(msvcrt, 'locking', fail_unlock)
    with pytest.raises(OSError): owner.close()
    monkeypatch.setattr(msvcrt, 'locking', original)
    with store.DevelopmentEpisodeStore(root, *inputs, expected_head=head, **CONFIG):
        pass


@pytest.mark.parametrize('pragma', ['user_version=2', 'application_id=0', 'journal_mode=WAL'])
def test_database_contract_drift_fails_before_execution(tmp_path, monkeypatch, pragma):
    inputs = supplied()
    root = tmp_path/'pragma_non_authoritative'
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        head = owner.inspection.head
    with sqlite3.connect(root/'journal.sqlite3') as db:
        db.execute('PRAGMA '+pragma)
    def forbidden(*a, **kw): raise AssertionError('no execution under changed journal contract')
    monkeypatch.setattr(ep.EpisodeSession, 'advance', forbidden)
    with pytest.raises(ValueError):
        store.DevelopmentEpisodeStore(root, *inputs, expected_head=head, **CONFIG)


@pytest.mark.parametrize('name', ['execution.lock', 'journal.sqlite3', 'journal.sqlite3-journal'])
def test_hardlinked_store_files_are_rejected(tmp_path, name):
    inputs = supplied()
    root = tmp_path/'linked_non_authoritative'
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        head = owner.inspection.head
    if name.endswith('-journal'):
        (root/name).write_bytes(b'foreign sidecar')
    os.link(root/name, tmp_path/('alias_'+name))
    with pytest.raises(ValueError, match='single-link'):
        store.DevelopmentEpisodeStore(root, *inputs, expected_head=head, **CONFIG)


def test_real_junction_store_path_is_rejected(tmp_path):
    import _winapi
    inputs = supplied()
    root = tmp_path/'original_non_authoritative'
    alias = tmp_path/'junction_non_authoritative'
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        head = owner.inspection.head
    _winapi.CreateJunction(str(root), str(alias))
    with pytest.raises(ValueError, match='reparse'):
        store.DevelopmentEpisodeStore(alias, *inputs, expected_head=head, **CONFIG)


def test_unique_predecessor_and_no_automatic_initialization_repair(tmp_path):
    inputs = supplied()
    root = tmp_path/'unique_non_authoritative'
    with store.DevelopmentEpisodeStore(root, *inputs, create=True, **CONFIG) as owner:
        intent = store._intent(owner.inspection.store_identity, 1, owner.inspection.head,
            owner._session.snapshot, inputs[2][0], CONFIG)
        owner._append(intent, 1, owner.inspection.head)
        with sqlite3.connect(root/'journal.sqlite3') as db:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute('INSERT INTO intents VALUES (?, ?, ?, ?)', (2, owner.inspection.head, b'other', 'f'*64))
    incomplete = tmp_path/'incomplete_non_authoritative'
    incomplete.mkdir()
    (incomplete/'execution.lock').write_bytes(b'0')
    (incomplete/'journal.sqlite3').write_bytes(b'')
    with pytest.raises(ValueError): store.inspect_episode_store(incomplete, *inputs, **CONFIG)
    assert (incomplete/'journal.sqlite3').stat().st_size == 0
