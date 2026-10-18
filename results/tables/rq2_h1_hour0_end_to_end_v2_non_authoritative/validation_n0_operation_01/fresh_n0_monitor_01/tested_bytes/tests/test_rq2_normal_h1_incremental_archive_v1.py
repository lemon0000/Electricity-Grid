from dataclasses import replace
import sqlite3
import pytest
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,packet,spec,LIMITS
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_incremental_archive as api


def make(tmp_path):
    return api.DevelopmentH1IncrementalArchive(tmp_path/'incremental_non_authoritative',packet(),spec(),LIMITS,
        parent_intent_head='1'*64,source_lineage_identity='2'*64,create=True)


def mutate(store,sql="UPDATE chunks SET payload=payload||x'00' WHERE event_seq=1"):
    peer=sqlite3.connect(store._journal._database,timeout=0)
    try:peer.execute(sql);peer.commit()
    finally:peer.close()


def test_sqlite_epoch_probe_and_only_current_stage_audited(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    v0,v1,v2,v3=store._epoch_probe
    assert v0==v1 and v1!=v2 and v2==v3
    calls=[]
    original=api.replay._audit_stage
    def audit(*a,**k):calls.append(a[3]);return original(*a,**k)
    monkeypatch.setattr(api.replay,'_audit_stage',audit)
    original_scan=store._journal._scan
    monkeypatch.setattr(store._journal,'_scan',lambda *a:pytest.fail('incremental write scanned old payload'))
    try:
        for raw in saved[1]:result=store.record_report(raw,expected_head=store.head)
        assert calls==[0,0,1,1,2,2] and result.canonical_locks==(20.,1.,20.)
        assert result.projection is None and result.status=='awaiting_terminal'
        assert store._version()==store._epoch
        monkeypatch.setattr(store._journal,'_scan',original_scan)
        result=store.finish(expected_head=store.head)
        assert result.status=='accepted'
        assert result.projection.projection_payload==api.replay.native.capture.encode(saved[0]['projection'])
        assert not result.formal_result and not result.source_authenticated
    finally:store.close()


def test_reopen_full_replay_and_old_interface_isolation(tmp_path,saved):
    store=make(tmp_path)
    for raw in saved[1]:store.record_report(raw,expected_head=store.head)
    result=store.finish(expected_head=store.head)
    head=store.head
    store.close()
    args=dict(parent_intent_head='1'*64,source_lineage_identity='2'*64,expected_head=head)
    with pytest.raises(ValueError):api.base.DevelopmentH1HourArchive(tmp_path/'incremental_non_authoritative',packet(),spec(),LIMITS,**args)
    reopened=api.DevelopmentH1IncrementalArchive(tmp_path/'incremental_non_authoritative',packet(),spec(),LIMITS,**args)
    try:
        assert reopened._epoch_probe is None
        assert reopened.inspect()==result
    finally:reopened.close()


@pytest.mark.parametrize('when',['before','after_audit','after_commit'])
def test_external_sql_commit_poisoned(tmp_path,saved,monkeypatch,when):
    store=make(tmp_path)
    store.record_report(saved[1][0],expected_head=store.head)
    prior=store._state
    # Same-length old-row mutation changes neither counts nor tail structure.
    sql="UPDATE chunks SET payload_sha='0000000000000000000000000000000000000000000000000000000000000000' WHERE event_seq=1"
    expected=store.head
    if when=='before':mutate(store,sql)
    elif when=='after_audit':
        original=api.replay._audit_stage
        def audit(*a,**k):
            result=original(*a,**k)
            mutate(store,sql)
            return result
        monkeypatch.setattr(api.replay,'_audit_stage',audit)
    else:
        original=store._journal._commit
        def commit(connection):original(connection);mutate(store,sql)
        monkeypatch.setattr(store._journal,'_commit',commit)
    try:
        with pytest.raises(ValueError,match='epoch'):store.record_report(saved[1][1],expected_head=expected)
        assert store._state==prior
        with pytest.raises(ValueError,match='unresolved'):_=store.head
    finally:store.close()


@pytest.mark.parametrize('fault',['before','after','noop','readback'])
def test_commit_ambiguity_does_not_advance_cache(tmp_path,saved,monkeypatch,fault):
    store=make(tmp_path)
    prior=store._state
    if fault=='readback':
        monkeypatch.setattr(store._journal,'_connect',lambda:(_ for _ in ()).throw(ValueError('fresh connection failed')))
    else:
        original=store._journal._commit
        def commit(c):
            if fault=='after':original(c)
            if fault!='noop':raise RuntimeError('commit failed')
        monkeypatch.setattr(store._journal,'_commit',commit)
    try:
        with pytest.raises((ValueError,RuntimeError,sqlite3.Error)):store.record_report(saved[1][0],expected_head=store.head)
        assert store._state==prior
        with pytest.raises(ValueError,match='unresolved'):_=store.head
    finally:store.close()


def test_readback_protected_against_external_writer(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    original=store._journal._connect
    blocked=[]
    def connect():
        with pytest.raises(sqlite3.OperationalError,match='locked'):
            mutate(store,'PRAGMA user_version=7')
        blocked.append(True)
        return original()
    monkeypatch.setattr(store._journal,'_connect',connect)
    try:
        result=store.record_report(saved[1][0],expected_head=store.head)
        assert result.canonical_locks==(20.,) and blocked==[True]
    finally:store.close()


def test_cache_tampering_rejected_before_audit(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    store.record_report(saved[1][0],expected_head=store.head)
    head=store.head
    store._state=replace(store._state,canonical_locks=(21.,))
    monkeypatch.setattr(api.replay,'_audit_stage',lambda *a:pytest.fail('tampered cache reached audit'))
    try:
        with pytest.raises(ValueError,match='cache'):store.record_report(saved[1][1],expected_head=head)
    finally:store.close()


def test_unexpected_own_dml_detected(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    original=store._journal._commit
    def commit(connection):
        connection.execute("UPDATE metadata SET header=header")
        original(connection)
    monkeypatch.setattr(store._journal,'_commit',commit)
    try:
        with pytest.raises(ValueError,match='DML'):store.record_report(saved[1][0],expected_head=store.head)
        assert store._state.canonical_locks==()
    finally:store.close()


def test_fresh_semantic_failure_poison_both_owners(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    prior=store._state
    original=api.replay._audit_stage
    calls=[]
    def audit(*args):
        calls.append(True)
        if len(calls)==2:raise RuntimeError('fresh audit unavailable')
        return original(*args)
    monkeypatch.setattr(api.replay,'_audit_stage',audit)
    try:
        with pytest.raises(RuntimeError,match='fresh audit'):store.record_report(saved[1][0],expected_head=store.head)
        assert store._state==prior
        assert store._poisoned and store._journal._poisoned
        with pytest.raises(ValueError):_=store._journal.head
    finally:store.close()


def test_terminal_replay_detects_internally_consistent_wrong_cache(tmp_path,saved):
    store=make(tmp_path)
    try:
        for raw in saved[1]:store.record_report(raw,expected_head=store.head)
        head=store.head
        store._state=replace(store._state,canonical_locks=(21.,1.,20.))
        store._cache_digest=store._cache_identity()
        with pytest.raises(ValueError,match='cache differs'):store.finish(expected_head=head)
        assert store._counts_cache[0]==3 and store._journal._poisoned
    finally:store.close()


def test_rejected_raw_is_durable_and_stops_next_stage(tmp_path):
    store=make(tmp_path)
    try:
        result=store.record_report(b'{}',expected_head=store.head)
        assert result.status=='rejected' and result.stored_reports==1
        assert result.canonical_locks==() and result.projection is None
        assert store.inspect()==result
        with pytest.raises(ValueError,match='terminal'):store.record_report(b'{}',expected_head=store.head)
    finally:store.close()
