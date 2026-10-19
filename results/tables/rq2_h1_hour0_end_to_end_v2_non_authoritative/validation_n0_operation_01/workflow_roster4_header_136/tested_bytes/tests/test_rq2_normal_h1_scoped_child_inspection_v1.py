from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import pytest
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,packet,spec,budget
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_scoped_child_inspection as api

LIMITS=api.base.replay.H1HourReplayLimits(3,100,500)


def prepared(tmp_path,saved,monkeypatch):
    rows=iter(saved[1])
    monkeypatch.setattr(api.base.native.capture,'solve_once',lambda *a,**k:next(rows))
    root=tmp_path/'collector_non_authoritative'
    anchor=tmp_path/'anchor_non_authoritative'
    args=dict(anchor_root=anchor,parent_intent_head='1'*64,source_lineage_identity='2'*64)
    owner=api.legacy.DevelopmentH1AnchoredCollector(root,packet(),spec(),budget(),LIMITS,create=True,**args)
    try:
        result=owner.run(expected_head=owner.inspect().registry_head)
        pin=owner._anchor.inspect().record_sha256
    finally:owner.close()
    return root,args,pin,result


def test_cached_scope_fault_matrix_and_constructor_cleanup(tmp_path,saved,monkeypatch):
    root,args,pin,expected=prepared(tmp_path,saved,monkeypatch)
    def open_reader():
        return api.DevelopmentH1ScopedChildInspection(root,packet(),spec(),budget(),LIMITS,
            expected_anchor_record=pin,**args)
    faults={
        'head':lambda a:setattr(a._journal,'_head','0'*64),
        'count':lambda a:setattr(a,'_counts_cache',(0,0,0,0)),
        'tail':lambda a:setattr(a,'_tail_cache',None),
        'header':lambda a:setattr(a._journal,'_header',b'{}'),
        'file_identity':lambda a:setattr(a._journal,'_file_identity',(0,0)),
        'request':lambda a:setattr(a,'_key','0'*64),
        'source_audit':lambda a:object.__setattr__(a._packet,'audit_identity','0'*64),
        'foreign_owner':lambda a:setattr(a._token,'owner',object()),
    }
    for name,inject in faults.items():
        owner=open_reader()
        try:
            inject(owner._child)
            with pytest.raises(ValueError):owner.inspect()
            assert owner._poisoned, name
            with pytest.raises(ValueError):owner.inspect()
        finally:owner.close()
    owner=open_reader()
    try:
        token=owner._child._token
        assert owner.inspect().inspection==expected and token.consumed
        owner._child._token=token
        with pytest.raises(ValueError,match='token'):owner.inspect()
    finally:owner.close()
    with monkeypatch.context() as patch:
        def fail(*a,**k):raise RuntimeError('construction replay failed')
        patch.setattr(api.base.replay,'_audit_stage',fail)
        with pytest.raises(RuntimeError,match='construction replay failed'):open_reader()
    owner=open_reader()
    try:assert owner.inspect().inspection==expected
    finally:owner.close()
    # Disposable database only: schema change does not increment total_changes.
    owner=open_reader()
    try:
        owner._child._writer.execute('CREATE TABLE unexpected (value TEXT)')
        with pytest.raises(ValueError):owner.inspect()
        with pytest.raises(ValueError):owner.inspect()
    finally:owner.close()


@pytest.mark.parametrize('mode',['rejected','previous','expected','terminal'])
def test_incomplete_and_rejected_match_legacy(tmp_path,saved,monkeypatch,mode):
    root=tmp_path/'collector_non_authoritative'
    args=dict(anchor_root=tmp_path/'anchor_non_authoritative',parent_intent_head='1'*64,
        source_lineage_identity='2'*64)
    owner=api.legacy.DevelopmentH1AnchoredCollector(root,packet(),spec(),budget(),LIMITS,create=True,**args)
    rows=iter(saved[1])
    monkeypatch.setattr(api.base.native.capture,'solve_once',lambda *a,**k:b'{}' if mode=='rejected' else next(rows))
    commit=owner._child._journal._commit
    count=0
    def fail(connection):
        nonlocal count
        count+=1
        if mode=='terminal' and count<4:return commit(connection)
        if mode!='previous':commit(connection)
        raise RuntimeError('child commit uncertain')
    if mode!='rejected':monkeypatch.setattr(owner._child._journal,'_commit',fail)
    try:
        if mode=='rejected':owner.run(expected_head=owner.inspect().registry_head)
        else:
            with pytest.raises(RuntimeError):owner.run(expected_head=owner.inspect().registry_head)
        pin=owner._anchor.inspect().record_sha256
    finally:owner.close()
    old=api.legacy.DevelopmentH1AnchoredCollector(root,packet(),spec(),budget(),LIMITS,expected_anchor_record=pin,**args)
    try:expected=old.inspect()
    finally:old.close()
    new=api.DevelopmentH1ScopedChildInspection(root,packet(),spec(),budget(),LIMITS,expected_anchor_record=pin,**args)
    try:
        assert new.inspect().inspection==expected
        assert expected.projection is None
        assert expected.status==('rejected' if mode=='rejected' else 'pending_unknown')
    finally:new.close()


def test_one_full_replay_first_inspect_and_fresh_second_inspect(tmp_path,saved,monkeypatch):
    root,args,pin,expected=prepared(tmp_path,saved,monkeypatch)
    calls=[]
    original=api.base.replay._audit_stage
    def audit(*a,**k):calls.append(a[3]);return original(*a,**k)
    monkeypatch.setattr(api.base.replay,'_audit_stage',audit)
    owner=api.DevelopmentH1ScopedChildInspection(root,packet(),spec(),budget(),LIMITS,expected_anchor_record=pin,**args)
    try:
        assert calls==[0,1,2]
        first=owner.inspect()
        assert type(first) is api.H1ScopedChildAudit and first.inspection==expected
        assert calls==[0,1,2] and owner._child._token is None
        assert owner.inspect()==first
        assert calls==[0,1,2,0,1,2]
        with pytest.raises(TypeError):owner.run()
    finally:owner.close()


@pytest.mark.parametrize('fault',['epoch','own_dml','cache','token','implementation'])
def test_scope_drift_is_poisoned(tmp_path,saved,monkeypatch,fault):
    root,args,pin,_=prepared(tmp_path,saved,monkeypatch)
    owner=api.DevelopmentH1ScopedChildInspection(root,packet(),spec(),budget(),LIMITS,expected_anchor_record=pin,**args)
    archive=owner._child
    if fault=='epoch':
        peer=sqlite3.connect(archive._journal._database)
        peer.execute('PRAGMA user_version=7')
        peer.commit();peer.close()
    elif fault=='own_dml':archive._writer.execute('UPDATE metadata SET header=header')
    elif fault=='cache':archive._state=replace(archive._state,canonical_locks=(21.,1.,20.))
    elif fault=='token':archive._token.fingerprint='0'*64
    else:monkeypatch.setattr(api,'implementation_identity',lambda:'0'*64)
    try:
        with pytest.raises(ValueError):owner.inspect()
        with pytest.raises(ValueError):owner.inspect()
    finally:owner.close()
