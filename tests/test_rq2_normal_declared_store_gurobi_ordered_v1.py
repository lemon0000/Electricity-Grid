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

from test_rq2_normal_declared_execution_gurobi_ordered_v1 import supplied, prepared_source, bound_source, source_supplied
from src.rq2_joint_deliverability_boundary_v1 import normal_declared_store_gurobi_ordered as api


LIMIT = 16*1024**2


def test_runtime_check_after_preparation_keeps_reserved_intent(tmp_path, supplied, monkeypatch):
    events = []
    original = api.execution.prepare.prepare_task_inputs
    def prepare(*args, **kwargs):
        events.append('prepare')
        assert store._inspect().status == 'unresolved_intent'
        return original(*args, **kwargs)
    def guard():
        events.append('guard')
        raise ValueError('runtime drift')
    monkeypatch.setattr(api.execution.prepare, 'prepare_task_inputs', prepare)
    monkeypatch.setattr(api.execution.source, 'run_source_normal', lambda *a, **k: events.append('source'))
    with open_store(tmp_path/'guard_non_authoritative', supplied) as store:
        with pytest.raises(ValueError, match='runtime drift'): store.execute(before_source=guard)
        assert events == ['prepare', 'guard']
        assert store.inspect().status == 'unresolved_intent'
        with pytest.raises(ValueError, match='cannot retry'): store.execute(before_source=guard)
        assert events == ['prepare', 'guard']


def test_invalid_runtime_check_does_not_consume_intent(tmp_path, supplied):
    with open_store(tmp_path/'invalid_guard_non_authoritative', supplied) as store:
        with pytest.raises(TypeError, match='callable'): store.execute(before_source=True)
        assert store.inspect().status == 'unused'


def open_store(root, supplied, **changes):
    request, options = supplied
    args = dict(create=True, max_record_bytes=LIMIT, **options)
    args.update(changes)
    return api.DevelopmentDeclaredGurobiOrderedNormalStore(root, request, **args)



def test_owned_tiny_invocation_archived_once_and_reconciled(tmp_path, supplied):
    root = tmp_path/'normal_non_authoritative'
    with open_store(root, supplied) as store:
        genesis = store.inspect().head
        assert store.inspect().status == 'unused'
        result, inspection = store.execute()
        assert result.accepted
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
    with open_store(tmp_path/'small_non_authoritative', supplied, max_record_bytes=1) as store:
        with pytest.raises(ValueError, match='complete normal result record'):
            store.execute()
        assert store.inspect().status == 'unresolved_intent'
        with pytest.raises(ValueError, match='cannot retry'): store.execute()


def test_source_failure_after_intent_never_retries(tmp_path, supplied, monkeypatch):
    def fail(*args, **kwargs): raise ValueError('source changed before inner invocation')
    monkeypatch.setattr(api.execution, 'run_declared_normal', fail)
    root = tmp_path/'failed_non_authoritative'
    with open_store(root, supplied) as store:
        head = store.inspect().head
        with pytest.raises(ValueError, match='source changed'): store.execute()
        assert store.inspect().status == 'unresolved_intent'
    with open_store(root, supplied, create=False, expected_head=head) as reopened:
        assert reopened.inspect().intent_present
        with pytest.raises(ValueError, match='cannot retry'): reopened.execute()


def test_lost_commit_response_reconciles_without_new_invocation(tmp_path, supplied, monkeypatch):
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
        monkeypatch.setattr(api.execution, 'run_declared_normal', forbidden)
        with pytest.raises(RuntimeError, match='intent readback unavailable'): store.execute()
        assert invoked == [False]
    with open_store(root, supplied, create=False, expected_head=genesis) as reopened:
        assert reopened.inspect().status == 'unresolved_intent'


def test_request_drift_before_intent_is_rejected(tmp_path, supplied):
    root = tmp_path/'drift_non_authoritative'
    with open_store(root, supplied) as store:
        # Fault-inject the privately held request; ordinary caller mutation is isolated.
        store._arguments['max_extra_unknown_field'] = 1
        with pytest.raises(ValueError, match='exact declared normal execution request'):
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
    root = tmp_path/'rewritten_non_authoritative'
    with open_store(root, supplied) as store:
        genesis = store.inspect().genesis
        _, saved = store.execute()
    connection = sqlite3.connect(root/'normal.sqlite3')
    try:
        record = json.loads(connection.execute('SELECT payload FROM result').fetchone()[0])
        for field in record['encoded_result'][1]:
            if field[0] == 'status': field[1] = 'changed_diagnostic_status'
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
from test_rq2_normal_declared_execution_gurobi_ordered_v1 import supplied, prepared_source, bound_source, source_supplied
from test_rq2_normal_declared_store_gurobi_ordered_v1 import open_store
mp=pytest.MonkeyPatch()
case=supplied.__wrapped__(prepared_source.__wrapped__(
 bound_source.__wrapped__(source_supplied.__wrapped__(Path(sys.argv[4]),mp),mp),Path(sys.argv[4])))
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
    child = subprocess.run([sys.executable, '-B', '-c', script, str(root), str(head_path), phase, str(tmp_path)],
        capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    assert child.returncode == 71, child.stderr.decode(errors='replace')
    head = head_path.read_text(encoding='ascii')
    with open_store(root, supplied, create=False, expected_head=head) as reopened:
        assert reopened.inspect().status == status
        if status != 'unused':
            with pytest.raises(ValueError, match='cannot retry'): reopened.execute()


def test_constructor_never_prepares_and_intent_precedes_prepare(tmp_path,supplied,monkeypatch):
    original=api.execution.prepare.prepare_task_inputs
    root=tmp_path/'intent_before_prepare_non_authoritative'
    seen=[]
    def prepare(*a,**k):
        connection=sqlite3.connect(root/'normal.sqlite3')
        try:
            assert connection.execute('SELECT count(*) FROM intent').fetchone()==(1,)
            assert connection.execute('SELECT count(*) FROM result').fetchone()==(0,)
        finally: connection.close()
        seen.append('prepare')
        return original(*a,**k)
    monkeypatch.setattr(api.execution.prepare,'prepare_task_inputs',prepare)
    with open_store(root,supplied) as store:
        assert seen==[] and not hasattr(store,'_assembly')
        result,inspection=store.execute()
        assert seen==['prepare'] and result.accepted
        connection=sqlite3.connect(root/'normal.sqlite3')
        try: raw=connection.execute('SELECT payload FROM result').fetchone()[0]
        finally: connection.close()
        record=api._decoded(raw)
        assert record['encoded_result']==api.execution.kernel._encode(result)
        assert record['encoded_result'][0]=='DeclaredGurobiOrderedNormalResult'
        assert inspection.archived_result_sha256==sha256(raw).hexdigest()


def test_declaration_drift_leaves_readable_pending_intent(tmp_path,supplied):
    root=tmp_path/'declaration_drift_non_authoritative'
    with open_store(root,supplied) as store:
        genesis=store.inspect().head
        Path(supplied[0].normal_record_path).write_bytes(b'changed')
        with pytest.raises(ValueError,match='size/hash mismatch'): store.execute()
        assert store.inspect().status=='unresolved_intent'
    with open_store(root,supplied,create=False,expected_head=genesis) as reopened:
        assert reopened.inspect().status=='unresolved_intent'
        with pytest.raises(ValueError,match='cannot retry'): reopened.execute()


@pytest.mark.parametrize('kind',['dict','wrong_request','wrong_execution'])
def test_unowned_or_wrong_lineage_return_not_archived(tmp_path,supplied,monkeypatch,kind):
    from dataclasses import fields
    original=api.execution.run_declared_normal
    def changed(*a,**k):
        if kind=='dict': return {'accepted':True}
        result=original(*a,**k)
        values={f.name:getattr(result,f.name) for f in fields(result)}
        values['request_identity' if kind=='wrong_request' else 'execution_identity']='0'*64
        return api.execution.kernel.native._make(api.execution.DeclaredGurobiOrderedNormalResult,**values)
    monkeypatch.setattr(api.execution,'run_declared_normal',changed)
    with open_store(tmp_path/'invalid_return_non_authoritative',supplied) as store:
        with pytest.raises(ValueError,match='owned normal result'):store.execute()
        assert store.inspect().status=='unresolved_intent'


def test_failed_post_declaration_check_is_archived_with_raw_evidence(tmp_path,supplied,monkeypatch):
    original=api.execution.source.run_source_normal
    def changed(*a,**k):
        result=original(*a,**k)
        Path(supplied[0].normal_record_path).write_bytes(b'changed after solve')
        return result
    monkeypatch.setattr(api.execution.source,'run_source_normal',changed)
    root=tmp_path/'post_declared_failure_non_authoritative'
    with open_store(root,supplied) as store:
        result,inspection=store.execute()
        assert not result.accepted and result.solver_calls==1
        assert result.source_result.normal_result.normal.optimal
        assert inspection.status=='returned_record_unreplayed'
        assert inspection.result_identity==result.identity
    with open_store(root,supplied,create=False,expected_head=inspection.head) as reopened:
        assert reopened.inspect()==inspection


@pytest.mark.parametrize('old_stream', [False, True, 'fast'])
def test_old_application_id_is_not_new_journal(tmp_path,supplied,old_stream):
    from src.rq2_joint_deliverability_boundary_v1 import normal_store as legacy
    if old_stream == 'fast':
        from src.rq2_joint_deliverability_boundary_v1 import normal_declared_store_stream_fast as legacy
    elif old_stream:
        from src.rq2_joint_deliverability_boundary_v1 import normal_declared_store_stream as legacy
    root=tmp_path/'old_schema_non_authoritative'
    with open_store(root,supplied) as store: head=store.inspect().head
    connection=sqlite3.connect(root/'normal.sqlite3')
    try:
        connection.execute('PRAGMA application_id='+str(legacy.APPLICATION_ID))
        connection.commit()
    finally: connection.close()
    with pytest.raises(ValueError,match='metadata/schema/integrity'):
        open_store(root,supplied,create=False,expected_head=head)
