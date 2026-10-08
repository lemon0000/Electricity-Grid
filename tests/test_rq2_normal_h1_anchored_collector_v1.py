import pytest
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,packet,spec,LIMITS,budget
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_anchored_collector as api


def make(tmp_path,**kwargs):
    return api.DevelopmentH1AnchoredCollector(tmp_path/'collector_non_authoritative',packet(),spec(),budget(),LIMITS,
        anchor_root=tmp_path/'anchor_non_authoritative',parent_intent_head='1'*64,source_lineage_identity='2'*64,**kwargs)


def test_each_effect_has_durable_anchor_and_reopen_needs_no_memory_head(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    calls=[]
    def solve(*a,**k):
        receipt=owner._anchor.inspect()
        assert receipt.registry_head==owner._registry.head
        assert receipt.sequence==len(calls)+1
        calls.append(True)
        return saved[1][len(calls)-1]
    monkeypatch.setattr(api.base.native.capture,'solve_once',solve)
    try:
        result=owner.run(expected_head=owner.inspect().registry_head)
        assert result.status=='accepted' and len(calls)==3
        assert owner._anchor.inspect().sequence==6
    finally:owner.close()
    reopened=make(tmp_path)
    try:
        assert reopened.inspect()==result
        with pytest.raises(ValueError,match='retried'):reopened.run(expected_head=result.registry_head)
    finally:reopened.close()


def test_anchor_failure_prevents_first_native_call(tmp_path,monkeypatch):
    owner=make(tmp_path,create=True)
    def fail(*a,**k):raise RuntimeError('anchor unavailable')
    monkeypatch.setattr(owner._anchor,'advance',fail)
    try:
        with pytest.raises(RuntimeError):owner.run(expected_head=owner.inspect().registry_head)
        assert owner._child.inspect().stored_reports==0
    finally:owner.close()


def test_child_commit_unknown_recovers_from_anchor_only(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    monkeypatch.setattr(api.base.native.capture,'solve_once',lambda *a,**k:saved[1][0])
    commit=owner._child._journal._commit
    def fail(conn):commit(conn);raise RuntimeError('child uncertain')
    monkeypatch.setattr(owner._child._journal,'_commit',fail)
    try:
        with pytest.raises(RuntimeError):owner.run(expected_head=owner.inspect().registry_head)
    finally:owner.close()
    reopened=make(tmp_path)
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.stored_reports==1 and state.solver_calls is None
        with pytest.raises(ValueError,match='retried'):reopened.run(expected_head=state.registry_head)
    finally:reopened.close()


def test_child_write_requires_checkpoint_anchor(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    rows=iter(saved[1])
    monkeypatch.setattr(api.base.native.capture,'solve_once',lambda *a,**k:next(rows))
    commit=owner._child._journal._commit
    sequences=[]
    def checked(conn):
        receipt=owner._anchor.inspect()
        assert receipt.registry_head==owner._registry.head
        sequences.append(receipt.sequence)
        commit(conn)
    monkeypatch.setattr(owner._child._journal,'_commit',checked)
    try:
        assert owner.run(expected_head=owner.inspect().registry_head).status=='accepted'
        assert sequences==[2,3,4,5]
    finally:owner.close()


def test_stale_anchor_after_report_prevents_child_write(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    def solve(*a,**k):
        (owner._anchor._lease.root/'001.json').write_bytes(b'{}')
        return saved[1][0]
    monkeypatch.setattr(api.base.native.capture,'solve_once',solve)
    try:
        with pytest.raises(ValueError):owner.run(expected_head=owner.inspect().registry_head)
        assert owner._child.inspect().stored_reports==0
    finally:owner.close()


@pytest.mark.parametrize('committed',[False,True])
def test_process_exit_recovers_only_from_durable_anchor(tmp_path,committed):
    import subprocess
    import sys
    from pathlib import Path
    script='''
import json,os,sys
from pathlib import Path
from tests.test_rq2_normal_h1_anchored_collector_v1 import make,api
from tests.test_rq2_normal_h1_hour_archive_v1 import SAMPLE
raw=json.loads(SAMPLE.read_bytes())['reports'][0].encode('ascii')
owner=make(Path(sys.argv[1]),create=True)
api.base.native.capture.solve_once=lambda *a,**k:raw
commit=owner._child._journal._commit
def crash(connection):
    if sys.argv[2]=='1':commit(connection)
    os._exit(17)
owner._child._journal._commit=crash
owner.run(expected_head=owner.inspect().registry_head)
raise AssertionError('expected process exit')
'''
    result=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path),str(int(committed))],
        cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=60)
    assert result.returncode==17,result.stderr
    reopened=make(tmp_path)
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.stored_reports==int(committed)
        assert state.solver_calls is None and state.projection is None
        with pytest.raises(ValueError,match='retried'):reopened.run(expected_head=state.registry_head)
    finally:reopened.close()


@pytest.mark.parametrize('phase',[1,2])
@pytest.mark.parametrize('persisted',[False,True])
def test_anchor_commit_ambiguity_reopen(tmp_path,saved,monkeypatch,phase,persisted):
    owner=make(tmp_path,create=True)
    monkeypatch.setattr(api.base.native.capture,'solve_once',lambda *a,**k:saved[1][0])
    advance=owner._anchor.advance
    def uncertain(*a,**k):
        if owner._anchor.inspect().sequence+1!=phase:return advance(*a,**k)
        if persisted:advance(*a,**k)
        raise RuntimeError('anchor confirmation unknown')
    monkeypatch.setattr(owner._anchor,'advance',uncertain)
    try:
        with pytest.raises(RuntimeError):owner.run(expected_head=owner.inspect().registry_head)
    finally:owner.close()
    if not persisted:
        with pytest.raises(ValueError):make(tmp_path)
    else:
        reopened=make(tmp_path)
        try:
            state=reopened.inspect()
            assert state.status=='pending_unknown' and state.stored_reports==0
            assert state.projection is None and state.solver_calls is None
            with pytest.raises(ValueError,match='retried'):reopened.run(expected_head=state.registry_head)
        finally:reopened.close()


def test_wrong_anchor_pin_rejected_before_registry_open(tmp_path,monkeypatch):
    owner=make(tmp_path,create=True)
    owner.close()
    def denied(*a,**k):pytest.fail('incorrect anchor pin reached registry')
    monkeypatch.setattr(api.base.chunks.DevelopmentH1ChunkJournal,'__init__',denied)
    with pytest.raises(ValueError,match='anchor record mismatch'):
        make(tmp_path,expected_anchor_record='0'*64)
