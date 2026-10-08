from dataclasses import replace
import os
import sqlite3
import pytest
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,packet,spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_archive_v3 as api


def make(root,**kw):
    return api.DevelopmentH1HourArchive(root,packet(),spec(),api.replay.H1HourReplayLimits(3,100,500),
        parent_intent_head='1'*64,source_lineage_identity='2'*64,**kw)


def full(root,rows):
    owner=make(root,create=True)
    for raw in rows:owner.record_report(raw,expected_head=owner.head)
    return owner


def test_same_head_reuses_numbers_but_every_call_scans_and_new_owner_reaudits(tmp_path,saved,monkeypatch):
    root=tmp_path/'archive_non_authoritative';owner=full(root,saved[1])
    counts={'audit':0,'scan':0};audit=api.replay._audit_stage;scan=owner._journal._scan
    def counted_audit(*a,**k):counts['audit']+=1;return audit(*a,**k)
    def counted_scan(*a,**k):counts['scan']+=1;return scan(*a,**k)
    monkeypatch.setattr(api.replay,'_audit_stage',counted_audit)
    monkeypatch.setattr(owner._journal,'_scan',counted_scan)
    try:
        prior=owner.inspect();assert counts=={'audit':0,'scan':1}
        one=owner._replay_complete_prefix();assert counts['audit']==3
        two=owner._replay_complete_prefix();assert one==two and counts['audit']==3 and counts['scan']==3
        final=owner.finish(expected_head=owner.head)
        assert final.status=='accepted' and counts['audit']==6  # new terminal head is reaudited
        assert owner.inspect()==final and counts['audit']==6
        head=owner.head
    finally:owner.close()
    reopened=make(root,expected_head=head)
    try:
        assert counts['audit']==9  # independent owner cannot inherit memoized audit
        assert reopened.inspect()==final and counts['audit']==9
    finally:reopened.close()


@pytest.mark.parametrize('fault',['raw','metadata','replace','receipt','type','threshold','spec','limits','source','implementation'])
def test_snapshot_hit_never_bypasses_physical_or_semantic_drift(tmp_path,saved,monkeypatch,fault):
    owner=full(tmp_path/'archive_non_authoritative',saved[1]);owner.inspect()
    db=owner._journal._database
    if fault in ('raw','metadata'):
        with sqlite3.connect(db) as c:
            if fault=='raw':c.execute('update chunks set payload=? where event_seq=1',(b'corrupt',))
            else:c.execute('update events set metadata=? where seq=1',(b'{}',))
    elif fault=='replace':
        other=tmp_path/'replacement.sqlite3';other.write_bytes(db.read_bytes());os.replace(other,db)
    elif fault=='receipt':object.__setattr__(owner._verified_snapshots['restore'][1],'formal_result',True)
    elif fault=='type':
        key,result,pin=owner._verified_snapshots['restore'];owner._verified_snapshots['restore']=(key,object(),pin)
    elif fault=='threshold':monkeypatch.setattr(api.replay.generation_projection.model_api,'RESIDUAL_LIMIT',1e-6)
    elif fault=='spec':owner._spec=replace(owner._spec,time_limit_seconds=2.)
    elif fault=='limits':owner._limits=replace(owner._limits,max_variables=101)
    elif fault=='source':owner._parent='9'*64
    elif fault=='implementation':monkeypatch.setattr(api.replay,'implementation_identity',lambda:'0'*64)
    try:
        with pytest.raises((ValueError,RuntimeError)):owner.inspect()
        assert owner._poisoned
        with pytest.raises(ValueError):owner.inspect()
    finally:owner.close()


def test_cache_hit_propagates_scan_error_and_poison(tmp_path,saved,monkeypatch):
    owner=full(tmp_path/'archive_non_authoritative',saved[1]);owner.inspect()
    def failed(*a):raise OSError('fresh read failure')
    monkeypatch.setattr(owner._journal,'_scan',failed)
    try:
        with pytest.raises(OSError):owner.inspect()
        assert owner._poisoned
    finally:owner.close()


def test_prefix_cache_write_failure_poison_owner(tmp_path,saved,monkeypatch):
    owner=full(tmp_path/'archive_non_authoritative',saved[1])
    original=owner._snapshot_bytes
    def failed(kind,result):
        if kind=='prefix':raise OSError('snapshot encoding failure')
        return original(kind,result)
    monkeypatch.setattr(owner,'_snapshot_bytes',failed)
    try:
        with pytest.raises(OSError):owner._replay_complete_prefix()
        assert owner._poisoned and not owner._verified_snapshots
        with pytest.raises(ValueError):owner.inspect()
        with pytest.raises(ValueError):_ = owner.head
    finally:owner.close()


@pytest.mark.parametrize('mode',['hit','put','prior_error'])
def test_snapshot_close_failure_poison_owner(tmp_path,saved,monkeypatch,mode):
    owner=full(tmp_path/'archive_non_authoritative',saved[1])
    connect=owner._journal._connect
    class BrokenClose:
        def __init__(self):self.connection=connect()
        def __getattr__(self,name):return getattr(self.connection,name)
        def close(self):
            self.connection.close()
            raise OSError('snapshot close failure')
    monkeypatch.setattr(owner._journal,'_connect',BrokenClose)
    if mode=='prior_error':
        def scan_error(*a):raise RuntimeError('original scan failure')
        monkeypatch.setattr(owner._journal,'_scan',scan_error)
    try:
        error,match=(RuntimeError,'original scan failure') if mode=='prior_error' else (OSError,'snapshot close failure')
        with pytest.raises(error,match=match):
            if mode=='put':owner._replay_complete_prefix()
            else:owner.inspect()
        assert owner._poisoned and not owner._verified_snapshots
        with pytest.raises(ValueError):owner.inspect()
        with pytest.raises(ValueError):_ = owner.head
    finally:owner.close()


def test_direct_prefix_precheck_drift_poison_owner(tmp_path,saved):
    owner=full(tmp_path/'archive_non_authoritative',saved[1])
    original=owner._spec
    owner._spec=replace(original,time_limit_seconds=2.)
    try:
        with pytest.raises(ValueError,match='drift'):owner._replay_complete_prefix()
        assert owner._poisoned and not owner._verified_snapshots
        owner._spec=original
        with pytest.raises(ValueError):owner.inspect()
        with pytest.raises(ValueError):_ = owner.head
    finally:owner.close()
