import pytest
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,packet,spec,LIMITS,budget
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_stage_collector as api


def make(tmp_path,**kwargs):
    return api.DevelopmentH1StageCollector(tmp_path/'collector_non_authoritative',packet(),spec(),budget(),LIMITS,
        parent_intent_head='1'*64,source_lineage_identity='2'*64,**kwargs)


def test_intent_and_each_receipt_precede_next_call(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    seen=[]
    def solve(*a,**k):
        assert owner._registry_state().events==len(seen)+1
        state=owner._child.inspect()
        assert state.stored_reports==len(seen)
        seen.append(state.canonical_locks)
        return saved[1][len(seen)-1]
    monkeypatch.setattr(api.native.capture,'solve_once',solve)
    try:
        result=owner._run_checkpoint_development(expected_head=owner.inspect().registry_head)
        assert seen==[(),(20.,),(20.,1.)]
        assert result.status=='accepted' and result.solver_calls==3
        assert not result.formal_result and not result.native_execution_authenticated
    finally:owner.close()
    reopened=make(tmp_path,expected_head=result.registry_head,expected_child_head=result.child_head)
    try:
        assert reopened.inspect()==result
        with pytest.raises(ValueError,match='retried'):reopened._run_checkpoint_development(expected_head=result.registry_head)
    finally:reopened.close()


def test_native_exception_leaves_nonresumable_pending(tmp_path,monkeypatch):
    owner=make(tmp_path,create=True)
    def fail(*a,**k):raise RuntimeError('native invocation unknown')
    monkeypatch.setattr(api.native.capture,'solve_once',fail)
    try:
        with pytest.raises(RuntimeError):owner._run_checkpoint_development(expected_head=owner.inspect().registry_head)
        head=owner._registry.head
        child=owner._child.head
        with pytest.raises(ValueError):owner._run_checkpoint_development(expected_head=head)
    finally:owner.close()
    reopened=make(tmp_path,expected_head=head,expected_child_head=child)
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.solver_calls is None
        assert state.projection is None and not state.resumable
        with pytest.raises(ValueError,match='retried'):reopened._run_checkpoint_development(expected_head=head)
    finally:reopened.close()


def test_intent_commit_failure_prevents_native_call(tmp_path,monkeypatch):
    owner=make(tmp_path,create=True)
    def fail(*a):raise RuntimeError('intent commit')
    monkeypatch.setattr(owner._registry,'_commit',fail)
    try:
        with pytest.raises(RuntimeError,match='intent commit'):owner._run_checkpoint_development(expected_head=owner.inspect().registry_head)
    finally:owner.close()


def test_sink_failure_stops_next_native_call(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    calls=[]
    def solve(*a,**k):calls.append(True);return saved[1][0]
    def fail(*a):raise RuntimeError('sink commit')
    monkeypatch.setattr(api.native.capture,'solve_once',solve)
    monkeypatch.setattr(owner._child._journal,'_commit',fail)
    try:
        with pytest.raises(RuntimeError,match='sink commit'):owner._run_checkpoint_development(expected_head=owner.inspect().registry_head)
        assert len(calls)==1 and owner._registry.inspect().events==2
    finally:owner.close()


def test_same_registry_root_cannot_create_second_attempt(tmp_path):
    owner=make(tmp_path,create=True)
    owner.close()
    with pytest.raises((ValueError,FileExistsError,OSError)):make(tmp_path,create=True)


def test_raw_rejection_stops_calls_and_is_reopenable(tmp_path,monkeypatch):
    owner=make(tmp_path,create=True)
    calls=[]
    def solve(*a,**k):calls.append(True);return b'{}'
    monkeypatch.setattr(api.native.capture,'solve_once',solve)
    try:
        result=owner._run_checkpoint_development(expected_head=owner.inspect().registry_head)
        assert result.status=='rejected' and result.stored_reports==1
        assert result.solver_calls is None and result.projection is None and len(calls)==1
    finally:owner.close()
    reopened=make(tmp_path,expected_head=result.registry_head,expected_child_head=result.child_head)
    try:assert reopened.inspect()==result
    finally:reopened.close()


def test_terminal_child_without_outcome_remains_pending(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    rows=iter(saved[1])
    monkeypatch.setattr(api.native.capture,'solve_once',lambda *a,**k:next(rows))
    original=owner._append
    def append(metadata):
        if metadata['kind']=='attempt_outcome':raise RuntimeError('outcome unavailable')
        return original(metadata)
    monkeypatch.setattr(owner,'_append',append)
    try:
        with pytest.raises(RuntimeError,match='outcome'):owner._run_checkpoint_development(expected_head=owner.inspect().registry_head)
        head,child=owner._registry.head,owner._child.head
    finally:owner.close()
    reopened=make(tmp_path,expected_head=head,expected_child_head=child)
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.stored_reports==3
        assert state.projection is None and state.solver_calls is None
        with pytest.raises(ValueError,match='retried'):reopened._run_checkpoint_development(expected_head=head)
    finally:reopened.close()


def test_insufficient_short_budget_rejected_before_creation(tmp_path):
    from dataclasses import replace
    with pytest.raises(ValueError,match='short budget'):
        api.DevelopmentH1StageCollector(tmp_path/'small_non_authoritative',packet(),spec(),
            replace(budget(),max_solver_calls=2),LIMITS,parent_intent_head='1'*64,
            source_lineage_identity='2'*64,create=True)
    assert not (tmp_path/'small_non_authoritative').exists()


@pytest.mark.parametrize('committed',[False,True])
def test_checkpoint_recovers_child_with_only_independent_registry_anchor(tmp_path,saved,monkeypatch,committed):
    owner=make(tmp_path,create=True)
    anchor=tmp_path/'parent_retained_head.txt'
    append=owner._append
    def persist(metadata):
        result=append(metadata)
        anchor.write_text(owner._registry.head)
        return result
    monkeypatch.setattr(owner,'_append',persist)
    monkeypatch.setattr(api.native.capture,'solve_once',lambda *a,**k:saved[1][0])
    commit=owner._child._journal._commit
    def uncertain(connection):
        if committed:commit(connection)
        raise RuntimeError('child commit unknown')
    monkeypatch.setattr(owner._child._journal,'_commit',uncertain)
    try:
        with pytest.raises(RuntimeError,match='unknown'):owner._run_checkpoint_development(expected_head=owner.inspect().registry_head)
    finally:owner.close()
    # No child head survives the failed owner. Only independently retained registry anchor.
    reopened=make(tmp_path,expected_head=anchor.read_text())
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.stored_reports==int(committed)
        assert state.solver_calls is None and state.projection is None
        with pytest.raises(ValueError,match='retried'):reopened._run_checkpoint_development(expected_head=state.registry_head)
    finally:reopened.close()


def test_public_execution_requires_durable_parent_anchor(tmp_path):
    owner=make(tmp_path,create=True)
    try:
        with pytest.raises(ValueError,match='parent registry anchor'):
            owner.run(expected_head=owner.inspect().registry_head)
        assert owner._registry.inspect().events==0
    finally:owner.close()
