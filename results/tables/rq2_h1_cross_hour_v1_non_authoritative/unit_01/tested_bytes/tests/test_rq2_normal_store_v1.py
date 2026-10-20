from copy import copy, deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import pickle
import shutil
import sqlite3
import subprocess
import sys

import pytest

from test_rq2_source_normal_execution_v1 import supplied, options
from test_rq2_continuous_grid_candidate_v1 import install
from src.rq2_joint_deliverability_boundary_v1 import normal_store as api


LIMIT = 16*1024**2


def open_store(root, supplied, **changes):
    assembly, declaration, report, _ = supplied
    args = dict(create=True, max_record_bytes=LIMIT, **options(assembly, declaration, report))
    args.update(changes)
    return api.DevelopmentNormalStore(root, assembly, 'unused', declaration, **args)


def test_owned_tiny_invocation_archived_once_and_reconciled(tmp_path, supplied):
    root = tmp_path/'normal_non_authoritative'
    with open_store(root, supplied) as store:
        genesis = store.inspect().head
        assert store.inspect().status == 'unused'
        result, inspection = store.execute()
        assert result.source_bound_normal_accepted
        assert inspection.status == 'returned_record_unreplayed'
        assert inspection.result_identity == result.identity
        assert inspection.head != genesis
        assert inspection.numerical_evidence_replayed is inspection.native_execution_authenticated is False
        with pytest.raises(ValueError, match='cannot retry'):
            store.execute()
        for function in (copy, deepcopy, pickle.dumps):
            with pytest.raises(TypeError): function(store)
    with open_store(root, supplied, create=False, expected_head=genesis) as reopened:
        assert reopened.inspect() == inspection
        with pytest.raises(ValueError, match='cannot retry'): reopened.execute()
    with pytest.raises(ValueError, match='head mismatch'):
        open_store(root, supplied, create=False, expected_head='0'*64)


def test_full_result_budget_not_core_budget(tmp_path, supplied, monkeypatch):
    install(monkeypatch, supplied[0].inputs)
    with open_store(tmp_path/'small_non_authoritative', supplied, max_record_bytes=1) as store:
        with pytest.raises(ValueError, match='complete normal result record'):
            store.execute()
        assert store.inspect().status == 'unresolved_intent'
        with pytest.raises(ValueError, match='cannot retry'): store.execute()


def test_source_failure_after_intent_never_retries(tmp_path, supplied, monkeypatch):
    def fail(*args, **kwargs): raise ValueError('source changed before inner invocation')
    monkeypatch.setattr(api.execution, 'run_source_normal', fail)
    root = tmp_path/'failed_non_authoritative'
    with open_store(root, supplied) as store:
        head = store.inspect().head
        with pytest.raises(ValueError, match='source changed'): store.execute()
        assert store.inspect().status == 'unresolved_intent'
    with open_store(root, supplied, create=False, expected_head=head) as reopened:
        assert reopened.inspect().intent_present
        with pytest.raises(ValueError, match='cannot retry'): reopened.execute()


def test_lost_commit_response_reconciles_without_new_invocation(tmp_path, supplied, monkeypatch):
    install(monkeypatch, supplied[0].inputs)
    root = tmp_path/'lost_non_authoritative'
    with open_store(root, supplied) as store:
        genesis = store.inspect().head
        original = store._append
        def lost(raw=None):
            original(raw)
            if raw is not None: raise RuntimeError('lost commit response')
        monkeypatch.setattr(store, '_append', lost)
        with pytest.raises(RuntimeError, match='lost commit response'): store.execute()
        saved = store.inspect()
        assert saved.result_present
    with open_store(root, supplied, create=False, expected_head=genesis) as reopened:
        assert reopened.inspect() == saved
        with pytest.raises(ValueError, match='cannot retry'): reopened.execute()


def test_same_and_other_process_exclusion(tmp_path, supplied):
    root = tmp_path/'locked_non_authoritative'
    with open_store(root, supplied) as store:
        head = store.inspect().head
        with pytest.raises(ValueError, match='already held'):
            open_store(root, supplied, create=False, expected_head=head)
        script = '''
import sys
from src.rq2_joint_deliverability_boundary_v1.episode_store import _Lease
try:
 lease=_Lease(sys.argv[1],False)
except (ValueError,OSError):
 sys.exit(23)
lease.close()
sys.exit(0)
'''
        child = subprocess.run([sys.executable, '-B', '-c', script, str(root)], capture_output=True,
            timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        assert child.returncode == 23, child.stderr


@pytest.mark.parametrize('mode', ['copy', 'hardlink', 'schema', 'metadata'])
def test_root_database_and_schema_identity(tmp_path, supplied, mode):
    root = tmp_path/'original_non_authoritative'
    with open_store(root, supplied) as store: head = store.inspect().head
    if mode == 'copy':
        target = tmp_path/'copy_non_authoritative'
        shutil.copytree(root, target)
        root = target
    elif mode == 'hardlink':
        os.link(root/'normal.sqlite3', tmp_path/'alias.sqlite3')
    else:
        connection = sqlite3.connect(root/'normal.sqlite3')
        try:
            connection.execute('CREATE TABLE unexpected(x)' if mode == 'schema' else 'DELETE FROM metadata')
            connection.commit()
        finally: connection.close()
    with pytest.raises(ValueError): open_store(root, supplied, create=False, expected_head=head)


def test_archived_record_corruption_detected(tmp_path, supplied, monkeypatch):
    install(monkeypatch, supplied[0].inputs)
    root = tmp_path/'corrupt_non_authoritative'
    with open_store(root, supplied) as store:
        genesis = store.inspect().head
        store.execute()
    connection = sqlite3.connect(root/'normal.sqlite3')
    try:
        raw = connection.execute('SELECT payload FROM result').fetchone()[0]
        record = json.loads(raw)
        record['result_identity'] = '0'*64
        altered = api._bytes(record)
        connection.execute('UPDATE result SET payload=?, digest=?', (altered, sha256(altered).hexdigest()))
        connection.commit()
    finally: connection.close()
    with pytest.raises(ValueError, match='result identity mismatch'):
        open_store(root, supplied, create=False, expected_head=genesis)


def test_noncanonical_archive_rejected():
    with pytest.raises(ValueError): api._decoded(b'{"a":1,"a":1}')
    with pytest.raises(ValueError): api._decoded(b'{"a": NaN}')
    with pytest.raises(ValueError): api._decoded(b'{ "a": 1 }')


def test_intent_readback_failure_prevents_invocation(tmp_path, supplied, monkeypatch):
    root = tmp_path/'readback_non_authoritative'
    with open_store(root, supplied) as store:
        genesis = store.inspect().head
        original = store._inspect
        calls = [0]
        def inspect():
            calls[0] += 1
            if calls[0] == 2: raise RuntimeError('intent readback unavailable')
            return original()
        invoked = [False]
        def forbidden(*args, **kwargs):
            invoked[0] = True
            raise AssertionError('must not invoke before readback')
        monkeypatch.setattr(store, '_inspect', inspect)
        monkeypatch.setattr(api.execution, 'run_source_normal', forbidden)
        with pytest.raises(RuntimeError, match='intent readback unavailable'): store.execute()
        assert invoked == [False]
    with open_store(root, supplied, create=False, expected_head=genesis) as reopened:
        assert reopened.inspect().status == 'unresolved_intent'


def test_request_drift_before_intent_is_rejected(tmp_path, supplied):
    root = tmp_path/'drift_non_authoritative'
    with open_store(root, supplied) as store:
        # Fault-inject the privately held request; ordinary caller mutation is isolated.
        store._arguments['max_extra_unknown_field'] = 1
        with pytest.raises(ValueError, match='exact normal source execution request'):
            store.execute()
    connection = sqlite3.connect(root/'normal.sqlite3')
    try: assert connection.execute('SELECT * FROM intent').fetchall() == []
    finally: connection.close()


def test_create_rejects_previous_head_before_files(tmp_path, supplied):
    root = tmp_path/'invalid_mode_non_authoritative'
    with pytest.raises(ValueError, match='cannot supply a previous head'):
        open_store(root, supplied, expected_head='0'*64)
    assert not root.exists()


def test_retained_current_head_detects_self_consistent_result_rewrite(tmp_path, supplied, monkeypatch):
    install(monkeypatch, supplied[0].inputs)
    root = tmp_path/'rewritten_non_authoritative'
    with open_store(root, supplied) as store:
        genesis = store.inspect().genesis
        _, saved = store.execute()
    connection = sqlite3.connect(root/'normal.sqlite3')
    try:
        record = json.loads(connection.execute('SELECT payload FROM result').fetchone()[0])
        for field in record['encoded_result'][1]:
            if field[0] == 'observed_wrapper_seconds': field[1] = ['float', float(999).hex()]
        record['result_identity'] = api._result_identity(record['encoded_result'])
        raw = api._bytes(record)
        connection.execute('UPDATE result SET payload=?,digest=?', (raw, sha256(raw).hexdigest()))
        connection.commit()
    finally: connection.close()
    with pytest.raises(ValueError, match='independent normal journal head mismatch'):
        open_store(root, supplied, create=False, expected_head=saved.head)
    # Genesis authenticates no unknown future result: this is integrity-only inspection.
    with open_store(root, supplied, create=False, expected_head=genesis) as reopened:
        inspection = reopened.inspect()
        assert inspection.head != saved.head
        assert not inspection.numerical_evidence_replayed and not inspection.native_execution_authenticated
        with pytest.raises(ValueError, match='cannot retry'): reopened.execute()


@pytest.mark.parametrize('phase,status', [('before_intent', 'unused'), ('after_intent', 'unresolved_intent'),
    ('before_result', 'unresolved_intent'), ('after_result', 'returned_record_unreplayed')])
def test_real_process_exit_windows(tmp_path, supplied, phase, status):
    root = tmp_path/(phase+'_non_authoritative')
    head_path = tmp_path/(phase+'.head')
    script = '''
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
import pytest
from test_rq2_source_normal_execution_v1 import supplied
from test_rq2_normal_store_v1 import open_store
from test_rq2_continuous_grid_candidate_v1 import install
mp=pytest.MonkeyPatch()
case=supplied.__wrapped__(mp)
install(mp,case[0].inputs)
store=open_store(Path(sys.argv[1]),case)
Path(sys.argv[2]).write_text(store.inspect().head,encoding='ascii')
original=store._append
phase=sys.argv[3]
def crash(raw=None):
 if (raw is None and phase=='before_intent') or (raw is not None and phase=='before_result'): os._exit(71)
 original(raw)
 if (raw is None and phase=='after_intent') or (raw is not None and phase=='after_result'): os._exit(71)
store._append=crash
store.execute()
os._exit(72)
'''
    child = subprocess.run([sys.executable, '-B', '-c', script, str(root), str(head_path), phase],
        capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    assert child.returncode == 71, child.stderr.decode(errors='replace')
    head = head_path.read_text(encoding='ascii')
    with open_store(root, supplied, create=False, expected_head=head) as reopened:
        assert reopened.inspect().status == status
        if status != 'unused':
            with pytest.raises(ValueError, match='cannot retry'): reopened.execute()
